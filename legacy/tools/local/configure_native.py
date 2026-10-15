"""Explicit local configuration of native UI write switches. No database access."""
from pathlib import Path
import argparse
import json
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(Path(__file__).resolve().parent)]
from tactic.core.native_settings import load_settings,save_settings
from local_lock import local_lock

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir',type=Path,default=ROOT/'local_data')
    p.add_argument('--writes',choices=['on','off'])
    p.add_argument('--uploads',choices=['on','off'])
    p.add_argument('--scripts',choices=['on','off'],help='Run saved Python scripts with the original PythonCmd; NOT a sandbox')
    args=p.parse_args(argv);data=args.data_dir.expanduser().resolve()
    if not (data/'config/tactic-conf.xml').is_file():raise ValueError('No existing TACTIC configuration in '+str(data)+'. Use --data-dir with your existing installation.')
    source=ROOT/'src/tactic/ui_api/config.json';settings=load_settings(source,data)
    path=data/'config/native-ui.json'
    print('Data:',data);print('Persistent UI settings:',path)
    print('Current settings:',json.dumps(settings,ensure_ascii=False))
    if args.writes is None and args.uploads is None and args.scripts is None:
        print('To ENABLE writes: MANAGE_TACTIC.bat configure --data-dir "'+str(data)+'" --writes on')
        print('To also ENABLE file uploads: add --uploads on. Changes require server restart.')
        return 0
    if args.writes:settings['allow_writes']=args.writes=='on'
    if args.uploads:settings['allow_uploads']=args.uploads=='on'
    if args.scripts:settings['allow_script_execution']=args.scripts=='on'
    if args.writes=='off':settings.update(allow_uploads=False,allow_script_execution=False)
    if settings.get('allow_script_execution') and not settings.get('allow_writes'):raise ValueError('Script execution requires --writes on explicitly.')
    if settings.get('allow_script_execution'):
        print('WARNING: saved Python runs with server permissions, filesystem and DB access. Not a sandbox.')
    if settings.get('allow_uploads') and not settings.get('allow_writes'):raise ValueError('Uploads require writes. Set --writes on explicitly.')
    print('Requested settings:',json.dumps(settings,ensure_ascii=False))
    confirm='ENABLE' if settings.get('allow_writes') else 'DISABLE'
    if not sys.stdin.isatty() or input('Stop TACTIC first. Type '+confirm+' to save: ').strip()!=confirm:raise ValueError('Cancelled; no changes')
    with local_lock(data):save_settings(path,settings)
    print('Saved. Restart TACTIC. The same data directory preserves these switches across source releases.')
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,RuntimeError) as exc:print('ERROR:',exc);raise SystemExit(2)
