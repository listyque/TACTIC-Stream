import json
import shutil
import tempfile
from pathlib import Path

import test_read_parity as read_tests
from test_pipeline import pipeline_fixture
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from tools.generation_probe import run_generation_case


GRAPH = '''<pipeline>
  <process name="design" assigned_group="crew"/>
  <process name="build" duration="1" bid_duration="2"/>
  <process name="review" type="approval" duration="1"/>
  <process name="auto" type="auto"/>
  <process name="publish" duration="1"/>
  <connect from="design" to="review" context="design/output"/>
  <connect from="build" to="review"/>
  <connect from="review" to="auto"/>
  <connect from="auto" to="publish"/>
</pipeline>'''


def generation_fixture(store):
    pipeline_fixture(store)
    with store.connection(write=True) as db:
        db.execute('INSERT INTO pipeline (code,pipeline,project_code) VALUES (?,?,?)', ('GEN', GRAPH, 'one'))
    with store.connection('one', write=True) as db:
        db.execute("UPDATE entity SET pipeline_code='GEN' WHERE code='A'")
        if 'description' not in {row[1] for row in db.execute('PRAGMA table_info(spt_process)')}:
            db.execute('ALTER TABLE spt_process ADD description text')
        workflow = {'version': 2, 'properties': {'duration': '2', 'bid_duration': '4'}}
        db.execute('INSERT INTO spt_process (code,process,pipeline_code,workflow,description) VALUES (?,?,?,?,?)',
                   ('GEN_DESIGN', 'design', 'GEN', json.dumps(workflow), 'Дизайн'))
        # Native workflow listeners require the same complete process metadata as Pipeline.commit.
        for process in ('build', 'review', 'auto', 'publish'):
            db.execute('INSERT INTO spt_process (code,process,pipeline_code) VALUES (?,?,?)',
                       ('GEN_' + process.upper(), process, 'GEN'))


class GenerationParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        generation_fixture(cls.store)
        cls.cases = [dict(method='generation_contract', project='one', name=name, **options) for name, options in
                     [('dag', {}), ('explicit', {'explicit': True}), ('copies', {'copies': True}),
                      ('prefix', {'prefix': True}), ('integer', {'integer': True}),
                      ('schedule', {'preview': 'schedule'}), ('projection', {'preview': 'projected_schedule'}),
                      ('calendar', {'calendar': True}), ('context', {'context': True})]]

    def new_result(self, case):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_generation_case(case)

    def assert_case_result(self, case, result, original):
        self.assertNotIn('error', result, result)
        if case.get('calendar'):
            self.assertEqual(original['negative'], '2026-01-19T12:00:00')
            self.assertEqual(result['negative'], '2026-01-16T12:00:00')
            self.assertEqual(result['forward'], '2026-01-21T12:00:00')
            self.assertEqual(result['backward'], '2026-01-16T12:00:00')
            original['negative'] = result['negative']
        if case.get('integer'):
            self.assertEqual(original, {'error': 'AttributeError'})
            self.assertEqual(len(result['tasks']), 4)
            self.assertEqual(result['effects'], {'tasks': 4, 'status_logs': 4})
            return
        if case.get('context'):
            self.assertEqual(original, {'error': 'TypeError'})
            self.assertEqual([row['context'] for row in result['tasks']], ['custom'])
            self.assertEqual(result['effects'], {'tasks': 1, 'status_logs': 1})
            return
        self.assertNotIn('error', original, original)
        if case.get('copies'):
            self.assertEqual(original['repeated'], [])
            self.assertEqual(len(result['repeated']), 4)
            self.assertTrue(all(row['context'].endswith('/001') for row in result['repeated']))
            self.assertEqual(original['effects'], {'tasks': 4, 'status_logs': 4})
            self.assertEqual(result['effects'], {'tasks': 8, 'status_logs': 8})
            original['effects'] = result['effects']
            result['repeated'] = []
        if case.get('prefix'):
            self.assertEqual([row['process'] for row in original['tasks']], ['build', 'review', 'publish'])
            self.assertEqual([row['process'] for row in result['tasks']], ['design', 'build', 'review', 'publish'])
            self.assertEqual(result['tasks'][0]['context'], 'design/output')
            self.assertEqual(result['tasks'][2]['bid_start_date'], '2026-01-21 12:00:00')
            self.assertEqual(original['effects'], {'tasks': 4, 'status_logs': 4})
            self.assertEqual(result['effects'], {'tasks': 5, 'status_logs': 5})
            return
        if case.get('explicit'):
            self.assertEqual(original['effects'], {'tasks': 2, 'status_logs': 2})
            self.assertEqual(result['effects'], {'tasks': 2, 'status_logs': 2})
        super().assert_case_result(case, result, original)

    def test_preflight_and_mid_generation_failure_leave_no_writes(self):
        from unittest.mock import patch
        from pyasm.biz import Task, TaskGenerator
        from pyasm.command import Command
        from pyasm.common.errors import UnsupportedContract
        from pyasm.search import Search, SearchType
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'data')
            shutil.copytree(self.store.data_dir, store.data_dir)
            from pyasm.common import Environment
            from pyasm.security import Security
            with request_context(RequestContext(store, 'admin', 'one')):
                security = Security()
                Environment.set_security(security)
                security._is_logged_in = 1
                security._login = Search.get_by_code('sthpw/login', 'admin')
                parent = Search.get_by_code('contract/entity', 'A')
                kinds = ('sthpw/task', 'sthpw/status_log', 'sthpw/transaction_log', 'sthpw/change_timestamp')
                before = [Search(kind).get_count() for kind in kinds]
                for xml in ('<pipeline><process name="a"/><connect from="a" to="a"/></pipeline>',
                            '<pipeline><process name="a" type="hierarchy"/></pipeline>',
                            '<pipeline><process name="a" task_pipeline="custom"/></pipeline>'):
                    pipeline = SearchType.create('sthpw/pipeline')
                    pipeline.set_value('code', 'GUARD')
                    pipeline.set_pipeline(xml)
                    expected = ValueError if 'type="hierarchy"' in xml else UnsupportedContract
                    with self.assertRaises(expected):
                        TaskGenerator().execute(parent, pipeline)
                create = Task.create
                calls = []
                def fail_second(*args, **kwargs):
                    task = create(*args, **kwargs)
                    calls.append(task.get_search_key())
                    if len(calls) == 2:
                        raise ValueError('generation failed')
                    return task
                class Failed(Command):
                    def execute(self):
                        self.get_transaction().set_sync(False)
                        return Task.add_initial_tasks(parent, start_date='2026-01-16')
                with patch.object(Task, 'create', side_effect=fail_second):
                    with self.assertRaisesRegex(ValueError, 'generation failed'):
                        Command.execute_cmd(Failed())
                self.assertEqual(len(calls), 2)
                self.assertEqual([Search(kind).get_count() for kind in kinds], before)
                self.assertTrue(all(Search.get_by_search_key(key) is None for key in calls))
