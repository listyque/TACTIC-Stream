"""Snapshot browsing and original set_current_snapshot; no direct flag updates."""
import mimetypes
from .contracts import ApiError, json_safe, revision, text
from .upload_store import integer
from .record_service import INLINE_TYPES


class VersionService:
    def _version_parent(self, data):
        opened = self.open_target(data.get('target'))
        if opened['kind'] not in ('table', 'form'):
            raise ApiError(400, 'version_target', 'Откройте запись из конфигурационного представления')
        return self._object(opened['search_type'], data.get('key'))

    def version_operation(self, method, path, data):
        from pyasm.search import Search
        from pyasm.biz import Snapshot
        parent = self._version_parent(data)
        if method == 'GET' and path == '/file-versions':
            offset = integer(data.get('offset', 0), 'offset', 0, 1000000)
            limit = integer(data.get('limit', 40), 'limit', 1, 100)
            search = Search('sthpw/snapshot'); search.add_relationship_filter(parent)
            context = text(data.get('context', ''), 'context', 200, empty=True)
            if context: search.add_filter('context', context)
            state = data.get('record_state', 'active')
            if state not in ('active', 'all'):
                raise ApiError(400, 'record_state', 'Выберите active или all')
            if state == 'all': search.set_show_retired(True)
            total = search.get_count()
            search.add_order_by('timestamp', direction='desc')
            search.add_order_by('id', direction='desc')
            search.set_offset(offset); search.set_limit(limit)
            snapshots = search.get_sobjects()
            files = Snapshot.get_files_by_snapshots(snapshots) if snapshots else []
            by_code = {f.get_code(): f for f in files}
            rows = []
            for snap in snapshots:
                row = self._version_item(snap)
                row['files'] = []
                for code in snap.get_all_file_codes():
                    file = by_code.get(code)
                    if file is None:
                        row['files'].append({'code': code, 'name': code, 'missing_registration': True})
                        continue
                    name = file.get_full_file_name()
                    mime = mimetypes.guess_type(name)[0] or 'application/octet-stream'
                    row['files'].append({'code': code, 'name': name,
                        'type': file.get_value('type', no_exception=True),
                        'size': json_safe(file.get_value('size', no_exception=True)),
                        'mime': mime, 'preview': mime in INLINE_TYPES})
                rows.append(row)
            return {'items': rows, 'total': total, 'offset': offset, 'limit': limit,
                    'has_more': offset+len(rows)<total, 'can_upload': self.allow_uploads,
                    'notice': 'Исходные snapshot и file; страницы сервера, не первые 100 версий. Current и latest имеют разный смысл.'}
        if path == '/snapshot-current' and method in ('GET', 'POST'):
            snapshot = self._snapshot_for(parent, data.get('snapshot'))
            if not snapshot.get_value('search_code', no_exception=True):
                # Upstream set_current filters search_code, not the old search_id.
                # Do not risk clearing flags for unrelated id-only legacy rows.
                raise ApiError(501, 'legacy_snapshot', 'У версии отсутствует search_code; исходный set_current требует отдельной проверки')
            if int(snapshot.get_value('version')) < 0 or snapshot.is_retired():
                raise ApiError(400, 'snapshot_state', 'Нельзя выбрать архивную или versionless-версию')
            stream = self._current_stream(snapshot)
            token = revision([s.get_sobject_dict() for s in stream])
            result = {'selected': self._version_item(snapshot), 'revision': token,
                      'current': [self._version_item(s) for s in stream if s.get_value('is_current')],
                      'can_write': self.allow_writes,
                      'notice': 'Исходный set_current_snapshot также обновляет versionless/current. Latest не переключается.'}
            if method == 'GET': return result
            if data.get('confirm') != 'SET_CURRENT':
                raise ApiError(400, 'confirmation', 'Подтвердите изменение current-версии')
            def apply():
                fresh = self._snapshot_for(parent, snapshot.get_search_key())
                if fresh.is_retired(): raise ApiError(409, 'snapshot_state', 'Версия уже архивирована')
                current = self._current_stream(fresh)
                if revision([s.get_sobject_dict() for s in current]) != data.get('revision'):
                    raise ApiError(409, 'conflict', 'Набор версий изменился; откройте подтверждение повторно')
                self._stub().set_current_snapshot(fresh.get_code())
                return {'changed': True, 'snapshot': fresh.get_search_key(),
                        'operation': 'TacticServerStub.set_current_snapshot', 'latest_changed': False}
            return self._write(apply)
        raise ApiError(405, 'method', 'Операция с версиями не поддерживается')

    def _current_stream(self, snapshot):
        """Mirror Snapshot.set_current's exact identity incl. optional level."""
        from pyasm.search import Search
        search = Search('sthpw/snapshot')
        for name in ('search_type', 'search_code', 'context'):
            search.add_filter(name, snapshot.get_value(name))
        if snapshot.get_value('level_type', no_exception=True):
            for name in ('level_type', 'level_id'):
                search.add_filter(name, snapshot.get_value(name))
        if search.get_count() > 5000:
            raise ApiError(413, 'version_stream', 'Более 5000 версий в current-потоке; операция не выполнена')
        search.add_order_by('id'); search.set_limit(5001)
        return search.get_sobjects()

    def _version_item(self, snapshot):
        fields = ('code','context','process','version','description','timestamp','login',
                  'is_current','is_latest','s_status','level_type','level_id')
        values = {f:json_safe(snapshot.get_value(f,no_exception=True)) for f in fields}
        return dict(values, key=snapshot.get_search_key(), revision=revision(snapshot.get_sobject_dict()))
