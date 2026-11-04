"""Actual retained VFX layouts, scripts and scoped data on disposable projects."""

import ast
import sys
import unittest
from pathlib import Path

from pyasm.search import Search, SearchType
from tactic.ui.table.custom_layout_element_wdg import read_custom_layout
from tactic.ui.table.nested_scope import read_nested_scope
from tactic_stream.server.table_cells import read_table_cells
from test_table_embedded_widgets import write
import test_vfx_standard_widgets as standard


def tables(nodes):
    for node in nodes:
        if node['kind'] == 'table':
            yield node['table']
        else:
            yield from tables(node.get('children') or [])


class VfxComposition(unittest.TestCase):
    setUp = standard.VfxStandardWidgets.setUp
    handler_read = standard.VfxStandardWidgets.handler_read

    def script(self, source, key, **extra):
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'TH'))
        from thlib.ui.table.scripts import TableScriptRunner

        case = self

        class Server:
            def set_project(self, project):
                if project != case.auth['project']:
                    raise ValueError('Unexpected script project')

            def __getattr__(self, name):
                def call(*args, **kwargs):
                    result = case.api.dispatch(name, (case.auth, *args), kwargs)
                    return (
                        ast.literal_eval(result)
                        if name == 'eval' and isinstance(result, str)
                        else result
                    )

                return call

        context = dict(
            searchKey=key,
            searchType=key.split('?')[0],
            project=self.auth['project'],
            record=Search.get_by_search_key(key).get_sobject_dict(),
            **extra,
        )
        return TableScriptRunner(Server(), context).run(source)

    def test_planners_keep_project_tables_and_exact_single_shot(self):
        from tactic_stream.server.navigation import read_navigation

        def entries(items):
            for item in items:
                yield item
                yield from entries(item.get('children') or [])

        planners = [
            entry
            for entry in entries(read_navigation()['entries'])
            if entry.get('layoutView')
        ]
        self.assertEqual(
            {entry['layoutView'] for entry in planners},
            {'shot_planner_wdg', 'sequence_planner_wdg'},
        )
        self.assertTrue(
            all(entry['layoutSearchType'] == 'vfx/asset' for entry in planners)
        )
        shot = Search('vfx/shot').get_sobject()
        other = SearchType.create('vfx/shot')
        other.set_value('code', 'OTHER')
        write(other.commit)
        key = shot.get_search_key()
        for view, count in [
            ('shot_planner_wdg', 2),
            ('single_shot_planner_wdg', 1),
            ('sequence_planner_wdg', 2),
        ]:
            layout = read_custom_layout(key, view)
            scopes = list(tables(layout['layoutNodes']))
            self.assertEqual(len(scopes), 2)
            result = read_nested_scope(
                scopes[1]['parentKey'],
                scopes[1]['searchType'],
                view=scopes[1]['view'],
                search_view=scopes[1]['searchView'],
                project_scope=scopes[1]['projectScope'],
            )
            self.assertEqual(len(result['records']), count)
            assets = read_nested_scope(
                scopes[0]['parentKey'],
                scopes[0]['searchType'],
                view=scopes[0]['view'],
                project_scope=True,
                simple_view=scopes[0]['simpleSearchView'],
            )
            if scopes[0]['simpleSearchView']:
                self.assertEqual(
                    [item['name'] for item in assets['simpleFilters']],
                    ['asset_category', 'sequence', 'shot'],
                )
                filtered = read_nested_scope(
                    scopes[0]['parentKey'],
                    scopes[0]['searchType'],
                    view=scopes[0]['view'],
                    project_scope=True,
                    simple_view=scopes[0]['simpleSearchView'],
                    simple_values={'shot': shot.get_code()},
                )
                self.assertEqual(
                    [row['code'] for row in filtered['records']], ['ROBOT']
                )
            self.assertEqual(len(assets['records']), 1)
            for scope in scopes:
                native = self.handler_read(
                    'query_table_layout',
                    search_type=scope['searchType'],
                    view=scope['view'],
                    project_code=self.auth['project'],
                    search_keys=[row['__search_key__'] for row in result['records']]
                    if scope is scopes[1]
                    else [Search('vfx/asset').get_sobject().get_search_key()],
                )
                self.assertTrue(native['columns'])
        script = Search('config/custom_script')
        script.add_filter('folder', 'shots')
        script.add_filter('title', 'load_shot_planner')
        result = self.script(script.get_sobject().get_value('script'), key)
        self.assertEqual(result['commands'][0]['tabKey'], 'SH010 Planner')
        self.assertEqual(result['commands'][0]['options']['search_key'], key)
        with self.assertRaisesRegex(ValueError, 'project-owned'):
            read_nested_scope(key, 'sthpw/login', project_scope=True)

    def test_shot_sheet_reports_fields_tables_and_print_action(self):
        import base64

        shot = Search('vfx/shot').get_sobject()
        key = shot.get_search_key()
        plate = SearchType.create('vfx/plate')
        plate.set_value('code', 'PLATE')
        plate.set_value('shot_code', shot.get_code())
        plate.set_value('description', 'Plate notes')
        write(plate.commit)
        cells = read_table_cells(
            'vfx/plate', 'shot_sheet_wdg_plates', [plate.get_search_key()]
        )[plate.get_search_key()]
        self.assertFalse(cells['file_range'].get('error'))
        for version, file_range in enumerate(('1001-1010', '2001-2010'), 1):
            snapshot = self.api.dispatch(
                'create_snapshot', (self.auth, plate.get_search_key(), 'publish')
            )
            path = self.store.data_dir / ('plate%d.exr' % version)
            path.write_bytes(b'fixture')
            self.api.dispatch(
                'add_file',
                (self.auth, snapshot['code'], str(path)),
                dict(file_type='main', mode='copy', create_icon=False),
            )
            files = Search('sthpw/file')
            files.add_filter('snapshot_code', snapshot['code'])
            file = files.get_sobject()
            file.set_value('file_range', file_range)
            write(file.commit)
        latest = read_table_cells('vfx/plate', 'table', [plate.get_search_key()])[
            plate.get_search_key()
        ]
        self.assertIn('2001-2010', latest['file_range']['text'])
        self.assertNotIn('1001-1010', latest['file_range']['text'])
        self.assertIn('admin', latest['login']['text'])
        icon = self.api.dispatch('create_snapshot', (self.auth, key, 'icon'))
        icon_path = self.store.data_dir / 'shot-icon.png'
        icon_path.write_bytes(
            base64.b64decode(
                'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP4/x8AAwAB/2+Bq7YAAAAASUVORK5CYII='
            )
        )
        self.api.dispatch(
            'add_file',
            (self.auth, icon['code'], str(icon_path)),
            dict(file_type='main', mode='copy', create_icon=False),
        )

        def plates():
            for index in range(100):
                row = SearchType.create('vfx/plate')
                row.set_value('code', 'EXTRA%03d' % index)
                row.set_value('shot_code', shot.get_code())
                row.commit()

        write(plates)
        report = self.api.dispatch(
            'execute_cmd',
            (
                self.auth,
                'tactic.ui.table.CustomLayoutReportCmd',
                dict(search_key=key, view='shot_sheet_wdg'),
            ),
        )['info']
        self.assertIn('1001', [block.get('text') for block in report['blocks']])
        self.assertEqual(
            [block['title'] for block in report['blocks'] if block['kind'] == 'table'],
            ['plates', 'tasks'],
        )
        self.assertTrue(
            any(
                'Plate notes' in row
                for block in report['blocks']
                if block['kind'] == 'table'
                for row in block['rows']
            )
        )
        self.assertEqual(
            len(
                next(block for block in report['blocks'] if block['kind'] == 'table')[
                    'rows'
                ]
            ),
            101,
        )
        self.assertEqual(
            base64.b64decode(
                next(block for block in report['blocks'] if block['kind'] == 'image')[
                    'data'
                ]
            ),
            icon_path.read_bytes(),
        )
        layout = read_custom_layout(key, 'shot_sheet_wdg')
        action = next(
            node for node in layout['layoutNodes'] if node['kind'] == 'action'
        )
        result = self.script(
            action['javascript'],
            key,
            layoutState=dict(root={}, controls=[]),
            layoutTrigger=action['selector'],
        )
        self.assertTrue(
            any(command['type'] == 'print-layout' for command in result['commands'])
        )
        native = self.handler_read(
            'query_table_layout',
            search_type='vfx/shot',
            view='shot_tracking',
            project_code=self.auth['project'],
            search_keys=[key],
        )
        self.assertFalse(native['rows'][key]['shot_sheet_wdg'].get('error'))

    def test_review_original_load_select_submit_and_duplicate(self):
        shot = Search('vfx/shot').get_sobject()
        snapshot = self.api.dispatch(
            'create_snapshot', (self.auth, shot.get_search_key(), 'animation')
        )
        review = self.api.dispatch(
            'insert',
            (
                self.auth,
                'vfx/review',
                dict(
                    code='DAILY',
                    type='daily',
                    description='Team review',
                    date='2026-10-25',
                ),
            ),
        )
        key = snapshot['__search_key__']
        layout = read_custom_layout(key, 'add_snapshot_to_review_wdg')
        self.assertNotIn('spt.Applet', layout['layoutLoad'][0]['javascript'])
        initial = dict(
            root={}, controls=layout['layoutControls'], form=layout['layoutForm']
        )
        result = self.script(
            layout['layoutLoad'][0]['javascript'],
            key,
            layoutState=initial,
            layoutUser='admin',
        )
        state = next(
            command['state']
            for command in result['commands']
            if command['type'] == 'layout-state'
        )
        self.assertEqual(state['root']['snapshot']['code'], snapshot['code'])
        choice = next(
            control for control in state['controls'] if control['kind'] == 'choice'
        )
        self.assertEqual(choice['options'][0]['value'], 'DAILY')
        action = next(
            node for node in layout['layoutNodes'] if node['kind'] == 'action'
        )
        self.assertIn('ReviewSubmissionCmd', action['javascript'])
        for _ in range(2):
            result = self.script(
                action['javascript'],
                key,
                layoutState=state,
                layoutUser='admin',
                layoutTrigger=action['selector'],
            )
            self.assertTrue(
                any(command['type'] == 'close-layout' for command in result['commands'])
            )
        search = Search('vfx/submission')
        search.add_filter('snapshot_code', snapshot['code'])
        submissions = search.get_sobjects()
        self.assertEqual(len(submissions), 1)
        self.assertEqual(submissions[0].get_value('version'), snapshot['version'])
        self.assertEqual(submissions[0].get_value('artist'), 'admin')
        nested = read_nested_scope(
            review['__search_key__'],
            'sthpw/snapshot',
            view='review_snapshots',
            expression='@SOBJECT(vfx/submission.sthpw/snapshot)',
        )
        self.assertEqual([row['code'] for row in nested['records']], [snapshot['code']])
        before = len(Search('vfx/submission').get_sobjects())
        with self.assertRaisesRegex(ValueError, 'review'):
            self.api.dispatch(
                'execute_cmd',
                (
                    self.auth,
                    'tactic.ui.table.ReviewSubmissionCmd',
                    dict(
                        snapshot_key=key,
                        review_code='MISSING',
                        expected_version=snapshot['version'],
                        expected_context=snapshot['context'],
                    ),
                ),
            )
        with self.assertRaisesRegex(ValueError, 'snapshot changed'):
            self.api.dispatch(
                'execute_cmd',
                (
                    self.auth,
                    'tactic.ui.table.ReviewSubmissionCmd',
                    dict(
                        snapshot_key=key,
                        review_code='DAILY',
                        expected_version=999,
                        expected_context=snapshot['context'],
                    ),
                ),
            )
        self.assertEqual(len(Search('vfx/submission').get_sobjects()), before)

    def test_layout_read_rejects_writes_in_mako_and_expressions(self):
        key = Search('vfx/shot').get_sobject().get_search_key()
        for html in (
            '${server.insert("vfx/shot", {})}',
            '[expr]@INSERT(vfx/shot)[/expr]',
            '${server.get_path_from_snapshot("UNRELATED")}',
        ):
            with self.assertRaises(ValueError):
                read_custom_layout(key, html=html)

    def test_json_eval_returns_data_and_original_sdk_transport_keeps_its_envelope(self):
        expression = '@SOBJECT(vfx/shot)'
        original = self.api.dispatch('eval', (self.auth, expression))
        self.assertIsInstance(original, str)
        self.api.protocol = 'json'
        result = self.api.dispatch('eval', (self.auth, expression))
        self.assertEqual(result, ast.literal_eval(original))

    def test_native_compilers_match_and_project_layouts_need_no_selected_object(self):
        from tactic.ui.table import custom_layout_element_wdg as compiler

        expected = next(
            node
            for node in ast.parse(Path(compiler.__file__).read_text()).body
            if isinstance(node, ast.FunctionDef) and node.name == 'read_custom_layout'
        )
        root = Path(__file__).resolve().parents[3] / 'TH'
        for file in ('thlib/ui/table/requests.py', 'thlib/tactic_query.py'):
            tree = ast.parse((root / file).read_text(encoding='utf-8'))
            actual = next(
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
                and node.name == 'read_custom_layout'
            )
            self.assertEqual(ast.dump(actual), ast.dump(expected))
        layout = read_custom_layout(view='shot_planner_wdg')
        self.assertTrue(layout['targetSearchKey'].startswith('sthpw/project?'))
        login = Search('sthpw/login').get_sobject()
        safe = read_custom_layout(login.get_search_key(), html='<p>Safe</p>')
        self.assertEqual(
            set(safe['layoutRecord']), {'__search_key__', 'code', 'name', 'title'}
        )
        shot = Search('vfx/shot').get_sobject()
        config = SearchType.create('config/widget_config')
        config.set_value('search_type', 'vfx/shot')
        config.set_value('view', 'native_layout')
        config.set_value(
            'config',
            '<config><native_layout><element name="sheet"><display class="tactic.ui.table.CustomLayoutElementWdg"><view>shot_sheet_wdg</view></display></element></native_layout></config>',
        )
        write(config.commit)
        native = self.handler_read(
            'query_table_layout',
            search_type='vfx/shot',
            view='native_layout',
            project_code=self.auth['project'],
            search_keys=[shot.get_search_key()],
        )
        self.assertEqual(
            native['rows'][shot.get_search_key()]['sheet']['layoutNodes'],
            read_custom_layout(shot.get_search_key(), 'shot_sheet_wdg')['layoutNodes'],
        )
