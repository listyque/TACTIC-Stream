"""Field and sidebar access rules extracted from TableLayoutWdg / panel_wdg."""

def sidebar_allowed(security, project, login, name):
    if security.get_version() == 1:
        return security.check_access('side_bar', name, 'view', default='view')
    keys = [{'project': project, 'element': name}, {'element': name},
            {'project': project, 'element': '*'}, {'element': '*'}]
    return security.check_access('link', keys, 'view', default='view' if name.startswith(login + '.') else 'deny')


def field_access(security, project, search_type, name, attrs):
    keys = [{'search_type': search_type, 'key': name, 'project': project},
            {'search_type': search_type, 'project': project}]
    default = attrs.get('access') or 'edit'
    visible = attrs.get('hidden') not in (True, 'true') and security.check_access('element', keys, 'view', default=default)
    editable = visible and security.check_access('element', keys, 'edit', default=default)
    return bool(visible), bool(editable)
