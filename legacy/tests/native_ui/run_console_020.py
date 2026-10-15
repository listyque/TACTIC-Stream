"""Actual subprocess checks for the unified console. Temporary seed only.
No licence bypass is needed: read-only DB inspection precedes server imports.
No Windows execution is claimed by this portable runner.
"""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys, tempfile, time
from managed_seed_08 import ROOT, create_seed
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
report={'passed':False,'platform':sys.platform,'scenarios':[]}
def check(name,ok):
    report['scenarios'].append({'name':name,'passed':bool(ok)})
    print(('PASS ' if ok else 'FAIL ')+name,flush=True)
    if not ok: raise AssertionError(name)
def call(name,argv,expected):
    proc=subprocess.run([sys.executable,'-X','utf8','-s',*argv],cwd=ROOT,input=b'',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
    (a.output/(name+'.log')).write_bytes(proc.stdout)
    check(name+' exit',proc.returncode==expected)
    return proc.stdout.decode('utf-8',errors='replace')
def hashes(folder):
    return {str(x.relative_to(folder)):hashlib.sha256(x.read_bytes()).hexdigest() for x in folder.rglob('*') if x.is_file()}
try:
    with tempfile.TemporaryDirectory(prefix='TACTIC console & ! ') as temp:
        data=Path(temp)/'Данные & ! % (local)';create_seed(data);initial=hashes(data)
        script='tools/local/control.py'
        native='tools/local/launch.py'
        call('wrapped-check-db',[script,'check','db','--data-dir',str(data)],3)
        check('Read-only delegate preserves every seed/config file',hashes(data)==initial)
        wrapped=json.loads((ROOT/'.runtime/local-db-check.json').read_text())
        call('direct-check-db',[native,'--check-local-db','--data-dir',str(data)],3)
        direct=json.loads((ROOT/'.runtime/local-db-check.json').read_text())
        check('Wrapped/direct original reports identical',wrapped==direct)
        call('show-permissions',[script,'configure','--data-dir',str(data)],0)
        check('Showing settings does not enable writes',hashes(data)==initial)
        call('noninteractive-enable-refused',[script,'configure','--data-dir',str(data),'--writes','on'],2)
        check('Original ENABLE confirmation still mandatory',hashes(data)==initial)
        call('noninteractive-restore-refused',[script,'db','restore','--data-dir',str(data)],1)
        check('Original RESTORE confirmation still mandatory',hashes(data)==initial)
        for command in [['start'],['start','--single'],['start','--legacy'],['db','init'],['db','upgrade'],['db','restore']]:
            text=call('dry-'+('-'.join(command).replace('--','')), [script,*command,'--data-dir',str(data),'--dry-run'],0)
            plan=json.loads(text);check('Dry plan contains exact selected path: '+' '.join(command),str(data) in plan['argv'])
        check('All dry runs leave databases untouched',hashes(data)==initial)
        call('help-before-runtime',[script,'--help'],0)
        check('No automatic background processes by plans',hashes(data)==initial)
    report['passed']=True
finally:
    (a.output/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
