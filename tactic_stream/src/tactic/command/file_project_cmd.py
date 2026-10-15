"""Fixed, bounded native API for opt-in file projects; no classic check-in path."""
import base64
from hashlib import sha256
from itertools import islice
from pathlib import PurePosixPath
import re
import uuid
from time import time_ns

from pyasm.biz import Project
from pyasm.biz.file_catalog import FileCatalog
from pyasm.biz.file_project import MODE, PageStore, access, blob_file_path, commit_records, create, encode, find, save, save_batch
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from pyasm.search import Search
from pyasm.search.search import _context
from pyasm.search.transaction import Transaction
from .file_change import FileChangeMixin
from .file_workspace import FileWorkspaceMixin
from .file_merge import FileMergeMixin
from .file_storage import FileStorageMixin, STORAGE_ACTIONS
from .file_transfer import FileTransferMixin, TRANSFER_ACTIONS
from .file_gc import FileGcMixin, GC_ACTIONS
from .file_selection import FileSelectionMixin
from .file_revision import FileRevisionMixin, revision_spec
from .file_bulk import FileBulkMixin, BULK_ACTIONS
from .file_reads import FileReadMixin, READ_ACTIONS
from .file_revert import FileRevertMixin
from .file_streams import FileStreamMixin, STREAM_TYPES

CHUNK_LIMIT = 1000
TRANSFER_LIMIT = 4 * 1024 * 1024
FILE_ACTIONS = {'revision_snapshot', 'revision_upgrade', 'capabilities', 'admin_search', 'create_depot', 'create_stream', 'update_stream', 'create_workspace', 'create_change',
    'upload_begin', 'upload_chunk', 'upload_batch', 'upload_finish', 'uploads', 'edit', 'checkout', 'locks', 'submit', 'submit_task_status', 'revert', 'revert_files', 'select_unchanged',
    'list', 'browse', 'workspace_browse', 'workspace_paths', 'file_states', 'file_info', 'file_preview', 'compare_files', 'select_query', 'selection_page', 'changes', 'history', 'read', 'status', 'transfer', 'have', 'workspace_status', 'sync_begin', 'sync_next', 'sync_ack', 'sync_cancel', 'sync_status',
    'change_files', 'change_preview', 'compare_shelf', 'update_shelf', 'offer_change', 'accept_change', 'inspect_change', 'inspect_change_files', 'index_change', 'update_change', 'remove_files', 'move_files', 'rename_files', 'restore_file', 'delete_change', 'shelve', 'rebase_begin', 'unshelve_begin',
    'integration_preview', 'integration_next', 'integration_finish', 'integration_cancel', 'conflicts', 'resolved_files', 'resolve', 'undo_resolve', 'depots', 'update_depot', 'streams',
    'stream_status', 'stream_graph', 'workspaces', 'workspace_preview', 'workspace_switch_preview', 'update_workspace', 'workspace_active', 'switch_workspace', 'reconcile', 'merge_begin', 'stream_ancestry'}


def logical_path(value, prefix=False):
    if not isinstance(value, str) or len(value.encode('utf-8')) > 2048:
        raise ValueError('Invalid depot path')
    if prefix and value == '':
        return value
    trimmed = value[:-1] if prefix and value.endswith('/') else value
    if (not trimmed or trimmed.startswith('/') or any(char in value for char in '\\:\x00') or
            any(part in ('', '.', '..') for part in trimmed.split('/'))):
        raise ValueError('Depot paths must be normalized relative POSIX paths')
    if PurePosixPath(trimmed).as_posix() != trimmed:
        raise ValueError('Invalid depot path')
    return value


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', value):
        raise ValueError('Invalid file-project identifier')
    return value


def integer(value, low=0, high=None):
    if isinstance(value, bool) or not isinstance(value, int) or value < low or (high is not None and value > high):
        raise ValueError('Invalid integer or chunk limit')
    return value


class UploadUndo:
    """Only a private append is reversible; committed immutable blobs are never overwritten."""
    rollback_before_database = True

    def __init__(self, path, length=None):
        self.path = path
        self.length = length

    def start(self):
        self.existed = self.path.exists()
        if self.length is None:
            self.length = self.path.stat().st_size if self.existed else 0

    def commit(self):
        pass

    def rollback(self):
        # A lost COMMIT reply can mean committed metadata; retain bytes for offset-based recovery.
        if Transaction.get().commit_started:
            return
        if not self.existed:
            self.path.unlink(missing_ok=True)
        elif self.path.exists():
            with self.path.open('r+b') as stream:
                stream.truncate(self.length)


from .file_submit import FileSubmitMixin, can_read_change


class FileProjectCmd(FileStreamMixin, FileSubmitMixin, FileRevertMixin, FileReadMixin, FileBulkMixin, FileRevisionMixin, FileSelectionMixin, FileGcMixin, FileTransferMixin, FileStorageMixin, FileWorkspaceMixin, FileMergeMixin, FileChangeMixin, Command):
    @classmethod
    def is_undoable(cls):
        return False

    def execute(self):
        project = Project.get()
        if project.get_value('type') != MODE:
            raise ValueError('This API requires a file_project project; classic projects are unchanged')
        self.project = project.get_code()
        self.owner = Environment.get_user_name()
        security = Environment.get_security()
        if not security.is_logged_in() or security.get_user_name() != _context.get().login:
            raise SecurityException('Authenticated file-project access required')
        if not security.check_access('project', [{'code': '*'}, {'code': self.project}], 'allow', default='deny'):
            raise SecurityException('Project access denied')
        action = self.kwargs.get('action')
        if action not in FILE_ACTIONS | STORAGE_ACTIONS | TRANSFER_ACTIONS | GC_ACTIONS | BULK_ACTIONS | READ_ACTIONS:
            raise ValueError('Unknown file-project action')
        self.pages = PageStore()
        self.catalog = FileCatalog(self.pages.load, self.pages.save)
        with access(self.project):
            if action == 'submit_task_status':
                # Task workflow triggers retain their normal native command lifecycle.
                self.info = self.submit_task_status()
                return
            Transaction.get().require_single_database(project.get_project_db_resource())
            from pyasm.common import Container
            previous = Container.get('FileProject:read-records')
            if action in READ_ACTIONS and not self.kwargs.get('file_revision'):
                Container.put('FileProject:read-records', {})
            try:
                self.storage_guard('revision_snapshot' if action in ('list','browse','read','transfer') and revision_spec(self.kwargs).get('file_revision') else action)
                self.info = getattr(self, action)()
                self.storage_flush()
                for _ in range(8):
                    root_revision = Container.get('FileGC:root-revision')
                    self.pages.flush()
                    if root_revision == Container.get('FileGC:root-revision'):
                        break
                    if self.storage_data is not None:
                        # Page callbacks can publish roots after the first barrier flush.
                        self.storage_record = self.lock('chunk', 'storage-policy')
                        self.storage_data = self.storage_record.get_json_value('data')
                        from copy import deepcopy
                        self.storage_original = deepcopy(self.storage_data)
                        self.storage_seen = Container.get('FileProject:storage-write-revision')
                        self.storage_flush()
                else:
                    raise ValueError('File-project callbacks did not finish publishing catalog roots')
            finally:
                Container.put('FileProject:read-records', previous)

    def admin_search(self):
        """Read managed tables through the native file API, never generic writes."""
        from pyasm.security.security import _require_admin
        from pyasm.biz.file_project import TABLES
        from pyasm.search import SearchType
        _require_admin()
        payload = dict(self.kwargs['payload'])
        kind = SearchType.breakup_search_type(payload['search_type'])
        if (payload['search_type'].split('?', 1)[0] not in {'file_project/' + name for name in TABLES}
                or kind.get('project') not in (None, '', self.project)):
            raise ValueError('Select a managed Search Type in the current file project')
        operation = self.kwargs.get('operation', 'query')
        if operation == 'cells':
            from tactic_stream.server.table_cells import read_table_cells
            return read_table_cells(payload['search_type'], payload.get('view', 'table'), payload.get('search_keys'))
        if operation == 'result_items':
            from tactic_stream.server.result_items import read_result_items
            return read_result_items(payload['search_type'], payload.get('search_keys'), payload.get('branch'),
                                     payload.get('offset', 0), payload.get('limit', 50))
        if operation not in ('query', 'settings', 'read', 'suggestions'):
            raise ValueError('Unknown managed table read operation')
        if operation == 'query' and any(row.get('column') == '_expression' for row in payload.get('records', [])):
            raise ValueError('Managed table searches require column filters')
        from tactic_stream.server.search_configuration import search_configuration_request
        return search_configuration_request(operation, payload)

    def capabilities(self):
        from pyasm.common import Config
        from pyasm.search import SearchType
        revision_index=find('chunk','revision-index',False)
        revision_ready=SearchType.column_exists('file_project/change','submitted_at') and (revision_index is None or revision_index.get_json_value('data').get('complete'))
        services = re.split(r'[|,]', Config.get_value('services', 'enable', default='tactic'))
        return {'mode': MODE, 'schema_version': 1, 'revision_index_ready':bool(revision_ready), 'edit_chunk_limit': CHUNK_LIMIT,
                'transfer_chunk_bytes': TRANSFER_LIMIT, 'catalog_page_size': FileCatalog.PAGE_SIZE,
                'atomic_submit': True, 'checkout_modes': ['ordinary', 'exclusive'],
                'changelists': ['update', 'remove', 'move', 'shelve', 'unshelve', 'rebase', 'resolve'],
                'integration_chunk_limit': CHUNK_LIMIT, 'workspace_mappings': True, 'reconcile': True,
                'cross_stream_merge': True, 'repository_bindings': True, 'bulk_transfers': True, 'bulk_mutations': True,
                'stream_types': list(STREAM_TYPES), 'stream_editor': True,
                'transfer_block_bytes': 64 * 1024 * 1024, 'background_verification': True,
                'administrator':Environment.get_security().is_admin(),
                'repositories':sorted(name for name in dict(Environment.get_asset_dirs()) | {'default': ''}
                                      if name != 'plugins') if Environment.get_security().is_admin() else [],
                'files_service_configured': 'files' in {value.strip() for value in services}}

    def permission(self, depot, operation):
        if not self.has_permission(depot, operation):
            raise SecurityException('Depot %s access denied: %s' % (operation, depot))

    def has_permission(self, depot: str, operation: str) -> bool:
        security = Environment.get_security()
        level = {'read': 'view', 'write': 'edit'}[operation]
        return security.check_access('file_depot', [{'project': self.project, 'code': depot},
                {'project': self.project, 'code': '*'}], level, default='deny')

    def lock(self, kind, code):
        item = find(kind, code)
        item.get_sql().lock_sobject(item, timeout=5000)
        return find(kind, code)

    def stream(self, code=None, operation='read', lock=False):
        code = identifier(code or self.kwargs.get('stream'))
        item = self.lock('stream', code) if lock else find('stream', code)
        data = item.get_json_value('data')
        self.permission(data['depot'], operation)
        return item, data

    def change(self, lock=True, pending=True):
        code = self.change_reference(self.kwargs.get('change'))
        self.kwargs['change'] = code
        item = self.lock('change', code) if lock else find('change', code)
        data = item.get_json_value('data')
        if data['state'] == 'expired':
            raise ValueError('Changelist expired by retention')
        self.stream(data['stream'], 'write' if lock else 'read')
        if data['owner'] != self.owner:
            raise SecurityException('Changelist belongs to another user')
        if pending and data['state'] != 'pending':
            raise ValueError('Changelist is no longer pending')
        return item, data

    @staticmethod
    def change_reference(value):
        if isinstance(value, str) and value.startswith('#'):
            if not re.fullmatch(r'#[1-9][0-9]{0,18}', value) or int(value[1:]) > 2**63 - 1:
                raise ValueError('Invalid changelist number')
            search = Search('file_project/change')
            search.add_filter('id', int(value[1:]))
            item = search.get_sobject()
            if item is None:
                raise ValueError('Unknown changelist number')
            return item.get_code()
        return identifier(value)

    @staticmethod
    def result(item):
        result = {'code': item.get_code(), **item.get_json_value('data')}
        if item.get_base_search_type() == 'file_project/change':
            if not can_read_change(result):
                raise SecurityException('Restricted changelist')
            result['number'] = item.get_id()
        return result

    def create_depot(self):
        from pyasm.security.security import _require_admin
        _require_admin()
        code = identifier(self.kwargs.get('code'))
        if find('depot', code, False):
            raise ValueError('Depot already exists')
        title = self.kwargs.get('title')
        if title is None or title == '':
            title = code
        if not isinstance(title, str) or len(title.encode()) > 1024:
            raise ValueError('Invalid depot title')
        return self.depot_status_result(create('depot', {'title': title,
            'case_sensitive': True, 'revision': 0, 'storage': self.depot_storage(self.kwargs.get('repository'))}, code))

    def create_stream(self):
        code = identifier(self.kwargs.get('code'))
        depot = identifier(self.kwargs.get('depot'))
        find('depot', depot)
        self.permission(depot, 'write')
        self.lock('depot', depot)
        if find('stream', code, False):
            raise ValueError('Stream already exists')
        spec = self.validate_stream_spec(code, depot)
        parent = spec['parent']
        root = self.catalog.empty()
        source = None
        if parent:
            _, source = self.stream(parent)
            if source['depot'] != depot:
                raise ValueError('Parent must belong to the same depot')
            root = source['root']
        self.pages.flush()
        baseline = create('change', {'owner': self.owner, 'workspace': None, 'stream': code,
            'state': 'submitted', 'base_root': root, 'base_revision': 0, 'root': root,
            'edit_revision': 0, 'submitted_revision': 0, 'submitted_at': time_ns()//1000, 'description': 'Stream baseline'})
        return self.stream_spec(create('stream', {**spec, 'depot': depot, 'parent': parent, 'branch_parent': parent, 'root': root,
            'owner': self.owner, 'spec_revision': 0, 'spec_updated_at': time_ns()//1000,
            'revision': 0, 'head_change': baseline.get_code(), 'baseline_change': baseline.get_code(),
            'fork_root': root, 'parent_change': source['head_change'] if source else None,
            'merge_bases_root': self.catalog.empty()}, code))

    def create_workspace(self):
        code = identifier(self.kwargs.get('code'))
        _, stream = self.stream()
        root = self.kwargs.get('local_root')
        if not isinstance(root, str) or not root or len(root) > 2048:
            raise ValueError('Workspace local_root required (metadata, never a server filesystem path)')
        if find('workspace', code, False):
            raise ValueError('Workspace already exists')
        data = {'owner': self.owner, 'stream': self.kwargs['stream'], 'depot': stream['depot'],
                'local_root': root, 'have_root': self.catalog.empty(), 'active_sync': None,
                'pending_root': self.catalog.empty(), 'view_revision': 0}
        if 'mappings' in self.kwargs:
            sensitive = self.kwargs.get('case_sensitive', True)
            data.update(mappings=self.validate_view(self.kwargs['mappings'], sensitive, self.kwargs['stream']), case_sensitive=sensitive)
        self.pages.flush()
        return self.result(create('workspace', data, code))

    def create_change(self):
        workspace = self.lock('workspace', identifier(self.kwargs.get('workspace')))
        ws = workspace.get_json_value('data')
        if ws['owner'] != self.owner:
            raise SecurityException('Workspace belongs to another user')
        code = identifier(self.kwargs.get('stream', ws['stream']))
        view = self.view(ws)
        if not any(rule['stream'] == code and not rule['exclude'] and rule['writable'] for rule in view.rules):
            raise SecurityException('Stream is not writable in this workspace')
        _, stream = self.stream(code, 'write')
        receipt = self.receipt(workspace.get_code(), 'create_change') if self.kwargs.get('request_id') else None
        if receipt and receipt[2] is not None:
            return receipt[2]
        change = create('change', {'owner': self.owner, 'workspace': workspace.get_code(),
            'stream': code, 'state': 'pending', 'base_root': stream['root'],
            'base_revision': stream['revision'], 'root': stream['root'], 'edit_revision': 0,
            'work_root': self.catalog.empty(),
            'workspace_view': ws.get('mappings'), 'case_sensitive': ws.get('case_sensitive', True),
            'description': str(self.kwargs.get('description') or '')[:4096]})
        if 'pending_root' in ws:
            ws['pending_root'] = self.catalog.update(ws['pending_root'], [{'path': change.get_code(), 'size': 0}])
            self.save_change(workspace, ws)
        result = self.result(change)
        return self.remember(receipt[0], receipt[1], result) if receipt else result

    def blob_path(self, code, data=None):
        data = data if data is not None else find('blob', code).get_json_value('data')
        path = blob_file_path(self.project, code, _context.get().store.data_dir, data.get('storage_root'))
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def owned_blob(self, change, lock=True):
        code = identifier(self.kwargs.get('blob'))
        item = self.lock('blob', code) if lock else find('blob', code)
        data = item.get_json_value('data')
        if data['change'] != change.get_code() or data['owner'] != self.owner:
            raise SecurityException('Blob belongs to another changelist')
        return item, data

    def upload_begin(self):
        change, data = self.change()
        _, stream = self.stream(data['stream'], 'write')
        storage = find('depot', stream['depot']).get_json_value('data').get('storage')
        location = {'storage_root': storage['root']} if storage else {}
        if 'files' in self.kwargs:
            files = self.kwargs['files']
            if not isinstance(files, list) or not 1 <= len(files) <= CHUNK_LIMIT:
                raise ValueError('Upload descriptors require a bounded chunk')
            if any(not isinstance(item, dict) or set(item) != {'path', 'size'} for item in files):
                raise ValueError('Invalid upload descriptor')
            files = [{'path': logical_path(item['path']), 'size': integer(item['size'], high=2**63 - 1)} for item in files]
            request = identifier(self.kwargs.get('request_id'))
            key = sha256(('upload\0' + change.get_code() + '\0' + request).encode('utf-8')).hexdigest()
            digest = sha256(encode(files).encode('utf-8')).hexdigest()
            receipt = find('chunk', key, False)
            if receipt:
                value = receipt.get_json_value('data')
                if value['digest'] != digest:
                    raise ValueError('Upload request identifier reused')
                return value['result']
            rows = [(uuid.uuid4().hex, {'owner': self.owner, 'change': change.get_code(), **item,
                    'received': 0, 'state': 'uploading', 'sha256': None, **location}) for item in files]
            self.reserve_storage([item['size'] for item in files])
            save_batch('blob', rows)
            result = {'change': change.get_code(), 'items': [{'blob': code, 'path': value['path'], 'size': value['size']} for code, value in rows]}
            create('chunk', {'digest': digest, 'result': result}, key)
            return result
        size = integer(self.kwargs.get('size'), high=2**63 - 1)
        self.reserve_storage([size])
        return self.result(create('blob', {'owner': self.owner, 'change': change.get_code(),
            'size': size, 'received': 0, 'state': 'uploading', 'sha256': None, **location}))

    def upload_chunk(self):
        change, _ = self.change()
        item, data = self.owned_blob(change)
        offset = integer(self.kwargs.get('offset'))
        payload = self.kwargs.get('data')
        if not isinstance(payload, (str, bytes)) or len(payload) > (TRANSFER_LIMIT + 2) // 3 * 4:
            raise ValueError('Transfer chunk exceeds limit')
        raw = base64.b64decode(payload, validate=True) if isinstance(payload, str) else payload
        if not raw or len(raw) > TRANSFER_LIMIT or offset + len(raw) > data['size']:
            raise ValueError('Invalid upload chunk size')
        path = self.blob_path(item.get_code())
        digest = sha256(raw).hexdigest()
        if offset < data['received']:
            with path.open('rb') as stream:
                stream.seek(offset)
                matches = stream.read(len(raw)) == raw
            if matches and offset + len(raw) <= data['received']:
                return {'blob': item.get_code(), 'received': data['received'], 'sha256': digest}
            raise ValueError('Conflicting upload retry')
        if data['state'] != 'uploading' or offset != data['received']:
            raise ValueError('Unexpected upload offset or completed blob')
        if offset and (not path.exists() or path.stat().st_size < offset):
            raise ValueError('Committed upload prefix is missing or truncated')
        Transaction.get().register(UploadUndo(path, offset))
        with path.open('r+b' if path.exists() else 'w+b') as stream:
            # Recover an uncommitted tail after process death using the committed offset.
            stream.truncate(offset)
            stream.seek(offset)
            stream.write(raw)
            stream.flush()
            import os
            os.fsync(stream.fileno())
        data['received'] += len(raw)
        save(item, data)
        return {'blob': item.get_code(), 'received': data['received'], 'sha256': digest}

    def upload_batch(self):
        change, _ = self.change()
        items = self.kwargs.get('items')
        if not isinstance(items, list) or not 1 <= len(items) <= CHUNK_LIMIT:
            raise ValueError('Upload batch requires bounded items')
        decoded, total = [], 0
        for item in items:
            if not isinstance(item, dict) or set(item) != {'blob', 'data'}:
                raise ValueError('Invalid upload batch item')
            code, payload = identifier(item['blob']), item['data']
            if not isinstance(payload, str) or len(payload) > (TRANSFER_LIMIT + 2) // 3 * 4:
                raise ValueError('Upload batch exceeds limit')
            raw = base64.b64decode(payload, validate=True)
            total += len(raw)
            if total > TRANSFER_LIMIT:
                raise ValueError('Upload batch exceeds limit')
            decoded.append((code, raw))
        if len({code for code, _ in decoded}) != len(decoded):
            raise ValueError('Duplicate upload blobs')
        search = Search('file_project/blob')
        search.add_filters('code', [code for code, _ in decoded])
        blobs = {item.get_code(): item for item in search.get_sobjects()}
        rows, results = [], []
        for code, raw in decoded:
            item = blobs.get(code)
            if not item:
                raise ValueError('Unknown upload blob')
            data = item.get_json_value('data')
            if data['owner'] != self.owner or data['change'] != change.get_code():
                raise SecurityException('Upload belongs to another changelist')
            digest = sha256(raw).hexdigest()
            if data['size'] != len(raw):
                raise ValueError('Batch accepts complete small files; use ranged chunks for large files')
            if data['state'] == 'ready':
                if data['sha256'] != digest:
                    raise ValueError('Conflicting upload retry')
            else:
                if data['received']:
                    raise ValueError('Cannot replace a partially uploaded blob in a small-file batch')
                path = self.blob_path(code)
                Transaction.get().register(UploadUndo(path, 0))
                with path.open('wb') as stream:
                    stream.write(raw)
                    stream.flush()
                    import os
                    os.fsync(stream.fileno())
                data.update(state='ready', received=len(raw), sha256=digest)
                item.set_json_value('data', data)
                rows.append(item)
            results.append({'blob': code, 'size': len(raw), 'sha256': digest})
        commit_records(rows)
        return {'items': results}

    def upload_finish(self):
        change, change_data = self.change(lock=False)
        self.stream(change_data['stream'], 'write')
        item, data = self.owned_blob(change, lock=False)
        expected = self.kwargs.get('sha256')
        if expected is not None:
            if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', expected):
                raise ValueError('Invalid SHA-256 checksum')
            expected = expected.lower()
        if data['state'] == 'ready':
            if expected and expected != data['sha256']:
                raise ValueError('Upload checksum mismatch')
            return self.result(item)
        if data['received'] != data['size']:
            raise ValueError('Upload is incomplete')
        path = self.blob_path(item.get_code(), data)
        digest = sha256()
        # A TB hash must not hold a SQLite writer or a changelist row lock.
        if data['size']:
            if path.stat().st_size != data['size']:
                raise ValueError('Stored upload length does not match committed size')
            with path.open('rb') as stream:
                for part in iter(lambda: stream.read(TRANSFER_LIMIT), b''):
                    digest.update(part)
        checksum = digest.hexdigest()
        if expected and checksum != expected:
            raise ValueError('Upload checksum mismatch')
        change, _ = self.change()
        item, current = self.owned_blob(change)
        if current['state'] == 'ready':
            if current['sha256'] != checksum:
                raise ValueError('Upload changed during checksum verification')
            return self.result(item)
        if any(current[field] != data[field] for field in ('size', 'received', 'state')):
            raise ValueError('Upload changed during checksum verification')
        if data['size'] == 0 and not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            Transaction.get().register(UploadUndo(path))
            path.touch()
        if path.stat().st_size != data['size']:
            raise ValueError('Stored upload length does not match committed size')
        data.update(state='ready', sha256=checksum)
        save(item, data)
        return self.result(item)

    def uploads(self):
        change, _ = self.change(lock=False, pending=False)
        search = Search('file_project/blob')
        search.add_filter('login', self.owner)
        search.add_filter('change_code', change.get_code())
        search.add_order_by('code')
        if self.kwargs.get('after'):
            search.add_filter('code', identifier(self.kwargs['after']), op='>')
        limit = integer(self.kwargs.get('limit', CHUNK_LIMIT), 1, CHUNK_LIMIT)
        search.set_limit(limit + 1)
        items = search.get_sobjects()
        more, items = len(items) > limit, items[:limit]
        return {'items': [self.result(item) for item in items], 'after': items[-1].get_code() if more else None}

    def checkout_active(self,data,path):
        if data['state'] != 'pending':
            return False
        if 'work_root' not in data or self.catalog.get(data['work_root'],path):
            return True
        acquired=data.get('integration',{}).get('acquired_root')
        return bool(acquired and self.catalog.get(acquired,path))

    def checkout_paths(self, change, paths, mode):
        if mode not in ('ordinary', 'exclusive'):
            raise ValueError('Unknown checkout mode')
        code = change.get_code()
        data = change.get_json_value('data')
        self.check_workspace_paths(data, paths)
        keys = [sha256((data['stream'] + '\0' + path).encode('utf-8')).hexdigest() for path in paths]
        search = Search('file_project/checkout')
        search.add_filters('code', keys)
        existing = {item.get_code(): item for item in search.get_sobjects()}
        fresh, updated, states, modes = [], [], {}, {}
        for path, key in zip(paths, keys):
            item = existing.get(key)
            opened = item.get_json_value('data') if item else {'stream': data['stream'], 'path': path, 'holders': []}
            holders = []
            for holder in opened['holders']:
                if holder['change'] not in states:
                    states[holder['change']] = find('change', holder['change']).get_json_value('data')
                held = states[holder['change']]
                if self.checkout_active(held,path):
                    holders.append(holder)
            own = next((holder for holder in holders if holder['change'] == code), None)
            others = [holder for holder in holders if holder['change'] != code]
            if others and (mode == 'exclusive' or any(holder['mode'] == 'exclusive' for holder in others)):
                raise ValueError('Exclusive checkout conflict: ' + path)
            if own and own['mode'] == 'exclusive':
                mode_for_path = 'exclusive'
            else:
                mode_for_path = mode
            if len(others) >= 128:
                raise ValueError('Too many concurrent checkouts for one path')
            opened['holders'] = others + [{'change': code, 'owner': self.owner, 'workspace':data.get('workspace'), 'mode': mode_for_path}]
            modes[path] = mode_for_path
            if item:
                if opened != item.get_json_value('data'):
                    item.set_json_value('data', opened)
                    updated.append(item)
            else:
                fresh.append((key, opened))
        commit_records(updated)
        save_batch('checkout', fresh)
        return modes

    def checkout(self):
        # All commands lock stream before change, including new checkout rows.
        probe, data = self.change(lock=False)
        self.stream(data['stream'], 'write', lock=True)
        change, data = self.change()
        receipt = self.receipt(change.get_code(), 'checkout') if 'request_id' in self.kwargs else None
        if receipt and receipt[2] is not None:
            return receipt[2]
        self.editable(data)
        if 'edit_revision' in self.kwargs:
            self.revision(data)
        original = data['work_root']
        count = 0
        for paths in self.checkout_chunks(data):
            modes = self.checkout_paths(change, paths, self.kwargs.get('mode', 'ordinary'))
            self.work_entries(data, paths, modes)
            count += len(paths)
        if not count:
            raise ValueError('Selected folders contain no mapped files at this changelist base; rebase to current Head if needed')
        if data['work_root'] != original:
            data['edit_revision'] += 1
        self.pages.flush()
        save(change, data)
        result = {'change': change.get_code(), 'paths': count, 'mode': self.kwargs.get('mode', 'ordinary'),
                  'edit_revision': data['edit_revision']}
        return self.remember(receipt[0], receipt[1], result) if receipt else result

    def lock_holders(self, groups):
        """One checkout read for all authorized streams in a file-state batch."""
        from pyasm.common import Container
        from pyasm.biz.file_project import cache_read_records
        keys = {sha256((stream+'\0'+path).encode()).hexdigest(): (stream,path)
                for stream,paths in groups.items() for path in paths}
        if not keys:
            return {}
        search = Search('file_project/checkout')
        search.add_filters('code', list(keys))
        rows = search.get_sobjects()
        codes = {holder['change'] for row in rows for holder in row.get_json_value('data')['holders']}
        cached = Container.get('FileProject:read-records') or {}
        opened = [cached[('change', code)] for code in codes if cached.get(('change', code)) is not None]
        missing = list(codes - {row.get_code() for row in opened})
        for offset in range(0,len(missing),1000):
            changes = Search('file_project/change')
            changes.add_filters('code', missing[offset:offset+1000])
            opened.extend(changes.get_sobjects())
        cache_read_records('change', opened)
        states = {row.get_code(): row.get_json_value('data') for row in opened}
        result = {}
        for row in rows:
            data = row.get_json_value('data')
            holders = []
            for holder in data['holders']:
                held = states[holder['change']]
                if self.checkout_active(held,data['path']):
                    holders.append({**holder,'workspace':held.get('workspace')})
            result[keys[row.get_code()]] = holders
        return result

    def locks(self):
        """Read only the requested page's current holders; never enumerate all checkouts."""
        stream, _ = self.stream()
        holders = self.lock_holders({stream.get_code():self.paths()})
        return {'items':[{'path':path,'holders':values} for (_,path),values in holders.items() if values]}

    def edit(self):
        _, probe = self.change(lock=False)
        self.stream(probe['stream'], 'write', lock=True)
        change, data = self.change()
        chunk = identifier(self.kwargs.get('chunk'))
        operations = self.kwargs.get('operations')
        if not isinstance(operations, list) or not 1 <= len(operations) <= CHUNK_LIMIT or len(encode(operations).encode('utf-8')) > 2 * 1024 * 1024:
            raise ValueError('Edit requires a bounded operations chunk')
        if any(not isinstance(op, dict) or set(op) - {'path', 'blob', 'delete'} for op in operations):
            raise ValueError('Invalid edit operation')
        if any(('delete' in op and not isinstance(op['delete'], bool)) or
               (op.get('delete') and 'blob' in op) for op in operations):
            raise ValueError('Deletion requires a boolean flag and no blob')
        revision = integer(self.kwargs.get('edit_revision'))
        digest = sha256(encode({'operations': operations, 'edit_revision': revision}).encode('utf-8')).hexdigest()
        key = sha256((change.get_code() + '\0' + chunk).encode('utf-8')).hexdigest()
        receipt = find('chunk', key, False)
        if receipt:
            saved = receipt.get_json_value('data')
            if saved['digest'] != digest:
                raise ValueError('Chunk identifier reused with different data')
            return saved['result']
        if revision != data['edit_revision']:
            raise ValueError('Changelist edit revision conflict')
        self.editable(data)
        paths = [logical_path(op.get('path')) for op in operations]
        if len(set(paths)) != len(paths):
            raise ValueError('Duplicate paths in one chunk')
        modes = self.checkout_paths(change, paths, 'ordinary')
        blobs = [identifier(op.get('blob')) for op in operations if not op.get('delete')]
        blob_search = Search('file_project/blob')
        blob_search.add_filters('code', list(set(blobs)))
        ready = {item.get_code(): item.get_json_value('data') for item in blob_search.get_sobjects()} if blobs else {}
        versions, edits = [], []
        for op, path in zip(operations, paths):
            current = self.catalog.get(data['root'], path)
            previous = self.catalog.get(data['base_root'], path)
            if current and current.get('moved_to') and not op.get('delete'):
                raise ValueError('Edit the rename destination; revert the paired rename to restore its source: ' + path)
            if op.get('delete'):
                if not current or current.get('deleted'):
                    raise ValueError('Cannot delete a missing file: ' + path)
                blob = {'size': 0, 'sha256': None}
            else:
                blob = ready.get(op['blob'])
                opened = self.catalog.get(data['work_root'], path)
                attached = opened and opened['file'] and opened['file'].get('blob') == op['blob']
                if not blob or blob['state'] != 'ready' or (not attached and (blob['change'] != change.get_code() or blob['owner'] != self.owner)):
                    raise SecurityException('Edit requires a completed upload belonging to this changelist')
            version = uuid.uuid4().hex
            entry = {'path': path, 'blob': None if op.get('delete') else op['blob'], 'size': blob['size'], 'sha256': blob['sha256'],
                     'version': version, 'number': previous['number'] + 1 if previous else 1}
            if op.get('delete'):
                entry['deleted'] = True
            for field in ('integrated_from','moved_from','moved_to'):
                if current and current.get(field):
                    entry[field]=current[field]
            if entry.get('moved_from'):
                previous=self.catalog.get(data['base_root'],entry['moved_from'])
            versions.append((version, {**entry, 'previous': previous['version'] if previous else None,
                                      'change': change.get_code(), 'stream': data['stream']}))
            edits.append(entry)
        save_batch('version', versions)
        data['root'] = self.catalog.update(data['root'], edits)
        self.work_entries(data, paths, modes, {entry['path']: entry for entry in edits})
        self.pages.flush()
        data['edit_revision'] += 1
        data.pop('merge_sources', None)
        save(change, data)
        result = {'change': change.get_code(), 'edit_revision': data['edit_revision'], **self.catalog.stats(data['root'])}
        create('chunk', {'digest': digest, 'result': result}, key)
        return result

    def submit(self):
        _, probe = self.change(lock=False, pending=False)
        stream, head = self.stream(probe['stream'], 'write', lock=True)
        change, data = self.change(pending=False)
        if data['state'] == 'submitted':
            return {'change': change.get_code(), 'revision': data['submitted_revision'], 'state': 'submitted'}
        if data['state'] != 'pending':
            raise ValueError('Changelist is reverted')
        if 'edit_revision' in self.kwargs:
            self.revision(data)
        self.editable(data)
        if data.get('integration') or data.get('indexing'):
            raise ValueError('Finish or cancel changelist integration before submit')
        if head['revision'] != data['base_revision'] or head['root'] != data['base_root']:
            raise ValueError('Stream head changed; resolve/rebase required before submit')
        settings = self.submit_settings(data)
        remainder, reopen = None, False
        if 'submit_options' in self.kwargs:
            data, remainder, reopen = self.submit_options(change, data)
        data.update(settings)
        waiting = self.catalog.waiting_uploads(data['work_root'])
        if waiting is None:
            raise ValueError('Index pending metadata with index_change before submit')
        if waiting:
            raise ValueError('Upload or remove newly opened files before submit: ' + str(waiting))
        head.update(root=data['root'], revision=head['revision'] + 1, head_change=change.get_code())
        if data.get('merge_sources'):
            root = head.get('merge_bases_root') or self.catalog.empty()
            head['merge_bases_root'] = self.catalog.update(root, [{'path': item['stream'], 'size': 0, **item}
                                                               for item in data['merge_sources']])
            self.pages.flush()
        save(stream, head)
        data.update(state='submitted', submitted_revision=head['revision'], submitted_at=time_ns()//1000)
        save(change, data)
        self.close_workspace_change(change, data)
        pending = self.finish_submit_options(data, head, remainder, reopen)
        return {'change': change.get_code(), 'revision': head['revision'], 'state': 'submitted', 'pending_change': pending, **self.catalog.stats(head['root'])}

    def revert(self):
        return self.revert_change()

    def status(self):
        change, data = self.change(lock=False, pending=False)
        return {**self.result(change), **self.catalog.stats(data['root']),
                'depot_writable':self.has_permission(self.stream(data['stream'])[1]['depot'], 'write')}

    def published_root(self):
        if revision_spec(self.kwargs):
            selected=self.revision_snapshot()
            return selected['root'], selected['published_change']
        if self.kwargs.get('shelf'):
            item, data = self.shelf()
            if self.kwargs.get('stream') and self.kwargs['stream'] != data['stream']:
                raise ValueError('Shelf belongs to a different stream')
            return data['root'], None
        if self.kwargs.get('change'):
            data = self.inspect_change()
            item = find('change', data['code'])
            if self.kwargs.get('stream') and self.kwargs['stream'] != data['stream']:
                raise ValueError('Changelist belongs to a different stream')
            return data['root'], item.get_code() if data['state'] == 'submitted' else None
        _, stream = self.stream()
        published = self.kwargs.get('published_change')
        if published:
            item = find('change', identifier(published))
            data = item.get_json_value('data')
            if data['stream'] != self.kwargs['stream'] or data['state'] != 'submitted':
                raise SecurityException('Catalog cursor requires a submitted changelist in this stream')
            return data['root'], item.get_code()
        return stream['root'], stream['head_change']

    def list(self):
        root, published = self.published_root()
        prefix = logical_path(self.kwargs.get('prefix', ''), prefix=True)
        after = self.kwargs.get('after', '')
        if after:
            logical_path(after)
        limit = integer(self.kwargs.get('limit', CHUNK_LIMIT), 1, CHUNK_LIMIT)
        items = list(islice(self.catalog.entries(root, after, prefix), limit + 1))
        more = len(items) > limit
        items = items[:limit]
        return {'items': items, 'published_change': published, 'after': items[-1]['path'] if more else None,
                **self.catalog.stats(root)}

    def browse(self):
        root, published = self.published_root()
        directory = logical_path(self.kwargs.get('directory', ''), prefix=True)
        if directory and not directory.endswith('/'):
            raise ValueError('Directory paths must end with /')
        after = logical_path(self.kwargs.get('after', ''), prefix=True)
        if after and (not after.startswith(directory) or '/' in after[len(directory):].rstrip('/')):
            raise ValueError('Directory cursor must be an immediate child')
        limit = integer(self.kwargs.get('limit', 200), 1, CHUNK_LIMIT)
        items = list(islice(self.catalog.children(root, directory, after), limit + 1))
        return {'items': items[:limit], 'published_change': published,
                'after': items[limit - 1]['path'] if len(items) > limit else None}

    def changes(self):
        states = self.kwargs.get('states')
        if states is not None and (not isinstance(states, list) or not states or len(states) > 4
                or any(state not in ('pending', 'submitted', 'shelved', 'reverted') for state in states)):
            raise ValueError('Choose valid changelist states')
        scope = self.kwargs.get('scope', 'mine')
        if scope not in ('mine', 'workspace', 'stream', 'all'):
            raise ValueError('Choose a changelist visibility scope')
        # Non-owned pending work is inspectable only by administrators.
        search = Search('file_project/change')
        if scope == 'mine':
            search.add_filter('login', self.owner)
        if search.column_exists('state'):
            if states is not None or self.kwargs.get('state'):
                search.add_op('begin')
            if states is not None:
                search.add_filters('state', states)
            elif self.kwargs.get('state'):
                search.add_filter('state', self.kwargs['state'])
            if states is not None or self.kwargs.get('state'):
                search.add_filter('state', None)
                search.add_op('or')
        if scope == 'stream' and search.column_exists('stream_code'):
            search.add_filter('stream_code', identifier(self.kwargs.get('stream')))
        search.add_order_by('id desc')
        if self.kwargs.get('after'):
            cursor = find('change', identifier(self.kwargs['after']))
            search.add_filter('id', cursor.get_id(), op='<')
        limit = integer(self.kwargs.get('limit', 100), 1, CHUNK_LIMIT)
        search.set_limit(limit)
        from pyasm.biz.file_project import cache_read_records
        visible, scanned, cursor = [], 0, None
        more = False
        # ACLs and old unindexed workspace metadata are filtered without empty short pages.
        while len(visible) < limit and scanned < 1000:
            batch_limit = min(limit, 1000-scanned)
            search.set_limit(batch_limit)
            items = search.get_sobjects(redo=True)
            cache_read_records('change', items)
            more = len(items) == batch_limit
            for index, item in enumerate(items):
                scanned += 1
                cursor = item
                data = item.get_json_value('data')
                if data.get('archived_shelf'):
                    continue
                if not can_read_change(data):
                    continue
                if data['owner'] != self.owner and data['state'] not in ('submitted', 'shelved') and data.get('handoff',{}).get('recipient') != self.owner and not Environment.get_security().is_admin():
                    continue
                if self.kwargs.get('workspace') and data.get('workspace') != self.kwargs['workspace']:
                    continue
                if scope == 'stream' and data['stream'] != self.kwargs.get('stream'):
                    continue
                if states is not None and data['state'] not in states:
                    continue
                if states is None and self.kwargs.get('state') and data['state'] != self.kwargs['state']:
                    continue
                try:
                    _, stream = self.stream(data['stream'])
                except SecurityException:
                    continue
                result = self.result(item)
                result['depot_writable'] = self.has_permission(stream['depot'], 'write')
                result['editable'] = data['owner'] == self.owner and data['state'] == 'pending'
                if data.get('work_root'):
                    stats = self.catalog.stats(data['work_root'])
                    result.update(opened_files=stats['files'], opened_bytes=stats['bytes'])
                    result['file_actions']=self.catalog.action_stats(data['work_root'])
                    result['waiting_uploads']=self.catalog.waiting_uploads(data['work_root'])
                job = data.get('integration')
                if job and job.get('conflicts_root'):
                    result['conflict_files'] = self.catalog.stats(job['conflicts_root'])['files']
                visible.append(result)
                if len(visible) == limit:
                    more = more or index+1 < len(items)
                    break
            if not more or not items:
                break
            search.add_filter('id', cursor.get_id(), op='<')
        return {'items': visible, 'after': cursor.get_code() if more and cursor else None}

    def workspace_browse(self):
        _, workspace = self.workspace(lock=False)
        for stream in {rule['stream'] for rule in workspace.get('mappings', [])}:
            self.stream(stream)
        root = workspace['have_root']
        if self.kwargs.get('root') and self.kwargs['root'] != root:
            raise ValueError('Workspace Have changed; restart pagination')
        directory = logical_path(self.kwargs.get('directory', ''), prefix=True)
        if workspace.get('mappings'):
            directory = self.view(workspace).key(directory)
        after = logical_path(self.kwargs.get('after', ''), prefix=True)
        if (directory and not directory.endswith('/') or
                after and (not after.startswith(directory) or '/' in after[len(directory):].rstrip('/'))):
            raise ValueError('Choose a directory and an immediate child cursor')
        limit = integer(self.kwargs.get('limit', 200), 1, CHUNK_LIMIT)
        items = list(islice(self.catalog.children(root, directory, after), limit + 1))
        return {'items': items[:limit], 'root': root,
                'after': items[limit - 1]['path'] if len(items) > limit else None}

    def history(self):
        return self.read_history()

    def read(self):
        path = logical_path(self.kwargs.get('path'))
        entry = self.transfer()
        offset = integer(self.kwargs.get('offset', 0), high=entry['size'])
        length = integer(self.kwargs.get('length', TRANSFER_LIMIT), 1, TRANSFER_LIMIT)
        with self.blob_path(entry['blob']).open('rb') as stream:
            stream.seek(offset)
            part = stream.read(length)
        return {'path': path, 'offset': offset, 'data': base64.b64encode(part).decode('ascii'),
                'size': entry['size'], 'sha256': entry['sha256'], 'published_change': entry['published_change']}

    def transfer(self):
        path = logical_path(self.kwargs.get('path'))
        if self.kwargs.get('have'):
            if self.kwargs['have'] is not True:
                raise ValueError('have must be boolean')
            _, ws = self.workspace(lock=False)
            stream, _ = self.stream()
            view = self.view(ws)
            mapped = view.forward(stream.get_code(), path)
            entry = self.catalog.get(ws['have_root'], view.key(mapped['path'])) if mapped else None
            if entry and (entry.get('stream', ws['stream']) != stream.get_code() or entry.get('source_path', entry['path']) != path):
                raise ValueError('Have entry no longer matches this workspace mapping')
            published = entry.get('published_change') if entry else None
        elif self.kwargs.get('sync'):
            entry=self.sync_file(path)
            published=entry.get('published_change')
        elif 'conflict_side' in self.kwargs:
            _, data = self.change(lock=False)
            job = self.integration_job(data)
            side = self.kwargs['conflict_side']
            if side not in ('base', 'ours', 'theirs'):
                raise ValueError('Invalid conflict side')
            conflict = self.catalog.get(job['conflicts_root'], path)
            if not conflict:
                raise ValueError('Conflict is no longer present')
            entry, published = conflict[side], None
        else:
            root, published = self.published_root()
            entry = self.catalog.get(root, path)
        if not entry or entry.get('deleted'):
            raise FileNotFoundError(path)
        blob = find('blob', entry['blob']).get_json_value('data')
        if blob['state'] != 'ready':
            raise FileNotFoundError(path)
        return {**entry, 'published_change': published, '_storage_root': blob.get('storage_root')}

    def workspace(self, lock=True):
        code = identifier(self.kwargs.get('workspace'))
        item = self.lock('workspace', code) if lock else find('workspace', code)
        data = item.get_json_value('data')
        if data['owner'] != self.owner:
            raise SecurityException('Workspace belongs to another user')
        self.stream(data['stream'])
        return item, data

    def have(self):
        _, ws = self.workspace(lock=False)
        if self.kwargs.get('root') and self.kwargs['root'] != ws['have_root']:
            raise ValueError('Workspace Have changed; restart pagination')
        prefix = logical_path(self.kwargs.get('prefix', ''), prefix=True)
        if ws.get('mappings'):
            prefix = self.view(ws).key(prefix)
        after = self.kwargs.get('after', '')
        if after:
            logical_path(after)
        limit = integer(self.kwargs.get('limit', CHUNK_LIMIT), 1, CHUNK_LIMIT)
        items = list(islice(self.catalog.entries(ws['have_root'], after, prefix), limit + 1))
        more, items = len(items) > limit, items[:limit]
        for stream in {item.get('stream',ws['stream']) for item in items}:
            self.stream(stream)
        return {'items': items, 'root': ws['have_root'], 'after': items[-1]['path'] if more else None}

    def workspace_status(self):
        workspace, ws = self.workspace(lock=False)
        return {**self.result(workspace), **self.catalog.stats(ws['have_root'])}

    def sync_begin(self):
        workspace, ws = self.workspace()
        if revision_spec(self.kwargs) and not self.capabilities()['revision_index_ready']:
            raise ValueError('Run revision_upgrade before selecting historical revisions')
        if ws['active_sync']:
            raise ValueError('Workspace already has an active sync; finish or cancel it first')
        if not isinstance(self.kwargs.get('force',False),bool):raise ValueError('force must be boolean')
        if ws.get('mappings') or revision_spec(self.kwargs) or self.kwargs.get('force') or self.kwargs.get('source_stream') or self.kwargs.get('source_depot'):
            return self.mapped_sync_begin(workspace,{**ws,'mappings':self.view(ws).rules})
        _, stream = self.stream(ws['stream'])
        prefix = logical_path(self.kwargs.get('prefix', ''), prefix=True)
        selected = self.sync_paths()
        source=self.sync_source(ws['stream'])
        job = create('sync', {'owner': self.owner, 'workspace': workspace.get_code(), 'stream': ws['stream'],
            'root': source['root'], 'published_change': source['published_change'], 'prefix': prefix, 'paths':selected, 'force':self.kwargs.get('force',False), 'after': '',
            'state': 'running', 'files_done': 0, 'bytes_done': 0, 'ack_revision': 0})
        ws['active_sync'] = job.get_code()
        save(workspace, ws)
        return self.result(job)

    def sync_job(self, active=True):
        code = identifier(self.kwargs.get('sync'))
        probe = find('sync', code)
        data = probe.get_json_value('data')
        if data.get('state') == 'expired':
            raise ValueError('Sync expired by retention')
        if data['owner'] != self.owner:
            raise SecurityException('Sync belongs to another user')
        # Keep workspace -> sync lock order for every acknowledgement/cancellation.
        workspace = self.lock('workspace', data['workspace'])
        job = self.lock('sync', code)
        data, ws = job.get_json_value('data'), workspace.get_json_value('data')
        self.stream(data['stream'])
        if active and (data['state'] != 'running' or ws['active_sync'] != job.get_code()):
            raise ValueError('Sync is not active')
        return job, data, workspace, ws

    def sync_next(self):
        job, data, _, ws = self.sync_job()
        if data.get('mapped'):
            result = self.mapped_sync_next(job, data, ws)
            result['items'] = self.storage_entries(result['items'])
            return result
        items = self.sync_entries(data)
        planned = [{**entry, '_have': self.catalog.get(ws['have_root'], entry['path'])} for entry in items[:CHUNK_LIMIT]]
        return {'sync': job.get_code(), 'items': self.storage_entries(planned), 'more': len(items) > CHUNK_LIMIT, 'ack_revision': data['ack_revision'],
                'published_change': data['published_change'], 'stream': data['stream'],
                'files_done': data['files_done'], 'bytes_done': data['bytes_done']}

    def sync_ack(self):
        job, data, workspace, ws = self.sync_job(active=False)
        revision = integer(self.kwargs.get('ack_revision'))
        paths = self.kwargs.get('paths')
        if not isinstance(paths, list) or len(paths) > CHUNK_LIMIT:
            raise ValueError('Sync acknowledgement requires a bounded path chunk')
        paths = [logical_path(path) for path in paths]
        if revision != data['ack_revision']:
            if revision == data['ack_revision'] - 1 and sha256(encode(paths).encode('utf-8')).hexdigest() == data.get('last_ack'):
                return self.result(job)
            raise ValueError('Sync acknowledgement revision conflict')
        if data['state'] != 'running' or ws['active_sync'] != job.get_code():
            raise ValueError('Sync is not active')
        if data.get('mapped'):
            return self.mapped_sync_ack(job, data, workspace, ws, paths)
        planned = self.sync_entries(data)
        items = planned[:CHUNK_LIMIT]
        if not isinstance(paths, list) or paths != [item['path'] for item in items]:
            raise ValueError('Acknowledge the whole planned chunk after files are written locally')
        ws['have_root'] = self.catalog.update(ws['have_root'], items) if items else ws['have_root']
        data['transferred_root'] = self.catalog.update(data.get('transferred_root') or self.catalog.empty(),items)
        self.pages.flush()
        data['files_done'] += len(items)
        data['bytes_done'] += sum(item['size'] for item in items)
        data['ack_revision'] += 1
        data['last_ack'] = sha256(encode(paths).encode('utf-8')).hexdigest()
        if items:
            data['after'] = items[-1]['path']
        if len(planned) <= CHUNK_LIMIT:
            data['state'] = 'complete'
            ws['active_sync'] = None
        save(workspace, ws)
        save(job, data)
        return self.result(job)

    def sync_status(self):
        job, _, _, _ = self.sync_job(active=False)
        return self.result(job)

    def sync_cancel(self):
        job, data, workspace, ws = self.sync_job()
        data['state'], ws['active_sync'] = 'cancelled', None
        save(workspace, ws)
        save(job, data)
        return self.result(job)
