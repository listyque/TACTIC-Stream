"""Read-only native user rule resolution, with source groups and membership paths."""


def effective_security(login_name, inspect_tools=None, targets=None, builtin=None):
    from pyasm.common import Environment
    from pyasm.security import AccessManager, Login
    from pyasm.security.security import Security

    caller = Environment.get_security()
    if not caller or not caller.is_admin():
        raise PermissionError('TACTIC administrator access is required')
    if not isinstance(login_name, str) or not login_name or len(login_name) > 256:
        raise ValueError('Choose an active user')
    login = Login.get_by_login(login_name)
    if not login or login.is_retired():
        raise ValueError('Choose an active user')
    direct = login.get_sub_group_names()
    subject = Security()
    subject._login = login
    # No ticket, impersonation RPC, writes or caller-manager mutation.
    Environment.set_security(subject)
    try:
        subject._do_login()
        manager = subject.get_access_manager()
        groups = subject.get_groups()
        paths = {}
        by_name = {group.get_login_group(): group for group in groups if group.get_id() != -1}

        def visit(name, path):
            if name in paths or name not in by_name:
                return
            route = path + [name]
            paths.setdefault(name, []).append(route)
            for child in by_name[name].get_sub_group_names():
                visit(child, route)

        for name in direct:
            visit(name, [])
        memberships, sources = [], {}
        tool_manager = AccessManager() if subject.is_admin() else None
        for group in groups:
            name = group.get_login_group()
            default = group.get_id() == -1
            memberships.append(dict(name=name, direct=name in direct, default=default,
                paths=paths.get(name, []), accessLevel=group.get_value('access_level', no_exception=True),
                project=group.get_value('project_code', no_exception=True) or ''))
            own = AccessManager()
            own.add_xml_rules(group)
            if tool_manager is not None:
                tool_manager.add_xml_rules(group)
            for scope, rules in own.groups.items():
                for key, entry in rules.items():
                    access = entry if key == '__DEFAULT__' else entry[0]
                    sources.setdefault((scope, key), []).append(dict(group=name, access=access,
                        default=default, paths=paths.get(name, [])))
        rows, compiled = [], dict(manager.groups)
        if tool_manager is not None:
            for scope in ('agent_tool', 'mcp_tool'):
                if scope in tool_manager.groups:
                    compiled[scope] = tool_manager.groups[scope]
        for scope, rules in sorted(compiled.items()):
            for key, entry in sorted(rules.items()):
                access = entry if key == '__DEFAULT__' else entry[0]
                attributes = {} if key == '__DEFAULT__' else entry[1]
                rows.append(dict(scope=scope, key=key, access=access or '', attributes=attributes,
                    sources=sources.get((scope, key), [])))
        result = dict(login=login.get_login(), title=login.get_full_name() or login.get_login(),
                      administrator=subject.is_admin(), groups=memberships, rules=rows)
        checks = []
        from pyasm.biz import Project
        project = Project.get_project_code()
        for scope in ('project', 'search_type', 'link', 'gear_menu', 'process', 'tasks', 'builtin'):
            catalog = (targets or {}).get(scope, []) if scope != 'builtin' else [
                dict(label=entry['title'], attributes=dict(key=entry['key'])) for entry in builtin or []]
            for entry in catalog:
                if entry.get('all'):
                    continue
                attrs = {key: value for key, value in entry['attributes'].items() if key != 'project'}
                wildcard = {key: '*' for key in attrs}
                native_scope = 'process' if scope == 'tasks' else scope
                if scope == 'project':
                    keys = [attrs, wildcard]
                elif scope == 'tasks':
                    keys = [dict(process='*', pipeline=attrs['pipeline']), wildcard, attrs]
                elif scope == 'gear_menu':
                    keys = [dict(wildcard, project=project), dict(attrs, project=project)]
                elif scope == 'search_type':
                    keys = [attrs, dict(attrs, project=project), wildcard, dict(wildcard, project=project)]
                elif scope == 'builtin':
                    keys = [dict(attrs, project=project), dict(attrs, project='*')]
                else:
                    keys = [dict(attrs, project=project), dict(attrs, project='*'),
                            dict(wildcard, project=project), dict(wildcard, project='*')]
                levels = ('allow',) if scope in ('project', 'link', 'gear_menu', 'builtin') else ('view', 'edit', 'insert', 'retire', 'delete')
                for level in levels:
                    checks.append(dict(scope=scope, label=entry['label'], attributes=entry['attributes'],
                        required=level, allowed=subject.check_access(native_scope, keys, level,
                            default='edit' if scope == 'builtin' else 'deny')))
        result['checks'] = checks
        if inspect_tools:
            result['tools'] = inspect_tools(subject)
        return result
    finally:
        Environment.set_security(caller)
