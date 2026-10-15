"""Refresh all native Administration snapshots before browser comparison."""
import os,subprocess,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
root=Path(__file__).resolve().parents[2]
os.environ['FRAME_CAPTURE_QUICK']='0'
(root/'.tmp/frame-tests').mkdir(parents=True,exist_ok=True)
out=root/'tools/frame_admin/output/capture';out.mkdir(parents=True,exist_ok=True)
os.environ.update(TMP=str(root/'.tmp/frame-tests'),TEMP=str(root/'.tmp/frame-tests'))
commands=[['tools/frame_groups/capture_qml.py'],['tools/frame_groups/capture_qml.py','--users']]+[[f'tools/frame_{name}/capture_qml.py'] for name in ['security','raw','sidebar','columns','types','naming','graph','graph_editor','layout','shell','rules','deletion']]
def capture(args):
 label=args[0].split('/')[1]+('-users' if len(args)>1 else '')
 with (out/(label+'.log')).open('w',encoding='utf8') as log:
  result=subprocess.run([sys.executable,'-B','-X','utf8','-X','faulthandler',*args],cwd=root,stdout=log,stderr=subprocess.STDOUT,timeout=300)
 print(label,result.returncode,flush=True)
 return result.returncode

with ThreadPoolExecutor(max_workers=2) as pool:
 results=list(pool.map(capture,commands))
if any(results):raise SystemExit(next(status for status in results if status))
