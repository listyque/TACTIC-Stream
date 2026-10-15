"""Owned native check-in replay, including versionless bytes and compensation."""
from pathlib import Path
import unittest
from unittest.mock import patch
from xmlrpc.client import Binary, Fault

import test_plugin_installation as plugin_tests
from test_project_writes import install_writer, PASSWORD
from pyasm.common import Common, Environment, Xml
from pyasm.common.errors import SecurityException, UnsupportedContract
from pyasm.search import Search, FileUndo, SObjectUndo
from pyasm.search.transaction import FileUndoReplay
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.api import Api


def exercise(store, prefix, password='plugin-test-password', client=None):
    check = unittest.TestCase()
    api = Api(store)
    token = api.get_ticket('admin', password)
    project = prefix + '_ok'
    admin = dict(ticket=token, project=project)
    api.dispatch('execute_cmd', (dict(ticket=token, project='admin'), 'tactic.command.CreateProjectCmd',
        dict(project_code=project, project_title='Private file replay', project_stype=['asset'])))
    parent = api.dispatch('insert', (admin, project + '/asset', dict(code='FILE_REPLAY', name='Private object')))
    for context in ('publish', 'frames'):
        for latest in (False, True):
            api.dispatch('insert', (admin, 'config/naming', dict(search_type=project + '/asset', context=context,
                latest_versionless=latest, file_naming='{basefile}_{file_type}' + ('' if latest else '_v{version}') + '.{ext}',
                dir_naming='{project.code}/{search_type.table_name}/{code}/{snapshot.process}/' + ('latest' if latest else 'versions'))))
    install_writer(store)
    user = dict(ticket=api.get_ticket('project_writer', PASSWORD), project=project)
    if client is not None:
        client.set_ticket(user['ticket']); client.set_project(project)

    def permissions(parent_access='allow', snapshot_access='allow', file_access='allow', extra=''):
        api.dispatch('update', (admin, 'sthpw/login_group?code=project_writers', {'access_rules':
            '<rules><rule group="project" code="%s" access="allow"/>'
            '<rule group="search_type" code="%s/asset" access="%s"/>'
            '<rule group="search_type" code="sthpw/snapshot" access="%s"/>'
            '<rule group="search_type" code="sthpw/file" access="%s"/>%s</rules>' %
            (project, project, parent_access, snapshot_access, file_access, extra)}))

    def call(method, *args, **kwargs):
        if client is not None and method == 'upload_file':
            return client.server.upload_file(client.ticket, *args)
        return getattr(client, method)(*args, **kwargs) if client is not None else api.dispatch(method, (user, *args), kwargs)

    def journals():
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            query = Search('sthpw/transaction_log')
            query.add_filter('login', 'project_writer'); query.add_filter('namespace', project); query.add_order_by('id')
            return [row.get_data() for row in query.get_sobjects()]

    def lib_path(code):
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            return Path(Search.get_by_code('sthpw/snapshot', code).get_lib_path_by_type())

    def state():
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            records = {kind: [row.get_data() for row in Search(kind).get_sobjects()] for kind in
                (project + '/asset', 'sthpw/file', 'sthpw/snapshot', 'sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp')}
            asset = Path(Environment.get_asset_dir())
            files = {str(path.relative_to(asset)): path.read_bytes() for path in asset.rglob('*') if path.is_file()}
            return records, files

    def assert_versions(expected):
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            query = Search('sthpw/snapshot'); query.add_filter('search_code', 'FILE_REPLAY'); query.add_filter('context', 'publish')
            snapshots = query.get_sobjects()
            check.assertEqual(sorted(row.get_value('version') for row in snapshots), expected)
            current = [row for row in snapshots if row.get_value('version') > 0 and row.get_value('is_latest')]
            check.assertEqual([row.get_value('version') for row in current], [max(expected)])
            for row in snapshots:
                for node in row.get_xml_value('snapshot').get_nodes('snapshot/file'):
                    file = Search.get_by_code('sthpw/file', node.get('file_code'))
                    check.assertIsNotNone(file)
                    check.assertEqual(file.get_value('snapshot_code'), row.get_code())

    permissions()
    for value in (b'first replay file', b'second replay file'):
        call('upload_file', 'replay.txt', Binary(value))
        snapshot = call('simple_checkin', parent['__search_key__'], 'publish', 'replay.txt', create_icon=False)
        if snapshot['version'] == 1:
            first = snapshot
            first_id = journals()[-1]['id']
            path = lib_path(first['code'])
            call('undo', transaction_id=first_id)
            check.assertFalse(path.exists())
            call('redo', transaction_id=first_id)
            check.assertEqual(path.read_bytes(), value)
            assert_versions([-1, 1])
    second = snapshot
    latest = api.dispatch('get_snapshot', (admin, parent['__search_key__'], 'publish'), dict(version=-1, versionless=True))
    first_path, second_path, latest_path = (lib_path(row['code']) for row in (first, second, latest))
    log_id = journals()[-1]['id']
    denied = SecurityException if client is None else Fault
    for options in (dict(parent_access='view'), dict(snapshot_access='view'), dict(file_access='view'),
            dict(extra='<rule group="sobject" search_type="sthpw/snapshot" project="%s" code="%s" access="deny"/>' % (project, second['code'])),
            dict(extra='<rule group="sobject_column" search_type="sthpw/file" project="%s" column="snapshot_code" access="deny"/>' % project)):
        permissions(**options)
        before = state()
        with check.assertRaises(denied):
            call('undo', transaction_id=log_id)
        check.assertEqual(state(), before)
    permissions()
    before = state()
    with check.assertRaises(UnsupportedContract if client is None else Fault):
        call('undo', transaction_id=log_id, ignore_files=True)
    check.assertEqual(state(), before)
    apply = FileUndoReplay.apply
    for direction in ('undo', 'redo'):
        before = state()
        applied = []
        def fail_after_io(self, node):
            apply(self, node)
            applied.append(node)
            if len(applied) == 2:
                raise ValueError('late replay IO failure')
        with patch.object(FileUndoReplay, 'apply', fail_after_io):
            with check.assertRaises(ValueError if client is None else Fault):
                call(direction, transaction_id=log_id)
        check.assertEqual(len(applied), 2)
        check.assertEqual(state(), before)
        call(direction, transaction_id=log_id)
        if direction == 'undo':
            assert_versions([-1, 1])
            check.assertEqual(first_path.read_bytes(), b'first replay file')
            check.assertFalse(second_path.exists())
            check.assertEqual(latest_path.read_bytes(), b'first replay file')
            permissions(file_access='view')
            before = state()
            with check.assertRaises(denied):
                call('redo', transaction_id=log_id)
            check.assertEqual(state(), before)
            permissions()
        else:
            assert_versions([-1, 1, 2])
    # A late metadata failure also compensates IO after the outer scope has closed.
    undo = SObjectUndo.undo
    def fail_after_metadata(node):
        undo(node)
        if node.get('search_type') == 'sthpw/snapshot' and node.get('action') == 'insert':
            raise ValueError('late replay metadata failure')
    before = state()
    with patch.object(SObjectUndo, 'undo', fail_after_metadata):
        with check.assertRaises(ValueError if client is None else Fault):
            call('undo', transaction_id=log_id)
    check.assertEqual(state(), before)
    # Replay scope cannot authorize a different fabricated file node.
    call('undo', transaction_id=log_id)
    redo = SObjectUndo.redo
    def forged_node(node, *args, **kwargs):
        with check.assertRaises(SecurityException):
            FileUndo.undo(Xml('<file type="remove" src="outside" dst="outside"/>').get_root_node())
        return redo(node, *args, **kwargs)
    with patch.object(SObjectUndo, 'redo', forged_node):
        call('redo', transaction_id=log_id)
    check.assertEqual(second_path.read_bytes(), b'second replay file')
    check.assertEqual(latest_path.read_bytes(), b'second replay file')
    # This failure is inside the IO call, with a real partial destination.
    call('undo', transaction_id=log_id)
    before = state()
    import shutil
    move = shutil.move
    def partial_move(source, destination, *args, **kwargs):
        if Path(destination) == second_path:
            Path(destination).write_bytes(b'partial version')
            raise OSError('partial version failure')
        return move(source, destination, *args, **kwargs)
    with patch('pyasm.search.transaction.shutil.move', side_effect=partial_move):
        with check.assertRaises(OSError if client is None else Fault):
            call('redo', transaction_id=log_id)
    check.assertEqual(state(), before)
    call('redo', transaction_id=log_id)
    check.assertEqual(second_path.read_bytes(), b'second replay file')
    check.assertEqual(latest_path.read_bytes(), b'second replay file')
    # Even a persisted own journal cannot replay a path outside its repository metadata.
    from pyasm.command import Command
    original_xml = journals()[-1]['transaction']
    def replace_xml(data):
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            command = Command()
            def save():
                command.get_transaction().set_record(False); command.get_transaction().set_sync(False)
                log = Search.get_by_id('sthpw/transaction_log', log_id)
                log.set_value('transaction', data); log.commit(triggers='none')
            command.execute = save; Command.execute_cmd(command)
    malformed = Xml(Common.decompress_transaction(original_xml) if original_xml.startswith('zlib:') else original_xml)
    outside = store.data_dir / 'outside-replay.txt'; outside.write_bytes(b'keep outside bytes')
    malformed.get_nodes('transaction/file')[0].set('src', str(outside))
    replace_xml(malformed.to_string())
    before = state()
    with check.assertRaises(denied):
        call('undo', transaction_id=log_id)
    check.assertEqual(state(), before); check.assertEqual(outside.read_bytes(), b'keep outside bytes')
    replace_xml(original_xml)
    # Appending a type restores the original snapshot XML and its versionless alias.
    call('upload_file', 'append.txt', Binary(b'append replay'))
    added = call('add_file', second['code'], 'append.txt', 'extra', mode=None if client is not None else 'uploaded')
    appended_id = journals()[-1]['id']
    with request_context(RequestContext(store, 'admin', project)):
        api.auth.bind_security('admin', token)
        appended_path = Path(Search.get_by_code('sthpw/snapshot', added['code']).get_lib_path_by_type('extra'))
    call('undo', transaction_id=appended_id)
    check.assertFalse(appended_path.exists())
    call('redo', transaction_id=appended_id)
    check.assertEqual(appended_path.read_bytes(), b'append replay')
    # Sequence expansion uses native FileGroup/FileRange, not a second path parser.
    for frame in (1, 3):
        call('upload_file', 'frame.%04d.txt' % frame, Binary(('frame %s' % frame).encode()))
    grouped = api.dispatch('group_checkin', (user, parent['__search_key__'], 'frames', 'frame.####.txt', '1-3/2'), dict(mode='upload'))
    grouped_id = journals()[-1]['id']
    with request_context(RequestContext(store, 'admin', project)):
        api.auth.bind_security('admin', token)
        paths = [Path(path) for path in Search.get_by_code('sthpw/snapshot', grouped['code']).get_paths_by_type('main')]
    call('undo', transaction_id=grouped_id)
    check.assertTrue(all(not path.exists() for path in paths))
    call('redo', transaction_id=grouped_id)
    check.assertEqual([path.read_bytes() for path in paths], [b'frame 1', b'frame 3'])
    return dict(files=True, versionless=True, permissions=True, rollback=True, append=True, groups=True)


class UserFileUndo(plugin_tests.PluginInstallation):
    exercise = staticmethod(exercise)


class UserFileUndoTransport(unittest.TestCase):
    def test_original_sdk_file_undo_redo(self):
        import importlib.util
        import test_transport
        import test_read_parity
        test_transport.Transport.setUpClass()
        client = None
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.user_file_undo_client',
                test_read_parity.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            client = module.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            self.assertTrue(exercise(test_transport.Transport.store, 'rpc_file_undo', password='private-test-password', client=client)['files'])
        finally:
            if client is not None:
                client.server.__exit__(None, None, None)
            test_transport.Transport.tearDownClass()
