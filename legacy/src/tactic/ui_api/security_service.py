"""Original TACTIC security matrices and explicit group assignment (native 0.17).

The matrix edits a bounded, unambiguous subset of original XML via original
callbacks. It is NOT a replacement permission evaluator. Deny/custom rules and
legacy ambiguous scopes remain inspectable in the existing XML editor.
"""
import json
import re
from pathlib import Path
from .contracts import ApiError, revision
from .action_log import execute_traced
from tactic.core.config_model import ConfigModel, parse_xml

CATEGORIES = {
 'users': ('Group Assignment', 'UserSecurityCbk'),
 'project': ('Project Security', 'ProjectSecurityCbk'),
 'link': ('Link Security', 'LinkSecurityCbk'),
 'gear_menu': ('Gear Menu Security', 'GearMenuSecurityCbk'),
 'search_type': ('sType Security', 'SearchTypeSecurityCbk'),
 'process': ('Process Security', 'ProcessSecurityCbk'),
 'task': ('Task Security', 'TaskSecurityCbk'),
}
FIXED_CATEGORY = {name.replace('Cbk','Wdg'): key for key,(_,name) in CATEGORIES.items()}
SAFE_NAME = re.compile(r'^[A-Za-z0-9_./@:* -]{1,256}$')


def rule_match(category, row, project):
    if category == 'users': return {'group':'membership','login':row['value']}
    if category == 'project': return {'group': 'project', 'code': row['value']}
    if category == 'search_type': return {'group': 'search_type', 'code': row['value'], 'project': project}
    if category == 'link': return {'group': 'link', 'element': row['value'], 'project': project}
    if category == 'gear_menu': return {'group': 'gear_menu', 'submenu': row['submenu'], 'label': row['value'], 'project': project}
    if category == 'task': return {'group': 'process', 'process': row['value'], 'pipeline': row['pipeline']}
    return dict({'group': 'process', 'process': row['value'], 'project': project}, **({'pipeline':'*'} if row['value']=='*' else {}))


def matrix_cell(category, row, rules, project, level, group_project='', protected=False):
    """Explicit rules plus original SecurityCheckboxElementWdg automatic ticks.

    Read-only for a broader or ambiguous rule: original callbacks may otherwise
    remove/change a different project/pipeline rule while painting it as ours.
    """
    wanted = rule_match(category, row, project)
    exact = [r for r in rules if all(r.get(k) == v for k,v in wanted.items())]
    family = wanted['group']; field = 'process' if family == 'process' else 'code' if family in ('project','search_type') else 'element' if family == 'link' else 'label'
    related = [r for r in rules if r.get('group') == family and r.get(field) == wanted.get(field)]
    plain = all(r.get('access') == 'allow' and not set(r) - set(wanted) - {'access'} for r in exact)
    legacy_broad = []
    if category in ('search_type','process','task'):
        legacy_broad = [r for r in related if r not in exact]
    if category == 'gear_menu':
        # SecurityBuilder.remove_gear_menu matches label+project, not submenu.
        legacy_broad = [r for r in related if r.get('project') == project and r not in exact]
    auto = ((category == 'project' and level in ('min','low','medium','high') and group_project == row['value'])
            or (category in ('link','gear_menu') and level == 'high')
            or (category == 'search_type' and level in ('min','low','medium','high'))
            or (category in ('process','task') and level in ('low','medium','high')))
    wildcard_row = dict(row, value='*', pipeline='*', submenu='*')
    wildcard = rule_match(category,wildcard_row,project)
    broad = row['value'] != '*' and any(all(r.get(k)==v for k,v in wildcard.items()) and r.get('access')=='allow' for r in rules)
    reason = ''
    if protected: reason = 'Встроенная группа admin защищена'
    elif auto: reason = 'Задано исходным access_level: ' + level
    elif len(exact)>1 or not plain: reason = 'Deny, дубли или дополнительные условия: редактируйте исходный XML'
    elif legacy_broad: reason = 'Есть правило другой/старой области; требуется XML, чтобы не изменить его смысл'
    elif broad and not exact: reason = 'Задано общим правилом *'
    return {'checked': any(r.get('access')=='allow' for r in exact) or bool(auto) or bool(broad), 'explicit': any(r.get('access')=='allow' for r in exact),
            'inherited': bool(auto or (broad and not exact)), 'read_only': bool(reason), 'reason': reason,
            'rules': exact, 'other_scope_rules': legacy_broad}


class SecurityService:
    def _admin_screen(self, data, kinds):
        from pyasm.common import Environment
        if not Environment.get_security().is_admin():
            raise ApiError(403, 'admin_only', 'Нужны права администратора TACTIC')
        screen = self.open_target(data.get('target'))
        if screen['kind'] not in kinds:
            raise ApiError(403, 'admin_target', 'Действие не принадлежит этому настроенному виджету')
        return screen

    def _security_groups(self, category, options):
        from pyasm.search import Search
        from pyasm.security import LoginGroup, Login
        search = Search('sthpw/login_group'); search.add_order_by('login_group'); search.set_limit(1001)
        all_groups = search.get_sobjects()
        if len(all_groups)>1000: raise ApiError(413,'groups_limit','Более 1000 групп: сузьте установку/представление')
        in_project = {o.get_value('login_group') for o in LoginGroup.get_by_project()}
        ignore = set(str(options.get('ignore_groups') or '').split(','))
        fixed = options.get('native_fixed_group') or options.get('search_key')
        result=[]
        for obj in all_groups:
            name=obj.get_value('login_group'); code=obj.get_code(); key=obj.get_search_key()
            if fixed and key!=fixed: continue
            if options.get('filter') and name!=options['filter']: continue
            if category=='project': allowed=name in in_project or not obj.get_value('project_code')
            else: allowed=name in in_project and name not in ignore
            if not allowed: continue
            raw=obj.get_value('access_rules') or '<rules/>'
            rules=[dict(n.attrib) for n in parse_xml(raw).findall('rule')]
            result.append({'key':key,'name':name,'code':code,'label':obj.get_value('name') or name,'description':obj.get_value('description'),
                           'level':obj.get_value('access_level') or Login.get_default_security_level(),
                           'project':obj.get_value('project_code'), 'revision':revision({'xml':raw,'level':obj.get_value('access_level'),'project':obj.get_value('project_code')}),
                           'rules':rules})
        return result

    def _security_rows(self, category, options):
        from pyasm.search import Search
        from pyasm.biz import Project
        rows=[{'id':'*','value':'*','label':'Все / *','key':'','pipeline':'*','submenu':'*','is_all':True}]
        if category=='users':
            search=Search('sthpw/login');search.add_filters('code',['admin'],op='not in');search.add_order_by('login');search.set_limit(501)
            objs=search.get_sobjects();rows=[]
        elif category=='project':
            search=Search('sthpw/project'); search.add_filters('code',['sthpw','admin','unittest'],op='not in'); search.add_order_by('title'); search.set_limit(501)
            objs=search.get_sobjects()
        elif category=='search_type': objs=Project.get().get_search_types()
        elif category in ('process','task'):
            pipelines=Search('sthpw/pipeline');pipelines.add_filter('search_type','sthpw/task');pipelines.set_limit(2001)
            codes=[o.get_code() for o in pipelines.get_sobjects()]+['task']
            if len(codes)>2001:raise ApiError(413,'pipeline_limit','Слишком много task pipelines')
            search=Search('config/process');search.add_filters('pipeline_code',codes,op='in' if category=='task' else 'not in');search.add_order_by('pipeline_code');search.add_order_by('process');search.set_limit(501)
            objs=search.get_sobjects()
        elif category=='gear_menu':
            menus=json.loads((Path(__file__).parents[1]/'core/security_menu_names.json').read_text())
            for menu,info in sorted(menus.items(),key=lambda x:x[1]['order']):
                if menu=='ALL MENU ITEMS':continue
                for label in info['label']:rows.append({'id':revision([menu,label]),'value':label,'label':label,'submenu':menu,'key':'','is_all':False})
            return rows
        elif category=='link':
            from tactic.core.sidebar_config import SidebarConfig
            def collect(view,trail=()):
                if view in trail or len(trail)>=16:raise ApiError(409,'sidebar_cycle','Цикл/слишком глубокий sidebar')
                model=ConfigModel.from_tactic(SidebarConfig.get_config('SideBarWdg',view))
                for e in model.elements():
                    name=e['name'];rows.append({'id':revision(['link',view,name]),'value':name,'label':e['title'],'key':'','is_all':False,'section':view})
                    handler=e['handler']
                    if handler not in ('LinkWdg','SeparatorWdg','pyasm.widget.LinkWdg','pyasm.widget.SeparatorWdg'):
                        collect(e['options'].get('view') or name,trail+(view,))
                    if len(rows)>501:raise ApiError(413,'rows_limit','Более 500 ссылок: выберите меньший base view')
            collect(options.get('base') or 'project_view')
            # A link rule is by element name, not occurrence in a folder.
            unique={}
            for row in rows:unique.setdefault(row['value'],row)
            return list(unique.values())
        else:raise ApiError(400,'category','Неизвестная категория прав')
        if len(objs)>500:raise ApiError(413,'rows_limit','Матрица ограничена 500 строками')
        for obj in objs:
            value=obj.get_value('login') if category=='users' else obj.get_value('process') if category in ('process','task') else obj.get_value('search_type') if category=='search_type' else obj.get_code()
            row={'id':obj.get_search_key(),'key':obj.get_search_key(),'value':value,'label':obj.get_value('title',no_exception=True) or value,'is_all':False}
            if category in ('process','task'):row.update(pipeline=obj.get_value('pipeline_code'),label=value)
            rows.append(row)
        return rows

    def security_matrix(self, method, data):
        screen=self._admin_screen(data,('security','users','group-assignment'))
        options=screen.get('options',{})
        fixed=FIXED_CATEGORY.get(screen.get('handler','').rsplit('.',1)[-1])
        category=data.get('category') or fixed or 'project'
        if category not in CATEGORIES or (fixed and fixed!=category):raise ApiError(403,'category','Категория закреплена исходным виджетом')
        groups=self._security_groups(category,options)
        requested=data.get('groups')
        if isinstance(requested,str):
            try:requested=json.loads(requested) if requested.startswith('[') else [requested]
            except ValueError:raise ApiError(400,'groups','Некорректный список групп')
        if requested:
            if not isinstance(requested,list) or any(not isinstance(k,str) for k in requested) or len(requested)>40 or len(set(requested))!=len(requested) or set(requested)-{g['key'] for g in groups}:raise ApiError(403,'groups','Недопустимый набор групп')
            shown=[g for g in groups if g['key'] in requested]
        else:shown=groups[:12]
        rows=self._security_rows(category,options)
        project=self._project()
        memberships=[]
        if category=='users':
            from pyasm.search import Search
            q=Search('sthpw/login_in_group');q.add_filters('login_group',[g['name'] for g in shown]);q.set_limit(20001)
            memberships=q.get_sobjects() if shown else []
            if len(memberships)>20000:raise ApiError(413,'membership_limit','Более 20000 назначений')
        for row in rows:
            row['cells']={g['key']:matrix_cell(category,row,g['rules'],project,g['level'],g['project'],g['name']=='admin') for g in shown} if category!='users' else {}
            for g in shown:
                if category=='users':
                    matching=[m for m in memberships if m.get_value('login_group')==g['name'] and m.get_value('login')==row['value']]
                    reason='Дубли назначений: проверьте login_in_group' if len(matching)>1 else 'Существующий администратор защищён' if g['name']=='admin' and matching else ''
                    row['cells'][g['key']]={'checked':bool(matching),'explicit':bool(matching),'read_only':bool(reason),'reason':reason,'inherited':False,'rules':[]}
                cell=row['cells'][g['key']]
                if g['name'].startswith('_') or not SAFE_NAME.fullmatch(g['name']) or not SAFE_NAME.fullmatch(g['code']) or g['code'].startswith('_') or not SAFE_NAME.fullmatch(row['value']):
                    cell.update(read_only=True,reason='Имя требует расширенного XML-редактора')
        rev=revision({'category':category,'project':project,'groups':[(g['key'],g['revision']) for g in shown],
                      'rows':[{k:v for k,v in r.items() if k!='cells'} for r in rows],
                      'memberships':[(m.get_search_key(),m.get_value('login_group'),m.get_value('login')) for m in memberships]})
        if method=='GET':
            return {'category':category,'categories':[{'id':k,'label':v[0]} for k,v in CATEGORIES.items() if (k==fixed if fixed else k!='users')],
                    'groups':shown,'available_groups':[{k:v for k,v in g.items() if k!='rules'} for g in groups],
                    'rows':rows,'revision':rev,'can_write':self.allow_writes,'command':CATEGORIES[category][1],
                    'notice':'Явные исходные правила и отметки access_level; это не вычисление совокупных прав пользователя. Нестандартные области редактируются через XML.'}
        if method!='PATCH':raise ApiError(405,'method','Неподдержанный метод')
        if rev!=data.get('revision'):raise ApiError(409,'conflict','Группы, правила или строки матрицы изменились; обновите её')
        changes=data.get('changes')
        if not isinstance(changes,list) or not 1<=len(changes)<=500:raise ApiError(400,'changes','Нужно 1–500 изменённых ячеек')
        byrow={r['id']:r for r in rows};bygroup={g['key']:g for g in shown};seen=set();by_payload={}
        for change in changes:
            if not isinstance(change,dict):raise ApiError(400,'cell','Некорректная ячейка')
            rk,gk=change.get('row'),change.get('group');value=change.get('value')
            if rk not in byrow or gk not in bygroup or not isinstance(value,bool) or (rk,gk) in seen:raise ApiError(400,'cell','Некорректная или повторная ячейка')
            seen.add((rk,gk));row=byrow[rk];cell=row['cells'][gk]
            if cell['read_only']:raise ApiError(403,'read_only',cell['reason'])
            if value==cell['explicit']:continue
            by_payload.setdefault(rk,{})[bygroup[gk]['name'] if category=='users' else bygroup[gk]['code']]='true' if value else 'false'
        if not by_payload:return {'saved':False,'unchanged':True}
        def apply():
            # Recheck inside the existing transaction. Original commands mutate only now.
            again=self.security_matrix('GET',dict(data,changes=None))
            if again['revision']!=rev:raise ApiError(409,'conflict','Правила изменились перед сохранением')
            from tactic.core import admin_commands_017 as original
            keys=[];updates=[];extras=[]
            for rk,update in by_payload.items():
                row=byrow[rk];keys.append(row['key']);updates.append(update)
                extras.append({'is_all':row.get('is_all',False),'link':row['value'],'label':row['value'],'submenu':row.get('submenu','')})
            cls=getattr(original,CATEGORIES[category][1])
            execute_traced(cls(search_keys=keys,update_data=updates,extra_data=extras))
            return {'saved':True,'cells':sum(len(v) for v in by_payload.values()),'command':cls.__name__,
                    'notice':'Исходные access_rules сохранены. Существующим сессиям может потребоваться повторный вход.'}
        return self._write(apply)

    def user_groups(self,method,data):
        from pyasm.search import Search
        from pyasm.security import LoginInGroup
        screen=self._admin_screen(data,('users','group-assignment'))
        fixed=screen.get('options',{}).get('search_key')
        if fixed and data.get('key') and data['key']!=fixed:raise ApiError(403,'user_binding','Виджет привязан к другому пользователю')
        if not data.get('key') and not fixed:
            if method!='GET':raise ApiError(400,'key','Выберите пользователя')
            search=Search('sthpw/login');search.add_order_by('login');search.set_limit(2001);objs=search.get_sobjects()
            if len(objs)>2000:raise ApiError(413,'users_limit','Более 2000 пользователей; используйте пользовательский виджет выбранной записи')
            return {'users':[{'key':o.get_search_key(),'login':o.get_value('login'),'label':o.get_value('display_name') or o.get_value('login')} for o in objs]}
        user=self._object('sthpw/login',data.get('key') or fixed)
        search=Search('sthpw/login_group');search.add_order_by('login_group');search.set_limit(1001);groups=search.get_sobjects()
        if len(groups)>1000:raise ApiError(413,'groups_limit','Более 1000 групп')
        links=Search('sthpw/login_in_group');links.add_filter('login',user.get_code());links.set_limit(2001);members=links.get_sobjects()
        if len(members)>2000:raise ApiError(413,'membership_limit','Более 2000 назначений')
        names=[m.get_value('login_group') for m in members]
        if len(names)!=len(set(names)):raise ApiError(409,'duplicates','Есть дубли назначений: сначала проверьте login_in_group')
        rev=revision({'user':user.get_code(),'links':[(m.get_search_key(),m.get_value('login_group')) for m in members],
                      'groups':[(g.get_search_key(),g.get_value('login_group'),g.get_value('project_code')) for g in groups]})
        if method=='GET':return {'key':user.get_search_key(),'login':user.get_value('login'),'members':names,'revision':rev,'can_write':self.allow_writes,
                                'groups':[{'name':g.get_value('login_group'),'title':g.get_value('name') or g.get_value('description') or g.get_value('login_group'),'project':g.get_value('project_code')} for g in groups]}
        if method!='PATCH':raise ApiError(405,'method','Неподдержанный метод')
        wanted=data.get('members')
        if rev!=data.get('revision'):raise ApiError(409,'conflict','Назначения или группы изменились')
        known={g.get_value('login_group') for g in groups}
        if not isinstance(wanted,list) or any(not isinstance(x,str) for x in wanted) or len(wanted)>2000 or len(wanted)!=len(set(wanted)) or set(wanted)-known-set(names):raise ApiError(400,'members','Некорректный список групп')
        if 'admin' in names and 'admin' not in wanted:raise ApiError(403,'admin_group','Удаление существующего администратора запрещено этим экраном')
        def apply():
            if self.user_groups('GET',data)['revision']!=rev:raise ApiError(409,'conflict','Назначения изменились')
            from tactic.core.admin_commands_017 import GroupAssignCbk
            execute_traced(GroupAssignCbk(values={'search_key':[user.get_search_key()],'group_name':wanted,'new_group':[]}))
            # A fresh request uses the real original membership cache.
            try: LoginInGroup.clear_cache()
            except AttributeError: pass
            return {'saved':True,'command':'GroupAssignCbk','notice':'Группы сохранены. Для применения прав в существующих сессиях выполните повторный вход.'}
        return self._write(apply)
