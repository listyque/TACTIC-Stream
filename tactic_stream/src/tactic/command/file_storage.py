"""Native storage accounting, retention settings and a fence for safe collection."""
from contextlib import contextmanager
from copy import deepcopy
from time import time

from pyasm.biz.file_project import commit_records, create, find, save, storage_schema, TABLES
from pyasm.common import Container, Environment
from pyasm.security.security import _require_admin
from pyasm.search import Search
import sqlite3

STORAGE_ACTIONS = {'storage_status', 'storage_policy', 'storage_upgrade', 'storage_index'}


class FileProjectBusy(Exception):
    """No domain mutation ran: retry the same command after its lock rolled back."""
REFERENCE_WRITES = {'revision_upgrade', 'revision_snapshot', 'create_stream', 'update_stream', 'create_workspace', 'update_workspace', 'create_change', 'edit', 'checkout',
                    'submit', 'revert', 'revert_files', 'shelve', 'update_shelf', 'offer_change', 'accept_change', 'remove_files', 'move_files', 'rename_files', 'restore_file', 'delete_change', 'select_query', 'index_change',
                    'rebase_begin', 'unshelve_begin', 'merge_begin', 'integration_next',
                    'integration_finish', 'integration_cancel', 'resolve', 'undo_resolve', 'sync_begin', 'sync_ack',
                    'sync_cancel', 'stream_ancestry', 'transfer_manifest', 'transfer_step', 'transfer_cancel',
                    'transfer_ack', 'transfer_begin', 'bulk_begin', 'bulk_run', 'bulk_fail', 'bulk_block'}
STORAGE_WRITES = REFERENCE_WRITES | {'upload_begin', 'transfer_begin', 'transfer_write_begin',
    'transfer_write_commit', 'transfer_write_abort', 'transfer_write_touch', 'transfer_batch_commit',
    'transfer_seal', 'transfer_claim', 'transfer_verify_next', 'transfer_verify_progress', 'transfer_verify_finish', 'transfer_fail',
    'storage_policy', 'storage_index', 'gc_begin', 'gc_step', 'gc_purged', 'gc_cancel', 'gc_fail', 'transfer_file_digest',
    'transfer_digests', 'transfer_block', 'transfer_pause', 'bulk_claim'}


def policy_defaults(indexed=False):
    return {'indexed': indexed, 'revision': 0, 'reference_revision': 0, 'allocated_bytes': 0,
            'allocated_files': 0, 'bytes_limit': 0, 'files_limit': 0, 'max_parallel': 4,
            'upload_retention_seconds': 7 * 86400, 'reverted_retention_seconds': 30 * 86400,
            'task_retention_seconds': 7 * 86400, 'shelf_retention_seconds': 0,
            'gc_grace_seconds': 86400, 'gc_interval_seconds': 86400, 'next_gc_at': int(time()) + 86400, 'leases': {}}


@contextmanager
def maintenance(project):
    previous = Container.get('FileProject:maintenance')
    Container.put('FileProject:maintenance', project)
    try:
        yield
    finally:
        Container.put('FileProject:maintenance', previous)


class FileStorageMixin:
    def storage_guard(self, action):
        self.storage_record = find('chunk', 'storage-policy', False)
        self.storage_data = None
        if self.storage_record and action in STORAGE_WRITES:
            try:
                self.storage_record = self.lock('chunk', 'storage-policy')
            except Exception as error:
                if (getattr(error, 'sqlite_errorcode', 0) & 255 in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
                        or getattr(error, 'sqlstate', None) == '55P03'):
                    raise FileProjectBusy('File project is busy; retry the same request') from error
                raise
            self.storage_data = self.storage_record.get_json_value('data')
        self.storage_action = action
        self.storage_original = deepcopy(self.storage_data)
        self.storage_seen = Container.get('FileProject:storage-write-revision')

    def storage_merge(self):
        if self.storage_seen == Container.get('FileProject:storage-write-revision'):
            return
        latest = self.lock('chunk', 'storage-policy').get_json_value('data')
        original, local = self.storage_original, self.storage_data
        merged = deepcopy(latest)
        for key in original.keys() | local.keys():
            if original.get(key) == local.get(key):
                continue
            if key in ('allocated_bytes', 'allocated_files', 'reference_revision'):
                merged[key] = latest.get(key, 0) + local.get(key, 0) - original.get(key, 0)
            elif key == 'leases':
                for token in original.get(key, {}).keys() | local.get(key, {}).keys():
                    before, after = original.get(key, {}).get(token), local.get(key, {}).get(token)
                    if before == after:
                        continue
                    if latest.get(key, {}).get(token) not in (before, after):
                        raise ValueError('Conflicting nested storage lease mutation')
                    if after is None:
                        merged[key].pop(token, None)
                    else:
                        merged[key][token] = after
            else:
                if latest.get(key) not in (original.get(key), local.get(key)):
                    raise ValueError('Conflicting nested storage policy mutation: ' + key)
                if key in local:
                    merged[key] = local[key]
                else:
                    merged.pop(key, None)
        for total, limit in (('allocated_bytes', 'bytes_limit'), ('allocated_files', 'files_limit')):
            if not 0 <= merged[total] <= 2**63 - 1 or merged[limit] and merged[total] > merged[limit]:
                raise ValueError('Nested file operations exceed the storage quota')
        self.storage_original, self.storage_data = latest, merged
        self.storage_seen = Container.get('FileProject:storage-write-revision')

    def storage_flush(self):
        if self.storage_data is not None:
            self.storage_merge()
            if self.storage_action in REFERENCE_WRITES:
                self.storage_data['reference_revision'] += 1
            task = self.storage_data.get('active_gc')
            if task and not self.storage_action.startswith('gc_'):
                item = self.lock('sync', task)
                data = item.get_json_value('data')
                if data['state'] in ('complete', 'cancelled', 'error'):
                    self.storage_data.pop('active_gc', None)
                else:
                    references = []
                    for row in (Container.get('FileGC:changed-roots') or {}).values():
                        if row.get_db_resource()._get_connection_key() != item.get_db_resource()._get_connection_key():
                            continue
                        value = row.get_json_value('data')
                        if value.get('kind') != 'gc':
                            references.extend(self.gc_refs(value))
                    self.gc_enqueue(data, references)
                    save(item, data)
            self.storage_merge()
            if self.storage_data != self.storage_original:
                save(self.storage_record, self.storage_data)
                self.storage_original = deepcopy(self.storage_data)
            self.storage_seen = Container.get('FileProject:storage-write-revision')

    def reserve_storage(self, sizes):
        if self.storage_data is None:
            return
        data = self.storage_data
        if not data['indexed']:
            raise ValueError('Finish storage_index before allocating uploads')
        size, count = sum(sizes), len(sizes)
        if data['allocated_bytes'] + size > 2**63 - 1:
            raise ValueError('Storage total exceeds supported size')
        if data['bytes_limit'] and data['allocated_bytes'] + size > data['bytes_limit']:
            raise ValueError('Storage byte quota exceeded')
        if data['files_limit'] and data['allocated_files'] + count > data['files_limit']:
            raise ValueError('Storage file quota exceeded')
        data['allocated_bytes'] += size
        data['allocated_files'] += count

    def storage_status(self):
        item = find('chunk', 'storage-policy', False)
        if not item:
            return {'initialized': False, 'indexed': False}
        data = item.get_json_value('data')
        result = {key: value for key, value in data.items() if key != 'leases'}
        result['initialized'] = True
        # Decimal strings keep quotas and revisions exact across the JavaScript/QML boundary.
        result['policy_values'] = {key: str(data[key]) for key in policy_defaults()
                                   if key.endswith('_seconds') or key in ('bytes_limit', 'files_limit', 'max_parallel')}
        result['policy_revision'] = str(data['revision'])
        if Environment.get_security().is_admin():
            search = Search('file_project/sync')
            search.add_filter('kind', 'gc')
            search.add_order_by('id desc')
            search.set_limit(1)
            gc = search.get_sobject()
            if gc:
                result['gc'] = {key: value for key, value in self.result(gc).items()
                                if key not in ('queue_root', 'marks_root', 'lease_until')}
        return result

    def storage_policy(self):
        from .file_project_cmd import integer
        _require_admin()
        data = self.storage_data
        if data is None or not data['indexed']:
            raise ValueError('Storage index is not complete')
        def policy_integer(value, low=0, high=2**63 - 1):
            if isinstance(value, str) and value.isascii() and value.isdigit() and len(value) <= 19:
                value = int(value)
            return integer(value, low, high)
        if policy_integer(self.kwargs.get('revision')) != data['revision']:
            raise ValueError('Storage policy revision conflict')
        values = self.kwargs.get('policy')
        allowed = {'bytes_limit', 'files_limit', 'max_parallel', 'upload_retention_seconds',
                   'reverted_retention_seconds', 'task_retention_seconds', 'shelf_retention_seconds', 'gc_grace_seconds',
                   'gc_interval_seconds'}
        if not isinstance(values, dict) or set(values) - allowed:
            raise ValueError('Invalid storage policy')
        for key, value in values.items():
            data[key] = policy_integer(value, 1 if key == 'max_parallel' else 0, 16 if key == 'max_parallel' else 2**63 - 1)
        data['revision'] += 1
        data['reference_revision'] += 1
        return {key: value for key, value in data.items() if key != 'leases'}

    def storage_upgrade(self):
        from pyasm.biz import Project
        _require_admin()
        if find('chunk', 'storage-policy', False):
            return self.storage_status()
        storage_schema(Project.get().get_project_db_resource().get_sql(), upgrade=True)
        return self.result(create('chunk', policy_defaults(), 'storage-policy'))

    def storage_index(self):
        _require_admin()
        data = self.storage_data
        if data is None:
            raise ValueError('Run storage_upgrade first')
        if data['indexed']:
            return self.storage_status()
        after = data.get('index_after', '')
        kind = TABLES[data.get('index_table', 0)]
        search = Search('file_project/' + kind)
        search.add_order_by('code')
        search.add_filter('code', after, op='>')
        search.set_limit(1001)
        rows = search.get_sobjects()
        page = rows[:1000]
        now = int(time())
        with maintenance(self.project):
            for row in page:
                blob = row.get_json_value('data')
                if kind == 'blob' and blob['state'] != 'purged':
                    data['allocated_bytes'] += blob['size']
                    data['allocated_files'] += 1
                if row.get_value('created_at', no_exception=True) is None:
                    row.set_value('created_at', now)
                row.set_json_value('data', blob)
                data['index_after'] = row.get_code()
            commit_records(page)
        if len(rows) <= 1000:
            data['index_after'] = ''
            data['index_table'] = data.get('index_table', 0) + 1
            data['indexed'] = data['index_table'] == len(TABLES)
        return {key: value for key, value in data.items() if key != 'leases'}

    def storage_slot(self, token, acquire=False):
        data = self.storage_data
        if data is None:
            raise ValueError('Storage is not initialized')
        now = int(time())
        data['leases'] = {key: value for key, value in data['leases'].items() if value > now}
        if acquire and token not in data['leases'] and len(data['leases']) >= data['max_parallel']:
            raise ValueError('Transfer concurrency limit reached; retry later')
        if acquire:
            data['leases'][token] = now + 300
        else:
            data['leases'].pop(token, None)
