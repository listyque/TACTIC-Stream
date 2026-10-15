"""Notes, schema relationships, versions and file delivery through original TACTIC models.

Every object is re-resolved from a freshly authorized view. A download request
contains snapshot/file identifiers, never an arbitrary filesystem path.
"""
from pathlib import Path
import base64
import json
import mimetypes
from .contracts import ApiError, clean_query, clean_values, json_safe, revision, text
from .file_payload import FilePayload

INLINE_TYPES = {'image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/bmp',
                'video/mp4', 'video/webm', 'audio/mpeg', 'audio/ogg', 'audio/wav', 'audio/mp4'}


def related_id(parent_target, key, stype):
    raw = json.dumps([key, stype], ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    return parent_target + '/~related/' + base64.urlsafe_b64encode(raw).decode().rstrip('=')


def decode_related_id(token):
    if not isinstance(token, str) or len(token) > 3500:
        raise ApiError(400, 'related_target', 'Слишком длинная ссылка связи')
    try:
        value = json.loads(base64.urlsafe_b64decode(token + '=' * (-len(token) % 4)).decode('utf-8'))
    except Exception as exc:
        raise ApiError(400, 'related_target', 'Некорректная ссылка связи') from exc
    if not isinstance(value, list) or len(value) != 2 or any(not isinstance(x, str) for x in value):
        raise ApiError(400, 'related_target', 'Некорректная ссылка связи')
    return value


def checked_file_path(filename, roots):
    """Resolve symlinks and reject paths outside explicitly configured repositories."""
    path = Path(filename).resolve()
    allowed = [Path(root).resolve() for root in roots if root]
    if not any(path.is_relative_to(root) for root in allowed):
        raise ApiError(403, 'file_scope', 'Файл находится вне разрешённых репозиториев TACTIC')
    if not path.is_file():
        raise ApiError(404, 'file_missing', 'Файл зарегистрирован, но недоступен в репозитории')
    return path


class RecordService:
    def record_operation(self, method, path, data):
        from pyasm.search import Search
        from pyasm.biz import Schema, Note
        from pyasm.common import Environment
        opened = self.open_target(data.get('target'))
        if opened['kind'] not in ('table', 'form'):
            raise ApiError(400, 'record_view', 'Откройте таблицу объектов')
        stype = opened['search_type']
        if path == '/bulk-records' and method == 'PATCH':
            changes = data.get('records')
            if not isinstance(changes, list) or not 1 <= len(changes) <= 100:
                raise ApiError(400, 'bulk_limit', 'От 1 до 100 записей за операцию')
            keys = [r.get('key') if isinstance(r, dict) else None for r in changes]
            if any(not isinstance(k, str) for k in keys) or len(set(keys)) != len(keys):
                raise ApiError(400, 'bulk_keys', 'Ключи должны быть уникальны')
            def apply():
                from tactic.core.native_edit import NativeEditCmd
                pending = []
                # Validate the whole set before running the first command. _write
                # supplies one original TACTIC transaction for the entire batch.
                for item in changes:
                    obj = self._object(stype, item['key']); form = self.prepare_form(stype, item['key'], item.get('values'))
                    if form.get('dependency_notice'): raise ApiError(400, 'form_dependency', form['dependency_notice'])
                    if form['record']['revision'] != item.get('revision'):
                        raise ApiError(409, 'conflict', 'Одна из выбранных записей изменилась')
                    values = clean_values(item.get('values'), form['spec']['fields'])
                    if hasattr(self,'check_native_write'):self.check_native_write(stype,values,item['key'])
                    pending.append((obj, values, form['spec']))
                result = []
                for obj, values, spec in pending:
                    cmd = NativeEditCmd(sobject=obj, view=spec['view'], data=values, input_prefix='__NONE__')
                    cmd.execute(); result.append(self._serialize(cmd.get_sobject(), spec))
                return {'items': result, 'updated': len(result), 'transaction': 'TACTIC Command'}
            return self._write(apply)
        obj = self._object(stype, data.get('key'))
        if path == '/relations' and method == 'GET':
            schema = Schema.get()
            types = sorted(set(schema.get_related_search_types(stype)))
            items = []
            for related in types:
                try:
                    self.require_type(related)
                    attrs = schema.get_relationship_attrs(related, stype)
                    if not attrs or attrs.get('disabled') in (True, 'true'): continue
                    search = Search(related); search.add_relationship_filter(obj)
                    # No guessed foreign key or direct SQL. Same Schema traversal
                    # as legacy tables, including instance connections.
                    count = search.get_count()
                    items.append({'search_type': related, 'count': count,
                                  'relationship': attrs.get('relationship'),
                                  'target': related_id(opened['id'], obj.get_search_key(), related)})
                except ApiError:
                    raise
                except Exception as exc:
                    items.append({'search_type': related, 'count': None, 'target': None,
                                  'error': 'Связь не разрешена движком: ' + type(exc).__name__})
            return {'items': items, 'key': obj.get_search_key(), 'source': 'TACTIC Schema'}
        if path == '/notes':
            if method == 'GET':
                search = Search('sthpw/note'); search.add_relationship_filter(obj)
                search.add_order_by('timestamp desc'); search.set_limit(200)
                fields = ('code', 'note', 'context', 'process', 'login', 'timestamp', 'parent_id', 'access')
                return {'items': [{'key': n.get_search_key(), **{f: json_safe(n.get_value(f, no_exception=True)) for f in fields}}
                                  for n in search.get_sobjects()], 'limit': 200, 'can_write': self.allow_writes}
            if method == 'POST':
                value = data.get('note')
                if not isinstance(value, str) or not value.strip() or len(value) > 200000 or '\x00' in value:
                    raise ApiError(400, 'note', 'Пустой или слишком длинный комментарий')
                process = text(data.get('process') or 'publish', 'process', 100)
                parent_key = data.get('parent_note')
                def add():
                    parent_id = 0
                    if parent_key:
                        parent = self._object('sthpw/note', parent_key)
                        search = Search('sthpw/note'); search.add_relationship_filter(obj); search.add_id_filter(parent.get_id())
                        if not search.get_sobject(): raise ApiError(403, 'note_scope', 'Комментарий другого объекта')
                        parent_id = parent.get_id()
                    note = Note.create(obj, value.strip(), process=process, parent_id=parent_id)
                    return {'created': True, 'key': note.get_search_key()}
                return self._write(add)
        if path == '/file' and method == 'GET':
            snapshot = self._snapshot_for(obj, data.get('snapshot'))
            from pyasm.biz import Snapshot
            files = Snapshot.get_files_by_snapshots([snapshot])
            file = next((f for f in files if f.get_code() == data.get('file')), None)
            if file is None: raise ApiError(404, 'file', 'Файл не принадлежит этой версии объекта')
            aliases = Environment.get_asset_dirs()
            roots = list(aliases.values()) + [Environment.get_asset_dir(file_object=file)]
            path = checked_file_path(file.get_lib_path(), roots)
            content_type = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
            inline = data.get('preview') == '1' and content_type in INLINE_TYPES
            # HTML, SVG, XML, PDF and scripts are always attachments. Preview uses
            # img/video/audio, never v-html/object or executable same-origin content.
            return FilePayload(str(path), path.name, content_type if inline else 'application/octet-stream', inline)
        raise ApiError(405, 'method', 'Операция не поддерживается')

    def _snapshot_for(self, parent, key):
        from pyasm.search import Search
        snapshot = self._object('sthpw/snapshot', key)
        if parent.get_base_search_type() == 'sthpw/snapshot' and parent.get_id() == snapshot.get_id():
            return snapshot
        search = Search('sthpw/snapshot'); search.add_relationship_filter(parent)
        search.add_id_filter(snapshot.get_id())
        found = search.get_sobject()
        if not found: raise ApiError(403, 'snapshot_scope', 'Версия не принадлежит выбранному объекту')
        return found

    def snapshots(self, stype, key):
        from pyasm.search import Search
        from pyasm.biz import Snapshot
        parent = self._object(stype, key)
        search = Search('sthpw/snapshot'); search.add_relationship_filter(parent)
        search.add_order_by('version desc'); search.set_limit(100)
        snapshots = search.get_sobjects()
        # Batch file lookup for all snapshot XML file codes.
        all_files = Snapshot.get_files_by_snapshots(snapshots) if snapshots else []
        by_code = {f.get_code(): f for f in all_files}
        fields = ('code', 'context', 'version', 'description', 'timestamp', 'login', 'is_latest', 'is_current')
        result = []
        for snap in snapshots:
            codes = snap.get_all_file_codes()
            items = []
            for code in codes:
                file = by_code.get(code)
                if file is None: continue
                filename = file.get_full_file_name()
                typ = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                items.append({'code': code, 'name': filename, 'type': file.get_value('type', no_exception=True),
                              'size': json_safe(file.get_value('size', no_exception=True)),
                              'preview': typ in INLINE_TYPES, 'mime': typ})
            result.append({'key': snap.get_search_key(), **{f: json_safe(snap.get_value(f, no_exception=True)) for f in fields}, 'files': items})
        return {'items': result, 'can_upload': self.allow_uploads, 'limit': 100,
                'notice': 'Версии и файлы исходного TACTIC; загрузка выполняет check-in. Лимит списка — 100 версий.'}
