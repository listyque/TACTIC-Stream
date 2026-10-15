"""Native chunk persistence, queue ownership, naming and transaction boundaries."""
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.checkin_benchmark import prepare
from pyasm.command import Command
from pyasm.search import Search
from pyasm.search.storage import Store
from pyasm.search.search import RequestContext, request_context
from pyasm.common.errors import UserException, SecurityException
from tactic.command.queue import JobTask, _ClaimJobCmd, _FinishJobsCmd
from tactic.command.checkin_queue_cmd import SubmitCheckinChunkCmd, CancelCheckinBatchCmd, updates, JOB_COMMAND


class CheckinQueue(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.store = Store(self.temporary.name)
        self.api, self.ticket = prepare(self.store)
        self.api.protocol = 'json'
        self.auth = dict(ticket=self.ticket, project='one')

    @contextmanager
    def context(self, login='admin', ticket=None):
        with request_context(RequestContext(self.store, login, 'one')):
            self.api.auth.bind_security(login, ticket or self.ticket)
            yield

    def submit(self, operations, pieces, contents, chunk='first', batch='test'):
        with self.context():
            cmd = SubmitCheckinChunkCmd(batch_id=batch, chunk_id=chunk, operations=operations,
                pieces=pieces, uploads=[('part', content) for content in contents])
            cmd.get_transaction().set_sync(False)
            return Command.execute_cmd(cmd)

    def options(self, count=1, **changes):
        return dict(search_key='cg/shot?project=one&code=SH001', context='publish/queue', process='publish',
                    source_files=[dict(path='payload_%04d.txt' % index, size=4) for index in range(count)],
                    keep_file_name=True, create_icon=False, update_versionless=True, **changes)

    def poll(self, cursors=None, limit=100, batch='test'):
        with self.context():
            return updates([dict(batch_id=batch, project='one')], cursors, limit)

    def run_one(self):
        with self.context():
            return JobTask(queue='checkin').check_new_job('checkin')

    def snapshots(self):
        return self.api.dispatch('query', (self.auth, 'sthpw/snapshot'), dict(filters=[('context','publish/queue')]))

    def test_partial_out_of_order_duplicate_and_durable_result(self):
        operation = dict(operation_id='one', options=self.options())
        piece = dict(operation_id='one', file_index=0, offset=2)
        self.submit([operation], [piece], [b'cd'])
        self.assertFalse(self.run_one())
        self.assertEqual(self.poll()['checkins'][0]['state'], 'staging')
        self.assertTrue(self.submit([operation], [piece], [b'cd'])['duplicate'])
        with self.assertRaises(UserException):
            self.submit([operation], [piece], [b'xy'])
        cursor = self.poll()['checkinCursors']
        self.submit([], [dict(piece, offset=0)], [b'ab'], chunk='last')
        self.assertEqual(self.poll(cursor)['checkins'][0]['state'], 'pending')
        self.assertTrue(self.run_one())
        result = self.poll(cursor)['checkins'][0]
        self.assertEqual(result['state'], 'complete')
        self.assertEqual(result['snapshot']['version'], 1)
        self.assertEqual(result['snapshot']['repo'], 'base')
        files = self.api.dispatch('query',(self.auth,'sthpw/file'),dict(filters=[('snapshot_code',result['snapshot']['code'])]))
        with self.context():
            from pyasm.biz import File
            paths = [File.get_by_code(file['code']).get_lib_path() for file in files]
        self.assertEqual([Path(path).read_bytes() for path in paths], [b'abcd'])
        # Staging was removed after commit; native history still replays the repository copy.
        self.api.dispatch('undo',(self.auth,))
        self.assertFalse(Path(paths[0]).exists())
        self.api.dispatch('redo',(self.auth,))
        self.assertEqual(Path(paths[0]).read_bytes(), b'abcd')
        self.assertEqual(self.poll(self.poll()['checkinCursors'])['checkins'], [])

    def test_two_jobs_same_context_versions_and_pagination(self):
        operations = [dict(operation_id=str(index), options=dict(self.options(),keep_file_name=False)) for index in range(2)]
        pieces = [dict(operation_id=str(index), file_index=0, offset=0) for index in range(2)]
        self.submit(operations, pieces, [b'abcd',b'efgh'])
        self.assertTrue(self.run_one()); self.assertTrue(self.run_one())
        page = self.poll(limit=1)
        self.assertTrue(page['checkinsHasMore'])
        other = self.poll(page['checkinCursors'], limit=1)
        self.assertFalse(other['checkinsHasMore'])
        self.assertEqual(sorted([page['checkins'][0]['snapshot']['version'], other['checkins'][0]['snapshot']['version']]), [1,2])

    def test_large_group_reaches_native_checkin_and_undo(self):
        count = 1001
        operation = dict(operation_id='large', options=dict(self.options(count), update_versionless=False))
        for index, record in enumerate(operation['options']['source_files']):
            record['path'] = 'payload_%04d_data.txt' % index
        for offset in range(0, count, 50):
            pieces = [dict(operation_id='large', file_index=index, offset=0)
                      for index in range(offset, min(offset + 50, count))]
            self.submit([operation] if offset == 0 else [], pieces, [b'abcd'] * len(pieces), chunk=str(offset))
        self.assertTrue(self.run_one())
        result = self.poll()['checkins'][0]
        self.assertEqual(result['state'], 'complete', result.get('error'))
        files = self.api.dispatch('query', (self.auth, 'sthpw/file'),
                                 dict(filters=[('snapshot_code', result['snapshot']['code'])]))
        self.assertEqual(len(files), count)
        with self.context():
            from pyasm.biz import File
            paths = [File.get_by_code(file['code']).get_lib_path() for file in files]
        self.assertEqual({Path(path).name for path in paths},
                         {record['path'] for record in operation['options']['source_files']})
        self.assertTrue(all(Path(path).read_bytes() == b'abcd' for path in paths))
        self.api.dispatch('undo', (self.auth,))
        self.assertEqual(self.snapshots(), [])
        self.assertFalse(any(Path(path).exists() for path in paths))

    def test_large_group_limit_cannot_be_overridden_by_client(self):
        operation = dict(operation_id='large', options=self.options(10001))
        with self.assertRaisesRegex(UserException, 'up to 10000 files'):
            self.submit([operation], [dict(operation_id='large', file_index=0, offset=0)], [b'abcd'])
        self.assertEqual(self.poll()['checkins'], [])
        operation['options'] = dict(self.options(), max_files=100000)
        with self.assertRaisesRegex(ValueError, 'Invalid queued check-in options'):
            self.submit([operation], [dict(operation_id='large', file_index=0, offset=0)], [b'abcd'])

    def test_existing_default_repository_is_readable_by_unchanged_handler(self):
        # Replay a pre-fix row through the actual Handler file and result model.
        import sys
        from pyasm.biz import Snapshot
        self.submit([dict(operation_id='one', options=self.options())],
                    [dict(operation_id='one', file_index=0, offset=0)], [b'abcd'])
        self.assertTrue(self.run_one())
        code = self.poll()['checkins'][0]['snapshot']['code']
        key = 'sthpw/snapshot?code=' + code
        self.api.dispatch('update', (self.auth, key, dict(repo='default')), dict(triggers=False))
        with self.context():
            self.assertEqual(Snapshot.get_by_code(code).get_value('repo'), 'default')
        self.assertEqual(self.api.dispatch('query', (self.auth, 'sthpw/snapshot'),
            dict(filters=[('code', code)], columns=['repo'], single=True))['repo'], 'base')
        records = self.api.dispatch('query_snapshots', (self.auth,),
            dict(filters=[('code', code)], include_files=True))
        self.assertEqual(records[0]['repo'], 'base')
        previous_path = sys.path.copy()
        sys.path.insert(0, 'D:/code/th_codex')
        try:
            from thlib.environment import env_tactic
            from thlib.tactic_classes import Snapshot as HandlerSnapshot
            from thlib.ui.workspace_models.results import WorkspaceItemModel
            base = [(self.store.data_dir / 'assets').as_posix(), 'Main repository', '#123456', 'base', True]
            with patch.object(env_tactic, 'base_dirs', dict(asset_base_dir=base)):
                self.assertIsNone(env_tactic.get_base_dir('default'))
                node = WorkspaceItemModel()._make_snapshot_node(
                    HandlerSnapshot(records[0]), 'publish', 'publish/queue', 1, '#123456', 'parent')
                self.assertEqual(node.title, 'payload_0000.txt')
                self.assertTrue(node.file_exists)
                self.assertEqual(Path(node.file_path).read_bytes(), b'abcd')
                self.assertEqual(node.repository, 'Main repository')
        finally:
            sys.path[:] = previous_path
        with self.context():
            self.assertEqual(Snapshot.get_by_code(code).get_value('repo'), 'default')

    def test_cancel_prevents_pending_and_partial_jobs(self):
        self.submit([dict(operation_id='one',options=self.options())],
                    [dict(operation_id='one',file_index=0,offset=0)],[b'ab'])
        with self.context():
            command = CancelCheckinBatchCmd(batch_id='test')
            command.get_transaction().set_sync(False); Command.execute_cmd(command)
        self.assertFalse(self.run_one())
        self.assertEqual(self.poll()['checkins'][0]['state'], 'terminated')
        with self.assertRaises(UserException):
            self.submit([], [dict(operation_id='one',file_index=0,offset=2)],[b'cd'],chunk='last')

    def test_failure_rolls_back_and_is_not_retried(self):
        self.submit([dict(operation_id='one',options=self.options())],
                    [dict(operation_id='one',file_index=0,offset=0)],[b'abcd'])
        from pyasm.web.api_xmlrpc import ApiXMLRPC
        original = ApiXMLRPC._get_sobject_dict
        calls = []
        def fail(api, obj, *args, **kwargs):
            if obj.get_base_search_type() == 'sthpw/snapshot':
                calls.append(obj.get_code()); raise ValueError('Late metadata failure')
            return original(api, obj, *args, **kwargs)
        with patch.object(ApiXMLRPC, '_get_sobject_dict', fail):
            self.assertTrue(self.run_one())
        self.assertEqual(len(calls),1)
        result = self.poll()['checkins'][0]
        self.assertEqual(result['state'],'error')
        self.assertIn('Late metadata failure',result['error'])
        self.assertEqual(self.snapshots(),[])
        self.assertFalse(self.run_one())

    def test_dead_worker_requires_explicit_review(self):
        self.submit([dict(operation_id='one',options=self.options())],
                    [dict(operation_id='one',file_index=0,offset=0)],[b'abcd'])
        with self.context():
            task = JobTask(queue='checkin')
            Command.execute_cmd(_ClaimJobCmd(task=task,queue_type='checkin'))
            Command.execute_cmd(_FinishJobsCmd(host=task.get_process_key(),state='pending'))
        result = self.poll()['checkins'][0]
        self.assertEqual(result['state'],'error')
        self.assertIn('worker stopped',result['error'])
        self.assertFalse(self.run_one())

    def test_rejects_escaping_manifest_and_overlapping_parts(self):
        options = self.options(); options['source_files'][0]['path'] = '../outside.txt'
        with self.assertRaises((ValueError,UserException)):
            self.submit([dict(operation_id='one',options=options)],
                        [dict(operation_id='one',file_index=0,offset=0)],[b'abcd'])
        self.submit([dict(operation_id='one',options=self.options())],
                    [dict(operation_id='one',file_index=0,offset=0)],[b'abc'])
        with self.assertRaises(UserException):
            self.submit([], [dict(operation_id='one',file_index=0,offset=1)],[b'bc'],chunk='overlap')

    def test_user_identity_acl_revocation_and_private_results(self):
        from test_project_writes import install_writer, set_rules, PASSWORD
        install_writer(self.store)
        rules = '<rules><rule group="project" code="one" access="allow"/><rule group="project" key="one" access="allow"/><rule group="search_type" code="cg/shot" project="one" access="allow"/><rule group="search_type" code="sthpw/snapshot" access="allow"/><rule group="search_type" code="sthpw/file" access="allow"/><rule group="api_cmd" key="tactic.command.PythonCmd" access="allow"/></rules>'
        set_rules(self.store,rules)
        ticket = self.api.get_ticket('project_writer',PASSWORD)
        writer = dict(ticket=ticket,project='one')
        self.submit([dict(operation_id='private',options=self.options())],
                    [dict(operation_id='private',file_index=0,offset=0)],[b'ab'],batch='admin-only')
        self.api.dispatch('insert',(self.auth,'sthpw/queue',dict(code='LEGACY_QUEUE',queue='default',login='admin',command='legacy.Job',state='complete',priority=9999,project_code='one',data='{}')))
        visible = self.api.dispatch('query',(writer,'sthpw/queue'))
        self.assertEqual([row['code'] for row in visible], ['LEGACY_QUEUE'])
        visible = self.api.dispatch('query',(writer,'sthpw/queue'),dict(filters=[('login','admin'),'or']))
        self.assertEqual([row['code'] for row in visible], ['LEGACY_QUEUE'])
        with self.context():
            task = JobTask(queue='checkin')
        for batch in ('allowed','allowed_again','revoked'):
            with self.context('project_writer',ticket):
                cmd = SubmitCheckinChunkCmd(batch_id=batch,chunk_id='one',
                    operations=[dict(operation_id='one',options=dict(self.options(),keep_file_name=False))],
                    pieces=[dict(operation_id='one',file_index=0,offset=0)],uploads=[('part',b'abcd')])
                cmd.get_transaction().set_sync(False); Command.execute_cmd(cmd)
            if batch == 'revoked':
                set_rules(self.store,rules.replace('code="sthpw/snapshot" access="allow"','code="sthpw/snapshot" access="deny"'))
            with self.store.connection() as db:
                before = db.execute('SELECT COUNT(*) FROM ticket').fetchone()[0]
            with self.context():
                self.assertTrue(task.check_new_job('checkin'))
            with self.store.connection() as db:
                after = db.execute('SELECT COUNT(*) FROM ticket').fetchone()[0]
            self.assertEqual(after - before, 1 if batch == 'allowed' else 0)
            self.assertEqual(self.api.auth.validate(task.ticket_cache[(self.store.data_dir, 'project_writer')]), 'project_writer')
            with self.context('project_writer',ticket):
                events = updates([dict(batch_id=batch,project='one')])['checkins']
                self.assertEqual(events[0]['state'],'error' if batch == 'revoked' else 'complete',events)
                if batch == 'allowed':
                    self.assertEqual(events[0]['snapshot']['login'],'project_writer')
            self.assertEqual(self.poll(batch=batch)['checkins'],[])
        with self.assertRaises(SecurityException):
            self.api.dispatch('add_queue_item',(writer,JOB_COMMAND,{}))

    def test_source_changes_between_parts_cannot_be_checked_in(self):
        import hashlib
        options = self.options()
        options['source_files'][0]['sha256'] = hashlib.sha256(b'abcd').hexdigest()
        self.submit([dict(operation_id='one',options=options)],
                    [dict(operation_id='one',file_index=0,offset=0)],[b'ab'])
        self.submit([], [dict(operation_id='one',file_index=0,offset=2)],[b'xy'],chunk='last')
        self.assertTrue(self.run_one())
        result = self.poll()['checkins'][0]
        self.assertEqual(result['state'],'error')
        self.assertIn('source changed',result['error'])
        self.assertEqual(self.snapshots(),[])

    def test_invalid_chunk_removes_new_parts_and_late_cancel_is_authoritative(self):
        from tactic.command.checkin_queue_cmd import batch_code, staging_root
        with self.context():
            root = staging_root(batch_code('test'))
        with self.assertRaises(ValueError):
            self.submit([dict(operation_id='one',options=self.options())],
                        [dict(operation_id='one',file_index=0,offset=0),
                         dict(operation_id='one',file_index=99,offset=0)], [b'ab',b'cd'])
        self.assertFalse(list(root.rglob('*_*')))
        self.assertEqual(self.poll()['checkins'],[])
        self.submit([dict(operation_id='one',options=self.options())],
                    [dict(operation_id='one',file_index=0,offset=0)],[b'abcd'])
        with self.context():
            task = JobTask(queue='checkin')
            Command.execute_cmd(_ClaimJobCmd(task=task,queue_type='checkin'))
            result = Command.execute_cmd(CancelCheckinBatchCmd(batch_id='test'))
            self.assertEqual(result['states'], {'one':'locked'})

    def test_cancel_before_first_upload_leaves_a_tombstone(self):
        with self.context():
            result = Command.execute_cmd(CancelCheckinBatchCmd(batch_id='never'))
            self.assertTrue(result['cancelled'])
        with self.assertRaises(UserException):
            self.submit([dict(operation_id='one',options=self.options())],
                        [dict(operation_id='one',file_index=0,offset=0)],[b'abcd'],batch='never')


if __name__ == '__main__':
    unittest.main()
