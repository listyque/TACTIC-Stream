"""Ordinary readers can render their records without crossing admin/write boundaries."""
import unittest
from unittest.mock import patch

from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.result_items import objects, read_result_items, snapshot_summaries
import test_table_services as fixture
from test_project_writes import install_writer, set_rules, PASSWORD


class UserResultItems(unittest.TestCase):
    setUp = fixture.TableServices.setUp

    def insert_snapshots(self, parent, contexts):
        with self.store.connection(write=True) as db:
            db.executemany('INSERT INTO snapshot (code,search_type,search_code,search_id,project_code,context,version,snapshot,login,column_name,s_status) '
                           'VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                           [(code, parent.get_search_type(), parent.get_code(), parent.get_id(), parent.get_project_code(),
                             context, version, '<snapshot/>', 'admin', '', retired)
                            for code, context, version, retired in contexts])

    def test_cards_count_large_snapshot_histories_without_loading_them(self):
        parent = Search.get_by_code('contract/entity', 'A')
        self.insert_snapshots(parent, [('H%05d' % index, 'publish/model', index, None) for index in range(10000)] +
                              [('LATEST', 'publish/model', -1, None), ('ICON', 'icon', 1, None),
                               ('FILE', 'attachment/source', 1, None), ('RETIRED', 'publish/model', 10001, 'retired')])
        original = Search.get_related_by_sobjects
        def related(records, search_type, *args, **kwargs):
            if search_type == 'sthpw/snapshot':
                self.fail('Card summary materialized snapshot history')
            return original(records, search_type, *args, **kwargs)
        with patch.object(Search, 'get_related_by_sobjects', side_effect=related):
            result = read_result_items('contract/entity', [parent.get_search_key()])['items'][0]
        branches = {row.get('process'): row for row in result['branches'] if row['kind'] == 'process'}
        self.assertEqual(branches['publish']['count'], 10000)
        self.assertTrue(branches['publish']['has_children'])
        self.assertEqual(branches['attachment']['count'], 1)
        self.assertTrue(result['has_snapshot'])

    def test_snapshot_summaries_preserve_id_relations_projects_and_row_permissions(self):
        from collections import Counter
        from pyasm.common import Environment

        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) "
                       "VALUES ('contract/id_entity','contract/id_entity','contract','{project}','id_entity','pyasm.search.SObject')")
        with self.store.connection('one', write=True) as db:
            db.execute('CREATE TABLE id_entity (id INTEGER PRIMARY KEY, name text)')
            db.execute("INSERT INTO id_entity VALUES (1,'By ID')")
        parent = Search.get_by_id('contract/id_entity', 1)
        self.insert_snapshots(parent, [('ID1', 'publish', 1, None), ('ID2', 'publish', -1, None),
                                       ('ID3', 'publish', 2, 'retired')])
        foreign = Search.get_by_code('contract/entity?project=two', 'A')
        self.insert_snapshots(foreign, [('FOREIGN', 'publish', 1, None)])
        install_writer(self.store)
        set_rules(self.store, '<rules><rule group="project" code="one" access="allow"/>'
                  '<rule group="search_type" code="contract/id_entity" project="one" access="view"/>'
                  '<rule group="search_filter" search_type="sthpw/snapshot" column="code" value="ID1"/></rules>')
        ticket = self.api.get_ticket('project_writer', PASSWORD)
        with request_context(RequestContext(self.store, 'project_writer', 'one')):
            self.api.auth.bind_security('project_writer', ticket)
            visible = Search.get_related_by_sobjects([parent], 'sthpw/snapshot')[parent.get_search_key()]
            self.assertEqual([snapshot.get_code() for snapshot in visible], ['ID1'])
            expected = Counter(snapshot.get_value('context') for snapshot in visible)
            actual = snapshot_summaries([parent])[parent.get_search_key()]
            self.assertEqual(actual, {context: [count, count] for context, count in expected.items()})
            self.assertFalse(Environment.get_security().is_admin())

    def test_branch_query_is_literal_unicode_and_precedes_paging(self):
        from tactic_stream.server.result_items import filter_branch_query
        for text in ('пЕРВ', 'перв'):
            search = Search('contract/entity')
            filter_branch_query(search, text)
            search.set_limit(1)
            self.assertEqual([row.get_code() for row in search.get_sobjects()], ['A'])
        for text in ('.*', '%', "' OR 1=1 --"):
            search = Search('contract/entity')
            filter_branch_query(search, text)
            self.assertEqual(search.get_count(), 0)
        search = Search('contract/entity')
        filter_branch_query(search, "O'Reilly")
        search.set_limit(1)
        self.assertEqual([row.get_code() for row in search.get_sobjects()], ['B'])
        key = Search.get_by_code('contract/entity', 'A').get_search_key()
        for query in (None, 'a' * 257, ['x']):
            with self.assertRaises(ValueError):
                read_result_items('contract/entity', [key], dict(kind='children'), query=query)

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
