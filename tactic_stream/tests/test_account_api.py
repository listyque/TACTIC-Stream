"""Public security writes use native Command, records, rights and rollback."""
import ast
import unittest
from unittest.mock import patch
from pyasm.common import Environment
from pyasm.security import Login, Security
from pyasm.search import Search, SearchType
from tactic_stream.server.api import Api
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search.search import RequestContext, request_context
import test_security_lifecycle as lifecycle


class AccountApi(unittest.TestCase):
    setUp = lifecycle.SecurityLifecycle.setUp
    group = lifecycle.SecurityLifecycle.group
    def test_original_write_signatures_records_and_atomic_list_updates(self):
        api = Api(self.store)
        ticket = {'ticket': self.security.get_ticket_key(), 'project': 'admin'}
        group = api.dispatch('insert', (ticket, 'sthpw/login_group', {'login_group': 'crew', 'name': 'Crew'}))
        login = api.dispatch('insert', (ticket, 'sthpw/login', {'login': 'artist', 'password': Login.encrypt_password('secret')}))
        api.dispatch('insert', (ticket, 'sthpw/login_in_group', {'login': 'artist', 'login_group': 'crew'}))
        self.assertEqual(api.auth.validate(api.get_ticket('artist', 'secret')), 'artist')
        updated = api.dispatch('update', (ticket, login['__search_key__'], {'display_name': 'Artist'}))
        self.assertEqual(updated['display_name'], 'Artist')
        before = api.dispatch('get_by_search_key', (ticket, login['__search_key__']))['first_name']
        with self.assertRaises(Exception):
            api.dispatch('update', (ticket, [login['__search_key__'], login['__search_key__']],
                                   [{'first_name': 'rolled back'}, {'missing_column': 'fail'}]))
        stored = api.dispatch('get_by_search_key', (ticket, login['__search_key__']))
        self.assertEqual(stored['first_name'], before)
        deleted = api.dispatch('delete_sobject', (ticket, group['__search_key__']))
        self.assertEqual(deleted['login_group'], 'crew')
        self.assertEqual(ast.literal_eval(api.dispatch('query', (ticket, 'sthpw/login_group'), {'filters': [['login_group', 'crew']]})), [])
        self.assertGreater(Search('sthpw/transaction_log').get_count(), 0)

    def test_non_admin_cannot_read_join_or_modify_accounts(self):
        Login.create('artist', 'secret')
        api = Api(self.store)
        ticket = {'ticket': api.get_ticket('artist', 'secret'), 'project': 'admin'}
        for method, args in [('query', ('sthpw/login',)), ('get_by_code', ('sthpw/login_group', 'admin')),
                             ('insert', ('sthpw/login_group', {'login_group': 'intruder'})),
                             ('update', ('sthpw/login?code=admin', {'password': 'bad'}))]:
            with self.subTest(method=method), self.assertRaises(SecurityException):
                api.dispatch(method, (ticket, *args))
        self.assertEqual(api.dispatch('ping', (ticket,)), 'OK')

    def test_ticket_data_is_the_original_native_record(self):
        data = Api(self.store).dispatch('get_ticket_data', ('admin', 'private-admin-password'))
        self.assertEqual(data['login'], 'admin')
        self.assertEqual(data['__search_type__'], 'sthpw/ticket')
        self.assertTrue(data['expiry'])
        self.assertEqual(self.auth.validate(data['ticket']), 'admin')

    def test_admin_can_revoke_own_group_and_rights_are_gone_on_next_request(self):
        from pyasm.security import LoginInGroup
        login = Login.create('lead', 'secret', groups=['admin'])
        key = LoginInGroup.get_by_names('lead', 'admin').get_search_key()
        api = Api(self.store)
        ticket = {'ticket': api.get_ticket('lead', 'secret'), 'project': 'admin'}
        deleted = api.dispatch('delete_sobject', (ticket, key))
        self.assertEqual(deleted['login'], 'lead')
        self.assertEqual(api.dispatch('ping', (ticket,)), 'OK')
        with self.assertRaises(SecurityException):
            api.dispatch('query', (ticket, 'sthpw/login'))

    def test_registration_cli_uses_native_creation_and_revokes_its_admin_session(self):
        from tactic_stream.__main__ import main
        self.group('artists')
        before = Search('sthpw/ticket').get_count()
        with patch('sys.argv', ['tactic-stream', '--data-dir', str(self.store.data_dir), 'register', 'cli-user', '--group', 'artists']), \
                patch('getpass.getpass', side_effect=['private-admin-password', 'user-secret', 'user-secret']):
            main()
        Login.clear_cache()
        self.assertEqual(Login.get_by_login('cli-user').get_sub_group_names(), ['artists'])
        self.assertEqual(Search('sthpw/ticket').get_count(), before)
        self.assertEqual(self.auth.validate(self.auth.get_ticket('cli-user', 'user-secret')), 'cli-user')
