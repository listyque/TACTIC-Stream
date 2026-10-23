"""Database event matching and handler execution against the original kernel."""
import ast
import copy
from contextlib import redirect_stderr, redirect_stdout
import inspect
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

import test_read_parity as read_tests
from tools.capture_legacy import trigger_schema
from tools.trigger_probe import Definition, run_trigger_case
from pyasm.command.command import Command, HandlerCmd
from pyasm.biz.command_trigger import TriggerSObj
from pyasm.common.common import Common, Container
from pyasm.common.errors import UnsupportedContract
from pyasm.biz.notification import Notification
from pyasm.search.search import RequestContext, Search, SObject, request_context
from pyasm.security.authenticator import hash_password
from pyasm.search.storage import Store
from pyasm.command.trigger import Trigger


def trigger_fixture(store):
    rows = [('A_GLOBAL', None, '', ''), ('B_ONE', 'one', '', ''), ('C_TWO', 'two', '', ''),
            ('D_MULTI', '||one||two||', '', ''), ('E_EMPTY', '', '', ''),
            ('F_PROCESS', 'one', 'model', ''), ('G_TYPE', 'one', '', 'contract/entity'),
            ('H_BOTH', 'one', 'model', 'contract/entity'), ('Z_RETIRED', 'one', '', '')]
    with store.connection(write=True) as db:
        for field in ('search_type', 'data', 'listen_process'):
            db.execute('ALTER TABLE "trigger" ADD COLUMN "' + field + '" text')
        db.execute("INSERT OR IGNORE INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('config/trigger','config/trigger','config','{project}','spt_trigger','pyasm.biz.TriggerSObj')")
        for code, project, process, search_type in rows:
            db.execute('INSERT INTO "trigger" (code,event,project_code,process,search_type,class_name,data,s_status) VALUES (?,?,?,?,?,?,?,?)',
                       (code, 'changed', project, process, search_type, 'tactic_stream_trigger_probe.RecordedTrigger', '{}',
                        'retired' if code == 'Z_RETIRED' else None))
        for code, project, process, search_type in rows:
            db.execute('INSERT INTO notification (code,event,project_code,process,search_type,type,s_status) VALUES (?,?,?,?,?,?,?)',
                       ('N_' + code, 'notice', project, process, search_type, 'email',
                        'retired' if code == 'Z_RETIRED' else None))
    for project in ('one', 'two'):
        with store.connection(project, write=True) as db:
            db.execute('CREATE TABLE IF NOT EXISTS spt_trigger (id integer PRIMARY KEY, code text, event text, process text, search_type text, class_name text, script_path text, mode text, data text, description text, listen_process text, s_status text)')
            db.execute('INSERT INTO spt_trigger (code,event,class_name,data) VALUES (?,?,?,?)',
                       ('P_' + project, 'changed', 'tactic_stream_trigger_probe.RecordedTrigger', '{}'))


def trigger_cases():
    cases = []
    def add(name, **options):
        cases.append({'name': name, 'method': 'trigger_dispatch', **options})
    for project in ('one', 'two', 'admin', 'sthpw'):
        add('db_' + project, project=project, operation='get_db_triggers')
        for process in (None, 'model', 'missing'):
            add('event_' + project + str(process), project=project, operation='get_by_event', args=['changed', process])
            add('notification_' + project + str(process), project=project,
                operation='get_notifications_by_event', args=['notice', process])
        add('notifications_all_' + project, project=project, operation='get_notifications_by_event')
        for process in (None, 'model'):
            for search_type in (None, 'contract/entity'):
                for integral in (False, True):
                    key = {'event': 'changed'}
                    if process: key['process'] = process
                    if search_type: key['search_type'] = search_type
                    add('key_' + project + str(key) + str(integral), project=project,
                        operation='_get_triggers', args=[key, integral])
        for notice in ({'event': 'notice'}, {'event': 'notice', 'process': 'model'},
                       {'event': 'notice', 'search_type': 'contract/entity'}):
            add('notice_key_' + project + str(notice), project=project, operation='_get_triggers', args=[notice])
        for process in (None, 'model'):
            for search_type in (None, 'contract/entity'):
                add('database_call_' + project + str(process) + str(search_type), project=project,
                    event='changed', command=True, kwargs={'process': process, 'search_type': search_type})
    definitions = [{'code': 'STATIC', 'event': 'changed'}, {'code': 'INTEGRAL', 'event': 'changed', 'integral': True},
                   {'code': 'STARTUP', 'event': 'changed', 'startup': True}]
    add('static_integral_order', operation='_get_triggers', args=[{'event': 'changed'}], definitions=definitions)
    add('integral_only', operation='_get_triggers', args=[{'event': 'changed'}, True], definitions=definitions)
    add('static_renew', operation='_get_triggers', args=[{'event': 'changed'}], definitions=definitions,
        cache_steps=[['append_static', {'code': 'ADDED', 'event': 'changed'}],
                     ['_get_triggers', {'event': 'changed'}], ['clear_db_cache'], ['_get_triggers', {'event': 'changed'}]])
    add('no_call_match', event='missing')
    add('no_key_match', operation='call_by_key', key={'event': 'missing'})
    add('exact_key_order', operation='_get_triggers', args=[{'process': 'model', 'event': 'changed'}])
    for output in ({}, None, {'value': 0}, [], False):
        add('output_' + repr(output), operation='handle', output=output,
            handlers=[{'code': 'direct', 'mode': 'same process,same transaction', 'data': {'result': False}}])
    for mode in ('same process,same transaction', 'same process,new transaction', ''):
        for command in (False, True):
            add('dispatch_' + mode + str(command), event='dispatch', command=command, flush=True, output={'value': 1},
                definitions=[{'code': 'class', 'event': 'dispatch', 'mode': mode, 'description': 'description',
                              'data': {'result': {'value': 2}}}])
    add('forced_mode_ignored_for_class', event='dispatch', kwargs={'forced_mode': 'separate process,blocking'},
        definitions=[{'event': 'dispatch', 'mode': 'same process,same transaction'}])
    add('class_object', operation='handle', handlers=[{'class_object': True, 'mode': 'same process,same transaction'}])
    add('shared_output_mutation', operation='handle', output={'original': True},
        handlers=[{'mode': 'same process,same transaction', 'data': {'mutate': 'extra'}}])
    for mode in ('same process,same transaction', 'same process,new transaction'):
        add('error_' + mode, event='dispatch', command=True, definitions=[
            {'code': 'broken', 'event': 'dispatch', 'mode': mode, 'data': {'fail': True}},
            {'code': 'next', 'event': 'dispatch', 'mode': mode, 'data': {'result': 'next'}}])
        add('handler_' + mode, event='dispatch', command=True, definitions=[
            {'event': 'dispatch', 'mode': mode, 'class_name': 'tactic_stream_trigger_probe.RecordedHandler'}])
        for fail in (False, True):
            add('rollback_' + mode + str(fail), event='dispatch', command=True, caller_write=True,
                caller_fail=fail, inspect_value=True, definitions=[
                    {'event': 'dispatch', 'mode': mode, 'data': {'write': True}}])
    add('deferred_dedup', event='dispatch', command=True, definitions=[
        {'event': 'dispatch', 'code': 'one'}, {'event': 'dispatch', 'code': 'two'}])
    add('deferred_recursive', event='dispatch', command=True,
        definitions=[{'event': 'dispatch', 'data': {'recursive': True}}])
    for updates in ({}, {'name': 'new'}, {'timestamp': 'now'}, {'name': 'new', 'amount': 1, 'timestamp': 'now'}):
        for integral in (False, True):
            events = ['update', 'update|contract/entity', 'change', 'change|contract/entity',
                      'update|contract/entity|name', 'change|contract/entity|name',
                      'update|contract/entity|amount', 'change|contract/entity|amount',
                      'update|contract/entity|timestamp']
            add('sobject_' + str(updates) + str(integral), operation='sobject_events', updates=updates,
                triggers='integral' if integral else True,
                definitions=[{'code': event + str(flag), 'event': event, 'integral': flag,
                              'mode': 'same process,same transaction'} for event in events for flag in (False, True)])
    add('sobject_process_parent_keys', operation='sobject_events', process='model', parent_type='contract/parent',
        definitions=[{'code': str(i), 'event': 'update', **key, 'mode': 'same process,same transaction'}
                     for i, key in enumerate(({}, {'process': 'model'}, {'search_type': 'contract/parent'},
                                              {'process': 'model', 'search_type': 'contract/parent'}))])
    for args, kwargs in (([], {}), ([False], {}), (['value'], {'extra': 1}), ([], {'value': None})):
        add('common_' + repr(args) + repr(kwargs), operation='common', args=args, kwargs=kwargs)
    for mode in ('same process,same transaction', 'same process,new transaction'):
        for fail in (False, True):
            add('unchanged_script_' + mode + str(fail), operation='script', mode=mode, fail=fail, caller_write=True)
    for lookup in ('get_by_code', 'get_by_id'):
        for identity, first, second in ((('A', 1), True, True), (('missing', 999), True, True),
                                        (('C', 3), True, False), (('C', 3), False, True)):
            for project in ('one', 'two'):
                add('lookup_cache_' + lookup + str(identity) + str(first) + project, operation='lookup_cache',
                    lookup=lookup, identity=identity[0 if lookup == 'get_by_code' else 1],
                    first_retired=first, second_retired=second, project=project)
    return cases


class TriggerParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        trigger_fixture(cls.store)
        cls.cases = trigger_cases()

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary) / 'probe'
            shutil.copytree(self.store.data_dir, data)
            with request_context(RequestContext(Store(data), 'admin', case.get('project', 'one'))), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                return run_trigger_case(case)

    def assert_case_result(self, case, result, original):
        if case['name'] in ('static_integral_order', 'static_renew'):
            # Source extends its cached list on reads, duplicating startup triggers.
            self.assertEqual(result['result'].count('STARTUP'), 1)
            self.assertGreater(original['result'].count('STARTUP'), 1)
            expected = copy.deepcopy(original)
            for rows in [expected['result']] + expected.get('cache_steps', []):
                if isinstance(rows, list):
                    while rows.count('STARTUP') > 1:
                        rows.remove('STARTUP')
            self.assertEqual(result, expected)
        else:
            super().assert_case_result(case, result, original)

    def test_original_imports_classes_and_signatures(self):
        from pyasm.biz import TriggerSObj as ImportedDefinition, Notification as ImportedNotification
        from pyasm.biz.command_trigger import Trigger as DeprecatedTrigger
        from pyasm.command import HandlerCmd as ImportedHandler
        self.assertIs(ImportedDefinition, TriggerSObj)
        self.assertIs(ImportedNotification, Notification)
        self.assertIs(ImportedHandler, HandlerCmd)
        self.assertTrue(issubclass(DeprecatedTrigger, TriggerSObj))
        self.assertTrue(issubclass(TriggerSObj, SObject))
        self.assertTrue(issubclass(Notification, SObject))
        for owner, source_path in ((TriggerSObj, 'biz/command_trigger.py'), (Notification, 'biz/notification.py'),
                                   (HandlerCmd, 'command/command.py'), (Common, 'common/common.py')):
            source = ast.parse((read_tests.LEGACY / 'src/pyasm' / source_path).read_text(encoding='utf-8'))
            original = next(n for n in source.body if isinstance(n, ast.ClassDef) and n.name == owner.__name__)
            for node in original.body:
                if isinstance(node, ast.FunctionDef) and node.name in owner.__dict__:
                    descriptor = owner.__dict__[node.name]
                    actual = inspect.signature(descriptor.__func__ if isinstance(descriptor, classmethod)
                                               else getattr(owner, node.name))
                    self.assertEqual(list(actual.parameters), [arg.arg for arg in node.args.args])
        with request_context(RequestContext(self.store, 'admin', 'one')):
            definition = Search.get_by_code('sthpw/trigger', 'B_ONE')
            self.assertIsInstance(definition, TriggerSObj)
            self.assertEqual(definition.get_primary_key_value(), 'tactic_stream_trigger_probe.RecordedTrigger')
            self.assertEqual(definition.get_description(), definition.get_primary_key_value())
            self.assertIsInstance(Search.get_by_code('sthpw/notification', 'N_B_ONE'), Notification)

    def test_unsupported_handlers_fail_before_any_selected_handler_executes(self):
        for fields in ({'mode': 'unsupported_mode'},
                       {'class_name': 'Trigger'},
                       {'class_name': 'tactic.plugins.example.Handler'}):
            with self.subTest(fields=fields), request_context(RequestContext(self.store, 'admin', 'one')):
                Container.put('TriggerProbe:state', {'events': []})
                definitions = [Definition({'mode': 'same process,same transaction'}), Definition(fields)]
                with self.assertRaises(UnsupportedContract):
                    Trigger._handle_trigger_sobjs(definitions, Command(), 'changed', {})
                self.assertEqual(Container.get('TriggerProbe:state')['events'], [])
                self.assertEqual(Container.get_seq('Trigger:called_triggers'), [])
                for path in ('Trigger', 'tactic.plugins.example.Handler'):
                    with self.assertRaises(UnsupportedContract): Common.resolve_class(path)
                with self.assertRaises(ValueError): Common.resolve_class('os.system("bad")')

    def test_missing_config_is_optional_but_broken_registered_tables_raise(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary) / 'probe')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with store.connection(write=True) as db:
                db.execute("DELETE FROM search_object WHERE search_type='config/trigger'")
            with request_context(RequestContext(store, 'admin', 'one')):
                self.assertEqual([obj.get_code() for obj in Trigger.get_db_triggers()],
                                 ['A_GLOBAL', 'B_ONE', 'D_MULTI', 'F_PROCESS', 'G_TYPE', 'H_BOTH'])
            with store.connection(write=True) as db:
                db.execute("INSERT INTO search_object (code,search_type,namespace,database,table_name,class_name) VALUES ('config/trigger','config/trigger','config','{project}','missing_trigger','pyasm.biz.TriggerSObj')")
            with request_context(RequestContext(store, 'admin', 'one')):
                with self.assertRaisesRegex(LookupError, 'Registered table does not exist'):
                    Trigger.call(None, 'missing')


class TriggerUpgrade(unittest.TestCase):
    def test_original_tables_upgrade_atomically_without_copying_rules_or_users(self):
        metadata = json.loads((read_tests.ROOT / 'src/tactic_stream/compatibility/trigger_upgrade.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata, trigger_schema(read_tests.LEGACY))
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary))
            store.initialize(hash_password('private-trigger-upgrade'))
            with store.connection(write=True) as db:
                for name in metadata['tables']:
                    self.assertEqual(db.execute('SELECT count(*) FROM "' + name + '"').fetchone()[0], 0)
                    db.execute('DROP TABLE "' + name + '"')
                    db.execute('DELETE FROM search_object WHERE search_type=?', ('sthpw/' + name,))
                account = dict(db.execute('SELECT * FROM login').fetchone())
            self.assertTrue(store.upgrade())
            with store.connection() as db:
                self.assertEqual(dict(db.execute('SELECT * FROM login').fetchone()), account)
                self.assertEqual(set(metadata['tables']) - set(store.tables('sthpw')), set())
            before = store.database_path('sthpw').read_bytes()
            self.assertFalse(store.upgrade())
            self.assertEqual(store.database_path('sthpw').read_bytes(), before)
            with store.connection(write=True) as db:
                db.execute('DROP TABLE notification')
                db.execute("UPDATE search_object SET class_name='custom.Trigger' WHERE search_type='sthpw/trigger'")
            before = store.database_path('sthpw').read_bytes()
            with self.assertRaises(ValueError): store.upgrade()
            self.assertEqual(store.database_path('sthpw').read_bytes(), before)
