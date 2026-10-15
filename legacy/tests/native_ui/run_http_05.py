"""0.5 real CherryPy HTTP: production messages/Select with test persistence.
No PostgreSQL, full TACTIC transaction or email-send claim. Timeline scope for
fixture/schedule invokes the production timeline service/query builder.
"""
import argparse,json,uuid
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:9147');p.add_argument('--output',default=str(Path(__file__).resolve().parents[2]/'docs/native-ui/0.5/http-05.json'));a=p.parse_args()
s=requests.Session();results=[];h={'X-Tactic-UI':'1'}
def check(name,condition):
 assert condition,name
 results.append({'scenario':name,'passed':True});print('PASS',name,flush=True)
def call(method,path,data=None,headers=None):return s.request(method,a.url+'/api/ui/v2'+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=headers or h,timeout=10)
def ok(method,path,data):
 r=call(method,path,data);assert r.status_code==200,(path,r.status_code,r.text);return r.json()
base={'project':'fixture'}
try:
 check('Messages require a browser session',call('GET','/messages',base).status_code==401)
 login=ok('POST','/session',{'login':'fixture','password':'fixture-only'});h['X-CSRF-Token']=login['csrf'];check('Authenticated fixture session',bool(login['user']))
 inbox=ok('GET','/messages',base);keys={i['message_code'] for i in inbox['items']};check('Inbox is own/project scoped',{'pair','group','legacy','event','progress'}<=keys and 'private' not in keys and 'foreign' not in keys)
 r=call('GET','/message-history',{**base,'message_code':'private'});check('Another users chat is denied',r.status_code==403)
 r=call('GET','/message-history',{**base,'message_code':'foreign'});check('Another project chat is denied',r.status_code==403)
 history=ok('GET','/message-history',{**base,'message_code':'pair','limit':20});old=ok('GET','/message-history',{**base,'message_code':'pair','before':history['next_before'],'limit':100})
 check('History pagination preserves 65 records',len(old['items'])+len(history['items'])==65)
 check('Identical texts are separate message_log IDs',history['items'][-1]['content']['text']==history['items'][-2]['content']['text'] and history['items'][-1]['id']!=history['items'][-2]['id'])
 check('Projectless legacy chat stays accessible to members',ok('GET','/message-history',{**base,'message_code':'legacy'})['legacy_global'])
 check('Initial welcome is not a fabricated log entry',ok('GET','/message-history',{**base,'message_code':'group'})['items']==[])
 send={**base,'message_code':'pair','message':'HTTP <script>not HTML</script> Привет','request_id':str(uuid.uuid4())}
 r=call('POST','/message-send',send,headers={'X-Tactic-UI':'1'});check('Message mutation requires CSRF',r.status_code==403)
 r=call('POST','/message-send',send,headers={**h,'Origin':'https://untrusted.example'});check('Foreign Origin is rejected',r.status_code==403)
 first=ok('POST','/message-send',send);same=ok('POST','/message-send',send);check('Retry returns same response without duplicate insertion',first==same)
 latest=ok('GET','/message-history',{**base,'message_code':'pair'});check('SQLite original API method persisted message_log',latest['items'][-1]['content']['text']==send['message'] and sum(i['content']['text']==send['message'] for i in latest['items'])==1)
 r=call('POST','/message-send',{**send,'message':'different'});check('Reused request ID cannot change content',r.status_code==409)
 r=call('POST','/message-send',{**send,'message_code':'event','request_id':str(uuid.uuid4())});check('System event cannot be overwritten as chat',r.status_code==403)
 r=call('POST','/message-send',{**send,'message':'x\0y','request_id':str(uuid.uuid4())});check('NUL is rejected before mutation',r.status_code==400)
 r=call('PATCH','/subscriptions',{**base,'message_code':'pair','revision':history['revision'],'action':'acknowledge'});check('Stale acknowledgment cannot clear unseen history',r.status_code==409)
 ack=ok('PATCH','/subscriptions',{**base,'message_code':'pair','revision':latest['revision'],'action':'acknowledge'});check('Acknowledgment is observed timestamp, not read receipt',ack['last_cleared']==latest['latest']['timestamp'] and ack['read_receipt'] is False)
 check('New filter reflects last_cleared',not any(i['message_code']=='pair' for i in ok('GET','/messages',{**base,'mode':'new'})['items']))
 target='fixture_deeper/configured_messages';opened=ok('GET','/open',{**base,'target':target});check('Configured SubscriptionWdg resolves to native screen',opened['kind']=='message-center' and opened['options']['show_unsubscribe']=='false')
 configured=ok('GET','/messages',{**base,'target':target});check('Config category controls message list',all(i['category']=='chat' for i in configured['items']))
 hc=ok('GET','/message-history',{**base,'target':target,'message_code':'pair'});check('Widget option disables unsubscribe',not hc['can_unsubscribe'])
 r=call('DELETE','/subscriptions',{**base,'target':target,'message_code':'pair','revision':hc['revision'],'confirm':'UNSUBSCRIBE'});check('Server repeats widget unsubscribe restriction',r.status_code==403)
 exact=ok('POST','/chats',{**base,'users':['bob'],'request_id':str(uuid.uuid4())});group=ok('POST','/chats',{**base,'users':['bob','carol'],'request_id':str(uuid.uuid4())});check('Exact participant sets do not mix pair/group chat',exact['message_code']=='pair' and group['message_code']=='group')
 new=ok('POST','/chats',{**base,'users':['outsider'],'request_id':str(uuid.uuid4())});check('ChatCmd creates a real scoped channel in test persistence',new['created'])
 nh=ok('GET','/message-history',{**base,'message_code':new['message_code']});check('Chat membership reflects both subscriptions',{p['login'] for p in nh['participants']}=={'fixture','outsider'})
 r=call('DELETE','/subscriptions',{**base,'message_code':new['message_code'],'revision':nh['revision'],'confirm':'UNSUBSCRIBE'});check('Unsubscribe preserves message history by contract',r.status_code==200 and not r.json()['deleted_messages'])
 check('Unsubscribed caller loses channel access',call('GET','/message-history',{**base,'message_code':new['message_code']}).status_code==403)
 users=ok('GET','/chat-users',{**base,'query':'bob'});check('Server user lookup returns login/display only',[u['login'] for u in users['items']]==['bob'] and all(set(u)=={'login','name'} for u in users['items']))
 rec={**base,'target':'fixture_native/fixture_items','key':'fixture/item?code=FIXTURE0'};sub=ok('GET','/record-subscription',rec);check('Object event key comes from original key rules',sub['message_code']==rec['key'])
 ok('POST','/record-subscription',{**rec,'revision':sub['revision']});sub=ok('GET','/record-subscription',rec);check('Object subscription stored by original subscribe API',sub['subscribed'])
 ok('DELETE','/record-subscription',{**rec,'revision':sub['revision'],'confirm':'UNSUBSCRIBE'});check('Object unsubscribe does not delete object',ok('GET','/record-subscription',rec)['subscribed'] is False)
 notify={**base,'target':'fixture_deeper/my_notification'};n=ok('GET','/open',notify);check('My Notifications handler carries original hidden scope',n['options']['native_notification_scope'])
 logs=ok('POST','/query',notify);check('Email log is recipient/project scoped, not all admin logs',logs['total']==1 and logs['items'][0]['values']['recipients']=='to: fixture')
 check('Email body is returned as data, not executed', '<script>' in logs['items'][0]['values']['message'])
 check('Direct record request cannot escape recipient scope',call('GET','/record',{**notify,'key':'sthpw/notification_log?id=2'}).status_code==403)
 args={**base,'target':'fixture_deeper/schedule','start':'2026-09-01','end':'2026-09-30','limit':200}
 rows=ok('POST','/timeline',args);page2=ok('POST','/timeline',{**args,'offset':200});check('Timeline has independent date-window pagination',rows['total']==320 and len(rows['items'])==200 and len(page2['items'])==120)
 check('Both configured bars are preserved',len(rows['bars'])==2 and all(len(r['timeline'])==2 for r in rows['items']))
 check('Page overlap not duplicated',len({r['key'] for r in rows['items']+page2['items']})==320)
 filtered=ok('POST','/timeline',{**args,'where':{'field':'status','op':'eq','value':'Complete'}});check('Timeline uses original user predicate',filtered['total']==160)
 check('Outside period is not current table page',ok('POST','/timeline',{**args,'start':'2027-01-01','end':'2027-01-31'})['total']==0)
 check('Excessive date range rejected',call('POST','/timeline',{**args,'end':'2029-01-01'}).status_code==400)
 check('Arbitrary date column refused',call('POST','/timeline',{**args,'start_field':'password','end_field':'end_date'}).status_code==403)
 check('Invalid target remains forbidden',call('POST','/timeline',{**args,'target':'not-configured'}).status_code==403)
 check('Unknown routes remain rejected',call('POST','/message-delete-all',{**base,'target':target}).status_code>=400)
finally:
 Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps({'mode':'real CherryPy; production message/timeline services with test persistence and schema collaborators','results':results},ensure_ascii=False,indent=2))
