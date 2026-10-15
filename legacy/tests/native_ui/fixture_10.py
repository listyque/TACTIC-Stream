"""TEST ONLY: production widget/menu services + isolated synthetic persistence.

Configuration below is XML fixture input. It is not imported by TACTIC runtime,
not a replacement for a real project's widget_config and not live-DB proof.
"""
import copy
from pathlib import Path
from fixture_09 import FixtureBackend as Previous
from tactic.core.config_model import ConfigModel, ConfigSource, SidebarProjection
from tactic.core.widget_containers import tab_model, tab_items, default_values, false
from tactic.ui_api.widget_service import WidgetService
from tactic.ui_api.menu_service import MenuService
from tactic.ui_api.contracts import ApiError, revision

ROOT = Path(__file__).resolve().parents[2]
MENU = '''<config><fixture_widgets title="TEST FIXTURE · Widget containers">
 <element name="widgets" title="TEST · Вложенные виджеты"><display class="tactic.ui.container.TabWdg"><view>workspace</view><include>fixtures-widgets.xml</include><selected>edit</selected><save_state>fixture-widgets</save_state><show_remove_tabs>edit</show_remove_tabs></display></element>
 <element name="embedded" title="TEST · Встроенная форма"><display class="tactic.ui.panel.EditWdg"><search_type>sthpw/task</search_type><search_key>sthpw/task?code=FIXTURE0</search_key><view>edit</view><title>Встроенная задача</title><element_names>description,status,bid_start_date</element_names></display></element>
 <element name="readonly" title="TEST · Только просмотр"><display class="tactic.ui.panel.EditWdg"><search_type>sthpw/task</search_type><search_key>sthpw/task?code=FIXTURE0</search_key><view>edit</view><mode>view</mode><show_header>false</show_header></display></element>
 <element name="insert_form" title="TEST · Создание из defaults"><display class="tactic.ui.panel.EditWdg"><search_type>fixture/item</search_type><view>insert</view><single>true</single><default>{"description":"Default из конфигурации"}</default></display></element>
</fixture_widgets></config>'''
TABS = '''<config><workspace>
 <element name="edit" title="Форма задачи"><display class="tactic.ui.panel.EditWdg"><search_type>sthpw/task</search_type><search_key>sthpw/task?code=FIXTURE0</search_key><view>edit</view><element_names>description,status,bid_start_date</element_names></display></element>
 <element name="secret" title="Скрытая вкладка" display="false"><display class="tactic.ui.panel.TableLayoutWdg"><search_type>sthpw/login</search_type></display></element>
 <element name="rows" title="Таблица задач" load="true"><display class="tactic.ui.panel.TableLayoutWdg"><search_type>sthpw/task</search_type><view>table</view><search_limit>5</search_limit></display></element>
 <element name="nested" title="Вложенный контейнер"><display class="tactic.ui.container.TabWdg"><view>inner</view><include>fixtures-widgets.xml</include><show_remove>false</show_remove></display></element>
</workspace><inner>
 <element name="task" title="Форма другой задачи"><display class="tactic.ui.panel.EditWdg"><search_type>sthpw/task</search_type><search_key>sthpw/task?code=FIXTURE1</search_key><view>edit</view></display></element>
 <element name="unported" title="Неперенесённый виджет"><display class="custom.studio.SpecialWdg"><custom>retained</custom></display></element>
</inner></config>'''

class Obj:
 def __init__(self, row): self.row=row
 def is_retired(self): return self.row['values'].get('s_status')=='retired'
 def get_search_key(self):return self.row['key']

class FixtureBackend(WidgetService, MenuService, Previous):
 def __init__(self,*a,**kw):
  super().__init__(*a,**kw); self.allow_writes=True;self.allow_uploads=True;self.created_form_count=10000
 def _tree(self):
  tree,targets=super()._tree()
  if self._project()=='fixture':
   p=SidebarProjection(lambda v,p=False:ConfigModel(v,[ConfigSource(MENU,v,'TEST widget_config')]),lambda n:True,'fixture','fixture')
   tree+=p.build(['fixture_widgets']);targets.update(p.targets)
  return tree,targets
 def _tab_model(self,parent):
  return tab_model(parent['options'],lambda name:TABS,lambda view:None)
 def _menu_admin(self):return True
 def _can_retire(self,stype):return stype in ('sthpw/task','fixture/item')
 def _object(self,stype,key):
  if not isinstance(key,str) or key.split('?',1)[0]!=stype:raise ApiError(403,'fixture_scope','Wrong fixture type')
  obj=super()._object(stype,key)
  if not hasattr(obj,'is_retired'):obj.is_retired=lambda:obj.get_value('s_status')=='retired'
  return obj
 def open_target(self,key):
  if not isinstance(key,str) or len(key)>4000 or key.count('/~')>8:raise ApiError(400,'target','Invalid depth')
  if key.startswith('fixture_widgets/'):
   if '/~tab/' in key:
    root,index=key.rsplit('/~tab/',1);parent=self.open_target(root)
    if parent['kind']!='tabs':raise ApiError(403,'tab','Not a container')
    target=next((c for c in self.tab_children(parent) if c['id']==key),None)
    if target is None:raise ApiError(403,'tab','Hidden or missing')
   else:
    _,targets=self._tree();target=copy.deepcopy(targets.get(key))
    if target is None:raise ApiError(403,'target','No fixture widget')
   self.active_target=target
   if target['kind']=='tabs':target['children']=self.tab_children(target)
   elif target['kind']=='form':
    opts=target['options'];target['form_binding']={'key':opts.get('search_key'),'mode':opts.get('mode') or ('edit' if opts.get('search_key') else 'insert')}
    target['spec']=self.form(target['search_type'],target['form_binding']['key'])['spec']
   elif target['kind']=='table':target['spec']=self.view(target['search_type'],target['view'],target['options'])
   return target
  result=super().open_target(key);self.active_target=result;return result
 def view(self,stype,view,options=None):
  spec=super().view(stype,view,options)
  if stype=='sthpw/task':
   for f in spec['fields']: f['nullable']=True
   if (options or {}).get('search_limit'):spec.setdefault('table_options',{})['page_size']=int(options['search_limit'])
  return spec
 def form(self,stype,key=None):
  form=super().form(stype,key)
  target=getattr(self,'active_target',{})
  if target.get('kind')=='form':
   opts=target['options'];names=opts.get('element_names')
   form['spec']['view']=target.get('view') or 'edit'
   if names:form['spec']['fields']=[f for n in names.split(',') for f in form['spec']['fields'] if f['name']==n]
   if form.get('record'):
    visible={f['name'] for f in form['spec']['fields']};form['record']['values']={n:v for n,v in form['record']['values'].items() if n in visible}
   mode=target['form_binding']['mode'];form['spec']['mode']=mode
   if mode=='view':
    form['spec']['capabilities']={'create':False,'update':False,'retire':False}
    for f in form['spec']['fields']:f['read_only']=True
   elif mode=='insert':form['spec']['capabilities']={'create':True,'update':False,'retire':False}
   form['defaults']=default_values(opts.get('default')) if key is None else {}
  return form
 def update(self,stype,key,values,expected,spec):
  if getattr(self,'active_target',{}).get('kind')!='form':return super().update(stype,key,values,expected,spec)
  original=super().form(stype,key)['record']
  if original['revision']!=expected:raise ApiError(409,'conflict','TEST original record changed')
  self.values.setdefault(key,{}).update(values)
  return self.form(stype,key)['record']
 def create(self,stype,values,spec):
  self.created_form_count+=1;key=stype+'?code=FIXTURE'+str(self.created_form_count);self.values[key]=copy.deepcopy(values)
  return {'key':key,'values':copy.deepcopy(values),'revision':revision(values)}
 def config_operation(self,method,path,data):
  if path=='/license' and method=='GET':
   if self.open_target(data.get('target'))['kind']!='license':raise ApiError(403,'target','Not a license fixture')
   return {'info':{'company':'TEST FIXTURE','tactic_version':'TEST','max_users':10,'current_users':2,'expiry_date':''},'licensed':False,'message':'Synthetic license metadata — signature not verified','can_write':False,'revision':'fixture-license'}
  if path=='/context-menu':
   if method!='GET':raise ApiError(405,'method','Read-only menu')
   return self.context_menu(data)
  if path=='/embedded-form':
   if method not in ('GET','POST','PATCH'):raise ApiError(405,'method','Invalid form operation')
   return self.embedded_form(method,data)
  return super().config_operation(method,path,data)
