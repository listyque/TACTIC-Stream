import sys
from pathlib import Path
from unittest.mock import patch

import test_read_parity as read_tests
from test_checkin import CheckinParity
from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context


class CommandListenersParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        import command_listener_contract
        with cls.store.connection(write=True) as db:
            command_listener_contract.install_fixture(db)
        cls.cases = [dict(method='command_listener_contract', project='admin', name='approval_checkin_and_failure')]

    new_result = CheckinParity.new_result

    def test_system_parent_references_survive_cache_clear(self):
        from pyasm.biz import Project
        from pyasm.search import SObject
        for value in ('contract/listener?project=admin', 'sthpw/note?project=admin'):
            self.assertEqual(Project.get_full_search_type(value, project_code='sthpw'), value)
        with self.store.connection(write=True) as db:
            db.execute("INSERT INTO listener_entity (code) VALUES ('ALIAS_PARENT')")
            for index, suffix in enumerate(('', '?project=admin', '?project=sthpw', '?project=one')):
                db.execute("INSERT INTO note (code, search_type, search_code, note) VALUES (?,?,?,?)",
                           ('ALIAS_NOTE' + str(index), 'contract/listener' + suffix, 'ALIAS_PARENT', str(index)))
        try:
            with request_context(RequestContext(self.store, 'admin', 'admin')):
                self.api.auth.bind_security('admin', self.api.get_ticket('admin', 'private-test-password'))
                parent = Search.get_by_code('contract/listener', 'ALIAS_PARENT')
                SObject.get_cache_dict(search_type='contract/listener').clear()
                search = Search('sthpw/note')
                search.add_parent_filter(parent)
                self.assertEqual(sorted(row.get_value('note') for row in search.get_sobjects()), ['0', '1', '2'])
        finally:
            with self.store.connection(write=True) as db:
                db.execute("DELETE FROM note WHERE search_code='ALIAS_PARENT'")
                db.execute("DELETE FROM listener_entity WHERE code='ALIAS_PARENT'")

    def assert_case_result(self, case, result, original):
        self.assertEqual(original.pop('reloaded_type'), 'contract/listener?project=admin')
        self.assertEqual(result.pop('reloaded_type'), 'contract/listener?project=admin')
        self.assertEqual(original.pop('factory'), 'NameError')
        self.assertEqual(result.pop('factory'), 'CustomCheckin')
        super().assert_case_result(case, result, original)
        self.assertEqual(result['notes'], ['caller committed', 'listener|review', 'listener|archive'])
        self.assertEqual(result['tasks'], [['publish', 'Approved'], ['other', 'Pending']])
        self.assertEqual(result['events'], [
            ['review', {'label': 'review'}, 'task/approved', True, True],
            ['archive', {'label': 'archive'}, 'task/approved', True, True]])
        self.assertEqual(result['failure'], 'listener failed')
        self.assertEqual(result['failed_notes'], ['caller committed'])
        self.assertEqual(result['checkin'], ['publish', 'custom check-in', 'listener file'])
        self.assertEqual(result['checkin_notes'][-1], 'listener|review')
        self.assertEqual(result['checkin_events'], [
            ['review', {'label': 'file'}, 'checkin/move', True, True]])

    def test_listener_cannot_construct_python_handler_with_forged_admin(self):
        from pyasm.biz import Pipeline
        from pyasm.command import Command
        from pyasm.common.errors import SecurityException
        from pyasm.security.authenticator import hash_password
        from pyasm.search.storage import Store
        from tactic_stream.server.api import Api
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('private-listener-password'))
            with request_context(RequestContext(store, 'admin', 'admin')):
                api = Api(store)
                api.auth.bind_security('admin', api.get_ticket('admin', 'private-listener-password'))
                pipeline = Pipeline()
                pipeline.set_pipeline('<pipeline><process name="start"/><process name="end"><action event="done" scope="dependent" class="command_listener_contract.Listener"/></process><connect from="start" to="end"/></pipeline>')
                # The persisted account, rather than mutable Security/Sudo, grants execution.
                with store.connection(write=True) as db:
                    db.execute("UPDATE login SET s_status='retired' WHERE login='admin'")
                with patch('pyasm.common.Common.create_from_class_path') as constructor:
                    with self.assertRaises(SecurityException):
                        Command().handle_pipeline(pipeline, 'start', 'done')
                    constructor.assert_not_called()


class DeferredListenerFailureParity(CommandListenersParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases[0]['deferred_failure'] = True

    def assert_case_result(self, case, result, original):
        self.assertEqual(original.pop('reloaded_type'), 'contract/listener?project=admin')
        self.assertEqual(result.pop('reloaded_type'), 'contract/listener?project=admin')
        self.assertEqual(original.pop('factory'), 'NameError')
        self.assertEqual(result.pop('factory'), 'CustomCheckin')
        # Source PipelineEventCaller swallows the nested error, letting the
        # Trigger commit the failed handler's Note. Stream rolls it back.
        self.assertEqual(original['checkin_notes'][-1], 'listener|review')
        self.assertEqual(result['checkin_notes'], result['notes'])
        original['checkin_notes'] = result['checkin_notes']
        read_tests.ReadParity.assert_case_result(self, case, result, original)
        self.assertEqual(result['checkin'], ['publish', 'custom check-in', 'listener file'])
