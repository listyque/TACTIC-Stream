"""The item editor discovers readable types in the actual project database."""
import json
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import test_transport
from tactic_stream.server.api import Api


class LayoutCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Server(test_transport.Transport):
            pass
        cls.server = Server
        cls.server.setUpClass()
        cls.api = Api(cls.server.store)
        cls.ticket = cls.api.get_ticket('admin', 'private-test-password')

    @classmethod
    def tearDownClass(cls):
        cls.server.tearDownClass()

    def setUp(self):
        with self.server.store.connection('one', write=True) as database:
            database.execute('CREATE TABLE IF NOT EXISTS layout_card (id INTEGER PRIMARY KEY, code TEXT, name TEXT)')
        with self.server.store.connection(write=True) as database:
            for code, table in [('library/card', 'layout_card'), ('foreign/activity', 'missing_layout_activity')]:
                database.execute('INSERT OR REPLACE INTO search_object (code,search_type,title,namespace,"database",table_name,class_name) VALUES (?,?,?,?,?,?,?)',
                    (code, code, code, code.split('/')[0], '{project}', table, 'pyasm.search.SObject'))

    def catalog(self, project='one', ticket=None):
        request = Request(self.server.url + '/admin/widget-configuration/catalog',
            json.dumps(dict(ticket=ticket or self.ticket, project=project)).encode(),
            headers={'Content-Type': 'application/json'})
        with urlopen(request) as response:
            return json.load(response)['result']['stypes']

    def test_actual_tables_define_scope_instead_of_namespace_prefix(self):
        codes = {row['code'] for row in self.catalog()}
        self.assertIn('library/card', codes)
        self.assertNotIn('foreign/activity', codes)
        self.assertNotIn('library/card', {row['code'] for row in self.catalog('two')})

    def test_catalog_rechecks_table_availability(self):
        self.assertIn('library/card', {row['code'] for row in self.catalog()})
        with self.server.store.connection('one', write=True) as database:
            database.execute('DROP TABLE layout_card')
        self.assertNotIn('library/card', {row['code'] for row in self.catalog()})

    def test_catalog_requires_admin_and_valid_authentication(self):
        from pyasm.security.authenticator import hash_password
        self.api.dispatch('insert', (dict(ticket=self.ticket, project='one'), 'sthpw/login',
            dict(login='layout_catalog_reader', password=hash_password('private-reader-password'))))
        ticket = self.api.get_ticket('layout_catalog_reader', 'private-reader-password')
        with self.assertRaises(HTTPError) as error:
            self.catalog('admin', ticket)
        self.assertEqual(error.exception.code, 403)
        error.exception.close()
        with self.assertRaises(HTTPError) as error:
            self.catalog(ticket='invalid-layout-ticket')
        self.assertEqual(error.exception.code, 403)
        error.exception.close()
