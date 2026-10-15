"""Same XML configuration operations in the original and migrated runtime."""
import tempfile
from pathlib import Path
from pyasm.common import Xml
from pyasm.widget import WidgetConfig, WidgetConfigView
from pyasm.search import WidgetDbConfig


def run(case):
    first = WidgetConfig.get(view='table', xml='''<config><table layout="TableWdg">
        <element name="name" width="90"/><element name="code"/></table></config>''')
    second = WidgetConfig.get(view='definition', xml='''<config><definition>
        <element name="name" title="Имя"><display class="CustomDisplay"><value>O'Reilly</value></display></element>
        <element name="amount" title="Amount"><display widget="format"/></element></definition></config>''')
    view = WidgetConfigView('sthpw/note', 'table', [first, second])
    node = view.get_element_node('name', prefer_child_nodes=True)
    result = dict(names=view.get_element_names(), names_with_definitions=view.get_element_names(include_definition=True),
                  attributes=view.get_element_attributes('name'), title=view.get_element_title('name'),
                  display=view.get_display_handler('name'), options=view.get_display_options('name'),
                  selected=Xml.get_attributes(node), views=view.get_views(),
                  widget_handler=view.get_display_handler('amount'))
    with tempfile.TemporaryDirectory() as directory:
        file = Path(directory) / 'views.xml'
        file.write_text('<config><table><element name="first"/></table></config>', encoding='utf-8')
        original = Xml(file_path=str(file))
        file.write_text('<config><table><element name="second"/></table></config>', encoding='utf-8')
        original.read_file(str(file), cache=False)
        result['fresh_file_names'] = original.get_values('config/table/element/@name')
    columns = ['id', 'view', 'priority', 'config']
    high = WidgetDbConfig('config/widget_config', columns, [2, 'table', 20, '<config><table><element name="code" title="Higher"/></table></config>'])
    low = WidgetDbConfig('config/widget_config', columns, [1, 'table', 10, '<config><table><element name="code"><display class="pyasm.widget.TextWdg"/></element></table></config>'])
    merged = WidgetDbConfig.merge_configs([high, low])
    result['merged_handler'] = merged.get_xml().get_value('config/table/element/display/@class')
    result['raw_handler'] = merged.get_xml_value('config').get_value('config/table/element/display/@class')
    outer = WidgetConfig.get(view='table', xml='''<config><table><element name="outer"><display class="tactic.ui.container.TabWdg"><config><element name="inner"><display class="tactic.ui.container.TabWdg"><config><element name="code"/></config></display></element></config></display></element></table></config>''')
    middle = WidgetConfig.get(view='tab', xml=outer.get_display_options('outer')['config_xml'])
    inner = WidgetConfig.get(view='tab', xml=middle.get_display_options('inner')['config_xml'])
    result['nested_inline_names'] = inner.get_element_names()
    panel = WidgetConfig.get(view='table', xml='''<config><table><element name="panel"><display class="tactic.ui.panel.ViewPanelWdg"><search_type>sthpw/note</search_type><search_limit>2</search_limit><order_by>code desc, id asc</order_by><do_initial_search>hidden</do_initial_search><show_refresh>false</show_refresh><show_search_limit>false</show_search_limit></display></element></table></config>''')
    result['panel_options'] = panel.get_display_options('panel')
    return result
