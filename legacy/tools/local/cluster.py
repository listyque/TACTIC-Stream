"""Local TACTIC native cluster: one gateway and three ORIGINAL server processes.

No Apache/Node/Redis required. Explicit native GETs and POST /query are balanced;
all other requests stay on worker 1 (the primary). Bind localhost only. No automatic replay of requests.
An offline migration, external plugin setup or schema change requires stopping
the WHOLE cluster. Existing data/config are not initialized or upgraded here.
"""
from pathlib import Path
import argparse
from contextlib import ExitStack
import http.client
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parent))
from launch import ROOT, configure_paths, choose_config, dependency_check
from local_lock import local_lock
from cluster_gateway import Gateway, RoutingPool


def atomic_json(path, data):
    temp=path.with_suffix('.writing')
    with temp.open('w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)


class Cluster:
    def __init__(self, data, config, port=9123, workers=3, worker_base=None, timeout=300, worker_script=None):
        self.data,self.config,self.port,self.timeout=data,config,port,timeout
        self.run_id=secrets.token_hex(16);self.secret=secrets.token_urlsafe(48)
        self.state_dir=data/'native-cluster'/self.run_id
        self.state_dir.mkdir(parents=True,mode=0o700)
        self.state_dir.chmod(0o700)
        self.status_path=self.state_dir/'status.json'
        self.pool=RoutingPool([{'id':str(i+1),'port':(worker_base or port+1)+i,
                               'role':'writer' if i==0 else 'reader','pid':None,'healthy':False,
                               'requests':0,'active':0,'errors':0,'restarts':0} for i in range(workers)])
        self.children={};self.logs=[];self.last_start={};self.failures={};self.stop_event=threading.Event()
        self.state='starting';self.server=None;self.monitor=None;self.status_lock=threading.Lock()
        # Injection is for local tests; no CLI/HTTP argument can select code.
        self.worker_script=worker_script or ROOT/'tools/local/cluster_worker.py'
        self.action_thread = None
        self.action_tailer = None
        self.gateway=Gateway(self.pool,self.secret,port,timeout)
        self.write_status()

    def write_status(self):
        # Startup and monitor both write heartbeat/status. Use one publication
        # lock; a shared .writing filename must never race another writer.
        with self.status_lock:
            with self.pool.lock:
                payload={'run_id':self.run_id,'heartbeat':time.time(),'updated_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                         'state':self.state,'port':self.port,'read_policy':'explicit native GET + POST query / round-robin',
                         'write_policy':'worker 1 / serialized gateway lane / no replay',
                         'workers':[dict(w) for w in self.pool.workers]}
            atomic_json(self.status_path,payload)

    def spawn(self, worker):
        env=os.environ.copy()
        env.update(TACTIC_CLUSTER_ROLE=worker['role'],TACTIC_CLUSTER_WORKER_ID=worker['id'],
                   TACTIC_CLUSTER_SECRET=self.secret,TACTIC_CLUSTER_RUN_ID=self.run_id,
                   TACTIC_CLUSTER_STATUS=str(self.status_path),
                   TACTIC_CLUSTER_SESSIONS=str(self.state_dir/'sessions.sqlite3'),TACTIC_UI='vue',
                   TACTIC_ACTION_LOG_DIR=str(self.state_dir/'actions'),PYTHONUNBUFFERED='1')
        logfile=(self.state_dir/f"worker-{worker['id']}.log").open('ab',buffering=0)
        self.logs.append(logfile)
        p=subprocess.Popen([sys.executable,'-X','utf8','-s',str(self.worker_script),
                           '--data-dir',str(self.data),'--config',str(self.config),'--port',str(worker['port'])],
                           cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=logfile,stderr=subprocess.STDOUT)
        self.children[worker['id']]=p;self.last_start[worker['id']]=time.monotonic()
        with self.pool.lock:worker['pid']=p.pid;worker['healthy']=False
        print(f"TACTIC worker {worker['id']} ({worker['role']}), pid={p.pid}, localhost:{worker['port']}",flush=True)

    def probe(self, worker):
        p=self.children.get(worker['id'])
        if p is None or p.poll() is not None:return False
        c=http.client.HTTPConnection('127.0.0.1',worker['port'],timeout=1)
        try:
            c.request('GET','/api/ui/v2/health',headers={'X-Tactic-Cluster':self.secret})
            r=c.getresponse();r.read()
            return r.status==200 and r.getheader('X-Tactic-Worker-Pid')==str(p.pid)
        except (OSError,http.client.HTTPException):return False
        finally:c.close()

    def supervise(self):
        while not self.stop_event.wait(1):
            try:
                for w in self.pool.workers:
                    if self.stop_event.is_set(): break
                    p=self.children.get(w['id'])
                    if p is None:continue
                    live=p.poll() is None
                    healthy=self.probe(w) if live else False
                    with self.pool.lock:w['healthy']=healthy
                    if not live:
                        now=time.monotonic();recent=[t for t in self.failures.get(w['id'],[]) if now-t<60]
                        self.failures[w['id']]=recent
                        if len(recent)>=5:
                            self.state='failed';self.stop_event.set();break
                        if now-self.last_start[w['id']]>=2:
                            recent.append(now);w['restarts']+=1;self.spawn(w)
                if self.server and hasattr(self,'http_thread') and not self.http_thread.is_alive():
                    self.state='failed';self.stop_event.set()
                if self.state!='starting' and self.state!='failed':
                    self.state='running' if all(w['healthy'] for w in self.pool.workers) else 'degraded'
                self.write_status()
            except Exception as exc:
                print('Cluster monitor failed:',type(exc).__name__,str(exc),flush=True)
                self.state='failed';self.stop_event.set()

    def start(self):
        # Reserve/check all ports before starting any original startup side effects.
        sockets=[]
        try:
            for p in [self.port]+[w['port'] for w in self.pool.workers]:
                s=socket.socket();sockets.append(s);s.bind(('127.0.0.1',p))
        finally:
            for s in sockets:s.close()
        from tactic.ui_api.shared_sessions import SharedSessionStore
        from tactic.ui_api.action_log import ActionLogTailer
        self.action_tailer = ActionLogTailer(self.state_dir/'actions', [w['id'] for w in self.pool.workers])
        def relay_actions():
            while not self.stop_event.wait(.15):
                self.action_tailer.poll()
        self.action_thread = threading.Thread(target=relay_actions, daemon=True, name='TACTIC-action-log')
        self.action_thread.start()
        SharedSessionStore(self.state_dir/'sessions.sqlite3')
        # Only the writer performs FirstRun initialization; start it to readiness first.
        self.monitor=threading.Thread(target=self.supervise,daemon=True);self.monitor.start()
        for w in self.pool.workers:
            self.spawn(w)
            deadline=time.monotonic()+90
            while not w['healthy']:
                if self.stop_event.wait(.1) or time.monotonic()>deadline:
                    raise RuntimeError(f"Worker {w['id']} failed startup; inspect private log in {self.state_dir}")
            self.write_status()
        from cheroot.wsgi import Server
        self.server=Server(('127.0.0.1',self.port),self.gateway,numthreads=16,server_name='localhost',timeout=30)
        self.server.prepare()
        self.http_thread=threading.Thread(target=self.server.serve,daemon=True);self.http_thread.start()
        self.state='running';self.write_status()
        print(f'Gateway: http://127.0.0.1:{self.port}/tactic/admin/; workers={len(self.pool.workers)}',flush=True)
        print('Private status/log directory:',self.state_dir,flush=True)

    def close(self):
        self.stop_event.set()
        if self.monitor:self.monitor.join(timeout=5)
        if self.action_thread:self.action_thread.join(timeout=3)
        if self.server:self.server.stop()
        for p in self.children.values():
            if p.poll() is None:p.terminate()
        for p in self.children.values():
            try:p.wait(timeout=8)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
        if self.action_tailer:self.action_tailer.poll()
        for log in self.logs:log.close()
        for w in self.pool.workers:w['healthy']=False
        self.state='stopped';self.write_status()
        # No persistent copy of TACTIC ticket secrets after a clean cluster stop.
        for suffix in ('','-journal','-wal','-shm'):
            try:(self.state_dir/('sessions.sqlite3'+suffix)).unlink(missing_ok=True)
            except OSError:pass


def preflight(data,config):
    if (data/'.sqlite-promotion.json').exists():raise RuntimeError('Interrupted database publication; restore first')
    marker=data/'local-install.json'
    if marker.exists() and json.loads(marker.read_text(encoding='utf-8')).get('state')!='upgraded':
        raise RuntimeError('Local database is not upgraded. Use the existing offline upgrade procedure first.')
    tree=ET.parse(config)
    if tree.findtext('portal/auto_upgrade','').lower()=='true':
        raise RuntimeError('portal/auto_upgrade=true is not allowed in a cluster. Upgrade offline before group startup.')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',type=Path);p.add_argument('--config')
    p.add_argument('--port',type=int,default=9123);p.add_argument('--workers',type=int,default=3)
    p.add_argument('--worker-base-port',type=int);p.add_argument('--timeout',type=int,default=300)
    a=p.parse_args(argv)
    if not 2<=a.workers<=8:p.error('--workers: 2..8, default 3')
    base=a.worker_base_port or a.port+1
    if not 1024<=a.port<=65535 or not 1024<=base<=65535-a.workers+1 or base<=a.port<base+a.workers:
        p.error('Gateway and workers need separate free ports in 1024..65535')
    if not 10<=a.timeout<=3600:p.error('--timeout: 10..3600 seconds')
    data=a.data_dir.expanduser().resolve() if a.data_dir else ROOT/'local_data'
    config=choose_config(data,a.config)
    if not a.data_dir and config!=data/'config/tactic-conf.xml':
        if config.parent.name.lower()!='config':p.error('Supply --data-dir for an external config')
        data=config.parent.parent
    configure_paths(data,config)
    if os.name!='nt' and os.getuid()==0:raise RuntimeError('Do not run TACTIC as root; use an unprivileged account')
    if not dependency_check():return 2
    preflight(data,config)
    with ExitStack() as leases:
        leases.enter_context(local_lock(data,name='.native-cluster-owner.lock'))
        # Require a quiescent installation before starting a NEW group. In
        # particular, surviving children of a dead supervisor must exit first.
        # The owner lease closes the gap against another cluster; if a standalone
        # server takes the lifetime lock in the gap, shared acquisition fails.
        with local_lock(data): preflight(data,config)
        leases.enter_context(local_lock(data,shared=True))
        preflight(data,config)
        cluster=Cluster(data,config,a.port,a.workers,base,a.timeout)
        def stop(*_):cluster.stop_event.set()
        old={s:signal.signal(s,stop) for s in (signal.SIGINT,signal.SIGTERM)}
        try:
            cluster.start()
            while not cluster.stop_event.wait(.25):pass
            return 1 if cluster.state=='failed' else 0
        finally:
            cluster.close()
            for sig,handler in old.items():signal.signal(sig,handler)

if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:raise SystemExit(130)
    except Exception as exc:
        print('CLUSTER ERROR:',type(exc).__name__,str(exc),flush=True)
        raise SystemExit(1)
