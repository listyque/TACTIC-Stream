import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import test_read_parity as read_tests
import test_checkin as checkin_tests
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store


class IngestionParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        cls.cases = [dict(method='ingestion_contract', project='admin', name='ingest_rules_and_late_persistence')]

    new_result = checkin_tests.CheckinParity.new_result

    def assert_case_result(self, case, result, original):
        self.assertEqual(original.pop('scan'), 'TypeError')  # Source calls a static method through an instance.
        self.assertEqual(result.pop('scan'), [13, 'scan', 'publish', True])
        self.assertEqual(original.pop('walk'), 'NameError')  # Source os.walk(unicode(...)).
        self.assertEqual(result.pop('walk'), 'ok')
        self.assertEqual(original['patterns'][2:][0][0], True)  # Source ignores final literal/suffix.
        self.assertEqual(original['patterns'][3][0], True)
        self.assertEqual(result['patterns'][2:], [[False, {}, {}], [False, {}, {}]])
        original['patterns'][2:] = result['patterns'][2:]
        super().assert_case_result(case, result, original)
        self.assertEqual(result['checkins'], [[1, True, True, 'ingest_copy', True],
                                             [1, True, True, 'ingest_move', False]])

    def test_import_scan_list_and_rollback(self):
        import ingestion_contract
        for fail, late_fail, reject in ((False, False, False), (True, False, False), (False, True, False), (False, False, True)):
            with self.subTest(fail=fail, late_fail=late_fail, reject=reject), tempfile.TemporaryDirectory() as directory:
                store = Store(Path(directory) / 'data')
                shutil.copytree(self.store.data_dir, store.data_dir)
                with request_context(RequestContext(store, 'admin', 'admin')):
                    if fail or late_fail:
                        with self.assertRaisesRegex(ValueError, 'ingest'):
                            ingestion_contract.import_files(fail=fail, late_fail=late_fail)
                        self.assertEqual(Search('sthpw/snapshot').get_count(), 0)
                        self.assertEqual(Search('config/ingest_rule').get_count(), 0)
                        self.assertEqual(Search('sthpw/file').get_count(), 0)
                        self.assertEqual(list(Path(Environment.get_asset_dir()).rglob('*.txt')), [])
                    else:
                        expected = [
                            ['alpha.txt', 'beta.txt'], ['ignored.txt', 'other.bin'],
                            [['alpha', 1, 'alpha.txt', 9], ['beta', 1, 'beta.txt', 8]], True]
                        if reject:
                            expected[2] = expected[2][1:]
                            expected.append(['alpha.txt'])
                        self.assertEqual(ingestion_contract.import_files(reject=reject), expected)

    def test_bulk_ingest_late_failure_restores_files_and_rows(self):
        import ingestion_contract
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                with self.assertRaisesRegex(ValueError, 'late bulk ingest failure'):
                    ingestion_contract.run({'fail': True})
                self.assertEqual(Search('sthpw/snapshot').get_count(), 0)
                self.assertEqual(Search('sthpw/file').get_count(), 0)
                self.assertEqual(list(Path(Environment.get_asset_dir()).rglob('*.txt')), [])
                inputs = Path(Environment.get_tmp_dir()) / 'ingestion_contract'
                for context in ('ingest_copy', 'ingest_move'):
                    self.assertEqual((inputs / (context + '.txt')).read_text(), context)

    def test_ingest_filesystem_access_requires_persisted_admin(self):
        from tactic.command import IngestionCmd
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'anonymous', 'admin')):
                with patch('tactic.command.ingestion_cmd.os.walk') as walk:
                    with self.assertRaises(SecurityException):
                        Command.execute_cmd(IngestionCmd(scan_type='rule', action='file', mode='scan'))
                    walk.assert_not_called()

    def test_ingest_creates_objects_and_resolves_existing_code_and_id(self):
        from tactic.command import IngestionCmd
        from tactic_stream.server.api import Api
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                Api(store).auth.bind_security('admin', self.ticket)
                inputs = Path(Environment.get_tmp_dir()) / 'object_ingest'
                for code in ('A', 'NEW'):
                    path = inputs / code / 'publish.txt'
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(code)
                options = dict(scan_type='rule', action='file', mode='checkin', base_dir='',
                               session_base_dir=inputs.as_posix(), search_type='contract/entity',
                               pattern='{code}/{snapshot.context}.txt', extra_name=['name'],
                               extra_value=['Imported'])
                command = IngestionCmd(**options)
                command.get_transaction().set_sync(False)
                Command.execute_cmd(command)
                self.assertEqual(Search.get_by_code('contract/entity', 'A').get_value('name'), 'Imported')
                created = Search.get_by_code('contract/entity', 'NEW')
                self.assertEqual(created.get_value('name'), 'Imported')
                identity_path = inputs / str(created.get_id()) / 'review.txt'
                identity_path.parent.mkdir(parents=True)
                identity_path.write_text('by ID')
                by_id = dict(options, scan_type='list', file_list=identity_path.as_posix(),
                             pattern='{id}/{snapshot.context}.txt', extra_value=['By ID'])
                command = IngestionCmd(**by_id)
                command.get_transaction().set_sync(False)
                Command.execute_cmd(command)
                search = Search('contract/entity')
                search.add_filter('code', 'NEW')
                self.assertEqual(search.get_count(), 1)
                self.assertEqual(search.get_sobject().get_value('name'), 'By ID')
