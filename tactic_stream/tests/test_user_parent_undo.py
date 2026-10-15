"""Owned task/note writes and replay on native vendors and the stock SDK."""
import unittest
from unittest.mock import patch
from xmlrpc.client import Fault

import test_plugin_installation as plugin_tests
from test_project_writes import install_writer, PASSWORD
from pyasm.common import Container, Xml
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search, SObjectUndo
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.api import Api


def exercise(store, prefix, password='plugin-test-password', client=None):
    check = unittest.TestCase()
    api = Api(store)
    token = api.get_ticket('admin', password)
    project = prefix + '_ok'
    admin = dict(ticket=token, project=project)
    api.dispatch('execute_cmd', (dict(ticket=token, project='admin'), 'tactic.command.CreateProjectCmd',
        dict(project_code=project, project_title='Private task/note replay', project_stype=['asset'])))
    parent = api.dispatch('insert', (admin, project + '/asset', dict(code='PARENT_REPLAY', name='Parent')))
    other = api.dispatch('insert', (admin, project + '/asset', dict(code='OTHER_REPLAY', name='Other')))
    install_writer(store)
    user = dict(ticket=api.get_ticket('project_writer', PASSWORD), project=project)
    if client is not None:
        client.set_ticket(user['ticket']); client.set_project(project)

    def permissions(parent_access='allow', task_access='allow', note_access='allow', extra=''):
        api.dispatch('update', (admin, 'sthpw/login_group?code=project_writers', {'access_rules':
            '<rules><rule group="project" code="%s" access="allow"/>'
            '<rule group="search_type" code="%s/asset" access="%s"/>'
            '<rule group="search_type" code="sthpw/task" project="%s" access="%s"/>'
            '<rule group="search_type" code="sthpw/note" project="%s" access="%s"/>%s</rules>' %
            (project, project, parent_access, project, task_access, project, note_access, extra)}))

    def call(method, *args, **kwargs):
        return getattr(client, method)(*args, **kwargs) if client is not None else api.dispatch(method, (user, *args), kwargs)

    def journals():
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            query = Search('sthpw/transaction_log'); query.add_filter('login', 'project_writer')
            query.add_filter('namespace', project); query.add_order_by('id')
            return [row.get_data() for row in query.get_sobjects()]

    def state():
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            return {kind: [row.get_data() for row in Search(kind).get_sobjects()] for kind in
                (project + '/asset', 'sthpw/task', 'sthpw/note', 'sthpw/status_log', 'sthpw/message', 'sthpw/message_log',
                 'config/process_state', 'sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp')}

    def row(stype, code):
        return api.dispatch('get_by_code', (admin, stype, code))

    permissions()
    task = call('create_task', parent['__search_key__'], process='work', description='Before task')
    task_id = journals()[-1]['id']
    call('undo', transaction_id=task_id)
    check.assertEqual(row('sthpw/task', task['code']), {})
    call('redo', transaction_id=task_id)
    check.assertEqual(row('sthpw/task', task['code'])['description'], 'Before task')
    call('update', task['__search_key__'], dict(description='After task'))
    changed_id = journals()[-1]['id']
    denied = SecurityException if client is None else Fault
    permissions(task_access='view')
    before = state()
    with check.assertRaises(denied):
        call('undo', transaction_id=changed_id)
    check.assertEqual(state(), before); permissions()
    call('undo', transaction_id=changed_id)
    check.assertEqual(row('sthpw/task', task['code'])['description'], 'Before task')
    call('redo', transaction_id=changed_id)
    call('update', task['__search_key__'], dict(status='Complete'))
    status_log = journals()[-1]
    check.assertTrue(any(node.get('search_type') == 'sthpw/status_log' for node in Xml(status_log['transaction']).get_nodes('transaction/sobject')))
    before = state()
    call('undo', transaction_id=status_log['id'])
    check.assertNotEqual(state(), before)
    check.assertIsNone(row('sthpw/task', task['code'])['status'])
    call('redo', transaction_id=status_log['id'])
    check.assertEqual(row('sthpw/task', task['code'])['status'], 'Complete')
    call('delete_sobject', task['__search_key__'])
    deleted_id = journals()[-1]['id']
    call('undo', transaction_id=deleted_id)
    check.assertEqual(row('sthpw/task', task['code'])['description'], 'After task')
    call('redo', transaction_id=deleted_id)
    check.assertEqual(row('sthpw/task', task['code']), {})
    note = call('create_note', parent['__search_key__'], 'До заметки', process='work')
    note_id = journals()[-1]['id']
    call('undo', transaction_id=note_id)
    check.assertEqual(row('sthpw/note', note['code']), {})
    call('redo', transaction_id=note_id)
    check.assertEqual(row('sthpw/note', note['code'])['id'], note['id'])
    call('update', note['__search_key__'], dict(note='После заметки'))
    changed_id = journals()[-1]['id']
    call('undo', transaction_id=changed_id)
    check.assertEqual(row('sthpw/note', note['code'])['note'], 'До заметки')
    call('redo', transaction_id=changed_id)
    call('update', note['__search_key__'], dict(code=note['code'] + '_RENAMED'))
    renamed_id = journals()[-1]['id']
    call('undo', transaction_id=renamed_id)
    check.assertEqual(row('sthpw/note', note['code'])['note'], 'После заметки')
    call('redo', transaction_id=renamed_id)
    note = row('sthpw/note', note['code'] + '_RENAMED')
    call('delete_sobject', note['__search_key__'])
    deleted_id = journals()[-1]['id']
    call('undo', transaction_id=deleted_id)
    check.assertEqual(row('sthpw/note', note['code'])['id'], note['id'])
    call('redo', transaction_id=deleted_id)
    check.assertEqual(row('sthpw/note', note['code']), {})
    call('undo', transaction_id=deleted_id)
    note = row('sthpw/note', note['code'])
    reply = call('insert', 'sthpw/note', dict(note='Reply', process='work', context='work', login='project_writer',
        project_code=project, search_type=project + '/asset?project=' + project, search_code=parent['code'],
        search_id=parent['id'], parent_id=note['id']))
    before = state()
    with check.assertRaises(UnsupportedContract if client is None else Fault):
        call('delete_sobject', note['__search_key__'])
    check.assertEqual(state(), before)
    call('delete_sobject', reply['__search_key__'])
    reply_deleted = journals()[-1]['id']
    call('delete_sobject', note['__search_key__'])
    root_deleted = journals()[-1]['id']
    call('undo', transaction_id=root_deleted)
    call('undo', transaction_id=reply_deleted)
    restored_reply = row('sthpw/note', reply['code'])
    check.assertEqual(restored_reply['parent_id'], row('sthpw/note', note['code'])['id'])
    check.assertEqual(restored_reply['id'], reply['id'])
    call('redo', transaction_id=reply_deleted)
    call('redo', transaction_id=root_deleted)
    # An old insert journal without the new ID anchor captures it before undo.
    note = call('create_note', parent['__search_key__'], 'Old journal', process='work')
    old_log = journals()[-1]
    from pyasm.command import Command
    def replace_xml(log_id, data):
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            command = Command()
            def save():
                command.get_transaction().set_record(False); command.get_transaction().set_sync(False)
                log = Search.get_by_id('sthpw/transaction_log', log_id)
                log.set_value('transaction', data); log.commit(triggers='none')
            command.execute = save; Command.execute_cmd(command)
    old_xml = Xml(old_log['transaction'])
    for node in old_xml.get_nodes('transaction/sobject'):
        node.attrib.pop('search_id', None)
    replace_xml(old_log['id'], old_xml.to_string())
    call('undo', transaction_id=old_log['id'])
    # A reused primary key must fail restoration, never overwrite the new note.
    with request_context(RequestContext(store, 'admin', project)):
        api.auth.bind_security('admin', token)
        command = Command()
        def occupy_id():
            from pyasm.search import SearchType
            command.get_transaction().set_record(False); command.get_transaction().set_sync(False)
            occupied = SearchType.create('sthpw/note')
            occupied.set_parent(Search.get_by_search_key(parent['__search_key__']))
            occupied.set_id(note['id']); occupied.set_force_insert()
            for name, value in dict(code='OCCUPIED_NOTE_ID', login='admin', process='work', context='work', note='Keep intact').items():
                occupied.set_value(name, value)
            occupied.commit(triggers='none')
        command.execute = occupy_id; Command.execute_cmd(command)
    before = state()
    with check.assertRaises(Exception if client is None else Fault):
        call('redo', transaction_id=old_log['id'])
    check.assertEqual(state(), before)
    api.dispatch('delete_sobject', (admin, 'sthpw/note?code=OCCUPIED_NOTE_ID'))
    call('redo', transaction_id=old_log['id'])
    check.assertEqual(row('sthpw/note', note['code'])['id'], note['id'])
    zero_root = call('insert', 'sthpw/note', dict(note='Zero root', process='work', context='work', login='project_writer',
        parent_id=0), parent_key=parent['__search_key__'])
    zero_log = journals()[-1]['id']
    call('undo', transaction_id=zero_log); call('redo', transaction_id=zero_log)
    check.assertEqual(row('sthpw/note', zero_root['code'])['parent_id'], 0)
    # Current permissions are rechecked before either replay direction.
    call('update', note['__search_key__'], dict(note='Permissions'))
    edited = journals()[-1]['id']
    for options in (dict(parent_access='view'), dict(note_access='view'),
            dict(extra='<rule group="sobject" project="%s" search_type="sthpw/note" code="%s" access="deny"/>' % (project, note['code'])),
            dict(extra='<rule group="sobject_column" project="%s" search_type="sthpw/note" column="note" access="deny"/>' % project),
            dict(extra='<rule group="search_filter" search_type="%s/asset" column="code" value="HIDDEN"/>' % project)):
        permissions(**options)
        before = state()
        with check.assertRaises(denied):
            call('undo', transaction_id=edited)
        check.assertEqual(state(), before)
    permissions()
    call('undo', transaction_id=edited)
    permissions(note_access='view')
    before = state()
    with check.assertRaises(denied):
        call('redo', transaction_id=edited)
    check.assertEqual(state(), before)
    permissions(); call('redo', transaction_id=edited)
    foreign = api.dispatch('create_note', (admin, parent['__search_key__'], 'Private admin note'), dict(process='work'))
    api.dispatch('update', (admin, foreign['__search_key__'], dict(access='private')))
    before = state()
    check.assertEqual(call('get_by_code', 'sthpw/note', foreign['code']), {})
    with check.assertRaises(LookupError if client is None else Fault):
        call('update', foreign['__search_key__'], dict(note='Wrong author'))
    check.assertEqual(state(), before)
    # Privileged read access does not grant a foreign author's write access.
    permissions(extra='<rule group="builtin" key="view_private_notes" access="view"/>')
    check.assertEqual(call('get_by_code', 'sthpw/note', foreign['code'])['note'], 'Private admin note')
    before = state()
    with check.assertRaises(denied):
        call('update', foreign['__search_key__'], dict(note='Wrong author'))
    check.assertEqual(state(), before); permissions()
    # Foreign author/reparenting is denied on the ordinary write path, too.
    for method, args in (('create_note', (parent['__search_key__'], 'Forged author')),
            ('update', (note['__search_key__'], dict(login='admin'))),
            ('update', (note['__search_key__'], dict(search_code=other['code'], search_id=other['id'])))):
        before = state()
        with check.assertRaises((SecurityException, UnsupportedContract) if client is None else Fault):
            call(method, *args, **({'user': 'admin'} if method == 'create_note' else {}))
        check.assertEqual(state(), before)
    # Workflow-produced own notes retain their native insert path and can replay separately.
    from pyasm.biz import Note
    with request_context(RequestContext(store, 'project_writer', project)):
        api.auth.bind_security('project_writer', user['ticket'])
        command = Command()
        def workflow_note():
            command.get_transaction().set_sync(False)
            source = Search.get_by_search_key(parent['__search_key__'])
            previous = Container.get('Workflow:note_source')
            Container.put('Workflow:note_source', source)
            try:
                Note.create(source, 'Workflow note', context='work', process='work')
            finally:
                Container.put('Workflow:note_source', previous)
        command.execute = workflow_note; Command.execute_cmd(command)
    workflow_log = journals()[-1]['id']
    call('undo', transaction_id=workflow_log); call('redo', transaction_id=workflow_log)
    # Batch replay rolls back already restored notes when a later native write fails.
    call('update_multiple', {note['__search_key__']: dict(note='Batch note'), parent['__search_key__']: dict(name='Batch parent')})
    batch_id = journals()[-1]['id']
    for direction in ('undo', 'redo'):
        original = getattr(SObjectUndo, direction)
        touched = []
        def late(node, *args, **kwargs):
            result = original(node, *args, **kwargs)
            if node.get('search_type') != 'sthpw/sobject_list':
                touched.append(node)
                if len(touched) == 2:
                    raise ValueError('late parent replay failure')
            return result
        before = state()
        with patch.object(SObjectUndo, direction, late):
            with check.assertRaises(ValueError if client is None else Fault):
                call(direction, transaction_id=batch_id)
        check.assertEqual(len(touched), 2); check.assertEqual(state(), before)
        call(direction, transaction_id=batch_id)
    return dict(task=True, note=True)


class UserParentUndo(plugin_tests.PluginInstallation):
    exercise = staticmethod(exercise)


class UserParentUndoTransport(unittest.TestCase):
    def test_original_sdk_task_note_undo_redo(self):
        import importlib.util
        import test_transport
        import test_read_parity
        test_transport.Transport.setUpClass()
        client = None
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.user_parent_undo_client',
                test_read_parity.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            client = module.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            self.assertTrue(exercise(test_transport.Transport.store, 'rpc_parent_undo', password='private-test-password', client=client)['note'])
        finally:
            if client is not None:
                client.server.__exit__(None, None, None)
            test_transport.Transport.tearDownClass()
