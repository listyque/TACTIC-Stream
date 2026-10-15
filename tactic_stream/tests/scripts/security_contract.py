"""The same native-account server script runs unchanged in both kernels."""
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security import Login, LoginGroup, LoginInGroup, Security, Ticket, Sudo


def policy(security, case):
    security._login = Search.get_by_code('sthpw/login', case.get('login', 'artist'))
    security.setup_access_manager()
    manager = security.get_access_manager()
    manager.add_xml_rules(case.get('rules', '<rules/>'))
    operation = case['policy']
    try:
        if operation in ('rows', 'count', 'rows_count', 'count_rows', 'permission'):
            search = Search(case.get('search_type', 'contract/entity'), **case.get('search_options', {}))
            search.set_show_retired(case.get('show_retired', False))
            for args in case.get('filters', []):
                search.add_filter(*args)
            if 'limit' in case:
                search.set_limit(case['limit'])
            if operation == 'permission':
                search.check_security()
                return {'allowed': True}
            def rows():
                return [obj.get_code() for obj in search.get_sobjects()]
            if operation == 'rows':
                return {'rows': rows(), 'filtered': search.security_filter}
            if operation == 'count':
                return {'count': search.get_count(), 'filtered': search.security_filter}
            if operation == 'rows_count':
                values = rows()
                return {'rows': values, 'count': search.get_count(), 'filtered': search.security_filter}
            count = search.get_count()
            return {'count': count, 'rows': rows(), 'filtered': search.security_filter}
        sudo = Sudo()
        try:
            if case.get('new'):
                obj = SearchType.create(case.get('search_type', 'contract/entity'))
            else:
                obj = Search.get_by_code(case.get('search_type', 'contract/entity'), case.get('code', 'A'))
        finally:
            sudo.exit()
        if operation == 'cache_policy':
            fetched = Search.get_by_code(case.get('search_type', 'contract/entity'), case.get('code', 'A'))
            return {'fetched': fetched.get_code() if fetched else None, 'same': fetched is obj,
                    'admin': security.is_admin()}
        if operation == 'commit_security':
            return {'allowed': obj.handle_commit_security(), 'base_access': obj.check_access('edit')}
        if operation == 'delete_sql':
            from pyasm.search import Transaction
            transaction = Transaction.get(create=True)
            result = obj.delete(return_sql=True, **case.get('kwargs', {}))
            return {'sql': result, 'journal': transaction.get_transaction_log().to_string(),
                    'data': obj.get_data()}
        if operation == 'field':
            result = obj.set_value(case.get('column', 'name'), case.get('value', 'changed'), **case.get('kwargs', {}))
            if case.get('statement'):
                result = obj.get_statement()
            return {'value': result, 'data': obj.get_data(), 'update': obj.update_data.copy(),
                    'admin': security.is_admin()}
        raise ValueError(operation)
    except Exception as error:
        return {'error': type(error).__name__, 'message': str(error)}


def account(obj):
    if obj is None:
        return None
    return {'class': type(obj).__name__, 'code': obj.get_code(), 'id': obj.get_id(),
            'key': obj.get_search_key(), 'primary': obj.get_primary_key(), 'foreign': obj.get_foreign_key()}


def run(case):
    previous = Environment.get_security()
    security = Security()
    Environment.set_security(security)
    try:
        operation = case['operation']
        if operation == 'policy':
            security._is_logged_in = 1
            return policy(security, case)
        search = Search('sthpw/login')
        search.add_filter('login', 'admin')
        security._login = search.get_sobject()
        security._is_logged_in = 1
        if operation == 'call':
            classes = {'Login': Login, 'LoginGroup': LoginGroup, 'LoginInGroup': LoginInGroup, 'Ticket': Ticket}
            owner = classes[case['owner']]
            if 'code' in case:
                owner = Search.get_by_code(owner.SEARCH_TYPE, case['code'])
            try:
                result = getattr(owner, case['function'])(*case.get('args', []), **case.get('kwargs', {}))
                if isinstance(result, list) and result and hasattr(result[0], 'get_data'):
                    return [account(obj) for obj in result]
                return account(result) if hasattr(result, 'get_data') else result
            except Exception as error:
                return {'error': type(error).__name__, 'message': str(error)}
        if operation == 'defaults':
            obj = SearchType.create(case['search_type'])
            for name, value in case['data'].items():
                obj.set_value(name, value, temp=True)
            return {'class': type(obj).__name__, 'defaults': obj.get_defaults()}
        if operation == 'cache':
            first = Login.get_by_login(case['login'], **case['first'])
            second = Login.get_by_login(case['login'], **case['second'])
            return {'first': account(first), 'second': account(second), 'same': first is second}
        if operation == 'security':
            security.sign_out()
            search = Search('sthpw/login')
            search.add_filter('login', case['login'])
            security._login = search.get_sobject()
            security._ticket = Ticket.get_by_key('contract-ticket')
            security._do_login()
            values = {'logged': security.is_logged_in(), 'user': Environment.get_user_name(),
                'ticket': Environment.get_ticket(), 'names': security.get_group_names(),
                'groups': [group.get_login_group() for group in security.get_groups()],
                'admin': security.is_admin(), 'start': security.get_start_link(),
                'checks': {name: security.is_in_group(name) for name in ['artists', 'production', 'admin', 'missing']}}
            values['default_access'] = security.get_access('missing', 'key', default='deny')
            if case.get('reset'):
                security.reset_access_manager()
            values['admin_after_reset'] = security.is_admin()
            if case.get('clear_ticket'):
                security.clear_ticket()
            values['ticket_after_clear'] = Environment.get_ticket()
            security.sign_out()
            values['admin_after_signout'] = security.is_admin()
            values['groups_after_signout'] = security.get_group_names()
            return values
        raise ValueError(operation)
    finally:
        Environment.set_security(previous)
