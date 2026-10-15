"""Disposable ORIGINAL server for development; never takes a working database.

Requires explicit --isolate-license only in CI without signature dependencies.
Stop by creating OUTPUT/STOP or interrupt the process. No credentials are logged.
"""
import argparse, json, os, shutil, socket, sys, tempfile, time
from pathlib import Path
from managed_seed_08 import ROOT, create_seed, licence_isolated_worker
import managed_sqlite as local
from launch import configure_paths
from cluster import Cluster, preflight
from local_lock import local_lock
import subprocess

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--isolate-license',action='store_true')
a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
def run(name,cmd):
    with (out/(name+'.log')).open('w') as log:
        r=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=180)
    if r.returncode:raise RuntimeError(name+' failed; see private test log')
def ports():
    for _ in range(100):
        with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        if port>65000:continue
        sockets=[]
        try:
            for n in range(4):
                s=socket.socket();sockets.append(s);s.bind(('127.0.0.1',port+n))
            return port
        except OSError:pass
        finally:
            for s in sockets:s.close()
    raise RuntimeError('No port range')
with tempfile.TemporaryDirectory(prefix='tactic-cluster014-design018-') as tmp:
    data=Path(tmp)/'local';conf=create_seed(data)
    result=local.perform_upgrade(ROOT,data,conf,worker=licence_isolated_worker if a.isolate_license else local.default_worker)
    if not result['passed']:raise RuntimeError('Original seed upgrade failed')
    shutil.copy2(data/'db/unittest.db',data/'db/native11test.db')
    (data/'.native-real-test').write_text('DISPOSABLE DESIGN TEST')
    port=ports()
    opts=['--isolate-license'] if a.isolate_license else []
    run('prepare',[sys.executable,str(ROOT/'tests/native_ui/real_server_012.py'),'--data-dir',str(data),'--port',str(port),'--prepare',*opts])
    run('grid',[sys.executable,str(ROOT/'tests/native_ui/prepare_grid_012.py'),'--data-dir',str(data),*opts])
    (data/'config/native-ui.json').write_text(json.dumps({'allow_writes':True,'allow_uploads':True,'allow_script_execution':True}))
    configure_paths(data,conf);preflight(data,conf)
    if a.isolate_license:os.environ['TACTIC_TEST_ISOLATE_SIGNATURE']='1'
    with local_lock(data,name='.native-cluster-owner.lock'),local_lock(data,shared=True):
        group=Cluster(data,conf,port,workers=3,worker_script=ROOT/'tests/native_ui/cluster_test_worker_014.py')
        try:
            group.start()
            (out/'ready.json').write_text(json.dumps({'url':f'http://127.0.0.1:{port}','data':str(data),'cluster_dir':str(group.state_dir),'pids':[w['pid'] for w in group.pool.workers]}))
            print('READY three original workers',flush=True)
            deadline=time.monotonic()+3600
            while time.monotonic()<deadline and not (out/'STOP').exists():time.sleep(.5)
        finally:
            (out/'ready.json').unlink(missing_ok=True)
            for log in group.state_dir.glob('worker-*.log'):shutil.copy2(log,out/('private-'+log.name))
            group.close()
