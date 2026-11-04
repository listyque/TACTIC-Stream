# Copyright (c) 2005, Southpaw Technology. Released under MIT; see LICENSE.TACTIC.
"""TACTIC account objects and Security, extracted from pyasm/security/security.py.

See LICENSE.TACTIC and tactic_stream/compatibility/source_manifest.json.
Security version 2, local authentication and native SQLite/PostgreSQL account writes.
External identity/site/2FA providers remain explicit unsupported branches.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import re
import six
from dateutil import parser
from pyasm.common import Base, Common, Config, Container, Environment, Xml
from pyasm.search import Search, SearchType, SObject
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.security.tactic_password_hasher import TacticPasswordHasher
from .access_manager import AccessManager, Sudo

__all__ = ['Login', 'LoginGroup', 'LoginInGroup', 'Site', 'Ticket', 'Security', 'get_security_version']


@contextmanager
def _security_transaction():
    """Native account writes join a command or own one local transaction."""
    from pyasm.search import Transaction
    transaction = Transaction.get()
    owner = transaction is None or not transaction.is_in_transaction()
    if owner:
        transaction = Transaction.get(create=True)
        record_flag, sync_flag = transaction.record_flag, transaction.sync_flag
        # Authentication is local; no remote server/queue has been configured.
        transaction.set_sync(False)
        # Password verification may persist failure counters before any user
        # has logged in. It has no authenticated actor for an undo journal.
        transaction.set_record(bool(Environment.get_security().get_login()))
    depth = Container.get('Security:writing') or 0
    Container.put('Security:writing', depth + 1)
    try:
        yield transaction
        if owner:
            transaction.commit()
            from pyasm.command import Trigger
            Trigger.call_all_triggers()
    except Exception:
        if owner and transaction.is_in_transaction():
            transaction.rollback()
        raise
    finally:
        Container.put('Security:writing', depth)
        if owner:
            transaction.set_record(record_flag)
            transaction.set_sync(sync_flag)


def _require_admin():
    security = Environment.get_security()
    if security is None or not (security.is_admin() or Sudo.is_sudo()):
        raise SecurityException('Account administration requires administrator access')


def _clear_account_cache():
    Container.put('FileUndo:identity-revision', (Container.get('FileUndo:identity-revision') or 0) + 1)
    Login.clear_cache()
    LoginGroup.clear_cache()
    LoginInGroup.clear_cache()
    Ticket.clear_cache()
    Container.put('LoginGroup:Groups_in_login', {})
    security = Environment.get_security()
    if security and security.get_login():
        login = Login.get_by_login(security.get_user_name())
        if not login or login.is_retired():
            security.sign_out()
        else:
            security._login = login
            security._do_login()


def get_security_version():
    return 2


class LoginInGroupException(Exception):
    pass


class Login(SObject):

    SEARCH_TYPE = "sthpw/login"

    def get_defaults(self):
        '''specifies the defaults for this sobject'''
        defaults = super(Login, self).get_defaults()

        login = self.get_value("login")
        if not login:
            login = self.get_value("code")

        if not login:
            login = Common.generate_alphanum_key(num_digits=12, delimit=4)

        # add the password "tactic" to any user that does not have one
        # specified
        defaults['password']= "39195b0707436a7ecb92565bf3411ab1"
        defaults['code'] = login
        defaults['upn'] = login
        defaults['login'] = login

        return defaults



    def get_display_value(self, long=False):
            return self.get_value("display_name") or self.get_value("code")






    def update_trigger(self):
        # the login groups are cached, so when an update has been made,
        # this cache has to be refreshed
        security = Environment.get_security()
        security.reset_access_manager()



    def get_primary_key(self):
        return "login"

    def get_foreign_key(self):
        return "login"

    def get_icon_context(self, context=None):
        return "icon"

    def get_description(self):
        return self.get_full_name()

    def get_code(self):
        return self.get_value("code")

    def get_login(self):
        return self.get_value("login")

    def get_full_name(self):
        full_name = "%s %s" % (self.get_value("first_name"), self.get_value("last_name"))
        full_name = full_name.strip()
        return full_name

    def get_full_email(self):
        email = self.get_value("email")
        if email:
            first_name = self.get_value("first_name") or ""
            last_name = self.get_value("last_name") or ""
            value = "%s %s <%s>" % (first_name, last_name, email)
            return value
        else:
            return ""

    def add_to_group(self, group_name):
        _require_admin()
        with _security_transaction():
            '''Adds a user to the specified group'''
            if isinstance(group_name, six.string_types):
                self.__validate_group(group_name)
            else:
                group_name = group_name.get_value("login_group")

            # use the sobject as well
            LoginInGroup.create_by_name( self.get_value("login"), group_name )
            _clear_account_cache()

    def remove_from_group(self, group_name):
        _require_admin()
        with _security_transaction():
            '''removes the user from a specfied group'''

            if isinstance(group_name, six.string_types):
                self.__validate_group(group_name)
            else:
                group_name = group_name.get_value("login_group")

            # use the sobject as well
            login_in_group = LoginInGroup.get_by_names( \
                    self.get_value("login"), group_name)
            if login_in_group != None:
                login_in_group.delete()
            _clear_account_cache()


    def remove_all_groups(self, except_list=[]):
        _require_admin()
        with _security_transaction():
            '''Remove the user from a specfied group. Return a list of skipped login_in_group'''
            connectors = LoginInGroup.get_by_login_name(self.get_value("login"))
            remaining = []
            for login_in_group in connectors:
                if login_in_group.get_value("login_group") in except_list:
                    remaining.append(login_in_group)
                    continue
                login_in_group.delete()
            _clear_account_cache()
            return remaining




    def __validate_group(self, group_name):
        group = LoginGroup.get_by_group_name(group_name)
        if not group:
            raise LoginInGroupException('This group [%s] does not exist' % group_name)


    def get_sub_group_names(self):
        '''Returns all of the names as a list of strings
        of the sub_groups a group contains'''

        connectors = LoginInGroup.get_by_login_name(self.get_login() )
        group_names = [ x.get_value("login_group") for x in connectors ]
        return group_names


    def get_sub_groups(self):
        sub_group_names = self.get_sub_group_names()
        if not sub_group_names or sub_group_names == ['']:
            return []

        search = Search("sthpw/login_group")
        search.add_filters("login_group", sub_group_names)
        groups = search.get_sobjects()


        # look access level rules for this user
        access_level = LoginGroup.NONE
        project_codes = set()
        for group in groups:
            group_access_level = group.get_value("access_level", no_exception=True)
            project_code = group.get_value("project_code")
            if project_code:
                project_codes.add(project_code)

            group_access_level = LoginGroup.ACCESS_DICT.get(group_access_level)
            if group_access_level == None:
                group_access_level = LoginGroup.LOW

            if group_access_level > access_level:
                access_level = group_access_level
        groups.append(self.get_security_level_group(access_level, project_codes))

        return groups


    def get_default_security_level():
        ''' this should match the default in get_sub_group()'''
        return "low"
    get_default_security_level = staticmethod(get_default_security_level)


    def get_security_level_group(access_level, project_codes=[]):

        xml = LoginGroup.get_default_access_rule(access_level, project_codes, add_root=True)

        default_group = SearchType.create("sthpw/login_group")
        default_group.set_value("login_group", "default")
        default_group.set_value("access_rules", xml)
        return default_group

    get_security_level_group = staticmethod(get_security_level_group)




    # static methods

    def get_search():
        return Search("sthpw/login")
    get_search = staticmethod(get_search)


    def get_by_code(code):
        return  Login.get_by_login(code)
    get_by_code = staticmethod(get_by_code)

    def get_by_login(login_name, namespace=None, use_upn=False):
        if not login_name:
            return None
        # Namespace/UPN are part of the identity; the original cache ignored them.
        insensitive = Config.get_value('security', 'case_insensitive_login') == 'true'
        if insensitive:
            login_name = login_name.lower()
        key = login_name if not namespace and not use_upn and not insensitive else (login_name, namespace, use_upn, insensitive)
        cached = Login.get_cached_obj(key)
        if cached:
            return cached
        sudo = Sudo()
        try:
            search = Search("sthpw/login")
            search.set_show_retired(True)
            if insensitive:
                # Original SQLite translates anchored regexes to LIKE, so
                # '^name'/'name$' never match. Compare literal identities.
                login = next((row for row in search.get_sobjects()
                              if (row.get_login().lower() == login_name or
                                  (use_upn and login_name != 'admin' and row.get_value('upn').lower() == login_name))
                              and (not namespace or login_name == 'admin' or row.get_value('namespace') == namespace)), None)
            else:
                if use_upn and login_name != "admin":
                    search.add_op("begin")
                search.add_filter("login", login_name)
                if use_upn and login_name != "admin":
                    search.add_filter("upn", login_name)
                    search.add_op("or")
                if namespace and login_name != "admin":
                    search.add_filter("namespace", namespace)
                login = search.get_sobject()
            if login_name == "admin" and login is None:
                raise UnsupportedContract("Virtual admin creation is not migrated")
        finally:
            sudo.exit()
        Login.get_cache_dict()[key] = login
        return login
    get_by_login = staticmethod(get_by_login)



    def set_password(self, password):
        security = Environment.get_security()
        own_account = security and security.is_logged_in() and self.get_base_search_type() == 'sthpw/login' and security.get_user_name() == self.get_login()
        if not own_account:
            _require_admin()
        sudo = Sudo()
        try:
            with _security_transaction():
                encrypted = self.encrypt_password(password)
                self.set_value("password", encrypted)
                self.commit()
                _clear_account_cache()
        finally:
            sudo.exit()



    def create(cls, user_name, password, first_name=None, last_name=None, groups=None, namespace=None, display_name=None, project_code=None):
        _require_admin()
        with _security_transaction():
            if Login.get_by_login(user_name):
                raise SecurityException('Login already exists')
            for group in groups or []:
                if not LoginGroup.get_by_group_name(group):
                    raise LoginInGroupException('This group [%s] does not exist' % group)

            login = SearchType.create("sthpw/login")
            login.set_value("login", user_name)
            login.set_value("upn", user_name)

            # encrypt the password
            encrypted = cls.encrypt_password(password)
            login.set_value("password", encrypted)

            if first_name:
                login.set_value("first_name", first_name)
            if last_name:
                login.set_value("last_name", last_name)

            if display_name:
                login.set_value("display_name", display_name)

            # DEPRECATED: this is no longer supported
            #if groups != None:
            #    login.set_value("groups", groups)

            if namespace != None:
                login.set_value("namespace", namespace)


            login.commit()

            if groups:
                for group in groups:
                    login.add_to_group(group)
            else:
                default_group = LoginGroup.get_project_default(project_code=project_code)
                if default_group:
                    login.add_to_group(default_group)

            return login

    create = classmethod(create)


    def get_default_encrypted_password():
        return "39195b0707436a7ecb92565bf3411ab1"
    get_default_encrypted_password = staticmethod(get_default_encrypted_password)

    def get_default_password():
        return "tactic"
    get_default_password = staticmethod(get_default_password)




    def encrypt_password(password):
        salt = Common.generate_alphanum_key(num_digits=8, mode='alpha')
        iter_code = 'D'
        encrypted = TacticPasswordHasher().encode(password, salt, iter_code)
        return encrypted
    encrypt_password = staticmethod(encrypt_password)



    def validate_password(password):
        try:
            password = password.decode()
        except (UnicodeDecodeError, AttributeError):
            pass

        import re
        """
        - at least one number.
        - at least one uppercase and one lowercase character.
        - at least one special symbol.
        - min 8 characters long.
        """
        # Regex modified from  https://www.geeksforgeeks.org/password-validation-in-python/
        reg = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{8,}$"

        # compiling regex
        pat = re.compile(reg)

        # searching regex
        mat = re.search(pat, password)

        # validating conditions
        if mat:
            return True

        return False

    validate_password = staticmethod(validate_password)


    def check_previous_passwords(self, password):
        from pyasm.security.authenticator import verify_password
        data = self.get_json_value('data', {})
        return not any(verify_password(password, stored) for stored in data.get('previous_passwords', []))


    def check_password_expiry(self):
        expiry = self.get_json_value('data', {}).get('password_expiry')
        if not expiry:
            return True
        try:
            expiry = parser.parse(expiry)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) <= expiry
        except (TypeError, ValueError):
            return False


    def check_invalid_logins(self, num_attempts=5):
        data = self.get_json_value('data', {})
        return int(data.get('invalid_logins') or 0) < int(num_attempts)



class LoginGroup(Login):

    SEARCH_TYPE = "sthpw/login_group"
    (NONE, MIN, LOW, MED, HI) = range(5)

    ACCESS_DICT = {'high': HI, 'medium': MED, 'low': LOW, 'min': MIN, 'none': NONE}

    def get_defaults(self):
        defaults = {}
        if not self.get_value("code"):
            if self.get_value("login_group"):
                defaults['code'] = self.get_value("login_group")
            else:
                code = Common.generate_alphanum_key(12, delimit=4)
                defaults['code'] = code
                defaults['login_group'] = code
        else:
            defaults['login_group'] = self.get_value("code")


        # LoginGroupTrigger handles the update event
        return defaults


    def get_display_value(self, long=False):
        return self.get_value("name") or self.get_value("code")


    def is_admin(self):
        group = self.get_value("login_group")
        return group == "admin"


    def get_primary_key(self):
        return "login_group"

    def get_foreign_key(self):
        return "login_group"

    def get_description(self):
        return self.get_value('description')

    def get_login_group(self):
        return self.get_value("login_group")

    def get_sub_group_names(self):
        sub_groups_str = self.get_value("sub_groups")
        return sub_groups_str.split("|")

    def get_access_rules(self):
        return self.get_value("access_rules")

    def get_xml_root(self, name):
        if name == "access_rules":
            return "rules"



    def get_logins(self):
        connectors = LoginInGroup.get_by_group_name(self.get_login_group())
        if not connectors:
            return []

        search = Search("sthpw/login")
        search.add_filters("login", [x.get_value("login") for x in connectors])
        logins = search.get_sobjects()
        return logins



    # static methods

    def get_by_code(code):
        return LoginGroup.get_by_group_name(code)
    get_by_code = staticmethod(get_by_code)

    def get_by_group_name(group_name):
         # find the group in the database
        search = Search("sthpw/login_group")
        search.add_filter("login_group", group_name)
        group = search.get_sobject()
        return group
    get_by_group_name = staticmethod(get_by_group_name)

    def get(namespace, group_names):
        assert isinstance(group_names, list)
        search = Search("sthpw/login_group")
        search.add_filter("namespace", namespace)
        search.add_filters("login_group", group_names)

        return search.get_sobjects()
    get = staticmethod(get)

    def get_group_names(cls, login_name=''):
        if not login_name:
            login_name = Environment.get_user_name()

        group_names = []
        login_in_groups = LoginInGroup.get_by_login_name(login_name)
        if login_in_groups:
            group_names = SObject.get_values(login_in_groups, 'login_group')
        return group_names
    get_group_names = classmethod(get_group_names)



    def get_login_codes_in_group(cls, login_name=None):
        if not login_name:
            login_name = Environment.get_user_name()

        key = "LoginGroup:Groups_in_login"
        groups_dict = Container.get(key)
        if groups_dict == None:
            groups_dict = {}
            Container.put(key, groups_dict)

        results = groups_dict.get(login_name)
        if results != None:
            return results

        group_names = cls.get_group_names(login_name)

        login_codes = set()
        for group_name in group_names:
            group = LoginGroup.get_by_code(group_name)
            if group:
                logins = group.get_logins()

                for login in logins:
                    login_code = login.get_value("login")
                    login_codes.add(login_code)
            else:
                #print("This group [%s] no longer exists" %group_name)
                pass

        results = list(login_codes)
        groups_dict[login_name] = results

        return results
    get_login_codes_in_group = classmethod(get_login_codes_in_group)



    def get_by_project(cls, project_code=None):

        if not project_code:
            from pyasm.biz import Project
            project = Project.get()
            project_code = project.get_code()

        # at the moment, the only way to tell if a group is "in" a project
        # is by the security rules
        search = Search("sthpw/login_group")
        groups = search.get_sobjects()

        project_groups = []
        for group in groups:

            access_level = group.get_value("access_level")

            # this column complete determines if a login is in a project or not
            group_project_code = group.get_value("project_code")
            if group_project_code:
                if project_code == group_project_code:
                    project_groups.append(group)
                continue

            elif access_level in ['high', 'medium']:
                project_groups.append(group)
                continue


            access_rules = group.get_xml_value("access_rules")
            node = access_rules.get_node("rules/rule[@group='project' and @code='%s' and @access='allow']" % project_code)
            if node is not None:
                project_groups.append( group )

            else:
                node = access_rules.get_node("rules/rule[@group='project' and @code='*' and @access='allow']")
                if node is not None:
                    print("added2")
                    project_groups.append( group )


        return project_groups
    get_by_project = classmethod(get_by_project)


    def get_project_default(cls, project_code=None):
        groups = cls.get_by_project(project_code)
        for group in groups:
            if group.get_value("is_default", no_exception=True):
                return group
        return None
    get_project_default = classmethod(get_project_default)




    def get_access_level(self):
        level = self.get_value('access_level')
        if not level:
            level = Login.get_default_security_level()
        level = self.ACCESS_DICT.get(level)
        return level



    def get_default_access_rule(access_level, project_codes=[], add_root=True):
        ''' Get the default xml rule for a paricular access level'''
        #(NONE, MIN, LOW, MED, HI) = range(5)
        assert access_level in [LoginGroup.NONE, LoginGroup.MIN, LoginGroup.LOW, LoginGroup.MED, LoginGroup.HI]
        xml = []

        if add_root:
            xml.append('''<rules>''')

        xml.append('''<rule group="builtin" default="deny"/>''')
        xml.append('''<rule category="secure_wdg" default="deny"/>''')
        xml.append('''<rule category="public_wdg" default="edit"/>''')

        if access_level == LoginGroup.HI:
            if project_codes:
                for project_code in project_codes:
                    xml.append('''<rule group="project" code="%s" access="allow"/>''' % project_code)
            else:
                xml.append('''<rule group="project" code="*" access="allow"/>''')
            xml.append('''<rule group="search_type" code="*" access="allow"/>''')
            xml.append('''<rule group="link" element="*" access="allow"/>''')
            xml.append('''<rule group="gear_menu" submenu="*" label="*" access="allow"/>''')
            xml.append('''<rule group="process" process="*" access="allow"/>''')
            xml.append('''<rule group="process" process="*" pipeline="*" access="allow"/>''')
            xml.append('''<rule group="builtin" key="edit" access="allow"/>''')
            xml.append('''<rule group="builtin" key="view_side_bar" access="allow"/>''')


        elif access_level == LoginGroup.MED:
            if project_codes:
                for project_code in project_codes:
                    xml.append('''<rule group="project" code="%s" access="allow"/>''' % project_code)
            else:
                xml.append('''<rule group="project" code="*" access="allow"/>''')

            xml.append('''<rule group="search_type" code="*" access="allow"/>''')
            xml.append('''<rule group="process" process="*" access="allow"/>''')
            xml.append('''<rule group="process" process="*" pipeline="*" access="allow"/>''')
            xml.append('''<rule group="builtin" key="edit" access="allow"/>''')


        elif access_level == LoginGroup.LOW:
            if project_codes:
                for project_code in project_codes:
                    xml.append('''<rule group="project" code="%s" access="allow"/>''' % project_code)
            xml.append('''<rule group="search_type" code="*" access="allow"/>''')
            xml.append('''<rule group="process" process="*" access="allow"/>''')
            xml.append('''<rule group="process" process="*" pipeline="*" access="allow"/>''')

        elif access_level == LoginGroup.MIN:
            if project_codes:
                for project_code in project_codes:
                    xml.append('''<rule group="project" code="%s" access="allow"/>''' % project_code)
            xml.append('''<rule group="search_type" code="*" access="allow"/>''')

        else: # no security access
            if project_codes:
                for project_code in project_codes:
                    xml.append('''<rule group="project" code="%s" access="allow"/>''' % project_code)

        if add_root:
            xml.append('''</rules>''')
        xml = "\n".join(xml)

        return xml

    get_default_access_rule = staticmethod(get_default_access_rule)



class LoginInGroup(SObject):

    SEARCH_TYPE = "sthpw/login_in_group"

    def get_display_value(self, long=False):
        user = Search.get_by_code("sthpw/login", self.get_value("login"))
        return user.get_value("display_name") or user.get_code()

    def get_by_names(login_name, group_name):
        search = Search( LoginInGroup.SEARCH_TYPE, sudo=True )
        search.add_filter("login", login_name)
        search.add_filter("login_group", group_name)
        sobject = search.get_sobject()
        return sobject
    get_by_names = staticmethod(get_by_names)


    def get_by_login_name(cls, login_name):
        search = Search( LoginInGroup.SEARCH_TYPE )
        search.add_filter("login", login_name)
        sobjects = cls.get_by_search(search, "%s|%s" %(cls.SEARCH_TYPE, login_name), is_multi=True)
        return sobjects
    get_by_login_name = classmethod(get_by_login_name)

    def get_by_group_name(login_name):
        search = Search( LoginInGroup.SEARCH_TYPE )
        search.add_filter("login_group", login_name)
        sobjects = search.get_sobjects()
        return sobjects
    get_by_group_name = staticmethod(get_by_group_name)



    def create(login, login_group):
        _require_admin()
        with _security_transaction():
            return LoginInGroup.create_by_name( \
                login.get_value("login"), login_group.get_value("login_group") )
    create = staticmethod(create)



    def create_by_name(login_name, group_name):
        _require_admin()
        with _security_transaction():
            if not Login.get_by_login(login_name) or not LoginGroup.get_by_group_name(group_name):
                raise LoginInGroupException('Login and group must exist')
            existing = LoginInGroup.get_by_names(login_name, group_name)
            if existing:
                return existing
            sobject = SearchType.create( LoginInGroup.SEARCH_TYPE )
            sobject.set_value( "login", login_name)
            sobject.set_value( "login_group", group_name)
            sobject.commit()
            _clear_account_cache()
            return sobject
    create_by_name = staticmethod(create_by_name)



def _valid_ticket_expiry(expiry):
    """The same expiry rule for SObjects and the transport identity lookup."""
    if not expiry:
        return True
    try:
        if not isinstance(expiry, datetime):
            # Stored database timestamps need no general-purpose date parser.
            if re.fullmatch(r'\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?', expiry):
                expiry = datetime.fromisoformat(expiry)
            else:
                expiry = parser.parse(expiry)
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return False
    return expiry > datetime.now(timezone.utc)


class Site:
    '''Original default-site provider; named-site database routing remains unported.'''

    def get_project_code(self):
        return 'admin'

    def get_base_search_type(self):
        return 'sthpw/virtual'

    def get_search_type(self):
        return 'sthpw/virtual'

    def get_value(self, name, no_exception=True):
        if name == 'code':
            return Site.get_site()

    def get_id(self):
        # Source's pseudo-SObject lacks identity when the default site code is empty.
        return -1

    def get_search_key(self, use_id=False):
        from pyasm.search import SearchKey
        return SearchKey.get_by_sobject(self, use_id=use_id)

    def get_data(self, merged=True):
        return {'code': self.get_value('code')}

    @classmethod
    def get(cls):
        class_name = Config.get_value('security', 'site_class')
        if class_name and class_name not in ('pyasm.security.Site', 'pyasm.security.security.Site'):
            raise UnsupportedContract('Custom site providers require native multi-site routing')
        return cls()

    @classmethod
    def get_sites(cls):
        sites = Container.get('sites')
        if sites:
            raise UnsupportedContract('Named site contexts require native multi-site routing')
        return sites

    @classmethod
    def get_site(cls):
        sites = cls.get_sites()
        return sites[-1] if sites else ''

    @classmethod
    def get_first_site(cls):
        sites = cls.get_sites()
        return sites[0] if sites else ''

    @classmethod
    def set_site(cls, site, store_security=True, options={}):
        if not site:
            print('WARNING: site is empty')
            return
        raise UnsupportedContract('Named site contexts require native multi-site routing')

    @classmethod
    def pop_site(cls, pop_security=True):
        sites = cls.get_sites()
        if sites is None:
            return ''
        return None

    @classmethod
    def clear_sites(cls):
        Container.put('sites', [])

    @classmethod
    def get_default_project(cls):
        return Config.get_value('install', 'default_project')

    @classmethod
    def get_user_project(cls):
        return Config.get_value('install', 'default_project')

    @classmethod
    def get_by_login(cls, login):
        return ''

    @classmethod
    def get_by_ticket(cls, ticket):
        return ''

    @classmethod
    def build_ticket(cls, ticket):
        return ticket

    @classmethod
    def validate_ticket(cls, ticket):
        # Original provider hook only; actual ticket authentication is Security's job.
        return True

    @classmethod
    def get_connect_data(cls, site, database=None):
        if site:
            raise UnsupportedContract('Named site connections require native multi-site routing')
        return {}

    @classmethod
    def get_db_resource(cls, site, database):
        if site:
            raise UnsupportedContract('Named site connections require native multi-site routing')
        return None

    @classmethod
    def get_db_resource_by_search_type(cls, search_type):
        return None

    @classmethod
    def get_site_data(cls, site):
        if site:
            raise UnsupportedContract('Named site data requires native multi-site routing')
        return {}

    @classmethod
    def allow_guest(cls, url=None):
        return None

    @classmethod
    def get_guest_hashes(cls):
        return []

    @classmethod
    def get_api_mode(cls):
        if cls.get_site() == 'default':
            return 'closed'

    def get_site_root(self):
        return ''

    def break_up_request_path(self, path):
        return []

    @classmethod
    def get_site_dir(cls, site):
        if site:
            raise UnsupportedContract('Named site paths require native multi-site routing')

    @classmethod
    def get_asset_dir(cls, file_object=None, alias=None):
        return None

    @classmethod
    def get_web_dir(cls, file_object=None, alias=None):
        return None

    def get_authenticate_class(self):
        return None

    def get_site_redirect(self):
        return None

    def register_sites(self, startup, config):
        raise UnsupportedContract('Site registration requires native multi-site routing')

    def handle_ticket(self, ticket):
        return None

    @classmethod
    def init_site(cls, site, options={}):
        if site:
            raise UnsupportedContract('Site initialization requires native multi-site routing')

    @classmethod
    def start_site(cls, site):
        if site:
            raise UnsupportedContract('Site startup requires native multi-site routing')
        return False

    def get_request_path_info(self):
        raise UnsupportedContract('Legacy site request-path routing is not supported')

    @classmethod
    def get_login_wdg(cls, hash=None):
        raise UnsupportedContract('Legacy HTML site widgets are excluded')

    def get_guest_wdg(self, hash):
        return None


class Ticket(SObject):
    SEARCH_TYPE = "sthpw/ticket"

    '''When a user logins, a ticket is created.  This ticket is stored in the
    database as a long unique string of alpha-numeric characters.  It is stored
    on the browser as a cookie and allows the user to login with a password.
    The ticket has an expiry date set in the Tactic config file'''

    def get_key(self):
        '''get the alphanumeric unique code for the session'''
        return self.get_value("ticket")


    def get_by_key(key):
        '''class method to get Ticket sobject by it's key'''
        # find the ticket in the database
        search = Search("sthpw/ticket")
        search.add_filter("ticket", key)
        ticket = search.get_sobject()
        return ticket
    get_by_key = staticmethod(get_by_key)


    def get_by_valid_key(key):
        ticket = Ticket.get_by_key(key)
        if not ticket:
            return None
        return ticket if _valid_ticket_expiry(ticket.get_value('expiry')) else None
    get_by_valid_key = staticmethod(get_by_valid_key)




    def create(key, login, expiry=None, interval=None, category=None, commit=True):
        _require_admin()
        if not isinstance(key, str) or not key or len(key) > 100:
            raise SecurityException('A ticket key of 1..100 characters is required')
        from pyasm.search import Sql
        impl = Sql.get_default_database_impl()
        now = impl.get_timestamp_now()
        generated_expiry = expiry == -1 or not expiry or expiry == 'NULL'
        if expiry == -1:
            expiry = 'NULL'
        elif not expiry or expiry == 'NULL':
            interval = interval or Config.get_value('security', 'ticket_expiry') or '10 hour'
            offset, unit = interval.split()
            expiry = impl.get_timestamp_now(offset=int(offset), type=unit)
        ticket = SearchType.create('sthpw/ticket')
        ticket.set_auto_code()
        ticket.set_value('ticket', key)
        ticket.set_value('login', login)
        ticket.set_value('timestamp', now, quoted=False)
        if category:
            ticket.set_value('category', category)
        if isinstance(expiry, datetime):
            ticket.set_value('expiry', expiry)
        else:
            # Keep source SQL timestamp expressions; quoted dates are also usable.
            value_info = impl.process_value('expiry', expiry, 'timestamp')
            if not generated_expiry and (value_info is None or value_info['quoted']):
                expiry = parser.parse(expiry)
                ticket.set_value('expiry', expiry)
            else:
                ticket.set_value('expiry', expiry, quoted=False)
        if commit:
            with _security_transaction():
                ticket.commit(triggers='none')
        return ticket
    create = staticmethod(create)

    def update_session_expiry():
        from pyasm.search import Sql
        security = Environment.get_security()
        ticket = security.get_ticket()
        timeout = Config.get_value('security', 'inactive_ticket_expiry')
        if not timeout:
            return
        if not ticket or not Ticket.get_by_valid_key(ticket.get_key()):
            raise SecurityException('Invalid or expired ticket')
        offset, unit = timeout.split()
        expiry = Sql.get_default_database_impl().get_timestamp_now(offset=int(offset), type=unit)
        Ticket.update_expiry(ticket, expiry)

    update_session_expiry = staticmethod(update_session_expiry)



    def update_expiry(ticket,expiry):
        from pyasm.search import Sql
        security = Environment.get_security()
        if not security or not (security.is_admin() or Sudo.is_sudo() or
                (security.is_logged_in() and ticket.get_key() == security.get_ticket_key())):
            raise SecurityException('Ticket renewal requires its owner or administrator')
        if not Ticket.get_by_valid_key(ticket.get_key()):
            raise SecurityException('Invalid or expired ticket')
        if isinstance(expiry, datetime):
            ticket.set_value('expiry', expiry)
        else:
            info = Sql.get_default_database_impl().process_value('expiry', expiry, 'timestamp')
            if info and not info['quoted']:
                ticket.set_value('expiry', expiry, quoted=False)
            else:
                ticket.set_value('expiry', parser.parse(expiry))
        sudo = Sudo()
        try:
            with _security_transaction():
                ticket.commit(triggers='none')
        finally:
            sudo.exit()
        Ticket.clear_cache()

    update_expiry = staticmethod(update_expiry)



class Security(Base):
    '''main class dealing with user identification'''

    def __init__(self):
        self._login_var = None
        self._is_logged_in = 0
        self._groups = []
        self._group_names = []
        self._ticket = None
        self._admin_login = None
        self.add_access_rules_flag = True
        self._access_manager = AccessManager()
        self.login_cache = None


    def _get_my_login(self):
        return self._login_var
    def _set_my_login(self, login):
        self._login_var = login
        if self._login_var and self._login_var.get_value("login") == 'admin':
            self._access_manager.set_admin(True)
    _login = property(_get_my_login, _set_my_login)




    def get_version(cls):
        return get_security_version()
    get_version = classmethod(get_version)

    def is_logged_in(self):
        return self._is_logged_in

    def is_admin(self):
        return self._access_manager.is_admin()

    def set_admin(self, flag):

        if flag == self._access_manager.is_admin_flag:
            return
        return self._access_manager.set_admin(flag)

    def get_groups(self):
        return self._groups

    def get_group_names(self):
        group_names = self._group_names
        group_names.sort()
        return group_names

    def is_in_group(self, group_name):
        if group_name == "admin" and self.get_user_name() == "admin":
            return True

        return group_name in self._group_names


    def get_login(self):
        return self._login

    def get_user_name(self):
        if not self._login:
            return None
        return self._login.get_login()

    def get_ticket(self):
        return self._ticket

    def get_ticket_key(self):
        if self._ticket:
            return self._ticket.get_key()
        else:
            return ""

    def clear_ticket(self):
        self._ticket = None


    def get_access_manager(self):
        return self._access_manager


    def reset_access_manager(self):
        self._access_manager = AccessManager()
        self.add_access_rules()
        self.setup_access_manager()

    def sign_out(self):
        self._is_logged_in = 0
        self._login = None
        self._groups = []
        self._group_names = []
        self._ticket = None
        self._access_manager = AccessManager()


    def get_start_link(self):
        for group in self._groups:
            start_link = group.get_value("start_link")
            if start_link:
                return start_link


    def requires_2fa(cls):
        from pyasm.biz import ProjectSetting
        required = Config.get_value('security', 'requires_2fa')
        return required == 'true' or ProjectSetting.get_value_by_key('feature/enable_2fa') == 'true'


    requires_2fa = classmethod(requires_2fa)



    def _do_login(self):
        '''function to actually log in the user'''
        if Environment.get_security() is not self:
            raise UnsupportedContract("Security must be installed in the current Environment")
        # Each identity/group refresh owns its manager. An earlier Sudo keeps
        # its old manager and cannot overwrite the newly authenticated rights.
        self._access_manager = AccessManager()
        # This manager has no authenticated rights yet. Sudo must not discover
        # groups in set_up before the explicit discovery below repeats the work.
        self._access_manager.was_admin = False
        # get from cache
        #from pyasm.biz import LoginCache
        #self.login_cache = LoginCache.get("logins")

        # find all of the groups for this login
        self._groups = None
        if self._groups == None:
            self._groups = []
            self._group_names = []

            sudo = Sudo()
            try:
                # Source Sudo inserts a temporary 'admin' group. Discovery must
                # use persisted groups, including a real group of that name.
                self._groups, self._group_names = [], []
                self._find_all_login_groups()
            finally:
                sudo.exit()


            # set the results to the cache
            #self.login_cache.set_attr("%s:groups" % login, self._groups)
            #self.login_cache.set_attr("%s:group_names" % login, self._group_names)


        # Setup the access manager and access rules
        # Admin and admin group do not get access rules
        self._group_names = [group.get_login_group() for group in self._groups]
        self._access_manager.is_admin_flag = False
        self._access_manager.was_admin = self.get_user_name() == 'admin' or 'admin' in self._group_names
        is_admin = self.setup_access_manager()
        if not is_admin and self.add_access_rules_flag:
            self.add_access_rules()

        # record that the login is logged in
        self._is_logged_in = 1


    def login_as_batch(self, login_name=None, ticket=None):
        login_name = login_name or 'admin'
        self.sign_out()
        sudo = Sudo()
        try:
            login = Login.get_by_login(login_name, use_upn=True)
            if not login or login.is_retired():
                raise SecurityException('Unrecognized or disabled login [%s]' % login_name)
            if isinstance(ticket, str):
                ticket = Ticket.get_by_valid_key(ticket)
                if not ticket:
                    raise SecurityException('Invalid or expired ticket')
            if ticket:
                owner = Login.get_by_login(ticket.get_value('login'), use_upn=True)
                if not Ticket.get_by_valid_key(ticket.get_key()) or not owner or owner.get_id() != login.get_id():
                    raise SecurityException('Ticket belongs to another login')
            self._login = login
            self._ticket = ticket or self._generate_ticket(login.get_login())
            self.add_access_rules_flag = True
            self._do_login()
        except Exception:
            self.sign_out()
            raise
        finally:
            sudo.exit()



    def login_as_guest(self):
        raise UnsupportedContract('Security.login_as_guest is not migrated')





    def login_with_ticket(self, key, add_access_rules=True, allow_guest=False):
        self.sign_out()
        if not key:
            return None
        sudo = Sudo()
        try:
            ticket = Ticket.get_by_valid_key(key)
            if not ticket:
                return None
            login = Login.get_by_login(ticket.get_value('login'), use_upn=True)
            if not login or login.is_retired():
                return None
            if login.get_login() == 'guest':
                if not allow_guest:
                    return None
                raise UnsupportedContract('Guest login rules are not migrated')
            self.add_access_rules_flag = add_access_rules
            self._login, self._ticket = login, ticket
            self._do_login()
            return login
        except Exception:
            self.sign_out()
            raise
        finally:
            sudo.exit()



    def login_with_session(self, sid, add_access_rules):
        raise UnsupportedContract('Drupal session authentication is excluded; sid is not a TACTIC ticket')







    def login_user_without_password(self, login_name, expiry=None, ticket_key=None, category=None):
        _require_admin()
        sudo = Sudo()
        try:
            login = Login.get_by_login(login_name)
            if not login or login.is_retired():
                raise SecurityException('Unrecognized or disabled login [%s]' % login_name)
            ticket = Ticket.get_by_key(ticket_key) if ticket_key else None
            if ticket:
                owner = Login.get_by_login(ticket.get_value('login'), use_upn=True)
                if not owner or owner.get_id() != login.get_id():
                    raise SecurityException('Ticket belongs to another login')
            if not ticket_key:
                search = Search('sthpw/ticket')
                search.add_filter('login', login.get_login())
                ticket = next((row for row in search.get_sobjects() if _valid_ticket_expiry(row.get_value('expiry'))), None)
            with _security_transaction():
                if ticket and ticket_key:
                    from pyasm.search import Sql
                    ticket.set_value('expiry', Sql.get_default_database_impl().get_timestamp_now(1, 'day'), quoted=False)
                    ticket.commit(triggers='none')
                elif not ticket:
                    ticket = self._generate_ticket(login.get_login(), expiry, category, ticket_key)
                self.sign_out()
                self._login, self._ticket = login, ticket
                LoginInGroup.clear_cache()
                self._do_login()
                return ticket
        except Exception:
            self.sign_out()
            raise
        finally:
            sudo.exit()




    def verify_two_factor(self, login, two_factor_code):
        raise UnsupportedContract('Security.verify_two_factor is not migrated')




    def login_user(self, login_name, password, expiry=None, domain=None, two_factor_code=None, test=False):
        previous = (self._login_var, self._ticket, self._groups, self._group_names, self._is_logged_in, self._access_manager) if test else None
        self.sign_out()
        sudo = Sudo()
        try:
            if Config.get_value('security', 'authenticate_version') == '1':
                raise UnsupportedContract('Authentication version 1 is not migrated')
            if '\\' in login_name:
                domain, login_name = login_name.split('\\', 1)
            authenticate_class = Config.get_value('security', 'authenticate_class') or 'pyasm.security.TacticAuthenticate'
            if login_name == 'admin':
                authenticate_class = 'pyasm.security.TacticAuthenticate'
            if domain and login_name != 'admin':
                login_name = '%s\\%s' % (domain, login_name)
            if self.requires_2fa():
                raise UnsupportedContract('Two-factor authentication provider is not migrated')
            authenticate = Common.create_from_class_path(authenticate_class)
            if authenticate.verify(login_name, password) is not True:
                raise SecurityException('Login/Password combination incorrect')
            if test:
                return
            mode = authenticate.get_mode() or Config.get_value('security', 'authenticate_mode') or 'default'
            if Config.get_value('security', 'case_insensitive_login') == 'true':
                login_name = login_name.lower()
            if mode not in ('default', 'autocreate', 'cache'):
                raise UnsupportedContract('Unrecognized authentication mode: ' + mode)
            with _security_transaction():
                login = authenticate.get_login() or Login.get_by_login(login_name, use_upn=True)
                if not login and mode in ('autocreate', 'cache'):
                    login = SearchType.create('sthpw/login')
                    login.set_value('login', login_name)
                    login.set_value('upn', login_name)
                    authenticate.add_user_info(login, password)
                    login.commit(triggers=False)
                elif login and mode == 'cache':
                    authenticate.add_user_info(login, password)
                    login.commit(triggers=False)
                if not login or login.is_retired():
                    raise SecurityException('Login/Password combination incorrect')
                self._login = login
                self._ticket = self._generate_ticket(login.get_login(), expiry, category='gui')
                LoginInGroup.clear_cache()
                self._do_login()
                authenticate.postprocess(login, self._ticket)
        except Exception:
            self.sign_out()
            raise
        finally:
            sudo.exit()
            if previous is not None:
                self._login_var, self._ticket, self._groups, self._group_names, self._is_logged_in, self._access_manager = previous



    def generate_ticket(self, login_name, expiry=None, category=None, ticket_key=None):
        _require_admin()
        return self._generate_ticket(login_name, expiry, category, ticket_key)


    def _generate_ticket(self, login_name, expiry=None, category=None, ticket_key=None):
        handler_class = Config.get_value('security', 'authenticate_ticket_class')
        handler = Common.create_from_class_path(handler_class) if handler_class and not ticket_key else None
        key = ticket_key or (handler.generate_key(login_name, expiry=expiry, category=category) if handler else None)
        if handler and not key:
            raise SecurityException('Ticket provider did not generate a key')
        if not key:
            import secrets
            key = secrets.token_hex(32)
        sudo = Sudo()
        try:
            with _security_transaction():
                ticket = handler.create(key, login_name, expiry=expiry, category=category) if handler else None
                ticket = ticket or Ticket.create(key, login_name, expiry=expiry, category=category)
                if handler:
                    handler.alter_ticket(ticket)
                return ticket
        finally:
            sudo.exit()



    def compare_access(self, user_access, required_access):
        return self._access_manager.compare_access(user_access, required_access)


    def check_access(self, group, key, access, value=None, is_match=False, default="edit"):
        '''convenience function to check the security level to the access
        manager'''
        return self._access_manager.check_access(group, key, access, value, is_match, default=default)

    def get_access(self, group, key, default=None):
        return self._access_manager.get_access(group, key, default=default)





    def alter_search(self, search):
        '''convenience function to alter a search for security reasons'''
        # Mark only successful filtering; failed attempts must not bypass a retry.
        result = self._access_manager.alter_search(search)
        search.set_security_filter()
        return result






    def is_login_in_group(self, group):
        '''returns whether the user is in the give group'''
        if group in self._group_names:
            return True
        else:
            return False


    def _find_all_login_groups(self, group=None):
        if group is None:
            default_group = None
            for item in self._login.get_sub_groups():
                if item.get_id() == -1 and item.get_login_group() == 'default':
                    default_group = item
                else:
                    self._find_all_login_groups(item)
            if default_group is not None:
                level = LoginGroup.NONE
                projects = set()
                for item in self._groups:
                    item_level = LoginGroup.ACCESS_DICT.get(item.get_value('access_level', no_exception=True), LoginGroup.LOW)
                    level = max(level, item_level)
                    project = item.get_value('project_code')
                    if project:
                        projects.add(project)
                self._find_all_login_groups(Login.get_security_level_group(level, projects))
            return
        group_name = group.get_login_group()
        if group_name in self._group_names:
            return
        self._groups.append(group)
        self._group_names.append(group_name)
        for item in group.get_sub_groups():
            # Aggregate default rights once, after discovering all real groups.
            if item.get_id() == -1 and item.get_login_group() == 'default':
                continue
            self._find_all_login_groups(item)

        #for x  in self._groups:
        #    print(x.get_login_group())


    def add_access_rules(self):
        '''Add access rules for each group to the access manager.'''
        for group in self._groups:
            self._access_manager.add_xml_rules(group)


    def setup_access_manager(self):
        '''Setup access manager for admin access.'''
        if self._login and self._login.get_value("login") == 'admin':
            self._access_manager.set_admin(True)
            return True

        for group in self._groups:
            login_group = group.get_value("login_group")
            if login_group == "admin":
                self._access_manager.set_admin(True)
                return True

        return False



