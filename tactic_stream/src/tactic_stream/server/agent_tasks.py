"""Conversation task access through the native table editor and schema relations."""
from pyasm.biz import Task
from pyasm.command import Command
from xml.etree import ElementTree as ET
from tactic.ui.panel.agent_request_cmd import selected_object, text
from tactic.ui.table.task_inspector import TaskTableEditCmd, task_fields, task_status_names


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
            choices = []
            for name in task_status_names(task):
                process = pipeline.get_process(name)
                definition = pipeline.get_process_sobject(name)
                workflow = definition.get_json_value('workflow', {}) if definition else {}
                choices.append(dict(value=name, label=process.get_label() or name,
                    completion=process.get_attribute('completion') or None,
                    mapping=workflow.get('mapping') or None, type=process.get_type()))
            allowed = {choice['value'] for choice in choices}
            root = ET.fromstring(pipeline.get_value('pipeline'))
            result['workflows'][code] = dict(statuses=choices, connections=[
                dict(source=edge.get('from'), target=edge.get('to')) for edge in root.findall('connect')
                if edge.get('from') in allowed and edge.get('to') in allowed])
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
