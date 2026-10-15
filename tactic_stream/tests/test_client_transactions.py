import tempfile
import unittest
from pathlib import Path

import test_read_parity as read_tests
from pyasm.common import Xml
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from tactic_stream.server.api import Api
from pyasm.common.errors import SecurityException


def exercise_client_transactions(store, password):
    api = Api(store)
    login = api.get_ticket('admin', password)
    ticket = dict(ticket=login, project='admin')
    key = api.dispatch('start', (ticket, 'admin', 'Grouped edits', 'Original client lifecycle'))
    transaction = dict(ticket=key, project='admin')
    first = api.dispatch('insert', (transaction, 'sthpw/note', dict(code='SESSION_A', note='before')))
    second = api.dispatch('insert', (transaction, 'sthpw/note', dict(code='SESSION_B', note='second')))
    api.dispatch('update', (transaction, first['__search_key__'], dict(note='after')))
    api.dispatch('set_state', (transaction, 'value', 'first'))
    api.dispatch('set_state', (transaction, 'value', 'second & <value>'))
    with store.connection() as db:
        rows = db.execute('SELECT * FROM transaction_log').fetchall()
        assert len(rows) == 1, len(rows)
        log_id = rows[0]['id']
        xml = Xml(rows[0]['transaction'])
        assert [node.get('action') for node in xml.get_nodes('transaction/sobject')] == ['insert', 'insert', 'update']
        state = db.execute('SELECT data FROM transaction_state WHERE ticket=' +
            store.get_db_resource().get_database_impl().get_parameter(), (key,)).fetchone()['data']
        assert Xml(state).get_value('state/value') == 'second & <value>'
    assert api.dispatch('finish', (transaction, 'Two notes saved')) is True
    assert api.dispatch('finish', (transaction,)) is True
    assert api.dispatch('undo', (ticket, None, log_id)) is True
    assert api.dispatch('get_by_code', (ticket, 'sthpw/note', first['code'])) == {}
    assert api.dispatch('get_by_code', (ticket, 'sthpw/note', second['code'])) == {}
    assert api.dispatch('redo', (ticket, None, log_id)) is True
    assert api.dispatch('get_by_code', (ticket, 'sthpw/note', first['code']))['note'] == 'after'
    aborted_key = api.dispatch('start', (ticket, 'admin', 'Aborted edits'))
    aborted = dict(ticket=aborted_key, project='admin')
    api.dispatch('insert', (aborted, 'sthpw/note', dict(code='SESSION_ABORT', note='temporary')))
    assert api.dispatch('abort', (aborted,)) is True
    assert api.dispatch('get_by_code', (ticket, 'sthpw/note', 'SESSION_ABORT')) == {}
    empty_key = api.dispatch('start', (ticket, 'admin', 'Empty edits'))
    assert api.dispatch('finish', (dict(ticket=empty_key, project='admin'),)) is True
    with store.connection() as db:
        assert not any(Xml(row['transaction']).get_nodes('transaction/*') == []
            for row in db.execute('SELECT "transaction" FROM transaction_log'))
    from xmlrpc.client import Binary
    file_key = api.dispatch('start', (ticket, 'admin', 'Aborted upload'))
    file_ticket = dict(ticket=file_key, project='admin')
    api.dispatch('upload_file', (file_ticket, 'session-file.bin', Binary(b'private upload bytes')))
    assert api.dispatch('get_upload_file_size', (file_ticket, 'session-file.bin')) == 20
    assert api.dispatch('abort', (file_ticket,)) is True
    assert api.dispatch('get_upload_file_size', (file_ticket, 'session-file.bin')) == 0
    return True


def exercise_client_transaction_failures(store, password):
    from ast import literal_eval
    from concurrent.futures import ThreadPoolExecutor
    from pyasm.common import Common
    from pyasm.search import SqlException
    api = Api(store)
    login = dict(ticket=api.get_ticket('admin', password), project='admin')
    key = api.dispatch('start', (login, 'admin', 'Concurrent edits'))
    ticket = dict(ticket=key, project='admin')
    with ThreadPoolExecutor(max_workers=4) as pool:
        notes = list(pool.map(lambda n: api.dispatch('insert', (ticket, 'sthpw/note',
            dict(code='SESSION_CONCURRENT_%02d' % n, note='concurrent & <value>' * 100))), range(12)))
    with store.connection() as db:
        marker = store.get_db_resource().get_database_impl().get_parameter()
        state = db.execute('SELECT data FROM transaction_state WHERE ticket=' + marker, (key,)).fetchone()['data']
        log_id = int(Xml(state).get_value('state/transaction'))
        data = db.execute('SELECT "transaction" FROM transaction_log WHERE id=' + marker, (log_id,)).fetchone()['transaction']
        assert data.startswith('zlib:'), 'Large appended journals must remain compressed'
        nodes = Xml(Common.decompress_transaction(data)).get_nodes('transaction/sobject')
        assert len(nodes) == len(notes), (len(nodes), len(notes))
        assert len({node.get('search_code') for node in nodes}) == len(notes)
    try:
        api.dispatch('start', (login, 'admin', 'Must not reset', None, key))
        raise AssertionError('Starting an active ticket must fail')
    except ValueError as error:
        assert 'already active' in str(error)
    try:
        api.dispatch('set_state', (ticket, '../transaction', 'invalid'))
        raise AssertionError('Invalid state names must fail')
    except ValueError:
        pass
    try:
        api.dispatch('insert', (ticket, 'sthpw/note', dict(code='SESSION_BAD', missing_column='invalid')))
        raise AssertionError('Invalid writes must fail')
    except SqlException:
        pass
    found = literal_eval(api.dispatch('query', (key, 'sthpw/note', [('code', 'in', '|'.join(note['code'] for note in notes))])))
    assert len(found) == len(notes), (len(found), len(notes))
    assert api.dispatch('finish', (ticket,)) is True
    assert api.dispatch('undo', (login, None, log_id)) is True
    assert api.dispatch('redo', (login, None, log_id)) is True
    assert api.dispatch('get_by_code', (login, 'sthpw/note', notes[0]['code']))['note'] == notes[0]['note']
    reader = api.dispatch('insert', (login, 'sthpw/login', dict(login='session_reader', password=hash_password(password))))
    reader_ticket = dict(ticket=api.get_ticket('session_reader', password), project='admin')
    try:
        api.dispatch('start', (reader_ticket, 'admin', 'Denied'))
        raise AssertionError('Reader writes must fail')
    except SecurityException:
        pass
    api.dispatch('delete_sobject', (login, reader['__search_key__']))
    saved_ticket = literal_eval(api.dispatch('query', (login, 'sthpw/ticket', [('ticket', key)])))[0]
    api.dispatch('update', (login, saved_ticket['__search_key__'], dict(expiry='2000-01-01')))
    try:
        api.dispatch('start', (login, 'admin', 'Expired', None, key))
        raise AssertionError('Expired tickets must not be reused')
    except SecurityException:
        pass
    return True


class ClientTransactions(unittest.TestCase):
    def test_grouped_commands_finish_abort_and_state(self):
        import subprocess
        import sys
        subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c',
            'from tactic_stream.__main__ import main; from pyasm.search import TransactionState'],
            check=True, capture_output=True, timeout=10)
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('private-session-password'))
            self.assertTrue(exercise_client_transactions(store, 'private-session-password'))
            self.assertTrue(exercise_client_transaction_failures(store, 'private-session-password'))

    def test_file_replay_restores_completed_and_partial_io_after_failure(self):
        from unittest.mock import patch
        from pyasm.command import Command
        from pyasm.search import FileUndo, Search, SearchType, TransactionLog
        from pyasm.search.search import RequestContext, request_context, SObjectUndo
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('private-session-password'))
            api = Api(store)
            token = api.get_ticket('admin', 'private-session-password')
            ticket = dict(ticket=token, project='admin')
            source, target = Path(directory) / 'source.bin', Path(directory) / 'target.bin'
            source.write_bytes(b'original bytes')
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', token)
                command = Command()
                command.get_transaction().set_sync(False)
                def execute():
                    FileUndo.copy(str(source), str(target))
                    note = SearchType.create('sthpw/note')
                    note.set_value('code', 'FILE_REPLAY_NOTE')
                    note.commit()
                command.execute = execute
                Command.execute_cmd(command)
                log_id = TransactionLog.get_last('undo').get_id()
            api.dispatch('undo', (ticket, None, log_id))
            source.write_bytes(b'changed source')
            with patch.object(SObjectUndo, 'redo', side_effect=ValueError('late replay failure')):
                with self.assertRaisesRegex(ValueError, 'late replay failure'):
                    api.dispatch('redo', (ticket, None, log_id))
            self.assertFalse(target.exists())
            self.assertEqual(api.dispatch('get_by_code', (ticket, 'sthpw/note', 'FILE_REPLAY_NOTE')), {})
            api.dispatch('redo', (ticket, None, log_id))
            self.assertEqual(target.read_bytes(), b'original bytes')
            second_target = Path(directory) / 'second.bin'
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', token)
                command = Command()
                command.get_transaction().set_sync(False)
                def update_and_copy():
                    note = Search.get_by_code('sthpw/note', 'FILE_REPLAY_NOTE')
                    note.set_value('note', 'updated')
                    note.commit()
                    FileUndo.copy(str(source), str(second_target))
                command.execute = update_and_copy
                Command.execute_cmd(command)
                update_id = TransactionLog.get_last('undo').get_id()
            with patch.object(SObjectUndo, 'undo', side_effect=ValueError('late undo failure')):
                with self.assertRaisesRegex(ValueError, 'late undo failure'):
                    api.dispatch('undo', (ticket, None, update_id))
            self.assertEqual(second_target.read_bytes(), b'changed source')
            self.assertEqual(api.dispatch('get_by_code', (ticket, 'sthpw/note', 'FILE_REPLAY_NOTE'))['note'], 'updated')
            target.unlink()
            xml = Xml('<transaction/>')
            node = xml.create_element('file', node=xml.get_root_node())
            for name, value in dict(type='copy', src=str(source), dst=str(target), state='done').items():
                Xml.set_attribute(node, name, value)
            def partial_copy(src, dst):
                Path(dst).write_bytes(b'partial')
                raise OSError('interrupted copy')
            with patch('pyasm.search.transaction.shutil.copyfile', side_effect=partial_copy):
                with self.assertRaisesRegex(OSError, 'interrupted copy'):
                    api.dispatch('execute_transaction', (ticket, xml.to_string(), 'immediate'))
            self.assertFalse(target.exists())
            self.assertEqual(source.read_bytes(), b'changed source')


class TransactionStateParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='transaction_state_contract', name='state_set_reset_restore', project='admin')]

    def new_result(self, case):
        import shutil
        from tools.snapshot_probe import run_snapshot_case
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            shutil.copytree(self.store.data_dir, store.data_dir, dirs_exist_ok=True)
            with request_context(RequestContext(store, 'admin', 'admin')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        self.assertEqual(result, ['first & <value>', 'second & <value>', 1, True, 'one', ''])
        # Original appends a duplicate element and reads its outdated first value.
        self.assertEqual(original, ['first & <value>', 'first & <value>', 2, True, 'one', ''])
