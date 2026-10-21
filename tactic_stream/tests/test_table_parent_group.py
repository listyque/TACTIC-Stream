"""Parent grouping identities and polymorphic code/id/project references."""
import unittest
from unittest.mock import patch

import test_table_services as fixtures
from test_table_embedded_widgets import write
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from tactic.ui.table.group_element_wdg import read_parent_cells
from tactic.ui.table.parent_group import edit_parent_group, TableParentGroupCmd


class ParentGroups(unittest.TestCase):
    setUp = fixtures.TableServices.setUp

    def note(self, parent_type='contract/entity', code='A', identity=1, project='one'):
        def create():
            obj = SearchType.create('sthpw/note')
            for name, value in dict(search_type=parent_type, search_code=code,
                    search_id=identity, project_code=project, login='admin', process='publish', note='Review').items():
                obj.set_value(name, value)
            obj.commit(triggers=False)
            return obj
        return write(create)

    def editor(self):
        config = SearchType.create('config/widget_config')
        config.set_value('search_type', 'sthpw/note')
        config.set_value('view', 'parent_test')
        config.set_value('config', '<config><parent_test><element name="parent">'
            '<display class="tactic.ui.table.ParentGroupTableElementWdg"/>'
            '<action class="tactic.ui.table.ParentGroupAction"/></element></parent_test></config>')
        write(config.commit)
        obj = self.note()
        args = dict(search_key=obj.get_search_key(), view='parent_test', column='parent')
        prepared = edit_parent_group(**args)
        rows = edit_parent_group(**args, action='candidates', parent_type='contract/entity',
            expected_revision=prepared['expectedRevision'])['rows']
        chosen = next(row for row in rows if row['code'] == 'B')
        save = dict(args, action='save', expected_revision=prepared['expectedRevision'],
            parent_key=chosen['searchKey'], parent_revision=chosen['revision'])
        return obj, config, args, prepared, save

    def test_actual_parent_descriptor_retired_id_and_missing(self):
        notes = [self.note(), self.note(code='', identity=4), self.note(code='C', identity=3), self.note(code='GONE')]
        cells = read_parent_cells([obj.get_search_key() for obj in notes])
        normal, by_id, retired, missing = [cells[obj.get_search_key()] for obj in notes]
        self.assertEqual(normal['text'], 'A')
        self.assertEqual(normal['parent']['name'], 'Первый')
        self.assertEqual(normal['parent']['record']['__search_key__'], normal['groupKey'])
        self.assertEqual(by_id['parent']['record']['id'], 4)
        self.assertEqual(by_id['text'], '4')
        self.assertTrue(retired['parent']['retired'])
        self.assertIsNone(missing['parent'])
        self.assertIn('GONE', missing['missingParentKey'])
        self.assertTrue(missing['groupKey'].startswith('missing:'))
        self.assertEqual(len(normal['sourceRevision']), 64)

    def test_system_note_result_tree_does_not_resolve_wildcard_as_a_search_type(self):
        from tactic_stream.server.result_items import read_result_items
        note = self.note()
        result = read_result_items('sthpw/note', [note.get_search_key()])
        self.assertEqual(result['items'][0]['record']['__search_key__'], note.get_search_key())

    def test_global_table_uses_record_project_for_bare_parent_type(self):
        note = self.note()
        with patch('pyasm.biz.Project.get_project_code', return_value='admin'):
            cell = read_parent_cells([note.get_search_key()])[note.get_search_key()]
        self.assertEqual(cell['projectCode'], 'one')
        self.assertEqual(cell['parent']['name'], 'Первый')
        self.assertIn('project=one', cell['parent']['searchKey'])

    def test_private_parent_guard_runs_before_target_lookup(self):
        obj = self.note(parent_type='sthpw/message', code='PRIVATE')
        with self.assertRaisesRegex(ValueError, 'not available in parent groups'):
            read_parent_cells([obj.get_search_key()])
        with patch.object(Environment.get_security(), 'is_admin', return_value=False), self.assertRaises(PermissionError):
            read_parent_cells([])
        for keys in ('not a list', [None], ['contract/entity?project=two&code=A']):
            with self.assertRaises(ValueError):
                read_parent_cells(keys)

    def test_parent_context_never_exports_account_secrets(self):
        obj = self.note(parent_type='sthpw/login', code='admin')
        parent = read_parent_cells([obj.get_search_key()])[obj.get_search_key()]['parent']
        self.assertEqual(parent['code'], 'admin')
        self.assertNotIn('password', parent['record'])
        self.assertNotIn('ticket', parent['record'])

    def test_same_code_on_different_types_has_distinct_group_identity(self):
        with self.store.connection(write=True) as database:
            database.execute("INSERT INTO search_object(code,search_type,namespace,database,table_name,class_name) "
                "VALUES('contract/other','contract/other','contract','{project}','entity','pyasm.search.SObject')")
        notes = [self.note(), self.note(parent_type='contract/other')]
        cells = read_parent_cells([obj.get_search_key() for obj in notes])
        left, right = [cells[obj.get_search_key()] for obj in notes]
        self.assertEqual(left['text'], right['text'])
        self.assertNotEqual(left['groupKey'], right['groupKey'])

    def test_configured_replacement_and_lost_response_check(self):
        obj, _, args, prepared, save = self.editor()
        self.assertIn('contract/entity', [row['value'] for row in prepared['parentTypes']])
        result = write(lambda: TableParentGroupCmd(**save).execute())
        self.assertEqual(result['state'], 'saved')
        self.assertEqual(Search.get_by_search_key(obj.get_search_key()).get_value('search_code'), 'B')
        self.assertEqual(edit_parent_group(**dict(save, action='check'))['state'], 'saved')
        self.assertEqual(write(lambda: edit_parent_group(**save))['state'], 'saved')

    def test_specialized_and_expression_parent_columns_have_the_same_action(self):
        from tactic_stream.server.table_cells import describe_cell, read_table_cells
        from tactic_stream.server.interface import read_interface
        obj, config, _, _, _ = self.editor()
        for expression in (False, True):
            if expression:
                config.set_value('config', config.get_value('config').replace(
                    '<display class="tactic.ui.table.ParentGroupTableElementWdg"/>',
                    '<display class="tactic.ui.table.ExpressionElementWdg"><expression>@GET(.search_code)</expression>'
                    '<order_by>search_type</order_by></display>'))
                write(config.commit)
            definition = read_interface('sthpw/note', 'parent_test')
            descriptor = definition['table']['elements'][0]['cell']
            self.assertTrue(descriptor['supported'])
            self.assertEqual(descriptor['kind'], 'commands')
            cell = read_table_cells('sthpw/note', 'parent_test', [obj.get_search_key()])[obj.get_search_key()]['parent']
            self.assertNotIn('error', cell)
            self.assertEqual(cell['text'], 'A')
            self.assertEqual(cell['parentGrouping'], not expression)
            self.assertTrue(cell['parentEditable'])
            self.assertEqual(cell['tableView'], 'parent_test')

    def test_stale_source_parent_and_definition_never_replace_relationship(self):
        obj, config, args, prepared, save = self.editor()
        parent = Search.get_by_code('contract/entity', 'B')
        write(lambda: (parent.set_value('name', 'Changed'), parent.commit()))
        with self.assertRaisesRegex(ValueError, 'Parent changed'):
            write(lambda: edit_parent_group(**save))
        self.assertEqual(Search.get_by_search_key(obj.get_search_key()).get_value('search_code'), 'A')
        config.set_value('config', config.get_value('config').replace('ParentGroupAction', 'NoLongerParentAction'))
        write(config.commit)
        with self.assertRaisesRegex(ValueError, 'configured parent action changed'):
            write(lambda: edit_parent_group(**save))

    def test_parent_query_matches_names_and_treats_regex_as_literal(self):
        _, _, args, prepared, _ = self.editor()
        arguments = dict(args, action='candidates', parent_type='contract/entity', expected_revision=prepared['expectedRevision'])
        self.assertEqual([row['code'] for row in edit_parent_group(**arguments, query="Reilly")['rows']], ['B'])
        self.assertEqual(edit_parent_group(**arguments, query='[')['rows'], [])
        with self.assertRaisesRegex(ValueError, 'another project'):
            edit_parent_group(**dict(arguments, parent_type='contract/entity?project=two'))

    def test_database_error_rolls_back_relationship_write(self):
        obj, _, _, _, save = self.editor()
        with self.store.connection(write=True) as database:
            database.execute("CREATE TRIGGER reject_parent_fixture BEFORE UPDATE ON note "
                "WHEN NEW.search_code='B' BEGIN SELECT RAISE(ABORT,'reject parent fixture'); END")
        with self.assertRaisesRegex(Exception, 'reject parent fixture'):
            write(lambda: edit_parent_group(**save))
        with self.store.connection() as database:
            row = database.execute('SELECT search_code FROM note WHERE id=?', (obj.get_id(),)).fetchone()
        self.assertEqual(row[0], 'A')

    def test_cycles_retired_targets_and_foreign_projects_are_rejected(self):
        obj, _, args, prepared, save = self.editor()
        child = self.note(parent_type='sthpw/note', code=obj.get_code(), identity=obj.get_id())
        for target, message in ((child, 'cyclic'), (obj, 'cyclic'),
                (Search.get_by_code('contract/entity', 'C'), 'current parent')):
            selected = edit_parent_group(**args, parent_key=target.get_search_key())['selectedParent']
            with self.assertRaisesRegex(ValueError, message):
                write(lambda: edit_parent_group(**dict(save, parent_key=selected['searchKey'], parent_revision=selected['revision'])))
        with self.assertRaisesRegex(ValueError, 'another project'):
            edit_parent_group(**dict(save, action='check', parent_key='contract/entity?project=two&code=A'))
        self.assertEqual(Search.get_by_search_key(obj.get_search_key()).get_value('search_code'), 'A')

    def test_source_revision_checks_fresh_data_in_the_same_request(self):
        obj, _, args, prepared, save = self.editor()
        with self.store.connection(write=True) as database:
            database.execute('UPDATE note SET note=? WHERE id=?', ('Changed elsewhere', obj.get_id()))
        with self.assertRaisesRegex(ValueError, 'Parent changed'):
            edit_parent_group(**args, source_revision=prepared['sourceRevision'])
        with self.assertRaisesRegex(ValueError, 'Parent changed'):
            write(lambda: edit_parent_group(**save))

    def test_orphan_with_missing_type_still_has_a_group_and_can_be_repaired(self):
        obj, _, args, _, save = self.editor()
        with self.store.connection(write=True) as database:
            database.execute("INSERT INTO note(code,search_type,search_code,search_id,project_code,login,process,note) "
                "VALUES('ORPHAN','contract/missing','A',1,'one','admin','publish','Imported old data')")
        obj = Search.get_by_code('sthpw/note', 'ORPHAN')
        args['search_key'] = obj.get_search_key()
        save['search_key'] = obj.get_search_key()
        cell = read_parent_cells([obj.get_search_key()])[obj.get_search_key()]
        self.assertIn('contract/missing', cell['missingParentKey'])
        prepared = edit_parent_group(**args, source_revision=cell['sourceRevision'])
        self.assertIsNone(prepared['currentParent'])
        self.assertEqual(write(lambda: edit_parent_group(**dict(save, expected_revision=prepared['expectedRevision'])))['state'], 'saved')

    def test_physical_source_identity_cannot_be_retargeted_on_refresh_or_save(self):
        obj, _, args, _, save = self.editor()
        for operation in ('prepare', 'save', 'check'):
            with self.assertRaisesRegex(LookupError, 'no longer available'):
                write(lambda: edit_parent_group(**dict(save, action=operation, source_id=str(obj.get_id() + 100))))

    def test_independently_shipped_handler_functions_execute_without_stream_imports(self):
        import ast
        from pathlib import Path
        source = (Path(__file__).resolve().parents[3] / 'th_codex/thlib/ui/table/requests.py').read_text(encoding='utf-8')
        functions = {node.name: ast.get_source_segment(source, node) for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
        scope = {}
        exec(functions['read_parent_cells'] + '\n' + functions['edit_parent_group'], scope)
        obj, _, args, _, save = self.editor()
        cell = scope['read_parent_cells']([obj.get_search_key()])[obj.get_search_key()]
        self.assertEqual(cell['parent']['code'], 'A')
        prepared = scope['edit_parent_group'](**args)
        result = write(lambda: scope['edit_parent_group'](**dict(save, expected_revision=prepared['expectedRevision'])))
        self.assertEqual(result['state'], 'saved')
