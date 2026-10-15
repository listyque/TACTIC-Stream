"""Native ManageViewPanelWdg over the original config/widget_config model."""
import re
from lxml import etree as X
from .contracts import ApiError, revision
from tactic.core.config_model import ConfigModel, target_spec
from tactic.core.sidebar_edits import patch_sidebar, load_xml, find_view, NAME

class SidebarService:
    def _sidebar_scope(self,data):
        from pyasm.common import Environment
        if not Environment.get_security().is_admin():raise ApiError(403,'admin_only','Нужны права администратора')
        view=data.get('view') or 'project_view'
        login=Environment.get_user_name();own='my_view_'+login.replace('\\','_')
        if view=='my_view':view=own
        if not isinstance(view,str) or not NAME.fullmatch(view):raise ApiError(400,'view','Некорректный view')
        if view.startswith('my_view_') and view!=own and not view.startswith(own+'__'):raise ApiError(403,'personal','Допустим только собственный personal sidebar')
        if view in ('definition','edit_definition','default_definition','_template'):
            raise ApiError(400,'definition','Общие definitions редактируются в исходном XML-редакторе')
        return view,login if view.startswith('my_view_') else None

    def _sidebar_data(self,view,login):
        from pyasm.search import Search
        from tactic.core.sidebar_config import SidebarConfig
        model=ConfigModel.from_tactic(SidebarConfig.get_config('SideBarWdg',view,personal=login is not None))
        search=Search('config/widget_config');search.add_filter('search_type','SideBarWdg');search.add_filter('view',view)
        search.add_order_by('priority desc');search.set_limit(101);records=search.get_sobjects()
        if len(records)>100:raise ApiError(413,'layers','Слишком много переопределений sidebar')
        # Original resolver does not filter view rows by login: refuse ambiguous ownership.
        if any((o.get_value('login') or None)!=login for o in records):raise ApiError(409,'scope_conflict','У view есть запись с другой login-областью; проверьте XML, не перезаписывайте её')
        obj=records[0] if records else None
        if len(records)>1 and records[0].get_value('priority',no_exception=True)==records[1].get_value('priority',no_exception=True):
            raise ApiError(409,'duplicate_view','Две конфигурации одинакового приоритета. Выберите/исправьте их в XML-редакторе')
        if obj:raw=obj.get_value('config')
        else:
            source=next((s for s in model.sources if s.view not in ('definition','edit_definition','default_definition') and s.node is not None),None)
            root=X.Element('config')
            if source is not None:
                old=load_xml(source.text);selected=find_view(old,view)
                if selected is not None:root.append(selected)
            if find_view(root,view) is None:X.SubElement(root,view)
            raw=X.tostring(root,encoding='unicode')
        rev=revision({'model':model.fingerprint(),'rows':[(o.get_search_key(),o.get_value('config'),o.get_value('priority',no_exception=True)) for o in records]})
        return model,obj,raw,rev

    def sidebar_editor(self,method,data):
        from pyasm.search import Search,SearchType
        from pyasm.common import Environment
        from tactic.core.sidebar_config import SidebarConfig
        view,login=self._sidebar_scope(data)
        model,obj,raw,rev=self._sidebar_data(view,login)
        if method=='GET':
            elements=[]
            root=load_xml(raw);node=find_view(root,view)
            for index,e in enumerate([n for n in node if n.tag=='element']):
                desc=model.describe(e.get('name'));h=desc['handler'];opts=desc['options']
                kind={'FolderWdg':'folder','SideBarSectionLinkWdg':'folder','SeparatorWdg':'separator','TitleWdg':'title'}.get(h,'link')
                resolved=target_spec(h,opts,desc['attributes']) if kind=='link' else {'kind':kind}
                elements.append({**desc,'index':index,'kind':kind,'renderer':resolved['kind'],'local_xml':X.tostring(e,encoding='unicode'),
                                 'can_edit_options':h in ('','LinkWdg','FolderWdg','SeparatorWdg','TitleWdg')})
            own='my_view_'+Environment.get_user_name().replace('\\','_')
            choices=set(SidebarConfig().get_views()+['project_view',own])
            search=Search('config/widget_config');search.add_filter('search_type','SideBarWdg');search.set_limit(1000)
            for o in search.get_sobjects():
                v=o.get_value('view')
                if v and NAME.fullmatch(v) and v not in ('definition','edit_definition','default_definition') and (not v.startswith('my_view_') or v==own or v.startswith(own+'__')):choices.add(v)
            return {'view':view,'login':login,'personal':login is not None,'elements':elements,'revision':rev,'can_write':self.allow_writes,
                    'views':sorted(choices),'layers':[{'view':s.view,'origin':s.origin} for s in model.sources],
                    'notice':'Порядок и локальные переопределения выбранного view. Удаление ссылки не удаляет её общую definition, дочерний view или объекты.'}
        if method!='PATCH':raise ApiError(405,'method','Метод не поддерживается')
        if rev!=data.get('revision'):raise ApiError(409,'conflict','Sidebar изменился; ваши правки не применены')
        operations=data.get('operations')
        descriptions={e['name']:e for e in model.elements()}
        if isinstance(operations,list):
            for op in operations:
                if not isinstance(op,dict):continue
                if op.get('op')=='add' and op.get('kind','link')=='link':
                    opts=op.get('options') or {}
                    stype=opts.get('search_type') if isinstance(opts,dict) else None
                    if stype and stype not in {x['code'] for x in self.catalog()['types']}:
                        raise ApiError(403,'stype_scope','SearchType ссылки отсутствует в доступном каталоге проекта')
        updated,folders=patch_sidebar(raw,view,operations,descriptions)
        own='my_view_'+Environment.get_user_name().replace('\\','_')
        for folder in folders:
            if login and not folder.startswith(own+'__'):raise ApiError(400,'folder_scope','Личная папка должна иметь имя '+own+'__...')
            if not login and folder.startswith('my_view_'):raise ApiError(403,'folder_scope','Общая папка не может ссылаться на личный sidebar')
            if folder in ('definition','edit_definition','default_definition','admin_views','project_view'):
                raise ApiError(400,'folder_scope','Служебный view не создаётся как новая папка')
            # Only create NEW folders. Referencing existing sections needs a reviewed XML definition.
            child=ConfigModel.from_tactic(SidebarConfig.get_config('SideBarWdg',folder,personal=login is not None))
            if any(s.node is not None and s.view==folder for s in child.sources):raise ApiError(409,'folder_exists','View папки уже существует; выберите новое системное имя')
        def save():
            if self._sidebar_data(view,login)[3]!=rev:raise ApiError(409,'conflict','Sidebar изменился перед сохранением')
            current=obj
            if current is None:
                current=SearchType.create('config/widget_config');current.set_value('search_type','SideBarWdg');current.set_value('category','SideBarWdg');current.set_value('view',view)
                if login:current.set_value('login',login)
            current.set_value('config',updated);current.commit()
            for folder in folders:
                child=SearchType.create('config/widget_config');child.set_value('search_type','SideBarWdg');child.set_value('category','SideBarWdg');child.set_value('view',folder)
                if login:child.set_value('login',login)
                r=X.Element('config');X.SubElement(r,folder);child.set_value('config',X.tostring(r,encoding='unicode'));child.commit()
            return {'saved':True,'view':view,'key':current.get_search_key(),'folders':folders,'notice':'Исходный widget_config сохранён; sidebar можно перечитать без перезапуска.'}
        return self._write(save)
