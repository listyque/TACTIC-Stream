"""Upgrade existing journals without changing rows; use indexes on actual read paths."""
from pathlib import Path
import tempfile
import unittest

from test_foundation import fixture
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tools.engine_index_probe import INDEX_NAMES


READS = (
    ("change_timestamp", "search_type=? AND search_code=?", ('sthpw/task', 'A')),
    ("change_timestamp", "timestamp>? ORDER BY timestamp", ('2000-01-01',)),
    ("change_timestamp", "project_code=? AND timestamp>? ORDER BY timestamp", ('one', '2000-01-01')),
    ("change_timestamp", "search_type=? AND timestamp>? ORDER BY timestamp", ('sthpw/task', '2000-01-01')),
    ("sobject_log", "search_type=? AND search_id=? ORDER BY timestamp DESC,id DESC", ('sthpw/task', 1)),
    ("sobject_log", "search_type=? ORDER BY id DESC", ('config/widget_config?project=one',)),
    ("sobject_log", "transaction_log_id=?", (1,)),
    ("sobject_log", "code=?", ('A',)),
    ("pref_setting", 'login=? AND project_code IS NULL', ('admin',)),
    ("sobject_list", 'search_type=? AND search_code=? ORDER BY code', ('sthpw/task', 'A')),
    ("sobject_list", 'search_type=? AND search_id=? ORDER BY code', ('sthpw/task', 1)),
    ("snapshot", 'search_type=? AND search_code=? AND context=? ORDER BY version DESC', ('sthpw/task', 'A', 'publish')),
    ("snapshot", 'search_type=? AND search_id=? AND context=? ORDER BY version DESC', ('sthpw/task', 1, 'publish')),
    ("file", 'relative_dir=? AND file_name=? ORDER BY code', ('test', 'test.txt')),
    ("connection", 'src_search_type=? AND src_search_id=? ORDER BY code', ('sthpw/task', 1)),
    ("connection", 'dst_search_type=? AND dst_search_id=? ORDER BY code', ('sthpw/task', 1)),
    ("login_in_group", 'login=?', ('admin',)),
)


class JournalIndexes(unittest.TestCase):
    def test_existing_database_upgrade_preserves_rows_and_indexes_read_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('private-index-password'))
            fixture(store)
            added = [index for index in Store._get_upgrade()['indexes']
                     if index['name'].startswith(('change_timestamp_', 'sobject_log_')) or index['name'] in INDEX_NAMES]
            with store.connection(write=True) as db:
                for index in added:
                    db.execute('DROP INDEX "' + index['name'] + '"')
                # Existing duplicate object markers remain readable; no new uniqueness rule.
                db.executemany('INSERT INTO change_timestamp(code,search_type,search_code) VALUES (?,?,?)',
                               [('OLD1', 'sthpw/task', 'A'), ('OLD2', 'sthpw/task', 'A')])
                before = [tuple(row) for row in db.execute('SELECT * FROM change_timestamp ORDER BY id')]
            self.assertTrue(store.upgrade())
            self.assertFalse(store.upgrade())
            with store.connection() as db:
                for table, where, values in READS:
                    plan = ' '.join(row[3] for row in db.execute(
                        'EXPLAIN QUERY PLAN SELECT * FROM ' + table + ' WHERE ' + where + ' LIMIT 80', values))
                    self.assertIn('INDEX', plan, (table, where, plan))
                self.assertEqual([tuple(row) for row in db.execute('SELECT * FROM change_timestamp ORDER BY id')], before)
            with store.connection('one') as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM entity').fetchone()[0], 4)


if __name__ == '__main__':
    unittest.main()
