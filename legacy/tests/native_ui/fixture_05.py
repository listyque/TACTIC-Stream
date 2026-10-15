"""TEST ONLY. 0.5 production message service + original Select on test tables.
No user database, credentials, triggers or working TACTIC server are simulated
as verified. The actual sidebar and notification field XML come from source.
"""
import json
import copy
from types import SimpleNamespace
from urllib.parse import parse_qs
from fixture_04 import FixtureBackend as Previous
from message_test_store import Stub,ROOT
from timeline_test_store import TimelineStore,Backend as TimelineBackend,spec as timeline_spec
from tactic.ui_api.message_service import MessageService
from tactic.core.config_model import ConfigModel,ConfigSource,SidebarProjection
from tactic.core.notification_filters import NotificationLogScope
from tactic.core.query_model import apply_tree
from tactic.ui_api.contracts import ApiError,revision
from tactic.core.timeline_model import date_window

XML='''<config><fixture_deeper title="TEST FIXTURE 0.5 · Исходные handlers"><element name="configured_messages" title="TEST · Configured subscriptions"><display class="tactic.ui.app.SubscriptionWdg"><category>chat</category><show_unsubscribe>false</show_unsubscribe></display></element><element name="my_notification"/><element name="schedule" title="TEST · Schedule 320"><display class="tactic.ui.panel.ViewPanelWdg"><search_type>fixture/schedule</search_type><view>table</view></display></element></fixture_deeper></config>'''
class FixtureBackend(MessageService,Previous):
 site='';allow_writes=True
 def __init__(self,*a,**kw):
  super().__init__(*a,**kw);self.message_store=TimelineStore(login='fixture',project='fixture');self.message_store.seed();self.message_store.schedule();self.timing=TimelineBackend(self.message_store)
  for i,project,user in [(1,'fixture','fixture'),(2,'fixture','bob'),(3,'other','fixture')]:
   self.message_store.row('notification_log',project_code=project,login='system',subject='TEST email '+str(i),message='<script>window.bad=1</script> TEST plain-text email body')
   self.message_store.row('notification_login',notification_log_id=i,project_code=project,login=user,type='to')
  self.message_store.db.commit()
 def _project(self):return self.state.get()
 def _stub(self):return Stub(self.message_store)
 def _write(self,callback):
  if not self.allow_writes:raise ApiError(403,'read_only','TEST write disabled')
  with self.message_store.db:return callback()
 def _object(self,stype,key):
  if stype=='sthpw/notification_log':
   q=self.message_store.search(stype);NotificationLogScope().alter_search(q);q.add_filter('id',int(parse_qs(key.split('?')[-1]).get('id',['-1'])[0]));obj=q.get_sobject()
   if not obj:raise ApiError(403,'notification_scope','Not your notification')
   return obj
  row=self.record(stype,key,self.view(stype,'table'));v=row['values']
  return SimpleNamespace(get_base_search_type=lambda:stype,get_search_key=lambda:key,get_value=lambda n,**kw:v.get(n),get_sobject_dict=lambda:dict(v,__search_key__=key))
 def message_operation(self,method,path,data):
  self.message_store.project=self._project()
  with self.message_store.bind():return MessageService.message_operation(self,method,path,data)
 def _tree(self):
  tree,targets=super()._tree()
  default=(ROOT/'src/tactic/ui/config/DEFAULT-conf.xml').read_text()
  project=SidebarProjection(lambda v,p:ConfigModel(v,[ConfigSource(XML,v,'TEST XML'),ConfigSource(default,'definition','original DEFAULT')]),lambda n:True,self._project(),'fixture')
  extra=project.build(['fixture_deeper']);tree+=extra;targets.update(project.targets);return tree,targets
 def view(self,stype,view,options=None):
  if stype=='fixture/schedule':return timeline_spec()
  spec=super().view(stype,view,options)
  if stype=='sthpw/notification_log':
   for f in spec['fields']:
    f.update(read_only=True,supported=True,reason='')
    if f['name']=='recipients':f.update(storage=False,provider='notification-recipients')
   spec['capabilities']={'create':False,'update':False,'retire':False}
  return spec
 def notification_query(self,spec,query,key=None):
  self.message_store.project=self._project()
  with self.message_store.bind():
   q=self.message_store.search('sthpw/notification_log');NotificationLogScope().alter_search(q)
   if key:q.add_filter('id',int(parse_qs(key.split('?')[-1]).get('id',['-1'])[0]))
   if query:
    apply_tree(q,query.get('where'),spec['fields']);total=q.get_count();q.add_order_by(query['sort']['field'],query['sort']['direction']);q.set_offset(query['offset']);q.set_limit(query['limit'])
   else:total=q.get_count()
   objects=q.get_sobjects();recipients=self._notification_recipients([o.get_id() for o in objects]);rows=[{'key':o.get_search_key(),'values':{f['name']:recipients.get(str(o.get_id()),'') if f['name']=='recipients' else o.get_value(f['name']) for f in spec['fields']},'revision':revision(o.get_sobject_dict())} for o in objects]
   if key:
    if not rows:raise ApiError(403,'notification_scope','Not a notification for current login/project')
    return rows[0]
   return {'items':rows,'total':total,'offset':query['offset'],'limit':query['limit'],'has_more':query['offset']+len(rows)<total}
 def query(self,stype,spec,query):
  if stype=='sthpw/notification_log':return self.notification_query(spec,query)
  if stype=='fixture/schedule':
   self.message_store.project=self._project()
   with self.message_store.bind():
    s=self.timing._query_search(stype,spec,query);total=s.get_count();s.add_order_by(query['sort']['field'],query['sort']['direction']);s.set_offset(query['offset']);s.set_limit(query['limit']);rows=self.timing._serialize_many(s.get_sobjects(),spec)
    return {'items':rows,'total':total,'offset':query['offset'],'limit':query['limit'],'has_more':query['offset']+len(rows)<total}
  return super().query(stype,spec,query)
 def record(self,stype,key,spec):
  if stype=='sthpw/notification_log':return self.notification_query(spec,None,key)
  if stype=='fixture/schedule':
   q=self.message_store.search('sthpw/records');q.add_filter('id',int(parse_qs(key.split('?')[-1]).get('id',['-1'])[0]));return self.timing._serialize_many(q.get_sobjects(),spec)[0]
  return super().record(stype,key,spec)
 def timeline(self,stype,spec,data):
  if stype=='fixture/schedule':
   self.message_store.project=self._project()
   with self.message_store.bind():return self.timing.timeline(stype,spec,data)
  # Previous fixture records are in the old synthetic dictionary. This fallback
  # exists ONLY to regression-test older UI flows. Production has no such path.
  from tactic.ui_api.contracts import clean_query
  q=clean_query(dict(data,offset=0,limit=200),spec['fields']);source=self.query(stype,spec,q)
  start,end,exclusive=date_window(data['start'],data['end']);bars=[]
  if data.get('start_field') and data.get('end_field'):bars=[{'id':'0','start_field':data['start_field'],'end_field':data['end_field'],'label':'TEST original dates','color':''}]
  else:
   for f in spec['fields']:
    for b in f.get('bars',[]):bars.append({'id':str(len(bars)),'start_field':b['start_date_col'],'end_field':b['end_date_col'],'label':b['start_date_col'],'color':''})
  if not bars:raise ApiError(400,'fields','Select configured date columns')
  rows=[]
  for row in source['items']:
   timeline=[dict(b,start=row['values'].get(b['start_field']),end=row['values'].get(b['end_field'])) for b in bars]
   if any(b['start'] and str(b['start'])<exclusive and str(b['end'] or b['start'])>=start for b in timeline):row=dict(row,timeline=timeline);rows.append(row)
  total=len(rows);offset=int(data.get('offset',0));limit=int(data.get('limit',200));rows=rows[offset:offset+limit]
  return {'items':rows,'total':total,'offset':offset,'limit':limit,'has_more':offset+len(rows)<total,'bars':bars,'window':{'start':start,'end':end},'notice':'TEST previous fixture projection, not the live database'}
