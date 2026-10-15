"""TEST ONLY. Production view/query/format/CSV over isolated original Select.

No real TACTIC authentication, full DB schema, transactions or workflow claim.
"""
import copy,json,re
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'src/client')]
from message_test_store import Store as OriginalStore, COLS, RealSearch
from tactic.core.config_model import ConfigModel,ConfigSource
from tactic.ui_api.extended_backend import ExtendedBackend
from tactic.ui_api.contracts import ApiError

ST='fixture/columns07'
COLS['columns07']={'id':'INTEGER PRIMARY KEY','code':'TEXT','name':'TEXT','department':'TEXT','amount':'REAL','ratio':'REAL','approved':'INTEGER','url':'TEXT','timestamp':'TEXT','project_code':'TEXT','s_status':'TEXT','password':'TEXT'}
COLUMNS={n:{'data_type':'numeric' if n in ('amount','ratio') else 'integer' if n in ('id','approved') else 'timestamp' if n=='timestamp' else 'varchar'} for n in COLS['columns07']}
XML='''<config><table><element name="code" title="Код" width="100"/><element name="name" title="Название" width="230"/><element name="department" title="Отдел"/><element name="amount" title="Сумма" width="130"/><element name="ratio" title="Доля"/><element name="approved" title="Принято"/><element name="url" title="Ссылка"/><element name="timestamp" title="Дата"/><element name="alias" title="Название · alias"/><element name="column.custom" title="Свой виджет"/><element name="password"/></table>
<definition>
<element name="amount"><display class="tactic.ui.table.FormatElementWdg"><type>float</type><format>-1234.12</format><total_summary>total</total_summary></display></element>
<element name="ratio"><display widget="format"><type>percent</type><format>-12.95%</format><total_summary>average</total_summary></display></element>
<element name="approved"><display class="tactic.ui.table.FormatElementWdg"><type>boolean</type><format>Checkbox</format></display></element>
<element name="timestamp"><display class="tactic.ui.table.FormatElementWdg"><type>date</type><format>31/12/1999</format><timezone>UTC</timezone></display></element>
<element name="url"><display class="tactic.ui.table.LinkElementWdg"/></element>
<element name="alias"><display class="tactic.ui.common.SimpleTableElementWdg"><column>name</column><single_line>true</single_line></display></element>
<element name="column.custom"><display class="company.CustomColumn"/></element>
</definition><edit><element name="heading" title="Основные параметры"><display class="tactic.ui.panel.EditTitleWdg"><level>1</level></display></element><element name="name"><display class="pyasm.widget.TextWdg"/></element></edit></config>'''
INLINE='''<config><table><element name="name" title="Имя из inline" width="260"/><element name="amount" title="Целая сумма"><display class="tactic.ui.table.FormatElementWdg"><type>integer</type><format>-1234</format></display></element><element name="code"/></table></config>'''
CODE_XML='<config><card title="Only stored code"><element name="code" title="Из config_code"/></card><definition><element name="code" title="Ignore other view"/></definition></config>'
CUSTOM_XML='<config><custom><element name="column.custom" title="Глобальное определение"><display class="company.CustomColumn"/></element></custom></config>'
ALIASES=json.loads((ROOT/'src/tactic/core/widget_aliases.json').read_text())
def model(xml=XML,view='table'):
 return ConfigModel(view,[ConfigSource(xml,view,'TEST config/widget_config:personal'),ConfigSource(xml,'definition','TEST project definitions')],ALIASES)

class Store(OriginalStore):
 def __init__(self,count=235):
  super().__init__(login='fixture',project='fixture');self.denied=set()
  for n in range(count):
   self.row('columns07',code='ROW%04d'%n,name=('=HYPERLINK("https://unsafe.invalid")' if n==0 else 'Строка %03d, "тест"'%n),department='A' if n%2==0 else 'B',amount=1234.567+n,ratio=.125,approved=n%2,url='javascript:alert(1)' if n==0 else 'https://example.invalid/'+str(n),timestamp='2026-10-01 10:20:30',project_code='fixture',s_status='active',password='DO-NOT-EXPORT')
  self.row('columns07',code='FOREIGN',name='Other project',department='A',amount=1,project_code='other',s_status='active',password='OTHER-SECRET')
  self.db.commit()
 def access(self,category,keys,*args,**kwargs):
  return not any(k.get('key') in self.denied for k in keys if isinstance(k,dict))
 @contextmanager
 def bind(self):
  store=self
  class SearchProxy:
   def __new__(cls,stype):return store.search(stype)
   @staticmethod
   def eval(*args,**kwargs):return RealSearch.eval(*args,**kwargs)
  with super().bind(),patch('pyasm.common.Environment.get_login',return_value=None),patch('pyasm.biz.PrefSetting.get_value_by_key',return_value='UTC'),patch('pyasm.search.Search',SearchProxy),patch('pyasm.common.Environment.get_security',return_value=SimpleNamespace(check_access=self.access,is_admin=lambda:True)),patch('pyasm.search.SearchType.get_tactic_type',side_effect=lambda st,n:COLUMNS[n]['data_type']),patch('pyasm.search.SearchType.get_column_info',return_value=COLUMNS),patch('pyasm.search.SearchType.column_exists',side_effect=lambda st,n:n in COLUMNS),patch('pyasm.search.SearchType.get',return_value=SimpleNamespace(get_retire_col=lambda:'s_status')):
   yield

class Backend(ExtendedBackend):
 def __init__(self,store):
  super().__init__({'allow_writes':False});self.store=store;self.xml=XML;self.extra=[];self.code_xml=CODE_XML
  self.active_target={'search_type':ST,'view':'table','options':{}}
 def _project(self):return self.store.project
 def require_type(self,stype):
  if stype!=ST:raise ApiError(403,'test_scope','TEST type only')
 def _stub(self):return SimpleNamespace(get_column_info=lambda st:COLUMNS)
 def _model(self,stype,view):return model(self.xml,view)
 def _column_config_sources(self):return list(self.extra)
 def _config_code_model(self,code):
  if code!='CONFIG07':raise ApiError(404,'config_code','TEST config not found')
  return ConfigModel('card',[ConfigSource(self.code_xml,'card','TEST config/widget_config:CONFIG07')],ALIASES)
 def _can_retire(self,stype):return False
 def _defaults(self,search,stype,options):
  search.add_filter('project_code',self._project())
  super()._defaults(search,stype,options)
 def _object(self,stype,key):
  self.require_type(stype)
  if not re.fullmatch(re.escape(ST)+r'\?id=\d+',key or ''):raise ApiError(403,'key_scope','TEST key scope')
  obj=self.store.get('columns07',id=int(key.split('=')[-1]),project_code=self._project())
  if not obj:raise ApiError(404,'not_found','TEST object missing')
  return obj
 def _serialize(self,obj,spec):
  row=super()._serialize(obj,spec);row['key']=ST+'?id='+str(obj.get_id());return row
 def open_target(self,key):
  self.active_target=dict(self.active_target,id=key,kind='table',handler='tactic.ui.panel.TableLayoutWdg')
  self.active_target['spec']=self.view(ST,self.active_target.get('view','table'),self.active_target['options'])
  return self.active_target
