"""TEST ONLY: original startup, authentication, models and complete SQLite seeds.

--data-dir MUST contain .native-real-test written by the companion runner. No
fixture backend is used. --isolate-license explicitly skips only signature
verification in this test subprocess; the production application is unchanged.
"""
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/local'))
from launch import configure_paths
p=argparse.ArgumentParser();p.add_argument('--data-dir',required=True,type=Path);p.add_argument('--port',type=int,required=True);p.add_argument('--isolate-license',action='store_true');p.add_argument('--prepare',action='store_true');a=p.parse_args()
data=a.data_dir.resolve()
if not (data/'.native-real-test').is_file():raise SystemExit('Refusing non-test data directory')
configure_paths(data,data/'config/tactic-conf.xml')
from pyasm.security.security import License
if a.isolate_license:
 from unittest.mock import patch
 # Actual stock licence metadata. Crypto validation is expressly NOT tested.
 lic=License(str(data/'config/tactic-license.xml'),verify=False)
 licence_patch=patch.object(License,'get',return_value=lic);licence_patch.start()
 print('TEST ONLY: signature verification isolated; original authentication and DB operations.',flush=True)
from tactic.startup import FirstRunInit
FirstRunInit().execute()
if a.prepare:
 from pyasm.security import Batch,Login
 from pyasm.common import Environment
 from pyasm.search import Search,SearchType
 from tactic.ui_api.extended_backend import ExtendedBackend
 from types import SimpleNamespace
 Batch(project_code='admin');sec=Environment.get_security();sess=SimpleNamespace(login='admin',ticket=sec.get_ticket_key(),site='',user={})
 import cherrypy
 cherrypy.request.wsgi_environ={'REQUEST_METHOD':'POST','PATH_INFO':'/api/ui/v2','QUERY_STRING':''};cherrypy.request.params={};cherrypy.request.base='http://localhost';cherrypy.request.path_info='/api/ui/v2'
 b=ExtendedBackend({'allow_writes':True})
 with b.context(sess,'admin'):
  def prepare():
   # Original Login helper persists password with original Drupal hash.
   Login.get_by_login('admin').set_password('Native-Test-Only-123')
   # Register an isolated test project backed by a COPY of the original
   # unittest seed; data relationships and command code remain original.
   obj=SearchType.create('sthpw/project');obj.set_value('code','native11test');obj.set_value('type','unittest');obj.set_value('database','native11test');obj.set_value('title','Original model integration TEST');obj.commit()
  b._write(prepare)
 from tactic.core.native_settings import save_settings
 save_settings(data/'config/native-ui.json',{'site':'','allow_writes':True,'allow_uploads':False})
 print('Prepared original model test installation.',flush=True)
else:
 from pyasm.web.cherrypy30_startup import CherryPyStartup
 server=CherryPyStartup(a.port)
 for key,value in {'server.socket_host':'127.0.0.1','server.socket_port':a.port,'server.thread_pool':8,'request.show_tracebacks':False,'engine.autoreload.on':False,'log.screen':True}.items():server.set_config('global',key,value)
 server.execute()
