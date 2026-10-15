"""Same custom task-status pipelines and commands on both TACTIC cores."""
import json
from pyasm.biz import Pipeline, Project, Task
from pyasm.command import Command, Trigger, Workflow
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security

CASES = ('v1', 'v2', 'xml', 'nested', 'alternate', 'output', 'branch')


def set_workflow(pipeline, name, workflow, subpipeline=None):
    # Source Pipeline.create duplicates definitions; configure both owned rows.
    search = Search('config/process')
    search.add_filter('pipeline_code', pipeline.get_code())
    search.add_filter('process', name)
    for definition in search.get_sobjects():
        definition.set_json_value('workflow', workflow)
        if subpipeline:
            definition.set_value('subpipeline_code', subpipeline)
        definition.commit()


class Setup(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        mode = self.kwargs.get('mode', 'v2')
        code = 'CS_' + mode
        status_code = code + '_STATUS'
        statuses = Pipeline.create('Custom task states', '', 'sthpw/task',
            '<pipeline><process name="Working" type="status"/><process name="Ready" type="status"/><process name="Back" type="status"/><process name="Send" type="status" direction="output" status="In Progress"/><process name="Route" type="status"/></pipeline>', code=status_code)
        statuses.set_pipeline(statuses.get_value('pipeline'))
        for name, mapping in (('Working', 'in_progress'), ('Ready', 'complete'), ('Back', 'revise')):
            node = statuses.get_process(name)
            if mode == 'xml':
                node.set_attribute('mapping', mapping)
            else:
                set_workflow(statuses, name, {'version': 2, 'mapping': mapping})
        if mode == 'xml':
            statuses.set_value('pipeline', statuses.get_pipeline_xml().to_string())
            statuses.commit()
        # Load the saved graph with its final code, as a separate request does.
        statuses = Pipeline.get_by_code(status_code)
        graph = '<pipeline><process name="work" type="manual"/><process name="done" type="action"/><connect from="work" to="done"/></pipeline>'
        if mode == 'branch':
            graph = graph.replace('to="done"/>', 'to="done" from_attr="Route"/>')
        child = Pipeline.create('Custom status work', '', 'contract/dep_parent', graph, code=code)
        child.set_pipeline(child.get_value('pipeline'))
        settings = {'task_pipeline': statuses.get_code()}
        workflow = dict(settings, version=1, task_number=2) if mode == 'v1' else {'version': 2, 'properties': settings, 'task_number': 2}
        set_workflow(child, 'work', workflow)
        if mode == 'xml':
            workflow['properties'] = {}
            set_workflow(child, 'work', workflow)
            child.get_process('work').set_attribute('task_pipeline', statuses.get_code())
            child.set_value('pipeline', child.get_pipeline_xml().to_string())
            child.commit()
        set_workflow(child, 'done', {'version': 2, 'on_action': "from pyasm.biz import Note\nimport json\nNote.create(sobject, json.dumps([data, input.get('packages', {}).get('custom')]), process='custom_status')\nreturn True"})
        parent_pipeline = child
        if mode == 'nested':
            parent_pipeline = Pipeline.create('Custom status hierarchy', '', 'contract/dep_parent',
                '<pipeline><process name="gate" type="hierarchy"/></pipeline>', code=code + '_ROOT')
            parent_pipeline.set_pipeline(parent_pipeline.get_value('pipeline'))
            set_workflow(parent_pipeline, 'gate', {'version': 2, 'default': {'subpipeline': code, 'task_creation': 'subtasks_only'}}, subpipeline=code)
        elif mode == 'alternate':
            parent_pipeline = Pipeline.create('Primary graph', '', 'contract/dep_parent', '<pipeline><process name="idle" type="manual"/></pipeline>', code=code + '_PRIMARY')
            parent_pipeline.set_pipeline(parent_pipeline.get_value('pipeline'))
        parent = SearchType.create('contract/dep_parent?project=' + Project.get_project_code())
        parent.set_value('code', code)
        parent.set_value('pipeline_code', parent_pipeline.get_code())
        parent.set_value('start_date', '2026-10-05 12:00:00')
        parent.set_value('due_date', '2026-10-15 12:00:00')
        parent.commit(triggers=False)
        parent_pipeline = Pipeline.get_by_code(parent_pipeline.get_code())
        child = Pipeline.get_by_code(code)
        Task.add_initial_tasks(parent, pipeline_code=parent_pipeline.get_code() if mode == 'nested' else code, start_date='2026-10-05')
        return parent.get_search_key()


class Begin(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        mode = self.kwargs.get('mode', 'v2')
        code = 'CS_' + mode
        parent = Search.get_by_search_key('contract/dep_parent?project=%s&code=%s' % (Project.get_project_code(), code))
        Workflow().init(quiet=True)
        pipeline = Pipeline.get_by_code(code + '_ROOT' if mode == 'nested' else code)
        Trigger.call(self, 'process|pending', {'pipeline': pipeline, 'sobject': parent,
            'process': 'gate' if mode == 'nested' else 'work', 'data': {'value': 7}, 'packages': {'custom': {'value': 9}}})


class Change(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        mode = self.kwargs.get('mode', 'v2')
        parent = Search.get_by_search_key('contract/dep_parent?project=%s&code=CS_%s' % (Project.get_project_code(), mode))
        Workflow().init(quiet=True)
        if mode in ('output', 'branch'):
            Trigger.call(self, 'process|custom', {'pipeline': Pipeline.get_by_code('CS_' + mode), 'sobject': parent,
                'process': 'work', 'status': 'Send' if mode == 'output' else 'Route',
                'data': {'value': 7}, 'packages': {'custom': {'value': 9}}})
        else:
            tasks = Task.get_by_sobject(parent, order=False)
            tasks.sort(key=lambda row: row.get_id())
            task = tasks[self.kwargs.get('number', 0)]
            task.set_value('status', self.kwargs.get('status', 'Ready'))
            task.commit()
        return result(mode)


def result(mode):
    parent = Search.get_by_search_key('contract/dep_parent?project=%s&code=CS_%s' % (Project.get_project_code(), mode))
    states = Search('config/process_state')
    states.add_parent_filter(parent)
    notes = Search('sthpw/note')
    notes.add_parent_filter(parent)
    notes.add_filter('process', 'custom_status')
    notes.add_order_by('id')
    tasks = Task.get_by_sobject(parent, order=False)
    tasks.sort(key=lambda row: row.get_id())
    return {'states': {row.get_value('process'): row.get_value('status') for row in states.get_sobjects()},
        'tasks': [[row.get_value('process'), row.get_value('status'), row.get_value('pipeline_code')] for row in tasks],
        'notes': [json.loads(row.get_value('note')) for row in notes.get_sobjects()]}


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        mode = case.get('operation', 'v2')
        Command.execute_cmd(Setup(mode=mode))
        Command.execute_cmd(Begin(mode=mode))
        if mode in ('output', 'branch'):
            return Command.execute_cmd(Change(mode=mode))
        active = Command.execute_cmd(Change(mode=mode, status='Working'))
        first = Command.execute_cmd(Change(mode=mode, status='Ready'))
        final = Command.execute_cmd(Change(mode=mode, status='Ready', number=1))
        return {'active': active, 'first': first, 'final': final}
    finally:
        Environment.set_security(previous)
