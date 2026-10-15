"""Original WorkHoursElementAction, plus the guarded native transport boundary.
Database entries below are explicit spies, not a production TACTIC database.
"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
R=Path(__file__).resolve().parents[2];sys.path[:0]=[str(R/'src'),str(R/'src/client')]
from tactic.core.work_hours import WorkHoursElementAction,WorkHoursSemantics
from tactic.ui_api.work_hour_service import WorkHourService
from tactic.ui_api.contracts import ApiError,revision
from test_task_form_04 import Obj
from test_domain_services_04 import ServiceBase

class Entry(Obj):
 def __init__(self,values):super().__init__(values,'sthpw/work_hour');self.commits=0;self.deleted=False
 def set_value(self,name,value):self.values[name]=value
 def set_user(self):self.values['login']='alice'
 def set_project(self):self.values['project_code']='fixture'
 def set_parent(self,parent):self.parent=parent
 def commit(self):self.commits+=1
 def delete(self):self.deleted=True

class OriginalHoursActionTests(unittest.TestCase):
 def setUp(self):
  self.parent=Obj({'code':'ITEM1'},'fixture/item');self.task=Obj({'code':'TASK1','process':'model','project_code':'fixture'},parent=self.parent);self.entries=[];self.created=[];self.parent.get_related_sobjects=lambda st:list(self.entries)
  def create(st):e=Entry({'code':'NEW'+str(len(self.created))});self.created.append(e);return e
  self.patches=[patch('pyasm.common.Environment.get_user_name',return_value='alice'),patch('pyasm.search.SearchType.create',side_effect=create)]
  for p in self.patches:p.start();self.addCleanup(p.stop)
 def entry(self,**kw):
  e=Entry({'code':'WH'+str(len(self.entries)),'task_code':'TASK1','login':'alice','day':'2026-09-30 00:00:00','category':'regular','straight_time':2,**kw});self.entries.append(e);return e
 def apply(self,value):
  a=WorkHoursElementAction();a.set_sobject(self.task);a.set_name('work_hours');a.set_data(json.dumps(value));a.execute()
 def test_create_keeps_original_task_parent_process_and_login(self):
  self.apply({'day_2026_09_30':'3.5'});e=self.created[0];self.assertIs(e.parent,self.parent);self.assertEqual(e.values['task_code'],'TASK1');self.assertEqual(e.values['process'],'model');self.assertEqual(e.values['login'],'alice');self.assertEqual(e.values['category'],'regular');self.assertEqual(e.values['straight_time'],'3.5');self.assertEqual(e.commits,1)
 def test_update_existing_no_duplicate(self):
  e=self.entry();self.apply({'day_2026_09_30':'4'});self.assertEqual(e.values['straight_time'],'4');self.assertEqual(e.commits,1);self.assertFalse(self.created)
 def test_same_string_value_not_recommitted(self):
  e=self.entry();self.apply({'day_2026_09_30':'2'});self.assertEqual(e.commits,0)
 def test_zero_deletes_matching_entry_not_task(self):
  e=self.entry();self.task.delete=Mock(side_effect=AssertionError('not task'));self.apply({'day_2026_09_30':'0'});self.assertTrue(e.deleted);self.task.delete.assert_not_called()
 def test_empty_deletes_matching_entry(self):
  e=self.entry();self.apply({'day_2026_09_30':''});self.assertTrue(e.deleted)
 def test_other_user_untouched(self):
  other=self.entry(login='bob');self.apply({'day_2026_09_30':'0'});self.assertFalse(other.deleted);self.assertEqual(other.commits,0)
 def test_other_task_untouched(self):
  other=self.entry(task_code='TASK2');self.apply({'day_2026_09_30':'6'});self.assertEqual(other.values['straight_time'],2);self.assertEqual(self.created[0].values['task_code'],'TASK1')
 def test_overtime_distinct_from_regular(self):
  regular=self.entry();self.apply({'otday_2026_09_30':'1'});self.assertEqual(regular.values['straight_time'],2);self.assertEqual(self.created[0].values['category'],'overtime')
 def test_empty_category_remains_original_regular_alias(self):
  e=self.entry(category='');self.apply({'day_2026_09_30':'4'});self.assertEqual(e.values['category'],'regular');self.assertFalse(self.created)
 def test_constants_are_source_categories_not_new_labels(self):self.assertEqual(WorkHoursSemantics.ROW_DICT['regular_row'],'regular');self.assertEqual(WorkHoursSemantics.UNIT_DICT,{'hour':3600,'minute':60})

class Hours(WorkHourService,ServiceBase):pass
class NativeHoursTests(unittest.TestCase):
 def setUp(self):
  self.b=Hours();self.parent=Obj({'code':'ITEM1'},'fixture/item');self.task=Obj({'code':'TASK1','status':'Open'},parent=self.parent);self.b._task_parent=lambda data:({},self.parent);self.b._task_for_parent=lambda parent,key:self.task
  self.config={'revision':'config','unit':'hour','straight':True,'own':True,'show_overtime':True,'editable':True,'options':{},'notice':''};self.b._hours_config=lambda *a:dict(self.config)
  self.entries=[];self.b._hours_state=lambda parent,task,start,end,cfg:(list(self.entries),revision([task.values,cfg,[e.values for e in self.entries]]))
  self.search=Mock(get_count=lambda:10);self.patches=[patch('pyasm.common.Environment.get_user_name',return_value='alice'),patch('pyasm.search.Search',return_value=self.search)]
  for p in self.patches:p.start();self.addCleanup(p.stop)
  self.data={'target':'target','key':self.parent.get_search_key(),'task':self.task.get_search_key(),'start':'2026-09-28','end':'2026-10-04'}
 def get(self):return self.b.work_hour_operation('GET',self.data)
 def save(self,cells=None,**kwargs):
  d={**self.data,'revision':self.get()['revision'],'cells':cells or [{'day':'2026-09-30','category':'regular','value':'2.5'}],'confirm':'SAVE_HOURS',**kwargs};return self.b.work_hour_operation('PATCH',d)
 def test_uses_original_action_with_exact_legacy_day_fields(self):
  action=Mock(check=lambda:True)
  with patch('tactic.core.work_hours.WorkHoursElementAction',return_value=action):self.save()
  action.set_sobject.assert_called_once_with(self.task);action.set_name.assert_called_once_with('work_hours');self.assertEqual(json.loads(action.set_data.call_args.args[0]),{'day_2026_09_30':'2.5'});action.execute.assert_called_once();action.post_execute.assert_called_once();action.postprocess.assert_called_once()
 def test_zero_canonicalized_to_original_delete_sentinel(self):
  action=Mock(check=lambda:True)
  with patch('tactic.core.work_hours.WorkHoursElementAction',return_value=action):self.save([{'day':'2026-09-30','category':'regular','value':'0.000'}])
  self.assertEqual(json.loads(action.set_data.call_args.args[0])['day_2026_09_30'],'0')
 def test_confirmation_required(self):
  with self.assertRaises(ApiError):self.save(confirm='')
 def test_user_cannot_be_chosen_in_cell(self):
  with self.assertRaises(ApiError):self.save([{'day':'2026-09-30','category':'regular','value':'2','login':'bob'}])
 def test_numeric_bounds_and_nan(self):
  for value in ('NaN','Infinity','-1','25','0.0000001',True,None,'1; SELECT 1'):
   with self.subTest(value=value):
    with self.assertRaises(ApiError):self.save([{'day':'2026-09-30','category':'regular','value':value}])
 def test_minute_bounds_follow_declared_unit(self):
  self.config['unit']='minute';action=Mock(check=lambda:True)
  with patch('tactic.core.work_hours.WorkHoursElementAction',return_value=action):self.save([{'day':'2026-09-30','category':'regular','value':'90'}])
  with self.assertRaises(ApiError):self.save([{'day':'2026-09-30','category':'regular','value':'1441'}])
 def test_outside_displayed_window_rejected(self):
  with self.assertRaises(ApiError):self.save([{'day':'2026-11-01','category':'regular','value':'2'}])
 def test_duplicate_payload_cell_rejected(self):
  cell={'day':'2026-09-30','category':'regular','value':'2'}
  with self.assertRaises(ApiError):self.save([cell,cell])
 def test_unknown_category_rejected(self):
  with self.assertRaises(ApiError):self.save([{'day':'2026-09-30','category':'admin','value':'2'}])
 def test_overtime_hidden_by_config_not_enabled_by_client(self):
  self.config['show_overtime']=False
  with self.assertRaises(ApiError):self.save([{'day':'2026-09-30','category':'overtime','value':'2'}])
 def test_duplicate_existing_entries_are_not_overwritten_by_sum(self):
  self.entries=[Entry({'code':'A','day':'2026-09-30 00:00:00','category':'regular','login':'alice'}),Entry({'code':'B','day':'2026-09-30 00:00:00','category':'regular','login':'alice'})]
  with patch('tactic.core.work_hours.WorkHoursElementAction') as cls:
   with self.assertRaises(ApiError) as e:self.save()
   cls.assert_not_called()
  self.assertEqual(e.exception.code,'hours_duplicate')
 def test_start_end_entry_not_reinterpreted_as_manual_hours(self):
  self.entries=[Entry({'code':'A','day':'2026-09-30 00:00:00','category':'regular','login':'alice','start_time':'2026-09-30 09:00:00'})]
  with self.assertRaises(ApiError) as e:self.save()
  self.assertEqual(e.exception.code,'hours_time_mode')
 def test_stale_revision_rejected(self):
  with self.assertRaises(ApiError) as e:self.save(revision='old')
  self.assertEqual(e.exception.status,409)
 def test_overlarge_original_parent_query_blocked(self):
  self.search.get_count=lambda:5001
  with self.assertRaises(ApiError) as e:self.save()
  self.assertEqual(e.exception.code,'hours_parent_limit')
 def test_readonly_and_special_mode_disable_writes(self):
  self.config['editable']=False;self.assertFalse(self.get()['can_write'])
  with self.assertRaises(ApiError):self.save()
 def test_maximum_date_window(self):
  with self.assertRaises(ApiError):self.save(start='2026-08-01',end='2026-10-01')
 def test_archived_task_readonly(self):
  self.task.values['s_status']='retired';self.assertFalse(self.get()['can_write'])
  with self.assertRaises(ApiError):self.save()

 def test_unknown_existing_category_never_overwritten_as_regular(self):
  self.entries=[Entry({'code':'CUSTOM','day':'2026-09-30 00:00:00','category':'holiday','login':'alice','straight_time':2})]
  self.assertEqual(self.get()['items'][0]['category'],'holiday')
  with patch('tactic.core.work_hours.WorkHoursElementAction') as command:
   with self.assertRaises(ApiError) as e:self.save()
   command.assert_not_called()
  self.assertEqual(e.exception.code,'hours_custom_category')
 def test_write_requires_exact_displayed_range(self):
  with self.assertRaises(ApiError):self.save(end='')

class WorkHourConfigTests(unittest.TestCase):
 def setUp(self):
  from tactic.core.config_model import ConfigModel,ConfigSource
  self.b=Hours();self.b._project=lambda:'fixture'
  self.raw=(R/'src/config2/search_type/widget/sthpw/task-conf.xml').read_text()
  self.custom='<config><week><element name="hours_alias"><display class="tactic.ui.table.WorkHoursElementWdg"><unit>minute</unit><days_per_page>3</days_per_page><show_overtime>true</show_overtime><start_date>2026-09-29</start_date></display></element></week></config>'
  def model(st,view):return ConfigModel(view,[ConfigSource(self.custom,view,'personal'),ConfigSource(self.raw,view,'original task-conf.xml'),ConfigSource(self.raw,'edit_definition' if view=='edit' else 'definition','original definitions'),ConfigSource(self.raw,'definition','original definition')])
  self.b._model=model;self.security=Mock(check_access=lambda *a,**kw:True)
  self.p=patch('pyasm.common.Environment.get_security',return_value=self.security);self.p.start();self.addCleanup(self.p.stop)
 def test_original_stock_widget_and_action(self):
  c=self.b._hours_config();self.assertTrue(c['editable']);self.assertEqual(c['days_per_page'],7);self.assertEqual(c['unit'],'hour')
 def test_selected_view_and_alias_are_source_driven(self):
  c=self.b._hours_config({'search_type':'sthpw/task','view':'week'},'hours_alias');self.assertTrue(c['editable']);self.assertEqual(c['days_per_page'],3);self.assertEqual(c['unit'],'minute');self.assertTrue(c['show_overtime'])
 def test_explicit_unknown_action_disables_inherited_default(self):
  self.custom=self.custom.replace('</element>','<action class="custom.DangerousAction"/></element>')
  self.assertFalse(self.b._hours_config({'search_type':'sthpw/task','view':'week'},'hours_alias')['editable'])
 def test_read_only_source_option(self):
  self.custom=self.custom.replace('<unit>','<read_only>true</read_only><unit>')
  self.assertFalse(self.b._hours_config({'search_type':'sthpw/task','view':'week'},'hours_alias')['editable'])
 def test_unknown_widget_cannot_gain_default_action(self):
  self.custom=self.custom.replace('tactic.ui.table.WorkHoursElementWdg','custom.HoursWidget')
  self.assertFalse(self.b._hours_config({'search_type':'sthpw/task','view':'week'},'hours_alias')['editable'])
 def test_configured_period_and_start_date(self):
  c=self.b._hours_config({'search_type':'sthpw/task','view':'week'},'hours_alias');start,end=self.b._hours_window({},c);self.assertEqual(str(start),'2026-09-29');self.assertEqual(str(end),'2026-10-01')
 def test_configured_unsupported_period_not_silently_truncated(self):
  self.custom=self.custom.replace('<days_per_page>3','<days_per_page>90')
  with self.assertRaises(ApiError):self.b._hours_config({'search_type':'sthpw/task','view':'week'},'hours_alias')
 def test_source_field_access_denied(self):
  self.security.check_access=lambda *a,**kw:False
  with self.assertRaises(ApiError):self.b._hours_config()
 def test_current_view_not_replaced_by_fixed_week(self):
  c=self.b._hours_config({'search_type':'sthpw/task','view':'week'},'hours_alias');start,end=self.b._hours_window({'start':'2026-10-05'},c);self.assertEqual(str(end),'2026-10-07')

if __name__=='__main__':unittest.main()
