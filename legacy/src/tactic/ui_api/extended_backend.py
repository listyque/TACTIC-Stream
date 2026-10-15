"""Version 0.5 source-fork backend: native semantic providers and original config routes."""
import json
import re
from .design_service import DesignService
from .security_service import SecurityService
from .search_type_service import SearchTypeService
from .sidebar_service import SidebarService
from .admin_workspace import AdminWorkspace
from .thumbnail_service import ThumbnailService
from .table_edit_service import TableEditService
from .cell_value_service import CellValueService, LOGIN_DISPLAY, STATUS_DISPLAY
from .global_admin_service import GlobalAdminService
from .widget_service import WidgetService
from .menu_service import MenuService
from .script_service import ScriptService, script_permission
from .csv_service import CsvService
from .column_service import ColumnService, EXPRESSION
from .config_backend import ConfigBackend, DATABASE_ACTIONS, DENY_EDIT_TYPES
from .graph_service import GraphService
from .view_service import ViewService
from .record_service import RecordService, decode_related_id
from .admin_service import AdminService
from .project_service import ProjectService
from .ui_state_service import UiStateService
from .task_service import TaskService
from .work_hour_service import WorkHourService, HOUR_HANDLERS
from .relationship_service import RelationshipService
from .history_service import HistoryService
from .message_service import MessageService, RECIPIENT_HANDLERS, WIKI_HANDLERS
from .timeline_service import TimelineService
from .upload_service import UploadService
from .version_service import VersionService
from .collection_service import CollectionService
from .contracts import ApiError, SYSTEM_FIELDS, json_safe
from tactic.core.field_policy import field_access

STATUS = {'tactic.ui.widget.misc_input_wdg.TaskStatusElementWdg', 'tactic.ui.widget.TaskStatusElementWdg', 'tactic.ui.table.TaskStatusElementWdg',
          'pyasm.widget.TaskStatusEditWdg', 'TaskStatusEditWdg', 'TaskStatusElementWdg',
          'tactic.ui.widget.TaskStatusSelectWdg', 'TaskStatusSelectWdg'}
LOGIN = {'tactic.ui.input.process_group_select_wdg.LoginTableElementWdg', 'LoginTableElementWdg', 'tactic.ui.input.LoginTableElementWdg', 'tactic.ui.input.ProcessGroupSelectWdg',
         'pyasm.widget.LoginSelectWdg', 'LoginSelectWdg'}
PROCESS = {'tactic.ui.input.ProcessElementWdg', 'tactic.ui.table.ProcessElementWdg',
           'pyasm.widget.ProcessSelectWdg', 'ProcessSelectWdg', 'tactic.ui.input.ProcessInputWdg', 'ProcessInputWdg'}
SUBCONTEXT = {'tactic.ui.input.SubContextInputWdg', 'SubContextInputWdg'}
SUBCONTEXT_ACTIONS = {'tactic.ui.input.SubContextAction', 'tactic.core.context_actions.SubContextAction', 'SubContextAction'}
TASK_LOOKUPS = {
 'milestone_code': "@GET(sthpw/milestone['project_code',$PROJECT]['project_code','is','NULL']['or'].code)",
 'pipeline_code': "@GET(sthpw/pipeline['search_type','sthpw/task']['project_code','EQ',$PROJECT]['project_code','is','NULL']['or'].code)",
}
GANTT = {'tactic.ui.table.GanttElementWdg', 'pyasm.widget.GanttWdg', 'GanttWdg'}


class ExtendedBackend(DesignService, SecurityService, SearchTypeService, SidebarService, AdminWorkspace, UiStateService, ProjectService, ThumbnailService, TableEditService, CellValueService, GlobalAdminService, WidgetService, MenuService, ScriptService, CsvService, ColumnService, CollectionService, VersionService, UploadService, TimelineService, MessageService, WorkHourService, TaskService, RelationshipService, HistoryService, GraphService, ViewService, RecordService, AdminService, ConfigBackend):
    def open_target(self, key):
        if not isinstance(key, str) or len(key) > 4000 or key.count('/~') > 8:
            raise ApiError(400, 'target', 'Некорректная или слишком глубокая ссылка')
        if '/~design/' in key and key.rfind('/~design/') == key.rfind('/~'):
            root,part=key.rsplit('/~design/',1)
            target=self.design_derived_target(self.open_target(root),part,key)
        elif '/~layout/' in key and key.rfind('/~layout/') == key.rfind('/~'):
            root,index=key.rsplit('/~layout/',1); parent=self.open_target(root)
            if parent['kind']!='custom-layout' or not index.isdecimal():raise ApiError(403,'layout_child','Недоступный виджет layout')
            children=parent['layout']['children'];n=int(index)
            if not 0<=n<len(children) or children[n].get('handler')=='Hidden by configuration':raise ApiError(403,'layout_child','Скрытый/отсутствующий виджет')
            target=children[n]
        elif '/~admin/' in key and key.rfind('/~admin/') == key.rfind('/~'):
            root,part=key.rsplit('/~admin/',1)
            target=self.admin_derived_target(self.open_target(root),part,key)
        elif '/~cell/' in key and key.rfind('/~cell/') == key.rfind('/~'):
            root,token=key.rsplit('/~cell/',1)
            parent=self.open_target(root)
            record_key,field_name=decode_related_id(token)
            target=self.global_cell_target(parent,record_key,field_name,key)
        elif key.endswith('/~scripts-table'):
            parent = self.open_target(key[:-len('/~scripts-table')])
            if parent['kind'] != 'script-editor':
                raise ApiError(403, 'script_target', 'Таблица скриптов должна исходить из ScriptEditorWdg')
            script_permission()
            # Exact management view/options used by original shelf_wdg.py.
            target = {'id': key, 'kind': 'table', 'handler': 'tactic.ui.panel.ViewPanelWdg',
                      'search_type': 'config/custom_script', 'view': 'table', 'title': 'Saved Scripts',
                      'config_view': parent.get('config_view'), 'attributes': {},
                      'options': {'show_shelf': 'false', 'element_names': 'folder,title,description,language'}}
        elif key.endswith('/~collection-items'):
            parent = self.open_target(key[:-len('/~collection-items')])
            if parent['kind'] != 'collections' or parent.get('options',{}).get('collection_key'):
                raise ApiError(403,'collection_target','Не определена общая таблица коллекций')
            target = dict(parent, id=key, kind='table', handler='tactic.ui.panel.ViewPanelWdg',
                          title=parent.get('title','Коллекции')+' · объекты', view=parent.get('view') or 'table')
        elif '/~tab/' in key and ('/~related/' not in key or key.rfind('/~tab/') > key.rfind('/~related/')):
            root, index = key.rsplit('/~tab/', 1)
            parent = self.open_target(root)
            if parent['kind'] != 'tabs' or not index.isdecimal():
                raise ApiError(403, 'tab', 'Вкладка не определена исходной конфигурацией')
            children = self.tab_children(parent)
            target = next((child for child in children if child['id'] == key), None)
            if target is None: raise ApiError(403, 'tab', 'Вкладка отсутствует или скрыта в исходной конфигурации')
        elif '/~related/' in key:
            root, token = key.rsplit('/~related/', 1)
            parent = self.open_target(root)
            if parent['kind'] not in ('table', 'form'):
                raise ApiError(403, 'related', 'Связь должна начинаться от таблицы')
            parent_key, related = decode_related_id(token)
            obj = self._object(parent['search_type'], parent_key)
            from pyasm.biz import Schema
            if related not in Schema.get().get_related_search_types(parent['search_type']):
                raise ApiError(403, 'related', 'Связь отсутствует в схеме')
            attrs = Schema.get().get_relationship_attrs(related, parent['search_type'])
            if not attrs or attrs.get('disabled') in (True, 'true'):
                raise ApiError(403, 'related', 'Связь отключена')
            target = {'id': key, 'kind': 'table', 'handler': 'tactic.ui.panel.ViewPanelWdg',
                      'name': related, 'title': related + ' ← ' + (obj.get_value('name', no_exception=True) or obj.get_code()),
                      'search_type': related, 'view': 'table', 'config_view': 'Schema relationship',
                      'attributes': {}, 'options': {'native_parent_key': parent_key,
                                                   'native_parent_type': parent['search_type'], 'show_insert': 'false'}}
        else:
            target = super().open_target(key)
        if target['kind'] == 'script-editor' or target.get('search_type') == 'config/custom_script':
            script_permission()
        self.active_target = target
        if target['kind'] == 'form':
            self.bind_form_target(target)
            target['spec'] = self.form(target['search_type'], target['form_binding']['key'])['spec']
        elif target['kind'] == 'table':
            target['spec'] = self.view(target['search_type'], target['view'], target['options'])
        elif target['kind'] == 'tabs':
            target['children'] = self.tab_children(target)
        elif target['kind'] == 'custom-layout':
            target['layout'] = self.layout_screen(target)
        from .action_log import resolved
        resolved(target)
        return target

    def config_operation(self, method, path, data):
        if path in ("/design-catalog", "/layout-document", "/layout-preview", "/view-document"): return self.design_operation(method,path,data)
        if path == "/security-matrix": return self.security_matrix(method,data)
        if path == "/user-groups": return self.user_groups(method,data)
        if path == "/stype-editor": return self.stype_editor(method,data)
        if path == '/stype-dependencies': return self.stype_dependencies(method,data)
        if path == '/stype-import': return self.stype_import(method,data)
        if path == "/sidebar-editor": return self.sidebar_editor(method,data)
        if path == '/ui-state':
            return self.ui_state_operation(method,data)
        if path in ('/project-create','/project-preflight'):
            return self.project_operation(method,path,data)
        if path in ('/cell-editor','/table-fill-preview','/table-changes'):
            return self.table_edit_operation(method,path,data)
        if path in ('/system-config','/license'):
            return self.global_operation(method,path,data)
        if path == '/context-menu' and method == 'GET': return self.context_menu(data)
        if path == '/embedded-form': return self.embedded_form(method, data)
        if path in ('/scripts', '/script', '/script-check', '/script-diff', '/script-run'): return self.script_operation(method, path, data)
        if path in ('/collections','/collection-members','/collection-change'): return self.collection_operation(method,path,data)
        if path in ('/file-versions','/snapshot-current'): return self.version_operation(method,path,data)
        if path == '/task-hours': return self.work_hour_operation(method, data)
        if path == '/form-preview' and method == 'POST':
            return self.form_preview(data)
        if path in ('/tasks','/task-generate','/task-form','/task-change', '/task-form-preview'):
            return self.task_operation(method,path,data)
        if path in ('/relationship','/relation-candidates'):
            return self.relationship_operation(method,path,data)
        if path in ('/history','/record-state'):
            return self.history_operation(method,path,data)
        if path == '/graph': return self.graph_operation(method, data)
        if path == '/view-config': return self.view_operation(method, data)
        if path == '/saved-view' and method == 'POST': return self.saved_view(data)
        if path in ('/users', '/security', '/project-create', '/system'):
            return self.admin_operation(method, path, data)
        if path in ('/relations', '/notes', '/file', '/bulk-records'):
            return self.record_operation(method, path, data)
        return super().config_operation(method, path, data)

    def view(self, stype, view='table', options=None):
        from pyasm.common import Environment
        options = self._effective_view_options(stype, view, options)
        spec = super().view(stype, view, options)
        spec['collection_supported'] = not stype.startswith(('sthpw/','config/')) and '_is_collection' in self._stub().get_column_info(stype)
        model = self._view_model(stype, view, options)
        security = Environment.get_security()
        for field in spec['fields']:
            el = model.describe(field['name']); handler = field['handler']
            field['hidden'] = el['attributes'].get('is_visible') in (False, 'false')
            opts = el['edit_options'] if (view in ('edit', 'insert') or (options or {}).get('native_form')) and el['edit_handler'] else el['options']
            family = 'status' if handler in STATUS else 'login' if handler in LOGIN else 'process' if handler in PROCESS else None
            if family and field['storage']:
                field.update(kind='select', provider=family, supported=True, reason='', options=[])
                _, editable = field_access(security, self._project(), stype, field['name'], el['attributes'])
                field['read_only'] = (opts.get('read_only') in (True, 'true') or el['attributes'].get('edit') in (False, 'false') or not self.allow_writes or not editable or stype in DENY_EDIT_TYPES or
                                      field['name'] in SYSTEM_FIELDS or field['action'] not in DATABASE_ACTIONS)
                field['provider_options'] = opts
                # Table values remain raw codes; the form resolves choices from
                # the actual row's pipeline/group, not a global invented list.
            if handler in SUBCONTEXT and field['action'] in SUBCONTEXT_ACTIONS and stype == 'sthpw/task':
                _, editable = field_access(security, self._project(), stype, field['name'], el['attributes'])
                context_visible, context_editable = field_access(security, self._project(), stype, 'context', model.describe('context')['attributes'])
                if context_visible:
                    field.update(kind='text', provider='subcontext', supported=True, reason='', nullable=False,
                                 read_only=(not self.allow_writes or not editable or not context_editable or
                                            opts.get('read_only') in (True, 'true') or el['attributes'].get('edit') in (False, 'false')))
            # Resolve only the two exact queries shipped in task-conf.xml.
            # Other expressions remain explicit unsupported metadata, never free input.
            if opts.get('values_expr') and field.get('provider') is None:
                expr = re.sub(r'\s+', '', opts['values_expr'])
                if stype == 'sthpw/task' and expr == TASK_LOOKUPS.get(field['name']) and field['storage']:
                    _, editable = field_access(security, self._project(), stype, field['name'], el['attributes'])
                    field.update(kind='select', provider='task-lookup', provider_options={'field': field['name']},
                                 supported=True, reason='', options=[],
                                 read_only=(not self.allow_writes or not editable or field['action'] not in DATABASE_ACTIONS or
                                            opts.get('read_only') in (True, 'true') or el['attributes'].get('edit') in (False, 'false')))
                else:
                    field.update(read_only=True, reason='Динамические values_expr пока не разрешены этим провайдером')
            field['choice_refresh'] = (stype == 'sthpw/task' and field['name'] in ('process', 'pipeline_code', 'context') and
                                       field.get('supported') and not field['read_only'])
            if handler in HOUR_HANDLERS and stype == 'sthpw/task':
                field.update(renderer='work-hours',supported=True,reason='',read_only=True)
            if handler in GANTT:
                try: bars = json.loads(opts.get('options') or '[]')
                except ValueError: bars = []
                from .contracts import safe_field
                valid = [b for b in bars if isinstance(b, dict) and
                         all(isinstance(b.get(k), str) and safe_field(b[k]) and
                             field_access(security, self._project(), stype, b[k], {})[0]
                             for k in ('start_date_col', 'end_date_col'))]
                if valid:
                    field.update(renderer='gantt', supported=True, reason='', read_only=True, bars=valid)
            expression = opts.get('expression', '')
            match = re.fullmatch(r'@GET\(\.([A-Za-z_][A-Za-z0-9_]*)\)', expression)
            if match and handler in EXPRESSION and not any(opts.get(n) for n in ('alt_expression','format_expression','use_cache')):
                source_field = match.group(1)
                from .contracts import safe_field
                visible, _ = field_access(security, self._project(), stype, source_field, model.describe(source_field)['attributes'])
                if safe_field(source_field) and source_field in self._stub().get_column_info(stype) and visible:
                    field.update(provider='direct-expression', source_field=source_field, supported=True, reason='', read_only=True)
        spec['capabilities']['retire'] = self._can_retire(stype)
        spec['diagnostics'] = [{'field': f['name'], 'handler': f['handler'], 'reason': f['reason']}
                               for f in spec['fields'] if f.get('reason')]
        if stype == 'sthpw/notification_log':
            for field in spec['fields']:
                if field['handler'] in RECIPIENT_HANDLERS:
                    field.update(provider='notification-recipients', supported=True, reason='', read_only=True)
                elif field['handler'] in WIKI_HANDLERS and field['storage']:
                    field.update(supported=True, reason='', read_only=True, renderer='text')
            spec['capabilities'].update(create=False, update=False, retire=False)
            spec['diagnostics'] = [{'field': f['name'], 'handler': f['handler'], 'reason': f['reason']}
                                   for f in spec['fields'] if f.get('reason')]
        if stype == 'sthpw/task':
            # Calendar/Gantt's columns come from an actual GanttElement config.
            bars = [bar for f in spec['fields'] for bar in f.get('bars', [])]
            spec['task_layout'] = {'bars': bars, 'status_field': next((f['name'] for f in spec['fields'] if f.get('provider') == 'status'), None)}
        spec = self._column_spec(spec, model, self._stub().get_column_info(stype), form=(view in ('edit','insert') or bool((options or {}).get('native_form'))))
        spec = self._native_value_spec(spec, form=(view in ('edit','insert') or bool((options or {}).get('native_form'))))
        spec = self._thumbnail_spec(spec, form=(view in ('edit','insert') or bool((options or {}).get('native_form'))))
        return self.global_spec(spec,model,options or {})

    def _defaults(self, search, stype, options):
        super()._defaults(search, stype, options)
        if options.get('native_user_panel'): self.admin_user_filter(search,options)
        if options.get('native_notification_scope'):
            from tactic.core.notification_filters import NotificationLogScope
            NotificationLogScope().alter_search(search)
        if options.get('native_fixed_key'):
            obj=self._object(stype,options['native_fixed_key']);search.add_id_filter(obj.get_id())
        parent_key = options.get('native_parent_key')
        if parent_key:
            obj = self._object(options.get('native_parent_type'), parent_key)
            search.add_relationship_filter(obj)

    def _object(self, stype, key):
        if stype == 'config/custom_script': script_permission()
        obj = super()._object(stype, key)
        target=getattr(self,'active_target',{})
        if stype=='sthpw/login' and target.get('options',{}).get('native_user_panel'):
            from pyasm.search import Search
            q=Search(stype);q.add_id_filter(obj.get_id());self.admin_user_filter(q,target['options'])
            if not q.get_sobject():raise ApiError(403,'user_scope','Пользователь не входит в область исходного UserPanelWdg')
        fixed=target.get('options',{}).get('native_fixed_key')
        if fixed and target.get('search_type')==stype and obj.get_search_key()!=fixed:
            raise ApiError(403,'cell_record','Нельзя подменить запись вложенного виджета')
        if stype == 'sthpw/notification_log' and getattr(self, 'active_target', {}).get('options', {}).get('native_notification_scope'):
            from pyasm.search import Search
            from tactic.core.notification_filters import NotificationLogScope
            search = Search(stype); search.add_id_filter(obj.get_id())
            NotificationLogScope().alter_search(search)
            if not search.get_sobject():
                raise ApiError(403, 'notification_recipient', 'Уведомление не адресовано текущему пользователю в этом проекте')
        return obj

    def _serialize_many(self, objects, spec):
        objects = list(objects)
        prior = getattr(self, '_notification_recipient_cache', None)
        old_thumbnails=getattr(self,'_thumbnail_cache',None)
        self._thumbnail_cache=self._thumbnail_page(objects,spec)
        old_members=getattr(self,'_global_member_cache',None)
        old_labels=getattr(self,'_cell_login_labels',None)
        login_fields=[f['name'] for f in spec['fields'] if (f.get('display_handler') or f.get('handler')) in LOGIN_DISPLAY and f.get('storage')]
        if login_fields:
            self._cell_login_labels=self._login_labels([o.get_value(n,no_exception=True) for o in objects for n in login_fields])
        if spec.get('type')=='sthpw/login_group' and any(f.get('renderer')=='group-members' for f in spec['fields']):
            from pyasm.search import Search
            self._global_member_cache={}
            names=[o.get_value('login_group') for o in objects]
            if names:
                q=Search('sthpw/login_in_group');q.add_filters('login_group',names);q.set_limit(20001)
                pairs=q.get_sobjects()
                if len(pairs)>20000:raise ApiError(413,'membership_page','Слишком много связей на странице; уменьшите размер страницы')
                for pair in pairs:self._global_member_cache.setdefault(pair.get_value('login_group'),[]).append(pair.get_value('login'))
        try:
            if any(f.get('provider') == 'notification-recipients' for f in spec['fields']):
                self._notification_recipient_cache = self._notification_recipients([o.get_id() for o in objects])
            return [self._serialize(obj, spec) for obj in objects]
        finally:
            self._notification_recipient_cache = prior
            self._global_member_cache=old_members
            self._cell_login_labels=old_labels
            self._thumbnail_cache=old_thumbnails

    def _serialize(self, obj, spec):
        row = super()._serialize(obj, spec)
        for f in spec['fields']:
            if f.get('provider') == 'notification-recipients':
                cache = getattr(self, '_notification_recipient_cache', None)
                if cache is None:
                    cache = self._notification_recipients([obj.get_id()])
                row['values'][f['name']] = cache.get(str(obj.get_id()), '')
            elif f.get('provider') == 'subcontext':
                value = obj.get_value('context', no_exception=True) or ''
                row['values'][f['name']] = value.split('/', 1)[1] if '/' in value else ''
            elif f.get('provider') == 'direct-expression':
                row['values'][f['name']] = json_safe(obj.get_value(f['source_field'], no_exception=True))
            elif f.get('renderer') == 'gantt':
                row['values'][f['name']] = {'bars': [{'start': json_safe(obj.get_value(b['start_date_col'], no_exception=True)),
                                                      'end': json_safe(obj.get_value(b['end_date_col'], no_exception=True)),
                                                      'color': b.get('color'), 'start_field': b['start_date_col'],
                                                      'end_field': b['end_date_col']} for b in f['bars']]}
        return self._thumbnail_cells(obj,self.global_cells(obj,self._native_value_cells(obj,self._column_cells(obj, row, spec),spec),spec),spec)

    def form(self, stype, key=None, choice_overrides=None):
        from pyasm.search import Search, SearchType
        from pyasm.biz import Pipeline, Task
        from pyasm.common import Environment
        from tactic.core.task_choices import allowed_task_statuses, process_choices
        form = super().form(stype, key)
        obj = self._object(stype, key) if key else None
        parent = obj.get_parent() if obj and stype == 'sthpw/task' else None
        if choice_overrides:
            if stype != 'sthpw/task' or obj is None:
                raise ApiError(400, 'form_context', 'Зависимые варианты поддержаны для существующей задачи')
            from tactic.core.task_choices import TaskChoiceContext
            obj = TaskChoiceContext(obj, choice_overrides)
            form['record']['values'].update(choice_overrides)
        for field in form['spec']['fields']:
            family = field.get('provider')
            if family not in ('status', 'process', 'login', 'task-lookup'): continue
            choices = []
            if family == 'status':
                if stype == 'sthpw/task':
                    # Task.get_pipeline is the original authoritative fallback.
                    pipeline = (obj or SearchType.create('sthpw/task')).get_pipeline()
                else:
                    pipeline_code = obj.get_value('pipeline_code', no_exception=True) if obj else None
                    if stype == 'sthpw/snapshot': pipeline_code = pipeline_code or 'snapshot'
                    pipeline = Pipeline.get_by_code(pipeline_code) if pipeline_code else None
                if pipeline:
                    allowed = allowed_task_statuses(Environment.get_security(), pipeline, obj.get_value('status') if obj else '')
                    choices = [{'value': p.get_name(), 'label': p.get_name(), 'color': p.get_color()} for p in pipeline.get_processes() if p.get_name() in allowed]
            elif family == 'process':
                pipeline = Pipeline.get_by_sobject(parent) if parent else None
                if pipeline: choices = [{'value': n, 'label': n} for n in process_choices(pipeline, field.get('provider_options', {}).get('context') == 'true')]
                elif parent and not parent.has_value('pipeline_code'):
                    # Explicit free-form branch of the ORIGINAL ProcessInputWdg.
                    field.update(kind='text', provider='process-freeform')
                    continue
            elif family == 'task-lookup':
                search = Search('sthpw/pipeline' if field['name'] == 'pipeline_code' else 'sthpw/milestone')
                if field['name'] == 'pipeline_code':
                    search.add_filter('search_type', 'sthpw/task')
                search.add_op('begin'); search.add_filter('project_code', self._project())
                search.add_filter('project_code', None); search.add_op('or')
                search.add_order_by('code'); search.set_limit(2001)
                rows = search.get_sobjects()
                if len(rows) > 2000:
                    field.update(read_only=True, reason='Слишком много вариантов: требуется отдельный поиск')
                    continue
                choices = [{'value': r.get_code(), 'label': r.get_code()} for r in rows]
            else:
                search = Search('sthpw/login')
                group_name = None  # Popup ProcessGroupSelectWdg uses parent pipeline's field_login_group.
                if parent:
                    pipeline = Pipeline.get_by_sobject(parent)
                    if pipeline:
                        group_name = pipeline.get_process_attrs(obj.get_value('process')).get(field['name'] + '_login_group') or group_name
                if group_name:
                    groups = Search('sthpw/login_in_group'); groups.add_filter('login_group', group_name)
                    logins = [o.get_value('login') for o in groups.get_sobjects()]
                    if logins: search.add_filters('login', logins)
                    else: search.add_filter('id', -1)
                search.add_order_by('login'); search.set_limit(2001)
                users = search.get_sobjects()
                if len(users) > 2000:
                    field.update(read_only=True, reason='Более 2000 пользователей: нужен серверный поиск; неполный список не используется')
                    continue
                attrs = field.get('provider_options', {}).get('label_attr', '').split('|')
                choices = [{'value': u.get_value('login'),
                            'label': (' '.join(str(u.get_value(a, no_exception=True) or '') for a in attrs if a).strip()
                                      if any(attrs) else u.get_value('display_name')) or u.get_value('login')} for u in users]
            if choices or family == 'task-lookup':
                field['options'] = [{'value': '', 'label': '—'}] + choices
                current = form['record']['values'].get(field['name']) if form['record'] else None
                if current not in (None, '') and current not in [c['value'] for c in choices] and not choice_overrides:
                    # Existing retired choice is visible, not replaced on save.
                    field['options'].append({'value': str(current), 'label': str(current) + ' (текущее)'})
            else:
                field['read_only'] = True
                field['reason'] = 'Не удалось разрешить допустимые значения из pipeline/group; свободный ввод запрещён'
        return self.complete_global_form(stype,key,form)


    def prepare_form(self, stype, key, values):
        """Validate dependent selector changes before any original action executes."""
        from .contracts import clean_values
        base = self.form(stype, key)
        if stype != 'sthpw/task' or key is None or not isinstance(values, dict):
            return base
        selectors = {k: v for k, v in values.items() if k in ('pipeline_code', 'process', 'context')}
        if not selectors:
            return base
        selectors = clean_values(selectors, base['spec']['fields'])
        prospective = self.form(stype, key, choice_overrides=selectors)
        # A status not present in the NEW task pipeline cannot silently survive
        # a pipeline change. Ask for an explicit valid status in the same edit.
        if 'pipeline_code' in selectors:
            current = values.get('status', base['record']['values'].get('status'))
            status = next((f for f in prospective['spec']['fields'] if f['name'] == 'status'), None)
            if current and (status is None or current not in [o['value'] for o in status['options']]):
                if 'status' not in values:
                    prospective['dependency_notice'] = 'Выберите статус из нового task pipeline перед сохранением'
                else:
                    raise ApiError(400, 'task_pipeline_status', 'Статус не принадлежит новому task pipeline')
        return prospective

    def form_preview(self, data):
        opened = self.open_target(data.get('target'))
        if opened['kind'] not in ('table', 'form') or opened['search_type'] != 'sthpw/task':
            raise ApiError(400, 'form_context', 'Этот preview предназначен для штатной формы задачи')
        key = data.get('key')
        self.check_form_binding(opened, data, 'GET', '/form')
        base = self.form('sthpw/task', key)
        if not key or not base['record'] or base['record']['revision'] != data.get('revision'):
            raise ApiError(409, 'conflict', 'Задача изменилась: перечитайте форму')
        values = data.get('values')
        if not isinstance(values, dict) or set(values) - {'pipeline_code', 'process', 'context'}:
            raise ApiError(400, 'form_context', 'Preview принимает только process, context и pipeline_code')
        return self.prepare_form('sthpw/task', key, values)
