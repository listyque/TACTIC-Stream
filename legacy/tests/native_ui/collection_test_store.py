"""TEST ONLY: source Collection commands + real Select on isolated SQLite tables.

Schema, authentication and object persistence collaborators are test-provided.
This is not a booted TACTIC database or proof of arbitrary custom triggers.
"""
import copy
from contextlib import contextmanager, ExitStack
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'src/client')]
from pyasm.search import Search as RealSearch, Select
from pyasm.search.database_impl import SqliteImpl, DatabaseImpl
from tactic.ui_api.collection_service import CollectionService
from tactic.ui_api.version_service import VersionService
from tactic.ui_api.contracts import ApiError
from tactic.core.config_model import ConfigModel,ConfigSource

COLS={
 'media':{'id':'INTEGER PRIMARY KEY','code':'TEXT UNIQUE','name':'TEXT','description':'TEXT','keywords':'TEXT','_is_collection':'INTEGER','s_status':'TEXT'},
 'media_in_media':{'id':'INTEGER PRIMARY KEY','parent_code':'TEXT','search_code':'TEXT','s_status':'TEXT'},
 'snapshot':{'id':'INTEGER PRIMARY KEY','code':'TEXT UNIQUE','search_type':'TEXT','search_code':'TEXT','context':'TEXT','version':'INTEGER','description':'TEXT','timestamp':'TEXT','login':'TEXT','is_current':'INTEGER','is_latest':'INTEGER','s_status':'TEXT','level_type':'TEXT','level_id':'INTEGER','process':'TEXT','snapshot':'TEXT'},
 'file':{'id':'INTEGER PRIMARY KEY','code':'TEXT UNIQUE','name':'TEXT','size':'INTEGER','type':'TEXT','s_status':'TEXT'},
}
class Row:
 def __init__(self,store,table,data=None):self.store,self.table,self.data=store,table,dict(data or {})
 def get(self,name):return self.get_value(name)
 def get_value(self,name,no_exception=False,auto_convert=True):return self.data.get(name)
 def set_value(self,name,value):self.data[name]=value
 def get_code(self):return self.data.get('code')
 def get_id(self):return self.data.get('id')
 def get_base_search_type(self):return ('fixture/' if self.table.startswith('media') else 'sthpw/')+self.table
 def get_search_type(self):return self.get_base_search_type()+'?project=fixture' if self.table.startswith('media') else self.get_base_search_type()
 def get_search_key(self):return self.get_base_search_type()+'?project=fixture&id='+str(self.get_id())
 def get_project_code(self):return 'fixture'
 def get_sobject_dict(self):return copy.deepcopy(self.data)
 def is_retired(self):return self.data.get('s_status')=='retired'
 def get_full_file_name(self):return self.data.get('name')
 def get_all_file_codes(self):
  import xml.etree.ElementTree as ET
  return [n.get('file_code') for n in ET.fromstring(self.data.get('snapshot') or '<snapshot/>').iter('file')]
 def update_versionless(self,mode):self.store.versionless_calls.append((self.get_code(),mode))
 def commit(self,**kw):
  values={k:v for k,v in self.data.items() if k!='id'}
  if self.get_id():self.store.db.execute('UPDATE "'+self.table+'" SET '+','.join('"'+k+'"=?' for k in values)+' WHERE id=?',[*values.values(),self.get_id()])
  else:
   values.setdefault('s_status','active')
   if self.table in ('media','snapshot','file'):values.setdefault('code',self.table.upper()+str(self.store.serial));self.store.serial+=1
   cur=self.store.db.execute('INSERT INTO "'+self.table+'" ('+','.join('"'+k+'"' for k in values)+') VALUES ('+','.join('?' for k in values)+')',list(values.values()));self.data.update(values,id=cur.lastrowid)
 def delete(self):self.store.db.execute('DELETE FROM "'+self.table+'" WHERE id=?',(self.get_id(),))

class Query(RealSearch):
 def __init__(self,store,stype):
  self.store=store;self.table=stype.split('/')[-1].split('?')[0];self.stype=stype;self.show_retired=False
  if self.table not in COLS:raise AssertionError(stype)
  self.database_impl=SqliteImpl()
  self.database_impl.get_column_types=lambda resource,table:{k:('boolean' if k in ('_is_collection','is_current','is_latest') else 'integer' if v.startswith('INTEGER') else 'varchar') for k,v in COLS[table].items()}
  with patch.object(DatabaseImpl,'get',return_value=self.database_impl):self.select=Select()
  self.select.tables=[self.table];self.select.db_resource=object()
 def get_base_search_type(self):return self.stype
 def get_id_col(self):return 'id'
 def get_full_search_type(self):return self.stype
 def get_search_type_obj(self):return SimpleNamespace(get_table=lambda:self.table)
 def set_show_retired(self,value=True):self.show_retired=value
 def add_order_by(self,name,direction='asc',**kw):self.select.add_order_by(name,direction=direction,table=self.table)
 def add_relationship_filter(self,obj,*a,**kw):
  assert self.table=='snapshot';self.add_filter('search_type',obj.get_search_type());self.add_filter('search_code',obj.get_code())
 def get_statement(self,*a,**kw):return self.select.get_statement(*a,**kw)
 def _sql(self,mode=None):
  clone=copy.deepcopy(self.select)
  if not self.show_retired:clone.add_filter('s_status','retired',op='!=',table=self.table)
  sql=clone.get_statement(mode=mode) if mode else clone.get_statement();self.store.statements.append(sql);return sql
 def get_count(self):return self.store.db.execute(self._sql('count')).fetchone()[0]
 def get_sobjects(self):return [Row(self.store,self.table,dict(r)) for r in self.store.db.execute(self._sql())]
 def get_sobject(self):
  rows=self.get_sobjects();return rows[0] if rows else None

class Store:
 def __init__(self):
  self.db=sqlite3.connect(':memory:',check_same_thread=False);self.db.row_factory=sqlite3.Row;self.serial=1;self.statements=[];self.versionless_calls=[]
  for table,cols in COLS.items():self.db.execute('CREATE TABLE "'+table+'" ('+','.join('"'+k+'" '+v for k,v in cols.items())+')')
 def search(self,stype):return Query(self,stype)
 def create(self,stype):return Row(self,stype.split('/')[-1])
 def row(self,table,**v):o=Row(self,table,v);o.commit();return o
 def object(self,stype,key):
  if not isinstance(key,str) or key.split('?')[0]!=stype:raise ApiError(403,'key_scope','Wrong type')
  args=parse_qs(key.split('?',1)[-1]);p=args.get('project',['fixture'])[0]
  if p!='fixture':raise ApiError(403,'key_scope','Wrong project')
  q=self.search(stype);q.set_show_retired(True)
  if 'id' in args:q.add_filter('id',int(args['id'][0]))
  else:q.add_filter('code',args.get('code',[''])[0])
  o=q.get_sobject()
  if not o:raise ApiError(404,'not_found','No test record')
  return o
 @contextmanager
 def bind(self):
  store=self
  class Facade:
   def __new__(cls,stype,*a,**kw):return store.search(stype)
   get_by_search_key=staticmethod(lambda key:store.object(key.split('?')[0],key))
   get_by_search_keys=staticmethod(lambda keys:[store.object(k.split('?')[0],k) for k in keys])
   get_by_code=staticmethod(lambda stype,code:store.search_code(stype,code))
  with ExitStack() as stack:
   for target,value in [('pyasm.search.Search',Facade),('tactic.core.collection_commands.Search',Facade),('pyasm.biz.snapshot.Search',Facade),
                        ('pyasm.search.SearchType.create',self.create),('pyasm.search.SearchType.get',lambda st:SimpleNamespace(get_table=lambda:st.split('/')[-1]) if st.split('/')[-1] in COLS else None),
                        ('pyasm.search.SearchType.column_exists',lambda st,n:n in COLS.get(st.split('/')[-1],{}))]:stack.enter_context(patch(target,value))
   yield
 def search_code(self,stype,code):q=self.search(stype);q.add_filter('code',code);return q.get_sobject()
 def seed(self):
  self.folder=self.row('media',code='ROOT',name='Review collection',_is_collection=True)
  self.child=self.row('media',code='CHILD',name='Nested collection',_is_collection=True)
  self.a=self.row('media',code='A',name='First asset',_is_collection=False)
  self.b=self.row('media',code='B',name='Second asset',_is_collection=False)
  self.link(self.folder,self.a);self.link(self.folder,self.child)
  self.db.commit()
 def link(self,parent,child):return self.row('media_in_media',parent_code=parent.get_code(),search_code=child.get_code())
 def close(self):self.db.close()

class Backend(CollectionService,VersionService):
 allow_writes=True;allow_uploads=True;site=''
 def __init__(self,store):self.store=store;self.create_calls=[];self.current_calls=[]
 def _project(self):return 'fixture'
 def require_type(self,stype):
  if stype not in ('fixture/media','fixture/media_in_media','sthpw/snapshot','sthpw/file'):raise ApiError(400,'type','Unknown')
 def open_target(self,key):
  if key not in ('collections','media'):raise ApiError(403,'target','Wrong target')
  return {'kind':'collections' if key=='collections' else 'table','id':key,'search_type':'fixture/media','options':{},'spec':self.view('fixture/media','table')}
 def _object(self,stype,key):return self.store.object(stype,key)
 def _write(self,fn):
  if not self.allow_writes:raise ApiError(403,'read_only','Disabled')
  with self.store.db:return fn()
 def view(self,stype,view,options=None):
  # Actual default field order, with TEST schema/renderers; not a production resolver assertion.
  xml=(ROOT/'src/config2/search_type/widget/prod/DEFAULT-conf.xml').read_text()
  model=ConfigModel(view,[ConfigSource(xml,view)])
  names=model.names() if view=='edit_collection' else ['code','name','description','_is_collection']
  fields=[{'name':n,'label':model.describe(n)['title'],'kind':'text','storage':n in COLS['media'],'supported':n in COLS['media'],'read_only':n not in ('name','description','keywords'),'options':[],'nullable':True} for n in names]
  return {'type':stype,'view':view,'fields':fields,'capabilities':{'create':self.allow_writes,'update':self.allow_writes,'retire':False},'diagnostics':[],'collection_supported':True}
 def _snapshot_for(self,parent,key):
  s=self._object('sthpw/snapshot',key)
  if s.get_value('search_type')!=parent.get_search_type() or s.get_value('search_code')!=parent.get_code():raise ApiError(403,'snapshot_scope','Foreign version')
  return s
 def _stub(self):
  backend=self
  class Stub:
   def set_current_snapshot(self,code):
    # Delegate real Snapshot.set_current; filesystem trigger effects recorded only.
    from pyasm.biz import Snapshot
    backend.current_calls.append(code);Snapshot.set_current(backend.store.search_code('sthpw/snapshot',code));return {'code':code}
  return Stub()
 @contextmanager
 def bind(self):
  backend=self
  class Edit:
   def __init__(self,**kw):self.kw=kw;backend.create_calls.append(kw)
   def execute(self):
    o=self.kw['sobject']
    for k,v in dict(self.kw['data'],**self.kw['extra_data']).items():o.set_value(k,v)
    o.commit()
   def get_sobject(self):return self.kw['sobject']
  with self.store.bind(),patch('tactic.core.native_edit.NativeEditCmd',Edit):yield
