"""Unchanged command/queue/snapshot calls in original and native runtimes."""
import ast
import json
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

from pyasm.biz import Project, File, Snapshot, ProjectSetting
from pyasm.command import Command, Trigger
from pyasm.common import Environment, Config
from pyasm.web.api_xmlrpc import ApiXMLRPC
from pyasm.search import Search, SearchType
from pyasm.security import Security
from tactic.command import Queue


class ApiProbe:
    def save(self, key, value):
        ProjectSetting.create(key, value)
        return dict(key=key, value=value)


class CheckoutProbe(Trigger):
    def execute(self):
        data = self.get_input()
        ProjectSetting.create('checkout_called', data['snapshot']['context'])


def run(case):
    previous = Environment.get_security()
    if previous is None:
        security = Security()
        Environment.set_security(security)
        security._is_logged_in = 1
        security._login = Search.get_by_code('sthpw/login', 'admin')
    cmd = Command()

    def execute():
        cmd.get_transaction().set_sync(False)
        api = ApiXMLRPC()
        api.set_protocol('local')
        ticket = dict(project=Project.get_project_code(), language='python')
        if case.get('insert_metadata'):
            row = api.insert(ticket, 'contract/entity',
                dict(code='INSERT_METADATA', name='Chat metadata', metadata={
                    'title': 'Группа', 'summary': {'messageCount': 0}}),
                {'flag': True})
            obj = Search.get_by_code('contract/entity', row['code'])
            inserted = json.loads(json.dumps(obj.get_metadata()))
            api.update(ticket, row['__search_key__'], {'metadata': {'title': 'Renamed'}})
            obj = Search.get_by_code('contract/entity', row['code'])
            return dict(inserted=inserted, updated=obj.get_metadata())
        if case.get('snapshot'):
            context = case.get('context', 'command_api_snapshot')
            parent = Search.get_by_code('contract/entity', 'A') if case.get('cross_project') else Project.get()
            snapshot = Snapshot.create(parent, 'file', context, version=1, commit=False)
            file = File.create('example.txt', parent.get_search_type(), parent.get_id(), commit=False, requires_file=False,
                               search_code=parent.get_code())
            file.set_value('snapshot_code', snapshot.get_code())
            file.set_value('file_name', "O'Reilly.txt" if case.get('quotes') else 'example.txt')
            if case.get('groups'):
                file.set_value('file_name', 'example.####.txt')
                file.set_value('base_type', 'sequence')
                file.set_value('file_range', '1-5/2')
            file.set_value('type', 'main')
            file.set_value('relative_dir', 'command_api')
            file.set_value('checkin_dir', 'input')
            file.set_value('source_path', 'input/source.txt')
            file.commit(triggers='none')
            from pyasm.checkin import SnapshotBuilder
            builder = SnapshotBuilder()
            builder.add_file(file, dict(type='main', file_range='1-5/2') if case.get('groups') else dict(type='main'))
            snapshot.set_value('snapshot', builder.to_string())
            snapshot.set_value('description', 'Текст & данные')
            snapshot.set_value('is_latest', True)
            snapshot.commit(triggers='none')
            cached = snapshot.get_xml_value('snapshot')
            before = cached.to_string()
            xml_error = None
            try:
                xml = ET.fromstring(api.get_full_snapshot_xml(ticket, dict(code=snapshot.get_code())))
                xml_data = dict(version=xml.get('version'), description=xml.get('description'),
                                file=xml.find('file').get('name'),
                                checkin_dir=xml.find('file').get('checkin_dir'),
                                source_path=xml.find('file').get('source_path'))
            except Exception as error:
                xml_error, xml_data = type(error).__name__, None
            cache_unchanged = cached.to_string() == before
            definition = SearchType.create('config/trigger')
            definition.set_value('event', 'checkout')
            definition.set_value('class_name', 'command_api_contract.CheckoutProbe')
            definition.set_value('mode', 'same process,same transaction')
            definition.commit()
            if case.get('cross_project'):
                Project.set_project('two')
                ticket['project'] = 'two'
            checkout_error = None
            try:
                paths = api.checkout(ticket, parent.get_search_key(), context, 1, 'main')
                sizes = {key: len(value) for key, value in paths.items()}
                if case.get('groups'):
                    names = {key: [Path(path).name for path in value] for key, value in paths.items()}
            except Exception as error:
                checkout_error, sizes = type(error).__name__, None
            restored_project = Project.get_project_code()
            if case.get('cross_project'):
                Project.set_project('one')
            result = dict(xml=xml_data, xml_error=xml_error, cache_unchanged=cache_unchanged,
                        checkout_error=checkout_error, paths=sizes,
                        trigger=ProjectSetting.get_value_by_key('checkout_called'))
            if case.get('groups'):
                result['names'] = names
            if case.get('cross_project'):
                result['restored_project'] = restored_project
                Project.set_project(restored_project)
            return result
        result = api.execute_class_method(ticket, 'command_api_contract.ApiProbe', 'save',
                                         dict(key='command_api_failure' if case.get('fail') else 'command_api', value='Unicode текст'))
        queue = api.add_queue_item(ticket, 'tactic.command.QueueTest', {'label': 'Данные'},
                                   'command_api', 0 if case.get('zero') else 10, 'Description', 'MESSAGE')
        queue_data = {name: queue.get(name) for name in ('queue', 'state', 'priority', 'description',
                                                        'project_code', 'command', 'message_code')}
        queue_data['priority'] = str(queue_data['priority'])
        queue_data['data'] = json.loads(queue['data'])
        job = Queue.get_next_job(queue_type='command_api')
        empty = Queue.get_next_job(queue_type='command_api')
        stored = Search.get_by_id('sthpw/queue', job.get_id())
        token = api.generate_ticket(ticket)
        try:
            api.test_error(ticket)
        except NameError:
            error_ok = True
        speeds = ast.literal_eval(api.test_speed(ticket))
        output = dict(result=result, queue=queue_data, claimed=stored.get_value('state'),
                      empty=empty is None, token_shape=len(token) == 19 and all(c in '0123456789abcdef' for c in token),
                      error=error_ok, tickets=isinstance(speeds, list),
                      missing_doc=api.get_doc_link(ticket, '__absent__'),
                      doc=api.get_doc_link(ticket, 'advanced-access-rule-configuration'))
        if case.get('fail'):
            raise ValueError('late command API failure')
        return output

    cmd.execute = execute
    original_config = Config.get_dict_value
    def config(section, key):
        if section == 'checkin' and key.endswith('_sandbox_dir'):
            return {'default': str(Path(Environment.get_tmp_dir()) / 'command_api_sandbox')}
        return original_config(section, key)
    try:
        with patch.object(Config, 'get_dict_value', config):
            return Command.execute_cmd(cmd)
    finally:
        Environment.set_security(previous)
