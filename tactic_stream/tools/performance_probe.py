"""Owned SQLite workload; timings exclude profiling and memory instrumentation."""
import argparse
import ast
from collections import Counter
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, InterpreterPoolExecutor
import ctypes
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import platform
import pstats
import sqlite3
import shutil
import statistics
import sys
import sysconfig
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), os.environ.get('TACTIC_PERF_SOURCE', str(ROOT / 'src')), str(ROOT / 'tests')]
# Reuse the test's fixture body without its sys.path mutation: an A/B run must
# import the explicitly selected source tree, including in child processes.
fixture_node = next(node for node in ast.parse((ROOT / 'tests/test_foundation.py').read_text(encoding='utf-8')).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'fixture')
exec(compile(ast.Module(body=[fixture_node], type_ignores=[]), str(ROOT / 'tests/test_foundation.py'), 'exec'))
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api


def rss_kib(pid=None):
    if os.name == 'nt':
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
                'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage')]
        counts = Counters()
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        handle = kernel.OpenProcess(0x410, False, pid) if pid else kernel.GetCurrentProcess()
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counts), ctypes.sizeof(counts)):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            if pid:
                kernel.CloseHandle(handle)
        return {'rss_kib': counts.WorkingSetSize / 1024, 'peak_rss_kib': counts.PeakWorkingSetSize / 1024}
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {'peak_rss_kib': peak / 1024 if sys.platform == 'darwin' else peak}


def environment():
    packages = {}
    for name in ('fastapi', 'uvicorn', 'starlette', 'anyio', 'pydantic', 'pydantic-core', 'python-dateutil', 'Pillow',
                 'Mako', 'psycopg', 'psycopg-binary', 'numpy', 'numba', 'Cython', 'nuitka'):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {'platform': platform.platform(), 'processor': platform.processor(),
            'python': sys.version, 'executable': sys.executable,
            'loaded_api_source': sys.modules['tactic_stream.server.api'].__file__,
            'gil_enabled': sys._is_gil_enabled(), 'free_threaded_build': sysconfig.get_config_var('Py_GIL_DISABLED'),
            'jit_available': sys._jit.is_available(), 'jit_enabled': sys._jit.is_enabled(),
            'sqlite': sqlite3.sqlite_version, 'optimization_level': sys.flags.optimize,
            'build_config': {name: sysconfig.get_config_var(name) for name in
                             ('CONFIG_ARGS', 'PY_CFLAGS', 'PY_LDFLAGS', 'Py_DEBUG')},
            'dependencies': packages, 'memory': rss_kib()}


def prepare(directory, rows):
    store = Store(directory)
    store.initialize(hash_password('private-performance-password'))
    fixture(store)
    # A real server requires its explicit config to exist. Keep this fixture's
    # security/database defaults equal to the prior in-process empty config.
    config = store.data_dir / 'config/tactic-conf.xml'
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('<config version="2"/>', encoding='utf-8')
    with closing(sqlite3.connect(store.database_path('one'))) as db, db:
        db.execute('DELETE FROM entity')
        db.execute('ALTER TABLE entity ADD COLUMN timestamp timestamp')
        db.execute('ALTER TABLE entity ADD COLUMN description text')
        db.executemany('INSERT INTO entity VALUES (?,?,?,?,?,?,?)', (
            (i, 'ASSET%06d' % i, 'Объект %06d' % i, i % 1000,
             'retired' if i % 20 == 0 else None, '2026-10-06 12:00:00', 'asset details ' * 20)
            for i in range(1, rows + 1)))
    return store


def workload(store):
    api = Api(store)
    ticket = {'ticket': api.get_ticket('admin', 'private-performance-password'), 'project': 'one'}
    return api, {
        'query_10': ('query', (ticket, 'contract/entity', [], None, ['id asc'], False, 10, 0)),
        'query_1000': ('query', (ticket, 'contract/entity', [], None, ['id asc'], False, 1000, 0)),
        'query_all': ('query', (ticket, 'contract/entity', [], None, ['id asc'], True)),
        'filter_sort_50': ('query', (ticket, 'contract/entity', [['amount', '>=', 900]],
                                   ['id', 'code', 'amount'], ['amount desc', 'id asc'], False, 50, 0)),
        'eval_names': ('eval', (ticket, '@GET(contract/entity.name)')),
    }


def executor_query(task):
    directory, ticket, log_dir = task
    logger = logging.getLogger('tactic_stream.server.api')
    logger.setLevel(logging.INFO)
    logger.propagate = False
    # FileHandler already serializes complete writes between threads.
    if not logger.handlers:
        logger.addHandler(logging.FileHandler(Path(log_dir) / ('executor-%s.log' % os.getpid()), encoding='utf-8'))
    value = Api(Store(Path(directory))).dispatch('query',
        ({'ticket': ticket, 'project': 'one'}, 'contract/entity', [], None, ['id asc'], True))
    return hashlib.sha256(value.encode()).hexdigest(), os.getpid(), rss_kib(), value


def measure_executors(store, directory, repeats, workers, tasks):
    ticket = Api(store).get_ticket('admin', 'private-performance-password')
    work = [(str(store.data_dir), ticket, str(directory))] * tasks
    report = {}
    for name, executor_class in [('serial', None), ('threads', ThreadPoolExecutor),
                                 ('processes', ProcessPoolExecutor), ('interpreters', InterpreterPoolExecutor)]:
        executor = None
        try:
            started = time.perf_counter()
            if executor_class:
                executor = executor_class(max_workers=workers)
            # This installed interpreter executor accepts shareable builtins,
            # but not Python functions. Include its explicit serialization cost.
            function, inputs = executor_query, work
            if name == 'interpreters':
                function = eval
                inputs = ["(__import__('sys').path.insert(0, %r), __import__('json').dumps("
                          "__import__('tools.performance_probe', fromlist=['executor_query']).executor_query(%r)))[1]"
                          % (str(ROOT), item) for item in work]
            results = [json.loads(value) if isinstance(value, str) else value
                       for value in (executor.map(function, inputs) if executor else map(function, inputs))]
            cold = (time.perf_counter() - started) * 1000
            expected = results[0][0]
            timings = []
            for _ in range(repeats):
                started = time.perf_counter()
                results = [json.loads(value) if isinstance(value, str) else value
                           for value in (executor.map(function, inputs) if executor else map(function, inputs))]
                timings.append((time.perf_counter() - started) * 1000)
                assert all(item[0] == expected for item in results)
            report[name] = {'cold_batch_ms': cold, 'median_batch_ms': statistics.median(timings),
                            'min_ms': min(timings), 'max_ms': max(timings),
                            'worker_memory': {str(pid): memory for _, pid, memory, _ in results},
                            'parent_memory': rss_kib(), 'results_match': True}
        except Exception as exc:
            report[name] = {'error': '%s: %s' % (type(exc).__name__, exc)}
        finally:
            if executor:
                executor.shutdown(wait=True, cancel_futures=True)
    return report


def measure_writes(store, directory, repeats, profile=False):
    # Every write run starts from a separate owned copy, never a working project.
    with tempfile.TemporaryDirectory(prefix='tactic-write-performance-') as temporary:
        data = Path(temporary) / 'data'
        shutil.copytree(store.data_dir, data)
        api = Api(Store(data))
        ticket = {'ticket': api.get_ticket('admin', 'private-performance-password'), 'project': 'one'}
        logger = logging.getLogger('tactic_stream.server.api')
        logger.setLevel(logging.INFO)
        logger.propagate = False
        handler = logging.FileHandler(directory / 'writes.log', encoding='utf-8')
        logger.addHandler(handler)
        samples = []
        try:
            for index in range(repeats + 1):
                rows = [{'note': 'audit-%s-%s' % (index, item), 'login': 'admin',
                         'search_type': 'contract/entity?project=one', 'search_code': 'ASSET000001'}
                        for item in range(100)]
                started = time.perf_counter()
                result = api.dispatch('insert_multiple', (ticket, 'sthpw/note', rows))
                elapsed = (time.perf_counter() - started) * 1000
                assert len(result) == 100
                assert [row['note'] for row in result] == [row['note'] for row in rows]
                if index:
                    samples.append(elapsed)
                else:
                    cold = elapsed
            with closing(sqlite3.connect(api.store.database_path('sthpw'))) as db:
                assert db.execute("SELECT COUNT(*) FROM note WHERE note LIKE 'audit-%'").fetchone()[0] == (repeats + 1) * 100
            if profile:
                import cProfile
                profiler = cProfile.Profile()
                profiler.runcall(api.dispatch, 'insert_multiple', (ticket, 'sthpw/note', rows))
                profiler.dump_stats(directory / 'insert_100_notes.prof')
                with (directory / 'insert_100_notes.profile.txt').open('w', encoding='utf-8') as output:
                    pstats.Stats(profiler, stream=output).strip_dirs().sort_stats('cumulative').print_stats(30)
            return {'insert_100_notes': {'cold_ms': cold, 'median_ms': statistics.median(samples),
                    'min_ms': min(samples), 'max_ms': max(samples), 'samples_ms': samples,
                    'memory_after': rss_kib(), 'rows_per_call': 100, 'persisted_rows_checked': True}}
        finally:
            logger.removeHandler(handler)
            handler.close()


def measure(store, repeats, profile, directory, json_pipeline=False, index_filter=False):
    import cProfile
    import tracemalloc
    api, cases = workload(store)
    if index_filter:
        with closing(sqlite3.connect(store.database_path('one'))) as db, db:
            db.execute('CREATE INDEX performance_amount_sort ON entity(amount DESC, id ASC)')
        cases = {'filter_sort_50': cases['filter_sort_50']}
    if json_pipeline:
        from starlette.responses import JSONResponse
        api.protocol = 'json'
        cases = {name: case for name, case in cases.items() if case[0] == 'query'}
    def invoke(method, args):
        value = api.dispatch(method, args)
        if json_pipeline:
            value = ast.literal_eval(value) if isinstance(value, str) else value
            return JSONResponse({'result': value}).body.decode('utf-8')
        return value
    logging.getLogger('tactic_stream.server.api').setLevel(logging.INFO)
    handler = logging.FileHandler(directory / 'requests.log', encoding='utf-8')
    logger = logging.getLogger('tactic_stream.server.api')
    logger.addHandler(handler)
    logger.propagate = False
    report = {}
    try:
        for name, (method, args) in cases.items():
            started = time.perf_counter()
            first = invoke(method, args)
            cold = (time.perf_counter() - started) * 1000
            expected = hashlib.sha256(first.encode()).hexdigest()
            timings = []
            for _ in range(repeats):
                started = time.perf_counter()
                value = invoke(method, args)
                timings.append((time.perf_counter() - started) * 1000)
                assert hashlib.sha256(value.encode()).hexdigest() == expected
            before = rss_kib()
            tracemalloc.start()
            value = invoke(method, args)
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            report[name] = {'cold_ms': cold, 'median_ms': statistics.median(timings),
                            'min_ms': min(timings), 'max_ms': max(timings),
                            'p90_ms': sorted(timings)[int((len(timings) - 1) * .9)],
                            'samples_ms': timings, 'python_peak_kib': peak / 1024,
                            'python_retained_kib': current / 1024, 'memory_before': before,
                            'memory_after': rss_kib(), 'result_bytes': len(value.encode()),
                            'result_count': len(json.loads(value)['result'] if json_pipeline else ast.literal_eval(value)),
                            'sha256': expected}
            # Count statements separately; SQL text and credentials stay out
            # of the report and instrumentation never affects speed samples.
            from unittest.mock import patch
            counts = Counter()
            connect = sqlite3.connect
            def traced_connect(*args, **kwargs):
                db = connect(*args, **kwargs)
                db.set_trace_callback(lambda statement: counts.update([statement.lstrip().split(' ', 1)[0].upper()]))
                return db
            with patch.object(sqlite3, 'connect', side_effect=traced_connect):
                invoke(method, args)
            report[name]['sql_statement_counts'] = dict(counts)
            if profile:
                profiler = cProfile.Profile()
                profiler.runcall(invoke, method, args)
                profiler.dump_stats(directory / (name + '.prof'))
                with (directory / (name + '.profile.txt')).open('w', encoding='utf-8') as output:
                    pstats.Stats(profiler, stream=output).strip_dirs().sort_stats('cumulative').print_stats(35)
                    pstats.Stats(profiler, stream=output).strip_dirs().sort_stats('tottime').print_stats(20)
    finally:
        logger.removeHandler(handler)
        handler.close()
        if index_filter:
            with closing(sqlite3.connect(store.database_path('one'))) as db, db:
                db.execute('DROP INDEX performance_amount_sort')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rows', type=int, default=10000)
    parser.add_argument('--repeats', type=int, default=21)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--data-dir', type=Path, help='Reuse only a database prepared by this probe')
    parser.add_argument('--prepare-data', type=Path, help='Prepare a new owned fixture and exit')
    parser.add_argument('--executors', action='store_true', help='Compare batch throughput and executor startup')
    parser.add_argument('--json-pipeline', action='store_true', help='Include the admin query conversion and JSON rendering')
    parser.add_argument('--index-filter', action='store_true', help='Temporarily index the owned fixture for filter/sort')
    parser.add_argument('--writes', action='store_true', help='Measure original batch insert on a disposable copy')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--tasks', type=int, default=16)
    args = parser.parse_args()
    if args.executors and (args.writes or args.json_pipeline or args.index_filter) or args.writes and (args.json_pipeline or args.index_filter):
        parser.error('Choose one measurement mode')
    if args.rows < 1000 or args.repeats < 3:
        parser.error('Require at least 1000 rows and 3 repeats')
    args.output.mkdir(parents=True, exist_ok=True)
    if args.prepare_data:
        if args.prepare_data.exists():
            parser.error('Refuse an existing fixture directory')
        prepare(args.prepare_data, args.rows)
        (args.prepare_data / 'performance-probe.json').write_text(json.dumps({'rows': args.rows}))
        return
    if args.data_dir:
        if not (args.data_dir / 'performance-probe.json').is_file():
            parser.error('Data directory was not prepared by this probe')
        rows = json.loads((args.data_dir / 'performance-probe.json').read_text())['rows']
        store = Store(args.data_dir)
        result = (measure_writes(store, args.output, args.repeats, args.profile) if args.writes else
                  measure_executors(store, args.output, args.repeats, args.workers, args.tasks)
                  if args.executors else measure(store, args.repeats, args.profile, args.output, args.json_pipeline, args.index_filter))
    else:
        rows = args.rows
        with tempfile.TemporaryDirectory(prefix='tactic-performance-') as directory:
            store = prepare(Path(directory), rows)
            result = (measure_writes(store, args.output, args.repeats, args.profile) if args.writes else
                      measure_executors(store, args.output, args.repeats, args.workers, args.tasks)
                      if args.executors else measure(store, args.repeats, args.profile, args.output, args.json_pipeline, args.index_filter))
    report = {'environment': environment(), 'rows': rows, 'repeats': args.repeats,
              'timing': 'Full native dispatch%s, fresh authentication, INFO file log; no profiler/tracemalloc' %
                        (' plus admin JSON conversion/render' if args.json_pipeline else ''),
              'cold_scope': 'First call per scenario in this process; excludes fixture and interpreter startup',
              'scenarios': result, 'executors': args.executors, 'workers': args.workers, 'tasks': args.tasks,
              'index_filter': args.index_filter}
    (args.output / 'results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(result if args.executors or args.writes else {name: {key: round(value[key], 3)
        for key in ('cold_ms', 'median_ms', 'min_ms', 'max_ms', 'python_peak_kib')}
        for name, value in result.items()}, indent=2))


if __name__ == '__main__':
    main()
