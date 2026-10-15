"""Authorized bounded revert plans and atomic workspace file selections."""
from hashlib import sha256
from itertools import islice

from pyasm.biz.file_project import find, save
from pyasm.common.errors import SecurityException


class FileRevertMixin:
    def select_unchanged(self):
        """Collect local comparisons for the existing atomic bulk-remove command."""
        from pyasm.biz.file_project import create
        from .file_project_cmd import logical_path, identifier
        item, data = self.change(lock=False)
        self.stream(data['stream'], 'write')
        self.editable(data)
        self.revision(data)
        key, digest, retry = self.receipt(item.get_code(), 'select_unchanged')
        if retry is not None:
            return retry
        files = self.kwargs.get('files')
        if not isinstance(files, list) or not 1 <= len(files) <= 1000:
            raise ValueError('Compare 1..1000 local files per page')
        entries = []
        for file in files:
            if not isinstance(file, dict) or set(file) != {'path', 'sha256'}:
                raise ValueError('Local comparisons require a path and SHA-256')
            path = logical_path(file['path'])
            entry = self.catalog.get(data['work_root'], path)
            base = (entry or {}).get('base') or {}
            if (not entry or entry['action'] not in ('checkout', 'write') or not base.get('sha256')
                    or base.get('deleted') or base['sha256'] != file['sha256']):
                raise ValueError('File differs from its checkout base: ' + path)
            entries.append(entry)
        reference = dict(change=item.get_code(), stream=data['stream'], edit_revision=data['edit_revision'])
        if self.kwargs.get('selection'):
            selection = self.lock('sync', identifier(self.kwargs['selection']))
            selected = selection.get_json_value('data')
            if selected.get('owner') != self.owner or selected.get('kind') != 'selection':
                raise SecurityException('Query selection belongs to another user')
            if (selected.get('state') != 'ready' or not selected.get('local_unchanged')
                    or selected.get('reference') != reference):
                raise ValueError('Unchanged-file selection is stale')
            selected['root'] = self.catalog.update(selected['root'], entries)
            self.save_change(selection, selected)
        else:
            root = self.catalog.update(self.catalog.empty(), entries)
            self.pages.flush()
            selection = create('sync', dict(kind='selection', owner=self.owner, state='ready',
                source='change', reference=reference, local_unchanged=True,
                root=root, prefix='', name='', file_action=''))
        return self.remember(key, digest, {'selection': selection.get_code()})

    def revert_plan(self):
        from .file_project_cmd import integer, logical_path
        workspace, ws = self.workspace(lock=False)
        view = self.view(ws)
        if self.kwargs.get('change'):
            item, data = self.change(lock=False)
            if data['workspace'] != workspace.get_code():
                raise SecurityException('Revert requires the changelist workspace')
            self.revision(data)
            if 'work_root' not in data:
                raise ValueError('Index pending metadata before reverting local files')
            after = logical_path(self.kwargs['after']) if self.kwargs.get('after') else ''
            limit = integer(self.kwargs.get('limit', 1000), 1, 1000)
            entries = list(islice(self.catalog.entries(data['work_root'], after), limit + 1))
            groups = [(item, data, entries[:limit])]
            cursor = entries[limit-1]['path'] if len(entries)>limit else None
        else:
            files = self.kwargs.get('files')
            if not isinstance(files,list) or not 1 <= len(files) <= 1000:
                raise ValueError('Select 1..1000 opened files')
            if any(not isinstance(row,dict) or set(row)-{'stream','path','change'} for row in files):
                raise ValueError('Choose workspace file paths')
            states = self.read_call('file_states', {'workspace':workspace.get_code(),
                'paths':[{'stream':row['stream'],'path':row['path']} for row in files]})['items']
            selected = {}
            for requested, state in zip(files,states):
                holders = [row for row in state['holders'] if row['owner']==self.owner
                    and row.get('workspace')==workspace.get_code()
                    and (not requested.get('change') or row['change']==requested['change'])]
                if not holders:
                    raise ValueError('The selected file is not opened in this workspace: '+state['path'])
                for holder in holders:
                    selected.setdefault(holder['change'],set()).add(state['path'])
            groups=[]
            for code,paths in sorted(selected.items()):
                item=find('change',code);data=item.get_json_value('data')
                entries={path:self.catalog.get(data['work_root'],path) for path in paths}
                for entry in list(entries.values()):
                    if entry and entry['action'] in ('move/add','move/delete'):
                        file=entry.get('file') or {}
                        partner=file.get('moved_from') or file.get('moved_to')
                        if partner:entries[partner]=self.catalog.get(data['work_root'],partner)
                if any(entry is None for entry in entries.values()):
                    raise ValueError('An opened file changed; refresh and retry')
                groups.append((item,data,list(entries.values())))
            if sum(len(entries) for _,_,entries in groups)>1000:
                raise ValueError('Select at most 1000 opened paths, including rename pairs')
            cursor=None
        items=[];revisions=[]
        for item,data,entries in groups:
            _,head=self.stream(data['stream'])
            revisions.append({'change':item.get_code(),'edit_revision':data['edit_revision'],
                'paths':[entry['path'] for entry in entries]})
            for entry in entries:
                mapped=view.forward(data['stream'],entry['path'])
                current=self.catalog.get(head['root'],entry['path'])
                base=entry.get('base')
                new_file=(not base or base.get('deleted')) and entry['action'] not in ('move/add','move/delete')
                items.append({'stream':data['stream'],'path':entry['path'],
                    'local_path':mapped['path'] if mapped and not mapped.get('excluded') else None,
                    'delete_local':bool(new_file and (not current or current.get('deleted'))
                        and mapped and mapped.get('writable') and not mapped.get('excluded'))})
        return {'items':items,'groups':revisions,'after':cursor}

    def revert_files(self):
        from .file_project_cmd import identifier, integer, logical_path
        workspace,ws=self.workspace(lock=False)
        groups=self.kwargs.get('groups')
        if not isinstance(groups,list) or not groups or len(groups)>1000:
            raise ValueError('Choose bounded pending changelists')
        count=0;codes=set();streams=set()
        for group in groups:
            if not isinstance(group,dict) or set(group)!={'change','edit_revision','paths'}:
                raise ValueError('Choose pinned opened file paths')
            code=identifier(group['change']);integer(group['edit_revision'])
            if code in codes:raise ValueError('Duplicate revert changelist')
            codes.add(code)
            paths=group['paths']
            if not isinstance(paths,list) or not paths:
                raise ValueError('Choose unique opened paths')
            for path in paths:logical_path(path)
            if len(set(paths))!=len(paths):raise ValueError('Choose unique opened paths')
            count+=len(paths)
            data=find('change',code).get_json_value('data')
            if data['owner']!=self.owner or data['workspace']!=workspace.get_code():
                raise SecurityException('Revert requires owned workspace changes')
            streams.add(data['stream'])
        if count>1000:raise ValueError('Select at most 1000 opened paths')
        for stream in sorted(streams):self.stream(stream,'write',lock=True)
        key,digest,retry=self.receipt(workspace.get_code(),'revert_files')
        if retry is not None:return retry
        original=self.kwargs;request=identifier(original.get('request_id'));results=[]
        try:
            for group in sorted(groups,key=lambda row:row['change']):
                self.kwargs={**group,'request_id':sha256((request+'\0'+group['change']).encode()).hexdigest()}
                results.append(self.remove_files())
        finally:self.kwargs=original
        return self.remember(key,digest,{'changes':results})

    def revert_change(self):
        _,probe=self.change(lock=False,pending=False)
        self.stream(probe['stream'],'write',lock=True)
        change,data=self.change(pending=False)
        receipt=self.receipt(change.get_code(),'revert') if self.kwargs.get('request_id') else None
        if receipt and receipt[2] is not None:return receipt[2]
        if data['state']!='pending':raise ValueError('Choose a pending changelist')
        if 'edit_revision' in self.kwargs:self.revision(data)
        self.editable(data)
        data['state']='reverted';save(change,data)
        self.close_workspace_change(change,data)
        result={'change':change.get_code(),'state':'reverted'}
        return self.remember(receipt[0],receipt[1],result) if receipt else result
