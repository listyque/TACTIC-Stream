"""Native object selections and relationships, using TACTIC's schema and commands."""
from pyasm.command import Command
from pyasm.search import Search, SearchKey, SearchType
from tactic.ui.tools import DeleteCmd
from tactic_stream.server.interface import _require_table_access, read_interface


def selected_objects(search_type, search_keys):
    _require_table_access(search_type, 'view')
    if isinstance(search_keys, str):
        search_keys = [search_keys]
    if not isinstance(search_keys, list) or not 1 <= len(search_keys) <= 500 or any(not isinstance(key, str) or not key for key in search_keys):
        raise ValueError('Select between 1 and 500 objects')
    for key in search_keys:
        data = SearchType.breakup_search_type(key)
        if not data.get('namespace') or not data.get('table') or not (data.get('code') or data.get('id')):
            raise ValueError('Select objects using their code or id search keys')
    base = SearchType.get(search_type).get_base_key()
    from pyasm.biz import Project
    records = {}
    for search_key in search_keys:
        if SearchKey.extract_base_search_type(search_key) != base:
            raise ValueError('Search key does not belong to this search type')
        project = SearchKey.extract_project(search_key)
        if project and project != Project.get_project_code():
            raise ValueError('Select the target project before changing its objects')
        record = Search.get_by_search_key(search_key)
        if not record:
            raise LookupError('Object no longer exists')
        records[record.get_id()] = record
    return list(records.values())


def read_relations(search_type, search_key):
    parent = selected_objects(search_type, [search_key])[0]
    base = parent.get_base_search_type()
    schema = parent.get_schema()
    relations = []
    for child_type in dict.fromkeys(SearchType.get_related_types(base)):
        child = SearchType.get(child_type)
        attrs = schema.get_relationship_attrs(child_type, base)
        relationship = attrs.get('relationship')
        available = bool(attrs) and not attrs.get('disabled') and child_type != base and not attrs.get('prefix')
        available = available and attrs.get('from') == child_type and attrs.get('to') in (base, '*')
        available = available and relationship in ('code', 'id', 'search_type', 'search_code', 'search_id')
        relations.append(dict(search_type=child_type, title=child.get_value('title') or child_type,
                              relationship=relationship, available=available,
                              can_create=available and child_type not in ('sthpw/file', 'sthpw/snapshot')))
    return dict(search_key=parent.get_search_key(use_id=True), relations=relations)


def read_deletion(search_type, search_key, view='table'):
    records = selected_objects(search_type, search_key)
    definition = read_interface(search_type, view)
    if not definition['operations']['delete']:
        raise ValueError('Deletion is unavailable in this view')
    return dict(search_key=records[0].get_search_key(), search_keys=[record.get_search_key() for record in records],
                search_type=SearchType.get(search_type).get_base_key(), groups=deletion_groups(records))


def deletion_groups(records):
    base = records[0].get_base_search_type()
    groups = []
    for related_type in dict.fromkeys(SearchType.get_related_types(base, direction='children')):
        if related_type in (base, 'sthpw/file'):
            continue
        related = {item.get_id(): item for record in records
                   for item in record.get_related_sobjects(related_type, show_retired=True)}
        if related:
            groups.append(dict(search_type=related_type, title=SearchType.get(related_type).get_title(),
                               count=len(related), selected=related_type in ('sthpw/note', 'sthpw/task', 'sthpw/snapshot', 'sthpw/status_log'),
                               items=[dependency_item(item) for item in related.values()]))
    return groups


def dependency_item(item):
    from .object_report import record
    data = record(item)
    transition = ''
    if item.get_base_search_type() == 'sthpw/status_log':
        before, after = data.get('from_status'), data.get('to_status')
        transition = f'{before} → {after}' if before and after and before != after else after or before or data.get('status') or ''
    title = transition or next((str(data[name]) for name in (
        'file_name', 'filename', 'name', 'title', 'description', 'note', 'process', 'context', 'status'
    ) if data.get(name)), data.get('code') or item.get_search_key())
    names = ('process', 'context', 'login', 'timestamp') if transition else (
        'description', 'note', 'context', 'process', 'status', 'assigned', 'login', 'timestamp')
    details = list(dict.fromkeys(str(data[name]) for name in names if data.get(name) and str(data[name]) != title))
    return dict(title=title, details=' · '.join(details if transition else details[:2]), searchKey=item.get_search_key())


def delete_object(search_type, search_key, related_types, view='table'):
    if not isinstance(related_types, list) or any(not isinstance(value, str) for value in related_types):
        raise ValueError('Invalid related types')
    definition = read_deletion(search_type, search_key, view)
    allowed = {group['search_type'] for group in definition['groups']}
    if set(related_types) - allowed:
        raise ValueError('Dependency selection changed. Reopen the deletion dialog.')
    # The source type prevents DeleteCmd's empty-selection default from deleting other groups.
    command = DeleteCmd(search_keys=definition['search_keys'],
                        values=dict(related_types=[definition['search_type'], *dict.fromkeys(related_types)]))
    command.get_transaction().set_sync(False)
    Command.execute_cmd(command)
    return dict(status='OK', search_key=definition['search_key'], search_keys=definition['search_keys'])


class ObjectStatusCmd(Command):
    """Apply the original SObject status methods in one Command transaction."""

    def execute(self):
        operation = self.kwargs.get('operation')
        if operation not in ('retire', 'reactivate'):
            raise ValueError('Invalid object status operation')
        search_type = self.kwargs['search_type']
        records = selected_objects(search_type, self.kwargs.get('search_keys'))
        definition = read_interface(search_type, self.kwargs.get('view', 'table'))
        if not definition['operations']['retire']:
            raise ValueError('Retirement is unavailable in this view')
        count = 0
        for record in records:
            if record.is_retired() == (operation == 'retire'):
                continue
            if operation == 'retire':
                record.retire()
            else:
                record.reactivate()
            count += 1
        self.add_description('%s: %s objects' % (operation, count))
        return dict(status='OK', count=count)
