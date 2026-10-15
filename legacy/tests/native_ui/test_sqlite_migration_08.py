"""Regression tests for reported 0.6 upgrade failures, using real SQLite."""
from contextlib import closing
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/local')]
from tactic.core.sqlite_upgrade import SQLiteUpgrade,MigrationError,split_sql,create_parts,prepare_config_schema
import managed_sqlite as local
from local_lock import local_lock
from managed_seed_08 import create_seed,licence_isolated_worker

class DialectTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.addCleanup(self.db.close)
        self.a=SQLiteUpgrade(self.db,recovery=True)
    def run_sql(self,sql):return self.a.execute(sql)
    def schema(self,name):return self.db.execute('SELECT sql FROM sqlite_master WHERE name=?',(name,)).fetchone()[0]
    def test_split_literals_comments(self):
        self.assertEqual(len(split_sql("CREATE TABLE t(x text DEFAULT 'a;b,--c', y text); -- x;\nINSERT INTO t VALUES('it''s;ok', '/*;*/');")),2)
    def test_unclosed_sql_rejected(self):
        for text in ["INSERT INTO t VALUES('x)",'SELECT (1','/* no end']:
            with self.subTest(text=text),self.assertRaises(MigrationError):split_sql(text)
    def test_literal_now_and_serial_not_rewritten(self):
        self.run_sql("CREATE TABLE t(id serial PRIMARY KEY, x text DEFAULT 'now() serial PRIMARY KEY')")
        self.db.execute('INSERT INTO t DEFAULT VALUES')
        self.assertEqual(self.db.execute('SELECT x FROM t').fetchone()[0],'now() serial PRIMARY KEY')
    def test_repeated_add_preserves_data(self):
        self.run_sql('CREATE TABLE t(code text)');self.db.execute("INSERT INTO t VALUES('custom')")
        self.run_sql('ALTER TABLE t ADD COLUMN code VARCHAR(256)')
        self.assertEqual(self.db.execute('SELECT code FROM t').fetchone()[0],'custom')
    def test_btree_index_and_repeat(self):
        self.run_sql('CREATE TABLE t(a TEXT,b TEXT); CREATE INDEX i ON t USING btree (a,b)')
        self.run_sql('CREATE INDEX i ON t(a,b)')
        self.assertEqual(self.a.journal[-1]['status'],'already_present')
    def test_different_existing_index_rejected(self):
        self.run_sql('CREATE TABLE t(a TEXT,b TEXT); CREATE INDEX i ON t(a)')
        with self.assertRaises(MigrationError):self.run_sql('CREATE INDEX i ON t(b)')
    def test_partial_index_not_misreported_as_full_constraint(self):
        self.run_sql('CREATE TABLE t(a text)')
        self.db.execute('CREATE UNIQUE INDEX i ON t(a) WHERE a IS NOT NULL')
        with self.assertRaises(MigrationError):self.run_sql('CREATE UNIQUE INDEX i ON t(a)')
    def test_different_collation_index_refused(self):
        self.run_sql('CREATE TABLE t(a text)')
        self.db.execute('CREATE UNIQUE INDEX i ON t(a COLLATE NOCASE)')
        with self.assertRaises(MigrationError):self.run_sql('CREATE UNIQUE INDEX i ON t(a)')
    def test_unique_constraint_becomes_enforced_index(self):
        self.run_sql('CREATE TABLE t(a text); ALTER TABLE t ADD CONSTRAINT uq UNIQUE(a)')
        self.db.execute("INSERT INTO t VALUES('a')")
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("INSERT INTO t VALUES('a')")
    def test_duplicate_unique_not_silenced(self):
        self.run_sql("CREATE TABLE t(a text);INSERT INTO t VALUES('a');INSERT INTO t VALUES('a')")
        with self.assertRaises(MigrationError):self.run_sql('ALTER TABLE t ADD CONSTRAINT uq UNIQUE(a)')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM t').fetchone()[0],2)
    def test_named_constraint_removed_not_rows(self):
        self.run_sql('CREATE TABLE t(id integer primary key,a text, CONSTRAINT uq UNIQUE(a))')
        self.db.execute("INSERT INTO t VALUES(7,'a')")
        self.run_sql('ALTER TABLE t DROP CONSTRAINT uq')
        self.db.execute("INSERT INTO t VALUES(8,'a')")
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM t').fetchone()[0],2)
    def test_drop_absent_constraint(self):
        self.run_sql('CREATE TABLE t(a text); ALTER TABLE t DROP CONSTRAINT gone CASCADE')
        self.assertEqual(self.a.journal[-1]['status'],'already_absent')
    def test_inline_named_constraint_fail_closed(self):
        self.run_sql('CREATE TABLE t(a text CONSTRAINT "uq" UNIQUE)')
        with self.assertRaises(MigrationError):self.run_sql('ALTER TABLE t DROP CONSTRAINT "uq"')
    def test_drop_not_null_does_not_edit_literal(self):
        self.run_sql("CREATE TABLE t(id INTEGER PRIMARY KEY, x text NOT NULL DEFAULT 'NOT NULL now()')")
        self.db.execute("INSERT INTO t(id) VALUES(40)")
        self.run_sql('ALTER TABLE t ALTER COLUMN x DROP NOT NULL')
        self.assertIn("'NOT NULL now()'",self.schema('t'))
        self.db.execute('INSERT INTO t(x) VALUES(NULL)')
        self.assertEqual(self.db.execute('SELECT x FROM t WHERE id=40').fetchone()[0],'NOT NULL now()')
    def test_type_change_retains_indices_triggers_rowid_sequence(self):
        self.run_sql('CREATE TABLE t(id INTEGER PRIMARY KEY AUTOINCREMENT,x varchar(20));CREATE INDEX ix ON t(x)')
        self.db.execute('CREATE TABLE audit(x text)')
        self.db.execute('CREATE TRIGGER tr AFTER INSERT ON t BEGIN INSERT INTO audit VALUES(new.x);END')
        self.db.execute("INSERT INTO t VALUES(100,'first')");self.db.execute('DELETE FROM t');self.db.execute("INSERT INTO t(id,x) VALUES(9,'stable')")
        self.run_sql('ALTER TABLE t ALTER COLUMN x TYPE text')
        self.assertEqual(self.db.execute('SELECT id,x FROM t').fetchall(),[(9,'stable')])
        self.db.execute("INSERT INTO t(x) VALUES('next')")
        self.assertEqual(self.db.execute("SELECT id FROM t WHERE x='next'").fetchone()[0],101)
        self.assertIsNotNone(self.db.execute("SELECT 1 FROM sqlite_master WHERE name='ix'").fetchone())
        self.assertEqual(self.db.execute('SELECT x FROM audit').fetchall(),[('first',),('stable',),('next',)])
    def test_type_change_preserves_hidden_rowid(self):
        self.run_sql('CREATE TABLE t(x varchar(10))');self.db.execute("INSERT INTO t(rowid,x) VALUES(129,'text')")
        self.run_sql('ALTER TABLE t ALTER COLUMN x TYPE text')
        self.assertEqual(self.db.execute('SELECT rowid,x FROM t').fetchall(),[(129,'text')])
    def test_value_coercion_rejected_atomic_rebuild(self):
        self.run_sql("CREATE TABLE t(x text);INSERT INTO t VALUES('001')")
        before=self.schema('t')
        with self.assertRaises(MigrationError):self.run_sql('ALTER TABLE t ALTER COLUMN x TYPE integer')
        self.assertEqual(self.schema('t'),before)
        self.assertEqual(self.db.execute('SELECT typeof(x),x FROM t').fetchone(),('text','001'))
        self.assertFalse(self.db.execute("SELECT name FROM sqlite_master WHERE name LIKE '_native_migrate_%'").fetchall())
    def test_nonempty_obsolete_table_not_deleted(self):
        self.run_sql("CREATE TABLE translation(x TEXT);INSERT INTO translation VALUES('keep')")
        with self.assertRaises(MigrationError):self.run_sql('DROP TABLE translation')
    def test_missing_table_not_ignored(self):
        with self.assertRaises(MigrationError):self.run_sql('ALTER TABLE missing ADD code TEXT')
    def test_custom_view_rebuild_refused(self):
        self.run_sql('CREATE TABLE t(x text NOT NULL)');self.db.execute('CREATE VIEW v AS SELECT x FROM t')
        with self.assertRaises(MigrationError):self.run_sql('ALTER TABLE t ALTER COLUMN x DROP NOT NULL')
    def test_generated_column_refused(self):
        self.db.execute('CREATE TABLE t(x TEXT NOT NULL,y AS (x))')
        with self.assertRaises(MigrationError):self.run_sql('ALTER TABLE t ALTER COLUMN x DROP NOT NULL')
    def test_old_checkin_field_not_recreated(self):
        self.run_sql("CREATE TABLE naming(checkin_type TEXT);INSERT INTO naming VALUES('sequence')")
        self.run_sql('ALTER TABLE naming ADD checkin_mode TEXT;UPDATE naming SET checkin_type=checkin_mode;ALTER TABLE naming DROP COLUMN checkin_mode')
        self.assertEqual(self.db.execute('SELECT checkin_type FROM naming').fetchone()[0],'sequence')
    def test_conflicting_checkin_modes_not_overwritten(self):
        self.run_sql("CREATE TABLE naming(checkin_mode TEXT,checkin_type TEXT);INSERT INTO naming VALUES('a','b')")
        with self.assertRaises(MigrationError):self.run_sql('UPDATE naming SET checkin_type=checkin_mode')
    def test_identity_display_backfills_preserve_custom(self):
        self.run_sql("CREATE TABLE login(first_name TEXT,last_name TEXT,display_name TEXT);INSERT INTO login VALUES('First','Last','Custom')")
        self.run_sql("UPDATE login SET display_name = last_name || ', ' || first_name")
        self.assertEqual(self.db.execute('SELECT display_name FROM login').fetchone()[0],'Custom')
    def test_natural_key_registry_duplicate_not_new_storage(self):
        self.run_sql("CREATE TABLE search_object(search_type TEXT UNIQUE,table_name TEXT);INSERT INTO search_object VALUES('custom/type','my_table')")
        self.run_sql("INSERT INTO search_object(search_type,table_name) VALUES('custom/type','wrong_table')")
        self.assertEqual(self.db.execute('SELECT table_name FROM search_object').fetchone()[0],'my_table')
    def test_non_registry_duplicate_is_failure(self):
        self.run_sql("CREATE TABLE task(code TEXT UNIQUE);INSERT INTO task VALUES('T1')")
        with self.assertRaises(MigrationError):self.run_sql("INSERT INTO task VALUES('T1')")
    def test_registry_config_alias_retains_single_store(self):
        self.db.execute('CREATE TABLE widget_config(id integer primary key,config text)')
        self.db.execute("INSERT INTO widget_config VALUES(8,'<config>original</config>')")
        aliases=prepare_config_schema(self.db,'CREATE TABLE spt_widget_config(id integer primary key,config text,priority integer);',{'config/widget_config':'widget_config'})
        self.assertEqual(aliases['spt_widget_config'],'widget_config')
        self.assertFalse(self.a.exists('spt_widget_config'))
        self.assertEqual(self.db.execute('SELECT id,config FROM widget_config').fetchall(),[(8,'<config>original</config>')])
    def test_alternate_config_storage_not_silently_abandoned(self):
        self.db.executescript("CREATE TABLE widget_config(id integer);CREATE TABLE spt_widget_config(id integer);INSERT INTO spt_widget_config VALUES(1);")
        with self.assertRaises(MigrationError):prepare_config_schema(self.db,'CREATE TABLE spt_widget_config(id integer);',{'config/widget_config':'widget_config'})
    def test_unknown_sql_refused(self):
        with self.assertRaises(MigrationError):self.run_sql('VACUUM')

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.data=Path(self.temp.name)/'local';self.config=create_seed(self.data)
        self.before={p.name:local.digest(p) for p in (self.data/'db').glob('*.db')}
    def fake_worker(self,root,stage,log):
        # Explicit unit-test collaborator, NOT migration correctness evidence.
        with closing(sqlite3.connect(stage/'db/sthpw.db')) as c:c.execute('CREATE TABLE publication_test(x text)');c.commit()
        report={'passed':True,'target':'5.0.0.a02','completed':[],'statements':[]}
        (stage/'upgrade-report.json').write_text(json.dumps(report));return 0
    def assert_original(self):
        self.assertEqual({p.name:local.digest(p) for p in (self.data/'db').glob('*.db')},self.before)
    def test_failed_worker_never_publishes(self):
        def fail(root,stage,log):self.fake_worker(root,stage,log);return 1
        with self.assertRaises(RuntimeError):local.perform_upgrade(ROOT,self.data,self.config,worker=fail)
        self.assert_original();self.assertEqual(json.loads((self.data/'local-install.json').read_text())['state'],'seed-requires-upgrade')
    def test_missing_report_never_publishes(self):
        with self.assertRaises(RuntimeError):local.perform_upgrade(ROOT,self.data,self.config,worker=lambda *a:0)
        self.assert_original()
    def test_promotion_preserves_backup_and_sets_marker(self):
        local.perform_upgrade(ROOT,self.data,self.config,worker=self.fake_worker)
        m=json.loads((self.data/'local-install.json').read_text());self.assertEqual(m['state'],'upgraded')
        self.assertFalse((self.data/local.PENDING).exists())
        for n,h in self.before.items():self.assertEqual(local.digest(Path(m['backup'])/'original-files'/n),h)
    def test_failed_second_file_promotion_rolls_back(self):
        original=os.replace
        def replace(src,dst):
            if Path(src).parts[-3:]==('stage','db','unittest.db'):raise OSError('Injected rename failure')
            return original(src,dst)
        with patch.object(local.os,'replace',side_effect=replace),self.assertRaises(OSError):
            local.perform_upgrade(ROOT,self.data,self.config,worker=self.fake_worker)
        self.assert_original();self.assertFalse((self.data/local.PENDING).exists())
    def test_changed_config_not_published(self):
        def change(root,stage,log):
            rc=self.fake_worker(root,stage,log);self.config.write_text(self.config.read_text()+'\n');return rc
        with self.assertRaisesRegex(RuntimeError,'Config/installation'):local.perform_upgrade(ROOT,self.data,self.config,worker=change)
        self.assert_original()
    def test_changed_original_not_overwritten(self):
        def change(root,stage,log):
            rc=self.fake_worker(root,stage,log)
            with closing(sqlite3.connect(self.data/'db/sthpw.db')) as c:c.execute('CREATE TABLE external_change(x text)');c.commit()
            return rc
        with self.assertRaisesRegex(RuntimeError,'changed while'):local.perform_upgrade(ROOT,self.data,self.config,worker=change)
        with closing(sqlite3.connect(self.data/'db/sthpw.db')) as c:
            self.assertTrue(c.execute("SELECT 1 FROM sqlite_master WHERE name='external_change'").fetchone())
            self.assertFalse(c.execute("SELECT 1 FROM sqlite_master WHERE name='publication_test'").fetchone())
    def test_missing_project_database_fails_before_worker(self):
        (self.data/'db/unittest.db').unlink()
        with self.assertRaisesRegex(ValueError,'Missing registered'):local.perform_upgrade(ROOT,self.data,self.config,worker=self.fake_worker)
        self.assertFalse((self.data/'backup').exists() and list((self.data/'backup').iterdir()))
    def test_non_sqlite_vendor_refused(self):
        self.config.write_text(self.config.read_text().replace('Sqlite','MySQL'))
        with self.assertRaisesRegex(ValueError,'not SQLite'):local.layout(self.data,self.config)
    def test_external_db_resource_refused(self):
        with closing(sqlite3.connect(self.data/'db/sthpw.db')) as c:
            c.execute("UPDATE project SET db_resource='external' WHERE code='unittest'");c.commit()
        with self.assertRaisesRegex(ValueError,'External project'):local.layout(self.data,self.config)
    def test_local_check_is_read_only_and_shows_missing_schema(self):
        report=local.inspect_local(ROOT,self.data,self.config)
        self.assertFalse(report['startup_ready']);self.assertFalse(report['structure_ready']);self.assert_original()
    def test_local_lock_blocks_second_process(self):
        code="from pathlib import Path;from local_lock import local_lock\nwith local_lock(Path(__import__('sys').argv[1])): print('acquired')"
        env=dict(os.environ,PYTHONPATH=str(ROOT/'tools/local'))
        with local_lock(self.data):
            proc=subprocess.run([sys.executable,'-c',code,str(self.data)],env=env,capture_output=True,text=True,timeout=10)
        self.assertNotEqual(proc.returncode,0);self.assertIn('Another local',proc.stderr)
    def test_process_death_publication_is_recoverable(self):
        # Kill process after original moved aside but before staged file arrives.
        script="""
from pathlib import Path
import os,sys
import managed_sqlite as m
from managed_seed_08 import ROOT
D=Path(sys.argv[1]);marker,tree,files,dbs=m.layout(D,D/'config/tactic-conf.xml')
b=D/'backup'/'crash';b.mkdir(parents=True);(b/'stage/db').mkdir(parents=True)
import shutil
shutil.copy2(D/'local-install.json',b/'local-install.json')
for n,p in files.items():shutil.copy2(p,b/'stage/db'/n)
before=m.fingerprint(files);orig=os.replace
first=True
def move(src,dst):
 global first
 if 'original-files' in Path(dst).parts:
  orig(src,dst);os._exit(73)
 return orig(src,dst)
os.replace=move
m.publish(D,b/'stage',b,files,before,marker,{'target':'5.0.0.a02'})
"""
        env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(ROOT/'tools/local'),str(ROOT/'tests/native_ui')]))
        p=subprocess.run([sys.executable,'-c',script,str(self.data)],env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,73,p.stderr);self.assertTrue((self.data/local.PENDING).exists())
        local.restore_pending(self.data);self.assert_original()
    def test_modified_backup_restore_refused(self):
        b=self.data/'backup/b';(b/'original-files').mkdir(parents=True)
        name='sthpw.db';shutil.copy2(self.data/'db'/name,b/'original-files'/name)
        (b/'original-files'/name).write_bytes(b'bad')
        local.atomic_json(self.data/local.PENDING,{'backup':'backup/b','files':{name:{'before':self.before[name],'after':self.before[name]}}})
        with self.assertRaisesRegex(ValueError,'backup hash mismatch'):local.restore_pending(self.data)
        self.assert_original()

class FullSeedMigrationTests(unittest.TestCase):
    def test_real_seed_original_migrations_repair_and_repeat(self):
        # Complete stock dbs, actual worker/upgrade classes, only licence boundary
        # substituted in a separate TEST subprocess. No fixture ORM/database.
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder)/'local';config=create_seed(data)
            original_xml="<config><project_view><element name='mine' custom='keep &amp; intact'/></project_view></config>"
            with closing(sqlite3.connect(data/'db/sthpw.db')) as c:
                c.execute("INSERT INTO widget_config(code,view,config) VALUES('KEEP_CONFIG','project_view',?)",(original_xml,))
                c.execute('ALTER TABLE login ADD COLUMN display_name text')
                c.execute("INSERT INTO login(code,login,first_name,last_name,display_name) VALUES('test-preserve','test-preserve','Given','Family','My custom display')")
                # Same false latest stamp the old updater can leave after errors.
                c.execute("UPDATE project SET last_version_update='5.0.0.a02'")
                c.commit()
            r=local.perform_upgrade(ROOT,data,config,worker=licence_isolated_worker)
            self.assertTrue(r['passed']);self.assertGreater(len(r['completed']),350)
            self.assertFalse([s for s in r['statements'] if s['status']=='error'])
            self.assertTrue(local.inspect_local(ROOT,data,config)['startup_ready'])
            with closing(sqlite3.connect(data/'db/sthpw.db')) as c:
                self.assertEqual(c.execute("SELECT config FROM widget_config WHERE code='KEEP_CONFIG'").fetchone()[0],original_xml)
                self.assertEqual(c.execute('SELECT DISTINCT display_name FROM login').fetchall(),[('My custom display',)])
                self.assertTrue(c.execute("SELECT 1 FROM sqlite_master WHERE name='message_log'").fetchone())
                self.assertFalse(c.execute("SELECT 1 FROM sqlite_master WHERE name='spt_widget_config'").fetchone())
            r2=local.perform_upgrade(ROOT,data,config,worker=licence_isolated_worker)
            self.assertTrue(r2['passed']);self.assertEqual(r2['completed'],[])
    def test_actual_migration_failure_keeps_original_versions_and_files(self):
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder)/'local';config=create_seed(data)
            # Unique task code constraint must fail, not deduplicate/delete tasks.
            with closing(sqlite3.connect(data/'db/sthpw.db')) as c:
                c.execute('CREATE TABLE must_keep_legacy(x text)');c.commit()
                c.execute("CREATE TABLE translation(value text)") if not c.execute("SELECT 1 FROM sqlite_master WHERE name='translation'").fetchone() else None
                # Known original migration drops translation; nonempty table is blocked.
                cols=c.execute('PRAGMA table_info(translation)').fetchall()
                col=next(x[1] for x in cols if x[1]!='id')
                c.execute('INSERT INTO translation("'+col+'") VALUES(?)',('user text',));c.commit()
            before={p.name:local.digest(p) for p in (data/'db').glob('*.db')}
            with self.assertRaises(RuntimeError):local.perform_upgrade(ROOT,data,config,worker=licence_isolated_worker)
            self.assertEqual(before,{p.name:local.digest(p) for p in (data/'db').glob('*.db')})
            self.assertEqual(json.loads((data/'local-install.json').read_text())['state'],'seed-requires-upgrade')
