"""Private, pinned query selections; no client expansion of large catalogs."""
from itertools import islice

from pyasm.biz.file_project import create, find
from pyasm.common.errors import SecurityException


class FileSelectionMixin:
    def checkout_chunks(self, data):
        """Expand folder roots on the server, keeping at most one path chunk."""
        from .file_project_cmd import logical_path, CHUNK_LIMIT
        paths = self.kwargs.get('paths', [])
        directories = self.kwargs.get('directories', [])
        local_directories = self.kwargs.get('local_directories', [])
        if any(not isinstance(items, list) for items in (paths, directories, local_directories)) or not 1 <= len(paths) + len(directories) + len(local_directories) <= CHUNK_LIMIT:
            raise ValueError('Checkout requires a bounded path chunk or folder roots')
        paths = [logical_path(path) for path in paths]
        if len(set(paths)) != len(paths):
            raise ValueError('Duplicate checkout paths')
        if not directories and not local_directories:
            yield paths
            return
        for items in (directories, local_directories):
            for prefix in items:
                logical_path(prefix, prefix=True)
                if prefix and not prefix.endswith('/'):
                    raise ValueError('Checkout folders must end with /')
        prefixes = []
        for prefix in sorted(set(directories)):
            if not prefixes or not prefix.startswith(prefixes[-1]):
                prefixes.append(prefix)
        view = self.view({'mappings': data.get('workspace_view'), 'stream': data['stream'], 'case_sensitive': data.get('case_sensitive', True)})
        local_prefixes = [view.key(prefix) for prefix in local_directories]

        def selected(path):
            mapped = view.forward(data['stream'], path)
            return bool(mapped and (any(path.startswith(prefix) for prefix in prefixes) or any(view.key(mapped['path']).startswith(prefix) for prefix in local_prefixes)))

        explicit = []
        for path in paths:
            entry = self.catalog.get(data['base_root'], path) if selected(path) else None
            if not entry or entry.get('deleted'):
                explicit.append(path)
        if explicit:
            yield explicit
        # Local folders can combine mappings; scanning stays paged, source folders seek directly.
        for prefix in [''] if local_prefixes else prefixes:
            scanned = self.catalog.entries(data['base_root'], prefix=prefix)
            chunk = []
            for entry in scanned:
                path = entry['path']
                if not selected(path):
                    continue
                chunk.append(path)
                if len(chunk) == CHUNK_LIMIT:
                    yield chunk
                    chunk = []
            if chunk:
                yield chunk

    def select_query(self):
        from .file_project_cmd import logical_path
        source = self.kwargs.get('source')
        prefix = logical_path(self.kwargs.get('prefix',''), prefix=True)
        name = self.kwargs.get('name','')
        action = self.kwargs.get('file_action','')
        start = logical_path(self.kwargs.get('start_path',''),prefix=True)
        end = logical_path(self.kwargs.get('end_path',''),prefix=True)
        if start and end and start>end:
            raise ValueError('Selection range start must precede its end')
        if not isinstance(name,str) or len(name.encode())>4096 or action not in ('','write','delete','checkout','move/add','move/delete'):
            raise ValueError('Select a valid file-name/action filter')
        if source=='depot':
            root,published=self.published_root()
            reference={'stream':self.kwargs['stream'],'published_change':published}
        elif source=='have':
            item,data=self.workspace(lock=False)
            view=self.view(data)
            for rule in view.rules:self.stream(rule['stream'])
            prefix,start,end=view.key(prefix),view.key(start),view.key(end)
            root=data['have_root'];reference={'workspace':item.get_code(),'view_revision':data.get('view_revision',0)}
        elif source=='change':
            data=self.inspect_change()
            root=data['work_root'];reference={'change':data['code'],'stream':data['stream'],'edit_revision':data['edit_revision']}
        else:
            raise ValueError('Select a server file view for a query selection')
        values={'kind':'selection','owner':self.owner,'state':'ready','source':source,'root':root,
                'prefix':prefix,'name':name,'file_action':action,'reference':reference,'start_path':start,'end_path':end}
        count=self.catalog.prefix_stats(root,prefix) if not name and not action and not start and not end else {'files':None,'bytes':None}
        item=create('sync',values)
        return {'selection':item.get_code(),'count_known':count['files'] is not None,**count}

    def selected_query(self):
        from .file_project_cmd import identifier
        item=find('sync',identifier(self.kwargs.get('selection')))
        data=item.get_json_value('data')
        if data.get('owner')!=self.owner or data.get('kind')!='selection':
            raise SecurityException('Query selection belongs to another user')
        if data['state']!='ready':
            raise ValueError('Query selection expired; select the files again')
        reference=data['reference']
        if data['source']=='have':
            old=self.kwargs
            try:
                self.kwargs={**old,'workspace':reference['workspace']}
                _,ws=self.workspace(lock=False)
                for rule in self.view(ws).rules:self.stream(rule['stream'])
            finally:self.kwargs=old
        elif data['source']=='change':
            old=self.kwargs
            try:
                self.kwargs={**old,'change':reference['change']}
                self.inspect_change()
            finally:self.kwargs=old
        else:self.stream(reference['stream'])
        return data

    @staticmethod
    def selection_matches(data,entry):
        return (not data.get('start_path') or entry['path']>=data['start_path']) and (
            not data.get('end_path') or entry['path']<=data['end_path']) and (
            not data['name'] or data['name'].lower() in entry['path'].lower()) and (
            not data['file_action'] or entry.get('action')==data['file_action'])

    def selection_entries(self,data,after=''):
        start = data.get('start_path','')
        end = data.get('end_path','')
        if not after and start:
            row = self.catalog.get(data['root'],start)
            if row and not row.get('deleted') and start.startswith(data['prefix']):
                yield row
        for row in self.catalog.entries(data['root'],max(after,start),data['prefix']):
            if end and row['path']>end:
                break
            yield row

    def selection_page(self):
        from .file_project_cmd import logical_path,integer,CHUNK_LIMIT
        data=self.selected_query()
        after=self.kwargs.get('after','')
        if after:logical_path(after)
        limit=integer(self.kwargs.get('limit',200),1,CHUNK_LIMIT)
        scanned=list(islice(self.selection_entries(data,after),limit+1))
        rows=[row for row in scanned[:limit] if self.selection_matches(data,row)]
        return {'items':rows,'after':scanned[limit-1]['path'] if len(scanned)>limit else None,
                'selection':self.kwargs['selection']}
