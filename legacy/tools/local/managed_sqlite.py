"""Stage/validate/publish a managed LOCAL SQLite upgrade; no in-place retry.

Only installations created by INIT_LOCAL_SQLITE are accepted. The original
upgrade worker runs against copies. Existing configs, assets and templates are
not replaced. A durable promotion journal and retained original files protect
multi-database publication; a pending journal blocks normal startup.
"""
from __future__ import annotations
from collections import Counter
from contextlib import closing
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from local_lock import local_lock

PENDING='.sqlite-promotion.json'

def atomic_json(path: Path, value):
    temp=path.with_name(path.name+'.tmp-'+uuid.uuid4().hex)
    try:
        with temp.open('x',encoding='utf-8') as f:
            json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:
        if temp.exists():temp.unlink()

def digest(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        while block:=f.read(4*1024*1024):h.update(block)
    return h.hexdigest()

def ro(path: Path):
    return sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)

def layout(data: Path, config: Path):
    data=data.resolve();config=config.resolve()
    if config!=data/'config/tactic-conf.xml' or not (data/'local-install.json').is_file():
        raise ValueError('Only the managed LOCAL SQLite installation is supported. No external/MySQL/PostgreSQL database will be touched.')
    marker=json.loads((data/'local-install.json').read_text(encoding='utf-8-sig'))
    if marker.get('format')!=1 or marker.get('seed')!='src/install/start':
        raise ValueError('Unknown local installation marker; automatic adoption refused')
    tree=ET.parse(config)
    if tree.findtext('database/vendor')!='Sqlite':raise ValueError('This is not SQLite; use the correct vendor upgrade procedure')
    path=tree.findtext('database/sqlite_db_dir')
    if not path or Path(path).resolve()!=(data/'db').resolve():
        raise ValueError('Config redirects SQLite outside the managed db directory; refused')
    if (data/'db').is_symlink():raise ValueError('Symlinked database directory is not managed')
    files={}
    for p in sorted((data/'db').glob('*.db')):
        if p.is_symlink() or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*\.db',p.name):raise ValueError('Unsafe database file '+p.name)
        with p.open('rb') as header: magic=header.read(16)
        if magic!=b'SQLite format 3\x00':raise ValueError('Not an ordinary SQLite database: '+p.name)
        files[p.name]=p
    if 'sthpw.db' not in files:raise ValueError('Missing managed sthpw.db')
    with closing(ro(files['sthpw.db'])) as c:
        c.row_factory=sqlite3.Row
        cols={x[1] for x in c.execute('PRAGMA table_info(project)')}
        rows=[dict(row) for row in c.execute('SELECT * FROM project')]
        resources=c.execute('SELECT COUNT(*) FROM db_resource').fetchone()[0] if c.execute("SELECT 1 FROM sqlite_master WHERE name='db_resource'").fetchone() else 0
        if resources:
            raise ValueError('Custom db_resource entries require DBA review; staged upgrade must not connect to an external resource')
    databases={}
    for row in rows:
        code=row.get('code')
        if code=='admin' or (row.get('s_status')=='retired' and code!='sthpw'):continue
        if row.get('db_resource'):raise ValueError('External project db_resource refused: '+str(code))
        if code!='sthpw' and row.get('type') not in (None,'','default','simple','unittest'):
            raise ValueError('This managed repair supports stock default/simple projects only: '+str(code))
        name=row.get('database') or code
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*',name):raise ValueError('Unsupported project database name')
        filename=name+'.db'
        if filename not in files:raise ValueError('Missing registered project database '+filename)
        databases[code]=filename
    if 'sthpw' not in databases:raise ValueError('Missing registered sthpw project')
    if len(set(databases.values()))!=len(databases):raise ValueError('Several projects share a database; manual migration review required')
    return marker,tree,files,databases

def fingerprint(files):
    result={}
    for name,path in files.items():
        result[name]=digest(path)
        for suffix in ('-wal','-shm','-journal'):
            p=Path(str(path)+suffix)
            if p.exists():result[name+suffix]=digest(p)
    return result

def _require_quiet_files(files):
    for name,path in files.items():
        for suffix in ('-wal','-journal'):
            p=Path(str(path)+suffix)
            if p.exists() and p.stat().st_size:
                raise ValueError('A live/recovery SQLite journal exists for '+name+'. Stop all servers and close database tools before retrying; do not delete journals manually.')
        # A read-write connection is used ONLY to probe an exclusive lock. No
        # SQL writes/checkpoint or application migrations are executed here.
        c=sqlite3.connect(path.resolve().as_uri()+'?mode=rw',uri=True,timeout=0.2)
        try:c.execute('BEGIN EXCLUSIVE');c.rollback()
        finally:c.close()

def inspect_local(root: Path,data: Path,config: Path):
    sys.path.insert(0,str(root/'src')) if str(root/'src') not in sys.path else None
    from tactic.core.schema_health import inspect_schema
    from tactic.core.sqlite_upgrade import identity_issues
    marker,tree,files,databases=layout(data,config)
    with closing(ro(files['sthpw.db'])) as c:
        registry=dict(c.execute('SELECT search_type,table_name FROM search_object'))
        versions=[{'project':r[0],'last_version_update':r[1]} for r in c.execute('SELECT code,last_version_update FROM project')]
    result={'vendor':'Sqlite','sqlite_library':sqlite3.sqlite_version,'state':marker.get('state'),
            'pending_promotion':(data/PENDING).exists(),'versions':versions,'databases':{}}
    for code,name in databases.items():
        with closing(ro(files[name])) as c:
            q=lambda t:[r[1] for r in c.execute('PRAGMA table_info("'+t.replace('"','""')+'")')]
            health=inspect_schema(q,registry,include_core=code=='sthpw')
            health['identity_issues']=identity_issues(c)
            if health['identity_issues']:health['ready']=False
            health['integrity_check']=[r[0] for r in c.execute('PRAGMA quick_check')]
            result['databases'][code]=health
    result['structure_ready']=all(v['ready'] and v['integrity_check']==['ok'] for v in result['databases'].values())
    result['startup_ready']=result['structure_ready'] and marker.get('state')=='upgraded' and not result['pending_promotion']
    return result

def default_worker(root: Path,stage: Path,log: Path):
    with log.open('w',encoding='utf-8') as stream:
        result=subprocess.run([sys.executable,'-X','utf8','-s',str(root/'tools/local/sqlite_worker.py'),str(stage)],
                              cwd=root,stdout=stream,stderr=subprocess.STDOUT,check=False)
    return result.returncode

def _safe_backup(data,pending):
    backup=(data/pending['backup']).resolve()
    if not backup.is_relative_to((data/'backup').resolve()):raise ValueError('Invalid promotion backup path')
    return backup

def restore_pending(data: Path):
    pending_path=data/PENDING
    if not pending_path.exists():raise ValueError('There is no interrupted promotion to restore')
    state=json.loads(pending_path.read_text(encoding='utf-8'))
    backup=_safe_backup(data,state)
    # Validate EVERY file before restoring any, to avoid overwriting later edits.
    for name,info in state['files'].items():
        if Path(name).name!=name or not name.endswith('.db'):raise ValueError('Invalid promotion database name')
        dest=data/'db'/name;saved=backup/'original-files'/name
        if saved.exists():
            if digest(saved)!=info['before']:raise ValueError('Original backup hash mismatch: '+name)
            if dest.exists() and digest(dest)!=info['after']:raise ValueError('Database changed after promotion: '+name+'; automatic rollback refused')
        elif not dest.exists() or digest(dest)!=info['before']:
            raise ValueError('Cannot safely restore '+name+'; preserve this backup and investigate')
    for name in state['files']:
        saved=backup/'original-files'/name
        if saved.exists():os.replace(saved,data/'db'/name)
    shutil.copy2(backup/'local-install.json',data/'local-install.json')
    pending_path.unlink()
    return backup

def publish(data: Path, stage: Path, backup: Path, files, before, marker, report):
    if fingerprint(files)!=before:raise RuntimeError('Original database files changed while the upgrade ran. Staged changes NOT installed.')
    _require_quiet_files(files)
    info={name:{'before':digest(p),'after':digest(stage/'db'/name)} for name,p in files.items()}
    pending={'format':1,'backup':str(backup.relative_to(data)),'files':info}
    atomic_json(data/PENDING,pending)
    (backup/'original-files').mkdir()
    try:
        for name,source in files.items():
            os.replace(source,backup/'original-files'/name)
            os.replace(stage/'db'/name,source)
        result=dict(marker,state='upgraded',version=report['target'],backup=str(backup),
                    schema_adapter='native-sqlite-0.8',identity_adapter='1.1',upgrade_report=str(backup/'upgrade-report.json'))
        atomic_json(data/'local-install.json',result)
        (data/PENDING).unlink()
    except BaseException:
        # Ordinary exceptions are rolled back immediately. Process/power death
        # leaves the durable journal for MANAGE_TACTIC.bat db restore.
        restore_pending(data)
        raise

def perform_upgrade(root: Path,data: Path,config: Path, *, worker=default_worker):
    with local_lock(data):
        if (data/PENDING).exists():raise RuntimeError('Interrupted database publication detected. Run MANAGE_TACTIC.bat db restore first.')
        marker,tree,files,databases=layout(data,config)
        _require_quiet_files(files)
        before=fingerprint(files)
        control_hashes=(digest(config),digest(data/'local-install.json'))
        total=sum(p.stat().st_size for p in files.values())
        if shutil.disk_usage(data).free<2*total+64*1024*1024:raise RuntimeError('Not enough free space for backup and staged migration')
        stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
        backup=data/'backup'/stamp;backup.mkdir(parents=True,mode=0o700)
        (backup/'db').mkdir()
        stage=backup/'stage';(stage/'db').mkdir(parents=True)
        shutil.copytree(data/'config',stage/'config')
        shutil.copy2(config,backup/'tactic-conf.xml')
        shutil.copy2(data/'local-install.json',backup/'local-install.json')
        for name,source in files.items():
            with closing(ro(source)) as src,closing(sqlite3.connect(backup/'db'/name)) as dst:
                src.backup(dst);dst.commit()
            shutil.copymode(source,backup/'db'/name)
            shutil.copy2(backup/'db'/name,stage/'db'/name)
        # Redirect all possible filesystem side effects to the staging tree.
        for category,key,value in [('database','sqlite_db_dir',stage/'db'),('checkin','asset_base_dir',stage/'assets')]:
            parent=tree.getroot().find(category)
            if parent is None:parent=ET.SubElement(tree.getroot(),category)
            node=parent.find(key)
            if node is None:node=ET.SubElement(parent,key)
            node.text=str(value).replace('\\','/')
        for node in tree.getroot().findall('checkin/*'):
            if node.tag.endswith(('_repo_dir','_sandbox_dir')):node.text=str(stage/'assets')
        tree.write(stage/'config/tactic-conf.xml',encoding='utf-8',xml_declaration=True)
        try:(stage/'config/tactic-conf.xml').chmod(0o600)
        except OSError:pass
        for folder in ('assets','tmp','temp','templates','plugins','log'):(stage/folder).mkdir(exist_ok=True)
        # Old failed upgrades may have falsely stamped the DB as version 5.0.
        repair=marker.get('state')!='upgraded' or marker.get('schema_adapter')!='native-sqlite-0.8'
        atomic_json(stage/'upgrade-stage.json',{'format':1,'databases':databases,'repair_from':'2.5.0.v01' if repair else None})
        print('Backup:',backup)
        print('Original TACTIC migrations will run against staged copies, not the original database files.')
        code=worker(root,stage,backup/'worker.log')
        report_path=stage/'upgrade-report.json'
        report=json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {'passed':False,'error':'Worker did not produce a report'}
        atomic_json(backup/'upgrade-report.json',report)
        if code or not report.get('passed'):
            raise RuntimeError('Staged upgrade FAILED; original databases were NOT replaced. '+str(report.get('error','See worker log'))+'\nLog: '+str(backup/'worker.log'))
        if (digest(config),digest(data/'local-install.json'))!=control_hashes:
            raise RuntimeError('Config/installation marker changed during upgrade. Staged changes NOT installed.')
        publish(data,stage,backup,files,before,marker,report)
        counts=dict(Counter(s['status'] for s in report.get('statements',[])))
        print('Upgrade installed. Completed original methods:',len(report.get('completed',[])))
        print('SQL decisions:',json.dumps(counts,ensure_ascii=False))
        print('Report:',backup/'upgrade-report.json')
        print('Run MANAGE_TACTIC.bat check db, then START_TACTIC.bat --single.')
        return report
