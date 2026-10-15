"""TEST ONLY: stock seed and real upgrade worker with isolated licence boundary.

Never imported by production. The CI environment lacks Cryptodome. Only
License.get is substituted; Batch, original migrations, Search, SqliteImpl and
complete on-disk seed databases are real. This is NOT a licence/login test.
"""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/local'))

def create_seed(data):
    shutil.copytree(ROOT/'src/install/start',data)
    tree=ET.Element('config',version='2')
    sections={'database':{'vendor':'Sqlite','sqlite_db_dir':str(data/'db')},
              'install':{'hostname':'127.0.0.1','server':'localvue-test'},
              'security':{'version':'2','allow_guest':'false'},
              'checkin':{'asset_base_dir':str(data/'assets'),'web_base_dir':'/assets'}}
    for name,values in sections.items():
        section=ET.SubElement(tree,name)
        for k,v in values.items():ET.SubElement(section,k).text=v
    config=data/'config/tactic-conf.xml';config.parent.mkdir(exist_ok=True)
    ET.ElementTree(tree).write(config,encoding='utf-8',xml_declaration=True)
    (data/'local-install.json').write_text(json.dumps({'format':1,'seed':'src/install/start','state':'seed-requires-upgrade'}))
    return config

def licence_isolated_worker(root,stage,log):
    with log.open('w',encoding='utf-8') as f:
        r=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker',str(stage)],
                         cwd=root,stdout=f,stderr=subprocess.STDOUT,check=False,timeout=120)
    return r.returncode

if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[1]!='--worker':raise SystemExit('TEST runner only: --worker STAGE')
    import launch
    stage=Path(sys.argv[2]);launch.configure_paths(stage,stage/'config/tactic-conf.xml')
    from unittest.mock import patch
    from pyasm.security.security import License
    from sqlite_worker import run_stage
    print('TEST ONLY: licence retrieval substituted; real migrations and SQLite seed, not production authentication.',flush=True)
    with patch.object(License,'get',return_value=object()):
        result=run_stage(stage)
    print('Original methods:',len(result['completed']),'passed:',result['passed'])
