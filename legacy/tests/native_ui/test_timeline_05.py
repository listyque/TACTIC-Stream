import copy
import sqlite3
import unittest
from datetime import date,timedelta
from unittest.mock import patch
from timeline_test_store import TimelineStore,Backend,spec,COLUMNS
from tactic.core.timeline_model import append_window,date_window
from tactic.ui_api.contracts import ApiError

class TimelineTests(unittest.TestCase):
 def setUp(self):
  self.store=TimelineStore();self.binding=self.store.bind();self.binding.__enter__();self.backend=Backend(self.store);self.spec=spec()
 def tearDown(self):self.binding.__exit__(None,None,None);self.store.close()
 def add(self,code,start,end,actual_start=None,actual_end=None,project='test',status='Open'):
  return self.store.row('records',code=code,name=code,start_date=start,end_date=end,actual_start=actual_start,actual_end=actual_end,project_code=project,status=status,s_status='active')
 def request(self,**kwargs):
  data={'start':'2026-09-10','end':'2026-09-12','limit':200,'sort':{'field':'code','direction':'asc'},**kwargs};return self.backend.timeline('fixture/schedule',self.spec,data)
 def names(self,**kwargs):return [r['values']['code'] for r in self.request(**kwargs)['items']]
 def test_interval_overlaps_start_boundary(self):self.add('A','2026-09-01','2026-09-10');self.assertEqual(self.names(),['A'])
 def test_interval_overlaps_end_boundary(self):self.add('A','2026-09-12T23:59:00','2026-09-14');self.assertEqual(self.names(),['A'])
 def test_outside_next_day_excluded(self):self.add('A','2026-09-13','2026-09-14');self.assertEqual(self.names(),[])
 def test_before_period_excluded(self):self.add('A','2026-09-01','2026-09-09T23:59:00');self.assertEqual(self.names(),[])
 def test_null_end_single_day_inside(self):self.add('A','2026-09-11',None);self.assertEqual(self.names(),['A'])
 def test_null_end_before_period_not_unbounded(self):self.add('A','2026-09-01',None);self.assertEqual(self.names(),[])
 def test_second_configured_bar_participates(self):self.add('A','2026-08-01','2026-08-10','2026-09-10','2026-09-13');r=self.request();self.assertEqual(r['total'],1);self.assertEqual(len(r['items'][0]['timeline']),2)
 def test_record_matching_two_bars_not_duplicated(self):self.add('A','2026-09-10','2026-09-12','2026-09-11','2026-09-11');self.assertEqual(self.request()['total'],1)
 def test_undated_explicit(self):self.add('A',None,None);self.assertEqual(self.names(),[]);self.assertEqual(self.names(include_undated=True),['A'])
 def test_partly_dated_outside_not_counted_as_undated(self):self.add('A',None,None,'2026-08-01','2026-08-02');self.assertEqual(self.names(include_undated=True),[])
 def test_foreign_project_not_leaked_by_or(self):self.add('A','2026-09-11','2026-09-12',project='other');self.assertEqual(self.names(),[])
 def test_config_base_filters_preserved(self):
  self.add('A','2026-09-11','2026-09-12');self.add('B','2026-09-11','2026-09-12',status='Complete')
  self.backend.active_target['options']['test_base_filter']={'field':'status','op':'eq','value':'Complete'};self.assertEqual(self.names(),['B'])
 def test_user_filters_combine_with_window(self):
  self.add('A','2026-09-11','2026-09-12');self.add('B','2026-09-11','2026-09-12');self.assertEqual(self.names(where={'field':'code','op':'eq','value':'A'}),['A'])
 def test_all_pages_are_independent_of_table_offset(self):
  self.store.schedule();one=self.request(start='2026-09-01',end='2026-09-30');two=self.request(start='2026-09-01',end='2026-09-30',offset=200)
  self.assertEqual(one['total'],320);self.assertEqual(len(one['items']),200);self.assertEqual(len(two['items']),120);self.assertFalse(two['has_more']);self.assertEqual(len({r['key'] for r in one['items']+two['items']}),320)
 def test_manual_dates_do_not_include_secondary_interval(self):self.add('A','2026-08-01','2026-08-02','2026-09-11','2026-09-12');self.assertEqual(self.names(start_field='start_date',end_field='end_date'),[])
 def test_manual_undeclared_column_denied(self):
  with self.assertRaises(ApiError):self.request(start_field='actual_start',end_field='actual_end')
 def test_manual_text_column_denied(self):
  with self.assertRaises(ApiError):self.request(start_field='name',end_field='name')
 def test_source_column_permission_checked(self):
  with patch('tactic.ui_api.timeline_service.field_access',return_value=(False,False)),self.assertRaises(ApiError):self.request()
 def test_config_nondate_column_explicit_error(self):
  self.spec=copy.deepcopy(self.spec);self.spec['fields'][-1]['bars'][0]['start_date_col']='status'
  with self.assertRaises(ApiError):self.request()
 def test_window_limits_and_invalid_dates(self):
  for kwargs in ({'end':'2027-10-01'},{'start':'2026-02-30'},{'end':'2026-09-01'},{'start':None},{'include_undated':'false'},{'end':'9999-12-31','start':'9999-12-01'}):
   with self.subTest(kwargs=kwargs),self.assertRaises(ApiError):self.request(**kwargs)
 def test_query_injection_field_rejected(self):
  with self.assertRaises(ApiError):self.request(start_field='start_date);DROP TABLE records;--',end_field='end_date')
 def test_color_projection_restricts_css(self):
  self.spec=copy.deepcopy(self.spec);self.spec['fields'][-1]['bars'][0]['color']='url(javascript:alert(1))';self.assertEqual(self.request()['bars'][0]['color'],'')
 def test_real_boolean_sql_against_reference_overlap(self):
  # Exhaustive small grid: true server Select/Postfix logic vs simple dates.
  dates=[None,'2026-09-08','2026-09-10','2026-09-12','2026-09-14'];expected=[]
  for i,a in enumerate(dates):
   for j,b in enumerate(dates):
    code=f'{i}-{j}';self.add(code,a,b)
    if a and a<'2026-09-13' and ((b and b>='2026-09-10') or (b is None and a>='2026-09-10')):expected.append(code)
  self.assertEqual(self.names(),expected)
 def test_timestamp_boundary_at_midnight_and_date_only(self):
  for code,end in [('A','2026-09-10'),('B','2026-09-10 00:00:00'),('C','2026-09-10T00:00:00+03:00')]:self.add(code,'2026-09-09',end)
  self.assertEqual(self.names(),['A','B','C'])
 def test_day_bounds_do_not_shift_through_legacy_timezone_conversion(self):
  from datetime import timezone
  self.add('A','2026-09-10','2026-09-10')
  with patch('pyasm.common.spt_date.TZLOCAL',timezone(timedelta(hours=3))):self.assertEqual(self.names(),['A'])
 def test_date_window_366_days_inclusive(self):self.assertEqual(date_window('2026-01-01','2027-01-01')[2],'2027-01-02')

if __name__=='__main__':unittest.main()
