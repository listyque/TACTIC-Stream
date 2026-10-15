"""Original simple_checkin at the end of a bounded resumable staging session."""
import hashlib
import json
from pathlib import Path

from .contracts import ApiError, json_safe
from .upload_store import UploadStore, MiB


class UploadService:
    def upload(self, stype, key, filename, content, context):
        # Keep the old bounded endpoint for existing native clients, but do not
        # let it bypass the same source-declared client/custom validation guard.
        opened = getattr(self, 'active_target', None)
        if not opened or opened.get('kind') not in ('table','form') or opened.get('search_type') != stype:
            raise ApiError(403, 'upload_target', 'Не определено исходное представление check-in')
        self._checkin_policy(opened, self._object(stype,key), context)
        return super().upload(stype,key,filename,content,context)

    def _upload_store(self):
        from pyasm.common import Environment
        settings = getattr(self, '_upload_settings', {})
        return UploadStore(Path(Environment.get_tmp_dir())/'native_resumable',
                           max_file=settings.get('max_file_mib', 2048)*MiB,
                           owner_quota=settings.get('owner_quota_mib', 8192)*MiB,
                           global_quota=settings.get('global_quota_mib', 32768)*MiB,
                           max_jobs=settings.get('max_active_jobs', 16),
                           ttl=settings.get('ttl_seconds', 86400))

    def _upload_owner(self):
        from pyasm.common import Environment
        # A stable identity permits reconnect/relogin, without storing credentials.
        value = [self.site, Environment.get_user_name()]
        return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode()).hexdigest()

    def upload_operation(self, method, path, data, body=b''):
        opened = self.open_target(data.get('target'))
        if opened['kind'] not in ('table', 'form'):
            raise ApiError(400, 'upload_target', 'Check-in выполняется из представления объекта')
        obj = self._object(opened['search_type'], data.get('key'))
        binding = {'project': self._project(), 'target': opened['id'],
                   'search_type': opened['search_type'], 'key': obj.get_search_key()}
        owner = self._upload_owner()
        store = self._upload_store()
        if method != 'GET' and not self.allow_uploads:
            raise ApiError(403, 'uploads_disabled', 'Включите allow_writes и allow_uploads на тестовой установке')
        if method == 'GET' and path == '/uploads':
            return {'items': store.list(owner, binding), 'limits': store.limits(),
                    'can_upload': self.allow_uploads,
                    'notice': 'Временные части → исходный simple_checkin. При неопределённом результате проверьте версии; повтор не выполняется.'}
        if method == 'POST' and path == '/uploads':
            self._checkin_policy(opened, obj, data.get('context', 'publish'))
            store.cleanup()
            return store.create(owner, binding, name=data.get('filename'), size=data.get('size'),
                                fingerprint=data.get('fingerprint'), context=data.get('context', 'publish'),
                                description=data.get('description', ''), request_id=data.get('request_id'))
        job = data.get('upload_id')
        if method == 'GET' and path == '/upload-status':
            return store.status(job, owner, binding)
        if method == 'PATCH' and path == '/upload-chunk':
            return store.chunk(job, owner, binding, data.get('offset'), body, data.get('sha256'))
        if method == 'DELETE' and path == '/uploads':
            return store.cancel(job, owner, binding)
        if method == 'POST' and path == '/upload-finish':
            status = store.status(job, owner, binding)
            if status['state'] == 'ready':
                self._checkin_policy(opened, obj, status['context'])
            def commit(path, state):
                # Re-check object before the original command. No caller-supplied path.
                self._object(opened['search_type'], obj.get_search_key())
                return self._finish_staged_upload(obj.get_search_key(), path, state)
            return store.finish(job, owner, binding, commit)
        raise ApiError(405, 'method', 'Операция загрузки не поддерживается')

    def _checkin_policy(self, opened, obj, context):
        import re
        if not isinstance(context, str) or not re.fullmatch(r'[A-Za-z0-9_/-]{1,100}',context) or '..' in context or context.startswith('/'):
            raise ApiError(400, 'context', 'Некорректный context check-in')
        from tactic.core.checkin_policy import checkin_constraints
        options = opened.get('options', {})
        pipeline = options.get('pipeline_code') or obj.get_value('pipeline_code', no_exception=True)
        process = options.get('process') or context.split('/')[0]
        if not isinstance(process, str) or not process or len(process) > 100:
            raise ApiError(501, 'checkin_custom_policy', 'Не удалось разрешить процесс исходного check-in')
        reasons = checkin_constraints(opened['search_type'], process, pipeline, options)
        if reasons:
            raise ApiError(501, 'checkin_custom_policy',
                           'Эта конфигурация требует ещё не перенесённого check-in обработчика. Пользовательские проверки не будут пропущены.',
                           {'constraints': reasons})

    def _finish_staged_upload(self, key, path, state):
        result = self._write(lambda: self._stub().simple_checkin(
            key, state['context'], str(path), description=state['description'],
            mode='copy', create_icon=False))
        # Avoid leaking server filesystem paths returned by extended stubs.
        result = json_safe(result)
        keep = ('code', '__search_key__', 'context', 'version', 'description', 'timestamp')
        snapshot = {k: result[k] for k in keep if k in result} if isinstance(result, dict) else None
        return {'snapshot': snapshot, 'filename': state['filename'], 'sha256': state['sha256'],
                'size': state['size'], 'operation': 'simple_checkin'}
