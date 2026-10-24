"""SideBarWdg metadata, following Handler NavigationModel.build_project_entries.

Uses the original SidebarConfig resolver; no Python widget or HTML is executed.
"""
import re
from xml.etree import ElementTree as ET

from pyasm.biz import Project
from pyasm.common import Environment, Container
from pyasm.search import WidgetDbConfig
from pyasm.widget import WidgetConfig, WidgetConfigView
from tactic.core.sidebar_config import SidebarConfig


def read_navigation():
    project = Project.get_project_code()
    security = Environment.get_security()
    login = Environment.get_user_name()
    # An explicitly empty Handler view is authoritative, as in Handler.
    stored = WidgetDbConfig.get_by_search_type('SideBarWdg', 'tactic_handler')
    view = 'tactic_handler' if stored is not None else 'project_view'
    if stored is None:
        stored = WidgetDbConfig.get_by_search_type('SideBarWdg', view)
    budget = [256]
    configured = stored is not None
    had_definitions = [False]

    def entries(config, path, views):
        if len(views) > 8:
            raise ValueError('Sidebar nesting limit exceeded')
        result = []
        for name in config.get_element_names():
            budget[0] -= 1
            if budget[0] < 0:
                raise ValueError('Sidebar entry limit exceeded')
            node = config.get_element_node(name, prefer_child_nodes=True)
            if node is None:
                continue
            element = ET.fromstring(ET.tostring(node, encoding='unicode'))
            if element.find('display') is None:
                # Unresolved built-in references do not constitute navigation.
                continue
            had_definitions[0] = True
            attributes = config.get_element_attributes(name)
            if str(attributes.get('is_visible', 'on')).lower() in ('off', 'false', 'no', '0'):
                continue
            # Original SimpleSideBarWdg link checks, including personal defaults.
            keys = [dict(project=project, element=name), dict(element=name),
                    dict(project=project, element='*'), dict(element='*')]
            if not security.check_access('link', keys, 'view', default='view' if name.startswith(login + '.') else 'deny'):
                continue
            options = config.get_display_options(name)
            handler = config.get_display_handler(name).split('.')[-1]
            kind = 'section' if handler == 'SideBarSectionLinkWdg' else 'separator' if handler == 'SeparatorWdg' else 'link'
            item = dict(key='/'.join((*path, name)), name=name, title=config.get_element_title(name),
                        kind=kind, icon=attributes.get('icon') or options.get('icon') or ('folder' if kind == 'section' else 'link'),
                        display=dict(handler=config.get_display_handler(name), options=options),
                        action=dict(handler=config.get_action_handler(name), options=config.get_action_options(name)),
                        default_view_mode='table' if view == 'project_view' else '', children=[])
            if kind == 'section':
                child_view = options.get('view') or element.findtext('view')
                inline = element.findall('element')
                if inline:
                    wrapper = ET.Element('config')
                    container = ET.SubElement(wrapper, 'inline')
                    container.extend(inline)
                    child = WidgetConfig.get(xml=ET.tostring(wrapper, encoding='unicode'), view='inline')
                    child = WidgetConfigView('SideBarWdg', 'inline', [child, *config.get_configs()])
                    item['children'] = entries(child, (*path, name), (*views, 'inline'))
                elif child_view:
                    if not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', child_view):
                        raise ValueError('Invalid sidebar view name')
                    if child_view in views:
                        raise ValueError('Cyclic sidebar view reference: ' + child_view)
                    item['children'] = entries(SidebarConfig.get_config('SideBarWdg', child_view, personal=True), (*path, name, child_view), (*views, child_view))
            result.append(item)
        return result

    previous = Container.get('WidgetConfig:metadata_only')
    try:
        Container.put('WidgetConfig:metadata_only', True)
        result = entries(SidebarConfig.get_config('SideBarWdg', view, personal=True), (view,), (view,))
    finally:
        if previous is None:
            Container.remove('WidgetConfig:metadata_only')
        else:
            Container.put('WidgetConfig:metadata_only', previous)
    return dict(view=view, configured=configured or had_definitions[0], entries=result)
