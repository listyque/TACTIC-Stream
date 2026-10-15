"""TEST ONLY: real shipped sidebar XML, synthetic record storage.

Never imported by production mount. This does not emulate or validate TACTIC's
PostgreSQL/permissions/workflow engine. It tests HTTP routing and Vue contracts.
"""
import copy,json,contextvars
from pathlib import Path
from contextlib import contextmanager
from tactic.core.config_model import ConfigSource,ConfigModel,SidebarProjection,parse_xml,view_node,reorder_view,patch_pipeline_positions
from tactic.ui_api.contracts import ApiError,revision

ROOT=Path(__file__).resolve().parents[2]

class FixtureBackend:
 mode='test-fixture'
 def __init__(self,*args,**kw):
  self.state=contextvars.ContextVar('fixture_project',default='admin');self.overrides={};self.members=['fixture'];self.pipeline='<pipeline fixture="keep"><process name="request" type="manual" xpos="80" ypos="90"/><process name="review" type="approval" xpos="380" ypos="160" custom="A &amp; B"/><connect from="request" to="review"/></pipeline>'
  self.schema='<schema><search_type name="fixture/item" xpos="80" ypos="90"/><search_type name="sthpw/task" xpos="380" ypos="160"/><connect from="fixture/item" to="sthpw/task" relationship="search_type"/></schema>'
 @contextmanager
 def context(self,session=None,project=None):
  token=self.state.set(project or 'admin')
  try:yield
  finally:self.state.reset(token)
 def login(self,login,password,two):
  if login!='fixture' or password!='fixture-only':raise ApiError(401,'invalid_credentials','Тестовые учётные данные неверны')
  return {'login':'fixture','ticket':'not-a-real-tactic-ticket','site':''}
 def identity(self,session):return {'login':'fixture','display_name':'Fixture user','mode':self.mode,'site':'','allow_writes':True,'allow_uploads':False}
 def projects(self):return [{'code':'admin','name':'TACTIC Site Admin · TEST'},{'code':'fixture','name':'Fixture project'}]
 def _loader(self,view,personal=False):
  texts=[((ROOT/'src/tactic/ui/config'/name).read_text(),name) for name in ['admin-conf.xml','DEFAULT-conf.xml']]
  layers=[]
  if view in self.overrides:layers.append(ConfigSource(self.overrides[view],view,'config/widget_config:TEST'))
  for v in (view,'definition'):
   for text,origin in texts:
    if view_node(parse_xml(text),v) is not None:layers.append(ConfigSource(text,v,origin))
  return ConfigModel(view,layers)
 def _tree(self):
  p=SidebarProjection(self._loader,lambda n:True,self.state.get(),'fixture');tree=p.build(['admin_views']);return tree,p.targets
 def sidebar(self):
  tree,targets=self._tree();return {'sections':tree,'title':'TACTIC configured administration · TEST','source':'original XML / synthetic records','targets':len(targets)}
 def catalog(self):
  _,targets=self._tree()
  return {'types':[{'code':st,'name':st,'target':next(k for k,t in targets.items() if t.get('search_type')==st)} for st in sorted({t['search_type'] for t in targets.values() if t.get('search_type')})]}
 def view(self,stype,view,options=None):
  path=ROOT/'src/config2/search_type/widget'/(stype+'-conf.xml')
  names=['code','name','description']; labels={}
  if path.exists():
   from tactic.core.widget_config import WidgetConfig,WidgetConfigView
   from pyasm.common import Container
   Container.create();xml=path.read_text();c=WidgetConfigView(search_type=None,view=view,configs=[WidgetConfig.get(xml=xml,view=v) for v in [view,'definition']]);m=ConfigModel.from_tactic(c)
   names=m.names() or names;labels={n:m.describe(n)['title'] for n in names}
  fields=[{'name':n,'label':labels.get(n,n.title()),'storage':True,'supported':True,'read_only':n in ('id','code'),'kind':'text','handler':'TEST ROW VALUE','reason':'','options':[]} for n in names if n not in ('password','secret')]
  return {'type':stype,'view':view,'fields':fields,'revision':'fixture-spec','attributes':{},'diagnostics':[],'capabilities':{'create':False,'update':False,'retire':False},'views':[view]}
 def open_target(self,key):
  _,targets=self._tree()
  if key not in targets:raise ApiError(403,'target_denied','Нет такой конфигурационной ссылки')
  t=copy.deepcopy(targets[key])
  if t['kind'] in ('table','form'):t['spec']=self.view(t['search_type'],t['view'],t['options'])
  return t
 def query(self,stype,spec,q):
  rows=[{'key':stype+'?code=FIXTURE'+str(i),'values':{f['name']:('fixture' if i==0 else f'{f["label"]} {i+1}') for f in spec['fields']},'revision':'fixture-row-'+str(i)} for i in range(12)]
  for f in q['filters']:
   if f['op']=='contains':rows=[r for r in rows if str(f['value']).lower() in str(r['values'].get(f['field'],'')).lower()]
  n=len(rows);rows=rows[q['offset']:q['offset']+q['limit']]
  return {'items':rows,'total':n,'offset':q['offset'],'limit':q['limit'],'has_more':False}
 def snapshots(self,*a):return {'items':[],'can_upload':False,'notice':'Test storage only'}
 def config_operation(self,method,path,data):
  if path=='/configs':return {'items':[{'key':'config/widget_config?code='+v,'view':v,'search_type':'SideBarWdg','login':''} for v in self.overrides]}
  if path=='/config' and method=='GET':
   if data.get('key'):
    v=data['key'].split('=')[-1];text=self.overrides[v];return {'key':data['key'],'view':v,'search_type':'SideBarWdg','login':'','xml':text,'revision':revision(text),'editable':True}
   v=data.get('view','admin_views');m=self._loader(v);return {'view':v,'layers':[{'view':s.view,'origin':s.origin,'xml':s.text} for s in m.sources],'elements':m.elements(),'revision':m.fingerprint(),'editable':False}
  if path=='/sidebar-order':
   v=data['view'];m=self._loader(v)
   if data['revision']!=m.fingerprint():raise ApiError(409,'conflict','Конфигурация изменена')
   base=next(s.text for s in m.sources if s.view==v and s.node is not None);self.overrides[v]=reorder_view(base,v,data['order']);return {'saved':True}
  if path=='/config' and method in ('POST','PATCH'):
   text=data['xml'];root=parse_xml(text);v=data.get('view') if method=='POST' else data['key'].split('=')[-1]
   if view_node(root,v) is None:raise ValueError('Отсутствует выбранный view')
   if method=='PATCH' and revision(self.overrides[v])!=data['revision']:raise ApiError(409,'conflict','Конфигурация изменена')
   self.overrides[v]=text;return {'key':'config/widget_config?code='+v,'revision':revision(text),'saved':True}
  if path=='/graph':
   if not data.get('key'):return {'items':[{'key':'sthpw/'+data['kind']+'?code=FIXTURE','code':'FIXTURE','name':'TEST '+data['kind']}]}
   text=self.schema if data['kind']=='schema' else self.pipeline
   return {'key':data['key'],'code':'FIXTURE','xml':text,'revision':revision(text),'can_save_positions':data['kind']=='pipeline'}
  if path=='/pipeline-positions':
   if data['revision']!=revision(self.pipeline):raise ApiError(409,'conflict','Граф изменён')
   self.pipeline=patch_pipeline_positions(self.pipeline,data['positions']);return {'saved':True}
  if path=='/search-types':return self.catalog()
  if path=='/memberships':
   if not data.get('key'):return {'items':[{'key':'sthpw/login_group?code=fixture','name':'fixture','description':'Test group'}]}
   if method=='GET':return {'key':data['key'],'group':'fixture','users':[{'login':'fixture','name':'Fixture user'},{'login':'second','name':'Second fixture'}],'members':self.members,'revision':revision(self.members),'can_write':True,'limit':5000}
   if data['revision']!=revision(self.members):raise ApiError(409,'conflict','Группа изменена')
   self.members=data['members'];return {'saved':True,'revision':revision(self.members)}
  raise ApiError(501,'fixture_missing','Этот путь не реализован в тестовом хранилище')
