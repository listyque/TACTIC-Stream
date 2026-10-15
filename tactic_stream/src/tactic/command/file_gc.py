"""Bounded mark/sweep with a native root fence and two-phase physical reclamation."""
from itertools import islice
from time import time

from pyasm.biz.file_project import find, create, save
from pyasm.search import Search
from pyasm.security.security import _require_admin
from .file_storage import maintenance
from .file_transfer import service_only

GC_ACTIONS = {'gc_begin', 'gc_status', 'gc_step', 'gc_purged', 'gc_cancel', 'gc_fail'}
ROOT_TABLES = ('stream', 'change', 'workspace', 'sync')
SWEEP_TABLES = ('version', 'page', 'blob')


class FileGcMixin:
    def gc_begin(self):
        _require_admin()
        if not self.storage_data or not self.storage_data['indexed']:
            raise ValueError('Finish the storage index before GC')
        dry = self.kwargs.get('dry_run', True)
        if not isinstance(dry, bool):
            raise ValueError('dry_run must be boolean')
        active = Search('file_project/sync')
        active.add_filter('kind', 'gc')
        active.add_filters('state', ['queued', 'running'])
        active.set_limit(1)
        if active.get_sobject():
            raise ValueError('A GC task is already active')
        item = create('sync', {'kind': 'gc', 'owner': self.owner, 'state': 'queued', 'lease_until': 0,
            'dry_run': dry, 'phase': 'roots', 'table': 0, 'after': '', 'cutoff': int(time()),
            'reference_revision': self.storage_data['reference_revision'],
            'write_barrier': True,
            'queue_root': self.catalog.empty(), 'marks_root': self.catalog.empty(),
            'objects_done': 0, 'candidates': 0, 'candidate_bytes': 0, 'quarantined': 0,
            'purged': 0, 'expired': 0, 'restarts': 0})
        self.storage_data['next_gc_at'] = int(time()) + self.storage_data.get('gc_interval_seconds', 86400)
        self.storage_data['active_gc'] = item.get_code()
        self.save_change(item, item.get_json_value('data'))
        return self.result(item)

    def gc_job(self):
        _require_admin()
        from .file_project_cmd import identifier
        item = self.lock('sync', identifier(self.kwargs.get('task')))
        data = item.get_json_value('data')
        if data.get('kind') != 'gc':
            raise ValueError('GC task required')
        return item, data

    def gc_status(self):
        item, _ = self.gc_job()
        return self.result(item)

    def gc_cancel(self):
        item, data = self.gc_job()
        data.update(state='cancelled', lease_until=0)
        save(item, data)
        if self.storage_data.get('active_gc') == item.get_code():
            self.storage_data.pop('active_gc')
        return self.result(item)

    def gc_fail(self):
        service_only()
        item, data = self.gc_job()
        data.update(state='error', error=str(self.kwargs.get('error', 'GC failed'))[:4096], lease_until=0)
        save(item, data)
        if self.storage_data.get('active_gc') == item.get_code():
            self.storage_data.pop('active_gc')
        return self.result(item)

    def gc_refs(self, value):
        if isinstance(value, list):
            for item in value:
                yield from self.gc_refs(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, str):
                    if (key == 'root' or key.endswith('_root')) and len(item) == 64:
                        yield 'page', item
                    elif key in ('blob', 'version', 'previous') and len(item) == 32:
                        yield ('blob' if key == 'blob' else 'version'), item
                else:
                    yield from self.gc_refs(item)
            # A sync checkpoint maps stream names directly to pinned catalog roots.
            for root in value.get('sources', {}).values() if isinstance(value.get('sources'), dict) else ():
                if isinstance(root, str) and len(root) == 64:
                    yield 'page', root

    def gc_enqueue(self, data, references):
        edits, seen = [], set()
        for kind, code in references:
            path = kind + '/' + code
            if path not in seen and not self.catalog.get(data['marks_root'], path):
                edits.append({'path': path, 'size': 0, 'kind': kind, 'code': code})
                seen.add(path)
        if edits:
            data['queue_root'] = self.catalog.update(data['queue_root'], edits)

    def gc_expired(self, kind, row, data):
        value = row.get_json_value('data')
        updated = row.get_value('updated_at', no_exception=True)
        if updated is None:
            return False
        policy = self.storage_data
        if kind == 'change':
            seconds = policy['shelf_retention_seconds'] if value['state'] == 'shelved' else policy['reverted_retention_seconds'] if value['state'] == 'reverted' else 0
        elif kind == 'sync':
            if value.get('kind') == 'upload' and value.get('state') == 'collecting' and not any(
                    lease['expires'] > time() for lease in value.get('leases', {}).values()):
                seconds = policy['upload_retention_seconds']
            else:
                seconds = policy['task_retention_seconds'] if value.get('state') in ('complete', 'submitted', 'ready', 'cancelled', 'error') else 0
        else:
            seconds = 0
        return bool(seconds and updated + seconds < data['cutoff'])

    def gc_rows(self, kind, after, *, cutoff=None):
        search = Search('file_project/' + kind)
        search.add_order_by('code')
        search.add_filter('code', after, op='>')
        if cutoff is not None:
            search.add_filter('created_at', cutoff, op='<')
        search.set_limit(1001)
        return search.get_sobjects()

    def gc_step(self):
        service_only()
        item, data = self.gc_job()
        if data['state'] in ('complete', 'cancelled', 'error'):
            return {**self.result(item), 'reap': []}
        if not data.get('write_barrier'):
            # Upgrade an older in-flight collection once before enabling its write barrier.
            data.update(phase='roots', table=0, after='', cutoff=int(time()), queue_root=self.catalog.empty(),
                        marks_root=self.catalog.empty(), reference_revision=self.storage_data['reference_revision'],
                        restarts=data['restarts'] + 1, write_barrier=True)
        self.storage_data['active_gc'] = item.get_code()
        if data['phase'] in ('sweep', 'reap') and self.catalog.stats(data['queue_root'])['files']:
            data['resume'] = {key: data[key] for key in ('phase', 'table', 'after')}
            data['phase'] = 'graph'
        data.update(state='running', lease_until=int(time()) + 60)
        staging = []
        if data['phase'] == 'roots':
            kind = ROOT_TABLES[data['table']]
            rows = self.gc_rows(kind, data['after'])
            for row in rows[:1000]:
                if row.get_code() == item.get_code():
                    continue
                value = row.get_json_value('data')
                if self.gc_expired(kind, row, data):
                    data['expired'] += 1
                    if not data['dry_run']:
                        if kind == 'sync' and value.get('kind') == 'upload':
                            self.restore_transfer(row.get_code(), value)
                        with maintenance(self.project):
                            value = {'state': 'expired', 'kind': value.get('kind', 'sync'),
                                     'owner': value.get('owner'), 'stream': value.get('stream'), 'root': self.catalog.empty()}
                            save(row, value)
                        if kind == 'sync' and value.get('kind') == 'upload':
                            staging.append(str(self.transfer_staging(row.get_code(), '0' * 32).parent))
                    continue
                if value.get('state') == 'expired':
                    if kind == 'sync' and value.get('kind') == 'upload' and not data['dry_run']:
                        staging.append(str(self.transfer_staging(row.get_code(), '0' * 32).parent))
                    continue
                self.gc_enqueue(data, self.gc_refs(value))
            if rows:
                data['after'] = rows[min(len(rows), 1000) - 1].get_code()
            if len(rows) <= 1000:
                data['table'], data['after'] = data['table'] + 1, ''
                if data['table'] == len(ROOT_TABLES):
                    data.update(phase='graph', table=0)
        elif data['phase'] == 'graph':
            remaining = 256
            while remaining:
                entries = list(islice(self.catalog.entries(data['queue_root']), remaining))
                if not entries:
                    break
                marks, remove, references = [], [], []
                for kind in ('page', 'version', 'blob'):
                    codes = [entry['code'] for entry in entries if entry['kind'] == kind]
                    if not codes:
                        continue
                    search = Search('file_project/' + kind)
                    search.add_filters('code', codes)
                    records = {row.get_code(): row.get_json_value('data') for row in search.get_sobjects()}
                    if set(codes) != set(records):
                        raise ValueError('GC found a missing referenced object; collection stopped')
                    for entry in entries:
                        if entry['kind'] != kind:
                            continue
                        value = records[entry['code']]
                        references.extend(self.gc_refs(value))
                        if kind == 'page' and not value['leaf']:
                            references.extend(('page', child['code']) for child in value['items'])
                        marks.append(entry)
                        remove.append({'path': entry['path'], 'delete': True})
                data['marks_root'] = self.catalog.update(data['marks_root'], marks)
                data['queue_root'] = self.catalog.update(data['queue_root'], remove)
                self.gc_enqueue(data, references)
                data['objects_done'] += len(entries)
                remaining -= len(entries)
            if self.catalog.stats(data['queue_root'])['files'] == 0:
                data.update(data.pop('resume') if 'resume' in data else dict(phase='sweep', table=0, after=''))
        if data['phase'] == 'sweep':
            kind = SWEEP_TABLES[data['table']]
            rows = self.gc_rows(kind, data['after'], cutoff=data['cutoff'])
            for row in rows[:1000]:
                if self.catalog.get(data['marks_root'], kind + '/' + row.get_code()):
                    continue
                value = row.get_json_value('data')
                if kind == 'blob':
                    if value['state'] in ('quarantined', 'reclaimed', 'purged') or value.get('write_lease', {}).get('expires', 0) > time():
                        continue
                    updated = row.get_value('updated_at', no_exception=True)
                    if updated is None or updated + self.storage_data['upload_retention_seconds'] >= data['cutoff']:
                        continue
                    change = find('change', value['change'], False)
                    if change and change.get_json_value('data')['state'] == 'pending':
                        task = find('sync', value.get('transfer'), False) if value.get('transfer') else None
                        if not task or task.get_json_value('data').get('state') != 'expired':
                            continue
                data['candidates'] += 1
                data['candidate_bytes'] += value.get('size', 0) if kind == 'blob' else 0
                if not data['dry_run']:
                    with maintenance(self.project):
                        if kind == 'blob':
                            value.update(state='quarantined', quarantine_until=int(time()) + self.storage_data['gc_grace_seconds'])
                            save(row, value)
                            data['quarantined'] += 1
                        else:
                            row.delete(log=False)
            if rows:
                data['after'] = rows[min(len(rows), 1000) - 1].get_code()
            if len(rows) <= 1000:
                data['table'], data['after'] = data['table'] + 1, ''
                if data['table'] == len(SWEEP_TABLES):
                    data.update(state='complete' if data['dry_run'] else 'running', phase='complete' if data['dry_run'] else 'reap', lease_until=0)
        elif data['phase'] == 'reap':
            result, due = self.gc_reap()
            if not result and due is None:
                data.update(state='complete', phase='complete', lease_until=0)
                self.storage_data.pop('active_gc', None)
            elif due and not result:
                data.update(state='queued', lease_until=due)
            self.save_change(item, data)
            return {**self.result(item), 'reap': result}
        self.save_change(item, data)
        if data['state'] == 'complete':
            self.storage_data.pop('active_gc', None)
        return {**self.result(item), 'reap': [], '_staging': staging}

    def gc_reap(self):
        rows = []
        for state in ('reclaimed', 'quarantined'):
            search = Search('file_project/blob')
            search.add_filter('state', state)
            if state == 'quarantined':
                search.add_filter('quarantine_until', int(time()), op='<=')
            search.add_order_by('code')
            search.set_limit(1000 - len(rows))
            rows.extend(search.get_sobjects())
            if len(rows) == 1000:
                break
        result = []
        for probe in rows:
            value = probe.get_json_value('data')
            if value['state'] == 'quarantined' and value['quarantine_until'] <= time():
                row = self.lock('blob', probe.get_code())
                value = row.get_json_value('data')
                with maintenance(self.project):
                    value['state'] = 'reclaimed'
                    save(row, value)
            if value['state'] == 'reclaimed':
                result.append({'blob': probe.get_code(), '_path': str(self.blob_path(probe.get_code(), value))})
        search = Search('file_project/blob')
        search.add_filter('state', 'quarantined')
        search.add_order_by('quarantine_until')
        search.set_limit(1)
        pending = search.get_sobject()
        return result, pending.get_value('quarantine_until') if pending else None

    def gc_purged(self):
        service_only()
        _require_admin()
        from .file_project_cmd import identifier
        row = self.lock('blob', identifier(self.kwargs.get('blob')))
        value = row.get_json_value('data')
        if value['state'] == 'purged':
            return {'blob': row.get_code(), 'state': 'purged'}
        if value['state'] != 'reclaimed' or self.blob_path(row.get_code(), value).exists():
            raise ValueError('Remove only an approved reclaimed file before releasing its quota')
        self.storage_data['allocated_bytes'] -= value['size']
        self.storage_data['allocated_files'] -= 1
        with maintenance(self.project):
            value['state'] = 'purged'
            save(row, value)
        if self.kwargs.get('task'):
            item, data = self.gc_job()
            data['purged'] += 1
            save(item, data)
        return {'blob': row.get_code(), 'state': 'purged'}
