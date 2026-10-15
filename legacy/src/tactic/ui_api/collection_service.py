"""Native collection tools over original _is_collection / *_in_* storage."""
from .contracts import ApiError, clean_values, revision, text
from .upload_store import integer


class CollectionService:
    def _collection_source(self, data):
        from pyasm.search import SearchType
        target = self.open_target(data.get('target'))
        if target['kind'] not in ('table', 'form', 'collections'):
            raise ApiError(400, 'collection_target', 'Виджет не определяет SearchType коллекций')
        stype = target.get('search_type')
        self.require_type(stype)
        if stype.startswith(('sthpw/', 'config/')) or len(stype.split('/')) != 2:
            raise ApiError(501, 'collection_type', 'Поддержаны коллекции проектных SearchType')
        namespace, table = stype.split('/')
        junction = f'{namespace}/{table}_in_{table}'
        if not all(SearchType.column_exists(stype, f) for f in ('_is_collection','code','name')):
            raise ApiError(501, 'collection_schema', 'SearchType не включает штатную поддержку коллекций')
        if not SearchType.get(junction) or not all(SearchType.column_exists(junction,f) for f in ('parent_code','search_code')):
            raise ApiError(501, 'collection_schema', 'Отсутствует исходная таблица связей коллекций')
        options = target.get('options', {})
        if options.get('expression') or options.get('parent_key'):
            raise ApiError(501, 'collection_options', 'Expression/parent-scoped коллекции требуют отдельного переноса')
        return target, stype, junction

    def _collection(self, stype, key):
        obj = self._object(stype, key)
        if obj.get_value('_is_collection', no_exception=True) not in (True, 1, 'true', 't'):
            raise ApiError(400, 'not_collection', 'Запись не является коллекцией')
        if obj.is_retired():
            raise ApiError(409, 'collection_retired', 'Коллекция находится в архиве')
        return obj

    def _collection_links(self, junction, code, incoming=False):
        from pyasm.search import Search
        search = Search(junction)
        search.add_filter('search_code' if incoming else 'parent_code', code)
        search.add_order_by('id'); search.set_limit(10001)
        rows = search.get_sobjects()
        if len(rows) > 10000:
            raise ApiError(413, 'collection_size', 'Более 10000 связей; операция не выполнена')
        return rows

    def _collection_state(self, collection, junction):
        outgoing = self._collection_links(junction, collection.get_code())
        incoming = self._collection_links(junction, collection.get_code(), True)
        token = revision({'object': collection.get_sobject_dict(),
                          'out': [r.get_sobject_dict() for r in outgoing],
                          'in': [r.get_sobject_dict() for r in incoming]})
        return outgoing, incoming, token

    @staticmethod
    def _collection_item(obj):
        fields = ('code','name','description','keywords','_is_collection','s_status')
        return {'key': obj.get_search_key(), 'values': {f:obj.get_value(f,no_exception=True) for f in fields},
                'revision': revision(obj.get_sobject_dict())}

    def _collection_create_form(self, stype):
        spec = self.view(stype, 'edit_collection', {'native_form': True})
        # The fixed collection marker is a server invariant, not a client edit.
        spec['fields'] = [f for f in spec['fields'] if f['name'] not in ('is_collection','_is_collection','add_to_collection')]
        return {'spec': spec, 'record': None, 'values': {}}

    def collection_operation(self, method, path, data):
        from pyasm.search import Search, SearchType
        from tactic.core.collection_commands import CollectionAddCmd, CollectionRemoveCmd, CollectionDeleteCmd
        target, stype, junction = self._collection_source(data)
        options = target.get('options', {})
        fixed_key = options.get('collection_key')
        chosen = data.get('collection') or fixed_key
        if fixed_key and chosen != fixed_key:
            raise ApiError(403, 'collection_scope', 'Конфигурация фиксирует конкретную коллекцию')
        if path == '/collections' and method == 'GET':
            search = Search(stype)
            mode = data.get('mode', 'collections')
            if mode not in ('collections', 'records'): raise ApiError(400,'collection_mode','Некорректный режим списка')
            if mode == 'collections': search.add_filter('_is_collection', True)
            if fixed_key and mode == 'collections':
                selected = self._collection(stype, fixed_key); search.add_filter('code', selected.get_code())
            keyword = text(data.get('keyword', ''), 'keyword', 200, empty=True)
            if keyword:
                # Same portable query compiler as normal native Search, not SQL interpolation.
                from tactic.core.query_model import apply_tree
                apply_tree(search, {'op':'and','children':[{'field':'name','op':'contains','value':keyword}]},
                           [{'name':'name','storage':True,'kind':'text','read_only':True}])
            offset = integer(data.get('offset',0), 'offset',0,1000000)
            limit = integer(data.get('limit',40), 'limit',1,100)
            total = search.get_count(); search.add_order_by('name'); search.add_order_by('id')
            search.set_offset(offset); search.set_limit(limit)
            rows = [self._collection_item(o) for o in search.get_sobjects()]
            return {'items':rows,'total':total,'offset':offset,'limit':limit,'has_more':offset+len(rows)<total,
                    'can_write': self.allow_writes, 'can_create': self.allow_writes and options.get('show_collection_shelf', 'true') not in (False, 'false'),
                    'fixed_collection': self._collection_item(self._collection(stype,fixed_key)) if fixed_key else None,
                    'records_target': target['id'] + '/~collection-items' if target['kind']=='collections' and not fixed_key else (target['id'] if target['kind']=='table' else None),
                    'search_type':stype, 'instance_type':junction,
                    'create_form':self._collection_create_form(stype),
                    'notice':'Штатные _is_collection и *_in_*; объекты не копируются в отдельное хранилище.'}
        if path == '/collection-members' and method == 'GET':
            collection = self._collection(stype, chosen)
            outgoing, incoming, token = self._collection_state(collection, junction)
            codes = {r.get_value('search_code') for r in outgoing}
            offset = integer(data.get('offset',0),'offset',0,1000000)
            limit = integer(data.get('limit',40),'limit',1,100)
            # A subselect avoids huge IN lists; load/count through original Search.
            search = Search(stype)
            # Original Search supports relationship-through-instance. Explicit
            # subselect preserves missing/duplicate junction diagnostics separately.
            sub = Search(junction); sub.add_filter('parent_code',collection.get_code())
            sub.add_column('search_code')
            search.add_filter('code','('+sub.get_statement()+')',op='in',quoted=False)
            search.set_show_retired(True)
            total=search.get_count();search.add_order_by('name');search.add_order_by('id');search.set_offset(offset);search.set_limit(limit)
            rows=[self._collection_item(o) for o in search.get_sobjects()]
            return {'collection':self._collection_item(collection),'items':rows,'total':total,'offset':offset,'limit':limit,
                    'has_more':offset+len(rows)<total,'revision':token,'links':len(outgoing),'parents':len(incoming),
                    'duplicate_links':len(outgoing)-len(codes),'missing_members':len(codes)-total,
                    'can_write':self.allow_writes,'notice':'Удаление из коллекции удаляет только исходную instance-связь.'}
        if path == '/collections' and method == 'POST':
            if options.get('show_collection_shelf', 'true') in (False, 'false'):
                raise ApiError(403,'collection_shelf','Создание коллекций выключено исходной конфигурацией')
            form=self._collection_create_form(stype)
            values=clean_values(data.get('values'),form['spec']['fields'])
            if not str(values.get('name','')).strip():
                raise ApiError(400,'collection_name','Введите название коллекции')
            def create():
                from tactic.core.native_edit import NativeEditCmd
                parent=self._collection(stype,chosen) if chosen else None
                if parent and self._collection_state(parent,junction)[2]!=data.get('revision'):
                    raise ApiError(409,'conflict','Родительская коллекция изменилась')
                obj=SearchType.create(stype)
                obj.set_value('_is_collection',True)
                cmd=NativeEditCmd(sobject=obj,view='edit_collection',data=values,
                                  extra_data={'_is_collection':True},input_prefix='__NONE__')
                cmd.execute();obj=cmd.get_sobject()
                if parent:
                    add=CollectionAddCmd(collection_keys=[parent.get_search_key()],search_keys=[obj.get_search_key()])
                    add.execute()
                    if add.info.get('message',{}).get('circular'):
                        raise ApiError(409,'collection_cycle','Обнаружен цикл коллекций')
                return {'created':True,'collection':self._collection_item(obj),'operation':'NativeEditCmd(edit_collection)'}
            return self._write(create)
        if path == '/collection-change' and method == 'POST':
            action=data.get('action')
            if action not in ('add','remove','delete'):
                raise ApiError(400,'collection_action','Выберите add, remove или delete')
            keys=data.get('keys',[])
            if action!='delete' and (not isinstance(keys,list) or not 1<=len(keys)<=100 or any(not isinstance(k,str) for k in keys) or len(set(keys))!=len(keys)):
                raise ApiError(400,'collection_keys','От 1 до 100 разных объектов одной таблицы')
            if action=='delete' and data.get('confirm')!='DELETE_COLLECTION':
                raise ApiError(400,'confirmation','Удаление самой коллекции требует подтверждения')
            def change():
                collection=self._collection(stype,chosen)
                outgoing,incoming,token=self._collection_state(collection,junction)
                if token!=data.get('revision'):raise ApiError(409,'conflict','Коллекция или её связи изменились')
                if action=='delete':
                    cmd=CollectionDeleteCmd(collection_key=collection.get_search_key())
                else:
                    objects=[self._object(stype,key) for key in keys]
                    if any(o.is_retired() for o in objects) and action=='add':
                        raise ApiError(409,'archived_member','Архивные записи нельзя добавить')
                    if action=='add':
                        cmd=CollectionAddCmd(collection_keys=[collection.get_search_key()],search_keys=keys)
                    else:
                        existing={r.get_value('search_code') for r in outgoing}
                        if any(o.get_code() not in existing for o in objects):
                            raise ApiError(409,'missing_member','Один из объектов уже отсутствует в коллекции')
                        cmd=CollectionRemoveCmd(collection_key=collection.get_search_key(),search_keys=keys)
                cmd.execute()
                if cmd.info.get('message',{}).get('circular'):
                    raise ApiError(409,'collection_cycle','Нельзя вложить коллекцию в саму себя или своего потомка')
                return {'changed':True,'operation':type(cmd).__name__,'deleted_member_objects':False}
            return self._write(change)
        raise ApiError(405,'method','Операция коллекции не поддерживается')
