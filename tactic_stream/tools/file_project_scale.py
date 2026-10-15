"""Bounded native API load with real version/checkout rows; not a physical TB test."""
import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import sys
import tempfile
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]

from pyasm.biz.file_project import COMMAND, access
from pyasm.common import Config
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from tools.file_project_checks import postgres
from unittest.mock import patch


def peak_mib():
    try:
        import ctypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', ctypes.c_ulong), ('faults', ctypes.c_ulong)] + [(name, ctypes.c_size_t) for name in
                ('peak', 'working', 'paged_peak', 'paged', 'nonpaged_peak', 'nonpaged', 'pagefile', 'pagefile_peak')]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if not ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(-1), ctypes.byref(counters), counters.cb):
            raise OSError('Memory counters unavailable')
        return round(counters.peak / 1024**2, 2)
    except (AttributeError, OSError):
        return None


def benchmark(files, config=''):
    if files < 1000:
        raise ValueError('At least 1000 logical files required')
    with tempfile.TemporaryDirectory(prefix='file-api-scale-') as directory, \
            patch.dict(os.environ, {'TACTIC_CONFIG_PATH': config, 'TACTIC_TMP_CONFIG_PATH': ''}):
        Config.reload_config()
        try:
            store = Store(Path(directory))
            store.initialize(hash_password('isolated-scale-password'))
            api = Api(store)
            token = api.get_ticket('admin', 'isolated-scale-password')
            api.dispatch('execute_cmd', ({'ticket': token, 'project': 'admin'}, 'tactic.command.CreateProjectCmd',
                         {'project_code': 'files', 'project_title': 'Private scale check', 'project_mode': 'file_project'}))
            ticket = {'ticket': token, 'project': 'files'}
            def call(action, **kwargs):
                started = perf_counter()
                result = api.dispatch('execute_cmd', (ticket, COMMAND, {'action': action, 'log_exception': False, **kwargs}))['info']
                return result, round((perf_counter() - started) * 1000, 2)
            call('create_depot', code='main')
            call('create_stream', code='main', depot='main')
            call('create_workspace', code='work', stream='main', local_root='D:/scale-only')
            draft, _ = call('create_change', workspace='work')
            change = draft['code']
            blob, _ = call('upload_begin', change=change, size=3)
            call('upload_chunk', change=change, blob=blob['code'], offset=0, data='YWJj')
            call('upload_finish', change=change, blob=blob['code'])
            samples, revision, first_ms, last_ms = [], 0, None, None
            started = perf_counter()
            for offset in range(0, files, 1000):
                ops = [{'path': 'dir/%09d.bin' % index, 'blob': blob['code']} for index in range(offset, min(offset + 1000, files))]
                result, elapsed = call('edit', change=change, chunk='chunk%d' % offset, edit_revision=revision, operations=ops)
                revision = result['edit_revision']
                first_ms = elapsed if first_ms is None else first_ms
                last_ms = elapsed
                if revision % 25 == 0 or offset + 1000 >= files:
                    progress = {'files': result['files'], 'elapsed_s': round(perf_counter() - started, 2),
                                'last_edit_ms': elapsed, 'peak_mib': peak_mib()}
                    samples.append(progress)
                    print(json.dumps(progress), flush=True)
            build_s = round(perf_counter() - started, 2)
            submitted, submit_ms = call('submit', change=change)
            assert submitted['files'] == files
            # Count persisted native rows, not in-memory generated entries.
            with request_context(RequestContext(store, 'admin', 'files')):
                api.auth.bind_security('admin', token)
                with access('files'):
                    counts = {kind: Search('file_project/' + kind).get_count() for kind in ('version', 'checkout', 'page', 'blob')}
            assert counts['version'] == counts['checkout'] == files, counts
            head, head_ms = call('list', stream='main')
            tail, tail_ms = call('list', stream='main', after='dir/%09d.bin' % (files - 1001), published_change=change)
            assert len(head['items']) == len(tail['items']) == 1000
            history, history_ms = call('history', stream='main', path='dir/%09d.bin' % (files - 1))
            assert len(history['items']) == 1
            sync, sync_begin_ms = call('sync_begin', workspace='work')
            plan, sync_next_ms = call('sync_next', sync=sync['code'])
            ack, sync_ack_ms = call('sync_ack', sync=sync['code'], ack_revision=0, paths=[item['path'] for item in plan['items']])
            assert ack['files_done'] == 1000
            if ack['state'] == 'running':
                call('sync_cancel', sync=sync['code'])
            # A fresh 1000-path change after the million-row history, with new payload.
            next_change, _ = call('create_change', workspace='work')
            new_blob, _ = call('upload_begin', change=next_change['code'], size=3)
            call('upload_chunk', change=next_change['code'], blob=new_blob['code'], offset=0, data='ZGVm')
            call('upload_finish', change=next_change['code'], blob=new_blob['code'])
            updated, reedit_ms = call('edit', change=next_change['code'], chunk='fresh', edit_revision=0,
                operations=[{'path': item['path'], 'blob': new_blob['code']} for item in tail['items']])
            _, resubmit_ms = call('submit', change=next_change['code'])
            assert updated['files'] == files
            history, _ = call('history', stream='main', path='dir/%09d.bin' % (files - 1))
            assert [item['number'] for item in history['items']] == [2, 1]
            return {'vendor': store.get_db_resource().get_vendor(), 'logical_files': files, 'persisted_before_reedit': counts,
                    'physical_payload_files': 2, 'network_included': False, 'build_s': build_s,
                    'first_edit_1000_ms': first_ms, 'last_edit_ms': last_ms, 'submit_ms': submit_ms,
                    'list_head_1000_ms': head_ms, 'list_tail_1000_ms': tail_ms, 'history_ms': history_ms,
                    'sync_begin_ms': sync_begin_ms, 'sync_next_ms': sync_next_ms, 'sync_ack_1000_ms': sync_ack_ms,
                    'fresh_edit_1000_ms': reedit_ms, 'fresh_submit_ms': resubmit_ms,
                    'peak_mib': peak_mib(), 'samples': samples}
        finally:
            Config.reload_config()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--files', type=int, default=1_000_000)
    parser.add_argument('--postgres', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    with postgres() if args.postgres else nullcontext('') as config:
        result = benchmark(args.files, config)
    text = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(text + '\n', encoding='utf-8')
    print(text)
