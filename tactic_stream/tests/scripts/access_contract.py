"""Unchanged server script, executed in both kernels on private data.

ContractSecurity below is a test double for the original Security protocol.
It checks rule/Sudo mechanics, not login authentication or group discovery.
"""
import copy

from pyasm.common import Common, Container, Environment, Xml
from pyasm.search import SearchType
from pyasm.security import AccessManager, AccessRule, AccessRuleBuilder, AccessRuleInGroup, Sudo


class ContractLogin:
    def __init__(self, name):
        self.name = name

    def get_login(self):
        return self.name


class ContractSecurity:
    def __init__(self, name, groups, logged_in=True):
        self._login = ContractLogin(name) if name else None
        self._group_names = list(groups)
        self._groups = []
        self._is_logged_in = logged_in
        self.discoveries = 0
        self.access_manager = AccessManager()

    def _find_all_login_groups(self):
        self.discoveries += 1

    def is_in_group(self, name):
        return name in self._group_names

    def get_user_name(self):
        return self._login.get_login() if self._login else None

    def get_login(self):
        return self._login

    def get_group_names(self):
        return self._group_names

    def is_logged_in(self):
        return self._is_logged_in

    def get_ticket_key(self):
        return 'private-contract-ticket'

    def get_access_manager(self):
        return self.access_manager

    def alter_search(self, search):
        return self.access_manager.alter_search(search)


def run(case):
    operation = case['operation']
    if operation == 'builder':
        builder = AccessRuleBuilder(Xml(case['xml']) if case.get('xml_object') else case.get('xml'))
        results = []
        for step in case['steps']:
            try:
                value = getattr(builder, step['method'])(*step.get('args', []), **step.get('kwargs', {}))
                result = {'value': value}
            except Exception as error:
                result = {'error': type(error).__name__, 'message': str(error)}
            result['xml'] = builder.to_string()
            results.append(result)
        return results
    if operation == 'xml':
        xml = Xml(case['xml'])
        return {path: [node if isinstance(node, str) else Xml.get_attributes(node)
                       for node in xml.get_nodes(path)] for path in case['paths']}
    if operation == 'lookup':
        groups = [SearchType.create('contract/entity', ['login_group'], [name]) for name in case['groups']]
        rules = AccessRule.get_by_groups(groups)
        connectors = AccessRuleInGroup.get_by_groups(groups)
        return {'rules': [obj.get_data() for obj in rules],
                'connectors': [obj.get_data() for obj in connectors],
                'keys': [AccessRule('sthpw/access_rule').get_primary_key(), AccessRule('sthpw/access_rule').get_foreign_key()]}
    if operation == 'manager':
        manager = AccessManager()
        results = []
        for step in case['steps']:
            args = copy.deepcopy(step.get('args', []))
            try:
                if step.get('sobject'):
                    obj = SearchType.create('contract/entity', ['access_rules', 'project_code'], args)
                    value = manager.add_xml_rules(obj)
                elif step['method'] == 'get_by_group':
                    obj = SearchType.create('contract/entity', ['access_rules', 'project_code'], args)
                    manager = AccessManager.get_by_group(obj)
                    value = None
                else:
                    value = getattr(manager, step['method'])(*args, **step.get('kwargs', {}))
                result = {'value': value, 'args_after': args}
            except Exception as error:
                result = {'error': type(error).__name__, 'message': str(error)}
            result['groups'] = manager.groups
            result['summary'] = manager.get_access_summary()
            result['xml'] = manager.to_string()
            results.append(copy.deepcopy(result))
        return results
    if operation == 'sudo':
        previous = Environment.get_security()
        previous_counter = Container.get('Sudo::is_sudo')
        security = ContractSecurity(case.get('login', 'artist'), case.get('groups', []), case.get('logged_in', True))
        Environment.set_security(security)
        Container.remove('Sudo::is_sudo')
        manager = security.access_manager
        sudos = []
        results = []
        try:
            for step in case['steps']:
                method = step['method']
                if method == 'enter':
                    sudos.append(Sudo())
                    value = None
                elif method == 'exit':
                    value = sudos[step['index']].exit()
                else:
                    value = getattr(manager, method)(*step.get('args', []))
                results.append(copy.deepcopy({'value': value, 'sudo': Sudo.is_sudo(),
                    'count': Container.get('Sudo::is_sudo'), 'admin': manager.is_admin(),
                    'was_admin': manager.was_admin, 'groups': Environment.get_group_names(),
                    'user': Environment.get_user_name(), 'ticket': Environment.get_ticket(),
                    'discoveries': security.discoveries, 'app': Environment.get_app_name()}))
            return results
        finally:
            for sudo in sudos:
                sudo.exit()
            Environment.set_security(previous)
            if previous_counter is None:
                Container.remove('Sudo::is_sudo')
            else:
                Container.put('Sudo::is_sudo', previous_counter)
    if operation == 'common':
        Container.remove('contract:counter')
        values = [Container.decrement('contract:counter'), Container.increment('contract:counter'),
                  Container.increment('contract:counter'), Container.decrement('contract:counter')]
        return {'counter': values, 'sorted': Common.get_dict_list(case['data'])}
    raise ValueError(operation)
