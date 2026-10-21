"""Connection cells retain original directions and protect both endpoint objects."""
import unittest
from unittest.mock import patch

import test_table_services as fixtures
from test_table_embedded_widgets import write
from pyasm.biz import SObjectConnection
from pyasm.common import Environment, UserException
from pyasm.search import Search, SearchType
from pyasm.widget import SObjectConnectionElement
from tactic.ui.table.connections import read_connection_cells, remove_connection, TableConnectionRemoveCmd
from tactic_stream.server.table_cells import describe_cell


class TableConnections(unittest.TestCase):
    setUp = fixtures.TableServices.setUp

    def connection(self):
        self.a = Search.get_by_code('contract/entity', 'A')
        self.b = Search.get_by_code('contract/entity', 'B')
        return write(lambda: SObjectConnection.create(self.a, self.b, direction='one'))

    def rows(self, parent, direction='dst'):
        return read_connection_cells([parent.get_search_key()], direction)[parent.get_search_key()]['connectionRows']

    def test_original_incoming_outgoing_and_connection_row_directions(self):
        connection = self.connection()
        self.assertEqual(self.rows(self.a), [])
        self.assertEqual(self.rows(self.b)[0]['searchKey'], self.a.get_search_key())
        self.assertEqual(self.rows(self.a, 'src')[0]['searchKey'], self.b.get_search_key())
        self.assertEqual(self.rows(connection)[0]['searchKey'], self.b.get_search_key())
        self.assertEqual(self.rows(connection, 'src')[0]['searchKey'], self.a.get_search_key())
        self.assertEqual(self.rows(self.b)[0]['connectionKey'], connection.get_search_key())
        self.assertIn('preview', self.rows(self.b)[0])

    def test_widget_aliases_and_supported_options(self):
        self.connection()
        for handler in ('SObjectConnectionElement', 'pyasm.widget.SObjectConnectionElement',
                'pyasm.widget.sobject_browser_wdg.SObjectConnectionElement'):
            element = dict(name='connections', display=dict(handler=handler, options={}), action=dict(handler='', options={}))
            self.assertEqual(describe_cell(element, {})['kind'], 'commands')
            self.assertTrue(describe_cell(element, {})['supported'])
            for options in ({'direction': 'invalid'}, {'icon_size': 'NaN'}, {'icon_size': '0'}, {'unknown': 'true'}):
                element['display']['options'] = options
                self.assertFalse(describe_cell(element, {})['supported'])
        widget = SObjectConnectionElement(direction='dst', icon_size='72')
        widget.set_sobjects([self.a, self.b])
        widget.preprocess()
        widget.set_current_index(1)
        value = widget.get_cell_value()
        self.assertEqual(value['iconSize'], 72)
        self.assertEqual(value['connectionRows'], self.rows(self.b))

    def test_scope_and_revision_prevent_removing_another_connection(self):
        connection = self.connection()
        row = self.rows(self.b)[0]
        for parent, revision in ((self.a, row['expectedRevision']), (self.b, 'stale')):
            with self.assertRaisesRegex(UserException, 'changed'):
                write(lambda: remove_connection(parent.get_search_key(), connection.get_search_key(), revision))
        self.assertIsNotNone(Search.get_by_search_key(connection.get_search_key()))
        command = TableConnectionRemoveCmd(parent_key=self.b.get_search_key(),
            connection_key=connection.get_search_key(), expected_revision=row['expectedRevision'])
        write(command.execute)
        self.assertEqual(command.info['state'], 'removed')
        self.assertIsNone(Search.get_by_search_key(connection.get_search_key()))
        self.assertIsNotNone(Search.get_by_search_key(self.a.get_search_key()))
        self.assertIsNotNone(Search.get_by_search_key(self.b.get_search_key()))

    def test_missing_target_remains_a_removable_connection(self):
        connection = self.connection()
        write(self.a.delete)
        row = self.rows(self.b)[0]
        self.assertFalse(row['available'])
        self.assertNotIn('searchKey', row)
        write(lambda: remove_connection(self.b.get_search_key(), connection.get_search_key(), row['expectedRevision']))
        self.assertIsNone(Search.get_by_search_key(connection.get_search_key()))
        self.assertIsNotNone(Search.get_by_search_key(self.b.get_search_key()))

    def test_replay_after_unknown_response_is_safe_for_parent_and_connection_rows(self):
        for direct in (False, True):
            connection = self.connection()
            parent = connection if direct else self.b
            row = self.rows(parent)[0]
            arguments = (parent.get_search_key(), connection.get_search_key(), row['expectedRevision'])
            result = write(lambda: remove_connection(*arguments))
            self.assertEqual(write(lambda: remove_connection(*arguments)), result)
            self.assertIsNotNone(Search.get_by_search_key(self.a.get_search_key()))
            self.assertIsNotNone(Search.get_by_search_key(self.b.get_search_key()))

    def test_late_failure_rolls_back_removal(self):
        connection = self.connection()
        row = self.rows(self.b)[0]
        original = SObjectConnection.delete
        def fail(record):
            original(record)
            raise RuntimeError('Late failure')
        with patch.object(SObjectConnection, 'delete', fail), self.assertRaisesRegex(RuntimeError, 'Late failure'):
            write(lambda: remove_connection(self.b.get_search_key(), connection.get_search_key(), row['expectedRevision']))
        self.assertIsNotNone(Search.get_by_search_key(connection.get_search_key()))
        self.assertIsNotNone(Search.get_by_search_key(self.a.get_search_key()))
        self.assertIsNotNone(Search.get_by_search_key(self.b.get_search_key()))

    def test_revision_uses_fresh_database_state_after_lock(self):
        connection = self.connection()
        row = self.rows(self.b)[0]
        backend = type(connection.get_sql().get_database_impl())
        lock = backend.lock_collection_table
        def changed(implementation, sql, table, timeout=None):
            lock(implementation, sql, table, timeout)
            sql.do_update("UPDATE connection SET context='parallel' WHERE id=%s" % connection.get_id())
        with patch.object(backend, 'lock_collection_table', changed), self.assertRaisesRegex(UserException, 'changed'):
            write(lambda: remove_connection(self.b.get_search_key(), connection.get_search_key(), row['expectedRevision']))
        self.assertIsNotNone(Search.get_by_search_key(connection.get_search_key()))

    def test_permissions_precede_record_reads_and_locks(self):
        connection = self.connection()
        row = self.rows(self.b)[0]
        with patch.object(Environment.get_security(), 'is_admin', return_value=False):
            with patch.object(Search, 'get_by_search_key', side_effect=AssertionError('Read before authorization')):
                with self.assertRaises(PermissionError):
                    remove_connection(self.b.get_search_key(), connection.get_search_key(), row['expectedRevision'])
            with patch.object(Search, 'get_by_search_keys', side_effect=AssertionError('Read before authorization')):
                with self.assertRaises(PermissionError):
                    read_connection_cells([self.b.get_search_key()])

    def test_target_objects_are_read_as_one_batch(self):
        parents = []
        for index in range(12):
            source, target = SearchType.create('contract/entity'), SearchType.create('contract/entity')
            source.set_value('code', 'SOURCE_%s' % index)
            target.set_value('code', 'TARGET_%s' % index)
            write(source.commit)
            write(target.commit)
            write(lambda: SObjectConnection.create(source, target, direction='one'))
            parents.append(target.get_search_key())
        with patch.object(Search, 'get_by_id', wraps=Search.get_by_id) as reads:
            values = read_connection_cells(parents)
        target_reads = [call for call in reads.call_args_list if call.args[0].startswith('contract/entity')]
        self.assertEqual(len(target_reads), 1)
        self.assertEqual(len(target_reads[0].args[1]), 12)
        self.assertTrue(all(len(cell['connectionRows']) == 1 for cell in values.values()))

    def test_project_scope_and_private_targets(self):
        connection = self.connection()
        def change(field, value):
            connection.set_value(field, value)
            connection.commit(triggers=False)
        write(lambda: change('project_code', 'two'))
        self.assertEqual(self.rows(self.b), [])
        with self.assertRaisesRegex(ValueError, 'another project'):
            read_connection_cells(['contract/entity?project=two&code=B'])
        write(lambda: change('project_code', 'one'))
        write(lambda: change('src_search_type', 'sthpw/message'))
        with patch.object(Search, 'get_by_id', side_effect=AssertionError('Private target was read')):
            with self.assertRaisesRegex(ValueError, 'Messages'):
                self.rows(self.b)
        with self.assertRaisesRegex(ValueError, 'Messages'):
            write(lambda: remove_connection(self.b.get_search_key(), connection.get_search_key(), 'revision'))

    def test_invalid_scopes_and_options_are_rejected(self):
        for keys in ('not-a-list', [None], list(range(501))):
            with self.assertRaises(ValueError):
                read_connection_cells(keys)
        for options in ({'icon_size': True}, {'direction': 'other'}):
            with self.assertRaises(ValueError):
                read_connection_cells([], **options)
