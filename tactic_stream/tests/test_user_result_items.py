"""Ordinary readers can render their records without crossing admin/write boundaries."""
import unittest

from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.result_items import objects, read_result_items
import test_table_services as fixture
from test_project_writes import install_writer, set_rules, PASSWORD


class UserResultItems(unittest.TestCase):
    setUp = fixture.TableServices.setUp

    def test_record_cards_use_read_policy_without_opening_other_projects_or_writes(self):
        install_writer(self.store)
        set_rules(self.store, '<rules><rule group="project" code="one" access="allow"/>'
                  '<rule group="search_type" code="contract/entity" project="one" access="view"/></rules>')
        key = Search.get_by_code('contract/entity', 'A').get_search_key()
        ticket = self.api.get_ticket('project_writer', PASSWORD)
        auth = dict(ticket=ticket, project='one')
        with request_context(RequestContext(self.store, 'project_writer', 'one')):
            self.api.auth.bind_security('project_writer', ticket)
            result = read_result_items('contract/entity', [key])
            self.assertEqual([item['record']['code'] for item in result['items']], ['A'])
            self.assertEqual(result['items'][0]['record']['name'], 'Первый')
            children = read_result_items('contract/entity', [key], dict(kind='children'))
            self.assertEqual(children['items'][0]['record']['code'], 'A')
            with self.assertRaises(SecurityException):
                objects('contract/entity', [key])
            with self.assertRaises(SecurityException):
                read_result_items('sthpw/login', ['sthpw/login?code=admin'])
            with self.assertRaises(ValueError):
                read_result_items('contract/entity', ['contract/entity?project=two&code=A'])
        with request_context(RequestContext(self.store, 'project_writer', 'two')):
            self.api.auth.bind_security('project_writer', ticket)
            with self.assertRaises(SecurityException):
                read_result_items('contract/entity', ['contract/entity?project=two&code=A'])
        with self.assertRaises(SecurityException):
            self.api.dispatch('update', (auth, key, dict(name='Not permitted')))
        self.assertEqual(Search.get_by_code('contract/entity', 'A').get_value('name'), 'Первый')
