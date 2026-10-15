import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_read_parity as read_tests
from test_checkin import CheckinParity
from pyasm.common import Config, Environment
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tactic_stream.server.api import Api, check_ticket_paths
from tools.snapshot_probe import run_snapshot_case


class HandoffParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='handoff_contract', project='admin', name='handoff_API')]

    new_result = CheckinParity.new_result

    def test_failure_rolls_back_database_and_keeps_consumed_files_in_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                api = Api(store)
                api.auth.bind_security('admin', self.ticket)
                kinds = ('sthpw/snapshot', 'sthpw/file', 'sthpw/transaction_log')
                before = [Search(kind).get_count() for kind in kinds]
                with self.assertRaisesRegex(ValueError, 'late handoff failure'):
                    run_snapshot_case(dict(method='handoff_contract', fail=True))
                self.assertEqual([Search(kind).get_count() for kind in kinds], before)
                # Original create-mode undo retains consumed inputs in the file cache.
                cache = Path(Environment.get_tmp_dir()) / 'undo'
                self.assertEqual({path.read_bytes() for path in cache.rglob('*.txt') if path.is_file()},
                    {b'extra1', b'extra2', b'extra', b'frame1', b'frame2', b'main'})
                self.assertFalse(any(path.is_file() for path in (store.data_dir / 'assets').rglob('*')))

class HandoffPaths(unittest.TestCase):
    def test_server_paths_preserve_full_ticket_and_client_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ticket = 'a' * 120
            values = {'win32_server_handoff_dir': 'incoming', 'linux_server_handoff_dir': 'incoming',
                      'win32_client_handoff_dir': '//share/handoff', 'linux_client_handoff_dir': '//share/handoff'}
            with (patch.object(Config, 'get_value', side_effect=lambda section, key, **kwargs: values.get(key, '')),
                  patch.object(Environment, 'get_data_dir', return_value=str(root))):
                self.assertEqual(Path(Environment.get_server_handoff_dir(ticket)), root / 'incoming' / ticket)
                self.assertEqual(Environment.get_client_handoff_dir(ticket), '//share/handoff/' + ticket)
                with self.assertRaisesRegex(Exception, 'Invalid directory ticket'):
                    Environment.get_server_handoff_dir('../outside')

    def test_ticket_paths_and_symlinked_frames_stay_inside_handoff(self):
        from pyasm.biz import FileRange
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            handoff = root / 'handoff'
            handoff.mkdir()
            outside = root / 'outside.txt'
            outside.write_text('keep')
            with self.assertRaises(ValueError):
                check_ticket_paths([str(outside)], handoff)
            link = handoff / 'image.0001.txt'
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest('Symlink privilege required; also checked in Linux/PostgreSQL test')
            with self.assertRaises(ValueError):
                check_ticket_paths([str(handoff / 'image.####.txt')], handoff, FileRange(1, 1))
            self.assertEqual(outside.read_text(), 'keep')
            outside_directory = root / 'outside_directory'
            outside_directory.mkdir()
            (handoff / 'TICKET').symlink_to(outside_directory, target_is_directory=True)
            with patch.object(Config, 'get_value', return_value=str(handoff)):
                self.assertEqual(Path(Environment.get_server_handoff_dir(include_ticket=False)), handoff)
                with self.assertRaisesRegex(Exception, 'inside its root'):
                    Environment.get_server_handoff_dir('TICKET')
