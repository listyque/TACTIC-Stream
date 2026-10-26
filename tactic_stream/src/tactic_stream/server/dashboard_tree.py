"""Lazy configured hierarchy over native schema relations and object permissions."""
from pyasm.biz import Project, Schema
from pyasm.search import Search, SearchKey, SearchType
from .interface import _require_table_access
from .navigation_links import check_project, check_article_visibility
from tactic_stream.dashboard_plan import DashboardTreeNode

SYSTEM_CHILDREN = ('sthpw/task', 'sthpw/note', 'sthpw/snapshot', 'sthpw/work_hour')


def validate_tree(value: DashboardTreeNode | dict) -> DashboardTreeNode:
    tree = DashboardTreeNode.model_validate(value)
    schema = Schema.get()
    budget = [64]

    def check(node, parent=None, depth=0):
        budget[0] -= 1
        if budget[0] < 0 or depth > 6:
            raise ValueError('Tree supports at most 64 branches and six relation levels')
        if '?' in node.search_type or node.search_type.startswith(('prod/', 'flash/')):
            raise ValueError('Choose a project Search Type or a native linked system type')
        info = SearchType.get(node.search_type)
        if info.get_database() not in (Project.get_project_code(), 'sthpw'):
            raise ValueError('Tree Search Type belongs to another project')
        if info.get_database() == 'sthpw' and node.search_type not in (*SYSTEM_CHILDREN, 'sthpw/file'):
            raise ValueError('Tree system nodes are limited to linked tasks, notes, snapshots, work hours and files')
        _require_table_access(node.search_type)
        if not node.title:
            node.title = info.get_title()
        columns = SearchType.get_column_info(node.search_type)
        if node.title_field and node.title_field not in columns:
            raise ValueError('Tree title requires an existing field')
        if any(row.column not in columns for row in node.filters):
            raise ValueError('Tree filters require existing fields')
        if parent is not None:
            if node.search_type not in SYSTEM_CHILDREN or node.path:
                attrs = schema.get_relationship_attrs(node.search_type, parent.search_type, path=node.path or None)
                if not attrs or attrs.get('disabled'):
                    raise ValueError('Tree branch requires an enabled schema relationship')
        elif info.get_database() == 'sthpw' and 'project_code' not in columns:
            raise ValueError('A system tree root must support project scope')
        for branch in node.branches:
            check(branch, node, depth + 1)
    check_project(Project.get_project_code())
    check(tree)
    return tree


def read_tree(tree: DashboardTreeNode | dict, branch_path: list[int] | None = None,
              parent_key: str = '', offset: int = 0, limit: int = 50) -> dict:
    tree = validate_tree(tree)
    path = [] if branch_path is None else branch_path
    if (not isinstance(path, list) or len(path) > 6
            or any(type(index) is not int or index < 0 for index in path)
            or type(offset) is not int or offset < 0 or offset > 100000
            or type(limit) is not int or not 1 <= limit <= 100
            or not isinstance(parent_key, str) or len(parent_key) > 2048):
        raise ValueError('Invalid tree page')
    node, parent_node = tree, None
    for index in path:
        if index >= len(node.branches):
            raise ValueError('Tree branch no longer exists')
        parent_node, node = node, node.branches[index]
    query = Search(node.search_type)
    if parent_node is not None:
        if (not parent_key or SearchKey.extract_base_search_type(parent_key) != parent_node.search_type
                or SearchKey.extract_project(parent_key) not in ('', None, Project.get_project_code())):
            raise ValueError('Tree parent belongs to another scope')
        parent = Search.get_by_search_key(parent_key)
        if parent is None:
            raise LookupError('Tree parent is no longer available')
        project = parent.get_value('project_code', no_exception=True)
        if project and project != Project.get_project_code():
            raise ValueError('Tree parent belongs to another project')
        check_article_visibility(parent)
        if node.search_type in SYSTEM_CHILDREN and not node.path:
            query.add_parent_filter(parent)
        else:
            query.add_relationship_filter(parent, path=node.path or None)
    elif parent_key:
        raise ValueError('A tree root does not take a parent')
    columns = SearchType.get_column_info(node.search_type)
    if node.search_type.startswith('sthpw/') and 'project_code' in columns:
        query.add_filter('project_code', Project.get_project_code())
    for condition in node.filters:
        query.add_filter(condition.column, condition.value, op=condition.relation)
    if query.joins:
        query.add_group_by(query._column('id'))  # Repeated instance links must not duplicate nodes across pages.
    query.add_order_by('id')
    query.set_offset(offset)
    query.set_limit(limit + 1)
    rows = query.get_sobjects()
    info = SearchType.get(node.search_type)
    result = []
    for row in rows[:limit]:
        check_article_visibility(row)
        title = next((row.get_value(field, no_exception=True) for field in
                      ([node.title_field] if node.title_field else ['name', 'title', 'process', 'code'])
                      if row.get_value(field, no_exception=True) not in ('', None)), row.get_code())
        result.append(dict(key=row.get_search_key(), title=str(title),
            detail=str(row.get_value('status', no_exception=True) or row.get_value('state', no_exception=True) or ''),
            icon=info.get_value('icon', no_exception=True) or 'account-tree'))
    return dict(items=result, has_next=len(rows) > limit, offset=offset, limit=limit)
