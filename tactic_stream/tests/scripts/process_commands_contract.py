"""Unchanged process commands run on both cores; all records are test-owned."""
import json
from pyasm.biz import Pipeline, Task, Note
from pyasm.command import Command, Trigger, Workflow
from pyasm.command.workflow import WorkflowActionNodeHandler, ProcessStatusTrigger
from pyasm.common import Environment, Container, Xml
from pyasm.search import Search, SearchType
from pyasm.security import Security, Ticket
from tactic.core.pipeline_commands import PipelineSaveCbk
from tactic.core.process_commands import ProcessInfoCmd, NewProcessInfoCmd

CASES = ['SAVE_V1', 'SAVE_V2', 'SAVED_SCRIPT', 'DEPENDENCY', 'PROGRESS', 'CUSTOM', 'BAD_SETTINGS', 'BAD_HANDLER', 'PROGRESS_EXECUTION']

class CustomHandler(WorkflowActionNodeHandler):
    def set_name(self, name):
        self.name = name
    def handle_action(self):
        Note.create(self.sobject, 'custom action', process=self.process)
        return super().handle_action()

class SaveHandler(Command):
    def set_name(self, name):
        self.name = name
    def execute(self):
        definition = Pipeline.get_by_code(self.kwargs['pipeline_code']).get_process_sobject(self.kwargs['process'])
        definition.set_value('description', 'custom saved')
        definition.commit()
        if self.kwargs.get('fail'):
            raise ValueError('custom save failed')

class BrokenConstructor(Command):
    def __init__(self, **kwargs):
        Container.increment('process_constructor_calls')
        raise ValueError('constructor failed')

class Setup(Command):
    def __init__(self, case):
        super().__init__()
        self.case = case
    def execute(self):
        self.get_transaction().set_sync(False)
        if not Environment.get_ticket():
            Environment.get_security()._ticket = Ticket.create('process_fixture_' + self.case, 'admin')
        code = 'PM_' + self.case
        pipeline = Pipeline.create('Process commands', '', 'contract/dep_parent', '<pipeline><process name="publish" type="action"/></pipeline>', code=code)
        pipeline.set_value('project_code', 'one')
        pipeline.commit(triggers=False)
        pipeline.update_dependencies()
        definition = pipeline.get_process_sobject('publish')
        definition.set_value('code', code + '_publish')
        definition.set_json_value('workflow', {'version': 2})
        definition.commit(triggers=False)
        parent = SearchType.create('contract/dep_parent')
        parent.set_value('code', code)
        parent.set_value('pipeline_code', code)
        parent.commit(triggers=False)
        if self.case in ('CUSTOM', 'BAD_HANDLER'):
            config = SearchType.create('config/widget_config')
            config.set_value('category', 'workflow')
            config.set_value('view', 'contract_custom')
            config.set_value('config', '<config><contract_custom><element name="process"><display class="process_commands_contract.CustomHandler"/></element><element name="save"><display class="process_commands_contract.SaveHandler"/></element></contract_custom></config>')
            config.commit(triggers=False)
        return pipeline.get_search_key()

class Save(Command):
    def __init__(self, case, key):
        super().__init__()
        self.case, self.key = case, key
    def execute(self):
        self.get_transaction().set_sync(False)
        code = 'PM_' + self.case
        script = "from pyasm.biz import Note\nfrom pyasm.search import Search\nparent = input['sobject']\nif isinstance(parent, dict):\n    parent = Search.get_by_search_key(parent['__search_key__'])\nNote.create(parent, 'saved action', process=input['process'])\nreturn True"
        if self.case == 'DEPENDENCY':
            ProcessInfoCmd(node_type='dependency', pipeline_code=code, process='publish', related_search_type='contract/dep_child', related_process='work', related_wait=False).execute()
            return
        if self.case == 'PROGRESS':
            ProcessInfoCmd(node_type='progress', pipeline_code=code, process='publish', related_search_type='contract/dep_child', related_process='work').execute()
            return
        if self.case == 'SAVED_SCRIPT':
            ProcessInfoCmd(node_type='action', pipeline_code=code, process='publish', script=script, script_path='tests/existing', execute_mode='same process,same transaction').execute()
            ProcessInfoCmd(node_type='action', pipeline_code=code, process='publish', script_path='tests/existing', execute_mode='same process,same transaction').execute()
        else:
            node_type = 'contract_custom' if self.case in ('CUSTOM', 'BAD_HANDLER') else 'action'
            kwargs = {'version': 1, 'script': script, 'execute_mode': 'same process,same transaction'} if self.case == 'SAVE_V1' else {'version': 2, 'default': {'script': script, 'execute_mode': 'same process,same transaction'}}
            if node_type == 'contract_custom':
                kwargs = {'version': 2, 'fail': self.case == 'BAD_HANDLER'}
            graph = '<pipeline><process name="publish" type="%s" label="A &amp; B"/></pipeline>' % node_type
            if self.case == 'BAD_SETTINGS':
                graph = graph.replace('/>', ' settings="broken"/>')
            PipelineSaveCbk(search_key=self.key, pipeline=graph, color='#445566', description='', node_kwargs={'publish': kwargs}).execute()
        Workflow().init(quiet=True)
        parent = Search.get_by_code('contract/dep_parent', code)
        Trigger.call(self, 'process|pending', {'sobject': parent, 'pipeline': Pipeline.get_by_code(code), 'process': 'publish', 'data': {'value': 9}})

def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        code = case['graph']
        if code == 'PROGRESS_EXECUTION':
            return {'statuses': progress_cycle()}
        key = Command.execute_cmd(Setup(code))
        error = ''
        try:
            Command.execute_cmd(Save(code, key))
        except Exception as exc:
            error = type(exc).__name__ + ': ' + str(exc)
        pipeline = Pipeline.get_by_code('PM_' + code)
        definitions = Search('config/process')
        definitions.add_filter('pipeline_code', 'PM_' + code)
        definitions.add_filter('process', 'publish')
        definition = definitions.get_sobject()
        triggers = Search('config/trigger')
        triggers.add_filter('process', definition.get_code() if code not in ('PROGRESS',) else 'work')
        parent = Search.get_by_code('contract/dep_parent', 'PM_' + code)
        notes = Search('sthpw/note')
        notes.add_parent_filter(parent)
        notes.add_order_by('id')
        workflow = definition.get_json_value('workflow')
        if workflow and workflow.get('trigger_code'):
            workflow['trigger_code'] = bool(Search.get_by_code('config/trigger', workflow['trigger_code']))
        return {'error': error, 'workflow': workflow, 'description': definition.get_value('description'),
                'label': pipeline.get_process('publish').get_attribute('label'),
                'process_code': pipeline.get_process('publish').get_attribute('process_code'),
                'triggers': [[row.get_value('event'), row.get_value('script_path'), row.get_value('class_name')] for row in triggers.get_sobjects()],
                'notes': [row.get_value('note') for row in notes.get_sobjects()]}
    finally:
        Environment.set_security(previous)


def progress_cycle():
    class SetupProgress(Command):
        def execute(self):
            self.get_transaction().set_sync(False)
            pipeline = Pipeline.create('Progress', '', 'contract/dep_parent', '<pipeline><process name="publish" type="progress"/></pipeline>', code='PM_AUTO_PROGRESS')
            pipeline.set_value('project_code', 'one')
            pipeline.commit(triggers=False)
            pipeline.update_dependencies()
            ProcessInfoCmd(node_type='progress', pipeline_code=pipeline.get_code(), process='publish', related_search_type='contract/dep_child', related_process='work').execute()
            parent = SearchType.create('contract/dep_parent')
            parent.set_value('code', 'PM_AUTO_PROGRESS')
            parent.set_value('pipeline_code', pipeline.get_code())
            parent.commit(triggers=False)
            for number in (1, 2):
                child = SearchType.create('contract/dep_child')
                for name, value in dict(code='PM_PROGRESS_' + str(number), pipeline_code='DEP_CHILD', parent_code=parent.get_code()).items():
                    child.set_value(name, value)
                child.commit(triggers=False)
                Task.create(child, 'work', status='Pending', triggers='none')
            Workflow().init(quiet=True)
            Trigger.call(self, 'process|pending', {'sobject': parent, 'pipeline': pipeline, 'process': 'publish'})
    Command.execute_cmd(SetupProgress())
    statuses = []
    for number in (1, 2):
        class FinishProgress(Command):
            def execute(self):
                self.get_transaction().set_sync(False)
                Workflow().init(quiet=True)
                child = Search.get_by_code('contract/dep_child', 'PM_PROGRESS_' + str(number))
                task = Task.get_by_sobject(child, process='work')[0]
                task.set_value('status', 'Complete')
                task.commit()
        Command.execute_cmd(FinishProgress())
        from pyasm.command.workflow import BaseProcessTrigger
        handler = BaseProcessTrigger()
        handler.input = {}
        statuses.append(handler.get_process_status(Search.get_by_code('contract/dep_parent', 'PM_AUTO_PROGRESS'), 'publish'))
    return statuses
