"""0.4 real CherryPy transport tests. Synthetic data, actual Select predicate SQL.
Production task/hour/relationship command semantics have separate unit tests;
this HTTP fixture is not a live TACTIC database.
"""
import argparse,json
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:9147');p.add_argument('--output',default=str(Path(__file__).resolve().parents[2]/'docs/native-ui/0.4/http-04.json'));a=p.parse_args()
s=requests.Session();results=[];h={'X-Tactic-UI':'1'}
def check(name,condition):
 assert condition,name
 results.append({'scenario':name,'passed':True});print('PASS',name,flush=True)
def call(method,path,data=None,headers=None):
 return s.request(method,a.url+'/api/ui/v2'+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=headers or h,timeout=8)
def leaf(n,op,v=None):return {'field':n,'op':op,'value':v}
def group(op,*items):return {'op':op,'children':list(items)}
def walk(nodes):
 for n in nodes:
  yield n
  yield from walk(n.get('children',[]))
try:
 r=call('POST','/session',{'login':'fixture','password':'fixture-only'});h['X-CSRF-Token']=r.json()['csrf'];check('Session for new feature contracts',r.status_code==200)
 args={'project':'fixture','target':'fixture_native/fixture_items'}
 r=call('GET','/sidebar',{'project':'fixture'});check('Project links from XML configuration',r.status_code==200 and 'fixture_native/fixture_items' in r.text)
 r=call('GET','/open',args);check('New arbitrary SearchType resolved from config',r.status_code==200 and r.json()['search_type']=='fixture/item')
 def query(where=None,state='active'):
  r=call('POST','/query',{**args,'where':where or group('and'),'record_state':state,'limit':50});assert r.status_code==200,r.text;return r.json()
 original=query();check('Active result excludes one archived object',original['total']==4)
 null=query(leaf('name','null'));check('NULL is not conflated with empty string',len(null['items'])==1 and null['items'][0]['values']['name'] is None)
 empty=query(leaf('name','empty'));check('Original empty semantics include NULL and empty text',empty['total']==2)
 notnull=query(leaf('name','not_null'));check('Actual Select emits IS NOT NULL rather than IS NULL',notnull['total']==3)
 boolean=group('and',group('or',leaf('name','eq','Atlas'),leaf('name','eq','Mesa')),leaf('quantity','eq',0))
 selected=query(boolean);check('Nested OR inside AND with numeric zero',selected['total']==1 and selected['items'][0]['values']['name']=='Atlas')
 r=call('POST','/query',{**args,'where':leaf('password','eq','x')});check('Unknown predicate column rejected',r.status_code==400)
 r=call('POST','/query',{**args,'where':group('and',*[leaf('quantity','eq',0)]*41)});check('Predicate complexity limit enforced',r.status_code==400)
 r=call('POST','/query',{**args,'where':leaf('quantity','gt',"0 OR 1=1")});check('Numeric SQL injection rejected before query',r.status_code==400)
 r=call('POST','/saved-view',{**args,'title':'HTTP native search','where':boolean});check('Search saved in legacy FilterData format',r.status_code==200)
 r=call('GET','/sidebar',{'project':'fixture'});sid=next(n['id'] for n in walk(r.json()['sections']) if n.get('title')=='HTTP native search')
 saved_args={**args,'target':sid};call('GET','/open',saved_args)
 r=call('POST','/query',{**saved_args,'limit':50});check('Reopened personal sidebar view repeats predicate result',r.status_code==200 and r.json()['total']==1)
 r=call('POST','/saved-view',{**args,'title':'Cannot silently alter','where':group('and',leaf('name','contains','%'))});check('Unrepresentable literal wildcard saved query rejected explicitly',r.status_code==400)
 row=next(r for r in original['items'] if r['values']['name']=='Atlas');base={**args,'key':row['key']}
 rel={**base,'related_type':'fixture/tag'}
 r=call('GET','/relationship',rel);rev=r.json()['revision'];check('Instance relation reports junction type',r.status_code==200 and r.json()['instance_type']=='fixture/item_in_tag')
 r=call('GET','/relation-candidates',rel);candidates=r.json()['items'];linked=next(x for x in candidates if x['linked']);unlinked=next(x for x in candidates if not x['linked']);check('Candidates identify already-linked objects',len(candidates)==3 and linked['links']==1)
 op={**rel,'revision':rev,'other_key':unlinked['key'],'other_revision':unlinked['revision']}
 r=call('POST','/relationship',op);check('Link operation changes membership, not object copies',r.status_code==200 and r.json()['direct_object_delete'] is False)
 r=call('POST','/relationship',op);check('Stale membership revision rejected',r.status_code==409)
 current=call('GET','/relationship',rel).json();op['revision']=current['revision'];op['confirm_count']=2
 r=call('DELETE','/relationship',op);check('Wrong junction deletion count rejected',r.status_code==409)
 op['confirm_count']=1;r=call('DELETE','/relationship',op);check('Unlink removes junction only in command contract',r.status_code==200 and r.json()['unlinked']==1 and not r.json()['direct_object_delete'])
 r=call('POST','/query',{'project':'fixture','target':'fixture_native/fixture_tags','limit':50});check('All tag objects remain after unlink',r.status_code==200 and r.json()['total']==3)
 r=call('GET','/relations',base);target=next(x['target'] for x in r.json()['items'] if x['search_type']=='fixture/tag');r=call('POST','/query',{**args,'target':target,'limit':50});check('Related view reads the updated schema membership',r.status_code==200 and r.json()['total']==1)
 r=call('GET','/tasks',base);tasks=r.json();check('Tasks are separated by their own task pipelines',r.status_code==200 and len(tasks['pipelines'])==2 and len(tasks['items'])==6)
 t=tasks['items'][0];targs={**base,'task':t['key']}
 r=call('PATCH','/task-change',{**targs,'revision':t['revision'],'values':{'status':'In Progress'}});check('Status update uses revisioned task endpoint',r.status_code==200 and r.json()['values']['status']=='In Progress')
 r=call('PATCH','/task-change',{**targs,'revision':t['revision'],'values':{'status':'Complete'}});check('Stale task revision cannot overwrite newer status',r.status_code==409)
 form=call('GET','/task-form',targs).json();rev=form['record']['revision']
 preview=call('POST','/task-form-preview',{**targs,'revision':rev,'values':{'pipeline_code':'alternate'}});check('Dependent selector preview flags incompatible current status',preview.status_code==200 and preview.json().get('dependency_notice'))
 check('Preview performs no persistent task mutation',call('GET','/task-form',targs).json()['record']['values']['pipeline_code']=='task')
 r=call('PATCH','/task-change',{**targs,'revision':rev,'values':{'pipeline_code':'alternate'}});check('Cannot persist new pipeline with foreign status',r.status_code==400)
 r=call('PATCH','/task-change',{**targs,'revision':rev,'values':{'pipeline_code':'alternate','status':'Todo'}});check('Compatible dependent fields save together',r.status_code==200 and r.json()['values']['status']=='Todo')
 r=call('GET','/task-form',{**targs,'key':'fixture/item?code=FIXTURE1'});check('Task from a different parent is denied',r.status_code==403)
 hourargs={**targs,'start':'2026-09-28','end':'2026-10-04'};hours=call('GET','/task-hours',hourargs).json()
 hop={**hourargs,'revision':hours['revision'],'cells':[{'day':'2026-09-30','category':'regular','value':'2.5'},{'day':'2026-09-30','category':'overtime','value':'1'}],'confirm':'SAVE_HOURS'}
 r=call('PATCH','/task-hours',hop);check('Weekly work-hour changed cells through HTTP',r.status_code==200)
 r=call('PATCH','/task-hours',hop);check('Stale work-hour range is rejected',r.status_code==409)
 hours=call('GET','/task-hours',hourargs).json();check('Regular and overtime returned separately',len(hours['items'])==2 and {x['category'] for x in hours['items']}=={'regular','overtime'})
 r=call('PATCH','/task-hours',{**hourargs,'revision':hours['revision'],'cells':[{'day':'2026-09-30','category':'regular','value':'0'}],'confirm':'SAVE_HOURS'});after=call('GET','/task-hours',hourargs).json();check('Zero clears only corresponding hour category',r.status_code==200 and len(after['items'])==1 and after['items'][0]['category']=='overtime')
 check('Zero hours did not remove task',call('GET','/task-form',targs).status_code==200)
 genargs={**base,'key':'fixture/item?code=FIXTURE1'};gen=call('GET','/task-generate',genargs).json();check('Generation preview exposes pipeline process choices',gen['existing']==0 and len(gen['processes'])==2)
 r=call('POST','/task-generate',{**genargs,'revision':gen['revision'],'processes':['model'],'confirm':'GENERATE'});check('Explicit process generation endpoint',r.status_code==200 and r.json()['created']==1)
 state=call('GET','/record-state',base).json();r=call('POST','/record-state',{**base,'revision':state['revision'],'action':'retire','confirm':'RETIRE'});check('Archive returns non-deletion contract',r.status_code==200 and r.json()['retired'] and not r.json()['deleted'])
 check('Archived record leaves active results',query()['total']==3)
 check('Archive query explicitly includes retired records',query(state='retired')['total']==2)
 history=call('GET','/history',base).json();check('Record history can be loaded after retirement',history['items'][-1]['action']=='retire')
 state=call('GET','/record-state',base).json();r=call('POST','/record-state',{**base,'revision':state['revision'],'action':'reactivate','confirm':'REACTIVATE'});check('Reactivate restores active record',r.status_code==200 and not r.json()['retired'] and query()['total']==4)
 r=call('POST','/task-form-preview',{**targs,'revision':rev,'values':{}},headers={'X-Tactic-UI':'1'});check('Preview also requires CSRF for POST',r.status_code==403)
 r=call('PATCH','/task-hours',hop,headers={**h,'Origin':'https://foreign.invalid'});check('Hour mutation rejects foreign Origin',r.status_code==403)
 r=requests.get(a.url+'/api/ui/v2/tasks',params=base,timeout=8);check('Anonymous task query denied',r.status_code==401)
 r=call('POST','/execute_cmd',{**base,'class_name':'arbitrary'});check('No arbitrary command dispatch endpoint',r.status_code==404)
finally:
 Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps({'transport':'real requests HTTP to bundled CherryPy','backend':'TEST fixture; actual TACTIC Select for queries only, not a TACTIC database','scenarios':results},ensure_ascii=False,indent=2)+'\n')
