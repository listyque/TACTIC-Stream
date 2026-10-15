"""Bounded, disk-backed staging, NOT an alternative TACTIC asset repository.

Chunks are fsynced before acknowledging their offset. Advisory file locks work
across processes on a LOCAL filesystem. NFS/SMB lock/durability semantics are not
claimed. A crash at the DB/filesystem boundary is explicitly 'uncertain'; it is
never retried automatically. Tickets/passwords and arbitrary client paths are
never persisted. Only the final callback may perform the original check-in.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
import uuid

from .contracts import ApiError

MiB = 1024 * 1024
CHUNK = 4 * MiB
ACTIVE = {'uploading', 'ready', 'committing', 'uncertain'}
HEX = re.compile(r'^[0-9a-f]{64}$')


def filename(value):
    if (not isinstance(value, str) or not value or len(value.encode('utf-8')) > 180
            or any(ord(c) < 32 or c in '/\\:*?"<>|' for c in value)
            or value in ('.', '..') or value.endswith(('.', ' '))
            or re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)', value, re.I)):
        raise ApiError(400, 'filename', 'Недопустимое имя файла')
    return value


def digest(value):
    if not isinstance(value, str) or not HEX.fullmatch(value):
        raise ApiError(400, 'checksum', 'Требуется SHA-256 в нижнем регистре')
    return value


def integer(value, name, minimum=0, maximum=2**53-1):
    if isinstance(value, str) and re.fullmatch(r'0|[1-9][0-9]{0,15}', value):
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ApiError(400, 'upload_value', 'Некорректное значение: ' + name)
    return value


@contextmanager
def local_lock(path, timeout=10):
    """OS locks release on process death; do not delete the stable lock inode."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        stream.seek(0, 2)
        if not stream.tell():
            stream.write(b'0'); stream.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                stream.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (BlockingIOError, OSError):
                if time.monotonic() >= deadline:
                    raise ApiError(409, 'upload_busy', 'Загрузка занята другой операцией; обновите состояние')
                time.sleep(.05)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_UN)


class UploadStore:
    def __init__(self, root, *, max_file=2048*MiB, owner_quota=8192*MiB,
                 global_quota=32768*MiB, max_jobs=16, ttl=86400, clock=time.time):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.max_file = integer(max_file, 'max_file', 1, 64*1024*MiB)
        self.owner_quota = integer(owner_quota, 'owner_quota', self.max_file, 256*1024*MiB)
        self.global_quota = integer(global_quota, 'global_quota', self.owner_quota, 1024*1024*MiB)
        self.max_jobs = integer(max_jobs, 'max_jobs', 1, 128)
        self.ttl = integer(ttl, 'ttl', 60, 7*86400)
        self.clock = clock

    def limits(self):
        return {'chunk_bytes': CHUNK, 'max_file_bytes': self.max_file,
                'owner_quota_bytes': self.owner_quota, 'global_quota_bytes': self.global_quota,
                'max_active_jobs': self.max_jobs, 'expires_after_seconds': self.ttl}

    def _folder(self, job):
        if not isinstance(job, str) or not re.fullmatch('[0-9a-f]{32}', job):
            raise ApiError(400, 'upload_id', 'Некорректный идентификатор загрузки')
        folder = self.root / job
        if folder.is_symlink():
            raise ApiError(403, 'upload_path', 'Некорректный каталог загрузки')
        return folder

    def _read(self, job):
        try:
            path = self._folder(job) / 'state.json'
            if path.is_symlink(): raise ValueError('symlink')
            if path.stat().st_size > MiB: raise ValueError('large state')
            result = json.loads(path.read_text(encoding='utf-8'))
            if result.get('id') != job: raise ValueError('identity')
            return result
        except FileNotFoundError:
            raise ApiError(404, 'upload_missing', 'Загрузка не найдена')
        except (ValueError, KeyError):
            raise ApiError(409, 'upload_corrupt', 'Метаданные загрузки повреждены; check-in не выполнен')

    def _save(self, state):
        folder = self._folder(state['id'])
        temporary = folder / ('state.' + uuid.uuid4().hex + '.tmp')
        try:
            with temporary.open('x', encoding='utf-8') as stream:
                json.dump(state, stream, ensure_ascii=False, allow_nan=False)
                stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, folder / 'state.json')
            if os.name != 'nt':
                fd = os.open(folder, os.O_RDONLY)
                try: os.fsync(fd)
                finally: os.close(fd)
        finally:
            temporary.unlink(missing_ok=True)

    def _owned(self, job, owner, binding):
        state = self._read(job)
        if state.get('owner') != owner or state.get('binding') != binding:
            raise ApiError(404, 'upload_missing', 'Загрузка не найдена в этом контексте')
        if state['state'] == 'committing':
            # This function is called under the per-job lock. No active finish
            # holds it; a persisted committing state means a process died.
            state['state'] = 'uncertain'; self._save(state)
        if state['state'] in ('uploading', 'ready') and self.clock() > state['expires']:
            raise ApiError(410, 'upload_expired', 'Срок загрузки истёк; создайте новую')
        return state

    def _public(self, state):
        keys = ('id', 'filename', 'size', 'offset', 'state', 'created', 'expires',
                'fingerprint', 'context', 'description', 'sha256', 'result')
        return {**{key: state[key] for key in keys if key in state}, 'chunk_bytes': CHUNK}

    def _lock(self, job):
        self._folder(job)  # validate BEFORE using id in a path
        return local_lock(self.root / '.locks' / (job + '.lock'))

    def _states(self):
        for folder in self.root.iterdir():
            if re.fullmatch('[0-9a-f]{32}', folder.name) and folder.is_dir():
                # Corrupt records cannot be ignored when calculating reservations.
                yield self._read(folder.name)

    def create(self, owner, binding, *, name, size, fingerprint, context, description='', request_id):
        size = integer(size, 'size', 1, self.max_file)
        name = filename(name); digest(fingerprint)
        if not isinstance(request_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}', request_id):
            raise ApiError(400, 'request_id', 'Нужен request_id загрузки')
        if not isinstance(context, str) or not re.fullmatch(r'[A-Za-z0-9_/-]{1,100}', context) or '..' in context or context.startswith('/'):
            raise ApiError(400, 'context', 'Некорректный context check-in')
        if not isinstance(description, str) or len(description) > 16000 or '\x00' in description:
            raise ApiError(400, 'description', 'Некорректное описание check-in')
        identity = {'owner': owner, 'binding': binding, 'filename': name, 'size': size,
                    'fingerprint': fingerprint, 'context': context, 'description': description}
        with local_lock(self.root / '.locks' / 'quota.lock'):
            states = list(self._states())
            for old in states:
                if old['owner'] == owner and old.get('request_id') == request_id:
                    if any(old.get(k) != v for k, v in identity.items()):
                        raise ApiError(409, 'upload_replay', 'request_id уже относится к другой загрузке')
                    return self._public(old)
            active = [s for s in states if s['state'] in ACTIVE]
            owned = [s for s in active if s['owner'] == owner]
            if (len(owned) >= self.max_jobs or len(active) >= 128
                    or sum(s['size'] for s in owned) + size > self.owner_quota
                    or sum(s['size'] for s in active) + size > self.global_quota):
                raise ApiError(413, 'upload_quota', 'Лимит незавершённых загрузок; отмените ненужные загрузки')
            # Other queued reservations are also relevant, not only actual bytes.
            reserved = sum(max(0, s['size'] - s['offset']) for s in active)
            if shutil.disk_usage(self.root).free < size + reserved + 64*MiB:
                raise ApiError(507, 'upload_space', 'Недостаточно места для временной загрузки')
            job = uuid.uuid4().hex
            folder = self._folder(job); folder.mkdir(mode=0o700)
            state = dict(identity, id=job, request_id=request_id, offset=0, state='uploading',
                         created=self.clock(), expires=self.clock()+self.ttl)
            (folder / 'payload').mkdir(mode=0o700)
            (folder / 'payload' / name).touch(mode=0o600)
            self._save(state)
            return self._public(state)

    def status(self, job, owner, binding):
        with self._lock(job):
            return self._public(self._owned(job, owner, binding))

    def list(self, owner, binding):
        # A list does not mutate an in-flight committing state.
        return [self._public(s) for s in sorted(self._states(), key=lambda x:x['created'], reverse=True)
                if s['owner'] == owner and s['binding'] == binding][:128]

    def _payload(self, state):
        path = self._folder(state['id']) / 'payload' / filename(state['filename'])
        if path.is_symlink() or not path.is_file():
            raise ApiError(409, 'upload_corrupt', 'Временный файл недоступен')
        if path.stat().st_size < state['offset']:
            raise ApiError(409, 'upload_corrupt', 'Подтверждённые байты отсутствуют; загрузка повреждена')
        return path

    def chunk(self, job, owner, binding, offset, content, checksum):
        offset = integer(offset, 'offset')
        digest(checksum)
        if not isinstance(content, bytes) or not 1 <= len(content) <= CHUNK:
            raise ApiError(413, 'chunk_size', 'Часть файла должна быть от 1 байта до 4 МиБ')
        if hashlib.sha256(content).hexdigest() != checksum:
            raise ApiError(400, 'checksum', 'SHA-256 части файла не совпадает')
        with self._lock(job):
            state = self._owned(job, owner, binding)
            if state['state'] not in ('uploading', 'ready'):
                raise ApiError(409, 'upload_state', 'Загрузка больше не принимает части')
            if offset + len(content) > state['size'] or offset % CHUNK or (len(content) != CHUNK and offset + len(content) != state['size']):
                raise ApiError(400, 'chunk_range', 'Некорректная граница части файла')
            path = self._payload(state)
            if offset < state['offset']:
                with path.open('rb') as stream:
                    stream.seek(offset); previous = stream.read(len(content))
                if offset + len(content) <= state['offset'] and hashlib.sha256(previous).hexdigest() == checksum:
                    return self._public(state)
                raise ApiError(409, 'chunk_replay', 'Повтор части содержит другие данные')
            if offset != state['offset']:
                raise ApiError(409, 'chunk_offset', 'Обновите подтверждённую позицию загрузки', {'offset': state['offset']})
            if shutil.disk_usage(self.root).free < len(content) + 16*MiB:
                raise ApiError(507, 'upload_space', 'Недостаточно места для части файла')
            with path.open('r+b') as stream:
                stream.truncate(state['offset'])  # recover unacknowledged tail after a crash
                stream.seek(state['offset']); stream.write(content)
                stream.flush(); os.fsync(stream.fileno())
            state['offset'] += len(content)
            state['state'] = 'ready' if state['offset'] == state['size'] else 'uploading'
            state['expires'] = self.clock() + self.ttl
            self._save(state)
            return self._public(state)

    def finish(self, job, owner, binding, callback):
        with self._lock(job):
            state = self._owned(job, owner, binding)
            if state['state'] == 'complete': return self._public(state)
            if state['state'] == 'uncertain':
                raise ApiError(409, 'checkin_uncertain', 'Результат check-in не определён. Проверьте версии объекта; автоматический повтор запрещён')
            if state['state'] != 'ready' or state['offset'] != state['size']:
                raise ApiError(409, 'upload_incomplete', 'Не все части файла получены')
            path = self._payload(state)
            if path.stat().st_size != state['size']:
                raise ApiError(409, 'upload_corrupt', 'Размер временного файла не совпадает')
            h = hashlib.sha256(); fingerprint = hashlib.sha256()
            with path.open('rb') as stream:
                while block := stream.read(CHUNK):
                    h.update(block); fingerprint.update(hashlib.sha256(block).digest())
            if fingerprint.hexdigest() != state['fingerprint']:
                raise ApiError(409, 'file_fingerprint', 'Полный блочный хеш файла не совпадает. Check-in не выполнялся; отмените повреждённую загрузку')
            state.update(sha256=h.hexdigest(), state='committing')
            self._save(state)  # before invoking any external/DB side effect
            try:
                result = callback(path, dict(state))
                # Serialize before declaring completion; never persist arbitrary objects.
                json.dumps(result, ensure_ascii=False, allow_nan=False)
                state.update(state='complete', result=result, expires=self.clock()+7*86400)
                self._save(state)
            except BaseException:
                state.update(state='uncertain', expires=self.clock()+7*86400)
                self._save(state)
                raise
            path.unlink(missing_ok=True)
            return self._public(state)

    def cancel(self, job, owner, binding):
        with self._lock(job):
            # Expired uploads can still be cancelled to release reservations.
            state = self._read(job)
            if state.get('owner') != owner or state.get('binding') != binding:
                raise ApiError(404, 'upload_missing', 'Загрузка не найдена')
            if state['state'] in ('committing', 'uncertain', 'complete'):
                raise ApiError(409, 'upload_state', 'Check-in начат или завершён; отмена не должна удалять версии')
            state.update(state='cancelled', expires=self.clock()+86400)
            self._save(state)
            (self._folder(job)/'payload'/filename(state['filename'])).unlink(missing_ok=True)
            return self._public(state)

    def cleanup(self):
        """Explicit opportunistic cleanup. Never discards an uncertain commit."""
        removed = 0
        with local_lock(self.root/'.locks'/'quota.lock'):
            for state in list(self._states()):
                if state['expires'] >= self.clock() or state['state'] in ('committing','uncertain'):
                    continue
                with self._lock(state['id']):
                    fresh = self._read(state['id'])
                    if fresh['expires'] < self.clock() and fresh['state'] not in ('committing','uncertain'):
                        shutil.rmtree(self._folder(fresh['id'])); removed += 1
        return removed
