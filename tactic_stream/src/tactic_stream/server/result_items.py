"""Handler result trees on native Search, Pipeline and ThumbWdg data."""
from pyasm.search import Search, SearchKey, SearchType
from pyasm.biz import Project
from pyasm.widget import ThumbWdg
from pyasm.security.security import _require_admin
from .table_cells import safe_link


def objects(search_type, keys, *, read_access=False):
    if read_access:
        from .navigation_links import check_project, check_type
        check_project(Project.get_project_code()); check_type(search_type, Project.get_project_code())
    else:
        _require_admin()
    if not isinstance(keys, list) or len(keys) > 500 or any(not isinstance(key, str) or not key for key in keys):
        raise ValueError('Choose at most 500 table records')
    base = SearchType.get(search_type).get_base_key()
    for key in keys:
        if SearchKey.extract_base_search_type(key) != base or SearchKey.extract_project(key) not in ('', None, Project.get_project_code()):
            raise ValueError('Table records belong to another type or project')
    result = {}
    for full_type in dict.fromkeys(SearchKey.extract_search_type(key) for key in keys):
        group = [key for key in keys if SearchKey.extract_search_type(key) == full_type]
        codes = [SearchKey.extract_code(key) for key in group if SearchKey.extract_code(key)]
        ids = [SearchKey.extract_id(key) for key in group if not SearchKey.extract_code(key)]
        by_code = {row.get_code(): row for row in Search.get_by_code(full_type, codes)} if codes else {}
        by_id = {str(row.get_id()): row for row in Search.get_by_id(full_type, ids)} if ids else {}
        for key in group:
            row = by_code.get(SearchKey.extract_code(key)) or by_id.get(str(SearchKey.extract_id(key)))
            if row is None:
                raise LookupError('Object no longer exists')
            result[key] = row
    return result


def relations(obj, direction='child'):
    return schema_relations(obj.get_base_search_type(), obj.get_schema(), direction)


def schema_relations(base, schema, direction='child'):
    result = {}
    pending = [schema]
    seen = set()
    while pending:
        current = pending.pop()
        if not current or current.get_code() in seen:
            continue
        seen.add(current.get_code())
        pending.append(current.parent_schema)
        if base.startswith('sthpw/'):
            pending.append(current.sthpw_schema)
        for node in current.xml.findall('connect'):
            target = node.get('from' if direction == 'child' else 'to')
            owner = node.get('to' if direction == 'child' else 'from')
            if owner not in (base, '*') or not target or target in ('sthpw/task', 'sthpw/note', 'sthpw/snapshot', 'sthpw/file'):
                continue
            path = node.get('path') or ''
            identity = (target, path)
            if identity in result or node.get('disabled') in ('true', '1') or node.get('type') == 'many_to_many':
                continue
            if direction == 'parent' and node.get('relationship') == 'instance':
                continue
            # Handler only offers registered project SearchTypes, not dangling
            # legacy schema references or the link tables behind instance edges.
            definition = SearchType.get(target, no_exception=True)
            if definition is None:
                continue
            attrs = schema.get_relationship_attrs(target, base, path=path or None) if direction == 'child' else schema.get_relationship_attrs(base, target, path=path or None)
            result[identity] = dict(kind='relation' if direction == 'child' else 'parent', search_type=target, path=path,
                title=definition.get_title(), key='relation:' + target + ':' + path,
                icon=definition.get_value('icon', no_exception=True) or 'MDI_CUBE_OUTLINE',
                accent=definition.get_value('color', no_exception=True) or '',
                relationship=attrs.get('relationship', ''))
    return list(result.values())


def relation_search(parent, branch):
    search = Search(branch['search_type'])
    search.add_relationship_filter(parent, path=branch.get('path') or None)
    return search


def progress_items(obj, pipeline, branches):
    """Counts follow Handler query_sobjects(include_progress=True), not a ratio guessed from status."""
    output = []
    for name in pipeline.get_process_names(type='progress') if pipeline else []:
        definition = pipeline.get_process_sobject(name)
        workflow = definition.get_json_value('workflow', {}) if definition else {}
        target = workflow.get('search_type')
        if not target:
            continue
        branch = next((row for row in branches if row.get('kind') == 'relation' and row.get('search_type') == target), None)
        if not branch:
            continue
        related = relation_search(obj, branch).get_sobjects()
        filters = []
        related_process = workflow.get('process')
        if related_process:
            behavior = Search('config/process')
            behavior.add_filter('process', related_process)
            behavior.add_filter('pipeline_code', workflow.get('pipeline_code'))
            behavior = behavior.get_sobject()
            settings = behavior.get_json_value('workflow', {}) if behavior else {}
            if not settings.get('task_pipeline'):
                continue
            statuses = Search('config/process')
            statuses.add_filter('pipeline_code', settings['task_pipeline'])
            mapped = [row.get_value('process') for row in statuses.get_sobjects() if row.get_json_value('workflow', {}).get('mapping')]
            filters = [('process', related_process)]
            if mapped:
                filters.append(('status', 'in', '|'.join(mapped)))
        tasks = Search.get_related_by_sobjects(related, 'sthpw/task', filters=filters)
        output.append(dict(name=name, approved=sum(len(rows) for rows in tasks.values()), total=len(related),
                           search_type=target, accent=branch['accent']))
    return output


def select_labels(search_type):
    from pyasm.widget import WidgetConfigView, SelectWdg
    from .interface import describe_view
    definition = describe_view(WidgetConfigView.get_by_search_type(search_type, 'edit_definition'))
    output = {}
    for element in definition['elements']:
        options = element['display']['options']
        if not any(options.get(name) for name in ('values', 'values_expr', 'query')) or options.get('mode_expr') == 'relative':
            continue
        control = SelectWdg(element['name'])
        control.set_options(options)
        labels, values = control.get_select_values()
        output[element['name']] = dict(zip(values, labels))
    return output


def info_items(obj, labels):
    # Handler builds its metadata strip from the configured table columns,
    # not every database field and not the SearchType name.
    from pyasm.widget import WidgetConfigView
    from .interface import describe_view
    definition = describe_view(WidgetConfigView.get_by_search_type(obj.get_base_search_type(), 'table'))
    excluded = {'name', 'code', 'keywords', 'description', 'timestamp'}
    output = []
    columns = {element['name']: element for element in definition['elements']}
    for column, value in obj.get_sobject_dict().items():
        element = columns.get(column)
        if element is None:
            continue
        if not value or column in excluded or column.startswith('__'):
            continue
        if not isinstance(value, (str, int, float, bool)):
            continue
        text = str(labels.get(column, {}).get(value, value))
        url = safe_link(text) if text.lower().startswith(('https://', 'http://', 'ftp://')) else ''
        output.append(dict(column=column, text=element['title'] if url or isinstance(value, bool) else text[:30], tooltip=text, url=url))
    return output


def organization_catalog(records, pipelines, tasks):
    from pyasm.biz import Pipeline

    ordered = {
        code: pipelines[code]
        for row in records
        if (code := row.get_value("pipeline_code", no_exception=True)) in pipelines
    }
    for base in dict.fromkeys(row.get_base_search_type() for row in records):
        for pipeline in Pipeline.get_by_search_type(base, Project.get_project_code()):
            ordered.setdefault(pipeline.get_code(), pipeline)
    processes, statuses = {}, {}
    for pipeline in ordered.values():
        for name in pipeline.get_process_names(recurse=True):
            process = pipeline.get_process(name)
            if not process or process.get_type() in (
                "action",
                "condition",
                "dependency",
                "progress",
            ):
                continue
            processes.setdefault(
                name,
                dict(
                    key=name,
                    title=process.get_label() or name,
                    accent=process.get_color() or "",
                ),
            )
            catalog = statuses.setdefault(name, {})
            task_pipeline = Pipeline.get_by_code(process.get_task_pipeline())
            if task_pipeline:
                for status in task_pipeline.get_process_names():
                    catalog.setdefault(
                        status,
                        dict(
                            key=status,
                            accent=task_pipeline.get_process_attrs(status).get("color")
                            or "",
                        ),
                    )
    for rows in tasks.values():
        for task in rows:
            process, status = task.get_value("process"), task.get_value("status")
            if not process:
                continue
            processes.setdefault(process, dict(key=process, title=process, accent=""))
            if status:
                statuses.setdefault(process, {}).setdefault(
                    status, dict(key=status, accent="")
                )
    return dict(
        processes=sorted(processes.values(), key=lambda row: row["title"].casefold()),
        statuses={name: list(catalog.values()) for name, catalog in statuses.items()},
    )


def describe(items, relation_counts=False, organization=None):
    if not items:
        return []
    records = list(items.values())
    from .knowledge_query import knowledge_request
    from .file_presentation import file_display, repository_display
    from pyasm.biz import File
    from pathlib import Path
    import json
    project = Project.get_project_code()
    labels = {base: select_labels(base) for base in dict.fromkeys(row.get_base_search_type() for row in records)}
    articles = []
    if SearchType.get(project + '/th_knowledge_article', no_exception=True):
        from .navigation_links import check_type
        from pyasm.common.errors import SecurityException
        try:
            check_type(project + '/th_knowledge_article', project)
        except SecurityException:
            pass
        else:
            articles = json.loads(knowledge_request('link_index', project)).get('links', [])
    tasks = Search.get_related_by_sobjects(records, 'sthpw/task')
    notes = Search.get_related_by_sobjects(records, 'sthpw/note')
    snapshots = Search.get_related_by_sobjects(records, 'sthpw/snapshot')
    pipeline_codes = list(dict.fromkeys(row.get_value('pipeline_code', no_exception=True) for row in records if row.get_value('pipeline_code', no_exception=True)))
    pipelines = {row.get_code(): row for row in Search.get_by_code('sthpw/pipeline', pipeline_codes)} if pipeline_codes else {}
    if organization is not None:
        organization.update(organization_catalog(records, pipelines, tasks))
    snapshot_records = [row for row in records if row.get_base_search_type() == 'sthpw/snapshot']
    snapshot_files = {}
    for file in File.get_by_snapshots(snapshot_records) if snapshot_records else []:
        snapshot_files.setdefault(file.get_value('snapshot_code'), []).append(file)
    authors = list(dict.fromkeys(row.get_value('login') for row in snapshot_records if row.get_value('login')))
    author_labels = {row.get_value('login'): row.get_full_name() or row.get_value('login') for row in Search.get_by_code('sthpw/login', authors)} if authors else {}
    thumb = ThumbWdg(latest_icon='true', protocol='http')
    thumb.set_sobjects(records)
    thumb.preprocess()
    output = []
    for index, (key, obj) in enumerate(items.items()):
        own_key = obj.get_search_key()
        own_tasks, own_notes = tasks.get(own_key, []), notes.get(own_key, [])
        own_snapshots = snapshots.get(own_key, [])
        pipeline = pipelines.get(obj.get_value('pipeline_code', no_exception=True))
        names = list(pipeline.get_process_names()) if pipeline else []
        if not names:
            names = ['icon', 'attachment', 'publish']
        if 'attachment' not in names and any((row.get_value('context') or '').split('/')[0] == 'attachment' for row in own_snapshots):
            names.append('attachment')
        branches = relations(obj) if obj.get_base_search_type() not in ('sthpw/snapshot', 'sthpw/file') else []
        if relation_counts:
            for branch in branches:
                branch['count'] = relation_search(obj, branch).get_count()
        accent = obj.get_search_type_obj().get_value('color', no_exception=True) or ''
        for name in names:
            if not name:
                continue
            process = pipeline.get_process(name) if pipeline else None
            if process and process.get_type() in ('action', 'condition', 'dependency', 'progress'):
                continue
            branches.append(dict(kind='process', key='process:' + name, process=name,
                title=process.get_label() or name if process else name.replace('_', ' ').title(),
                description=process.get_attribute('description') or process.get_attribute('detail') or '' if process else '',
                accent=process.get_color() or accent if process else accent,
                process_type=process.get_type() if process else 'manual',
                task_count=sum(row.get_value('process') == name for row in own_tasks),
                note_count=sum((row.get_value('process') or row.get_value('context')) == name for row in own_notes),
                has_children=any((row.get_value('context') or '').split('/')[0] == name for row in own_snapshots),
                count=sum((row.get_value('context') or '').split('/')[0] == name and row.get_value('version') >= 0 for row in own_snapshots)))
        if obj.get_base_search_type() == 'sthpw/snapshot':
            branches = [dict(kind='versions', key='versions', process=obj.get_value('context'), title='Versions')] if obj.get_value('version') < 0 else []
        thumb.set_current_index(index)
        preview = thumb.get_cell_value()
        preview['image'] = safe_link(preview['image'])
        preview['text'] = safe_link(preview['text'])
        for file in preview['files']:
            file['href'] = safe_link(file['href'])
        row = obj.get_sobject_dict()
        row['__search_key__'] = key
        snapshot_display = None
        if obj.get_base_search_type() == 'sthpw/snapshot':
            files = [file for file in snapshot_files.get(obj.get_code(), []) if file.get_type() not in ('icon', 'web', 'playblast')]
            primary = files[0] if files else None
            primary_group = [file for file in files if file.get_type() == primary.get_type()] if primary else []
            display = file_display(primary, row.get('context') or '')
            display['title'] = display['title'] or row.get('context') or ''
            snapshot_display = dict(**display, **repository_display(row.get('repo') or ''),
                multiple=len(primary_group) if len(primary_group) > 1 else 0,
                size=primary.get_value('st_size', no_exception=True) if primary else None,
                exists=Path(primary.get_lib_path()).exists() if primary else False,
                author=author_labels.get(row.get('login'), row.get('login') or ''),
                latest=bool(row.get('is_latest')),
                version='latest' if row.get('version', -1) <= 0 else 'v%03d' % row['version'],
                revision='r%03d' % row['revision'] if row.get('revision') else '')
        pipeline_title = pipeline.get_value('name') or pipeline.get_code() if pipeline else obj.get_value('pipeline_code', no_exception=True)
        category_column = 'category' if row.get('category') else next((name for name, value in row.items() if name.endswith('_category_code') and value), '')
        output.append(dict(record=row, preview=preview, branches=branches, snapshot_display=snapshot_display,
            related_parents=relations(obj, 'parent') if obj.get_base_search_type() not in ('sthpw/snapshot', 'sthpw/file') else [],
            knowledge=[dict(identity=article['identity'], title=article['title'], searchKey='skey://' + SearchType.build_search_type(project + '/th_knowledge_article', project) + '&id=' + article['identity'])
                       for article in articles if 'skey://' + key in article['linkedSearchKeys']],
            accent=accent, subtitle=' · '.join(str(value) for value in (row.get('description'), pipeline_title, labels[obj.get_base_search_type()].get(category_column, {}).get(row.get(category_column), row.get(category_column))) if value),
            info_items=info_items(obj, labels[obj.get_base_search_type()]), progress_items=progress_items(obj, pipeline, branches), pipeline=pipeline_title,
            task_count=len(own_tasks), note_count=len(own_notes),
            note_counts={name: sum((note.get_value('process') or note.get_value('context')) == name for note in own_notes)
                         for name in dict.fromkeys((note.get_value('process') or note.get_value('context')) for note in own_notes)},
            has_snapshot=any(snapshot.get_value('context') != 'icon' for snapshot in own_snapshots),
            tasks=[dict(taskSearchKey=task.get_search_key(), process=task.get_value('process'), status=task.get_value('status'),
                        context=task.get_value('context') or task.get_value('process')) for task in own_tasks]))
    return output


def read_result_items(search_type, search_keys, branch=None, offset=0, limit=50):
    policy = SearchType.get(search_type).get_record_read_options()
    if policy.get('command'):
        from pyasm.common import Container
        if Container.get('FileProject:access') != Project.get_project_code():
            from pyasm.command import Command
            from tactic.command.file_project_cmd import FileProjectCmd
            command = FileProjectCmd(action=policy['action'], operation='result_items',
                payload={'search_type':search_type,'search_keys':search_keys,'branch':branch,'offset':offset,'limit':limit})
            Command.execute_cmd(command)
            return command.info
    selected = objects(search_type, search_keys, read_access=isinstance(branch,dict) and branch.get('kind') in ('snapshot_browser','snapshot_members','object_report'))
    if branch is None:
        organization = {}
        return dict(items=describe(selected, organization=organization), organization=organization, has_next=False)
    if len(selected) != 1 or not isinstance(branch, dict) or set(branch) - {'kind', 'search_type', 'path', 'process'}:
        raise ValueError('Invalid result branch')
    if type(offset) is not int or type(limit) is not int or offset < 0 or not 1 <= limit <= 100:
        raise ValueError('Invalid result page')
    parent = next(iter(selected.values()))
    if branch.get('kind') == 'object_report' and not set(branch) - {'kind', 'path'}:
        from .object_report import read_report
        return read_report(parent, branch.get('path', 'tasks'), offset, limit)
    if branch == {'kind': 'snapshot_members'}:
        from .snapshot_browser import read_snapshot_members
        if parent.get_base_search_type() != 'sthpw/file':
            raise ValueError('Select a metadata file group')
        return read_snapshot_members(parent, offset, limit)
    if branch.get('kind') == 'snapshot_browser' and not set(branch) - {'kind', 'process'}:
        from .snapshot_browser import read_snapshot_browser
        return read_snapshot_browser(parent, branch.get('process', ''), offset, limit)
    if branch == {'kind': 'children'}:
        # Handler resolves relation counts when the owner is expanded; avoid
        # counting every branch of every object during the initial page load.
        item = describe(selected, relation_counts=True)[0]
        snapshots = []
        while True:
            page = read_result_items(search_type, search_keys, dict(kind='process', process='publish'), offset=len(snapshots), limit=100)
            snapshots.extend(page['items'])
            if not page['has_next']:
                break
        item['direct_snapshots'] = list(reversed(snapshots))
        return dict(items=[item], has_next=False)
    if branch.get('kind') in ('process', 'versions'):
        process = branch.get('process')
        if branch.get('kind') == 'process' and (not isinstance(process, str) or not process or len(process) > 256):
            raise ValueError('Invalid process')
        if branch.get('kind') == 'versions' and process not in (None, '') and (not isinstance(process, str) or len(process) > 256):
            raise ValueError('Invalid result branch')
        search = Search('sthpw/snapshot')
        snapshot_parent = parent.get_base_search_type() == 'sthpw/snapshot'
        owner = parent.get_sobject() if snapshot_parent else parent
        if owner is None:
            raise LookupError('Object no longer exists')
        search.add_parent_filter(owner)
        if snapshot_parent:
            search.add_filter('context', parent.get_value('context'))
            search.add_filter('version', 0, op='>=')
            if parent.get_value('version') >= 0:
                search.add_filter('code', parent.get_code(), op='!=')
        if process and not snapshot_parent:
            search.add_op('begin')
            search.add_filter('context', process)
            search.add_filter('context', process + '/%', op='like')
            search.add_op('or')
        if branch.get('kind') == 'process' and not snapshot_parent:
            search.add_filter('version', 0, op='<')
        search.add_order_by('version desc')
    elif branch.get('kind') in ('relation', 'parent'):
        if not any(row['search_type'] == branch.get('search_type') and row['path'] == branch.get('path', '') for row in relations(parent, 'parent' if branch['kind'] == 'parent' else 'child')):
            raise ValueError('Relationship is not in the project schema')
        search = relation_search(parent, branch)
        search.add_order_by('id asc')
    else:
        raise ValueError('Invalid result branch')
    search.set_limit(limit + 1)
    search.set_offset(offset)
    rows = search.get_sobjects()
    if not rows and not offset and branch.get('kind') == 'process' and not snapshot_parent:
        # A check-in may deliberately omit its versionless copy (attachments).
        # Keep its latest real snapshot reachable, rather than hiding the files.
        fallback = Search('sthpw/snapshot')
        fallback.add_parent_filter(parent)
        fallback.add_filter('context', process)
        fallback.add_order_by('version desc')
        fallback.set_limit(1)
        rows = fallback.get_sobjects()
        items = describe({obj.get_search_key(): obj for obj in rows})
        for item in items:
            item['branches'] = [dict(kind='versions', key='versions', process=process, title='Versions')]
        return dict(items=items, has_next=False)
    return dict(items=describe({obj.get_search_key(): obj for obj in rows[:limit]}), has_next=len(rows) > limit)
