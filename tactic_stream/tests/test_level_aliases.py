"""Level aliases retain separate rows, files and transactional rollback."""
from pathlib import Path
import unittest
from unittest.mock import patch
from xmlrpc.client import Binary, Fault

import test_plugin_installation as plugin_tests
import test_user_checkout as checkout_tests
import test_snapshot_levels as level_tests
from test_project_writes import install_writer, PASSWORD
from pyasm.biz import Snapshot
from pyasm.checkin import FileCheckin
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.api import Api


def exercise(store, prefix, password='plugin-test-password', client=None):
    check = unittest.TestCase()
    api = Api(store)
    token = api.get_ticket('admin', password)
    project = prefix + '_ok'
    admin = dict(ticket=token, project=project)
    api.dispatch('execute_cmd', (dict(ticket=token, project='admin'), 'tactic.command.CreateProjectCmd',
        dict(project_code=project, project_title='Private level aliases', project_stype=['asset'])))
    parent = api.dispatch('insert', (admin, project + '/asset', dict(code='LEVEL_PARENT')))
    levels = [None] + [api.dispatch('insert', (admin, project + '/asset', dict(code=code)))['__search_key__']
                       for code in ('LEVEL_A', 'LEVEL_B')]
    for mode in ('versioned', 'latest', 'current'):
        values = dict(search_type=project + '/asset', context='levels', file_naming='{basefile}.{ext}',
            dir_naming='{project.code}/levels/{snapshot.level_id}/' + ('{version}' if mode == 'versioned' else mode))
        if mode != 'versioned':
            values[mode + '_versionless'] = True
        api.dispatch('insert', (admin, 'config/naming', values))
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

    def state():
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            return ({kind: [dict(row.get_data()) for row in Search(kind).get_sobjects()]
                     for kind in ('sthpw/snapshot', 'sthpw/file', 'sthpw/transaction_log', 'sthpw/sobject_log', 'sthpw/change_timestamp')},
                    {path.relative_to(store.data_dir / 'assets'): path.read_bytes()
                     for path in (store.data_dir / 'assets').rglob('*') if path.is_file()})

    def checkin(level, payload, is_current=True, context='levels'):
        call('upload_file', 'level.txt', Binary(payload))
        return call('simple_checkin', parent['__search_key__'], context, 'level.txt',
                    level_key=level, is_current=is_current, create_icon=False)

    def alias(level, version):
        row = call('get_snapshot', parent['__search_key__'], 'levels', version=version,
                   level_key=level, versionless=True, include_files=True)
        paths = call('get_paths', parent['__search_key__'], 'levels', version=version,
                     level_key=level, versionless=True, path_types=['lib'])['lib_paths']
        check.assertEqual(len(paths), 1)
        check.assertEqual(row['version'], int(version))
        check.assertEqual(row['__files__'][0]['snapshot_code'], row['code'])
        return row, Path(paths[0]).read_bytes(), paths[0]

    permissions()
    identities = []
    for index, level in enumerate(levels):
        first = checkin(level, ('level %s version 1' % index).encode())
        second = checkin(level, ('level %s version 2' % index).encode(), is_current=False)
        check.assertEqual((first['version'], second['version']), (1, 2))
        latest = alias(level, '-1')
        current = alias(level, '0')
        check.assertEqual(latest[1], ('level %s version 2' % index).encode())
        check.assertEqual(current[1], ('level %s version 1' % index).encode())
        identities.append((latest[0]['code'], current[0]['code'], latest[2], current[2]))
    check.assertEqual(len({code for pair in identities for code in pair[:2]}), 6)
    check.assertEqual(len({path for pair in identities for path in pair[2:]}), 6)
    for index, level in enumerate(levels):
        check.assertEqual(alias(level, -1)[1], ('level %s version 2' % index).encode())
        check.assertEqual(alias(level, 0)[1], ('level %s version 1' % index).encode())
    with request_context(RequestContext(store, 'admin', project)):
        api.auth.bind_security('admin', token)
        no_level = Snapshot.get_versionless(project + '/asset', parent['code'], 'levels', mode='latest', create=False)
        check.assertEqual(no_level.get_code(), identities[0][0])

    denied = SecurityException if client is None else Fault
    for options in (dict(parent_access='view'), dict(snapshot_access='view'), dict(file_access='view'),
                    dict(extra='<rule group="sobject_column" search_type="sthpw/snapshot" project="%s" column="level_id" access="deny"/>' % project)):
        permissions(**options)
        call('upload_file', 'level.txt', Binary(b'denied level refresh'))
        before = state()
        with check.assertRaises(denied):
            call('simple_checkin', parent['__search_key__'], 'levels', 'level.txt', level_key=levels[1], create_icon=False)
        check.assertEqual(state(), before)
    permissions()
    call('upload_file', 'level.txt', Binary(b'late level refresh'))
    before = state()
    original = FileCheckin.call_triggers
    def fail(command):
        original(command)
        raise ValueError('late level alias failure')
    with patch.object(FileCheckin, 'call_triggers', fail), check.assertRaises(ValueError if client is None else Fault):
        call('simple_checkin', parent['__search_key__'], 'levels', 'level.txt', level_key=levels[1], create_icon=False)
    check.assertEqual(state(), before)
    checkin(levels[1], b'level 1 version 3')
    check.assertEqual(alias(levels[1], -1)[0]['code'], identities[1][0])
    check.assertEqual(alias(levels[1], 0)[0]['code'], identities[1][1])
    check.assertEqual(alias(levels[1], -1)[1], b'level 1 version 3')
    check.assertEqual(alias(levels[2], -1)[1], b'level 2 version 2')
    for mode in ('versioned', 'latest', 'current'):
        values = dict(search_type=project + '/asset', context='collision', file_naming='{basefile}.{ext}',
            dir_naming='{project.code}/collision/' + ('{snapshot.level_id}/{version}' if mode == 'versioned' else mode))
        if mode != 'versioned':
            values[mode + '_versionless'] = True
        api.dispatch('insert', (admin, 'config/naming', values))
    checkin(levels[1], b'protected alias', context='collision')
    with request_context(RequestContext(store, 'admin', project)):
        api.auth.bind_security('admin', token)
        check.assertIsNone(Snapshot.get_versionless(project + '/asset', parent['code'],
            'collision', mode='latest', create=False))
    call('upload_file', 'level.txt', Binary(b'colliding alias'))
    before = state()
    with check.assertRaisesRegex(ValueError if client is None else Fault,
                                'outside this alias' if client is None else 'Fault 400'):
        call('simple_checkin', parent['__search_key__'], 'collision', 'level.txt',
             level_key=levels[2], create_icon=False)
    check.assertEqual(state(), before)
    return dict(rollback=True)


class LevelAliases(plugin_tests.PluginInstallation):
    exercise = staticmethod(exercise)


class LevelAliasesTransport(checkout_tests.UserCheckoutTransport):
    exercise = staticmethod(exercise)


class LevelAliasesParity(level_tests.SnapshotLevelsParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='snapshot_levels_contract', project='one', name='level_aliases', level_aliases=True)]

    def assert_case_result(self, case, result, original):
        self.assertEqual(result, dict(alias_count=6, rows=[[version, index > 0, 'level ' + str(index)]
            for index in range(3) for version in (-1, 0)]))
        # Source shares aliases and returns the same final versioned snapshot for every level.
        self.assertEqual(original, dict(alias_count=1, rows=[[3, False, 'level 2']] * 6))
