"""Native task workspace using the original Task/Pipeline/EditCmd services.

There is no independent task database or client-side transition engine. The
parent pipeline controls generation; each Task's pipeline controls its statuses.
All writes run in the existing TACTIC Command transaction and retain triggers.
"""
from datetime import date
from .contracts import ApiError, clean_values, integer, json_safe, revision, text
from tactic.core.field_policy import field_access

TASK_FIELDS = ('code', 'description', 'process', 'context', 'status', 'assigned',
               'supervisor', 'assigned_group', 'bid_start_date', 'bid_end_date',
               'actual_start_date', 'actual_end_date', 'bid_duration', 'priority',
               'task_type', 'pipeline_code')


class TaskService:
    def _task_parent(self, data):
        opened = self.open_target(text(data.get('target'), 'target', 4000))
        if opened['kind'] not in ('table', 'form'):
            raise ApiError(400, 'task_source', 'Задачи открываются из записи TACTIC')
        obj = self._object(opened['search_type'], text(data.get('key'), 'key', 1500))
        parent = obj.get_parent() if opened['search_type'] == 'sthpw/task' else obj
        if parent is None:
            raise ApiError(404, 'task_parent', 'Родитель задачи не найден')
        # Re-resolve, do not trust an implicitly loaded parent of another project.
        parent = self._object(parent.get_base_search_type(), parent.get_search_key())
        return opened, parent

    def _task_search(self, parent):
        from pyasm.search import Search
        search = Search('sthpw/task')
        search.add_relationship_filter(parent)
        return search

    def _task_for_parent(self, parent, key):
        task = self._object('sthpw/task', text(key, 'task', 1500))
        search = self._task_search(parent)
        search.add_id_filter(task.get_id())
        if not search.get_sobject():
            raise ApiError(403, 'task_scope', 'Задача не принадлежит выбранному объекту')
        return task

    def _task_write_parent(self, parent):
        if parent.get_base_search_type().startswith(('sthpw/', 'config/')):
            raise ApiError(403, 'task_generation_type', 'Создание задач для системных объектов этим экраном запрещено')
        if parent.get_project_code() != self._project():
            raise ApiError(403, 'task_project', 'Откройте проект родительского объекта перед изменением задач')
        if parent.is_retired():
            raise ApiError(409, 'parent_retired', 'Сначала восстановите родительский объект из архива')

    def _initial_pipeline(self, parent):
        from pyasm.search import SearchType
        from pyasm.biz import Task
        if not SearchType.column_exists(parent.get_search_type(), 'pipeline_code'):
            return None
        return Task.resolve_initial_pipeline(parent)

    def _generation_state(self, parent):
        pipeline = self._initial_pipeline(parent)
        if pipeline is None:
            raise ApiError(400, 'pipeline_missing', 'У объекта нет разрешённого pipeline для генерации задач')
        search = self._task_search(parent)
        search.add_order_by('id'); search.set_limit(2001)
        existing = search.get_sobjects()
        if len(existing) > 2000:
            raise ApiError(413, 'task_limit', 'У объекта более 2000 задач; нужна отдельная пакетная операция')
        digest = revision({'parent': parent.get_sobject_dict(),
                           'pipeline': pipeline.get_sobject_dict(),
                           'processes': {name: obj.get_sobject_dict() for name, obj in pipeline.get_process_sobjects().items()},
                           'tasks': [t.get_sobject_dict() for t in existing]})
        return pipeline, existing, digest

    def _task_card(self, task, spec, pipelines):
        from pyasm.common import Environment
        from pyasm.search import SearchType
        model = self._model('sthpw/task', spec['view'])
        record = self._serialize(task, spec)
        security = Environment.get_security()
        values = {}
        for name in TASK_FIELDS:
            attrs = model.describe(name).get('attributes', {})
            if SearchType.column_exists('sthpw/task', name) and field_access(security, self._project(), 'sthpw/task', name, attrs)[0]:
                values[name] = json_safe(task.get_value(name, no_exception=True))
        record['task'] = values
        # Use Task.get_pipeline, including its exact upstream fallback. Avoid
        # combining identically named statuses from distinct task pipelines.
        from tactic.core.task_choices import allowed_task_statuses
        pipeline = task.get_pipeline()
        allowed = allowed_task_statuses(security, pipeline, task.get_value('status'))
        record['allowed_statuses'] = allowed
        code = pipeline.get_code()
        if code not in pipelines:
            pipelines[code] = {'code': code, 'statuses': [
                {'name': p.get_name(), 'color': p.get_color()} for p in pipeline.get_processes()]}
        record['task_pipeline'] = code
        record['retired'] = task.is_retired()
        return record

    def task_operation(self, method, path, data):
        from pyasm.biz import Task
        from tactic.core.native_edit import NativeEditCmd
        opened, parent = self._task_parent(data)
        if path == '/tasks' and method == 'GET':
            offset = integer(int(data.get('offset', 0)), 'offset', 0, 1000000)
            limit = integer(int(data.get('limit', 100)), 'limit', 1, 200)
            search = self._task_search(parent)
            total = search.get_count()
            search.add_order_by('process'); search.add_order_by('id')
            search.set_limit(limit); search.set_offset(offset)
            spec = self.view('sthpw/task', 'table')
            pipelines = {}
            records = [self._task_card(t, spec, pipelines) for t in search.get_sobjects()]
            pipeline = self._initial_pipeline(parent)
            return {'items': records, 'spec': spec, 'pipelines': list(pipelines.values()),
                    'parent_key': parent.get_search_key(), 'parent_type': parent.get_base_search_type(),
                    'parent_title': parent.get_value('name', no_exception=True) or parent.get_code(),
                    'processes': [{'name': p.get_name(), 'type': p.get_type()} for p in pipeline.get_processes()] if pipeline else [],
                    'total': total, 'offset': offset, 'limit': limit,
                    'can_write': bool(self.allow_writes and not parent.is_retired() and parent.get_project_code() == self._project() and not parent.get_base_search_type().startswith(('sthpw/', 'config/'))),
                    'can_generate': bool(self.allow_writes and pipeline and not parent.is_retired() and
                                         parent.get_project_code() == self._project() and
                                         not parent.get_base_search_type().startswith(('config/', 'sthpw/'))),
                    'source': 'Task.get_pipeline / Task.add_initial_tasks / original EditCmd'}
        if path == '/task-generate':
            self._task_write_parent(parent)
            pipeline, existing, expected = self._generation_state(parent)
            if method == 'GET':
                return {'revision': expected, 'pipeline': pipeline.get_code(),
                        'processes': [{'name': p.get_name(), 'type': p.get_type()} for p in pipeline.get_processes()],
                        'existing': len(existing), 'can_write': self.allow_writes,
                        'notice': 'Без выбора процессов выполняется штатный TaskGenerator. Выбранные процессы проходят исходную ветку add_initial_tasks с проверкой дубликатов.'}
            if method == 'POST':
                processes = data.get('processes', [])
                if not isinstance(processes, list) or len(processes) > 200 or any(not isinstance(p, str) for p in processes) or len(set(processes)) != len(processes):
                    raise ApiError(400, 'processes', 'Выберите до 200 различных процессов')
                known = set(pipeline.get_process_names())
                if not set(processes).issubset(known):
                    raise ApiError(400, 'processes', 'Процесс отсутствует в исходном pipeline')
                start = data.get('start_date') or None
                if start:
                    try: date.fromisoformat(start)
                    except (ValueError, TypeError) as exc: raise ApiError(400, 'start_date', 'Нужна дата YYYY-MM-DD') from exc
                if data.get('confirm') != 'GENERATE':
                    raise ApiError(400, 'confirmation', 'Подтвердите создание задач')
                def create():
                    # Re-read both task membership and pipeline inside Command.
                    _, _, fresh = self._generation_state(parent)
                    if fresh != data.get('revision'):
                        raise ApiError(409, 'conflict', 'Задачи, родитель или pipeline изменились; перечитайте предварительный просмотр')
                    result = Task.add_initial_tasks(parent, processes=processes,
                                                    start_date=start, skip_duplicate=True)
                    return {'created': len(result or []), 'keys': [t.get_search_key() for t in result or []],
                            'command': 'Task.add_initial_tasks', 'skip_duplicate': True}
                return self._write(create)
        if path in ('/task-form', '/task-change', '/task-form-preview'):
            task = self._task_for_parent(parent, data.get('task'))
            form = self.form('sthpw/task', task.get_search_key())
            if path == '/task-form-preview' and method == 'POST':
                if form['record']['revision'] != data.get('revision'):
                    raise ApiError(409, 'conflict', 'Задача изменилась: перечитайте форму')
                values = data.get('values')
                if not isinstance(values, dict) or set(values) - {'pipeline_code', 'process', 'context'}:
                    raise ApiError(400, 'form_context', 'Preview принимает только process, context и pipeline_code')
                return self.prepare_form('sthpw/task', task.get_search_key(), values)
            if path == '/task-form' and method == 'GET':
                return form
            if path == '/task-change' and method == 'PATCH':
                self._task_write_parent(parent)
                if task.is_retired(): raise ApiError(409, 'task_retired', 'Задача находится в архиве')
                form = self.prepare_form('sthpw/task', task.get_search_key(), data.get('values'))
                if form.get('dependency_notice'): raise ApiError(400, 'form_dependency', form['dependency_notice'])
                values = clean_values(data.get('values'), form['spec']['fields'])
                def update():
                    fresh = self._task_for_parent(parent, task.get_search_key())
                    if self._serialize(fresh, form['spec'])['revision'] != data.get('revision'):
                        raise ApiError(409, 'conflict', 'Задача изменена другим пользователем')
                    cmd = NativeEditCmd(sobject=fresh, view=form['spec']['view'], data=values, input_prefix='__NONE__')
                    cmd.execute()
                    return self._serialize(cmd.get_sobject(), form['spec'])
                return self._write(update)
        raise ApiError(405, 'method', 'Недопустимая операция задач')
