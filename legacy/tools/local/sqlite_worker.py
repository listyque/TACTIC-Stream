"""Internal worker: run ORIGINAL TACTIC upgrade methods only on staged databases."""
from pathlib import Path
from contextlib import closing
import json
import sqlite3
import sys
import traceback
import xml.etree.ElementTree as ET
# Windows embeddable Python does not automatically add this directory.
sys.path.insert(0,str(Path(__file__).resolve().parent))
import launch

ROOT=launch.ROOT

def run_stage(stage: Path):
    stage=stage.resolve();control=stage/'upgrade-stage.json'
    if not control.is_file():raise ValueError('Not an explicit managed upgrade staging directory')
    meta=json.loads(control.read_text(encoding='utf-8'))
    config=stage/'config/tactic-conf.xml'
    xml=ET.parse(config).getroot()
    if xml.findtext('database/vendor')!='Sqlite' or Path(xml.findtext('database/sqlite_db_dir')).resolve()!=stage/'db':
        raise ValueError('Staging config does not point exclusively at its own SQLite directory')
    launch.configure_paths(stage,config)
    from tactic.core.sqlite_upgrade import prepare_config_schema,split_sql,strip_comments,create_parts,SQLiteUpgrade,repair_identity_columns,identity_issues
    from tactic.core.schema_health import inspect_schema
    state={'format':1,'target':(ROOT/'VERSION').read_text().strip().replace('_','.'),
           'repair_from':meta.get('repair_from'),'aliases':{},'statements':[],'completed':[],'passed':False}
    report=stage/'upgrade-report.json'
    try:
        with closing(sqlite3.connect(stage/'db/sthpw.db')) as db:
            registry=dict(db.execute('SELECT search_type,table_name FROM search_object'))
        ddl=(ROOT/'src/pyasm/search/upgrade/sqlite/config_schema.sql').read_text()
        # config/custom_property is registered by the seed but missing from the
        # project seed. Its definition is the ORIGINAL shared sthpw schema.
        custom=None
        for sql in split_sql((ROOT/'src/pyasm/search/upgrade/sqlite/sthpw_schema.sql').read_text()):
            cleaned=strip_comments(sql).strip()
            if cleaned.startswith('CREATE TABLE') and create_parts(cleaned)[0]=='custom_property':custom=cleaned
        for code,name in meta['databases'].items():
            with closing(sqlite3.connect(stage/'db'/name)) as db:
                db.execute('PRAGMA journal_mode=DELETE')
                state['aliases'][code]=prepare_config_schema(db,ddl,registry,state['statements'])
                if custom:
                    SQLiteUpgrade(db,journal=state['statements'],method=code+'/stock_config_custom_property').execute(custom)
                repair_identity_columns(db,state['statements'])
                db.commit()
        from pyasm.security import Batch
        from pyasm.search import DbContainer
        from pyasm.search.upgrade.upgrade_db import Upgrade
        try:
            Batch(project_code='admin',login_code='admin')
            command=Upgrade(state['target'],is_forced=False,is_confirmed=True,quiet=True,sqlite_managed=state)
            command.execute()
            if command.errors:raise RuntimeError('Original upgrade reported errors: '+str(command.errors[:10]))
        finally:DbContainer.close_all()
        with closing(sqlite3.connect(stage/'db/sthpw.db')) as db:
            registry=dict(db.execute('SELECT search_type,table_name FROM search_object'))
        state['databases']={}
        for code,name in meta['databases'].items():
            with closing(sqlite3.connect(stage/'db'/name)) as db:
                q=lambda table:[r[1] for r in db.execute('PRAGMA table_info("'+table.replace('"','""')+'")')]
                repair_identity_columns(db,state['statements'])
                health=inspect_schema(q,registry,include_core=code=='sthpw')
                health['identity_issues']=identity_issues(db)
                if health['identity_issues']:health['ready']=False
                integrity=[r[0] for r in db.execute('PRAGMA integrity_check')]
                foreign=list(db.execute('PRAGMA foreign_key_check'))
                health.update(integrity_check=integrity,foreign_key_violations=len(foreign))
                state['databases'][code]=health
                if not health['ready'] or integrity!=['ok'] or foreign:
                    raise RuntimeError('Post-upgrade structure/integrity check failed for '+code+': '+str(health))
                db.commit()
        state['passed']=True
        return state
    except Exception as exc:
        state['error']=str(exc);state['traceback']=traceback.format_exc();raise
    finally:
        report.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
    try:
        if len(sys.argv)!=2:raise ValueError('Internal usage: sqlite_worker.py STAGE')
        r=run_stage(Path(sys.argv[1]));print('Staged original migrations completed:',len(r['completed']));raise SystemExit(0)
    except Exception:
        traceback.print_exc();raise SystemExit(1)
