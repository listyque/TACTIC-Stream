import shutil
import sys
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from pyasm.command import Command
from pyasm.search import Search, SearchType
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
from tools.snapshot_probe import run_snapshot_case


class Collections(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import collection_contract
        with cls.store.connection(write=True) as db:
            collection_contract.install_fixture(db)
        cls.cases = [dict(method='collection_contract', name='parent_and_collection', project='one'),
                     dict(method='collection_contract', name='source_recursive_sql', operation='cte', project='one')]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        if case.get('operation') == 'cte':
            self.assertEqual(original['error'], 'SqlException')
            self.assertIn('ARRAY', original['message'])
            self.assertEqual(result, [])
            return
        # Original Schema.resolve_search_type_relationship compares full keys
        # with bare schema names, so qualified parent_key silently does nothing.
        self.assertEqual(original.pop('parents'), [None, None, None])
        self.assertEqual(result.pop('parents'), ['ROOT', 1, "OTHER'"])
        self.assertEqual(result, original)

    def test_keywords_cycles_and_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                result = run_snapshot_case(dict(method='collection_contract', keywords=True))
                self.assertEqual(result['collections'], ['SUB'])
                self.assertIn('renamed', result['keywords'])
                self.assertIn('tag', result['keywords'])
                api = Api(store)
                api.auth.bind_security('admin', self.ticket)
                ticket = {'project': 'one'}
                root = Search.get_by_code('contract/collect', 'ROOT')
                sub = Search.get_by_code('contract/collect', 'SUB')
                command = Command()
                command.execute = lambda: sub.add_to_collection(root)
                Command.execute_cmd(command)
                before = Search('contract/collect_in_collect').get_count()
                command = Command()
                command.get_transaction().set_sync(False)
                def execute():
                    root.add_to_collection(sub)
                command.execute = execute
                with self.assertRaisesRegex(Exception, 'Circular'):
                    Command.execute_cmd(command)
                self.assertEqual(Search('contract/collect_in_collect').get_count(), before)
                def remove_edges():
                    leaf = Search.get_by_code('contract/collect', 'LEAF')
                    leaf.add_to_collection(root)
                    edges = Search('contract/collect_in_collect')
                    edges.add_filter('parent_code', 'ROOT')
                    edges.add_filter('search_code', 'LEAF')
                    edges.get_sobject().delete()
                    self.assertIn('renamed', Search.get_by_code('contract/collect', 'LEAF').get_value('keywords'))
                    edges = Search('contract/collect_in_collect')
                    edges.add_filter('parent_code', 'ROOT')
                    edges.add_filter('search_code', 'SUB')
                    edges.get_sobject().delete()
                    self.assertNotIn('renamed', Search.get_by_code('contract/collect', 'LEAF').get_value('keywords'))
                command = Command()
                command.execute = remove_edges
                Command.execute_cmd(command)
                before = Search('contract/collect_in_collect').get_count()
                def fail():
                    api.insert(ticket, 'contract/collect', {'code': 'ROLLED'}, collection_key=root.get_search_key())
                    raise ValueError('late collection failure')
                command = Command()
                command.execute = fail
                with self.assertRaisesRegex(ValueError, 'late collection failure'):
                    Command.execute_cmd(command)
                self.assertIsNone(Search.get_by_code('contract/collect', 'ROLLED'))
                self.assertEqual(Search('contract/collect_in_collect').get_count(), before)
                self.assertEqual(SearchType.get_collection_type('contract/collect?project=one'), 'contract/collect_in_collect')
                def invalid_parent():
                    api.insert(ticket, 'contract/collect', {'code': 'UNRELATED'}, parent_key=root.get_search_key())
                command = Command()
                command.execute = invalid_parent
                with self.assertRaisesRegex(Exception, 'Parent relationship'):
                    Command.execute_cmd(command)
                self.assertIsNone(Search.get_by_code('contract/collect', 'UNRELATED'))


class CollectionCommands(Collections):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='collection_commands_contract', project='one', operation=mode, name=mode)
                     for mode in ('lifecycle', 'batch_cycle')]

    def assert_case_result(self, case, result, original):
        if case['operation'] == 'batch_cycle':
            self.assertEqual(original['earlier_destination_edges'], 1)
            self.assertEqual(result['earlier_destination_edges'], 0)
            self.assertEqual(original['message'].pop('CB_OTHER'), 'Insert OK')
            self.assertEqual(result['message'], original['message'])
        else:
            self.assertTrue(original.pop('deleted_cached'))
            self.assertFalse(result.pop('deleted_cached'))
            self.assertEqual(result, original)

    def test_commands_keep_keyword_descendants_and_roll_back(self):
        from tactic.ui.panel import CollectionAddCmd, CollectionRemoveCmd, CollectionDeleteCmd
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                run_snapshot_case(dict(method='collection_contract', keywords=True))
                api = Api(store)
                api.auth.bind_security('admin', self.ticket)
                root, sub, leaf = [Search.get_by_code('contract/collect', code) for code in ('ROOT', 'SUB', 'LEAF')]
                add = CollectionAddCmd(collection_keys=[root.get_search_key()], search_keys=[sub.get_search_key()])
                Command.execute_cmd(add)
                self.assertIn('renamed', Search.get_by_code('contract/collect', 'LEAF').get_value('keywords'))
                kinds = ('contract/collect', 'contract/collect_in_collect', 'sthpw/sobject_list', 'sthpw/sobject_log', 'sthpw/change_timestamp')
                before = [Search(kind).get_count() for kind in kinds]
                command = Command()
                def fail():
                    Command.execute_cmd(CollectionDeleteCmd(collection_key=sub.get_search_key()))
                    raise ValueError('late collection command failure')
                command.execute = fail
                with self.assertRaisesRegex(ValueError, 'late collection command failure'):
                    Command.execute_cmd(command)
                self.assertEqual([Search(kind).get_count() for kind in kinds], before)
                self.assertIn('renamed', Search.get_by_code('contract/collect', 'LEAF').get_value('keywords'))
                Command.execute_cmd(CollectionRemoveCmd(collection_key=root.get_search_key(), search_keys=[sub.get_search_key()]))
                self.assertNotIn('renamed', Search.get_by_code('contract/collect', 'LEAF').get_value('keywords'))
                Command.execute_cmd(CollectionDeleteCmd(collection_key=sub.get_search_key()))
                self.assertIsNone(Search.get_by_code('contract/collect', 'SUB'))
                self.assertIsNotNone(Search.get_by_code('contract/collect', 'LEAF'))
                self.assertEqual(Search.get_by_code('contract/collect', 'LEAF').get_collections(), [])
                before = Search('contract/collect_in_collect').get_count()
                for cmd in (
                    CollectionAddCmd(collection_keys=[root.get_search_key(), leaf.get_search_key()], search_keys=[leaf.get_search_key()]),
                    CollectionRemoveCmd(collection_key=root.get_search_key(), search_keys=['contract/collect?project=one&code=MISSING']),
                    CollectionDeleteCmd(collection_key=leaf.get_search_key()),
                ):
                    with self.assertRaises(Exception):
                        Command.execute_cmd(cmd)
                    self.assertEqual(Search('contract/collect_in_collect').get_count(), before)
                    self.assertIsNotNone(Search.get_by_code('contract/collect', 'LEAF'))
                # A previously fetched collection is invalid after deletion too.
                Command.execute_cmd(CollectionDeleteCmd(collection_key=root.get_search_key()))
                command = Command()
                command.execute = lambda: leaf.add_to_collection(root)
                with self.assertRaisesRegex(Exception, 'no longer exists'):
                    Command.execute_cmd(command)
