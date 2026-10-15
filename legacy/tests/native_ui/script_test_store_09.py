"""TEST ONLY: real Search/Select SQL with isolated custom_script persistence.

No full TACTIC DB/auth/trigger proof. Production ScriptService is shared by
unit and HTTP tests; only record persistence + metadata are collaborators.
"""
from contextlib import contextmanager, ExitStack
import copy
from datetime import datetime
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'src/client')]
from pyasm.search import Search as RealSearch, Select
from pyasm.search.database_impl import DatabaseImpl, SqliteImpl
from tactic.ui_api.script_service import ScriptService, STYPE, script_permission
from tactic.ui_api.config_backend import ConfigBackend
from tactic.ui_api.contracts import ApiError
COLS={'id':'integer','code':'varchar','title':'varchar','folder':'varchar','language':'varchar','description':'varchar','script':'varchar','timestamp':'timestamp','s_status':'varchar'}
class Row:
 def __init__(self,store,values):self.store=store;self.values=dict(values)
 def get_value(self,name,no_exception=False,auto_convert=True):return self.values.get(name)
 def get_id(self):return self.values.get('id')
 def get_code(self):return self.values.get('code')
 def get_search_key(self):return STYPE+'?project='+self.store.project+'&code='+str(self.get_code())
 def get_sobject_dict(self):return copy.deepcopy(self.values)
class Query(RealSearch):
 def __init__(self,store,stype):
  assert stype==STYPE,stype
  self.store=store;self.order_bys=[];self.search_type_obj=SimpleNamespace(get_table=lambda:'custom_script');self.database_impl=SqliteImpl();self.database_impl.get_column_types=lambda *a:COLS;self.database_impl.is_column_sortable=lambda resource,table,column:column in COLS
  with patch.object(DatabaseImpl,'get',return_value=self.database_impl):self.select=Select()
  self.select.tables=['custom_script'];self.select.db_resource=object();self.db_resource=self.select.db_resource;self.add_filter('s_status','retired',op='!=')
 def get_id_col(self):return 'id'
 def get_count(self):
  sql=self.select.get_statement(mode='count');self.store.statements.append(sql);return self.store.db.execute(sql).fetchone()[0]
 def get_sobjects(self):
  sql=self.select.get_statement();self.store.statements.append(sql);return [Row(self.store,dict(row)) for row in self.store.db.execute(sql)]
 def get_sobject(self):return next(iter(self.get_sobjects()),None)
class Store:
 def __init__(self):
  self.db=sqlite3.connect(':memory:',check_same_thread=False);self.db.row_factory=sqlite3.Row;self.project='admin';self.allowed=True;self.statements=[];self.calls=[]
  self.db.execute('CREATE TABLE custom_script (id INTEGER PRIMARY KEY,code TEXT,title TEXT,folder TEXT,language TEXT,description TEXT,script TEXT,timestamp TEXT,s_status TEXT)')
 def row(self,**values):
  defaults={'code':'SCRIPT'+str(self.db.execute('SELECT coalesce(max(id),0)+1 FROM custom_script').fetchone()[0]),'folder':'default','title':'test','language':'python','script':'pass\n','description':'','timestamp':'2026-10-01 10:00:00','s_status':'active'};defaults.update(values)
  cur=self.db.execute('INSERT INTO custom_script('+','.join('"'+k+'"' for k in defaults)+') VALUES ('+','.join('?' for _ in defaults)+')',list(defaults.values()));return Row(self,dict(defaults,id=cur.lastrowid))
 def by_key(self,key):
  from urllib.parse import parse_qs
  if not isinstance(key,str) or key.split('?')[0]!=STYPE:raise ApiError(403,'key_scope','Foreign type')
  q=parse_qs(key.split('?',1)[-1])
  if q.get('project',[self.project])[0]!=self.project:raise ApiError(403,'key_scope','Foreign project')
  row=self.db.execute('SELECT * FROM custom_script WHERE code=?',(q.get('code',[''])[0],)).fetchone();return Row(self,dict(row)) if row else None
 def update(self,key,values):
  self.calls.append(('update',key,copy.deepcopy(values)));obj=self.by_key(key)
  self.db.execute('UPDATE custom_script SET '+','.join('"'+k+'"=?' for k in values)+' WHERE id=?',list(values.values())+[obj.get_id()]);return {'__search_key__':key}
 def insert(self,stype,values):
  self.calls.append(('insert',stype,copy.deepcopy(values)));obj=self.row(**values);return {'__search_key__':obj.get_search_key()}
 @contextmanager
 def bind(self):
  with ExitStack() as stack:
   stack.enter_context(patch('pyasm.search.Search',side_effect=lambda st:Query(self,st)))
   stack.enter_context(patch('pyasm.search.SearchKey.get_by_search_key',side_effect=self.by_key))
   stack.enter_context(patch('pyasm.common.Environment.get_security',return_value=SimpleNamespace(check_access=lambda *a,**kw:self.allowed,is_admin=lambda:True)))
   yield
 def seed(self,count=65):
  for i in range(count):self.row(title='script_%03d'%i,folder='workflow/review' if i%2 else 'tools',script='# TEST FIXTURE\nresult = %d\n'%i)
  self.db.commit()
class Backend(ScriptService):
 site='';allow_writes=True
 def __init__(self,store,target=None):self.store=store;self.target=target
 def require_type(self,stype):assert stype==STYPE
 def _project(self):return self.store.project
 def _stub(self):return self.store
 def _object(self,stype,key):return ConfigBackend._object(self,stype,key)
 def _write(self,cb):
  if not self.allow_writes:raise ApiError(403,'read_only','Writes disabled')
  with self.store.db:return cb()
 def open_target(self,key):
  if self.target is not None and key==self.target['id']:return self.target
  if key=='editor':return {'id':key,'kind':'script-editor','options':{}}
  raise ApiError(403,'script_target','Wrong target')
