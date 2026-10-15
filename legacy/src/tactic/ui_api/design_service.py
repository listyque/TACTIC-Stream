"""Native Custom Layout / Manage Views, backed only by original widget_config.

All mutations use original SObject/Command transactions. No arbitrary server
class, template expression or JavaScript execution endpoint is introduced.
"""
from copy import deepcopy
from urllib.parse import quote, unquote
import re
from lxml import etree as E
from tactic.core import design_document as doc
from tactic.core.config_model import ConfigModel, ConfigSource, target_spec
from .contracts import ApiError, revision


_VISIBLE = object()


class DesignService:
    def _design_screen(self, data, layout=False):
        kinds = ('layout-editor',) if layout else ('views-manager', 'search-types', 'config-editor')
        return self._admin_screen(data, kinds)

    def _design_owner(self, login):
        from pyasm.common import Environment
        if login not in (None, '', Environment.get_user_name()):
            raise ApiError(403, 'config_owner', 'Доступно общее или собственное персональное определение')
        return login or None

    def _design_stype(self, data, screen):
        stype = data.get('search_type') or screen.get('search_type')
        if not stype:
            raise ApiError(400,'search_type','Выберите SearchType')
        self.require_type(stype)
        if screen['kind'] == 'search-types' or screen.get('options',{}).get('native_fixed_stype'):
            fixed = screen.get('options',{}).get('native_fixed_stype')
            if fixed and fixed != stype: raise ApiError(403,'scope','Тип закреплён исходной ссылкой')
            self._stype_object(stype)
        return stype

    def _design_rows(self, layout=False, stype=None, view=None, owner=_VISIBLE):
        from pyasm.search import Search
        from pyasm.common import Environment
        s = Search('config/widget_config')
        if layout:
            s.add_op('begin'); s.add_filter('category','CustomLayoutWdg'); s.add_filter('search_type','CustomLayoutWdg'); s.add_op('or')
        elif stype:
            s.add_filter('search_type',stype)
        if view is not None: s.add_filter('view',view)
        if owner is _VISIBLE:
            s.add_op('begin');s.add_filter('login',None);s.add_filter('login','');s.add_filter('login',Environment.get_user_name());s.add_op('or')
        elif owner is None:
            s.add_op('begin');s.add_filter('login',None);s.add_filter('login','');s.add_op('or')
        else: s.add_filter('login',owner)
        s.add_order_by('view');s.add_order_by('priority desc');s.add_order_by('id')
        return s

    def _design_record(self, key, layout=False, stype=None):
        obj = self._object('config/widget_config',key)
        self._design_owner(obj.get_value('login',no_exception=True))
        if layout:
            if 'CustomLayoutWdg' not in (obj.get_value('category',no_exception=True),obj.get_value('search_type',no_exception=True)):
                raise ApiError(403,'layout_scope','Запись не является исходным CustomLayoutWdg')
        elif obj.get_value('search_type') != stype:
            raise ApiError(403,'config_scope','Запись другого SearchType')
        return obj

    def _design_envelope(self,obj, layout=False):
        xml = obj.get_value('config'); view = obj.get_value('view')
        result = {'key':obj.get_search_key(),'view':view,'xml':xml,
                  'login':obj.get_value('login',no_exception=True) or None,
                  'revision':revision(obj.get_sobject_dict()),'can_write':self.allow_writes}
        if layout:
            try: result['parts']=doc.layout_parts(xml,view)
            except ValueError as exc: result.update(parts=None,notice=str(exc)+'; исходный XML доступен без потери данных')
        return result

    def _design_template(self, stype, view):
        """Snapshot resolved definitions for explicit COPY, never mutate source."""
        from tactic.core.config_options import append_option
        import xml.etree.ElementTree as ET
        model = self._model(stype,view)
        root=ET.Element('config'); node=ET.SubElement(root,'view',{'name':view}) if ('@' in view or ':' in view) else ET.SubElement(root,view)
        for k,v in model.attributes().items(): node.set(k,str(v))
        for el in model.elements():
            n=ET.SubElement(node,'element',{'name':el['name'],**el['attributes']})
            for kind,handler,options in (('display',el['handler'],el['options']),('edit',el['edit_handler'],el['edit_options']),('action',el['action_handler'],el['action_options'])):
                if handler or options:
                    d=ET.SubElement(n,kind,{'class':handler} if handler else {})
                    for k,v in options.items(): append_option(d,k,v)
        return ET.tostring(root,encoding='unicode'), model

    def design_operation(self,method,path,data):
        from pyasm.search import SearchType
        layout = path in ('/layout-document','/layout-preview') or data.get('kind') == 'layout'
        screen = self._design_screen(data,layout)
        if path == '/layout-preview':
            if method != 'POST': raise ApiError(405,'method','POST required')
            xml = data.get('xml'); name = doc.view_name(data.get('view'))
            parts = doc.layout_parts(xml,name)
            return {'parts':parts,'executed':False,'notice':'Статический предпросмотр. Mako, expressions, behaviors и callbacks не исполняются.'}
        stype = None if layout else (data.get('search_type') or screen.get('search_type'))
        if path == '/design-catalog' and method == 'GET':
            if not layout and not stype:
                return {'types':self.catalog()['types'],'items':[],'total':0}
            if stype: stype=self._design_stype(data,screen)
            s=self._design_rows(layout,stype)
            try: offset=int(data.get('offset',0));limit=int(data.get('limit',100))
            except (ValueError,TypeError): raise ApiError(400,'pagination','Некорректная страница')
            if not 0<=offset<=1000000 or not 1<=limit<=100:raise ApiError(400,'pagination','Страница: 1–100 записей')
            q=data.get('q','')
            if not isinstance(q,str) or len(q)>200:raise ApiError(400,'search','Поиск до 200 символов')
            if q:
                from pyasm.search import Sql
                escaped=q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
                s.add_where('view LIKE %s ESCAPE %s' % (Sql.quote('%'+escaped+'%'),Sql.quote('\\')))
            total=s.get_count();s.set_limit(limit);s.set_offset(offset)
            rows=s.get_sobjects()
            items=[{'key':o.get_search_key(),'view':o.get_value('view'),'login':o.get_value('login') or None,
                    'category':o.get_value('category',no_exception=True),'priority':o.get_value('priority',no_exception=True)} for o in rows]
            views=[]
            if not layout:
                model=self._model(stype,'table')
                for source in model.sources:
                    for el in doc.parse(source.text):
                        if isinstance(el.tag,str):
                            name=el.get('name') if el.tag=='view' else el.tag
                            if name and name not in views:views.append(name)
                views=sorted(set(views)|{o['view'] for o in items if o['view']})
            return {'items':items,'total':total,'offset':offset,'limit':limit,'views':views,
                    'types':self.catalog()['types'] if not layout else [],'can_write':self.allow_writes,
                    'initial_view':screen.get('options',{}).get('view')}
        if path not in ('/layout-document','/view-document'):
            raise ApiError(405,'method','Неизвестная операция редактора')
        if not layout: stype=self._design_stype(data,screen)
        if method == 'GET':
            if data.get('key'):
                obj=self._design_record(data['key'],layout,stype)
                return self._design_envelope(obj,layout)
            name=doc.view_name(data.get('view') or 'table')
            if layout:raise ApiError(400,'key','Выберите запись layout по ключу')
            xml,model=self._design_template(stype,name)
            return {'key':None,'view':name,'xml':xml,'revision':model.fingerprint(),'inherited':True,
                    'can_write':self.allow_writes,'elements':model.elements(),
                    'layers':[{'view':x.view,'origin':x.origin} for x in model.sources]}
        if method not in ('POST','PATCH','DELETE'):raise ApiError(405,'method','Метод не поддерживается')
        def save():
            obj=self._design_record(data['key'],layout,stype) if data.get('key') else None
            current=self._design_envelope(obj,layout) if obj else None
            if current and current['revision']!=data.get('revision'):
                raise ApiError(409,'conflict','Запись изменилась. Ваши правки не перезаписывают чужую версию.')
            if method == 'DELETE':
                if obj is None or data.get('confirm')!='REMOVE_OVERRIDE':raise ApiError(400,'confirmation','Выберите запись и подтвердите REMOVE_OVERRIDE')
                xml=doc.remove_view(current['xml'],current['view'])
                root=doc.parse(xml)
                if any(isinstance(x.tag,str) for x in root):obj.set_value('config',xml);obj.commit()
                else:obj.delete()
                return {'removed':True,'notice':'Удалено только локальное переопределение; нижние слои могут снова стать видимыми.'}
            if method == 'PATCH':
                if obj is None:raise ApiError(400,'key','Нужна существующая запись')
                name=current['view']
                if layout and 'changes' in data:xml=doc.patch_layout(current['xml'],name,data['changes'])
                elif 'xml' in data:
                    # Replace only the selected view; never wholesale replace the document.
                    replacement=doc.find_view(doc.parse(data['xml']),name)
                    if replacement is None:raise ApiError(400,'view','XML не содержит выбранный view')
                    root=doc.parse(current['xml']);old=doc.find_view(root,name)
                    if old is None:raise ApiError(400,'view','В существующей записи не найден view')
                    root.replace(old,deepcopy(replacement));xml=doc.serialize(root)
                else:raise ApiError(400,'changes','Не переданы изменения')
                obj.set_value('config',xml);obj.commit()
            else:
                name=doc.view_name(data.get('view'));owner=self._design_owner(data.get('login'))
                # Sharing a global source does not grant access to another user's override.
                existing=self._design_rows(layout,stype,name,owner);existing.set_limit(1)
                if existing.get_sobject():raise ApiError(409,'exists','Такой view в выбранной области уже существует')
                if data.get('source_key'):
                    source=self._design_record(data['source_key'],layout,stype)
                    if revision(source.get_sobject_dict())!=data.get('source_revision'):raise ApiError(409,'conflict','Исходник копии изменился')
                    xml=doc.copy_view(source.get_value('config'),source.get_value('view'),'<config/>',name)
                elif data.get('source_view'):
                    if layout:raise ApiError(400,'source','Выберите конкретный layout')
                    xml,model=self._design_template(stype,doc.view_name(data['source_view']))
                    if model.fingerprint()!=data.get('source_revision'):raise ApiError(409,'conflict','Определения исходного view изменились')
                    xml=doc.copy_view(xml,data['source_view'],'<config/>',name)
                elif data.get('xml'):
                    if data.get('expected_source_revision') and self._model(stype,name).fingerprint()!=data['expected_source_revision']:
                        raise ApiError(409,'conflict','Исходное представление изменилось')
                    selected=doc.find_view(doc.parse(data['xml']),name)
                    if selected is None:raise ApiError(400,'view','XML не содержит новый view')
                    root=E.Element('config');root.append(deepcopy(selected));xml=doc.serialize(root)
                else:
                    root=E.Element('config');node=doc.new_view(root,name)
                    if layout:E.SubElement(E.SubElement(node,'html'),'div').text='Новый Custom Layout'
                    else:
                        node.set('layout','tactic.ui.panel.TableLayoutWdg')
                        for column in ('code','name','description'):
                            if column in SearchType.get_column_info(stype):E.SubElement(node,'element',name=column)
                    xml=doc.serialize(root)
                obj=SearchType.create('config/widget_config');obj.set_value('view',name);obj.set_value('login',owner or '')
                if layout:obj.set_value('category','CustomLayoutWdg')
                else:obj.set_value('search_type',stype)
                obj.set_value('config',xml);obj.commit()
            return dict(self._design_envelope(obj,layout),saved=True,executed=False)
        try:return self._write(save)
        except ValueError as exc:raise ApiError(400,'design_xml',str(exc)) from exc

    def layout_screen(self, target):
        """Resolve a SAVED definition, never an arbitrary browser-supplied widget."""
        from pyasm.search import Search
        from pyasm.common import Environment
        from pathlib import Path
        opts=target.get('options',{})
        if opts.get('native_layout_key'):
            obj=self._design_record(opts['native_layout_key'],True)
            text=obj.get_value('config');name=obj.get_value('view')
        else:
            name=doc.view_name(str(opts.get('view') or target.get('view') or '').replace('/','.'))
            text=opts.get('config_xml')
            if text:
                doc.parse(text)
            else:
                # Match the legacy precedence: category DB -> includes -> deprecated DB.
                # Scope each DB lookup to shared / own entries (never another user's draft).
                def query(category=None, legacy=False):
                    q=Search('config/widget_config');q.add_filter('view',name)
                    if category:q.add_filter('category',category)
                    if legacy:q.add_filter('search_type','CustomLayoutWdg')
                    elif opts.get('search_type'):q.add_filter('search_type',opts['search_type'])
                    q.add_op('begin');q.add_filter('login',None);q.add_filter('login','');q.add_filter('login',Environment.get_user_name());q.add_op('or')
                    q.set_limit(101);found=q.get_sobjects()
                    if len(found)>100:raise ApiError(413,'layout_layers','Слишком много определений layout')
                    def priority(o):
                        value=o.get_value('priority',no_exception=True)
                        return int(value) if value not in ('',None) else 0
                    found.sort(key=priority,reverse=True)
                    if len(found)>1 and priority(found[0])==priority(found[1]):
                        raise ApiError(409,'layout_ambiguous','Несколько определений с одинаковым priority; выберите запись в редакторе')
                    return found[0].get_value('config') if found else None
                text=query(opts.get('category') or 'CustomLayoutWdg')
                if not text:
                    base=Path(Environment.get_install_dir())/'src/tactic/ui/config'
                    for item in str(opts.get('include') or '').split('|'):
                        if not item:continue
                        path=(base/item).resolve()
                        if not path.is_relative_to(base.resolve()) or not path.is_file():raise ApiError(400,'include','Разрешены только исходные файлы UI config')
                        candidate=path.read_text(encoding='utf-8')
                        if doc.find_view(doc.parse(candidate),name) is not None:text=candidate;break
                if not text:text=query(opts.get('category'),legacy=True)
            if not text:raise ApiError(404,'layout_missing','Custom Layout не найден в исходной конфигурации')
        parts=doc.layout_parts(text,name)
        # Inline <element>, display_class shorthand, and same-view definitions
        # follow get_element_wdg rather than inventing a default data table.
        tree=doc.parse('<config><layout><html>'+parts['html']+'</html></layout></config>')
        elements=[el for el in tree.findall('.//element') if not any(p.tag=='element' for p in el.iterancestors())];children=[]
        if len(elements)>64:raise ApiError(413,'layout_widgets','До 64 вложенных виджетов')
        for index,el in enumerate(elements):
            el=deepcopy(el);attrs=dict(el.attrib);element_name=el.get('name') or 'element'+str(index);el.set('name',element_name)
            unsupported=None
            if attrs.get('type')=='reference':
                ref_type=attrs.get('search_type');self.require_type(ref_type)
                model=self._model(ref_type,attrs.get('view') or 'table');definition=model.describe(element_name)
                definition['options']={**definition['options'],**attrs}
            else:
                if el.find('display') is None and (attrs.get('display_class') or attrs.get('view')):
                    display=E.SubElement(el,'display',{'class':attrs.get('display_class') or 'tactic.ui.panel.CustomLayoutWdg'})
                    for k,v in attrs.items():
                        k=k.replace('spt_','')
                        if not re.fullmatch(r'[A-Za-z_][\w.-]*',k):raise ApiError(400,'layout_attribute','Некорректный параметр элемента')
                        E.SubElement(display,k).text=v
                tmp=E.Element('config');v=E.SubElement(tmp,'layout');v.append(el)
                model=ConfigModel('layout',[ConfigSource(doc.serialize(tmp),'layout','CustomLayoutWdg inline'),ConfigSource(text,name,'CustomLayoutWdg definition')])
                definition=model.describe(element_name)
            if not definition['handler']:
                unsupported='Нет определения display-виджета в выбранном layout'
            options=dict(definition['options'])
            if isinstance(options.get('view'),str) and options['view'].startswith('.'):
                options['view']='.'.join(name.split('.')[:-1])+options['view']
            if opts.get('include') and 'include' not in options:options['include']=opts['include']
            if attrs.get('load') in ('manual','sequence','async') or attrs.get('load_once') in ('true',True):
                unsupported='Специальный режим загрузки '+str(attrs.get('load') or 'load_once')+' требует отдельного адаптера'
            child=target_spec(definition['handler'] or 'UnresolvedLayoutElement',options,definition['attributes'])
            child.update(id=target['id']+'/~layout/'+str(index),title=definition['title'],name=element_name,config_view=name)
            if unsupported:child.update(kind='unsupported',notice=unsupported)
            if attrs.get('display')=='false' or attrs.get('load')=='none':child.update(kind='unsupported',handler='Hidden by configuration',hidden=True)
            children.append(child)
        return {'view':name,'parts':parts,'children':children,'revision':revision(text),'executed':False,
                'notice':'Нативные вложенные виджеты. Статическая разметка не исполняет пользовательские Mako/JS.'}

    def design_derived_target(self,parent,part,key):
        if part.startswith('layout:'):
            if parent['kind']!='layout-editor':raise ApiError(403,'layout_target','Требуется исходный Layout Editor')
            obj=self._design_record(unquote(part[7:]),True)
            return {'id':key,'kind':'custom-layout','handler':'tactic.ui.panel.CustomLayoutWdg','title':obj.get_value('view'),
                    'search_type':None,'view':obj.get_value('view'),'config_view':parent.get('config_view'),'attributes':{},
                    'options':{'native_layout_key':obj.get_search_key(),'view':obj.get_value('view')}}
        if part.startswith('view:'):
            if parent['kind'] not in ('views-manager','search-types'):raise ApiError(403,'view_target','Требуется Manage Views')
            import json
            try:stype,view=json.loads(unquote(part[5:]))
            except (ValueError,TypeError):raise ApiError(400,'view_target','Некорректная ссылка')
            self.require_type(stype);doc.view_name(view)
            if parent['kind']=='search-types':self._stype_object(stype)
            model=self._model(stype,view);attrs=model.attributes()
            handler=attrs.get('layout') or ('tactic.ui.panel.EditWdg' if view in ('insert','edit') else 'tactic.ui.panel.TableLayoutWdg')
            handler={'table':'tactic.ui.panel.TableLayoutWdg','table_layout':'tactic.ui.panel.TableLayoutWdg',
                     'TableLayoutWdg':'tactic.ui.panel.TableLayoutWdg','edit':'tactic.ui.panel.EditWdg',
                     'tab':'tactic.ui.container.TabWdg'}.get(handler,handler)
            options={'search_type':stype,'view':view}
            target=target_spec(handler,options,attrs)
            if target['kind']=='tabs':
                # TabWdg's category lookup differs from SearchType views; provide
                # the authorized resolved definition through its original inline branch.
                xml,_=self._design_template(stype,view);target['options']['config_xml']=xml
            elif target['kind']=='form':target['options']['mode']='insert'
            target.update(id=key,title=stype+' / '+view,config_view=view)
            return target
        raise ApiError(403,'design_target','Неизвестный дочерний редактор')
