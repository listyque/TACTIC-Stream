"""Persistent native-UI switches; separate from original TACTIC XML configuration.

The defaults remain read-only. Only an explicit local administrator operation
writes native-ui.json. Copying a new source fork no longer loses that decision.
"""
from pathlib import Path
import json
import os
import tempfile


def checked_settings(value):
    if not isinstance(value,dict):raise ValueError('Native settings must be an object')
    allowed={'site','allow_writes','allow_uploads','allow_script_execution','resumable_uploads'}
    if set(value)-allowed:raise ValueError('Unknown native setting: '+', '.join(sorted(set(value)-allowed)))
    for field in ('allow_writes','allow_uploads','allow_script_execution'):
        if field in value and type(value[field]) is not bool:raise ValueError(field+' must be a Boolean')
    if 'site' in value and (not isinstance(value['site'],str) or len(value['site'])>100):raise ValueError('Invalid site')
    if 'resumable_uploads' in value and not isinstance(value['resumable_uploads'],dict):raise ValueError('Invalid upload settings')
    return dict(value)


def load_settings(source_file,data_dir):
    base=checked_settings(json.loads(Path(source_file).read_text(encoding='utf-8-sig')))
    override=Path(data_dir)/'config/native-ui.json'
    if override.is_file():base.update(checked_settings(json.loads(override.read_text(encoding='utf-8-sig'))))
    return base


def save_settings(path,settings):
    path=Path(path);settings=checked_settings(settings)
    if settings.get('allow_uploads') and not settings.get('allow_writes'):raise ValueError('Uploads require allow_writes')
    if settings.get('allow_script_execution') and not settings.get('allow_writes'):raise ValueError('Script execution requires allow_writes')
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        backup=path.with_name(path.name+'.previous')
        backup.write_bytes(path.read_bytes())
        try:backup.chmod(0o600)
        except OSError:pass
    fd,temp=tempfile.mkstemp(prefix='.native-ui-',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(settings,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)
