"""Conversation task access through the native table editor and schema relations."""
from pyasm.biz import Task
from pyasm.command import Command
from xml.etree import ElementTree as ET
from tactic.ui.panel.agent_request_cmd import selected_object, text
from tactic.ui.table.task_inspector import (
    TaskTableEditCmd, TaskInspectorCmd, task_fields, task_status_names,
    task_scope, task_edit_options, prepare_task_data,
)


def workflow(task, statuses):
    pipeline = task.get_pipeline()
    choices = []
    for name in statuses:
        process = pipeline.get_process(name)
        definition = pipeline.get_process_sobject(name)
        settings = definition.get_json_value('workflow', {}) if definition else {}
        choices.append(dict(value=name, label=process.get_label() or name,
            completion=process.get_attribute('completion') or None,
            mapping=settings.get('mapping') or None, type=process.get_type()))
    allowed = set(statuses)
    root = ET.fromstring(pipeline.get_value('pipeline'))
    return dict(statuses=choices, connections=[dict(source=edge.get('from'), target=edge.get('to'))
        for edge in root.findall('connect') if edge.get('from') in allowed and edge.get('to') in allowed])


def edit_scope(plan):
    from tactic.ui.panel.agent_actions_cmd import local_type
    parent = selected_object(plan['search_key'])
    local_type(parent.get_base_search_type())
    scope = task_scope(parent.get_search_key(), plan['process'], plan.get('task_key', ''))
    node = scope[-1].get_process(scope[1]) if scope[-1] else None
    if node and node.get_type() == 'progress':
        raise ValueError('This process has no editable task')
    return scope


def prepare_edits(values, request):
    keys = values.get('search_keys')
    if keys is None:
        keys = request['document']['context']['search_keys']
    if not isinstance(keys, list) or not 1 <= len(keys) <= 200 or not all(isinstance(key, str) for key in keys):
        raise ValueError('Choose between 1 and 200 task objects')
    result = dict(plans=[], workflows={}, fields=[], users=[])
    for key in dict.fromkeys(keys):
        item = selected_object(key)
        task = item if isinstance(item, Task) else None
        if task and task.get_parent() is None:
            raise ValueError('Task parent no longer exists')
        plan = dict(search_key=task.get_parent().get_search_key() if task else item.get_search_key(),
            process=task.get_value('process') if task else values.get('process', ''),
            task_key=task.get_search_key() if task else '')
        parent, process, tasks, selected, defaults, revision, pipeline = edit_scope(plan)
        virtual, fields, statuses, users = task_edit_options(parent, selected, defaults)
        code = virtual.get_pipeline().get_code()
        if code not in result['workflows']:
            result['workflows'][code] = workflow(virtual, statuses)
        result['fields'], result['users'] = fields, users
        result['plans'].append(dict(search_key=parent.get_search_key(), process=process,
            parent_title=parent.get_value('name', no_exception=True) or parent.get_value('title', no_exception=True) or parent.get_code(),
            task_key=selected.get_search_key() if selected else '', expected_revision=revision, workflow=code,
            values={field['name']:virtual.get_value(field['name'], no_exception=True) for field in fields}))
    return result


def verified_edits(result):
    for item in result['tasks']:
        task, parent, plan = task_plan(item['task_key'])
        if plan['expected_revision'] != item['expected_revision']:
            raise ValueError('Tasks changed after this operation. Read again before applying.')
    return result


def save_edits(changes):
    if not isinstance(changes, list) or not 1 <= len(changes) <= 200:
        raise ValueError('Choose between 1 and 200 task changes')
    from pyasm.search import Search, SearchType
    sql = Search('sthpw/task').get_sql()
    sql.get_database_impl().lock_collection_table(sql, SearchType.get('sthpw/task').get_table())
    prepared, seen = [], set()
    for plan in changes:
        if (not isinstance(plan, dict) or set(plan) != {'search_key','process','task_key','expected_revision','data'}
                or not all(isinstance(plan[name], str) for name in ('search_key','process','task_key','expected_revision'))):
            raise ValueError('Use a native task plan with data from tasks_prepare')
        for name in ('search_key','process','task_key','expected_revision'):
            text(plan[name], 2048, empty=name=='task_key')
        data = plan['data']
        if (not isinstance(data, dict) or not data or len(data)>16 or any(
                value is not None and (type(value) not in (str,int,float,bool)
                    or isinstance(value,str) and len(value)>12000) for value in data.values())):
            raise ValueError('Task fields must be bounded scalar values')
        parent, process, tasks, selected, defaults, revision, pipeline = edit_scope(plan)
        identity = (parent.get_search_key(), process, selected.get_search_key() if selected else '')
        if identity in seen:
            raise ValueError('Duplicate task changes')
        seen.add(identity)
        if revision != plan['expected_revision']:
            raise ValueError('Tasks changed. Reload before saving.')
        task, fields, statuses, users = task_edit_options(parent, selected, defaults)
        prepare_task_data(task, selected, defaults, fields, statuses, users, data)
        prepared.append((plan, selected is None))
    saved = []
    for plan, created in prepared:
        command = TaskInspectorCmd(action='save', **plan)
        Command.execute_cmd(command)
        saved.append((command.info['task_key'], created))
    result = dict(tasks=[], count=len(saved), created=sum(created for key,created in saved))
    for key, created in saved:
        task, parent, plan = task_plan(key)
        fields = task_fields()
        result['tasks'].append(dict(task_key=key, search_key=parent.get_search_key(), process=plan['process'],
            parent_title=parent.get_value('name', no_exception=True) or parent.get_value('title', no_exception=True) or parent.get_code(),
            created=created, expected_revision=plan['expected_revision'],
            values={field['name']:task.get_value(field['name'], no_exception=True) for field in fields}))
    return result


def task_plan(key):
    task = selected_object(key)
    if not isinstance(task, Task):
        raise ValueError('Choose an existing task')
    parent = task.get_parent()
    if parent is None:
        raise ValueError('Task parent no longer exists')
    plan = dict(search_key=parent.get_search_key(), task_key=task.get_search_key(),
                process=task.get_value('process'), context=task.get_value('context') or task.get_value('process'))
    parent, selected, defaults, revision = TaskTableEditCmd.scope(plan)
    return selected, parent, dict(plan, expected_revision=revision)


def note_scope(values):
    from tactic.ui.panel.agent_actions_cmd import local_type
    item = selected_object(values.get('search_key'))
    process = text(values.get('process', ''), 128, empty=True)
    if isinstance(item, Task):
        task, parent, plan = task_plan(item.get_search_key())
        local_type(parent.get_base_search_type())
        if process and process != plan['process']:
            raise ValueError('The comment process must match the selected task')
    else:
        local_type(item.get_base_search_type())
        if not process:
            return item, 'publish', None
        plan = dict(search_key=item.get_search_key(), process=process)
    state = TaskInspectorCmd(action='read', **plan).execute()
    return selected_object(state['note_target']), state['process'], state['notes']


def read_notes(values):
    from tactic.ui.widget.discussion_wdg import DiscussionReadCmd
    target, process, notes = note_scope(values)
    offset = values.get('offset', 0)
    if type(offset) is not int or offset < 0:
        raise ValueError('Invalid comment offset')
    if notes is None:
        notes = DiscussionReadCmd(search_key=target.get_search_key(), process=process, include_identities=False).execute()['notes']
    return dict(search_key=values['search_key'], target_key=target.get_search_key(), process=process,
                notes=notes[offset:offset+50], has_next=len(notes) > offset+50)


def add_note(values):
    from tactic.ui.widget.discussion_wdg import DiscussionAddNoteCmd, note_revision
    target, process, _notes = note_scope(values)
    note = values.get('note')
    if not isinstance(note, str) or not note.strip() or len(note) > 12000:
        raise ValueError('Use a nonempty comment of at most 12000 characters')
    command = DiscussionAddNoteCmd(search_key=target.get_search_key(), process=process, context=process, note=note)
    Command.execute_cmd(command)
    saved = selected_object(command.info['note']['__search_key__'])
    return dict(search_key=values['search_key'], target_key=target.get_search_key(), process=process,
                note_key=saved.get_search_key(), note=saved.get_value('note'), login=saved.get_value('login'),
                revision=note_revision(saved))


def verified_note(result):
    from tactic.ui.widget.discussion_wdg import note_revision
    note = selected_object(result['note_key'])
    if note_revision(note) != result['revision']:
        raise ValueError('The comment changed after this operation. Read it again before continuing.')
    return result


def read_tasks(values, request):
    from tactic.ui.panel.agent_actions_cmd import local_type
    from tactic_stream.server.result_items import relations, relation_search
    keys = values.get('search_keys')
    if keys is None:
        keys = request['document']['context']['search_keys']
    if not isinstance(keys, list) or not 1 <= len(keys) <= 200 or not all(isinstance(key, str) for key in keys):
        raise ValueError('Choose between 1 and 200 task objects')
    offset = values.get('offset', 0)
    if type(offset) is not int or offset < 0:
        raise ValueError('Invalid task offset')
    parents, tasks = {}, {}
    related = values.get('related_type', '')
    if related:
        local_type(related)
    for key in dict.fromkeys(keys):
        item = selected_object(key)
        if isinstance(item, Task):
            if related:
                raise ValueError('Choose a project object for related tasks')
            tasks[item.get_search_key()] = item
            continue
        local_type(item.get_base_search_type())
        if related:
            branch = next((branch for branch in relations(item) if branch['search_type']==related
                           and branch['path']==values.get('path', '')), None)
            if branch is None:
                raise ValueError('Choose a relationship from the project schema')
            query = relation_search(item, branch)
            query.set_limit(201)
            objects = query.get_sobjects()
        else:
            objects = [item]
        for parent in objects:
            parents[parent.get_search_key()] = parent
        if len(parents)>200:
            raise ValueError('Read related objects in pages, then select at most 200 for tasks')
    if parents:
        for task in Task.get_by_sobjects(list(parents.values())):
            tasks[task.get_search_key()] = task
    fields = {field['name']:field for field in task_fields()}
    if 'status' not in fields:
        raise ValueError('Task status is not accessible')
    page = sorted(tasks)[offset:offset+50]
    result = dict(tasks=[], workflows={}, total=len(tasks), has_next=offset+50<len(tasks))
    for key in page:
        task, parent, plan = task_plan(key)
        pipeline = task.get_pipeline()
        code = pipeline.get_code()
        if code not in result['workflows']:
            result['workflows'][code] = workflow(task, task_status_names(task))
        result['tasks'].append(dict(task_key=key, parent_key=parent.get_search_key(),
            parent_title=parent.get_value('name', no_exception=True) or parent.get_value('title', no_exception=True) or parent.get_code(),
            process=plan['process'], context=plan['context'], status=task.get_value('status'),
            pipeline=code, expected_revision=plan['expected_revision'], editable=fields['status']['editable']))
    return result


def status_plans(changes):
    if not isinstance(changes, list) or not 1 <= len(changes) <= 200:
        raise ValueError('Choose between 1 and 200 task status changes')
    plans, seen = [], set()
    for change in changes:
        if (not isinstance(change, dict) or set(change)!={'task_key','status','expected_revision'}
                or not all(isinstance(value, str) and value for value in change.values())):
            raise ValueError('Use task_key, status and expected_revision from tasks_read')
        text(change['task_key'], 2048)
        text(change['status'], 256)
        text(change['expected_revision'], 256)
        task, parent, plan = task_plan(change['task_key'])
        if task.get_search_key() in seen:
            raise ValueError('Duplicate task changes')
        seen.add(task.get_search_key())
        plans.append(dict(plan, expected_revision=change['expected_revision'], data=dict(status=change['status'])))
    return plans


def verified_statuses(changes):
    result = []
    for plan in status_plans(changes):
        task = selected_object(plan['task_key'])
        if task.get_value('status') != plan['data']['status']:
            raise ValueError('Task changed after this operation. Read again before applying.')
        result.append(dict(task_key=task.get_search_key(), status=task.get_value('status')))
    return dict(tasks=result, count=len(result))


def save_statuses(changes):
    plans = status_plans(changes)
    Command.execute_cmd(TaskTableEditCmd(action='save', plans=plans))
    return verified_statuses(changes)
