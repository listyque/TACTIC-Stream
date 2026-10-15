"""Unchanged pipeline/task/dependency API scenario for both original kernels and vendors."""
from pyasm.biz import Pipeline, Project, Snapshot, Task, Note
from pyasm.command import Command, Trigger, Workflow
from pyasm.common import Environment, Xml
from pyasm.web.api_xmlrpc import ApiXMLRPC
from pyasm.search import Search, SearchType
from pyasm.security import Security


class RecordTrigger(Trigger):
    def execute(self):
        return Note.create(self.get_caller(), self.get_input().get('note', 'none'), process='workflow_api')


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        api = ApiXMLRPC()
        api.set_protocol('local')
        ticket = {'project': 'admin', 'language': 'python'}
        xml = '<pipeline><process name="one"/><process name="two"/><connect from="one" to="two"/></pipeline>'
        core = Pipeline.create('Core API', 'Описание', 'sthpw/task', xml=xml, code='WORKFLOW_API_CORE')
        definitions = Search('config/process')
        definitions.add_filter('pipeline_code', core.get_code())
        core_process_count = definitions.get_count()
        created = api.create_pipeline(ticket, 'API metadata', 'sthpw/task', ['alpha', 'beta'], [], '', False)
        api_metadata = {name: created.get(name) for name in ('name', 'description', 'search_type')}
        api_metadata['connects'] = len(Xml(created['pipeline']).get_nodes('pipeline/connect'))
        parent = Search.get_by_code('contract/engine', 'ENGINE')
        other = Search.get_by_code('contract/engine', 'MANUAL')
        tasks = [Task.create(parent, process, triggers='none') for process in ('start', 'left', 'right', 'join')]
        inputs = api.get_input_tasks(ticket, tasks[-1].get_search_key())
        outputs = api.get_output_tasks(ticket, {'__search_key__': tasks[0].get_search_key()})
        info = api.get_pipeline_xml_info(ticket, parent.get_search_key(), True)
        processes = api.get_pipeline_processes_info(ticket, parent.get_search_key(), True)
        related = api.get_pipeline_processes_info(ticket, parent.get_search_key(), False, 'join')
        colors = api.get_task_status_colors(ticket)
        assert 'task' in colors and 'approval' in colors
        assert api.get_pipeline_xml_info(ticket, Project.get().get_search_key()) == '<pipeline/>'
        assert api.get_pipeline_processes_info(ticket, Project.get().get_search_key()) == {}
        trigger = SearchType.create('sthpw/trigger')
        trigger.set_value('event', 'workflow_api|record', temp=True)
        trigger.set_value('class_name', RecordTrigger, temp=True)
        trigger.set_value('mode', 'same process,same transaction', temp=True)
        Trigger.append_static_trigger(trigger)
        count = api.call_trigger(ticket, [parent.get_search_key(), other.get_search_key()], 'workflow_api|record', {'note': 'API trigger'})
        assert count == 2
        Workflow().init(quiet=True)
        api.call_pipeline_event(ticket, [parent.get_search_key(), other.get_search_key()], 'start', 'pending', {'value': 7})
        status_error = False
        try:
            statuses = [api.get_pipeline_status(ticket, row.get_search_key(), 'start') for row in (parent, other)]
            assert api.get_pipeline_status(ticket, parent.get_search_key(), 'missing') is None
        except AttributeError as error:
            if "NoneType" not in str(error):
                raise
            status_error = True
            statuses = []
            for row in (parent, other):
                message = Search.get_by_code('sthpw/message', row.get_search_key()+'|start|status')
                statuses.append(message.get_value('message') if message else None)
        owner = Project.get()
        first = api.create_snapshot(ticket, owner.get_search_key(), 'workflow_ref')
        second = api.create_snapshot(ticket, owner.get_search_key(), 'workflow_child')
        api.add_dependency_by_code(ticket, first, second, 'input_ref', "quoted'tag")
        linked = Snapshot.get_by_code(first['code'])
        refs = linked.get_xml_value('snapshot').get_nodes('snapshot/input_ref')
        assert len(refs) == 1 and Xml.get_attribute(refs[0], 'snapshot_code') == second['code']
        file = SearchType.create('sthpw/file')
        file.set_value('file_name', 'workflow_reference.txt')
        file.set_value('snapshot_code', second['code'])
        file.set_value('search_type', owner.get_search_type())
        file.set_value('search_id', owner.get_id())
        file.set_value('search_code', owner.get_code())
        file.set_value('project_code', 'admin')
        file.commit()
        path = api.add_dependency(ticket, first['__search_key__'], '/any/workflow_reference.txt')
        assert len(Xml(path['snapshot']).get_nodes('snapshot/ref')) == 1
        api.lock_sobject(ticket, owner.get_search_key(), 'workflow_ref')
        locked = Snapshot.is_locked(owner, 'workflow_ref')
        api.unlock_sobject(ticket, owner.get_search_key(), 'workflow_ref')
        unlocked = not Snapshot.is_locked(owner, 'workflow_ref')
        if self.fail:
            raise ValueError('workflow API rollback')
        return {'api_metadata': api_metadata, 'core_process_count': core_process_count,
                'inputs': sorted(row['process'] for row in inputs), 'outputs': sorted(row['process'] for row in outputs),
                'hierarchy': info['hierarchy'], 'processes': processes, 'related': related,
                'colors': colors.get('WORKFLOW_API_CORE'), 'trigger_count': count,
                'statuses': statuses, 'status_error': status_error, 'locked': locked, 'unlocked': unlocked}


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        command = Run()
        command.fail = case.get('fail', False)
        return Command.execute_cmd(command)
    finally:
        Environment.set_security(previous)
