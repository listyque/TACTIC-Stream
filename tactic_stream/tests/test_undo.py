import tempfile
import shutil
from pathlib import Path
import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case


class UndoParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='undo_contract', name='original_rename_undo_bug', project='admin', rename=True)]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'admin')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        code = 'UNDO_RENAMED' if case.get('rename') else 'UNDO_CONTRACT'
        self.assertEqual(result, [
            [['UNDO_CONTRACT', 'before']], [], [['UNDO_CONTRACT', 'before']],
            [[code, 'after']], [['UNDO_CONTRACT', 'before']], [[code, 'after']],
            [], [[code, 'after']], [],
        ])
        if case.get('rename'):
            # Original Note code dependency handling leaves the in-memory old
            # code and therefore addresses the wrong row in the durable journal.
            self.assertEqual(original['error'], 'SObjectException')
            self.assertIn('Insert/Update of [sthpw/note] failed', original['message'])
        else:
            # Source replay leaves the previous identity cached in one request.
            self.assertEqual(original, [
                [['UNDO_CONTRACT', 'before']], [], [['UNDO_CONTRACT', 'before']],
                [['UNDO_CONTRACT', 'after']], [['UNDO_CONTRACT', 'before']],
                [['UNDO_CONTRACT', 'before']], [], [['UNDO_CONTRACT', 'before']], [['UNDO_CONTRACT', 'before']],
            ])


class UndoBasicParity(UndoParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='undo_contract', name='insert_update_delete_undo_redo', project='admin')]


class NoteThreadUndoParity(UndoParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='undo_contract', name='note_thread_identity_restoration', project='admin', thread=True)]

    def assert_case_result(self, case, result, original):
        self.assertEqual(result, [True, True])
        # Source reassigns coded note IDs on restore, leaving parent_id dangling.
        self.assertEqual(original, [False, False])
