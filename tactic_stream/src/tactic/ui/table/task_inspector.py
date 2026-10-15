"""Handler task-inspector operations on native TACTIC objects and commands."""
import datetime
import hashlib
import json
import math

from dateutil import parser
from pyasm.biz import Pipeline, Project, Schema, Task
from pyasm.command import Command
from pyasm.common import Environment, SecurityException, UserException
from pyasm.search import Search, SearchKey, SearchType
from pyasm.security.security import _require_admin
from tactic.ui.widget.discussion_wdg import discussion_target, DiscussionReadCmd, same_note_target
from .task_element_wdg import TaskElementWdg, TaskElementCbk


def process_configuration(pipeline, process):
    node = pipeline.get_process(process) if pipeline else None
    config = pipeline.get_process_sobject(process) if node else None
    workflow = (config.get_json_value('workflow') or {}) if config else {}
    if not isinstance(workflow, dict) or not isinstance(workflow.get('properties') or {}, dict):
        raise ValueError('Invalid task workflow defaults')
    properties = workflow.get('properties') or {}
    values = dict(node.get_attributes()) if node else {}
    # Handler process_task_configuration: runtime assignees are not defaults.
    for source in (workflow, properties):
        for name, value in source.items():
            if name in ('assigned', 'supervisor') and source is not properties:
                continue
            if value not in (None, ''):
                values[name] = value
    return values, workflow


def task_processes(parent, pipeline, process):
    processes = []
    for node in pipeline.get_processes() if pipeline else []:
        if node.get_type() not in ('action', 'condition', 'dependency') and TaskElementWdg.can_view_process(node.get_name()):
            processes.append(dict(value=node.get_name(), label=node.get_label() or node.get_name(), type=node.get_type(),color=node.get_attribute('color') or ''))
    names = {item['value'] for item in processes}
    for name in ['publish', process, *(task.get_value('process') for task in Task.get_by_sobjects([parent]))]:
        node = pipeline.get_process(name) if pipeline else None
        if node and node.get_type() in ('action', 'condition', 'dependency'):
            continue
        if name and name not in names and TaskElementWdg.can_view_process(name):
            processes.append(dict(value=name, label=name, type='built-in' if name == 'publish' else 'manual',color='')); names.add(name)
    return processes


def related_tasks(parent, pipeline, process):
    # Handler communication._load_related_tasks, with native schema identities
    # and one Task query for all parents (also works with id-based parents).
    values, _workflow = process_configuration(pipeline, process)
    related_type = values.get('search_type') or ''
    result = dict(state='unconfigured', items=[], object_count=0, search_type=related_type,
                  parent_keys=[], approved=0, total=0, summary_available=False)
    if not related_type:
        return result
    if not isinstance(related_type, str):
        raise ValueError('Invalid related Search Type')
    scope = SearchType.breakup_search_type(related_type).get('project')
    if scope and scope != Project.get_project_code():
        raise ValueError('Related objects belong to another project')
    if SearchType.get(related_type, no_exception=True) is None:
        result['state'] = 'missingType'; return result
    schema = Schema.get(project_code=Project.get_project_code())
    if not schema.get_relationship(parent.get_base_search_type(), related_type):
        result['state'] = 'unrelated'; return result
    objects = parent.get_related_sobjects(related_type)
    result.update(state='ready', object_count=len(objects), total=len(objects),
                  parent_keys=[item.get_search_key() for item in objects])
    attrs = schema.get_relationship_attrs('sthpw/task', related_type)
    attrs = schema.resolve_relationship_attrs(attrs, 'sthpw/task', related_type)
    parents = {str(item.get_value(attrs['to_col'])): item for item in objects}
    tasks = [task for task in Task.get_by_sobjects(objects) if TaskElementWdg.can_view_process(task.get_value('process'))]
    for task in tasks:
        obj = parents.get(str(task.get_value(attrs['from_col'])))
        if obj is None:
            continue
        title = obj.get_value('name', no_exception=True) or obj.get_value('title', no_exception=True) or obj.get_code() or str(obj.get_id())
        result['items'].append(dict(parent_title=str(title), parent_key=obj.get_search_key(),
            task_key=task.get_search_key(), process=task.get_value('process'),
            status=task.get_value('status'), assigned=task.get_value('assigned')))
    result['items'].sort(key=lambda item: (item['parent_title'], item['process'], item['task_key']))
    # Handler query_sobjects(include_progress): tc counts objects; ac counts
    # matching tasks, including separate assignees. Do not turn it into a %.
    related_process = values.get('process')
    if not related_process:
        result.update(approved=len(tasks), summary_available=True)
        return result
    if not isinstance(related_process, str) or not TaskElementWdg.can_view_process(related_process):
        return result
    search = Search('config/process')
    search.add_filter('process', related_process)
    search.add_filter('pipeline_code', values.get('pipeline_code'))
    behavior = search.get_sobject()
    workflow = behavior.get_json_value('workflow', {}) if behavior else {}
    task_pipeline = workflow.get('task_pipeline') if isinstance(workflow, dict) else None
    if not task_pipeline:
        return result
    search = Search('config/process'); search.add_filter('pipeline_code', task_pipeline)
    statuses = {item.get_value('process') for item in search.get_sobjects()
                if (item.get_json_value('workflow', {}) or {}).get('mapping')}
    result.update(approved=sum(task.get_value('process') == related_process and
                              (not statuses or task.get_value('status') in statuses) for task in tasks), summary_available=True)
    return result


def inspector_processes(parent, pipeline, process):
    choices = task_processes(parent, pipeline, process)
    notes = Search('sthpw/note')
    notes.add_relationship_filters([parent, *Task.get_by_sobjects([parent])])
    notes = notes.get_sobjects()
    for choice in choices:
        choice['count'] = sum(note.get_process() == choice['value'] for note in notes)
    return choices, notes


def task_scope(search_key, process, task_key=''):
    # Native Task defaults already support tasks owned only by the project.
    parent = discussion_target(search_key) if search_key else Project.get()
    if isinstance(parent, Task):
        task_key = parent.get_search_key()
        process = parent.get_value('process')
        parent = parent.get_parent()
        if not parent:
            raise LookupError('Task parent no longer exists')
    if parent.get_base_search_type() == 'sthpw/project' and parent.get_code() != Project.get_project_code():
        raise ValueError('Task belongs to another project')
    if not isinstance(process, str) or not process or len(process) > 256 or any(ord(char) < 32 for char in process):
        raise ValueError('Choose a valid task process')
    if not TaskElementWdg.can_view_process(process):
        raise SecurityException('Task process is not accessible')
    pipeline = Pipeline.get_by_code(parent.get_value('pipeline_code', no_exception=True))
    node = pipeline.get_process(process) if pipeline else None
    if node and node.get_type() in ('action', 'condition', 'dependency'):
        raise ValueError('This process has no editable task')
    tasks = [task for task in Task.get_by_sobjects([parent]) if task.get_value('process') == process]
    # Handler's primary branch: the unsuffixed context, then creation time/code.
    tasks.sort(key=lambda task: (0 if task.get_value('context') in ('', process) else 1,
                                str(task.get_value('timestamp')), str(task.get_code())))
    requested = discussion_target(task_key) if task_key else None
    selected = next((task for task in tasks if isinstance(requested, Task) and task.get_id() == requested.get_id()), None)
    if task_key and selected is None:
        raise LookupError('Task does not belong to this object and process')
    if not selected:
        selected = next((task for task in tasks if task.get_value('assigned') == Environment.get_user_name()),
                        tasks[0] if tasks else None)
    values, workflow = process_configuration(pipeline, process)
    defaults = dict(process=process, context=process)
    if parent.get_base_search_type() == 'sthpw/project':
        defaults['assigned'] = Environment.get_user_name()
    for name in ('status', 'assigned', 'supervisor'):
        if values.get(name) not in (None, ''):
            defaults[name] = str(values[name])
    defaults['pipeline_code'] = values.get('task_pipeline') or (node.get_task_pipeline() if node else None) or 'task'
    for name in ('duration', 'bid_duration', 'completion'):
        try:
            value = float(values.get(name) or 0)
        except (TypeError, ValueError):
            value = 0
        if not math.isfinite(value):
            raise ValueError('Invalid task workflow defaults')
        values[name] = max(0, min(100, int(value))) if name == 'completion' else max(0, value)
    if values['bid_duration']:
        defaults['bid_duration'] = values['bid_duration']
    if values['completion']:
        column = 'progress' if SearchType.column_exists('sthpw/task', 'progress') else 'completion'
        defaults[column] = values['completion']
    duration = values['duration']
    if duration:
        start = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
        defaults.update(bid_start_date=str(start), bid_end_date=str(start+datetime.timedelta(days=duration)))
    revision = hashlib.sha256(json.dumps(dict(parent=parent.get_data(), tasks=[task.get_data() for task in tasks],
        pipeline=pipeline.get_data() if pipeline else {}, workflow=workflow), sort_keys=True, default=str).encode()).hexdigest()
    return parent, process, tasks, selected, defaults, revision, pipeline


def task_fields(additional=()):
    columns = SearchType.get_columns('sthpw/task')
    names = ['status', 'assigned', 'supervisor', 'bid_start_date', 'bid_end_date', 'bid_duration',
             'progress' if 'progress' in columns else 'completion', 'description', *additional]
    fields = []
    security = Environment.get_security()
    for name in names:
        if name not in columns:
            continue
        keys = [dict(search_type='sthpw/task', key=name, project=Project.get_project_code()),
                dict(search_type='sthpw/task', project=Project.get_project_code())]
        column = dict(search_type='sthpw/task', column=name, project=Project.get_project_code())
        if security.check_access('element', keys, 'view', default='edit') and security.check_access('sobject_column', column, 'view'):
            fields.append(dict(name=name, editable=security.check_access('element', keys, 'edit', default='edit')
                               and security.check_access('sobject_column', column, 'edit')))
    return fields


def inspector_object(parent):
    from pyasm.widget.file_wdg import ThumbWdg
    widget = ThumbWdg(); widget.set_sobjects([parent]); widget.preprocess()
    security = Environment.get_security()
    data = {name: parent.get_value(name, no_exception=True) for name in ('name', 'title', 'code', 'description', 'status')
            if security.check_access('sobject_column', dict(search_type=parent.get_base_search_type(),
                column=name, project=Project.get_project_code()), 'view')}
    search_type = SearchType.get(parent.get_base_search_type())
    return dict(record=dict(data, __search_key__=parent.get_search_key(), id=parent.get_id()),
                search_type=parent.get_base_search_type(), type_title=search_type.get_value('title'), preview=widget.get_cell_value())


def task_status_names(task):
    pipeline = task.get_pipeline()
    security = Environment.get_security()
    return [name for name in pipeline.get_process_names() if
        name == task.get_value('status') or security.check_access('process_select', name, 'view', default='deny') or
        security.check_access('process', [dict(process='*', pipeline=pipeline.get_code()),
            dict(process='*', pipeline='*'), dict(process=name, pipeline=pipeline.get_code())], 'view', default='deny')]


def task_edit_options(parent, selected, defaults, additional=()):
    task = selected or SearchType.create('sthpw/task')
    if not selected:
        task.set_parent(parent)
        for name, value in defaults.items():
            if value is not None:
                task.set_value(name, value)
    fields = task_fields(additional) if additional else task_fields()
    pipeline = task.get_pipeline()
    security = Environment.get_security()
    statuses = task_status_names(task)
    users = Search('sthpw/login'); users.add_order_by('display_name')
    from tactic_stream.server.security_groups import user_directory
    users = [dict(**user,value=user['login'],label=user['displayName']) for user in user_directory(users.get_sobjects())]
    return task, fields, statuses, users


def prepare_task_data(task, selected, defaults, fields, statuses, users, data):
    if not isinstance(data, dict) or set(data) - {field['name'] for field in fields if field['editable']}:
        raise ValueError('Unsupported or read-only task fields')
    # Defaults used for a missing task must pass the same validation as edits.
    data = {**({field['name']: defaults[field['name']] for field in fields
               if field['editable'] and field['name'] in defaults} if not selected else {}), **data}
    prepared = dict(data)
    if 'status' in data and data['status'] not in statuses:
        raise ValueError('Task status is not accessible')
    for name in ('assigned', 'supervisor'):
        if name in data and data[name] is not None and (not isinstance(data[name], str) or
                data[name] and data[name] not in {user['value'] for user in users}):
            raise ValueError('Choose an existing user')
    for name in ('bid_duration', 'completion', 'progress'):
        if name in data:
            try:
                value = float(data[name] or 0)
            except (TypeError, ValueError):
                raise ValueError('Invalid task progress or planned hours') from None
            if not math.isfinite(value) or value < 0 or name != 'bid_duration' and value > 100:
                raise ValueError('Invalid task progress or planned hours')
            prepared[name] = value
    for name in ('bid_start_date', 'bid_end_date'):
        if name in data:
            try:
                prepared[name] = parser.parse(str(data[name])) if data[name] else None
            except (TypeError, ValueError, OverflowError):
                raise ValueError('Choose a valid task date') from None
    start = prepared.get('bid_start_date', task.get_value('bid_start_date', no_exception=True))
    end = prepared.get('bid_end_date', task.get_value('bid_end_date', no_exception=True))
    if start and end:
        start, end = (parser.parse(str(value)) for value in (start, end))
        start = start.replace(tzinfo=datetime.timezone.utc) if start.tzinfo is None else start
        end = end.replace(tzinfo=datetime.timezone.utc) if end.tzinfo is None else end
        if start > end:
            raise ValueError('Start date must not be after the end date')
    if 'description' in data and data['description'] is not None and (not isinstance(data['description'], str) or len(data['description'].encode()) > 1024*1024):
        raise ValueError('Task description must be text no larger than 1 MiB')
    return prepared


class TaskInspectorCmd(Command):
    def check_security(self):
        _require_admin()
        return True

    def execute(self):
        _require_admin()
        action = self.kwargs.get('action', 'read')
        if action not in ('read', 'save', 'copy', 'delete'):
            raise ValueError('Unsupported task operation')
        if action != 'read':
            search = Search('sthpw/task')
            sql = search.get_sql()
            # ponytail: table lock; use row locks if simultaneous task edits contend.
            sql.get_database_impl().lock_collection_table(sql, SearchType.get('sthpw/task').get_table())
        parent, process, tasks, selected, defaults, revision, pipeline = task_scope(
            self.kwargs.get('search_key'), self.kwargs.get('process'), self.kwargs.get('task_key', ''))
        node = pipeline.get_process(process) if pipeline else None
        if node and node.get_type() == 'progress':
            if action != 'read':
                raise ValueError('This process has no editable task')
            discussion = DiscussionReadCmd(search_key=parent.get_search_key(), process=process).execute()
            notes = discussion['notes']
            related = related_tasks(parent, pipeline, process)
            choices, _process_notes = inspector_processes(parent, pipeline, process)
            for choice in choices:
                if choice['value'] == process:
                    choice.update(approved=related['approved'], total=related['total'])
            return dict(search_key=parent.get_search_key(), process=process, process_type='progress',
                object=inspector_object(parent), work_hours=None,
                related=related, processes=choices,
                selected_task='', task_choices=[], task={}, fields=[], statuses=[], users=[], defaults={}, revision=revision,
                notes=[dict(note, target_key=parent.get_search_key(), entry_type='note') for note in notes], history=[],
                identities=discussion['identities'],
                note_target=parent.get_search_key(), current_user=Environment.get_user_name())
        if action != 'read' and self.kwargs.get('expected_revision') != revision:
            raise UserException('Tasks changed. Reload before saving.')
        if action in ('copy', 'delete'):
            if selected is None:
                raise ValueError('Choose an existing task')
            assigned = self.kwargs.get('assigned', '')
            if action == 'copy' and (not isinstance(assigned, str) or assigned and Search.get_by_code('sthpw/login', assigned) is None):
                raise ValueError('Choose an existing user')
            callback = TaskElementCbk()
            callback.set_sobject(parent)
            callback.set_data({'assigned|%s|%s' % ('COPY' if action == 'copy' else 'DELETE', selected.get_id()): assigned})
            Command.execute_cmd(callback)
            if action == 'delete':
                return dict(task_key='')
            clone = callback.get_sobjects()[0]
            return dict(task_key=clone.get_search_key())
        task, fields, statuses, users = task_edit_options(parent, selected, defaults)
        if action == 'save':
            prepared = prepare_task_data(task, selected, defaults, fields, statuses, users, self.kwargs.get('data'))
            for name, value in prepared.items():
                task.set_value(name, value, allow_none=True)
            task.commit()  # Native rights, status log and workflow triggers, same transaction.
            return dict(task_key=task.get_search_key())
        primary = not selected or selected is tasks[0] or len(tasks) == 1
        note_target = parent if primary else selected
        notes = []
        for target in ([parent, selected] if primary and selected and len(tasks) == 1 else [note_target]):
            cmd = DiscussionReadCmd(search_key=target.get_search_key(), process=process, include_identities=False)
            result = cmd.execute()
            for note in result['notes']:
                notes.append(dict(note, target_key=target.get_search_key(), entry_type='note'))
        history = []
        if selected:
            search = Search('sthpw/status_log'); search.add_relationship_filters([selected]); search.add_order_by('timestamp')
            history = [dict(id=log.get_id(), timestamp=str(log.get_value('timestamp')),
                login=log.get_value('login'), before=log.get_value('from_status'), after=log.get_value('to_status'),
                entry_type='status', process=process) for log in search.get_sobjects()]
        processes, process_notes = inspector_processes(parent, pipeline, process)
        from tactic_stream.server.security_groups import user_identities
        logins = {item['login'] for item in [*notes, *history] if item['login']}
        logins.update(task.get_value(name) for task in tasks for name in ('assigned', 'supervisor') if task.get_value(name))
        identity_fields = ('login', 'displayName', 'retired', 'initials', 'avatarColor', 'avatarUrl')
        identities = [{name: user[name] for name in identity_fields} for user in users if user['login'] in logins]
        missing = logins - {user['login'] for user in identities}
        if missing:
            search = Search('sthpw/login'); search.set_show_retired(True); search.add_filters('login', list(missing))
            identities.extend(user_identities(search.get_sobjects()))
        from .work_hours import task_hours
        return dict(search_key=parent.get_search_key(), process=process, process_type=node.get_type() if node else 'manual', selected_task=selected.get_search_key() if selected else '',
            object=inspector_object(parent), work_hours=task_hours(selected) if selected else None,
            process_available=bool(node), task_context=task.get_value('context'),
            status_choices=[dict(value=name,label=name,color=(task.get_pipeline().get_process(name).get_attribute('color') or '')) for name in statuses],
            task_choices=[dict(value=item.get_search_key(), label=' · '.join(str(item.get_value(name) or '') for name in ('context', 'assigned')),
                primary=index == 0, status=item.get_value('status'),
                count=sum(note.get_process() == process and (same_note_target(note, item) or
                    index == 0 and same_note_target(note, parent)) for note in process_notes),
                identity=next((identity for identity in identities if identity['login'] == item.get_value('assigned')),None)) for index,item in enumerate(tasks)],
            task={field['name']: task.get_value(field['name'], no_exception=True) for field in fields},
            fields=fields, statuses=statuses, users=users, identities=identities, defaults=defaults, revision=revision, processes=processes, notes=notes, history=history,
            note_target=note_target.get_search_key(), current_user=Environment.get_user_name())


class TaskTableEditCmd(Command):
    """Handler table task drafts, committed together through native SObjects."""
    FIELDS = {'status', 'assigned', 'bid_start_date', 'bid_end_date'}

    def check_security(self):
        _require_admin()
        return True

    @staticmethod
    def scope(item):
        if not isinstance(item, dict) or any(not isinstance(item.get(name, ''), str)
                for name in ('search_key', 'task_key', 'process', 'context')):
            raise ValueError('Invalid task selection')
        parent, process, tasks, selected, defaults, revision, pipeline = task_scope(
            item.get('search_key'), item.get('process'), item.get('task_key', ''))
        context = item.get('context') or process
        if not item.get('task_key'):
            selected = next((task for task in tasks if (task.get_value('context') or process) == context), None)
        if selected and (selected.get_value('context') or process) != context:
            raise ValueError('Task context does not match the selected cell')
        node = pipeline.get_process(process) if pipeline else None
        if node and node.get_type() in ('progress', 'action', 'condition', 'dependency'):
            raise ValueError('This process has no editable task')
        if not selected and (context != process or not node):
            raise ValueError('The task process is unavailable for a selected row.')
        defaults['context'] = context
        return parent, selected, defaults, revision

    def execute(self):
        _require_admin()
        action = self.kwargs.get('action', 'prepare')
        if action == 'prepare':
            source = self.kwargs.get('source')
            parent, selected, _defaults, _revision = self.scope(source)
            context = selected.get_value('context') if selected else source['process']
            keys = self.kwargs.get('search_keys', [source['search_key']])
            if not isinstance(keys, list) or not 1 <= len(keys) <= 500 or not all(isinstance(key, str) and key for key in keys):
                raise ValueError('Choose between 1 and 500 task rows')
            plans, seen = [], set()
            for key in dict.fromkeys(keys):
                same_source = (key == source['search_key'] or SearchKey.extract_code(key) == parent.get_code()
                               or SearchKey.extract_id(key) == str(parent.get_id()))
                item = dict(search_key=key, process=source['process'], context=context,
                    task_key=source.get('task_key', '') if same_source else '')
                target, task, defaults, revision = self.scope(item)
                if target.get_base_search_type() != parent.get_base_search_type():
                    raise ValueError('Select rows of the same object type')
                canonical = target.get_search_key()
                if canonical in seen:
                    continue
                seen.add(canonical)
                virtual, fields, statuses, users = task_edit_options(target, task, defaults)
                status_pipeline = virtual.get_pipeline()
                plans.append(dict(search_key=canonical, process=source['process'], context=context,
                    task_key=task.get_search_key() if task else '', expected_revision=revision,
                    task={name: virtual.get_value(name, no_exception=True) for name in self.FIELDS},
                    fields=[field for field in fields if field['name'] in self.FIELDS], statuses=statuses, users=users,
                    colors={name: status_pipeline.get_process(name).get_color() for name in statuses}))
            return dict(plans=plans)
        if action not in ('save', 'check'):
            raise ValueError('Unsupported table task operation')
        plans = self.kwargs.get('plans')
        if not isinstance(plans, list) or not 1 <= len(plans) <= 500:
            raise ValueError('Choose between 1 and 500 task changes')
        if action == 'save':
            sql = Search('sthpw/task').get_sql()
            # Same native lock as Inspector; preflight the entire packet before writing.
            sql.get_database_impl().lock_collection_table(sql, SearchType.get('sthpw/task').get_table())
        prepared, states, seen = [], [], set()
        for plan in plans:
            parent, selected, defaults, revision = self.scope(plan)
            identity = (parent.get_search_key(), plan['process'], plan.get('context') or plan['process'],
                        selected.get_id() if selected else '')
            if identity in seen:
                raise ValueError('Duplicate task changes')
            seen.add(identity)
            data = plan.get('data')
            if not isinstance(data, dict) or not data or set(data) - self.FIELDS:
                raise ValueError('Unsupported table task fields')
            if action == 'check':
                visible = {field['name'] for field in task_fields()}
                if set(data) - visible:
                    raise SecurityException('Task fields are not accessible')
                matches = selected is not None
                for name, value in data.items():
                    actual = selected.get_value(name, no_exception=True) if selected else None
                    if name.endswith('_date'):
                        from pyasm.common import SPTDate
                        actual = SPTDate.add_gmt_timezone(parser.parse(str(actual))) if actual else None
                        value = SPTDate.add_gmt_timezone(parser.parse(str(value))) if value else None
                    matches = matches and (actual or '') == (value or '')
                states.append('unchanged' if revision == plan.get('expected_revision') else 'saved' if matches else 'conflict')
                continue
            if revision != plan.get('expected_revision'):
                raise UserException('Tasks changed. Reload before saving.')
            task, fields, statuses, users = task_edit_options(parent, selected, defaults)
            changes = prepare_task_data(task, selected, defaults, fields, statuses, users, data)
            prepared.append((plan, task, changes))
        if action == 'check':
            return dict(state=states[0] if len(set(states)) == 1 else 'conflict')
        result = []
        for plan, task, changes in prepared:
            for name, value in changes.items():
                task.set_value(name, value, allow_none=True)
            task.commit()
            result.append(dict(search_key=plan['search_key'], process=plan['process'],
                context=plan.get('context') or plan['process'], task_key=task.get_search_key()))
        return dict(tasks=result)
