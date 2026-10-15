"""Native records for the opt-in file_project project mode."""
import json
import uuid
from contextlib import contextmanager
from hashlib import sha256

from pyasm.common import Container, Common
from pyasm.common.errors import SecurityException
from pyasm.search import Search, SearchType, SObject

MODE = 'file_project'
COMMAND = 'tactic.command.file_project_cmd.FileProjectCmd'
TABLES = ('depot', 'stream', 'workspace', 'change', 'page', 'blob', 'chunk', 'version', 'checkout', 'sync')


@contextmanager
def access(project):
    previous = Container.get('FileProject:access')
    Container.put('FileProject:access', project)
    try:
        yield
    finally:
        Container.put('FileProject:access', previous)


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


class FileProjectRecord(SObject):
    record_read = {'command': COMMAND, 'action': 'admin_search', 'admin_only': True, 'readonly': True, 'project_mode': MODE}
    # The file domain records its own immutable revisions in the same project DB.
    track_change_timestamps = False
    global_search_index = False

    def get_base_search_type(self):
        if self.full_search_type.startswith('file_project/'):
            return self.full_search_type.partition('?')[0]
        return super().get_base_search_type()

    @classmethod
    def alter_search(cls, search):
        from pyasm.biz import Project
        project = Project.get()
        if (Container.get('FileProject:access') != project.get_code() or
                search.get_db_resource()._get_connection_key() != project.get_project_db_resource()._get_connection_key()):
            raise SecurityException('File-project records require the file-project command API')

    def _check_business_write(self, access=None):
        from pyasm.biz import Project
        project = Project.get()
        if (Container.get('FileProject:access') != project.get_code() or project.get_value('type') != MODE or
                self.get_db_resource()._get_connection_key() != project.get_project_db_resource()._get_connection_key()):
            raise SecurityException('File-project writes require an opted-in project and command API')
        maintenance = Container.get('FileProject:maintenance') == project.get_code()
        if not maintenance and self.get_id() != -1 and (self.get_base_search_type() in ('file_project/page', 'file_project/version')
                and (access == 'delete' or self.update_data)):
            raise ValueError('Published catalog pages and file revisions are immutable')
        previous = self.data.get('data') or {}
        if isinstance(previous, str) and previous.startswith('zlib:'):
            previous = Common.decompress_transaction(previous)
        previous = json.loads(previous) if isinstance(previous, str) else previous
        if not maintenance and self.get_base_search_type() == 'file_project/blob' and previous.get('state') == 'ready' and (access == 'delete' or self.update_data):
            raise ValueError('Completed blobs are immutable')
        if not maintenance and self.get_base_search_type() == 'file_project/blob' and previous.get('state') in ('quarantined', 'reclaimed', 'purged') and (access == 'delete' or self.update_data):
            raise ValueError('Retired blobs are immutable')
        if not maintenance and self.get_base_search_type() == 'file_project/change' and previous.get('state') == 'shelved' and (access == 'delete' or self.update_data):
            raise ValueError('Shelved changelists are immutable')
        super()._check_business_write(access)

    def commit(self, triggers=True, log_transaction=False, cache=False, return_sql=False):
        try:
            result = super().commit(triggers, log_transaction, cache, return_sql)
            if not return_sql and self.get_base_search_type() == 'file_project/chunk' and self.get_code() == 'storage-policy':
                Container.put('FileProject:storage-write-revision', (Container.get('FileProject:storage-write-revision') or 0) + 1)
            if not return_sql and self.get_base_search_type().split('/')[-1] in ('stream', 'change', 'workspace', 'sync'):
                roots = Container.get('FileGC:changed-roots')
                if roots is None:
                    roots = {}
                    Container.put('FileGC:changed-roots', roots)
                roots[self.get_search_type(), self.get_code()] = self
                Container.put('FileGC:root-revision', (Container.get('FileGC:root-revision') or 0) + 1)
            return result
        except Exception as error:
            data=self.get_json_value('data',{})
            if data.get('path') and not getattr(error,'file_error',None):
                error.file_error={'path':data['path'],'operation':'commit','cause':str(error)}
            raise

    def _call_triggers(self, trigger_update_data, mode, output, process, parent_type, triggers):
        from pyasm.command import Trigger
        from pyasm.biz import Project
        project_code=Project.get_project_code()
        integral = triggers == 'integral' or Container.get('is_undo') is True
        # Warm/renew the native maps so added static triggers and cache invalidation still apply.
        Trigger._get_triggers({'event':mode}, integral, project_code=project_code)
        key = Trigger.TRIGGER_EVENT_KEY + (':integral' if integral else '')
        events, notices = Container.get(key), Container.get(Trigger.NOTIFICATION_EVENT_KEY)
        cached = Container.get('FileProject:trigger-events:' + key)
        if cached is None or cached[0] is not events or cached[1] is not notices:
            names = {json.loads(value)['event'] for values in (events, notices) for value in values}
            cached = (events, notices, names)
            Container.put('FileProject:trigger-events:' + key, cached)
        search_type = self.get_base_search_type()
        names = [mode, mode+'|'+search_type, 'change', 'change|'+search_type]
        for column in trigger_update_data:
            if column != 'timestamp':
                names.extend((mode+'|'+search_type+'|'+column, 'change|'+search_type+'|'+column))
        for name in names:
            if name not in cached[2]:
                continue
            keys = [{'event':name}]
            if parent_type:keys.append({'event':name,'search_type':parent_type})
            if process:keys.append({'event':name,'process':process})
            if process and parent_type:keys.append({'event':name,'process':process,'search_type':parent_type})
            called = False
            for event_key in keys:
                called = Trigger.call_by_key(event_key, self, output, integral_only=integral,
                                             project_code=project_code) or called
            if called:
                # A callback can register the next field event or clear the native maps.
                Trigger._get_triggers({'event':mode}, integral, project_code=project_code)
                events, notices = Container.get(key), Container.get(Trigger.NOTIFICATION_EVENT_KEY)
                cached = (events, notices, {json.loads(value)['event'] for values in (events, notices) for value in values})
                Container.put('FileProject:trigger-events:' + key, cached)


def find(kind, code, required=True):
    cached = Container.get('FileProject:read-records')
    key = (kind, code)
    if cached is not None and key in cached:
        item = cached[key]
        if required and item is None:
            raise ValueError('Unknown file-project %s: %s' % (kind, code))
        return item
    search = Search('file_project/' + kind)
    search.add_filter('code', code)
    item = search.get_sobject()
    if cached is not None:
        cached[key] = item
    if required and item is None:
        raise ValueError('Unknown file-project %s: %s' % (kind, code))
    return item


def cache_read_records(kind, rows):
    cached = Container.get('FileProject:read-records')
    if cached is not None:
        cached.update({(kind, row.get_code()): row for row in rows})


def create(kind, data, code=None):
    from pyasm.common import Environment
    item = SearchType.create('file_project/' + kind)
    item.set_value('code', code or uuid.uuid4().hex)
    item.set_value('login', Environment.get_user_name())
    if kind == 'blob':
        item.set_value('change_code', data['change'])
    item.set_json_value('data', data)
    stamp(item, data)
    item.commit()
    return item


def save(item, data):
    item.set_json_value('data', data)
    stamp(item, data)
    item.commit()


def stamp(item, data):
    from time import time
    if item.column_exists('created_at'):
        if item.get_id() == -1:
            item.set_value('created_at', int(time()))
        item.set_value('updated_at', int(time()))
    kind = item.get_base_search_type().split('/')[-1]
    if kind == 'change':
        item.set_value('login', data['owner'])
    if kind in ('change', 'version') and item.column_exists('stream_code'):
        item.set_value('stream_code', data['stream'])
        if kind == 'change':
            item.set_value('state', data['state'])
            item.set_value('submitted_revision', data.get('submitted_revision', -1))
            item.set_value('submitted_at', data.get('submitted_at', 0))
        else:
            item.set_value('path', data['path'])
            item.set_value('number', data['number'])
    if item.get_base_search_type() in ('file_project/sync', 'file_project/blob') and item.column_exists('state'):
        item.set_value('state', data.get('state', 'running'))
    if item.get_base_search_type() == 'file_project/sync' and item.column_exists('kind'):
        item.set_value('kind', data.get('kind', 'sync'))
        item.set_value('lease_until', data.get('lease_until', 0))
    if item.get_base_search_type() == 'file_project/blob' and item.column_exists('quarantine_until'):
        item.set_value('quarantine_until', data.get('quarantine_until', 0))


def save_batch(kind, values):
    """Native preparation, row authorization and triggers, with bounded DML."""
    for offset in range(0, len(values), 128):
        from pyasm.common import Environment
        rows = []
        for code, data in values[offset:offset + 128]:
            row = SearchType.create('file_project/' + kind)
            row.set_value('code', code)
            row.set_value('login', Environment.get_user_name())
            if kind == 'blob':
                row.set_value('change_code', data['change'])
            row.set_json_value('data', data)
            rows.append(row)
        commit_records(rows)


def commit_records(rows):
    """One bounded native table batch; preserve each row's normal hooks."""
    if len(rows) > 128:
        for offset in range(0, len(rows), 128):
            commit_records(rows[offset:offset + 128])
        return
    if rows:
        for row in rows:
            stamp(row, row.get_json_value('data'))
        kind = rows[0].get_base_search_type().split('/')[-1]
        if any(type(row) is not FileProjectRecord or row.get_base_search_type() != rows[0].get_base_search_type()
               or 'commit' in row.__dict__ for row in rows):
            for row in rows:
                row.commit()
            return
        sql = rows[0].get_sql()
        from pyasm.command import Trigger
        base = rows[0].get_base_search_type()
        # A configured callback may inspect preceding inserts, so retain sequential semantics.
        custom_trigger = any(trigger.get_value('event').split('|')[0] in ('insert', 'update', 'change') and
            (len(trigger.get_value('event').split('|')) == 1 or trigger.get_value('event').split('|')[1] == base) and
            trigger.get_value('search_type', no_exception=True) in ('', None, base)
            for trigger in Trigger.get_db_triggers())
        if not custom_trigger:
            # These framework handlers still run per row; empty handlers need no insert ordering.
            builtin_noops = {'tactic.command.FolderTrigger'}
            if all(not row.global_search_index for row in rows):
                builtin_noops.add('tactic.command.GlobalSearchTrigger')
            if all(not row.get_value('pipeline_code',no_exception=True) for row in rows):
                builtin_noops.add('tactic.command.TaskCreatorTrigger')
            custom_trigger = any(trigger.get_value('class_name') not in builtin_noops and
                trigger.get_value('event').split('|')[0] in ('insert','update','change') and
                (len(trigger.get_value('event').split('|'))==1 or trigger.get_value('event').split('|')[1]==base) and
                trigger.get_value('search_type',no_exception=True) in ('',None,base)
                for trigger in Trigger.get_static_triggers()+Trigger.get_integral_triggers())
        sequential = custom_trigger or sql.get_database_impl().has_table_triggers(sql, rows[0].get_table())
        if sequential and kind != 'page':
            for row in rows:
                row.commit()
            return
        for batch in ([row] for row in rows) if sequential else (rows,):
            prepared = []
            for row in batch:
                try:prepared.append(row._prepare_commit(True, False, False))
                except Exception as error:
                    data=row.get_json_value('data',{})
                    if data.get('path') and not getattr(error,'file_error',None):
                        error.file_error={'path':data['path'],'operation':'commit','cause':str(error)}
                    raise
            updates = [item[0] for item in prepared]
            # Independent workspaces can publish identical immutable pages concurrently.
            ids = sql.do_update_multiple(updates, batch, ignore_existing=kind == 'page')
            search = Search('file_project/' + kind)
            search.add_filters('code', [row.get_code() for row in batch])
            stored = {row.get_code(): row for row in search.get_sobjects()}
            for row, (_, inserting, row_id, triggers) in zip(batch, prepared):
                if kind == 'page' and row.get_code() not in ids:
                    if row.get_json_value('data') != stored[row.get_code()].get_json_value('data'):
                        raise ValueError('Immutable catalog page identity collision')
                    continue
                try:
                    row._finish_commit(inserting, ids[row.get_code()] if inserting else row_id, triggers, False, False,
                                       stored=stored[row.get_code()])
                except Exception as error:
                    data=row.get_json_value('data',{})
                    if data.get('path') and not getattr(error,'file_error',None):
                        error.file_error={'path':data['path'],'operation':'commit','cause':str(error)}
                    raise


def blob_file_path(project, code, data_dir, storage_root=None):
    import re
    from pathlib import Path
    if not re.fullmatch(r'[A-Za-z0-9_-]+', project) or not re.fullmatch(r'[0-9a-f]{32}', code):
        raise ValueError('Invalid private storage identity')
    if storage_root:
        root = Path(storage_root)
        if not root.is_absolute() or not root.name.endswith('.file-projects'):
            raise ValueError('Invalid private repository binding')
    else:
        root = Path(data_dir) / 'file-projects'
    return root / project / 'blobs' / code[:2] / code


class PageStore:
    def __init__(self):
        self.pending = {}

    def load(self, code):
        return self.pending[code] if code in self.pending else find('page', code).get_json_value('data')

    def save(self, data):
        code = sha256(encode(data).encode('utf-8')).hexdigest()
        self.pending[code] = data
        if len(self.pending) >= 16:
            self.flush()
        return code

    def flush(self):
        pending = self.pending.copy()
        codes = list(pending)
        existing = set()
        for offset in range(0, len(codes), 128):
            search = Search('file_project/page')
            search.add_filters('code', codes[offset:offset + 128])
            existing.update(item.get_code() for item in search.get_sobjects())
        for code in codes:
            self.pending.pop(code)
        try:
            save_batch('page', [(code, data) for code, data in pending.items() if code not in existing])
        except Exception:
            self.pending.update(pending)
            raise


def install(project):
    """Schema installation goes through the existing native schema command."""
    from pyasm.biz import Project
    from tactic.core.schema_commands import SearchTypeCreatorCmd
    from importlib.resources import files
    manifest = json.loads(files('tactic_stream').joinpath('config/file_project.json').read_text(encoding='utf-8'))
    if manifest['schema_version'] != 1 or manifest['project_mode'] != MODE or tuple(manifest['tables']) != TABLES:
        raise ValueError('Unsupported file-project template schema')
    Project.set_project(project)
    try:
        for table in TABLES:
            creator = SearchTypeCreatorCmd(database=project, namespace='file_project', schema='public',
                search_type_name=table, asset_title=table.title(), asset_description='File-project ' + table)
            creator.execute()
            registry = Search('sthpw/search_object')
            registry.add_filter('search_type', 'file_project/' + table)
            record = registry.get_sobject()
            record.set_value('class_name', 'pyasm.biz.file_project.FileProjectRecord')
            record.commit()
        sql = Project.get().get_project_db_resource().get_sql()
        sql.create_index('change', ['login', 'code'], 'file_change_owner')
        sql.add_column('blob', 'change_code', 'varchar')
        sql.create_index('blob', ['login', 'change_code', 'code'], 'file_upload_change')
        storage_schema(sql)
        revision_schema(sql)
        with access(project):
            from tactic.command.file_storage import policy_defaults
            create('chunk', policy_defaults(indexed=True), 'storage-policy')
    finally:
        Project.set_project('admin')


def storage_schema(sql, upgrade=False):
    for table in TABLES:
        for column in ('created_at', 'updated_at'):
            if column not in sql.get_column_info(table):
                sql.add_column(table, column, 'bigint')
    add_index = not upgrade or 'kind' not in sql.get_column_info('sync')
    for column, kind in (('kind', 'varchar'), ('state', 'varchar'), ('lease_until', 'bigint')):
        if column not in sql.get_column_info('sync'):
            sql.add_column('sync', column, kind)
    if 'state' not in sql.get_column_info('blob'):
        sql.add_column('blob', 'state', 'varchar')
        sql.create_index('blob', ['state', 'code'], 'file_blob_lifecycle')
    if 'quarantine_until' not in sql.get_column_info('blob'):
        sql.add_column('blob', 'quarantine_until', 'bigint')
        sql.create_index('blob', ['state', 'quarantine_until', 'code'], 'file_blob_reap')
    if add_index:
        sql.create_index('sync', ['kind', 'state', 'lease_until', 'code'], 'file_tasks_pending')


def revision_schema(sql):
    for table, fields, indexes in (
        ('change', (('stream_code','varchar'),('state','varchar'),('submitted_revision','bigint'),('submitted_at','bigint')),
         ((['stream_code','state','submitted_at','submitted_revision'],'file_change_date'),
          (['stream_code','state','submitted_revision'],'file_change_revision'))),
        ('version', (('stream_code','varchar'),('path','varchar'),('number','bigint')),
         ((['stream_code','path','number','code'],'file_revision_path'),)),
    ):
        columns=sql.get_column_info(table)
        new=any(name not in columns for name,_ in fields)
        for name,kind in fields:
            if name not in columns:sql.add_column(table,name,kind)
        if new:
            for columns,name in indexes:sql.create_index(table,columns,name)
