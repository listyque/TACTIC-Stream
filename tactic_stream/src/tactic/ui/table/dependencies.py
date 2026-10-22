"""Snapshot dependency reads without the legacy HTML shell."""
# Adapted from pyasm/widget/dependency_wdg.py, Southpaw Technology; see LICENSE.TACTIC.
from pyasm.command import Command


def read_dependency_node(search_key, offset=0, limit=50, expected_revision='', file_index=None):
    import hashlib
    import json
    from pyasm.biz import FileGroup, FileRange, Project, Snapshot, SObjectNotFoundException
    from pyasm.common import Environment, UserException, Xml
    from pyasm.search import Search, SearchKey

    if not __import__('pyasm.common', fromlist=['Environment']).Environment.get_security().is_admin() and (not __import__('pyasm.common', fromlist=['Environment']).Environment.get_security().is_logged_in() or __import__('pyasm.common', fromlist=['Environment']).Environment.get_security().get_user_name() == 'admin' or not (__import__('pyasm.biz', fromlist=['Project']).Project.get_project_code() in ('admin', 'sthpw') or __import__('pyasm.common', fromlist=['Environment']).Environment.get_security().check_access('project', [{'code': '*'}, {'code': __import__('pyasm.biz', fromlist=['Project']).Project.get_project_code()}], 'allow', default='deny'))):
        raise PermissionError('Administration requires administrator access')
    project = Project.get_project_code()
    if not isinstance(search_key, str) or SearchKey.extract_project(search_key) not in (None, '', 'sthpw', 'admin', project):
        raise ValueError('Open dependencies in the source project')
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError('Invalid dependency page')
    if file_index is not None and (type(file_index) is not int or file_index < 0):
        raise ValueError('Invalid dependency file')

    def check_type(search_type):
        base = SearchKey.extract_base_search_type(search_type)
        if base in ('sthpw/message', 'sthpw/message_log') or base.startswith(('prod/', 'flash/')):
            raise ValueError('This object is not available in Dependencies')
        return base

    def owner(value):
        try:
            return value.get_sobject()
        except SObjectNotFoundException:
            return None

    def concrete(value, source_project=project):
        check_type(value.get_value('search_type'))
        if value.get_value('project_code') != source_project:
            raise ValueError('Open dependencies in the snapshot project')
        if int(value.get_value('version')) > 0:
            return value
        parent = owner(value)
        if parent is None:
            raise LookupError('Snapshot owner is no longer available')
        result = Snapshot.get_snapshot(
            parent.get_search_type(), parent.get_code() or parent.get_id(),
            context=value.get_value('context'), version=int(value.get_value('version')), revision=-1,
            level_type=value.get_value('level_type'), level_id=value.get_value('level_id'),
            process=value.get_value('process') or None, use_cache=False, level_parent_search=False)
        if result is None or int(result.get_value('version')) <= 0:
            raise LookupError('No concrete snapshot version is available')
        return result

    def revision(value):
        return hashlib.sha256(json.dumps(value.get_data(), sort_keys=True, default=str).encode()).hexdigest()

    source = Search.get_by_search_key(search_key)
    if source is None:
        raise LookupError('Object is no longer available')
    source_type = check_type(source.get_search_type())
    snapshot = source if source_type == 'sthpw/snapshot' else Snapshot.get_latest(source.get_search_type(), source.get_id())
    if snapshot is None:
        return dict(title='Dependencies', identity=source.get_display_value(), rows=[], hasNext=False, message='No snapshot found')
    snapshot = concrete(snapshot)
    current = revision(snapshot)
    if expected_revision and expected_revision != current:
        raise UserException('Dependencies changed. Reload this snapshot.')
    xml = snapshot.get_snapshot_xml()
    files = xml.get_nodes('snapshot/file')
    result = dict(title='Dependencies', identity=snapshot.get_code(), snapshotKey=snapshot.get_search_key(),
        projectCode=project, version=snapshot.get_value('version'), context=snapshot.get_value('context'),
        revision=current, offset=offset)
    parent = owner(snapshot)
    result['owner'] = dict(searchKey=parent.get_search_key(), title=parent.get_display_value()) if parent else None
    if file_index is not None:
        if file_index >= len(files):
            raise LookupError('Dependency file is no longer available')
        file_node = files[file_index]
        file_range = FileRange.get(Xml.get_attribute(file_node, 'file_range'))
        start, end, step = file_range.get_values()
        if step <= 0 or start > end:
            raise ValueError('Invalid dependency file range')
        count = (end - start) // step + 1
        # Expand only this page, even if the snapshot contains millions of frames.
        first, last = start + offset * step, min(end, start + (offset + limit - 1) * step)
        paths = FileGroup.expand_paths(Xml.get_attribute(file_node, 'name'), FileRange(first, last, step)) if first <= end else []
        result.update(rows=[dict(key=str(offset + index), kind='member', title=path, group='Files')
            for index, path in enumerate(paths)], hasNext=offset + len(paths) < count)
        return result
    nodes = []
    for group, path in (
            ('Files', 'snapshot/file'), ('Upstream', 'snapshot/ref'), ('Inputs', 'snapshot/input_ref'),
            ('Downstream', 'snapshot/fref'), ('File references', 'snapshot/file/ref'),
            ('Unresolved references', 'snapshot/unknown_ref')):
        nodes.extend((group, node) for node in xml.get_nodes(path))
    rows = []
    for index, (group, node) in enumerate(nodes[offset:offset + limit], offset):
        row = dict(key=str(index), group=group, kind='reference')
        if group == 'Files':
            row.update(kind='file', fileCode=Xml.get_attribute(node, 'file_code'), filename=Xml.get_attribute(node, 'name'),
                fileType=Xml.get_attribute(node, 'type'), fileRange=Xml.get_attribute(node, 'file_range'),
                fileIndex=index, snapshotKey=snapshot.get_search_key(), projectCode=project)
        elif group == 'Unresolved references':
            row.update(kind='missing', title=Xml.get_attribute(node, 'path'))
        else:
            row.update(instance=Xml.get_attribute(node, 'instance'), node=(Xml.get_attribute(node, 'node') or '')[:100])
            if group == 'File references':
                row['origin'] = Xml.get_attribute(Xml.get_parent(node), 'name')
            code = Xml.get_attribute(node, 'snapshot_code')
            # Legacy code-only nodes have no numeric search_id for the contextual resolver.
            target = Snapshot.get_by_code(code, show_retired=True) if code and not Xml.get_attribute(node, 'level_type') else Snapshot.get_ref_snapshot_by_node(node, show_retired=True)
            if target is None:
                row.update(kind='missing', title=code or Xml.get_attribute(node, 'search_code') or Xml.get_attribute(node, 'search_id'))
            else:
                check_type(target.get_value('search_type'))
                target_project = target.get_value('project_code')
                target = concrete(target, target_project)
                parent = owner(target)
                row.update(snapshotKey=target.get_search_key(), projectCode=target_project,
                    version=target.get_value('version'), context=target.get_value('context'),
                    parentType=SearchKey.extract_base_search_type(target.get_value('search_type')),
                    parentCode=parent.get_code() if parent else '', ownerMissing=parent is None,
                    current=bool(target.is_current()), retired=target.is_retired(), revision=revision(target))
        rows.append(row)
    result.update(rows=rows, hasNext=len(nodes) > offset + limit)
    return result


class TableDependencyReadCmd(Command):
    def execute(self):
        self.info = read_dependency_node(**self.kwargs)
        return self.info
