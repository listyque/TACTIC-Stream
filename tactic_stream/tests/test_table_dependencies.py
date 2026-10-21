"""Exact snapshot references, bounded sequences and private/project boundaries."""
import unittest
import ast
from pathlib import Path
from unittest.mock import patch

import test_table_services as fixtures
from test_table_embedded_widgets import write
from pyasm.biz import Snapshot
from pyasm.common import Environment, UserException
from pyasm.search import Search
from tactic.ui.table.dependencies import read_dependency_node as read


class TableDependencies(unittest.TestCase):
    setUp = fixtures.TableServices.setUp

    def test_independent_native_reader_copies_match(self):
        native = Path(__file__).resolve().parents[3] / 'th_codex/thlib/ui/table/requests.py'
        if not native.is_file():
            self.skipTest('Handler checkout is required for the independent-copy check')
        functions = {node.name: node for node in ast.parse(native.read_text(encoding='utf-8')).body if isinstance(node, ast.FunctionDef)}
        for filename, name in (('dependencies.py', 'read_dependency_node'), ('file_actions.py', 'read_snapshot_files')):
            source = Path(__file__).resolve().parents[1] / 'src/tactic/ui/table' / filename
            function = next(node for node in ast.parse(source.read_text(encoding='utf-8')).body if isinstance(node, ast.FunctionDef) and node.name == name)
            self.assertEqual(ast.dump(function), ast.dump(functions[name]), name)

    def snapshots(self, body='<snapshot/>'):
        def create():
            parent = Search.get_by_code('contract/entity', 'A')
            target = Snapshot.create(parent, 'file', 'target', triggers=False)
            root = Snapshot.create(parent, 'file', 'root', snapshot_data=body.replace('TARGET', target.get_code()), triggers=False)
            return root, target
        return write(create)

    def test_exact_references_files_missing_origin_and_pages(self):
        root, target = self.snapshots('<snapshot><file file_code="F1" name="image.####.exr" type="main" file_range="1-3">'
            '<ref snapshot_code="TARGET"/></file><ref snapshot_code="TARGET" node="node" instance="3"/>'
            '<fref snapshot_code="MISSING"/><unknown_ref path="lost.ma"/></snapshot>')
        first = read(root.get_search_key(), limit=2)
        self.assertTrue(first['hasNext'])
        self.assertEqual(first['rows'][0]['fileRange'], '1-3')
        self.assertEqual(first['rows'][1]['snapshotKey'], target.get_search_key())
        self.assertEqual(first['rows'][1]['instance'], '3')
        second = read(root.get_search_key(), offset=2, limit=3, expected_revision=first['revision'])
        self.assertEqual([row['kind'] for row in second['rows']], ['missing', 'reference', 'missing'])
        self.assertEqual(second['rows'][1]['origin'], 'image.####.exr')
        self.assertFalse(second['hasNext'])

    def test_large_sequence_is_expanded_only_for_requested_page(self):
        root, _ = self.snapshots('<snapshot><file name="image.####.exr" file_range="1-10000000/2"/></snapshot>')
        result = read(root.get_search_key(), file_index=0, offset=100, limit=2)
        self.assertEqual([row['title'] for row in result['rows']], ['image.0201.exr', 'image.0203.exr'])
        self.assertTrue(result['hasNext'])
        result = read(root.get_search_key(), file_index=0, offset=4999999, limit=2)
        self.assertEqual([row['title'] for row in result['rows']], ['image.9999999.exr'])
        self.assertFalse(result['hasNext'])

    def test_empty_object_and_stale_snapshot(self):
        parent = Search.get_by_code('contract/entity', 'A')
        self.assertEqual(read(parent.get_search_key())['message'], 'No snapshot found')
        root, _ = self.snapshots()
        with self.assertRaisesRegex(UserException, 'Dependencies changed'):
            read(root.get_search_key(), expected_revision='old')

    def test_widget_captures_owned_project_for_global_snapshot_and_project_tables(self):
        from pyasm.widget import DependencyLink
        root, _ = self.snapshots()
        widget = DependencyLink()
        with patch('pyasm.biz.Project.get_project_code', return_value='admin'):
            for obj in (root, Search.get_by_code('sthpw/project', 'one'), Search.get_by_code('contract/entity?project=one', 'A')):
                widget.set_sobject(obj)
                self.assertEqual(widget.get_cell_value()['projectCode'], 'one')

    def test_level_reference_uses_contextual_resolution_instead_of_its_unscoped_code(self):
        root, target = self.snapshots()
        parent = Search.get_by_code('contract/entity', 'A')
        level = Search.get_by_code('contract/entity', 'B')
        scoped = write(lambda: Snapshot.create(parent, 'file', 'target', level_type=level.get_search_type(),
            level_id=level.get_id(), triggers=False))
        def update():
            root.set_value('snapshot', '<snapshot><ref snapshot_code="'+target.get_code()+'" search_type="'+parent.get_search_type()+
                '" search_code="A" context="target" version="'+str(scoped.get_value('version'))+'" level_type="'+level.get_search_type()+
                '" level_id="'+str(level.get_id())+'"/></snapshot>')
            root.commit(triggers=False)
        write(update)
        self.assertEqual(read(root.get_search_key())['rows'][0]['snapshotKey'], scoped.get_search_key())

    def test_invalid_request_admin_and_private_owner(self):
        root, _ = self.snapshots()
        for arguments in ({'offset': -1}, {'limit': 201}, {'offset': True}, {'file_index': -1}, {'file_index': 0}):
            with self.assertRaises((ValueError, LookupError)):
                read(root.get_search_key(), **arguments)
        with patch.object(Environment.get_security(), 'is_admin', return_value=False), self.assertRaises(PermissionError):
            read(root.get_search_key())
        with self.assertRaisesRegex(ValueError, 'source project'):
            read('contract/entity?project=other&code=A')
        write(lambda: (root.set_value('search_type', 'sthpw/message?project=contract'), root.commit()))
        with self.assertRaisesRegex(ValueError, 'not available'):
            read(root.get_search_key())

    def test_deleted_owner_and_retired_snapshot_are_still_visible(self):
        root, target = self.snapshots('<snapshot><ref snapshot_code="TARGET"/></snapshot>')
        def orphan():
            target.set_value('search_code', 'MISSING')
            target.set_value('search_id', 99999)
            target.commit(triggers=False)
            target.retire()
        write(orphan)
        row = read(root.get_search_key())['rows'][0]
        self.assertTrue(row['retired'])
        self.assertTrue(row['ownerMissing'])
        self.assertIsNone(read(target.get_search_key())['owner'])


if __name__ == '__main__':
    unittest.main()
