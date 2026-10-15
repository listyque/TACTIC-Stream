"""Ordinary-user checkout paths, original SDK IO and transactional callbacks."""
from pathlib import Path
import unittest
from unittest.mock import patch
from xmlrpc.client import Binary, Fault

import test_plugin_installation as plugin_tests
from test_project_writes import install_writer, PASSWORD
from pyasm.biz import Snapshot, Project
from pyasm.command import Trigger, Command
from pyasm.common import Environment, Config
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context, _context
from tactic_stream.server.api import Api


class CheckoutProbe(Trigger):
    events = []
    fail = False

    def execute(self):
        self.events.append((self.get_event(), Environment.get_user_name(), Project.get_project_code()))
        parent = Search.get_by_code('sthpw/snapshot', self.get_input()['snapshot']['code']).get_sobject()
        parent.set_value('description', self.get_event() + (' failure' if self.fail else ''))
        parent.commit()
        if self.fail and self.get_event().startswith('checkout|'):
            raise ValueError('late checkout callback failure')


def exercise(store, prefix, password='plugin-test-password', client=None, cross_project=False, groups=False):
    get_dict_value = Config.get_dict_value
    def config(section, key, *args, **kwargs):
        if section == 'checkin' and key.endswith('_sandbox_dir'):
            return {'default': (store.data_dir / 'checkout_sandbox').as_posix()}
        return get_dict_value(section, key, *args, **kwargs)
    with patch.object(Config, 'get_dict_value', config):
        return checkout_contract(store, prefix, password, client, cross_project, groups)


def checkout_contract(store, prefix, password, client, cross_project, groups):
    check = unittest.TestCase()
    api = Api(store)
    token = api.get_ticket('admin', password)
    project = prefix + '_ok'
    admin = dict(ticket=token, project=project)
    api.dispatch('execute_cmd', (dict(ticket=token, project='admin'), 'tactic.command.CreateProjectCmd',
        dict(project_code=project, project_title='Private checkout', project_stype=['asset'])))
    caller_project = prefix + '_copy' if cross_project else project
    if cross_project:
        caller = dict(ticket=token, project='admin')
        api.dispatch('execute_cmd', (caller, 'tactic.command.CreateProjectCmd',
            dict(project_code=caller_project, project_title='Private checkout caller', project_stype=['asset'])))
        caller['project'] = caller_project
        api.dispatch('insert', (caller, 'config/custom_script', dict(folder='checkout', title='wrong', language='python',
            script="raise ValueError('Caller-project checkout trigger must not run')")))
        api.dispatch('insert', (caller, 'config/trigger', dict(event='checkout', class_name='', script_path='checkout/wrong',
            mode='same process,same transaction')))
    parent = api.dispatch('insert', (admin, project + '/asset', dict(code='CHECKOUT_PARENT', description='original')))
    level = api.dispatch('insert', (admin, project + '/asset', dict(code='CHECKOUT_LEVEL')))
    key = parent['__search_key__']
    install_writer(store)
    user = dict(ticket=api.get_ticket('project_writer', PASSWORD), project=caller_project)
    if client is not None:
        client.set_ticket(user['ticket']); client.set_project(caller_project)

    def permissions(project_access='allow', parent_access='view', snapshot_access='view', file_access='view', extra='', level_access='allow'):
        xml = ('<rules><rule group="project" code="%s" access="%s"/>'
               '<rule group="search_type" code="%s/asset" project="%s" access="%s"/>'
               '<rule group="search_type" code="sthpw/snapshot" access="%s"/>'
               '<rule group="search_type" code="sthpw/file" access="%s"/>%s</rules>') % \
            (project, project_access, project, project, parent_access, snapshot_access, file_access, extra)
        if cross_project:
            xml = xml.replace('<rules>', '<rules><rule group="project" code="%s" access="allow"/>' % caller_project, 1)
            xml = xml.replace('</rules>', '<rule group="project" code="%s" access="%s"/>'
                '<rule group="search_type" code="%s/asset" project="%s" access="view"/></rules>' %
                (level_project, level_access, level_project, level_project))
        api.dispatch('update', (admin, 'sthpw/login_group?code=project_writers', {'access_rules': xml}))

    def checkout(version=-1, file_type='main', context='publish', search_key=key, level_key=None):
        if client is not None:
            return client.server.checkout(client.ticket, search_key, context, version, file_type, level_key)
        return api.dispatch('checkout', (user, search_key, context, version, file_type, level_key))

    def state():
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            return {kind: [dict(row.get_data()) for row in Search(kind).get_sobjects()]
                    for kind in (project + '/asset', 'sthpw/snapshot', 'sthpw/file', 'sthpw/sobject_log',
                                 'sthpw/transaction_log', 'sthpw/change_timestamp')}

    for latest in (False, True):
        api.dispatch('insert', (admin, 'config/naming', dict(search_type=project + '/asset', context='publish',
            latest_versionless=latest, file_naming='{basefile}_{file_type}' + ('' if latest else '_v{version}') + '.{ext}',
            dir_naming='{project.code}/{search_type.table_name}/{code}/{snapshot.process}/' + ('latest' if latest else 'versions'))))
    snapshots = []
    for contents in (b'first checkout file', b'second checkout file'):
        api.dispatch('upload_file', (admin, 'private.txt', Binary(contents)))
        snapshots.append(api.dispatch('simple_checkin', (admin, key, 'publish', 'private.txt'), {'create_icon': False}))
    api.dispatch('upload_file', (admin, 'extra.txt', Binary(b'extra checkout file')))
    api.dispatch('add_file', (admin, snapshots[-1]['code'], 'extra.txt', 'extra'), {'mode': 'uploaded'})
    api.dispatch('insert', (admin, 'config/naming', dict(search_type=project + '/asset', context='level',
        file_naming='{basefile}.{ext}', dir_naming='{project.code}/levels/{snapshot.level_id}/{context}/{version}')))
    api.dispatch('upload_file', (admin, 'level.txt', Binary(b'level checkout file')))
    api.dispatch('simple_checkin', (admin, key, 'level', 'level.txt'),
        {'create_icon': False, 'level_key': level['__search_key__']})
    if cross_project:
        level_project = prefix + '_tpl'
        api.dispatch('execute_cmd', (dict(ticket=token, project='admin'), 'tactic.command.CreateProjectCmd',
            dict(project_code=level_project, project_title='Private checkout level', project_stype=['asset'])))
        foreign_level = api.dispatch('insert', (dict(ticket=token, project=level_project), level_project + '/asset', dict(code='FOREIGN_LEVEL')))
        api.dispatch('upload_file', (admin, 'foreign-level.txt', Binary(b'foreign level checkout file')))
        api.dispatch('simple_checkin', (admin, key, 'foreign_level', 'foreign-level.txt'),
            {'create_icon': False, 'level_key': foreign_level['__search_key__']})
    sequences = []
    if groups:
        for context, marker in (('hash_frames', '####'), ('printf_frames', '%04d')):
            for latest in (False, True):
                api.dispatch('insert', (admin, 'config/naming', dict(search_type=project + '/asset', context=context,
                    latest_versionless=latest, file_naming='{basefile}.{ext}',
                    dir_naming='{project.code}/sequences/{snapshot.context}/' + ('latest' if latest else '{version}'))))
            for version in (1, 2):
                for frame in (1, 3, 5):
                    api.dispatch('upload_file', (admin, 'frames.%04d.txt' % frame,
                        Binary(('frame %s version %s' % (frame, version)).encode())))
                sequence = api.dispatch('group_checkin', (admin, key, context, 'frames.' + marker + '.txt', '1-5/2'),
                    dict(mode='upload'))
                check.assertEqual(int(sequence['version']), version)
            for frame in (-2, 0, 2):
                api.dispatch('upload_file', (admin, 'extra.%0.4d.txt' % frame, Binary(('extra frame %s' % frame).encode())))
            api.dispatch('add_group', (admin, sequence['code'], 'extra.%0.4d.txt', 'extra', '-2-2/2'),
                dict(mode='upload'))
            api.dispatch('upload_file', (admin, 'sequence-note.txt', Binary(b'sequence static file')))
            api.dispatch('add_file', (admin, sequence['code'], 'sequence-note.txt', 'note'), {'mode': 'uploaded'})
            sequences.append((context, sequence))
    permissions()
    CheckoutProbe.events = []
    before = state()
    for version, contents in ((1, b'first checkout file'), (2, b'second checkout file'), (-1, b'second checkout file'), (None, b'second checkout file')):
        paths = checkout(version)
        check.assertEqual(set(paths), {'client_lib_paths', 'sandbox_paths', 'web_paths'})
        check.assertTrue(all(len(value) == 1 for value in paths.values()))
        check.assertEqual(Path(paths['client_lib_paths'][0]).read_bytes(), contents)
    paths = checkout(2, '*', search_key=[key])
    check.assertTrue(all(len(value) == 2 for value in paths.values()))
    check.assertEqual({Path(path).read_bytes() for path in paths['client_lib_paths']}, {b'second checkout file', b'extra checkout file'})
    level_paths = checkout(1, context='level', level_key=level['__search_key__'])
    check.assertEqual(Path(level_paths['client_lib_paths'][0]).read_bytes(), b'level checkout file')
    check.assertEqual(state(), before)
    if cross_project:
        foreign_paths = checkout(1, context='foreign_level', level_key=foreign_level['__search_key__'])
        check.assertEqual(Path(foreign_paths['client_lib_paths'][0]).read_bytes(), b'foreign level checkout file')
        for options in (dict(level_access='deny'), dict(extra='<rule group="sobject_column" project="%s" search_type="%s/asset" column="description" access="deny"/>' % (level_project, level_project)),
                dict(extra='<rule group="sobject" project="%s" search_type="%s/asset" code="FOREIGN_LEVEL" access="deny"/>' % (level_project, level_project))):
            permissions(**options)
            before = state()
            with check.assertRaises(SecurityException if client is None else Fault):
                checkout(1, context='foreign_level', level_key=foreign_level['__search_key__'])
            check.assertEqual(state(), before)
        permissions()
        before = state()
    if client is not None:
        for mode in ('copy', 'download'):
            target = store.data_dir / ('checkout_' + mode)
            target.mkdir(parents=True)
            copied = client.checkout(key, version=2, file_type='*', to_dir=str(target), mode=mode)
            check.assertEqual({Path(path).read_bytes() for path in copied}, {b'second checkout file', b'extra checkout file'})
        copied = client.checkout(key, version=2, to_dir=str(target), to_sandbox_dir=True)
        check.assertEqual(Path(copied[0]).read_bytes(), b'second checkout file')
        check.assertTrue(Path(copied[0]).is_relative_to(store.data_dir / 'checkout_sandbox'))
        check.assertEqual(state(), before)

    if groups:
        for context, sequence in sequences:
            for version, count in ((1, 3), (2, 3), (-1, 3), (None, 3)):
                sequence_paths = checkout(version, context=context)
                check.assertTrue(all(len(value) == count for value in sequence_paths.values()))
                check.assertEqual([Path(path).read_bytes() for path in sequence_paths['client_lib_paths']],
                    [('frame %s version %s' % (frame, 1 if version == 1 else 2)).encode() for frame in (1, 3, 5)])
                check.assertEqual([Path(path).name for path in sequence_paths['client_lib_paths']],
                    [Path(path).name for path in sequence_paths['sandbox_paths']])
                check.assertEqual([Path(path).name for path in sequence_paths['client_lib_paths']],
                    [Path(path).name for path in sequence_paths['web_paths']])
            selected = checkout(2, 'extra', context=context)
            check.assertEqual([Path(path).read_bytes() for path in selected['client_lib_paths']],
                [('extra frame %s' % frame).encode() for frame in (-2, 0, 2)])
            mixed = checkout(2, '*', context=context)
            check.assertTrue(all(len(value) == 7 for value in mixed.values()))
            check.assertEqual([Path(path).read_bytes() for path in mixed['client_lib_paths']],
                [('frame %s version 2' % frame).encode() for frame in (1, 3, 5)] +
                [('extra frame %s' % frame).encode() for frame in (-2, 0, 2)] + [b'sequence static file'])
            check.assertEqual(state(), before)
            if client is not None:
                for mode in ('copy', 'download'):
                    target = store.data_dir / (context + '_' + mode)
                    target.mkdir()
                    copied = client.checkout(key, context=context, version=2, file_type='*', to_dir=str(target), mode=mode)
                    check.assertEqual([Path(path).read_bytes() for path in copied],
                        [Path(path).read_bytes() for path in mixed['client_lib_paths']])
                copied = client.checkout(key, context=context, version=2, to_dir=str(target), to_sandbox_dir=True)
                check.assertEqual([Path(path).read_bytes() for path in copied],
                    [('frame %s version 2' % frame).encode() for frame in (1, 3, 5)])
                check.assertTrue(all(Path(path).is_relative_to(store.data_dir / 'checkout_sandbox') for path in copied))
            for options in (dict(file_access='deny'), dict(extra='<rule group="sobject_column" project="%s" search_type="sthpw/file" column="file_range" access="deny"/>' % project)):
                permissions(**options)
                denied_before = state()
                with check.assertRaises(SecurityException if client is None else Fault):
                    checkout(2, '*', context=context)
                check.assertEqual(state(), denied_before)
            permissions()
            selected_file = api.dispatch('get_snapshot', (admin, key, context, 2), {'include_files': True})['__files__'][0]
            file_key = selected_file['__search_key__']
            api.dispatch('update', (admin, file_key, {'file_range': '5-1'}))
            corrupt_before = state()
            from pyasm.biz.file import FileException
            try:
                with check.assertRaises(FileException if client is None else Fault):
                    checkout(2, '*', context=context)
                check.assertEqual(state(), corrupt_before)
                check.assertEqual(CheckoutProbe.events, [])
            finally:
                api.dispatch('update', (admin, file_key, {'file_range': selected_file['file_range']}))
            before = state()

    denied = SecurityException if client is None else Fault
    for rules in (dict(project_access='deny'), dict(snapshot_access='deny'), dict(file_access='deny'),
            dict(extra='<rule group="sobject" project="%s" search_type="%s/asset" code="CHECKOUT_PARENT" access="deny"/>' % (project, project)),
            dict(extra='<rule group="sobject" project="%s" search_type="sthpw/snapshot" code="%s" access="deny"/>' % (project, snapshots[-1]['code'])),
            *(dict(extra='<rule group="sobject_column" project="%s" search_type="%s" column="%s" access="deny"/>' % (project, kind, column))
              for kind, column in ((project + '/asset', 'description'), ('sthpw/file', 'relative_dir'), ('sthpw/snapshot', 'snapshot')))):
        permissions(**rules)
        before = state()
        with check.assertRaises(denied) as caught:
            checkout(2)
        if client is not None:
            check.assertEqual(caught.exception.faultCode, 403)
        check.assertEqual(state(), before)
    permissions(extra='<rule group="api_method" key="checkout" access="deny"/>')
    get_value = Config.get_value
    with patch.object(Config, 'get_value', side_effect=lambda section, name, *args, **kwargs:
            'true' if (section, name) == ('security', 'api_method_restricted') else get_value(section, name, *args, **kwargs)):
        with check.assertRaises(denied):
            checkout(2)
    permissions()
    before = state()
    check.assertEqual(api.dispatch('checkout', (dict(user, project='admin'), key, 'publish', 2))['client_lib_paths'], paths['client_lib_paths'][:1])
    check.assertEqual(state(), before)
    permissions(extra='<rule group="sobject" project="%s" search_type="%s/asset" code="CHECKOUT_LEVEL" access="deny"/>' % (project, project))
    before = state()
    with check.assertRaises(denied):
        checkout(1, context='level', level_key=level['__search_key__'])
    check.assertEqual(state(), before)
    permissions()
    from pyasm.web.api_xmlrpc import ApiException
    invalid = ApiException if client is None else Fault
    for arguments in (dict(version=99), dict(file_type='missing'), dict(context='missing')):
        with check.assertRaises(invalid):
            checkout(**arguments)
    api.dispatch('lock_sobject', (admin, key, 'publish'))
    with check.assertRaises(invalid) as caught:
        checkout(2)
    if client is None:
        check.assertIn('locked', str(caught.exception))
    api.dispatch('unlock_sobject', (admin, key, 'publish'))
    snapshot_key = snapshots[-1]['__search_key__']
    original_xml = api.dispatch('get_by_code', (admin, 'sthpw/snapshot', snapshots[-1]['code']))['snapshot']
    api.dispatch('update', (admin, snapshot_key, {'snapshot': '<snapshot><file file_code="MISSING" type="main" name="missing.txt"/></snapshot>'}))
    before = state()
    try:
        with check.assertRaises(denied):
            checkout(2)
        check.assertEqual(state(), before)
    finally:
        api.dispatch('update', (admin, snapshot_key, {'snapshot': original_xml}))
    for event in ('checkout', 'checkout|' + project + '/asset'):
        api.dispatch('insert', (admin, 'config/trigger', dict(event=event, class_name='test_user_checkout.CheckoutProbe',
            mode='same process,same transaction')))
    before = state()
    with check.assertRaises(denied):
        checkout(2)
    check.assertEqual(state(), before)
    check.assertEqual(CheckoutProbe.events, [('checkout', 'project_writer', project)])
    permissions(parent_access='allow')
    CheckoutProbe.events = []
    checkout(2)
    check.assertEqual(CheckoutProbe.events, [('checkout', 'project_writer', project), ('checkout|' + project + '/asset', 'project_writer', project)])
    check.assertEqual(api.dispatch('get_by_code', (admin, project + '/asset', parent['code']))['description'], 'checkout|' + project + '/asset')
    before = state()
    original_files = {path: Path(path).read_bytes() for path in paths['client_lib_paths']}
    CheckoutProbe.fail = True
    try:
        with check.assertRaises(ValueError if client is None else Fault) as caught:
            checkout(2)
        if client is None:
            check.assertIn('late checkout callback failure', str(caught.exception))
        else:
            check.assertEqual(caught.exception.faultCode, 400)
    finally:
        CheckoutProbe.fail = False
    check.assertEqual(state(), before)
    check.assertEqual({path: Path(path).read_bytes() for path in original_files}, original_files)
    api.dispatch('insert', (admin, 'config/custom_script', dict(folder='checkout', title='user', language='python',
        script="server.update(%r, {'name': 'Python checkout · ' + server.login})\nreturn server.login" % key)))
    api.dispatch('insert', (admin, 'config/trigger', dict(event='checkout', class_name='', script_path='checkout/user',
        mode='same process,same transaction')))
    CheckoutProbe.events = []
    before = state()
    with check.assertRaises(denied):
        checkout(2)
    check.assertEqual(CheckoutProbe.events, [])
    check.assertEqual(state(), before)
    if cross_project:
        permissions(parent_access='allow', extra='<rule group="api_cmd" key="tactic.command.PythonCmd" project="%s" access="allow"/>' % caller_project)
        before = state()
        with check.assertRaises(denied):
            checkout(2)
        check.assertEqual(CheckoutProbe.events, [])
        check.assertEqual(state(), before)
    permissions(parent_access='allow', extra='<rule group="api_cmd" key="tactic.command.PythonCmd" project="%s" access="allow"/>' % project)
    checkout(2)
    check.assertEqual(api.dispatch('get_by_code', (admin, project + '/asset', parent['code']))['name'], 'Python checkout · project_writer')
    if groups:
        CheckoutProbe.events = []
        group_paths = checkout(2, '*', context=sequences[0][0])
        check.assertEqual(len(group_paths['client_lib_paths']), 7)
        check.assertEqual(CheckoutProbe.events, [('checkout', 'project_writer', project), ('checkout|' + project + '/asset', 'project_writer', project)])
        before = state()
        sequence_bytes = {path: Path(path).read_bytes() for path in group_paths['client_lib_paths']}
        CheckoutProbe.fail = True
        try:
            with check.assertRaises(ValueError if client is None else Fault):
                checkout(2, '*', context=sequences[0][0])
        finally:
            CheckoutProbe.fail = False
        check.assertEqual(state(), before)
        check.assertEqual({path: Path(path).read_bytes() for path in sequence_bytes}, sequence_bytes)
    if cross_project:
        from pyasm.search.transaction import Transaction
        from pyasm.common import Container
        def nested(fail):
            with request_context(RequestContext(store, 'project_writer', caller_project)):
                api.auth.bind_security('project_writer', user['ticket'])
                command = Command(log_exception=False)
                command.get_transaction().set_sync(False)
                def run():
                    original_context, original_transaction = _context.get(), Transaction.get()
                    try:
                        return api.checkout(user, key, 'publish', 2)
                    finally:
                        check.assertIs(_context.get(), original_context)
                        check.assertIs(Transaction.get(), original_transaction)
                        check.assertIs(Container.get_seq('Command:executing')[-1], command)
                command.execute = run
                CheckoutProbe.fail = fail
                try:
                    return Command.execute_cmd(command)
                finally:
                    CheckoutProbe.fail = False
        nested(False)
        before = state()
        with check.assertRaisesRegex(ValueError, 'late checkout callback failure'):
            nested(True)
        check.assertEqual(state(), before)
    return dict(read=True, versions=True, permissions=True, callbacks=True, rollback=True)


class UserCheckout(plugin_tests.PluginInstallation):
    exercise = staticmethod(exercise)


class UserCheckoutTransport(unittest.TestCase):
    exercise = staticmethod(exercise)
    def test_original_sdk_checkout(self):
        import importlib.util
        import test_transport
        import test_read_parity
        test_transport.Transport.setUpClass()
        client = None
        try:
            spec = importlib.util.spec_from_file_location('tactic_client_lib.checkout_permissions_client',
                test_read_parity.LEGACY / 'src/client/tactic_client_lib/tactic_server_stub.py')
            module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            client = module.TacticServerStub(setup=False, protocol='xmlrpc')
            client.set_server(test_transport.Transport.url)
            self.assertTrue(self.exercise(test_transport.Transport.store, 'rpc_checkout',
                password='private-test-password', client=client)['rollback'])
        finally:
            if client is not None:
                client.server.__exit__(None, None, None)
            test_transport.Transport.tearDownClass()
