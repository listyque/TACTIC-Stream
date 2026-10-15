"""Original WidgetConfig option shapes without importing a display class.

Scalar text is not stripped; nested generic options are dictionaries. Explicit
stock config-bearing handlers retain the original config→config_xml transform.
HTML stays inert text; this module never renders/executes it. A third-party
has_config() implementation is not guessed or executed.
"""
import copy
import xml.etree.ElementTree as ET
CONFIG_HANDLERS={'tactic.ui.container.TabWdg','tactic.ui.panel.EditWdg','tactic.ui.container.ContentBoxWdg','tactic.ui.panel.TableLayoutWdg'}

def serialized(node):
    # Same normalizer as original Xml's lxml backend, not browser HTML parsing.
    from lxml import etree
    node=copy.deepcopy(node);node.tail=None
    root=etree.fromstring(ET.tostring(node,encoding='utf-8'),parser=etree.XMLParser(remove_blank_text=True,resolve_entities=False,no_network=True))
    return etree.tostring(root,pretty_print=True,encoding='unicode')

def recursive(node):
    children=[c for c in node if isinstance(c.tag,str)]
    return {c.tag:recursive(c) for c in children} if children else node.text or ''

def options_from_node(node):
    handler=node.get('class') or ''
    if handler=='tactic.ui.panel.CustomLayoutWdg':
        return {c.tag:(serialized(c).replace('<html>','').replace('</html>','').strip() if c.tag=='html' else (c.text or '').replace('&amp;','&')) for c in node if isinstance(c.tag,str)}
    if handler in CONFIG_HANDLERS:
        result={};view='table' if handler=='tactic.ui.panel.TableLayoutWdg' else 'tab'
        for c in node:
            if not isinstance(c.tag,str):continue
            if c.tag=='config':
                value=serialized(c)
                value=value.replace('<config>',"<config><%s layout='%s'>"%(view,handler) if handler.endswith('.EditWdg') else '<config><%s>'%view)
                result['config_xml']=value.replace('</config>','</%s></config>'%view).strip().replace('&','&amp;')
            else:result[c.tag]=(c.text or '').replace('&amp;','&')
        return result
    value=recursive(node)
    return value if isinstance(value,dict) else {}


def append_option(parent, name, value, depth=0):
    """Write resolved scalar/nested options without turning dicts into repr text.

    XML is data here: element names are checked and values are escaped by ET.
    Unsupported arrays/custom objects are rejected before a config is committed.
    """
    import re
    if depth > 20 or not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,199}", name):
        raise ValueError('Invalid configuration option name/depth')
    node = ET.SubElement(parent, name)
    if isinstance(value, dict):
        if len(value) > 500: raise ValueError('Too many nested options')
        for key, item in value.items(): append_option(node, key, item, depth + 1)
    elif value is None:
        node.text = ''
    elif isinstance(value, bool):
        node.text = 'true' if value else 'false'
    elif isinstance(value, (str, int, float)):
        node.text = str(value)
    else:
        raise ValueError('Unsupported option value: ' + name)
    return node
