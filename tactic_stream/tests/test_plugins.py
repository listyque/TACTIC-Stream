"""Plugin directory behavior against the actual original runtime."""
import shutil
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.snapshot_probe import run_snapshot_case


class PluginParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='plugin_contract', name='plugin_' + str(fail), fail=fail)
                     for fail in (True, False)]
        cls.cases.append(dict(method='plugin_contract', name='explicit_id_update', explicit_id=True))

    def assert_case_result(self, case, result, original):
        if case.get('explicit_id'):
            # Original keeps force_insert after matching a unique row, then
            # swallows duplicate-PK errors. Assert both behaviors explicitly.
            self.assertEqual(original, dict(error=None, rows=[['PLUGIN_EXPLICIT', 'Плагин', 10]]))
            self.assertEqual(result, dict(error=None, rows=[['PLUGIN_EXPLICIT', 'Обновлённый плагин', 77]]))
        else:
            self.assertEqual(result, original)

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)
