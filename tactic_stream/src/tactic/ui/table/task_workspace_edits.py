"""Handler Task Manager field catalog and staged writes on native TACTIC.

Sources: thlib/ui/task_workspace/field_catalog.py and thlib/ui/tasks.py, EPL-1.0.
"""
import hashlib
import json

from pyasm.biz import Pipeline, Project, ProjectSetting
from pyasm.command import Command
from pyasm.common import UserException, SecurityException
from pyasm.search import Search, SearchType
from tactic.ui.widget.discussion_wdg import discussion_target
from .task_inspector import task_fields, task_scope, task_processes, task_edit_options, prepare_task_data, task_permissions, task_status_names, require_task_access


ADDITIONAL_FIELDS = ('process', 'context', 'priority', 'milestone_code')


def task_field_catalog(parent_key=''):
    """Resolve priority from the native XML input and project milestones."""
    require_task_access()
    parent = discussion_target(parent_key) if parent_key else Project.get()
    permissions = task_permissions(parent)
    fields = task_fields(ADDITIONAL_FIELDS, writable=permissions['edit'] or permissions['create'])
    visible = {field['name'] for field in fields}
    priorities, milestones, sources = [], [], []
    if 'priority' in visible:
        from tactic.ui.panel.edit_wdg import EditWdg
        widget = EditWdg(search_type='sthpw/task', view='insert', mode='insert',
                         parent_key=parent_key or None, element_names='priority')
        widget.explicit_display()
        for item in widget.get_widgets():
            if (item.get_option('column') or item.name) != 'priority':
                continue
            prepared = getattr(item, 'input', item)
            if hasattr(prepared, 'get_select_values'):
                labels, values = prepared.get_select_values()
            else:
                action = widget.config.get_action_options(item.name)
                values, labels = (item.get_option(name) or action.get(name) or [] for name in ('values', 'labels'))
                values = values.split('|') if isinstance(values, str) else list(values)
                labels = labels.split('|') if isinstance(labels, str) else list(labels)
                if item.get_option('values_expr'):
                    values = Search.eval(item.get_option('values_expr'), single=False) or []
                if item.get_option('labels_expr'):
                    labels = Search.eval(item.get_option('labels_expr'), single=False) or []
            priorities = [dict(value=value, label=str(labels[index] if index < len(labels) else value), color='')
                          for index, value in enumerate(values)]
        if not any(item['value'] in (None, '') for item in priorities):
            priorities.insert(0, dict(value='', label='No priority', color=''))
        config = Search('config/widget_config'); config.add_filter('search_type', 'sthpw/task')
        sources = [row.get_data() for row in config.get_sobjects()]
    if 'milestone_code' in visible:
        search = Search('sthpw/milestone'); search.add_filter('project_code', Project.get_project_code())
        search.add_order_by('due_date'); search.add_order_by('description')
        rows = search.get_sobjects()
        milestones = [dict(value='', label='No milestone', dueDate='')] + [dict(value=row.get_code(),
            label=row.get_value('description') or row.get_code() or 'Milestone', dueDate=str(row.get_value('due_date') or ''))
            for row in rows if row.get_code()]
        sources.extend(row.get_data() for row in rows)
    processes = []
    if parent.get_base_search_type() == 'sthpw/project':
        from .task_element_wdg import TaskElementWdg
        if TaskElementWdg.can_view_process('task'):
            processes = [dict(value='task', label='task', type='manual', color='')]
    elif parent and 'process' in visible:
        pipeline = Pipeline.get_by_code(parent.get_value('pipeline_code', no_exception=True))
        processes = [choice for choice in task_processes(parent, pipeline, '') if choice['type'] != 'progress']
    result = dict(priorityChoices=priorities, milestoneChoices=milestones, fields=fields, processes=processes, permissions=permissions,
                  bidDurationUnit=ProjectSetting.get_value_by_key('bid_duration_unit') or 'hour',
                  project=Project.get_project_code(), parent_key=parent.get_search_key() if parent else '')
    result['statusChoices'] = [dict(value=name, label=name, color='') for name in task_status_names(SearchType.create('sthpw/task'))]
    users = Search('sthpw/login'); users.add_order_by('display_name'); users.add_order_by('login')
    from tactic_stream.server.security_groups import user_directory
    result['users'] = [dict(**user, value=user['login'], label=user['displayName'])
                       for user in user_directory(users.get_sobjects())]
    groups = Search('sthpw/login_group'); groups.add_order_by('login_group')
    result['teams'] = [dict(value=group.get_code(), label=group.get_value('description') or group.get_code())
                       for group in groups.get_sobjects()]
    changes = Search('sthpw/sobject_log')
    changes.add_filters('search_type', list(dict.fromkeys(['sthpw/milestone', 'config/widget_config',
        Project.get_full_search_type('config/widget_config'), 'config/widget_config?project=' + Project.get_project_code()])))
    changes.add_order_by('id desc'); changes.add_limit(1)
    latest = changes.get_sobject()
    result['revision'] = hashlib.sha256(json.dumps(dict(catalog=result, sources=sources, journal=latest.get_id() if latest else None),
                                                 sort_keys=True, default=str).encode()).hexdigest()
    return result


def workspace_edit_plan(item, catalogs, read_only=False):
    if not isinstance(item, dict) or any(not isinstance(item.get(name, ''), str)
            for name in ('search_key', 'task_key', 'process', 'context', 'draft_id')):
        raise ValueError('Invalid task draft')
    operation = item.get('operation', 'update')
    if operation not in ('create', 'update', 'delete') or operation != 'create' and not item.get('task_key') or operation == 'create' and item.get('task_key'):
        raise ValueError('Choose task creation or an existing task')
    if operation == 'create' and (not item.get('draft_id') or len(item['draft_id']) > 128):
        raise ValueError('A task draft identity is required')
    parent, process, tasks, selected, defaults, revision, pipeline = task_scope(
        item.get('search_key'), item.get('process'), item.get('task_key', ''))
    if not read_only and operation in ('create', 'delete') and not task_permissions(parent)[operation]:
        raise SecurityException('Task write access denied')
    node = pipeline.get_process(process) if pipeline else None
    if node and node.get_type() == 'progress':
        raise ValueError('This process has no editable task')
    if operation == 'create':
        selected = None
        defaults['context'] = item.get('context') or process
        if len(defaults['context']) > 1024 or any(ord(char) < 32 for char in defaults['context']):
            raise ValueError('Choose a valid task context')
    if operation == 'delete':
        deletion, deletion_revision = task_deletion(selected)
        return parent, selected, selected, dict(operation=operation, draft_id=item.get('draft_id', ''),
            search_key=parent.get_search_key(), task_key=selected.get_search_key(), process=process,
            expected_revision=revision, deletion=deletion, deletion_revision=deletion_revision)
    task, fields, statuses, users = task_edit_options(parent, selected, defaults, ADDITIONAL_FIELDS)
    key = parent.get_search_key()
    if key not in catalogs:
        catalogs[key] = task_field_catalog(key)
    catalog = catalogs[key]
    plan = dict(operation=operation, draft_id=item.get('draft_id', ''), search_key=key,
        task_key=selected.get_search_key() if selected else '', process=process, context=task.get_value('context') or process,
        expected_revision=revision, catalog_revision=catalog['revision'],
        defaults={field['name']: defaults[field['name']] for field in fields if field['name'] in defaults},
        task={field['name']: task.get_value(field['name'], no_exception=True) for field in fields},
        fields=fields, statuses=statuses, users=users, catalog=catalog,
        statusChoices=[dict(value=name, label=task.get_pipeline().get_process(name).get_label() or name,
                            color=task.get_pipeline().get_process(name).get_color()) for name in statuses])
    return parent, selected, task, plan


def task_deletion(task):
    from tactic_stream.server.object_operations import read_deletion
    definition = read_deletion('sthpw/task', task.get_search_key())
    dependencies = {group['search_type']: [row.get_data() for row in task.get_related_sobjects(group['search_type'], show_retired=True)]
                    for group in definition['groups']}
    revision = hashlib.sha256(json.dumps(dict(task=task.get_data(), definition=definition, dependencies=dependencies),
                                        sort_keys=True, default=str).encode()).hexdigest()
    return definition, revision


class TaskWorkspaceEditCmd(Command):
    """Prepare or atomically save Task Manager inserts, edits and dependency deletion."""
    def check_security(self):
        require_task_access()
        return True

    def execute(self):
        require_task_access()
        action = self.kwargs.get('action', 'prepare')
        if action not in ('prepare', 'save'):
            raise ValueError('Unsupported task workspace edit operation')
        items = self.kwargs.get('plans')
        if not isinstance(items, list) or not 1 <= len(items) <= 500:
            raise ValueError('Choose between 1 and 500 task drafts')
        if action == 'save':
            # ponytail: native collection locks; per-parent locks if measured contention warrants it.
            locked = ['sthpw/task', 'config/widget_config', 'sthpw/milestone']
            if any(isinstance(item, dict) and item.get('operation') == 'delete' for item in items):
                locked.extend([*SearchType.get_related_types('sthpw/task', direction='children'), 'sthpw/file'])
            for name in dict.fromkeys(locked):
                sql = Search(name).get_sql()
                sql.get_database_impl().lock_collection_table(sql, SearchType.get(name).get_table())
        seen, prepared, plans, catalogs = set(), [], [], {}
        for item in items:
            parent, selected, task, plan = workspace_edit_plan(item, catalogs)
            if action == 'save' and not task_permissions(parent)['edit' if plan['operation'] == 'update' else plan['operation']]:
                raise SecurityException('Task write access denied')
            identity = ('create', plan['draft_id']) if not selected else ('update', selected.get_id())
            if identity in seen:
                raise ValueError('Duplicate task drafts')
            seen.add(identity)
            plans.append(plan)
            if action == 'prepare':
                if plan['operation'] != 'delete':
                    plan['defaults'] = {name: value for name, value in plan['defaults'].items()
                                        if name in {field['name'] for field in plan['fields']}}
                continue
            if item.get('expected_revision') != plan['expected_revision']:
                raise UserException('Tasks or task configuration changed. Reload before saving.')
            if plan['operation'] == 'delete':
                related = item.get('related_types')
                allowed = {group['search_type'] for group in plan['deletion']['groups']}
                if not isinstance(related, list) or any(not isinstance(value, str) for value in related) or set(related) - allowed:
                    raise ValueError('Dependency selection changed. Reopen the deletion dialog.')
                if item.get('deletion_revision') != plan['deletion_revision']:
                    raise UserException('Task dependencies changed. Reopen the deletion dialog.')
                prepared.append((plan, task, related))
                continue
            if item.get('catalog_revision') != plan['catalog_revision']:
                raise UserException('Tasks or task configuration changed. Reload before saving.')
            data = item.get('data')
            if not isinstance(data, dict) or not data:
                raise ValueError('Task changes are required')
            for name in ('process', 'context'):
                if name in data and (not isinstance(data[name], str) or not data[name] or len(data[name]) > (256 if name == 'process' else 1024)
                                     or any(ord(char) < 32 for char in data[name])):
                    raise ValueError('Choose a valid task process and context')
            if 'process' in data and data['process'] != plan['process']:
                if plan['operation'] == 'create':
                    raise ValueError('Prepare the selected task process before saving')
                _parent, _process, _tasks, _selected, _defaults, _revision, pipeline = task_scope(parent.get_search_key(), data['process'])
                node = pipeline.get_process(data['process']) if pipeline else None
                if node and node.get_type() == 'progress':
                    raise ValueError('This process has no editable task')
            for name, choices in (('priority', plan['catalog']['priorityChoices']), ('milestone_code', plan['catalog']['milestoneChoices'])):
                if name in data and (data[name] is not None and type(data[name]) not in (str, int)
                    or str('' if data[name] is None else data[name]) not in {str('' if choice['value'] is None else choice['value']) for choice in choices}):
                    raise ValueError('Task priority or milestone is not accessible')
            changes = prepare_task_data(task, selected, plan['defaults'], plan['fields'], plan['statuses'], plan['users'], data)
            prepared.append((plan, task, changes))
        if action == 'prepare':
            return dict(plans=plans)
        results = []
        for plan, task, changes in prepared:
            if plan['operation'] == 'delete':
                if task_deletion(task)[1] != plan['deletion_revision']:
                    raise UserException('Task dependencies changed. Reopen the deletion dialog.')
                from tactic.ui.tools import DeleteCmd
                Command.execute_cmd(DeleteCmd(sobject=task, values=dict(related_types=['sthpw/task', *changes])))
                results.append(dict(draft_id=plan['draft_id'], task_key=plan['task_key'], operation='delete'))
                continue
            for name, value in changes.items():
                task.set_value(name, value, allow_none=True)
            task.commit()
            results.append(dict(draft_id=plan['draft_id'], task_key=task.get_search_key(), operation=plan['operation']))
        return dict(tasks=results)
