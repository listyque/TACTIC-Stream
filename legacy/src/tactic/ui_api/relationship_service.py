"""Instance membership through SObject.add_instance/remove_instance.

The API does not accept SQL, class paths, foreign-key column names or file paths.
A Schema relation is re-resolved for every request. remove_instance intentionally
removes all existing duplicate junctions for the pair (upstream semantics); the
client must confirm their exact count. Source/target records are never deleted.
"""
from .contracts import ApiError, integer, revision, text, safe_field
from .record_service import related_id


class RelationshipService:
    def _instance_context(self, data):
        from pyasm.biz import Schema
        opened = self.open_target(text(data.get('target'), 'target', 4000))
        if opened['kind'] not in ('table', 'form'):
            raise ApiError(400, 'relation_source', 'Откройте запись исходного представления')
        source = self._object(opened['search_type'], text(data.get('key'), 'key', 1500))
        other_type = text(data.get('related_type'), 'related_type', 200)
        self.require_type(other_type)
        schema = Schema.get()
        if other_type not in schema.get_related_search_types(opened['search_type']):
            raise ApiError(403, 'relation_missing', 'Связь не объявлена в Schema')
        attrs = schema.get_relationship_attrs(opened['search_type'], other_type)
        if not attrs or attrs.get('disabled') in (True, 'true') or attrs.get('relationship') != 'instance':
            raise ApiError(400, 'not_instance', 'Этот редактор изменяет только штатные instance-связи')
        instance_type = attrs.get('instance_type')
        self.require_type(instance_type)
        if opened['search_type'] == other_type:
            raise ApiError(501, 'self_instance', 'Самоссылочная instance-связь требует выбора направления; автоматическое направление не угадывается')
        return opened, source, other_type, instance_type

    def _instance_revision(self, source, other_type):
        instances = source.get_instances(other_type)
        if len(instances) > 5000:
            raise ApiError(413, 'instance_limit', 'Более 5000 связей; используйте отдельное представление instance-таблицы')
        instances = sorted(instances, key=lambda obj: obj.get_search_key())
        return instances, revision({'source': source.get_sobject_dict(),
                                    'instances': [obj.get_sobject_dict() for obj in instances]})

    def _instance_writable(self, source, other_type, instance_type):
        return bool(self.allow_writes and not source.is_retired() and
                    source.get_project_code() == self._project() and
                    all(not t.startswith(('sthpw/', 'config/')) for t in
                        (source.get_base_search_type(), other_type, instance_type)))

    def relationship_operation(self, method, path, data):
        from pyasm.search import Search
        from pyasm.biz import ExpressionParser
        opened, source, other_type, instance_type = self._instance_context(data)
        instances, current_revision = self._instance_revision(source, other_type)
        writable = self._instance_writable(source, other_type, instance_type)
        target = related_id(opened['id'], source.get_search_key(), other_type)
        spec = self.view(other_type, 'table')
        if path == '/relationship' and method == 'GET':
            return {'revision': current_revision, 'instance_type': instance_type,
                    'count': len(instances), 'can_write': writable, 'target': target,
                    'notice': 'Удаление связи вызывает remove_instance и не удаляет связанные объекты. Дополнительные поля связи сохраняются в исходной instance-таблице.'}
        if path == '/relation-candidates' and method == 'POST':
            offset = integer(data.get('offset', 0), 'offset', 0, 1000000)
            limit = integer(data.get('limit', 30), 'limit', 1, 100)
            search = Search(other_type)
            keyword = text(data.get('keyword') or '', 'keyword', 200, empty=True)
            searchable = [f for f in spec['fields'] if f.get('storage') and f['kind'] in ('text','textarea','select') and safe_field(f['name'])]
            field = next((f for name in ('name','title','code','description') for f in searchable if f['name']==name), None)
            if keyword:
                if field is None: raise ApiError(400, 'search_field', 'В view нет доступного текстового поля')
                # Native keywords are literal; Search supplies the database operator.
                from tactic.core.query_model import apply_tree
                apply_tree(search, {'field':field['name'],'op':'contains','value':keyword}, spec['fields'])
            total = search.get_count()
            search.add_order_by('id'); search.set_offset(offset); search.set_limit(limit)
            candidates = search.get_sobjects()
            # Use the SAME original relationship traversal as remove_instance,
            # batched by source instances. No guessed from_col/to_col arithmetic.
            source_keys = {obj.get_search_key() for obj in instances}
            linked_by_object = Search.get_related_by_sobjects(candidates, instance_type) if candidates else {}
            items = []
            for obj in candidates:
                matches = [x for x in linked_by_object.get(obj.get_search_key(), []) if x.get_search_key() in source_keys]
                row = self._serialize(obj, spec)
                row.update(linked=bool(matches), links=len(matches))
                items.append(row)
            return {'items': items, 'spec': spec, 'total': total, 'offset': offset,
                    'limit': limit, 'revision': current_revision, 'can_write': writable,
                    'instance_type': instance_type}
        if path == '/relationship' and method in ('POST', 'DELETE'):
            if not writable:
                raise ApiError(403, 'relation_read_only', 'Изменение этой instance-связи отключено')
            key = text(data.get('other_key'), 'other_key', 1500)
            other = self._object(other_type, key)
            if other.get_project_code() != self._project() or other.is_retired():
                raise ApiError(403, 'relation_scope', 'Выберите активный объект из текущего проекта')
            def apply():
                fresh_instances, fresh_revision = self._instance_revision(source, other_type)
                if fresh_revision != data.get('revision'):
                    raise ApiError(409, 'conflict', 'Состав связей изменился; перечитайте список')
                if self._serialize(other, spec)['revision'] != data.get('other_revision'):
                    raise ApiError(409, 'conflict', 'Связанный объект изменился; перечитайте список')
                keys = {x.get_search_key() for x in fresh_instances}
                matches = [x for x in other.get_instances(source.get_base_search_type()) if x.get_search_key() in keys]
                if method == 'POST':
                    if matches: raise ApiError(409, 'already_linked', 'Такая связь уже существует')
                    instance = source.add_instance(other)
                    ExpressionParser.clear_cache()
                    return {'linked': True, 'instance_key': instance.get_search_key(),
                            'direct_object_delete': False}
                count = integer(data.get('confirm_count'), 'confirm_count', 1, 5000)
                if count != len(matches):
                    raise ApiError(409, 'link_count', 'Количество записей связи изменилось; подтвердите актуальное число')
                source.remove_instance(other)
                return {'unlinked': count, 'direct_object_delete': False}
            return self._write(apply)
        raise ApiError(405, 'method', 'Недопустимая операция связи')
