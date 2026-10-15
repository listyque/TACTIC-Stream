"""Regressions for original Globals, private settings and SERIAL SQLite repair."""
import ast,hashlib,json,os,sqlite3,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from tactic.core.system_config_model import read_document,config_fields,patch_config
from tactic.core.native_settings import load_settings,save_settings,checked_settings
from tactic.core.sqlite_upgrade import repair_identity_columns,identity_issues,MigrationError
from tactic.core.config_model import target_spec

XML=b'''<?xml version="1.0"?><config custom="keep"><!--retain--><database><vendor>Sqlite</vendor><password>PRIVATE-TEST</password></database><checkin><asset_base_dir>C:/assets</asset_base_dir><custom_alias keep="yes">untouched</custom_alias></checkin><custom><xml><![CDATA[<a/>]]></xml></custom></config>'''
class ConfigTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'tactic-conf.xml';self.path.write_bytes(XML);self.rev=hashlib.sha256(XML).hexdigest()
 def tearDown(self):self.temp.cleanup()
 def test_original_groups(self):
  _,root=read_document(self.path);self.assertEqual([g['title'] for g in config_fields(root)],['Database Setup','Installation','Asset Management','Mail Server','Services','Look and Feel','Security'])
 def test_secrets_are_not_in_projection(self):
  _,root=read_document(self.path);projection=config_fields(root);self.assertNotIn('PRIVATE-TEST',json.dumps(projection));self.assertTrue(next(f for g in projection for f in g['fields'] if f['name']=='database/password')['configured'])
 def test_unknown_xml_comments_cdata_and_secret_preserved(self):
  result=patch_config(self.path,self.rev,{'services/thread_count':'12'});raw,root=read_document(self.path);self.assertTrue(result['backup_created']);self.assertEqual(root.findtext('database/password'),'PRIVATE-TEST');self.assertIn(b'<![CDATA[<a/>]]>',raw);self.assertIn(b'<!--retain-->',raw);self.assertEqual(root.get('custom'),'keep')
 def test_private_byte_exact_backup(self):
  patch_config(self.path,self.rev,{'services/thread_count':'12'});p=next((self.path.parent/'native-config-backups').glob('*.xml'));self.assertEqual(p.read_bytes(),XML)
  if os.name!='nt':self.assertEqual(p.stat().st_mode&0o777,0o600)
 def test_revision_conflict_does_not_write(self):
  with self.assertRaises(FileExistsError):patch_config(self.path,'wrong',{'services/thread_count':'12'})
  self.assertEqual(self.path.read_bytes(),XML)
 def test_invalid_integer_does_not_write(self):
  with self.assertRaises(ValueError):patch_config(self.path,self.rev,{'services/thread_count':'12;execute'})
  self.assertEqual(self.path.read_bytes(),XML)
 def test_invalid_boolean_does_not_write(self):
  with self.assertRaises(ValueError):patch_config(self.path,self.rev,{'security/allow_guest':'yes'})
 def test_unknown_setting_does_not_write(self):
  with self.assertRaises(ValueError):patch_config(self.path,self.rev,{'custom/value':'x'})
 def test_dynamic_checkin_key_retains_attributes(self):
  patch_config(self.path,self.rev,{'checkin/custom_alias':'changed'});_,root=read_document(self.path);self.assertEqual(root.find('checkin/custom_alias').get('keep'),'yes')
 def test_duplicate_section_rejected(self):
  raw=b'<config><services/><services/></config>';self.path.write_bytes(raw)
  with self.assertRaises(ValueError):patch_config(self.path,hashlib.sha256(raw).hexdigest(),{'services/thread_count':'2'})
 def test_duplicate_key_rejected(self):
  raw=b'<config><services><thread_count>1</thread_count><thread_count>2</thread_count></services></config>';self.path.write_bytes(raw)
  with self.assertRaises(ValueError):patch_config(self.path,hashlib.sha256(raw).hexdigest(),{'services/thread_count':'3'})
 def test_entity_and_wrong_root_rejected(self):
  for raw in (b'<!DOCTYPE config [<!ENTITY x SYSTEM "file:///etc/passwd">]><config>&x;</config>',b'<other/>'):
   with self.subTest(raw=raw):
    self.path.write_bytes(raw)
    with self.assertRaises(ValueError):read_document(self.path)
 def test_empty_default_project_removes_legacy_node(self):
  patch_config(self.path,self.rev,{'install/default_project':'a'});raw,_=read_document(self.path);patch_config(self.path,hashlib.sha256(raw).hexdigest(),{'install/default_project':''});_,root=read_document(self.path);self.assertIsNone(root.find('install/default_project'))
 def test_writes_persist_outside_new_source_copy(self):
  root=self.path.parent;source=root/'source.json';source.write_text('{"site":"","allow_writes":false,"allow_uploads":false}')
  save_settings(root/'config/native-ui.json',{'allow_writes':True,'allow_uploads':False});self.assertTrue(load_settings(source,root)['allow_writes']);source.write_text('{"allow_writes":false}');self.assertTrue(load_settings(source,root)['allow_writes'])
 def test_settings_default_readonly(self):
  source=self.path.parent/'source.json';source.write_text('{"allow_writes":false}');self.assertFalse(load_settings(source,self.path.parent)['allow_writes'])
 def test_settings_unknown_or_non_boolean_rejected(self):
  for value in ({'allow_writes':'true'},{'execute':'x'},[],{'allow_uploads':1}):
   with self.subTest(value=value),self.assertRaises(ValueError):checked_settings(value)
 def test_uploads_without_writes_rejected(self):
  with self.assertRaises(ValueError):save_settings(self.path.parent/'settings.json',{'allow_uploads':True,'allow_writes':False})
 def test_original_system_and_license_handlers(self):
  self.assertEqual(target_spec('LinkWdg',{'class_name':'tactic.ui.startup.DbConfigWdg'})['kind'],'system-config');self.assertEqual(target_spec('LinkWdg',{'class_name':'tactic.ui.app.LicenseManagerWdg'})['kind'],'license')

class IdentityTests(unittest.TestCase):
 def setUp(self):self.db=sqlite3.connect(':memory:')
 def tearDown(self):self.db.close()
 def create(self,typ='serial'):
  self.db.execute(f'CREATE TABLE spt_process(id {typ} PRIMARY KEY,code text UNIQUE, data text)');self.db.execute("INSERT INTO spt_process(code,data) VALUES('one','001')");self.db.commit()
 def test_reproduces_original_null_id(self):
  self.create();self.assertIsNone(self.db.execute('select id from spt_process').fetchone()[0]);self.assertEqual(identity_issues(self.db)[0]['table'],'spt_process')
 def test_repairs_null_from_original_rowid_and_keeps_storage(self):
  self.create();result=repair_identity_columns(self.db);self.assertEqual(result,[{'table':'spt_process','filled_null_ids':1}]);self.assertEqual(self.db.execute('select id,data,typeof(data) from spt_process').fetchone(),(1,'001','text'))
 def test_new_original_insert_gets_real_primary_key(self):
  self.create();repair_identity_columns(self.db);self.db.execute("insert into spt_process(code) values('two')");self.assertEqual(self.db.execute("select id from spt_process where code='two'").fetchone()[0],2)
 def test_repeat_noop(self):
  self.create();repair_identity_columns(self.db);sql=self.db.execute("select sql from sqlite_master where name='spt_process'").fetchone();self.assertEqual(repair_identity_columns(self.db),[]);self.assertEqual(sql,self.db.execute("select sql from sqlite_master where name='spt_process'").fetchone())
 def test_unique_index_not_lost(self):
  self.create();repair_identity_columns(self.db)
  with self.assertRaises(sqlite3.IntegrityError):self.db.execute("insert into spt_process(code) values('one')")
 def test_trigger_preserved(self):
  self.create();self.db.execute('create table audit(code text)');self.db.execute('create trigger inserted after insert on spt_process begin insert into audit values(new.code); end');repair_identity_columns(self.db);self.db.execute("insert into spt_process(code) values('two')");self.assertEqual(self.db.execute('select * from audit').fetchall(),[('two',)])
 def test_conflicting_non_null_id_not_renumbered(self):
  self.create();self.db.execute('update spt_process set id=7');before=self.db.execute('select * from spt_process').fetchall()
  with self.assertRaises(MigrationError):repair_identity_columns(self.db)
  self.assertEqual(before,self.db.execute('select * from spt_process').fetchall())
 def test_string_id_not_coerced(self):
  self.create();self.db.execute("update spt_process set id='007'")
  with self.assertRaises(MigrationError):repair_identity_columns(self.db)
 def test_custom_view_stops_rebuild(self):
  self.create();self.db.execute('create view custom_processes as select * from spt_process')
  with self.assertRaises(MigrationError):repair_identity_columns(self.db)
 def test_all_original_serial_spellings(self):
  for typ in ('smallserial','bigserial'):
   with self.subTest(typ=typ):
    self.db.execute('drop table if exists spt_process');self.create(typ);repair_identity_columns(self.db);self.assertEqual(identity_issues(self.db),[])
 def test_normal_identity_untouched(self):
  self.db.execute('create table ok(id integer primary key, value text)');self.db.execute("insert into ok values(100,'a')");self.assertEqual(repair_identity_columns(self.db),[]);self.assertEqual(self.db.execute('select * from ok').fetchall(),[(100,'a')])
 def test_existing_equal_id_preserved(self):
  self.create();self.db.execute('update spt_process set id=rowid');result=repair_identity_columns(self.db);self.assertEqual(result[0]['filled_null_ids'],0)

if __name__=='__main__':unittest.main()
