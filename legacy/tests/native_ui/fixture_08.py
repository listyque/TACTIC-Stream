"""TEST ONLY: real read-only stock seed metadata in the native SystemInfo path.

The seed is NOT a running/authenticated TACTIC installation. Only request/metadata
collaborators are substituted, production system service + checker execute.
"""
from contextlib import closing
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from unittest.mock import patch
from fixture_07 import FixtureBackend as Previous
from tactic.ui_api.admin_service import AdminService
ROOT=Path(__file__).resolve().parents[2]

class FixtureBackend(Previous):
 def config_operation(self,method,path,data):
  if path!='/system':return super().config_operation(method,path,data)
  def ro(name):return sqlite3.connect((ROOT/'src/install/start/db'/(name+'.db')).resolve().as_uri()+'?mode=ro',uri=True)
  class Meta:
   def __init__(self,name):self.name=name
   def get_columns(self,table,use_cache=False):
    with closing(ro(self.name)) as c:return [r[1] for r in c.execute('PRAGMA table_info("'+table.replace('"','""')+'")')]
   def get_database_type(self):return 'Sqlite'
  class Query:
   def __init__(self,stype):self.stype=stype;self.filters=[]
   def add_filters(self,field,values):self.filters=list(values)
   def get_count(self):
    with closing(ro('sthpw')) as c:return c.execute('SELECT count(*) FROM project').fetchone()[0]
   def get_sobjects(self):
    with closing(ro('sthpw')) as c:rows=c.execute('SELECT search_type,table_name FROM search_object').fetchall()
    return [SimpleNamespace(get_value=lambda n,k=k,v=v:k if n=='search_type' else v) for k,v in rows if k in self.filters]
  def project(code):return SimpleNamespace(get_code=lambda:code,get_project_db_resource=lambda:'sthpw' if code in ('admin','sthpw') else 'unittest')
  service=SimpleNamespace(open_target=self.open_target,allow_writes=False,allow_uploads=False)
  with patch('pyasm.search.Search',Query),patch('pyasm.search.DbContainer.get',side_effect=lambda resource:Meta(resource)),patch('pyasm.biz.Project.get',return_value=project(self._project())),patch('pyasm.biz.Project.get_by_code',side_effect=project),patch('pyasm.biz.Project.get_project_code',return_value=self._project()),patch('pyasm.common.Environment.get_security',return_value=SimpleNamespace(is_admin=lambda:True)),patch('pyasm.common.Environment.get_install_dir',return_value=str(ROOT)),patch('pyasm.common.Config.get_value',return_value='Sqlite'):
   result=AdminService.admin_operation(service,method,path,data)
  result['notes'].insert(0,'TEST FIXTURE: метаданные штатного seed, не работающий сервер и не пользовательская БД.')
  return result
