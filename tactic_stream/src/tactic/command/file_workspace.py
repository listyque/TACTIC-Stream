"""Native depot/workspace metadata and bounded mapped sync/reconcile operations."""
from hashlib import sha256
from itertools import islice
from pathlib import Path

from pyasm.biz.file_project import create, find, save, encode
from pyasm.biz.file_view import FileView
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from pyasm.search import Search


class FileWorkspaceMixin:
    def depot_status(self):
        from .file_project_cmd import identifier
        item = find('depot', identifier(self.kwargs.get('depot')))
        self.permission(item.get_code(), 'read')
        return self.depot_status_result(item)

    def depot_status_result(self, item):
        result = self.result(item)
        if result.get('storage'):
            result['storage'] = {'repository': result['storage']['repository']}
        return result

    def storage_entries(self, entries):
        codes = list({entry['blob'] for entry in entries if entry.get('blob')})
        if not codes:
            return entries
        search = Search('file_project/blob')
        search.add_filters('code', codes)
        roots = {item.get_code(): item.get_json_value('data').get('storage_root') for item in search.get_sobjects()}
        return [{**entry, '_storage_root': roots.get(entry.get('blob'))} for entry in entries]
    def depot_storage(self, repository):
        if repository is None:
            return None
        from .file_project_cmd import identifier
        repository = identifier(repository)
        roots = dict(Environment.get_asset_dirs())
        roots.setdefault('default', Environment.get_asset_dir())
        if repository not in roots or repository == 'plugins':
            raise ValueError('Unknown writable repository alias')
        root = Path(roots[repository]).resolve()
        private = root.with_name(root.name + '.file-projects').resolve()
        # Repository HTTP aliases are public; private blobs must remain outside all of them.
        if any(private.is_relative_to(Path(value).resolve()) for value in roots.values()):
            raise ValueError('Private storage would be inside a public repository')
        return {'repository': repository, 'root': private.as_posix()}

    def update_depot(self):
        from pyasm.security.security import _require_admin
        from .file_project_cmd import identifier, integer
        _require_admin()
        item = self.lock('depot', identifier(self.kwargs.get('depot')))
        data = item.get_json_value('data')
        revision = integer(self.kwargs.get('revision'))
        if revision != data.get('revision', 0):
            raise ValueError('Depot revision conflict')
        if 'repository' in self.kwargs:
            data['storage'] = self.depot_storage(self.kwargs['repository'])
        if 'title' in self.kwargs:
            title = self.kwargs['title']
            if not isinstance(title, str) or len(title.encode()) > 1024:
                raise ValueError('Invalid depot title')
            data['title'] = title
        data['revision'] = revision + 1
        save(item, data)
        return self.depot_status_result(item)

    def listing(self, kind):
        from .file_project_cmd import identifier, integer, CHUNK_LIMIT
        search = Search('file_project/' + kind)
        if kind == 'workspace':
            search.add_filter('login', self.owner)
        search.add_order_by('code')
        if self.kwargs.get('after'):
            search.add_filter('code', identifier(self.kwargs['after']), op='>')
        limit = integer(self.kwargs.get('limit', 100), 1, CHUNK_LIMIT)
        search.set_limit(limit + 1)
        rows = search.get_sobjects()
        from pyasm.biz.file_project import cache_read_records
        cache_read_records(kind, rows)
        items = []
        for row in rows[:limit]:
            data = row.get_json_value('data')
            try:
                if kind == 'depot':
                    self.permission(row.get_code(), 'read')
                else:
                    self.stream(row.get_code() if kind == 'stream' else data['stream'])
            except SecurityException:
                continue
            if kind == 'stream' and self.kwargs.get('depot') and data['depot'] != self.kwargs['depot']:
                continue
            public = self.stream_spec(row) if kind == 'stream' else self.result(row)
            if kind in ('depot', 'stream'):
                public['writable'] = self.has_permission(row.get_code() if kind == 'depot' else data['depot'], 'write')
            if kind == 'depot' and public.get('storage'):
                public['storage'] = {'repository': public['storage']['repository']}
            items.append(public)
        return {'items': items, 'after': rows[limit - 1].get_code() if len(rows) > limit else None}

    def depots(self):
        return self.listing('depot')

    def streams(self):
        return self.listing('stream')

    def stream_graph(self):
        """One permitted stream page and bounded real branch/merge provenance."""
        page=self.listing('stream')
        heads={node['code']:[node['head_change'],node['spec_revision']] for node in page['items']}
        if self.kwargs.get('heads') is not None and self.kwargs['heads']!=heads:
            raise ValueError('Graph changed; refresh it.')
        page['heads']=heads
        edges=[]
        allowed={}
        cursor=self.kwargs.get('edge_after','')
        if cursor:
            from .file_project_cmd import identifier
            parts=cursor.split('/')
            if len(parts)!=3 or parts[1] not in ('0','1'):raise ValueError('Invalid graph edge cursor')
            identifier(parts[0]);identifier(parts[2])
            if parts[0] not in {row['code'] for row in page['items']}:raise ValueError('Graph page changed; refresh it.')
        else:parts=['','','']
        scanned=0
        for node in page['items']:
            if cursor and node['code']<parts[0]:continue
            if node.get('parent') and (not cursor or node['code']!=parts[0]):
                original=node.get('branch_parent',node['parent'])==node['parent']
                edges.append({'source':node['parent'],'target':node['code'],'kind':'branch' if original else 'parent',
                              'change':node.get('parent_change') if original else None})
                scanned+=1
                if scanned==1000:
                    return {**page,'edges':edges,'edge_after':node['code']+'/0/'+node['parent'],'edge_limit':1000}
            if node.get('merge_bases_root'):
                after=parts[2] if node['code']==parts[0] and parts[1]=='1' else ''
                for merged in islice(self.catalog.entries(node['merge_bases_root'],after),max(0,1000-scanned)):
                    source=merged['stream']
                    if source not in allowed:
                        try:self.stream(source);allowed[source]=True
                        except SecurityException:allowed[source]=False
                    if allowed[source]:edges.append({'source':source,'target':node['code'],'kind':'merge','change':merged.get('change')})
                    scanned+=1
                    if scanned==1000:return {**page,'edges':edges,'edge_after':node['code']+'/1/'+source,'edge_limit':1000}
        return {**page,'edges':edges,'edge_after':None,'edge_limit':1000}

    def workspaces(self):
        return self.listing('workspace')

    def workspace_paths(self):
        from .file_project_cmd import CHUNK_LIMIT, logical_path, identifier
        _, data = self.workspace(lock=False)
        paths = self.kwargs.get('paths')
        if not isinstance(paths, list) or not 1 <= len(paths) <= CHUNK_LIMIT:
            raise ValueError('Resolve a bounded file path batch')
        if any(not isinstance(item, dict) or set(item) not in ({'stream','path'},{'local_path'}) for item in paths):
            raise ValueError('Workspace paths require stream/depot path or a relative local path')
        view = self.view(data)
        items = []
        for item in paths:
            if 'local_path' in item:
                path=logical_path(item['local_path'])
                mapped=view.reverse(path)
                items.append(mapped or {'path':path,'stream':None,'source_path':None,'excluded':True})
            else:
                path = logical_path(item['path'])
                stream=identifier(item['stream'])
                mapped = view.forward(stream, path)
                items.append(mapped or {'stream':stream,'source_path':path,'excluded':True})
        for stream in {item['stream'] for item in items if item.get('stream')}:
            self.stream(stream)
        return {'items':items,'view_revision':data.get('view_revision',0)}

    def file_states(self):
        """Read current Head/Have for a bounded set under workspace and depot ACLs."""
        mapped=self.workspace_paths()
        if any('local_path' in row for row in self.kwargs['paths']):
            raise ValueError('Resolve local paths with workspace_paths before requesting file states')
        _,ws=self.workspace(lock=False)
        view=self.view(ws)
        streams={stream:self.stream(stream)[1] for stream in {item['stream'] for item in self.kwargs['paths']}}
        writable={stream:self.has_permission(data['depot'], 'write') for stream,data in streams.items()}
        items=[]
        for source,target in zip(self.kwargs['paths'],mapped['items']):
            path=target['source_path']
            head=self.catalog.get(streams[source['stream']]['root'],path)
            have=None if target.get('excluded') else self.catalog.get(ws['have_root'],view.key(target['path']))
            status='unmapped' if target.get('excluded') else 'deleted' if head and head.get('deleted') else 'server-absent' if not head else 'server-only' if not have else 'current' if head.get('version')==have.get('version') else 'newer'
            items.append({**source,'path':path,'local_path':None if target.get('excluded') else target['path'],
                          'excluded':target.get('excluded',False),'writable':target.get('writable',False),
                          'depot_writable':writable[source['stream']],'head':head,'have':have,'head_state':status})
        holders = self.lock_holders({stream:[row['path'] for row in items if row['stream']==stream]
                                     for stream in streams})
        for row in items:
            row['holders'] = holders.get((row['stream'], row['path']), [])
        return {'items':items,'view_revision':mapped['view_revision']}

    def stream_status(self):
        item, data = self.stream()
        return {**self.stream_spec(item), **self.catalog.stats(data['root']),
                'writable': self.has_permission(data['depot'], 'write')}

    def file_info(self):
        """Inspect a selected file without enumerating a depot or changing the work tab."""
        from .file_project_cmd import logical_path
        path = logical_path(self.kwargs.get('path'))
        stream, data = self.stream()
        head = self.catalog.get(data['root'], path)
        selected = head
        if any(self.kwargs.get(key) for key in ('change', 'shelf', 'published_change')):
            root, _ = self.published_root()
            selected = self.catalog.get(root, path)
        info = {'path': path, 'stream': stream.get_code(), 'head': head, 'file': selected,
                'holders': [], 'have': None, 'local_path': None, 'excluded': False}
        if self.kwargs.get('workspace'):
            self.kwargs['paths'] = [{'stream': stream.get_code(), 'path': path}]
            info.update(self.file_states()['items'][0])
        else:
            self.kwargs['paths'] = [path]
            info['holders'] = next((row['holders'] for row in self.locks()['items'] if row['path']==path),[])
        info['holders'] = [{**holder,'number':find('change',holder['change']).get_id()} for holder in info['holders']]
        if selected and selected.get('version'):
            version = find('version', selected['version']).get_json_value('data')
            change = find('change', version['change'])
            change_data = change.get_json_value('data')
            info.update(author=change_data['owner'], description=change_data.get('description', '') if self.can_read_change_metadata(change_data) else '',
                        submitted_at=change_data.get('submitted_at'), change_number=change.get_id(),
                        provenance=version.get('integrated_from'), deleted=selected.get('deleted', False))
        preview = self.kwargs.get('preview', False)
        if not isinstance(preview, bool):
            raise ValueError('Preview must be a boolean')
        if preview and selected and not selected.get('deleted'):
            info['preview'] = self.file_preview()
        return info

    def file_preview(self):
        return self.preview_entry(self.transfer())

    def preview_entry(self, entry):
        """Bounded text/image preview; binary content keeps its metadata and a hex sample."""
        import base64
        import codecs
        with self.blob_path(entry['blob']).open('rb') as source:
            part = source.read(262144)
        result = {'path': entry['path'], 'size': entry['size'], 'sha256': entry['sha256'],
                  'truncated': entry['size'] > len(part), 'kind': 'binary', 'text': ''}
        for magic, mime in ((b'\x89PNG\r\n\x1a\n', 'image/png'), (b'\xff\xd8\xff', 'image/jpeg'),
                            (b'GIF8', 'image/gif'), (b'RIFF', 'image/webp')):
            if part.startswith(magic) and (mime != 'image/webp' or part[8:12] == b'WEBP') and not result['truncated']:
                result.update(kind='image', image='data:' + mime + ';base64,' + base64.b64encode(part).decode('ascii'))
                return result
        try:
            if b'\0' not in part:
                result.update(text=codecs.getincrementaldecoder('utf-8')().decode(part,final=not result['truncated']), kind='text')
        except UnicodeError:
            pass
        if result['kind'] == 'binary':
            result['text'] = part[:256].hex(' ')
        return result

    def compare_files(self):
        from difflib import unified_diff
        from .file_change import content
        allowed = {'path', 'stream', 'change', 'shelf', 'published_change', 'file_revision',
                   'revision', 'changelist', 'at_date', 'conflict_side', 'integration', 'edit_revision', 'workspace', 'have'}
        sources = [self.kwargs.get(side) for side in ('left', 'right')]
        if any(not isinstance(source, dict) or set(source) - allowed for source in sources):
            raise ValueError('Compare two authorized file selections')
        original = self.kwargs
        files, previews = [], []
        try:
            for source in sources:
                self.kwargs = source.copy()
                try:
                    entry=self.transfer()
                    files.append(entry)
                    previews.append(self.preview_entry(entry))
                except FileNotFoundError:
                    files.append({'path': self.kwargs['path'], 'size':0, 'sha256':None, 'deleted':True})
                    previews.append({'kind':'text', 'truncated':False, 'text':''})
        finally:
            self.kwargs = original
        identical = content(files[0]) == content(files[1])
        textual = all(item['kind'] == 'text' and not item['truncated'] for item in previews)
        return {'left': {k:v for k,v in files[0].items() if not k.startswith('_')},
                'right': {k:v for k,v in files[1].items() if not k.startswith('_')},
                'identical': identical, 'kind': 'text' if textual else 'binary',
                'text': ''.join(unified_diff(previews[0]['text'].splitlines(keepends=True), previews[1]['text'].splitlines(keepends=True),
                                           fromfile=sources[0]['path'], tofile=sources[1]['path'])) if textual else ''}

    def view(self, data):
        return FileView(data.get('mappings') or [{'stream': data['stream'], 'source': '...', 'target': '...', 'writable': True}],
                        data.get('case_sensitive', True))

    def validate_view(self, mappings, case_sensitive, primary):
        if not isinstance(case_sensitive, bool):
            raise ValueError('case_sensitive must be boolean')
        view = FileView(mappings, case_sensitive)
        for stream in sorted({rule['stream'] for rule in view.rules}):
            self.stream(stream)
        if not any(rule['stream'] == primary and not rule['exclude'] for rule in view.rules):
            raise ValueError('Primary stream must be mapped')
        return view.rules

    def workspace_pending(self, workspace, data):
        if data.get('pending_root'):
            return self.catalog.stats(data['pending_root'])['files'] > 0
        # Existing workspaces are checked once before the new pending index is installed.
        after = ''
        while True:
            search = Search('file_project/change')
            search.add_filter('login', self.owner)
            search.add_order_by('code')
            search.add_filter('code', after, op='>')
            search.set_limit(1000)
            rows = search.get_sobjects()
            if any(row.get_json_value('data').get('workspace') == workspace.get_code() and
                   row.get_json_value('data')['state'] == 'pending' for row in rows):
                return True
            if len(rows) < 1000:
                return False
            after = rows[-1].get_code()

    def workspace_preview(self):
        from .file_project_cmd import identifier, logical_path
        primary = identifier(self.kwargs.get('stream'))
        rules = self.validate_view(self.kwargs.get('mappings'),self.kwargs.get('case_sensitive',True),primary)
        view = FileView(rules,self.kwargs.get('case_sensitive',True))
        samples = self.kwargs.get('paths',[])
        if not isinstance(samples,list) or len(samples)>1000:
            raise ValueError('Preview requires at most 1000 path samples')
        results, seen = [], {}
        for sample in samples:
            if not isinstance(sample,dict) or set(sample) not in ({'local_path'},{'stream','path'}):
                raise ValueError('Preview a relative local path or stream/depot path')
            if 'local_path' in sample:
                path = logical_path(sample['local_path'])
                mapped = view.reverse(path)
                result = {'local_path':path,'stream':mapped['stream'] if mapped else None,
                          'source_path':mapped['source_path'] if mapped else None}
            else:
                stream = identifier(sample['stream']);path = logical_path(sample['path'])
                self.stream(stream)
                mapped = view.forward(stream,path)
                result = {'stream':stream,'source_path':path,'local_path':mapped['path'] if mapped else None}
            result.update(excluded=not mapped,writable=bool(mapped and mapped['writable']),collision=False)
            if mapped:
                key = view.key(result['local_path'])
                previous = seen.get(key)
                if previous is not None and (results[previous]['stream'],results[previous]['source_path']) != (result['stream'],result['source_path']):
                    result['collision']=results[previous]['collision']=True
                seen[key]=len(results)
            results.append(result)
        return {'mappings':rules,'items':results,'valid':not any(row['collision'] for row in results)}

    def workspace_switch_preview(self):
        target, data = self.workspace(lock=False)
        current = self.workspace_active()
        previous = current.get('info')
        return {'workspace':target.get_code(),'revision':current['revision'],'target':self.result(target),
                'previous':current.get('workspace'),'pending_changes':self.catalog.stats(previous['pending_root'])['files'] if previous and previous.get('pending_root') else None,
                'active_transfer':previous.get('active_transfer') if previous else None,
                'active_bulk_tasks':self.catalog.stats(previous['active_bulk_root'])['files'] if previous and previous.get('active_bulk_root') else 0}

    def update_workspace(self):
        from .file_project_cmd import identifier, integer
        workspace, data = self.workspace()
        key, digest, retry = self.receipt(workspace.get_code(), 'workspace_update')
        if retry is not None:
            return retry
        if integer(self.kwargs.get('view_revision')) != data.get('view_revision', 0):
            raise ValueError('Workspace view revision conflict')
        if data['active_sync'] or self.workspace_pending(workspace, data):
            raise ValueError('Finish sync and submit/revert pending changelists before changing the workspace view')
        primary = identifier(self.kwargs.get('stream', data['stream']))
        _, stream = self.stream(primary)
        mappings = self.kwargs.get('mappings', data.get('mappings'))
        if primary != data['stream'] and 'mappings' not in self.kwargs and mappings:
            mappings = [{**rule, 'stream': primary if rule['stream'] == data['stream'] else rule['stream']} for rule in mappings]
        if mappings is None:
            mappings = [{'stream': primary, 'source': '...', 'target': '...', 'writable': True}]
        sensitive = self.kwargs.get('case_sensitive', data.get('case_sensitive', True))
        mappings = self.validate_view(mappings, sensitive, primary)
        root = self.kwargs.get('local_root', data['local_root'])
        if not isinstance(root, str) or not root or len(root.encode()) > 2048:
            raise ValueError('Invalid local root metadata')
        if root != data['local_root'] or sensitive != data.get('case_sensitive', True):
            data['have_root'] = self.catalog.empty()
        data.update(stream=primary, depot=stream['depot'], mappings=mappings, case_sensitive=sensitive,
                    local_root=root, view_revision=data.get('view_revision', 0) + 1, pending_root=self.catalog.empty())
        self.save_change(workspace, data)
        return self.remember(key, digest, self.result(workspace))

    def active_workspace_key(self):
        return sha256(('active-workspace\0' + self.owner).encode()).hexdigest()

    def workspace_active(self):
        item = find('chunk', self.active_workspace_key(), False)
        if not item:
            return {'workspace': None, 'revision': 0}
        data = item.get_json_value('data')
        workspace = find('workspace', data['workspace'])
        self.stream(workspace.get_json_value('data')['stream'])
        return {'workspace': data['workspace'], 'revision': data['revision'], 'info': self.result(workspace)}

    def switch_workspace(self):
        from .file_project_cmd import integer
        workspace, _ = self.workspace()
        receipt, digest, retry = self.receipt(workspace.get_code(), 'workspace_switch')
        if retry is not None:
            return retry
        key = self.active_workspace_key()
        item = find('chunk', key, False)
        item = self.lock('chunk', key) if item else None
        old = item.get_json_value('data') if item else {'revision': 0}
        if integer(self.kwargs.get('revision')) != old['revision']:
            raise ValueError('Active workspace revision conflict')
        data = {'owner': self.owner, 'workspace': workspace.get_code(), 'revision': old['revision'] + 1}
        save(item, data) if item else create('chunk', data, key)
        return self.remember(receipt, digest, {'workspace': workspace.get_code(), 'revision': data['revision']})

    def check_workspace_paths(self, data, paths):
        if not data.get('workspace_view'):
            return
        view = self.view({'mappings': data['workspace_view'], 'case_sensitive': data.get('case_sensitive', True)})
        for path in paths:
            mapped = view.forward(data['stream'], path)
            if not mapped or not mapped['writable']:
                raise SecurityException('Path is excluded or read-only in this workspace: ' + path)

    def close_workspace_change(self, change, data):
        if not data.get('workspace'):
            return
        workspace = self.lock('workspace', data['workspace'])
        ws = workspace.get_json_value('data')
        if ws.get('pending_root'):
            ws['pending_root'] = self.catalog.update(ws['pending_root'], [{'path': change.get_code(), 'delete': True}])
            self.save_change(workspace, ws)

    def sync_paths(self):
        from .file_project_cmd import CHUNK_LIMIT, logical_path
        paths=self.kwargs.get('paths')
        if paths is None:return None
        if not isinstance(paths,list) or not 1<=len(paths)<=CHUNK_LIMIT:
            raise ValueError('Sync requires 1..1000 explicit local paths, or a subtree prefix')
        if self.kwargs.get('prefix'):raise ValueError('Choose explicit paths or a subtree prefix')
        return sorted({logical_path(path) for path in paths})

    def sync_entries(self, data):
        from .file_project_cmd import CHUNK_LIMIT
        if data.get('paths') is not None:
            return [file for path in data['paths'] if path>data['after']
                    and (file:=self.catalog.get(data['root'],path)) is not None]
        return list(islice(self.catalog.entries(data['root'],data['after'],data['prefix'],include_deleted=True),CHUNK_LIMIT+1))

    def mapped_sync_begin(self, workspace, ws):
        from .file_project_cmd import logical_path, identifier
        from .file_revision import revision_spec
        view = self.view(ws)
        prefix = logical_path(self.kwargs.get('prefix', ''), prefix=True)
        if prefix and not prefix.endswith('/'):raise ValueError('Folder sync prefix must end with /')
        scope=identifier(self.kwargs['source_stream']) if self.kwargs.get('source_stream') else None
        depot=identifier(self.kwargs['source_depot']) if self.kwargs.get('source_depot') else None
        selected=self.sync_paths()
        if selected is not None and any(not view.reverse(path) for path in selected):
            raise ValueError('Selected local paths must be mapped to this workspace')
        selected_mappings={view.reverse(path)['mapping'] for path in selected} if selected is not None else None
        checkpoint = ws.get('sync_checkpoint', {})
        incremental = not self.kwargs.get('force') and not revision_spec(self.kwargs) and not scope and not depot and selected is None and not prefix and checkpoint.get('view_revision') == ws.get('view_revision', 0) and checkpoint.get('have_root') == ws['have_root']
        sources = {}
        slots = []
        for index, rule in enumerate(view.rules):
            if rule['exclude'] or scope and rule['stream']!=scope or selected_mappings is not None and index not in selected_mappings:
                continue
            if depot and self.stream(rule['stream'])[1]['depot']!=depot:continue
            scan_prefix=FileView.prefix(rule['source'])
            # shortcut: insensitive subtrees scan their mapping; add a folded path index for narrow million-file seeks.
            if prefix and view.case_sensitive:
                mapped=view.reverse(prefix+'__subtree__')
                if mapped and mapped['mapping']==index:scan_prefix=mapped['source_path'][:-len('__subtree__')]
                elif not FileView.prefix(rule['target']).startswith(prefix):continue
            elif prefix:
                target_prefix=view.key(FileView.prefix(rule['target']))
                if not view.key(prefix).startswith(target_prefix) and not target_prefix.startswith(view.key(prefix)):continue
            if rule['stream'] not in sources:
                sources[rule['stream']] = self.sync_source(rule['stream'])
            slots.append({'stream': rule['stream'], 'mapping': index, 'prefix': scan_prefix,
                          'previous_root': checkpoint.get('sources', {}).get(rule['stream']) if incremental else None,
                          **sources[rule['stream']]})
        if not slots:raise ValueError('Selected stream or folder is not mapped to this workspace')
        job = create('sync', {'owner': self.owner, 'workspace': workspace.get_code(), 'stream': ws['stream'],
            'force':self.kwargs.get('force',False),'source_stream':scope,'source_depot':depot,'file_revision':revision_spec(self.kwargs).get('file_revision'),
            'mapped': True, 'mappings': ws['mappings'], 'case_sensitive': ws.get('case_sensitive', True),
            'view_revision': ws.get('view_revision', 0), 'slots': slots, 'slot': 0, 'after': '', 'phase': 'files',
            'prefix': prefix, 'paths':selected, 'incremental': incremental, 'desired_root': ws['have_root'] if incremental else self.catalog.empty(),
            'state': 'running', 'files_done': 0, 'bytes_done': 0, 'ack_revision': 0})
        ws['active_sync'] = job.get_code()
        self.save_change(workspace, ws)
        return self.result(job)

    def mapped_plan(self, data, ws):
        from .file_project_cmd import CHUNK_LIMIT
        view = self.view(data)
        desired, items, missing = [], [], []
        after, slot, phase = data['after'], data['slot'], data['phase']
        if phase == 'files':
            source = data['slots'][slot]
            self.stream(source['stream'])
            if data.get('paths') is not None:
                mapped_paths=[view.reverse(path) for path in data['paths']]
                scan=({**(self.catalog.get(source['root'],mapped['source_path']) or {'deleted':True,'size':0}), 'path':mapped['source_path']} for mapped in mapped_paths if mapped['mapping']==source['mapping'])
            elif source.get('previous_root'):
                scan = ({**(entry or {'size': 0, 'deleted': True}), 'path': path}
                        for path, _, entry in self.catalog.diff(source['previous_root'], source['root'], after))
            else:
                scan = self.catalog.entries(source['root'], after, source['prefix'], include_deleted=True)
            entries = list(islice(scan, CHUNK_LIMIT + 1))
            revision_files=None
            if data.get('file_revision'):
                revision_files,missing=self.file_revisions(entries[:CHUNK_LIMIT],data['file_revision'],source['stream'])
                for path in missing:
                    mapped=view.forward(source['stream'],path)
                    have=self.catalog.get(ws['have_root'],view.key(mapped['path'])) if mapped else None
                    if have:desired.append(have)
            seen = {}
            for original in entries[:CHUNK_LIMIT]:
                file=revision_files.get(original['path']) if revision_files is not None else original
                if file is None:continue
                mapped = view.forward(source['stream'], file['path'])
                if not mapped or mapped['mapping'] != source['mapping'] or not view.key(mapped['path']).startswith(view.key(data['prefix'])):
                    continue
                key = view.key(mapped['path'])
                entry = {**file, 'path': key, 'local_path': mapped['path'], 'source_path': file['path'],
                         'stream': source['stream'], 'published_change': source['published_change'],
                         'writable': mapped['writable']}
                previous = seen.get(key) or self.catalog.get(data['desired_root'], key)
                if previous and (previous['stream'], previous['source_path']) != (entry['stream'], entry['source_path']):
                    old = self.catalog.get(source['root'], previous['source_path']) if previous['stream'] == source['stream'] else previous
                    if not file.get('deleted') and old and not old.get('deleted'):
                        raise ValueError('Multiple server files map to one local path: ' + mapped['path'])
                seen[key] = entry
                have = self.catalog.get(ws['have_root'], key)
                if file.get('deleted'):
                    if data.get('incremental') and previous and previous.get('source_path') == file['path']:
                        desired.append({'path': key, 'delete': True})
                    if have and not have.get('deleted') and have.get('source_path', have['path']) == file['path']:
                        items.append(entry)
                else:
                    desired.append(entry)
                    if data.get('force') or not have or (have.get('stream'), have.get('source_path'), have.get('version')) != (entry['stream'], entry['source_path'], entry['version']):
                        items.append(entry)
            if len(entries) > CHUNK_LIMIT:
                after = entries[CHUNK_LIMIT - 1]['path']
            else:
                slot, after = slot + 1, ''
                if slot == len(data['slots']):
                    phase = 'complete' if data.get('incremental') or data.get('paths') is not None else 'cleanup'
        else:
            entries = list(islice(self.catalog.entries(ws['have_root'], after, view.key(data['prefix'])), CHUNK_LIMIT + 1))
            for entry in entries[:CHUNK_LIMIT]:
                mapped=view.reverse(entry.get('local_path',entry['path']))
                if (not data.get('source_stream') or entry.get('stream')==data['source_stream'] or mapped and mapped['stream']==data['source_stream']) and (not data.get('source_depot') or entry.get('stream') in {slot['stream'] for slot in data['slots']}) and not self.catalog.get(data['desired_root'], entry['path']):
                    items.append({**entry, 'deleted': True, 'size': 0})
            after = entries[min(len(entries), CHUNK_LIMIT) - 1]['path'] if entries else after
            if len(entries) <= CHUNK_LIMIT:
                phase = 'complete'
        # A case-only rename can contain a tombstone and a replacement in one chunk.
        unique = {}
        for entry in items:
            if entry['path'] not in unique or not entry.get('deleted'):
                unique[entry['path']] = entry
        return {'items': list(unique.values()), 'desired': desired, 'phase': phase, 'slot': slot, 'after': after, 'missing':missing}

    def sync_file(self, path):
        _,data,_,_=self.sync_job()
        view=self.view(data) if data.get('mapped') else None
        if self.kwargs.get('ack_revision') is not None and self.kwargs['ack_revision']!=data['ack_revision']:
            raise ValueError('Download plan changed')
        selected={view.key(item) if view else item for item in data['paths']} if data.get('paths') is not None else None
        if selected is not None and path not in selected or data.get('prefix') and not path.startswith(view.key(data['prefix']) if view else data['prefix']):
            raise ValueError('File is outside the sync selection')
        if data.get('mapped'):
            mapped=view.reverse(path)
            source=next((slot for slot in data['slots'] if mapped and slot['mapping']==mapped['mapping']),None)
            if source is None:raise ValueError('File is not mapped by this sync')
            self.stream(source['stream'])
            source_path=self.kwargs.get('source_path',mapped['source_path'])
            forward=view.forward(source['stream'],source_path)
            if not forward or forward['mapping']!=source['mapping'] or view.key(forward['path'])!=path:
                raise ValueError('Source file is outside the sync mapping')
            entry=self.catalog.get(source['root'],source_path)
        else:
            entry=self.catalog.get(data['root'],path)
        if entry is None:raise FileNotFoundError(path)
        if data.get('file_revision') and entry:
            selected,_=self.file_revisions([entry],data['file_revision'],source['stream'])
            entry=selected.get(entry['path'])
            if entry is None:raise FileNotFoundError(path)
        return entry

    def mapped_sync_next(self, job, data, ws):
        plan = self.mapped_plan(data, ws)
        items = [{**entry, '_have': self.catalog.get(ws['have_root'], entry['path'])} for entry in plan['items']]
        return {'sync': job.get_code(), 'mapped': True, 'items': items, 'more': plan['phase'] != 'complete',
                'ack_revision': data['ack_revision'], 'files_done': data['files_done'], 'bytes_done': data['bytes_done'],
                'stream': data['stream'], 'published_change': None, 'phase': data['phase']}

    def mapped_sync_ack(self, job, data, workspace, ws, paths):
        plan = self.mapped_plan(data, ws)
        if paths != [entry['path'] for entry in plan['items']]:
            raise ValueError('Acknowledge the complete mapped chunk after local writes')
        data['missing_revisions']=data.get('missing_revisions',0)+len(plan['missing'])
        if plan['missing']:data['missing_path']=plan['missing'][0]
        edits = [{'path': entry['path'], 'delete': True} if entry.get('deleted') else entry for entry in plan['items']]
        ws['have_root'] = self.catalog.update(ws['have_root'], edits)
        data['transferred_root'] = self.catalog.update(data.get('transferred_root') or self.catalog.empty(),plan['items'])
        data['desired_root'] = self.catalog.update(data['desired_root'], plan['desired'])
        if plan['phase'] == 'cleanup' and ws['have_root'] == data['desired_root']:
            plan['phase'] = 'complete'
        data.update(phase=plan['phase'], slot=plan['slot'], after=plan['after'], ack_revision=data['ack_revision'] + 1,
                    last_ack=sha256(encode(paths).encode()).hexdigest(), files_done=data['files_done'] + len(plan['items']),
                    bytes_done=data['bytes_done'] + sum(entry['size'] for entry in plan['items']))
        if plan['phase'] == 'complete':
            data['state'], ws['active_sync'] = 'complete', None
            if not data['prefix'] and data.get('paths') is None and not any(data.get(key) for key in ('source_stream','source_depot','file_revision')):
                ws['sync_checkpoint'] = {'view_revision': data['view_revision'], 'have_root': ws['have_root'],
                                         'sources': {slot['stream']: slot['root'] for slot in data['slots']}}
        self.save_change(workspace, ws)
        save(job, data)
        return self.result(job)

    def reconcile(self):
        from .file_project_cmd import CHUNK_LIMIT, integer, logical_path
        workspace, ws = self.workspace(lock=False)
        if 'view_revision' in self.kwargs and integer(self.kwargs['view_revision']) != ws.get('view_revision', 0):
            raise ValueError('Workspace view changed; restart reconciliation')
        if self.kwargs.get('have_root') and self.kwargs['have_root'] != ws['have_root']:
            raise ValueError('Have changed; restart reconciliation')
        files = self.kwargs.get('files')
        if not isinstance(files, list) or not 1 <= len(files) <= CHUNK_LIMIT or len(encode(files).encode()) > 2 * 1024 * 1024:
            raise ValueError('Reconcile requires a bounded local manifest')
        pinned = self.kwargs.get('heads', {})
        if not isinstance(pinned, dict) or len(pinned) > FileView.LIMIT or len(encode(pinned).encode()) > 64 * 1024:
            raise ValueError('Invalid pinned stream heads')
        view = self.view(ws)
        items, paths, heads = [], set(), {}
        for local in files:
            if not isinstance(local, dict) or set(local) - {'path', 'size', 'sha256', 'missing'}:
                raise ValueError('Invalid local file descriptor')
            path = logical_path(local.get('path'))
            key = view.key(path)
            if key in paths:
                raise ValueError('Duplicate local file path')
            paths.add(key)
            missing = local.get('missing', False)
            if not isinstance(missing, bool):
                raise ValueError('missing must be boolean')
            if not missing:
                integer(local.get('size'))
                digest = local.get('sha256')
                if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
                    raise ValueError('Local SHA-256 required for content comparison')
            mapping = view.reverse(path)
            have = self.catalog.get(ws['have_root'], key)
            if mapping and have and have.get('stream') == mapping['stream']:
                previous = view.forward(have['stream'], have.get('source_path', have['path']))
                if previous and view.key(previous['path']) == key:
                    mapping = previous
            if not mapping:
                items.append({'path': path, 'local_status': 'unmapped', 'server_status': 'unmapped', 'have': have})
                continue
            stream = mapping['stream']
            if stream not in heads:
                _, heads[stream] = self.stream(stream)
                if stream in pinned:
                    from .file_project_cmd import identifier
                    snapshot = find('change', identifier(pinned[stream])).get_json_value('data')
                    if snapshot['stream'] != stream or snapshot['state'] != 'submitted':
                        raise SecurityException('Reconciliation requires a published snapshot of the authorized stream')
                    heads[stream] = {**heads[stream], 'root': snapshot['root'], 'head_change': pinned[stream]}
            head = self.catalog.get(heads[stream]['root'], mapping['source_path'])
            exists = head and not head.get('deleted')
            server_status = 'deleted' if not exists and have else 'untracked' if not exists else 'current' if have and have.get('version') == head['version'] and have.get('stream', ws['stream']) == stream else 'newer'
            baseline = have if have and not have.get('deleted') else None
            local_status = 'missing' if missing else 'added' if not baseline else 'clean' if (local['size'], local['sha256']) == (baseline['size'], baseline['sha256']) else 'modified'
            items.append({'path': path, 'stream': stream, 'source_path': mapping['source_path'], 'writable': mapping['writable'],
                          'local_status': local_status, 'server_status': server_status, 'have': have, 'head': head})
        keys={sha256((row['stream']+'\0'+row['source_path']).encode()).hexdigest():row
              for row in items if row.get('stream') and row.get('writable')}
        if keys:
            descriptors={row['path']:row for row in files}
            search=Search('file_project/checkout');search.add_filters('code',list(keys))
            pending={}
            for opened in search.get_sobjects():
                row=keys[opened.get_code()]
                for holder in opened.get_json_value('data')['holders']:
                    if holder['owner']!=self.owner or holder.get('workspace')!=workspace.get_code():continue
                    if holder['change'] not in pending:
                        pending[holder['change']]=find('change',holder['change']).get_json_value('data')
                    change=pending[holder['change']]
                    if change['state']!='pending':continue
                    entry=self.catalog.get(change['work_root'],row['source_path']) if change.get('work_root') else None
                    if not entry:continue
                    descriptor=descriptors[row['path']]
                    staged=entry.get('file') or {}
                    current=bool(descriptor.get('missing')) if entry['action'] in ('delete','move/delete') else not descriptor.get('missing') and staged.get('sha256')==descriptor.get('sha256')
                    row.setdefault('pending',[]).append({'change':holder['change'],'edit_revision':change['edit_revision'],
                        'action':entry['action'],'staged_current':current})
        return {'workspace': workspace.get_code(), 'view_revision': ws.get('view_revision', 0), 'have_root': ws['have_root'],
                'heads': {code: data['head_change'] for code, data in heads.items()}, 'items': items}
