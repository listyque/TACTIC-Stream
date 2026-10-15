"""TEST ONLY timeline metadata/persistence around production query and services."""
from types import SimpleNamespace
from datetime import date,timedelta
from contextlib import contextmanager
from unittest.mock import patch
from message_test_store import Store,Query,COLS
from tactic.ui_api.timeline_service import TimelineService
from tactic.ui_api.config_backend import ConfigBackend
from tactic.ui_api.contracts import revision
from tactic.core.config_model import ConfigModel,ConfigSource
from tactic.core.query_model import apply_tree

COLS['records']={'id':'INTEGER PRIMARY KEY','code':'TEXT','name':'TEXT','status':'TEXT','project_code':'TEXT','start_date':'TEXT','end_date':'TEXT','actual_start':'TEXT','actual_end':'TEXT','s_status':'TEXT'}
COLUMNS={n:{'data_type':'timestamp' if n in ('start_date','end_date','actual_start','actual_end') else 'integer' if n=='id' else 'varchar'} for n in COLS['records']}
XML='''<config><table><element name="code"/><element name="name"/><element name="status"/><element name="start_date"/><element name="end_date"/><element name="gantt" title="План / факт"><display class="tactic.ui.table.GanttElementWdg"><options>[{"start_date_col":"start_date","end_date_col":"end_date","label":"План","color":"#5479a6"},{"start_date_col":"actual_start","end_date_col":"actual_end","label":"Факт","color":"#56855b"}]</options></display></element></table></config>'''
BARS=[{'start_date_col':'start_date','end_date_col':'end_date','label':'План','color':'#5479a6'}, {'start_date_col':'actual_start','end_date_col':'actual_end','label':'Факт','color':'#56855b'}]
def spec():
 return {'type':'fixture/schedule','view':'table','fields':[{'name':n,'label':n,'storage':True,'kind':('datetime' if n in ('start_date','end_date') else 'text'),'read_only':False,'supported':True,'handler':'TEST','reason':''} for n in ('code','name','status','start_date','end_date')]+[{'name':'gantt','label':'План / факт','storage':False,'renderer':'gantt','bars':BARS,'read_only':True,'supported':True,'kind':'text','handler':'tactic.ui.table.GanttElementWdg','reason':''}],
         'capabilities':{'create':False,'update':False,'retire':False},'diagnostics':[],'revision':revision(XML)}
class TimelineStore(Store):
 def schedule(self,count=320):
  for i in range(count):
   start=date(2026,9,1)+timedelta(days=i%25);end=start+timedelta(days=3)
   self.row('records',code='S%04d'%i,name='TEST Schedule %04d'%i,status='Open' if i%2==0 else 'Complete',project_code=self.project,
            start_date=start.isoformat(),end_date=end.isoformat(),actual_start=(start+timedelta(days=1)).isoformat(),actual_end=(end+timedelta(days=1)).isoformat(),s_status='active')
  self.db.commit()
 @contextmanager
 def bind(self):
  with super().bind(),patch('pyasm.common.Environment.get_security',return_value=SimpleNamespace(check_access=lambda *a,**kw:True)),patch('pyasm.search.SearchType.column_exists',side_effect=lambda st,n:n in COLUMNS),patch('pyasm.search.SearchType.get',return_value=SimpleNamespace(get_retire_col=lambda:'s_status')):
   yield
class Backend(TimelineService):
 allow_writes=False
 _query_search=ConfigBackend._query_search
 def __init__(self,store):self.store=store;self.active_target={'options':{}};self.denied=set()
 def _project(self):return self.store.project
 def _stub(self):return SimpleNamespace(get_column_info=lambda st:COLUMNS)
 def _model(self,*args):return ConfigModel('table',[ConfigSource(XML,'table','TEST widget_config')])
 def _defaults(self,search,stype,options):
  search.add_filter('project_code',self._project())
  apply_tree(search,options.get('test_base_filter'),spec()['fields'])
 def _query_search(self,stype,spec,query):
  # Production builder with a test-specific SearchType/table mapping.
  return ConfigBackend._query_search(self,'sthpw/records',spec,query)
 def _serialize_many(self,objects,spec):
  return [{'key':'fixture/schedule?id='+str(o.get_id()),'values':{f['name']:o.get_value(f['name']) for f in spec['fields'] if f.get('storage')},'revision':revision(o.get_sobject_dict())} for o in objects]
