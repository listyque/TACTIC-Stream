"""Unmodified Handler batch protocol and native rollback of naming callbacks."""
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.checkin_benchmark import prepare
from pyasm.search.storage import Store


class NamingBatch(unittest.TestCase):
    def test_callback_failure_rolls_back_the_entire_native_request(self):
        previous_path = sys.path.copy()
        try:
            sys.path.insert(0, 'D:/code/th_codex')
            from thlib import tactic_query as tq
        finally:
            sys.path[:] = previous_path
        get_source = tq._function_source_lines
        callback = '''def get_virtual_snapshot_extended(context):
    import json
    from pyasm.search import SearchType
    shot = SearchType.create('cg/shot')
    shot.set_value('code', 'NAMING_' + context)
    shot.set_value('name', context)
    shot.commit()
    if context == 'fail':
        raise ValueError('naming callback failed after a native write')
    return json.dumps([context])
'''
        with tempfile.TemporaryDirectory() as directory:
            api, ticket = prepare(Store(directory))
            api.protocol = 'json'
            auth = dict(ticket=ticket, project='one')
            def source(function):
                return callback.splitlines(True) if function is tq.get_virtual_snapshot_extended else get_source(function)
            with patch.object(tq, '_function_source_lines', side_effect=source):
                command = tq.prepare_serverside_script(tq.get_virtual_snapshots_extended,
                    dict(operations=[dict(context='first'), dict(context='fail')]),
                    shrink=False, catch_traceback=False)
                with self.assertRaisesRegex(ValueError, 'naming callback failed'):
                    api.dispatch('execute_python_script', (auth, '', command))
                self.assertEqual(api.dispatch('query', (auth, 'cg/shot'),
                    dict(filters=[('code', ['NAMING_first', 'NAMING_fail'])])), [])
                command = tq.prepare_serverside_script(tq.get_virtual_snapshots_extended,
                    dict(operations=[dict(context='first'), dict(context='second')]),
                    shrink=False, catch_traceback=False)
                result = api.dispatch('execute_python_script', (auth, '', command))
                values = result['info']
                if isinstance(values, dict):
                    values = values['spt_ret_val']
                if isinstance(values, str):
                    values = json.loads(values)
                self.assertEqual([value['result'] for value in values], [['first'], ['second']])
                self.assertEqual(len(api.dispatch('query', (auth, 'cg/shot'),
                    dict(filters=[('code', ['NAMING_first', 'NAMING_second'])]))), 2)
