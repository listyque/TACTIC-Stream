"""Relationship joins against the actual source, including known source defects."""
import sys
import ast
from pathlib import Path

from test_read_parity import ReadParity
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.common.errors import SecurityException, UnsupportedContract
from tools.snapshot_probe import run_snapshot_case


EXPECTED = {'child_code': ['R1'], 'parent_code': ['P1'], 'child_id': ['ID_REF'],
            'parent_id': [7], 'prefixed': ['R1'], 'chain': ['R1'], 'branch': ['P1'],
            'physical_table': ['P1'], 'default_order': ['P2', 'P1'],
            'named_order': ['P1', 'P2'], 'short_named_order': ['P1', 'P2'], 'duplicate': ['P1', 'P2']}


class SearchJoinParity(ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import search_join_contract
        from schema_api_contract import install_fixture
        with cls.store.connection(write=True) as db:
            install_fixture(db)
            search_join_contract.install_fixture(db)
        cls.cases = [dict(method='search_join_contract', name=name, operation=name) for name in EXPECTED]

    def new_result(self, case):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        name = case['name']
        self.assertEqual(result, EXPECTED[name])
        if name in ('default_order', 'duplicate'):
            self.assertEqual(result, original)
            return
        errors = {'child_code': 'no such table: sthpw.join_parent',
                  'parent_code': 'no such table: sthpw.join_ref',
                  'child_id': 'no such table: sthpw.join_id_parent',
                  'parent_id': 'no such table: sthpw.join_ref',
                  'prefixed': 'no such table: sthpw.join_parent',
                  'chain': 'no such table: sthpw.join_parent',
                  'branch': 'no such column: join_ref.search_type',
                  'physical_table': 'no such table: join_alias',
                  'named_order': 'no such column: join_tag.contract/join_tag',
                  'short_named_order': 'Search type [join_tag] not registered'}
        self.assertEqual(original['error'], 'SearchException' if name == 'short_named_order' else 'SqlException')
        self.assertIn(errors[name], original['message'])
        if name in ('child_code', 'child_id', 'prefixed', 'chain'):
            # Same source SQL also shows the wrong child discriminator.
            self.assertIn("\"join_ref\".\"search_type\" = 'contract/join_ref?project=one'", original['message'])

    def test_unported_filter_dependencies_and_sql_are_rejected(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            for filters in (['code = P1'], [['other_table.code', 'P1']], [['name', '@@', 'secret']]):
                with self.assertRaises(UnsupportedContract):
                    Search('contract/join_parent').add_op_filters(filters)

    def test_join_guards_and_api_order_use_the_same_core(self):
        with request_context(RequestContext(self.store, 'admin', 'one')):
            search = Search('contract/join_parent')
            search.add_join('contract/join_tag')
            search.add_join('contract/join_tag', path='alternate')
            search.add_filter('code', 'T1', table='join_tag')
            self.assertEqual(search.copy().get_sobject_codes(), ['P1'])
            with self.assertRaises(UnsupportedContract):
                search.add_order_by('contract/join_tag.name;DROP TABLE join_parent')
        ticket = {'ticket': self.ticket, 'project': 'one'}
        rows = self.api.dispatch('query', (ticket, 'contract/join_parent', [], ['code'], ['alternate:contract/join_tag.name']))
        rows = ast.literal_eval(rows)
        self.assertEqual([row['code'] for row in rows], ['P1', 'P2'])
        from unittest.mock import patch
        # Main type is readable; the joined type must independently pass Search ACL.
        with request_context(RequestContext(self.store, 'admin', 'one')):
            self.api.auth.bind_security('admin', self.ticket)
            from pyasm.common import Environment
            search = Search('contract/join_parent')
            with patch.object(Environment.get_security(), 'check_access', return_value=False):
                with self.assertRaises(SecurityException):
                    search.add_join('contract/join_tag')
            self.assertEqual(search.joins, [])
