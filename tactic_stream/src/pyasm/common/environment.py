"""Original Environment accessors over the request-local Container.

See LICENSE.TACTIC and compatibility/source_manifest.json.
Security is installed explicitly; owned paths retain the native Config names.
Legacy web environment initialization and multi-site providers remain unported.
"""
from pyasm.common.common import Base, Container
from pyasm.common.errors import UnsupportedContract
from pyasm.common.common_exception import TacticWarning
import os
from pathlib import Path


class EnvironmentException(Exception):
    pass


class Environment(Base):
    @staticmethod
    def get_install_dir():
        '''get the installation directory for the entire framework'''
        return (os.environ.get('TACTIC_INSTALL_DIR') or '').replace('\\', '/')

    def __init__(self):
        raise UnsupportedContract("Environment initialization/configuration is not migrated")

    @classmethod
    def get_base_url(cls):
        """Original batch URL with the current HTTP request's origin when available."""
        from pyasm.common import Config
        from pyasm.web import Url
        environ = Container.get('Api:environ') or {}
        origin = environ.get('BASE_URL') or Config.get_value('install', 'base_url')
        if origin:
            return Url(origin.rstrip('/'))
        server = Config.get_value('install', 'hostname')
        protocol = Config.get_value('security', 'protocol') or 'http'
        return Url('%s://%s' % (protocol, server))

    @staticmethod
    def get_data_dir(manual=False):
        from pyasm.search.search import _context
        context = _context.get(None)
        if context:
            cached = Container.get('Environment:data_dir') if not manual else None
            if cached:
                return cached
            path = context.store.data_dir
        else:
            path = Path(os.environ.get('TACTIC_DATA_DIR') or 'data').expanduser().resolve()
        value = Path(path).as_posix()
        if context:
            Container.put('Environment:data_dir', value)
        return value

    @staticmethod
    def _directory(value):
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = Path(Environment.get_data_dir()) / path
        from pyasm.search.search import _context
        if _context.get(None) is None:
            return path.resolve().as_posix()
        cache = Container.get_full_dict('Environment:directories')
        key = path.absolute().as_posix()
        # Follow links on each lookup; a moved/replaced root must not reuse its old canonical path.
        for depth, existing in enumerate((path, *path.parents)):
            try:
                stat = existing.stat()
                break
            except FileNotFoundError:
                continue
            except OSError:
                return path.resolve().as_posix()
        else:
            return path.resolve().as_posix()
        if not stat.st_ino:
            return path.resolve().as_posix()
        identity = (existing.absolute().as_posix(), stat.st_dev, stat.st_ino)
        cached = cache.get(key)
        if cached and cached[0] == identity:
            try:
                canonical = cached[2].stat()
                if (canonical.st_dev, canonical.st_ino) == identity[1:]:
                    return cached[1]
            except OSError:
                pass
        resolved = path.resolve()
        ancestor = resolved.parents[depth - 1] if depth else resolved
        # File operations can visit many distinct parents in one check-in.
        if key not in cache and len(cache) >= 256:
            cache.pop(next(iter(cache)))
        cache[key] = (identity, resolved.as_posix(), ancestor)
        return cache[key][1]

    @classmethod
    def get_plugin_dir(cls):
        from pyasm.common.config import Config
        return cls._directory(Config.get_value('install', 'plugin_dir') or 'plugins')

    @classmethod
    def get_dist_dir(cls):
        return cls._directory('dist')

    @classmethod
    def get_template_dir(cls):
        return cls._directory('templates')

    @classmethod
    def get_builtin_plugin_dir(cls):
        return (Path(cls.get_install_dir()) / 'src/plugins').resolve().as_posix()

    @classmethod
    def is_builtin_plugin(cls, plugin_code):
        return plugin_code.startswith('TACTIC')

    @classmethod
    def get_asset_dirs(cls):
        from pyasm.common.config import Config
        aliases = Config.get_dict_value('checkin', 'asset_base_dir')
        aliases.setdefault('plugins', cls.get_plugin_dir())
        aliases.update(Config.get_dict_value('checkin', 'base_dir_alias'))
        return {name: cls._directory(path) for name, path in aliases.items() if path}

    @classmethod
    def get_asset_dir(cls, file_object=None, alias=None):
        from pyasm.common.config import Config
        if file_object:
            alias = file_object.get_value('base_dir_alias')
        alias = alias or 'default'
        aliases = Config.get_dict_value('checkin', 'asset_base_dir')
        aliases.update(Config.get_dict_value('checkin', 'base_dir_alias'))
        if alias == 'plugins' and alias not in aliases:
            return cls.get_plugin_dir()
        return cls._directory(aliases.get(alias) or 'assets')

    @staticmethod
    def _ticket_directory(base, ticket, create=True):
        import re
        if not isinstance(ticket, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', ticket) or ticket in ('.', '..'):
            raise EnvironmentException('Invalid directory ticket')
        path = Path(base) / ticket
        if not path.resolve().is_relative_to(Path(base).resolve()):
            raise EnvironmentException('Ticket directory must remain inside its root')
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path.as_posix()

    @classmethod
    def get_tmp_dir(cls, include_ticket=False):
        from pyasm.common.config import Config
        path = cls._directory(Config.get_value('install', 'tmp_dir') or 'temp')
        if include_ticket:
            return cls._ticket_directory(Path(path) / 'temp', cls.get_ticket())
        return path

    @classmethod
    def get_upload_dir(cls, ticket=None):
        staged = Container.get('CheckinQueue:upload_directory')
        if staged and ticket is None:
            return staged
        return cls._ticket_directory(Path(cls.get_tmp_dir()) / 'upload', ticket or cls.get_ticket())

    @classmethod
    def get_client_handoff_dir(cls, ticket=None, no_exception=False, include_ticket=True):
        from pyasm.common.config import Config
        import re
        if cls.get_client_os() =='nt':
            base_handoff_dir = Config.get_value("checkin", "win32_client_handoff_dir", no_exception=True)
        else:
            base_handoff_dir = Config.get_value("checkin", "linux_client_handoff_dir", no_exception=True)


        if not base_handoff_dir:
            tmp_dir = cls.get_tmp_dir()
            base_handoff_dir = "%s/%s" % (tmp_dir, "handoff")
                

        if no_exception == False and not base_handoff_dir:
            raise EnvironmentException("No handoff directory defined in TACTIC config file")


        if include_ticket and not ticket:
            security = Environment.get_security()
            ticket = security.get_ticket_key()


        if include_ticket:
            if not isinstance(ticket, str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', ticket) or ticket in ('.', '..'):
                raise EnvironmentException('Invalid directory ticket')
            handoff_dir = "%s/%s" % (base_handoff_dir, ticket)
        else:
            handoff_dir = base_handoff_dir

        # can't create this because it may be different on the server
        #if not os.path.exists(handoff_dir):
        #    System().makedirs(handoff_dir)
        #    os.chmod(handoff_dir, 0777)
        return handoff_dir

    @classmethod
    def get_server_handoff_dir(cls, ticket=None, include_ticket=True):
        from pyasm.common.config import Config
        if include_ticket and not ticket:
            security = Environment.get_security()
            ticket = security.get_ticket_key()

        if os.name == "nt":
            base_handoff_dir = Config.get_value("checkin", "win32_server_handoff_dir",\
                no_exception=True)
        else:
            base_handoff_dir = Config.get_value("checkin", "linux_server_handoff_dir",\
                no_exception=True)

        # Resolve server-relative paths against tactic_data and reject a ticket
        # directory linked outside its configured root. Client paths stay untouched.
        base = cls._directory(base_handoff_dir or cls.get_client_handoff_dir(include_ticket=False))
        if include_ticket:
            return cls._ticket_directory(base, ticket, create=False)
        return base

    @classmethod
    def get_client_os(cls):
        return os.name

    @classmethod
    def get_web_dirs(cls):
        from .config import Config
        aliases = Config.get_dict_value('checkin', 'web_base_dir')
        aliases.setdefault('plugins', '/plugins')
        aliases.update(Config.get_dict_value('checkin', 'base_dir_alias'))
        return aliases

    @classmethod
    def get_web_dir(cls, file_object=None, alias=None):
        if file_object:
            alias = file_object.get_value('base_dir_alias') or alias
        return cls.get_web_dirs().get(alias or 'default') or '/assets'

    def get_app_server():
        return os.environ.get("TACTIC_APP_SERVER") or "batch"
    get_app_server = staticmethod(get_app_server)

    def get_security():
        return Container.get("Environment:security")
    get_security = staticmethod(get_security)

    def set_security(security):
        Container.put("Environment:security", security)

    set_security = staticmethod(set_security)

    def set_security_list(security_list):
        Container.put("Environment:security_list", security_list)
    set_security_list = staticmethod(set_security_list)


    def get_ticket():
        '''get the upload dir which relies on the ticket info'''
        security = Environment.get_security()
        if not security:
            return ""
        ticket = security.get_ticket_key()
        return ticket
    get_ticket = staticmethod(get_ticket)



    def get_login():
        security = Environment.get_security()
        assert security
        return security.get_login()
    get_login = staticmethod(get_login)

    def get_user_name():
        login = Environment.get_login()
        if login:
            return login.get_login()
        else:
            return None
    get_user_name = staticmethod(get_user_name)

    def get_group_names():
        security = Environment.get_security()
        assert security
        return security.get_group_names()
    get_group_names = staticmethod(get_group_names)

 


    def get_app_name():
        return "Browser"
    get_app_name = staticmethod(get_app_name)


    def set_env_object(env_object):
        '''Stores the main environment container.  This is primarily
        used to get information that has specific implementations in
        the environment running.   For example, the main config path
        differs depending on whether a batch program is run, or whether
        the context is through the web
        '''
        Container.put("Environment:object", env_object)
    set_env_object = staticmethod(set_env_object)

    def get_env_object():
        env_object = Container.get("Environment:object")
        if env_object == None:
            raise EnvironmentException("Environment not initialised")
        return env_object
    get_env_object = staticmethod(get_env_object)


    def get():
        env_object = Container.get("Environment:object")
        if env_object == None:
            raise EnvironmentException("Environment not initialised")
        return env_object
    get = staticmethod(get)



    def has_env_object():
        return Container.has("Environment:object")
    has_env_object = staticmethod(has_env_object)




    def get_warning():
        return Container.get_seq('widget_warning')
    get_warning = staticmethod(get_warning)


    def add_warning(label, warning, type=''):
        # for now print it out
        print("WARNING: %s - %s, type[%s]" % (label, warning, type))
        warning = TacticWarning(label, warning, type)
        return Container.append_seq('widget_warning', warning)
    add_warning = staticmethod(add_warning)

    @classmethod
    def get_release_version(cls):
        from tactic_stream import __version__
        return __version__

    @classmethod
    def get_release_api_version(cls):
        from importlib.resources import files
        return (files('tactic_client_lib') / 'VERSION_API').read_text(encoding='utf8').strip()
