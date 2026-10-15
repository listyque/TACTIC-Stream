"""TACTIC-native UI service. Sidebar and screens originate in original configs.

No fixed admin menu. No demo database. Existing Command/Transaction/Trigger and
WidgetConfigView resolution are used. Unsupported semantics fail explicitly.
"""
import json
import re
from pathlib import Path
from urllib.parse import parse_qs
from .tactic_backend import TacticBackend
from .action_log import execute_traced
from .contracts import ApiError, json_safe, revision, safe_field, safe_element, SYSTEM_FIELDS
from tactic.core.config_model import ConfigModel, ConfigSource, SidebarProjection, target_spec, parse_xml, view_node, reorder_view, patch_pipeline_positions
from tactic.core.field_policy import sidebar_allowed, field_access

PLAIN = {'', 'TextWdg', 'TextAreaWdg', 'SelectWdg', 'CheckboxWdg', 'DateTimeWdg', 'SimpleTableElementWdg', 'RawTableElementWdg', 'pyasm.widget.TextWdg', 'pyasm.widget.TextAreaWdg', 'pyasm.widget.SelectWdg',
         'pyasm.widget.CheckboxWdg', 'pyasm.widget.DateTimeWdg', 'tactic.ui.input.TextInputWdg',
         'tactic.ui.input.TextAreaInputWdg', 'tactic.ui.widget.CalendarInputWdg',
         'tactic.ui.common.SimpleTableElementWdg', 'tactic.ui.common.RawTableElementWdg',
         'tactic.ui.table.FormatElementWdg', 'pyasm.widget.SimpleTableElementWdg',
         'tactic.ui.table.SelectWdg', 'tactic.ui.input.SelectInputWdg', 'tactic.ui.input.ColorInputWdg',
         'tactic.ui.table.ColorWdg', 'tactic.ui.table.TaskStatusElementWdg', 'pyasm.widget.TaskStatusEditWdg'}
DATABASE_ACTIONS = {'NonEmptyAction', 'pyasm.command.NonEmptyAction', 'TaskDateAction', 'pyasm.command.TaskDateAction', '', 'DatabaseAction', 'pyasm.command.DatabaseAction', 'DefaultValueDatabaseAction', 'pyasm.command.DefaultValueDatabaseAction'}
DENY_EDIT_TYPES = {'sthpw/login', 'sthpw/login_group', 'sthpw/login_in_group', 'sthpw/ticket',
                   'sthpw/db_resource', 'sthpw/schema', 'sthpw/pipeline', 'config/process_state',
                   'sthpw/search_object', 'config/widget_config', 'config/custom_script', 'config/trigger', 'sthpw/trigger'}


class ConfigBackend(TacticBackend):
    def projects(self):
        from pyasm.biz import Project
        from pyasm.search import Search
        from pyasm.common import Environment
        security = Environment.get_security()
        result = []
        for obj in Search('sthpw/project').get_sobjects():
            code = obj.get_code()
            if code in ('sthpw', 'default') or obj.get_value('type') == 'resource':
                continue
            if security.is_admin() or security.check_access('project', [{'code': code}, {'code': '*'}], 'allow', default='deny'):
                result.append({'code': code, 'name': obj.get_value('title') or code})
        if security.is_admin() and not any(p['code'] == 'admin' for p in result):
            result.insert(0, {'code': 'admin', 'name': 'TACTIC Site Admin'})
        return result

    def catalog(self):
        from pyasm.biz import Project
        items = []
        for obj in Project.get().get_search_types(include_sthpw=True, include_config=True):
            code = obj.get_value('search_type')
            if code:
                items.append({'code': code, 'name': obj.get_value('title') or code})
        return {'types': items}

    def _tree(self):
        from tactic.core.sidebar_config import SidebarConfig
        from pyasm.common import Environment
        from pyasm.biz import Project
        security, project = Environment.get_security(), Project.get()
        login = Environment.get_user_name()
        loader = lambda v, personal: ConfigModel.from_tactic(SidebarConfig.get_config('SideBarWdg', v, personal=personal))
        projection = SidebarProjection(loader, lambda n: sidebar_allowed(security, project.get_code(), login, n), project.get_code(), login)
        sections = projection.build(SidebarConfig().get_views())
        # Use the ORIGINAL schema XML generator, including its folder hierarchy.
        # Its views refer to other views in the same XML, not the DB sidebar loader.
        if any(section['view'] == 'admin_views' for section in sections):
            xml = SidebarConfig().get_schema_xml()
            schema_loader = lambda v, personal: ConfigModel(v, [ConfigSource(xml, v, 'Schema-generated XML')])
            schema_projection = SidebarProjection(schema_loader, lambda n: sidebar_allowed(security, project.get_code(), login, n), project.get_code(), login)
            schema_sections = schema_projection.build(['schema'])
            sections.extend(schema_sections)
            projection.targets.update(schema_projection.targets)
        return sections, projection.targets

    def sidebar(self):
        from pyasm.biz import Project
        sections, targets = self._tree()
        return {'project': self._project(), 'title': Project.get().get_value('title') or self._project(),
                'sections': sections, 'source': 'config/widget_config + original XML',
                'targets': len(targets), 'unsupported_targets': sum(s['kind'] == 'unsupported' for s in targets.values())}

    def open_target(self, key):
        _, targets = self._tree()
        if key not in targets:
            raise ApiError(403, 'target_denied', 'Ссылка отсутствует в доступной конфигурации sidebar. Обновите меню.')
        spec = dict(targets[key])
        self.active_target = spec
        if spec['kind'] == 'table':
            spec['spec'] = self.view(spec['search_type'], spec['view'], spec['options'])
        return spec

    def require_type(self, stype):
        from pyasm.search import SearchType
        # HTTP dispatch derives this from a freshly authorized config target.
        if not isinstance(stype, str) or not re.fullmatch(r'[A-Za-z0-9_\-]+/[A-Za-z0-9_\-/]+', stype) or not SearchType.get(stype):
            raise ApiError(400, 'search_type', 'Некорректный SearchType')

    def _model(self, stype, view):
        from tactic.core.widget_config import WidgetConfigView
        return ConfigModel.from_tactic(WidgetConfigView.get_by_search_type(stype, view, use_cache=False))

    def _column_config_sources(self):
        from tactic.core.widget_config import WidgetConfigView
        configs = WidgetConfigView.get_by_type('column')
        return ConfigModel.from_tactic(WidgetConfigView(search_type=None, view='definition', configs=configs)).sources if configs else []

    def _config_code_model(self, code):
        from pyasm.search import Search
        from pyasm.common import Environment
        from tactic.core.widget_config import WidgetConfigView
        obj = Search.get_by_code('config/widget_config', code)
        if not obj:
            raise ApiError(404, 'config_code', 'Указанная конфигурация не найдена')
        owner = obj.get_value('login', no_exception=True)
        if owner and owner != Environment.get_user_name():
            raise ApiError(403, 'config_owner', 'Персональная конфигурация другого пользователя')
        return ConfigModel.from_tactic(WidgetConfigView(search_type=None, view=obj.get_value('view'), configs=[obj]))

    def _effective_view_options(self, stype, view, options):
        if options is not None:
            return options
        target = getattr(self, 'active_target', {}) or {}
        return target.get('options', {}) if target.get('search_type') == stype and target.get('view') == view else {}

    def _edit_base_model(self, stype, view, mode):
        from tactic.core.widget_containers import edit_base_model
        return edit_base_model(stype, view, mode)

    def _view_model(self, stype, view, options=None):
        cell = getattr(self, "_native_cell_model", None)
        if cell and cell[0] == stype and (options or {}).get("native_form"):
            return cell[1]
        from tactic.core.view_resolution import resolve_table
        options = self._effective_view_options(stype, view, options)
        base = self._model(stype, view)
        if options.get('native_form'):
            from tactic.core.widget_containers import edit_base_model, resolve_edit
            # Preserve the special legacy custom edit-view branch.
            if view not in ('edit','insert'):
                base = self._edit_base_model(stype, view, options.get('mode','edit'))
            return resolve_edit(base, options)
        if view in ('edit', 'insert'):
            return base
        # Inline/config_code branches in upstream do NOT append custom columns.
        columns = [] if options.get('config_xml') or options.get('config_code') else self._column_config_sources()
        try:
            return resolve_table(base, options, columns, self._config_code_model)
        except ValueError as exc:
            raise ApiError(400, 'table_config', str(exc)) from exc

    def view(self, stype, view='table', options=None):
        from pyasm.common import Environment
        from pyasm.search import SearchType
        self.require_type(stype)
        options = self._effective_view_options(stype, view, options)
        model = self._view_model(stype, view, options)
        columns = self._stub().get_column_info(stype)
        names = model.names()
        fields, diagnostics = [], []
        security = Environment.get_security()
        for name in names:
            el = model.describe(name)
            if not safe_element(name):
                continue
            visible, editable = field_access(security, self._project(), stype, name, el['attributes'])
            if not visible:
                continue
            column = columns.get(name) if safe_field(name) else None
            handler = el['handler']
            opts = el['options']
            if (view in ('edit', 'insert') or options.get('native_form')) and el['edit_handler']:
                handler, opts = el['edit_handler'], el['edit_options']
            storage = column is not None
            col = column if isinstance(column, dict) else {'data_type': str(column or '')}
            dbtype = str(col.get('data_type') or col.get('type') or '').lower()
            kind = 'text'
            if 'bool' in dbtype: kind = 'boolean'
            elif 'int' in dbtype: kind = 'integer'
            elif any(n in dbtype for n in ('numeric', 'float', 'decimal', 'double')): kind = 'number'
            elif dbtype == 'date': kind = 'date'
            elif 'timestamp' in dbtype or 'datetime' in dbtype: kind = 'datetime'
            elif 'json' in dbtype: kind = 'json'
            elif dbtype == 'text' or 'TextArea' in handler: kind = 'textarea'
            select = []
            # Explicit editor wins over SQL storage type (TEXT need not be a textarea).
            if (view in ('edit','insert') or options.get('native_form')) and handler.rsplit('.',1)[-1] in ('TextWdg','TextInputWdg') and kind=='textarea':kind='text'
            if opts.get('values'):
                values = opts['values'].split('|'); labels = opts.get('labels', '').split('|')
                select = [{'value': v, 'label': labels[i] if i < len(labels) and labels[i] else v} for i, v in enumerate(values)]
                kind = 'select'
            supported = storage and handler in PLAIN
            # Plain raw columns are readable even with a custom renderer, but must
            # NOT be presented as implemented widgets or editable form controls.
            reason = '' if supported else ('Вычисляемый виджет ещё не перенесён' if not storage else 'Показано исходное значение; специальный редактор не перенесён')
            if reason: diagnostics.append({'field': name, 'handler': handler, 'reason': reason})
            read_only = (opts.get('read_only') == 'true' or el['attributes'].get('edit') == 'false' or not self.allow_writes or not editable or not supported or name in SYSTEM_FIELDS or stype in DENY_EDIT_TYPES or el['action_handler'] not in DATABASE_ACTIONS)
            fields.append({'name': name, 'label': el['title'], 'kind': kind, 'storage': storage,
                           'read_only': read_only, 'supported': supported, 'reason': reason,
                           'sortable': storage and not bool(opts.get('order_by') or opts.get('order_by_where')),
                           'sort_reason': 'Пользовательский alter_order_by ещё не перенесён' if opts.get('order_by') or opts.get('order_by_where') else '',
                           'handler': handler, 'action': el['action_handler'], 'options': select,
                           'nullable': col.get('nullable', True), 'width': el['attributes'].get('width'),
                           'sources': el['sources'], 'display_options': opts,
                           'config_attributes': el['attributes'], 'display_handler': el['handler'],
                           'edit_handler': el['edit_handler'], 'action_options': el['action_options']})
        writable = self.allow_writes and stype not in DENY_EDIT_TYPES
        from tactic.core.view_resolution import table_options, configured_sort
        sort_error = None
        try: default_sort = configured_sort(options.get('order_by'), fields)
        except ValueError as exc: default_sort, sort_error = [], str(exc)
        return {'type': stype, 'view': view, 'resolved_view': model.view, 'fields': fields, 'revision': revision({'config':model.fingerprint(),'options':options,'fields':[(f['name'],f['kind'],f['read_only']) for f in fields]}),
                'table_options': table_options(options, model.attributes()), 'default_sort': default_sort, 'sort_error': sort_error,
                'attributes': model.attributes(), 'diagnostics': diagnostics,
                'capabilities': {'create': writable and options.get('show_insert') != 'false',
                                 'update': writable, 'retire': False}, 'views': [view]}

    def _defaults(self, search, stype, options):
        from pyasm.common import Environment
        from pyasm.search import SearchType
        if options.get('expression'):
            raise ApiError(501, 'expression_view', 'Этот view использует expression для выборки; адаптер выражений ещё не перенесён')
        raw = options.get('filter')
        if not raw: return
        from tactic.core.query_model import apply_saved
        try:
            rules = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(rules, list): raise ValueError('Ожидается список фильтров')
            security = Environment.get_security()
            for rule in rules:
                if not isinstance(rule, dict): raise ValueError('Некорректный фильтр')
                if rule.get('prefix', 'main_body') != 'main_body': continue
                enabled = rule.get('main_body_enabled')
                if enabled is not None and str(enabled).lower() not in ('on','true'): continue
                name = rule.get('main_body_column')
                if not safe_field(name) or not field_access(security, self._project(), stype, name, {})[0]:
                    raise ApiError(403, 'filter_field', 'Поле сохранённого фильтра недоступно')
            apply_saved(search, rules, login=Environment.get_user_name(), project=self._project())
        except (ValueError, TypeError) as exc:
            raise ApiError(400, 'config_filter', 'Сохранённый поиск: ' + str(exc)) from exc

    def _query_search(self, stype, spec, query):
        """Shared original search semantics for table and date-window projection."""
        from pyasm.search import Search
        search = Search(stype)
        self._defaults(search, stype, self.active_target.get('options', {}))
        from tactic.core.query_model import apply_tree
        apply_tree(search, query.get('where') or {'op': 'and', 'children': query['filters']}, spec['fields'])
        if query.get('parent_key'):
            raise ApiError(501, 'parent_filter', 'Выборка по произвольному parent_key пока не перенесена')
        if query.get('record_state','active') != 'active':
            from pyasm.search import SearchType
            column = SearchType.get(stype).get_retire_col()
            if not column or not SearchType.column_exists(stype,column):
                raise ApiError(400,'retire_column','Этот SearchType не поддерживает архив')
            search.set_show_retired(True)
            if query['record_state']=='retired': search.add_filter(column,'retired')
        return search

    def query(self, stype, spec, query):
        if spec.get('sort_error'):
            raise ApiError(501, 'configured_sort', spec['sort_error'])
        search = self._query_search(stype, spec, query)
        total = search.get_count()
        orders = query.get('sorts') or [query['sort']]
        for order in orders:
            if order['field'] is not None:
                search.add_order_by(order['field'], direction=order['direction'])
        # Stable page boundaries when multiple records share the selected value.
        from pyasm.search import SearchType
        if not any(order['field'] == 'id' for order in orders) and SearchType.column_exists(stype, 'id'):
            search.add_order_by('id', direction='asc')
        search.set_limit(query['limit']); search.set_offset(query['offset'])
        objects = search.get_sobjects()
        rows = self._serialize_many(objects, spec)
        summaries = self._page_summaries(objects, spec) if hasattr(self, '_page_summaries') else []
        return {'items': rows, 'summaries': summaries, 'total': total, 'offset': query['offset'], 'limit': query['limit'], 'has_more': query['offset'] + len(rows) < total}

    def _serialize_many(self, objects, spec):
        return [self._serialize(obj, spec) for obj in objects]

    def _raw_record(self, obj):
        raw = obj.get_sobject_dict()
        # The legacy dict converts SQL NULL to '' (or 0). Keep that display
        # behaviour in cell providers, not in the editable JSON value/revision.
        for name in list(raw):
            if not name.startswith('__') and obj.get_value(name, no_exception=True, auto_convert=False) is None:
                raw[name] = None
        return raw

    def _serialize(self, obj, spec):
        raw = self._raw_record(obj)
        raw['__search_key__'] = obj.get_search_key()
        row = self._row(raw, spec)
        row['revision'] = revision(raw)
        return row

    def _object(self, stype, key):
        from pyasm.search import SearchKey
        self.require_type(stype)
        if not isinstance(key, str) or key.split('?', 1)[0] != stype:
            raise ApiError(403, 'key_scope', 'SearchKey относится к другому типу')
        args = parse_qs(key.split('?', 1)[1] if '?' in key else '')
        if any(len(v) != 1 for v in args.values()) or args.get('project', [self._project()])[0] != self._project() or args.get('site', [self.site])[0] != self.site:
            raise ApiError(403, 'key_scope', 'Чужой проект/site в SearchKey')
        obj = SearchKey.get_by_search_key(key)
        if not obj: raise ApiError(404, 'not_found', 'Запись не найдена')
        return obj

    def _load(self, stype, key):
        obj = self._object(stype, key)
        raw = self._raw_record(obj); raw['__search_key__'] = obj.get_search_key(); return raw

    def record(self, stype, key, spec):
        return self._serialize(self._object(stype, key), spec)

    def form(self, stype, key=None):
        target = getattr(self, 'active_target', {})
        options = target.get('options', {}) if target.get('search_type') == stype else {}
        configured = options.get('edit_view' if key else 'insert_view')
        if target.get('kind') == 'form' and target.get('view'):
            configured = configured or target['view']
        from .contracts import view_name
        selected_view = view_name(configured or ('edit' if key else 'insert'))
        # Direct EditWdg retains its own inline config/ignore/default/options.
        direct = target.get('kind') == 'form'
        form_options = dict(options) if direct else {}
        mode = target.get('form_binding',{}).get('mode') or ('edit' if key else 'insert')
        form_options.update(native_form=True, mode=mode)
        spec = self.view(stype, selected_view, form_options)
        spec['mode'] = mode
        if options.get('show_insert') == 'false': spec['capabilities']['create'] = False
        defaults = {}
        if direct:
            from tactic.core.widget_containers import default_values, false
            ignored = options.get('ignore') or []
            if isinstance(ignored,str): ignored = ignored.split('|')
            disabled = options.get('disables') or {}
            if not isinstance(disabled,dict): raise ApiError(400,'disables','disables должен быть словарём')
            spec['fields'] = [f for f in spec['fields'] if f['name'] not in ignored]
            for field in spec['fields']:
                if field['label'] in disabled or mode == 'view': field['read_only'] = True
            if mode == 'view': spec['capabilities'] = dict(create=False, update=False, retire=False)
            elif mode == 'insert': spec['capabilities']['update'] = False
            else: spec['capabilities']['create'] = False
            if not key:
                defaults = default_values(options.get('default'))
                allowed = {f['name'] for f in spec['fields'] if not f['read_only']}
                if set(defaults) - allowed:
                    raise ApiError(501,'form_defaults','Default для скрытого/неперенесённого поля требует отдельного action adapter')
        return {'spec': spec, 'defaults': defaults, 'record': self.record(stype, key, spec) if key else None}

    def create(self, stype, values, spec):
        from pyasm.search import SearchType
        from tactic.core.native_edit import NativeEditCmd
        def apply():
            if hasattr(self, 'check_native_write'):self.check_native_write(stype,values)
            obj = SearchType.create(stype)
            target = getattr(self, 'active_target', {})
            inline = target.get('options',{}).get('config_xml') if target.get('kind') == 'form' else None
            if inline:
                from tactic.core.view_resolution import inline_xml
                inline = inline_xml(inline)
            cmd = NativeEditCmd(sobject=obj, view=spec['view'], data=values, input_prefix='__NONE__', config_xml=inline)
            execute_traced(cmd)
            return self._serialize(cmd.get_sobject(), spec)
        return self._write(apply)

    def update(self, stype, key, values, expected, spec):
        from tactic.core.native_edit import NativeEditCmd
        def apply():
            if hasattr(self, 'check_native_write'):self.check_native_write(stype,values,key)
            obj = self._object(stype, key)
            if self._serialize(obj, spec)['revision'] != expected:
                raise ApiError(409, 'conflict', 'Запись изменена другим пользователем. Перечитайте её.')
            target = getattr(self, 'active_target', {})
            inline = target.get('options',{}).get('config_xml') if target.get('kind') == 'form' else None
            if inline:
                from tactic.core.view_resolution import inline_xml
                inline = inline_xml(inline)
            cmd = NativeEditCmd(sobject=obj, view=spec['view'], data=values, input_prefix='__NONE__', config_xml=inline)
            execute_traced(cmd)
            return self._serialize(cmd.get_sobject(), spec)
        return self._write(apply)

    def config_operation(self, method, path, data):
        from pyasm.common import Environment
        from pyasm.search import Search, SearchType
        from pyasm.biz import Project, Schema
        if not Environment.get_security().is_admin():
            raise ApiError(403, 'admin_only', 'Административная операция')
        if path == '/search-types' and method == 'GET':
            catalog = self.catalog()
            _, targets = self._tree()
            for item in catalog['types']:
                item['target'] = next((key for key, spec in targets.items() if spec.get('search_type') == item['code']), None)
            return catalog
        if path == '/memberships':
            from pyasm.security import LoginInGroup
            from tactic.core.security_commands import UserAssignCbk
            opened = self.open_target(data.get('target'))
            if opened['kind'] != 'group-membership':
                raise ApiError(403, 'target_denied', 'Этот view не является назначением групп')
            if method == 'GET' and not data.get('key'):
                groups = Search('sthpw/login_group'); groups.add_order_by('login_group'); groups.set_limit(1000)
                return {'items': [{'key': o.get_search_key(), 'name': o.get_value('login_group'),
                                  'description': o.get_value('description')} for o in groups.get_sobjects()], 'limit':1000}
            fixed=opened.get('options',{}).get('native_fixed_group')
            if fixed and fixed!=data.get('key'):raise ApiError(403,'group_binding','Этот виджет привязан к другой группе')
            group = self._object('sthpw/login_group', data.get('key'))
            def members():
                rows = LoginInGroup.get_by_group_name(group.get_value('login_group'))
                return sorted(set(o.get_value('login') for o in rows))
            if method == 'GET':
                users = Search('sthpw/login'); users.add_order_by('login'); users.set_limit(5000)
                selected = members()
                return {'key':group.get_search_key(), 'group':group.get_value('login_group'),
                        'users':[{'login':o.get_value('login'),'name':o.get_value('display_name') or o.get_value('login')} for o in users.get_sobjects()],
                        'members':selected,'revision':revision(selected),'can_write':self.allow_writes,'limit':5000}
            if method == 'POST':
                wanted = data.get('members')
                if not isinstance(wanted,list) or len(wanted)>5000 or any(not isinstance(x,str) or not x or len(x)>200 for x in wanted) or len(set(wanted))!=len(wanted):
                    raise ApiError(400,'members','Некорректный список пользователей')
                def apply():
                    current = members()
                    if revision(current)!=data.get('revision'):raise ApiError(409,'conflict','Состав группы изменён')
                    if group.get_value('login_group')=='admin' and set(current)-set(wanted):
                        raise ApiError(403,'admin_removal','Удаление существующих администраторов через этот экран запрещено')
                    users=Search('sthpw/login'); users.add_filters('login',wanted)
                    found={o.get_value('login') for o in users.get_sobjects()} if wanted else set()
                    if set(wanted)!=found:raise ApiError(400,'members','Один из пользователей не существует')
                    cmd=UserAssignCbk(values={'search_key':[group.get_search_key()],'login_name':wanted});execute_traced(cmd)
                    LoginInGroup.clear_cache()
                    return {'saved':True,'revision':revision(members())}
                return self._write(apply)
            raise ApiError(405,'method','Метод не поддерживается')
        if path == '/search-types' and method == 'POST':
            from tactic.core.schema_commands import SearchTypeCreatorCmd
            if self._project() in ('admin','sthpw','default'):
                raise ApiError(403,'project_required','Выберите рабочий проект, не глобальную администрацию')
            name=data.get('name'); title=data.get('title'); description=data.get('description','')
            if not isinstance(name,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,49}',name):
                raise ApiError(400,'name','Имя SearchType: строчные латинские буквы, цифры и подчёркивания')
            if not isinstance(title,str) or not title.strip() or len(title)>200 or not isinstance(description,str) or len(description)>10000:
                raise ApiError(400,'title','Некорректное название или описание')
            columns=data.get('columns',[])
            if not isinstance(columns,list) or len(columns)>50:raise ApiError(400,'columns','Не более 50 дополнительных полей')
            names=[]; types=[]
            for column in columns:
                if not isinstance(column,dict):raise ApiError(400,'column','Некорректное поле')
                n=column.get('name'); typ=column.get('type')
                if not isinstance(n,str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,49}',n) or n in names or n in ('id','code','name','description','keywords','login','timestamp','data','s_status','pipeline_code','relative_dir'):
                    raise ApiError(400,'column','Некорректное, повторное или служебное имя поля')
                if typ not in ('varchar','text','integer','float','boolean','timestamp','date','json'):
                    raise ApiError(400,'column_type','Недопустимый тип поля')
                names.append(n);types.append(typ)
            def apply():
                # The upstream project-specific creator can re-use existing types.
                # This endpoint is create-only: never overwrite existing views.
                existing=Search(SearchType.SEARCH_TYPE)
                existing.add_filter('search_type',self._project()+'/'+name)
                if existing.get_sobject():
                    raise ApiError(409,'type_exists','SearchType уже зарегистрирован')
                cmd=SearchTypeCreatorCmd(database=self._project(),namespace=self._project(),schema='public',
                    search_type_name=name,asset_title=title.strip(),asset_description=description,project_specific='on',
                    column_name=names,data_type=types,format=['']*len(names),
                    sobject_pipeline='on' if data.get('pipeline') is True else '',
                    sobject_preview='on' if data.get('preview') is True else '')
                if cmd.table_exists():
                    raise ApiError(409,'table_exists','Таблица уже существует; создание не должно её переиспользовать')
                execute_traced(cmd)
                return {'created':True,'search_type':cmd.get_search_type_obj().get_value('search_type')}
            return self._write(apply)
        if path == '/configs' and method == 'GET':
            search = Search('config/widget_config')
            if data.get('search_type'): search.add_filter('search_type', data['search_type'])
            search.add_order_by('view'); search.set_limit(1000)
            return {'items': [{'key': x.get_search_key(), 'view': x.get_value('view'), 'search_type': x.get_value('search_type'),
                               'login': x.get_value('login'), 'category': x.get_value('category', no_exception=True)} for x in search.get_sobjects()], 'limit': 1000}
        if path == '/config' and method == 'GET':
            if data.get('key'):
                obj = self._object('config/widget_config', data['key'])
                xml = obj.get_value('config')
                return {'key': obj.get_search_key(), 'view': obj.get_value('view'), 'search_type': obj.get_value('search_type'),
                        'login': obj.get_value('login'), 'xml': xml, 'revision': revision(xml), 'editable': self.allow_writes}
            from tactic.core.sidebar_config import SidebarConfig
            v = data.get('view') or 'project_view'
            model = ConfigModel.from_tactic(SidebarConfig.get_config('SideBarWdg', v, personal=v.startswith('my_view_')))
            # Return all ORIGINAL layers; do not flatten them on save.
            return {'view': v, 'layers': [{'view': s.view, 'origin': s.origin, 'xml': s.text} for s in model.sources],
                    'elements': model.elements(), 'revision': model.fingerprint(), 'editable': False}
        if path == '/config' and method == 'POST':
            text = data.get('xml'); root = parse_xml(text)
            view = data.get('view'); stype = data.get('search_type'); login = data.get('login') or None
            if not isinstance(view, str) or not re.fullmatch(r'[A-Za-z0-9_@.:-]{1,200}',view):
                raise ApiError(400,'view','Некорректный view')
            if not isinstance(stype,str) or not re.fullmatch(r'[A-Za-z0-9_/.-]{1,200}',stype):
                raise ApiError(400,'type','Некорректный search_type')
            if login is not None and (not isinstance(login,str) or len(login)>120):
                raise ApiError(400,'login','Некорректный login')
            if root.tag!='config' or view_node(root,view) is None:
                raise ApiError(400,'xml','XML должен содержать выбранный view внутри config')
            def apply():
                search=Search('config/widget_config'); search.add_filter('search_type',stype);search.add_filter('view',view);search.add_filter('login',login)
                if search.get_sobject(): raise ApiError(409,'exists','Такой view уже существует. Откройте его для редактирования.')
                obj=SearchType.create('config/widget_config');obj.set_value('search_type',stype);obj.set_value('view',view);obj.set_value('login',login)
                if stype=='SideBarWdg':obj.set_value('category','SideBarWdg')
                obj.set_value('config',text);obj.commit()
                return {'saved':True,'key':obj.get_search_key(),'revision':revision(text)}
            return self._write(apply)
        if path == '/config' and method == 'PATCH':
            text = data.get('xml'); root = parse_xml(text)
            if root.tag != 'config': raise ApiError(400, 'xml', 'Корень должен быть <config>')
            def apply():
                obj = self._object('config/widget_config', data.get('key'))
                if revision(obj.get_value('config')) != data.get('revision'):
                    raise ApiError(409, 'conflict', 'Конфигурация уже изменена')
                if view_node(root, obj.get_value('view')) is None:
                    raise ApiError(400, 'view_missing', 'Нельзя удалить основной view этой записи')
                obj.set_value('config', text); obj.commit()
                return {'saved': True, 'key': obj.get_search_key(), 'revision': revision(text)}
            return self._write(apply)
        if path == '/sidebar-order' and method == 'POST':
            from tactic.core.sidebar_config import SidebarConfig
            from tactic.core.config_model import xml_text
            import xml.etree.ElementTree as ET
            v = data.get('view') or 'project_view'
            model = ConfigModel.from_tactic(SidebarConfig.get_config('SideBarWdg', v, personal=v.startswith('my_view_')))
            if model.fingerprint() != data.get('revision'):
                raise ApiError(409, 'conflict', 'Sidebar изменился. Обновите конфигурацию.')
            source = next((s for s in model.sources if s.view not in ('definition','edit_definition','default_definition') and s.node is not None), None)
            if source is None: raise ApiError(404, 'view_missing', 'View не найден')
            updated = reorder_view(source.text, v, data.get('order'))
            # Only the requested view is written; inherited definitions stay inherited.
            root = parse_xml(updated); newroot = ET.Element('config'); newroot.append(view_node(root, v))
            xml = xml_text(newroot)
            def apply():
                search = Search('config/widget_config'); search.add_filter('search_type','SideBarWdg'); search.add_filter('view', v)
                search.add_order_by('priority desc')
                obj = search.get_sobject()
                if obj:
                    # Preserve ALL other views and XML content in an existing DB row.
                    xml_out = reorder_view(obj.get_value('config'), v, data.get('order'))
                else:
                    obj = SearchType.create('config/widget_config'); obj.set_value('search_type','SideBarWdg'); obj.set_value('category','SideBarWdg'); obj.set_value('view',v)
                    if v.startswith('my_view_'): obj.set_value('login', Environment.get_user_name())
                    xml_out = xml
                obj.set_value('config',xml_out); obj.commit()
                return {'saved': True, 'key': obj.get_search_key()}
            return self._write(apply)
        if path == '/graph' and method == 'GET':
            kind = data.get('kind')
            stype, column = ('sthpw/schema','schema') if kind == 'schema' else ('sthpw/pipeline','pipeline')
            if not data.get('key'):
                search = Search(stype); search.add_order_by('code'); search.set_limit(500)
                return {'items': [{'key': x.get_search_key(), 'code': x.get_code(), 'name': x.get_value('name', no_exception=True) or x.get_code()} for x in search.get_sobjects()]}
            obj = self._object(stype, data['key']); xml = obj.get_value(column)
            return {'key': obj.get_search_key(), 'xml': xml, 'revision': revision(xml), 'code': obj.get_code(),
                    'can_save_positions': kind != 'schema' and self.allow_writes}
        if path == '/pipeline-positions' and method == 'POST':
            from tactic.core.pipeline_commands import PipelineSaveCbk
            def apply():
                obj = self._object('sthpw/pipeline', data.get('key'))
                original = obj.get_value('pipeline')
                if revision(original) != data.get('revision'): raise ApiError(409,'conflict','Pipeline изменён')
                xml = patch_pipeline_positions(original, data.get('positions'))
                # Use original save semantics (process synchronization, dependencies,
                # cache invalidation, configured triggers), not just raw SQL/XML update.
                cmd = PipelineSaveCbk(search_key=obj.get_search_key(), pipeline=xml,
                                      color=obj.get_value('color'), pipeline_data=obj.get_json_value('data', default={}),
                                      xml_is_escaped=True)
                execute_traced(cmd)
                return {'saved': True}
            return self._write(apply)
        raise ApiError(405, 'operation', 'Операция не поддерживается')
