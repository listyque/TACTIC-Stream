"""Original full seed -> old SERIAL shape -> staged identity repair -> repeat.

Disposable data only. --isolate-license is TEST ONLY, no SQL/model replacement.
"""
from contextlib import closing
from pathlib import Path
import argparse,json,sqlite3,sys,tempfile
from managed_seed_08 import ROOT,create_seed,licence_isolated_worker
import managed_sqlite as local
sys.path.insert(0,str(ROOT/'src'))
from tactic.core.sqlite_upgrade import SQLiteUpgrade,create_parts,column_name,identity_issues
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);p.add_argument('--isolate-license',action='store_true');a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
summary={'full_original_seed':True,'sql_mocked':False,'signature_verification_isolated':a.isolate_license,'passed':False,'checks':[]}
worker=licence_isolated_worker if a.isolate_license else local.default_worker
def check(name,ok):
 if not ok:raise AssertionError(name)
 summary['checks'].append({'name':name,'passed':True})
try:
 with tempfile.TemporaryDirectory(prefix='tactic-identity11-') as tmp:
  data=Path(tmp)/'data';config=create_seed(data);first=local.perform_upgrade(ROOT,data,config,worker=worker);check('Clean original seed upgrade completes 402 methods',first['passed'] and len(first['completed'])==402)
  with closing(sqlite3.connect(data/'db/sthpw.db')) as db:
   tables=('spt_client_trigger','spt_ingest_rule','spt_ingest_session','spt_plugin','spt_process','spt_url')
   adapter=SQLiteUpgrade(db)
   for name in tables:
    sql=db.execute('SELECT sql FROM sqlite_master WHERE name=?',(name,)).fetchone()[0]
    _,defs,suffix=create_parts(sql)
    defs=['id serial PRIMARY KEY' if column_name(d)=='id' else d for d in defs]
    adapter.rebuild(name,defs,suffix)
   db.execute("INSERT INTO spt_process(code,pipeline_code,process,workflow) VALUES('KEEP_PROCESS11','test','design','{\"key\":\"001\"}')")
   db.execute("INSERT INTO widget_config(code,view,config) VALUES('KEEP_UI11','custom','<config><custom unknown=\"preserve\"><element name=\"name\"/></custom></config>')")
   db.commit();row=db.execute("select rowid,id,code,workflow,typeof(workflow) from spt_process where code='KEEP_PROCESS11'").fetchone()
   check('Old SERIAL schema reproduces NULL id on actual full seed',row[1] is None and len(identity_issues(db))==6)
  mark=json.loads((data/'local-install.json').read_text());mark.pop('identity_adapter',None);(data/'local-install.json').write_text(json.dumps(mark))
  before={n:local.digest(f) for n,f in local.layout(data,config)[2].items()}
  health=local.inspect_local(ROOT,data,config);check('Read-only DB diagnostic refuses incorrect identity shape',not health['startup_ready'])
  report=local.perform_upgrade(ROOT,data,config,worker=worker)
  (out/'repair-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
  check('Already upgraded schema does not replay historical methods',report['passed'] and len(report['completed'])==0)
  check('All six SERIAL identities repaired on staged copies',sum(s['status']=='identity_repaired' for s in report['statements'])==6)
  with closing(sqlite3.connect(data/'db/sthpw.db')) as db:
   fixed=db.execute("select rowid,id,code,workflow,typeof(workflow) from spt_process where code='KEEP_PROCESS11'").fetchone()
   check('Missing id filled from preserved ROWID; code/value/storage remain',fixed==(row[0],row[0],row[2],row[3],row[4]))
   check('User widget_config XML preserved byte-for-byte',db.execute("select config from widget_config where code='KEEP_UI11'").fetchone()[0]=='<config><custom unknown="preserve"><element name="name"/></custom></config>')
   db.execute("INSERT INTO spt_process(code,pipeline_code,process) VALUES('NEXT_PROCESS11','test','approval')")
   check('Next original-style insert receives real primary key',db.execute("select id from spt_process where code='NEXT_PROCESS11'").fetchone()[0]>row[0]);db.commit()
  marker=json.loads((data/'local-install.json').read_text());backup=Path(marker['backup'])
  check('Original database backup hashes match before upgrade',all(local.digest(backup/'original-files'/name)==value for name,value in before.items()))
  check('Original managed checker accepts repaired schema',local.inspect_local(ROOT,data,config)['startup_ready'])
  again=local.perform_upgrade(ROOT,data,config,worker=worker)
  check('Repeat executes zero historical methods and zero identity rebuilds',again['passed'] and not again['completed'] and not any(s['status']=='identity_repaired' for s in again['statements']))
  summary['original_initial_methods']=len(first['completed']);summary['original_repair_methods']=len(report['completed']);summary['passed']=True
except Exception as exc:summary['error']=str(exc);raise
finally:(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
