"""Optional bulk check-ins on the native persistent queue; no client-side naming."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

from pyasm.command import Command
from pyasm.common import Container, Environment
from pyasm.common.errors import SecurityException, UserException
from pyasm.biz import Project
from pyasm.search import Search, SearchType, DbContainer

QUEUE = 'checkin'
BATCH_QUEUE = 'checkin-batch'
JOB_COMMAND = 'tactic.command.checkin_queue_cmd.CheckinQueueJobCmd'
MAX_FILES = 10000
MAX_OPERATIONS = 2000


def identity(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
        raise ValueError('Invalid check-in batch, chunk or operation identity')
    return value


def batch_code(batch_id, project=None):
    value = [Environment.get_user_name(), project or Project.get_project_code(), identity(batch_id)]
    return 'CHECKIN_' + hashlib.sha256(json.dumps(value).encode()).hexdigest()


def staging_root(code):
    root = Path(Environment.get_tmp_dir()).resolve() / 'checkin-queue'
    path = root / code
    if not re.fullmatch(r'CHECKIN_[a-f0-9]{64}', code) or not path.resolve().is_relative_to(root.resolve()):
        raise SecurityException('Invalid check-in staging directory')
    return path


@contextmanager
def queue_lock():
    previous = Container.get('CheckinQueue:locking')
    Container.put('CheckinQueue:locking', True)
    try:
        from pyasm.search.transaction import Transaction
        from pyasm.search.search import _context
        sql = DbContainer.get(_context.get().store.get_db_resource())
        Transaction.get().register_database(sql)
        sql.lock_queue()
        yield
    finally:
        Container.put('CheckinQueue:locking', previous)


def save_queue(row):
    from pyasm.search import SObject
    previous = Container.get('CheckinQueue:writing')
    if not Environment.get_security().is_admin():
        Container.put('CheckinQueue:writing', row)
    try:
        # Upload progress is durable queue state; repository changes own the Undo journal.
        row.commit(log_transaction=False, cache=False)
    finally:
        Container.put('CheckinQueue:writing', previous)
        SObject.get_cache_dict(search_type='sthpw/queue').clear()


def new_row(code, queue, state, data, command=JOB_COMMAND):
    row = SearchType.create('sthpw/queue')
    for name, value in dict(code=code, queue=queue, state=state, command=command,
                            project_code=Project.get_project_code(), login=Environment.get_user_name(),
                            priority='9999').items():
        row.set_value(name, value)
    row.set_json_value('data', data)
    save_queue(row)
    return row


def owned_batch(code):
    search = Search('sthpw/queue')
    search.add_filter('code', code)
    search.add_filter('queue', BATCH_QUEUE)
    search.add_filter('login', Environment.get_user_name())
    row = search.get_sobject()
    if row is None:
        raise LookupError('Check-in batch is not available')
    from tactic_stream.server.navigation_links import check_project
    check_project(row.get_value('project_code'))
    return row


class _UploadedParts:
    """Temporary uploads join rollback without becoming repository undo history."""
    def __init__(self):
        self.paths = []

    def start(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        for path in self.paths:
            path.unlink(missing_ok=True)
            for directory in (path.parent, path.parent.parent):
                if directory.exists() and not any(directory.iterdir()):
                    directory.rmdir()


def record_update(data, job, *, error='', snapshot=None):
    operation_id = job.get_json_value('data')['operation_id']
    data['revision'] += 1
    event = dict(operation_id=operation_id, state=job.get_value('state'), revision=data['revision'])
    if error:
        event['error'] = error
    if snapshot:
        event['snapshot'] = {name: value for name, value in snapshot.items() if name != 'snapshot'}
        event['source_checksums'] = {record['source_path']: record['sha256']
                                    for record in job.get_json_value('data')['options']['source_files']
                                    if record.get('source_path') and record.get('sha256')}
    data['updates'][operation_id] = event


def job_updated(job, *, error=''):
    """Completion and its update join the same native transaction as the snapshot."""
    if job.get_value('command') != JOB_COMMAND:
        return
    with queue_lock():
        code = job.get_json_value('data')['batch_code']
        batch = Search.get_by_code('sthpw/queue', code)
        if batch is None:
            raise LookupError('Check-in batch is missing')
        data = batch.get_json_value('data')
        result = job.get_json_value('data').get('result') or {}
        record_update(data, job, error=error, snapshot=result.get('snapshot'))
        batch.set_json_value('data', data)
        save_queue(batch)


class SubmitCheckinChunkCmd(Command):
    def execute(self):
        from tactic.command.browser_checkin_cmd import matched_files
        from tactic_stream.server.navigation_links import check_project
        from pyasm.search import SearchKey
        check_project(Project.get_project_code())
        code = batch_code(self.kwargs.get('batch_id'))
        chunk_id = identity(self.kwargs.get('chunk_id'))
        operations = self.kwargs.get('operations', [])
        pieces = self.kwargs.get('pieces', [])
        uploads = self.kwargs.get('uploads', [])
        if not isinstance(operations, list) or len(operations) > MAX_OPERATIONS or not isinstance(pieces, list) or not 1 <= len(pieces) <= 50 or len(pieces) != len(uploads):
            raise ValueError('A check-in chunk requires at most 50 file parts')
        digest = hashlib.sha256(json.dumps([operations, pieces], sort_keys=True, ensure_ascii=False).encode())
        part_hashes = [hashlib.sha256(content) for _name, content in uploads]
        for part_hash in part_hashes:
            digest.update(part_hash.digest())
        digest = digest.hexdigest()
        from pyasm.search import Transaction
        from uuid import uuid4
        uploaded = _UploadedParts()
        Transaction.get().register(uploaded)
        prepared_parts = []
        root_dir = staging_root(code)
        try:
            for piece, (_name, content), part_hash in zip(pieces, uploads, part_hashes):
                if not isinstance(piece, dict) or set(piece) != {'operation_id', 'file_index', 'offset'}:
                    raise ValueError('Invalid check-in file part')
                sha = part_hash.hexdigest()
                root_dir.mkdir(parents=True, exist_ok=True)
                temporary = root_dir / ('.upload_' + uuid4().hex + '.part')
                with temporary.open('wb') as stream:
                    stream.write(content); stream.flush()
                prepared_parts.append((piece, content, sha, temporary))
            with queue_lock():
                search = Search('sthpw/queue'); search.add_filter('code', code)
                batch = search.get_sobject()
                if batch is None:
                    batch = new_row(code, BATCH_QUEUE, 'staging', dict(chunks={}, jobs={}, updates={}, revision=0))
                batch = owned_batch(code)
                data = batch.get_json_value('data')
                if chunk_id in data['chunks']:
                    if data['chunks'][chunk_id] != digest:
                        raise UserException('A check-in chunk identity was reused with different content')
                    return dict(batch_id=self.kwargs['batch_id'], accepted=True, duplicate=True)
                if batch.get_value('state') != 'staging':
                    raise UserException('This check-in batch no longer accepts files')
                if len(data['chunks']) >= 10000:
                    raise UserException('Check-in batch has too many chunks')
                jobs, values = {}, {}
                for operation in operations:
                    if not isinstance(operation, dict) or set(operation) != {'operation_id', 'options'}:
                        raise ValueError('Invalid queued check-in')
                    op_id = identity(operation['operation_id'])
                    options = operation['options']
                    if not isinstance(options, dict) or set(options) - {'search_key', 'context', 'process', 'description', 'source_files', 'templates', 'padding', 'repository_alias', 'keep_file_name', 'is_revision', 'version', 'explicit_filename', 'update_versionless', 'only_versionless', 'create_icon', 'versionless_mode', 'application_info'}:
                        raise ValueError('Invalid queued check-in options')
                    records = options.get('source_files')
                    matched_files(records, options.get('templates'), options.get('padding', 3), max_files=MAX_FILES)
                    if any(record.get('sha256') is not None and not re.fullmatch(r'[a-f0-9]{64}', str(record['sha256'])) for record in records):
                        raise ValueError('Invalid check-in source checksum')
                    parent = SearchKey.get_by_search_key(options.get('search_key'))
                    if parent is None or parent.get_project_code() != Project.get_project_code():
                        raise SecurityException('Check-in requires a visible object in its project')
                    parent._check_business_write('edit')
                    if op_id in data['jobs']:
                        job = Search.get_by_code('sthpw/queue', data['jobs'][op_id])
                        if job.get_json_value('data')['options'] != options:
                            raise UserException('A check-in operation identity was reused with different options')
                    else:
                        if len(data['jobs']) >= MAX_OPERATIONS:
                            raise UserException('Check-in batch has too many operations')
                        total = data.get('file_count', 0) + len(records)
                        if total > MAX_FILES:
                            raise UserException('Check-in batch has too many files; split the selection')
                        data['file_count'] = total
                        job = new_row(code + '_' + op_id, QUEUE, 'staging',
                                      dict(batch_code=code, operation_id=op_id, options=options, parts={}))
                        data['jobs'][op_id] = job.get_code()
                    jobs[op_id] = job
                    values[op_id] = job.get_json_value('data')
                for piece, content, sha, temporary in prepared_parts:
                    op_id = identity(piece['operation_id'])
                    if op_id not in data['jobs']:
                        raise ValueError('File part has no check-in operation')
                    job = jobs.get(op_id) or Search.get_by_code('sthpw/queue', data['jobs'][op_id])
                    if job.get_value('state') != 'staging':
                        raise UserException('This operation no longer accepts files')
                    if op_id not in values:
                        values[op_id] = job.get_json_value('data')
                    value = values[op_id]
                    index, offset = piece['file_index'], piece['offset']
                    records = value['options']['source_files']
                    if type(index) is not int or not 0 <= index < len(records) or type(offset) is not int or offset < 0 or offset + len(content) > records[index]['size'] or not content and records[index]['size']:
                        raise ValueError('Invalid check-in file part range')
                    parts = value['parts'].setdefault(str(index), {})
                    if str(offset) in parts:
                        raise UserException('File part overlaps an accepted part')
                    if any(offset < int(start) + part['size'] and int(start) < offset + len(content) for start, part in parts.items()):
                        raise UserException('File parts overlap')
                    path = root_dir / op_id / str(index) / (str(offset) + '_' + sha)
                    if not path.resolve().is_relative_to(root_dir.resolve()):
                        raise SecurityException('File part points outside staging')
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if not path.exists():
                        uploaded.paths.append(path)
                    os.replace(temporary, path)
                    parts[str(offset)] = dict(size=len(content), sha256=sha)
                    jobs[op_id] = job
                for op_id, job in jobs.items():
                    value = values[op_id]
                    ready = len(value['parts']) == len(value['options']['source_files'])
                    if ready:
                        for index, record in enumerate(value['options']['source_files']):
                            position = 0
                            for start, part in sorted(value['parts'].get(str(index), {}).items(), key=lambda item:int(item[0])):
                                if int(start) != position:
                                    ready = False
                                    break
                                position = int(start) + part['size']
                            if not ready or position != record['size']:
                                ready = False
                                break
                    if ready:
                        job.set_value('state', 'pending')
                    job.set_json_value('data', value)
                    save_queue(job)
                    record_update(data, job)
                data['chunks'][chunk_id] = digest
                batch.set_json_value('data', data); save_queue(batch)
        finally:
            for _piece, _content, _sha, temporary in prepared_parts:
                temporary.unlink(missing_ok=True)
            if root_dir.exists() and not any(root_dir.iterdir()):
                root_dir.rmdir()
        return dict(batch_id=self.kwargs['batch_id'], accepted=True, duplicate=False)


class CheckinQueueJobCmd(Command):
    def can_run(self, source='api'):
        return False  # Only the native queue may supply the trusted job object.

    def execute(self):
        from tactic.command.browser_checkin_cmd import BrowserCheckinCmd
        job = self.kwargs['job']
        value = job.get_json_value('data')
        batch = owned_batch(value['batch_code'])
        if job.get_value('login') != Environment.get_user_name() or job.get_value('project_code') != Project.get_project_code():
            raise SecurityException('Check-in job belongs to another identity')
        root = staging_root(batch.get_code()) / value['operation_id']
        directory = root / 'assembled'
        if not directory.resolve().is_relative_to(staging_root(batch.get_code()).resolve()):
            raise SecurityException('Check-in assembly points outside staging')
        directory.mkdir(parents=True, exist_ok=True)
        names = []
        for index, record in enumerate(value['options']['source_files']):
            name = str(index) + Path(record['path']).suffix
            destination = directory / name
            if destination.is_symlink():
                raise SecurityException('Check-in staging links are not supported')
            position = 0
            parts_for_file = sorted(value['parts'][str(index)].items(), key=lambda item:int(item[0]))
            single_part = len(parts_for_file) == 1
            checksum = None if single_part else hashlib.sha256()
            with destination.open('wb') as target:
                for start, part in parts_for_file:
                    if int(start) != position:
                        raise UserException('Check-in file has a missing part')
                    path = root / str(index) / (start + '_' + part['sha256'])
                    if not path.resolve().is_relative_to(root.resolve()):
                        raise SecurityException('Check-in file part points outside staging')
                    sha = hashlib.sha256()
                    with path.open('rb') as source:
                        while content := source.read(4 * 1024 * 1024):
                            target.write(content); sha.update(content); position += len(content)
                            if checksum is not None:
                                checksum.update(content)
                    if sha.hexdigest() != part['sha256']:
                        raise UserException('Check-in file part changed after upload')
                    if single_part:
                        checksum = sha
            if position != record['size']:
                raise UserException('Check-in file size does not match its manifest')
            if record.get('sha256') and (checksum or hashlib.sha256()).hexdigest() != record['sha256']:
                raise UserException('Check-in source changed while its parts were uploaded')
            names.append(name)
        command = BrowserCheckinCmd(**dict(value['options'], action='checkin', files=names))
        command.upload_directory = directory.as_posix()
        command.max_files = MAX_FILES
        from pyasm.common import Xml
        from pyasm.search import Transaction
        Xml.set_attribute(Transaction.get().get_transaction_log().get_root_node(), 'checkin_file_replay', 'complete')
        Command.execute_cmd(command)
        value['result'] = dict(snapshot=command.get_info()['snapshot'])
        job.set_json_value('data', value)
        save_queue(job)
        return value['result']


def updates(batches, cursors=None, limit=100):
    from tactic_stream.server.navigation_links import check_project
    cursors = cursors or {}
    if not isinstance(batches, list) or len(batches) > 100 or not isinstance(cursors, dict) or type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError('Invalid check-in update request')
    codes = {}
    for item in batches:
        if not isinstance(item, dict) or set(item) != {'batch_id', 'project'} or not isinstance(item['project'], str):
            raise ValueError('Invalid check-in batch reference')
        check_project(item['project'])
        codes[batch_code(item['batch_id'], item['project'])] = item['batch_id']
    search = Search('sthpw/queue'); search.add_filters('code', list(codes)); search.add_filter('login', Environment.get_user_name()); search.add_filter('queue', BATCH_QUEUE)
    events, next_cursors, more = [], {}, False
    for batch in search.get_sobjects() if codes else []:
        batch_id = codes[batch.get_code()]
        cursor = cursors.get(batch_id, 0)
        if type(cursor) is not int or cursor < 0:
            raise ValueError('Invalid check-in update cursor')
        changes = sorted((event for event in batch.get_json_value('data')['updates'].values() if event['revision'] > cursor), key=lambda event:event['revision'])
        page = changes[:max(0, limit - len(events))]
        events.extend(dict(event, batch_id=batch_id) for event in page)
        next_cursors[batch_id] = page[-1]['revision'] if page else cursor
        more = more or len(page) < len(changes)
    return dict(checkins=events, checkinCursors=next_cursors, checkinsHasMore=more)


class CancelCheckinBatchCmd(Command):
    def execute(self):
        code = batch_code(self.kwargs['batch_id'])
        with queue_lock():
            search = Search('sthpw/queue'); search.add_filter('code',code)
            if search.get_sobject() is None:
                new_row(code,BATCH_QUEUE,'cancelled',dict(chunks={},jobs={},updates={},revision=0))
            batch = owned_batch(code)
            data = batch.get_json_value('data')
            search = Search('sthpw/queue'); search.add_filters('code', list(data['jobs'].values()))
            for job in search.get_sobjects() if data['jobs'] else []:
                if job.get_value('state') in ('staging', 'pending'):
                    job.set_value('state', 'terminated'); save_queue(job); record_update(data, job)
                    try:
                        cleanup_job(job)
                    except OSError:
                        pass
            batch.set_json_value('data', data)
            batch.set_value('state', 'cancelled'); save_queue(batch)
            states = {job.get_json_value('data')['operation_id']: job.get_value('state')
                      for job in search.get_sobjects()} if data['jobs'] else {}
        return dict(cancelled=True, states=states)


def cleanup_job(job):
    if job and job.get_value('command') == JOB_COMMAND and job.get_value('state') in ('complete', 'error', 'terminated'):
        value = job.get_json_value('data')
        batch_dir = staging_root(value['batch_code'])
        path = batch_dir / identity(value['operation_id'])
        if not path.resolve().is_relative_to(batch_dir.resolve()):
            raise SecurityException('Invalid staging cleanup directory')
        if path.exists():
            shutil.rmtree(path)
        if batch_dir.exists() and not any(batch_dir.iterdir()):
            batch_dir.rmdir()
