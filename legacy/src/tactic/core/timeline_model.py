"""Date-window projection of configured Gantt intervals, not a scheduler.

Predicates are appended to the original Search, never a replacement for its
saved filters, relationships, project scope or permissions.
"""
import re
from datetime import date, timedelta

IDENTIFIER=re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

def date_window(start,end):
 if not isinstance(start,str) or not isinstance(end,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',start) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',end):
  raise ValueError('Укажите начало и конец периода в формате YYYY-MM-DD')
 a,b=date.fromisoformat(start),date.fromisoformat(end)
 if b<a or (b-a).days>365:raise ValueError('Период должен содержать от 1 до 366 дней')
 try:exclusive=b+timedelta(days=1)
 except OverflowError as exc:raise ValueError('Конечная дата вне поддержанного диапазона') from exc
 return a.isoformat(),b.isoformat(),exclusive.isoformat()

def _day_bound(search, field, day, operator):
 # Select.add_filter converts timestamp strings through SPTDate/TZLOCAL even
 # with quoted=True. These are CALENDAR-DAY boundaries, not UTC instants.
 # A validated day literal also includes SQLite date-only and midnight values
 # consistently with the displayed ISO date prefix. Existing view predicates
 # still use the original Search/Select normalization unchanged.
 from pyasm.search import Sql
 table = search.get_search_type_obj().get_table()
 if not IDENTIFIER.fullmatch(table):
  raise ValueError('Имя таблицы не поддерживается дневной проекцией')
 search.add_where('"%s"."%s" %s %s' % (table, field, operator, Sql.quote(day)))

def append_window(search,bars,start,end,include_undated=False):
 start,end,exclusive=date_window(start,end)
 if not isinstance(include_undated,bool):raise ValueError('include_undated должен быть boolean')
 if not bars or len(bars)>8:raise ValueError('Поддерживается от 1 до 8 интервалов из конфигурации')
 search.add_op('begin')
 for bar in bars:
  a,b=bar['start_field'],bar['end_field']
  if not IDENTIFIER.fullmatch(a) or not IDENTIFIER.fullmatch(b):raise ValueError('Некорректное поле даты')
  search.add_op('begin')
  _day_bound(search,a,exclusive,'<')
  search.add_op('begin')
  _day_bound(search,b,start,'>=')
  # A missing end is a one-day marker, not an unbounded interval.
  search.add_op('begin');search.add_filter(b,None);_day_bound(search,a,start,'>=');search.add_op('and')
  search.add_op('or');search.add_op('and')
 if include_undated:
  search.add_op('begin')
  for bar in bars:search.add_filter(bar['start_field'],None)
  search.add_op('and')  # include wholly undated records only, once per record
 search.add_op('or')
 return {'start':start,'end':end,'exclusive_end':exclusive}
