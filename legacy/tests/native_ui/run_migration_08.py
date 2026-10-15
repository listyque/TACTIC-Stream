"""Exercise managed upgrades on complete ORIGINAL seed copies, never user data.

Default requires a real working TACTIC environment. --isolate-license is an
explicit TEST ONLY switch for CI without Cryptodome; it does not validate
licence verification or full startup/authentication.
"""
from contextlib import closing
from pathlib import Path
import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
from managed_seed_08 import ROOT,create_seed,licence_isolated_worker
import managed_sqlite as local
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--isolate-license',action='store_true');a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
summary={'original_seed':True,'sql_mocks':False,'licence_boundary_substituted':a.isolate_license,
         'full_startup_tested':False,'cases':[]}
worker=licence_isolated_worker if a.isolate_license else local.default_worker
try:
 with tempfile.TemporaryDirectory(prefix='tactic-full-seed-08-') as tmp:
  for case in ('clean-seed','partially-applied-falsely-stamped'):
   data=Path(tmp)/case;config=create_seed(data)
   with closing(sqlite3.connect(data/'db/sthpw.db')) as c:
    c.execute("INSERT INTO widget_config(code,view,config) VALUES('NATIVE08_KEEP','custom_view','<config><custom_view keep=\"yes\"/></config>')")
    if case!='clean-seed':
     c.execute("UPDATE project SET last_version_update='5.0.0.a02'")
     c.execute('ALTER TABLE login ADD display_name text')
     c.execute("INSERT INTO login(login,code,display_name) VALUES('preserved-user','preserved-user','Custom name')")
    c.commit()
   before={n:local.digest(f) for n,f in local.layout(data,config)[2].items()}
   report=local.perform_upgrade(ROOT,data,config,worker=worker)
   marker=json.loads((data/'local-install.json').read_text());backup=Path(marker['backup'])
   shutil.copy2(backup/'worker.log',a.output/(case+'-worker.log'))
   (a.output/(case+'-report.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
   health=local.inspect_local(ROOT,data,config)
   with closing(sqlite3.connect(data/'db/sthpw.db')) as c:
    preserved=c.execute("SELECT config FROM widget_config WHERE code='NATIVE08_KEEP'").fetchone()[0]=='<config><custom_view keep="yes"/></config>'
   assert report['passed'] and health['startup_ready'] and preserved
   assert all(local.digest(backup/'original-files'/n)==h for n,h in before.items())
   item={'case':case,'passed':True,'completed_original_methods':len(report['completed']),
         'sql_errors':sum(x['status']=='error' for x in report['statements']),
         'required_structure_ready':health['structure_ready'],'custom_widget_config_preserved':preserved,
         'original_backups_hash_verified':True}
   second=local.perform_upgrade(ROOT,data,config,worker=worker)
   assert second['passed'] and second['completed']==[]
   item['repeat_completed_methods']=len(second['completed']);summary['cases'].append(item)
 summary['passed']=all(x['passed'] for x in summary['cases'])
except Exception as exc:
 summary.update(passed=False,error=str(exc));raise
finally:
 (a.output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
