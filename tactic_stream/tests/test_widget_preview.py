"""Draft overlay uses original merging; the renderer receives a bounded view tree."""
import json
from copy import deepcopy
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from tactic_stream.server.api import Api
from tactic_stream.server.interface import read_interface
from tactic_stream.server.widget_configuration import read_widget_configuration, preview_widget_configuration, save_widget_configuration


def exercise_preview(store, password):
    api = Api(store)
    token = api.get_ticket('admin', password)
    ticket = dict(ticket=token, project='admin')
    lower = '<config><preview_test><element name="code" title="Lower"><display class="pyasm.widget.TextWdg"/></element></preview_test></config>'
    upper = '<config><preview_test><element name="code" title="Higher"/></preview_test></config>'
    for priority, xml in ((10, lower), (20, upper)):
        api.dispatch('insert', (ticket, 'config/widget_config', dict(search_type='sthpw/note', view='preview_test', priority=priority, config=xml)))
    tab_xml = '''<config><nested><element name="notes" title="Nested notes"><display class="tactic.ui.panel.ViewPanelWdg"><search_type>sthpw/note</search_type><view>preview_test</view></display></element><element name="unknown"><display class="custom.Unknown"><script>raise RuntimeError('must never execute')</script></display></element></nested></config>'''
    api.dispatch('insert', (ticket, 'config/widget_config', dict(category='TabWdg', view='nested', config=tab_xml)))
    with request_context(RequestContext(store, 'admin', 'admin')):
        api.auth.bind_security('admin', token)
        current = read_widget_configuration('sthpw/note', 'preview_test')
        before = read_interface('sthpw/note', 'preview_test')
        count = Search('config/widget_config').get_count()
        low = current['sources'][1]['id']
        high = current['sources'][0]['id']
        draft = preview_widget_configuration('sthpw/note', 'preview_test', low, lower.replace('Lower', 'Ignored'), current['revision'])
        assert draft['interface'] == before, 'editing lower priority must not override the winner'
        draft = preview_widget_configuration('sthpw/note', 'preview_test', high, upper.replace('Higher', 'Draft'), current['revision'])
        assert draft['interface']['table']['elements'][0]['title'] == 'Draft', draft
        assert draft['interface']['table']['elements'][0]['display']['handler'] == 'pyasm.widget.TextWdg'
        assert read_interface('sthpw/note', 'preview_test') == before, 'draft leaked into request cache'
        assert Search('config/widget_config').get_count() == count
        assert read_widget_configuration('sthpw/note', 'preview_test')['revision'] == current['revision']
        # A new NULL-priority source is below numbered overrides, exactly as in core.
        created = preview_widget_configuration('sthpw/note', 'preview_test', None, upper.replace('Higher', 'New'), current['revision'])
        assert created['interface'] == before
        save_widget_configuration('sthpw/note', 'preview_test', None, upper.replace('Higher', 'New'), current['revision'])
        assert read_interface('sthpw/note', 'preview_test') == created['interface']
        current = read_widget_configuration('sthpw/note', 'dashboard')
        dashboard = '''<config><dashboard layout="tactic.ui.container.TabWdg"><element name="direct" title="Notes"><display class="tactic.ui.panel.ViewPanelWdg"><search_type>sthpw/note</search_type><view>preview_test</view><search_limit>2</search_limit><order_by>code desc, id asc</order_by><do_initial_search>hidden</do_initial_search><show_refresh>false</show_refresh><show_search_limit>false</show_search_limit></display></element><element name="nested" title="More"><display class="tactic.ui.container.TabWdg"><view>nested</view><selected>notes</selected></display></element></dashboard></config>'''
        draft = preview_widget_configuration('sthpw/note', 'dashboard', None, dashboard, current['revision'])
        tree = draft['interface']['table']
        assert tree['elements'][0]['interface']['table']['elements'][0]['title'] == 'Higher'
        panel = tree['elements'][0]['interface']['panel']
        assert panel == dict(search_limit=2, order_by=['code desc', 'id asc'], do_initial_search=False, show_refresh=False, show_search_limit=False)
        for invalid in (dashboard.replace('<search_limit>2', '<search_limit>0'),
                        dashboard.replace('<search_limit>2', '<search_limit>501'),
                        dashboard.replace('code desc, id asc', 'code; DROP TABLE note'),
                        dashboard.replace('<show_refresh>false', '<show_refresh>hidden')):
            try:
                preview_widget_configuration('sthpw/note', 'dashboard', None, invalid, current['revision'])
            except ValueError:
                pass
            else:
                raise AssertionError('invalid native panel options were accepted')
        nested = tree['elements'][1]['interface']['table']
        assert nested['selected'] == 'notes'
        assert nested['elements'][0]['interface']['search_type'] == 'sthpw/note'
        assert 'interface' not in nested['elements'][1], 'unknown script handler must stay opaque'
        count = Search('config/widget_config').get_count()
        cyclic = dashboard.replace('<view>preview_test</view>', '<view>dashboard</view>')
        try:
            preview_widget_configuration('sthpw/note', 'dashboard', None, cyclic, current['revision'])
        except ValueError as error:
            assert 'Cyclic interface reference' in str(error)
        else:
            raise AssertionError('recursive view was accepted')
        assert read_interface('sthpw/note', 'preview_test') == before
        assert Search('config/widget_config').get_count() == count
        # Same query arguments as the child renderer; real vendor sort/filter/offset.
        from ast import literal_eval
        for index in range(5):
            api.dispatch('insert', (ticket, 'sthpw/note', dict(code='VIEW_PAGE_%d' % index, note='panel paging')))
        def query(offset):
            records = api.dispatch('query', (ticket, 'sthpw/note'), dict(filters=[['code', 'contains', 'VIEW_PAGE_']],
                order_bys=panel['order_by'], limit=panel['search_limit'] + 1, offset=offset))
            return literal_eval(records) if isinstance(records, str) else records
        assert [item['code'] for item in query(0)] == ['VIEW_PAGE_4', 'VIEW_PAGE_3', 'VIEW_PAGE_2']
        assert [item['code'] for item in query(2)] == ['VIEW_PAGE_2', 'VIEW_PAGE_1', 'VIEW_PAGE_0']
        # Separate inline configs may both be named "tab" without being a cycle.
        from xml.etree.ElementTree import Element, SubElement, tostring, fromstring
        from pyasm.widget import WidgetConfig, WidgetConfigView
        from tactic_stream.server.interface import describe_composition
        inline = '<config><tab><element name="unknown"><display class="custom.Unknown"/></element></tab></config>'
        def wrap(xml):
            root = Element('config')
            node = SubElement(SubElement(SubElement(root, 'tab', layout='tactic.ui.container.TabWdg'), 'element', name='nested'), 'display', {'class': 'tactic.ui.container.TabWdg'})
            embedded = SubElement(node, 'config')
            for element in fromstring(xml).find('tab'):
                embedded.append(element)
            return tostring(root, encoding='unicode')
        inline = wrap(wrap(inline))
        config = WidgetConfigView('TabWdg', 'tab', [WidgetConfig.get(view='tab', xml=inline)], layout='tactic.ui.container.TabWdg')
        from pyasm.common import Common
        from unittest.mock import patch
        resolve = Common.resolve_class
        imports = []
        def track(path):
            imports.append(path)
            return resolve(path)
        with patch.object(Common, 'resolve_class', side_effect=track):
            assert describe_composition(config, 'TabWdg')['elements'][0]['interface']['table']['elements'][0]['interface']
        assert not any(path.startswith('custom.') for path in imports), 'metadata imported a widget module'
        # Reading metadata must neither import a custom widget nor poison its SDK cache.
        from tactic_stream.server.interface import describe_view
        custom = WidgetConfigView('sthpw/note', 'table', [WidgetConfig.get(view='table', xml='<config><table><element name="custom"><display class="custom.Unknown"><config><element name="code"/></config></display></element></table></config>')])
        with patch.object(Common, 'resolve_class') as lookup:
            lookup.return_value.has_config.return_value = True
            description = describe_view(custom)
            lookup.assert_not_called()
            assert 'config' in description['elements'][0]['display']['options']
            assert 'config_xml' in custom.get_display_options('custom')
            lookup.assert_called_once_with('custom.Unknown')
            lookup.reset_mock()
            assert describe_view(custom) == description
            lookup.assert_not_called()
        for _ in range(8):
            inline = wrap(inline)
        config = WidgetConfigView('TabWdg', 'tab', [WidgetConfig.get(view='tab', xml=inline)], layout='tactic.ui.container.TabWdg')
        try:
            describe_composition(config, 'TabWdg')
        except ValueError as error:
            assert 'composition limit' in str(error)
        else:
            raise AssertionError('unbounded composition was accepted')
        tree = deepcopy(tree)
        def field_names(table):
            for element in table['elements']:
                if 'interface' in element:
                    child = element['interface']
                    # Physical type spelling, nullability and sizes belong to the vendor.
                    child['columns'] = sorted(child['columns'])
                    field_names(child['table'])
        field_names(tree)
        return tree


class WidgetPreview(unittest.TestCase):
    def test_preview_and_native_boundary(self):
        from test_transport import Transport
        class FixtureServer(Transport):
            pass
        FixtureServer.setUpClass()
        self.addCleanup(FixtureServer.tearDownClass)
        exercise_preview(FixtureServer.store, 'private-test-password')
        token = Api(FixtureServer.store).get_ticket('admin', 'private-test-password')
        def post(action, **options):
            return urlopen(Request(FixtureServer.url + '/admin/widget-configuration/' + action,
                json.dumps(dict(ticket=token, project='admin', search_type='sthpw/note', view='preview_test', **options)).encode(),
                headers={'Content-Type': 'application/json'}))
        with post('read') as response:
            current = json.load(response)['result']
        with post('preview', source_id=current['sources'][0]['id'], xml=current['sources'][0]['xml'], revision=current['revision']) as response:
            self.assertEqual(json.load(response)['result']['interface']['table']['elements'][0]['title'], 'Higher')
        with self.assertRaises(HTTPError) as error:
            post('preview', source_id=None, xml='<config/>', revision='stale')
        self.assertEqual(error.exception.code, 409)
        error.exception.close()
