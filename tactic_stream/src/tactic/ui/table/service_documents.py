"""Read-only documents opened by configured table actions."""
from pyasm.command import Command


def read_group_summary(search_key):
    from pyasm.common import Environment
    from pyasm.search import Search, SearchKey
    if not Environment.get_security().is_admin():
        raise PermissionError('Administration requires administrator access')
    if SearchKey.extract_base_search_type(search_key) != 'sthpw/login':
        raise ValueError('Select a user before opening the security summary')
    user = Search.get_by_search_key(search_key)
    if user is None:
        raise ValueError('User is no longer available')
    memberships = Search('sthpw/login_in_group')
    memberships.add_filter('login', user.get_value('login'))
    groups = sorted({row.get_value('login_group') for row in memberships.get_sobjects()})
    sections = []
    for code in groups:
        search = Search('sthpw/login_group')
        search.add_filter('login_group',code)
        group = search.get_sobject()
        if group:
            sections.append(dict(title=code, text=group.get_value('access_rules') or '<rules/>', syntax='xml'))
    return dict(title='Security Summary', identity=user.get_value('display_name') or user.get_value('login'), sections=sections)


class TableDocumentReadCmd(Command):
    def execute(self):
        self.info = read_group_summary(**self.kwargs)
        return self.info
