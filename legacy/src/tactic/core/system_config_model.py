"""Data projection of DbConfigContentWdg, without HTML or restart side effects.

The field groups and persisted section/key names follow startup/db_config_wdg.py.
Only edits are written: unknown sections, attributes and secrets are preserved.
Connection/bootstrap and process restart are deliberately separate operations.
"""
from pathlib import Path
import hashlib
import os
import re
import tempfile
import time
from lxml import etree

GROUPS = (
 ('Database Setup', 'database', ('vendor','sqlite_db_dir','server','port','user','password','encoding','charset')),
 ('Installation', 'install', ('default_project','tmp_dir')),
 ('Asset Management', 'checkin', ('asset_base_dir','web_base_dir')),
 ('Mail Server', 'services', ('mailserver','mail_user','mail_password','mail_port','mail_tls_enabled','mail_sender_disabled')),
 ('Services', 'services', ('process_count','process_time_alive','thread_count','python_path','rsync')),
 ('Look and Feel', 'look', ('palette',)),
 ('Security', 'security', ('ticket_expiry','authenticate_mode','authenticate_class','authenticate_version','auto_create_user','api_require_password','api_password','max_login_attempt','account_logout_duration','allow_guest','guest_mode')),
)
BOOLEANS = {'mail_tls_enabled','mail_sender_disabled','auto_create_user','api_require_password','allow_guest'}
INTEGERS = {'port','mail_port','process_count','process_time_alive','thread_count','max_login_attempt','account_logout_duration'}
VENDORS = ('PostgreSQL','MySQL','Sqlite','Oracle','SQLServer')
SECRET = re.compile(r'password|secret|private_key|api_key|token', re.I)


def read_document(path):
    path = Path(path)
    raw = path.read_bytes()
    if len(raw) > 2*1024*1024 or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('Unsupported or oversized system XML')
    parser = etree.XMLParser(resolve_entities=False, no_network=True, remove_blank_text=False, strip_cdata=False)
    root = etree.fromstring(raw, parser)
    if root.tag != 'config':
        raise ValueError('System configuration must have a <config> root')
    return raw, root


def config_fields(root):
    groups = []
    checkin = root.find('checkin')
    dynamic = tuple(n.tag for n in checkin if isinstance(n.tag,str)) if checkin is not None else ()
    for title, section, keys in GROUPS:
        if section == 'checkin':
            keys = tuple(dict.fromkeys((*keys,*dynamic,'win32_client_handoff_dir' if os.name=='nt' else 'linux_client_handoff_dir')))
        fields=[]
        for key in keys:
            node = root.find(section+'/'+key)
            value = node.text if node is not None and node.text is not None else ''
            secret = bool(SECRET.search(key))
            kind = 'secret' if secret else 'boolean' if key in BOOLEANS else 'integer' if key in INTEGERS else 'text'
            choices = VENDORS if key == 'vendor' else ()
            fields.append({'name':section+'/'+key,'label':key,'kind':kind,'value':'' if secret else value,
                           'present':node is not None, 'configured':bool(value), 'secret':secret,
                           'choices':list(choices), 'restart_required':True})
        groups.append({'title':title,'section':section,'fields':fields})
    return groups


def patch_config(path, expected, changes):
    """Atomic file replacement, private backup, no reload until server restart.

    The caller must supply authorization, request serialization and allow_writes.
    This does not protect against an unrelated external writer during os.replace.
    """
    path=Path(path).resolve()
    raw,root=read_document(path)
    digest=hashlib.sha256(raw).hexdigest()
    if digest != expected: raise FileExistsError('System configuration changed; reload before saving')
    if not isinstance(changes,dict) or not changes or len(changes)>200: raise ValueError('Expected 1–200 changed settings')
    known={f['name']:f for group in config_fields(root) for f in group['fields']}
    for name,value in changes.items():
        field=known.get(name)
        if not field: raise ValueError('Unknown system setting: '+str(name))
        if not isinstance(value,str) or len(value)>10000 or '\x00' in value: raise ValueError('Invalid setting value: '+name)
        if field['kind']=='boolean' and value not in ('','true','false'): raise ValueError('Expected true/false: '+name)
        if field['kind']=='integer' and value and (not value.isdecimal() or int(value)>2147483647): raise ValueError('Expected non-negative integer: '+name)
        if field['choices'] and value not in field['choices']: raise ValueError('Invalid database vendor')
        section,key=name.split('/',1)
        parents=root.findall(section)
        if len(parents)>1:raise ValueError('Ambiguous duplicate section: '+section)
        parent=root.find(section)
        if parent is None:parent=etree.SubElement(root,section)
        nodes=parent.findall(key)
        if len(nodes)>1:raise ValueError('Ambiguous duplicate system setting: '+name)
        if section=='install' and key=='default_project' and value=='':
            if nodes:parent.remove(nodes[0])
        else:
            node=nodes[0] if nodes else etree.SubElement(parent,key)
            node.text=value
    out=etree.tostring(root,encoding='utf-8',xml_declaration=True)
    backup_dir=path.parent/'native-config-backups'
    backup_dir.mkdir(mode=0o700,exist_ok=True)
    backup=backup_dir/(time.strftime('%Y%m%d-%H%M%S')+'-'+digest[:12]+'.xml')
    # Do not create broad-readable copies of passwords from the original config.
    fd=os.open(backup,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600) if not backup.exists() else None
    if fd is not None:
        with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    fd,tmp=tempfile.mkstemp(prefix='.native-config-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:stream.write(out);stream.flush();os.fsync(stream.fileno())
        os.chmod(tmp,path.stat().st_mode & 0o777)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise FileExistsError('Configuration changed during save')
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return {'revision':hashlib.sha256(out).hexdigest(),'backup_created':True,'restart_required':True}
