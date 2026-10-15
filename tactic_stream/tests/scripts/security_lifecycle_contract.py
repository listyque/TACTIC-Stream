"""Unchanged native server script, executed in both real kernels."""
from datetime import datetime
from pyasm.common import Config, Environment
from pyasm.search import Search, SearchType, Transaction
from pyasm.security import Login, LoginGroup, LoginInGroup, Security, Sudo, Ticket, TacticAuthenticate


def run(case):
    previous = Environment.get_security()
    security = Security()
    Environment.set_security(security)
    security._login = Search.get_by_code('sthpw/login', 'admin')
    security._is_logged_in = 1
    transaction = Transaction.get(create=True)
    transaction.set_record(False)
    transaction.set_sync(False)
    name = 'lifecycle_' + case['name']
    result = {}
    try:
        group = SearchType.create('sthpw/login_group')
        group.set_value('login_group', name)
        group.set_value('access_level', 'low')
        group.commit()
        login = Login.create(name, 'first-secret', 'Ann', 'Artist', groups=[name], display_name='Ann Artist')
        operation = case['operation']
        if operation == 'registration':
            result = {'login': login.get_login(), 'upn': login.get_value('upn'),
                      'name': login.get_full_name(), 'display': login.get_display_value(),
                      'groups': login.get_sub_group_names(),
                      'password': TacticAuthenticate().verify(name, 'first-secret')}
        elif operation == 'password':
            login.set_password('second-secret')
            result = {'verified': TacticAuthenticate().verify(name, 'second-secret'),
                      'different': login.get_value('password') != Login.get_default_encrypted_password()}
        elif operation == 'membership':
            login.remove_from_group(name)
            login.add_to_group(group)
            search = Search('sthpw/login_in_group')
            search.add_filter('login', name)
            result = {'groups': [row.get_value('login_group') for row in search.get_sobjects()]}
        elif operation == 'cached_membership':
            before = login.get_sub_group_names()
            login.remove_from_group(name)
            result = {'before': before, 'after': login.get_sub_group_names()}
        elif operation == 'duplicate_membership':
            login.add_to_group(name)
            search = Search('sthpw/login_in_group')
            search.add_filter('login', name)
            result = {'count': search.get_count()}
        elif operation == 'ticket':
            expiry = datetime(2099, 1, 1)
            ticket = Ticket.create(name, name, expiry=expiry, category='api', commit=case.get('commit', True))
            result = {'key': ticket.get_key(), 'login': ticket.get_value('login'),
                      'expiry': bool(ticket.get_value('expiry')), 'category': ticket.get_value('category'),
                      'stored': Ticket.get_by_key(name) is not None}
        elif operation == 'expired_ticket':
            ticket = Ticket.create(name, name, expiry=datetime(2000, 1, 1))
            result = {'valid': Ticket.get_by_valid_key(name) is not None}
        elif operation == 'invalid_login':
            value = security.login_with_ticket('missing-' + name)
            result = {'login': value is not None, 'logged_in': bool(security.is_logged_in()),
                      'user': security.get_user_name(), 'sudo': Sudo.is_sudo()}
        elif operation == 'stolen_ticket':
            ticket = Ticket.create(name, 'admin', expiry=-1)
            try:
                security.login_user_without_password(name, ticket_key=name)
                result = {'rejected': False}
            except Exception:
                result = {'rejected': True}
            result.update(owner=Ticket.get_by_key(name).get_value('login'), logged_in=bool(security.is_logged_in()))
        elif operation == 'password_revocation':
            Ticket.create(name, name, expiry=-1)
            login.set_password('second-secret')
            result = {'valid': Ticket.get_by_valid_key(name) is not None}
        elif operation == 'disabled_login':
            ticket = Ticket.create(name, name, expiry=-1)
            login.set_value('s_status', 'retired')
            login.commit()
            result = {'accepted': security.login_with_ticket(name) is not None}
        elif operation == 'group_deletion':
            group.delete()
            search = Search('sthpw/login_in_group')
            search.add_filter('login', name)
            result = {'memberships': search.get_count()}
        elif operation == 'attempts':
            Config.set_value('security', 'invalid_login_attempts', '2')
            authenticate = TacticAuthenticate()
            authenticate.increment_login_attempt(login)
            result = {'allowed': login.check_invalid_logins(2), 'attempts': login.get_json_value('data', {})}
        else:
            raise ValueError(operation)
        transaction.commit()
        return result
    except Exception as error:
        if transaction.is_in_transaction():
            transaction.rollback()
        return {'error': type(error).__name__, 'message': str(error)}
    finally:
        Environment.set_security(previous)
