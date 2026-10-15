"""TEST ONLY. Upstream admin XML plus synthetic projects/records for UI contracts.
Production code never imports this module. No live TACTIC DB/workflow claim.
"""
import copy
import json
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import date,timedelta
from unittest.mock import patch
from fixture_deep import FixtureBackend as Previous
from tactic.core.config_model import ConfigSource,ConfigModel,SidebarProjection,parse_xml,view_node,xml_text
from tactic.core.query_model import apply_tree,apply_saved,merge_saved
from tactic.ui_api.contracts import ApiError,revision,clean_values
from tactic.ui_api.record_service import related_id,decode_related_id
from test_sql_builder_04 import BuilderSearch

PROJECT_XML='''<config><fixture_native title="TEST FIXTURE · Данные проекта"><element name="fixture_items" title="Объекты проекта"><display class="tactic.ui.panel.ViewPanelWdg"><search_type>fixture/item</search_type><view>table</view></display></element><element name="fixture_tags" title="Теги"><display class="tactic.ui.panel.ViewPanelWdg"><search_type>fixture/tag</search_type><view>table</view></display></element><element name="fixture_task_hours" title="Задачи · исходный my_task"><display class="tactic.ui.panel.ViewPanelWdg"><search_type>sthpw/task</search_type><view>my_task</view></display></element></fixture_native></config>'''
TASK_PIPELINES={'task': ['Open','In Progress','Complete'],'alternate':['Todo','Doing','Done']}

class FixtureBackend(Previous):
 def __init__(self,*a,**kw):
  super().__init__(*a,**kw);self.links={('fixture/item?code=FIXTURE0','fixture/tag?code=FIXTURE0')};self.archived={'fixture/item?code=FIXTURE4'};self.history_data={};self.hours={};self.new_tasks=[];self.task_values={};self.active_target={}
 def _tree(self):
  tree,targets=super()._tree()
  if self.state.get()=='fixture':
   proj=SidebarProjection(lambda v,p:ConfigModel(v,[ConfigSource(PROJECT_XML,v,'TEST PROJECT XML')]),lambda n:True,'fixture','fixture');tree+=proj.build(['fixture_native']);targets.update(proj.targets)
  return tree,targets
 def view(self,stype,view,options=None):
  spec=super().view(stype,view,options)
  if stype in ('fixture/item','fixture/tag'):
   fields=['code','name','description','quantity'] if stype=='fixture/item' else ['code','name','description']
   spec['fields']=[{'name':n,'label':n,'storage':True,'supported':True,'read_only':n=='code','kind':'integer' if n=='quantity' else 'text','options':[],'reason':'','handler':'TEST DATA','nullable':n!='code'} for n in fields]
   spec['capabilities']={'create':False,'update':True,'retire':True};spec['views']=['table','edit']
  if stype=='sthpw/task' and view=='my_task':
   from fixture_backend import FixtureBackend as SourceConfigFixture
   spec=SourceConfigFixture.view(self,stype,view,options)
   # Field order/title comes from the shipped my_task view. Data is synthetic.
   for f in spec['fields']:
    if f['name']=='work_hours':f.update(handler='tactic.ui.table.WorkHoursElementWdg',renderer='work-hours',storage=False,supported=True,read_only=True)
  return spec
 def open_target(self,key):
  if '/~related/' in key and not key.endswith('/TEST'):
   root,token=key.rsplit('/~related/',1);parent_key,stype=decode_related_id(token);base=self.open_target(root)
   allowed=self._relation_rows(base['search_type'],parent_key)
   if stype not in allowed:raise ApiError(403,'relation','Not declared in test schema')
   t={'id':key,'kind':'table','name':stype,'title':('Related tasks' if stype=='sthpw/task' else stype)+' · TEST relationship','search_type':stype,'view':'table','options':{'native_parent_key':parent_key,'native_parent_type':base['search_type']},'attributes':{},'spec':self.view(stype,'table')}
  else:t=super().open_target(key)
  self.active_target=t;return t
 def _row(self,stype,spec,i):
  if stype not in ('fixture/item','fixture/tag'):return super()._row(stype,spec,i)
  key=stype+'?code=FIXTURE'+str(i)
  values={'code':'FIXTURE'+str(i),'name':(['Atlas','Mesa',None,'','Orion'][i] if stype=='fixture/item' else ['Outdoor','Interior','Review'][i]),'description':'TEST record '+str(i),'quantity':[0,2,4,8,16][i]}
  values.update(self.values.get(key,{}));return {'key':key,'values':{f['name']:values.get(f['name']) for f in spec['fields']},'revision':revision(values)}
 def record(self,stype,key,spec):
  if key.startswith('sthpw/task?code=WORK'):return self._task_record(key,spec)
  return super().record(stype,key,spec)
 def _relation_rows(self,stype,key):
  if stype=='fixture/item':return {'fixture/tag':[b for a,b in sorted(self.links) if a==key],'sthpw/task':[t['key'] for t in self._tasks() if t['parent']==key]}
  if stype=='fixture/tag':return {'fixture/item':[a for a,b in sorted(self.links) if b==key]}
  if stype=='sthpw/task' and key.startswith('sthpw/task?code=WORK'):
   return {'fixture/item':[next(t['parent'] for t in self._tasks() if t['key']==key)]}
  return {'sthpw/task':['sthpw/task?code=FIXTURE'+str(i) for i in range(12)]}
 def query(self,stype,spec,q):
  count=5 if stype=='fixture/item' else 3 if stype=='fixture/tag' else 12
  rows=[self._row(stype,spec,i) for i in range(count)]
  if stype=='sthpw/task' and spec['view']=='my_task':rows=[self._task_record(t['key']) for t in self._tasks()]
  opts=self.active_target.get('options',{})
  if opts.get('native_parent_key'):
   keys=self._relation_rows(opts['native_parent_type'],opts['native_parent_key']).get(stype,[])
   rows=[self.record(stype,key,spec) for key in keys]
  state=q.get('record_state','active');rows=[r for r in rows if state=='all' or (r['key'] in self.archived)==(state=='retired')]
  # Exercise the SAME normalized query emitter against a test SQLite predicate
  # table. This table is not a TACTIC database; no writes use it.
  fields=[f for f in spec['fields'] if f.get('storage')];names=[f['name'] for f in fields]
  for n in ('project_code','search_type'):
   if n not in names:fields.append({'name':n,'kind':'text','storage':True});names.append(n)
  with sqlite3.connect(':memory:') as db:
   db.create_function('regexp',2,lambda p,v:None if v is None else bool(re.search(p,str(v),re.I)))
   db.execute('create table records (__key text,'+','.join('"'+f['name']+'" '+('NUMERIC' if f['kind'] in ('integer','number','boolean') else 'TEXT') for f in fields)+')')
   for row in rows:db.execute('insert into records values ('+','.join(['?']*(len(fields)+1))+')',[row['key']]+[self.state.get() if n=='project_code' else 'fixture/item' if n=='search_type' else str(row['values'].get(n)) if isinstance(row['values'].get(n),(dict,list)) else row['values'].get(n) for n in names])
   pred=BuilderSearch(fields=fields);pred.get_base_search_type=lambda:stype
   if opts.get('filter'):
    with patch('pyasm.search.SearchType.column_exists',side_effect=lambda st,n:n in names),patch('pyasm.search.SearchType.get_tactic_type',side_effect=lambda st,n:'integer' if n=='quantity' else 'varchar'):
     apply_saved(pred,opts['filter'],login='fixture',project=self.state.get())
   apply_tree(pred,q.get('where'),fields)
   keys={x[0] for x in db.execute('select __key from records where '+pred.sql())}
   rows=[r for r in rows if r['key'] in keys]
  for sort in [q['sort']] if q.get('sort') else []:
   rows.sort(key=lambda r:(r['values'].get(sort['field']) is None,r['values'].get(sort['field'])),reverse=sort['direction']=='desc')
  total=len(rows);rows=rows[q['offset']:q['offset']+q['limit']]
  return {'items':rows,'total':total,'offset':q['offset'],'limit':q['limit'],'has_more':q['offset']+len(rows)<total}
 def _tasks(self):
  parent='fixture/item?code=FIXTURE0';records=[]
  for i in range(6):
   pipeline='task' if i<3 else 'alternate';status=TASK_PIPELINES[pipeline][i%3]
   values={'code':'WORK'+str(i),'description':'TEST task '+str(i),'process':['model','review'][i%2],'context':['model','review'][i%2],'status':status,'assigned':'fixture','pipeline_code':pipeline,'bid_start_date':'2026-09-28','bid_end_date':'2026-10-02'}
   key='sthpw/task?code=WORK'+str(i);values.update(self.task_values.get(key,{}));records.append({'key':key,'parent':parent,'values':values})
  extra=copy.deepcopy(self.new_tasks)
  for row in extra:row['values'].update(self.task_values.get(row['key'],{}))
  return records+extra
 def _task_spec(self):
  return {'type':'sthpw/task','view':'edit','fields':[{'name':n,'label':n,'kind':'select' if n in ('pipeline_code','status','process') else 'text','storage':True,'read_only':n=='code','supported':True,'reason':'','handler':'TEST','nullable':False,'options':[{'value':x,'label':x} for x in list(TASK_PIPELINES) if n=='pipeline_code'] if n=='pipeline_code' else [{'value':x,'label':x} for x in ['model','review']] if n=='process' else [],'choice_refresh':n in ('pipeline_code','process')} for n in ['code','description','process','context','pipeline_code','status','assigned','bid_start_date','bid_end_date']],'capabilities':{'update':True,'create':False,'retire':False},'diagnostics':[]}
 def _task_record(self,key,spec=None):
  row=next((r for r in self._tasks() if r['key']==key),None)
  if row is None:raise ApiError(404,'task','Missing test task')
  return {'key':key,'values':row['values'],'revision':revision(row['values'])}
 def _task_form(self,key,values=None):
  record=self._task_record(key);spec=self._task_spec();prospective={**record['values'],**(values or {})};names=TASK_PIPELINES.get(prospective['pipeline_code'])
  if names is None:raise ApiError(400,'pipeline','Unknown test pipeline')
  for f in spec['fields']:
   if f['name']=='status':f['options']=[{'value':x,'label':x} for x in names]
  form={'spec':spec,'record':{**record,'values':prospective}}
  if prospective['status'] not in names:form['dependency_notice']='Выберите статус из нового task pipeline перед сохранением'
  return form
 def form(self,stype,key=None):
  if key and key.startswith('sthpw/task?code=WORK'):return self._task_form(key)
  return super().form(stype,key)
 def prepare_form(self,stype,key,values):
  return self._task_form(key,values) if key and key.startswith('sthpw/task?code=WORK') else self.form(stype,key)
 def _check(self,current,expected):
  if current!=expected:raise ApiError(409,'conflict','TEST: данные изменились')
 def config_operation(self,method,path,data):
  if path=='/relations':
   opened=self.open_target(data['target']);rows=self._relation_rows(opened['search_type'],data['key']);return {'items':[{'search_type':st,'count':len(keys),'relationship':'instance' if st in ('fixture/item','fixture/tag') and opened['search_type'] in ('fixture/item','fixture/tag') else 'search_type','target':related_id(data['target'],data['key'],st)} for st,keys in rows.items()]}
  if path in ('/relationship','/relation-candidates'):
   self.open_target(data['target']);current=revision(sorted(self.links));source=data['key'];stype=data['related_type']
   if path=='/relationship' and method=='GET':return {'revision':current,'count':sum(1 for a,b in self.links if a==source),'instance_type':'fixture/item_in_tag','can_write':True,'notice':'TEST FIXTURE · original-shaped instance membership','target':related_id(data['target'],source,stype)}
   if path=='/relation-candidates':
    spec=self.view(stype,'table');items=[self._row(stype,spec,i) for i in range(3)];items=[{**r,'linked':(source,r['key']) in self.links,'links':int((source,r['key']) in self.links)} for r in items if data.get('keyword','').lower() in str(r['values']['name']).lower()];return {'items':items,'spec':spec,'total':len(items),'offset':0,'limit':30,'revision':current,'can_write':True,'instance_type':'fixture/item_in_tag'}
   self._check(current,data['revision']);row=self.record(stype,data['other_key'],self.view(stype,'table'));self._check(row['revision'],data['other_revision']);pair=(source,data['other_key'])
   if method=='POST':
    if pair in self.links:raise ApiError(409,'already_linked','TEST duplicate')
    self.links.add(pair);return {'linked':True,'instance_key':'fixture/item_in_tag?code=TEST','direct_object_delete':False}
   if pair not in self.links or data.get('confirm_count')!=1:raise ApiError(409,'link_count','TEST count changed')
   self.links.remove(pair);return {'unlinked':1,'direct_object_delete':False}
  if path in ('/tasks','/task-form','/task-form-preview','/task-change','/task-generate','/task-hours'):
   parent=data['key']
   if parent.startswith('sthpw/task?code=WORK'):parent=next(r['parent'] for r in self._tasks() if r['key']==parent)
   records=[r for r in self._tasks() if r['parent']==parent]
   if path=='/tasks':
    items=[{'key':r['key'],'values':r['values'],'task':r['values'],'revision':revision(r['values']),'task_pipeline':r['values']['pipeline_code'],'allowed_statuses':TASK_PIPELINES[r['values']['pipeline_code']],'retired':False} for r in records];offset=int(data.get('offset',0));limit=int(data.get('limit',100));return {'items':items[offset:offset+limit],'total':len(items),'offset':offset,'limit':limit,'spec':self._task_spec(),'pipelines':[{'code':k,'statuses':[{'name':x,'color':None} for x in v]} for k,v in TASK_PIPELINES.items()],'parent_title':'Atlas · TEST FIXTURE','can_write':True,'can_generate':True}
   if path=='/task-generate':
    current=revision(records)
    if method=='GET':return {'revision':current,'pipeline':'production','processes':[{'name':'model','type':'manual'},{'name':'review','type':'approval'}],'existing':len(records),'can_write':True,'notice':'TEST task generation only, not the production TaskGenerator'}
    self._check(current,data['revision'])
    if data.get('confirm')!='GENERATE':raise ApiError(400,'confirmation','Confirm generation')
    made=[]
    for name in data.get('processes') or ['model','review']:
     if any(r['values']['process']==name for r in records):continue
     i=6+len(self.new_tasks);key='sthpw/task?code=WORK'+str(i);r={'key':key,'parent':parent,'values':{'code':'WORK'+str(i),'process':name,'context':name,'status':'Open','pipeline_code':'task','assigned':'','description':'Generated TEST task'}};self.new_tasks.append(r);made.append(key)
    return {'created':len(made),'keys':made}
   key=data['task']
   if not any(r['key']==key for r in records):raise ApiError(403,'task_scope','TEST task parent mismatch')
   if path=='/task-form':return self._task_form(key)
   if path=='/task-hours':
    start=date.fromisoformat(data['start']) if data.get('start') else date(2026,9,27);end=date.fromisoformat(data['end']) if data.get('end') else start+timedelta(days=6);entries=self.hours.setdefault(key,{})
    chosen={k:v for k,v in entries.items() if str(start)<=k.split('|')[0]<=str(end)};current=revision(chosen)
    if method=='GET':return {'items':[{'key':'work-hour:'+k,'day':k.split('|')[0]+' 00:00:00','category':k.split('|')[1],'straight_time':v,'login':'fixture','start_time':'','end_time':''} for k,v in chosen.items()],'revision':current,'can_write':True,'unit':'hour','show_overtime':True,'login':'fixture','days_per_page':7,'field':data.get('field','work_hours'),'notice':'TEST FIXTURE · no work-hour database','start':str(start),'end':str(end)}
    self._check(current,data['revision'])
    if data.get('confirm')!='SAVE_HOURS':raise ApiError(400,'confirmation','Confirm hours')
    for cell in data['cells']:
     identity=cell['day']+'|'+cell['category'];amount=float(cell['value'] or 0)
     if amount:entries[identity]=amount
     else:entries.pop(identity,None)
    return {'saved':True,'cells':len(data['cells'])}
   self._check(self._task_record(key)['revision'],data['revision']);values=data['values'];form=self._task_form(key,values)
   if path=='/task-form-preview':return form
   if form.get('dependency_notice'):raise ApiError(400,'dependency',form['dependency_notice'])
   cleaned=clean_values(values,form['spec']['fields']);self.task_values.setdefault(key,{}).update(cleaned);self.history_data.setdefault(key,[]).append({'key':'log:'+str(len(self.history_data.get(key,[]))),'login':'fixture','timestamp':'2026-09-30 20:00:00','action':'update'});return self._task_record(key)
  if path in ('/record-state','/history'):
   opened=self.open_target(data['target']);key=data['key'];row=self.record(opened['search_type'],key,opened['spec'])
   if path=='/history':return {'items':list(reversed(self.history_data.get(key,[]))),'total':len(self.history_data.get(key,[])),'offset':0,'limit':100,'source':data.get('source','changes'),'notice':'TEST FIXTURE journal'}
   if method=='GET':return {'revision':row['revision'],'retired':key in self.archived,'can_write':opened['search_type'].startswith('fixture/')}
   self._check(row['revision'],data['revision']);action=data['action']
   if data.get('confirm')!=action.upper():raise ApiError(400,'confirmation','Confirm state change')
   if (key in self.archived)==(action=='retire'):raise ApiError(409,'state','Already in this state')
   if action=='retire':self.archived.add(key)
   elif action=='reactivate':self.archived.discard(key)
   else:raise ApiError(400,'action','Unknown action')
   self.values.setdefault(key,{})['s_status']='retired' if action=='retire' else None
   self.history_data.setdefault(key,[]).append({'key':'state:'+str(len(self.history_data.get(key,[]))),'login':'fixture','timestamp':'2026-09-30 20:00:00','action':action});return {'retired':key in self.archived,'key':key,'deleted':False}
  if path=='/saved-view':
   target=self.open_target(data['target']);spec=target['spec'];from tactic.ui_api.contracts import clean_query
   q=clean_query(data,spec['fields']);filters=merge_saved(target['options'].get('filter') or [],q['where'],spec['fields'],'Sqlite')
   view='my_view_fixture';root=parse_xml(self.overrides.get(view,'<config><my_view_fixture/></config>'));v=view_node(root,view);e=ET.SubElement(v,'element',name='saved_'+str(len(list(v))),title=data['title']);d=ET.SubElement(e,'display',{'class':'tactic.ui.panel.ViewPanelWdg'})
   for k,value in [('search_type',target['search_type']),('view',target['view']),('filter',json.dumps(filters))]:ET.SubElement(d,k).text=value
   self.overrides[view]=xml_text(root);return {'saved':True}
  return super().config_operation(method,path,data)
