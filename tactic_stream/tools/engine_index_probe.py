"""Compare hot native lookup shapes and index write cost on private SQLite data."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
from time import perf_counter
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from pyasm.common import Config
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password


INDEX_NAMES = {
    'pref_setting_scope_idx', 'sobject_list_parent_code_idx', 'sobject_list_parent_id_idx',
    'snapshot_parent_code_idx', 'snapshot_parent_id_idx', 'file_path_idx',
    'connection_src_idx', 'connection_dst_idx', 'login_in_group_login_idx',
}
TYPE = 'contract/entity?project=one'


def batches(start, count):
    items = range(start, start + count)
    return (
        ('pref_setting', 'login,project_code,"key",value',
         [(f'bench_{i // 5}', None, f'key_{i % 5}', 'benchmark') for i in items]),
        ('sobject_list', 'code,search_type,search_code,search_id',
         [(f'LIST{i:08d}', TYPE, f'OBJ{i}', i + 1) for i in items]),
        ('snapshot', 'code,search_type,search_code,search_id,context,version,revision,snapshot,login',
         [(f'SNAP{i:08d}', TYPE, f'OBJ{i // 10}', i // 10 + 1, 'publish', i % 10 + 1, 0, '<snapshot/>', 'admin') for i in items]),
        ('file', 'code,relative_dir,file_name,search_type',
         [(f'FILE{i:08d}', f'group_{i // 10}', f'payload_{i % 10}.bin', TYPE) for i in items]),
        ('connection', 'code,src_search_type,src_search_id,dst_search_type,dst_search_id,context',
         [(f'LINK{i:08d}', TYPE, i + 1, TYPE, i + 2, 'related') for i in items]),
        ('login_in_group', 'code,login,login_group',
         [(f'GROUP{i:08d}', f'bench_{i}', 'benchmark') for i in items]),
    )


def insert(db, groups):
    for table, columns, values in groups:
        db.executemany(f'INSERT INTO {table} ({columns}) VALUES ({",".join("?" for _ in values[0])})', values)


def compare(store, rows, repeats):
    indexes = [index for index in Store._get_upgrade()['indexes'] if index['name'] in INDEX_NAMES]
    assert len(indexes) == len(INDEX_NAMES)
    target = rows - 1
    queries = {
        'preferences': ('SELECT * FROM pref_setting WHERE login=? AND project_code IS NULL', (f'bench_{target // 5}',)),
        'global_search_code': ('SELECT * FROM sobject_list WHERE search_type=? AND search_code=? ORDER BY code', (TYPE, f'OBJ{target}')),
        'global_search_id': ('SELECT * FROM sobject_list WHERE search_type=? AND search_id=? ORDER BY code', (TYPE, target + 1)),
        'snapshot_code': ('SELECT * FROM snapshot WHERE search_type=? AND search_code=? AND context=? AND level_type IS NULL AND level_id IS NULL AND revision=0 ORDER BY version DESC,revision DESC,timestamp DESC LIMIT 1', (TYPE, f'OBJ{target // 10}', 'publish')),
        'snapshot_id': ('SELECT * FROM snapshot WHERE search_type=? AND search_id=? AND context=? AND level_type IS NULL AND level_id IS NULL AND revision=0 ORDER BY version DESC,revision DESC,timestamp DESC LIMIT 1', (TYPE, target // 10 + 1, 'publish')),
        'file_path': ('SELECT * FROM file WHERE relative_dir=? AND file_name=? ORDER BY code LIMIT 1', (f'group_{target // 10}', f'payload_{target % 10}.bin')),
        'connections_out': ('SELECT * FROM connection WHERE src_search_type=? AND src_search_id=? ORDER BY code', (TYPE, target + 1)),
        'connections_in': ('SELECT * FROM connection WHERE dst_search_type=? AND dst_search_id=? ORDER BY code', (TYPE, target + 2)),
        'group_membership': ('SELECT * FROM login_in_group WHERE login=?', (f'bench_{target}',)),
    }
    report = {'rows_per_table': rows, 'repeats': repeats, 'lookups': {}, 'write_batch_1000_per_table_ms': {}}
    extra = batches(rows, 1000)
    with store.connection(write=True) as db:
        for index in indexes:
            db.execute('DROP INDEX "' + index['name'] + '"')
        insert(db, batches(0, rows))
        db.commit()
        for stage in ('before', 'after'):
            if stage == 'after':
                for index in indexes:
                    db.execute(index['sql'])
            for name, (query, parameters) in queries.items():
                digest = sha256(repr([tuple(row) for row in db.execute(query, parameters)]).encode()).hexdigest()
                result = report['lookups'].setdefault(name, {'result_hash': digest})
                assert digest == result['result_hash'], name
                plan = [row[3] for row in db.execute('EXPLAIN QUERY PLAN ' + query, parameters)]
                samples = []
                for _ in range(repeats):
                    started = perf_counter()
                    db.execute(query, parameters).fetchall()
                    samples.append((perf_counter() - started) * 1000)
                result[stage + '_ms'] = statistics.median(samples)
                result[stage + '_plan'] = plan
                if stage == 'after':
                    assert any('SEARCH' in step and 'INDEX' in step for step in plan), name
                    result['results_match'] = True
            write_samples = []
            for _ in range(5):
                db.execute('BEGIN')
                started = perf_counter()
                insert(db, extra)
                write_samples.append((perf_counter() - started) * 1000)
                db.rollback()
            report['write_batch_1000_per_table_ms'][stage] = statistics.median(write_samples)
        for result in report['lookups'].values():
            result['speedup'] = result['before_ms'] / result['after_ms']
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rows', type=int, default=50000)
    parser.add_argument('--repeats', type=int, default=21)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.rows < 1000 or args.repeats < 3:
        parser.error('Require at least 1000 rows and 3 repeats')
    with tempfile.TemporaryDirectory(prefix='engine-index-probe-') as directory, patch.dict(os.environ, {
            'TACTIC_DATA_DIR': directory, 'TACTIC_CONFIG_PATH': '', 'TACTIC_TMP_CONFIG_PATH': ''}):
        Config.reload_config()
        store = Store(Path(directory))
        assert store.get_db_resource().get_vendor() == 'Sqlite'
        store.initialize(hash_password('private-probe-password'))
        report = compare(store, args.rows, args.repeats)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({name: {key: round(value[key], 4) for key in ('before_ms', 'after_ms', 'speedup')}
                      for name, value in report['lookups'].items()}, indent=2))
    print('Write batch ms:', report['write_batch_1000_per_table_ms'])


if __name__ == '__main__':
    main()
