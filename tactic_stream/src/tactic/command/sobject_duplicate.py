"""Handler's dependency-aware duplication procedures on the native kernel.

Source: thlib/tactic_query.py. Files use native copy check-in, not shared inplace
ownership; schema traversal preserves named paths. No GUI/server connection.
"""
from pyasm.biz import Schema
from pyasm.search import SearchType
from pathlib import Path


def duplicate_relations(source):
    base = source.get_base_search_type()
    schema = source.get_schema()
    pending, seen, edges = [schema], set(), set()
    while pending:
        current = pending.pop(0)
        if not current or current.get_code() in seen:
            continue
        seen.add(current.get_code())
        pending.extend([current.parent_schema, current.sthpw_schema])
        for node in current.xml.findall('connect'):
            first, second = node.get('from'), node.get('to')
            targets = []
            if base == first:
                targets.append(('parent', second))
            if second in (base, '*'):
                targets.append(('children', first))
            for direction, target in targets:
                if not target or target == '*' or target in ('sthpw/task', 'sthpw/note', 'sthpw/snapshot', 'sthpw/file'):
                    continue
                if node.get('disabled') in ('true', '1') or SearchType.get(target, no_exception=True) is None:
                    continue
                path = node.get('path') or ''
                identity = (direction, target, path)
                if identity in edges:
                    continue
                edges.add(identity)
                attrs = dict(schema.get_relationship_attrs(base, target, path=path or None) or {})
                attrs = schema.resolve_relationship_attrs(attrs, source.get_search_type(), SearchType.build_search_type(target, source.get_project_code()))
                if not attrs.get('disabled'):
                    yield direction, target, attrs


def duplicate_related_objects(source, direction, related_type, attrs):
    # A self-hierarchy needs an explicit direction; native default lookup is parent-only.
    if related_type == source.get_base_search_type() and attrs.get('relationship') in ('code', 'id'):
        from pyasm.search import Search
        search = Search(source.get_search_type())
        local, remote = (attrs['to_col'], attrs['from_col']) if direction == 'parent' else (attrs['from_col'], attrs['to_col'])
        value = source.get_value(remote)
        if value in (None, ''):
            return []
        search.add_filter(local, value)
        return search.get_sobjects()
    return source.get_related_sobjects(related_type, path=attrs.get('path') or None)


def analyze_sobject_duplicate(search_key):
    """Return editable fields and copyable dependencies for one sObject."""
    import json
    from pyasm.biz import Schema, Snapshot, Task
    from pyasm.search import Search, SearchKey, SearchType

    sobject = SearchKey.get_by_search_key(search_key)
    if not sobject:
        raise Exception("SObject [%s] does not exist" % search_key)

    search_type = sobject.get_base_search_type()
    project_code = sobject.get_project_code()
    schema = Schema.get(project_code=project_code)
    source_data = dict(sobject.get_data() or {})
    columns = set(SearchType.get_columns(search_type) or [])
    protected = set([
        'id', 'code', 'timestamp', 'last_update', 'project_code',
        's_status', 'creator',
    ])
    try:
        column_info = dict(SearchType.get_column_info(search_type) or {})
    except Exception:
        column_info = {}

    relationship_columns = set()
    related_specs = []
    seen_specs = set()
    for direction, related_type, attrs in duplicate_relations(sobject):
        relationship = attrs.get('relationship') or 'code'
        path = attrs.get('path') or ''
        instance_type = attrs.get('instance_type') or ''
        key = '|'.join([
            str(relationship), str(direction), str(related_type),
            str(instance_type), str(path),
        ])
        if relationship == 'instance':
            key = '|'.join([
                'instance', str(related_type), str(instance_type),
                str(path),
            ])
        if key in seen_specs:
            continue
        seen_specs.add(key)

        local_columns = []
        if attrs.get('from') == search_type:
            local_column = attrs.get('from_col')
        elif attrs.get('to') == search_type:
            local_column = attrs.get('to_col')
        else:
            local_column = None
        if local_column:
            local_columns.append(local_column)
        if direction == 'parent':
            if relationship in ('search_type', 'search_code', 'search_id'):
                prefix = (attrs['prefix'] + '_') if attrs.get('prefix') else ''
                local_columns.extend([prefix + 'search_type', prefix + 'search_id'])
                if relationship != 'search_id':
                    local_columns.append(prefix + 'search_code')
            elif relationship == 'parent_code':
                local_columns.append('parent_code')
            elif relationship == 'search_key':
                local_columns.append('search_key')
        for column in local_columns:
            if column:
                relationship_columns.add(column)

        try:
            related = list(duplicate_related_objects(sobject, direction, related_type, attrs) or [])
        except Exception:
            related = []
        if direction == 'parent' and not related and not path:
            try:
                parent = sobject.get_parent(related_type)
            except Exception:
                parent = None
            if parent:
                related = [parent]
        if not related:
            continue

        items = []
        for item in related[:24]:
            data = dict(item.get_data() or {})
            title = (
                data.get('name') or data.get('title')
                or data.get('code') or item.get_code()
            )
            items.append({
                'searchKey': SearchKey.get_by_sobject(
                    item, use_id=False
                ),
                'title': str(title or ''),
            })
        try:
            stype = SearchType.get(related_type)
            related_title = (
                stype.get_title() or stype.get_value('title')
                or related_type
            )
        except Exception:
            related_title = related_type.rsplit('/', 1)[-1]
        kind = 'instance' if relationship == 'instance' else direction
        options = [
            {'value': 'none', 'label': 'Do not copy', 'icon': 'link-off'},
        ]
        default_mode = 'none'
        if kind == 'instance':
            options.append({
                'value': 'link', 'label': 'Keep links', 'icon': 'link',
            })
            default_mode = 'link'
        elif kind == 'parent':
            options.append({
                'value': 'link', 'label': 'Keep parent', 'icon': 'account-tree',
            })
            default_mode = 'link'
        else:
            options.append({
                'value': 'copy', 'label': 'Duplicate children',
                'icon': 'content-copy',
            })
        related_specs.append({
            'key': key,
            'direction': direction,
            'kind': kind,
            'relationship': relationship,
            'searchType': related_type,
            'title': str(related_title or related_type),
            'count': len(related),
            'mode': default_mode,
            'defaultMode': default_mode,
            'localColumn': ','.join(
                str(column) for column in local_columns if column
            ),
            'path': str(path),
            'instanceType': str(instance_type),
            'options': options,
            'items': items,
        })

    ordered_names = ['name', 'title', 'description', 'keywords']
    ordered_names.extend(sorted(
        name for name in source_data
        if name not in ordered_names
    ))
    fields = []
    for name in ordered_names:
        if (
            name in protected or name in relationship_columns
            or name not in columns or name.startswith('__')
        ):
            continue
        value = source_data.get(name)
        if isinstance(value, (dict, list, tuple)):
            continue
        if value is None:
            value = ''
        metadata = dict(column_info.get(name) or {})
        data_type = str(
            metadata.get('data_type') or type(value).__name__
        )
        label = str(
            metadata.get('title') or metadata.get('label')
            or name.replace('_', ' ').strip().title()
        )
        fields.append({
            'name': name,
            'label': label,
            'value': str(value),
            'originalValue': str(value),
            'dataType': data_type,
            'multiline': name in ('description', 'keywords', 'notes'),
        })

    process_records = {}

    def process_record(process):
        process = str(process or 'publish')
        return process_records.setdefault(process, {
            'name': process,
            'snapshotCount': 0,
            'fileCount': 0,
            'taskCount': 0,
            'processMessageCount': 0,
            'taskMessageCount': 0,
            'processAttachmentCount': 0,
            'taskAttachmentCount': 0,
        })

    def identity(item):
        code = str(item.get_code() or '')
        return code or str(item.get_id() or '')

    def root_notes(target):
        target_type = str(
            target.get_base_search_type() or ''
        ).split('?', 1)[0]
        target_code = str(target.get_code() or '')
        target_id = str(target.get_id() or '')
        if not target_code and not target_id:
            return []
        note_search = Search('sthpw/note')
        note_search.add_filter(
            'search_code' if target_code else 'search_id',
            target_code or target_id,
        )
        if project_code:
            note_search.add_filter('project_code', project_code)
        roots = []
        for note in note_search.get_sobjects() or []:
            note_type = str(
                note.get_value('search_type') or ''
            ).split('?', 1)[0]
            if note_type and target_type and note_type != target_type:
                continue
            if note.get_value('parent_id') in (None, '', 0, '0'):
                roots.append(note)
        return roots

    def flatten_notes(notes):
        result = []
        pending = list(notes or [])
        seen = set()
        while pending:
            note = pending.pop(0)
            key = identity(note)
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            result.append(note)
            try:
                pending.extend(note.get_child_notes() or [])
            except Exception:
                pass
        return result

    def snapshot_file_count(snapshot):
        try:
            paths_by_type = snapshot.get_all_paths_dict() or {}
        except Exception:
            return 0
        count = 0
        for paths in paths_by_type.values():
            if isinstance(paths, str):
                count += bool(paths)
            else:
                count += len([path for path in paths or [] if path])
        return count

    tasks = list(Task.get_by_sobject(sobject) or [])
    task_processes = {}
    for task in tasks:
        process = str(task.get_value('process') or 'publish')
        record = process_record(process)
        record['taskCount'] += 1
        task_processes[identity(task)] = process

    process_notes = root_notes(sobject)
    process_note_trees = {}
    for note in process_notes:
        process = str(note.get_value('process') or 'publish')
        process_note_trees[identity(note)] = flatten_notes([note])
        process_record(process)['processMessageCount'] += len(
            process_note_trees[identity(note)]
        )

    task_note_trees = {}
    for task in tasks:
        task_key = identity(task)
        task_note_trees[task_key] = flatten_notes(root_notes(task))
        process = task_processes.get(task_key) or 'publish'
        process_record(process)['taskMessageCount'] += len(
            task_note_trees[task_key]
        )

    attachment_codes = set()

    def count_attachments(notes, process, task_scope=False):
        for note in notes:
            attachments = list(Snapshot.get_by_sobjects([note]) or [])
            known = set(
                str(snapshot.get_code() or '') for snapshot in attachments
            )
            for snapshot in note.get_connections(
                    context='attachment') or []:
                code = str(snapshot.get_code() or '')
                if snapshot and code not in known:
                    attachments.append(snapshot)
                    known.add(code)
            if not attachments:
                continue
            count = 0
            for snapshot in attachments:
                code = str(snapshot.get_code() or '')
                if code:
                    attachment_codes.add(code)
                count += snapshot_file_count(snapshot)
            key = (
                'taskAttachmentCount' if task_scope
                else 'processAttachmentCount'
            )
            process_record(process)[key] += count

    for root in process_notes:
        process = str(root.get_value('process') or 'publish')
        count_attachments(
            process_note_trees.get(identity(root), []), process,
            task_scope=False,
        )
    for task_key, notes in task_note_trees.items():
        process = task_processes.get(task_key) or 'publish'
        count_attachments(notes, process, task_scope=True)
        for snapshot in Snapshot.get_by_sobjects([
                next(task for task in tasks if identity(task) == task_key)
        ]) or []:
            process_record(process)['taskAttachmentCount'] += (
                snapshot_file_count(snapshot)
            )

    snapshots = []
    for snapshot in Snapshot.get_all_current_by_sobject(sobject) or []:
        if str(snapshot.get_code() or '') in attachment_codes:
            continue
        snapshots.append(snapshot)
    for snapshot in snapshots:
        context = str(snapshot.get_value('context') or 'publish')
        process = str(
            snapshot.get_value('process') or context.split('/', 1)[0]
            or 'publish'
        )
        record = process_record(process)
        record['snapshotCount'] += 1
        record['fileCount'] += snapshot_file_count(snapshot)

    processes = []
    for name in sorted(process_records):
        record = process_records[name]
        record.update({
            'copySnapshots': False,
            'copyTasks': False,
            'copyProcessMessages': False,
            'copyTaskMessages': False,
            'copyProcessAttachments': False,
            'copyTaskAttachments': False,
        })
        processes.append(record)

    source_title = (
        source_data.get('name') or source_data.get('title')
        or source_data.get('code') or sobject.get_code()
    )
    return json.dumps({
        'searchKey': search_key,
        'searchType': search_type,
        'projectCode': project_code,
        'title': str(source_title or ''),
        'fields': fields,
        'relations': related_specs,
        'processes': processes,
    })

def duplicate_sobject_advanced(search_key, options=None):
    """Duplicate one sObject using explicit relation and content choices."""
    import json
    from pyasm.biz import Schema, Snapshot, Task
    from pyasm.checkin import FileCheckin
    from pyasm.search import Search, SearchKey, SearchType

    options = dict(options or {})
    source = SearchKey.get_by_search_key(search_key)
    if not source:
        raise Exception("SObject [%s] does not exist" % search_key)

    search_type = source.get_base_search_type()
    project_code = source.get_project_code()
    from tactic_client_lib import TacticServerStub
    server = TacticServerStub.get(protocol='local')
    server.set_project(project_code)
    schema = Schema.get(project_code=project_code)
    relation_options = dict(options.get('relations') or {})
    field_values = dict(options.get('fields') or {})
    process_options = dict(options.get('processes') or {})

    omitted_columns = set(['id', 'code', 'timestamp', 'last_update'])
    parent_specs = []
    child_specs = []
    instance_specs = []
    seen = set()
    for direction, related_type, attrs in duplicate_relations(source):
        relationship = attrs.get('relationship') or 'code'
        path = attrs.get('path') or ''
        instance_type = attrs.get('instance_type') or ''
        key = '|'.join([
            str(relationship), str(direction), str(related_type),
            str(instance_type), str(path),
        ])
        if relationship == 'instance':
            key = '|'.join([
                'instance', str(related_type), str(instance_type),
                str(path),
            ])
        if key in seen:
            continue
        seen.add(key)
        mode = str(relation_options.get(key) or (
            'link' if relationship == 'instance'
            or direction == 'parent' else 'none'
        ))
        spec = (related_type, path, attrs, mode)
        if relationship == 'instance':
            instance_specs.append(spec)
        elif direction == 'parent':
            parent_specs.append(spec)
            if mode == 'none':
                local_columns = []
                if attrs.get('from') == search_type:
                    local_column = attrs.get('from_col')
                elif attrs.get('to') == search_type:
                    local_column = attrs.get('to_col')
                else:
                    local_column = None
                if local_column:
                    local_columns.append(local_column)
                if relationship in ('search_type', 'search_code', 'search_id'):
                    prefix = (attrs['prefix'] + '_') if attrs.get('prefix') else ''
                    local_columns.extend([prefix + 'search_type', prefix + 'search_id'])
                    if relationship != 'search_id':
                        local_columns.append(prefix + 'search_code')
                elif relationship == 'parent_code':
                    local_columns.append('parent_code')
                elif relationship == 'search_key':
                    local_columns.append('search_key')
                omitted_columns.update(
                    column for column in local_columns if column
                )
        else:
            child_specs.append(spec)

    def identity(sobject):
        if not sobject:
            return ''
        code = str(sobject.get_code() or '')
        if code:
            return code
        return str(sobject.get_id() or '')

    def require_created(sobject, label):
        if not identity(sobject):
            raise RuntimeError('%s was not created by TACTIC' % label)
        return sobject

    def root_notes(target):
        target_type = str(
            target.get_base_search_type() or ''
        ).split('?', 1)[0]
        target_code = str(target.get_code() or '')
        target_id = str(target.get_id() or '')
        if not target_code and not target_id:
            return []
        note_search = Search('sthpw/note')
        note_search.add_filter(
            'search_code' if target_code else 'search_id',
            target_code or target_id,
        )
        if project_code:
            note_search.add_filter('project_code', project_code)
        roots = []
        for note in note_search.get_sobjects() or []:
            note_type = str(
                note.get_value('search_type') or ''
            ).split('?', 1)[0]
            if note_type and target_type and note_type != target_type:
                continue
            if note.get_value('parent_id') in (None, '', 0, '0'):
                roots.append(note)
        return roots

    source_tasks = list(Task.get_by_sobject(source) or [])
    process_notes = root_notes(source)
    task_notes = {}
    task_snapshots = {}
    for task in source_tasks:
        key = identity(task)
        task_notes[key] = root_notes(task)
        task_snapshots[key] = list(
            Snapshot.get_by_sobjects([task]) or []
        )

    def note_attachments(note):
        attachments = list(Snapshot.get_by_sobjects([note]) or [])
        known = set(
            str(snapshot.get_code() or '') for snapshot in attachments
        )
        for snapshot in note.get_connections(context='attachment') or []:
            code = str(snapshot.get_code() or '')
            if snapshot and code not in known:
                attachments.append(snapshot)
                known.add(code)
        return attachments

    attachment_codes = set()
    visited_notes = set()

    def note_tree(notes):
        result = []
        pending = list(notes or [])
        while pending:
            note = pending.pop(0)
            key = identity(note)
            if key and key in visited_notes:
                continue
            if key:
                visited_notes.add(key)
            result.append(note)
            try:
                pending.extend(note.get_child_notes() or [])
            except Exception:
                pass
        return result

    process_note_trees = {}
    process_note_tree = []
    for note in process_notes:
        branch = note_tree([note])
        process_note_trees[identity(note)] = branch
        process_note_tree.extend(branch)
    task_note_trees = {}
    for task_key, notes in task_notes.items():
        task_note_trees[task_key] = note_tree(notes)
    for note in process_note_tree:
        for snapshot in note_attachments(note):
            if identity(snapshot):
                attachment_codes.add(identity(snapshot))
    for notes in task_note_trees.values():
        for note in notes:
            for snapshot in note_attachments(note):
                if identity(snapshot):
                    attachment_codes.add(identity(snapshot))

    snapshot_plans = {}

    def snapshot_plan(snapshot):
        key = identity(snapshot)
        if key in snapshot_plans:
            return snapshot_plans[key]
        try:
            paths_by_type = dict(snapshot.get_all_paths_dict() or {})
        except Exception as error:
            raise RuntimeError(
                'Could not resolve files for snapshot [%s]: %s'
                % (key or 'unknown', error)
            )
        file_types = []
        file_paths = []
        for file_type in sorted(paths_by_type):
            paths = paths_by_type.get(file_type) or []
            if isinstance(paths, str):
                paths = [paths]
            for path in paths:
                path = str(path or '')
                if not path:
                    continue
                if not Path(path).is_file():
                    raise ValueError('Snapshot file is missing: %s' % path)
                file_types.append(str(file_type or 'main'))
                file_paths.append(path)
        if not file_paths:
            raise RuntimeError(
                'Snapshot [%s] has no repository files to duplicate'
                % (key or 'unknown')
            )
        snapshot_plans[key] = (file_types, file_paths)
        return snapshot_plans[key]

    def checkin_snapshot(snapshot, target):
        context = str(snapshot.get_value('context') or 'publish')
        file_types, file_paths = snapshot_plan(snapshot)
        checkin = FileCheckin(
            target, context=context, file_paths=file_paths,
            file_types=file_types,
            snapshot_type=snapshot.get_value('snapshot_type'),
            mode='copy', process=snapshot.get_value('process'), description=snapshot.get_value('description')
        )
        created = require_created(
            checkin.execute(), 'Snapshot [%s]' % identity(snapshot)
        )
        return created, len(file_paths)

    source_snapshots = []
    for snapshot in Snapshot.get_all_current_by_sobject(source) or []:
        if identity(snapshot) in attachment_codes:
            continue
        source_snapshots.append(snapshot)

    # Resolve every selected repository path before the first write. This
    # avoids creating a root duplicate and only then discovering that a
    # selected snapshot or attachment cannot be copied.
    for snapshot in source_snapshots:
        context = str(snapshot.get_value('context') or 'publish')
        process = str(
            snapshot.get_value('process') or context.split('/', 1)[0]
            or 'publish'
        )
        if dict(process_options.get(process) or {}).get('copySnapshots'):
            snapshot_plan(snapshot)
    for note in process_notes:
        process = str(note.get_value('process') or 'publish')
        if dict(process_options.get(process) or {}).get(
                'copyProcessAttachments'):
            for branch_note in process_note_trees.get(identity(note), []):
                for snapshot in note_attachments(branch_note):
                    snapshot_plan(snapshot)
    for task in source_tasks:
        process = str(task.get_value('process') or 'publish')
        if not dict(process_options.get(process) or {}).get(
                'copyTaskAttachments'):
            continue
        for snapshot in task_snapshots.get(identity(task), []):
            snapshot_plan(snapshot)
        for note in task_note_trees.get(identity(task), []):
            for snapshot in note_attachments(note):
                snapshot_plan(snapshot)

    new_sobject = SearchType.create(search_type)
    columns = set(SearchType.get_columns(search_type) or [])
    for name, value in (source.get_data() or {}).items():
        if (
                name in omitted_columns or name not in columns
                or value is None):
            continue
        if isinstance(value, (dict, list)):
            new_sobject.set_json_value(name, value)
        else:
            new_sobject.set_value(name, value)
    for name, value in field_values.items():
        if name in columns and name not in omitted_columns:
            new_sobject.set_value(name, '' if value is None else value)
    new_sobject.commit()
    require_created(new_sobject, 'Duplicate sObject')

    relation_counts = {'linked': 0, 'children': 0}
    for related_type, path, attrs, mode in instance_specs:
        if mode != 'link':
            continue
        instance_type = str(attrs.get('instance_type') or '')
        if not instance_type:
            raise RuntimeError(
                'Instance relationship to [%s] has no instance type'
                % related_type
            )
        related = source.get_related_sobjects(
            related_type, path=path or None
        ) or []
        for related_sobject in related:
            from_type = str(attrs.get('from') or '').split('?', 1)[0]
            if from_type == search_type:
                from_sobject, to_sobject = new_sobject, related_sobject
            else:
                from_sobject, to_sobject = related_sobject, new_sobject
            instance = SearchType.create(instance_type)
            instance.add_related_connection(
                from_sobject, to_sobject, src_path=path or None
            )
            instance.commit()
            require_created(instance, 'Instance relationship')
            relation_counts['linked'] += 1

    for related_type, path, attrs, mode in child_specs:
        if mode != 'copy':
            continue
        children = duplicate_related_objects(source, 'children', related_type, attrs) or []
        for child in children:
            resolved = schema.resolve_relationship_attrs(attrs, child.get_search_type(), new_sobject.get_search_type())
            if resolved.get('relationship') in ('code', 'id'):
                clone = child.clone(recursive=False, extra_data={resolved['from_col']: new_sobject.get_value(resolved['to_col'])})
            elif resolved.get('relationship') in ('search_code', 'search_id'):
                prefix = (resolved['prefix'] + '_') if resolved.get('prefix') else ''
                values = {prefix + 'search_type': new_sobject.get_search_type(), resolved['from_col']: new_sobject.get_value(resolved['to_col'])}
                if SearchType.column_exists(child.get_search_type(), prefix + 'search_id'):
                    values[prefix + 'search_id'] = new_sobject.get_id()
                clone = child.clone(recursive=False, extra_data=values)
            else:
                clone = child.clone(recursive=False, parent=new_sobject)
            require_created(clone, 'Child sObject')
            relation_counts['children'] += 1

    copied_snapshots = 0
    for snapshot in source_snapshots:
        context = str(snapshot.get_value('context') or 'publish')
        process = str(
            snapshot.get_value('process') or context.split('/', 1)[0]
            or 'publish'
        )
        choice = dict(process_options.get(process) or {})
        if not choice.get('copySnapshots'):
            continue
        checkin_snapshot(snapshot, new_sobject)
        copied_snapshots += 1

    task_map = {}
    copied_tasks = 0
    for task in source_tasks:
        process = str(task.get_value('process') or 'publish')
        choice = dict(process_options.get(process) or {})
        if not choice.get('copyTasks'):
            continue
        task_clone = require_created(
            task.clone(recursive=False, parent=new_sobject),
            'Task [%s]' % identity(task),
        )
        task_map[identity(task)] = task_clone
        copied_tasks += 1

    copied_attachments = 0
    copied_note_keys = set()

    def copy_attachments(note, note_clone):
        copied = 0
        for snapshot in note_attachments(note):
            created, file_count = checkin_snapshot(snapshot, note_clone)
            require_created(created, 'Note attachment')
            copied += file_count
        return copied

    def copy_note_branch(note, target, copy_files, parent_clone=None):
        key = note.get_search_key()
        if key in copied_note_keys:
            raise ValueError('Cyclic or shared message tree cannot be duplicated')
        copied_note_keys.add(key)
        clone = require_created(
            note.copy_note(target, parent=parent_clone),
            'Message [%s]' % identity(note),
        )
        files_copied = copy_attachments(note, clone) if copy_files else 0
        messages_copied = 1
        try:
            children = note.get_child_notes() or []
        except Exception:
            children = []
        for child_note in children:
            child_count, child_files = copy_note_branch(
                child_note, target, copy_files, parent_clone=clone
            )
            messages_copied += child_count
            files_copied += child_files
        return messages_copied, files_copied

    copied_process_messages = 0
    for note in process_notes:
        process = str(note.get_value('process') or 'publish')
        choice = dict(process_options.get(process) or {})
        if not choice.get('copyProcessMessages'):
            continue
        message_count, file_count = copy_note_branch(
            note, new_sobject,
            bool(choice.get('copyProcessAttachments')),
        )
        copied_process_messages += message_count
        copied_attachments += file_count

    copied_task_messages = 0
    if task_map:
        for task in source_tasks:
            task_key = identity(task)
            task_clone = task_map.get(task_key)
            if not task_clone:
                continue
            process = str(task.get_value('process') or 'publish')
            choice = dict(process_options.get(process) or {})
            if choice.get('copyTaskAttachments'):
                for snapshot in task_snapshots.get(task_key, []):
                    created, file_count = checkin_snapshot(
                        snapshot, task_clone
                    )
                    require_created(created, 'Task attachment')
                    copied_attachments += file_count
            if not choice.get('copyTaskMessages'):
                continue
            for note in task_notes.get(task_key, []):
                message_count, file_count = copy_note_branch(
                    note, task_clone,
                    bool(choice.get('copyTaskAttachments')),
                )
                copied_task_messages += message_count
                copied_attachments += file_count

    return json.dumps({
        'searchKey': SearchKey.get_by_sobject(new_sobject, use_id=False),
        'code': new_sobject.get_code(),
        'relationsLinked': relation_counts['linked'],
        'childrenCopied': relation_counts['children'],
        'snapshotsCopied': copied_snapshots,
        'tasksCopied': copied_tasks,
        'processMessagesCopied': copied_process_messages,
        'taskMessagesCopied': copied_task_messages,
        'attachmentFilesCopied': copied_attachments,
    })
