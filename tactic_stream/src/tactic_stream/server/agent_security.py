"""Group tool restrictions supplement, never replace, native operation rights."""
from pyasm.biz import Project
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from pyasm.security import AccessManager


def tool_access(security, name, transport='chat', manager=None):
    if transport not in ('chat', 'mcp'):
        raise ValueError('Unknown agent transport')
    if not security or not security.is_logged_in():
        return False
    scope = 'mcp_tool' if transport == 'mcp' else 'agent_tool'
    # Administrators normally bypass native rules. Explicit tool restrictions
    # still narrow their external integrations without changing native rights.
    if manager is None:
        manager = tool_rules(security)
    project = Project.get_project_code()
    rules = manager.groups.get(scope, {})
    if not any(key == '__DEFAULT__' or key.endswith('?project=' + project) or
               key.endswith('?project=*') for key in rules):
        return security.is_admin()
    keys = [dict(key=name, project=project), dict(key=name, project='*'),
            dict(key='*', project=project), dict(key='*', project='*')]
    return manager.check_access(scope, keys, 'allow', default='deny')


def tool_rules(security):
    manager = AccessManager()
    for group in security.get_groups():
        manager.add_xml_rules(group)
    return manager


def permissions(security, names, transport='chat'):
    manager = tool_rules(security)
    return [name for name in names if tool_access(security, name, transport, manager)]


def allowed_catalog(transport):
    from .mcp_access import tool_catalog
    catalog = tool_catalog(transport)
    allowed = permissions(Environment.get_security(), [tool['name'] for tool in catalog], transport)
    return [tool for tool in catalog if tool['name'] in allowed]


def require_tool(name, transport='chat'):
    if not isinstance(name, str) or not name or len(name) > 128:
        raise ValueError('Choose a registered agent tool')
    if not tool_access(Environment.get_security(), name, transport):
        raise SecurityException('This tool is not allowed for your groups: ' + name)
