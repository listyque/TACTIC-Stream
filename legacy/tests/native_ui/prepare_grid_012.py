"""TEST ONLY: install original widget_config overrides in the disposable seed."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/local'))
from launch import configure_paths
p=argparse.ArgumentParser();p.add_argument('--data-dir',type=Path,required=True);p.add_argument('--isolate-license',action='store_true');a=p.parse_args()
data=a.data_dir.resolve()
if not (data/'.native-real-test').is_file():raise SystemExit('Refusing non-test data')
configure_paths(data,data/'config/tactic-conf.xml')
from pyasm.security.security import License
if a.isolate_license:
 from unittest.mock import patch
 lic=License(str(data/'config/tactic-license.xml'),verify=False)
 patch.object(License,'get',return_value=lic).start()
from tactic.startup import FirstRunInit
FirstRunInit().execute()
from pyasm.security import Batch
from pyasm.common import Environment
from pyasm.search import SearchType
from tactic.ui_api.extended_backend import ExtendedBackend
from types import SimpleNamespace
import cherrypy
Batch(project_code='admin');sec=Environment.get_security();sess=SimpleNamespace(login='admin',ticket=sec.get_ticket_key(),site='',user={})
cherrypy.request.wsgi_environ={'REQUEST_METHOD':'POST','PATH_INFO':'/api/ui/v2','QUERY_STRING':''};cherrypy.request.params={};cherrypy.request.base='http://localhost';cherrypy.request.path_info='/api/ui/v2'
b=ExtendedBackend({'allow_writes':True})
with b.context(sess,'admin'):
 def prepare():
  config=SearchType.create('config/widget_config')
  for n,v in {'search_type':'sthpw/login','view':'edit_item','priority':100,'config':'''<config><edit_item>
  <element name="first_name"><display class="TextAreaWdg"/><edit><rows>5</rows></edit><action class="NonEmptyAction"/></element>
  <element name="last_name"><display class="TextWdg"/><action class="DatabaseAction"/></element>
  </edit_item></config>'''}.items():config.set_value(n,v)
  config.commit()
  trigger=SearchType.create('sthpw/trigger')
  for n,v in {'event':'update_multi|sthpw/login','class_name':'grid_audit_012.GridAuditTrigger','mode':'same process,same transaction'}.items():trigger.set_value(n,v)
  trigger.commit()
  for code,first,last in [('grid_anna','Анна','Петрова'),('grid_alex','Алексей','Иванов')]:
   obj=SearchType.create('sthpw/login')
   for n,v in {'code':code,'login':code,'first_name':first,'last_name':last,'display_name':first+' '+last}.items():obj.set_value(n,v)
   obj.commit()
 b._write(prepare)
 # Create a real registered image through the original API, not a fake URL.
 import struct,zlib
 def chunk(name,raw):return struct.pack('>I',len(raw))+name+raw+struct.pack('>I',zlib.crc32(name+raw)&0xffffffff)
 pixels=b''.join(b'\x00'+bytes([104,88,216])*48 for _ in range(48))
 png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',48,48,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')
 file=data/'temp'/'grid-preview.png';file.parent.mkdir(exist_ok=True);file.write_bytes(png)
 b._write(lambda:b._stub().simple_checkin('sthpw/login?code=grid_anna','icon',str(file),file_type='icon',mode='copy',create_icon=False))
print('Installed real edit_item override + test users')
