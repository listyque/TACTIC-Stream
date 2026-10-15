"""Ordinary-user ticket upload and native check-in on both database vendors."""
from pathlib import Path
import unittest
from unittest.mock import patch
from xmlrpc.client import Binary

import test_plugin_installation as plugin_tests
from test_project_writes import install_writer, PASSWORD
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from pyasm.search import Search, FileUndo
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.api import Api


def exercise(store, prefix, password='plugin-test-password', client=None, groups=False, http=False):
    check = unittest.TestCase()
    api = Api(store)
    token = api.get_ticket('admin', password)
    project = prefix + '_ok'
    admin = dict(ticket=token, project=project)
    api.dispatch('execute_cmd', (dict(ticket=token, project='admin'), 'tactic.command.CreateProjectCmd',
        dict(project_code=project, project_title='Private file permissions', project_stype=['asset'])))
    parent = api.dispatch('insert', (admin, project + '/asset', dict(code='FILE_PARENT', name='Private object')))
    other = api.dispatch('insert', (admin, project + '/asset', dict(code='OTHER_PARENT', name='Other object')))
    for context in (('frames', 'publish') if groups or http else ('publish',)):
        api.dispatch('insert', (admin, 'config/naming', dict(search_type=project + '/asset', context=context,
            file_naming='{basefile}_{file_type}_v{version}.{ext}',
            dir_naming='{project.code}/{search_type.table_name}/{code}/{snapshot.process}/versions')))
        api.dispatch('insert', (admin, 'config/naming', dict(search_type=project + '/asset', context=context, latest_versionless=True,
            file_naming='{basefile}_{file_type}.{ext}',
            dir_naming='{project.code}/{search_type.table_name}/{code}/{snapshot.process}/latest')))
    install_writer(store)
    user = dict(ticket=api.get_ticket('project_writer', PASSWORD), project=project)
    if client is not None:
        client.set_ticket(user['ticket']); client.set_project(project)
    sources = store.data_dir / 'http_sources'
    if http:
        sources.mkdir(parents=True, exist_ok=True)
    from xmlrpc.client import Fault
    denied = SecurityException if client is None else Fault
    def permissions(project_access='allow', parent_access='allow', snapshot_access='allow', file_access='allow', extra=''):
        xml = ('<rules><rule group="project" code="%s" access="%s"/>'
            '<rule group="search_type" code="%s/asset" project="%s" access="%s"/>'
            '<rule group="search_type" code="sthpw/snapshot" access="%s"/>'
            '<rule group="search_type" code="sthpw/file" access="%s"/>%s</rules>') % \
            (project, project_access, project, project, parent_access, snapshot_access, file_access, extra)
        api.dispatch('update', (admin, 'sthpw/login_group?code=project_writers', {'access_rules': xml}))
    def records():
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            return {kind: [dict(row.data) for row in Search(kind).get_sobjects()]
                    for kind in ('sthpw/snapshot', 'sthpw/file', 'sthpw/sobject_log', 'sthpw/transaction_log', 'sthpw/change_timestamp')}
    def paths():
        with request_context(RequestContext(store, 'project_writer', project)):
            api.auth.bind_security('project_writer', user['ticket'])
            return Path(Environment.get_upload_dir()) / 'private.txt', Path(Environment.get_asset_dir())
    def checkin(**kwargs):
        if client is not None:
            return client.simple_checkin(parent['__search_key__'], 'publish', 'private.txt', create_icon=False, **kwargs)
        return api.dispatch('simple_checkin', (user, parent['__search_key__'], 'publish', 'private.txt'),
            dict(create_icon=False, **kwargs))
    def upload_file(data):
        if http:
            if client is not None:
                path = sources / 'private.txt'
                path.write_bytes(data)
                return client.upload_file(str(path), chunk_size=113)
            return api.http_upload({'ticket': user['ticket']}, [('private.txt', data)])
        if client is not None:
            return client.server.upload_file(client.ticket, 'private.txt', Binary(data))
        return api.dispatch('upload_file', (user, 'private.txt', Binary(data)))
    def lib_path(code):
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            return Path(Search.get_by_code('sthpw/snapshot', code).get_lib_path_by_type())
    permissions()
    upload, assets = paths()
    upload_file(b'first private file')
    check.assertEqual(upload.read_bytes(), b'first private file')
    if http:
        from pyasm.common.errors import AuthenticationError, UnsupportedContract, TacticException
        for fields, error in (({'ticket': 'invalid-ticket'}, AuthenticationError),
                ({'ticket': user['ticket'], 'transaction_ticket': token}, UnsupportedContract),
                ({'ticket': user['ticket'], 'upload_dir': str(assets)}, UnsupportedContract),
                ({'ticket': user['ticket'], 'subdir': '../escape'}, TacticException)):
            with check.assertRaises(error):
                api.http_upload(fields, [('private.txt', b'damaged')])
            check.assertEqual(upload.read_bytes(), b'first private file')
        before = records()
        with check.assertRaises(ValueError):
            api.http_upload({'ticket': user['ticket']}, [('private.txt', b'replaced'), ('broken.bin', b'data:xyz/xyz;base64,???')])
        check.assertEqual(records(), before)
        check.assertEqual(upload.read_bytes(), b'first private file')
        check.assertFalse((upload.parent / 'broken.bin').exists())
        from pyasm.common import Config
        permissions(extra='<rule group="api_method" key="upload_file" access="deny"/>')
        get_value = Config.get_value
        with patch.object(Config, 'get_value', side_effect=lambda section, key, *args, **kwargs:
                'true' if (section, key) == ('security', 'api_method_restricted') else get_value(section, key, *args, **kwargs)):
            with check.assertRaises(SecurityException):
                api.http_upload({'ticket': user['ticket']}, [('private.txt', b'damaged')])
            if client is not None:
                from tactic_client_lib.common import TacticUploadException
                with check.assertRaises(TacticUploadException):
                    client.upload_file(str(sources / 'private.txt'))
        check.assertEqual(upload.read_bytes(), b'first private file')
        permissions()
    for options in (dict(project_access='deny'), dict(parent_access='view'),
                    dict(snapshot_access='view'), dict(file_access='view'),
                    dict(extra='<rule group="sobject_column" search_type="sthpw/snapshot" column="context" project="%s" access="deny"/>' % project)):
        permissions(**options)
        before = records()
        with check.assertRaises(denied) as error:
            checkin()
        if client is not None:
            check.assertEqual(error.exception.faultCode, 403)
        check.assertEqual(records(), before)
        check.assertEqual(upload.read_bytes(), b'first private file')
    permissions()
    first = checkin(metadata={'private': 'Первый файл'})
    check.assertEqual(first['version'], 1)
    check.assertEqual(first['login'], 'project_writer')
    check.assertEqual(first['project_code'], project)
    first_path = lib_path(first['code'])
    check.assertEqual(first_path.read_bytes(), b'first private file')
    upload_file(b'second private file')
    before = records()
    files_before = {path.relative_to(assets): path.read_bytes() for path in assets.rglob('*') if path.is_file()}
    from pyasm.checkin import FileCheckin
    original = FileCheckin.call_triggers
    def fail(self):
        original(self)
        raise ValueError('late file check-in failure')
    with patch.object(FileCheckin, 'call_triggers', fail):
        with check.assertRaises(ValueError if client is None else Fault):
            checkin()
    check.assertEqual(records(), before)
    check.assertEqual({path.relative_to(assets): path.read_bytes() for path in assets.rglob('*') if path.is_file()}, files_before)
    # Native create undo keeps consumed uploads in its durable cache.
    with request_context(RequestContext(store, 'admin', project)):
        api.auth.bind_security('admin', token)
        cached = list((Path(Environment.get_tmp_dir()) / 'undo').rglob('*.txt'))
        check.assertTrue(any(path.read_bytes() == b'second private file' for path in cached if path.is_file()))
    upload_file(b'second private file')
    second = checkin()
    check.assertEqual(second['version'], 2)
    check.assertEqual(first_path.read_bytes(), b'first private file')
    latest = api.dispatch('get_snapshot', (admin, parent['__search_key__'], 'publish'), dict(version=-1, versionless=True))
    check.assertEqual(latest['version'], -1)
    latest_path = lib_path(latest['code'])
    check.assertEqual(latest_path.read_bytes(), b'second private file')
    before = records()
    files_before = {path.relative_to(assets): path.read_bytes() for path in assets.rglob('*') if path.is_file()}
    native_source = store.data_dir / 'native.txt'
    native_source.write_bytes(b'native trusted Python source')
    with request_context(RequestContext(store, 'project_writer', project)):
        api.auth.bind_security('project_writer', user['ticket'])
        from pyasm.command import Command
        with patch.object(FileCheckin, 'call_triggers', fail), check.assertRaisesRegex(ValueError, 'late file check-in failure'):
            Command.execute_cmd(FileCheckin(Search.get_by_search_key(parent['__search_key__']),
                [str(native_source)], context='native', mode='copy', checkin_type='strict'))
    check.assertEqual(records(), before)
    check.assertEqual({path.relative_to(assets): path.read_bytes() for path in assets.rglob('*') if path.is_file()}, files_before)
    check.assertEqual(native_source.read_bytes(), b'native trusted Python source')
    from io import BytesIO
    from PIL import Image
    api.dispatch('insert', (admin, 'config/naming', dict(search_type=project + '/asset', context='preview',
        checkin_type='auto', file_naming='{basefile}_{file_type}_v{version}.{ext}',
        dir_naming='{project.code}/{search_type.table_name}/{code}/{snapshot.process}/versions')))
    image = BytesIO()
    Image.new('RGB', (31, 17), (20, 40, 60)).save(image, format='PNG')
    api.dispatch('upload_file', (user, 'preview.png', Binary(image.getvalue())))
    if client is not None:
        preview = client.simple_checkin(parent['__search_key__'], 'preview', 'preview.png')
    else:
        preview = api.dispatch('simple_checkin', (user, parent['__search_key__'], 'preview', 'preview.png'), {'checkin_type': ''})
    with request_context(RequestContext(store, 'admin', project)):
        api.auth.bind_security('admin', token)
        snapshot = Search.get_by_code('sthpw/snapshot', preview['code'])
        check.assertEqual(set(snapshot.get_all_file_types()), {'main', 'web', 'icon'})
        check.assertTrue(all(Path(path).is_file() for path in snapshot.get_all_lib_paths()))
    if groups:
        if client is not None:
            with request_context(RequestContext(store, 'project_writer', project)):
                api.auth.bind_security('project_writer', user['ticket'])
                handoff = Path(Environment.get_server_handoff_dir())
                handoff.mkdir(parents=True, exist_ok=True)
        def call(method, *args, **kwargs):
            if client is not None:
                # The SDK's upload mode uploads local files; these are already ticket uploads.
                if kwargs.get('mode') == 'upload':
                    kwargs['mode'] = None
                return getattr(client, method)(*args, **kwargs)
            return api.dispatch(method, (user, *args), kwargs)
        def frames(name, values=(1, 2, 3)):
            for frame in values:
                api.dispatch('upload_file', (user, '%s.%04d.txt' % (name, frame), Binary(('%s %s' % (name, frame)).encode())))
                if client is not None and name in ('group_checkin', 'missing'):
                    # Original SDK manual group mode reads the ticket's handoff directory.
                    (handoff / ('%s.%04d.txt' % (name, frame))).write_bytes(('%s %s' % (name, frame)).encode())
        def files(code):
            with request_context(RequestContext(store, 'admin', project)):
                api.auth.bind_security('admin', token)
                obj = Search.get_by_code('sthpw/snapshot', code)
                return {kind: [Path(path).read_bytes() for path in obj.get_paths_by_type(kind)]
                        for kind in obj.get_all_file_types()}
        for options in (dict(project_access='deny'), dict(parent_access='view'), dict(snapshot_access='view'), dict(file_access='view'),
                        dict(extra='<rule group="sobject_column" search_type="sthpw/file" column="file_name" project="%s" access="deny"/>' % project)):
            permissions()
            api.dispatch('upload_file', (user, 'denied.txt', Binary(b'denied append')))
            permissions(**options)
            before = records()
            files_before = {path.relative_to(assets): path.read_bytes() for path in assets.rglob('*') if path.is_file()}
            with check.assertRaises(denied):
                call('add_file', second['code'], 'denied.txt', 'extra', mode='upload')
            check.assertEqual(records(), before)
            check.assertEqual({path.relative_to(assets): path.read_bytes() for path in assets.rglob('*') if path.is_file()}, files_before)
        permissions()
        before = records()
        with check.assertRaises(ValueError if client is None else Fault):
            call('group_checkin', parent['__search_key__'], 'escape', [str(first_path.parent / 'escape.####.txt')], '1-3', mode='upload')
        check.assertEqual(records(), before)
        # Append two files through the original array form; the second fails late.
        for filename in ('append.txt', 'late.txt'):
            api.dispatch('upload_file', (user, filename, Binary(filename.encode())))
        before = records()
        files_before = {path.relative_to(assets): path.read_bytes() for path in assets.rglob('*') if path.is_file()}
        from pyasm.checkin import FileAppendCheckin, FileGroupCheckin, FileGroupAppendCheckin
        append_trigger = FileAppendCheckin.call_triggers
        def second_failure(self):
            append_trigger(self)
            if self.file_types[0] == 'late':
                raise ValueError('second append failure')
        with patch.object(FileAppendCheckin, 'call_triggers', second_failure):
            with check.assertRaises(ValueError if client is None else Fault):
                call('add_file', second['code'], ['append.txt', 'late.txt'], ['extra', 'late'], mode='upload')
        check.assertEqual(records(), before)
        check.assertEqual({path.relative_to(assets): path.read_bytes() for path in assets.rglob('*') if path.is_file()}, files_before)
        api.dispatch('upload_file', (user, 'append.txt', Binary(b'appended file')))
        added = call('add_file', second['code'], 'append.txt', 'extra', mode='upload')
        check.assertEqual(added['code'], second['code'])
        check.assertEqual(files(second['code'])['extra'], [b'appended file'])
        for method in ('group_checkin', 'add_group'):
            frames(method)
            args = ((parent['__search_key__'], 'frames', method + '.####.txt', '1-3') if method == 'group_checkin'
                    else (second['code'], method + '.####.txt', 'frames', '1-3'))
            for options in (dict(project_access='deny'), dict(parent_access='view'), dict(snapshot_access='view'), dict(file_access='view'),
                            dict(extra='<rule group="sobject_column" search_type="sthpw/file" column="file_range" project="%s" access="deny"/>' % project)):
                permissions(**options)
                before = records()
                files_before = {path.relative_to(assets): path.read_bytes() for path in assets.rglob('*') if path.is_file()}
                with check.assertRaises(denied):
                    call(method, *args, mode='upload')
                check.assertEqual(records(), before)
                check.assertEqual({path.relative_to(assets): path.read_bytes() for path in assets.rglob('*') if path.is_file()}, files_before)
            permissions()
            before = records()
            files_before = {path.relative_to(assets): path.read_bytes() for path in assets.rglob('*') if path.is_file()}
            cls = FileGroupCheckin if method == 'group_checkin' else FileGroupAppendCheckin
            with patch.object(cls, 'call_triggers', fail):
                with check.assertRaises(ValueError if client is None else Fault):
                    call(method, *args, mode='upload')
            check.assertEqual(records(), before)
            check.assertEqual({path.relative_to(assets): path.read_bytes() for path in assets.rglob('*') if path.is_file()}, files_before)
            frames(method)
            row = call(method, *args, mode='upload')
            check.assertEqual(files(row['code'])['main' if method == 'group_checkin' else 'frames'],
                [('%s %s' % (method, frame)).encode() for frame in (1, 2, 3)])
            alias = api.dispatch('get_snapshot', (admin, parent['__search_key__'], 'frames' if method == 'group_checkin' else 'publish'),
                dict(versionless=True))
            check.assertEqual(alias['version'], -1)
            check.assertEqual(files(alias['code']), files(row['code']))
            if method == 'group_checkin':
                check.assertEqual(row['version'], '1')
            for mode in ('copy', 'move', 'preallocate', 'inplace'):
                with check.assertRaises(SecurityException):
                    api.dispatch(method, (user, *args), {'mode': mode})
        # Missing frames are rejected without consuming the frames that arrived.
        frames('missing', (1, 3))
        before = records()
        from pyasm.biz.file import FileException
        with check.assertRaises(FileException if client is None else Fault):
            call('group_checkin', parent['__search_key__'], 'missing', 'missing.####.txt', '1-3', mode='upload')
        check.assertEqual(records(), before)
        check.assertEqual((upload.parent / 'missing.0001.txt').read_bytes(), b'missing 1')
        stepped = call('group_checkin', parent['__search_key__'], 'frames',
            [str((handoff if client is not None else upload.parent) / 'missing.%04d.txt')], '1-3/2', mode='upload', metadata={'range': 'stepped'})
        check.assertEqual(stepped['version'], '2')
        check.assertEqual(files(stepped['code'])['main'], [b'missing 1', b'missing 3'])
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            check.assertEqual(Search.get_by_code('sthpw/snapshot', stepped['code']).get_metadata(), {'range': 'stepped'})
    if http:
        payload = b'\x00\xff\xfe\x80multipart' * 97
        source = sources / 'Файл 🚀.bin'
        source.write_bytes(payload)
        api.http_upload({'ticket': user['ticket']}, [(source.name, payload[:113])])
        if client is not None:
            client.upload_file(str(source), chunk_size=113, offset=1)
        else:
            for offset in range(113, len(payload), 113):
                api.http_upload({'ticket': user['ticket'], 'action': 'append'}, [(source.name, payload[offset:offset + 113])])
        check.assertEqual((upload.parent / source.name).read_bytes(), payload)
        source = sources / 'empty.bin'
        source.write_bytes(b'')
        if client is not None:
            client.upload_file(str(source))
        else:
            api.http_upload({'ticket': user['ticket']}, [(source.name, b'')])
        check.assertEqual((upload.parent / source.name).read_bytes(), b'')
        source = sources / 'automatic.txt'
        source.write_bytes(b'automatic HTTP check-in')
        if client is not None:
            automatic = client.simple_checkin(parent['__search_key__'], 'http_auto', str(source), create_icon=False, mode='upload')
        else:
            api.http_upload({'ticket': user['ticket']}, [(source.name, source.read_bytes())])
            automatic = api.dispatch('simple_checkin', (user, parent['__search_key__'], 'http_auto', source.name), {'create_icon': False, 'mode': 'upload'})
        check.assertEqual(lib_path(automatic['code']).read_bytes(), source.read_bytes())
        for frame in (1, 2, 3):
            name = 'http.%04d.txt' % frame
            data = ('frame %s' % frame).encode()
            (sources / name).write_bytes(data)
            if client is None:
                api.http_upload({'ticket': user['ticket']}, [(name, data)])
        if client is not None:
            sequence = client.group_checkin(parent['__search_key__'], 'frames', str(sources / 'http.####.txt'), '1-3', mode='upload')
            client.add_group(second['code'], str(sources / 'http.####.txt'), 'frames', '1-3', mode='upload')
        else:
            sequence = api.dispatch('group_checkin', (user, parent['__search_key__'], 'frames', 'http.####.txt', '1-3'), {'mode': 'upload'})
            for frame in (1, 2, 3):
                name = 'http.%04d.txt' % frame
                api.http_upload({'ticket': user['ticket']}, [(name, (sources / name).read_bytes())])
            api.dispatch('add_group', (user, second['code'], 'http.####.txt', 'frames', '1-3'), {'mode': 'upload'})
        extra = sources / 'extra.txt'
        extra.write_bytes(b'HTTP appended file')
        if client is not None:
            client.add_file(second['code'], str(extra), 'extra', mode='upload')
        else:
            api.http_upload({'ticket': user['ticket']}, [(extra.name, extra.read_bytes())])
            api.dispatch('add_file', (user, second['code'], extra.name, 'extra'), {'mode': 'upload'})
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            group = Search.get_by_code('sthpw/snapshot', sequence['code'])
            check.assertEqual([Path(path).read_bytes() for path in group.get_paths_by_type('main')], [b'frame 1', b'frame 2', b'frame 3'])
            appended = Search.get_by_code('sthpw/snapshot', second['code'])
            check.assertEqual([Path(path).read_bytes() for path in appended.get_paths_by_type('frames')], [b'frame 1', b'frame 2', b'frame 3'])
            check.assertEqual(Path(appended.get_lib_path_by_type('extra')).read_bytes(), extra.read_bytes())
    allowed = api.dispatch('create_snapshot', (user, other['__search_key__'], 'publish'))
    check.assertEqual(allowed['search_code'], other['code'])
    check.assertEqual(allowed['login'], 'project_writer')
    for method, args in (('update', (first['__search_key__'], {'search_code': 'OTHER_PARENT'})),):
        with check.assertRaises(SecurityException):
            api.dispatch(method, (user, *args))
    for kwargs in (dict(mode='inplace'), dict(mode='local'), dict(checkin_cls='pyasm.checkin.FileAppendCheckin')):
        with check.assertRaises(denied):
            checkin(**kwargs)
    with request_context(RequestContext(store, 'project_writer', project)):
        api.auth.bind_security('project_writer', user['ticket'])
        with check.assertRaises(SecurityException):
            FileUndo._check_access()
        from pyasm.common import Xml
        from pyasm.search import Transaction
        from pyasm.search.transaction import TransactionException
        transaction = Transaction.get(create=True)
        transaction.start()
        try:
            node = transaction.create_log_node('file')
            for name, value in dict(type='copy', src=str(first_path), dst=str(native_source), state='done').items():
                Xml.set_attribute(node, name, value)
            with check.assertRaisesRegex(TransactionException, 'Rollback cleanup failed'):
                transaction.rollback()
            check.assertEqual(native_source.read_bytes(), b'native trusted Python source')
        finally:
            transaction._reset()
    permissions(project_access='deny')
    with check.assertRaises(SecurityException):
        api.dispatch('upload_file', (user, 'private.txt', Binary(b'denied')))
    if http:
        api.dispatch('update', (admin, 'sthpw/login?code=project_writer', {'s_status': 'retired'}))
        with check.assertRaises(AuthenticationError):
            api.http_upload({'ticket': user['ticket']}, [('private.txt', b'damaged')])
        if client is not None:
            from tactic_client_lib.common import TacticUploadException
            with check.assertRaises(TacticUploadException):
                client.upload_file(str(sources / 'automatic.txt'))
    return dict(versions=[first['version'], second['version']], versionless=True, rollback=True, permissions=True)


class UserCheckin(plugin_tests.PluginInstallation):
    exercise = staticmethod(exercise)


class UserGroupCheckin(plugin_tests.PluginInstallation):
    exercise = staticmethod(lambda store, prefix: exercise(store, prefix, groups=True))


class UserHttpCheckin(plugin_tests.PluginInstallation):
    exercise = staticmethod(lambda store, prefix: exercise(store, prefix, http=True))


class UserCheckinTransport(unittest.TestCase):
    http = False
    def test_original_sdk_upload_versions_and_rollback(self):
        import importlib.util
        import test_transport
        import test_read_parity
        test_transport.Transport.setUpClass()
        client = None
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.file_permissions_client',
                test_read_parity.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            client = module.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            self.assertTrue(exercise(test_transport.Transport.store, 'rpc_files',
                password='private-test-password', client=client, groups=not self.http, http=self.http)['versionless'])
        finally:
            if client is not None:
                client.server.__exit__(None, None, None)
            test_transport.Transport.tearDownClass()


class UserHttpTransport(UserCheckinTransport):
    http = True


if __name__ == '__main__':
    unittest.main()
