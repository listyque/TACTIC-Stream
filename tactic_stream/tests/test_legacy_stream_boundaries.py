"""Transported procedures retain native reads without the Stream package."""
import builtins
import inspect
from pathlib import Path
from runpy import run_path
import unittest

import test_table_services as fixtures
from test_table_embedded_widgets import write
from pyasm.biz import Task
from pyasm.common import Container
from pyasm.search import Search, SearchType
from tactic.ui.table.nested_scope import read_nested_scope
from tactic.ui.table.custom_layout_element_wdg import read_custom_layout


class LegacyStreamBoundaries(unittest.TestCase):
    setUp = fixtures.TableServices.setUp

    def procedures(self, name, native, missing='tactic_stream'):
        path = Path(__file__).resolve().parents[3] / 'TH/thlib/ui/table/requests.py'
        handler = run_path(str(path))[name]

        def legacy_import(module, *args, **kwargs):
            if module.startswith('tactic_stream'):
                raise ModuleNotFoundError('Unavailable module: ' + missing, name=missing)
            return builtins.__import__(module, *args, **kwargs)

        for function in (handler, native):
            scope = dict(function.__globals__)
            scope['__builtins__'] = {**vars(builtins), '__import__': legacy_import}
            exec(inspect.getsource(function), scope)
            yield scope[name]

    def test_native_simple_choices_and_parent_scope_without_stream_imports(self):
        parent = Search.get_by_code('contract/entity', 'A')
        other = Search.get_by_code('contract/entity', 'B')

        def seed():
            for owner, process in ((parent, 'model'), (parent, 'rig'), (other, 'other')):
                Task.create(owner, process, triggers=False)
            config = SearchType.create('config/widget_config')
            config.set_value('search_type', 'sthpw/task')
            config.set_value('view', 'legacy_simple')
            config.set_value('config', '''<config><legacy_simple><element name="process">
<display class="tactic.ui.filter.SelectFilterElementWdg"><column>process</column>
<values_expr>@GET(sthpw/task.process)</values_expr></display>
</element></legacy_simple></config>''')
            config.commit(triggers=False)
        write(seed)
        previous = (Container.get('Expression:check_record_access'), Container.get('Expression:check_method_access'))
        for read in self.procedures('read_nested_scope', read_nested_scope):
            result = read(parent.get_search_key(), 'sthpw/task', simple_view='legacy_simple', simple_values={'process': 'model'})
            self.assertEqual([row['process'] for row in result['records']], ['model'])
            self.assertIn('other', [row['value'] for row in result['simpleFilters'][0]['options']])
            self.assertEqual(previous, (Container.get('Expression:check_record_access'), Container.get('Expression:check_method_access')))
        for read in self.procedures('read_nested_scope', read_nested_scope, missing='broken_stream_dependency'):
            with self.assertRaisesRegex(ModuleNotFoundError, 'broken_stream_dependency'):
                read(parent.get_search_key(), 'sthpw/task', simple_view='legacy_simple')

    def test_legacy_html_works_and_stream_layouts_are_reported_before_import(self):
        parent = Search.get_by_code('contract/entity', 'A')

        def seed():
            for view, xml in (
                ('legacy_html', '<html><div>Legacy content</div></html>'),
                ('stream_page', '<dashboard>{"name":"review","blocks":[]}</dashboard>'),
            ):
                row = SearchType.create('config/widget_config')
                row.set_value('search_type', 'CustomLayoutWdg')
                row.set_value('view', view)
                row.set_value('config', '<config><' + view + '>' + xml + '</' + view + '></config>')
                row.commit(triggers=False)
            row = SearchType.create('config/widget_config')
            row.set_value('search_type', 'CustomLayoutWdg')
            row.set_value('view', 'stream_item')
            row.set_value('config', '<config><stream_item layout="sobject-layout"/></config>')
            row.commit(triggers=False)
        write(seed)
        for read in self.procedures('read_custom_layout', read_custom_layout):
            self.assertTrue(read(parent.get_search_key(), 'legacy_html', stream_api=False)['layoutNodes'])
            for view in ('stream_page', 'stream_item'):
                result = read(parent.get_search_key(), view, stream_api=False)
                self.assertTrue(result['streamRequired'])
                self.assertEqual(result['layoutNodes'], [])
