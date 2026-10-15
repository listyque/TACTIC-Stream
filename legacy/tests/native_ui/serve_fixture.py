"""TEST-ONLY CherryPy process: original XML menus + synthetic rows, never real DB.

Use a supported TACTIC Python environment with CherryPy dependencies installed.
This process only binds localhost and must not be used as a TACTIC server.
"""
import sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'src/client'),str(ROOT/'3rd_party/python3/site-packages')]
import cherrypy
from fixture_10 import FixtureBackend
from tactic.ui_api import mount
mount.ConfigBackend=FixtureBackend  # TEST PROCESS ONLY: production module is not edited.
class Service:
 @cherrypy.expose
 def index(self,**kw):return 'LEGACY SERVICE SENTINEL'
 @cherrypy.expose
 def default(self,*a,**kw):return 'LEGACY SERVICE SENTINEL'
class Project:
 Api=Service();REST=Service();UploadServer=Service()
 @cherrypy.expose
 def index(self,**kw):return 'LEGACY PAGE MUST BE REPLACED'
 @cherrypy.expose
 def default(self,*args,**kw):return 'LEGACY ENDPOINT SENTINEL'
class Root:
 @cherrypy.expose
 def index(self):return 'ROOT MUST BE REPLACED'
 @cherrypy.expose
 def default(self,*args,**kw):return 'LEGACY ENDPOINT SENTINEL'
port=int(os.environ.get('TACTIC_FIXTURE_PORT','9147'))
cherrypy.config.update({'server.socket_host':'127.0.0.1','server.socket_port':port,'engine.autoreload.on':False,'log.screen':False,'log.error_file':os.environ.get('TACTIC_FIXTURE_ERROR_LOG',''),'tools.trailing_slash.on':False})
cherrypy.tree.mount(Root(),'/')
for project in ('admin','fixture','default'):cherrypy.tree.mount(Project(),'/tactic/'+project)
mount.install()
cherrypy.engine.start()
cherrypy.engine.block()
