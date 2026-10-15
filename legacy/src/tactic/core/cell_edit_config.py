"""CellEditWdg config resolution, without rendering any legacy HTML.

Provenance: tactic/ui/panel/layout_wdg.py: CellEditWdg.init. The edit
configuration and the table's SAVE configuration are deliberately separate.
"""
from .config_model import ConfigModel


def cell_config(search_type, config_xml=None):
    from .widget_config import WidgetConfigView, WidgetConfig
    from pyasm.search import WidgetDbConfig
    # Do not mutate the cached WidgetConfigView: another table may have different
    # inline options in the very same request.
    source = WidgetConfigView.get_by_search_type(search_type, 'edit', use_cache=False)
    config = WidgetConfigView(search_type=search_type, view='edit', configs=list(source.get_configs()))
    if config_xml:
        config.get_configs().insert(0, WidgetConfig.get(view='edit', xml=config_xml))
    override = WidgetDbConfig.get_by_search_type(search_type, 'edit_item')
    if override:
        config.get_configs().insert(0, override)
    return config


def save_config(search_type, names, view='edit_item', config_xml=None):
    """Same config branches as EditCmd._get_action_handlers for changed fields."""
    from .widget_config import WidgetConfigView, WidgetConfig
    if config_xml:
        config = WidgetConfigView.get_by_search_type(search_type, view, use_cache=False)
        config = WidgetConfigView(search_type=search_type, view=view, configs=list(config.get_configs()))
        config.get_configs().insert(0, WidgetConfig.get(view='tab', xml=config_xml))
        config.get_configs().insert(0, WidgetConfig.get(view='edit', xml=config_xml))
        return config
    # get_by_element_names mutates its cached source. Reproduce that branch on
    # a fresh container so several edited rows cannot contaminate one another.
    from pyasm.search import WidgetDbConfig
    import xml.etree.ElementTree as ET
    base = WidgetConfigView.get_by_search_type(search_type, view, use_cache=False)
    config = WidgetConfigView(search_type=search_type, view=view, configs=list(base.get_configs()))
    definition = WidgetDbConfig.get_by_search_type(search_type, 'edit_definition')
    if definition:
        config.get_configs().insert(0, definition)
    root = ET.Element('config')
    order = ET.SubElement(root, 'custom', layout='TableLayoutWdg')
    for name in names:
        ET.SubElement(order, 'element', name=name)
    config.get_configs().insert(0, WidgetConfig.get(view='custom', xml=ET.tostring(root, encoding='unicode')))
    config._native_generated_order = True
    return config


class CellConfigModel(ConfigModel):
    """Expose resolved EDIT handlers, not the table's DISPLAY or EditWdg view."""
    def __init__(self, config, actions, names):
        projected = ConfigModel.from_tactic(config)
        super().__init__('edit', projected.sources, projected.aliases)
        self.config, self.action_config, self.requested_names = config, actions, list(names)

    def names(self):
        return list(self.requested_names)

    def describe(self, name):
        item = super().describe(name)
        # The original getter resolves <edit> and historical <display> fallbacks
        # per layer. Flattening just the first XML block is not equivalent.
        handler = self.config.get_edit_handler(name) or ''
        options = self.config.get_options(name, 'edit')
        item.update(handler=handler, options=options, edit_handler=handler,
                    edit_options=options,
                    action_handler=self.action_config.get_action_handler(name),
                    action_options=self.action_config.get_action_options(name))
        return item

    def fingerprint(self):
        import hashlib
        projected = ConfigModel.from_tactic(self.action_config)
        if getattr(self.action_config, '_native_generated_order', False):
            # A request for a second cell must have the SAME definition revision.
            # Synthetic selected-field order is not a configuration change.
            projected.sources = projected.sources[1:]
        other = projected.fingerprint()
        return hashlib.sha256((super().fingerprint()+other).encode()).hexdigest()
