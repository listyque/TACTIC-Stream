"""0.6 HTTP contracts through bundled CherryPy, not a live TACTIC database.
Collection commands/Select/staging are real; schema, authentication, check-in
persistence and Snapshot trigger collaborators are explicitly TEST-only.
"""
import argparse,hashlib,json,uuid
from pathlib import Path
import requests
p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:9147');p.add_argument('--output',default=str(Path(__file__).resolve().parents[2]/'docs/native-ui/0.6/http-06.json'));a=p.parse_args()
s=requests.Session();results=[];h={'X-Tactic-UI':'1'};CHUNK=4*1024*1024
sha=lambda b:hashlib.sha256(b).hexdigest()
fp=lambda b:sha(b''.join(hashlib.sha256(b[o:o+CHUNK]).digest() for o in range(0,len(b),CHUNK)))
def check(name,value):
 assert value,name
 results.append({'scenario':name,'passed':True});print('PASS',name,flush=True)
def call(method,path,data=None,headers=None):return s.request(method,a.url+'/api/ui/v2'+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=headers or h,timeout=30)
def ok(method,path,data):
 r=call(method,path,data);assert r.status_code==200,(path,r.status_code,r.text);return r.json()
def binary(job,body,offset=0,checksum=None,headers=None,extra=None):
 return s.patch(a.url+'/api/ui/v2/upload-chunk',params=dict(base,upload_id=job['id'],offset=offset,sha256=checksum or sha(body),**(extra or {})),data=body,headers=headers or dict(h,**{'Content-Type':'application/octet-stream'}),timeout=30)
base={'project':'fixture','target':'fixture_files/media','key':'fixture/media?project=fixture&id=3'}
coll={'project':'fixture','target':'fixture_files/collections'}
root='fixture/media?project=fixture&id=1';child='fixture/media?project=fixture&id=2';recordb='fixture/media?project=fixture&id=4'
try:
 check('Version read requires authentication',call('GET','/file-versions',base).status_code==401)
 login=ok('POST','/session',{'login':'fixture','password':'fixture-only'});h['X-CSRF-Token']=login['csrf']
 check('Fixture enables upload explicitly, not production config',login['user']['allow_uploads'])
 t=ok('GET','/open',coll);check('Original CollectionLayoutWdg selects native collections',t['kind']=='collections' and t['handler']=='tactic.ui.panel.CollectionLayoutWdg')
 catalog=ok('GET','/collections',coll);check('Original _is_collection selects two collections',catalog['total']==2 and catalog['instance_type']=='fixture/media_in_media')
 check('Creation form comes from original edit_collection order',[f['name'] for f in catalog['create_form']['spec']['fields']]==['preview','name','description','keywords'])
 check('Collection marker is not a browser editable field',not any(f['name']=='_is_collection' for f in catalog['create_form']['spec']['fields']))
 check('Derived object target remains bound to configured SearchType',ok('GET','/open',dict(coll,target=catalog['records_target']))['search_type']=='fixture/media')
 candidates=ok('GET','/collections',dict(coll,mode='records',keyword='Second'));check('Server candidate lookup uses original Select',candidates['total']==1 and candidates['items'][0]['key']==recordb)
 members=ok('GET','/collection-members',dict(coll,collection=root));check('Initial membership has object and nested collection',members['total']==2 and members['links']==2)
 add=dict(coll,collection=root,revision=members['revision'],action='add',keys=[recordb])
 check('Collection write requires CSRF',call('POST','/collection-change',add,headers={'X-Tactic-UI':'1'}).status_code==403)
 check('Original CollectionAddCmd is invoked',ok('POST','/collection-change',add)['operation']=='CollectionAddCmd')
 check('Stale collection revision is rejected',call('POST','/collection-change',add).status_code==409)
 members=ok('GET','/collection-members',dict(coll,collection=root));check('Link added without cloning object',members['total']==3 and ok('GET','/collections',dict(coll,mode='records'))['total']==4)
 again=ok('POST','/collection-change',dict(add,revision=members['revision']));members=ok('GET','/collection-members',dict(coll,collection=root));check('Duplicate add does not create second junction row',members['links']==3 and not members['duplicate_links'])
 c=ok('GET','/collection-members',dict(coll,collection=child));cycle=call('POST','/collection-change',dict(coll,collection=child,revision=c['revision'],action='add',keys=[root]));check('Ancestor cycle is rejected and transaction rolled back',cycle.status_code==409 and ok('GET','/collection-members',dict(coll,collection=child))['total']==0)
 changed=ok('POST','/collection-change',dict(coll,collection=root,revision=members['revision'],action='remove',keys=[recordb]));check('Remove invokes source command and preserves member object',changed['operation']=='CollectionRemoveCmd' and ok('GET','/record',dict(base,key=recordb))['values']['code']=='B')
 members=ok('GET','/collection-members',dict(coll,collection=root))
 check('Foreign project cannot be inserted into collection',call('POST','/collection-change',dict(coll,collection=root,revision=members['revision'],action='add',keys=[recordb.replace('project=fixture','project=foreign')])).status_code==403)
 made=ok('POST','/collections',dict(coll,values={'name':'HTTP Review set','description':'Native source command test'}));newkey=made['collection']['key'];check('New collection is ordinary TACTIC object with fixed marker',made['collection']['values']['_is_collection'] in (1,True) and made['operation']=='NativeEditCmd(edit_collection)')
 check('Caller cannot replace fixed collection marker',call('POST','/collections',dict(coll,values={'name':'Invalid','_is_collection':False})).status_code==403)
 empty=ok('GET','/collection-members',dict(coll,collection=newkey));ok('POST','/collection-change',dict(coll,collection=newkey,revision=empty['revision'],action='add',keys=[recordb]));fresh=ok('GET','/collection-members',dict(coll,collection=newkey))
 check('Collection deletion requires explicit confirmation',call('POST','/collection-change',dict(coll,collection=newkey,revision=fresh['revision'],action='delete')).status_code==400)
 deleted=ok('POST','/collection-change',dict(coll,collection=newkey,revision=fresh['revision'],action='delete',confirm='DELETE_COLLECTION'))
 check('Delete removes collection and links, not contained records',deleted['operation']=='CollectionDeleteCmd' and not deleted['deleted_member_objects'] and ok('GET','/record',dict(base,key=recordb))['values']['code']=='B')
 check('Deleted collection cannot be opened',call('GET','/collection-members',dict(coll,collection=newkey)).status_code==404)
 versions=ok('GET','/file-versions',base);nextpage=ok('GET','/file-versions',dict(base,offset=120));check('Version pagination reaches beyond original 100 cap',versions['total']==125 and len(versions['items'])==40 and len(nextpage['items'])==5)
 check('Version context filter is exact and server-side',ok('GET','/file-versions',dict(base,context='review'))['total']==5)
 check('Arbitrary version limit is bounded',call('GET','/file-versions',dict(base,limit=1000)).status_code==400)
 snapshot=nextpage['items'][-1];preview=ok('GET','/snapshot-current',dict(base,snapshot=snapshot['key']));check('Current preview distinguishes current from selected',preview['selected']['code']=='SNAP0' and preview['current'][0]['code']=='SNAP119')
 check('Choosing current requires confirmation',call('POST','/snapshot-current',dict(base,snapshot=snapshot['key'],revision=preview['revision'])).status_code==400)
 switched=ok('POST','/snapshot-current',dict(base,snapshot=snapshot['key'],revision=preview['revision'],confirm='SET_CURRENT'));check('Current delegates original API while leaving latest unchanged',switched['operation']=='TacticServerStub.set_current_snapshot' and not switched['latest_changed'])
 check('Current snapshot cannot escape parent binding',call('GET','/snapshot-current',dict(base,key=recordb,snapshot=snapshot['key'])).status_code==403)
 check('Stale stream revision cannot overwrite another choice',call('POST','/snapshot-current',dict(base,snapshot=preview['current'][0]['key'],revision=preview['revision'],confirm='SET_CURRENT')).status_code==409)
 link=versions['items'][0];f=s.get(a.url+'/api/ui/v2/file',params=dict(base,snapshot=link['key'],file='FILE',preview='1'));check('SVG file remains attachment, not executable preview',f.status_code==200 and 'attachment' in f.headers.get('Content-Disposition',''))
 check('File endpoint preserves download Range support',s.get(a.url+'/api/ui/v2/file',params=dict(base,snapshot=link['key'],file='FILE'),headers={'Range':'bytes=0-9'}).status_code==206)
 listing=ok('GET','/uploads',base);check('Disk queue advertises bounded 4 MiB chunks and 2 GiB file ceiling',listing['limits']['chunk_bytes']==CHUNK and listing['limits']['max_file_bytes']==2*1024**3)
 content=(b'TACTIC06\x00\xff'*((17*1024*1024)//10+1))[:17*1024*1024]
 body=dict(base,filename='Model data.bin',size=len(content),fingerprint=fp(content),context='publish',description='HTTP 17 MiB TEST',request_id=str(uuid.uuid4()))
 check('Upload create requires CSRF',call('POST','/uploads',body,headers={'X-Tactic-UI':'1'}).status_code==403)
 check('Upload create rejects path traversal names',call('POST','/uploads',dict(body,filename='../escape')).status_code==400)
 job=ok('POST','/uploads',body);check('Create retry reuses disk job identity',ok('POST','/uploads',body)['id']==job['id'])
 check('Create request ID cannot be reused for changed context',call('POST','/uploads',dict(body,context='review')).status_code==409)
 check('Partial chunk wrong checksum is rejected',binary(job,content[:CHUNK],checksum='0'*64).status_code==400)
 check('Out-of-order chunk is rejected',binary(job,content[CHUNK:2*CHUNK],offset=CHUNK).status_code==409)
 r=binary(job,content[:CHUNK]);check('Raw PATCH writes and acknowledges first chunk',r.status_code==200 and r.json()['offset']==CHUNK)
 check('Exact chunk retry returns same confirmed offset',binary(job,content[:CHUNK]).json()['offset']==CHUNK)
 check('Altered retry cannot overwrite acknowledged bytes',binary(job,b'X'*CHUNK).status_code==409)
 check('Chunk requires binary content type',binary(job,content[:CHUNK],headers=dict(h,**{'Content-Type':'text/plain'})).status_code==415)
 check('Chunk accepts at most 4 MiB at HTTP ingress',binary(job,b'X'*(CHUNK+1)).status_code==413)
 check('Chunk scope cannot switch to another record',binary(job,content[:CHUNK],extra={'key':recordb}).status_code==404)
 ok('DELETE','/session',{});login=ok('POST','/session',{'login':'fixture','password':'fixture-only'});h['X-CSRF-Token']=login['csrf'];status=ok('GET','/upload-status',dict(base,upload_id=job['id']))
 check('Re-login retains server-confirmed offset without ticket persisted',status['offset']==CHUNK and 'owner' not in status and 'binding' not in status)
 check('Incomplete check-in is refused',call('POST','/upload-finish',dict(base,upload_id=job['id'])).status_code==409)
 for offset in range(CHUNK,len(content),CHUNK):
  r=binary(job,content[offset:offset+CHUNK],offset);assert r.status_code==200,(r.status_code,r.text)
 ready=r.json();check('17 MiB file is staged beyond old 16 MiB cap',ready['state']=='ready' and ready['offset']==len(content))
 count=ok('GET','/file-versions',base)['total'];done=ok('POST','/upload-finish',dict(base,upload_id=job['id']));check('Final check-in produces durable receipt and full SHA256',done['state']=='complete' and done['sha256']==sha(content) and done['result']['snapshot']['code']=='UPLOADED1')
 check('Receipt strips arbitrary server paths', 'server_path' not in json.dumps(done) and '/tmp/' not in json.dumps(done))
 check('Repeated final request does not create duplicate snapshot',ok('POST','/upload-finish',dict(base,upload_id=job['id']))==done and ok('GET','/file-versions',base)['total']==count+1)
 check('Completed check-in cannot be cancelled as staging',call('DELETE','/uploads',dict(base,upload_id=job['id'])).status_code==409)
 newest=ok('GET','/file-versions',base)['items'][0];f=s.get(a.url+'/api/ui/v2/file',params=dict(base,snapshot=newest['key'],file='UPLOADFILE1'));check('Uploaded bytes download intact through file endpoint',f.status_code==200 and sha(f.content)==sha(content))
 bad=ok('POST','/uploads',dict(base,filename='wrong.bin',size=5,fingerprint='0'*64,context='publish',request_id=str(uuid.uuid4())));r=binary(bad,b'hello');assert r.status_code==200
 check('Final complete-file fingerprint is checked before DB callback',call('POST','/upload-finish',dict(base,upload_id=bad['id'])).json()['error']['code']=='file_fingerprint')
 check('Cancellation deletes only staging, not existing versions',ok('DELETE','/uploads',dict(base,upload_id=bad['id']))['state']=='cancelled' and ok('GET','/file-versions',base)['total']==count+1)
 check('Unknown upload routes do not expose methods',call('POST','/upload-execute',base).status_code>=400)
finally:
 Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps({'mode':'bundled CherryPy + actual disk staging/Select/Collection commands, TEST DB/check-in collaborators','results':results},ensure_ascii=False,indent=2)+'\n')
