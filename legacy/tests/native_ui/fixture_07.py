"""TEST ONLY: adds production config/query/cell/CSV on an isolated SQLite table.

Existing fixture subsystems stay synthetic. This is not a server installation.
"""
import copy
from fixture_06 import FixtureBackend as Previous
from column_test_store_07 import Store,Backend,ST,INLINE,model,ConfigSource,CUSTOM_XML
from tactic.core.config_model import ConfigModel,SidebarProjection
from tactic.ui_api.contracts import ApiError
MENU='''<config><fixture_columns title="TEST FIXTURE 0.7 · Widget configuration"><element name="formatted" title="TEST · Форматы и итоги"><display class="tactic.ui.panel.TableLayoutWdg"><search_type>fixture/columns07</search_type><view>table</view><order_by>department asc, amount desc</order_by><search_limit>20</search_limit></display></element>
<element name="inline" title="TEST · Inline-конфигурация"><display class="tactic.ui.panel.TableLayoutWdg"><search_type>fixture/columns07</search_type><view>table</view><config><element name="name" title="Имя из inline" width="260"/><element name="amount" title="Целая сумма"><display class="tactic.ui.table.FormatElementWdg"><type>integer</type><format>-1234</format></display></element><element name="code"/></config></display></element>
<element name="code_view" title="TEST · config_code"><display class="tactic.ui.panel.TableLayoutWdg"><search_type>fixture/columns07</search_type><config_code>CONFIG07</config_code><view>table</view></display></element>
<element name="compact" title="TEST · Настройки таблицы"><display class="tactic.ui.panel.TableLayoutWdg"><search_type>fixture/columns07</search_type><view>table</view><element_names>code,name,amount</element_names><show_header>false</show_header><show_select>false</show_select><show_shelf>false</show_shelf><show_search>false</show_search><show_context_menu>none</show_context_menu><show_search_limit>false</show_search_limit></display></element>
<element name="filtered" title="TEST · Сохранённый фильтр"><display class="tactic.ui.panel.TableLayoutWdg"><search_type>fixture/columns07</search_type><view>table</view><element_names>code,name,department,amount</element_names><order_by>code asc</order_by><filter>[{"prefix":"main_body","main_body_enabled":"on","main_body_column":"department","main_body_relation":"is","main_body_value":"A"}]</filter></display></element>
</fixture_columns></config>'''
class FixtureBackend(Previous):
 def __init__(self,*a,**kw):
  super().__init__(*a,**kw);self.columns_store=Store(235);self.columns_backend=Backend(self.columns_store);self.columns_backend.extra=[ConfigSource(CUSTOM_XML,'custom','TEST global columns')]
 def _tree(self):
  tree,targets=super()._tree()
  if self._project()=='fixture':
   p=SidebarProjection(lambda v,p:ConfigModel(v,[ConfigSource(MENU,v,'TEST widget_config menu')]),lambda n:True,'fixture','fixture');tree+=p.build(['fixture_columns']);targets.update(p.targets)
  return tree,targets
 def view(self,stype,view,options=None):
  if stype!=ST:return super().view(stype,view,options)
  with self.columns_store.bind():return self.columns_backend.view(stype,view,options)
 def query(self,stype,spec,query):
  if stype!=ST:return super().query(stype,spec,query)
  self.columns_backend.active_target=copy.deepcopy(self.active_target)
  with self.columns_store.bind():return self.columns_backend.query(stype,spec,query)
 def resolved_view(self,data):
  target=self.open_target(data['target'])
  if target.get('search_type')!=ST:raise ApiError(501,'test_fixture','Old TEST views do not bind the production config service')
  self.columns_backend.active_target=copy.deepcopy(target)
  with self.columns_store.bind():return self.columns_backend.resolved_view(data)
 def export_csv(self,stype,spec,data):
  if stype!=ST:raise ApiError(501,'test_fixture','Old TEST views do not bind the production CSV service')
  self.columns_backend.active_target=copy.deepcopy(self.active_target)
  with self.columns_store.bind():return self.columns_backend.export_csv(stype,spec,data)
