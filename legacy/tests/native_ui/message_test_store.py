"""TEST ONLY: real Select predicates and extracted API methods on SQLite tables.

The schema collaborator and persistence are deliberately supplied by this test;
this is NOT a full TACTIC database, authentication, transaction or trigger test.
Production never imports this module. Used by unit + HTTP fixtures so message
endpoints execute the production MessageService rather than duplicate logic.
"""
import ast
import copy
import json
import sqlite3
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'src/client')]
from pyasm.search import Search as RealSearch, Select, SObject
from pyasm.search.database_impl import SqliteImpl,DatabaseImpl
from pyasm.common import Environment
from pyasm.biz import Project

COLS={
 'message': {'id':'INTEGER PRIMARY KEY','code':'TEXT UNIQUE','category':'TEXT','message':'TEXT','status':'TEXT','login':'TEXT','project_code':'TEXT','timestamp':'TEXT'},
 'message_log': {'id':'INTEGER PRIMARY KEY','code':'TEXT','message_code':'TEXT','category':'TEXT','message':'TEXT','status':'TEXT','login':'TEXT','project_code':'TEXT','timestamp':'TEXT'},
 'subscription': {'id':'INTEGER PRIMARY KEY','code':'TEXT','category':'TEXT','message_code':'TEXT','login':'TEXT','project_code':'TEXT','status':'TEXT','last_cleared':'TEXT','timestamp':'TEXT'},
 'login': {'id':'INTEGER PRIMARY KEY','code':'TEXT','login':'TEXT UNIQUE','display_name':'TEXT','s_status':'TEXT'},
 'notification_log': {'id':'INTEGER PRIMARY KEY','project_code':'TEXT','login':'TEXT','command_cls':'TEXT','subject':'TEXT','message':'TEXT','timestamp':'TEXT'},
 'notification_login': {'id':'INTEGER PRIMARY KEY','notification_log_id':'INTEGER','login':'TEXT','type':'TEXT','project_code':'TEXT','timestamp':'TEXT'},
}
class Row:
 def __init__(self,store,table,values=None):self.store,self.table,self.values=store,table,dict(values or {})
 def get_value(self,name,no_exception=False,auto_convert=True):return self.values.get(name)
 def set_value(self,name,value):self.values[name]=self.store.now() if value=='NOW' else value
 def get_id(self):return self.values.get('id')
 def get_code(self):return self.values.get('code')
 def get_base_search_type(self):return 'sthpw/'+self.table
 def get_search_type(self):return self.get_base_search_type()
 def get_search_key(self):return self.get_base_search_type()+'?id='+str(self.get_id())
 def get_sobject_dict(self):return copy.deepcopy(self.values)
 def set_user(self):self.set_value('login',self.store.login)
 def commit(self,**kw):
  unknown=set(self.values)-set(COLS[self.table])
  if unknown:raise AssertionError('Unknown fixture columns: '+str(unknown))
  values={k:v for k,v in self.values.items() if k!='id'}
  if self.get_id():
   self.store.db.execute('UPDATE "'+self.table+'" SET '+','.join('"'+k+'"=?' for k in values)+' WHERE id=?',[*values.values(),self.get_id()])
  else:
   values.setdefault('timestamp',self.store.now()) if 'timestamp' in COLS[self.table] else None
   if self.table=='subscription':values.setdefault('last_cleared',self.store.now())
   cur=self.store.db.execute('INSERT INTO "'+self.table+'" ('+','.join('"'+k+'"' for k in values)+') VALUES ('+','.join('?' for k in values)+')',list(values.values()))
   self.values.update(values,id=cur.lastrowid)
 def delete(self):self.store.db.execute('DELETE FROM "'+self.table+'" WHERE id=?',(self.get_id(),))

class Query(RealSearch):
 def __init__(self,store,stype):
  self.store=store;self.table=stype.split('/')[-1];self.stype=stype
  if self.table not in COLS:raise AssertionError('Unexpected test SearchType: '+stype)
  self.database_impl=SqliteImpl()
  self.database_impl.get_column_types=lambda resource,table:{k:('integer' if v.startswith('INTEGER') else 'timestamp' if k in ('timestamp','last_cleared','start_date','end_date','actual_start','actual_end') else 'varchar') for k,v in COLS[table].items()}
  with patch.object(DatabaseImpl,'get',return_value=self.database_impl):self.select=Select()
  self.select.tables=[self.table];self.select.db_resource=object()
  if self.table=='login':self.add_filter('s_status','retired',op='!=')
 def get_base_search_type(self):return self.stype
 def get_id_col(self):return 'id'  # Fixture schema metadata; original add_id_filter is retained.
 def get_full_search_type(self):return self.stype
 def get_search_type_obj(self):return SimpleNamespace(get_table=lambda:self.table)
 def add_user_filter(self):self.add_filter('login',self.store.login)
 def add_order_by(self,name,direction='asc',**kw):
  if '.' in name:
   table,col=name.split('.',1)
   if (self.table,table)!=('subscription','message'):raise AssertionError('Unexpected test join')
   if not self.select.joins:self.select.add_join('subscription','message','message_code','code')
  else:table,col=self.table,name
  self.select.add_order_by(col,direction=direction,table=table)
 def get_count(self):return self.store.db.execute(self.select.get_statement(mode='count')).fetchone()[0]
 def get_sobjects(self):
  sql=self.select.get_statement();self.store.statements.append(sql)
  return [Row(self.store,self.table,dict(r)) for r in self.store.db.execute(sql)]
 def get_sobject(self):
  rows=self.get_sobjects();return rows[0] if rows else None

class Store:
 def __init__(self,login='alice',project='test'):
  self.db=sqlite3.connect(':memory:',check_same_thread=False);self.db.row_factory=sqlite3.Row
  self.login,self.project=login,project;self.statements=[];self.clock=datetime(2026,9,1,10)
  for name,cols in COLS.items():self.db.execute('CREATE TABLE "'+name+'" ('+','.join('"'+k+'" '+v for k,v in cols.items())+')')
 def now(self):
  self.clock+=timedelta(microseconds=1);return self.clock.isoformat(' ',timespec='microseconds')
 def row(self,table,**values):
  obj=Row(self,table,values);obj.commit();return obj
 def search(self,stype):return Query(self,stype)
 def create(self,stype):return Row(self,stype.split('/')[-1])
 def get(self,table,**filters):
  q=self.search('sthpw/'+table)
  for k,v in filters.items():q.add_filter(k,v)
  return q.get_sobject()
 @contextmanager
 def bind(self):
  with ExitStack() as stack:
   for target,value in [('pyasm.search.Search',self.search),('pyasm.search.SearchType.create',self.create),
      ('pyasm.common.Environment.get_user_name',lambda:self.login),('pyasm.biz.Project.get_project_code',lambda:self.project),
      ('tactic.core.message_commands.Search',self.search),('tactic.core.notification_filters.Search',self.search)]:
    stack.enter_context(patch(target,value))
   stack.enter_context(patch('pyasm.security.Site.get_site',return_value=''))
   stack.enter_context(patch('pyasm.security.Site.get_db_resource',return_value='sthpw'))
   yield
 def seed(self):
  for login in [self.login,'bob','carol','outsider']:
   self.row('login',login=login,code=login,display_name='TEST '+login,s_status='active')
  self.row('login',login='retired',code='retired',display_name='Retired test',s_status='retired')
  self.chat('pair',[self.login,'bob'])
  self.chat('group',[self.login,'bob','carol'])
  self.chat('legacy',[self.login,'carol'],project=None)
  self.chat('foreign',[self.login,'bob'],project='other')
  self.chat('private',['bob','carol'])
  for n in range(65):self.log('pair','Repeated TEST message' if n in (63,64) else 'TEST history %03d'%n,login='bob')
  self.event('event',{'search_type':'fixture/item','mode':'change','sobject':{'code':'FIXTURE0'},'update_data':{'name':'<script>not executed</script>'}})
  self.event('progress',{'message':'TEST progress','progress':45},category='progress')
  self.row('subscription',message_code='orphan',category='sobject',login=self.login,project_code=self.project,last_cleared=None)
  self.db.commit()
 def chat(self,key,users,project='CURRENT'):
  project=self.project if project=='CURRENT' else project
  message=self.row('message',code=key,category='chat',message='Welcome!!!',login=self.login,project_code=project)
  for user in users:self.row('subscription',message_code=key,login=user,category='chat',project_code=project,last_cleared=None)
  return message
 def log(self,key,message,login=None,category='chat',project=None):
  m=self.get('message',code=key);m.set_value('message',message);m.set_value('login',login or self.login);m.set_value('timestamp',self.now());m.commit()
  return self.row('message_log',message_code=key,message=message,login=login or self.login,category=category,project_code=project or self.project,timestamp=m.get_value('timestamp'))
 def event(self,key,value,category='sobject'):
  self.row('message',code=key,category=category,message=json.dumps(value),login='bob',project_code=self.project)
  self.row('subscription',message_code=key,category=category,login=self.login,project_code=self.project,last_cleared=None)
 def close(self):self.db.close()

# Execute actual API method bodies, with only auth decorator removed. This
# permits testing the SQLite branch without importing the entire API server.
def api_method(name):
 path=ROOT/'src/pyasm/prod/service/api_xmlrpc.py';tree=ast.parse(path.read_text())
 cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and any(isinstance(x,ast.FunctionDef) and x.name==name for x in n.body))
 fun=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name));fun.decorator_list=[]
 mod=ast.Module(body=[fun],type_ignores=[]);ast.fix_missing_locations(mod)
 return compile(mod,str(path),'exec')
class Stub:
 def __init__(self,store):self.store=store
 def _get_sobject_dict(self,obj):return obj.get_sobject_dict()
 def _call(self,name,*args,**kwargs):
  class NoSudo:
   def exit(self):pass
  store=self.store
  class Sql:
   def __init__(self,*a):pass
   def connect(self):pass
   def get_database_impl(self):return SqliteImpl()
  namespace={'Search':store.search,'SearchType':SimpleNamespace(create=store.create),'Environment':Environment,'Project':Project,
             'Sql':Sql,'jsondumps':json.dumps,'Sudo':NoSudo,'ApiException':RuntimeError}
  exec(api_method(name),namespace)
  return namespace[name](self,'TEST-TICKET',*args,**kwargs)
 def log_message(self,*args,**kwargs):return self._call('log_message',*args,**kwargs)
 def subscribe(self,*args,**kwargs):return self._call('subscribe',*args,**kwargs)
