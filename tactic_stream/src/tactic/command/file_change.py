"""Changelist operations on immutable catalogs, inside FileProjectCmd's native transaction."""
from hashlib import sha256
from itertools import islice
import uuid

from pyasm.biz.file_project import create, encode, find, save, save_batch, commit_records
from pyasm.common.errors import SecurityException
from pyasm.search import Search


def identity(entry):
    return entry.get('version') if entry else None


def content(entry):
    if not entry or entry.get('deleted'):
        return None
    return entry['size'], entry['sha256']


class FileChangeMixin:
    def save_change(self, item, data):
        # Native row callbacks must see every page referenced by the new catalog roots.
        self.pages.flush()
        save(item, data)

    def revision(self, data, field='edit_revision'):
        from .file_project_cmd import integer
        if integer(self.kwargs.get(field)) != data['edit_revision']:
            raise ValueError('Changelist edit revision conflict')

    def editable(self, data):
        if data.get('active_bulk') and data['active_bulk'] != getattr(self, '_bulk_job', None):
            raise ValueError('Finish or cancel the bulk operation before editing this changelist')
        if data.get('active_transfer') and data['active_transfer'] != getattr(self, '_staging_transfer', None):
            raise ValueError('Finish or cancel the upload before editing or submitting this changelist')
        if data.get('integration'):
            raise ValueError('Finish or cancel changelist integration before editing')
        if data.get('indexing'):
            raise ValueError('Finish metadata indexing before editing this changelist')
        if 'work_root' not in data:
            raise ValueError('Index this older pending changelist with index_change first')

    def mutation(self):
        _, probe = self.change(lock=False)
        self.stream(probe['stream'], 'write', lock=True)
        item, data = self.change()
        return item, data

    def receipt(self, change, operation):
        from .file_project_cmd import identifier
        request = identifier(self.kwargs.get('request_id'))
        key = sha256((change + '\0' + operation + '\0' + request).encode()).hexdigest()
        digest = sha256(encode({k: v for k, v in self.kwargs.items() if k not in ('log_exception',)}).encode()).hexdigest()
        item = find('chunk', key, False)
        if item:
            data = item.get_json_value('data')
            if data['digest'] != digest:
                raise ValueError('Request identifier reused with different data')
            return key, digest, data['result']
        return key, digest, None

    @staticmethod
    def remember(key, digest, result):
        create('chunk', {'digest': digest, 'result': result}, key)
        return result

    def paths(self):
        from .file_project_cmd import CHUNK_LIMIT, logical_path
        paths = self.kwargs.get('paths')
        if not isinstance(paths, list) or not 1 <= len(paths) <= CHUNK_LIMIT:
            raise ValueError('A bounded path chunk is required')
        paths = [logical_path(path) for path in paths]
        if len(set(paths)) != len(paths):
            raise ValueError('Duplicate paths in one chunk')
        return paths

    def work_entries(self, data, paths, modes, files=None):
        entries = []
        for path in paths:
            existing = self.catalog.get(data['work_root'], path)
            base = existing['base'] if existing else self.catalog.get(data['base_root'], path)
            entry = existing or {'path': path, 'size': 0, 'base': base, 'file': base, 'action': 'checkout'}
            entry = {**entry, 'mode': modes[path]}
            if files is not None:
                file=files[path]
                entry.update(file=file, size=file['size'], action='move/delete' if file.get('moved_to') else 'move/add' if file.get('moved_from') else 'delete' if file.get('deleted') else 'write')
            entries.append(entry)
        data['work_root'] = self.catalog.update(data['work_root'], entries)

    def checkout_release(self, data, paths, change):
        keys = [sha256((data['stream'] + '\0' + path).encode()).hexdigest() for path in paths]
        search = Search('file_project/checkout')
        search.add_filters('code', keys)
        rows = []
        for item in search.get_sobjects():
            opened = item.get_json_value('data')
            opened['holders'] = [h for h in opened['holders'] if h['change'] != change]
            item.set_json_value('data', opened)
            rows.append(item)
        commit_records(rows)

    def version_entry(self, path, file, base, change, stream, versions, *, rename=False, lineage_base=None):
        entry = {'path': path, 'blob': file.get('blob'), 'size': file['size'], 'sha256': file['sha256'],
                 'version': uuid.uuid4().hex, 'number': base['number'] + 1 if base else 1}
        if file.get('deleted'):
            entry['deleted'] = True
        if file.get('integrated_from'):
            entry['integrated_from'] = file['integrated_from']
        previous=identity(base)
        if rename:
            entry.update({key:file[key] for key in ('moved_from','moved_to') if file.get(key)})
            if file.get('moved_from'):
                previous=identity(lineage_base) or find('version',file['version']).get_json_value('data').get('previous')
        versions.append((entry['version'], {**entry, 'previous': previous, 'change': change, 'stream': stream}))
        return entry

    def inspect_change(self):
        from pyasm.common import Environment
        item = find('change', self.change_reference(self.kwargs.get('change') or self.kwargs.get('shelf')))
        data = item.get_json_value('data')
        _, stream = self.stream(data['stream'])
        if data['state'] == 'expired':
            raise ValueError('Changelist expired by retention')
        offered = data.get('handoff', {}).get('recipient') == self.owner
        if data['owner'] != self.owner and data['state'] not in ('submitted','shelved') and not offered and not Environment.get_security().is_admin():
            raise SecurityException('Private pending changelist')
        return {**self.result(item), 'editable':data['owner']==self.owner and data['state']=='pending',
                'depot_writable':self.has_permission(stream['depot'], 'write')}

    def offer_change(self):
        from pyasm.security import Login
        item, data = self.mutation()
        key, digest, retry = self.receipt(item.get_code(), 'offer_change')
        if retry is not None:
            return retry
        self.editable(data)
        self.revision(data)
        recipient = self.kwargs.get('recipient')
        if recipient is None:
            data.pop('handoff', None)
        else:
            if not isinstance(recipient,str) or recipient == self.owner:
                raise ValueError('Choose a different recipient login')
            login = Login.get_by_login(recipient)
            if not login or login.get_value('s_status',no_exception=True) == 'retired':
                raise ValueError('Recipient account is missing or retired')
            data['handoff'] = {'recipient':recipient,'code':uuid.uuid4().hex}
        data['edit_revision'] += 1
        self.save_change(item,data)
        return self.remember(key,digest,self.result(item))

    def accept_change(self):
        """Recipient acceptance moves ownership, workspace index and checkout holders atomically."""
        reference = self.change_reference(self.kwargs.get('change'))
        self.kwargs['change'] = reference
        probe = find('change',reference).get_json_value('data')
        self.stream(probe['stream'],'write',lock=True)
        item = self.lock('change',reference)
        data = item.get_json_value('data')
        key,digest,retry = self.receipt(reference,'accept_change')
        if retry is not None:
            return retry
        self.editable(data)
        self.revision(data)
        offer = data.get('handoff')
        if data['state'] != 'pending' or not offer or offer['recipient'] != self.owner or offer['code'] != self.kwargs.get('handoff'):
            raise SecurityException('This pending changelist was not offered to you')
        workspace, ws = self.workspace(lock=False)
        for code in sorted({workspace.get_code(),data['workspace']}):
            self.lock('workspace',code)
        ws = find('workspace',workspace.get_code()).get_json_value('data')
        if not any(rule['stream'] == data['stream'] and not rule['exclude'] and rule['writable'] for rule in self.view(ws).rules):
            raise SecurityException('Recipient workspace does not map this stream for writing')
        target = {**data,'workspace_view':ws.get('mappings'),'case_sensitive':ws.get('case_sensitive',True)}
        cursor = iter(self.catalog.entries(data['work_root']))
        while True:
            paths = [entry['path'] for entry in islice(cursor,1000)]
            if not paths:
                break
            self.check_workspace_paths(target,paths)
            search = Search('file_project/checkout')
            search.add_filters('code',[sha256((data['stream']+'\0'+path).encode()).hexdigest() for path in paths])
            records = search.get_sobjects()
            for record in records:
                opened = record.get_json_value('data')
                for holder in opened['holders']:
                    if holder['change'] == reference:
                        holder.update(owner=self.owner,workspace=workspace.get_code())
                record.set_json_value('data',opened)
            commit_records(records)
        self.close_workspace_change(item,data)
        if ws.get('pending_root'):
            ws['pending_root'] = self.catalog.update(ws['pending_root'],[{'path':reference,'size':0}])
            self.save_change(workspace,ws)
        history = data.get('handoff_history',[])
        if len(history) >= 128:
            raise ValueError('Too many ownership transfers for this changelist')
        data.update(owner=self.owner,workspace=workspace.get_code(),workspace_view=target['workspace_view'],
                    case_sensitive=target['case_sensitive'],edit_revision=data['edit_revision']+1,
                    handoff_history=history+[{'from':probe['owner'],'to':self.owner,'from_workspace':probe['workspace'],'workspace':workspace.get_code()}])
        data.pop('handoff')
        self.save_change(item,data)
        return self.remember(key,digest,self.result(item))

    def inspect_change_files(self):
        permitted = self.inspect_change()
        item = find('change', permitted['code'])
        return self.change_file_page(item, item.get_json_value('data'))

    def change_files(self):
        from .file_project_cmd import CHUNK_LIMIT, integer, logical_path
        if self.kwargs.get('shelf'):
            item, data = self.shelf()
        else:
            item, data = self.change(lock=False, pending=False)
        return self.change_file_page(item, data)

    def change_file_page(self, item, data):
        from .file_project_cmd import CHUNK_LIMIT, integer, logical_path
        baseline = data['state'] == 'submitted' and data.get('workspace') is None
        if 'work_root' not in data and not baseline:
            raise ValueError('Index this older pending changelist with index_change first')
        work_root = data['root'] if baseline else data['work_root']
        if 'edit_revision' in self.kwargs:
            self.revision(data)
        after = self.kwargs.get('after', '')
        if after:
            logical_path(after)
        prefix = logical_path(self.kwargs.get('prefix', ''), prefix=True)
        limit = integer(self.kwargs.get('limit', CHUNK_LIMIT), 1, CHUNK_LIMIT)
        entries = list(islice(self.catalog.entries(work_root, after, prefix), limit + 1))
        shown=entries[:limit]
        if baseline:
            shown = [{'path': row['path'], 'size': row['size'], 'file': row, 'base': row, 'action': 'baseline'} for row in shown]
        if data.get('active_transfer') and data['owner']==self.owner and shown:
            original=self.kwargs
            try:
                self.kwargs={'task':data['active_transfer'],'paths':[row['path'] for row in shown],'limit':1000}
                transfer={row['path']:row for row in self.transfer_items()['items']}
            finally:
                self.kwargs=original
            shown=[{**row,'transfer_state':transfer[row['path']]['state'],'received':transfer[row['path']]['received'],
                    'transfer_size':transfer[row['path']]['size']} if row['path'] in transfer else row for row in shown]
        stats=self.catalog.stats(work_root)
        info={**self.result(item),'opened_files':stats['files'],'opened_bytes':stats['bytes'],
              'depot_writable':self.has_permission(self.stream(data['stream'])[1]['depot'], 'write'),
              'file_actions':{'baseline': stats['files']} if baseline else self.catalog.action_stats(work_root),
              'waiting_uploads':0 if baseline else self.catalog.waiting_uploads(work_root),
              'editable':data['owner']==self.owner and data['state']=='pending'}
        return {'change': item.get_code(), 'info': info,
                'edit_revision': data['edit_revision'], 'items': shown,
                'after': entries[limit - 1]['path'] if len(entries) > limit else None,
                **stats}

    def index_change(self):
        from .file_project_cmd import CHUNK_LIMIT
        item, data = self.mutation()
        if 'work_root' in data:
            if self.catalog.waiting_uploads(data['work_root']) is not None:
                return {'change': item.get_code(), 'complete': True}
            if data.get('active_transfer') or data.get('integration'):
                raise ValueError('Finish or cancel active work before indexing')
            migration=data.get('indexing') or {'source_work_root':data['work_root'],'rebuilt_work_root':self.catalog.empty(),'after':''}
            entries=list(islice(self.catalog.entries(migration['source_work_root'],migration['after']),CHUNK_LIMIT+1))
            migration['rebuilt_work_root']=self.catalog.update(migration['rebuilt_work_root'],entries[:CHUNK_LIMIT])
            if entries:
                migration['after']=entries[min(len(entries),CHUNK_LIMIT)-1]['path']
            complete=len(entries)<=CHUNK_LIMIT
            if complete:
                data['work_root']=migration['rebuilt_work_root']
                data.pop('indexing',None)
            else:
                data['indexing']=migration
            self.save_change(item,data)
            return {'change':item.get_code(),'complete':complete,'after':migration['after']}
        migration = data.get('indexing') or {'root': self.catalog.empty(), 'after': '', 'phase': 'files'}
        if migration['phase'] == 'files':
            entries = list(islice(self.catalog.diff(data['base_root'], data['root'], migration['after']), CHUNK_LIMIT + 1))
            work = [{'path': path, 'size': new['size'] if new else 0, 'base': old,
                     'file': new or {'path': path, 'size': 0, 'sha256': None, 'blob': None, 'deleted': True},
                     'action': 'delete' if not new or new.get('deleted') else 'write', 'mode': 'ordinary'}
                    for path, old, new in entries[:CHUNK_LIMIT]]
            migration['root'] = self.catalog.update(migration['root'], work)
            if len(entries) <= CHUNK_LIMIT:
                migration.update(phase='checkouts', after='')
            else:
                migration['after'] = work[-1]['path']
        complete = False
        if migration['phase'] == 'checkouts':
            # One-time migration also recovers checkout-only files, including shared rows.
            search = Search('file_project/checkout')
            search.add_order_by('code')
            if migration['after']:
                search.add_filter('code', migration['after'], op='>')
            search.set_limit(CHUNK_LIMIT + 1)
            rows = search.get_sobjects()
            work = []
            for row in rows[:CHUNK_LIMIT]:
                opened = row.get_json_value('data')
                holder = next((h for h in opened['holders'] if h['change'] == item.get_code()), None)
                if not holder:
                    continue
                path = opened['path']
                entry = self.catalog.get(migration['root'], path)
                base = self.catalog.get(data['base_root'], path)
                work.append({**(entry or {'path': path, 'size': 0, 'base': base, 'file': base, 'action': 'checkout'}),
                             'mode': holder['mode']})
            migration['root'] = self.catalog.update(migration['root'], work)
            complete = len(rows) <= CHUNK_LIMIT
            if not complete:
                migration['after'] = rows[CHUNK_LIMIT - 1].get_code()
        if complete:
            data['work_root'] = migration['root']
            data.pop('indexing', None)
        else:
            data['indexing'] = migration
        self.save_change(item, data)
        return {'change': item.get_code(), 'complete': 'work_root' in data}

    def update_change(self):
        item, data = self.mutation()
        key, digest, retry = self.receipt(item.get_code(), 'update')
        if retry is not None:
            return retry
        self.editable(data)
        self.revision(data)
        data.update(self.submit_settings(data), edit_revision=data['edit_revision'] + 1)
        self.save_change(item, data)
        return self.remember(key, digest, self.result(item))

    def remove_files(self):
        item, data = self.mutation()
        key, digest, retry = self.receipt(item.get_code(), 'remove')
        if retry is not None:
            return retry
        self.editable(data)
        self.revision(data)
        paths = self.paths()
        self.complete_renames(data, paths)
        restore = []
        for path in paths:
            entry = self.catalog.get(data['work_root'], path)
            if not entry:
                raise ValueError('Path is not opened in this changelist: ' + path)
            restore.append(entry['base'] or {'path': path, 'delete': True})
        self.checkout_release(data, paths, item.get_code())
        data['root'] = self.catalog.update(data['root'], restore)
        data['work_root'] = self.catalog.update(data['work_root'], [{'path': p, 'delete': True} for p in paths])
        data['edit_revision'] += 1
        data.pop('merge_sources', None)
        self.save_change(item, data)
        return self.remember(key, digest, self.result(item))

    def complete_renames(self, data, paths):
        selected = set(paths)
        for path in paths:
            entry = self.catalog.get(data['work_root'], path)
            if entry and entry['action'] in ('move/add', 'move/delete'):
                file = entry.get('file') or {}
                partner = file.get('moved_from') or file.get('moved_to')
                if partner and partner not in selected:
                    raise ValueError('Select both sides of the rename operation')

    def delete_change(self):
        """Delete one change or an explicit batch in the enclosing native transaction."""
        if 'changes' not in self.kwargs:
            return self._delete_change()
        from .file_project_cmd import CHUNK_LIMIT, integer
        rows = self.kwargs['changes']
        if not isinstance(rows, list) or not 1 <= len(rows) <= CHUNK_LIMIT:
            raise ValueError('Select 1..1000 changelists to delete')
        selected = {}
        for row in rows:
            if not isinstance(row, dict) or set(row) != {'change', 'edit_revision'}:
                raise ValueError('Deletion requires changelist codes and edit revisions')
            code = self.change_reference(row['change'])
            if code in selected:
                raise ValueError('Select each changelist only once')
            selected[code] = integer(row['edit_revision'])
        original = self.kwargs
        results = []
        try:
            for code in sorted(selected):
                self.kwargs = {**original, 'change': code, 'edit_revision': selected[code]}
                del self.kwargs['changes']
                results.append(self._delete_change())
        finally:
            self.kwargs = original
        return {'items': results}

    def _delete_change(self):
        """Retire an owned shelf or empty pending change; physical GC stays separate."""
        from .file_storage import maintenance
        reference = self.change_reference(self.kwargs.get('change'))
        self.kwargs['change'] = reference
        probe = find('change', reference).get_json_value('data')
        if probe['owner'] != self.owner:
            raise SecurityException('Changelist belongs to another user')
        self.stream(probe['stream'], 'write', lock=True)
        item = self.lock('change', reference)
        data = item.get_json_value('data')
        if data['owner'] != self.owner:
            raise SecurityException('Changelist belongs to another user')
        key, digest, retry = self.receipt(item.get_code(), 'delete_change')
        if retry is not None:
            return retry
        self.revision(data)
        if data['state'] not in ('pending', 'shelved'):
            raise ValueError('Only an empty pending changelist or shelf can be deleted')
        if data['state'] == 'pending':
            self.editable(data)
            if self.catalog.stats(data['work_root'])['files']:
                raise ValueError('Move or revert the files before deleting this changelist')
            self.close_workspace_change(item, data)
        with maintenance(self.project):
            self.save_change(item, {**data, 'state': 'expired', 'root': self.catalog.empty(),
                'work_root': self.catalog.empty(), 'edit_revision': data['edit_revision'] + 1})
        return self.remember(key, digest, {'change': item.get_code(), 'state': 'expired'})

    def rename_files(self):
        """Stage linked move/delete + move/add revisions in one native transaction."""
        from .file_project_cmd import CHUNK_LIMIT, logical_path
        item, data = self.mutation()
        key, digest, retry = self.receipt(item.get_code(), 'rename')
        if retry is not None:
            return retry
        self.editable(data)
        self.revision(data)
        pairs = self.kwargs.get('renames')
        if not isinstance(pairs, list) or not 1 <= len(pairs) <= CHUNK_LIMIT // 2:
            raise ValueError('Select a bounded rename batch')
        if any(not isinstance(pair, dict) or set(pair) != {'source', 'target'} for pair in pairs):
            raise ValueError('Rename requires source and target paths')
        pairs = [(logical_path(pair['source']), logical_path(pair['target'])) for pair in pairs]
        paths = [path for pair in pairs for path in pair]
        if len(set(paths)) != len(paths):
            raise ValueError('Rename paths must be distinct')
        sources = {}
        for source, target in pairs:
            entry = self.catalog.get(data['root'], source)
            if not entry or entry.get('deleted') or self.catalog.get(data['root'], target):
                raise ValueError('Rename source is missing or destination already exists')
            sources[source] = entry
        modes = self.checkout_paths(item, paths, 'ordinary')
        versions, edits = [], []
        for source, target in pairs:
            base = self.catalog.get(data['base_root'], source)
            old = sources[source]
            moved = self.version_entry(target, old, None, item.get_code(), data['stream'], versions)
            moved['moved_from'] = source
            versions[-1][1].update(previous=old['version'], moved_from=source)
            removed = self.version_entry(source, {'deleted':True,'size':0,'sha256':None}, base,
                                         item.get_code(), data['stream'], versions)
            removed['moved_to'] = target
            versions[-1][1]['moved_to'] = target
            edits.extend((removed, moved))
        save_batch('version', versions)
        data['root'] = self.catalog.update(data['root'], edits)
        self.work_entries(data, paths, modes, {entry['path']: entry for entry in edits})
        work = []
        for source, target in pairs:
            for path, action in ((source, 'move/delete'), (target, 'move/add')):
                entry = self.catalog.get(data['work_root'], path)
                work.append({**entry, 'action': action})
        data['work_root'] = self.catalog.update(data['work_root'], work)
        data['edit_revision'] += 1
        data.pop('merge_sources', None)
        self.save_change(item, data)
        return self.remember(key, digest, self.result(item))

    def restore_file(self):
        """Stage an authorized published revision without copying immutable bytes."""
        from .file_project_cmd import logical_path
        item,data=self.mutation()
        key,digest,retry=self.receipt(item.get_code(),'restore_file')
        if retry is not None:return retry
        self.editable(data);self.revision(data)
        source=logical_path(self.kwargs.get('path'))
        target=logical_path(self.kwargs.get('target',source))
        if not self.kwargs.get('published_change'):raise ValueError('Choose a published revision to restore')
        if self.catalog.get(data['work_root'],target):raise ValueError('Target already has a pending edit; move or revert it first')
        original=self.kwargs
        try:
            self.kwargs={'stream':data['stream'],'path':source,'published_change':original['published_change']}
            restored=self.transfer()
        finally:self.kwargs=original
        modes=self.checkout_paths(item,[target],'ordinary')
        versions=[]
        base=self.catalog.get(data['base_root'],target)
        entry=self.version_entry(target,restored,base,item.get_code(),data['stream'],versions)
        versions[-1][1]['restored_from']=restored['version']
        save_batch('version',versions)
        data['root']=self.catalog.update(data['root'],[entry])
        self.work_entries(data,[target],modes,{target:entry})
        data['edit_revision']+=1;data.pop('merge_sources',None)
        self.save_change(item,data)
        return self.remember(key,digest,self.result(item))

    def move_files(self):
        from .file_project_cmd import identifier
        _, probe = self.change(lock=False)
        target = self.change_reference(self.kwargs.get('target_change'))
        if target == self.kwargs['change']:
            raise ValueError('Source and target changelists must differ')
        self.stream(probe['stream'], 'write', lock=True)
        locked = {code: self.lock('change', code) for code in sorted((self.kwargs['change'], target))}
        source, destination = locked[self.kwargs['change']], locked[target]
        data, dest = source.get_json_value('data'), destination.get_json_value('data')
        if dest['owner'] != self.owner or data['owner'] != self.owner:
            raise SecurityException('Both changelists must belong to the authenticated user')
        if data['state'] != 'pending' or dest['state'] != 'pending' or dest['stream'] != data['stream']:
            raise ValueError('Move requires pending changelists in the same stream')
        key, digest, retry = self.receipt(source.get_code(), 'move')
        if retry is not None:
            return retry
        for value in (data, dest):
            self.editable(value)
        self.revision(data)
        self.revision(dest, 'target_edit_revision')
        paths = self.paths()
        self.complete_renames(data, paths)
        versions, moved, restore, edits = [], [], [], []
        for path in paths:
            entry = self.catalog.get(data['work_root'], path)
            base = self.catalog.get(dest['base_root'], path)
            if not entry or self.catalog.get(dest['work_root'], path):
                raise ValueError('Move source missing or destination path already opened: ' + path)
            if identity(entry['base']) != identity(base):
                raise ValueError('Rebase both changelists before moving this path: ' + path)
            copy = {**entry, 'base': base}
            if entry['action'] != 'checkout':
                copy['file'] = self.version_entry(path, entry['file'], base, target, dest['stream'], versions,rename=entry['action'].startswith('move/'))
                edits.append(copy['file'])
            moved.append(copy)
            restore.append(entry['base'] or {'path': path, 'delete': True})
        self.checkout_release(data, paths, source.get_code())
        for mode in ('ordinary', 'exclusive'):
            subset = [e['path'] for e in moved if e['mode'] == mode]
            if subset:
                self.checkout_paths(destination, subset, mode)
        save_batch('version', versions)
        data['root'] = self.catalog.update(data['root'], restore)
        data['work_root'] = self.catalog.update(data['work_root'], [{'path': p, 'delete': True} for p in paths])
        dest['root'] = self.catalog.update(dest['root'], edits)
        dest['work_root'] = self.catalog.update(dest['work_root'], moved)
        for item, value in ((source, data), (destination, dest)):
            value['edit_revision'] += 1
            value.pop('merge_sources', None)
            self.save_change(item, value)
        return self.remember(key, digest, {'source': self.result(source), 'target': self.result(destination)})

    def shelve(self):
        probe, initial = self.change(lock=False,pending=False)
        self.stream(initial['stream'],'write',lock=True)
        key, digest, retry = self.receipt(probe.get_code(), 'shelve')
        if retry is not None:
            return retry
        item, data = self.mutation()
        self.editable(data)
        self.revision(data)
        if 'revert' in self.kwargs and not isinstance(self.kwargs['revert'], bool):
            raise ValueError('revert must be boolean')
        if 'paths' in self.kwargs:
            paths = self.paths()
            self.complete_renames(data, paths)
            entries = [self.catalog.get(data['work_root'], path) for path in paths]
            if any(entry is None for entry in entries):
                raise ValueError('Select opened files from this changelist')
            data = {**data, 'work_root': self.catalog.update(self.catalog.empty(), entries),
                    'root': self.catalog.update(data['base_root'], [entry['file'] for entry in entries if entry['file']])}
        self.pages.flush()
        shelf = create('change', {**data, 'state': 'shelved', 'source_change': item.get_code(),
                                  'source_edit_revision': data['edit_revision']})
        if self.kwargs.get('revert') is True:
            if 'paths' in self.kwargs:
                self.remove_files()
            else:
                self.revert()
        return self.remember(key, digest, self.result(shelf))

    def update_shelf(self):
        """Explicit replacement archives the previous immutable shelf before changing its number."""
        from .file_storage import maintenance
        from .file_project_cmd import integer
        deleting = self.kwargs.get('delete', False)
        if not isinstance(deleting, bool):
            raise ValueError('delete must be boolean')
        probe, initial = self.shelf()
        self.stream(initial['stream'],'write',lock=True)
        if deleting:
            data = initial
            receipt_owner = probe.get_code()
        else:
            source, data = self.change(lock=False,pending=False)
            receipt_owner = source.get_code()
        key, digest, retry = self.receipt(receipt_owner, 'update_shelf')
        if retry is not None:
            return retry
        if not deleting:
            source, data = self.mutation()
            self.editable(data)
            self.revision(data)
        item = self.lock('change', probe.get_code())
        old = item.get_json_value('data')
        if old['state'] != 'shelved' or old['owner'] != self.owner or old['stream'] != data['stream']:
            raise SecurityException('Replace only your shelf in the same stream')
        if integer(self.kwargs.get('shelf_revision')) != old['edit_revision']:
            raise ValueError('Shelf edit revision conflict')
        paths = self.paths()
        self.complete_renames(old, paths)
        if not deleting:
            self.complete_renames(data, paths)
        edits, work = [], []
        for path in paths:
            entry = self.catalog.get(old['work_root'], path) if deleting else self.catalog.get(data['work_root'], path)
            if not entry:
                raise ValueError('Selected file is not present: ' + path)
            work.append({'path': path, 'delete': True} if deleting else entry)
            edits.append((entry['base'] or {'path': path, 'delete': True}) if deleting else entry['file'])
        archived = create('change', {**old, 'archived_shelf': item.get_code()})
        updated = {**old, 'previous_shelf': archived.get_code(), 'edit_revision': old['edit_revision'] + 1,
                   'root': self.catalog.update(old['root'], [e for e in edits if e]),
                   'work_root': self.catalog.update(old['work_root'], work)}
        with maintenance(self.project):
            self.save_change(item, updated)
        return self.remember(key, digest, self.result(item))

    def compare_shelf(self):
        from .file_project_cmd import integer, logical_path
        pending = self.inspect_change()
        _, shelf = self.shelf()
        if shelf['stream'] != pending['stream']:
            raise ValueError('Compare shelves in the same stream')
        if 'shelf_revision' in self.kwargs and integer(self.kwargs['shelf_revision']) != shelf['edit_revision']:
            raise ValueError('Shelf changed; review the comparison again')
        if 'edit_revision' in self.kwargs:
            self.revision(pending)
        after = logical_path(self.kwargs.get('after',''),prefix=True)
        limit = integer(self.kwargs.get('limit',200),1,1000)
        rows = list(islice(self.catalog.diff(shelf['work_root'],pending['work_root'],after),limit+1))
        return {'items':[{'path':path,'shelf':old,'pending':new,
                         'action':'shelf_only' if new is None else 'pending_only' if old is None else
                                  'same' if content(old['file'])==content(new['file']) else 'different'} for path,old,new in rows[:limit]],
                'after':rows[limit-1][0] if len(rows)>limit else None,'number':pending['number'],
                'edit_revision':pending['edit_revision'],'shelf_revision':shelf['edit_revision'],
                'shelf':self.kwargs['shelf'],'editable':pending['editable'],'kind':'comparison'}

    def change_preview(self):
        """Bounded exact-file inspection, pinned to the edit revision shown for approval."""
        data = self.inspect_change()
        if 'edit_revision' in self.kwargs:
            self.revision(data)
        item = find('change', data['code'])
        page = self.change_file_page(item, data)
        if 'paths' in self.kwargs:
            paths = self.paths()
            entries = [self.catalog.get(data['work_root'], path) for path in paths]
            if any(entry is None for entry in entries):
                raise ValueError('Select opened files from this changelist')
            page.update(items=entries, after=None, files=len(entries), bytes=sum(row['size'] for row in entries))
        _, head = self.stream(data['stream'])
        shelf = self.shelf()[1] if self.kwargs.get('shelf') else None
        if shelf and shelf['stream'] != data['stream']:
            raise ValueError('Compare shelves in the same stream')
        entries = []
        for entry in page['items']:
            row = {**entry, 'uploaded': entry['action'] != 'checkout'}
            if shelf:
                other = self.catalog.get(shelf['work_root'], entry['path'])
                row['shelf'] = other
                row['shelf_status'] = 'absent' if other is None else 'same' if content(entry['file']) == content(other['file']) else 'different'
            entries.append(row)
        return {**page, 'items': entries, 'description': data.get('description', ''), 'number': data['number'],
                'state': data['state'], 'active_transfer': data.get('active_transfer'),
                'integration': data.get('integration'), 'rebase_required': head['revision'] != data['base_revision'],
                'actions': self.catalog.action_stats(data['work_root']), 'waiting_uploads':self.catalog.waiting_uploads(data['work_root']),
                'indexing':data.get('indexing'), 'editable': data['editable']}

    def shelf(self):
        from .file_project_cmd import identifier
        item = find('change', self.change_reference(self.kwargs.get('shelf')))
        data = item.get_json_value('data')
        from .file_submit import can_read_change
        if not can_read_change(data):
            raise SecurityException('Restricted changelist')
        if data['state'] != 'shelved':
            raise ValueError('A shelved changelist is required')
        self.stream(data['stream'])
        return item, data

    def integration_begin(self, kind):
        item, data = self.mutation()
        key, digest, retry = self.receipt(item.get_code(), kind + '_begin')
        if retry is not None:
            return retry
        self.editable(data)
        self.revision(data)
        _, head = self.stream(data['stream'], 'write')
        from .file_project_cmd import integer
        if 'preview_head_revision' in self.kwargs and integer(self.kwargs['preview_head_revision']) != head['revision']:
            raise ValueError('Stream head changed; review integration again')
        if kind == 'unshelve':
            shelf, source = self.shelf()
            if source['stream'] != data['stream']:
                raise ValueError('Unshelve requires the same stream; stream merge is a separate operation')
            if self.kwargs.get('preview_source_root') and self.kwargs['preview_source_root'] != source['work_root']:
                raise ValueError('Shelf changed; review integration again')
            if data['base_root'] != head['root'] or data['base_revision'] != head['revision']:
                raise ValueError('Rebase the destination before unshelving')
            root, work = data['root'], data['work_root']
            if 'paths' in self.kwargs:
                paths = self.paths()
                self.complete_renames(source, paths)
                entries = [self.catalog.get(source['work_root'], path) for path in paths]
                if any(entry is None for entry in entries):
                    raise ValueError('Selected shelf file is not present')
                source = {**source, 'work_root': self.catalog.update(self.catalog.empty(), entries)}
        else:
            source = data
            root, work = head['root'], self.catalog.empty()
        data['integration'] = {'code': uuid.uuid4().hex, 'kind': kind, 'source_root': source['work_root'],
            'shelf': shelf.get_code() if kind == 'unshelve' else None, 'head_root': head['root'],
            'head_revision': head['revision'], 'root': root, 'work_root': work, 'after': '',
            'conflicts_root': self.catalog.empty(), 'acquired_root': self.catalog.empty(), 'complete': False}
        self.save_change(item, data)
        return self.remember(key, digest, self.integration_result(item, data))

    def rebase_begin(self):
        return self.integration_begin('rebase')

    def integration_preview(self):
        from .file_project_cmd import integer, logical_path, identifier
        _, data = self.change(lock=False)
        self.editable(data)
        self.revision(data)
        _, head = self.stream(data['stream'], 'write')
        if 'preview_head_revision' in self.kwargs and integer(self.kwargs['preview_head_revision']) != head['revision']:
            raise ValueError('Stream head changed; review integration again')
        kind = self.kwargs.get('kind')
        after = logical_path(self.kwargs.get('after',''), prefix=True)
        limit = integer(self.kwargs.get('limit',200),1,1000)
        if kind == 'unshelve':
            shelf, source = self.shelf()
            if source['stream'] != data['stream']:
                raise ValueError('Unshelve requires the same stream')
            source_root = source['work_root']
            entries = self.catalog.entries(source_root,after)
            target = data['root']
            source_name = '#' + str(shelf.get_id())
        elif kind == 'rebase':
            source_root = data['work_root']
            entries = self.catalog.entries(source_root,after)
            target = head['root']
            source_name = data['stream']
        elif kind == 'merge':
            code = identifier(self.kwargs.get('source_stream'))
            _, source = self.stream(code)
            if code == data['stream'] or source['depot'] != head['depot']:
                raise ValueError('Choose a different source stream in the same depot')
            published = identifier(self.kwargs.get('source_change',source['head_change']))
            snapshot = find('change',published).get_json_value('data')
            if snapshot['stream'] != code or snapshot['state'] != 'submitted':
                raise SecurityException('Merge requires a published source snapshot')
            merged = self.catalog.get(head['merge_bases_root'],code) if head.get('merge_bases_root') else None
            base = merged['root'] if merged else self.common_base(data['stream'],code)
            source_root = snapshot['root']
            entries = self.merge_entries({'source_stream':code,'source_change':published,'source_root':source_root,'merge_base_root':base,'after':after})
            target = data['root']
            source_name = code
        else:
            raise ValueError('Preview unshelve, rebase or merge')
        if self.kwargs.get('preview_source_root') and self.kwargs['preview_source_root'] != source_root:
            raise ValueError('Source changed; review integration again')
        if 'paths' in self.kwargs:
            if kind != 'unshelve':
                raise ValueError('Explicit integration paths apply to unshelve')
            paths = self.paths()
            self.complete_renames(source, paths)
            selected = [self.catalog.get(source_root,path) for path in sorted(paths)]
            if any(row is None for row in selected):
                raise ValueError('Selected shelf file is not present')
            entries = (row for row in selected if row['path'] > after)
        page = list(islice(entries,limit+1))
        view = self.view({'mappings':data['workspace_view'],'case_sensitive':data.get('case_sensitive',True)}) if data.get('workspace_view') else None
        rows = []
        for entry in page[:limit]:
            mapped = view.forward(data['stream'],entry['path']) if view else {'writable':True}
            ours = self.catalog.get(target,entry['path'])
            rows.append({**entry,'target_file':ours,'excluded':not mapped or not mapped['writable'],
                         'conflict':content(entry['base'])!=content(ours) and content(entry['file'])!=content(ours) and content(entry['base'])!=content(entry['file'])})
        return {'items':rows,'after':page[limit-1]['path'] if len(page)>limit else None,
                'kind':kind,'source':source_name,'target':data['stream'],'edit_revision':data['edit_revision'],
                'preview_head_revision':head['revision'],'preview_source_root':source_root,
                'rebase_required':kind!='rebase' and data['base_revision']!=head['revision']}

    def unshelve_begin(self):
        return self.integration_begin('unshelve')

    def integration_result(self, item, data):
        job = data.get('integration')
        if not job:
            return {'change': item.get_code(), 'edit_revision': data['edit_revision'], 'complete': True}
        return {'change': item.get_code(), 'edit_revision': data['edit_revision'], 'integration': job['code'],
                'kind': job['kind'], 'after': job['after'], 'complete': job['complete'],
                'conflicts': self.catalog.stats(job['conflicts_root'])['files'], 'excluded_files':job.get('excluded_files',0), 'cancelling': job.get('cancelling', False)}

    def integration_job(self, data):
        from .file_project_cmd import identifier
        job = data.get('integration')
        if not job or identifier(self.kwargs.get('integration')) != job['code']:
            raise ValueError('Integration identifier conflict')
        self.revision(data)
        if job.get('source_stream'):
            self.stream(job['source_stream'])
        return job

    def integration_next(self):
        from .file_project_cmd import CHUNK_LIMIT
        item, data = self.mutation()
        key, digest, retry = self.receipt(item.get_code(), 'integration_next')
        if retry is not None:
            return retry
        job = self.integration_job(data)
        if job.get('cancelling'):
            raise ValueError('Integration is being cancelled')
        if self.kwargs.get('after', '') != job['after']:
            raise ValueError('Integration cursor conflict')
        if job['complete']:
            return self.remember(key, digest, self.integration_result(item, data))
        source = self.merge_entries(job) if job['kind'] == 'merge' else self.catalog.entries(job['source_root'], job['after'])
        entries = list(islice(source, CHUNK_LIMIT + 1))
        versions, edits, work, conflicts, acquired, integrated = [], [], [], [], [], []
        conflict_paths=set()
        view = self.view({'mappings':data['workspace_view'],'case_sensitive':data.get('case_sensitive',True)}) if data.get('workspace_view') else None
        for original in entries[:CHUNK_LIMIT]:
            path = original['path']
            partner=(original.get('file') or {}).get('moved_from') or (original.get('file') or {}).get('moved_to')
            mapped = view.forward(data['stream'],path) if view else {'writable':True}
            partner_mapping = view.forward(data['stream'],partner) if view and partner else {'writable':True}
            if not mapped or not mapped['writable'] or not partner_mapping or not partner_mapping['writable']:
                job['excluded_files'] = job.get('excluded_files',0) + 1
                continue
            if job['kind'] == 'merge':
                integrated.append(self.catalog.get(job['source_root'],path) or {'path':path,'delete':True})
            theirs = self.catalog.get(job['root'], path)
            base = self.catalog.get(job['head_root'], path)
            mode = original['mode']
            if job['kind'] in ('unshelve', 'merge'):
                opened = self.catalog.get(data['work_root'], path)
                mode = opened['mode'] if opened else 'ordinary'
                if not opened:
                    acquired.append({'path': path, 'size': 0})
            entry = {**original, 'base': base, 'mode': mode}
            if partner and (path in conflict_paths or self.catalog.get(job['conflicts_root'],path)):
                continue
            if original['action'] == 'checkout' or content(original['file']) == content(original['base']):
                if job['kind'] in ('unshelve', 'merge') and self.catalog.get(data['work_root'], path):
                    continue
                entry.update(file=theirs, size=0, action='checkout')
            elif content(original['base']) != content(theirs) and content(original['file']) != content(theirs):
                conflicts.append({'path': path, 'size': 0, 'base': original['base'], 'ours': original['file'],
                                  'theirs': theirs, 'mode': mode, **({'rename_partner':partner} if partner else {})})
                if partner:
                    conflict_paths.update((path,partner))
                    initial_root=data['root'] if job['kind'] in ('unshelve','merge') else job['head_root']
                    partner_file=self.catalog.get(initial_root,partner)
                    if job['kind']=='merge':
                        partner_ours=self.catalog.get(job['source_root'],partner)
                        partner_base=self.catalog.get(job['merge_base_root'],partner)
                        partner_mode='ordinary'
                    else:
                        partner_entry=self.catalog.get(job['source_root'],partner)
                        partner_ours=partner_entry['file'];partner_base=partner_entry['base'];partner_mode=partner_entry['mode']
                    conflicts.append({'path':partner,'size':0,'base':partner_base,'ours':partner_ours,
                                      'theirs':partner_file,'mode':partner_mode,'rename_partner':path})
                    edits.append(partner_file or {'path':partner,'delete':True})
                    work.append(self.catalog.get(data['work_root'],partner) if job['kind'] in ('unshelve','merge') and self.catalog.get(data['work_root'],partner) else {'path':partner,'delete':True})
                    if job['kind'] in ('unshelve','merge'):
                        acquired.append({'path':partner,'size':0})
                continue
            elif content(original['file']) == content(theirs):
                entry.update(file=theirs, size=0, action='checkout')
                # Unshelve matching an existing local edit must retain that edit's manifest.
                if job['kind'] in ('unshelve', 'merge') and self.catalog.get(data['work_root'], path):
                    continue
            else:
                lineage=self.catalog.get(job['head_root'],original['file']['moved_from']) if original['file'].get('moved_from') else None
                entry['file'] = self.version_entry(path, original['file'], base, item.get_code(), data['stream'], versions,
                                                 rename=bool(partner),lineage_base=lineage)
                edits.append(entry['file'])
            work.append(entry)
        if acquired:
            self.checkout_paths(item, list(dict.fromkeys(e['path'] for e in acquired)), 'ordinary')
        save_batch('version', versions)
        job['root'] = self.catalog.update(job['root'], edits)
        job['work_root'] = self.catalog.update(job['work_root'], work)
        job['conflicts_root'] = self.catalog.update(job['conflicts_root'], conflicts)
        job['acquired_root'] = self.catalog.update(job['acquired_root'], acquired)
        if job['kind'] == 'merge':
            job['integrated_source_root'] = self.catalog.update(job.get('integrated_source_root') or job['merge_base_root'], integrated)
        if entries:
            job['after'] = entries[min(CHUNK_LIMIT, len(entries)) - 1]['path']
        job['complete'] = len(entries) <= CHUNK_LIMIT
        self.save_change(item, data)
        return self.remember(key, digest, self.integration_result(item, data))

    def conflicts(self):
        from .file_project_cmd import CHUNK_LIMIT, integer, logical_path
        item, data = self.change(lock=False)
        job = self.integration_job(data)
        after = self.kwargs.get('after', '')
        if after:
            logical_path(after)
        limit = integer(self.kwargs.get('limit', CHUNK_LIMIT), 1, CHUNK_LIMIT)
        entries = list(islice(self.catalog.entries(job['conflicts_root'], after), limit + 1))
        return {**self.integration_result(item, data), 'items': entries[:limit],
                'after': entries[limit - 1]['path'] if len(entries) > limit else None}

    def resolve(self):
        from .file_project_cmd import CHUNK_LIMIT, logical_path, identifier
        item, data = self.mutation()
        key, digest, retry = self.receipt(item.get_code(), 'resolve')
        if retry is not None:
            return retry
        job = self.integration_job(data)
        if job.get('cancelling'):
            raise ValueError('Integration is being cancelled')
        resolutions = self.kwargs.get('resolutions')
        if (not isinstance(resolutions, list) or not 1 <= len(resolutions) <= CHUNK_LIMIT or
                len(encode(resolutions).encode('utf-8')) > 2 * 1024 * 1024):
            raise ValueError('Resolution requires a bounded chunk')
        paths, edits, work, versions, resolved = [], [], [], [], []
        selected={resolution.get('path'):resolution for resolution in resolutions if isinstance(resolution,dict)}
        for resolution in resolutions:
            if not isinstance(resolution, dict) or set(resolution) - {'path', 'choice', 'blob'}:
                raise ValueError('Invalid resolution')
            path = logical_path(resolution.get('path'))
            conflict = self.catalog.get(job['conflicts_root'], path)
            if not conflict or path in paths:
                raise ValueError('Missing or duplicate conflict: ' + path)
            paths.append(path)
            resolved.append({**conflict, 'previous_file': self.catalog.get(job['root'], path),
                             'previous_work': self.catalog.get(job['work_root'], path), 'choice': resolution.get('choice')})
            choice = resolution.get('choice')
            if choice not in ('ours', 'theirs', 'blob') or ('blob' in resolution and choice != 'blob'):
                raise ValueError('Resolve with ours, theirs or an uploaded merged blob')
            partner=conflict.get('rename_partner')
            if partner:
                other=selected.get(partner)
                if not other or not ((choice==other.get('choice') and choice in ('ours','theirs')) or
                        choice=='blob' and other.get('choice')=='ours' and not (conflict.get('ours') or {}).get('deleted') or
                        choice=='ours' and other.get('choice')=='blob' and (conflict.get('ours') or {}).get('deleted')):
                    raise ValueError('Resolve both sides of a rename together with a compatible choice')
            base = self.catalog.get(job['head_root'], path)
            file = conflict['ours'] if choice == 'ours' else conflict['theirs']
            if choice == 'blob':
                code = identifier(resolution.get('blob'))
                blob = find('blob', code).get_json_value('data')
                if blob['owner'] != self.owner or blob['change'] != item.get_code() or blob['state'] != 'ready':
                    raise SecurityException('Merged blob must be a ready upload of this changelist')
                file = {'blob': code, 'size': blob['size'], 'sha256': blob['sha256']}
                if conflict['ours'] and conflict['ours'].get('integrated_from'):
                    file['integrated_from'] = conflict['ours']['integrated_from']
                if partner:
                    file.update({key:conflict['ours'][key] for key in ('version','moved_from','moved_to') if conflict['ours'].get(key)})
            entry = {'path': path, 'size': 0, 'base': base, 'file': file, 'mode': conflict['mode'], 'action': 'checkout'}
            if content(file) != content(base):
                lineage=self.catalog.get(job['head_root'],file['moved_from']) if file.get('moved_from') else None
                entry['file'] = self.version_entry(path, file, base, item.get_code(), data['stream'], versions,rename=bool(partner),lineage_base=lineage)
                entry.update(size=file['size'], action='move/delete' if file.get('moved_to') else 'move/add' if file.get('moved_from') else 'delete' if file.get('deleted') else 'write')
                edits.append(entry['file'])
            elif file != self.catalog.get(job['root'], path):
                edits.append(file or {'path': path, 'delete': True})
            previous_work=self.catalog.get(data['work_root'],path) if job['kind'] in ('unshelve','merge') else None
            entry['resolved_sha256'] = (entry.get('file') or {}).get('sha256')
            work.append(entry if file or base else previous_work or {'path':path,'delete':True})
        save_batch('version', versions)
        job['root'] = self.catalog.update(job['root'], edits)
        job['work_root'] = self.catalog.update(job['work_root'], work)
        job['conflicts_root'] = self.catalog.update(job['conflicts_root'], [{'path': p, 'delete': True} for p in paths])
        job['resolved_root'] = self.catalog.update(job.get('resolved_root') or self.catalog.empty(), resolved)
        self.save_change(item, data)
        return self.remember(key, digest, self.integration_result(item, data))

    def resolved_files(self):
        from .file_project_cmd import CHUNK_LIMIT, integer, logical_path
        _, data = self.change(lock=False)
        job = self.integration_job(data)
        after = logical_path(self.kwargs.get('after', ''), prefix=True)
        limit = integer(self.kwargs.get('limit', 200), 1, CHUNK_LIMIT)
        rows = list(islice(self.catalog.entries(job.get('resolved_root') or self.catalog.empty(), after), limit + 1))
        return {'items': rows[:limit], 'after': rows[limit-1]['path'] if len(rows)>limit else None}

    def undo_resolve(self):
        item, data = self.mutation()
        key, digest, retry = self.receipt(item.get_code(), 'undo_resolve')
        if retry is not None:
            return retry
        job = self.integration_job(data)
        if job.get('cancelling'):
            raise ValueError('Integration is being cancelled')
        paths = self.paths()
        resolved_root = job.get('resolved_root') or self.catalog.empty()
        rows = [self.catalog.get(resolved_root, path) for path in paths]
        if any(row is None for row in rows):
            raise ValueError('Select resolved conflicts from this integration')
        if any(row.get('rename_partner') and row['rename_partner'] not in paths for row in rows):
            raise ValueError('Undo both sides of a rename resolution together')
        job['root'] = self.catalog.update(job['root'], [row['previous_file'] or {'path':row['path'],'delete':True} for row in rows])
        job['work_root'] = self.catalog.update(job['work_root'], [row['previous_work'] or {'path':row['path'],'delete':True} for row in rows])
        job['conflicts_root'] = self.catalog.update(job['conflicts_root'], [{k:v for k,v in row.items() if k not in ('previous_file','previous_work','choice')} for row in rows])
        job['resolved_root'] = self.catalog.update(resolved_root, [{'path':path,'delete':True} for path in paths])
        self.save_change(item, data)
        return self.remember(key, digest, self.integration_result(item, data))

    def integration_finish(self):
        item, data = self.mutation()
        key, digest, retry = self.receipt(item.get_code(), 'integration_finish')
        if retry is not None:
            return retry
        job = self.integration_job(data)
        _, head = self.stream(data['stream'], 'write')
        if job.get('cancelling') or not job['complete'] or self.catalog.stats(job['conflicts_root'])['files']:
            raise ValueError('Process all chunks and resolve all conflicts before finishing')
        if head['root'] != job['head_root'] or head['revision'] != job['head_revision']:
            raise ValueError('Stream head changed again; cancel and restart integration')
        data.update(root=job['root'], work_root=job['work_root'], base_root=job['head_root'],
                    base_revision=job['head_revision'], edit_revision=data['edit_revision'] + 1)
        if job['kind'] == 'merge':
            sources = {entry['stream']: entry for entry in data.get('merge_sources', [])}
            if len(sources) >= 128 and job['source_stream'] not in sources:
                raise ValueError('Too many source streams in one changelist')
            sources[job['source_stream']] = {'stream': job['source_stream'], 'root': job.get('integrated_source_root') or job['source_root'],
                'change': job['source_change'], 'revision': job['source_revision']}
            data['merge_sources'] = list(sources.values())
        data.pop('integration')
        self.save_change(item, data)
        return self.remember(key, digest, self.result(item))

    def integration_cancel(self):
        from .file_project_cmd import CHUNK_LIMIT
        item, data = self.mutation()
        key, digest, retry = self.receipt(item.get_code(), 'integration_cancel')
        if retry is not None:
            return retry
        job = self.integration_job(data)
        job['cancelling'] = True
        paths = [entry['path'] for entry in islice(self.catalog.entries(job['acquired_root']), CHUNK_LIMIT)]
        if paths:
            self.checkout_release(data, paths, item.get_code())
            job['acquired_root'] = self.catalog.update(job['acquired_root'], [{'path': p, 'delete': True} for p in paths])
        if self.catalog.stats(job['acquired_root'])['files'] == 0:
            data.pop('integration')
            data['edit_revision'] += 1
        self.save_change(item, data)
        return self.remember(key, digest, self.integration_result(item, data))
