"""Native UI at normal /tactic/PROJECT paths, within the original CherryPy server.
Set TACTIC_UI=legacy to disable the native UI; XML-RPC and REST are untouched.
"""
from pathlib import Path
from urllib.parse import parse_qs
import json
import os
from .api import Api, Request, MAX_JSON, MAX_UPLOAD
from .extended_backend import ExtendedBackend as ConfigBackend
from .file_payload import FilePayload
from .csv_service import BytesPayload
from .routing import native_page
from .upload_store import CHUNK

INSTALLED = False

def install():
    global INSTALLED
    if INSTALLED or os.environ.get('TACTIC_UI', 'vue').lower() == 'legacy': return
    import cherrypy
    root = Path(__file__).resolve().parent
    from tactic.core.native_settings import load_settings
    from pyasm.common import Environment
    settings = load_settings(root/'config.json',Environment.get_data_dir())
    from . import action_log
    action_log.configure(Environment.get_data_dir())
    from .cluster_runtime import enabled
    if enabled():
        from .shared_sessions import SharedSessionStore
        api = Api(ConfigBackend(settings), SharedSessionStore(os.environ['TACTIC_CLUSTER_SESSIONS']))
    else:
        api = Api(ConfigBackend(settings))

    class ApiRoot:
        @cherrypy.expose
        def index(self, **kwargs): return self.default(**kwargs)
        @cherrypy.expose
        def default(self, *parts, **kwargs):
            request = cherrypy.request
            path = '/' + '/'.join(parts)
            cap = MAX_UPLOAD if path == '/upload' else CHUNK if path == '/upload-chunk' else MAX_JSON
            try: length = int(request.headers.get('Content-Length', '0'))
            except ValueError: length = -1
            if not 0 <= length <= cap:
                cherrypy.response.status = 413
                cherrypy.response.headers['Content-Type']='application/json'
                return b'{"error":{"message":"Request too large"}}'
            if request.method in ('POST','PATCH') and not length:
                cherrypy.response.status = 411
                return b'{"error":{"message":"Content-Length required"}}'
            # TACTIC's bundled Entity.read(size, fp_out) assumes its multipart
            # processor wrapped fp. With processing disabled, fp is Cheroot's
            # one-argument KnownLengthRFile: read bounded raw bytes directly.
            body = request.body.fp.read(length) if length else b''
            query = {k:v[-1] for k,v in parse_qs(request.query_string,keep_blank_values=True).items()}
            res = api.handle(Request(request.method,path,query,dict(request.headers),body,request.remote.ip,request.scheme=='https'))
            cherrypy.response.status=res.status
            cherrypy.response.headers.update(res.headers)
            if isinstance(res.data, BytesPayload):
                from urllib.parse import quote
                cherrypy.response.headers['Content-Type'] = res.data.content_type
                cherrypy.response.headers['Content-Disposition'] = "attachment; filename*=UTF-8''" + quote(res.data.filename, safe='')
                cherrypy.response.headers['Content-Security-Policy'] = "default-src 'none'; sandbox"
                return res.data.data
            if isinstance(res.data, FilePayload):
                f=res.data
                cherrypy.response.headers['Content-Security-Policy']="default-src 'none'; sandbox"
                return cherrypy.lib.static.serve_file(f.path, content_type=f.content_type,
                    disposition='inline' if f.inline else 'attachment', name=f.filename)
            cherrypy.response.headers['Content-Type']='application/json; charset=utf-8'
            return json.dumps(res.data,ensure_ascii=False,allow_nan=False).encode('utf-8')

    web = root/'web'
    csp="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    def serve_shell():
        r=cherrypy.request
        if native_page(r.script_name+r.path_info,r.method,r.headers.get('Accept',''),settings.get('site','')):
            cherrypy.response.headers.update({'Content-Type':'text/html; charset=utf-8', 'Cache-Control':'no-cache', 'Content-Security-Policy':csp, 'X-Content-Type-Options':'nosniff'})
            r.handler = lambda: (web/'index.html').read_bytes() if r.method=='GET' else b''
    cherrypy.tools.tactic_native_ui = cherrypy.Tool('before_handler', serve_shell, priority=90)
    cherrypy.config.update({'tools.tactic_native_ui.on':True})
    api_app = cherrypy.tree.mount(ApiRoot(),'/api/ui/v2',config={'/':{'request.process_request_body':False,'tools.encode.on':False,'tools.sessions.on':False,'request.show_tracebacks':False}})
    api_app.log.access_log.addFilter(action_log.NativeAccessFilter())
    cherrypy.tree.mount(None,'/tactic-ui',config={'/':{
        'tools.staticdir.on':True,'tools.staticdir.dir':str(web),'tools.staticdir.index':'index.html',
        'request.show_tracebacks':False,'tools.response_headers.on':True,
        'tools.response_headers.headers':[('Cache-Control','no-cache'),('Content-Security-Policy',csp),('X-Content-Type-Options','nosniff')]}})
    INSTALLED = True
    print('TACTIC native configuration UI: /tactic/<project>/; admin-only; writes=%s' % settings.get('allow_writes'))
