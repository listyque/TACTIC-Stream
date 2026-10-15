"""0.19 compact workspaces, original design regressions and live console trace through three ORIGINAL TACTIC processes.
Only licence signature validation may be isolated explicitly. No working data
argument. Authentication, core, commands, transactions and storage are original.
"""
from pathlib import Path
import argparse, concurrent.futures, json, os, shutil, socket, subprocess, sys, tempfile, time
import requests
from managed_seed_08 import ROOT, create_seed, licence_isolated_worker
import managed_sqlite as local
from launch import configure_paths
from cluster import Cluster, preflight
from local_lock import local_lock
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,required=True);p.add_argument('--isolate-license',action='store_true')
p.add_argument('--skip-browser',action='store_true');p.add_argument('--bridge',action='store_true')
p.add_argument('--chromium',default='/usr/bin/chromium');a=p.parse_args()
out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
report={'version':'0.19','passed':False,'scenarios':[], 'backend':'3 original TACTIC processes; complete SQLite seeds; original authentication and commands','signature_isolated':a.isolate_license,'browser_bridge':a.bridge}
def check(name,ok,**detail):
 report['scenarios'].append({'scenario':name,'passed':bool(ok),**detail})
 print(('PASS ' if ok else 'FAIL ')+name,flush=True)
 if not ok:raise AssertionError(name)
def run(name,cmd):
 with (out/(name+'.log')).open('w') as log:r=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=300)
 check(name+' exit',r.returncode==0,returncode=r.returncode)
def available_range():
 for _ in range(100):
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));base=sock.getsockname()[1]
  if base>65000:continue
  probes=[]
  try:
   for port in range(base,base+4):
    sock=socket.socket();probes.append(sock);sock.bind(('127.0.0.1',port))
   return base
  except OSError:pass
  finally:
   for sock in probes:sock.close()
 raise RuntimeError('No free port range')
try:
 with tempfile.TemporaryDirectory(prefix='tactic-cluster014-') as tmp:
  data=Path(tmp)/'local';config=create_seed(data)
  migration=local.perform_upgrade(ROOT,data,config,worker=licence_isolated_worker if a.isolate_license else local.default_worker)
  check('Original staged migrations',migration['passed'])
  shutil.copy2(data/'db/unittest.db',data/'db/native11test.db')
  (data/'.native-real-test').write_text('DISPOSABLE CLUSTER TEST')
  port=available_range();url=f'http://127.0.0.1:{port}'
  prep=[sys.executable,str(ROOT/'tests/native_ui/real_server_012.py'),'--data-dir',str(data),'--port',str(port),'--prepare']
  if a.isolate_license:prep+=['--isolate-license']
  run('prepare-original',prep)
  prep=[sys.executable,str(ROOT/'tests/native_ui/prepare_grid_012.py'),'--data-dir',str(data)]
  if a.isolate_license:prep+=['--isolate-license']
  run('prepare-grid',prep)
  (data/'config/native-ui.json').write_text(json.dumps({'allow_writes':True,'allow_uploads':True,'allow_script_execution':True}))
  configure_paths(data,config);preflight(data,config)
  if a.isolate_license:os.environ['TACTIC_TEST_ISOLATE_SIGNATURE']='1'
  with local_lock(data,name='.native-cluster-owner.lock'),local_lock(data,shared=True):
   cluster=Cluster(data,config,port,workers=3,worker_script=ROOT/'tests/native_ui/cluster_test_worker_014.py')
   try:
    cluster.start()
    check('Three original worker PIDs healthy',len({w['pid'] for w in cluster.pool.workers})==3 and all(w['healthy'] for w in cluster.pool.workers))
    report['initial_pids']=[w['pid'] for w in cluster.pool.workers]
    observed={x.name.split('-')[-1]:x.read_text() for x in data.glob('.scheduler-observed-*')}
    check('Only primary registers original periodic scheduler',observed=={str(cluster.pool.workers[0]['pid']):'writer'})

    check('Direct internal port denied without secret',requests.get(f'http://127.0.0.1:{port+1}/api/ui/v2/health',timeout=10).status_code==403)
    check('Gateway reports three healthy workers',requests.get(url+'/__cluster/health',timeout=10).json()['healthy_workers']==3)
    import xmlrpc.client
    with xmlrpc.client.ServerProxy(url+'/tactic/default/Api/',allow_none=True) as rpc:
     rpc_ticket=rpc.get_ticket('admin','Native-Test-Only-123')
     check('Original XML-RPC login and ping work through primary',isinstance(rpc_ticket,str) and rpc.ping({'ticket':rpc_ticket,'project':'admin','language':'python','site':''})=='OK')

    check('Untrusted public host blocked',requests.get(url+'/api/ui/v2/health',headers={'Host':'attacker.test'},timeout=10).status_code==400)
    s=requests.Session();h={'X-Tactic-UI':'1','Origin':url}
    def call(method,path,**data):return s.request(method,url+'/api/ui/v2'+path,params=data if method=='GET' else None,json=data if method!='GET' else None,headers=h,timeout=60)
    def good(r):
     if r.status_code not in (200,201):raise AssertionError(f'{r.status_code} {r.text[:1600]}')
     return r.json()
    auth=call('POST','/session',login='admin',password='Native-Test-Only-123');info=good(auth);h['X-CSRF-Token']=info['csrf']
    check('Original password authentication routed to writer',auth.headers.get('X-Tactic-Worker')=='1' and info['user']['mode']=='tactic')
    ids=[]
    for i in range(12):
     r=call('GET','/session');good(r);ids.append(r.headers.get('X-Tactic-Worker'))
    check('Same authenticated cookie works on all three PIDs',set(ids)=={'1','2','3'},sequence=ids)
    q={'project':'admin','target':'admin_views/global_admin/users','limit':100}
    rows=[];ids=[]
    for i in range(6):
     r=call('POST','/query',**q);rows=good(r)['items'];ids.append(r.headers.get('X-Tactic-Worker'))
    check('Original user query balanced over all workers',set(ids)=={'1','2','3'} and any(r['values'].get('login')=='grid_anna' for r in rows))
    def parallel_query(_):
     response=requests.post(url+'/api/ui/v2/query',json=q,headers=h,cookies=s.cookies.copy(),timeout=60)
     return response.status_code,response.headers.get('X-Tactic-Worker')
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as threads:
     parallel=list(threads.map(parallel_query,range(12)))
    check('Twelve concurrent original queries complete on three workers',all(code==200 for code,_ in parallel) and {w for _,w in parallel}=={'1','2','3'},routing=parallel)
    key=next(r['key'] for r in rows if r['values'].get('login')=='grid_anna')
    e=good(call('POST','/cell-editor',project='admin',target=q['target'],key=key,field='last_name'))
    spec=good(call('GET','/open',project='admin',target=q['target']))['spec']
    r=call('POST','/table-changes',project='admin',target=q['target'],table_revision=spec['revision'],records=[{'key':key,'revision':e['revision'],'config_revision':e['config_revision'],'values':{'last_name':'Кластер 3 процесса'}}]);good(r)
    check('Save uses writer and original EditMultipleCmd',r.headers.get('X-Tactic-Worker')=='1' and 'EditMultipleCmd' in r.json()['transaction'])
    for i in range(6):
     r=call('GET','/record',project='admin',target=q['target'],key=key);d=good(r)
     check('Read-after-write on worker '+r.headers.get('X-Tactic-Worker','?')+' sample '+str(i),d['values']['last_name']=='Кластер 3 процесса')
    check('Client cannot inject internal gateway credential',s.get(url+'/api/ui/v2/session',headers={'X-Tactic-Cluster':'bad'},timeout=10).status_code==200)
    old=cluster.children['2'];oldpid=old.pid;old.terminate();old.wait(timeout=10)
    deadline=time.monotonic()+40
    while time.monotonic()<deadline:
     w=cluster.pool.workers[1]
     if w['pid']!=oldpid and w['healthy']:break
     time.sleep(.3)
    check('Dead read worker automatically replaced',w['pid']!=oldpid and w['healthy'],old_pid=oldpid,new_pid=w['pid'])
    for i in range(6):good(call('GET','/session'))
    check('Session survives read worker replacement',True)
    old=cluster.children['1'];oldpid=old.pid;old.terminate();old.wait(timeout=10)
    deadline=time.monotonic()+40
    while time.monotonic()<deadline:
     w=cluster.pool.workers[0]
     if w['pid']!=oldpid and w['healthy']:break
     time.sleep(.3)
    check('Dead writer replaced without changing lane',w['pid']!=oldpid and w['healthy'],old_pid=oldpid,new_pid=w['pid'])
    for i in range(6):good(call('GET','/session'))
    check('Session survives writer replacement',True)
    good(call('DELETE','/session'))
    check('Logout revokes shared session on all workers',all(call('GET','/session').status_code==401 for _ in range(6)))
    run('table-http',[sys.executable,str(ROOT/'tests/native_ui/run_http_012.py'),'--url',url,'--output',str(out/'table-http.json')])
    run('fill-http',[sys.executable,str(ROOT/'tests/native_ui/run_http_fill_014.py'),'--url',url,'--output',str(out/'fill-http.json')])
    run('globals-http',[sys.executable,str(ROOT/'tests/native_ui/run_http_11.py'),'--url',url,'--output',str(out/'globals-http.json')])
    run('state-project-http',[sys.executable,str(ROOT/'tests/native_ui/run_http_state_015.py'),'--url',url,'--output',str(out/'state-project-http.json')])
    run('diagnostics-http',[sys.executable,str(ROOT/'tests/native_ui/run_http_016.py'),'--url',url,'--output',str(out/'diagnostics-http.json')])
    run('administration-http',[sys.executable,str(ROOT/'tests/native_ui/run_http_admin_017.py'),'--url',url,'--output',str(out/'administration-http.json')])
    run('design-http',[sys.executable,str(ROOT/'tests/native_ui/run_http_design_018.py'),'--url',url,'--output',str(out/'design-http.json')])
    created=json.loads((out/'state-project-http.json').read_text())
    auth=good(call('POST','/session',login='admin',password='Native-Test-Only-123'));h['X-CSRF-Token']=auth['csrf']
    state_pids=[]
    for i in range(6):
     r=call('GET','/ui-state',project='admin',scope='geometry',target=q['target']);d=good(r);state_pids.append(r.headers.get('X-Tactic-Worker'))
     check('Original persisted state readable on worker sample '+str(i),d['value']['widths']['login']==280)
    check('Settings reads actually balanced over three workers',set(state_pids)=={'1','2','3'})
    project_pids=[]
    for i in range(6):
     r=call('POST','/query',project=created['created_project'],target=created['created_target'],limit=50);d=good(r);project_pids.append(r.headers.get('X-Tactic-Worker'))
     check('New project SObject visible on worker sample '+str(i),any(x['values']['name']=='Тестовый объект' for x in d['items']))
    check('New project propagates to all workers without restart',set(project_pids)=={'1','2','3'})
    # Reset ONLY namespaced preferences in this disposable test account before
    # repeating older UI tests, never records or original widget_config.
    for scope,value,target in [('workspace',{'ids':[],'active':''},''),('navigation',{'folders':{}},''),('appearance',{'theme':'light'},''),('query',{},q['target']),('geometry',{},q['target'])]:
     previous=good(call('GET','/ui-state',project='admin',scope=scope,target=target))
     good(call('PATCH','/ui-state',project='admin',scope=scope,target=target,revision=previous['revision'],value=value))
    if not a.skip_browser:
     print('Respecting original login rate limit before browser regression',flush=True)
     time.sleep(61)
     browser=[sys.executable,str(ROOT/'tests/native_ui/run_browser_compact_019.py'),'--url',url,'--output',str(out/'browser-compact'),'--http-report',str(out/'design-http.json'),'--chromium',a.chromium]
     if a.bridge:browser+=['--bridge']
     run('compact-browser',browser)
    time.sleep(.5)
    actions=[]
    for path in (cluster.state_dir/'actions').glob('*.jsonl'):
     for line in path.read_text().splitlines():
      try: actions.append(json.loads(line))
      except ValueError: pass
    check('All three real workers produce safe action records',{e.get('worker') for e in actions}=={'1','2','3'})
    check('Log includes resolved pipeline and schema renderers',{'pipeline','schema'} <= {e.get('renderer') for e in actions})
    check('Log includes actual original pipeline save command',any('PipelineSaveCbk' in ','.join(e.get('commands',[])) for e in actions))
    check('Log includes original table multi-edit command',any('EditMultipleCmd' in ','.join(e.get('commands',[])) for e in actions))
    check('Log includes correlated failed and completed requests',any(e.get('status')==403 and e.get('action_id')=='ui_integration_save_016' for e in actions))
    check('Administrative matrix commands are traced',any('SecurityCbk' in ','.join(e.get('commands',[])) for e in actions))
    check('Physical column creation traced through original command',any('ColumnEditCbk' in ','.join(e.get('commands',[])) for e in actions))
    text=json.dumps(actions)
    check('No passwords tickets field bodies or filter operands in action records',all(secret not in text for secret in ['DIAGNOSTIC_PRIVATE_PASSWORD_016','DIAGNOSTIC_PRIVATE_FILTER_016','Native-Test-Only-123','Private-Test-Pass-1','Private-Test-DB-2','UNSAVED_PRIVATE_FIELD_016',info['csrf'],rpc_ticket]))
    # Verify a membership action is meaningful instead of an empty generic access line.
    check('Membership request has action user project duration and target',any(e.get('route')=='/memberships' and all(k in e for k in ['user','project','ms','target','request_id']) for e in actions))
    (out/'action-sample.json').write_text(json.dumps([e for e in actions if e.get('renderer') in ('pipeline','schema') or e.get('route')=='/memberships'][-25:],ensure_ascii=False,indent=2))
    raw='\n'.join(p.read_text(errors='replace') for p in cluster.state_dir.glob('worker-*.log'))
    check('Normal native single-site requests do not print empty-site warning','WARNING: site is empty' not in raw)
    slow=[e for e in actions if e.get('action_id')=='ui_slow_saved_script_018']
    check('Console emits START RUNNING END during original saved Python',{'start','running','end'} <= {e.get('phase') for e in slow})
    check('Long request stays correlated and has one successful end',len({e.get('request_id') for e in slow})==1 and sum(e.get('phase')=='end' and e.get('status')==200 for e in slow)==1)
    check('END phase identifies actual completed state',all(e.get('state')=='completed' for e in slow if e.get('phase')=='end'))
    check('Design XML code CSV and parameters absent from safe logs',all(v not in text for v in ('DESIGN_PRIVATE_BODY_018','private_marker','original browser command')))
    from tactic.ui_api.action_log import human
    (out/'console-example.txt').write_text('\n'.join(human(e) for e in slow)+'\n',encoding='utf-8')
    report['action_records']=len(actions)
    report['final_workers']=[dict(w) for w in cluster.pool.workers]
   finally:
    # Only keep logs in private test output; publication excludes these files.
    for path in cluster.state_dir.glob('*.log'):shutil.copy2(path,out/('private-'+path.name))
    cluster.close()
   check('Clean stop terminates all worker processes',all(x.poll() is not None for x in cluster.children.values()))
   check('Clean stop removes transport session secrets',not (cluster.state_dir/'sessions.sqlite3').exists())
  report['passed']=True
except Exception as exc:
 report['error']=str(exc)
 import traceback;traceback.print_exc()
finally:
 (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if not report['passed']:raise SystemExit(1)
