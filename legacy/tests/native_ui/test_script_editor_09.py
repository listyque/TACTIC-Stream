import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from script_test_store_09 import Store,Backend,ROOT,STYPE
from tactic.ui_api.contracts import ApiError
from tactic.ui_api.script_service import syntax_check,clean_script_values,MAX_SCRIPT_BYTES
from tactic.core.config_model import target_spec,ConfigModel,ConfigSource,SidebarProjection

class ScriptEditor09(unittest.TestCase):
 def setUp(self):
  self.store=Store();self.store.seed();self.backend=Backend(self.store);self.binding=self.store.bind();self.binding.__enter__()
 def tearDown(self):self.binding.__exit__(None,None,None);self.store.db.close()
 def op(self,method,path,**data):return self.backend.script_operation(method,path,dict(target='editor',**data))
 def first(self):return self.op('GET','/scripts')['items'][0]
 def record(self,key=None):return self.op('GET','/script',key=key or self.first()['key'])['record']
 def values(self,**kw):
  v={'folder':'tools','title':'new_script','language':'python','script':'# Привет\nresult = 0\n','description':'описание'};v.update(kw);return v
 def assertCode(self,code,call):
  with self.assertRaises(ApiError) as ctx:call()
  self.assertEqual(ctx.exception.code,code)
 def test_stock_widget_handlers(self):
  for name in ('tactic.ui.app.ShelfEditWdg','tactic.ui.app.ScriptEditorWdg','tactic.ui.app.shelf_wdg.ShelfEditWdg','tactic.ui.app.shelf_wdg.ScriptEditorWdg'):
   self.assertEqual(target_spec('LinkWdg',{'class_name':name})['kind'],'script-editor')
 def test_stock_sidebar_not_replaced(self):
  xml=(ROOT/'src/tactic/ui/config/DEFAULT-conf.xml').read_text();m=ConfigModel('definition',[ConfigSource(xml,'definition')]);el=m.describe('script_editor');self.assertEqual(target_spec(el['handler'],el['options'])['kind'],'script-editor')
 def test_directory_has_server_pagination(self):
  first=self.op('GET','/scripts',limit=20);second=self.op('GET','/scripts',limit=20,offset=20)
  self.assertEqual(first['total'],65);self.assertTrue(first['has_more']);self.assertFalse({i['key'] for i in first['items']}&{i['key'] for i in second['items']})
 def test_directory_does_not_fetch_script_bodies(self):
  result=self.op('GET','/scripts');self.assertTrue(all('script' not in x['values'] for x in result['items']));self.assertNotIn('"script"',self.store.statements[-1])
 def test_nested_folder_search(self):self.assertEqual(self.op('GET','/scripts',folder='workflow/review')['total'],32)
 def test_search_is_literal_sql_not_regex(self):
  self.store.row(title='100%_done');self.assertEqual(self.op('GET','/scripts',q='%_')['total'],1)
 def test_search_quote_is_literal(self):
  self.assertEqual(self.op('GET','/scripts',q="' OR 1=1 --")['total'],0)
 def test_read_preserves_newlines_unicode_spaces(self):
  obj=self.store.row(title='中文',script='  # привет\r\nx = 0\r\n');self.assertEqual(self.record(obj.get_search_key())['values']['script'],'  # привет\r\nx = 0\r\n')
 def test_read_by_original_virtual_script_path(self):self.assertEqual(self.op('GET','/script',script_path='tools/script_000')['record']['values']['title'],'script_000')
 def test_duplicate_path_not_arbitrary_first(self):
  self.store.row(title='script_000',folder='tools');self.assertCode('script_duplicate',lambda:self.op('GET','/script',script_path='tools/script_000'))
 def test_original_default_folder_and_language_and_title(self):
  result=self.op('POST','/script',values=self.values(folder='',language='',title='///new_script'));self.assertEqual(result['record']['values']['folder'],'default');self.assertEqual(result['record']['values']['title'],'new_script');self.assertEqual(result['record']['values']['language'],'javascript');self.assertEqual(self.store.calls[-1][0],'insert')
 def test_update_uses_key_and_only_allowed_fields(self):
  rec=self.record();values=self.values(title=rec['values']['title'],folder=rec['values']['folder']);self.op('PATCH','/script',key=rec['key'],revision=rec['revision'],values=values);self.assertEqual(self.store.calls[-1],('update',rec['key'],values))
 def test_read_only_still_reads_and_checks_but_not_saves(self):
  self.backend.allow_writes=False;self.assertFalse(self.op('GET','/scripts')['can_write']);self.assertTrue(self.op('POST','/script-check',language='python',script='pass')['valid']);self.assertCode('read_only',lambda:self.op('POST','/script',values=self.values()))
 def test_original_builtin_permission_rechecked_every_request(self):
  rec=self.record();self.store.allowed=False
  for method,path,data in [('GET','/scripts',{}),('GET','/script',{'key':rec['key']}),('POST','/script-check',{'language':'python','script':'pass'}),('PATCH','/script',{'key':rec['key'],'revision':rec['revision'],'values':self.values()})]:
   self.assertCode('script_permission',lambda:self.op(method,path,**data))
 def test_target_cannot_be_an_arbitrary_table(self):
  self.assertCode('script_target',lambda:self.backend.script_operation('GET','/scripts',{'target':'some-table'}))
 def test_foreign_project_key_rejected(self):self.assertCode('key_scope',lambda:self.record(self.first()['key'].replace('project=admin','project=other')))
 def test_foreign_type_key_rejected(self):self.assertCode('key_scope',lambda:self.record('sthpw/login?code=admin'))
 def test_change_revision_conflict_keeps_text(self):
  rec=self.record();self.store.update(rec['key'],{'script':'changed outside'});self.store.db.commit();n=len(self.store.calls);self.assertCode('conflict',lambda:self.op('PATCH','/script',key=rec['key'],revision=rec['revision'],values=self.values()));self.assertEqual(n,len(self.store.calls));self.assertEqual(self.record(rec['key'])['values']['script'],'changed outside')
 def test_duplicate_create_is_not_an_overwrite(self):self.assertCode('script_duplicate',lambda:self.op('POST','/script',values=self.values(title='script_000')))
 def test_save_as_insert_does_not_change_original(self):
  rec=self.record();self.op('POST','/script',values=self.values(title='copy'));self.assertEqual(rec,self.record(rec['key']))
 def test_unknown_existing_language_preserved(self):
  obj=self.store.row(title='custom',language='custom_dcc');rec=self.record(obj.get_search_key());r=self.op('PATCH','/script',key=rec['key'],revision=rec['revision'],values=self.values(title='custom',folder='default',language='custom_dcc'));self.assertEqual(r['record']['values']['language'],'custom_dcc')
 def test_new_unknown_language_rejected(self):self.assertCode('script_language',lambda:self.op('POST','/script',values=self.values(language='magic')))
 def test_no_full_script_execution_endpoint(self):self.assertCode('script_execution_disabled',lambda:self.op('POST','/script-run',key=self.first()['key']))
 def test_save_with_syntax_errors_retains_original_editor_semantics(self):self.assertTrue(self.op('POST','/script',values=self.values(script='invalid python :'))['saved'])
 def test_unknown_fields_rejected(self):self.assertCode('script_fields',lambda:self.op('POST','/script',values=self.values(class_name='evil')))
 def test_oversize_utf8_not_character_count(self):self.assertCode('script_size',lambda:self.op('POST','/script',values=self.values(script='я'*(MAX_SCRIPT_BYTES//2+1))))
 def test_nul_rejected(self):self.assertCode('script_size',lambda:self.op('POST','/script',values=self.values(script='\x00')))
 def test_empty_script_is_valid_and_preserved(self):self.assertEqual(self.op('POST','/script',values=self.values(script=''))['record']['values']['script'],'')
 def test_bad_page_limits_rejected(self):
  for value in (0,101,-1,True,'1.1'):
   self.assertCode('limit',lambda:self.op('GET','/scripts',limit=value))
 def test_read_without_key_needs_path(self):self.assertCode('script_path',lambda:self.op('GET','/script'))
 def test_syntax_parse_does_not_execute(self):
  with TemporaryDirectory() as tmp:
   p=Path(tmp)/'never-created';source='open('+repr(str(p))+', "w").write("no")'
   self.assertTrue(self.op('POST','/script-check',language='python',script=source)['valid']);self.assertFalse(p.exists())
 def test_python_syntax_error_has_line(self):
  data=syntax_check('python','x =\n');self.assertFalse(data['valid']);self.assertEqual(data['line'],1);self.assertFalse(data['executed'])
 def test_xml_entity_not_expanded(self):self.assertFalse(syntax_check('xml','<!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]><x>&e;</x>')['valid'])
 def test_unsupported_js_check_is_not_fake_success(self):self.assertIsNone(syntax_check('javascript','not javascript')['valid'])
 def test_xml_valid_no_exec(self):self.assertTrue(syntax_check('xml','<config/>')['valid'])
 def test_archived_script_not_overwritten(self):
  rec=self.record();self.store.update(rec['key'],{'s_status':'retired'});rec=self.record(rec['key']);self.assertCode('script_retired',lambda:self.op('PATCH','/script',key=rec['key'],revision=rec['revision'],values=self.values()))

if __name__=='__main__':unittest.main()
