"""One ORIGINAL TACTIC process owned by the local supervisor. Not a fixture."""
from pathlib import Path
import argparse
import json
import os
import sys
import threading
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
from launch import ROOT, configure_paths
from local_lock import local_lock


def watchdog(status_path, run_id):
    # Supervisor refreshes its status every second. Fail closed if it disappears.
    # The worker holds a shared lifetime lock until it exits, blocking upgrades.
    while True:
        time.sleep(3)
        try:
            state=json.loads(Path(status_path).read_text(encoding='utf-8'))
            alive=state.get('run_id')==run_id and -5 <= time.time()-state.get('heartbeat',0)<20 and state.get('state')!='stopped'
        except (OSError,ValueError): alive=False
        if not alive:
            os._exit(71)  # no new requests; unknown write result is NOT replayed


def run_worker(data, config, port):
    role=os.environ.get('TACTIC_CLUSTER_ROLE')
    if role not in ('writer','reader') or not os.environ.get('TACTIC_CLUSTER_RUN_ID'):
        raise RuntimeError('Start through START_TACTIC.bat, not cluster_worker directly')
    if (data/'.sqlite-promotion.json').exists():raise RuntimeError('Pending offline database recovery')
    configure_paths(data,config)
    with local_lock(data,shared=True):
        threading.Thread(target=watchdog,args=(os.environ['TACTIC_CLUSTER_STATUS'],os.environ['TACTIC_CLUSTER_RUN_ID']),daemon=True).start()
        from tactic.startup import FirstRunInit
        if role=='writer': FirstRunInit().execute()
        from pyasm.web.cherrypy30_startup import CherryPyStartup
        from tactic.ui_api.cluster_runtime import install_guard
        server=CherryPyStartup(port)
        for key,value in {'server.socket_host':'127.0.0.1','server.socket_port':port,
                          'server.thread_pool':8,'request.show_tracebacks':False,
                          'engine.autoreload.on':False,'log.screen':True}.items():
            server.set_config('global',key,value)
        install_guard()
        server.execute()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',required=True,type=Path);p.add_argument('--config',required=True,type=Path)
    p.add_argument('--port',required=True,type=int)
    a=p.parse_args()
    run_worker(a.data_dir.resolve(),a.config.resolve(),a.port)

if __name__=='__main__': main()
