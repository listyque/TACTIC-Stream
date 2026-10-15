"""Isolated native changelist timings; real metadata and payloads, no client network."""
import argparse
import base64
from contextlib import nullcontext
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import perf_counter
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'tests')]

from test_file_project import FileProjectFixture
from tools.file_project_checks import postgres
from tools.file_project_scale import peak_mib


class Fixture(FileProjectFixture, unittest.TestCase):
    pass


def benchmark(config='', catalog_files=10000, changed_files=1000):
    if catalog_files < changed_files or not 1 <= changed_files <= 1000:
        raise ValueError('Sample requires a positive 1..1000 changed-file chunk inside the catalog')
    fixture = Fixture()
    fixture.database_config = config
    timings = {}
    try:
        fixture.setUp()
        def call(label, action, **kwargs):
            started = perf_counter()
            result = fixture.call(action, **kwargs)
            timings[label] = round((perf_counter() - started) * 1000, 2)
            return result
        seed = fixture.change()
        blob = fixture.upload(seed, b'base')
        started = perf_counter()
        revision = 0
        for offset in range(0, catalog_files, 1000):
            result = fixture.call('edit', change=seed, edit_revision=revision, chunk='seed-%d' % offset,
                operations=[{'path': '%08d.bin' % i, 'blob': blob} for i in range(offset, min(offset + 1000, catalog_files))])
            revision = result['edit_revision']
        fixture.call('submit', change=seed)
        timings['catalog_build'] = round((perf_counter() - started) * 1000, 2)
        draft = fixture.change()
        contents = [sha256(str(i).encode()).digest() * 16 for i in range(changed_files)]
        uploads = call('upload_begin', 'upload_begin', change=draft, request_id='files',
            files=[{'path': '%08d.bin' % i, 'size': len(data)} for i, data in enumerate(contents)])
        call('upload_batch', 'upload_batch', change=draft, items=[
            {'blob': item['blob'], 'data': base64.b64encode(data).decode()} for item, data in zip(uploads['items'], contents)])
        call('edit', 'edit', change=draft, chunk='files', edit_revision=0,
             operations=[{'path': item['path'], 'blob': item['blob']} for item in uploads['items']])
        unrelated = fixture.change()
        fixture.call('edit', change=unrelated, chunk='unrelated', edit_revision=0,
                     operations=[{'path': 'unrelated.bin', 'blob': fixture.upload(unrelated)}])
        fixture.call('submit', change=unrelated)
        job = call('rebase_begin', 'rebase_begin', change=draft, edit_revision=1, request_id='rebase')
        job = call('rebase_next', 'integration_next', change=draft, edit_revision=1, integration=job['integration'],
                   after='', request_id='rebase-next')
        assert job['complete'] and job['conflicts'] == 0
        call('rebase_finish', 'integration_finish', change=draft, edit_revision=1,
             integration=job['integration'], request_id='rebase-finish')
        shelf = call('shelve', 'shelve', change=draft, edit_revision=2, request_id='shelf')
        target = fixture.change()
        call('move', 'move_files', change=draft, target_change=target, edit_revision=2,
             target_edit_revision=0, paths=[item['path'] for item in uploads['items']], request_id='move')
        assert fixture.call('change_files', change=draft)['files'] == 0
        fixture.call('revert', change=target)
        target = fixture.change()
        job = call('unshelve_begin', 'unshelve_begin', change=target, edit_revision=0,
                   shelf=shelf['code'], request_id='unshelve')
        job = call('unshelve_next', 'integration_next', change=target, edit_revision=0,
                   integration=job['integration'], after='', request_id='unshelve-next')
        assert job['complete'] and job['conflicts'] == 0
        call('unshelve_finish', 'integration_finish', change=target, edit_revision=0,
             integration=job['integration'], request_id='unshelve-finish')
        result = call('submit', 'submit', change=target)
        assert result['files'] == catalog_files + 1
        for i in (0, changed_files - 1):
            entry = fixture.call('read', stream='main', path='%08d.bin' % i)
            assert base64.b64decode(entry['data']) == contents[i]
            assert [v['number'] for v in fixture.call('history', stream='main', path='%08d.bin' % i)['items']] == [2, 1]
        return {'vendor': fixture.store.get_db_resource().get_vendor(), 'catalog_files': catalog_files,
                'changed_files': changed_files, 'distinct_uploaded_payloads': changed_files,
                'payload_bytes': sum(map(len, contents)), 'network_included': False,
                'milliseconds': timings, 'process_peak_mib': peak_mib()}
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--postgres', action='store_true')
    parser.add_argument('--catalog-files', type=int, default=10000)
    parser.add_argument('--changed-files', type=int, default=1000)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    with postgres() if args.postgres else nullcontext('') as config:
        result = benchmark(config, args.catalog_files, args.changed_files)
    output = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(output + '\n', encoding='utf-8')
    print(output)
