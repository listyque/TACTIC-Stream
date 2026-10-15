"""Unchanged Pipeline action/check-in calls for source and native runtimes."""
from pathlib import Path

from pyasm.biz import Pipeline, Task, Note, Snapshot
from pyasm.checkin import FileCheckin
from pyasm.command import Command
from pyasm.common import Environment, Container
from pyasm.search import Search, SearchType, SObject
from pyasm.security import Security, Ticket
from pyasm.web.api_xmlrpc import ApiXMLRPC


def install_fixture(db, id_definition='integer PRIMARY KEY'):
    db.execute('CREATE TABLE listener_entity (id ' + id_definition + ', code varchar(256), pipeline_code varchar(256))')
    db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('contract/listener','contract/listener','contract','sthpw','listener_entity','pyasm.search.SObject')")


class Listener:
    def set_prev_command(self, command):
        self.previous = command

    def set_options(self, options):
        self.options = options

    def set_process_name(self, process):
        self.process = process

    def set_input(self, value):
        self.input = value

    def set_output(self, value):
        self.output = value

    def get_input(self):
        return self.input

    def execute(self):
        parent = self.previous.get_sobjects()[0]
        # The original passes the same info to both setters, without an envelope.
        Container.append_seq('listener_events', [self.process, self.options,
                             self.previous.get_event_name(), self.input is self.output,
                             self.input == self.previous.get_info()])
        Note.create(parent, 'listener|' + self.process, process='listener')
        if self.options.get('fail') == 'true' or (
                self.options.get('label') == 'file' and Container.get('listener_fail_file')):
            raise ValueError('listener failed')


class CustomCheckin(FileCheckin):
    def postprocess_snapshot(self):
        super().postprocess_snapshot()
        self.snapshot.set_value('description', 'custom check-in')


class Setup(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        if not Environment.get_ticket():
            Environment.get_security()._ticket = Ticket.create('listener_fixture', 'admin')
        graph = '''<pipeline>
          <process name="publish"><action event="checkin" scope="current" class="command_listener_contract.CustomCheckin"/></process>
          <process name="review">
            <action event="task/approved" scope="dependent" class="command_listener_contract.Listener"><label>review</label></action>
            <action event="checkin/move" scope="dependent" class="command_listener_contract.Listener"><label>file</label></action>
          </process>
          <process name="archive">
            <action event="task/approved" scope="dependent" class="command_listener_contract.Listener"><label>archive</label></action>
          </process>
          <process name="ignored">
            <action event="other" scope="dependent" class="command_listener_contract.Listener"/>
            <action event="task/approved" scope="current" class="command_listener_contract.Listener"/>
            <action event="task/approved" scope="dependent"/>
          </process>
          <connect from="publish" to="review"/>
          <connect from="publish" to="archive"/>
          <connect from="publish" to="ignored"/>
        </pipeline>'''
        for code, xml in (('LISTENERS', graph), ('LISTENERS_FAIL', graph.replace(
                '<label>review</label>', '<label>review</label><fail>true</fail>'))):
            pipeline = SearchType.create('sthpw/pipeline')
            pipeline.set_value('code', code)
            pipeline.set_value('project_code', 'admin')
            pipeline.set_value('use_workflow', False)
            pipeline.set_value('pipeline', xml)
            pipeline.commit(triggers=False)
        for code in ('PUBLISHED', 'FAILED'):
            parent = SearchType.create('contract/listener')
            parent.set_value('code', code)
            parent.set_value('pipeline_code', 'LISTENERS_FAIL' if code == 'FAILED' else 'LISTENERS')
            parent.commit(triggers=False)
            Task.create(parent, 'publish', status='Pending', triggers='none')
            Task.create(parent, 'other', status='Pending', triggers='none')


class Publish(Command):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sobjects = [Search.get_by_code('contract/listener', kwargs.get('code', 'PUBLISHED'))]
        self.set_process('publish')

    def execute(self):
        self.get_transaction().set_sync(False)
        self.set_as_approved()
        Note.create(self.sobjects[0], 'caller committed', process='listener')
        return {'payload': 'unchanged'}


def notes(parent):
    search = Search('sthpw/note')
    search.add_parent_filter(parent)
    search.add_order_by('id')
    return [row.get_value('note') for row in search.get_sobjects()]


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    try:
        Command.execute_cmd(Setup())
        parent = Search.get_by_code('contract/listener', 'PUBLISHED')
        Container.put('listener_events', [])
        Container.put('listener_fail_file', bool(case.get('deferred_failure')))
        info = Command.execute_cmd(Publish())
        result = {'info': info, 'events': Container.get_seq('listener_events')[:],
                  'notes': notes(parent),
                  'tasks': [[task.get_value('process'), task.get_value('status')]
                            for task in Task.get_by_sobject(parent)]}
        try:
            Command.execute_cmd(Publish(code='FAILED', log_exception=False))
        except ValueError as error:
            result['failure'] = str(error)
        result['failed_notes'] = notes(Search.get_by_code('contract/listener', 'FAILED'))
        Container.put('listener_events', [])
        directory = Path(Environment.get_upload_dir())
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'listener.txt').write_bytes(b'listener file')
        api = ApiXMLRPC()
        api.set_protocol('local')
        ticket = dict(ticket=Environment.get_ticket(), project='admin', language='python')
        cmd = Command()
        def checkin():
            cmd.get_transaction().set_sync(False)
            try:
                selected = FileCheckin.get(parent, [str(directory / 'listener.txt')], ['main'],
                                          context='publish', mode='create')
                result['factory'] = type(selected).__name__
            except NameError:
                # Source exec/import + eval breaks custom classes on Python 3.
                result['factory'] = 'NameError'
            # All original local API arguments must be positional.
            return api.simple_checkin(ticket, parent.get_search_key(), 'publish', 'listener.txt',
                'file', 'initial', False, 'main', True, None, {}, None, False, {}, False, False,
                'command_listener_contract.CustomCheckin')
        cmd.execute = checkin
        row = Command.execute_cmd(cmd)
        snapshot = Snapshot.get_by_code(row['code'])
        result['checkin'] = [row['context'], row['description'],
                            Path(snapshot.get_lib_path_by_type()).read_text()]
        result['checkin_notes'] = notes(parent)
        result['checkin_events'] = Container.get_seq('listener_events')[:]
        SObject.get_cache_dict(search_type='contract/listener').clear()
        result['reloaded_type'] = Search.get_by_search_key(parent.get_search_key()).get_search_type()
        return result
    finally:
        Environment.set_security(previous)
