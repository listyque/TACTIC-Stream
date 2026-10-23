"""Write-ahead file intents, with commit evidence in each participating database."""
import json
import logging
import os
from pathlib import Path
from uuid import uuid4

from pyasm.biz.file_bytes import byte_lock
from pyasm.common import Container, Environment, Xml

LOG = logging.getLogger(__name__)


class FileJournal:
    def __init__(self, store):
        directory = store.data_dir / 'temp' / 'file-transactions'
        directory.mkdir(parents=True, exist_ok=True)
        self.token = uuid4().hex
        self.path = directory / (self.token + '.jsonl')
        self.lock = byte_lock(self.path)
        self.lock.__enter__()
        self.stream = self.path.open('x', encoding='utf-8')
        self.resources = []
        self.databases = []
        self.nodes = []
        self.completed = set()
        self.append({'asset_dir': Environment.get_asset_dir()})

    def append(self, value):
        if self.stream.closed:
            self.stream = self.path.open('a', encoding='utf-8')
        self.stream.write(json.dumps(value, ensure_ascii=False) + '\n')
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def claim(self):
        if self.lock is None:
            if not self.path.exists():
                raise RuntimeError('File transaction already recovered; discard the failed request')
            self.lock = byte_lock(self.path)
            self.lock.__enter__()

    def add(self, node):
        self.append({'file': dict(node.attrib)})
        saved = Xml().create_element('file')
        for name, value in node.attrib.items():
            Xml.set_attribute(saved, name, value)
        self.nodes.append(saved)

    def undone(self, index):
        self.append({'undone': index})
        self.completed.add(index)

    def prepare(self, databases):
        databases = [sql for sql in databases if getattr(sql, '_has_writes', False)]
        if not databases:
            from pyasm.search import DbContainer, Transaction
            from pyasm.search.search import _context
            transaction = Transaction.get()
            sql = DbContainer.get(_context.get().store.get_db_resource())
            depth = transaction.counter
            transaction.counter = 1
            try:
                transaction.register_database(sql)
                if sql.conn is None:
                    sql.connect()
            finally:
                transaction.counter = depth
            databases.append(sql)
        self.resources = [dict(database=sql.get_database_name(), schema=sql.get_db_resource().get_schema(),
                               key=sql.get_db_resource().get_key()) for sql in databases]
        self.databases = databases
        self.append({'databases': self.resources})
        for sql in databases:
            sql._record_file_commit(self.token)

    def close(self, resolved=False):
        self.stream.close()
        if resolved:
            try:
                self.path.unlink(missing_ok=True)
            except OSError:
                LOG.exception('Resolved file journal cleanup deferred: %s', self.path.name)
                resolved = False
        if self.lock is not None:
            self.lock.__exit__(None, None, None)
            self.lock = None
        if resolved:
            try:
                self.path.with_name(self.path.name + '.lock').unlink(missing_ok=True)
            except OSError:
                LOG.warning('File journal lock cleanup deferred: %s', self.path.name)
            for sql in self.databases:
                sql._clear_file_commit(self.token)


def commit_states(store, resources, token):
    from pyasm.search import DbResource
    from pyasm.search.search import RequestContext, request_context
    committed = []
    # Read independently of the failed owner's uncommitted connections.
    with request_context(RequestContext(store, 'admin', 'admin')):
        for saved in resources:
            resource = DbResource.get_default(saved['database'], schema=saved['schema'], use_config=True)
            if resource.get_key() != saved['key']:
                raise RuntimeError('File recovery database configuration changed: ' + saved['database'])
            with store.connection(resource) as db:
                if resource.get_vendor() == 'Sqlite':
                    exists = db.execute("SELECT 1 FROM sqlite_master WHERE name='_stream_file_commits'").fetchone()
                else:
                    exists = db.execute("SELECT to_regclass('_stream_file_commits') AS present").fetchone()['present']
                marker = resource.get_database_impl().get_parameter()
                committed.append(bool(exists and db.execute('SELECT token FROM _stream_file_commits WHERE token=' + marker,
                                                             (token,)).fetchone()))
    return committed


def recover_files(store):
    """Skip live owners; preserve and reject writes when outcomes cannot be proved."""
    from pyasm.search import DbResource, FileUndo
    from pyasm.search.transaction import PartialCommitException, TransactionException
    directory = store.data_dir / 'temp' / 'file-transactions'
    if not directory.exists() or not any(directory.glob('*.jsonl')):
        return
    try:
        guard = byte_lock(directory / 'recovery')
        guard.__enter__()
    except (PermissionError, BlockingIOError):
        if not any(directory.glob('*.jsonl')):
            return
        raise TransactionException('Another worker is recovering file transactions; retry after recovery') from None
    try:
        for path in directory.glob('*.jsonl'):
            if len(path.stem) != 32 or any(char not in '0123456789abcdef' for char in path.stem):
                raise TransactionException('Invalid file recovery journal: ' + path.name)
            try:
                if not path.exists():
                    continue
                lock = byte_lock(path)
                lock.__enter__()
            except (PermissionError, BlockingIOError):
                continue
            try:
                if not path.exists():
                    continue
                records = []
                offset = 0
                with path.open('rb') as stream:
                    for line in stream:
                        if line.endswith(b'\n'):
                            records.append(json.loads(line))
                            offset = stream.tell()
                if path.stat().st_size != offset:
                    with path.open('r+b') as stream:
                        stream.truncate(offset)
                        stream.flush()
                        os.fsync(stream.fileno())
                if not records:
                    path.unlink()
                    continue
                asset_dir = records[0]['asset_dir']
                if not os.path.isabs(asset_dir):
                    raise TransactionException('Invalid recovery asset directory')
                resources = next((record['databases'] for record in reversed(records) if 'databases' in record), [])
                committed = commit_states(store, resources, path.stem)
                if any(committed) and not all(committed):
                    raise PartialCommitException('File transaction partially committed; backups retained: ' + path.name)
                if not any(committed):
                    finished = {record['undone'] for record in records if 'undone' in record}
                    nodes = [record['file'] for record in records if 'file' in record]
                    for index in reversed(range(len(nodes))):
                        if index in finished:
                            continue
                        node = Xml().create_element('file')
                        attributes = nodes[index]
                        if attributes.get('type') not in ('move', 'copy', 'remove', 'mkdir', 'rmdir', 'create', 'symlink'):
                            raise TransactionException('Invalid recovery file operation')
                        for name, value in attributes.items():
                            if name in ('src', 'dst', 'orig', 'link', 'prev') and value and not os.path.isabs(value):
                                value = os.path.join(asset_dir, value)
                            Xml.set_attribute(node, name, value)
                        previous = Container.get('FileUndo:rollback')
                        Container.put('FileUndo:rollback', node)
                        try:
                            FileUndo.undo(node)
                        finally:
                            Container.put('FileUndo:rollback', previous)
                        with path.open('a', encoding='utf-8') as stream:
                            stream.write(json.dumps({'undone': index}) + '\n')
                            stream.flush()
                            os.fsync(stream.fileno())
                    LOG.warning('Recovered aborted file transaction %s (%s operations)', path.stem, len(nodes))
                else:
                    LOG.info('Retained committed file transaction %s', path.stem)
                path.unlink()
                for saved, committed_marker in zip(resources, committed):
                    if not committed_marker:
                        continue
                    resource = DbResource.get_default(saved['database'], schema=saved['schema'], use_config=True)
                    resource.get_sql()._clear_file_commit(path.stem)
            finally:
                lock.__exit__(None, None, None)
                if not path.exists():
                    path.with_name(path.name + '.lock').unlink(missing_ok=True)
    finally:
        guard.__exit__(None, None, None)
