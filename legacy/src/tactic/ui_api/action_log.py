"""Bounded, structured native action log. NEVER serializes request/response bodies.

Client events are reported intentions, not proof of command execution. Only the
server's request result is authoritative. This diagnostic log does not replace
TACTIC's transaction/sobject logs. One rotating file per OS worker; the gateway
relays only these structured records, never the legacy stdout (which may contain
tickets). No SQL parameters, field values, scripts, XML, passwords or headers.
"""
from contextvars import ContextVar
from pathlib import Path
from logging.handlers import RotatingFileHandler
import json
import logging
import os
import re
import sys
import threading
import time

TRACE = ContextVar('tactic_native_action_trace', default=None)
LOG = logging.getLogger('tactic.native.actions')
LOG.addHandler(logging.NullHandler())
LOCK = threading.RLock()
CONFIGURED = False
MODE = 'actions'
PENDING = {}
PENDING_LOCK = threading.RLock()
MONITOR = None
EVENTS = frozenset({'view.open','view.select','view.close','view.refresh','project.select',
                    'menu.open','menu.select','table.mode','table.search','table.create',
                    'cell.edit','cell.stage','cell.cancel','buffer.discard','buffer.save',
                    'form.open','form.save','form.cancel','graph.select','graph.save','graph.edit',
                    'tab.select','tab.close','sidebar.toggle','theme.toggle',
                    'layout.open','layout.save','layout.preview','view.create','view.copy','view.save',
                    'script.open','script.save','script.check','script.run','stype.open','stype.inspect'})
LABELS = {'security-matrix':'SECURITY MATRIX','user-groups':'USER GROUPS','stype-editor':'SEARCH TYPE EDITOR','sidebar-editor':'SIDEBAR EDITOR','open':'OPEN','query':'QUERY','sidebar':'SIDEBAR','graph':'GRAPH',
          'memberships':'GROUP MEMBERSHIP','record':'RECORD','table-changes':'SAVE TABLE',
          'cell-editor':'CELL EDITOR','form':'FORM','embedded-form':'EMBEDDED FORM',
          'project-create':'CREATE PROJECT','project-preflight':'CHECK PROJECT',
          'ui-state':'UI STATE','system-config':'SYSTEM CONFIG','context-menu':'CONTEXT MENU',
          'session':'SESSION','projects':'PROJECTS','upload-chunk':'UPLOAD CHUNK'}
LABELS.update({'design-catalog':'DESIGN CATALOG','layout-document':'CUSTOM LAYOUT','layout-preview':'LAYOUT PREVIEW','view-document':'MANAGE VIEWS','scripts':'SCRIPT CATALOG','script':'SCRIPT','script-check':'SCRIPT CHECK','script-run':'RUN SAVED SCRIPT','stype-dependencies':'COLUMN DEPENDENCIES','stype-import':'CSV IMPORT','script-diff':'SCRIPT DIFF'})
QUIET = frozenset({'/health','/ui-state','/upload-status'})
SECRET = re.compile(r'password|passwd|secret|token|ticket|cookie|authorization|csrf|signature|license|credential|two_factor|otp', re.I)
CONTROL = re.compile(r'[\x00-\x1f\x7f-\x9f]')


def plain(value, limit=180):
    """Single-line display only; never use this as a generic body sanitizer."""
    if not isinstance(value, (str, int, float, bool)):
        return ''
    return CONTROL.sub(' ', str(value)).strip()[:limit]


def names(value, limit=12):
    if not isinstance(value, (list, tuple, dict)):
        return []
    return [plain(x, 60) for x in list(value)[:limit] if isinstance(x, str) and not SECRET.search(x)]


def query_shape(data):
    """Show field/operator structure, NEVER filter operand values."""
    result = []
    def walk(node, depth=0):
        if depth > 5 or len(result) >= 12:
            return
        if isinstance(node, dict):
            if isinstance(node.get('field'), str):
                field = '<private-field>' if SECRET.search(node['field']) else plain(node['field'],60)
                op = plain(node.get('operator') or node.get('op') or 'eq',15)
                result.append(field+':'+op+'(?)')
            elif isinstance(node.get('children'), list) and node['children']:
                result.append(plain(node.get('op','and'),8)+'[')
                for child in node['children'][:12]:walk(child,depth+1)
                result.append(']')
        elif isinstance(node, (list, tuple)) and len(node) >= 2 and isinstance(node[0], str):
            result.append(('<private-field>' if SECRET.search(node[0]) else plain(node[0],60))+':filter(?)')
    for node in (data.get('filters') or [])[:12] if isinstance(data.get('filters'),list) else []:walk(node)
    if isinstance(data.get('where'),dict):walk(data['where'])
    return ' '.join(result)[:350]


class RequestTrace:
    def __init__(self, request, request_id):
        self.started=time.monotonic()
        self.event={'source':'server','request_id':request_id,'method':plain(request.method,10),
                    'route':plain(request.path,80)}
        correlation=request.headers.get('x-tactic-action-id','')
        if isinstance(correlation,str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}',correlation):
            self.event['action_id']=correlation
        self.project=None
        self.commands=[]
        self.token=None
        self.announced=False
        self.last_progress=self.started

    def begin(self):
        self.token=TRACE.set(self)
        with PENDING_LOCK:PENDING[id(self)]=self
        ensure_monitor()
        # The authenticated query metadata is emitted after parsing below.
        if self.event['route']=='/session' and self.event['method']!='GET':self.announce()
        return self

    def loggable(self):
        return MODE != 'off' and self.event['route'] != '/client-events' and (MODE == 'verbose' or not (
            self.event['route'] in QUIET or self.event['route'] == '/session' and self.event['method'] == 'GET'))

    def announce(self):
        if not self.announced and self.loggable():
            emit(dict(self.event,phase='start',state='queued',ms=round((time.monotonic()-self.started)*1000,1)))
            self.announced=True

    def progress(self, now=None):
        now=time.monotonic() if now is None else now
        if self.announced and now-self.last_progress >= 5:
            self.last_progress=now
            emit(dict(self.event,phase='running',ms=round((now-self.started)*1000,1),commands=list(self.commands)))

    def identity(self, session):
        self.event.update(user=plain(session.login,100),site=plain(session.site or 'default',100))

    def parameters(self, data):
        if not isinstance(data,dict):return
        self.project=plain(data.get('project'),100)
        if self.project:self.event['project']=self.project
        for key in ('target','kind','view','search_type','field','scope','record_state'):
            val=data.get(key)
            if isinstance(val,str) and not SECRET.search(key):self.event[key]=plain(val,350 if key=='target' else 100)
        for key in ('offset','limit'):
            val=data.get(key)
            if isinstance(val,int) and not isinstance(val,bool) and 0<=val<=10000000:self.event[key]=val
            elif isinstance(val,str) and val.isdecimal() and len(val)<8:self.event[key]=int(val)
        if isinstance(data.get('sort'),(dict,list)):
            sort=data['sort'] if isinstance(data['sort'],list) else [data['sort']]
            self.event['sort']=[plain(item.get('field',''),60)+':'+plain(item.get('direction','asc'),8)
                                for item in sort[:6] if isinstance(item,dict) and not SECRET.search(str(item.get('field','')))]
        shape=query_shape(data)
        if shape:self.event['filters']=shape
        if isinstance(data.get('values'),dict):self.event['fields']=names(data['values'])
        if isinstance(data.get('records'),list):
            self.event['rows_requested']=len(data['records'])
            self.event['fields']=names(dict.fromkeys(k for r in data['records'][:100] if isinstance(r,dict)
                                       for k in names(r.get('values',{}))))
        if isinstance(data.get('operations'),list):
            self.event['operations']=len(data['operations'])
        if isinstance(data.get('keys'),list):self.event['rows_requested']=len(data['keys'])
        # Keys are identifiers, but can contain user-controlled literal values: not printed by default.
        if data.get('key'):self.event['record_selected']=True
        self.announce()

    def resolve(self, target):
        self.event['state']='executing'
        # Inner re-resolution must not overwrite the final cell/tab target.
        if self.event.get('target') and plain(target.get('id'),350)!=self.event['target']:return
        for src,dst in (('handler','handler'),('kind','renderer'),('search_type','search_type'),('view','view')):
            if src == 'view' and target.get('kind') not in ('table','form','tabs'):
                self.event.pop('view',None)
                continue
            if isinstance(target.get(src),str):self.event[dst]=plain(target[src],160)
        if target.get('kind') == 'unsupported':self.event['notice']='unmapped-handler'

    def exception(self, exc):
        # Trace origin without exception values, source lines or local variables.
        import traceback
        self.event['error_frames']=[{'module':plain(frame.f_globals.get('__name__','?'),140),
             'function':plain(frame.f_code.co_name,80),'line':line}
             for frame,line in traceback.walk_tb(exc.__traceback__)][-4:]

    def finish(self, status, result, error=None):
        # Synchronize with the progress monitor: no RUNNING record after END.
        with PENDING_LOCK:PENDING.pop(id(self),None)
        try:
            self.event.update(phase='end',status=status,ms=round((time.monotonic()-self.started)*1000,1))
            if error:self.event['error']=plain(error,80)
            if isinstance(result,dict):
                if isinstance(result.get('items'),list):self.event['rows']=len(result['items'])
                for key in ('total','updated','cells'):
                    if isinstance(result.get(key),int):self.event[key]=result[key]
                if result.get('kind') and result.get('handler'):self.resolve(result)
            self.event['state']='completed' if status<400 else 'failed'
            if self.commands:self.event['commands']=self.commands[:12]
            route=self.event['route']
            if MODE!='off' and (status>=400 or (route!='/client-events' and
                    (MODE=='verbose' or not(route in QUIET and self.event['method']=='GET') and not(route=='/session' and self.event['method']=='GET')))):
                emit(self.event)
        finally:
            with PENDING_LOCK:PENDING.pop(id(self),None)
            if self.token is not None:TRACE.reset(self.token)


def ensure_monitor():
    global MONITOR
    if MODE=='off':return
    with PENDING_LOCK:
        if MONITOR is not None and MONITOR.is_alive():return
        def watch():
            while True:
                time.sleep(1)
                with PENDING_LOCK:
                    for trace in tuple(PENDING.values()):
                        try:trace.progress()
                        except Exception:pass
        MONITOR=threading.Thread(target=watch,name='tactic-request-progress',daemon=True)
        MONITOR.start()


def command_started(cmd):
    trace=TRACE.get()
    if trace is not None:
        name=type(cmd).__module__+'.'+type(cmd).__name__
        if name not in trace.commands and len(trace.commands)<12:trace.commands.append(plain(name,180))


def execute_traced(cmd):
    command_started(cmd)
    trace=TRACE.get(); started=time.monotonic()
    if trace is not None: trace.event['state']='command'
    try:
        return cmd.execute()
    finally:
        if trace is not None:
            trace.event['state']='executing'
            trace.event['command_ms']=round(trace.event.get('command_ms',0)+(time.monotonic()-started)*1000,1)



def resolved(target):
    trace=TRACE.get()
    if trace is not None:trace.resolve(target)


def authenticated(session):
    trace=TRACE.get()
    if trace is not None:trace.identity(session)


def parameters(data):
    trace=TRACE.get()
    if trace is not None:trace.parameters(data)


def client_events(data, session):
    from .contracts import ApiError
    events=data.get('events')
    if not isinstance(events,list) or not 1<=len(events)<=32:
        raise ApiError(400,'client_events','Ожидается 1–32 действия интерфейса')
    # Validate the whole batch before logging any item. Identity comes from the actual session.
    checked=[]
    for item in events:
        if not isinstance(item,dict) or set(item)-{'event','action_id','target','field','control','count'}:
            raise ApiError(400,'client_event','Недопустимые поля действия')
        if item.get('event') not in EVENTS:raise ApiError(400,'client_event','Неизвестное действие')
        event={'source':'client','event':item['event'],'user':plain(session.login,100),
               'site':plain(session.site or 'default',100),'project':plain(data.get('project'),100)}
        for key in ('action_id','target','field','control'):
            if key not in item:continue
            value=item[key]
            if not isinstance(value,str) or len(value)>(4000 if key=='target' else 100):
                raise ApiError(400,'client_event','Слишком длинный идентификатор действия')
            if key=='action_id' and not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',value):
                raise ApiError(400,'client_event','Некорректный action_id')
            if key in ('field','control') and SECRET.search(value):value='<private-field>'
            event[key]=plain(value,350 if key=='target' else 100)
        if 'count' in item:
            if type(item['count']) is not int or not 0<=item['count']<=1000000:
                raise ApiError(400,'client_event','Некорректное количество')
            event['count']=item['count']
        checked.append(event)
    if MODE!='off':
        for event in checked:emit(event)
    return {'accepted':len(checked)}


def short_target(value):
    value=plain(value,350)
    for marker in ('/~cell/','/~related/'):
        if marker in value:
            base,_=value.rsplit(marker,1)
            return '/'.join(base.split('/')[-2:])+marker[:-1]
    return '/'.join(value.split('/')[-3:])[:130]


def human(event):
    """Render only known keys. A compromised record cannot cause raw console injection."""
    ts=plain(event.get('time',''),40)
    main=event.get('event') if event.get('source')=='client' else LABELS.get(str(event.get('route','')).strip('/'),str(event.get('route','')).strip('/').upper())
    parts=[ts, f"[w{plain(event.get('worker','-'),4)}:{plain(event.get('pid',''),12)}]",
           plain(event.get('user','anonymous'),100)+'@'+plain(event.get('project','-'),100),
           'UI' if event.get('source')=='client' else plain(event.get('phase','end'),12).upper(),
           '' if event.get('source')=='client' else plain(event.get('method',''),10),plain(main,80)]
    for key,label in (('request_id','req'),('action_id','act'),('target','target'),('handler','widget'),
                      ('renderer','render'),('search_type','type'),('view','view'),('field','field'),
                      ('control','control'),('filters','filters'),('limit','limit'),('offset','offset'),
                      ('rows_requested','requested'),('rows','rows'),('total','total'),('updated','updated'),('cells','cells'),
                      ('operations','operations'),('count','count'),('state','state'),('command_ms','command_ms')):
        if key in event:
            value=short_target(event[key]) if key=='target' else plain(event[key],160)
            if key=='handler':value=value.rsplit('.',1)[-1]
            parts.append(label+'='+value)
    for key in ('sort','fields','commands'):
        val=event.get(key)
        if isinstance(val,list):parts.append(key+'='+','.join(plain(x,120).rsplit('.',1)[-1] if key=='commands' else plain(x,120) for x in val[:12]))
    if event.get('phase')=='running':parts.append('elapsed='+plain(event.get('ms',''),15)+'ms')
    if 'status'in event:parts.append('-> '+plain(event['status'],5)+' '+plain(event.get('ms',''),15)+'ms')
    if 'notice'in event:parts.append('notice='+plain(event['notice'],80))
    if 'error'in event:parts.append('error='+plain(event['error'],80))
    frames=event.get('error_frames')
    if isinstance(frames,list) and frames and isinstance(frames[-1],dict):
        f=frames[-1];parts.append('at='+plain(f.get('module',''),140)+':'+plain(f.get('line',''),10)+'/'+plain(f.get('function',''),80))
    return ' '.join(parts)


class JsonFormatter(logging.Formatter):
    def format(self, record):return json.dumps(record.action,ensure_ascii=False,separators=(',',':'))


class ConsoleFormatter(logging.Formatter):
    def format(self,record):return human(record.action)


class NativeAccessFilter(logging.Filter):
    def filter(self, record):
        # Keep legacy/other access lines and ALL error logs. Suppress only native duplicates.
        message = record.getMessage()
        if MODE == 'off' or ' /api/ui/v2/' not in message:
            return True
        # Some boundary rejections (e.g. Content-Length/413) happen before Api.handle.
        # Keep errors and unfamiliar formats so they cannot disappear from diagnostics.
        status = re.search(r'HTTP/[0-9.]+[\"\']\s+([0-9]{3})\b', message)
        return status is None or int(status.group(1)) >= 400


def configure(data_dir, mode=None):
    global CONFIGURED, MODE
    with LOCK:
        if CONFIGURED:return
        chosen=mode if mode is not None else os.environ.get('TACTIC_ACTION_LOG','actions')
        MODE=chosen if chosen in ('actions','verbose','off') else 'actions'
        LOG.setLevel(logging.INFO);LOG.propagate=False
        if MODE!='off':
            cluster=bool(os.environ.get('TACTIC_CLUSTER_WORKER_ID'))
            worker=os.environ.get('TACTIC_CLUSTER_WORKER_ID','standalone')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,20}',worker):worker='standalone'
            directory=Path(os.environ['TACTIC_ACTION_LOG_DIR']) if cluster and os.environ.get('TACTIC_ACTION_LOG_DIR') else Path(data_dir)/'log/native-actions'
            try:
                directory.mkdir(parents=True,exist_ok=True,mode=0o700)
                path=directory/('actions-'+worker+'.jsonl')
                handler=RotatingFileHandler(path,maxBytes=5*1024*1024,backupCount=3,encoding='utf-8')
                try:path.chmod(0o600)
                except OSError:pass
                handler.setFormatter(JsonFormatter());LOG.addHandler(handler)
                if not cluster:
                    stream=logging.StreamHandler(sys.stdout);stream.setFormatter(ConsoleFormatter());LOG.addHandler(stream)
            except OSError:
                # A logging failure must not turn a completed DB command into a reported failure.
                stream=logging.StreamHandler(sys.stdout);stream.setFormatter(ConsoleFormatter());LOG.addHandler(stream)
                print('TACTIC action log: file unavailable; using process console',file=sys.stderr,flush=True)
        CONFIGURED=True


def emit(event):
    record=dict(event,time=time.strftime('%Y-%m-%dT%H:%M:%S%z'),pid=os.getpid(),worker=os.environ.get('TACTIC_CLUSTER_WORKER_ID','-'))
    try:
        # Defensive record limit. No arbitrary structures are accepted by the producer.
        if len(json.dumps(record,ensure_ascii=False))>12000:return
        LOG.info('native-action',extra={'action':record})
    except Exception:
        pass  # Diagnostics must not alter API semantics (including a completed write).


class ActionLogTailer:
    """Only structured action logs are relayed; legacy output stays private.

    Open file handles are never held across iterations, permitting Windows
    rotation. Bytes already present on first discovery are read (fresh run-dir).
    Bounded non-blocking reads; not a durable audit delivery protocol.
    """
    def __init__(self,directory,workers,output=None):
        self.directory=Path(directory);self.workers=list(workers);self.output=output or (lambda line:print(line,flush=True))
        self.positions={};self.seen={};self.warning=False

    def poll(self):
        for worker in self.workers:
            path=self.directory/('actions-'+str(worker)+'.jsonl')
            try:
                stat=path.stat();signature=(stat.st_dev,stat.st_ino)
                old=self.positions.get(worker,(None,0))
                offset=old[1] if old[0]==signature and stat.st_size>=old[1] else 0
                with path.open('rb') as stream:
                    stream.seek(offset)
                    for _ in range(256):
                        pos=stream.tell();line=stream.readline(16385)
                        if not line:break
                        if not line.endswith(b'\n'):
                            if len(line)>16384:
                                # Skip a malformed overlong record, bounded by one block on each poll.
                                self.positions[worker]=(signature,stream.tell())
                            else:stream.seek(pos)
                            break
                        try:
                            event=json.loads(line)
                            if isinstance(event,dict) and event.get('source') in ('server','client'):
                                self.output(human(event))
                        except (ValueError,UnicodeDecodeError,TypeError):pass
                    self.positions[worker]=(signature,stream.tell())
            except OSError:
                continue
