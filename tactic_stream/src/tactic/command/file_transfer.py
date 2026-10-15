"""Durable bounded manifests, byte leases and owner-executed transfer tasks."""
from hashlib import sha256
from itertools import islice
from pathlib import Path
from time import time
import re
import tarfile
import uuid

from pyasm.biz.file_project import create, find, save, save_batch, commit_records, encode, blob_file_path
from pyasm.common import Container
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.transaction import Transaction

BLOCK_BYTES = 64 * 1024 * 1024
TRANSFER_ACTIONS = {'transfer_begin', 'transfer_manifest', 'transfer_seal', 'transfer_next', 'transfer_status',
    'transfer_tasks', 'transfer_items', 'transfer_cancel', 'transfer_write_begin', 'transfer_write_touch', 'transfer_write_commit',
    'transfer_write_abort', 'transfer_batch_commit', 'transfer_file_digest', 'transfer_claim',
    'transfer_verify_progress', 'transfer_verify_finish', 'transfer_verify_next', 'transfer_step', 'transfer_fail',
    'transfer_ack', 'transfer_received', 'transfer_block', 'transfer_digests', 'transfer_pause'}


def checksum(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Lowercase SHA-256 required')
    return value


def service_only():
    if not Container.get('FileTransfer:service'):
        raise SecurityException('Local file-transfer worker required')


class FileTransferMixin:
    def transfer_staging(self, code, token):
        from pyasm.search.search import _context
        root = blob_file_path(self.project, '0' * 32, _context.get().store.data_dir).parents[2]
        return root / 'transfers' / code / (token + '.tar')

    def transfer_job(self, lock=True, operation=None):
        from .file_project_cmd import identifier
        code = identifier(self.kwargs.get('task'))
        item = self.lock('sync', code) if lock else find('sync', code)
        data = item.get_json_value('data')
        if data.get('state') == 'expired':
            raise ValueError('Transfer expired by retention')
        if data.get('kind') not in ('upload', 'download') or data.get('owner') != self.owner:
            raise SecurityException('Transfer task belongs to another user or has the wrong kind')
        self.stream(data['stream'], operation or ('write' if data['kind'] == 'upload' else 'read'))
        return item, data

    def transfer_public(self, item, data=None):
        data = data or item.get_json_value('data')
        if data.get('kind') == 'mutation':
            return self.bulk_public(item,data)
        policy = self.storage_data if self.storage_data is not None else self.storage_record.get_json_value('data') if self.storage_record else {}
        return {'task': item.get_code(), 'max_parallel': policy.get('max_parallel', 4), **{key: value for key, value in data.items()
                if key not in ('leases', 'worker_token', 'manifest_root', 'worker', 'lease_until', 'original_change')}}

    def transfer_begin(self):
        if not self.storage_record or not self.storage_data['indexed']:
            raise ValueError('Run storage_upgrade/storage_index first')
        kind = self.kwargs.get('kind', 'upload')
        if kind == 'download':
            workspace, ws = self.workspace()
            from .file_revision import revision_spec
            scope={**revision_spec(self.kwargs),**{key:self.kwargs[key] for key in ('source_stream','source_depot','path') if self.kwargs.get(key) is not None}}
            force=self.kwargs.get('force',False)
            if not isinstance(force,bool):raise ValueError('force must be boolean')
            selected=self.sync_paths()
            client_root = self.kwargs.get('client_root')
            if client_root is not None and (not isinstance(client_root, str) or not client_root or len(client_root) > 2048 or '\x00' in client_root):
                raise ValueError('Invalid download client root')
            if ws.get('active_transfer'):
                pending = find('sync', ws['active_transfer']).get_json_value('data')
                underlying = find('sync', pending['sync']).get_json_value('data') if pending['state'] not in ('complete', 'cancelled', 'expired') else None
                if underlying and underlying['state'] == 'running' and ws['active_sync'] == pending['sync']:
                    if pending.get('client_root') != client_root:
                        raise ValueError('Workspace has a download for another local root')
                    pending_paths=sorted(set(pending['paths'])) if pending.get('paths') is not None else None
                    same_selection=pending.get('prefix','')==self.kwargs.get('prefix','') and pending_paths==selected
                    same_revision=pending.get('revision_spec',{})==scope
                    if pending['state']!='blocked':
                        if not same_selection:
                            raise ValueError('Workspace has a download for another selection; finish or cancel it first')
                        if not same_revision:
                            raise ValueError('Workspace has a download for another revision; finish or cancel it first')
                    if not same_selection or not same_revision or force and not pending.get('force'):
                        old=self.kwargs
                        try:
                            self.kwargs={**old,'task':ws['active_transfer']}
                            self.transfer_cancel()
                        finally:self.kwargs=old
                    else:
                        if pending['state']=='blocked':
                            pending['state']='streaming'
                            for key in ('reason','path','paused_ack_revision','required_bytes','available_bytes'):pending.pop(key,None)
                            save(find('sync',ws['active_transfer']),pending)
                        return self.transfer_public(find('sync', ws['active_transfer']))
            old = self.kwargs
            try:
                self.kwargs = {**old, 'workspace': workspace.get_code()}
                sync = self.sync_begin()
            finally:
                self.kwargs = old
            item = create('sync', {'kind': kind, 'owner': self.owner, 'stream': ws['stream'],
                'sync': sync['code'], 'workspace': workspace.get_code(), 'state': 'streaming',
                'files_done': 0, 'bytes_done': 0, 'total_known': False, 'client_root': client_root,
                'prefix':self.kwargs.get('prefix',''), 'paths':selected,'revision_spec':scope,'force':force})
            workspace = find('workspace', workspace.get_code())
            ws = workspace.get_json_value('data')
            ws['active_transfer'] = item.get_code()
            save(workspace, ws)
            return self.transfer_public(item)
        if kind != 'upload':
            raise ValueError('Unknown transfer kind')
        change, data = self.change()
        key, digest, retry = self.receipt(change.get_code(), 'transfer_begin')
        if retry is not None:
            return retry
        self.editable(data)
        if 'edit_revision' in self.kwargs:
            self.revision(data)
        submit = self.kwargs.get('submit', False)
        if not isinstance(submit, bool):
            raise ValueError('submit must be boolean')
        from .file_project_cmd import integer
        expected = {}
        if 'expected_files' in self.kwargs or 'expected_bytes' in self.kwargs:
            expected = {name: integer(self.kwargs.get(name), high=2**63 - 1) for name in ('expected_files', 'expected_bytes')}
        item = create('sync', {'kind': kind, 'owner': self.owner, 'stream': data['stream'], 'change': change.get_code(),
            'state': 'collecting', 'manifest_root': self.catalog.empty(), 'sealed': False, 'submit': submit,
            'expected_edit_revision': data['edit_revision'], 'files_total': expected.get('expected_files', 0),
            'bytes_total': expected.get('expected_bytes', 0), 'files_manifested': 0, 'bytes_manifested': 0,
            'files_done': 0, 'bytes_done': 0, 'verified_files': 0, 'verified_bytes': 0,
            'staged_files': 0, 'verify_after': '', 'stage_after': '', 'leases': {}, 'total_known': bool(expected),
            'original_change': data.copy(), **expected})
        data['active_transfer'] = item.get_code()
        save(change, data)
        self.pages.flush()
        return self.remember(key, digest, self.transfer_public(item))

    def transfer_manifest(self):
        from .file_project_cmd import logical_path, integer, CHUNK_LIMIT
        item, data = self.transfer_job()
        key, digest, retry = self.receipt(item.get_code(), 'manifest')
        if retry is not None:
            return retry
        if data['kind'] != 'upload' or data['sealed'] or data['state'] != 'collecting':
            raise ValueError('Transfer manifest is closed')
        files = self.kwargs.get('files')
        if not isinstance(files, list) or not 1 <= len(files) <= CHUNK_LIMIT or len(encode(files).encode()) > 2 * 1024 * 1024:
            raise ValueError('Manifest requires 1..1000 descriptors within 2 MiB')
        rows, entries, seen = [], [], set()
        _, stream = self.stream(data['stream'], 'write')
        depot = find('depot', stream['depot']).get_json_value('data').get('storage')
        location = {'storage_root': depot['root']} if depot else {}
        for descriptor in files:
            if not isinstance(descriptor, dict) or set(descriptor) - {'path', 'size', 'sha256'}:
                raise ValueError('Invalid manifest descriptor')
            path = logical_path(descriptor.get('path'))
            size = integer(descriptor.get('size'), high=2**63 - 1)
            if path in seen or self.catalog.get(data['manifest_root'], path):
                raise ValueError('Duplicate manifest path')
            seen.add(path)
            expected = checksum(descriptor['sha256']) if 'sha256' in descriptor else None
            code = uuid.uuid4().hex
            rows.append((code, {'owner': self.owner, 'change': data['change'], 'transfer': item.get_code(),
                'path': path, 'size': size, 'received': 0, 'state': 'uploading', 'sha256': None,
                'expected_sha256': expected, **location}))
            entries.append({'path': path, 'size': size, 'blob': code})
        change_item=self.lock('change',data['change'])
        change = change_item.get_json_value('data')
        if change['state'] != 'pending':
            raise ValueError('Transfer changelist is no longer pending')
        self.check_workspace_paths(change, list(seen))
        modes=self.checkout_paths(change_item,sorted(seen),'ordinary')
        self.work_entries(change,sorted(seen),modes)
        change['edit_revision']+=1
        data['expected_edit_revision']=change['edit_revision']
        self.save_change(change_item,change)
        self.reserve_storage([entry['size'] for entry in entries])
        save_batch('blob', rows)
        data['manifest_root'] = self.catalog.update(data['manifest_root'], entries)
        totals = self.catalog.stats(data['manifest_root'])
        if 'expected_files' in data and (totals['files'] > data['expected_files'] or totals['bytes'] > data['expected_bytes']):
            raise ValueError('Manifest exceeds declared transfer totals')
        data.update(files_manifested=totals['files'], bytes_manifested=totals['bytes'],
                    files_total=data.get('expected_files', totals['files']), bytes_total=data.get('expected_bytes', totals['bytes']))
        self.save_change(item, data)
        return self.remember(key, digest, {'task': item.get_code(), 'items': entries,
                              'files_total': data['files_total'], 'bytes_total': data['bytes_total']})

    def transfer_next(self):
        item, data = self.transfer_job(lock=False)
        if data['kind'] == 'download':
            old = self.kwargs
            try:
                self.kwargs = {**old, 'sync': data['sync']}
                return self.sync_next()
            finally:
                self.kwargs = old
        from .file_project_cmd import logical_path
        after = self.kwargs.get('after', '')
        if after:
            logical_path(after)
        entries = list(islice(self.catalog.entries(data['manifest_root'], after), 1001))
        search = Search('file_project/blob')
        search.add_filters('code', [entry['blob'] for entry in entries[:1000]])
        blobs = {blob.get_code(): blob.get_json_value('data') for blob in search.get_sobjects()}
        return {'task': item.get_code(), 'items': [{**entry, **{key: blobs[entry['blob']].get(key) for key in
                ('received', 'state', 'sha256', 'expected_sha256')}} for entry in entries[:1000]],
                'after': entries[999]['path'] if len(entries) > 1000 else None}

    def transfer_status(self):
        item, data = self.transfer_job(lock=False)
        if data['kind'] == 'download':
            sync = find('sync', data['sync']).get_json_value('data')
            data = {**data, 'state': 'blocked' if data['state']=='blocked' and sync['state']=='running' else sync['state'], 'files_done': sync['files_done'], 'bytes_done': sync['bytes_done'], 'missing_revisions':sync.get('missing_revisions',0),'missing_path':sync.get('missing_path','')}
        return self.transfer_public(item, data)

    def transfer_received(self):
        _, data = self.transfer_job()
        item, blob = self.transfer_blob(data)
        return {'blob': item.get_code(), **{key: blob.get(key) for key in ('received', 'size', 'state', 'sha256')}}

    def transfer_ack(self):
        item, data = self.transfer_job()
        if data['kind'] != 'download':
            raise ValueError('Download task required')
        old = self.kwargs
        try:
            self.kwargs = {**old, 'sync': data['sync']}
            result = self.sync_ack()
        finally:
            self.kwargs = old
        sync = find('sync', data['sync']).get_json_value('data')
        data.update(state=sync['state'], files_done=sync['files_done'], bytes_done=sync['bytes_done'],missing_revisions=sync.get('missing_revisions',0),missing_path=sync.get('missing_path',''))
        for key in ('reason','path','paused_ack_revision','required_bytes','available_bytes'):data.pop(key,None)
        if data['state'] == 'complete':
            data.update(total_known=True, files_total=data['files_done'], bytes_total=data['bytes_done'])
            workspace = find('workspace', data['workspace'])
            ws = workspace.get_json_value('data')
            if ws.get('active_transfer') == item.get_code():
                ws.pop('active_transfer')
                save(workspace, ws)
        save(item, data)
        return self.transfer_public(item)

    def transfer_tasks(self):
        from .file_project_cmd import integer, identifier
        search = Search('file_project/sync')
        search.add_filter('login', self.owner)
        search.add_filters('kind', ['upload', 'download', 'mutation'])
        search.add_order_by('code')
        if self.kwargs.get('after'):
            search.add_filter('code', identifier(self.kwargs['after']), op='>')
        limit = integer(self.kwargs.get('limit', 100), 1, 1000)
        search.set_limit(limit + 1)
        rows = search.get_sobjects()
        return {'items': [self.transfer_public(item) for item in rows[:limit]],
                'after': rows[limit - 1].get_code() if len(rows) > limit else None}

    def transfer_items(self):
        from .file_project_cmd import integer, logical_path
        from .file_project_cmd import identifier
        if find('sync',identifier(self.kwargs.get('task'))).get_json_value('data').get('kind') == 'mutation':
            return self.bulk_items()
        item,data = self.transfer_job(lock=False,operation='read')
        limit = integer(self.kwargs.get('limit',200),1,1000)
        after = logical_path(self.kwargs.get('after',''),prefix=True)
        if data['kind']=='download':
            sync=find('sync',data['sync']).get_json_value('data')
            root=sync.get('transferred_root') or self.catalog.empty()
        else:
            root=data['manifest_root']
        selected=self.paths() if 'paths' in self.kwargs else None
        if selected is not None:
            entries=[entry for path in selected if (entry:=self.catalog.get(root,path)) is not None]
        else:
            entries=list(islice(self.catalog.entries(root,after),limit+1))
        streams={entry.get('stream',data['stream']) for entry in entries[:limit]}
        for stream in streams:
            self.stream(stream)
        blobs={}
        if data['kind']=='upload' and entries:
            search=Search('file_project/blob')
            search.add_filters('code',[entry['blob'] for entry in entries[:limit]])
            blobs={row.get_code():row.get_json_value('data') for row in search.get_sobjects()}
        rows=[]
        for entry in entries[:limit]:
            if data['kind']=='download':
                rows.append({**entry,'state':'deleted' if entry.get('deleted') else 'downloaded','received':entry['size']})
                continue
            blob=blobs[entry['blob']]
            state='staged' if blob['state']=='ready' and data['state'] not in ('error','cancelled') and entry['path']<=data.get('stage_after','') else 'verified' if blob['state']=='ready' else 'verifying' if data.get('verifying_path')==entry['path'] else 'uploaded' if blob['state']=='uploaded' else 'uploading' if blob['received'] else 'waiting'
            if data['state']=='error' and (data.get('file_error',{}).get('path') or data.get('verifying_path'))==entry['path']:
                state='error'
            rows.append({**entry,'state':state,'received':blob['received'],'error':data.get('error') if state=='error' else None})
        return {'task':item.get_code(),'items':rows,'after':entries[limit-1]['path'] if selected is None and len(entries)>limit else None,
                'state':data['state'],'error':data.get('error')}

    def transfer_seal(self):
        item, data = self.transfer_job()
        if data['kind'] != 'upload':
            raise ValueError('Only upload manifests can be sealed')
        if data['sealed']:
            return self.transfer_public(item)
        data['leases'] = {key: value for key, value in data['leases'].items() if value['expires'] > time()}
        if data['files_done'] != data['files_total'] or data['leases']:
            raise ValueError('Finish all uploads before sealing the manifest')
        if data.get('files_manifested', data['files_total']) != data['files_total'] or data.get('bytes_manifested', data['bytes_total']) != data['bytes_total']:
            raise ValueError('Finish the entire declared manifest before sealing')
        data.update(sealed=True, total_known=True, state='queued', lease_until=0)
        save(item, data)
        return self.transfer_public(item)

    def transfer_blob(self, data, item=None):
        from .file_project_cmd import identifier
        if item is None:
            item = self.lock('blob', identifier(self.kwargs.get('blob')))
        else:
            item._check_business_write('edit')
        blob = item.get_json_value('data')
        if blob.get('transfer') != self.kwargs['task'] or blob['owner'] != self.owner or blob['change'] != data['change']:
            raise SecurityException('Blob does not belong to this transfer')
        return item, blob

    def transfer_write_begin(self):
        from .file_project_cmd import integer
        item, data = self.transfer_job()
        if data['kind'] != 'upload' or data['state'] != 'collecting':
            raise ValueError('Transfer is not accepting bytes')
        token = uuid.uuid4().hex
        self.storage_slot(token, acquire=True)
        size = integer(self.kwargs.get('size'), 1, BLOCK_BYTES)
        offset = integer(self.kwargs.get('offset', 0))
        batch = self.kwargs.get('batch', False)
        if not isinstance(batch, bool):
            raise ValueError('batch must be boolean')
        if batch and offset:
            raise ValueError('Batch archives start at offset zero')
        lease = {'token': token, 'expires': int(time()) + 300, 'offset': offset, 'size': size, 'batch': batch}
        if batch:
            path = self.transfer_staging(item.get_code(), token)
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            blob_item, blob = self.transfer_blob(data)
            current = blob.get('write_lease')
            if current and current['expires'] > time():
                from .file_storage import FileProjectBusy
                raise FileProjectBusy('Blob already has an active byte writer; wait for its cleanup')
            if blob['state'] != 'uploading' or offset != blob['received'] or offset + size > blob['size']:
                raise ValueError('Unexpected upload offset or completed blob')
            lease['blob'] = blob_item.get_code()
            blob['write_lease'] = lease
            path = self.blob_path(blob_item.get_code(), blob)
            if offset and (not path.exists() or path.stat().st_size < offset):
                raise ValueError('Committed upload prefix is missing')
            save(blob_item, blob)
        data['leases'] = {key: value for key, value in data['leases'].items() if value['expires'] > time()}
        data['leases'][token] = lease
        save(item, data)
        return {'token': token, 'offset': offset, 'size': size, '_path': str(path), 'batch': batch}

    def write_lease(self, data):
        token = self.kwargs.get('token')
        lease = data['leases'].get(token)
        if not lease or lease['expires'] <= time():
            raise ValueError('Upload byte lease expired')
        return lease

    def transfer_write_touch(self):
        item, data = self.transfer_job()
        lease = self.write_lease(data)
        lease['expires'] = int(time()) + 300
        self.storage_slot(lease['token'], acquire=True)
        if not lease['batch']:
            blob_item, blob = self.transfer_blob(data)
            if blob.get('write_lease', {}).get('token') != lease['token']:
                raise ValueError('Upload byte lease changed')
            blob['write_lease'] = lease
            save(blob_item, blob)
        save(item, data)
        return {'expires': lease['expires']}

    def transfer_write_commit(self):
        item, data = self.transfer_job()
        lease = self.write_lease(data)
        if lease['batch'] or data['state'] != 'collecting':
            raise ValueError('Transfer is not accepting this block')
        blob_item, blob = self.transfer_blob(data)
        if blob.get('write_lease', {}).get('token') != lease['token'] or blob['received'] != lease['offset']:
            raise ValueError('Upload byte lease changed')
        path = self.blob_path(blob_item.get_code(), blob)
        if path.stat().st_size != lease['offset'] + lease['size']:
            raise ValueError('Upload byte block is incomplete')
        blob['received'] += lease['size']
        blob.pop('write_lease')
        data['bytes_done'] += lease['size']
        if blob['received'] == blob['size']:
            blob['state'] = 'uploaded'
            data['files_done'] += 1
        data['leases'].pop(lease['token'])
        self.storage_slot(lease['token'])
        save(blob_item, blob)
        save(item, data)
        return {'blob': blob_item.get_code(), 'received': blob['received']}

    def transfer_write_abort(self):
        item, data = self.transfer_job()
        lease = data['leases'].pop(self.kwargs.get('token'), None)
        if lease:
            if not lease['batch']:
                self.kwargs['blob'] = lease['blob']
                blob_item, blob = self.transfer_blob(data)
                if blob.get('write_lease', {}).get('token') == lease['token']:
                    # An uncommitted tail is truncated by the next exclusive byte writer.
                    blob.pop('write_lease')
                    save(blob_item, blob)
            self.storage_slot(lease['token'])
            save(item, data)
        return self.transfer_public(item)

    def transfer_batch_commit(self):
        from .file_project_cmd import UploadUndo
        item, data = self.transfer_job()
        lease = self.write_lease(data)
        if not lease['batch'] or data['state'] != 'collecting':
            raise ValueError('Transfer is not accepting a batch')
        path = self.transfer_staging(item.get_code(), lease['token'])
        if path.stat().st_size != lease['size']:
            raise ValueError('Incomplete upload archive')
        # The storage fence covers transfer writers; the changelist lock covers legacy upload writers.
        self.lock('change', data['change'])
        rows, seen, results, members = [], set(), [], []
        with path.open('rb') as source:
            while True:
                header = source.read(512)
                if not header or header == bytes(512):
                    break
                if len(header) != 512:
                    raise ValueError('Truncated archive header')
                member = tarfile.TarInfo.frombuf(header, 'utf-8', 'strict')
                if not member.isfile() or not re.fullmatch('[0-9a-f]{32}', member.name) or member.name in seen or len(seen) >= 1000:
                    raise ValueError('Archive requires at most 1000 distinct blob files; links and paths are forbidden')
                seen.add(member.name)
                offset = source.tell()
                end = offset + (member.size + 511) // 512 * 512
                if member.size < 0 or member.size > BLOCK_BYTES or end > lease['size']:
                    raise ValueError('Invalid or truncated upload archive member')
                members.append((member, offset))
                source.seek(end)
            if not seen:
                raise ValueError('Empty archive')
            search = Search('file_project/blob')
            search.add_filters('code', sorted(seen))
            blobs = {row.get_code(): row for row in search.get_sobjects()}
            if len(blobs) != len(seen):
                raise ValueError('Unknown upload blob')
            for member, offset in members:
                source.seek(offset)
                blob_item, blob = self.transfer_blob(data, blobs[member.name])
                ready = blob['state'] == 'ready'
                if member.size > BLOCK_BYTES or blob.get('write_lease') or (blob['received'] and not ready) or blob['state'] not in ('uploading', 'ready') or blob['size'] != member.size:
                    raise ValueError('Batch cannot replace a completed/partial blob or change its size')
                target = self.blob_path(member.name, blob)
                if not ready:
                    Transaction.get().register(UploadUndo(target, 0))
                digest = sha256()
                remaining = member.size
                from contextlib import nullcontext
                with (nullcontext(None) if ready else target.open('wb')) as output:
                    while remaining:
                        block = source.read(min(4 * 1024 * 1024, remaining))
                        if not block:
                            raise ValueError('Truncated upload archive')
                        digest.update(block)
                        if output:
                            output.write(block)
                        remaining -= len(block)
                    if output:
                        output.flush()
                        import os
                        os.fsync(output.fileno())
                padding = (512 - member.size % 512) % 512
                if len(source.read(padding)) != padding:
                    raise ValueError('Truncated archive padding')
                value = digest.hexdigest()
                if blob.get('expected_sha256') and blob['expected_sha256'] != value:
                    raise ValueError('Upload checksum mismatch')
                if ready:
                    if blob['sha256'] != value:
                        raise ValueError('Conflicting upload retry')
                    results.append({'blob': member.name, 'sha256': value})
                    continue
                blob.update(state='ready', received=member.size, sha256=value)
                blob_item.set_json_value('data', blob)
                rows.append(blob_item)
                results.append({'blob': member.name, 'sha256': value})
                data['files_done'] += 1
                data['bytes_done'] += member.size
                data['verified_files'] += 1
                data['verified_bytes'] += member.size
        commit_records(rows)
        data['leases'].pop(lease['token'])
        self.storage_slot(lease['token'])
        save(item, data)
        return {**self.transfer_public(item), 'items': results}

    def transfer_digests(self):
        from .file_project_cmd import identifier
        _, data = self.transfer_job()
        if data['kind'] != 'upload' or data['sealed'] or data['state'] != 'collecting':
            raise ValueError('Transfer is not collecting checksums')
        values = self.kwargs.get('items')
        if not isinstance(values, list) or not 1 <= len(values) <= 1000:
            raise ValueError('Checksums require 1..1000 descriptors')
        expected = {}
        for entry in values:
            code = identifier(entry['blob'])
            if code in expected:
                raise ValueError('Duplicate checksum blob')
            expected[code] = checksum(entry['sha256'])
        search = Search('file_project/blob')
        search.add_filters('code', list(expected))
        rows = search.get_sobjects()
        if len(rows) != len(expected):
            raise ValueError('Unknown checksum blob')
        changed = []
        for row in rows:
            blob = row.get_json_value('data')
            if blob.get('transfer') != self.kwargs['task'] or blob['owner'] != self.owner or blob['change'] != data['change']:
                raise SecurityException('Checksum blob belongs to another transfer')
            value = expected[row.get_code()]
            if blob['state'] == 'ready':
                if value != blob['sha256']:
                    raise ValueError('Upload checksum mismatch')
            elif blob.get('expected_sha256') != value:
                blob['expected_sha256'] = value
                row.set_json_value('data', blob)
                changed.append(row)
        commit_records(changed)
        return {'files': len(rows)}

    def transfer_file_digest(self):
        item, data = self.transfer_job()
        if data['sealed']:
            raise ValueError('Transfer is sealed')
        blob_item, blob = self.transfer_blob(data)
        expected = checksum(self.kwargs.get('sha256'))
        if blob['state'] == 'ready':
            if blob['sha256'] != expected:
                raise ValueError('Upload checksum mismatch')
        else:
            blob['expected_sha256'] = expected
            save(blob_item, blob)
        return {'blob': blob_item.get_code(), 'expected_sha256': expected}

    def transfer_claim(self):
        service_only()
        item, data = self.transfer_job()
        if data['kind'] != 'upload' or data['state'] not in ('queued', 'running') or data.get('lease_until', 0) > time():
            raise ValueError('Task is not claimable')
        data.update(state='running', worker_token=uuid.uuid4().hex, lease_until=int(time()) + 60,
                    verifying_bytes=0, verifying_path=None)
        save(item, data)
        return {**self.transfer_public(item), 'worker_token': data['worker_token']}

    def worker_job(self):
        service_only()
        item, data = self.transfer_job()
        if data['state'] != 'running' or data.get('worker_token') != self.kwargs.get('worker_token'):
            raise ValueError('Transfer worker lease changed or task stopped')
        data['lease_until'] = int(time()) + 60
        return item, data

    def transfer_verify_next(self):
        item, data = self.worker_job()
        entries = list(islice(self.catalog.entries(data['manifest_root'], data['verify_after']), 1001))
        if not entries:
            save(item, data)
            return {'complete': True}
        search = Search('file_project/blob')
        search.add_filters('code', [entry['blob'] for entry in entries[:1000]])
        blobs = {row.get_code(): row.get_json_value('data') for row in search.get_sobjects()}
        for entry in entries[:1000]:
            blob = blobs[entry['blob']]
            if blob['state'] != 'ready':
                save(item, data)
                return {'complete': False, **entry, 'state': blob['state'], 'sha256': blob['sha256'],
                    'expected_sha256': blob.get('expected_sha256'), '_path': str(self.blob_path(entry['blob'], blob))}
            data['verify_after'] = entry['path']
        save(item, data)
        return {'complete': len(entries) <= 1000, 'skipped': True}

    def transfer_verify_progress(self):
        from .file_project_cmd import integer, logical_path
        item, data = self.worker_job()
        path = logical_path(self.kwargs.get('path'))
        entry = self.catalog.get(data['manifest_root'], path)
        if not entry:
            raise ValueError('Unknown verification path')
        data.update(verifying_path=path, verifying_bytes=integer(self.kwargs.get('bytes'), high=entry['size']))
        save(item, data)
        return self.transfer_public(item)

    def transfer_verify_finish(self):
        item, data = self.worker_job()
        blob_item, blob = self.transfer_blob(data)
        value = checksum(self.kwargs.get('sha256'))
        path = self.blob_path(blob_item.get_code(), blob)
        if blob['received'] != blob['size'] or path.stat().st_size != blob['size'] or blob.get('write_lease'):
            raise ValueError('Stored upload is incomplete')
        if blob.get('expected_sha256') and value != blob['expected_sha256']:
            raise ValueError('Upload checksum mismatch')
        if blob['state'] != 'ready':
            if blob['state'] != 'uploaded':
                raise ValueError('Blob is not waiting for verification')
            blob.update(state='ready', sha256=value)
            save(blob_item, blob)
            data['verified_files'] += 1
            data['verified_bytes'] += blob['size']
        elif value != blob['sha256']:
            raise ValueError('Verified upload changed')
        if blob['path'] <= data['verify_after']:
            return self.transfer_public(item)
        data.update(verify_after=blob['path'], verifying_path=None, verifying_bytes=0)
        save(item, data)
        return self.transfer_public(item)

    def transfer_step(self):
        item, data = self.worker_job()
        if data['verified_files'] != data['files_total']:
            raise ValueError('Verify the entire transfer before staging')
        entries = list(islice(self.catalog.entries(data['manifest_root'], data['stage_after']), 1001))
        old = self.kwargs
        try:
            self._staging_transfer = item.get_code()
            if entries:
                self.kwargs = {'change': data['change'], 'chunk': sha256((item.get_code() + data['stage_after']).encode()).hexdigest(),
                               'edit_revision': data['expected_edit_revision'],
                               'operations': [{'path': entry['path'], 'blob': entry['blob']} for entry in entries[:1000]]}
                edited = self.edit()
                data['expected_edit_revision'] = edited['edit_revision']
                data['stage_after'] = entries[min(len(entries), 1000) - 1]['path']
                data['staged_files'] += min(len(entries), 1000)
            if len(entries) <= 1000:
                change = self.lock('change', data['change'])
                draft = change.get_json_value('data')
                draft.pop('active_transfer', None)
                save(change, draft)
                if data['submit']:
                    self.kwargs = {'change': data['change']}
                    self.submit()
                    data['state'] = 'submitted'
                else:
                    data['state'] = 'ready'
                data['lease_until'] = 0
        finally:
            self._staging_transfer = None
            self.kwargs = old
        save(item, data)
        return self.transfer_public(item)

    def transfer_fail(self):
        item, data = self.worker_job()
        error = self.kwargs.get('error')
        if not isinstance(error, str):
            raise ValueError('Error description required')
        details=self.kwargs.get('file_error')
        if details is not None:
            from .file_project_cmd import logical_path
            if not isinstance(details,dict) or set(details)-{'path','operation','cause'}:
                raise ValueError('Invalid file error details')
            details={**details,'path':logical_path(details.get('path'))}
            if any(not isinstance(details.get(key),str) or len(details[key])>4096 for key in ('operation','cause')):
                raise ValueError('Invalid file error details')
        self.restore_transfer(item.get_code(), data)
        data.update(state='error', error=error[:4096], lease_until=0)
        if details:data['file_error']=details
        save(item, data)
        return self.transfer_public(item)

    def transfer_block(self):
        service_only()
        from pyasm.security.security import _require_admin
        from .file_project_cmd import identifier
        _require_admin()
        item = self.lock('sync', identifier(self.kwargs.get('task')))
        data = item.get_json_value('data')
        if data.get('kind') != 'upload':
            raise ValueError('Upload task required')
        if data['state'] in ('queued', 'running'):
            self.restore_transfer(item.get_code(), data)
            data.update(state='error', error=str(self.kwargs.get('error', 'Worker access denied'))[:4096], lease_until=0)
            save(item, data)
        return self.transfer_public(item)

    def transfer_pause(self):
        """Persist a stopped download without acknowledging or deleting local files."""
        from .file_project_cmd import integer
        _,probe=self.transfer_job(lock=False)
        if probe['kind']!='download':raise ValueError('Download task required')
        workspace=self.lock('workspace',probe['workspace'])
        item,data=self.transfer_job()
        sync=find('sync',data['sync']).get_json_value('data')
        if sync['state']!='running':return self.transfer_public(item)
        ws=workspace.get_json_value('data')
        if ws.get('active_transfer')!=item.get_code() or ws['active_sync']!=data['sync']:
            raise ValueError('Download is no longer active')
        if integer(self.kwargs.get('ack_revision'))!=sync['ack_revision']:
            raise ValueError('Download advanced before pause')
        reason=self.kwargs.get('reason')
        path=self.kwargs.get('path','')
        if reason not in ('local_modified_or_untracked','download_error','interrupted','insufficient_disk_space'):
            raise ValueError('Download stop reason required')
        if not isinstance(path,str) or len(path)>8192 or '\x00' in path:
            raise ValueError('Invalid stopped download path')
        space = {}
        if reason == 'insufficient_disk_space':
            space = {key:integer(self.kwargs.get(key),high=2**63-1)
                     for key in ('required_bytes','available_bytes')}
        data.update(state='blocked',reason=reason,path=path,paused_ack_revision=sync['ack_revision'],**space)
        save(item,data)
        return self.transfer_public(item)

    def transfer_cancel(self):
        item, data = self.transfer_job()
        if data['state'] in ('complete', 'ready', 'submitted', 'cancelled'):
            return self.transfer_public(item)
        if data['kind'] == 'download':
            old = self.kwargs
            try:
                self.kwargs = {'sync': data['sync']}
                if find('sync', data['sync']).get_json_value('data')['state'] == 'running':
                    self.sync_cancel()
                workspace = find('workspace', data['workspace'])
                ws = workspace.get_json_value('data')
                if ws.get('active_transfer') == item.get_code():
                    ws.pop('active_transfer')
                    save(workspace, ws)
            finally:
                self.kwargs = old
        elif data['state'] in ('ready', 'submitted', 'cancelled'):
            return self.transfer_public(item)
        if data['kind'] == 'upload':
            self.restore_transfer(item.get_code(), data)
        data.update(state='cancelled', lease_until=0)
        save(item, data)
        return self.transfer_public(item)

    def restore_transfer(self, code, data):
        """Restore the complete private draft with one root flip after cancel/failure."""
        if not data.get('original_change'):
            return
        change = self.lock('change', data['change'])
        draft = change.get_json_value('data')
        if draft['state'] == 'pending' and draft.get('active_transfer') == code:
            restored = {**data['original_change'], 'edit_revision': draft['edit_revision'] + 1}
            save(change, restored)
            self.storage_data['reference_revision'] += 1
