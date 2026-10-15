"""TEST ONLY original worker, isolated signature. No fixture auth or persistence.
The companion runner owns a newly created disposable seed installation.
This file is never selected by the production cluster CLI.
"""
from pathlib import Path
import argparse, os, sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/local'))
from launch import configure_paths
p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,required=True);p.add_argument('--config',type=Path,required=True);p.add_argument('--port',type=int,required=True)
a=p.parse_args();data=a.data_dir.resolve()
if not (data/'.native-real-test').is_file() or 'tactic-cluster014-' not in str(data):
    raise SystemExit('Refusing non-disposable test data')
configure_paths(data,a.config)
if os.environ.get('TACTIC_TEST_ISOLATE_SIGNATURE')=='1':
    from pyasm.security.security import License
    from unittest.mock import patch
    license_patch=patch.object(License,'get',return_value=License(str(data/'config/tactic-license.xml'),verify=False))
    license_patch.start()
    print('TEST ONLY: signature isolated, original auth/DB/commands remain.',flush=True)
# Observe the real periodic scheduler registration without suppressing it.
from pyasm.web.cache_startup import CacheStartup
original_scheduler = CacheStartup.init_scheduler
def observed_scheduler(self):
    (data / ('.scheduler-observed-'+str(os.getpid()))).write_text(os.environ['TACTIC_CLUSTER_ROLE'])
    return original_scheduler(self)
CacheStartup.init_scheduler = observed_scheduler
from cluster_worker import run_worker
run_worker(data,a.config,a.port)
