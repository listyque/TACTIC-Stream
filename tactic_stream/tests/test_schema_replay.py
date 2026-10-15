"""Public API schema replay with rows, indexes, sequence floors and failed replay."""
from unittest.mock import patch

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.search import AlterTableUndo, DatabaseImpl, DbContainer, DropTable, TransactionException, TransactionLog
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.api import Api


def exercise_schema_replay(store, prefix):
    api = Api(store)
    token = api.get_ticket('admin', 'plugin-test-password')
    ticket = dict(ticket=token, project='admin')
    project = prefix + '_copy'
    api.dispatch('execute_cmd', (ticket, 'tactic.command.CreateProjectCmd',
                               dict(project_code=project, project_title='Schema replay')))
    ticket['project'] = project
    search_type = project + '/replay_object'
    api.dispatch('create_search_type', (ticket, search_type, 'Replay objects'))

    def inspect(callback):
        with request_context(RequestContext(store, 'admin', project)):
            api.auth.bind_security('admin', token)
            return callback()

    def last_id():
        return inspect(lambda: TransactionLog.get_last('undo').get_id())

    def sql():
        return DbContainer.get(Project.get().get_project_db_resource())

    def command(callback):
        def run():
            cmd = Command()
            cmd.get_transaction().set_sync(False)
            cmd.execute = callback
            return Command.execute_cmd(cmd)
        return inspect(run)

    creation = last_id()
    # Native defaults/nullability are preserved, rather than reconstructed from normalized types.
    command(lambda: sql().add_column('replay_object', 'stamp', 'timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL'))
    first = api.dispatch('insert', (ticket, search_type, dict(code='SCHEMA_ONE', description='original')))
    key = first['__search_key__']
    command(lambda: sql().do_update('CREATE INDEX replay_description_idx ON replay_object(description)'))
    api.dispatch('undo', (ticket, None, creation))
    assert not inspect(lambda: sql().get_database_impl().table_exists(sql().get_db_resource(), 'replay_object'))
    api.dispatch('redo', (ticket, None, creation))
    assert api.dispatch('get_by_code', (ticket, search_type, 'SCHEMA_ONE'))['description'] == 'original'
    assert api.dispatch('get_by_code', (ticket, search_type, 'SCHEMA_ONE'))['stamp']
    assert 'replay_description_idx' in str(inspect(lambda: sql().get_database_impl().get_table_definition(sql(), 'replay_object')))

    assert api.dispatch('add_column_to_search_type', (ticket, search_type, 'extra_value', 'integer')) is True
    addition = last_id()
    api.dispatch('update', (ticket, key, dict(extra_value=42)))
    api.dispatch('undo', (ticket, None, addition))
    assert 'extra_value' not in inspect(lambda: sql().get_column_info('replay_object'))
    # Ordinary journaled writes intentionally delete Redo history in TACTIC.
    command(lambda: sql().do_update("UPDATE replay_object SET description='edited while column absent' WHERE code='SCHEMA_ONE'"))
    api.dispatch('redo', (ticket, None, addition))
    row = api.dispatch('get_by_code', (ticket, search_type, 'SCHEMA_ONE'))
    assert row['extra_value'] == 42 and row['description'] == 'edited while column absent'

    def drop_column():
        AlterTableUndo.log_drop(sql().get_db_resource(), 'replay_object', 'extra_value')
        sql().drop_column('replay_object', 'extra_value')
    command(drop_column)
    removal = last_id()
    api.dispatch('insert', (ticket, search_type, dict(code='SCHEMA_NEW', description='new row')))
    api.dispatch('undo', (ticket, None, removal))
    assert api.dispatch('get_by_code', (ticket, search_type, 'SCHEMA_ONE'))['extra_value'] == 42
    assert api.dispatch('get_by_code', (ticket, search_type, 'SCHEMA_NEW'))['extra_value'] is None
    api.dispatch('redo', (ticket, None, removal))
    assert 'extra_value' not in inspect(lambda: sql().get_column_info('replay_object'))

    def drop_stamp():
        AlterTableUndo.log_drop(sql().get_db_resource(), 'replay_object', 'stamp')
        sql().drop_column('replay_object', 'stamp')
    original_stamp = api.dispatch('get_by_code', (ticket, search_type, 'SCHEMA_ONE'))['stamp']
    command(drop_stamp)
    stamp_removal = last_id()
    api.dispatch('insert', (ticket, search_type, dict(code='SCHEMA_DEFAULT')))
    command(lambda: sql().add_column('replay_object', 'unexpected', 'integer'))
    try:
        api.dispatch('undo', (ticket, None, stamp_removal))
    except TransactionException as error:
        assert 'schema changed' in str(error)
    else:
        raise AssertionError('Changed schema must refuse restoration')
    assert 'unexpected' in inspect(lambda: sql().get_column_info('replay_object'))
    assert api.dispatch('get_by_code', (ticket, search_type, 'SCHEMA_DEFAULT'))['code'] == 'SCHEMA_DEFAULT'
    command(lambda: sql().drop_column('replay_object', 'unexpected'))
    api.dispatch('undo', (ticket, None, stamp_removal))
    assert api.dispatch('get_by_code', (ticket, search_type, 'SCHEMA_ONE'))['stamp'] == original_stamp
    assert api.dispatch('get_by_code', (ticket, search_type, 'SCHEMA_DEFAULT'))['stamp']

    command(lambda: sql().get_database_impl().ensure_table_sequence(sql(), 'replay_object', 5000))
    command(lambda: DropTable(search_type).commit())
    dropped = last_id()
    restore = DatabaseImpl.restore_table
    def failed_restore(*args):
        restore(*args)
        raise ValueError('late schema restore failure')
    with patch.object(DatabaseImpl, 'restore_table', side_effect=failed_restore, autospec=True):
        try:
            api.dispatch('undo', (ticket, None, dropped))
        except ValueError as error:
            assert str(error) == 'late schema restore failure'
        else:
            raise AssertionError('Failed schema replay must fail its API call')
    assert not inspect(lambda: sql().get_database_impl().table_exists(sql().get_db_resource(), 'replay_object'))
    api.dispatch('undo', (ticket, None, dropped))
    assert api.dispatch('get_by_code', (ticket, search_type, 'SCHEMA_ONE'))['description'] == 'edited while column absent'
    assert api.dispatch('get_by_code', (ticket, search_type, 'SCHEMA_NEW'))['description'] == 'new row'
    command(lambda: sql().do_update("INSERT INTO replay_object(code) VALUES('SCHEMA_NEXT')"))
    last = api.dispatch('get_by_code', (ticket, search_type, 'SCHEMA_NEXT'))
    assert last['id'] == 5001
    api.dispatch('redo', (ticket, None, dropped))
    api.dispatch('undo', (ticket, None, dropped))
    assert api.dispatch('get_by_code', (ticket, search_type, 'SCHEMA_NEXT'))['id'] == last['id']
    return True


# Original-runtime harness stays out of the Docker helper import path.
import shutil
import tempfile
from pathlib import Path
import test_read_parity as read_tests


class SchemaReplayParity(read_tests.ReadParity):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cases = [dict(method='schema_replay_contract', name='column_values', project='one'),
                     dict(method='schema_replay_contract', name='api_missing_journal', project='one', api=True)]

    def new_result(self, case):
        from tools.snapshot_probe import run_snapshot_case
        with tempfile.TemporaryDirectory() as directory:
            store = type(self.store)(Path(directory))
            shutil.copytree(self.store.data_dir, store.data_dir, dirs_exist_ok=True)
            with request_context(RequestContext(store, 'admin', 'one')):
                return run_snapshot_case(case)

    def assert_case_result(self, case, result, original):
        if case.get('api'):
            self.assertEqual(result, 1)
            self.assertEqual(original, 0)  # Source API forgot its alter journal.
        else:
            self.assertEqual(result, [True, 51])
            self.assertEqual(original, [True, None])  # Source lost removed values.
