"""Repeat 0.12 on original complete SQLite seeds and actual TACTIC startup.

No input path to user data is accepted. All databases/configs exist only in a
TemporaryDirectory. --isolate-license deliberately isolates only signature
validation, never authentication, Search, native persistence or commands.
"""
import argparse,json,os,shutil,socket,subprocess,sys,tempfile,time
from pathlib import Path
from urllib.request import urlopen
from managed_seed_08 import ROOT,create_seed,licence_isolated_worker
import managed_sqlite as local
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--isolate-license',action='store_true')
p.add_argument('--bridge',action='store_true')
p.add_argument('--skip-browser',action='store_true')
p.add_argument('--chromium',default='/usr/bin/chromium')
a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
summary={'original_startup':True,'full_stock_sqlite_seeds':True,'db_authentication':'original','persistence':'original Search, SObject, commands and transaction wrapper','signature_verification_isolated':a.isolate_license,'native_browser_transport':not a.bridge,'suites':{},'passed':False}
def run(name,command,timeout=240):
 with (out/(name+'.log')).open('w',encoding='utf-8') as log:r=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=timeout,check=False)
 summary['suites'][name]={'return_code':r.returncode}
 if r.returncode:raise RuntimeError(name+' failed; inspect '+str(out/(name+'.log')))
def scenarios(path):
 raw=json.loads(path.read_text());items=raw.get('scenarios',[])
 return {'scenarios':len(items),'passed_scenarios':sum(x.get('passed') is True for x in items),'js_errors':raw.get('js_errors',[])}
try:
 with tempfile.TemporaryDirectory(prefix='tactic-original-012-') as work:
  data=Path(work)/'local';config=create_seed(data)
  migration=local.perform_upgrade(ROOT,data,config,worker=licence_isolated_worker if a.isolate_license else local.default_worker)
  assert migration['passed']
  (out/'migration.json').write_text(json.dumps(migration,ensure_ascii=False,indent=2)+'\n')
  summary['migration']={'passed':True,'original_methods':len(migration['completed']),'identity_repairs':sum(s['status']=='identity_repaired' for s in migration['statements'])}
  shutil.copy2(data/'db/unittest.db',data/'db/native11test.db')
  (data/'.native-real-test').write_text('Disposable original model test only.\n')
  with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
  url='http://127.0.0.1:'+str(port)
  command=[sys.executable,str(ROOT/'tests/native_ui/real_server_012.py'),'--data-dir',str(data),'--port',str(port)]
  if a.isolate_license:command+=['--isolate-license']
  run('prepare',command+['--prepare'])
  prep=[sys.executable,str(ROOT/'tests/native_ui/prepare_grid_012.py'),'--data-dir',str(data)]
  if a.isolate_license:prep+=['--isolate-license']
  run('prepare-grid',prep)
  with (out/'original-server.log').open('w',encoding='utf-8') as log:
   process=subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
   try:
    deadline=time.monotonic()+40
    while True:
     if process.poll() is not None:raise RuntimeError('Original startup failed')
     try:
      with urlopen(url+'/api/ui/v2/health',timeout=2) as r:
       if r.status==200:break
     except OSError:pass
     if time.monotonic()>deadline:raise RuntimeError('Original startup timed out')
     time.sleep(.1)
    summary['server_started']=True
    run('http',[sys.executable,str(ROOT/'tests/native_ui/run_http_012.py'),'--url',url,'--output',str(out/'http.json')])
    summary['suites']['http'].update(scenarios(out/'http.json'))
    if not a.skip_browser:
     cmd=[sys.executable,str(ROOT/'tests/native_ui/run_browser_012.py'),'--url',url,'--output',str(out/'browser'),'--chromium',a.chromium]
     if a.bridge:cmd+=['--bridge']
     run('browser',cmd)
     summary['suites']['browser'].update(scenarios(out/'browser/browser-results.json'))
   finally:
    process.terminate()
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
  summary['passed']=True
except Exception as exc:
 summary['error']=str(exc);raise
finally:
 (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
