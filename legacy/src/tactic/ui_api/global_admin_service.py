"""Native handlers for the original Global administration widgets.

No new menu or data store: targets are resolved from Sidebar WidgetConfig. Forms
keep their original field ordering and action classes; secrets are write-only.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import re
import uuid
from .contracts import ApiError, revision, json_safe, SYSTEM_FIELDS, safe_field
from tactic.core.field_policy import field_access
from tactic.core.config_model import parse_xml

GLOBAL_EDIT = {'sthpw/login','sthpw/login_group','sthpw/db_resource'}
APPROVED_ACTIONS = {'','DatabaseAction','pyasm.command.DatabaseAction',
 'DefaultValueDatabaseAction','pyasm.command.DefaultValueDatabaseAction','NonEmptyAction','pyasm.command.NonEmptyAction',
 'LoginAction','pyasm.command.LoginAction','PasswordAction','pyasm.command.PasswordAction',
 'NullAction','pyasm.command.NullAction',
 'tactic.ui.startup.SecurityAddGroupToProjectAction'}
SECRET_NAMES={'password','password_reenter','password re-enter'}


AUDITED_BUTTONS = {
    ('sthpw/pipeline','editor'): ('pipeline-editor', '8035becac43bc0fe671c5638340470cbab6e87491e655e7706fa166a85eedde2'),
    ('sthpw/schema','create'): ('schema-editor', '411dd36aa5e6fc9321117e90f5a1336043358cefbf291ed1569636e93ca61a0e'),
    ('sthpw/login_group','user_assign'): ('members', '350282c3699ffae30adb666e9161aedb82c73e9fbe6e93308b55b9cf2871803f'),
    ('sthpw/db_resource','add_project'): ('resource-project', '28705f9f3faa1cee669f0d6c61a06591559b40d0a089a191140bf07a03c2772b'),
}


def cell_reference(parent,key,field):
    from .record_service import related_id
    base,token=related_id(parent,key,field).rsplit('/~related/',1)
    return base+'/~cell/'+token


class GlobalAdminService:
    def global_operation(self, method, path, data):
        from pyasm.common import Config, Environment
        security=Environment.get_security()
        if not security.is_admin():raise ApiError(403,'admin_only','Требуются права администратора TACTIC')
        target=self.open_target(data.get('target'))
        expected={'/system-config':'system-config','/license':'license'}
        if target.get('kind')!=expected.get(path):raise ApiError(403,'target_denied','Операция не принадлежит этому виджету')
        if path=='/system-config':
            from tactic.core.system_config_model import read_document,config_fields,patch_config
            config_path=Path(Config.get_config_path()).resolve()
            if method=='GET':
                raw,root=read_document(config_path)
                return {'groups':config_fields(root),'revision':hashlib.sha256(raw).hexdigest(),
                        'can_write':self.allow_writes,'source':'DbConfigContentWdg / tactic-conf.xml',
                        'notice':'Сохранение создаёт резервную копию. Изменения применяются после ручного перезапуска. Базы и каталоги автоматически не создаются.'}
            if method=='PATCH':
                if data.get('confirm')!='SAVE_SYSTEM_CONFIG':raise ApiError(400,'confirmation','Подтвердите изменение конфигурации сервера')
                if not self.allow_writes:raise ApiError(403,'read_only','Запись отключена. Используйте MANAGE_TACTIC.bat configure --writes on на сервере.')
                try:result=patch_config(config_path,data.get('revision'),data.get('changes'))
                except FileExistsError as exc:raise ApiError(409,'conflict',str(exc)) from exc
                except ValueError as exc:raise ApiError(400,'system_config',str(exc)) from exc
                return dict(result,saved=True,notice='Файл сохранён с резервной копией. Перезапустите TACTIC для применения.')
        if path=='/license':
            if method=='GET':
                lic=security.get_license()
                info={k:lic.get_data(k) for k in ('company','tactic_version','max_users','expiry_date')}
                info['current_users']=lic.get_current_users()
                # Match the original LicenseManagerWdg. Never serialize public/private keys or signature XML.
                fields=('company','tactic_version','max_users','current_users','expiry_date')
                return {'info':{k:json_safe(info.get(k)) for k in fields},'message':lic.get_message(),
                        'licensed':lic.is_licensed(),'can_write':self.allow_writes,'revision':self._license_revision()}
            if method=='POST':
                if data.get('confirm')!='RENEW_LICENSE':raise ApiError(400,'confirmation','Подтвердите замену лицензии')
                if not self.allow_writes:raise ApiError(403,'read_only','Запись отключена')
                xml=data.get('xml')
                if not isinstance(xml,str) or not 1<=len(xml.encode('utf-8'))<=256*1024:raise ApiError(400,'license_xml','Ожидается XML лицензии до 256 КиБ')
                root=parse_xml(xml)
                if root.tag!='license':raise ApiError(400,'license_xml','Ожидается <license>')
                if (root.findtext('data/version') or '').strip()!='2':raise ApiError(501,'license_format','Через native UI принимается только подписанная XML-лицензия v2; legacy v1 требует отдельной процедуры.')
                from pyasm.security.security import License
                from tactic.core.license_commands import RenewLicenseCbk
                directory=Path(Environment.get_upload_dir());directory.mkdir(parents=True,exist_ok=True)
                name='native-license-'+uuid.uuid4().hex+'.xml';file=directory/name
                try:
                    file.write_text(xml,encoding='utf-8')
                    # Original cryptographic verification, explicitly enabled, before replacing anything.
                    candidate=License(str(file),verify=True)
                    if not candidate.is_licensed():raise ApiError(400,'license_invalid','TACTIC не подтвердил лицензию; текущий файл не изменён')
                    def apply():
                        if data.get('revision')!=self._license_revision():raise ApiError(409,'conflict','Лицензия уже изменена')
                        cmd=RenewLicenseCbk(file_name=name);cmd.execute()
                        return {'saved':True,'revision':self._license_revision(),'notice':'Исходный RenewLicenseCbk установил и перечитал лицензию.'}
                    return self._write(apply)
                finally:
                    if file.exists():file.unlink()
        raise ApiError(405,'method','Метод не поддерживается')

    def _license_revision(self):
        from pyasm.common import Environment
        p=Path(Environment.get_license_dir())/'tactic-license.xml'
        return hashlib.sha256(p.read_bytes() if p.exists() else b'').hexdigest()

    def global_spec(self,spec,model,options):
        """Lift only the audited original administrative form/action families."""
        from pyasm.common import Environment
        from .config_backend import PLAIN, DATABASE_ACTIONS, DENY_EDIT_TYPES
        stype=spec['type'];form=bool(options.get('native_form')) or spec['view'] in ('insert','edit')
        security=Environment.get_security();is_global=stype in GLOBAL_EDIT and security.is_admin()
        if is_global:
            # Default deny still applies to auth tickets, trigger execution and arbitrary system types.
            spec['capabilities'].update(create=self.allow_writes,update=self.allow_writes)
            if getattr(self,'active_target',{}).get('options',{}).get('show_insert')=='false':spec['capabilities']['create']=False
        for f in spec['fields']:
            el=model.describe(f['name']);opts=f.get('display_options') or {};h=f['handler'];short=h.rsplit('.',1)[-1]
            visible,editable=field_access(security,self._project(),stype,f['name'],el['attributes'])
            original_ro=opts.get('read_only') in (True,'true') or el['attributes'].get('edit') in (False,'false')
            if is_global and f['storage'] and h in PLAIN and f['action'] in APPROVED_ACTIONS:
                f.update(supported=True,reason='',read_only=not(self.allow_writes and editable and not original_ro))
                if f['name'] in SYSTEM_FIELDS:f['read_only']=True
            if form and f['name']=='code' and options.get('mode')=='insert' and stype not in DENY_EDIT_TYPES-GLOBAL_EDIT:
                if f['storage'] and h in PLAIN and f['action'] in DATABASE_ACTIONS and editable and not original_ro:
                    f.update(write_system=True,read_only=not self.allow_writes)
            if form and short=='EditTitleWdg':f.update(kind='heading',supported=True,read_only=True,reason='')
            if form and stype=='sthpw/login' and f['name']=='login' and f['action'] in ('LoginAction','pyasm.command.LoginAction'):
                f.update(supported=True,reason='',read_only=not(self.allow_writes and editable and not original_ro))
            if form and stype=='sthpw/login_group' and short=='SecurityAddGroupToProjectInputWdg' and f['action']=='tactic.ui.startup.SecurityAddGroupToProjectAction':
                f.update(kind='boolean',supported=True,reason='',read_only=not(self.allow_writes and editable),virtual_write=True)
            if form and short in ('SelectWdg','SelectInputWdg') and opts.get('query') and not opts.get('values'):
                f.update(kind='select', provider='config-select-query', supported=True, options=[], reason='',
                         read_only=not(self.allow_writes and editable and not original_ro and f['action'] in DATABASE_ACTIONS))
            if not form and short=='ButtonElementWdg':
                button=AUDITED_BUTTONS.get((stype,f['name']))
                actual=hashlib.sha256(' '.join(str(opts.get('cbjs_action') or '').split()).encode()).hexdigest()
                if button and actual==button[1]:f.update(renderer='widget-link',widget_link=True,cell_action=button[0],supported=True,reason='',read_only=True)
            if not form and stype=='sthpw/login_group' and short=='SecurityManagerButtonWdg':
                f.update(renderer='widget-link',widget_link=True,cell_action='security',supported=True,reason='',read_only=True)
            # Actual relation/button widgets, not raw JSON placeholders.
            if not form and stype=='sthpw/login_group' and f['name']=='users' and short=='DropElementWdg' and opts.get('instance_type')=='sthpw/login_in_group':
                f.update(renderer='group-members',supported=True,reason='',read_only=True,widget_link=True,cell_action='members')
            if not form and short in ('HiddenRowElementWdg','HiddenRowToggleWdg') and (opts.get('search_type') or opts.get('dynamic_class')):
                f.update(renderer='widget-link',supported=True,reason='',read_only=True,widget_link=True)
            if not form and stype=='sthpw/project' and short=='ProjectWdg':
                f.update(renderer='project-database',supported=True,reason='',read_only=True)
            if not form and short in ('XmlWdg',) and f['storage']:
                f.update(renderer='xml',supported=True,reason='',read_only=True)
        spec['write_notice']='' if self.allow_writes else 'Запись отключена в настройках native UI. Включите её явно через MANAGE_TACTIC.bat configure --writes on и перезапустите сервер.'
        spec['diagnostics']=[{'field':f['name'],'handler':f['handler'],'reason':f['reason']} for f in spec['fields'] if f.get('reason')]
        return spec

    def complete_global_form(self,stype,key,form):
        from pyasm.common import Environment
        from .config_backend import DATABASE_ACTIONS
        for field in form['spec']['fields']:
            if field.get('provider')=='config-select-query':
                field['options']=self.config_select_options(field,stype,key)
        model=self._view_model(stype,form['spec']['view'],dict(getattr(self,'active_target',{}).get('options',{}),native_form=True,mode='edit' if key else 'insert')) if stype in GLOBAL_EDIT else None
        if stype in GLOBAL_EDIT:
            fields={f['name']:f for f in form['spec']['fields']}
            for name in model.names():
                el=model.describe(name)
                visible,editable=field_access(Environment.get_security(),self._project(),stype,name,el['attributes'])
                if not visible:continue
                if name in SECRET_NAMES and ((stype=='sthpw/login' and el['action_handler'] in APPROVED_ACTIONS) or stype=='sthpw/db_resource'):
                    fields[name]={'name':name,'label':el['title'],'kind':'password','storage':name=='password',
                        'handler':el['edit_handler'] or el['handler'],'action':el['action_handler'],
                        'read_only':not(self.allow_writes and editable),'supported':True,'reason':'Неизменённый пароль сохраняется; значение никогда не возвращается клиенту.',
                        'nullable':False,'options':[],'write_only':True,'virtual_write':True,'sources':el.get('sources',[])}
            form['spec']['fields']=[fields[n] for n in model.names() if n in fields]
            if not key and stype=='sthpw/login_group' and 'add_to_project' in fields:
                form['defaults']['add_to_project']=True  # Original checkbox is checked by default.
            if key and stype=='sthpw/login_group':
                obj=self._object(stype,key)
                if obj.get_value('login_group')=='admin':
                    for f in form['spec']['fields']:
                        if f['name'] in ('name','access_rules','access_level','add_to_project'):f.update(read_only=True,reason='Встроенная группа admin защищена')
        # Secret values are not present even in the form's initial record.
        if form.get('record'):
            for f in form['spec']['fields']:
                if f.get('write_only'):form['record']['values'].pop(f['name'],None)
        return form

    def check_native_write(self,stype,values,key=None):
        from pyasm.common import Environment
        from pyasm.search import Search
        if stype in GLOBAL_EDIT and not Environment.get_security().is_admin():raise ApiError(403,'admin_only','Изменение системных записей доступно администратору')
        if stype=='sthpw/login':
            if key:
                obj=self._object(stype,key)
                if obj.get_value('login')=='admin' and ('password' in values or 'login' in values):raise ApiError(403,'admin_account','Встроенная учётная запись admin настраивается на сервере')
            else:
                login=values.get('login','')
                if not isinstance(login,str) or not login.strip() or login.lower() in ('admin','guest','root'):raise ApiError(400,'login','Укажите незарезервированный логин')
                q=Search(stype);q.set_show_retired(True);q.add_filter('login',login)
                if q.get_sobject():raise ApiError(409,'exists','Такой логин уже существует, включая архив')
                if not values.get('password'):raise ApiError(400,'password','Задайте пароль нового пользователя')
            confirm=values.get('password_reenter',values.get('password re-enter'))
            if confirm not in (None,'') and confirm!=values.get('password'):raise ApiError(400,'password_match','Пароли не совпадают')
        if stype=='sthpw/login_group':
            if key:
                obj=self._object(stype,key)
                if obj.get_value('login_group')=='admin' and set(values)&{'name','access_rules','access_level','add_to_project'}:raise ApiError(403,'admin_group','Встроенная группа admin защищена')
            elif not str(values.get('name') or '').strip():raise ApiError(400,'group_name','Укажите имя группы')
            if 'access_rules' in values and parse_xml(values['access_rules'] or '<rules/>').tag!='rules':raise ApiError(400,'rules_xml','Ожидается <rules>')
        if stype=='sthpw/db_resource' and key:
            obj=self._object(stype,key)
            q=Search('sthpw/project');q.add_filter('db_resource',obj.get_code());q.add_filters('code',['sthpw',self._project()])
            if q.get_count() and set(values)&{'host','port','vendor','login','password'}:
                raise ApiError(409,'active_resource','Этот ресурс обслуживает текущую БД. Измените его при остановленном сервере, чтобы не оборвать транзакцию.')


    def config_select_options(self,field,stype,key):
        from pyasm.search import Search
        from pyasm.common import Environment
        opts=field.get('display_options',{})
        parts=str(opts.get('query','')).split('|')
        if len(parts)!=3 or opts.get('query_filter'):
            raise ApiError(501,'select_query','SelectWdg query_filter/SQL expressions require their own adapter')
        related,value,label=parts
        self.require_type(related)
        columns=self._stub().get_column_info(related)
        method_label=label=='get_label()' and related=='sthpw/project_type'
        for name in (value,) if method_label else (value,label):
            if not safe_field(name) or name not in columns or not field_access(Environment.get_security(),self._project(),related,name,{})[0]:
                raise ApiError(403,'select_column','SelectWdg source column is not available')
        q=Search(related);q.add_order_by(value if method_label else label)
        limit=int(opts.get('query_limit') or 1000)
        if not 1<=limit<=1000:raise ApiError(413,'select_limit','SelectWdg supports at most 1000 choices; use a bounded query')
        q.set_limit(limit+1);objects=q.get_sobjects()
        if len(objects)>limit:raise ApiError(413,'select_limit','Too many choices for this SelectWdg; narrow the source configuration')
        return [{'value':json_safe(o.get_value(value)),'label':str(o.get_label() if method_label else o.get_value(label))} for o in objects]

    def global_cell_target(self,parent,key,field_name,reference):
        """Re-resolve the ORIGINAL visible column; the URL carries no executable options."""
        from pyasm.biz import Schema
        if parent['kind']!='table':raise ApiError(403,'cell_source','Column widget must originate from a table')
        obj=self._object(parent['search_type'],key)
        field=next((f for f in parent['spec']['fields'] if f['name']==field_name and f.get('widget_link')),None)
        if not field:raise ApiError(403,'cell_widget','This column does not define a supported subwidget')
        opts=dict(field.get('display_options') or {})
        target={'id':reference,'title':field['label'],'name':field_name,'attributes':{},'config_view':parent.get('config_view'),'view':opts.get('view') or 'table'}
        action=field.get('cell_action')
        if action in ('members','security'):
            if parent['search_type']!='sthpw/login_group':raise ApiError(403,'cell_group','Expected a group record')
            target.update(kind='group-membership' if action=='members' else 'security',
                          handler='tactic.ui.startup.UserAssignWdg' if action=='members' else 'tactic.ui.panel.SecurityManagerWdg',
                          options={'search_key':obj.get_search_key(),'native_fixed_group':obj.get_search_key()})
        elif action=='pipeline-editor':
            if parent['search_type'] != 'sthpw/pipeline':
                raise ApiError(403, 'cell_pipeline', 'Expected an original pipeline record')
            # Original ButtonElementWdg passes the selected search_key as INITIAL selection.
            target.update(kind='pipeline', handler='tactic.ui.tools.PipelineToolWdg',
                          title='Project Workflow ['+str(obj.get_code())+']',
                          options={'search_key':obj.get_search_key()})
        elif action=='schema-editor':
            if parent['search_type'] != 'sthpw/schema':
                raise ApiError(403, 'cell_schema', 'Expected an original schema record')
            # The source cbjs passes {}, i.e. current project Schema.get(), NOT a forged row owner.
            target.update(kind='schema', handler='tactic.ui.tools.SchemaToolWdg',
                          title='Project Schema', options={})
        elif action=='resource-project':
            # Original button opens EditWdg(sthpw/project, view=db_resource).
            # It registers the original project/database reference; it does not create/migrate a database.
            target.update(kind='form',handler='tactic.ui.panel.EditWdg',search_type='sthpw/project',view='db_resource',
                          options={'search_type':'sthpw/project','view':'db_resource','mode':'insert'})
        else:
            related=opts.get('search_type') or parent['search_type'];self.require_type(related)
            handler=opts.get('dynamic_class') or opts.get('class_name') or 'tactic.ui.panel.TableLayoutWdg'
            if handler not in ('tactic.ui.panel.TableLayoutWdg','tactic.ui.panel.FastTableLayoutWdg'):
                raise ApiError(501,'cell_handler','This HiddenRow dynamic_class is not implemented')
            options={k:v for k,v in opts.items() if k not in ('dynamic_class','class_name','search_key','parent_key','expression')}
            if opts.get('expression'):raise ApiError(501,'cell_expression','HiddenRow expression adapter is required')
            if related==parent['search_type']:options['native_fixed_key']=obj.get_search_key()
            else:
                if related not in Schema.get().get_related_search_types(parent['search_type']):raise ApiError(403,'cell_relation','Relation is missing from original Schema')
                options.update(native_parent_key=obj.get_search_key(),native_parent_type=parent['search_type'])
            options['show_insert']='false'
            target.update(kind='table',handler=handler,search_type=related,options=options)
        return target

    def global_cells(self,obj,row,spec):
        from pyasm.search import Search
        cells=row.setdefault('cells',{})
        parent=getattr(self,'active_target',{})
        for f in spec['fields']:
            if f.get('renderer')=='project-database':
                from pyasm.common import Environment
                try:exists=obj.database_exists()
                except Exception:exists=False  # Same legacy boundary; do not expose connection secrets.
                version=obj.get_value('last_version_update') or ''
                cells[f['name']]={'kind':'project-database','text':'Exists: '+str(bool(exists))+' · Version: '+version,
                    'exists':bool(exists),'version':version,'current':version >= Environment.get_release_version()}
            if f.get('renderer')=='xml' and f.get('storage'):
                cells[f['name']]={'kind':'xml','text':str(obj.get_value(f['name'],no_exception=True) or '')}
            if not f.get('widget_link') or not parent.get('id'):continue
            label=f['label']
            if f.get('renderer')=='group-members':
                cache=getattr(self,'_global_member_cache',None)
                group=obj.get_value('login_group')
                if cache is None:
                    q=Search('sthpw/login_in_group');q.add_filter('login_group',group);q.set_limit(1001)
                    members=[o.get_value('login') for o in q.get_sobjects()]
                else:members=cache.get(group,[])
                label=', '.join(members[:30]) or 'Назначить пользователей'
                if len(members)>30:label+=' … ('+str(len(members))+')'
                row['values'][f['name']]=', '.join(members)
            elif f.get('cell_action')=='members':label='Назначить пользователей'
            elif f.get('cell_action')=='security':label='Правила доступа'
            elif f.get('cell_action')=='pipeline-editor':label='Открыть pipeline'
            elif f.get('cell_action')=='schema-editor':label='Открыть схему проекта'
            cells[f['name']]={'kind':'widget','text':label,'target':cell_reference(parent['id'],obj.get_search_key(),f['name']),
                              'inline':not bool(f.get('cell_action')),'source_handler':f['handler']}
            if f.get('cell_action') in ('pipeline-editor','schema-editor'):
                # These exact stock callbacks use spt.tab.add_new, not load_popup.
                cells[f['name']]['open_mode']='tab'
        return row
