"""Crash outcomes, native read bounds and Windows publication collisions."""
from contextlib import closing
import ast
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_foundation import fixture
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import FileUndo, Search, SearchType, Transaction
from pyasm.search.file_recovery import recover_files
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.search.transaction import PartialCommitException
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api


class EngineFixes(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name))
        self.store.initialize(hash_password('private-engine-test'))
        fixture(self.store)
        self.api = Api(self.store)
        self.token = self.api.get_ticket('admin', 'private-engine-test')

    def context(self):
        return request_context(RequestContext(self.store, 'admin', 'admin'))

    def crash(self, point):
        source = '''
import os,sys
from pathlib import Path
from pyasm.search.storage import Store
from tactic_stream.server.api import Api
from pyasm.search.search import RequestContext,request_context
from pyasm.search import FileUndo,SearchType,Search,Sql,Transaction
from pyasm.command import Command
from pyasm.common import Environment
store=Store(Path(sys.argv[1])); api=Api(store); token=sys.argv[2]; point=sys.argv[3]
with request_context(RequestContext(store,'admin','one')):
    api.auth.bind_security('admin',token)
    path=Path(Environment.get_asset_dir())/'existing.txt'
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text('original')
    (store.data_dir/'asset-path.txt').write_text(str(path))
    original=Sql.commit
    def commit(self):
        if point=='before_commit':os._exit(73)
        original(self)
        if point=='after_commit' and self.get_database_name()=='sthpw' or point=='partial' and self.get_database_name()=='one':os._exit(73)
    Sql.commit=commit
    cmd=Command(log_exception=False)
    def execute():
        Transaction.get().set_sync(False)
        if point=='partial':
            row=Search.get_by_code('contract/entity','A');row.set_value('amount',17);row.commit()
        row=SearchType.create('sthpw/note');row.set_value('code','CRASH');row.set_value('note','persisted');row.commit()
        if point=='before_io':
            FileUndo._add_to_transaction_log('remove',str(path),str(store.data_dir/'backup.txt'))
            os._exit(73)
        FileUndo.remove(str(path))
        if point=='after_io':os._exit(73)
    cmd.execute=execute;Command.execute_cmd(cmd)
'''
        result = subprocess.run([sys.executable, '-B', '-c', source, str(self.store.data_dir), self.token, point],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 73, result.stderr)
        return Path((self.store.data_dir / 'asset-path.txt').read_text())

    def test_crash_before_and_after_file_and_before_commit_restores_original(self):
        for point in ('before_io', 'after_io', 'before_commit'):
            with self.subTest(point=point):
                path = self.crash(point)
                with self.context():
                    self.api.auth.bind_security('admin', self.token)
                    recover_files(self.store)
                    recover_files(self.store)
                    self.assertIsNone(Search.get_by_code('sthpw/note', 'CRASH'))
                self.assertEqual(path.read_text(), 'original')

    def test_crash_after_commit_retains_committed_files(self):
        path = self.crash('after_commit')
        with self.context():
            recover_files(self.store)
            self.api.auth.bind_security('admin', self.token)
            self.assertIsNotNone(Search.get_by_code('sthpw/note', 'CRASH'))
        self.assertFalse(path.exists())

    def test_partial_commit_preserves_files_and_blocks_automatic_rollback(self):
        path = self.crash('partial')
        with self.context():
            with self.assertRaises(PartialCommitException):
                recover_files(self.store)
        self.assertFalse(path.exists())
        self.assertEqual(len(list((self.store.data_dir / 'temp/file-transactions').glob('*.jsonl'))), 1)

    def test_no_journal_file_only_commit_has_recoverable_evidence(self):
        with self.context():
            self.api.auth.bind_security('admin', self.token)
            path = Path(Environment.get_asset_dir()) / 'file-only.txt'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('old')
            cmd = Command(log_exception=False)
            def execute():
                Transaction.get().set_sync(False)
                Transaction.get().set_record(False)
                FileUndo.remove(str(path))
            cmd.execute = execute
            Command.execute_cmd(cmd)
            self.assertFalse(path.exists())
        self.assertFalse(list((self.store.data_dir / 'temp/file-transactions').glob('*.jsonl')))

    def test_single_and_columns_are_applied_before_row_materialisation(self):
        with closing(sqlite3.connect(str(self.store.database_path('one')))) as db, db:
            db.execute('DELETE FROM entity')
            db.executemany('INSERT INTO entity(id,code,name) VALUES(?,?,?)', ((i, str(i), 'x' * 32768) for i in range(1, 501)))
        original = Search.get_sobjects
        rows = []
        def get(search, *args, **kwargs):
            result = original(search, *args, **kwargs)
            if search.get_base_search_type() == 'contract/entity':
                rows.extend(result)
            return result
        with patch.object(Search, 'get_sobjects', get):
            result = self.api.dispatch('query', ({'ticket': self.token, 'project': 'one'}, 'contract/entity'),
                                       dict(single=True, columns=['code'], order_bys=['id'], offset=4))
        result = ast.literal_eval(result) if isinstance(result, str) else result
        self.assertEqual(result['code'], '5')
        self.assertEqual(len(rows), 1)
        self.assertNotIn('name', rows[0].data)

    def test_account_cache_is_invalidated_when_current_account_is_retired(self):
        from pyasm.security import Login
        from pyasm.common.errors import SecurityException
        auth = {'ticket': self.token, 'project': 'admin'}
        self.api.dispatch('insert', (auth, 'sthpw/login', {'login': 'file_admin', 'password': hash_password('private-file-admin')}))
        self.api.dispatch('insert', (auth, 'sthpw/login_in_group', {'login': 'file_admin', 'login_group': 'admin'}))
        token = self.api.get_ticket('file_admin', 'private-file-admin')
        with request_context(RequestContext(self.store, 'file_admin', 'admin')):
            self.api.auth.bind_security('file_admin', token)
            root = Path(Environment.get_asset_dir())
            root.mkdir(parents=True, exist_ok=True)
            source = root / 'cache-source.txt'
            source.write_text('unchanged')
            command = Command(log_exception=False)
            def execute():
                Transaction.get().set_sync(False)
                FileUndo.copy(str(source), str(root / 'first-copy.txt'))
                login = Login.get_by_login('file_admin')
                login.set_value('s_status', 'retired')
                login.commit()
                with self.assertRaises(SecurityException):
                    FileUndo.copy(str(source), str(root / 'forbidden-copy.txt'))
                raise ValueError('rollback account retirement')
            command.execute = execute
            with self.assertRaisesRegex(ValueError, 'rollback account retirement'):
                Command.execute_cmd(command)
            self.assertFalse((root / 'first-copy.txt').exists())
            self.assertFalse((root / 'forbidden-copy.txt').exists())

    def test_interrupted_rollback_does_not_undo_an_already_restored_overwrite(self):
        with self.context():
            self.api.auth.bind_security('admin', self.token)
            root = Path(Environment.get_asset_dir())
            root.mkdir(parents=True, exist_ok=True)
            source, destination = root / 'new.txt', root / 'old.txt'
            source.write_text('new')
            destination.write_text('old')
            transaction = Transaction.get(create=True)
            transaction.set_sync(False)
            FileUndo.copy(str(source), str(destination))
            journal = transaction.file_journal
            original = journal.close
            with patch.object(journal, 'close', side_effect=lambda **kwargs: original(resolved=False)):
                transaction.rollback()
            recover_files(self.store)
            self.assertEqual(destination.read_text(), 'old')

    def test_lost_commit_acknowledgement_preserves_committed_file_effects(self):
        from pyasm.search import Sql
        with self.context():
            self.api.auth.bind_security('admin', self.token)
            root = Path(Environment.get_asset_dir())
            root.mkdir(parents=True, exist_ok=True)
            source, destination = root / 'ack-source.txt', root / 'ack-destination.txt'
            source.write_text('committed')
            original = Sql.commit
            def commit(sql):
                original(sql)
                if sql.get_database_name() == 'sthpw':
                    raise OSError('lost commit acknowledgement')
            command = Command(log_exception=False)
            def execute():
                Transaction.get().set_sync(False)
                FileUndo.copy(str(source), str(destination))
            command.execute = execute
            with patch.object(Sql, 'commit', commit), self.assertRaises(PartialCommitException):
                Command.execute_cmd(command)
            self.assertEqual(destination.read_text(), 'committed')
        with self.context():
            recover_files(self.store)
        self.assertEqual(destination.read_text(), 'committed')

    @unittest.skipUnless(os.name == 'nt', 'Windows file sharing')
    def test_locked_publication_is_durable_and_collector_retries_feed(self):
        from pyasm.search.update_events import publish_changes
        from tactic_stream.server.update_collector import UpdateCollector
        from pyasm.common.file_io import read_text
        publish_changes(self.store.data_dir, [('one', 'contract/entity')])
        directory = self.store.data_dir / 'cache/update-events'
        path = next(directory.glob('*.json'))
        with path.open('rb'):
            publish_changes(self.store.data_dir, [('one', 'contract/entity')])
            self.assertEqual(len(list(directory.glob('*.pending'))), 1)
            collector = UpdateCollector(self.store.data_dir)
            collector.tick()
            newest = json.loads(read_text(collector.feed))[0][3]
        collector.tick()
        self.assertFalse(list(directory.glob('*.pending')))
        self.assertEqual(json.loads(read_text(path))[2], newest)
        publish_changes(self.store.data_dir, [('one', 'contract/entity')])
        with collector.feed.open('rb'):
            collector.tick()
            self.assertTrue(collector.dirty)
        collector.tick()
        self.assertFalse(collector.dirty)
        self.assertNotEqual(json.loads(read_text(collector.feed))[0][3], newest)
