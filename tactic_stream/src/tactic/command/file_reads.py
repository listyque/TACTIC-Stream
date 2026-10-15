"""Bounded file-workspace reads in one native command and request context."""
from pyasm.common.errors import SecurityException
READ_ACTIONS = frozenset({
    'capabilities', 'depots', 'depot_status', 'streams', 'stream_status', 'workspaces', 'workspace_active', 'changes',
    'inspect_change', 'status', 'list', 'have', 'change_files', 'inspect_change_files',
    'file_states', 'locks', 'browse', 'workspace_browse', 'history', 'transfer_tasks',
    'transfer_status', 'conflicts', 'resolved_files', 'stream_graph', 'storage_status',
    'file_info', 'file_entries', 'file_preview', 'workspace_status', 'workspace_paths',
    'read_batch', 'read_page', 'workspace_snapshot', 'revert_plan', 'submit_tasks', 'submit_shelves', 'changelist_details',
})


class FileReadMixin:
    def changelist_details(self):
        """One bounded desktop inspection, with revision-pinned section pages."""
        from pyasm.biz.file_project import find
        from pyasm.search import Search
        from tactic.ui.table.task_inspector import task_fields
        from tactic.ui.table.task_element_wdg import TaskElementWdg
        info = self.inspect_change()
        if 'edit_revision' in self.kwargs:
            self.revision(info)
        section = self.kwargs.get('section', 'all')
        if section not in ('all', 'files', 'shelves', 'shelf_files'):
            raise ValueError('Unknown changelist section')
        item = find('change', info['code'])
        info['date'] = str(item.get_value('timestamp', no_exception=True) or '')
        info['created_at'] = item.get_value('created_at', no_exception=True) or None
        result = {'change': info['code'], 'info': info}
        if section in ('all', 'files'):
            result['files'] = self.read_call('inspect_change_files', dict(change=info['code'],
                edit_revision=info['edit_revision'], after=self.kwargs.get('after', '') if section == 'files' else '', limit=200))
            result['info'].update(opened_files=result['files']['files'], opened_bytes=result['files']['bytes'])
            if info.get('integration'):
                root = info['integration']['conflicts_root']
                for row in result['files']['items']:
                    row['conflict'] = self.catalog.get(root, row['path']) is not None
        if section in ('all', 'shelves'):
            result['shelves'] = self.related_shelves(info['code'], self.kwargs.get('after') if section == 'shelves' else None)
        shelf = self.kwargs.get('shelf') if section == 'shelf_files' else None
        if section in ('all', 'shelves') and result['shelves']['items']:
            shelf = result['shelves']['items'][0]['code']
        if shelf:
            options = dict(change=shelf, limit=200, after=self.kwargs.get('after', '') if section == 'shelf_files' else '')
            if 'shelf_revision' in self.kwargs:
                options['edit_revision'] = self.kwargs['shelf_revision']
            detail = self.read_call('inspect_change_files', options)
            if detail['info'].get('source_change') != info['code'] or detail['info']['state'] != 'shelved':
                raise ValueError('Choose a shelf of this changelist')
            result['shelf_files'] = detail
        elif section in ('all', 'shelves'):
            result['shelf_files'] = {'items': [], 'files': 0}
        if section == 'all':
            tasks = {'items': [], 'unavailable': False}
            codes = info.get('task_codes', [])
            if codes:
                try:
                    fields = {field['name'] for field in task_fields()}
                    search = Search('sthpw/task'); search.add_filter('project_code', self.project)
                    search.add_filters('code', codes)
                    tasks['items'] = [dict(code=task.get_code(),
                        status=(task.get_value('status') or '') if 'status' in fields else '',
                        description=(task.get_value('description') or '') if 'description' in fields else '')
                        for task in search.get_sobjects() if TaskElementWdg.can_view_process(task.get_value('process') or 'publish')]
                except SecurityException:
                    tasks['unavailable'] = True
            result['tasks'] = tasks
        return result

    def read_history(self):
        from pyasm.biz.file_project import find, cache_read_records
        from pyasm.search import Search
        from .file_project_cmd import logical_path, integer, CHUNK_LIMIT
        root, published = self.published_root()
        entry = self.catalog.get(root, logical_path(self.kwargs.get('path')))
        if not entry:
            return {'items': [], 'published_change': published}
        limit = integer(self.kwargs.get('limit', 100), 1, CHUNK_LIMIT)
        if self.kwargs.get('after_version'):
            raise ValueError('History cursor is not available; request a bounded head history')
        items, version, visited = [], entry['version'], 0
        while version and len(items) < limit and visited < CHUNK_LIMIT:
            first = find('version', version)
            anchor = first.get_json_value('data')
            search = Search('file_project/version')
            search.add_filter('stream_code', anchor['stream'])
            search.add_filter('path', anchor['path'])
            search.add_filter('number', anchor['number'], op='<=')
            search.add_order_by('number desc'); search.add_order_by('id desc'); search.set_limit(128)
            rows = search.get_sobjects()
            cache_read_records('version', rows)
            candidates = {row.get_code(): row for row in rows}
            candidates[first.get_code()] = first
            chain = []
            while version in candidates and len(chain) < limit-len(items) and visited < CHUNK_LIMIT:
                row = candidates.pop(version)
                data = row.get_json_value('data')
                chain.append((row, data)); version = data['previous']; visited += 1
            changes = Search('file_project/change')
            changes.add_filters('code', list({data['change'] for _, data in chain}))
            holders = changes.get_sobjects()
            cache_read_records('change', holders)
            published_changes = {row.get_code(): row for row in holders}
            # Follow the authorized previous links; indexed siblings may be abandoned drafts.
            for row, data in chain:
                change = published_changes.get(data['change'])
                if change is None:
                    raise ValueError('Unknown file-project change: ' + data['change'])
                change_data = change.get_json_value('data')
                published_entry = self.catalog.get(change_data['root'], data['path']) if change_data['state']=='submitted' else None
                if published_entry and published_entry.get('version') == row.get_code():
                    items.append({**self.result(row), 'author':change_data['owner'],
                        'description':change_data.get('description','') if self.can_read_change_metadata(change_data) else '', 'submitted_at':change_data.get('submitted_at'),
                        'change_number':change.get_id(),
                        'workspace':change_data.get('workspace') if self.can_read_change_metadata(change_data) else None,
                        'action':'move/delete' if data.get('moved_to') else 'move/add' if data.get('moved_from') else
                            'delete' if data.get('deleted') else 'edit' if data.get('previous') else 'add'})
        return {'items':items, 'published_change':published, 'more':bool(version)}

    def file_entries(self):
        paths = self.paths()
        root, published = self.published_root()
        return {'items': [{'path': path, 'file': self.catalog.get(root, path)} for path in paths],
                'published_change': published}

    def read_call(self, action, values):
        if action not in READ_ACTIONS - {'read_batch', 'workspace_snapshot'} or not isinstance(values, dict):
            raise ValueError('Choose a supported read-only file action')
        if action in ('list', 'browse', 'file_info', 'file_entries', 'file_preview', 'read_page') and values.get('file_revision') not in (None, ''):
            raise ValueError('Materialize per-file revisions with revision_snapshot before batching reads')
        original = self.kwargs
        try:
            self.kwargs = dict(values)
            return getattr(self, action)()
        finally:
            self.kwargs = original

    def read_batch(self):
        requests = self.kwargs.get('requests')
        if not isinstance(requests, list) or not 1 <= len(requests) <= 16:
            raise ValueError('Read batch requires 1..16 requests')
        for request in requests:
            if (not isinstance(request, dict) or set(request) != {'action', 'values'}
                    or request['action'] not in READ_ACTIONS - {'read_batch', 'workspace_snapshot'}
                    or not isinstance(request['values'], dict)):
                raise ValueError('Choose a supported read-only file action')
        return {'items': [self.read_call(row['action'], row['values']) for row in requests]}

    def read_page(self):
        values = dict(self.kwargs)
        source = values.pop('source', None)
        workspace = values.pop('workspace_context', None)
        folder = values.pop('folder', False)
        if not isinstance(folder, bool):
            raise ValueError('Folder must be a boolean')
        if source not in {'list', 'have', 'change_files', 'inspect_change_files'}:
            raise ValueError('Choose a supported file page')
        if folder and source in ('list', 'have'):
            values['directory'] = values.pop('prefix', '')
            page = self.read_call('browse' if source == 'list' else 'workspace_browse', values)
            page['items'] = [row for row in page['items'] if row['kind'] == 'file']
        else:
            page = self.read_call(source, values)
        if not page['items'] or not workspace:
            return page
        stream = page.get('info', {}).get('stream') or values.get('stream')
        states = self.read_call('file_states', {'workspace': workspace, 'paths': [
            {'stream': row.get('stream') or stream, 'path': row.get('source_path', row['path'])}
            for row in page['items']]})
        page['items'] = [{**row, **{key: value for key, value in state.items() if key not in ('path', 'stream')}}
                         for row, state in zip(page['items'], states['items'])]
        return page

    def workspace_snapshot(self):
        options = dict(self.kwargs)
        tab = options.get('tab', {})
        expanded = options.get('expanded', [])
        if not isinstance(tab, dict) or not isinstance(expanded, list) or len(expanded) > 32:
            raise ValueError('Snapshot requires a bounded workspace view')
        directories = options.get('directories', [])
        if (not isinstance(directories, list) or len(directories) > 16
                or any(not isinstance(row, dict) or row.get('action') not in ('browse', 'workspace_browse')
                       or not isinstance(row.get('values'), dict) or not isinstance(row.get('id'), str) for row in directories)):
            raise ValueError('Snapshot accepts at most 16 directory pages')
        if options.get('catalog', True):
            catalog = self.read_batch_catalog()
        else:
            ws = self.read_call('workspace_status', {'workspace': options.get('workspace')}) if options.get('workspace') else None
            catalog = {'active': {'workspace': options.get('workspace'), 'info': ws,
                                  'revision': options.get('active_revision', 0)},
                       'workspaces': {'items': []}, 'tasks': self.read_call('transfer_tasks', {'limit': 200})}
        workspace = catalog['active'].get('workspace') or options.get('workspace')
        ws = catalog['active'].get('info') or next((row for row in catalog['workspaces']['items']
                                                   if row['code'] == workspace), None)
        if ws:
            workspace = ws['code']
        elif not workspace and catalog['workspaces']['items']:
            ws = catalog['workspaces']['items'][0]
            workspace = ws['code']
        stream = options.get('stream') or (ws or {}).get('stream')
        scope = tab.get('scope', 'mine')
        values = {'state': tab.get('state', options.get('state', 'pending')), 'scope': scope, 'limit': 100}
        if tab.get('states'):
            values['states'] = tab['states']
        if scope == 'workspace':
            values['workspace'] = workspace
        if scope == 'stream':
            values['stream'] = stream
        selected = options.get('change')
        closed = self.read_call('inspect_change', {'change': selected}) if selected and options.get('reason') in ('submit', 'revert') else None
        if closed and closed['state'] in ('submitted', 'reverted'):
            values.pop('states', None)
            values['state'] = closed['state']
        changes = ({'items': [self.read_call('inspect_change', {'change': tab['change']})], 'after': None}
                   if tab.get('change') else self.read_call('changes', values))
        result = {'catalog': catalog, 'changes': changes, 'pages': {}, 'workspace': workspace, 'stream': stream}
        current = closed or next((row for row in changes['items'] if row['code'] == selected), None)
        if selected and current is None:
            current = self.read_call('inspect_change', {'change': selected})
        if current:
            result['change'] = current
        if closed:
            result['active_state'] = closed['state']
        if workspace:
            pending_visible = 'pending' in values.get('states', [values['state']])
            if (pending_visible and changes['after'] is None and scope in ('mine', 'workspace')
                    and not tab.get('change')):
                targets = {'items': [row for row in changes['items'] if row['state'] == 'pending'
                                     and row.get('workspace') == workspace and row['owner'] == self.owner], 'after': None}
            else:
                targets = self.read_call('changes', {'workspace': workspace, 'state': 'pending', 'limit': 200})
            catalog['targets'] = targets
        else:
            catalog['targets'] = {'items': [], 'after': None}
        for change in changes['items']:
            if change['code'] not in expanded and change['code'] != selected:
                continue
            values = {'source': 'inspect_change_files', 'workspace_context': workspace, 'limit': 200,
                      'shelf' if change['state'] == 'shelved' else 'change': change['code']}
            result['pages'][change['code']] = self.read_call('read_page', values)
        if current and current['code'] not in result['pages'] and options.get('view') == 'change':
            result['pages'][current['code']] = self.read_call('read_page', {
                'source': 'inspect_change_files', 'workspace_context': workspace, 'limit': 200,
                'shelf' if current['state'] == 'shelved' else 'change': current['code']})
        view = options.get('view')
        if view in ('depot', 'have') and (stream if view == 'depot' else workspace):
            result['files'] = self.read_call('read_page', {
                'source': 'list' if view == 'depot' else 'have', 'workspace_context': workspace,
                'stream' if view == 'depot' else 'workspace': stream if view == 'depot' else workspace,
                'prefix': options.get('prefix', ''), 'limit': 200,
                'folder': tab.get('kind') == 'files' and tab.get('source') == 'selection',
                'after': options.get('files_after', '')})
        if current and current.get('integration'):
            integration = {'change': current['code'], 'edit_revision': current['edit_revision'],
                           'integration': current['integration']['code'], 'limit': 100}
            result['conflicts'] = self.read_call('conflicts', integration)
            result['resolved'] = self.read_call('resolved_files', {**integration, 'limit': 200})
        if tab.get('kind') == 'history' and options.get('history_path'):
            result['history'] = self.read_call('history', {'path': options['history_path'],
                'stream': options.get('history_stream'), 'limit': 1000})
        if tab.get('kind') in ('catalog', 'graph'):
            source = tab.get('source')
            if source not in ('workspaces', 'streams', 'depots', 'stream_graph', 'storage'):
                raise ValueError('Choose a supported catalog view')
            result['catalog_view'] = (catalog[source] if source in catalog else
                self.read_call('storage_status' if source == 'storage' else source, {'limit': 200}))
        result['directories'] = {}
        for row in directories:
            values = {**row['values'], 'limit': 200}
            if row['action'] == 'workspace_browse':
                if not workspace:
                    continue
                values['workspace'] = workspace
            try:
                page = self.read_call(row['action'], values)
                directory = values.get('directory', '')
                parent = directory.rstrip('/').rpartition('/')[0]
                seek = self.read_call(row['action'], {**values, 'directory': parent+'/' if parent else '',
                    'after': directory.rstrip('/'), 'limit': 1}) if directory else None
                result['directories'][row['id']] = {'page': page, 'seek': seek}
            except SecurityException:
                continue  # Revoked tree nodes are absent from the permitted metadata snapshot.
        return result

    def read_batch_catalog(self):
        return {
            'capabilities': self.read_call('capabilities', {}),
            'streams': self.read_call('streams', {'limit': 200}),
            'workspaces': self.read_call('workspaces', {'limit': 200}),
            'depots': self.read_call('depots', {'limit': 200}),
            'tasks': self.read_call('transfer_tasks', {'limit': 200}),
            'active': self.read_call('workspace_active', {}),
        }
