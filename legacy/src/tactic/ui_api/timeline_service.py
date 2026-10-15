"""Server-paginated date windows over the original configured TACTIC Search."""
from .contracts import ApiError,clean_query,json_safe,safe_field
from tactic.core.field_policy import field_access
from tactic.core.timeline_model import append_window,date_window
import re

class TimelineService:
 def _timeline_bars(self,stype,spec,data):
  from pyasm.common import Environment
  columns=self._stub().get_column_info(stype)
  model=self._view_model(stype,spec['view']) if hasattr(self,'_view_model') else self._model(stype,spec['view'])
  security=Environment.get_security()
  visible={f['name']:f for f in spec['fields'] if f.get('storage') and not f.get('hidden')}
  manual_start=data.get('start_field');manual_end=data.get('end_field')
  if manual_start or manual_end:
   if not manual_start or not manual_end:raise ApiError(400,'date_fields','Выберите оба поля дат')
   if any(not isinstance(n,str) or n not in visible or visible[n]['kind'] not in ('date','datetime') for n in (manual_start,manual_end)):
    raise ApiError(403,'date_fields','Можно выбрать только доступные поля дат этого view')
   raw=[{'start_date_col':manual_start,'end_date_col':manual_end,'source':'selected','label':visible[manual_start]['label']+' → '+visible[manual_end]['label']}]
  else:
   raw=[dict(b,source=f['name']) for f in spec['fields'] if f.get('renderer')=='gantt' and not f.get('hidden') for b in f.get('bars',[])]
  if not raw:raise ApiError(400,'gantt_config','В представлении нет поддержанных Gantt-интервалов; выберите поля дат')
  if len(raw)>8:raise ApiError(400,'gantt_limit','Более восьми интервалов в конфигурации; нужен отдельный составной редактор')
  result=[]
  for i,b in enumerate(raw):
   for n in (b.get('start_date_col'),b.get('end_date_col')):
    if not isinstance(n,str) or not safe_field(n) or n not in columns:raise ApiError(400,'gantt_column','Дата интервала не является колонкой SearchType')
    col=columns[n];typ=str((col.get('data_type') or col.get('type') or '') if isinstance(col,dict) else col).lower()
    if typ!='date' and not any(t in typ for t in ('timestamp','datetime')):raise ApiError(400,'gantt_column_type','Поле '+n+' не является датой')
    attrs=model.describe(n)['attributes']
    if not field_access(security,self._project(),stype,n,attrs)[0]:raise ApiError(403,'gantt_field_access','Поле даты недоступно')
   color=b.get('color') or ''
   if not isinstance(color,str) or not re.fullmatch(r'#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?',color):color=''
   result.append({'id':str(i),'start_field':b['start_date_col'],'end_field':b['end_date_col'],
                  'source':b['source'],'label':str(b.get('label') or b.get('name') or b['start_date_col'])[:200],'color':color})
  return result

 def timeline(self,stype,spec,data):
  from pyasm.search import SearchType
  try:date_window(data.get('start'),data.get('end'))
  except (ValueError,TypeError) as exc:raise ApiError(400,'date_window',str(exc)) from exc
  if spec.get('sort_error'): raise ApiError(501,'configured_sort',spec['sort_error'])
  bars=self._timeline_bars(stype,spec,data)
  query=clean_query(data,spec['fields'],spec.get('default_sort'))
  search=self._query_search(stype,spec,query)
  try:window=append_window(search,bars,data['start'],data['end'],data.get('include_undated',False))
  except ValueError as exc:raise ApiError(400,'date_window',str(exc)) from exc
  total=search.get_count()
  orders=query.get('sorts') or [query['sort']]
  for order in orders: search.add_order_by(order['field'],direction=order['direction'])
  if not any(o['field']=='id' for o in orders) and SearchType.column_exists(stype,'id'):search.add_order_by('id',direction='asc')
  search.set_limit(query['limit']);search.set_offset(query['offset'])
  objects=search.get_sobjects();rows=self._serialize_many(objects,spec)
  for obj,row in zip(objects,rows):
   row['timeline']=[dict(b,start=json_safe(obj.get_value(b['start_field'],no_exception=True)),end=json_safe(obj.get_value(b['end_field'],no_exception=True))) for b in bars]
  return {'items':rows,'bars':bars,'total':total,'offset':query['offset'],'limit':query['limit'],
          'has_more':query['offset']+len(rows)<total,'window':window,
          'source':'original Search + configured view filters + date window',
          'notice':'NULL-конец — событие одного дня. Это не ресурсный планировщик. Данные перечитываются при смене периода; страницы не являются транзакционным снимком.'}
