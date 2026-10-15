import shutil
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from test_pipeline import pipeline_fixture
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.business_probe import run_business_case


class BusinessParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        pipeline_fixture(cls.store)
        cls.cases = [dict(name='business', method='business_contract', project='one'),
                     dict(name='task_sort', method='business_contract', project='one', sort=True)]

    def new_result(self, case):
        with tempfile.TemporaryDirectory(prefix='tactic-stream-business-') as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', case['project'])):
                return run_business_case(case)

    def assert_case_result(self, case, result, original):
        if case.get('sort'):
            self.assertEqual(original, {'error': 'TypeError'})
            self.assertEqual(result, {'sorted': ['start', 'review']})
            return
        self.assertNotIn('error', original, original)
        if case.get('triggers') is not False:
            # Original Task.create plus CoreInit logs the initial status twice.
            self.assertEqual(original['status_log'][:2], [['', 'Assignment']] * 2)
            self.assertEqual(result['status_log'][0], ['', 'Assignment'])
            original['status_log'].pop(0)
            self.assertEqual(result['journal'], original['journal'] - 1)
            original['journal'] -= 1
            # One duplicate initial log plus two records from deferred completion
            # disappear when completion is folded into the original transaction.
            self.assertEqual(sum(row[0] == 'sthpw/sobject_log' for row in original['change_timestamps']),
                             sum(row[0] == 'sthpw/sobject_log' for row in result['change_timestamps']) + 3)
            original['change_timestamps'] = [row for row in original['change_timestamps']
                                             if row[0] not in ('sthpw/status_log', 'sthpw/sobject_log')]
            result['change_timestamps'] = [row for row in result['change_timestamps']
                                           if row[0] not in ('sthpw/status_log', 'sthpw/sobject_log')]
        super().assert_case_result(case, result, original)
        self.assertEqual(result['completion'], [0, 10, 100, 100, 10])
        self.assertEqual(result['ended'], case.get('triggers') is not False)
        self.assertEqual(result['deleted'], [0, 0])

    def test_private_notes_public_writes_and_failed_command_rollback(self):
        import ast
        from pyasm.biz import Task, Project
        from pyasm.command import Command
        from pyasm.common import Container
        from pyasm.common.errors import SecurityException, UnsupportedContract
        from pyasm.search import Search, SearchType, Transaction
        from tactic_stream.server.api import Api
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            from pyasm.security.authenticator import hash_password
            store.initialize(hash_password('private-test-password'))
            api = Api(store)
            admin = {'ticket': api.get_ticket('admin', 'private-test-password'), 'project': 'admin'}
            viewer = api.dispatch('insert', (admin, 'sthpw/login', {'login': 'viewer', 'password': hash_password('private-viewer-password')}))
            ticket = {'ticket': api.get_ticket('viewer', 'private-viewer-password'), 'project': 'admin'}
            task = api.dispatch('insert', (admin, 'sthpw/task', {'process': 'publish', 'status': 'Pending'}))
            notes = []
            for login, access in [('admin', 'private'), ('viewer', 'private'), ('admin', 'public'), ('admin', None)]:
                data = {'login': login, 'context': 'publish', 'note': "Комментарий O'Reilly"}
                if access:
                    data['access'] = access
                notes.append(api.dispatch('insert', (admin, 'sthpw/note', data), {'parent_key': task['__search_key__']}))
            visible = ast.literal_eval(api.dispatch('query', (ticket, 'sthpw/note')))
            self.assertEqual({row['id'] for row in visible}, {row['id'] for row in notes[1:]})
            self.assertEqual(api.dispatch('get_by_code', (ticket, 'sthpw/note', notes[0]['code'])), {})
            filtered = ast.literal_eval(api.dispatch('query', (ticket, 'sthpw/note', [['code', 'missing']])))
            self.assertEqual(filtered, [])
            with self.assertRaises(SecurityException):
                api.dispatch('update', (ticket, task['__search_key__'], {'status': 'Complete'}))
            with request_context(RequestContext(store, 'viewer', 'admin')):
                api.auth.bind_security('viewer', ticket['ticket'])
                search = Search('sthpw/note')
                self.assertEqual(search.get_count(), 3)
                self.assertEqual(len(search.get_sobjects()), 3)
                self.assertEqual(search.get_count(), 3)
            from unittest.mock import patch
            before_logs = ast.literal_eval(api.dispatch('query', (admin, 'sthpw/status_log')))
            with patch('tactic.command.TaskCompleteTrigger.execute', side_effect=ValueError('failed completion trigger')):
                with self.assertRaisesRegex(ValueError, 'failed completion trigger'):
                    api.dispatch('update', (admin, task['__search_key__'], {'status': 'Complete'}))
            unchanged = api.dispatch('get_by_search_key', (admin, task['__search_key__']))
            self.assertEqual(unchanged['status'], 'Pending')
            self.assertFalse(unchanged['actual_end_date'])
            self.assertEqual(ast.literal_eval(api.dispatch('query', (admin, 'sthpw/status_log'))), before_logs)
            api.dispatch('update', (admin, task['__search_key__'], {'status': 'Complete'}))
            self.assertTrue(api.dispatch('get_by_search_key', (admin, task['__search_key__']))['actual_end_date'])
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', admin['ticket'])
                before = [Search(kind).get_count() for kind in ('sthpw/task', 'sthpw/status_log', 'sthpw/transaction_log', 'sthpw/change_timestamp')]
                class Failed(Command):
                    def execute(self):
                        self.get_transaction().set_sync(False)
                        obj = Task.create(Project.get(), 'review', project_code='admin')
                        self.key = obj.get_search_key()
                        Search.get_by_search_key(self.key)
                        raise ValueError('failed business command')
                failed = Failed()
                with self.assertRaisesRegex(ValueError, 'failed business command'):
                    Command.execute_cmd(failed)
                self.assertEqual([Search(kind).get_count() for kind in ('sthpw/task', 'sthpw/status_log', 'sthpw/transaction_log', 'sthpw/change_timestamp')], before)
                self.assertIsNone(Search.get_by_search_key(failed.key))
                self.assertFalse(Transaction.get().is_in_transaction())
                self.assertEqual(Container.get_seq(Command.TOP_CMD_KEY), [])
            with self.assertRaises(UnsupportedContract):
                api.dispatch('update', (admin, task['__search_key__'], {'pipeline_code': 'unported_custom'}))
            self.assertEqual(api.dispatch('get_by_search_key', (admin, task['__search_key__']))['pipeline_code'], 'task')
