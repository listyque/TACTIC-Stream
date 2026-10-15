"""Unchanged calls in the actual original and native local TACTIC SDKs."""
import json
from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search
from pyasm.security import Security
from pyasm.web.api_xmlrpc import ApiXMLRPC


def record(row):
    # Generated identities/timestamps vary; relationships and keys are checked below.
    return {key: row.get(key) for key in ('note', 'process', 'context', 'login', 'project_code', 's_status')}


class Run(Command):
    def execute(self):
        self.get_transaction().set_sync(False)
        api = ApiXMLRPC()
        api.set_protocol('local')
        ticket = {'project': Project.get_project_code(), 'language': 'python'}
        kinds = ('sthpw/note', 'sthpw/task', 'sthpw/retire_log', 'sthpw/pref_setting')
        before = [Search(kind).get_count() for kind in kinds]
        rows = api.insert_multiple(ticket, 'sthpw/note', json.dumps([
            {'note': "Пакет O'Reilly", 'process': 'batch'}, {'note': 'second', 'process': 'batch'}]), [], None, False, False)
        keys = [row['__search_key__'] for row in rows]
        updated = api.update_multiple(ticket, json.dumps({keys[0]: {'note': 'updated'}, keys[1]: {'note': 'second updated'}}), False)
        assert [row['id'] for row in updated] == [row['id'] for row in rows]
        upsert = api.insert_update(ticket, 'sthpw/note?code=BATCH_UPSERT', {'note': 'new', 'process': 'batch'}, {}, None, {}, False, False)
        again = api.insert_update(ticket, upsert['__search_key__'], {'note': 'existing'}, {}, None, {}, False, False)
        assert again['id'] == upsert['id']
        unique = api.get_unique_sobject(ticket, 'sthpw/note', {'note': 'unique', 'process': 'batch'})
        same = api.get_unique_sobject(ticket, 'sthpw/note', {'note': 'unique', 'process': 'batch'})
        assert same['id'] == unique['id']
        clone = api.clone_sobject(ticket, unique['__search_key__'], {'note': 'clone'})
        assert clone['id'] != unique['id'] and clone['code'] != unique['code']
        parent = Project.get()
        task = api.create_task(ticket, parent.get_search_key(), 'batch')
        retired = api.retire_sobject(ticket, task['__search_key__'])
        retire_logs = Search('sthpw/retire_log')
        retire_logs.add_filter('search_code', task['code'])
        assert retire_logs.get_count() == 1
        active = api.reactivate_sobject(ticket, retired)
        assert not active['s_status']
        note = api.create_note(ticket, parent.get_search_key(), 'Комментарий', 'publish', 'review', 'admin')
        tasks_error = False
        try:
            tasks = api.get_tasks(ticket, parent.get_search_key(), 'batch')
        except AttributeError as error:
            if 'set_parent' not in str(error):
                raise
            tasks_error = True
            tasks = [api.get_by_search_key(ticket, task['__search_key__'])]
        assert [row['id'] for row in tasks] == [task['id']]
        pipeline_xml = api.get_pipeline_xml(ticket, task['__search_key__'])
        processes = api.get_pipeline_processes(ticket, task['__search_key__'], True)
        assert '<pipeline' in pipeline_xml and processes
        assert api.get_pipeline_processes(ticket, parent.get_search_key()) == []
        assert api.get_pipeline_xml(ticket, parent.get_search_key()) == '<pipeline/>'
        assert api.get_preference(ticket, 'batch_api') == ''
        assert api.set_preference(ticket, 'batch_api', 'Русский') is None
        assert api.get_preference(ticket, 'batch_api') == 'Русский'
        api.set_preference(ticket, 'batch_api', 'English')
        assert api.get_preference(ticket, 'batch_api') == 'English'
        if self.fail:
            raise ValueError('batch rollback')
        return {'updated': [record(row) for row in updated], 'upsert': record(again),
                'unique': record(unique), 'clone': record(clone), 'retired': record(retired),
                'active': record(active), 'note': record(note), 'tasks': [record(row) for row in tasks],
                'processes': processes, 'tasks_error': tasks_error, 'preference': api.get_preference(ticket, 'batch_api'),
                'counts': [Search(kind).get_count() - count for kind, count in zip(kinds, before)]}


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
