"""Configured parent replacement, with a captured source and column revision."""
from pyasm.command import Command


def edit_parent_group(search_key, view, column, action='prepare', source_revision='',
                      expected_revision='', parent_type='', query='', offset=0,
                      parent_key='', parent_revision='', source_id=None):
    """Self-contained procedure for both clients; writes join the caller's Command."""
    import hashlib
    import json
    import re
    from pyasm.biz import Project
    from pyasm.common import Environment
    from pyasm.search import Search, SearchKey, SearchType
    from pyasm.widget import WidgetConfigView

    if not __import__('pyasm.common', fromlist=['Environment']).Environment.get_security().is_admin() and (not __import__('pyasm.common', fromlist=['Environment']).Environment.get_security().is_logged_in() or __import__('pyasm.common', fromlist=['Environment']).Environment.get_security().get_user_name() == 'admin' or not (__import__('pyasm.biz', fromlist=['Project']).Project.get_project_code() in ('admin', 'sthpw') or __import__('pyasm.common', fromlist=['Environment']).Environment.get_security().check_access('project', [{'code': '*'}, {'code': __import__('pyasm.biz', fromlist=['Project']).Project.get_project_code()}], 'allow', default='deny'))):
        raise PermissionError('Administration requires administrator access')
    if action not in ('prepare', 'candidates', 'save', 'check'):
        raise ValueError('Invalid parent operation')
    if any(not isinstance(value, str) or not value for value in (search_key, view, column)):
        raise ValueError('Choose a configured parent column')
    if not re.fullmatch(r'[A-Za-z_][\w.@-]{0,127}', view) or len(column) > 256:
        raise ValueError('Choose a configured parent column')
    if not isinstance(query, str) or len(query) > 200 or type(offset) is not int or offset < 0:
        raise ValueError('Invalid parent search')
    project = Project.get_project_code()

    def check_key(key):
        if not isinstance(key, str) or not key or SearchKey.extract_project(key) not in (None, '', 'sthpw', 'admin', project):
            raise ValueError('The parent belongs to another project')
        base = SearchKey.extract_base_search_type(key)
        if base in ('sthpw/message', 'sthpw/message_log', 'sthpw/ticket') or base.startswith(('prod/', 'flash/')):
            raise ValueError('This object is not available in parent groups')
        metadata = SearchType.get(base)
        if str(metadata.get_value('class_name') or '').startswith('pyasm.prod.'):
            raise ValueError('This object is not available in parent groups')
        if hasattr(metadata, 'get_record_read_options') and metadata.get_record_read_options().get('command'):
            raise ValueError('This object is not available in parent groups')
        return base

    def revision(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()

    def parent_of(record, missing_ok=False):
        from pyasm.search import SearchException
        related = record.get_value('search_type', no_exception=True)
        if not related:
            return record.get_parent()
        try:
            check_key(related)
        except SearchException:
            if missing_ok:
                return None
            raise LookupError('Parent is no longer available')
        if not SearchKey.extract_project(related):
            related = SearchType.build_search_type(related, record.get_value('project_code', no_exception=True) or project)
        code = record.get_value('search_code', no_exception=True)
        identity = code or record.get_value('search_id', no_exception=True)
        if identity in (None, '', -1, '-1'):
            return None
        return Search.get_by_search_key(SearchKey.build_search_key(related, identity, column='code' if code else 'id'))

    base = check_key(search_key)
    obj = Search.get_by_search_key(search_key)
    if obj is None:
        raise LookupError('Object is no longer available')
    if source_id is not None and str(source_id) != str(obj.get_id()):
        raise LookupError('Object is no longer available')
    if action == 'save':
        sql = obj.get_sql()
        table = SearchType.get(base).get_table()
        lock = getattr(sql.get_database_impl(), 'lock_collection_table', None)
        if lock:
            lock(sql, table)
        elif sql.get_database_type() == 'PostgreSQL':
            sql.do_update('LOCK TABLE "%s" IN EXCLUSIVE MODE' % table.replace('"', '""'))
        else:
            raise ValueError('Parent revisions require a transactional database lock')
    fresh = Search(obj.get_search_type())
    fresh.add_id_filter(obj.get_id())
    obj = fresh.get_sobject()
    if obj is None:
        raise LookupError('Object is no longer available')
    if source_id is not None and str(source_id) != str(obj.get_id()):
        raise LookupError('Object is no longer available')
    if obj.get_value('project_code', no_exception=True) not in (None, '', project):
        raise ValueError('Open parent editing in the source project')
    config = WidgetConfigView.get_by_search_type(base, view, use_cache=False)
    if column not in config.get_element_names() or config.get_action_handler(column) not in (
            'ParentGroupAction', 'tactic.ui.table.ParentGroupAction', 'tactic.ui.table.group_element_wdg.ParentGroupAction'):
        raise ValueError('The configured parent action changed. Reload before saving.')
    if config.get_action_options(column):
        raise ValueError('Unsupported parent action options')
    definition = [config.get_display_handler(column), config.get_display_options(column),
                  config.get_action_handler(column), config.get_action_options(column)]
    current = revision([obj.get_data(), definition])
    if action == 'prepare' and source_revision and revision(obj.get_data()) != source_revision:
        raise ValueError('Parent changed. Reload before saving.')
    parent = parent_of(obj, missing_ok=True)
    current_key = parent.get_search_key() if parent else ''
    schema = obj.get_schema()

    def allowed_type(value):
        target = check_key(value)
        declared = schema.get_parent_type(base)
        if declared not in ('*', target):
            raise ValueError('The configured parent relationship is unavailable')
        if schema.get_relationship(base, target) not in (
                'search_type', 'search_code', 'search_id', 'foreign_key', 'code', 'id', 'parent_code', 'search_key'):
            raise ValueError('The configured parent relationship is unavailable')
        return target

    def candidate(record):
        return dict(searchKey=record.get_search_key(), code=record.get_code() or '',
            title=record.get_value('name', no_exception=True) or record.get_value('title', no_exception=True)
                or record.get_code() or str(record.get_id()), retired=record.is_retired(), revision=revision(record.get_data()))

    if action == 'prepare':
        types = {}
        for metadata in Search('sthpw/search_object').get_sobjects():
            value = metadata.get_value('search_type') or metadata.get_code()
            try:
                target = allowed_type(value)
            except ValueError:
                continue
            types[target] = dict(value=target, label=metadata.get_value('title') or target)
        types = list(types.values())
        types.sort(key=lambda item: (item['label'].casefold(), item['value']))
        selected = None
        if parent_key:
            allowed_type(parent_key)
            chosen = Search.get_by_search_key(parent_key)
            if chosen is None:
                raise LookupError('Parent is no longer available')
            selected = candidate(chosen)
        return dict(expectedRevision=current, sourceRevision=revision(obj.get_data()), sourceId=str(obj.get_id()),
            sourceTitle=obj.get_value('name', no_exception=True) or obj.get_value('title', no_exception=True)
                or obj.get_code() or str(obj.get_id()), parentTypes=types,
            currentParentKey=current_key, currentParent=candidate(parent) if parent else None, selectedParent=selected,
            parentType=SearchKey.extract_base_search_type(parent_key or current_key) if parent_key or current_key else '')
    if action == 'candidates':
        if not expected_revision or expected_revision != current:
            raise ValueError('Parent changed. Reload before saving.')
        target = allowed_type(parent_type)
        search = Search(SearchType.build_search_type(target, project))
        if SearchType.column_exists(target, 'project_code'):
            search.add_filter('project_code', project)
        if target == base:
            search.add_filter('id', obj.get_id(), '!=')
        if query:
            fields = [name for name in ('code', 'name', 'title') if SearchType.column_exists(target, name)]
            if fields:
                search.add_op('begin')
                for name in fields:
                    search.add_regex_filter(name, re.escape(query))
                search.add_op('or')
            else:
                search.add_id_filter(int(query) if query.isdecimal() else -1)
        search.add_order_by('code' if SearchType.column_exists(target, 'code') else 'id')
        search.set_offset(offset)
        search.set_limit(51)
        records = search.get_sobjects()
        return dict(rows=[candidate(record) for record in records[:50]], offset=offset, hasNext=len(records) > 50)
    allowed_type(parent_key)
    chosen = Search.get_by_search_key(parent_key)
    if chosen is None:
        raise LookupError('Parent is no longer available')
    if chosen.get_value('project_code', no_exception=True) not in (None, '', project):
        raise ValueError('The parent belongs to another project')
    if chosen.get_search_key() == current_key:
        return dict(state='saved', searchKey=obj.get_search_key())
    if action == 'check':
        return dict(state='unchanged' if expected_revision == current else 'conflict')
    if not expected_revision or expected_revision != current or not parent_revision or parent_revision != revision(chosen.get_data()):
        raise ValueError('Parent changed. Reload before saving.')
    if chosen.is_retired():
        raise ValueError('Choose a current parent')
    ancestor, visited = chosen, {obj.get_search_key()}
    while ancestor is not None:
        identity = ancestor.get_search_key()
        if identity in visited:
            raise ValueError('Parent relationship is cyclic')
        visited.add(identity)
        ancestor = parent_of(ancestor)
    obj.add_relationship(chosen)
    obj.commit()
    return dict(state='saved', searchKey=obj.get_search_key())


class TableParentGroupCmd(Command):
    def execute(self):
        self.info = edit_parent_group(**self.kwargs)
        return self.info
