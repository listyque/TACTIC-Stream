"""Original editor deletion on owned fixtures; also usable through XML-RPC."""
from pyasm.biz import Pipeline, Note, Task
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Security, Ticket
from tactic.core.pipeline_commands import PipelineSaveCbk
from tactic.core.process_commands import NewProcessInfoCmd


class DeleteHandler(Command):
    def execute(self):
        definition = Search.get_by_code('config/process', self.kwargs['process_code'])
        if definition is None:
            raise AssertionError('Delete handler must run before deleting the definition')
        parent = Search.get_by_code('contract/dep_parent', 'PD_PARENT')
        Note.create(parent, 'custom deleted', process='custom')
        if self.kwargs.get('fail') == 'true':
            raise ValueError('custom delete failed')


class Setup(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        if not Environment.get_ticket():
            Environment.get_security()._ticket = Ticket.create('process_delete_fixture', 'admin')
        config = SearchType.create('config/widget_config')
        config.set_value('category', 'workflow')
        config.set_value('view', 'delete_custom')
        config.set_value('config', '<config><delete_custom><element name="delete"><display class="process_delete_contract.DeleteHandler"/></element></delete_custom></config>')
        config.commit(triggers=False)
        pipeline = Pipeline.create('Deletion', '', 'contract/dep_parent',
            '<pipeline><process name="custom" type="delete_custom"/><process name="action" type="action"/><process name="progress" type="progress"/></pipeline>', code='PD_MAIN')
        pipeline.commit(triggers=False)
        pipeline.update_dependencies()
        # No node_type metadata: the old graph is the only source of custom type.
        for name in ('action', 'progress'):
            options = {'default': {'script': 'return True', 'execute_mode': 'same process,same transaction'}} if name == 'action' else {'progress': {'related_search_type': 'contract/dep_child', 'related_process': 'work'}}
            NewProcessInfoCmd(node_type=name, pipeline_code='PD_MAIN', process=name, **options).execute()
        parent = SearchType.create('contract/dep_parent')
        parent.set_value('code', 'PD_PARENT')
        parent.set_value('pipeline_code', 'PD_MAIN')
        parent.commit(triggers=False)
        Task.create(parent, 'custom', status='Pending', triggers='none')
        # An external listener must survive deletion of this pipeline's processes.
        trigger = SearchType.create('config/trigger')
        trigger.set_value('code', 'PD_EXTERNAL')
        trigger.set_value('event', 'workflow|contract/dep_child')
        trigger.set_value('process', 'work')
        trigger.set_value('class_name', 'pyasm.command.ProcessStatusTrigger')
        trigger.set_json_value('data', {'process_code': 'OTHER', 'pipeline_code': 'OTHER'})
        trigger.commit(triggers=False)
        return pipeline.get_search_key()


class Delete(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        PipelineSaveCbk(search_key=Pipeline.get_by_code('PD_MAIN').get_search_key(), pipeline='<pipeline/>', color='#445566', description='').execute()


def result():
    search = Search('config/process')
    search.add_filter('pipeline_code', 'PD_MAIN')
    notes = Search('sthpw/note')
    notes.add_parent_filter(Search.get_by_code('contract/dep_parent', 'PD_PARENT'))
    tasks = Search('sthpw/task')
    tasks.add_parent_filter(Search.get_by_code('contract/dep_parent', 'PD_PARENT'))
    return {'processes': search.get_count(), 'triggers': Search('config/trigger').get_count(),
            'scripts': Search('config/custom_script').get_count(),
            'notes': [note.get_value('note') for note in notes.get_sobjects()], 'tasks': tasks.get_count()}


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        Command.execute_cmd(Setup())
        before = result()
        Command.execute_cmd(Delete())
        return {'before': before, 'after': result()}
    finally:
        Environment.set_security(previous)
