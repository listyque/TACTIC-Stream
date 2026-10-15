"""Native TaskElementWdg: batch selection, SDK text, ordering, fillers and ACL."""
import ast
from unittest.mock import patch
from pyasm.common import Environment
from pyasm.search import Search
from pyasm.biz import Schema
from tactic.ui.table import TaskElementWdg


def exercise(api, auth):
    # Cold imports must also work when command/file-upload loads biz first.
    import subprocess
    import sys
    cold = subprocess.run([sys.executable, '-B', '-c',
        'import pyasm.command; from pyasm.search import SObjectAttr; from pyasm.biz import SimpleStatusAttr; from tactic.ui.table import TaskElementWdg, TaskElementCbk, TaskCompletionWdg'],
        capture_output=True, text=True)
    assert cold.returncode == 0, cold.stderr
    def record(method, *args, **kwargs):
        result = api.dispatch(method, (auth, *args), kwargs)
        return ast.literal_eval(result) if isinstance(result, str) else result
    record('execute_cmd', 'tactic.core.schema_commands.SearchTypeCreatorCmd',
           dict(search_type_name='contract/task_parent', sobject_pipeline=True, process=['review', 'model']))
    key, other_key = [record('insert', 'contract/task_parent', dict(code='TASK_PARENT_'+letter))['__search_key__']
                      for letter in ('A', 'B')]
    record('insert', 'sthpw/pipeline', dict(code='admin/CELL_TASKS', project_code='admin',
        pipeline='<pipeline><process name="review" type="manual"/><process name="model" type="manual"/></pipeline>'))
    created = [record('create_task', key, process='model', subcontext=context, assigned='admin')
               for context in ('B', 'A')]
    created.append(record('create_task', key, process='review', assigned='admin'))
    record('create_task', other_key, process='model', assigned='admin')
    parents = [Search.get_by_search_key(key), Search.get_by_search_key(other_key)]
    empty = record('insert', 'contract/task_parent', dict(code='TASK_PARENT_EMPTY'))
    parents.append(Search.get_by_search_key(empty['__search_key__']))
    widget = TaskElementWdg(pipeline_code='admin/CELL_TASKS')
    widget.set_sobjects(parents)
    with patch.object(Search, 'get_sobjects', autospec=True, side_effect=Search.get_sobjects) as reads:
        widget.preprocess()
        native = widget.get_tasks()
        cell = widget.get_cell_value()
        widget.set_current_index(1); second = widget.get_cell_value()
        widget.set_current_index(2); assert widget.get_cell_value()['count'] == 0
        assert sum(call.args[0].get_base_search_type() == 'sthpw/task' for call in reads.call_args_list) == 1
        # Security also loads its account catalogue once; neither lookup is per row.
        assert sum(call.args[0].get_base_search_type() == 'sthpw/login' for call in reads.call_args_list) <= 2
    assert [task.get_value('context') for task in native] == ['review', 'model/A', 'model/B'], ([(task.get_value('context'), task.get_value('process')) for task in native], widget.tasks_dict, widget.get_pipeline_code())
    assert cell['text'].split(',')[0].startswith('review:') and cell['count'] == 3
    assert [task['taskCode'] for task in cell['tasks']] == [created[2]['code'], created[1]['code'], created[0]['code']]
    assert second['count'] == 1 and widget.get_tasks(parents[0])[0].get_id() == created[2]['id']
    assert widget.get_tasks(parents[0], pipeline_code='task') == []
    assert TaskElementWdg.is_editable() is False and TaskElementWdg.get_args_keys()['show_filler_tasks']
    assert all(task['taskSearchKey'] for task in cell['tasks'])
    assert all(task['assignedIdentity']['login'] == 'admin' for task in cell['tasks'])
    assert not any('password' in field for task in cell['tasks'] for field in task['assignedIdentity'])
    record('insert', 'config/widget_config', dict(search_type='contract/task_parent', view='task_preview',
        config='<config><task_preview><element name="tasks"><display class="tactic.ui.table.TaskElementWdg"/></element></task_preview></config>'))
    from tactic_stream.server.table_cells import read_table_cells
    mixed_keys = [key, parents[0].get_search_key(use_id=True), other_key]
    batch = read_table_cells('contract/task_parent', 'task_preview', mixed_keys)
    assert batch[key]['tasks']['count'] == batch[mixed_keys[1]]['tasks']['count'] == 3
    assert batch[other_key]['tasks']['count'] == 1
    assert all(task['assignedIdentity']['login'] == 'admin' for task in batch[key]['tasks']['tasks'])
    widget.set_option('show_filler_tasks', 'true')
    widget.set_current_index(1); filler = next(task for task in widget.get_tasks() if task.is_insert())
    assert filler.get_value('process') == 'review' and filler.get_value('search_code') == parents[1].get_code()
    # Reading another row must never mutate a previously returned virtual task.
    widget.set_current_index(0); widget.get_tasks()
    assert filler.get_value('search_code') == parents[1].get_code()
    widget.set_option('task_filter', 'context_only')
    assert [task.get_value('context') for task in widget.get_tasks() if not task.is_insert()] == ['model/A', 'model/B']
    widget.set_options(dict(show_filler_tasks='false', task_filter='process_only'))
    assert [task.get_value('context') for task in widget.get_tasks()] == ['review']
    security = Environment.get_security()
    original = security.check_access
    def access(group, keys, *args, **kwargs):
        if group == 'process' and isinstance(keys, list) and any(key.get('process') == 'review' for key in keys):
            return False
        return original(group, keys, *args, **kwargs)
    with patch.object(security, 'check_access', side_effect=access):
        widget.set_options(dict(task_filter='', show_current_pipeline_only='false', show_filler_tasks='true'))
        assert all(task.get_value('process') != 'review' for task in widget.get_tasks())
        # No pipeline must not bypass process ACL either.
        no_pipeline = TaskElementWdg(); no_pipeline.set_sobjects(parents)
        assert all(task.get_value('process') != 'review' for task in no_pipeline.get_tasks())
    widget.set_sobjects([]); assert widget.get_tasks() == []
    from tactic.ui.table import TaskCompletionWdg
    for task, status in zip(created, ('Complete', 'In Progress', 'Waiting')):
        record('update', task['__search_key__'], dict(status=status))
    completion = TaskCompletionWdg(); completion.set_sobjects(parents)
    with patch.object(Search, 'get_sobjects', autospec=True, side_effect=Search.get_sobjects) as reads:
        completion.preprocess(); first_completion = completion.get_cell_value()
        completion.set_current_index(1); completion.get_cell_value()
        completion.set_current_index(2); assert completion.get_cell_value()['completion'] is None
        assert sum(call.args[0].get_base_search_type() == 'sthpw/task' for call in reads.call_args_list) == 1
    assert first_completion['completion'] == (100+20+5)/3 and first_completion['text'] == '41.7%'
    from pyasm.biz import SimpleStatusAttr, Pipeline
    from pyasm.search import SearchType
    local = SearchType.create('sthpw/task')
    attr = SimpleStatusAttr('status', local); attr.pipeline = Pipeline.get_by_code('task')
    local.set_value('status', 'Assignment'); assert attr.get_percent_completion() == 0
    local.set_value('status', 'Unknown obsolete status'); assert attr.get_percent_completion() == -100
    ordinal = SearchType.create('sthpw/pipeline')
    ordinal.set_pipeline('<pipeline><process name="first"/><process name="last"/></pipeline>')
    attr.pipeline = ordinal; local.set_value('status', 'first')
    assert attr.get_percent_completion() == 50
    local.set_value('status', 'last'); assert attr.get_percent_completion() == 100
    completion.set_sobjects([Search.get_by_id('sthpw/task', created[0]['id'])])
    assert completion.get_text_value() == '100.0%'
    completion.set_option('task_expr', "@SOBJECT(sthpw/task['search_code','TASK_PARENT_A']['context','model/B'])")
    completion.set_sobjects(parents); assert completion.get_text_value() == '100.0%'
    completion.set_options(dict(task_expr='')); completion.set_sobjects([])
    assert completion.get_cell_value()['completion'] is None
    # The original computational selector remains our normal-case reference.
    from pathlib import Path
    source_path = Path(__file__).resolve().parents[3] / 'legacy/src/tactic/ui/table/task_element_wdg.py'
    if source_path.exists():
        source = source_path.read_text(encoding='utf-8-sig')
        tree = ast.parse(source)
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'TaskElementWdg')
        methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == '_get_tasks']
        reference = ast.ClassDef(name='SourceSelector', bases=[ast.Name(id='TaskElementWdg', ctx=ast.Load())], keywords=[], body=methods, decorator_list=[])
        namespace = vars(__import__('tactic.ui.table.task_element_wdg', fromlist=['TaskElementWdg'])).copy()
        exec(compile(ast.fix_missing_locations(ast.Module(body=[reference], type_ignores=[])), str(source_path), 'exec'), namespace)
        original_widget = namespace['SourceSelector'](pipeline_code='admin/CELL_TASKS')
        original_widget.set_sobjects(parents)
        widget.set_options(dict(show_filler_tasks='false', task_filter='', show_current_pipeline_only='true'))
        widget.set_sobjects(parents)
        assert [task.get_id() for task in original_widget.get_tasks()] == [task.get_id() for task in widget.get_tasks()]
    exercise_inspector(record, key, other_key, empty['__search_key__'], created)
    exercise_week(record)
    exercise_callbacks(record, source_path)
    exercise_related(api, auth)
    exercise_table_edits(record)
    exercise_workspace(record, api, auth)
    exercise_workspace_edits(record)
    exercise_milestones(record)


def exercise_milestones(record):
    from pyasm.biz import Milestone
    from pyasm.common import UserException, SecurityException
    command = 'tactic.ui.table.milestones.MilestoneCmd'
    def call(action='read', **values):
        return record('execute_cmd', command, dict(action=action, **values))['info']
    initial = call()
    created = call('create', expected_revision=initial['revision'], data=dict(description='Milestone contract', due_date='2030-01-09'))
    row = next(row for row in created['records'] if row['code'] == created['selected'])
    assert created['before_revision'] == initial['revision'] and created['revision'] != initial['revision']
    assert isinstance(Search.get_by_search_key(row['search_key']), Milestone)
    row = next(item for item in call()['records'] if item['code'] == row['code'])
    with patch.object(Search, 'get_sobjects', autospec=True, side_effect=Search.get_sobjects) as reads:
        call()
        assert sum(call.args[0].get_base_search_type() == 'sthpw/task' for call in reads.call_args_list) == 1
    for data, error in [(dict(description='MILESTONE CONTRACT', due_date='2030-01-09'), 'already exists'),
                        (dict(description='Other', due_date='2030-02-30'), 'valid milestone due'),
                        (dict(description='', due_date='2030-01-09'), 'name is required')]:
        try:
            call('create', expected_revision=created['revision'], data=data)
        except (ValueError, UserException) as exc:
            assert error in str(exc)
        else:
            raise AssertionError('Invalid milestone accepted')
    updated = call('update', code=row['code'], expected_revision=row['revision'], data=dict(description='Edited milestone', due_date='2030-01-10'))
    updated_row = next(item for item in call()['records'] if item['code'] == row['code'])
    try:
        call('update', code=row['code'], expected_revision=row['revision'], data=dict(description='Stale milestone', due_date='2030-01-11'))
    except UserException:
        pass
    else:
        raise AssertionError('Stale milestone revision accepted')
    # A -> B -> A native/XML-RPC writes must still invalidate the revision.
    record('update', row['search_key'], dict(description='External'))
    record('update', row['search_key'], dict(description='Edited milestone'))
    try:
        call('delete', code=row['code'], expected_revision=updated_row['revision'])
    except UserException:
        pass
    else:
        raise AssertionError('ABA edit bypassed milestone revision')
    parent = record('insert', 'contract/task_parent', dict(code='MILESTONE_PLAN_PARENT'))
    task = record('create_task', parent['__search_key__'], process='model', assigned='admin')
    record('update', task['__search_key__'], dict(milestone_code=row['code'], status='Complete',
        bid_start_date='2025-01-01', bid_end_date='2025-01-03', bid_duration=3, completion=7, pipeline_code='task'), triggers=False)
    loaded = call(); plan = next(item for item in loaded['records'] if item['code'] == row['code'])
    assert plan['completion'] == 100 and plan['taskCount'] == plan['completedCount'] == 1, plan
    assert plan['overdueCount'] == 0 and plan['planStartDate'] == '2025-01-01' and plan['plannedHours'] == 3
    record('update', task['__search_key__'], dict(s_status='retired'))
    retired = call(); assert next(item for item in retired['records'] if item['code'] == row['code'])['taskCount'] == 0
    try:
        call('delete', code=row['code'], expected_revision=next(item for item in retired['records'] if item['code'] == row['code'])['revision'])
    except UserException as exc:
        assert 'assigned to tasks' in str(exc)
    else:
        raise AssertionError('Retired task lost its milestone')
    # A native late write failure must roll back the entire Command.
    original = Milestone.commit
    def fail(obj, *args, **kwargs):
        original(obj, *args, **kwargs)
        raise ValueError('Milestone rollback')
    with patch.object(Milestone, 'commit', fail):
        try:
            call('update', code=row['code'], expected_revision=next(item for item in retired['records'] if item['code'] == row['code'])['revision'], data=dict(description='Rolled back', due_date='2030-01-09'))
        except ValueError:
            pass
        else:
            raise AssertionError('Late milestone failure accepted')
    assert next(item for item in call()['records'] if item['code'] == row['code'])['description'] == 'Edited milestone'
    security = Environment.get_security(); access = type(security).check_access
    def deny(self, group, keys, *args, **kwargs):
        if group == 'sobject_column' and isinstance(keys, dict) and keys.get('search_type') == 'sthpw/milestone' and keys.get('column') == 'description' and args[0] == 'edit':
            return False
        return access(self, group, keys, *args, **kwargs)
    with patch.object(type(security), 'check_access', deny):
        restricted = call(); assert not restricted['canCreate']
        try:
            call('update', code=row['code'], expected_revision=next(item for item in restricted['records'] if item['code'] == row['code'])['revision'], data=dict(description='Denied', due_date='2030-01-09'))
        except SecurityException:
            pass
        else:
            raise AssertionError('Milestone field ACL bypassed')
    record('update', task['__search_key__'], dict(milestone_code='', s_status=''))
    current = call(); deleted = call('delete', code=row['code'], expected_revision=next(item for item in current['records'] if item['code'] == row['code'])['revision'])
    assert not any(item['code'] == row['code'] for item in deleted['records'])


def exercise_workspace_edits(record):
    from pyasm.common import UserException
    from pyasm.biz import Task
    command = 'tactic.ui.table.task_workspace_edits.TaskWorkspaceEditCmd'
    parent = record('insert', 'contract/task_parent', dict(code='WORKSPACE_EDIT_PARENT', name='Task drafts'))
    parent_key = parent['__search_key__']
    record('insert', 'config/widget_config', dict(search_type='sthpw/task', view='insert', priority=200,
        config='<config><insert><element name="priority"><display class="SelectWdg"><values>0|1|2</values><labels>Low|Normal|High</labels></display></element></insert></config>'))
    milestone = record('insert', 'sthpw/milestone', dict(code='WORKSPACE_EDIT_MILESTONE', project_code='admin', description='Release', due_date='2030-01-09'))
    def call(action, plans):
        return record('execute_cmd', command, dict(action=action, plans=plans))['info']
    catalog = record('execute_cmd', 'tactic.ui.table.task_workspace.TaskWorkspaceCmd', dict(action='catalog', search_key=parent_key))['info']
    assert {str(item['value']) for item in catalog['priorityChoices']} == {'', '0', '1', '2'}
    assert next(item for item in catalog['milestoneChoices'] if item['value'] == milestone['code'])['label'] == 'Release'
    prepared = call('prepare', [dict(operation='create', draft_id='first', search_key=parent_key, process='model', context='model/first'),
                                dict(operation='create', draft_id='second', search_key=parent_key, process='model', context='model/second')])['plans']
    search = Search('sthpw/task'); search.add_filter('search_code', parent['code']); assert not search.get_sobjects()
    changes = [dict(plan, data=dict(status='Waiting', assigned='admin', supervisor='admin', priority='2', milestone_code=milestone['code'],
                                  description='Prepared task', bid_duration=8, bid_start_date='2030-01-07T09:00', bid_end_date='2030-01-07T17:00')) for plan in prepared]
    saved = call('save', changes)['tasks']; assert len(saved) == 2
    try:
        call('save', changes)
    except UserException:
        pass
    else:
        raise AssertionError('Task draft replay created duplicates')
    tasks = [Search.get_by_search_key(row['task_key']) for row in saved]
    def stored_tasks():
        return record('query', 'sthpw/task', filters=[['code', 'in', [task.get_code() for task in tasks]]])
    assert {task.get_value('context') for task in tasks} == {'model/first', 'model/second'}
    assert all(task.get_value('milestone_code') == milestone['code'] and str(task.get_value('priority')) == '2' for task in tasks)
    requests = [dict(search_key=parent_key, task_key=task.get_search_key(), process='model') for task in tasks]
    schedule_command = 'tactic.ui.table.task_schedule.TaskScheduleCmd'
    before_schedule = stored_tasks()
    projected = [dict(taskCode=row['__search_key__'], parentTitle=parent['name'], assigned=row['assigned'], progress=0,
                      start=row['bid_start_date'], end=row['bid_end_date']) for row in before_schedule]
    def schedule(**values):
        return record('execute_cmd', schedule_command, dict(records=projected, **values))['info']
    projection = schedule(action='projection', year=2030, month=1,
                          milestones=[dict(value=milestone['code'], label='Release', dueDate='2030-01-09')])
    assert len(projection['calendar']) == 42 and projection['gantt']['scheduled'] == 2
    assert projection['gantt']['milestones'][0]['label'] == 'Release'
    shifted = schedule(action='batch', operation='shift', amount=1, working_days=True)['edits']
    assert stored_tasks() == before_schedule, 'Schedule calculations must never write tasks'
    schedule_plans = call('prepare', requests)['plans']
    updates = []
    for plan in schedule_plans:
        changes = shifted[plan['task_key']]
        progress_field = next(field['name'] for field in plan['fields'] if field['name'] in ('progress', 'completion'))
        updates.append(dict(plan, data=dict(bid_start_date=changes['start'], bid_end_date=changes['end'], **{progress_field: 50})))
    call('save', updates)
    assert all(row['bid_start_date'].startswith('2030-01-08 09:00') and row['bid_end_date'].startswith('2030-01-08 17:00')
               and float(row.get('progress') or row.get('completion')) == 50 for row in stored_tasks())
    try:
        schedule(action='batch', operation='shift', amount=999999, working_days=True)
    except ValueError:
        pass
    else:
        raise AssertionError('Unbounded schedule calculation accepted')
    edits = call('prepare', requests)['plans']
    invalid = [dict(plan, data=dict(description='Should roll back', priority='1')) for plan in edits]
    invalid[-1]['data']['milestone_code'] = 'NO_SUCH_MILESTONE'
    try:
        call('save', invalid)
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid last task edit accepted')
    assert all(task['description'] == 'Prepared task' for task in stored_tasks())
    native_commit = Task.commit
    def fail_last(task, *args, **kwargs):
        if task.get_code() == tasks[-1].get_code():
            raise ValueError('Workspace late commit failure')
        return native_commit(task, *args, **kwargs)
    valid = [dict(plan, data=dict(description='Must be atomic', priority='1')) for plan in edits]
    with patch.object(Task, 'commit', fail_last):
        try:
            call('save', valid)
        except ValueError:
            pass
        else:
            raise AssertionError('Late commit failure did not roll back')
    assert all(task['description'] == 'Prepared task' for task in stored_tasks())
    call('save', valid)
    assert all(task['description'] == 'Must be atomic' for task in stored_tasks())
    stale = call('prepare', requests)['plans']
    record('update', milestone['__search_key__'], dict(description='Changed release'))
    try:
        call('save', [dict(stale[0], data=dict(priority='2'))])
    except UserException:
        pass
    else:
        raise AssertionError('Stale task field catalog accepted')
    record('update', milestone['__search_key__'], dict(description='Release'))
    try:
        call('save', [dict(stale[0], data=dict(priority='0'))])
    except UserException:
        pass
    else:
        raise AssertionError('A -> B -> A catalog change accepted')
    from pyasm.security import Security
    original_access = Security.check_access
    def access(security, group, key, mode, *args, **kwargs):
        if group == 'sobject_column' and isinstance(key, dict) and key.get('column') == 'priority' and mode == 'edit':
            return False
        return original_access(security, group, key, mode, *args, **kwargs)
    with patch.object(Security, 'check_access', access):
        readonly = call('prepare', requests)['plans']
        try:
            call('save', [dict(readonly[0], data=dict(priority='0'))])
        except ValueError:
            pass
        else:
            raise AssertionError('Read-only priority edited')
    current = call('prepare', requests)['plans']
    call('save', [dict(current[0], data=dict(process='review', context='review/custom', priority='0'))])
    stored = stored_tasks()
    assert next(row for row in stored if row['code'] == tasks[0].get_code())['process'] == 'review'
    requests = [dict(search_key=parent_key, task_key=row['__search_key__'], process=row['process']) for row in stored]
    note = record('insert', 'sthpw/note', dict(search_type='sthpw/task', search_code=tasks[0].get_code(), process='review', note='Dependency'))
    deletions = call('prepare', [dict(request, operation='delete') for request in requests])['plans']
    record('update', note['__search_key__'], dict(note='Changed dependency'))
    try:
        note_plan = next(plan for plan in deletions if plan['task_key'] == tasks[0].get_search_key())
        call('save', [dict(note_plan, related_types=[])])
    except UserException:
        pass
    else:
        raise AssertionError('Changed deletion dependencies accepted')
    deletions = call('prepare', [dict(request, operation='delete') for request in requests])['plans']
    delete_plans = [dict(plan, related_types=['sthpw/note'] if any(group['search_type'] == 'sthpw/note' for group in plan['deletion']['groups']) else []) for plan in deletions]
    native_delete = Task.delete
    def fail_delete(task, *args, **kwargs):
        if task.get_search_key() == delete_plans[-1]['task_key']:
            raise ValueError('Workspace late deletion failure')
        return native_delete(task, *args, **kwargs)
    with patch.object(Task, 'delete', fail_delete):
        try:
            call('save', delete_plans)
        except ValueError:
            pass
        else:
            raise AssertionError('Late deletion failure did not roll back')
    assert len(stored_tasks()) == 2
    assert record('query', 'sthpw/note', filters=[['code', note['code']]])
    deleted = call('save', delete_plans)['tasks']
    assert len(deleted) == 2 and not stored_tasks()
    assert not record('query', 'sthpw/note', filters=[['code', note['code']]])


def exercise_workspace(record, api, auth):
    import json
    import os
    from pathlib import Path
    from pyasm.common.errors import SecurityException
    from tactic.ui.table.task_workspace import TaskWorkspaceCmd
    command = 'tactic.ui.table.task_workspace.TaskWorkspaceCmd'
    parents = [record('insert', 'contract/task_parent', dict(code='WORKSPACE_PARENT_'+name, name='Workspace '+name))
               for name in ('A', 'B')]
    tasks = [record('create_task', parent['__search_key__'], 'model', assigned='admin') for parent in parents]
    extra = record('create_task', parents[0]['__search_key__'], 'model', subcontext='extra', assigned='admin')
    record('insert', 'sthpw/login_group', dict(login_group='workspace_team'))
    record('insert', 'sthpw/login_in_group', dict(login='admin', login_group='workspace_team'))
    record('insert', 'sthpw/login_group', dict(login_group='workspace_empty_team'))
    record('insert', 'sthpw/note', dict(search_type='contract/task_parent?project=admin',
        search_code=parents[0]['code'], process='model', note='Workspace root note'))
    def page(**values):
        return record('execute_cmd', command, dict(query=dict(filters=dict(text='WORKSPACE_PARENT')), **values))['info']
    first = page(scope='object', identity=parents[0]['__search_key__'], limit=1)
    assert first['total'] == 2 and first['loaded'] == 1 and first['hasMore']
    assert first['parents'][0]['code'] == parents[0]['code']
    second = page(scope='object', identity=parents[0]['__search_key__'], offset=1, limit=1)
    assert first['tasks'][0]['code'] != second['tasks'][0]['code'] and not second['hasMore']
    multiple = page(scope='multiple', search_keys=[parent['__search_key__'] for parent in parents])
    assert multiple['total'] == 3 and len(multiple['parents']) == 2
    assert sorted(task['__notes_count__'] for task in multiple['tasks']) == [0, 0, 1]
    for scope, identity in (('project', ''), ('user', 'admin'), ('team', 'workspace_team'),
                            ('search_type', 'contract/task_parent')):
        result = page(scope=scope, identity=identity)
        assert {task['code'] for task in result['tasks']} == {task['code'] for task in [*tasks, extra]}, scope
    assert page(scope='object')['total'] == 0
    assert page(scope='multiple')['total'] == 0
    assert page(scope='team', identity='workspace_empty_team')['total'] == 0
    assert page(scope='object', identity=parents[0]['__search_key__'].replace('code='+parents[0]['code'], 'id='+str(parents[0]['id'])))['total'] == 2
    for invalid in (dict(scope='other'), dict(scope='user', identity='no_such_login'),
                    dict(scope='search_type', identity='contract/task_parent?project=wrong'), dict(limit=501),
                    dict(offset=-1), dict(limit=True), dict(scope='team', identity='missing_team')):
        try:
            page(**invalid)
        except (ValueError, LookupError):
            pass
        else:
            raise AssertionError('Invalid workspace selection accepted: '+str(invalid))
    with patch.object(TaskElementWdg, 'can_view_process', return_value=False):
        blocked = page(scope='project')
        assert blocked['tasks'] == [] and blocked['total'] == 0 and blocked['facets'] == {}
    with patch('tactic.ui.table.task_workspace._require_admin', side_effect=SecurityException('denied')):
        try:
            TaskWorkspaceCmd(scope='project').execute()
        except SecurityException:
            pass
        else:
            raise AssertionError('Workspace read without authorization')
    # The unchanged Handler procedure remains the reference, not a rewritten mock.
    source_path = Path(os.environ['STREAM_HANDLER_QUERY_FILE']) if os.environ.get('STREAM_HANDLER_QUERY_FILE') else next(
        (parent / 'th_codex/thlib/tactic_query.py' for parent in Path(__file__).resolve().parents
         if (parent / 'th_codex/thlib/tactic_query.py').is_file()), None)
    if source_path and source_path.is_file():
        tree = ast.parse(source_path.read_text(encoding='utf-8'))
        node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'query_task_workspace_page')
        function = '\n'.join(source_path.read_text(encoding='utf-8').splitlines()[node.lineno-1:node.end_lineno])
        for sort in ('due', 'recent', 'object', 'user', 'process', 'status', 'priority', 'milestone'):
            query = dict(filters=dict(text='WORKSPACE_PARENT'), sort=sort, group='user', today='2030-01-07',
                         currentLogin='admin', labels=dict(assigned=[dict(value='admin', label='admin')], supervisor=[dict(value='admin', label='admin')]))
            filters = [('project_code', 'admin')]
            script = function+'\nreturn query_task_workspace_page('+repr(filters)+", [], 'admin', 100, 0, "+repr(query)+')'
            expected = json.loads(api.dispatch('execute_python_script', (auth, '', dict(code=script)))['info'])
            from tactic.ui.table.task_workspace import query_task_workspace_page
            actual = query_task_workspace_page(filters, [], 'admin', 100, 0, query)
            assert actual == expected, sort


def exercise_table_edits(record):
    from pyasm.biz import Task
    from pyasm.common import UserException, SecurityException
    from tactic.ui.table.task_inspector import TaskTableEditCmd
    command = 'tactic.ui.table.task_inspector.TaskTableEditCmd'
    parents = [record('insert', 'contract/task_parent', dict(code='TABLE_BATCH_'+letter,
        pipeline_code='admin/CELL_TASKS'))['__search_key__'] for letter in ('A', 'B', 'C')]
    first = record('create_task', parents[0], process='model')
    record('create_task', parents[1], process='model', assigned='admin')
    source = dict(search_key=parents[0], task_key=first['__search_key__'], process='model', context='model')
    def prepare():
        return record('execute_cmd', command, dict(source=source, search_keys=parents))['info']['plans']
    plans = prepare()
    assert len(plans) == 3 and not plans[2]['task_key']
    def tasks():
        return record('query', 'sthpw/task', [('search_code', 'in', ['TABLE_BATCH_A', 'TABLE_BATCH_B', 'TABLE_BATCH_C'])])
    before = tasks()
    assert len(before) == 2, 'Preparation must not create virtual tasks'
    for plan in plans:
        plan['data'] = dict(status='Waiting', assigned='admin', bid_start_date='2030-01-07T09:00', bid_end_date='2030-01-07T17:00')
    assert record('execute_cmd', command, dict(action='check', plans=plans))['info']['state'] == 'unchanged'
    result = record('execute_cmd', command, dict(action='save', plans=plans))['info']
    assert len(result['tasks']) == len(tasks()) == 3
    assert all(task['status'] == 'Waiting' and task['assigned'] == 'admin' for task in tasks())
    assert record('execute_cmd', command, dict(action='check', plans=plans))['info']['state'] == 'saved'
    try:
        record('execute_cmd', command, dict(action='save', plans=plans)); raise AssertionError('Creation retry duplicated a task')
    except UserException:
        pass

    assert len(tasks()) == 3
    plans = prepare()
    for plan in plans:
        plan['data'] = dict(status='Complete')
    plans[-1]['data']['status'] = 'INVALID_STATUS'
    before = tasks()
    try:
        record('execute_cmd', command, dict(action='save', plans=plans)); raise AssertionError('Invalid last row committed the first')
    except ValueError:
        pass
    assert tasks() == before
    plans[-1]['data']['status'] = 'Complete'
    commit, calls = Task.commit, []
    def fail_last(task, *args, **kwargs):
        commit(task, *args, **kwargs); calls.append(task.get_id())
        if len(calls) == 3:
            raise ValueError('Late batch task failure')
    with patch.object(Task, 'commit', fail_last):
        try:
            record('execute_cmd', command, dict(action='save', plans=plans)); raise AssertionError('Late failure did not roll back')
        except ValueError as error:
            assert 'Late batch task failure' in str(error)
    assert tasks() == before
    with patch('tactic.ui.table.task_inspector.task_fields', return_value=[dict(name='status', editable=False)]):
        try:
            record('execute_cmd', command, dict(action='save', plans=plans)); raise AssertionError('Read-only status updated')
        except ValueError:
            pass
    with patch.object(TaskElementWdg, 'can_view_process', return_value=False):
        try:
            prepare(); raise AssertionError('Denied process prepared')
        except SecurityException:
            pass
    assert tasks() == before
    record('update', first['__search_key__'], dict(description='Parallel edit'))
    assert record('execute_cmd', command, dict(action='check', plans=plans))['info']['state'] == 'conflict'
    try:
        record('execute_cmd', command, dict(action='save', plans=plans)); raise AssertionError('Stale batch overwrote parallel edit')
    except UserException:
        pass
    duplicate = record('create_task', parents[0], process='model', assigned='admin')
    alias = Search.get_by_search_key(parents[0]).get_search_key(use_id=True)
    chosen = record('execute_cmd', command, dict(source=dict(source, task_key=duplicate['__search_key__']), search_keys=[alias]))['info']['plans']
    assert chosen[0]['task_key'] == duplicate['__search_key__'], 'An id alias must retain the exact chosen task'


def exercise_inspector(record, key, other_key, empty_key, created):
    import json
    from pyasm.common import UserException
    def inspect(parent=key, process='model', **values):
        return record('execute_cmd', 'tactic.ui.table.task_inspector.TaskInspectorCmd',
                      dict(search_key=parent, process=process, **values))['info']
    def note(target, text, process):
        record('execute_cmd', 'tactic.ui.widget.discussion_wdg.DiscussionAddNoteCmd',
               dict(search_key=target, note=text, process=process, files=[]))
    note(key, 'Primary model branch', 'model')
    note(created[1]['__search_key__'], 'Secondary model branch', 'model')
    note(key, 'Single review parent', 'review')
    note(created[2]['__search_key__'], 'Single review task', 'review')
    primary = inspect()
    assert primary['selected_task'] == created[0]['__search_key__']
    assert primary['note_target'] == key and [note['body'] for note in primary['notes']] == ['Primary model branch']
    counts = {choice['value']:choice['count'] for choice in primary['processes']}
    assert counts['model'] == counts['review'] == 2, 'Process counts include secondary task branches in other processes'
    assert next(user for user in primary['identities'] if user['login'] == 'admin')['initials']
    assert all(set(user) == {'login', 'displayName', 'retired', 'initials', 'avatarColor', 'avatarUrl'} for user in primary['identities'])
    # Authors, task assignees and status-history actors share one identity batch.
    from tactic_stream.server.security_groups import user_identities
    with patch('tactic_stream.server.security_groups.user_identities', wraps=user_identities) as reads:
        inspect(process='review')
        assert reads.call_count == 1
    secondary = inspect(task_key=created[1]['__search_key__'])
    assert secondary['note_target'] == created[1]['__search_key__']
    assert [note['body'] for note in secondary['notes']] == ['Secondary model branch']
    review = inspect(process='review')
    assert {note['body'] for note in review['notes']} == {'Single review parent', 'Single review task'}
    assert review['history'] and all(item['entry_type'] == 'status' for item in review['history'])
    assert inspect(parent=created[1]['__search_key__'])['selected_task'] == created[1]['__search_key__']
    try:
        inspect(task_key=created[2]['__search_key__'])
        raise AssertionError('Foreign process task accepted')
    except LookupError:
        pass
    progress = next(field['name'] for field in secondary['fields'] if field['name'] in ('progress', 'completion'))
    data = dict(status='Approved', assigned='admin', supervisor='admin', description='Compact task edit',
                bid_start_date='2026-10-08T09:00', bid_end_date='2026-10-08T10:00+00:00', bid_duration=2, **{progress: 75})
    saved = inspect(task_key=secondary['selected_task'], action='save', expected_revision=secondary['revision'], data=data)
    assert saved['task_key'] == secondary['selected_task']
    after = inspect(task_key=saved['task_key'])
    assert after['task']['description'] == data['description'] and after['task'][progress] == 75
    assert after['history'][-1]['after'] == 'Approved' and after['history'][-1]['before'] == 'In Progress'
    exercise_hours(record, key, saved['task_key'], created[2]['__search_key__'])
    assert after['object']['record']['__search_key__'] == key and 'files' in after['object']['preview']
    for invalid in (dict(status='Unknown'), dict(assigned='missing-login'), dict(assigned={}), dict(bid_duration=float('nan')),
                    {progress: 101}, dict(bid_start_date='not-a-date'), dict(bid_end_date='2020-01-01'),
                    dict(project_code='foreign')):
        try:
            inspect(task_key=saved['task_key'], action='save', expected_revision=after['revision'], data=invalid)
            raise AssertionError('Invalid fields accepted: '+str(invalid))
        except ValueError:
            pass
        assert inspect(task_key=saved['task_key'])['revision'] == after['revision']
    from pyasm.biz import Task
    commit = Task.commit
    def fail_commit(task, *args, **kwargs):
        commit(task, *args, **kwargs)
        raise ValueError('Task failure after native commit')
    with patch.object(Task, 'commit', fail_commit):
        try:
            inspect(task_key=saved['task_key'], action='save', expected_revision=after['revision'], data={'status': 'Waiting'})
            raise AssertionError('Failed task commit accepted')
        except ValueError as error:
            assert 'Task failure' in str(error)
    rolled_back = inspect(task_key=saved['task_key'])
    assert rolled_back['revision'] == after['revision'] and rolled_back['history'] == after['history']
    try:
        inspect(action='save', task_key=saved['task_key'], expected_revision=secondary['revision'], data={'status': 'Waiting'})
        raise AssertionError('Stale task overwrite accepted')
    except UserException as error:
        assert 'Reload' in str(error)
    record('update', empty_key, dict(pipeline_code='admin/CELL_TASKS'))
    record('insert', 'config/process', dict(pipeline_code='admin/CELL_TASKS', process='review',
        workflow=json.dumps(dict(properties=dict(status='Waiting', assigned='admin', supervisor='admin',
            duration=1, bid_duration=8, completion=15)))))
    missing = inspect(parent=empty_key, process='review')
    assert missing['selected_task'] == '' and missing['task']['status'] == 'Waiting'
    assert missing['task']['assigned'] == 'admin' and missing['task']['bid_duration'] == 8
    assert missing['task']['bid_start_date'] and missing['task']['bid_end_date']
    created_key = inspect(parent=empty_key, process='review', action='save', expected_revision=missing['revision'], data={})['task_key']
    assert inspect(parent=empty_key, process='review')['selected_task'] == created_key
    try:
        inspect(parent=empty_key, process='review', action='save', expected_revision=missing['revision'], data={})
        raise AssertionError('Retried creation duplicated task')
    except UserException:
        pass
    assert len(inspect(parent=empty_key, process='review')['task_choices']) == 1
    copy = inspect(task_key=saved['task_key'], action='copy', assigned='reader', expected_revision=after['revision'])
    copied = inspect(task_key=copy['task_key'])
    assert copied['task']['assigned'] == 'reader' and len(copied['task_choices']) == 3
    assert copied['notes'] == []  # Task copying does not copy the discussion branch.
    note(copy['task_key'], 'Copy branch remains after delete', 'model')
    before_delete = inspect(task_key=copy['task_key'])
    try:
        inspect(task_key=copy['task_key'], action='delete', expected_revision=after['revision'])
        raise AssertionError('Stale task deletion accepted')
    except UserException:
        pass
    inspect(task_key=copy['task_key'], action='delete', expected_revision=before_delete['revision'])
    assert len(inspect()['task_choices']) == 2
    assert record('query', 'sthpw/note', [['note', 'Copy branch remains after delete']])
    from pyasm.biz import Pipeline
    pipeline = Pipeline(); pipeline.set_pipeline('<pipeline><process name="manual" type="manual"/><process name="action" type="action"/></pipeline>')
    assert pipeline.get_process_names(exclude=['action']) == ['manual']


def exercise_hours(record, parent_key, task_key, foreign_task):
    from pyasm.biz import WorkHour
    from pyasm.common import UserException
    def hours(**values):
        return record('execute_cmd', 'tactic.ui.table.work_hours.WorkHoursCmd',
            dict(search_key=parent_key, process='model', task_key=task_key, **values))['info']
    initial = hours()
    assert initial['summary']['planned'] == 2 and initial['entries'] == []
    from pyasm.biz import ProjectSetting
    with patch.object(ProjectSetting, 'get_value_by_key', return_value='minute'):
        assert hours()['summary']['planned'] == .03
    data = dict(day='2026-10-08', hours=1.25, category='overtime', description='Time test', login='admin')
    created = hours(action='create', data=data, expected_revision=initial['revision'])
    assert created['summary']['logged'] == created['summary']['overtime'] == created['summary']['pending'] == 1.25
    entry = created['entries'][0]['search_key']
    try:
        hours(action='create', data=data, expected_revision=initial['revision'])
        raise AssertionError('Retried entry creation duplicated time')
    except (ValueError, UserException):
        pass
    approved = hours(action='approve', entry_key=entry, expected_revision=created['revision'])
    assert approved['summary']['approved'] == 1.25 and approved['summary']['remaining'] == .75
    assert approved['summary']['progress'] == 62.5 and approved['summary']['pending'] == 0
    for invalid in (dict(hours=float('nan')), dict(hours=-1), dict(hours=25), dict(hours=.001),
                    dict(day='bad'), dict(login='missing'), dict(category='missing'), dict(approve='false'), dict(description={})):
        try:
            hours(action='update', entry_key=entry, data={**data, **invalid}, expected_revision=approved['revision'])
            raise AssertionError('Invalid time entry accepted: '+str(invalid))
        except (ValueError, UserException):
            pass
        assert hours()['revision'] == approved['revision']
    changed = hours(action='update', entry_key=entry, data={**data, 'hours': 3, 'login': 'reader'}, expected_revision=approved['revision'])
    assert changed['entries'][0]['login'] == 'reader' and changed['summary']['overPlan'] == 1
    foreign = record('execute_cmd', 'tactic.ui.table.work_hours.WorkHoursCmd',
                    dict(search_key=parent_key, process='review', task_key=foreign_task))['info']
    try:
        record('execute_cmd', 'tactic.ui.table.work_hours.WorkHoursCmd', dict(search_key=parent_key, process='review',
            task_key=foreign_task, action='delete', entry_key=entry, expected_revision=foreign['revision']))
        raise AssertionError('Entry from another task accepted')
    except (ValueError, UserException):
        pass
    # Legacy regular entries can contain extra over_time; count it in daily limits.
    record('update', entry, dict(category='regular', over_time=2, status='Approved'))
    legacy = hours(); assert legacy['summary']['logged'] == 5 and legacy['summary']['overtime'] == 2
    assert legacy['entries'][0]['status'] == 'approved' and legacy['summary']['approved'] == 5
    try:
        hours(action='create', data={**data, 'hours': 20, 'login': 'reader'}, expected_revision=legacy['revision'])
        raise AssertionError('Daily limit ignored legacy overtime')
    except (ValueError, UserException) as error:
        assert '24' in str(error)
    commit = WorkHour.commit
    def fail_commit(item, *args, **kwargs):
        commit(item, *args, **kwargs); raise ValueError('Failure after time commit')
    with patch.object(WorkHour, 'commit', fail_commit):
        try:
            hours(action='reject', entry_key=entry, expected_revision=legacy['revision'])
            raise AssertionError('Failed time commit accepted')
        except (ValueError, UserException):
            pass
    assert hours()['revision'] == legacy['revision']
    rejected = hours(action='reject', entry_key=entry, expected_revision=legacy['revision'])
    assert rejected['summary']['approved'] == 0 and rejected['summary']['pending'] == 5
    deleted = hours(action='delete', entry_key=entry, expected_revision=rejected['revision'])
    assert deleted['entries'] == [] and deleted['summary']['logged'] == 0


def exercise_week(record):
    from pyasm.biz import WorkHour, ProjectSetting
    from pyasm.common import UserException, SecurityException
    parent = record('insert', 'contract/task_parent', dict(code='WEEK_PARENT', pipeline_code='admin/CELL_TASKS'))['__search_key__']
    tasks = [record('create_task', parent, process='model', subcontext=name) for name in ('weekA', 'weekB')]
    scope = dict(search_key=parent, process='model', task_key=tasks[0]['__search_key__'])
    command = 'tactic.ui.table.work_hours.WorkHoursCmd'
    def call(mode='week', **values):
        return record('execute_cmd', command, dict(mode=mode, week='2030-01-09', login='', **values))['info']
    def add(index, day, amount, login='admin', category='regular', approve=False):
        args = dict(search_key=parent, process='model', task_key=tasks[index]['__search_key__'])
        before = record('execute_cmd', command, args)['info']
        after = record('execute_cmd', command, dict(args, action='create', expected_revision=before['revision'],
            data=dict(day=day, hours=amount, login=login, category=category, approve=approve)))['info']
        return next(item for item in after['entries'] if item['day'] == day)['search_key']
    first = add(0, '2030-01-07', 1.5)
    second = add(1, '2030-01-13', 2, 'reader', 'overtime', True)
    record('update', second, dict(day='2030-01-13 23:59:00'))
    outside = add(0, '2030-01-14', .5)
    orphan = record('insert', 'sthpw/work_hour', dict(project_code='admin', task_code='REMOVED_TASK',
        login='admin', process='model', day='2030-01-09', straight_time=.25))['__search_key__']
    foreign = record('insert', 'sthpw/work_hour', dict(project_code='sthpw', task_code=tasks[0]['code'],
        login='admin', process='model', day='2030-01-07', straight_time=4))['__search_key__']
    with patch.object(Search, 'get_sobjects', autospec=True, side_effect=Search.get_sobjects) as reads:
        week = call()
        assert sum(call.args[0].get_base_search_type() == 'sthpw/task' for call in reads.call_args_list) == 1
    assert week['week_start'] == '2030-01-07' and week['week_end'] == '2030-01-13'
    assert week['summary'] == dict(logged=3.75, approved=2, pending=1.75, overtime=2)
    assert {item['search_key'] for item in week['entries']} == {first, second, orphan}
    assert next(item for item in week['entries'] if item['search_key'] == orphan)['can_edit'] is False
    for invalid in ([first, outside], [first, foreign], [first, 'sthpw/work_hour?id=99999999']):
        try:
            call(action='approve', entry_keys=invalid, expected_revision=week['revision'])
            raise AssertionError('Foreign weekly selection accepted')
        except UserException:
            pass
        assert call()['revision'] == week['revision']
    commit = WorkHour.commit; calls = 0
    def fail_second(item, *args, **kwargs):
        nonlocal calls
        result = commit(item, *args, **kwargs); calls += 1
        if calls == 2:
            raise UserException('Failure in bulk time change')
        return result
    with patch.object(WorkHour, 'commit', fail_second):
        try:
            call(action='approve', entry_keys=[first, orphan], expected_revision=week['revision'])
            raise AssertionError('Partial bulk commit accepted')
        except UserException:
            pass
    assert call()['revision'] == week['revision']
    approved = call(action='approve', entry_keys=[first, orphan, first], expected_revision=week['revision'])
    assert approved['summary']['approved'] == 3.75
    try:
        call(action='reject', entry_keys=[first], expected_revision=week['revision'])
        raise AssertionError('Stale weekly change accepted')
    except UserException:
        pass
    pending = call(action='reject', entry_keys=[first, second, orphan], expected_revision=approved['revision'])
    assert pending['summary']['pending'] == 3.75
    edited = call(action='update', entry_key=second, expected_revision=pending['revision'],
        data=dict(day='2030-01-13', hours=2.5, category='overtime', login='reader', description='Weekly edit'))
    assert edited['summary']['logged'] == 4.25
    # Active task invalidates creation retries even outside the chosen week/user.
    active = call(**scope)
    created = call(**scope, action='create', expected_revision=active['revision'],
                   data=dict(day='2030-01-21', hours=.5, login='reader'))
    assert created['revision'] != active['revision']
    try:
        call(**scope, action='create', expected_revision=active['revision'], data=dict(day='2030-01-21', hours=.5, login='reader'))
        raise AssertionError('Out-of-week retry duplicated time')
    except UserException:
        pass
    record('update', 'sthpw/login?code=admin', dict(hourly_wage=10))
    record('update', 'sthpw/login?code=reader', dict(hourly_wage=5))
    for task, planned in zip(tasks, (120, 60)):
        record('update', task['__search_key__'], dict(bid_duration=planned, bid_end_date='2030-01-13 12:00:00'))
    for key in ('my_hours', 'bid_actual', 'approval', 'team', 'process', 'labor_cost'):
        with patch.object(ProjectSetting, 'get_value_by_key', return_value='minute'):
            report = call(mode='report', report=key)
        values = {row['label']: row['value'] for row in report['rows']}
        if key == 'bid_actual': assert values == dict(Planned=3, Logged=4.25), values
        elif key == 'approval': assert values == dict(Pending=4.25), values
        elif key == 'team': assert values == dict(admin=1.75, reader=2.5), values
        elif key == 'process': assert values == dict(model=4.25), values
        elif key == 'labor_cost': assert values == dict(admin=17.5, reader=12.5), values
        else: assert sum(values.values()) == 1.75
    security = Environment.get_security(); check_access = type(security).check_access
    def deny_wages(instance, group, keys, *args, **kwargs):
        if group == 'sobject_column' and keys.get('column') == 'hourly_wage': return False
        return check_access(instance, group, keys, *args, **kwargs)
    with patch.object(type(security), 'check_access', autospec=True, side_effect=deny_wages):
        assert 'labor_cost' not in {item['value'] for item in call(mode='report')['reports']}
        try:
            call(mode='report', report='labor_cost'); raise AssertionError('Wages exposed without access')
        except SecurityException:
            pass
    for bad in ('bad', '9999-12-31', {}):
        try:
            record('execute_cmd', command, dict(mode='week', week=bad)); raise AssertionError('Invalid week accepted')
        except UserException:
            pass
    before_delete = call(); deleted = call(action='delete', entry_key=orphan, expected_revision=before_delete['revision'])
    assert deleted['summary']['logged'] == 4
    for entry in record('query', 'sthpw/work_hour', [['task_code', tasks[0]['code']]]): record('delete_sobject', entry['__search_key__'])
    record('delete_sobject', second)


def exercise_callbacks(record, source_path):
    import json
    from pyasm.biz import Task
    from pyasm.command import Command
    from pyasm.common import TacticException, SecurityException
    from pyasm.web import Web, WebContainer
    from tactic.ui.table import TaskElementCbk
    parent = record('insert', 'contract/task_parent', dict(code='CBK_NATIVE', pipeline_code='admin/CELL_TASKS'))['__search_key__']
    payload = {'status|NEW|model': 'Waiting', 'assigned|NEW|model': 'admin', 'bid|NEW|model': 2, 'status|NEW|review': 'Waiting'}
    def callback(data, processes=None, values=None):
        args = dict(search_key=parent, data=data)
        if processes is not None:
            args['processes'] = processes
        return record('execute_cmd', 'tactic.ui.table.TaskElementCbk', args if values is None else {}, values or {})
    def tasks():
        return Task.get_by_sobjects([Search.get_by_search_key(parent)])
    # Normal legacy callback run against the same native objects; no legacy imports in the server.
    if source_path.exists():
        tree = ast.parse(source_path.read_text(encoding='utf-8-sig'))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'TaskElementCbk')
        cls.name = 'SourceTaskElementCbk'
        module = __import__('tactic.ui.table.task_element_wdg', fromlist=['TaskElementCbk'])
        namespace = vars(module).copy()
        namespace.update(jsonloads=json.loads, WebContainer=WebContainer)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), str(source_path), 'exec'), namespace)
        original_parent = record('insert', 'contract/task_parent', dict(code='CBK_SOURCE', pipeline_code='admin/CELL_TASKS'))['__search_key__']
        source = namespace['SourceTaskElementCbk'](); source.set_sobject(Search.get_by_search_key(original_parent)); source.set_data(json.dumps(payload))
        previous_web = WebContainer.get_web()
        try:
            WebContainer.set_web(Web(dict(web_data=dict(process_data=json.dumps(dict(processes=['model', 'review']))))))
            with patch.object(module, 'SourceTaskElementCbk', namespace['SourceTaskElementCbk'], create=True):
                source.get_transaction().set_sync(False); Command.execute_cmd(source)
        finally:
            WebContainer.set_web(previous_web)
        callback(json.dumps(payload), processes=['model', 'review'])
        def projection(items):
            return sorted(tuple(task.get_value(name) for name in ('process', 'context', 'status', 'assigned', 'bid_duration')) for task in items)
        assert projection(tasks()) == projection(Task.get_by_sobjects([Search.get_by_search_key(original_parent)]))
    else:
        callback(json.dumps(payload), processes=['model', 'review'])
    model = next(task for task in tasks() if task.get_value('process') == 'model')
    callback({f'status|EDIT|{model.get_id()}': 'Complete', f'assigned|EDIT|{model.get_id()}': 'reader', f'bid_duration|EDIT|{model.get_id()}': 4})
    changed = Search.get_by_id('sthpw/task', model.get_id())
    assert changed.get_value('status') == 'Complete' and changed.get_value('assigned') == 'reader' and changed.get_value('bid_duration') == 4
    old_ids = {task.get_id() for task in tasks()}
    callback({f'assigned|COPY|{model.get_id()}_123': 'admin'})
    clone = next(task for task in tasks() if task.get_id() not in old_ids)
    assert clone.get_value('process') == 'model' and clone.get_value('assigned') == 'admin' and clone.get_value('status') == 'Complete'
    callback({f'assigned|DELETE|{clone.get_id()}': ''})
    assert {task.get_id() for task in tasks()} == old_ids
    # Bug fixes: NEW without web_data and both bid field spellings.
    callback({'assigned|NEW|review': 'admin'})
    assert len(tasks()) == 3
    callback({f'bid|EDIT|{model.get_id()}': 7})
    assert next(task for task in tasks() if task.get_id() == model.get_id()).get_value('bid_duration') == 7
    before = {task.get_id() for task in tasks()}
    foreign = record('create_task', 'contract/task_parent?project=admin&code=TASK_PARENT_B', process='review')
    for data in ({f'assigned|EDIT|{foreign['id']}': 'admin'}, {'status|EDIT|999999999': 'Complete'}, '[]', '{broken'):
        try:
            callback(data)
            raise AssertionError('Invalid callback accepted')
        except TacticException:
            pass
        assert {task.get_id() for task in tasks()} == before
    with patch.object(TaskElementWdg, 'can_view_process', return_value=False):
        try:
            callback({f'status|EDIT|{model.get_id()}': 'Waiting'})
            raise AssertionError('Denied process updated')
        except SecurityException:
            pass
    commit = Task.commit
    def fail_commit(task, *args, **kwargs):
        commit(task, *args, **kwargs)
        raise ValueError('Callback failure after native commit')
    with patch.object(Task, 'commit', fail_commit):
        try:
            callback({'status|NEW|review': 'Waiting'})
            raise AssertionError('Callback rollback failed')
        except ValueError as error:
            assert 'Callback failure' in str(error)
    assert {task.get_id() for task in tasks()} == before
    callback(None, values=dict(search_key=parent, data=dict(data=json.dumps({f'bid|EDIT|{model.get_id()}': 9}))))
    assert next(task for task in tasks() if task.get_id() == model.get_id()).get_value('bid_duration') == 9
    # A script's identity lookup and callback execute within one real API context.
    code = '''from pyasm.search import Search
from pyasm.command import Command
from tactic.ui.table import TaskElementCbk
cached = Search.get_by_id('sthpw/task', kwargs['task_id'])
callback = TaskElementCbk()
callback.set_sobject(Search.get_by_search_key(kwargs['parent_key']))
callback.set_data({'bid|EDIT|%s' % cached.get_id(): 11})
Command.execute_cmd(callback)
return Search.get_by_id('sthpw/task', cached.get_id()).get_value('bid_duration')'''
    assert record('execute_python_script', '', dict(code=code, task_id=model.get_id(), parent_key=parent))['info'] == 11
    initial = record('insert', 'contract/task_parent', dict(code='CBK_INITIAL', pipeline_code='admin/CELL_TASKS'))['__search_key__']
    record('execute_cmd', 'tactic.ui.table.task_element_wdg.TaskElementCbk', dict(search_key=initial, data=json.dumps(dict(add_initial_tasks=True))))
    assert {task.get_value('process') for task in Task.get_by_sobjects([Search.get_by_search_key(initial)])} == {'model', 'review'}


def exercise_related(api, auth):
    import json
    from pyasm.biz import Task
    project = 'progress_' + api.store.data_dir.parent.name
    api.dispatch('execute_cmd', (auth, 'tactic.command.CreateProjectCmd', dict(project_code=project, project_title='Related task contract')))
    scoped = dict(auth, project=project) if isinstance(auth, dict) else dict(ticket=auth, project=project)
    def record(method, *args, **kwargs):
        result = api.dispatch(method, (scoped, *args), kwargs)
        return ast.literal_eval(result) if isinstance(result, str) else result
    record('execute_cmd', 'tactic.core.schema_commands.SearchTypeCreatorCmd', dict(
        search_type_name='contract/progress_parent', sobject_pipeline=True, process=['model']))
    parent = record('insert', 'contract/progress_parent', dict(code='TASK_PARENT_A'))['__search_key__']
    record('execute_cmd', 'tactic.core.schema_commands.SearchTypeCreatorCmd', dict(
        search_type_name='contract/task_child', sobject_pipeline=True, process=['model', 'review'],
        column_name=['owner_code', 'owner_id'], data_type=['varchar', 'integer']))
    parent_row = record('query', 'contract/progress_parent', [['code', 'TASK_PARENT_A']])[0]
    schema = record('query', 'sthpw/schema', [['code', project]])[0]
    xml = schema['schema'].replace('</schema>', '<connect from="contract/task_child" to="contract/progress_parent" '
        'relationship="code" from_col="owner_code" to_col="code" type="hierarchy"/></schema>')
    assert 'owner_code' in xml, schema['schema']
    record('update', schema['__search_key__'], dict(schema=xml))
    record('insert', 'sthpw/pipeline', dict(code=project+'/RELATED', project_code=project,
        pipeline='<pipeline><process name="model" type="manual"/><process name="linked" type="progress"/>'
        '<process name="all" type="progress"/><process name="empty" type="progress"/>'
        '<process name="missing" type="progress"/><process name="unrelated" type="progress"/></pipeline>'))
    record('update', parent, dict(pipeline_code=project+'/RELATED'))
    for process, workflow in (
        ('linked', dict(search_type='contract/task_child', process='model', pipeline_code=project+'/task_child')),
        ('all', dict(properties=dict(search_type='contract/task_child'))),
        ('missing', dict(search_type='contract/absent')),
        ('unrelated', dict(search_type='sthpw/project'))):
        definition = record('query', 'config/process', [['pipeline_code', project+'/RELATED'], ['process', process]])[0]
        record('update', definition['__search_key__'], dict(workflow=json.dumps(workflow)))
    behavior = record('query', 'config/process', [['pipeline_code', project+'/task_child'], ['process', 'model']])[0]
    record('update', behavior['__search_key__'], dict(workflow=json.dumps(dict(task_pipeline=project+'/related_status'))))
    record('insert', 'config/process', dict(pipeline_code=project+'/related_status', process='Complete', workflow='{"mapping":"complete"}'))
    children = [record('insert', 'contract/task_child', dict(code=code, name=code, owner_code=owner,
                    owner_id=parent_row['id'], pipeline_code=project+'/task_child'))['__search_key__']
                for code, owner in [('LINK_A', 'TASK_PARENT_A'), ('LINK_B', 'TASK_PARENT_A'), ('OUTSIDE', 'elsewhere')]]
    tasks = [record('create_task', key, process='model', subcontext=suffix)
             for key, suffix in [(children[0], ''), (children[0], 'other'), (children[1], ''), (children[1], 'waiting'), (children[2], '')]]
    for task in tasks[:3]:
        record('update', task['__search_key__'], dict(status='Complete'), triggers=False)
    record('create_task', children[0], process='review')
    # A different Search Type with the same code is never selected by coincidence.
    record('insert', 'contract/progress_parent', dict(code='LINK_A', pipeline_code=project+'/RELATED'))
    record('create_task', 'contract/progress_parent?project='+project+'&code=LINK_A', process='model')
    def inspect(process='linked', **kwargs):
        return record('execute_cmd', 'tactic.ui.table.task_inspector.TaskInspectorCmd',
                      dict(search_key=parent, process=process, **kwargs))['info']
    result = inspect(); related = result['related']
    assert result['process_type'] == 'progress' and not result['fields'] and not result['selected_task']
    assert related['state'] == 'ready' and related['object_count'] == 2, related
    assert (related['approved'], related['total']) == (3, 2), related  # Native Handler counts tasks, not a capped percentage.
    assert len(related['items']) == 5 and set(related['parent_keys']) == set(children[:2])
    assert {item['task_key'] for item in related['items']} == {task['__search_key__'] for task in tasks[:4]} | {
        task['__search_key__'] for task in record('query', 'sthpw/task', [['search_code', 'LINK_A'], ['search_type', 'contract/task_child?project='+project], ['process', 'review']])}
    assert any(item['value'] == 'linked' and item['type'] == 'progress' for item in result['processes'])
    choice = next(item for item in result['processes'] if item['value'] == 'linked')
    assert (choice['approved'],choice['total']) == (3,2), 'Progress picker keeps native task/object counts'
    assert inspect('all')['related']['approved'] == 5
    assert inspect('empty')['related']['state'] == 'unconfigured'
    assert inspect('missing')['related']['state'] == 'missingType'
    assert inspect('unrelated')['related']['state'] == 'unrelated'
    for action in ('save', 'copy', 'delete'):
        try:
            inspect(action=action, data={}, expected_revision=result['revision'])
            raise AssertionError('Progress node accepted task mutation')
        except ValueError as error:
            assert 'no editable task' in str(error)
    # One batched task query irrespective of the number of related objects.
    with patch.object(Task, 'get_by_sobjects', wraps=Task.get_by_sobjects) as reads:
        inspect()
        assert sum(len(call.args[0]) == 2 for call in reads.call_args_list) == 1
    with patch.object(TaskElementWdg, 'can_view_process', side_effect=lambda process: process != 'review'):
        hidden = inspect()['related']; assert len(hidden['items']) == 4
    with patch.object(TaskElementWdg, 'can_view_process', side_effect=lambda process: process != 'linked'):
        from pyasm.common import SecurityException
        try:
            inspect(); raise AssertionError('Hidden progress accepted')
        except SecurityException:
            pass
    # Foreign-key ID and reversed direction both use Schema, not guessed code columns.
    id_xml = xml.replace('relationship="code" from_col="owner_code" to_col="code"',
                         'relationship="id" from_col="owner_id" to_col="id"')
    record('update', schema['__search_key__'], dict(schema=id_xml))
    assert inspect()['related']['object_count'] == 3
    record('update', children[0], dict(pipeline_code=project+'/RELATED'))
    config = record('query', 'config/process', [['pipeline_code', project+'/RELATED'], ['process', 'linked']])[0]
    record('update', config['__search_key__'], dict(workflow=json.dumps(dict(search_type='contract/progress_parent'))))
    assert 'contract/progress_parent' in record('query', 'config/process', [['id', config['id']]])[0]['workflow']
    reverse = record('execute_cmd', 'tactic.ui.table.task_inspector.TaskInspectorCmd',
                     dict(search_key=children[0], process='linked'))['info']['related']
    assert reverse['state'] == 'ready' and reverse['parent_keys'] == [parent], reverse
    # Configuration and DB changes take effect on the next read; no global result cache.
    record('update', config['__search_key__'], dict(workflow=json.dumps(dict(search_type='contract/task_child'))))
    record('update', children[2], dict(s_status='retired'))
    assert inspect()['related']['object_count'] == 2
    record('delete_sobject', tasks[2]['__search_key__'])
    assert inspect()['related']['approved'] == 4
    record('update', config['__search_key__'], dict(workflow=json.dumps(dict(search_type='contract/task_child', process='model', pipeline_code=project+'/not_configured'))))
    assert not inspect()['related']['summary_available']
