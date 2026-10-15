"""Unchanged Workflow type-change commands for the original and native cores."""
from pyasm.biz import Pipeline, Note, Task
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security, Ticket
from tactic.core.pipeline_commands import PipelineSaveCbk
from tactic.core.process_commands import NewProcessInfoCmd

NAMES = ('custom', 'action', 'progress', 'hierarchy')
MANUAL_XML = '<pipeline>' + ''.join('<process name="%s" type="manual"/>' % name for name in NAMES) + '</pipeline>'


class DeleteHandler(Command):
    def execute(self):
        definition = Search.get_by_code('config/process', self.kwargs['process_code'])
        if definition is None:
            raise AssertionError('Type change deleted the process definition')
        Note.create(Search.get_by_code('contract/dep_parent', 'PT_PARENT'), 'custom type released', process='custom')
        if self.kwargs.get('fail') == 'true':
            raise ValueError('custom type release failed')


class Setup(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        if not Environment.get_ticket():
            Environment.get_security()._ticket = Ticket.create('process_type_fixture', 'admin')
        config = SearchType.create('config/widget_config')
        config.set_value('category', 'workflow')
        config.set_value('view', 'type_custom')
        config.set_value('config', '<config><type_custom><element name="delete"><display class="process_type_contract.DeleteHandler"/></element></type_custom></config>')
        config.commit(triggers=False)
        pipeline = Pipeline.create('Types', '', 'contract/dep_parent',
            '<pipeline><process name="custom" type="type_custom"/><process name="action" type="action"/><process name="progress" type="progress"/><process name="hierarchy" type="hierarchy"/></pipeline>', code='PT_MAIN')
        Pipeline.create('Child', '', 'contract/dep_child', '<pipeline/>', code='PT_CHILD')
        for name in NAMES:
            definition = pipeline.get_process_sobject(name)
            definition.set_value('description', 'Keep ' + name)
            if name == 'hierarchy':
                definition.set_value('subpipeline_code', 'PT_CHILD')
            definition.commit(triggers=False)
        NewProcessInfoCmd(node_type='action', pipeline_code='PT_MAIN', process='action',
            default={'script': 'return True', 'execute_mode': 'same process,same transaction'}).execute()
        NewProcessInfoCmd(node_type='progress', pipeline_code='PT_MAIN', process='progress',
            progress={'related_search_type': 'contract/dep_child', 'related_process': 'work'}).execute()
        parent = SearchType.create('contract/dep_parent')
        parent.set_value('code', 'PT_PARENT')
        parent.set_value('pipeline_code', 'PT_MAIN')
        parent.commit(triggers=False)
        Task.create(parent, 'action', status='Pending', triggers='none')
        return pipeline.get_search_key()


class Change(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        PipelineSaveCbk(search_key=Pipeline.get_by_code('PT_MAIN').get_search_key(),
            pipeline=self.kwargs.get('pipeline') or MANUAL_XML, color='#445566', description='',
            node_kwargs=self.kwargs.get('node_kwargs') or {}).execute()


def result():
    definitions = Search('config/process')
    definitions.add_filter('pipeline_code', 'PT_MAIN')
    rows = definitions.get_sobjects()
    codes = set(row.get_code() for row in rows)
    triggers = [row for row in Search('config/trigger').get_sobjects()
                if row.get_value('process') in codes or (row.get_json_value('data') or {}).get('pipeline_code') == 'PT_MAIN']
    scripts = Search('config/custom_script')
    scripts.add_filter('folder', '_triggers/PT_MAIN')
    parent = Search.get_by_code('contract/dep_parent', 'PT_PARENT')
    notes, tasks = Search('sthpw/note'), Search('sthpw/task')
    notes.add_parent_filter(parent)
    tasks.add_filter('search_type', 'contract/dep_parent%', op='like')
    tasks.add_filter('search_code', parent.get_code())
    tasks.add_filter('project_code', parent.get_project_code())
    return {'workflow': {row.get_value('process'): row.get_json_value('workflow') for row in rows},
            'descriptions': {row.get_value('process'): row.get_value('description') for row in rows},
            'subpipeline': next(row.get_value('subpipeline_code') for row in rows if row.get_value('process') == 'hierarchy'),
            'triggers': len(triggers), 'scripts': scripts.get_count(), 'tasks': tasks.get_count(),
            'notes': [row.get_value('note') for row in notes.get_sobjects()]}


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        Command.execute_cmd(Setup())
        Command.execute_cmd(Change())
        return result()
    finally:
        Environment.set_security(previous)
