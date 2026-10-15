"""Native API check-ins in an isolated SQLite project imported from the CG preset.

Mass CG cases keep CG directory naming and use unique basename-derived filenames;
the single CG case also keeps the preset's file naming and latest copy.
Timings exclude input generation and validation; API timing excludes HTTP.
"""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
from statistics import median
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]

from pyasm.common import Environment, Xml
from pyasm.search import Search
from pyasm.search.sql import Sql
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
import mako.template

CHECKIN_SCRIPT = """from pyasm.checkin import FileCheckin
from pyasm.search import Search
import time
parent = Search.get_by_code('cg/shot', 'SH001')
checkin = FileCheckin(parent, paths, file_types=['main'] * len(paths), **options)
started = time.perf_counter()
snapshot = checkin.execute()
return dict(snapshot=snapshot.get_code(), method_seconds=time.perf_counter() - started)
"""

def prepare(store):
    store.initialize(hash_password('private-benchmark-password'))
    api = Api(store)
    token = api.get_ticket('admin', 'private-benchmark-password')
    context = dict(ticket=token, project='admin')
    api.dispatch('execute_cmd', (context, 'tactic.command.ProjectTemplateInstallerCmd',
        dict(project_code='one', project_title='Checkin benchmark', path=str(ROOT.parent / 'cg'), verbose=False)))
    context['project'] = 'one'
    api.dispatch('insert', (context, 'cg/scenes', dict(code='EP001', name='Episode_01')), {'triggers': False})
    api.dispatch('insert', (context, 'cg/shot', dict(code='SH001', name='Shot_01', scenes_code='EP001')), {'triggers': False})
    # Windows test hosts need no symlink privilege for the preset's latest files.
    with request_context(RequestContext(store, 'admin', 'one')):
        api.auth.bind_security('admin', token)
        search = Search('config/prod_setting')
        search.add_filter('key', 'versionless_mode')
        key = search.get_sobject().get_search_key()
    api.dispatch('update', (context, key, {'value': 'copy'}))
    return api, token


def uncached_directory(value):
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path(Environment.get_data_dir()) / path
    return path.resolve().as_posix()


def measure(store, api, token, folder, count, variant):
    folder.mkdir()
    paths = []
    for index in range(count):
        path = folder / ('payload_%04d.abc' % index)
        path.write_bytes(b'1234567890abcdef')
        paths.append(path.as_posix())
    counts = {'resolve': 0, 'compilation': 0, 'xml_parse': 0, 'sql_write': 0}
    resolve, compile_text, read_string = Path.resolve, mako.template._compile_text, Xml.read_string
    do_update = Sql._do_update
    def counted_resolve(path, *args, **kwargs):
        counts['resolve'] += 1
        return resolve(path, *args, **kwargs)
    def counted_compile(*args, **kwargs):
        counts['compilation'] += 1
        return compile_text(*args, **kwargs)
    def counted_xml(xml, *args, **kwargs):
        counts['xml_parse'] += 1
        return read_string(xml, *args, **kwargs)
    def counted_update(sql, query, *args, **kwargs):
        if query:
            counts['sql_write'] += 1
        return do_update(sql, query, *args, **kwargs)
    options = dict(context=folder.name, process=folder.name, mode='copy', source_paths=paths,
                   checkin_type='auto', md5s='ignore')
    if variant != 'cg':
        options.update(checkin_type='strict', file_naming='{basefile}_v{version}.{ext}',
                       do_update_versionless=False)
        if variant == 'core':
            options['dir_naming'] = '{project.code}/audit/{snapshot.context}'
    with ExitStack() as stack:
        stack.enter_context(patch.object(Path, 'resolve', counted_resolve))
        stack.enter_context(patch.object(mako.template, '_compile_text', counted_compile))
        stack.enter_context(patch.object(Xml, 'read_string', counted_xml))
        stack.enter_context(patch.object(Sql, '_do_update', counted_update))
        started = time.perf_counter()
        result = api.dispatch('execute_python_script', (dict(ticket=token, project='one'), '',
            dict(code=CHECKIN_SCRIPT, paths=paths, options=options)))['info']
        seconds = time.perf_counter() - started
    with request_context(RequestContext(store, 'admin', 'one')):
        api.auth.bind_security('admin', token)
        snapshot = Search.get_by_code('sthpw/snapshot', result['snapshot'])
        files = snapshot.get_all_file_objects()
        assert len(files) == count
        destinations = [Path(file.get_lib_path()) for file in files]
        assert len(set(destinations)) == count
        assert snapshot.get_value('context') == folder.name
        assert all(path.read_bytes() == b'1234567890abcdef' for path in destinations)
        assert all(Path(path).read_bytes() == b'1234567890abcdef' for path in paths)
        return dict(seconds=seconds, method_seconds=result['method_seconds'], **counts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', default='current')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--uncached-roots', action='store_true', help='Reproduce the original root lookup for comparison')
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    temporary_root = ROOT / '.test-tmp'
    temporary_root.mkdir(exist_ok=True)
    assert temporary_root.resolve().is_relative_to(ROOT.resolve())
    results = []
    with tempfile.TemporaryDirectory(prefix='checkin-benchmark-', dir=temporary_root) as directory:
        store = Store(Path(directory) / 'data')
        api, token = prepare(store)
        with ExitStack() as stack:
            if args.uncached_roots:
                stack.enter_context(patch.object(Environment, '_directory', staticmethod(uncached_directory)))
            for variant, count in [('cg', 1), ('core', 1), ('core', 100), ('core', 1000), ('cg-dir', 100), ('cg-dir', 1000)]:
                runs = []
                for repeat in range(args.repeats):
                    run = measure(store, api, token, Path(directory) / ('%s_%s_%s' % (variant, count, repeat)), count, variant)
                    runs.append(run)
                    print(json.dumps(dict(label=args.label, variant=variant, count=count, repeat=repeat, **run)), flush=True)
                results.append(dict(variant=variant, count=count, runs=runs,
                                    median={key: median(run[key] for run in runs) for key in runs[0]}))
    report = dict(label=args.label, bytes_per_file=16, database='SQLite', results=results)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
