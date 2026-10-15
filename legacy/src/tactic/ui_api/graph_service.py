"""Native schema/workflow operations backed by the existing TACTIC commands."""
import json
import re
from copy import deepcopy
from tactic.core.graph_model import apply_graph_edits, graph_spec, normalize_workflow_settings, PROCESS_TYPES
from tactic.core.config_model import parse_xml, xml_text
from .action_log import execute_traced
from .contracts import ApiError, revision, json_safe


class GraphService:
    def graph_operation(self, method, data):
        from pyasm.common import Environment
        if not Environment.get_security().is_admin():
            raise ApiError(403,'admin_only','Редактор графа доступен администраторам')
        options={}
        if data.get('target'):
            opened=self.open_target(data['target'])
            if opened['kind']!=data.get('kind') or opened['kind'] not in ('pipeline','schema'):
                raise ApiError(403,'graph_target','Граф не принадлежит выбранному конфигурационному виджету')
            options=opened.get('options',{})
        data=dict(data,_config_options=options)
        if data.get('kind')=='pipeline' and data.get('key'):
            obj=self._object('sthpw/pipeline',data['key'])
            owner=obj.get_value('project_code',no_exception=True)
            if owner and owner!=self._project() and self._project()!='admin':
                raise ApiError(403,'pipeline_scope','Pipeline другого проекта')
            fixed=options.get('native_fixed_pipeline')
            if fixed and obj.get_code()!=fixed:raise ApiError(403,'pipeline_scope','Этот виджет привязан к другому pipeline')
            if owner and owner!=self._project():
                with self._graph_project(owner):return self._graph_operation(method,data)
        return self._graph_operation(method,data)

    from contextlib import contextmanager
    @contextmanager
    def _graph_project(self,project):
        from pyasm.biz import Project
        from pyasm.common import Container
        from tactic_client_lib import TacticServerStub
        state=self._state.get();prior=state['project'];stub=state['stub']
        # Search caches resource resolution by bare type. Do not reuse another
        # project's config/* resolution while executing an owner's save command.
        cache=Container.get_instance().get_data()
        saved={k:v for k,v in list(cache.items()) if str(k).startswith('Search:resource:')}
        for k in saved:Container.put(k,None)
        token=self._state.set(dict(state,project=project))
        try:
            stub.set_project(project);TacticServerStub.set(stub)
            yield
        finally:
            stub.set_project(prior or 'admin');self._state.reset(token)
            for k in list(Container.get_instance().get_data()):
                if str(k).startswith('Search:resource:'):Container.put(k,None)
            for k,v in saved.items():Container.put(k,v)

    def _graph_operation(self, method, data):
        from pyasm.search import Search, SearchType
        from pyasm.biz import Schema, Pipeline
        from pyasm.common import Environment
        if not Environment.get_security().is_admin():
            raise ApiError(403, 'admin_only', 'Редактор графа доступен администраторам')
        kind = data.get('kind')
        if kind not in ('pipeline', 'schema'):
            raise ApiError(400, 'kind', 'Ожидается pipeline или schema')
        options=data.get('_config_options',{})
        stype, column = ('sthpw/pipeline', 'pipeline') if kind == 'pipeline' else ('sthpw/schema', 'schema')
        if method == 'GET' and not data.get('key'):
            search = Search(stype)
            if kind == 'pipeline' and self._project() != 'admin':
                search.add_op('begin')
                search.add_filter('project_code', self._project())
                search.add_filter('project_code', None)
                search.add_filter('project_code', '')
                search.add_op('or')
            if kind=='schema':
                search.add_op('begin');search.add_filter('code',self._project());search.add_filter('project_code',self._project());search.add_op('or')
            elif options.get('search_type'):
                search.add_filter('search_type',options['search_type'])
            fixed=options.get('native_fixed_pipeline')
            if kind=='pipeline' and fixed:search.add_filter('code',fixed)
            search.add_order_by('code'); search.set_limit(500)
            items = [{'key': o.get_search_key(), 'code': o.get_code(),
                      'name': o.get_value('name', no_exception=True) or o.get_code()}
                     for o in search.get_sobjects()]
            if kind=='schema':
                original=Schema.get(project_code=self._project())
                if original:
                    actual=original.get_search_key() if not original.is_insert() else None
                    if actual is None or not any(i['key']==actual for i in items):
                        items.insert(0,{'key':'@schema:'+self._project(),'code':self._project(),'name':'Схема '+self._project(),'source':'TACTIC Schema.get'})
            initial = next((i['key'] for i in items if i['code'] ==
                            (fixed or options.get('pipeline') or options.get('pipeline_code') or self._project())),
                           items[0]['key'] if items else None)
            requested_key = options.get('search_key') if kind == 'pipeline' else None
            if requested_key:
                selected = self._object('sthpw/pipeline', requested_key)
                owner = selected.get_value('project_code', no_exception=True)
                if owner and owner != self._project() and self._project() != 'admin':
                    raise ApiError(403, 'pipeline_scope', 'Pipeline другого проекта')
                if fixed and selected.get_code() != fixed:
                    raise ApiError(403, 'pipeline_scope', 'Pipeline не принадлежит фиксированному представлению')
                if options.get('search_type') and selected.get_value('search_type', no_exception=True) != options['search_type']:
                    raise ApiError(403, 'pipeline_scope', 'Pipeline не принадлежит типу представления')
                if selected.get_value('s_status', no_exception=True) == 'retired':
                    raise ApiError(409, 'pipeline_retired', 'Выбранный pipeline находится в архиве')
                initial = selected.get_search_key()
                if not any(i['key'] == initial for i in items):
                    # The initial record can legitimately be outside the first 500 sorted results.
                    items.append({'key':initial, 'code':selected.get_code(),
                                  'name':selected.get_value('name', no_exception=True) or selected.get_code()})
            return {'items': items, 'can_create': kind == 'pipeline' and self.allow_writes and not fixed,
                    'initial_key':initial,
                    'search_types':self.catalog()['types'],
                    'node_types': list(PROCESS_TYPES), 'limit': 500}
        if method == 'POST' and not data.get('key'):
            if kind != 'pipeline':
                raise ApiError(400, 'create_schema', 'Схема создаётся вместе с проектом')
            code, title = data.get('code'), data.get('name') or data.get('code')
            if not isinstance(code, str) or not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_.-]{0,99}', code):
                raise ApiError(400, 'code', 'Некорректный код pipeline')
            if not isinstance(title, str) or len(title) > 200:
                raise ApiError(400, 'name', 'Некорректное имя pipeline')
            def create():
                if Search.get_by_code(stype, code):
                    raise ApiError(409, 'exists', 'Pipeline с таким кодом уже существует')
                obj = SearchType.create(stype)
                obj.set_value('code', code); obj.set_value('name', title)
                obj.set_value('project_code', self._project() if self._project() != 'admin' else None)
                assigned=options.get('search_type') or data.get('search_type')
                if assigned:self.require_type(assigned);obj.set_value('search_type',assigned)
                obj.set_value('pipeline', '<pipeline/>'); obj.commit()
                Pipeline.clear_cache(search_key=obj.get_search_key())
                return {'created': True, 'key': obj.get_search_key()}
            return self._write(create)
        reference=data.get('key')
        if kind=='schema' and isinstance(reference,str) and reference.startswith('@schema:'):
            if reference!='@schema:'+self._project():raise ApiError(403,'schema_scope','Схема другого проекта')
            obj=Schema.get(project_code=self._project())
        else:
            obj = self._object(stype, reference)
        if kind == 'schema' and self._project() != 'admin' and obj.get_code() != self._project():
            raise ApiError(403, 'schema_scope', 'Откройте проект, которому принадлежит схема')
        raw = obj.get_value(column) or ('<pipeline/>' if kind == 'pipeline' else '<schema/>')
        if method == 'GET':
            settings = {}
            if kind == 'pipeline':
                search = Search('config/process'); search.add_filter('pipeline_code', obj.get_code())
                for process in search.get_sobjects():
                    settings[process.get_value('process')] = {
                        'workflow': json_safe(process.get_json_value('workflow', default={})),
                        'description': process.get_value('description', no_exception=True),
                        'subpipeline_code': process.get_value('subpipeline_code', no_exception=True),
                        'code': process.get_code()}
            result = {'key': reference, 'code': obj.get_code(), 'name': obj.get_value('name', no_exception=True),
                      'xml': raw, 'revision': revision({'xml': raw, 'settings': settings}),
                      'graph': graph_spec(raw, kind), 'settings': settings,
                      'can_edit': self.allow_writes and not (kind == 'schema' and obj.get_code() in ('admin', 'sthpw', 'unittest')),
                      'can_save_positions': self.allow_writes and not (kind == 'schema' and obj.get_code() in ('admin', 'sthpw', 'unittest')),
                      'node_types': list(PROCESS_TYPES),
                      'source': 'predefined' if kind=='schema' and obj.get_code() in ('admin','sthpw','unittest') else 'sthpw/'+kind,
                      'owner_project':self._project(),
                      'notice': 'Встроенная схема читается из исходников TACTIC. Для редактирования выберите рабочий проект.' if kind=='schema' and obj.get_code() in ('admin','sthpw','unittest') else ('' if self.allow_writes else 'Запись отключена. Используйте MANAGE_TACTIC.bat configure --writes on и перезапустите сервер.')}
            if kind == 'schema':
                result['search_types'] = self.catalog()['types']
            return result
        if method != 'PATCH':
            raise ApiError(405, 'method', 'Метод не поддерживается')
        def apply():
            if kind == 'schema' and obj.get_code() in ('admin', 'sthpw', 'unittest'):
                raise ApiError(403, 'builtin_schema', 'Встроенная схема читается из исходников и здесь доступна только для чтения')
            current = self._graph_operation('GET', {**data, 'kind': kind})
            if data.get('revision') != current['revision']:
                raise ApiError(409, 'conflict', 'Граф или настройки процессов изменились; перечитайте его')
            try:
                change = apply_graph_edits(current['xml'], kind, data.get('operations', []))
            except ValueError as exc:
                raise ApiError(400, 'graph', str(exc)) from exc
            root = parse_xml(change['xml'])
            if kind == 'pipeline':
                # Do not silently rename/delete steps which have runtime history.
                affected = set(change['removed']) | set(change['renamed'])
                if affected and not obj.get_value('project_code', no_exception=True):
                    raise ApiError(409, 'global_pipeline_history', 'Для глобального pipeline удаление/переименование требует межпроектной проверки истории; используйте отдельную миграцию')
                for process_name in affected:
                    for entity_type in ('sthpw/task', 'config/process_state'):
                        search = Search(entity_type); search.add_filter('process', process_name)
                        if entity_type == 'sthpw/task':
                            # Global/admin pipelines can be used by any project.
                            owner = obj.get_value('project_code', no_exception=True)
                            if owner:
                                search.add_filter('project_code', owner)
                        else:
                            search.add_filter('pipeline_code', obj.get_code())
                        if search.get_count():
                            raise ApiError(409, 'process_in_use', 'Процесс «%s» используется задачами или состоянием workflow. Нужна отдельная миграция.' % process_name)
                settings_patch = data.get('settings', {})
                if not isinstance(settings_patch, dict) or len(settings_patch) > 2000:
                    raise ApiError(400, 'settings', 'Некорректные настройки процессов')
                by_name = {n.get('name'): n for n in root.findall('process')}
                inverse = {new: old for old, new in change['renamed'].items()}
                # Carry original process settings when a type changes; the legacy save
                # command otherwise replaces the previous workflow dictionary.
                old_nodes = {n['name']: n for n in current['graph']['nodes']}
                for process_name, node in by_name.items():
                    old_name = inverse.get(process_name, process_name)
                    previous = old_nodes.get(old_name)
                    if previous is None or previous['type'] != node.get('type', 'manual'):
                        preserved = deepcopy(current['settings'].get(old_name, {}).get('workflow') or {})
                        preserved['node_type'] = node.get('type', 'manual')
                        node.set('settings', json.dumps(preserved, ensure_ascii=False))
                for process_name, patch in settings_patch.items():
                    if process_name not in by_name:
                        raise ApiError(400, 'process', 'Неизвестный процесс')
                    try:
                        validated = normalize_workflow_settings(patch)
                    except ValueError as exc:
                        raise ApiError(400, 'settings', str(exc)) from exc
                    original_name = inverse.get(process_name, process_name)
                    prior = current['settings'].get(original_name, {}).get('workflow') or {}
                    # Deep merge at the boundary preserves unknown nested configuration.
                    workflow = self._merge_settings(prior, validated)
                    workflow['node_type'] = by_name[process_name].get('type', 'manual')
                    self._validate_process_settings(workflow, by_name[process_name].get('type', 'manual'))
                    by_name[process_name].set('settings', json.dumps(workflow, ensure_ascii=False))
                from tactic.core.pipeline_commands import PipelineSaveCbk
                # Update existing process names by code before original save resolves them.
                for old, new in change['renamed'].items():
                    search = Search('config/process'); search.add_filter('pipeline_code', obj.get_code()); search.add_filter('process', old)
                    for process in search.get_sobjects():
                        process.set_value('process', new); process.commit()
                cmd = PipelineSaveCbk(search_key=obj.get_search_key(), pipeline=xml_text(root),
                                      color=obj.get_value('color'), pipeline_data=obj.get_json_value('data', default={}),
                                      xml_is_escaped=True)
                execute_traced(cmd)
                # Finite original property handlers, not arbitrary execute_cmd.
                for process_name, node in by_name.items():
                    previous = old_nodes.get(inverse.get(process_name, process_name))
                    changed_type = previous is None or previous['type'] != node.get('type', 'manual')
                    changed_description = previous is None or previous['attributes'].get('description') != node.get('description')
                    if process_name in settings_patch or changed_type or changed_description:
                        self._sync_process_properties(obj, process_name, node, changed_type, process_name in settings_patch, changed_description)
                # Original PipelineSaveCbk synchronizes config/process, including removal of obsolete process definitions.
                # Runtime task/state history was checked above and is not deleted by this adapter.
                Pipeline.clear_cache(search_key=obj.get_search_key())
            else:
                self._validate_schema_links(root)
                if obj.is_insert():obj.set_value('project_code',self._project())
                obj.set_value('schema', xml_text(root)); obj.commit()
                Schema.get(reset_cache=True, project_code=self._project())
            return {'saved': True, 'key': obj.get_search_key(),
                    'notice': 'XML сохранён исходной командой. Определения процессов синхронизированы; runtime-история не удалялась.' if kind=='pipeline' else 'Схема сохранена. Таблицы, колонки и данные не мигрировались.'}
        return self._write(apply)


    def _validate_process_settings(self, workflow, node_type):
        from pyasm.biz import Pipeline
        if node_type == 'hierarchy':
            hierarchy = workflow.get('hierarchy') or workflow.get('default') or {}
            if not isinstance(hierarchy, dict): raise ApiError(400, 'hierarchy', 'hierarchy должен быть объектом')
            code = hierarchy.get('subpipeline')
            if code and not Pipeline.get_by_code(code): raise ApiError(400, 'subpipeline', 'Вложенный pipeline не найден')
        if node_type == 'progress':
            progress = workflow.get('progress') or {}
            if not isinstance(progress, dict): raise ApiError(400, 'progress', 'progress должен быть объектом')
            related = progress.get('related_search_type')
            if related: self.require_type(related)
            if progress.get('related_scope', 'local') not in ('local', 'global'):
                raise ApiError(400, 'scope', 'related_scope: local или global')
        if node_type == 'status' and not isinstance(workflow.get('default') or {}, dict):
            raise ApiError(400, 'status', 'default должен быть объектом')

    def _sync_process_properties(self, pipeline, process_name, node, type_changed, settings_changed, description_changed=False):
        from pyasm.search import Search
        from tactic.core.process_commands import NewProcessInfoCmd
        search = Search('config/process'); search.add_filter('pipeline_code', pipeline.get_code())
        search.add_filter('process', process_name); process = search.get_sobject()
        if not process: raise ApiError(500, 'process_missing', 'Команда TACTIC не создала запись процесса')
        workflow = deepcopy(process.get_json_value('workflow', default={}) or {})
        node_type = node.get('type', 'manual')
        workflow['node_type'] = node_type
        self._validate_process_settings(workflow, node_type)
        cmd = NewProcessInfoCmd(**deepcopy(workflow))
        cmd.pipeline_code = pipeline.get_code(); cmd.process = process_name
        cmd.pipeline = pipeline; cmd.process_sobj = process; cmd.workflow = deepcopy(workflow)
        # Action/condition scripts are preserved untouched, not reset by the
        # legacy handler's "create_new" default. Script authoring is not native yet.
        handler = {'hierarchy': cmd.handle_hierarchy, 'progress': cmd.handle_progress,
                   'status': cmd.handle_status}.get(node_type)
        if handler and (settings_changed or type_changed):
            if node_type == 'progress' and not (workflow.get('progress') or {}).get('related_search_type'):
                # Incomplete newly created nodes have no listener until configured.
                handler = None
            if handler: handler()
        # Handlers may add trigger_code/mapping fields; retain all prior extensions.
        workflow = self._merge_settings(workflow, cmd.kwargs)
        process.set_json_value('workflow', workflow)
        if description_changed or node.get('description') is not None: process.set_value('description', node.get('description') or '')
        if node_type == 'status' and node.get('color') is not None: process.set_value('color', node.get('color'))
        process.commit()

    @staticmethod
    def _merge_settings(old, patch):
        result = deepcopy(old) if isinstance(old, dict) else {}
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = GraphService._merge_settings(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    def _validate_schema_links(self, root):
        from pyasm.search import SearchType
        # All types/columns must already exist. Relationship editing is not a silent
        # DDL generator; SearchType creation remains its separate audited command.
        for node in root.findall('search_type'):
            self.require_type(node.get('name'))
        for edge in root.findall('connect'):
            source, dest = edge.get('from'), edge.get('to')
            self.require_type(source); self.require_type(dest)
            relationship = edge.get('relationship', 'code')
            if relationship not in ('code', 'id', 'search_type', 'instance', 'many_to_many'):
                # Existing custom relation handlers are preserved but not rewritten.
                continue
            for typ, attr in ((source, 'from_col'), (dest, 'to_col')):
                column = edge.get(attr)
                if column and not SearchType.column_exists(typ, column):
                    raise ApiError(400, 'schema_column', 'Поле %s.%s отсутствует. Сначала создайте его через SearchType.' % (typ, column))
            instance = edge.get('instance_type')
            if instance:
                self.require_type(instance)
