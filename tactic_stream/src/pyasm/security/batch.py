# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Headless Batch/XML-RPC initialization on owned request contexts.

Adapted from pyasm/security/batch.py; no legacy startup, UI or plugin paths.
"""
import hmac
import os
from pathlib import Path
from pyasm.common import Common, Config, Environment, SecurityException
from pyasm.common.errors import UnsupportedContract
from pyasm.search.search import RequestContext, _context, request_context
from pyasm.search.storage import Store
from .security import Security, Ticket
from .access_manager import Sudo


class Batch(Environment):
    def __init__(self, project_code=None, login_code=None, site=None, ticket=None, ticket_cache=None):
        if site:
            raise UnsupportedContract('Multi-site batch initialization is not migrated')
        previous = _context.get(None)
        store = previous.store if previous else Store(Path(os.environ.get('TACTIC_DATA_DIR', 'data')))
        self.ticket = ticket
        self.login_code = login_code
        self.context = project_code or self.get_default_context()
        project = 'admin' if self.context == 'batch' else self.context
        self._request = RequestContext(store, 'admin', project)
        self._scope = request_context(self._request)
        self._scope.__enter__()
        try:
            cache_key = (store.data_dir, login_code or 'admin')
            if ticket_cache is not None and ticket is None:
                key = ticket_cache.get(cache_key)
                if not key and previous:
                    security = previous.container.get_data().get('Environment:security')
                    if security and security.get_user_name() == cache_key[1]:
                        key = security.get_ticket_key()
                self.ticket = Ticket.get_by_valid_key(key) if key else None
            Environment.set_env_object(self)
            Environment.set_security(Security())
            self._do_login()
            from pyasm.biz import Project
            if not Project.get():
                raise SecurityException('Project unavailable: ' + project)
            if ticket_cache is not None:
                ticket_cache[cache_key] = Environment.get_security().get_ticket_key()
        except Exception:
            self._scope.__exit__(None, None, None)
            self._scope = None
            raise

    def _do_login(self):
        security = Environment.get_security()
        security.login_as_batch(self.login_code, ticket=self.ticket)
        if self._request.login != security.get_user_name():
            # Authentication connections must not retain their bootstrap admin authority.
            self._scope.__exit__(None, None, None)
            self._request = RequestContext(self._request.store, security.get_user_name(), self._request.project)
            self._scope = request_context(self._request)
            self._scope.__enter__()
            Environment.set_env_object(self)
            Environment.set_security(security)

    def __del__(self):
        # An older Batch destructor must never close a later request's database.
        scope = getattr(self, '_scope', None)
        if scope is not None and _context.get(None) is self._request:
            scope.__exit__(None, None, None)
            self._scope = None

    def get_default_context(self):
        return 'batch'

    def set_context(self, context):
        self.context = context

    def get_context_name(self):
        return self.context

    def get_command_key(self):
        return Common.generate_random_key()


class XmlRpcInit(Environment):
    def __init__(self, ticket, site=None):
        if site:
            raise UnsupportedContract('Multi-site XML-RPC initialization is not migrated')
        self.ticket = ticket
        Environment.set_env_object(self)
        Environment.set_security(Security())
        self._do_login()

    def _do_login(self):
        allow_guest = Config.get_value('security', 'allow_guest') == 'true'
        login = Environment.get_security().login_with_ticket(self.ticket, allow_guest=allow_guest)
        if not login:
            raise SecurityException('Cannot login with key. Session may have expired.')


class XmlRpcLogin(Environment):
    def __init__(self, login_name, password=None):
        self.login_name = login_name.lower() if Config.get_value('security', 'force_lowercase_login') == 'true' else login_name
        self.password = password
        Environment.set_env_object(self)
        Environment.set_security(Security())
        self._do_login()

    def _do_login(self):
        security = Environment.get_security()
        if security.requires_2fa():
            raise UnsupportedContract('Two-factor authentication provider is not migrated')
        require_password = Config.get_value('security', 'api_require_password')
        api_password = Config.get_value('security', 'api_password')
        if self.login_name == 'guest':
            raise UnsupportedContract('Guest XML-RPC login is not migrated')
        if require_password == 'false' or (api_password and isinstance(self.password, str) and
                hmac.compare_digest(api_password.encode(), self.password.encode())):
            sudo = Sudo()
            try:
                security.login_user_without_password(self.login_name, expiry='NULL')
            finally:
                sudo.exit()
        else:
            security.login_user(self.login_name, self.password, expiry='NULL')
        if not security.is_logged_in():
            raise SecurityException('Cannot login as user: %s.' % self.login_name)


class TacticInit(Environment):
    def __init__(self, ticket=None):
        self.ticket = ticket
        Environment.set_env_object(self)
        Environment.set_security(Security())
