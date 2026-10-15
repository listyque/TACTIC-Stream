"""Native requests from independent clients, rollback and crash recovery."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

import test_file_project
from pyasm.biz.file_project import COMMAND, FileProjectRecord, blob_file_path
from pyasm.search.storage import Store
from pyasm.command import Trigger
from tactic_stream.server.api import Api


class PageProbe(Trigger):
    codes = []

    def execute(self):
        self.codes.append(self.get_caller().get_code())


class EditFailure(Trigger):
    def execute(self):
        if self.get_caller().get_json_value('data')['edit_revision'] == 1:
            raise ValueError('late edit trigger failure')


class CheckoutProbe(Trigger):
    counts = []

    def execute(self):
        from pyasm.search import Search
        change = self.get_caller().get_json_value('data')['holders'][0]['change']
        self.counts.append(sum(any(holder['change'] == change for holder in row.get_json_value('data')['holders'])
                               for row in Search('file_project/checkout').get_sobjects()))


class FileProjectResilience(test_file_project.FileProjectFixture, unittest.TestCase):
    def client(self, ticket, action, **kwargs):
        api = Api(Store(self.store.data_dir))
        return api.dispatch('execute_cmd', (ticket, COMMAND, {'action': action, 'log_exception': False, **kwargs}))['info']

    def race(self, calls):
        gate = threading.Barrier(len(calls))
        def perform(call):
            gate.wait(timeout=10)
            try:
                return call()
            except ValueError as exc:
                return exc
        with ThreadPoolExecutor(max_workers=len(calls)) as pool:
            return list(pool.map(perform, calls))

    def writer(self):
        from pyasm.biz.file_project import TABLES
        from pyasm.security.authenticator import hash_password
        grants = ''.join('<rule group="search_type" code="file_project/%s" project="files" access="allow"/>' % kind for kind in TABLES)
        rules = '<rules><rule group="project" code="files" access="allow"/>' + grants + '<rule group="file_depot" code="main" project="files" access="allow"/></rules>'
        admin = {'ticket': self.token, 'project': 'admin'}
        self.api.dispatch('insert', (admin, 'sthpw/login', {'code': 'artist', 'login': 'artist', 'password': hash_password('artist-test-password')}))
        self.api.dispatch('insert', (admin, 'sthpw/login_group', {'code': 'artists', 'login_group': 'artists', 'access_rules': rules}))
        self.api.dispatch('insert', (admin, 'sthpw/login_in_group', {'code': 'artist-group', 'login': 'artist', 'login_group': 'artists'}))
        ticket = {'ticket': self.api.get_ticket('artist', 'artist-test-password'), 'project': 'files'}
        self.client(ticket, 'create_workspace', code='artist', stream='main', local_root='D:/artist')
        return ticket

    def test_two_users_checkout_and_submit_races(self):
        baseline=self.change()
        blob=self.upload(baseline)
        self.call('edit',change=baseline,edit_revision=0,chunk='baseline',operations=[
            {'path':path,'blob':blob} for path in ('exclusive.bin','shared.bin')])
        self.call('submit',change=baseline)
        artist = self.writer()
        first = self.change()
        second = self.client(artist, 'create_change', workspace='artist')['code']
        calls = [lambda: self.client(self.ticket, 'checkout', change=first, paths=['exclusive.bin'], mode='exclusive'),
                 lambda: self.client(artist, 'checkout', change=second, paths=['exclusive.bin'], mode='exclusive')]
        result = self.race(calls)
        self.assertEqual(sum(isinstance(item, dict) for item in result), 1, result)
        self.assertEqual(sum(isinstance(item, ValueError) and 'Exclusive checkout' in str(item) for item in result), 1, result)
        # Ordinary checkout permits both users, even on the same logical file.
        result = self.race([lambda: self.client(self.ticket, 'checkout', change=first, paths=['shared.bin']),
                            lambda: self.client(artist, 'checkout', change=second, paths=['shared.bin'])])
        self.assertTrue(all(isinstance(item, dict) for item in result), result)
        result = self.race([lambda: self.client(self.ticket, 'submit', change=first),
                            lambda: self.client(artist, 'submit', change=second)])
        self.assertEqual(sum(isinstance(item, dict) for item in result), 1, result)
        self.assertEqual(sum(isinstance(item, ValueError) and 'head changed' in str(item) for item in result), 1, result)

    def test_parallel_retries_do_not_duplicate_upload_edit_or_sync_ack(self):
        change = self.change()
        args = dict(change=change, request_id='one', files=[{'path': 'a.bin', 'size': 3}])
        result = self.race([lambda: self.client(self.ticket, 'upload_begin', **args)] * 4)
        self.assertTrue(all(item == result[0] for item in result), result)
        blob = result[0]['items'][0]['blob']
        args = dict(change=change, blob=blob, offset=0, data='YWJj')
        result = self.race([lambda: self.client(self.ticket, 'upload_chunk', **args)] * 4)
        self.assertTrue(all(item == result[0] for item in result), result)
        self.call('upload_finish', change=change, blob=blob)
        args = dict(change=change, chunk='one', edit_revision=0, operations=[{'path': 'a.bin', 'blob': blob}])
        result = self.race([lambda: self.client(self.ticket, 'edit', **args)] * 4)
        self.assertTrue(all(item == result[0] for item in result), result)
        self.call('submit', change=change)
        job = self.call('sync_begin', workspace='work')['code']
        args = dict(sync=job, ack_revision=0, paths=['a.bin'])
        result = self.race([lambda: self.client(self.ticket, 'sync_ack', **args)] * 4)
        self.assertTrue(all(item == result[0] for item in result), result)
        self.assertEqual(self.call('sync_status', sync=job)['files_done'], 1)
        self.assertEqual(len(self.call('history', stream='main', path='a.bin')['items']), 1)

    def test_partial_file_and_metadata_failure_keeps_committed_prefix(self):
        change = self.change()
        blob = self.call('upload_begin', change=change, size=6)['code']
        self.call('upload_chunk', change=change, blob=blob, offset=0, data='YWJj')
        path = blob_file_path('files', blob, self.store.data_dir)
        # A worker died after writing/fsync but before committing the offset.
        with path.open('ab') as stream:
            stream.write(b'UNCOMMITTED-TAIL')
        original = FileProjectRecord._call_triggers
        def fail(record, *args, **kwargs):
            if record.get_base_search_type() == 'file_project/blob' and record.get_json_value('data')['received'] == 6:
                raise ValueError('injected upload failure')
            return original(record, *args, **kwargs)
        with patch.object(FileProjectRecord, '_call_triggers', fail), self.assertRaisesRegex(ValueError, 'injected upload failure'):
            self.call('upload_chunk', change=change, blob=blob, offset=3, data='ZGVm')
        self.assertEqual(path.read_bytes(), b'abc')
        self.assertEqual(self.call('uploads', change=change)['items'][0]['received'], 3)
        self.api = Api(Store(self.store.data_dir))
        self.call('upload_chunk', change=change, blob=blob, offset=3, data='ZGVm')
        self.call('upload_finish', change=change, blob=blob)
        self.assertEqual(path.read_bytes(), b'abcdef')

    def test_missing_committed_bytes_cannot_be_replaced_with_zero_padding(self):
        change = self.change()
        blob = self.call('upload_begin', change=change, size=6)['code']
        self.call('upload_chunk', change=change, blob=blob, offset=0, data='YWJj')
        path = blob_file_path('files', blob, self.store.data_dir)
        path.write_bytes(b'a')
        with self.assertRaisesRegex(ValueError, 'prefix is missing or truncated'):
            self.call('upload_chunk', change=change, blob=blob, offset=3, data='ZGVm')
        self.assertEqual(path.read_bytes(), b'a')
        self.assertEqual(self.call('uploads', change=change)['items'][0]['received'], 3)

    def test_file_rollback_runs_before_releasing_database_locks(self):
        from tactic.command.file_project_cmd import UploadUndo
        from pyasm.search.transaction import Transaction
        change = self.change()
        blob = self.call('upload_begin', change=change, size=3)['code']
        original_rollback = UploadUndo.rollback
        def check(undo):
            project = Transaction.get().get_databases()['files']
            self.assertGreater(project.transaction_count, 0, 'A retry must not obtain the DB lock before private-file rollback')
            if project.vendor == 'Sqlite':
                self.assertTrue(project.conn.in_transaction)
            return original_rollback(undo)
        original = FileProjectRecord._call_triggers
        def fail(record, *args, **kwargs):
            if record.get_base_search_type() == 'file_project/blob':
                raise ValueError('injected rollback')
            return original(record, *args, **kwargs)
        with patch.object(UploadUndo, 'rollback', check), patch.object(FileProjectRecord, '_call_triggers', fail):
            with self.assertRaisesRegex(ValueError, 'injected rollback'):
                self.call('upload_chunk', change=change, blob=blob, offset=0, data='YWJj')
        self.assertFalse(blob_file_path('files', blob, self.store.data_dir).exists())

    def kill_request(self, action, after_commit=False, **kwargs):
        script = Path(__file__).parent / 'scripts' / 'file_project_crash.py'
        payload = {'directory': str(self.store.data_dir), 'ticket': self.ticket,
                   'kwargs': {'action': action, 'log_exception': False, **kwargs}, 'after_commit': after_commit}
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(script)],
                                input=json.dumps(payload), capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 74 if after_commit else 73, result.stderr)
        self.api = Api(Store(self.store.data_dir))

    def test_process_death_before_commit_and_lost_submit_response(self):
        change = self.change()
        blob = self.call('upload_begin', change=change, size=6)['code']
        self.call('upload_chunk', change=change, blob=blob, offset=0, data='YWJj')
        self.kill_request('upload_chunk', change=change, blob=blob, offset=3, data='ZGVm')
        self.assertEqual(self.call('uploads', change=change)['items'][0]['received'], 3)
        self.call('upload_chunk', change=change, blob=blob, offset=3, data='ZGVm')
        self.call('upload_finish', change=change, blob=blob)
        args = dict(change=change, chunk='one', edit_revision=0,
                    operations=[{'path': 'a.bin', 'blob': blob}])
        self.kill_request('edit', **args)
        self.assertEqual(self.call('status', change=change)['edit_revision'], 0)
        self.assertEqual(self.call('list', change=change)['files'], 0)
        self.call('edit', **args)
        self.kill_request('submit', change=change)
        self.assertEqual(self.call('status', change=change)['state'], 'pending')
        self.assertEqual(self.call('list', stream='main')['files'], 0)
        self.kill_request('submit', after_commit=True, change=change)
        self.assertEqual(self.call('submit', change=change)['revision'], 1)
        self.assertEqual(self.call('list', stream='main')['files'], 1)
        self.assertEqual(len(self.call('history', stream='main', path='a.bin')['items']), 1)

    def test_two_workspaces_can_create_the_same_immutable_page(self):
        if self.store.get_db_resource().get_vendor() != 'PostgreSQL':
            self.skipTest('SQLite serializes project writers; PostgreSQL permits this race')
        change = self.change()
        blob = self.upload(change)
        self.call('edit', change=change, chunk='one', edit_revision=0,
                  operations=[{'path': path, 'blob': blob} for path in ('a.bin', 'b.bin')])
        self.call('submit', change=change)
        self.api.dispatch('insert', (self.ticket, 'config/trigger', {'code': 'page-probe',
            'event': 'insert|file_project/page', 'class_name': 'test_file_project_resilience.PageProbe',
            'mode': 'same process,same transaction'}))
        PageProbe.codes = []
        self.call('create_workspace', code='work2', stream='main', local_root='D:/work2')
        jobs = [self.call('sync_begin', workspace=workspace, prefix='a.bin')['code'] for workspace in ('work', 'work2')]
        # Storage/GC fencing serializes metadata writes; synchronize clients before acquiring it.
        result = self.race([lambda job=job: self.client(self.ticket, 'sync_ack', sync=job,
                            ack_revision=0, paths=['a.bin']) for job in jobs])
        self.assertTrue(all(item['state'] == 'complete' for item in result), result)
        for workspace in ('work', 'work2'):
            self.assertEqual(len(self.call('have', workspace=workspace)['items']), 1)
        self.assertEqual(len(PageProbe.codes), 1, 'A reused page must not fire another insert trigger')

    def test_late_native_trigger_and_database_commit_failure_roll_back_whole_change(self):
        from pyasm.biz.file_project import access
        from pyasm.search import Search
        from pyasm.search.search import RequestContext, request_context
        from pyasm.search.sql import Sql
        change = self.change()
        blob = self.upload(change)
        def counts():
            with request_context(RequestContext(self.store, 'admin', 'files')):
                self.api.auth.bind_security('admin', self.token)
                with access('files'):
                    return {kind: Search('file_project/' + kind).get_count() for kind in ('page', 'version', 'checkout', 'chunk')}
        initial = counts()
        trigger = self.api.dispatch('insert', (self.ticket, 'config/trigger', {'code': 'late-failure',
            'event': 'update|file_project/change', 'class_name': 'test_file_project_resilience.EditFailure',
            'mode': 'same process,same transaction'}))
        args = dict(change=change, chunk='one', edit_revision=0,
                    operations=[{'path': '%04d.bin' % index, 'blob': blob} for index in range(1000)])
        with self.assertRaisesRegex(ValueError, 'late edit trigger failure'):
            self.call('edit', **args)
        self.assertEqual(counts(), initial)
        self.assertEqual(self.call('status', change=change)['edit_revision'], 0)
        self.api.dispatch('delete_sobject', (self.ticket, trigger['__search_key__']))
        self.call('edit', **args)
        original = Sql.commit
        def commit(sql):
            if sql.get_database_name() == 'files':
                raise OSError('injected database commit failure')
            return original(sql)
        with patch.object(Sql, 'commit', commit), self.assertRaisesRegex(OSError, 'database commit failure'):
            self.call('submit', change=change)
        self.assertEqual(self.call('list', stream='main')['files'], 0)
        self.assertEqual(self.call('status', change=change)['state'], 'pending')
        self.assertEqual(self.call('uploads', change=change)['items'][0]['state'], 'ready')
        self.call('submit', change=change)
        self.assertEqual(self.call('list', stream='main')['files'], 1000)

    def test_postgres_wait_for_busy_changelist_is_bounded(self):
        if self.store.get_db_resource().get_vendor() != 'PostgreSQL':
            self.skipTest('PostgreSQL row lock wait contract')
        from pyasm.biz.file_project import access, find
        from pyasm.command import Command
        from pyasm.search.search import RequestContext, request_context
        from pyasm.search.transaction import Transaction
        from pyasm.search.sql import Sql
        from pyasm.biz import Project
        from time import perf_counter
        locked, release = threading.Event(), threading.Event()
        change = self.change()
        def hold():
            with request_context(RequestContext(self.store, 'admin', 'files')):
                self.api.auth.bind_security('admin', self.token)
                command = Command(log_exception=False)
                def execute():
                    with access('files'):
                        Transaction.get().require_single_database(Project.get().get_project_db_resource())
                        item = find('change', change)
                        item.get_sql().lock_sobject(item)
                        locked.set()
                        self.assertTrue(release.wait(15))
                command.execute = execute
                Command.execute_cmd(command)
        original = Sql.lock_sobject
        def short_wait(sql, item, timeout=None):
            return original(sql, item, timeout=100)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(hold)
            try:
                self.assertTrue(locked.wait(10))
                started = perf_counter()
                with patch.object(Sql, 'lock_sobject', short_wait), self.assertRaisesRegex(Exception, 'lock timeout'):
                    self.client(self.ticket, 'upload_begin', change=change, size=3)
                self.assertLess(perf_counter() - started, 3)
            finally:
                release.set()
                future.result(timeout=10)
        self.assertEqual(self.call('uploads', change=change)['items'], [])

    def test_atomic_resource_ownership_is_checked_once_without_skipping_row_acl(self):
        from contextlib import contextmanager
        from pyasm.search.sql import DbResource
        from pyasm.search.search import RequestContext, request_context
        from pyasm.search.transaction import Transaction, TransactionException
        from pyasm.command import Command
        change = self.change()
        blob = self.upload(change)
        queries = []
        original = Store.connection
        class Probe:
            def __init__(probe, database):
                probe.database = database
            def execute(probe, statement, *args, **kwargs):
                if statement.startswith('SELECT 1 FROM project WHERE COALESCE'):
                    queries.append(statement)
                return probe.database.execute(statement, *args, **kwargs)
            def __getattr__(probe, name):
                return getattr(probe.database, name)
        @contextmanager
        def connection(store, *args, **kwargs):
            with original(store, *args, **kwargs) as db:
                yield Probe(db)
        with patch.object(Store, 'connection', connection):
            self.call('edit', change=change, chunk='one', edit_revision=0,
                      operations=[{'path': '%04d.bin' % index, 'blob': blob} for index in range(1000)])
        self.assertEqual(len(queries), 1)
        with request_context(RequestContext(self.store, 'admin', 'files')):
            self.api.auth.bind_security('admin', self.token)
            command = Command(log_exception=False)
            command.execute = lambda: Transaction.get().require_single_database(DbResource.get_default('not_registered'))
            with self.assertRaisesRegex(TransactionException, 'registered database'):
                Command.execute_cmd(command)
        # Existing ordinary-user/column/cross-database cases exercise the remaining ACLs.

    def test_reopening_checkout_keeps_native_callback_sequence(self):
        first = self.change()
        paths = ['a.bin', 'b.bin', 'c.bin']
        self.call('checkout', change=first, paths=paths)
        blob=self.upload(first)
        self.call('edit',change=first,edit_revision=1,chunk='initial-files',operations=[{'path':path,'blob':blob} for path in paths])
        self.call('submit', change=first)
        change = self.change()
        self.api.dispatch('insert', (self.ticket, 'config/trigger', {'code': 'checkout-probe',
            'event': 'update|file_project/checkout', 'class_name': 'test_file_project_resilience.CheckoutProbe',
            'mode': 'same process,same transaction'}))
        CheckoutProbe.counts = []
        self.call('checkout', change=change, paths=paths)
        self.assertEqual(CheckoutProbe.counts, [1, 2, 3])

    def test_upload_commit_error_preserves_bytes_when_commit_outcome_is_unknown(self):
        from pyasm.search.sql import Sql
        change = self.change()
        original = Sql.commit
        for committed in (False, True):
            blob = self.call('upload_begin', change=change, size=3)['code']
            def commit(sql):
                if sql.get_database_name() == 'files':
                    if committed:
                        original(sql)
                    raise OSError('lost COMMIT response')
                return original(sql)
            with patch.object(Sql, 'commit', commit), self.assertRaisesRegex(OSError, 'lost COMMIT response'):
                self.call('upload_chunk', change=change, blob=blob, offset=0, data='YWJj')
            self.api = Api(Store(self.store.data_dir))
            path = blob_file_path('files', blob, self.store.data_dir)
            self.assertTrue(path.exists(), 'An uncertain commit must not delete bytes possibly referenced by committed metadata')
            self.assertEqual(path.read_bytes(), b'abc')
            row = next(item for item in self.call('uploads', change=change)['items'] if item['code'] == blob)
            self.assertEqual(row['received'], 3 if committed else 0)
            self.call('upload_chunk', change=change, blob=blob, offset=0, data='YWJj')
            self.call('upload_finish', change=change, blob=blob)

    def test_classic_client_transaction_cannot_publish_unjournaled_file_changes(self):
        from pyasm.search.transaction import TransactionException
        token = self.api.dispatch('start', (self.ticket, 'files', 'Classic journal'))
        ticket = {'ticket': token, 'project': 'files'}
        try:
            with self.assertRaisesRegex(TransactionException, 'clean transaction journal'):
                self.client(ticket, 'create_change', workspace='work')
        finally:
            self.api.dispatch('abort', (ticket,))
        self.assertFalse(any(item['workspace'] == 'work' for item in self.call('changes')['items']))
