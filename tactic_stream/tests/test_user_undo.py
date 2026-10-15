"""Owned project CRUD replay on native vendors and the unchanged XML-RPC SDK."""
import unittest
from unittest.mock import patch
from xmlrpc.client import Fault

import test_plugin_installation as plugin_tests
from test_project_writes import install_writer, PASSWORD
from pyasm.common import Config, Xml
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search, SObjectUndo
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.api import Api


def exercise(store, prefix, password='plugin-test-password', client=None):
    check = unittest.TestCase()
    api = Api(store)
    token = api.get_ticket('admin', password)
    project = prefix + '_ok'
    stype = project + '/asset'
    admin = dict(ticket=token, project=project)
    api.dispatch('execute_cmd', (dict(ticket=token, project='admin'), 'tactic.command.CreateProjectCmd',
        dict(project_code=project, project_title='Private user replay', project_stype=['asset'])))
    install_writer(store)
    user = dict(ticket=api.get_ticket('project_writer', PASSWORD), project=project)
    if client is not None:
        client.set_ticket(user['ticket']); client.set_project(project)

    def permissions(access='allow', project_access='allow', extra=''):
        api.dispatch('update', (admin, 'sthpw/login_group?code=project_writers', {'access_rules':
            '<rules><rule group="project" code="%s" access="%s"/>'
            '<rule group="search_type" code="%s" project="%s" access="%s"/>%s</rules>' %
            (project, project_access, stype, project, access, extra)}))

    def call(method, *args, **kwargs):
        if client is not None:
            return getattr(client, method)(*args, **kwargs)
        return api.dispatch(method, (user, *args), kwargs)

    def journals(login='project_writer'):
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            search = Search('sthpw/transaction_log')
            search.add_filter('login', login); search.add_filter('namespace', project)
            search.add_order_by('id')
            return [dict(row.get_data()) for row in search.get_sobjects()]

    def state():
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            return {kind: [dict(row.get_data()) for row in Search(kind).get_sobjects()]
                for kind in (stype, 'sthpw/sobject_list', 'sthpw/transaction_log', 'sthpw/change_timestamp', 'sthpw/sobject_log')}

    def row(code):
        return api.dispatch('get_by_code', (admin, stype, code))

    permissions()
    created = call('insert', stype, dict(code='USER_REPLAY', name='before'))
    key = created['__search_key__']
    inserted = journals()[-1]['id']
    call('undo', transaction_id=inserted)
    check.assertEqual(row('USER_REPLAY'), {})
    check.assertEqual(journals()[-1]['type'], 'redo')
    denied = SecurityException if client is None else Fault
    before = state()
    with check.assertRaises(denied):
        call('undo', transaction_id=inserted)
    check.assertEqual(state(), before)
    call('redo', transaction_id=inserted)
    check.assertEqual(row('USER_REPLAY')['name'], 'before')
    call('update', key, dict(name='after'))
    call('undo')
    check.assertEqual(row('USER_REPLAY')['name'], 'before')
    call('redo')
    check.assertEqual(row('USER_REPLAY')['name'], 'after')
    call('update', key, dict(code='USER_RENAMED'))
    renamed = journals()[-1]['id']
    call('undo', transaction_id=renamed)
    check.assertEqual(row('USER_REPLAY')['name'], 'after')
    call('redo', transaction_id=renamed)
    check.assertEqual(row('USER_RENAMED')['name'], 'after')
    key = row('USER_RENAMED')['__search_key__']
    call('delete_sobject', key)
    deleted = journals()[-1]['id']
    call('undo', transaction_id=deleted)
    check.assertEqual(row('USER_RENAMED')['name'], 'after')
    call('redo', transaction_id=deleted)
    check.assertEqual(row('USER_RENAMED'), {})
    call('undo', transaction_id=deleted)
    call('update', key, dict(description='fresh branch'))
    check.assertTrue(all(log['type'] == 'undo' for log in journals()))

    api.dispatch('insert', (admin, stype, dict(code='SECOND', name='second before')))
    second = row('SECOND')['__search_key__']
    call('update_multiple', {key: dict(name='batch after'), second: dict(name='batch after')})
    batch = journals()[-1]['id']
    check.assertEqual(sum(node.get('search_type').startswith(stype + '?')
        for node in Xml(journals()[-1]['transaction']).get_nodes('transaction/sobject')), 2)
    for options in (dict(access='view'), dict(project_access='deny'),
            dict(extra='<rule group="sobject" project="%s" search_type="%s" code="SECOND" access="deny"/>' % (project, stype)),
            dict(extra='<rule group="sobject_column" project="%s" search_type="%s" column="name" access="deny"/>' % (project, stype)),
            dict(extra='<rule group="search_filter" search_type="%s" column="code" value="HIDDEN"/>' % stype)):
        permissions(**options)
        before = state()
        with check.assertRaises(denied) as caught:
            call('undo', transaction_id=batch)
        if client is not None:
            check.assertEqual(caught.exception.faultCode, 403)
        check.assertEqual(state(), before)
    permissions()
    before = state()
    native_undo = SObjectUndo.undo
    seen = []
    def fail_second(node):
        native_undo(node)
        if node.get('search_type').startswith(stype + '?'):
            seen.append(node.get('search_code'))
        if len(seen) == 2:
            raise ValueError('late user undo failure')
    with patch.object(SObjectUndo, 'undo', fail_second):
        with check.assertRaises(ValueError if client is None else Fault):
            call('undo', transaction_id=batch)
    check.assertEqual(len(seen), 2)
    check.assertEqual(state(), before)
    call('undo', transaction_id=batch)
    check.assertEqual(row('USER_RENAMED')['name'], 'after')
    check.assertEqual(row('SECOND')['name'], 'second before')
    permissions(access='view')
    before = state()
    with check.assertRaises(denied):
        call('redo', transaction_id=batch)
    check.assertEqual(state(), before)
    permissions()
    before = state()
    native_redo = SObjectUndo.redo
    seen.clear()
    def fail_redo_second(node, no_exception=True):
        native_redo(node, no_exception)
        if node.get('search_type').startswith(stype + '?'):
            seen.append(node.get('search_code'))
        if len(seen) == 2:
            raise ValueError('late user redo failure')
    with patch.object(SObjectUndo, 'redo', fail_redo_second):
        with check.assertRaises(ValueError if client is None else Fault):
            call('redo', transaction_id=batch)
    check.assertEqual(len(seen), 2)
    check.assertEqual(state(), before)
    call('redo', transaction_id=batch)
    check.assertEqual(row('SECOND')['name'], 'batch after')

    from concurrent.futures import ThreadPoolExecutor
    call('update', second, dict(name='race after'))
    concurrent = journals()[-1]['id']
    def undo_once(_):
        try:
            api.dispatch('undo', (user, None, concurrent))
            return 'undone'
        except SecurityException:
            return 'denied'
    with ThreadPoolExecutor(max_workers=2) as pool:
        check.assertEqual(sorted(pool.map(undo_once, range(2))), ['denied', 'undone'])
    check.assertEqual(row('SECOND')['name'], 'batch after')
    call('redo', transaction_id=concurrent)
    check.assertEqual(row('SECOND')['name'], 'race after')

    foreign = journals('admin')[-1]['id']
    before = state()
    with check.assertRaises(denied):
        call('undo', transaction_id=foreign)
    with check.assertRaises(SecurityException):
        api.dispatch('undo', (dict(user, project='admin'), None, batch))
    check.assertEqual(state(), before)
    permissions(extra='<rule group="api_method" key="undo" access="deny"/>')
    get_value = Config.get_value
    with patch.object(Config, 'get_value', side_effect=lambda section, name, *args, **kwargs:
            'true' if (section, name) == ('security', 'api_method_restricted') else get_value(section, name, *args, **kwargs)):
        with check.assertRaises(denied):
            call('undo', transaction_id=batch)
    permissions()
    from xmlrpc.client import Binary
    api.dispatch('upload_file', (user, 'owned-upload.bin', Binary(b'owned undo guard')))
    file_log = journals()[-1]['id']
    before = state()
    with check.assertRaises(UnsupportedContract if client is None else Fault):
        call('undo', transaction_id=file_log, ignore_files=True)
    check.assertEqual(state(), before)
    original = journals()[-1]
    with request_context(RequestContext(store, 'admin', project)):
        api.auth.bind_security('admin', token)
        from pyasm.command import Command
        def replace_xml(xml):
            cmd = Command()
            def execute():
                cmd.get_transaction().set_record(False); cmd.get_transaction().set_sync(False)
                log = Search.get_by_id('sthpw/transaction_log', original['id'])
                log.set_value('transaction', xml); log.commit()
            cmd.execute = execute
            Command.execute_cmd(cmd)
        for suffix in ('<file type="create" src="outside"/>', '<table action="drop" database="outside" table="asset"/>',
                       '<sobject search_type="sthpw/login" action="update" search_code="admin"/>',
                       '<sobject search_type="%s?project=admin" action="update" search_code="SECOND"/>' % stype):
            replace_xml('<transaction>' + suffix + '</transaction>')
            before = state()
            with check.assertRaises(UnsupportedContract if client is None else Fault):
                call('undo', transaction_id=original['id'], ignore_files=True)
            check.assertEqual(state(), before)
        replace_xml(original['transaction'])
    before = state()
    with request_context(RequestContext(store, 'project_writer', project)):
        api.auth.bind_security('project_writer', user['ticket'])
        command = Command()
        def forged():
            log = Search.get_by_id('sthpw/transaction_log', original['id'])
            log.set_value('transaction', '<transaction/>')
            log.undo()
        command.execute = forged
        with check.assertRaises(SecurityException):
            Command.execute_cmd(command)
    check.assertEqual(state(), before)
    with check.assertRaises(denied):
        call('execute_transaction', '<transaction/>')
    return dict(crud=True, ownership=True, rights=True, rollback=True)


class UserUndo(plugin_tests.PluginInstallation):
    exercise = staticmethod(exercise)


class UserUndoTransport(unittest.TestCase):
    def test_original_sdk_user_undo_redo(self):
        import importlib.util
        import test_transport
        import test_read_parity
        test_transport.Transport.setUpClass()
        client = None
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.user_undo_client',
                test_read_parity.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            client = module.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            self.assertTrue(exercise(test_transport.Transport.store, 'rpc_undo', password='private-test-password', client=client)['rollback'])
        finally:
            if client is not None:
                client.server.__exit__(None, None, None)
            test_transport.Transport.tearDownClass()
