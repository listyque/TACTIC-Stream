import shutil
import sys
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from pyasm.command import Command
from pyasm.search import Search, DbContainer
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
from tools.snapshot_probe import run_snapshot_case


class SchemaEdit(read_tests.ReadParity):
    maxDiff = None
    filter_test_search_type = 'contract/schema_asset'
    test_expressions_and_sql_remain_explicitly_unsupported = None
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import schema_api_contract, schema_edit_contract
        with cls.store.connection(write=True) as db:
            schema_api_contract.install_fixture(db)
            schema_edit_contract.install_fixture(db)
        cls.cases = [dict(method='schema_edit_contract', name=mode, operation=mode, project='one')
                     for mode in ('code', 'id', 'cache', 'save', 'creator')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        if case['operation'] == 'save':
            self.assertEqual(original['error'], 'NameError')
            self.assertIn('SearchTypeCreatorCmd', original['message'])
            self.assertEqual(result, dict(types=['contract/ss_child', 'contract/ss_parent']))
        elif case['operation'] == 'cache':
            self.assertEqual(original, dict(before=True, after=True, draft_serialized=True))
            self.assertEqual(result, dict(before=True, after=False, draft_serialized=False))
        elif case['operation'] in ('code', 'id'):
            self.assertTrue(original['relationship'].pop('disabled'))
            self.assertNotIn('disabled', result['relationship'])
            prefix = 'si' if case['operation'] == 'id' else 'sc'
            view = 'contract/%s_child:edit_definition' % prefix
            self.assertEqual(original['configs'][view][3].pop(), ['edit_definition', {}, '', []])
            self.assertEqual(len(result['configs'][view][3]), 1)
            if case['operation'] == 'id':
                self.assertEqual(original.pop('parent'), '1')
                self.assertEqual(result.pop('parent'), 1)
                import json
                self.assertEqual(json.dumps(original['configs']).count('@GET(contract/si_parent.code)'), 2)
                self.assertEqual(json.dumps(result['configs']).count('@GET(contract/si_parent.id)'), 2)
                original['configs'] = json.loads(json.dumps(original['configs']).replace('@GET(contract/si_parent.code)', '@GET(contract/si_parent.id)'))
            self.assertEqual(result, original)
        else:
            self.assertEqual(result, original)

    def test_rollback_and_permission_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                api = Api(store)
                api.auth.bind_security('admin', self.ticket)
                kinds = ('sthpw/search_object', 'sthpw/schema', 'config/naming', 'config/widget_config')
                from pyasm.biz import Schema
                schema = Schema.get('one')
                setup = Command()
                setup.get_transaction().set_sync(False)
                def setup_schema():
                    schema.add_search_type('contract/sc_child', 'contract/sc_parent')
                    schema.commit()
                setup.execute = setup_schema
                Command.execute_cmd(setup)
                self.assertTrue(schema.get_relationship_attrs('contract/sc_child', 'contract/sc_parent')['disabled'])
                before = {kind: [obj.get_sobject_dict() for obj in Search(kind).get_sobjects()] for kind in kinds}
                with self.assertRaisesRegex(ValueError, 'late schema editor failure'):
                    run_snapshot_case(dict(method='schema_edit_contract', fail=True))
                self.assertEqual({kind: [obj.get_sobject_dict() for obj in Search(kind).get_sobjects()] for kind in kinds}, before)
                self.assertNotIn('sc_parent_code', Search('contract/sc_child').get_columns())
                from tactic.ui.tools import SchemaConnectorCbk, SchemaSaveCmd
                connector = SchemaConnectorCbk(left_search_type='contract/sc_child', left='sc_parent_code', right_search_type='contract/sc_parent', right='code')
                connector.get_transaction().set_sync(False)
                Command.execute_cmd(connector)
                self.assertNotIn('disabled', schema.get_relationship_attrs('contract/sc_child', 'contract/sc_parent'))
                def fail_creation():
                    SchemaSaveCmd(from_search_type='contract/rolled_child', to_search_type='contract/rolled_parent').execute()
                    raise ValueError('late creator failure')
                command = Command()
                command.get_transaction().set_sync(False)
                command.execute = fail_creation
                with self.assertRaisesRegex(ValueError, 'late creator failure'):
                    Command.execute_cmd(command)
                self.assertNotIn('rolled_child', store.tables('sthpw'))
                self.assertNotIn('rolled_parent', store.tables('sthpw'))
                for kwargs in (dict(left_search_type='contract/schema_instance', left='bad column', right_search_type='contract/schema_asset', right='late'),
                               dict(left_search_type='contract/schema_instance', left='late', right_search_type='contract/missing', right='code')):
                    with self.assertRaises(Exception):
                        Command.execute_cmd(SchemaConnectorCbk(**kwargs))
                self.assertNotIn('late', Search('contract/schema_instance').get_columns())
            with request_context(RequestContext(store, 'anonymous', 'one')):
                from pyasm.common import Environment
                from pyasm.security import Security
                Environment.set_security(Security())
                with self.assertLogs('pyasm.command.command', level='ERROR'), self.assertRaises(Exception):
                    Command.execute_cmd(SchemaSaveCmd(from_search_type='forbidden', to_search_type='forbidden_parent'))
                self.assertNotIn('forbidden', store.tables('sthpw'))
