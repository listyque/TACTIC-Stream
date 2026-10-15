import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_read_parity as read_tests
import test_checkin as checkin_tests
from pyasm.common import Environment, FormatValue
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store


class DirectoryParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        cls.cases = [dict(method='directory_contract', project='admin', name='directory_checkin')]

    new_result = checkin_tests.CheckinParity.new_result

    def assert_case_result(self, case, result, original):
        self.assertEqual(original.pop('timecode'), ['AttributeError'] * 3)
        self.assertEqual(result.pop('timecode'), [['00:00:00', 24, -12], ['00:01:12', 60, 24], ['01:15:00', 1824, 1788]])
        old_format = original.pop('format')
        self.assertEqual(old_format[3:6], ['True', 'true', 'SyntaxError'])
        self.assertEqual(result.pop('format'), ['0.0 B', '512 B', '1.0 KB', 'False', 'false',
                                               'a : 1<br />b : 2', 172803, '07/10/26'])
        super().assert_case_result(case, result, original)
        self.assertEqual(result['info'], {'size': 10, 'count': 2, 'display_size': '10 B', 'file_type': 'directory'})

    def test_directory_ingest_and_late_rollback(self):
        import directory_contract
        for fail, list_mode in ((False, False), (False, True), (True, True)):
            with self.subTest(fail=fail, list=list_mode), tempfile.TemporaryDirectory() as directory:
                store = Store(Path(directory) / 'data')
                shutil.copytree(self.store.data_dir, store.data_dir)
                with request_context(RequestContext(store, 'admin', 'admin')):
                    if fail:
                        with self.assertRaisesRegex(ValueError, 'late directory ingest'):
                            directory_contract.ingest(fail=True, list=list_mode)
                        self.assertEqual(Search('sthpw/snapshot').get_count(), 0)
                        self.assertEqual(Search('sthpw/file').get_count(), 0)
                        self.assertEqual(list(Path(Environment.get_asset_dir()).rglob('*.txt')), [])
                    else:
                        self.assertEqual(directory_contract.ingest(list=list_mode), [['first', 'second'],
                            [['first', [['main.txt', 'first'], ['nested/main.txt', 'child']]],
                             ['second', [['main.txt', 'second'], ['nested/main.txt', 'child']]]], 'keep me'])
                    root = Path(Environment.get_tmp_dir()) / 'directory_ingest'
                    self.assertTrue((root / 'first' / 'empty').is_dir())
                    self.assertEqual((root / 'second' / 'nested' / 'main.txt').read_text(), 'child')

    def test_directory_move_rollback_restores_tree(self):
        import directory_contract
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                with self.assertRaisesRegex(ValueError, 'late directory failure'):
                    directory_contract.run({'fail': True})
                self.assertEqual(Search('sthpw/snapshot').get_count(), 0)
                self.assertEqual(Search('sthpw/file').get_count(), 0)
                root = Path(Environment.get_tmp_dir()) / 'directory_contract'
                self.assertEqual((root / 'move' / 'nested' / 'entry.txt').read_text(), 'inside')
                self.assertTrue((root / 'move' / 'empty').is_dir())

    def test_file_size_format_needs_no_currency_locale(self):
        with patch('locale.currency', side_effect=ValueError('C locale')):
            self.assertEqual(FormatValue().get_format_value(1024 ** 3, 'KB'), '1.0 GB')


class DirectoryPaths(unittest.TestCase):
    def test_ticket_directory_descendants_cannot_escape_or_recurse(self):
        from tactic_stream.server.api import check_ticket_paths
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ticket = root / 'ticket'
            bundle = ticket / 'bundle'
            bundle.mkdir(parents=True)
            outside = root / 'outside.txt'
            outside.write_text('outside')
            link = bundle / 'escape.txt'
            try:
                link.symlink_to(outside)
            except OSError as error:
                self.skipTest('OS symlink privilege unavailable: ' + str(error))
            with self.assertRaisesRegex(ValueError, 'directory contents'):
                check_ticket_paths([bundle], ticket)
            link.unlink()
            link = bundle / 'loop'
            link.symlink_to(bundle, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'directory links'):
                check_ticket_paths([bundle], ticket)
            self.assertEqual(outside.read_text(), 'outside')
