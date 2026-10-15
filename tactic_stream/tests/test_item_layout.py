"""Layout authoring uses native configs, revision checks and bounded composition."""
import copy
import tempfile
import unittest
from pathlib import Path

from pyasm.search import Search
from pyasm.search.search import RequestContext, request_context
from pyasm.search.storage import Store
from pyasm.security.authenticator import hash_password
from pyasm.widget import WidgetConfig, WidgetConfigView
from tactic_stream.server.api import Api
from tactic_stream.server.interface import describe_view, read_interface
from tactic_stream.server.item_layout import describe_item_layout, layout_templates
from tactic_stream.server.widget_configuration import (
    read_widget_configuration, preview_widget_configuration, save_widget_configuration, WidgetConfigConflict)


class ItemLayouts(unittest.TestCase):
    def test_templates_and_validation(self):
        with request_context(RequestContext(None, 'admin', 'admin')):
            self.check_templates()

    def check_templates(self):
        for template in layout_templates():
            view = {'continuous':'continuous_example','table':'table_example','cards':'cards_example'}.get(template['name'],'custom_view')
            config = WidgetConfig.get(view=view, xml=template['xml'], use_cache=False)
            descriptor = describe_view(WidgetConfigView('sthpw/note', view, [config]))
            layout = describe_item_layout(descriptor)
            self.assertIn(layout['collection'], ('tree', 'grid', 'table'))
            if template['name'] == 'continuous':
                self.assertEqual(layout['flow'], 'contents')
                self.assertIn('snapshot-details', [item['kind'] for item in layout['elements']])
            if template['name'] == 'cards':
                cards = descriptor
        for mutate in (
            lambda item: item['display']['options'].update(bind='node.__proto__.name'),
            lambda item: item['display']['options'].update(script='alert(1)'),
            lambda item: item['display'].update(handler='custom.PythonWidget'),
            lambda item: item['attributes'].update(parent='missing'),
            lambda item: item['attributes'].update(span='13'),
            lambda item: item['attributes'].update(layer='101'),
            lambda item: item['attributes'].update(layer='1.5'),
            lambda item: item['attributes'].update(role='arbitrary-class'),
            lambda item: item['attributes'].update(tag='script'),
            lambda item: item['attributes'].update(flow='unknown'),
            lambda item: item['attributes'].update(when='unknown'),
        ):
            invalid = copy.deepcopy(cards)
            mutate(invalid['elements'][0])
            with self.assertRaises(ValueError):
                describe_item_layout(invalid)
        overlap = copy.deepcopy(cards)
        image, title = overlap['elements'][:2]
        title['attributes'].update(row='1', column='1', layer='5')
        image['attributes'].update(layer='-1')
        layered = describe_item_layout(overlap)['elements']
        self.assertEqual([item['layer'] for item in layered[:2]], [-1, 5])
        self.assertEqual(layered[0]['row'], layered[1]['row'])
        self.assertEqual(layered[0]['column'], layered[1]['column'])

    def test_native_save_preview_inheritance_and_reuse(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory))
            store.initialize(hash_password('layout-test-password'))
            api = Api(store)
            token = api.get_ticket('admin', 'layout-test-password')
            services = []
            for view in ('quick_filters@cg/assets@th_assets', 'quick_filters@plain'):
                xml = '<config><view name="%s"><values type="json">{}</values></view></config>' % view
                record = api.dispatch('insert', (dict(ticket=token, project='admin'), 'config/widget_config',
                    dict(search_type='sthpw/note', view=view, category='quick_filters', config=xml)))
                services.append((record['id'], xml))
            with request_context(RequestContext(store, 'admin', 'admin')):
                api.auth.bind_security('admin', token)
                standard = read_interface('sthpw/note')
                self.assertNotIn('item_layout', standard['table'])
                example = read_interface('sthpw/note', 'continuous_example')
                self.assertEqual(example['table']['item_layout']['collection'], 'tree')
                current = read_widget_configuration('sthpw/note', 'my_cards')
                self.assertEqual(current['layout_views'], ['continuous_example','table_example','cards_example'])
                self.assertNotIn('quick_filters@cg/assets@th_assets', current['views'])
                self.assertEqual(standard['views'], ['continuous_example','table_example','cards_example'])
                self.assertEqual(read_interface('sthpw/note','cards_example')['table']['item_layout']['collection'],'grid')
                xml = layout_templates()[1]['xml'].replace('cards_example', 'my_cards')
                count = Search('config/widget_config').get_count()
                draft = preview_widget_configuration('sthpw/note', 'my_cards', None, xml, current['revision'])
                self.assertEqual(draft['interface']['table']['item_layout']['collection'], 'grid')
                self.assertEqual(Search('config/widget_config').get_count(), count)
                saved = save_widget_configuration('sthpw/note', 'my_cards', None, xml, current['revision'])
                self.assertEqual(saved['sources'][0]['xml'], xml)
                self.assertIn('my_cards', read_interface('sthpw/note')['views'])
                self.assertEqual(saved['layout_views'], ['continuous_example','table_example','cards_example','my_cards'])
                with self.assertRaises(WidgetConfigConflict):
                    save_widget_configuration('sthpw/note', 'my_cards', None, xml, current['revision'])
                reusable = '<config><my_widget layout="sobject-layout"><element name="cards"><display class="view"><view>my_cards</view></display></element></my_widget></config>'
                widget = read_widget_configuration('sthpw/note', 'my_widget')
                save_widget_configuration('sthpw/note', 'my_widget', None, reusable, widget['revision'])
                nested = read_interface('sthpw/note', 'my_widget')['table']['item_layout']['elements'][0]
                self.assertEqual(nested['widget_layout']['collection'], 'grid')
                cycle = reusable.replace('<view>my_cards</view>', '<view>my_widget</view>')
                widget = read_widget_configuration('sthpw/note', 'my_widget')
                with self.assertRaisesRegex(ValueError, 'Cyclic'):
                    save_widget_configuration('sthpw/note', 'my_widget', widget['sources'][0]['id'], cycle, widget['revision'])
                self.assertEqual(read_widget_configuration('sthpw/note', 'my_widget')['sources'][0]['xml'], reusable)
                item = read_widget_configuration('sthpw/note', 'continuous_example')
                changed = layout_templates()[0]['xml'].replace('title="Title"', 'title="Custom title"')
                save_widget_configuration('sthpw/note', 'continuous_example', None, changed, item['revision'])
                elements = read_interface('sthpw/note', 'continuous_example')['table']['item_layout']['elements']
                self.assertEqual(next(item['title'] for item in elements if item['name']=='title'), 'Custom title')
                for identity, xml in services:
                    service = Search('config/widget_config')
                    service.add_filter('id', identity)
                    self.assertEqual(service.get_sobject().get_value('config'), xml)


if __name__ == '__main__':
    unittest.main()
