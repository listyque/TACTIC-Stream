"""Fresh real-byte HTTP benchmark, isolated native fixture, no production data."""
import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import sys
import threading
from time import perf_counter
from unittest.mock import patch


def peak_memory():
    import ctypes
    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('faults', ctypes.c_ulong)] + [(name, ctypes.c_size_t) for name in
            ('peak', 'working', 'paged_peak', 'paged', 'nonpaged_peak', 'nonpaged', 'pagefile', 'pagefile_peak')]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if os.name == 'nt':
        if not ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(-1), ctypes.byref(counters), counters.cb):
            raise OSError('Process memory counters unavailable')
        return round(counters.peak / 1024**2, 2)
    import resource
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1024**2 if sys.platform == 'darwin' else 1024), 2)

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / name) for name in ('src', 'tests')]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_file_transfer import FileTransferTest
from tactic_client_lib.file_transfer import FileTransferClient, digest_file
from tactic_stream.server import file_tasks


def run(files, small_size, large_files, large_size):
    fixture = FileTransferTest('test_http_client_fresh_bytes_upload_download_and_dirty_protection')
    fixture.setUp()
    try:
        source, target = Path(fixture.temp.name) / 'fresh', Path(fixture.temp.name) / 'download'
        source.mkdir()
        started = perf_counter()
        for index in range(files + large_files):
            size = small_size if index < files else large_size
            path = source / ('fresh-%08d.bin' % index)
            with path.open('wb') as output:
                remaining = size
                while remaining:
                    block = os.urandom(min(1024 * 1024, remaining))
                    output.write(block)
                    remaining -= len(block)
        generated = perf_counter() - started
        commands, workers, lock, progress = defaultdict(lambda: [0, 0.0]), defaultdict(lambda: [0, 0.0]), threading.Lock(), {}
        timestamps = {}
        def report(value):
            progress.update(value)
            if value.get('state') == 'collecting' and value.get('total_known') and value.get('files_done') == value.get('files_total') and value.get('bytes_done') == value.get('bytes_total'):
                timestamps.setdefault('uploaded', perf_counter())
        worker_call = file_tasks.call
        def timed_worker(action, **kwargs):
            started = perf_counter()
            try:
                return worker_call(action, **kwargs)
            finally:
                with lock:
                    workers[action][0] += 1
                    workers[action][1] += perf_counter() - started
        with patch.object(file_tasks, 'call', timed_worker), fixture.http(worker=True) as url:
            client = FileTransferClient(url, fixture.token, 'files', progress=report)
            original = client.rpc
            def timed(action, **kwargs):
                start = perf_counter()
                try:
                    return original(action, **kwargs)
                finally:
                    with lock:
                        commands[action][0] += 1
                        commands[action][1] += perf_counter() - start
            client.rpc = timed
            change = fixture.change()
            started = perf_counter()
            upload = client.upload(change, source, Path(fixture.temp.name) / 'outbox.sqlite', submit=True, timeout=600)
            upload_seconds = perf_counter() - started
            completion_seconds = perf_counter() - timestamps['uploaded'] if 'uploaded' in timestamps else None
            upload_peak = peak_memory()
            started = perf_counter()
            download = client.download('work', target)
            download_seconds = perf_counter() - started
            download_peak = peak_memory()
        verified = 0
        for path in source.iterdir():
            if digest_file(path) != digest_file(target / path.name):
                raise AssertionError('Roundtrip bytes differ')
            verified += 1
        return {'database': 'SQLite', 'transport': 'real loopback HTTP', 'fresh_random_bytes': True,
            'files': verified, 'bytes': files * small_size + large_files * large_size,
            'small_files': files, 'small_size': small_size, 'large_files': large_files, 'large_size': large_size,
            'generation_seconds': round(generated, 3), 'upload_submit_seconds': round(upload_seconds, 3),
            'already_uploaded_to_confirmed_seconds': round(completion_seconds, 3) if completion_seconds is not None else None,
            'download_have_seconds': round(download_seconds, 3),
            'upload_peak_process_mib': upload_peak, 'download_peak_process_mib': download_peak,
            'upload_state': upload['state'], 'download_state': download['state'],
            'commands': {key: {'count': value[0], 'aggregate_seconds': round(value[1], 3)} for key, value in commands.items()},
            'worker_commands': {key: {'count': value[0], 'aggregate_seconds': round(value[1], 3)} for key, value in workers.items()}}
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--files', type=int, default=1000)
    parser.add_argument('--small-size', type=int, default=4096)
    parser.add_argument('--large-files', type=int, default=0)
    parser.add_argument('--large-size', type=int, default=64 * 1024 * 1024)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if min(args.files, args.small_size, args.large_files, args.large_size) < 0:
        parser.error('Counts and sizes must be nonnegative')
    result = run(args.files, args.small_size, args.large_files, args.large_size)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + '\n', encoding='utf-8')
    print(rendered)
