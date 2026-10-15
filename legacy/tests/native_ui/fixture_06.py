"""TEST ONLY: actual 0.6 services/Collection commands + isolated SQLite rows.

The check-in persistence and view schema are TEST collaborators, not a running
TACTIC database. No production module imports this file or switches to fixtures.
"""
import hashlib
from pathlib import Path
import mimetypes
import shutil
import tempfile
from fixture_05 import FixtureBackend as Previous
from collection_test_store import Store,Backend as CollectionBackend
from tactic.ui_api.upload_service import UploadService
from tactic.ui_api.upload_store import UploadStore
from tactic.ui_api.file_payload import FilePayload
from tactic.ui_api.contracts import ApiError
from tactic.core.config_model import ConfigModel,ConfigSource,SidebarProjection
from tactic.core.query_model import apply_tree

XML='''<config><fixture_files title="TEST FIXTURE 0.6 · Original Collection handlers"><element name="media" title="TEST · Media objects"><display class="tactic.ui.panel.ViewPanelWdg"><search_type>fixture/media</search_type><view>table</view></display></element><element name="collections" title="TEST · Native collections"><display class="tactic.ui.panel.CollectionLayoutWdg"><search_type>fixture/media</search_type><view>table</view><show_collection_shelf>true</show_collection_shelf></display></element></fixture_files></config>'''

class FileBackend(UploadService,CollectionBackend):
 def __init__(self,outer,store):
  super().__init__(store);self.outer=outer;self.tmp=tempfile.TemporaryDirectory(prefix='tactic-ui06-test-');self.paths={};self.checkins=[]
 def open_target(self,key):
  target=self.outer.open_target(key)
  if self.outer._project()!='fixture' or target.get('search_type')!='fixture/media':raise ApiError(403,'test_scope','TEST media scope')
  return target
 def _upload_store(self):return UploadStore(Path(self.tmp.name)/'staging')
 def _upload_owner(self):return 'fixture-identity-06'
 def _checkin_policy(self,opened,obj,context):
  # TEST schema contains no process/client_trigger tables. Policy is unit-tested separately.
  if getattr(self,'blocked_policy',False):raise ApiError(501,'checkin_custom_policy','TEST configured check-in policy')
 def _stub(self):
  parent=super()._stub();backend=self
  class Stub:
   set_current_snapshot=parent.set_current_snapshot
   def simple_checkin(self,key,context,path,description,mode,create_icon):
    # TEST persistence callback; no actual workflow/check-in engine claim.
    obj=backend._object('fixture/media',key);source=Path(path);n=len(backend.checkins)+1;code='UPLOADED'+str(n);filecode='UPLOADFILE'+str(n)
    dest=Path(backend.tmp.name)/('asset-'+str(n));shutil.copyfile(source,dest);backend.paths[filecode]=dest
    backend.store.row('file',code=filecode,name=source.name,size=source.stat().st_size,type='main')
    snap=backend.store.row('snapshot',code=code,search_type=obj.get_search_type(),search_code=obj.get_code(),context=context,version=130+n,description=description,timestamp='2026-10-01 12:00:%02d'%n,login='fixture',is_current=False,is_latest=True,snapshot='<snapshot><file file_code="'+filecode+'"/></snapshot>')
    backend.checkins.append({'mode':mode,'create_icon':create_icon,'key':key,'context':context,'size':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
    return dict(snap.get_sobject_dict(),__search_key__=snap.get_search_key(),server_path=str(dest))
  return Stub()

class FixtureBackend(Previous):
 def __init__(self,*a,**kw):
  super().__init__(*a,**kw);self.collection_store=Store();self.collection_store.seed();self.file_backend=FileBackend(self,self.collection_store)
  for n in range(125):
   self.collection_store.row('snapshot',code='SNAP'+str(n),search_type=self.collection_store.a.get_search_type(),search_code='A',context='publish' if n<120 else 'review',version=n+1,description='TEST version '+str(n),timestamp='2026-09-01 10:%02d:%02d'%(n//60,n%60),login='fixture',is_current=n==119,is_latest=n==119,snapshot='<snapshot><file file_code="FILE"/></snapshot>')
  f=Path(self.file_backend.tmp.name)/'test-image.svg';f.write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>TEST</text></svg>');self.file_backend.paths['FILE']=f
  self.collection_store.row('file',code='FILE',name='test-image.svg',size=f.stat().st_size,type='main');self.collection_store.db.commit()
 def identity(self,session):return dict(super().identity(session),allow_uploads=True)
 def _tree(self):
  tree,targets=super()._tree()
  if self._project()=='fixture':
   p=SidebarProjection(lambda v,p:ConfigModel(v,[ConfigSource(XML,v,'TEST XML 0.6')]),lambda n:True,'fixture','fixture');tree+=p.build(['fixture_files']);targets.update(p.targets)
  return tree,targets
 def view(self,stype,view,options=None):
  if stype=='fixture/media':
   spec=self.file_backend.view(stype,view,options)
   for f in spec['fields']:f.setdefault('handler','TEST schema');f.setdefault('reason','')
   spec['capabilities'].update(create=False,update=False);return spec
  return super().view(stype,view,options)
 def open_target(self,key):
  if isinstance(key,str) and key.endswith('/~collection-items'):
   t=self.open_target(key[:-len('/~collection-items')])
   if t['kind']!='collections':raise ApiError(403,'target','Not a collection widget')
   t=dict(t,id=key,kind='table',spec=self.view(t['search_type'],t['view']));self.active_target=t;return t
  return super().open_target(key)
 def query(self,stype,spec,query):
  if stype!='fixture/media':return super().query(stype,spec,query)
  with self.collection_store.bind():
   q=self.collection_store.search(stype);apply_tree(q,query.get('where'),spec['fields'])
   if query.get('record_state')=='all':q.set_show_retired(True)
   total=q.get_count();q.add_order_by(query['sort']['field'],query['sort']['direction']);q.set_offset(query['offset']);q.set_limit(query['limit']);rows=[self.file_backend._collection_item(o) for o in q.get_sobjects()]
   return {'items':rows,'total':total,'offset':query['offset'],'limit':query['limit']}
 def record(self,stype,key,spec):
  if stype=='fixture/media':return self.file_backend._collection_item(self.collection_store.object(stype,key))
  return super().record(stype,key,spec)
 def upload_operation(self,method,path,data,body=b''):
  with self.file_backend.bind():return self.file_backend.upload_operation(method,path,data,body)
 def config_operation(self,method,path,data):
  if path in ('/collections','/collection-members','/collection-change'):
   with self.file_backend.bind():return self.file_backend.collection_operation(method,path,data)
  if path in ('/file-versions','/snapshot-current'):
   target=self.open_target(data.get('target'))
   if target.get('search_type')=='fixture/media':
    with self.file_backend.bind():return self.file_backend.version_operation(method,path,data)
   if path=='/file-versions':
    # TEST-only compatibility for old browser regression fixture rows.
    old=self.snapshots(target['search_type'],data['key']);rows=old['items'];return dict(old,total=len(rows),offset=0,limit=40,has_more=False,can_upload=False)
   raise ApiError(501,'test_snapshot','Older synthetic versions have no current operation')
  if path=='/file' and data.get('file') in self.file_backend.paths:
   target=self.open_target(data['target'])
   if target.get('search_type')!='fixture/media':raise ApiError(403,'test_file_scope','Wrong test target')
   parent=self.collection_store.object('fixture/media',data['key']);snap=self.file_backend._snapshot_for(parent,data['snapshot'])
   if data['file'] not in snap.get_all_file_codes():raise ApiError(403,'test_file_scope','File not in snapshot')
   file=self.collection_store.search_code('sthpw/file',data['file']);mime=mimetypes.guess_type(file.get_full_file_name())[0]or'application/octet-stream'
   return FilePayload(str(self.file_backend.paths[data['file']]),file.get_full_file_name(),mime,False)
  return super().config_operation(method,path,data)
