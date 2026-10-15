"""Isolated million-entry catalog benchmark; synthetic metadata, not TB transfers."""
import argparse
import base64
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import tempfile
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from pyasm.biz import Project
from pyasm.biz.file_catalog import FileCatalog
from pyasm.biz.file_project import COMMAND, PageStore, access, find, save
from pyasm.command import Command
from pyasm.common import Config
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.search.transaction import Transaction
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api


def benchmark(count, checkin_files=1000):
    if count < 1:
        raise ValueError('Positive file count required')
    if not 0 <= checkin_files <= 1000:
        raise ValueError('Real check-in sample must contain 0..1000 files')
    with tempfile.TemporaryDirectory(prefix='file-catalog-') as directory:
        store = Store(Path(directory))
        if store.get_db_resource().get_vendor() != 'Sqlite':
            raise ValueError('Benchmark requires isolated SQLite configuration')
        store.initialize(hash_password('isolated-file-benchmark'))
        api = Api(store)
        token = api.get_ticket('admin', 'isolated-file-benchmark')
        api.dispatch('execute_cmd', ({'ticket': token, 'project': 'admin'}, 'tactic.command.CreateProjectCmd',
            {'project_code': 'files', 'project_title': 'Isolated benchmark', 'project_mode': 'file_project'}))
        ticket = {'ticket': token, 'project': 'files'}
        def call(action, **kwargs):
            started = perf_counter()
            result = api.dispatch('execute_cmd', (ticket, COMMAND, {'action': action, **kwargs}))['info']
            return result, (perf_counter() - started) * 1000
        call('create_depot', code='main')
        call('create_stream', code='main', depot='main')
        call('create_workspace', code='work', stream='main', local_root='D:/benchmark-only')
        change, _ = call('create_change', workspace='work')
        # Build bounded native catalog pages without claiming one million physical uploads/versions.
        started = perf_counter()
        with request_context(RequestContext(store, 'admin', 'files')):
            api.auth.bind_security('admin', token)
            children = []
            for start in range(0, count, 4096):
                cmd = Command(log_exception=False)
                def build(start=start):
                    with access('files'):
                        Transaction.get().require_single_database(Project.get().get_project_db_resource())
                        pages = PageStore()
                        catalog = FileCatalog(pages.load, pages.save)
                        for offset in range(start, min(start + 4096, count), 256):
                            entries = [{'path': 'dir/%09d.bin' % index, 'blob': '0' * 32, 'size': 1024,
                                        'sha256': '0' * 64, 'version': '0' * 32, 'number': 1,
                                        'stream': 'main', 'source_path': 'dir/%09d.bin' % index,
                                        'local_path': 'dir/%09d.bin' % index, 'published_change': change['code']}
                                       for index in range(offset, min(offset + 256, count))]
                            children.append(catalog.store({'leaf': True, 'items': entries}))
                        pages.flush()
                cmd.execute = build
                Command.execute_cmd(cmd)
            cmd = Command(log_exception=False)
            def root():
                nonlocal children
                with access('files'):
                    Transaction.get().require_single_database(Project.get().get_project_db_resource())
                    pages = PageStore()
                    catalog = FileCatalog(pages.load, pages.save)
                    while len(children) > 1:
                        children = [catalog.store({'leaf': False, 'items': children[start:start + 256]})
                                    for start in range(0, len(children), 256)]
                    pages.flush()
                    item = find('change', change['code'])
                    data = item.get_json_value('data')
                    data['root'] = children[0]['code']
                    save(item, data)
            cmd.execute = root
            Command.execute_cmd(cmd)
        build_ms = (perf_counter() - started) * 1000
        published, submit_ms = call('submit', change=change['code'])
        first, first_ms = call('list', stream='main', limit=1000)
        tail, tail_ms = call('list', stream='main', limit=1000, after='dir/%09d.bin' % max(0, count - 1001),
                             published_change=first['published_change'])
        sync, sync_begin_ms = call('sync_begin', workspace='work')
        plan, sync_next_ms = call('sync_next', sync=sync['code'])
        assert first['files'] == count and published['files'] == count
        assert len(plan['items']) == min(count, 1000)
        # Synthetic Have is a metadata fixture; no download/physical million-version claim.
        call('create_workspace', code='mapped', stream='main', local_root='D:/mapped-benchmark-only',
             mappings=[{'stream': 'main', 'source': '...', 'target': '...', 'writable': True}])
        with request_context(RequestContext(store, 'admin', 'files')):
            api.auth.bind_security('admin', token)
            cmd = Command(log_exception=False)
            def seed_have():
                with access('files'):
                    Transaction.get().require_single_database(Project.get().get_project_db_resource())
                    stream = find('stream', 'main').get_json_value('data')
                    item = find('workspace', 'mapped')
                    data = item.get_json_value('data')
                    data.update(have_root=stream['root'], sync_checkpoint={'view_revision': 0,
                                'have_root': stream['root'], 'sources': {'main': stream['root']}})
                    save(item, data)
            cmd.execute = seed_have
            Command.execute_cmd(cmd)
        _, branch_ms = call('create_stream', code='branch', depot='main', parent='main')
        unchanged, unchanged_begin_ms = call('sync_begin', workspace='mapped')
        no_files, unchanged_next_ms = call('sync_next', sync=unchanged['code'])
        assert not no_files['items']
        _, unchanged_ack_ms = call('sync_ack', sync=unchanged['code'], ack_revision=0, paths=[])
        draft, _ = call('create_change', workspace='work')
        blob, _ = call('upload_begin', change=draft['code'], size=1)
        call('upload_chunk', change=draft['code'], blob=blob['code'], offset=0, data='eA==')
        call('upload_finish', change=draft['code'], blob=blob['code'])
        call('edit', change=draft['code'], chunk='sparse', edit_revision=0,
             operations=[{'path': 'dir/%09d.bin' % (count // 2), 'blob': blob['code']}])
        call('submit', change=draft['code'])
        sparse, sparse_begin_ms = call('sync_begin', workspace='mapped')
        difference, sparse_next_ms = call('sync_next', sync=sparse['code'])
        assert len(difference['items']) == 1
        _, sparse_ack_ms = call('sync_ack', sync=sparse['code'], ack_revision=0,
                                paths=[item['path'] for item in difference['items']])
        workspace = {'synthetic_have_without_download': True, 'branch_ms': round(branch_ms, 2),
                     'unchanged_begin_ms': round(unchanged_begin_ms, 2), 'unchanged_next_ms': round(unchanged_next_ms, 2),
                     'unchanged_ack_ms': round(unchanged_ack_ms, 2), 'one_changed_file_begin_ms': round(sparse_begin_ms, 2),
                     'one_changed_file_next_ms': round(sparse_next_ms, 2), 'one_changed_file_ack_ms': round(sparse_ack_ms, 2)}
        real = None
        if checkin_files:
            call('create_stream', code='real', depot='main')
            call('create_workspace', code='real', stream='real', local_root='D:/real-benchmark-only')
            draft, _ = call('create_change', workspace='real')
            contents = [sha256(str(index).encode('ascii')).digest() * 16 for index in range(checkin_files)]
            uploaded, descriptors_ms = call('upload_begin', change=draft['code'], request_id='unique-files',
                files=[{'path': 'unique/%06d.bin' % index, 'size': len(data)} for index, data in enumerate(contents)])
            _, upload_ms = call('upload_batch', change=draft['code'], items=[
                {'blob': row['blob'], 'data': base64.b64encode(data).decode('ascii')} for row, data in zip(uploaded['items'], contents)])
            _, edit_ms = call('edit', change=draft['code'], chunk='unique-files', edit_revision=0,
                operations=[{'path': row['path'], 'blob': row['blob']} for row in uploaded['items']])
            result, real_submit_ms = call('submit', change=draft['code'])
            assert result['files'] == checkin_files
            for index in set((0, checkin_files // 2, checkin_files - 1)):
                downloaded, _ = call('read', stream='real', path='unique/%06d.bin' % index)
                assert base64.b64decode(downloaded['data']) == contents[index]
            real = {'files': checkin_files, 'distinct_physical_files': True, 'bytes': sum(map(len, contents)),
                    'upload_descriptors_ms': round(descriptors_ms, 2), 'upload_bytes_ms': round(upload_ms, 2),
                    'edit_ms': round(edit_ms, 2), 'submit_ms': round(real_submit_ms, 2),
                    'already_uploaded_to_submitted_ms': round(edit_ms + real_submit_ms, 2),
                    'total_ms': round(descriptors_ms + upload_ms + edit_ms + real_submit_ms, 2)}
        try:
            import ctypes
            class Counters(ctypes.Structure):
                _fields_ = [('cb', ctypes.c_ulong), ('faults', ctypes.c_ulong)] + [(name, ctypes.c_size_t) for name in
                    ('peak', 'working', 'paged_peak', 'paged', 'nonpaged_peak', 'nonpaged', 'pagefile', 'pagefile_peak')]
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            handle = ctypes.c_void_p(-1)
            if not ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                raise OSError('Process memory counters unavailable')
            peak_mib = counters.peak / 1024**2
        except (AttributeError, OSError):
            peak_mib = None
        return {'files': count, 'synthetic_catalog_only': True, 'catalog_build_ms': round(build_ms, 2),
                'submit_ms': round(submit_ms, 2), 'list_first_1000_ms': round(first_ms, 2),
                'list_tail_1000_ms': round(tail_ms, 2), 'sync_begin_ms': round(sync_begin_ms, 2),
                'sync_next_1000_ms': round(sync_next_ms, 2), 'process_peak_mib': peak_mib, 'real_checkin': real,
                'mapped_workspace': workspace}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--files', type=int, default=1_000_000)
    parser.add_argument('--checkin-files', type=int, default=1000)
    args = parser.parse_args()
    # Never use the configured production PostgreSQL/database for this benchmark.
    os.environ['TACTIC_CONFIG_PATH'] = os.environ['TACTIC_TMP_CONFIG_PATH'] = ''
    Config.reload_config()
    print(json.dumps(benchmark(args.files, args.checkin_files), indent=2))
