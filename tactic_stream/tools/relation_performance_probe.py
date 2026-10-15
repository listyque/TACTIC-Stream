"""Disposable tree/file discovery through authenticated native Python RPC."""
import argparse
from collections import Counter
import cProfile
import hashlib
import json
import logging
import os
from pathlib import Path
import pstats
import sqlite3
import statistics
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
from test_foundation import fixture
from test_schema import relationship_fixture
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api


def prepare(store, count):
    store.initialize(hash_password('private-tree-performance'))
    fixture(store)
    relationship_fixture(store)
    with store.connection(write=True) as db:
        db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) "
                   "VALUES ('contract/leaf','contract/leaf','contract','{project}','leaf','pyasm.search.SObject')")
        xml = db.execute('SELECT "schema" FROM "schema" WHERE code=?', ('one',)).fetchone()[0]
        # Many unrelated connections expose inherited and absent lookup costs.
        edges = ''.join(f'<connect from="unused/type{i}" to="unused/parent{i}" relationship="code"/>'
                        for i in range(500))
        xml = xml.replace('</schema>', edges + '<connect from="contract/leaf" to="contract/child" '
                          'relationship="code" from_col="child_code"/></schema>')
        db.execute('UPDATE "schema" SET "schema"=? WHERE code=?', (xml, 'one'))
        db.executemany("INSERT INTO snapshot(code,search_type,search_code,context,version,snapshot,login) VALUES (?,?,?,?,?,?,'admin')",
                       ((f'SNAP{i}', 'contract/leaf?project=one', f'L{i}', 'publish', -1,
                         f'<snapshot><file file_code="FILE{i}" type="main"/></snapshot>') for i in range(count)))
        db.executemany('INSERT INTO file(code,snapshot_code,search_type,file_name,relative_dir) VALUES (?,?,?,?,?)',
                       ((f'FILE{i}', f'SNAP{i}', 'contract/leaf?project=one', f'file{i}.dat', 'private/tree')
                        for i in range(count)))
    with store.connection('one', write=True) as db:
        db.execute('DELETE FROM entity')
        db.execute('DELETE FROM child')
        db.executemany('INSERT INTO entity(id,code,name) VALUES (?,?,?)',
                       ((i + 1, f'P{i}', f'Parent {i}') for i in range(count)))
        db.executemany('INSERT INTO child(id,code,entity_code) VALUES (?,?,?)',
                       ((i + 1, f'C{i}', f'P{i}') for i in range(count)))
        db.execute('CREATE TABLE leaf (id INTEGER PRIMARY KEY, code text, child_code text, s_status text)')
        db.executemany('INSERT INTO leaf(id,code,child_code) VALUES (?,?,?)',
                       ((i + 1, f'L{i}', f'C{i}') for i in range(count)))


TREE = '''from pyasm.search import Search
from pyasm.biz import ExpressionParser, Snapshot
roots = Search('contract/entity').get_sobjects()
leaves = ExpressionParser().eval('@SOBJECT(contract/child.contract/leaf)', roots)
snapshots = Snapshot.get_by_sobjects(leaves)
files = Snapshot.get_files_dict_by_snapshots(snapshots)
return {'leaves': [item.get_code() for item in leaves],
        'files': {key: [item.get_code() for item in values] for key, values in files.items()}}
'''
GET = '''from pyasm.search import Search
from pyasm.biz import ExpressionParser
return ExpressionParser().eval('@GET(.name)', Search('contract/entity').get_sobjects())
'''
SCHEMA = '''from pyasm.biz import Schema
schema = Schema.get()
return [schema.get_relationship_attrs('contract/inherited', 'contract/entity') for _ in range(1000)]
'''


def measure(store, output, repeats, count):
    api = Api(store)
    auth = dict(ticket=api.get_ticket('admin', 'private-tree-performance'), project='one')
    results = {}
    output.mkdir(parents=True, exist_ok=True)
    for name, body in [('tree_files', TREE), ('get_1000_roots', GET), ('inherited_1000', SCHEMA)]:
        def invoke():
            return api.dispatch('execute_python_script', (auth, '', {'code': body}))['info']
        expected = invoke()
        if name == 'tree_files':
            assert len(expected['leaves']) == len(expected['files']) == count
            assert sum(len(values) for values in expected['files'].values()) == count
        else:
            assert len(expected) == (1000 if name == 'inherited_1000' else count)
        times = []
        for _ in range(repeats):
            start = time.perf_counter()
            result = invoke()
            times.append((time.perf_counter() - start) * 1000)
            assert result == expected, name
        statements = Counter()
        connect = sqlite3.connect
        def traced(*args, **kwargs):
            db = connect(*args, **kwargs)
            db.set_trace_callback(lambda sql: statements.update([sql.lstrip().split(' ', 1)[0].upper()]))
            return db
        with patch.object(sqlite3, 'connect', side_effect=traced):
            assert invoke() == expected
        profiler = cProfile.Profile()
        assert profiler.runcall(invoke) == expected
        with (output / (name + '.profile.txt')).open('w', encoding='utf-8') as stream:
            pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats('cumulative').print_stats(30)
        results[name] = dict(median_ms=statistics.median(times), samples_ms=times,
                            statements=dict(statements),
                            sha256=hashlib.sha256(json.dumps(expected, sort_keys=True).encode()).hexdigest())
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rows', type=int, default=1000)
    parser.add_argument('--repeats', type=int, default=7)
    args = parser.parse_args()
    if args.rows < 1 or args.repeats < 1:
        parser.error('--rows and --repeats must be positive')
    logging.disable(logging.CRITICAL)
    with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            'TACTIC_DATA_DIR': directory, 'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
        store = Store(Path(directory))
        assert store.get_db_resource().get_vendor() == 'Sqlite', 'Only owned SQLite fixtures'
        prepare(store, args.rows)
        results = measure(store, args.output, args.repeats, args.rows)
    args.output.joinpath('results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps({name: {key: value for key, value in result.items() if key != 'samples_ms'}
                      for name, result in results.items()}, indent=2))


if __name__ == '__main__':
    main()
