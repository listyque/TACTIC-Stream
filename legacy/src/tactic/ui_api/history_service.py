"""Read original history tables; retire/reactivate via original SObject methods."""
from .contracts import ApiError, integer, json_safe, text

HISTORY_SOURCES = {
    'status': ('sthpw/status_log', ('login','timestamp','from_status','to_status')),
    'changes': ('sthpw/sobject_log', ('login','timestamp','action','transaction_log_id')),
    'retire': ('sthpw/retire_log', ('login','timestamp')),
}


class HistoryService:
    def _can_retire(self, stype):
        from pyasm.search import SearchType
        if stype.startswith(('sthpw/', 'config/')) or not self.allow_writes:
            return False
        obj = SearchType.get(stype)
        column = obj.get_retire_col()
        return bool(column and SearchType.column_exists(stype, column))

    def history_operation(self, method, path, data):
        from pyasm.search import Search, SearchType
        opened = self.open_target(text(data.get('target'), 'target', 4000))
        if opened['kind'] not in ('table','form'):
            raise ApiError(400,'record_source','История открывается из записи')
        stype = opened['search_type']
        obj = self._object(stype, text(data.get('key'), 'key', 1500))
        if path == '/record-state':
            if method == 'GET':
                return {'retired': obj.is_retired(), 'can_write': self._can_retire(stype),
                        'revision': self._serialize(obj, opened['spec'])['revision']}
            if method == 'POST':
                action = data.get('action')
                if action not in ('retire','reactivate'):
                    raise ApiError(400,'action','Выберите retire или reactivate')
                if data.get('confirm') != action.upper():
                    raise ApiError(400,'confirmation','Нужно явное подтверждение операции')
                return self._set_record_state(stype,obj.get_search_key(),data.get('revision'),opened['spec'],action)
        if path == '/history' and method == 'GET':
            source = data.get('source', 'changes')
            if source not in HISTORY_SOURCES: raise ApiError(400,'history_source','Неизвестный вид истории')
            log_type, fields = HISTORY_SOURCES[source]
            if source == 'status' and stype not in ('sthpw/task','config/process_state'):
                return {'items': [], 'total': 0, 'offset': 0, 'limit': 100,
                        'notice': 'Штатная status_log в этом UI относится к задачам и состояниям процессов'}
            offset = integer(int(data.get('offset',0)),'offset',0,1000000)
            limit = integer(int(data.get('limit',100)),'limit',1,200)
            search = Search(log_type)
            if source == 'retire':
                # RetireLog.create uses source's full type and either code or id.
                search.add_filter('search_type', obj.get_search_type())
                by_code = SearchType.column_exists(log_type,'search_code') and bool(obj.get_code())
                by_id = SearchType.column_exists(log_type,'search_id')
                if not by_code and not by_id:
                    raise ApiError(501, 'history_schema', 'В retire_log нет ключа для безопасного отбора истории объекта')
                search.add_op('begin')
                if by_code:
                    search.add_filter('search_code',obj.get_code())
                if by_id:
                    search.add_filter('search_id',obj.get_id())
                search.add_op('or')
            else:
                search.add_relationship_filter(obj)
            total = search.get_count()
            search.add_order_by('timestamp',direction='desc');search.add_order_by('id',direction='desc')
            search.set_offset(offset);search.set_limit(limit)
            return {'items': [{'key': row.get_search_key(), **{f:json_safe(row.get_value(f,no_exception=True)) for f in fields}}
                              for row in search.get_sobjects()], 'total':total, 'offset':offset, 'limit':limit,
                    'source':log_type,'notice':'Исходный журнал TACTIC. Секреты и произвольное содержимое transaction_log не выдаются.'}
        raise ApiError(405,'method','Недопустимая операция истории')

    def _set_record_state(self, stype, key, expected, spec, action):
        if not self._can_retire(stype):
            raise ApiError(403,'read_only','Архивирование системного типа или запись отключены')
        def apply():
            obj=self._object(stype,key)
            if obj.get_project_code()!=self._project():
                raise ApiError(403,'project_scope','Откройте проект объекта')
            if self._serialize(obj,spec)['revision']!=expected:
                raise ApiError(409,'conflict','Запись изменилась; перечитайте её')
            if obj.is_retired() == (action=='retire'):
                raise ApiError(409,'record_state','Запись уже находится в этом состоянии')
            # Do not replace this with update(s_status): retire produces its own
            # log, messages and retire/change events in upstream TACTIC.
            if action=='retire':obj.retire()
            else:obj.reactivate()
            return {'key':obj.get_search_key(),'retired':obj.is_retired(),
                    'revision':self._serialize(obj,spec)['revision'],
                    'operation':'SObject.'+action,'deleted':False}
        return self._write(apply)

    def retire(self, stype, key, expected, spec):
        return self._set_record_state(stype,key,expected,spec,'retire')
