"""TEST ONLY: native script service + original Search on isolated SQLite tables."""
from fixture_08 import FixtureBackend as Previous
from script_test_store_09 import Store,Backend,STYPE,Query
from tactic.ui_api.contracts import ApiError
from tactic.core.config_model import ConfigModel,ConfigSource
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class FixtureBackend(Previous):
 def __init__(self,*a,**kw):
  super().__init__(*a,**kw);self.script_stores={}
 def script_backend(self,target):
  project=self._project()
  if project not in self.script_stores:
   store=Store();store.project=project;store.seed();self.script_stores[project]=store
  return Backend(self.script_stores[project],target)
 def open_target(self,key):
  if isinstance(key,str) and key.endswith('/~scripts-table'):
   parent=super().open_target(key[:-len('/~scripts-table')])
   if parent['kind']!='script-editor':raise ApiError(403,'script_target','Not original script editor')
   result={'id':key,'kind':'table','handler':'tactic.ui.panel.ViewPanelWdg','search_type':STYPE,'view':'table','title':'Saved Scripts','config_view':parent.get('config_view'),'attributes':{},'options':{'show_shelf':'false','element_names':'folder,title,description,language'}}
   result['spec']=self.view(STYPE,'table',result['options']);return result
  return super().open_target(key)
 def view(self,stype,view,options=None):
  if stype!=STYPE:return super().view(stype,view,options)
  spec=super().view(stype,view,options);allowed=(options or {}).get('element_names','folder,title,description,language').split(',')
  spec['fields']=[f for n in allowed for f in spec['fields'] if f['name']==n]
  for f in spec['fields']:f.update(read_only=True,handler='tactic.ui.common.SimpleTableElementWdg')
  spec['capabilities']={'create':False,'update':False,'retire':False};spec['table_options']={'show_shelf':False,'page_size':40};return spec
 def query(self,stype,spec,query):
  if stype!=STYPE:return super().query(stype,spec,query)
  backend=self.script_backend(None)
  with backend.store.bind():
   q=Query(backend.store,STYPE);total=q.get_count();q.add_order_by('folder');q.add_order_by('title');q.set_limit(query['limit']);q.set_offset(query['offset'])
   rows=[{'key':row.get_search_key(),'values':{f['name']:row.get_value(f['name']) for f in spec['fields']},'revision':'test'} for row in q.get_sobjects()]
  return {'items':rows,'total':total,'offset':query['offset'],'limit':query['limit'],'has_more':query['offset']+len(rows)<total}
 def config_operation(self,method,path,data):
  if path in ('/scripts','/script','/script-check'):
   target=self.open_target(data.get('target'));backend=self.script_backend(target)
   with backend.store.bind():return backend.script_operation(method,path,data)
  return super().config_operation(method,path,data)
