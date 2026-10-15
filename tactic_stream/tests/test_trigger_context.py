"""Reuse trigger context only across events with no invoked handler."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.checkin_benchmark import prepare
from pyasm.biz import Snapshot
from pyasm.command import Command, Trigger
from pyasm.common import Container, Environment
from pyasm.security import LoginGroup
from pyasm.search import Search, SearchType, SObject
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store


class ContextMutation(Trigger):
    def execute(self):
        change = Container.get('context_change')
        parent = Search.get_by_code('cg/shot', 'SH001')
        if change == 'pipeline':
            parent.set_value('pipeline_code', 'second')
            parent.commit(triggers=False)
        elif change == 'process':
            obj = Search.get_by_code('config/process', 'FIRST')
            obj.set_value('code', 'RENAMED')
            obj.commit(triggers=False)
        elif change == 'uncommitted':
            parent.set_value('pipeline_code', 'second')
        elif change == 'rights':
            group = LoginGroup.get_by_group_name('context_writers')
            group.set_value('access_rules', Container.get('context_denied_rules'))
            manager = Environment.get_security().get_access_manager()
            manager.groups.pop('search_type', None)
            manager.add_xml_rules(group)
        elif change == 'failure':
            parent.set_value('pipeline_code', 'second')
            parent.commit(triggers=False)
            raise ValueError('context trigger failure')


class TriggerContext(unittest.TestCase):
    def setUp(self):
        builtins = patch.object(Trigger, 'get_integral_triggers',
                                side_effect=lambda: Container.get_seq(Trigger.INTEGRAL_TRIGGER_KEY)[:])
        builtins.start()
        self.addCleanup(builtins.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name) / 'data')
        self.api, self.ticket = prepare(self.store)
        self.auth = dict(ticket=self.ticket, project='one')
        self.api.dispatch('update', (self.auth, 'cg/shot?project=one&code=SH001',
                         dict(pipeline_code='first')), dict(triggers=False))
        for code, pipeline in [('FIRST', 'first'), ('SECOND', 'second')]:
            self.api.dispatch('insert', (self.auth, 'config/process',
                             dict(code=code, process='publish', pipeline_code=pipeline)),
                             dict(triggers=False))

    def scope(self):
        return request_context(RequestContext(self.store, 'admin', 'one'))

    def snapshot(self):
        return Snapshot.create(Search.get_by_code('cg/shot', 'SH001'), 'file', 'publish', commit=False)

    def test_empty_handlers_resolve_parent_and_process_once_per_call(self):
        with self.scope():
            self.api.auth.bind_security('admin', self.ticket)
            obj = self.snapshot()
            original = SObject.get_parent
            parents = []
            def get_parent(instance, *args, **kwargs):
                parents.append(instance)
                return original(instance, *args, **kwargs)
            statements = []
            sql = Search('config/process').get_sql()
            sql.get_connection().set_trace_callback(statements.append)
            try:
                with patch.object(SObject, 'get_parent', get_parent):
                    for _ in range(2):
                        obj._call_triggers({'description': 'x', 'version': 1},
                            'insert', {}, 'publish', 'cg/shot', 'integral')
                self.assertEqual(parents, [obj, obj])
                queries = [query for query in statements if query.startswith('SELECT')
                           and '"spt_process"' in query and '"pipeline_code"' in query]
                self.assertEqual(len(queries), 2, queries)
            finally:
                sql.get_connection().set_trace_callback(None)

    def test_invoked_triggers_refresh_committed_and_uncommitted_context(self):
        for change, expected in [('pipeline', 'SECOND'), ('process', 'RENAMED'),
                                 ('uncommitted', 'SECOND')]:
            with self.subTest(change=change), self.scope():
                self.api.auth.bind_security('admin', self.ticket)
                # Each case restores fixture state through the native API.
                parent = Search.get_by_code('cg/shot', 'SH001')
                parent.set_value('pipeline_code', 'first')
                process = Search('config/process')
                process.add_filter('pipeline_code', 'first')
                process = process.get_sobject()
                command = Command()
                command.get_transaction().set_sync(False)
                def execute():
                    parent.commit(triggers=False)
                    process.set_value('code', 'FIRST')
                    process.commit(triggers=False)
                    Container.put('context_change', change)
                    definition = SearchType.create('sthpw/trigger')
                    for name, value in dict(event='change', class_name=ContextMutation,
                                           mode='same process,same transaction').items():
                        definition.set_value(name, value)
                    Trigger.append_integral_trigger(definition)
                    Trigger.clear_db_cache()
                    calls = []
                    original = Trigger.call_by_key
                    def call(key, *args, **kwargs):
                        calls.append(dict(key))
                        return original(key, *args, **kwargs)
                    with patch.object(Trigger, 'call_by_key', side_effect=call):
                        self.snapshot()._call_triggers({'description': 'x'}, 'insert', {},
                            'publish', 'cg/shot', 'integral')
                    self.assertIn({'event': 'insert', 'process': 'FIRST'}, calls)
                    self.assertIn({'event': 'change', 'process': expected}, calls)
                    self.assertIn({'event': 'change|sthpw/snapshot|description',
                                   'process': expected, 'search_type': 'cg/shot'}, calls)
                command.execute = execute
                Command.execute_cmd(command)

    def test_late_trigger_failure_rolls_back_context_write(self):
        with self.scope():
            self.api.auth.bind_security('admin', self.ticket)
            command = Command()
            command.get_transaction().set_sync(False)
            def execute():
                Container.put('context_change', 'failure')
                definition = SearchType.create('sthpw/trigger')
                for name, value in dict(event='change', class_name=ContextMutation,
                                       mode='same process,same transaction').items():
                    definition.set_value(name, value)
                Trigger.append_integral_trigger(definition)
                Trigger.clear_db_cache()
                self.snapshot()._call_triggers({}, 'insert', {}, 'publish', 'cg/shot', 'integral')
            command.execute = execute
            with self.assertRaisesRegex(ValueError, 'context trigger failure'):
                Command.execute_cmd(command)
            self.assertEqual(Search.get_by_code('cg/shot', 'SH001').get_value('pipeline_code'), 'first')

    def test_custom_parent_getter_is_not_reused(self):
        with self.scope():
            self.api.auth.bind_security('admin', self.ticket)
            parents = []
            def dynamic_parent(instance, *args, **kwargs):
                parent = SObject.get_parent(instance, *args, **kwargs)
                parent.set_value('pipeline_code', 'first' if len(parents) % 2 == 0 else 'second')
                parents.append(parent)
                return parent
            class DynamicSnapshot(Snapshot):
                get_parent = dynamic_parent
            calls = []
            original = Trigger.call_by_key
            def call(key, *args, **kwargs):
                calls.append(dict(key))
                return original(key, *args, **kwargs)
            for style in ('class', 'instance'):
                with self.subTest(style=style):
                    obj = self.snapshot()
                    parents.clear()
                    calls.clear()
                    if style == 'class':
                        obj.__class__ = DynamicSnapshot
                    else:
                        obj.get_parent = lambda: dynamic_parent(obj)
                    with patch.object(Trigger, 'call_by_key', side_effect=call):
                        obj._call_triggers({}, 'insert', {}, 'publish', 'cg/shot', 'integral')
                    self.assertEqual(len(parents), 4)
                    self.assertEqual([key['process'] for key in calls if 'search_type' not in key
                                     and key.get('process') in ('FIRST', 'SECOND')],
                                     ['FIRST', 'SECOND', 'FIRST', 'SECOND'])

    def test_trigger_revoking_read_rights_invalidates_context_without_commit(self):
        rules = ('<rules><rule group="project" code="one" access="allow"/>'
                 '<rule group="search_type" code="*" access="allow"/>%s</rules>')
        self.api.dispatch('insert', (self.auth, 'sthpw/login_group',
            dict(login_group='context_writers', access_rules=rules % '')))
        self.api.dispatch('execute_python_script', (self.auth, '', dict(code=
            "from pyasm.security import Login\nLogin.create('context_writer', 'private-context-writer', groups=['context_writers'])")))
        ticket = self.api.get_ticket('context_writer', 'private-context-writer')
        with request_context(RequestContext(self.store, 'context_writer', 'one')):
            self.api.auth.bind_security('context_writer', ticket)
            command = Command()
            command.get_transaction().set_sync(False)
            def execute():
                Container.put('context_change', 'rights')
                Container.put('context_denied_rules', rules %
                    '<rule group="search_type" code="cg/shot" project="one" access="deny"/>')
                definition = SearchType.create('sthpw/trigger')
                for name, value in dict(event='change', class_name=ContextMutation,
                                       mode='same process,same transaction').items():
                    definition.set_value(name, value)
                Trigger.append_integral_trigger(definition)
                Trigger.clear_db_cache()
                calls = []
                original = Trigger.call_by_key
                def call(key, *args, **kwargs):
                    calls.append(dict(key))
                    return original(key, *args, **kwargs)
                with patch.object(Trigger, 'call_by_key', side_effect=call):
                    self.snapshot()._call_triggers({}, 'insert', {}, 'publish', 'cg/shot', 'integral')
                self.assertIn({'event': 'insert', 'process': 'FIRST'}, calls)
                self.assertNotIn({'event': 'change', 'process': 'FIRST'}, calls)
                self.assertIsNone(Search.get_by_code('cg/shot', 'SH001'))
            command.execute = execute
            Command.execute_cmd(command)
