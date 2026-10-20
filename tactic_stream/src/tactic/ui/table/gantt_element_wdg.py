"""Legacy table schedule options projected to the common Frame timeline."""
from tactic.ui.common import BaseTableElementWdg


def table_schedule(objects, options):
    import calendar
    import datetime
    import json
    import re
    from dateutil import parser
    from pyasm.biz import Pipeline
    from pyasm.search import Search

    if options.get('date_mode') not in (None, '', 'visible', 'hover', 'none'):
        raise ValueError('Invalid schedule date display')
    if options.get('color_mode') not in (None, '', 'process', 'status'):
        raise ValueError('Invalid schedule color mode')
    if str(options.get('week_start') or 0) not in tuple(str(i) for i in range(7)):
        raise ValueError('Invalid schedule week start')
    if int(options.get('bar_height') or 12) not in (6,12,18,24):
        raise ValueError('Invalid schedule bar height')

    def date_value(value):
        if isinstance(value, (list, tuple)):
            value = next((item for item in value if item), '')
        return parser.parse(str(value)).date() if value else None

    def read_date(record, properties, edge):
        field = properties.get(edge + '_date_col')
        expression = properties.get(edge + '_date_expr') or '@GET(.bid_' + edge + '_date)'
        if field:
            return date_value(record.get_value(field))
        if not re.fullmatch(r'\s*@(GET|MIN|MAX)\([^@;{}]*\)\s*', expression, re.I):
            raise ValueError('A table schedule requires a read-only date expression')
        return date_value(Search.eval(expression, sobjects=record))

    properties = json.loads(options['options']) if options.get('options') else [dict(
        sobject_expr='@SOBJECT(sthpw/task)', start_date_col='bid_start_date', end_date_col='bid_end_date', color='#888')]
    if not isinstance(properties, list) or not 1 <= len(properties) <= 32:
        raise ValueError('Configure between one and 32 schedule bars')
    allowed = {'start_date_col','end_date_col','start_date_expr','end_date_expr','sobject_expr',
               'color','edit','default','hide_empty_bar','label'}
    for item in properties:
        if not isinstance(item, dict) or set(item) - allowed:
            raise ValueError('Unsupported schedule bar options')
    mode = options.get('color_mode') or ''
    result, dates = {}, []
    for obj in objects:
        bars = []
        for index, item in enumerate(properties):
            expression = item.get('sobject_expr')
            if expression and not re.fullmatch(r'\s*@SOBJECT\([^@;{}]*\)\s*', expression, re.I):
                raise ValueError('A schedule bar requires an @SOBJECT expression')
            records = Search.eval(expression, sobjects=obj) if expression else [obj]
            records = records if isinstance(records, (list, tuple)) else [records] if records else []
            if len(bars) + len(records) > 256:
                raise ValueError('A table row can display at most 256 schedule bars')
            for record in records:
                start, end = read_date(record, item, 'start'), read_date(record, item, 'end')
                if start and end and start > end:
                    raise ValueError('Schedule start date is after its end date')
                dates.extend(value for value in (start, end) if value)
                color = item.get('color') or '#888'
                if mode and record.get_base_search_type() == 'sthpw/task':
                    parent = record.get_parent()
                    pipeline = Pipeline.get_by_code(record.get_value('pipeline_code') or 'task') if mode == 'status' else (
                        Pipeline.get_by_code(parent.get_value('pipeline_code')) if parent else None)
                    process = pipeline.get_process(record.get_value('status' if mode == 'status' else 'process')) if pipeline else None
                    color = process.get_color() if process and process.get_color() else color
                bars.append(dict(index=index, searchKey=record.get_search_key(), start=str(start or ''), end=str(end or ''),
                    color=str(color), label=str(item.get('label') or record.get_display_value()),
                    editable=item.get('edit') not in (False, 'false'),
                    hidden=not (start or end) and (item.get('hide_empty_bar') in (True, 'true') or item.get('default') in (False, 'false'))))
        parent = obj.get_parent() if obj.get_base_search_type() == 'sthpw/task' else None
        result[obj.get_search_key()] = dict(text='', widthHint=400, targetSearchKey=parent.get_search_key() if parent else obj.get_search_key(),
            sourceSearchKey=obj.get_search_key(), timeline=dict(bars=bars))
    start = date_value(options.get('range_start_date')) or (min(dates) if dates else datetime.date.today())
    end = date_value(options.get('range_end_date')) or (max(dates) if dates else start)
    if not options.get('range_start_date'):
        start = start.replace(day=1)
    if not options.get('range_end_date'):
        end = end.replace(day=calendar.monthrange(end.year, end.month)[1])
    if start > end or (end - start).days > 3660:
        raise ValueError('Choose a schedule range of at most ten years')
    for value in result.values():
        value['timeline'].update(start=str(start), end=str(end), dateMode=options.get('date_mode') or 'hover',
            overlap=options.get('overlap') in (True, 'true'), barHeight=int(options.get('bar_height') or 12),
            showTitle=options.get('show_title') in (True, 'true'), year=options.get('year_display') != 'none',
            week=options.get('week_display') != 'none', weekStart=int(options.get('week_start') or 0))
    return result


class GanttElementWdg(BaseTableElementWdg):
    ARGS_KEYS = dict.fromkeys(('show_title','options','range_start_date','range_end_date','overlap',
        'date_mode','year_display','week_display','week_start','bar_height','color_mode'), {})

    def is_editable(self):
        return False

    def preprocess(self):
        self._schedule = table_schedule(self.sobjects, self.options)

    def get_cell_value(self):
        return dict(self._schedule[self.get_current_sobject().get_search_key()], columnName=self.get_name())
