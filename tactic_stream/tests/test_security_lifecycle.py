"""Persistent native account/group/session lifecycle on private owned data."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from pyasm.common import Config, Environment
from pyasm.security import Login, LoginGroup, LoginInGroup, Security, Sudo, Ticket, TacticAuthenticate
from pyasm.search import Search, SearchType, Transaction
from pyasm.search.search import RequestContext, request_context
from pyasm.security.authenticator import Authenticator, hash_password
from pyasm.search.storage import Store
from pyasm.common.errors import AuthenticationError, SecurityException, UnsupportedContract


class SecurityLifecycle(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='tactic-stream-security-lifecycle-')
        self.addCleanup(directory.cleanup)
        self.store = Store(Path(directory.name))
        self.store.initialize(hash_password('private-admin-password'))
        self.auth = Authenticator(self.store)
        context = request_context(RequestContext(self.store, 'admin'))
        context.__enter__()
        self.addCleanup(context.__exit__, None, None, None)
        self.security = Security()
        Environment.set_security(self.security)
        self.security.login_user('admin', 'private-admin-password')

    def group(self, name):
        group = SearchType.create('sthpw/login_group')
        group.set_value('login_group', name)
        group.set_value('name', name)
        group.commit()
        return group

    def test_background_ticket_cache_reuses_keys_and_rechecks_accounts(self):
        from pyasm.security import Batch
        cache = {}
        before = Search('sthpw/ticket').get_count()
        batch = Batch(login_code='admin', ticket_cache=cache)
        batch.__del__()
        self.assertEqual(Search('sthpw/ticket').get_count(), before)
        artist = Login.create('background_artist', 'private-artist-password')
        for _ in range(5):
            batch = Batch(login_code='background_artist', ticket_cache=cache)
            try:
                self.assertEqual(Environment.get_user_name(), 'background_artist')
                self.assertFalse(Environment.get_security().is_admin())
                self.assertFalse(Sudo.is_sudo())
            finally:
                batch.__del__()
        self.assertEqual(Search('sthpw/ticket').get_count(), before + 1)
        key = cache[(self.store.data_dir, 'background_artist')]
        with self.store.connection(write=True) as db:
            db.execute('UPDATE ticket SET expiry=? WHERE ticket=?', ('2000-01-01', key))
        batch = Batch(login_code='background_artist', ticket_cache=cache)
        batch.__del__()
        self.assertNotEqual(cache[(self.store.data_dir, 'background_artist')], key)
        self.assertEqual(Search('sthpw/ticket').get_count(), before + 2)
        revoked = cache[(self.store.data_dir, 'background_artist')]
        with self.store.connection(write=True) as db:
            db.execute('DELETE FROM ticket WHERE ticket=?', (revoked,))
        batch = Batch(login_code='background_artist', ticket_cache=cache)
        batch.__del__()
        self.assertNotEqual(cache[(self.store.data_dir, 'background_artist')], revoked)
        self.assertEqual(Search('sthpw/ticket').get_count(), before + 2)
        artist.set_value('s_status', 'retired')
        artist.commit()
        retired_count = Search('sthpw/ticket').get_count()
        with self.assertRaises(SecurityException):
            Batch(login_code='background_artist', ticket_cache=cache)
        self.assertEqual(Search('sthpw/ticket').get_count(), retired_count)
        self.assertIs(Environment.get_security(), self.security)

    def test_background_ticket_cache_isolates_databases_and_rejects_stolen_keys(self):
        from pyasm.security import Batch
        Login.create('background_artist', 'private-artist-password')
        cache = {(self.store.data_dir, 'background_artist'): self.security.get_ticket_key()}
        with self.assertRaises(SecurityException):
            Batch(login_code='background_artist', ticket_cache=cache)
        cache.clear()
        batch = Batch(login_code='admin', ticket_cache=cache)
        batch.__del__()
        with tempfile.TemporaryDirectory() as directory:
            other = Store(Path(directory))
            other.initialize(hash_password('other-private-password'))
            with request_context(RequestContext(other, 'admin')):
                for _ in range(2):
                    batch = Batch(login_code='admin', ticket_cache=cache)
                    batch.__del__()
                self.assertEqual(Search('sthpw/ticket').get_count(), 1)
        self.assertEqual(len(cache), 2)
        self.assertNotEqual(cache[(self.store.data_dir, 'admin')], cache[(other.data_dir, 'admin')])

    def test_registration_groups_password_ticket_and_logout(self):
        self.group('artists')
        login = Login.create('artist', 'private-artist-password', 'Ann', 'Artist', ['artists'])
        self.assertEqual(login.get_full_name(), 'Ann Artist')
        self.assertEqual(login.get_sub_group_names(), ['artists'])
        login.add_to_group('artists')
        self.assertEqual(len(LoginInGroup.get_by_login_name('artist')), 1)
        token = self.auth.get_ticket('artist', 'private-artist-password')
        self.assertEqual(self.auth.validate(token), 'artist')
        self.auth.logout(token)
        with self.assertRaises(AuthenticationError):
            self.auth.validate(token)
        login.remove_from_group('artists')
        self.assertEqual(login.get_sub_group_names(), [])
        self.assertGreater(Search('sthpw/transaction_log').get_count(), 0)

    def test_ticket_expiry_modes_and_renewal(self):
        future = Ticket.create('future', 'admin', datetime.now(timezone.utc) + timedelta(hours=2))
        self.assertIsNotNone(Ticket.get_by_valid_key(future.get_key()))
        expired = Ticket.create('expired', 'admin', datetime.now(timezone.utc) - timedelta(seconds=2))
        self.assertIsNone(Ticket.get_by_valid_key(expired.get_key()))
        permanent = Ticket.create('permanent', 'admin', expiry=-1)
        self.assertFalse(permanent.get_value('expiry'))
        self.assertIsNotNone(Ticket.get_by_valid_key('permanent'))
        Ticket.create('default', 'admin', interval='2 hour')
        default = Ticket.get_by_key('default')
        self.assertTrue(default.get_value('expiry'))
        Ticket.update_expiry(default, datetime.now(timezone.utc) + timedelta(days=2))
        self.security._ticket = default
        Config.set_value('security', 'inactive_ticket_expiry', '1 day')
        Ticket.update_session_expiry()
        self.assertTrue(Ticket.get_by_valid_key('default'))
        self.assertFalse(Sudo.is_sudo())

    def test_password_change_and_disabled_account_revoke_sessions(self):
        login = Login.create('artist', 'first-password')
        token = self.auth.get_ticket('artist', 'first-password')
        login.set_password('second-password')
        with self.assertRaises(AuthenticationError):
            self.auth.validate(token)
        with self.assertRaises(AuthenticationError):
            self.auth.get_ticket('artist', 'first-password')
        token = self.auth.get_ticket('artist', 'second-password')
        login.set_value('s_status', 'retired')
        login.commit()
        with self.assertRaises(AuthenticationError):
            self.auth.validate(token)
        with self.assertRaises(AuthenticationError):
            self.auth.get_ticket('artist', 'second-password')

    def test_failed_registration_and_command_rollback_leave_no_accounts_or_cache(self):
        with self.assertRaises(Exception):
            Login.create('failed', 'secret', groups=['missing'])
        self.assertIsNone(Login.get_by_login('failed'))
        transaction = Transaction.get(create=True)
        transaction.set_sync(False)
        login = Login.create('rollback', 'secret')
        key = login.get_search_key()
        self.assertIsNotNone(Search.get_by_search_key(key))
        transaction.rollback()
        self.assertIsNone(Login.get_by_login('rollback'))
        self.assertIsNone(Search.get_by_search_key(key))

    def test_failed_login_and_stolen_ticket_do_not_leave_privilege(self):
        Login.create('artist', 'secret')
        admin_ticket = self.security.get_ticket_key()
        with self.assertRaises(SecurityException):
            self.security.login_user_without_password('artist', ticket_key=admin_ticket)
        self.assertFalse(self.security.is_logged_in())
        self.assertFalse(self.security.is_admin())
        self.assertFalse(Sudo.is_sudo())
        self.assertIsNone(self.security.login_with_ticket('missing'))
        self.security.login_user('artist', 'secret')
        self.assertFalse(self.security.is_admin())
        with self.assertRaises(SecurityException):
            Login.create('intruder', 'secret', groups=['admin'])
        self.assertIsNone(self.security.login_with_ticket('missing'))
        self.assertFalse(Sudo.is_sudo())

    def test_password_history_expiry_and_attempts(self):
        login = Login.create('artist', 'secret')
        Config.set_value('security', 'invalid_login_attempts', '2')
        Config.set_value('security', 'password_expiry', '90')
        # Config changes are server-owned and read afresh by transport requests.
        Config.save_config()
        for _ in range(2):
            with self.assertRaises(AuthenticationError):
                self.auth.get_ticket('artist', 'wrong')
        with self.assertRaises(AuthenticationError):
            self.auth.get_ticket('artist', 'secret')
        Login.clear_cache()
        login = Login.get_by_login('artist')
        self.assertEqual(login.get_json_value('data', {})['invalid_logins'], 2)
        TacticAuthenticate().reset_password(login, 'replacement')
        self.assertFalse(login.check_previous_passwords('replacement'))
        self.assertTrue(login.check_previous_passwords('other'))
        self.assertEqual(self.auth.validate(self.auth.get_ticket('artist', 'replacement')), 'artist')
        login.set_json_value('data', {'password_expiry': '2000-01-01T00:00:00Z'})
        login.commit()
        with self.assertRaises(AuthenticationError):
            self.auth.get_ticket('artist', 'replacement')

    def test_concurrent_failures_keep_every_attempt(self):
        from concurrent.futures import ThreadPoolExecutor
        Login.create('artist', 'secret')
        Config.set_value('security', 'invalid_login_attempts', '100')
        Config.save_config()
        def fail(_):
            try:
                self.auth.get_ticket('artist', 'wrong')
            except AuthenticationError:
                return True
            return False
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertTrue(all(pool.map(fail, range(8))))
        Login.clear_cache()
        self.assertEqual(Login.get_by_login('artist').get_json_value('data', {})['invalid_logins'], 8)

    def test_own_password_change_and_sql_scope_cannot_escape(self):
        from pyasm.search import Sql
        Login.create('artist', 'secret')
        token = self.auth.get_ticket('artist', 'secret')
        with request_context(RequestContext(self.store, 'artist', 'admin')):
            security = self.auth.bind_security('artist', token)
            security.get_login().set_password('replacement')
            sql = Sql('sthpw')
            with self.assertRaises(UnsupportedContract):
                sql.do_update("UPDATE login SET password='bad'")
            self.assertFalse(Sudo.is_sudo())
        with self.assertRaises(AuthenticationError):
            self.auth.validate(token)
        self.assertEqual(self.auth.validate(self.auth.get_ticket('artist', 'replacement')), 'artist')

    def test_configured_authentication_modes_and_inactive_expiry(self):
        from pyasm.security import Batch
        from pyasm.search.search import _context
        Login.create('MixedCase', 'secret')
        Config.set_value('security', 'case_insensitive_login', 'true')
        Config.save_config()
        token = self.auth.get_ticket('MIXEDCASE', 'secret')
        self.assertEqual(self.auth.validate(token), 'MixedCase')
        Config.set_value('security', 'api_password', 'master-secret')
        Config.set_value('security', 'inactive_ticket_expiry', '2 hour')
        Config.save_config()
        master_ticket = self.auth.get_ticket('MixedCase', 'master-secret')
        self.auth.renew(master_ticket)
        Ticket.clear_cache()
        self.assertTrue(Ticket.get_by_valid_key(master_ticket))
        self.assertEqual(_context.get().project, 'admin')
        batch = Batch(project_code='admin', login_code='MixedCase', ticket=token)
        self.assertEqual(Environment.get_user_name(), 'MixedCase')
        self.assertFalse(Environment.get_security().is_admin())
        self.assertEqual(_context.get().login, 'MixedCase')
        from pyasm.command import Command
        from pyasm.search import DbContainer
        command = Command(log_exception=False)
        command.execute = lambda: DbContainer.get('sthpw').do_update("UPDATE project SET title='must not change'")
        with self.assertRaises(UnsupportedContract):
            Command.execute_cmd(command)
        self.assertEqual(batch.get_context_name(), 'admin')
        self.assertFalse(Sudo.is_sudo())
        batch.__del__()
        self.assertIs(Environment.get_security(), self.security)
        Config.set_value('security', 'requires_2fa', 'true')
        Config.save_config()
        with self.assertRaises(UnsupportedContract):
            self.auth.get_ticket('MixedCase', 'secret')

    def test_identity_preflight_matches_ticket_upn_and_expiry_rules(self):
        login = Login.create('AliasUser', 'secret')
        login.set_value('upn', 'alias@example.test')
        login.commit()
        key = 'alias-identity-ticket'
        Ticket.create(key, 'alias@example.test', expiry=-1)
        self.assertEqual(self.auth.validate(key), 'AliasUser')
        with self.store.connection(write=True) as db:
            db.execute('UPDATE ticket SET expiry=? WHERE ticket=?', ('2099-01-01T12:30:00+03:00', key))
        self.assertEqual(self.auth.validate(key), 'AliasUser')
        for expiry in ('malformed', '2000-01-01T12:30:00+03:00'):
            with self.store.connection(write=True) as db:
                db.execute('UPDATE ticket SET expiry=? WHERE ticket=?', (expiry, key))
            with self.assertRaises(AuthenticationError):
                self.auth.validate(key)
            self.assertIsNone(Ticket.get_by_valid_key(key))


if __name__ == '__main__':
    unittest.main()
