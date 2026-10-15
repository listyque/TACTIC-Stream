"""Original semantic units with replaced DB collaborators, not live DB tests."""
import ast
import copy
import json
import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
R=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(R/'src'),str(R/'src/client')]
from pyasm.common import Container, SetupException, UserException
from tactic.core.filter_data import FilterData
from tactic.core.context_actions import SubContextAction
from tactic.core.task_choices import allowed_task_statuses, process_choices, TaskChoiceContext
from tactic.core.native_edit import NativeEditCmd, ExplicitTaskDateAction
from tactic.core.edit_commands import EditCmd
from pyasm.command.edit_wdg_action import TaskDateAction
import test_query_04 as query_tests
from test_query_04 import FIELDS, leaf, group
from tactic.core.query_model import merge_saved

class FilterDataTests(unittest.TestCase):
 def test_json_apostrophes_unchanged(self):
  raw=[{'prefix':'main_body','main_body_value':"O'Reilly & Sons"}]
  self.assertEqual(FilterData(json.dumps(raw)).get_data(),raw)
 def test_legacy_literal_accepted_without_eval(self):
  self.assertEqual(FilterData("[{'value': 'a', 'enabled': True}]").get_data(),[{'value':'a','enabled':True}])
 def test_no_code_execution(self):
  with patch('builtins.eval',side_effect=AssertionError('NO EVAL')):
   with self.assertRaises(SetupException):FilterData("__import__('os').system('false')")
 def test_cached_inputs_not_mutated(self):
  raw=[{'values':[1,2]}];data=FilterData(raw);data.get_data()[0]['values'].append(3)
  self.assertEqual(raw,[{'values':[1,2]}])
 def test_add_and_set_copy(self):
  raw={'value':['x']};data=FilterData();data.add_data(raw);raw['value'].append('y');self.assertEqual(data.get_data(),[{'value':['x']}]);data.set_data(raw);raw['value'].append('z');self.assertEqual(data.get_data(),[{'value':['x','y']}])
 def test_empty_inputs(self):
  for raw in (None,'','  ',[]):self.assertTrue(FilterData(raw).is_empty())
 def test_bad_shapes(self):
  for raw in (1,False,[1],['x'],'null-not-json','[None]'):
   with self.subTest(raw=raw):
    with self.assertRaises(SetupException):FilterData(raw)
 def test_prefix_and_index_semantics(self):
  data=FilterData([{'prefix':'a','x':1},{'prefix':'b','x':2},{'prefix':'a','x':3}]);self.assertEqual(data.get_values('a','x'),[1,3]);self.assertEqual(data.get_values_by_index('a',1)['x'],3);self.assertEqual(data.get_values_by_index('a',2),{})
 def test_legacy_import_reexports_actual_class(self):
  self.assertIs(runpy.run_path(str(R/'src/tactic/ui/filter/filter_data.py'))['FilterData'],FilterData)
 def test_no_eager_presentation_import(self):
  tree=ast.parse((R/'src/tactic/core/filter_data.py').read_text());self.assertFalse(any(isinstance(x,ast.ImportFrom) and (x.module or '').startswith(('pyasm.web','tactic.ui')) for x in tree.body))

class MergeSavedTests(unittest.TestCase):
 setUp=query_tests.QueryTests.setUp
 tearDown=query_tests.QueryTests.tearDown
 normalized=query_tests.QueryTests.normalized
 ids=query_tests.QueryTests.ids
 run_tree=query_tests.QueryTests.run_tree
 run_saved=query_tests.QueryTests.run_saved
 # Reuse ONLY protocol/database helpers; inherited tests are deliberately removed
 # below to avoid reporting the same 25 scenarios twice.
 def test_inherited_groups_keep_semantics(self):
  for mode in ('and','or'):
   base=[{'prefix':'main_body','main_body_column':'name','main_body_relation':'contains','main_body_value':'a'}, {'prefix':'main_body','main_body_column':'age','main_body_relation':'is greater than','main_body_value':'10'}, {'prefix':'filter_mode','filter_mode':mode}]
   before=copy.deepcopy(base)
   for tree in (group('and',leaf('age','lt',40)),group('or',leaf('age','eq',10),leaf('age','eq',40)),group('and',group('or',leaf('age','eq',10),leaf('age','eq',20)),leaf('flag','eq',False))):
    expected=sorted(set(self.run_saved(base)) & set(self.run_tree(tree)))
    with self.subTest(mode=mode,tree=tree):self.assertEqual(self.run_saved(merge_saved(base,self.normalized(tree),FIELDS)),expected)
   self.assertEqual(base,before)
 def test_unchanged_custom_filter_copied(self):
  base=[{'prefix':'filter_mode','filter_mode':'custom'},{'prefix':'search_ops','ops':[]}]
  got=merge_saved(base,group('and'),FIELDS);got[0]['filter_mode']='x';self.assertEqual(base[0]['filter_mode'],'custom')
 def test_custom_base_not_flattened(self):
  with self.assertRaises(ValueError):merge_saved([{'prefix':'filter_mode','filter_mode':'custom'}],group('and',leaf('age','eq',0)),FIELDS)
 def test_disabled_base_not_resurrected(self):
  with self.assertRaises(ValueError):merge_saved([{'main_body_enabled':'false','main_body_column':'age'}],group('and',leaf('age','eq',0)),FIELDS)
 def test_empty_base_same_as_native(self):
  tree=group('or',leaf('age','eq',0),leaf('age','eq',10));self.assertEqual(self.run_tree(tree),self.run_saved(merge_saved([],self.normalized(tree),FIELDS)))

class TaskChoiceTests(unittest.TestCase):
 def pipeline(self,names=('Open','Waiting','Closed')):
  return Mock(get_process_names=lambda:list(names),get_code=lambda:'review')
 def test_current_status_preserved_even_if_other_statuses_denied(self):
  sec=Mock(check_access=lambda *a,**k:False);self.assertEqual(allowed_task_statuses(sec,self.pipeline(),'Waiting'),['Waiting'])
 def test_process_select_permission_shortcuts(self):
  calls=[]
  def access(kind,key,*a,**kw):calls.append((kind,key,kw));return kind=='process_select' and key=='Open'
  self.assertEqual(allowed_task_statuses(Mock(check_access=access),self.pipeline()),['Open']);self.assertNotIn(('process',[{'process':'*','pipeline':'review'},{'process':'*','pipeline':'*'},{'process':'Open','pipeline':'review'}],{'default':'deny'}),calls)
 def test_original_process_wildcards_are_preserved(self):
  sec=Mock();sec.check_access.side_effect=lambda kind,key,*a,**kw: kind=='process' and key[-1]=={'process':'Closed','pipeline':'review'}
  self.assertEqual(allowed_task_statuses(sec,self.pipeline()),['Closed']);self.assertEqual(sec.check_access.call_args_list[-1].args,('process',[{'process':'*','pipeline':'review'},{'process':'*','pipeline':'*'},{'process':'Closed','pipeline':'review'}],'view'))
 def test_no_assumed_status_names(self):
  sec=Mock(check_access=lambda *a,**kw:True);self.assertEqual(allowed_task_statuses(sec,self.pipeline(('Custom A','Custom B'))),['Custom A','Custom B'])
 def test_recursive_processes_and_contexts(self):
  a=Mock(get_name=lambda:'a',is_from_sub_pipeline=lambda:False);b=Mock(get_name=lambda:'b',is_from_sub_pipeline=lambda:True,get_full_name=lambda:'sub.b');p=Mock();p.get_processes.return_value=[a,b];p.get_output_contexts.side_effect=lambda name:['a/main','a/thumb'] if name=='a' else ['a/main','b/out']
  self.assertEqual(process_choices(p),['a','sub.b']);p.get_processes.assert_called_with(recurse=True,type=['manual','approval','node']);self.assertEqual(process_choices(p,True),['a/main','a/thumb','b/out'])
 def test_preview_is_nonpersistent_view(self):
  original=Mock(get_value=lambda n,*a,**kw:{'pipeline_code':'old','status':'Open'}[n],get_parent=lambda:'parent');proxy=TaskChoiceContext(original,{'pipeline_code':'new'});sentinel=object()
  with patch('pyasm.biz.Pipeline.get_by_code',return_value=sentinel) as get:
   self.assertIs(proxy.get_pipeline(),sentinel);get.assert_called_once_with('new')
  self.assertEqual(proxy.get_value('status'),'Open');self.assertEqual(original.get_value('pipeline_code'),'old');self.assertEqual(proxy.get_parent(),'parent');self.assertFalse(hasattr(proxy,'commit'))

class SubContextTests(unittest.TestCase):
 def action(self,old,new):
  a=SubContextAction();a.get_value=lambda:new;a.sobject=Mock(get_value=lambda n:old);return a
 def test_replace_suffix_keeps_process(self):
  a=self.action('render/old','final');a.postprocess();a.sobject.set_value.assert_called_once_with('context','render/final');a.sobject.commit.assert_called_once()
 def test_remove_suffix_not_context(self):
  a=self.action('render/old','');a.postprocess();a.sobject.set_value.assert_called_once_with('context','render')
 def test_simple_context_unchanged(self):
  a=self.action('render','');a.postprocess();a.sobject.commit.assert_not_called()
 def test_empty_context_with_suffix_is_validation_error(self):
  a=self.action(None,'final')
  with self.assertRaises(UserException):a.postprocess()
  a.sobject.commit.assert_not_called()
 def test_both_empty_is_noop_not_attributeerror(self):
  a=self.action(None,'');a.postprocess();a.sobject.commit.assert_not_called()
 def test_original_execute_is_noop(self):
  a=self.action('x','y');a.execute();a.sobject.set_value.assert_not_called()
 def test_only_exact_task_date_is_adapted(self):
  plain=TaskDateAction();plain.name='date';custom=type('CustomDate',(TaskDateAction,),{})();custom.name='custom';cmd=object.__new__(NativeEditCmd);cmd.data={'date':None,'custom':None}
  with patch.object(EditCmd,'_get_action_handlers',return_value=[plain,custom]):got=cmd._get_action_handlers()
  self.assertIs(type(got[0]),ExplicitTaskDateAction);self.assertIs(got[1],custom);self.assertIs(ExplicitTaskDateAction.postprocess,TaskDateAction.postprocess)
 def test_task_date_null_keeps_original_postprocess(self):
  a=ExplicitTaskDateAction();a.name='bid_end_date';a.explicit_value=None;a.sobject=Mock();a.execute();a.postprocess();a.sobject.set_value.assert_called_once_with('bid_end_date',None,allow_none=True)

class HeaderCompatibilityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.parse=staticmethod(runpy.run_path(str(R/'3rd_party/python3/site-packages/cherrypy/lib/_cgi_header.py'))['parse_header'])
 def test_multipart(self):self.assertEqual(self.parse('multipart/form-data; boundary="abc"'),('multipart/form-data',{'boundary':'abc'}))
 def test_quoted_semicolon_and_escaped_quote(self):self.assertEqual(self.parse('text/plain; name="a;b\\"c"; charset=UTF-8'),('text/plain',{'name':'a;b"c','charset':'UTF-8'}))
 def test_no_parameters(self):self.assertEqual(self.parse('application/json'),('application/json',{}))
 def test_parameter_case_normalized(self):self.assertEqual(self.parse('text/plain; CHARSET="utf-8"'),('text/plain',{'charset':'utf-8'}))
 def test_bare_parameter_ignored(self):self.assertEqual(self.parse('x/y; broken; a=b'),('x/y',{'a':'b'}))

if __name__=='__main__':unittest.main()
