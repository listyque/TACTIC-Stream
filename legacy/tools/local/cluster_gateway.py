"""Bounded localhost-only WSGI reverse proxy used with bundled Cheroot.

Only explicit native read routes are balanced (including POST /query). Legacy/RPC, login and all mutations
stay on worker 1 (the primary). NO request is automatically retried, even a read. Losing a
write response never implies that the original command did not commit.
"""
from contextlib import nullcontext
import http.client
import json
import threading
from urllib.parse import urlsplit

READ_ROUTES = frozenset(('/session','/projects','/catalog','/sidebar','/open','/query','/record','/form',
    '/resolved-view','/timeline','/context-menu','/configs','/config','/view-config','/graph',
    '/search-types','/memberships','/tasks','/task-form','/task-hours','/history','/relations',
    '/relationship','/relation-candidates','/notes','/file-versions','/file','/collections',
    '/collection-members','/users','/security','/project-create','/system','/scripts','/script',
    '/messages','/message-history','/subscriptions','/chats','/chat-users','/record-subscription',
    '/snapshot-current','/system-config','/license','/ui-state','/security-matrix','/user-groups','/stype-editor','/sidebar-editor','/design-catalog','/layout-document','/view-document','/stype-dependencies'))
HOP = frozenset(('connection','keep-alive','proxy-authenticate','proxy-authorization','te',
                 'trailer','trailers','transfer-encoding','upgrade','proxy-connection'))
MAX_BODY = 32 * 1024 * 1024
BLOCK = 64 * 1024


def is_balanced(method, path):
    # PATH_INFO is decoded by WSGI. This is an exact allowlist, not prefix trust.
    return (method == 'POST' and path == '/api/ui/v2/query') or (method == 'GET' and path.startswith('/api/ui/v2/') and path[len('/api/ui/v2'):] in READ_ROUTES)


def filtered_headers(pairs):
    pairs = list(pairs)
    connection = {x.strip().lower() for k,v in pairs if k.lower() == 'connection' for x in v.split(',')}
    return [(k,v) for k,v in pairs if k.lower() not in HOP | connection]


class RoutingPool:
    def __init__(self, workers):
        self.workers = workers
        self.lock = threading.RLock()
        self.cursor = 0
        self.write_lock = threading.Lock()

    def select(self, balanced):
        with self.lock:
            if not balanced:
                w = self.workers[0]
                if not w['healthy']: return None
            else:
                live = [w for w in self.workers if w['healthy']]
                if not live: return None
                w = live[self.cursor % len(live)]
                self.cursor += 1
            w['requests'] += 1
            w['active'] += 1
            return w

    def done(self, worker):
        with self.lock: worker['active'] -= 1


class Gateway:
    def __init__(self, pool, secret, public_port, timeout=300):
        self.pool, self.secret, self.public_port, self.timeout = pool, secret, public_port, timeout

    @staticmethod
    def error(start, status, code, message):
        data = json.dumps({'error': {'code': code, 'message': message}}, ensure_ascii=False).encode('utf-8')
        start(status, [('Content-Type','application/json; charset=utf-8'),('Content-Length',str(len(data))),
                       ('Cache-Control','no-store'),('X-Content-Type-Options','nosniff')])
        return [data]

    def __call__(self, environ, start_response):
        if environ.get('REMOTE_ADDR') not in ('127.0.0.1','::1'):
            return self.error(start_response,'403 Forbidden','local_only','Local access only')
        host = environ.get('HTTP_HOST','').lower()
        if host not in {f'127.0.0.1:{self.public_port}',f'localhost:{self.public_port}'}:
            return self.error(start_response,'400 Bad Request','host','Use the localhost gateway address')
        method = environ.get('REQUEST_METHOD','GET')
        path = environ.get('PATH_INFO','')
        if method not in ('GET','HEAD','POST','PATCH','PUT','DELETE','OPTIONS'):
            return self.error(start_response,'405 Method Not Allowed','method','Method not supported')
        if environ.get('HTTP_UPGRADE') or environ.get('HTTP_TRANSFER_ENCODING'):
            return self.error(start_response,'400 Bad Request','framing','Upgrade/chunked request bodies are not supported')
        try: length = int(environ.get('CONTENT_LENGTH') or '0')
        except ValueError: length = -1
        if length < 0 or length > MAX_BODY:
            return self.error(start_response,'413 Content Too Large','size','Use the resumable upload endpoint')
        if method in ('GET','HEAD') and length:
            return self.error(start_response,'400 Bad Request','body','GET/HEAD body not supported')
        if path == '/__cluster/health':
            if method != 'GET': return self.error(start_response,'405 Method Not Allowed','method','GET required')
            with self.pool.lock:
                healthy = sum(w['healthy'] for w in self.pool.workers)
                ready = self.pool.workers[0]['healthy']
            data = json.dumps({'ready':ready,'healthy_workers':healthy,'configured_workers':len(self.pool.workers)}).encode()
            start_response('200 OK' if ready else '503 Service Unavailable',
                           [('Content-Type','application/json'),('Content-Length',str(len(data))),('Cache-Control','no-store')])
            return [data]
        # PATH_INFO is latin1-as-bytes per PEP 3333; re-encode without changing slash semantics.
        from urllib.parse import quote_from_bytes
        route = quote_from_bytes(path.encode('latin1'), safe='/~:@!$&\'()*+,;=-._')
        query = environ.get('QUERY_STRING','')
        if query: route += '?' + query
        if not route.startswith('/') or route.startswith('//') or '\r' in route or '\n' in route:
            return self.error(start_response,'400 Bad Request','path','Invalid request target')
        headers = [(k[5:].replace('_','-'),str(v)) for k,v in environ.items() if k.startswith('HTTP_')]
        headers = [(k,v) for k,v in filtered_headers(headers)
                   if k.lower() not in ('x-tactic-cluster','x-forwarded-for','x-forwarded-host','x-forwarded-proto',
                                        'forwarded','content-length','content-type','expect','host')]
        if environ.get('CONTENT_TYPE'): headers.append(('Content-Type',environ['CONTENT_TYPE']))
        headers += [('Host',host),('Content-Length',str(length)),('X-Tactic-Cluster',self.secret),('Connection','close')]
        balanced = is_balanced(method, path)
        lane = nullcontext() if balanced else self.pool.write_lock

        def stream():
            worker = conn = response = None
            started = False
            with lane:
                try:
                    worker = self.pool.select(balanced)
                    if worker is None:
                        for part in self.error(start_response,'503 Service Unavailable','worker_unavailable',
                            'Ведущий процесс недоступен. Запрос не отправлен; дождитесь восстановления.'): yield part
                        return
                    conn = http.client.HTTPConnection('127.0.0.1',worker['port'],timeout=min(5,self.timeout))
                    conn.connect(); conn.sock.settimeout(self.timeout)
                    conn.putrequest(method,route,skip_host=True,skip_accept_encoding=True)
                    for k,v in headers: conn.putheader(k,v)
                    conn.endheaders()
                    remaining = length
                    while remaining:
                        chunk = environ['wsgi.input'].read(min(remaining,BLOCK))
                        if not chunk: raise ConnectionError('Client body ended early')
                        conn.send(chunk); remaining -= len(chunk)
                    response = conn.getresponse()
                    out = filtered_headers(response.getheaders())
                    # HTTPResponse de-chunks. Keep Content-Length if present; Cheroot frames otherwise.
                    start_response(f'{response.status} {response.reason}',out)
                    started = True
                    if method != 'HEAD':
                        while True:
                            chunk = response.read(BLOCK)
                            if not chunk: break
                            yield chunk
                except (OSError, http.client.HTTPException, ValueError):
                    if worker:
                        with self.pool.lock: worker['errors'] += 1
                    if started:
                        # Do not append a JSON error to a partial file or disguise it as success.
                        raise
                    message = ('Связь с процессом прервана. Результат операции неизвестен. '
                               'Проверьте записи/версии перед повтором; запрос автоматически не повторялся.')
                    for part in self.error(start_response,'502 Bad Gateway','upstream_uncertain',message): yield part
                finally:
                    if response: response.close()
                    if conn: conn.close()
                    if worker: self.pool.done(worker)
        return stream()
