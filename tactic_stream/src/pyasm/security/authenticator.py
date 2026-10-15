"""Password compatibility and native Security transport integration."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import secrets
import string

from pyasm.security.tactic_password_hasher import TacticPasswordHasher, _ITOA64
from pyasm.common.errors import AuthenticationError, UnsupportedContract


def hash_password(password: str) -> str:
    if not password or len(password) > 4096:
        raise ValueError("A non-empty password of at most 4096 characters is required")
    salt = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    return TacticPasswordHasher().encode(password, salt, "D")


def verify_password(password: str, stored: str) -> bool:
    if not isinstance(password, str) or not password or len(password) > 4096 or not isinstance(stored, str):
        return False
    if stored.startswith("$S$"):
        if len(stored) != 55 or stored[3] not in _ITOA64 or not 7 <= _ITOA64.index(stored[3]) <= 20:
            return False
        actual = TacticPasswordHasher().encode(password, stored[4:12], stored[3])
    elif re.fullmatch("[0-9a-f]{32}", stored):
        # Existing TACTIC MD5 records can be read; new accounts use the original salted TACTIC format.
        actual = hashlib.md5(password.encode()).hexdigest()
    else:
        return False
    return hmac.compare_digest(actual, stored)


class Authenticator:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def _admin(db, login, parameter='?', *, active=None):
        if active is None:
            active = db.execute("SELECT 1 FROM login WHERE login=" + parameter + " AND (s_status IS NULL OR s_status!='retired')", (login,)).fetchone()
        if not active:
            return False
        if login == 'admin':
            return True  # Original Security's built-in administrator identity.
        pending = [row['login_group'] if isinstance(row, dict) else row[0]
                   for row in db.execute('SELECT login_group FROM login_in_group WHERE login=' + parameter, (login,))]
        seen = set()
        while pending:
            name = pending.pop()
            if name in seen:
                continue
            seen.add(name)
            row = db.execute("SELECT sub_groups FROM login_group WHERE login_group=" + parameter + " AND "
                             "(s_status IS NULL OR s_status!='retired')", (name,)).fetchone()
            if row is None:
                continue
            if name == 'admin':
                return True
            pending.extend(((row['sub_groups'] if isinstance(row, dict) else row[0]) or '').split('|'))
        return False

    def get_ticket(self, login_name, password, site=None):
        if site:
            raise UnsupportedContract("Multi-site authentication is not migrated yet")
        if not isinstance(login_name, str) or not login_name or len(login_name) > 100:
            raise AuthenticationError("Login/Password combination incorrect")
        if password is not None and (not isinstance(password, str) or len(password) > 4096):
            raise AuthenticationError('Login/Password combination incorrect')
        from pyasm.common import Environment
        from pyasm.security import XmlRpcLogin
        from pyasm.common.errors import SecurityException
        from pyasm.search.search import RequestContext, request_context
        # The trusted transport initializes Security before password verification;
        # no caller can supply this bootstrap identity or a Sudo flag.
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            try:
                XmlRpcLogin(login_name, password)
            except SecurityException:
                raise AuthenticationError('Login/Password combination incorrect') from None
            return Environment.get_security().get_ticket_key()

    def get_ticket_data(self, login_name, password, site=None):
        from pyasm.search.search import RequestContext, request_context
        key = self.get_ticket(login_name, password, site)
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            security = self.bind_security(None, key)
            return security.get_ticket().get_sobject_dict()

    def validate(self, ticket, return_state=False):
        if not isinstance(ticket, str) or not ticket or len(ticket) > 256:
            raise AuthenticationError("Invalid or expired ticket")
        from pyasm.search.search import RequestContext, request_context
        from pyasm.common import Config
        from pyasm.security.security import _valid_ticket_expiry
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            # Only resolve the identity here; full SObjects/groups/ACLs are built
            # and the ticket is rechecked by bind_security in its actual context.
            marker = self.store.get_db_resource().get_database_impl().get_parameter()
            with self.store.connection() as db:
                if return_state:
                    saved = db.execute('SELECT t.login,t.expiry,s.data FROM ticket t '
                        'LEFT JOIN transaction_state s ON s.ticket=t.ticket WHERE t.ticket=' + marker, (ticket,)).fetchone()
                else:
                    saved = db.execute('SELECT login,expiry FROM ticket WHERE ticket=' + marker, (ticket,)).fetchone()
                if not saved or not _valid_ticket_expiry(saved['expiry']):
                    raise AuthenticationError('Invalid or expired ticket')
                name = saved['login']
                if not name:
                    raise AuthenticationError('Invalid or expired ticket')
                if Config.get_value('security', 'case_insensitive_login') == 'true':
                    name = name.lower()
                    login = next((row for row in db.execute('SELECT login,upn,s_status FROM login')
                                  if (row['login'] or '').lower() == name or
                                  (name != 'admin' and (row['upn'] or '').lower() == name)), None)
                elif name == 'admin':
                    login = db.execute('SELECT login,s_status FROM login WHERE login=' + marker, (name,)).fetchone()
                else:
                    login = db.execute('SELECT login,s_status FROM login WHERE login=' + marker +
                                       ' OR upn=' + marker + ' LIMIT 1', (name, name)).fetchone()
            if not login or login['s_status'] == 'retired' or login['login'] == 'guest':
                raise AuthenticationError('Invalid or expired ticket')
            return (login['login'], saved['data']) if return_state else login['login']

    def bind_security(self, login_name, ticket_key):
        """Re-read persisted identity/groups on every authenticated request."""
        from pyasm.common import Environment
        from pyasm.security import XmlRpcInit
        XmlRpcInit(ticket_key)
        security = Environment.get_security()
        login = security.get_login()
        if not login or (login_name and login.get_login() != login_name):
            raise AuthenticationError("Invalid or expired ticket")
        return security

    def logout(self, ticket_key):
        from pyasm.security import Sudo
        from pyasm.search.search import RequestContext, request_context
        self.validate(ticket_key)
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            security = self.bind_security(None, ticket_key)
            sudo = Sudo()
            try:
                security.get_ticket().delete(triggers=False)
                security.sign_out()
            finally:
                sudo.exit()

    def renew(self, ticket_key):
        from pyasm.security import Ticket
        from pyasm.search.search import RequestContext, request_context
        self.validate(ticket_key)
        with request_context(RequestContext(self.store, 'admin', 'admin')):
            self.bind_security(None, ticket_key)
            Ticket.update_session_expiry()
