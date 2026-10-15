# Copyright (c) 2005, Southpaw Technology. MIT; see LICENSE.TACTIC.
"""Native authentication hooks, adapted from pyasm/security/authenticate.py."""
from datetime import datetime, timedelta, timezone
from pyasm.common import Config, SecurityException
from pyasm.search import Sql
from pyasm.security.authenticator import verify_password
from .security import Login, _security_transaction, _require_admin

__all__ = ['Authenticate', 'TacticAuthenticate']


class Authenticate:
    def __init__(self):
        self.login = None

    def get_login(self):
        return self.login

    def get_mode(self):
        return 'default'

    def verify(self, login_name, password):
        raise SecurityException('Custom Authenticate class must override verify method')

    def add_user_info(self, login, password=None):
        pass

    def authenticate(self, login, password):
        raise SecurityException('Must override authenticate method')

    def postprocess(self, login, ticket):
        pass

    def reset_password(self, login, password):
        raise SecurityException('Must override reset_password method')


class TacticAuthenticate(Authenticate):
    def verify(self, login_name, password):
        self.login = Login.get_by_login(login_name, use_upn=True)
        if not self.login or self.login.is_retired():
            raise SecurityException('Login/Password combination incorrect')
        password_expiry = Config.get_value('security', 'password_expiry').strip()
        if password_expiry and not self.login.check_password_expiry():
            raise SecurityException('Password expired. Please reset by clicking on Forgot your password link.')
        attempts = Config.get_value('security', 'invalid_login_attempts').strip()
        if attempts and not self.login.check_invalid_logins(int(attempts)):
            raise SecurityException('Too many login attempts. Please reset your password.')
        if not verify_password(password, self.login.get_value('password')):
            self.increment_login_attempt(self.login)
            raise SecurityException('Login/Password combination incorrect')
        self.increment_login_attempt(self.login, reset=True)
        return True

    def add_user_info(self, login, password):
        login.set_value('password', Login.encrypt_password(password))

    def authenticate(self, login, password):
        raise Exception('TacticAuthenticate.authenticate() is DEPRECATED')

    def reset_password(self, login, password):
        _require_admin()
        with _security_transaction():
            encrypted = Login.encrypt_password(password)
            login.set_value('password', encrypted)
            data = login.get_json_value('data', {})
            previous = data.get('previous_passwords') or []
            previous.append(encrypted)
            data['previous_passwords'] = previous[-3:]
            days = Config.get_value('security', 'password_expiry').strip() or '90'
            try:
                days = int(days)
            except ValueError:
                raise ValueError('Check password_expiry config value.') from None
            data['password_expiry'] = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
            data['invalid_logins'] = 0
            login.set_json_value('data', data)
            login.commit()

    def increment_login_attempt(self, login, reset=False):
        if not Config.get_value('security', 'invalid_login_attempts').strip():
            return
        with _security_transaction():
            # Concurrent failures must increment the persisted counter rather
            # than overwrite it with an earlier request's cached JSON value.
            value = Sql.get_default_database_impl().get_json_counter_update('data', 'invalid_logins', reset)
            login.set_value('data', value, quoted=False)
            login.commit()
