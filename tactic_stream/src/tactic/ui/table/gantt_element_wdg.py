"""Legacy table schedule options projected to the common Frame timeline."""
import calendar
import datetime
import json
import re
from dateutil import parser
from pyasm.biz import Pipeline
from pyasm.command import DatabaseAction
from pyasm.common import TacticException, jsondumps, jsonloads
from pyasm.search import Search
from pyasm.web import WebContainer
from tactic.ui.common import BaseTableElementWdg


def _parse_action_options(action_options):
    if not action_options:
        return []
    raw = action_options.get('options')
    if raw:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(parsed, list):
            raise ValueError('Unsupported schedule action options')
        items = parsed
    else:
        items = [dict(action_options)]
    allowed = {'mode', 'prefix', 'start_date_col', 'end_date_col', 'sobjects'}
    for item in items:
        if not isinstance(item, dict) or set(item) - allowed:
            raise ValueError('Unsupported schedule action options')
        if item.get('mode') not in (None, '', 'default', 'cascade'):
            raise ValueError('Unsupported schedule action mode')
        if item.get('prefix') not in (None, '', 'bid', 'actual'):
            raise ValueError('Unsupported schedule action prefix')
        expr = item.get('sobjects')
        if expr and not re.fullmatch(r'\s*@SOBJECT\([^@;{}]*\)\s*', str(expr), re.I):
            raise ValueError('A schedule action requires an @SOBJECT expression')
    return items


def table_schedule(objects, options, action_options=None):
    if options.get('date_mode') not in (None, '', 'visible', 'hover', 'none'):
        raise ValueError('Invalid schedule date display')
    if options.get('color_mode') not in (None, '', 'process', 'status'):
        raise ValueError('Invalid schedule color mode')
    if str(options.get('week_start') or 0) not in tuple(str(i) for i in range(7)):
        raise ValueError('Invalid schedule week start')
    if int(options.get('bar_height') or 12) not in (6, 12, 18, 24):
        raise ValueError('Invalid schedule bar height')
    for size in ('width', 'cal_margin'):
        raw = options.get(size)
        if raw not in (None, '') and (not str(raw).isdecimal() or int(raw) <= 0):
            raise ValueError('Invalid schedule width')
    width_hint = int(options.get('width') or 400)

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

    handlers_raw = str(options.get('handlers') or '').strip()
    handlers = [h.strip() for h in handlers_raw.split('|') if h.strip()] if handlers_raw else []
    if any(h not in ('ScheduleGanttWdg', 'ResourceUsageGanttWdg') for h in handlers):
        raise ValueError('Unsupported Gantt handler')
    action_items = _parse_action_options(action_options)

    result, dates = {}, []
    if 'ResourceUsageGanttWdg' in handlers:
        logins = [str(obj.get_value('login', no_exception=True) or obj.get_code() or '') for obj in objects]
        task_search = Search('sthpw/task')
        task_search.add_filters('assigned', [login for login in logins if login] or [''])
        all_tasks = task_search.get_sobjects()
        for obj in objects:
            login = str(obj.get_value('login', no_exception=True) or obj.get_code() or '')
            user_tasks = [t for t in all_tasks if str(t.get_value('assigned') or '') == login]
            day_counts = {}
            for task in user_tasks:
                t_start = date_value(task.get_value('bid_start_date'))
                t_end = date_value(task.get_value('bid_end_date'))
                if not t_start or not t_end or t_start > t_end or (t_end - t_start).days > 3660:
                    continue
                cur = t_start
                while cur <= t_end:
                    day_counts[cur] = min(2, day_counts.get(cur, 0) + 1)
                    cur += datetime.timedelta(days=1)
            bars = []
            for day_key in sorted(day_counts):
                count = day_counts[day_key]
                color = '#33F' if count == 1 else '#d9534f'
                label = '1 task' if count == 1 else 'Overlapping tasks'
                if bars and bars[-1]['color'] == color and date_value(bars[-1]['end']) + datetime.timedelta(days=1) == day_key:
                    bars[-1]['end'] = str(day_key)
                else:
                    bars.append(dict(index=len(bars), searchKey=obj.get_search_key(), start=str(day_key), end=str(day_key),
                        color=color, label=label, editable=True, hidden=False, login=login))
                dates.append(day_key)
            result[obj.get_search_key()] = dict(text='', widthHint=width_hint, targetSearchKey=obj.get_search_key(),
                sourceSearchKey=obj.get_search_key(), login=login, timeline=dict(bars=bars))
    else:
        properties = json.loads(options['options']) if options.get('options') else [dict(
            sobject_expr='@SOBJECT(sthpw/task)', start_date_col='bid_start_date', end_date_col='bid_end_date', color='#888')]
        if not isinstance(properties, list) or not 1 <= len(properties) <= 32:
            raise ValueError('Configure between one and 32 schedule bars')
        allowed = {'start_date_col', 'end_date_col', 'start_date_expr', 'end_date_expr', 'sobject_expr',
                   'color', 'edit', 'default', 'hide_empty_bar', 'label'}
        for item in properties:
            if not isinstance(item, dict) or set(item) - allowed:
                raise ValueError('Unsupported schedule bar options')
        mode = options.get('color_mode') or ''
        for obj in objects:
            bars = []
            base_type = obj.get_base_search_type()
            for index, item in enumerate(properties):
                expression = item.get('sobject_expr')
                if expression and not re.fullmatch(r'\s*@SOBJECT\([^@;{}]*\)\s*', expression, re.I):
                    raise ValueError('A schedule bar requires an @SOBJECT expression')
                records = Search.eval(expression, sobjects=obj) if expression else [obj]
                records = records if isinstance(records, (list, tuple)) else [records] if records else []
                if len(bars) + len(records) > 256:
                    raise ValueError('A table row can display at most 256 schedule bars')
                act = action_items[index] if index < len(action_items) else (action_items[0] if len(action_items) == 1 else {})
                act_mode = act.get('mode') or ('cascade' if act.get('sobjects') and not act.get('mode') and (
                    item.get('start_date_expr') or item.get('end_date_expr')) else 'default')
                act_prefix = act.get('prefix') or ('actual' if 'actual' in str(item.get('start_date_col') or item.get('start_date_expr') or '') else 'bid')
                act_expr = act.get('sobjects') or expression
                parent_keys = []
                if act_mode == 'cascade' and act_expr and base_type != 'sthpw/project':
                    rel_tasks = Search.eval(act_expr, sobjects=obj)
                    rel_tasks = rel_tasks if isinstance(rel_tasks, (list, tuple)) else [rel_tasks] if rel_tasks else []
                    seen = set()
                    for rel in rel_tasks:
                        p_obj = rel.get_parent() if rel.get_base_search_type() == 'sthpw/task' else rel
                        p_key = p_obj.get_search_key() if p_obj else ''
                        if p_key and p_key not in seen:
                            seen.add(p_key)
                            parent_keys.append(p_key)
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
                    bar = dict(index=index, searchKey=record.get_search_key(), start=str(start or ''), end=str(end or ''),
                        color=str(color), label=str(item.get('label') or record.get_display_value()),
                        editable=item.get('edit') not in (False, 'false'),
                        hidden=not (start or end) and (item.get('hide_empty_bar') in (True, 'true') or item.get('default') in (False, 'false')))
                    if act:
                        bar.update(mode=act_mode, prefix=act_prefix,
                            startField=act.get('start_date_col') or item.get('start_date_col') or (act_prefix + '_start_date'),
                            endField=act.get('end_date_col') or item.get('end_date_col') or (act_prefix + '_end_date'))
                    if base_type == 'sthpw/project':
                        bar['scope'] = 'project'
                    elif parent_keys:
                        bar['parentKeys'] = parent_keys
                    bars.append(bar)
            parent = obj.get_parent() if base_type == 'sthpw/task' else None
            cell = dict(text='', widthHint=width_hint, targetSearchKey=parent.get_search_key() if parent else obj.get_search_key(),
                sourceSearchKey=obj.get_search_key(), timeline=dict(bars=bars))
            if base_type == 'sthpw/project':
                cell['scope'] = 'project'
            result[obj.get_search_key()] = cell

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
    ARGS_KEYS = dict.fromkeys(('show_title', 'options', 'range_start_date', 'range_end_date', 'overlap',
        'date_mode', 'year_display', 'week_display', 'week_start', 'bar_height', 'color_mode', 'width'), {})

    def is_editable(self):
        return False

    def preprocess(self):
        self._cells = table_schedule(self.sobjects, self.options, getattr(self, 'action_options', None))

    def get_cell_value(self):
        return self._cells[self.get_current_sobject().get_search_key()]


class GanttCbk(DatabaseAction):
    def get_title(self):
        return "Dates Changed"

    def set_sobject(self, sobject):
        self.sobject = sobject

    def execute(self):
        if not self.sobject:
            return
        value = self.get_value()
        web = WebContainer.get_web()
        gantt_data = value
        web_data = None
        if not gantt_data and web:
            gantt_data = web.get_form_value("gantt_data")
            if not gantt_data:
                web_data = web.get_form_value("web_data")
                if web_data:
                    gantt_data = web_data
        if not gantt_data:
            return

        options = self.get_option("options")
        if options:
            options_list = jsonloads(options) if isinstance(options, str) else list(options)
        else:
            options_list = [dict(self.options or {})]

        if isinstance(gantt_data, dict):
            payload = dict(gantt_data)
        elif not web_data:
            payload = jsonloads(gantt_data)
        else:
            parsed_web = jsonloads(web_data) if isinstance(web_data, str) else web_data
            if isinstance(parsed_web, list) and parsed_web:
                parsed_web = parsed_web[0]
            raw_inner = parsed_web.get('gantt_data') if isinstance(parsed_web, dict) else None
            payload = jsonloads(raw_inner) if isinstance(raw_inner, str) else (raw_inner or {})

        for key, data in payload.items():
            if key == '__data__' or str(key).startswith("_") or not isinstance(data, dict):
                continue
            index = int(data.get("index") or 0)
            try:
                bar_options = options_list[index]
            except IndexError as exc:
                raise TacticException(
                    'Missing option in the action class GanttCbk. Please check the Column Definition. '
                    'The number of action options should match the number of editable bars.'
                ) from exc

            expression = bar_options.get("sobjects") or "@SOBJECT(sthpw/task)"
            if not re.fullmatch(r'\s*@SOBJECT\([^@;{}]*\)\s*', str(expression), re.I):
                raise ValueError('A schedule action requires an @SOBJECT expression')
            prefix = bar_options.get("prefix") or 'bid'
            mode = bar_options.get("mode") or ('cascade' if bar_options.get("sobjects") and not bar_options.get("mode") and not data.get('search_key') else 'default')

            tasks = Search.eval(expression, [self.sobject])
            tasks = tasks if isinstance(tasks, (list, tuple)) else [tasks] if tasks else []
            if len(tasks) == 1 and tasks[0] is self.sobject and self.sobject.get_base_search_type() != 'sthpw/task' and 'sthpw/task' in expression:
                tasks = self.sobject.get_related_sobjects('sthpw/task')
            if not tasks and self.sobject.get_base_search_type() == 'sthpw/task':
                tasks = [self.sobject]
            task_dict = {task.get_search_key(): task for task in tasks}

            start_date_col = bar_options.get('start_date_col') or ('%s_start_date' % prefix)
            end_date_col = bar_options.get('end_date_col') or ('%s_end_date' % prefix)

            start_date = parser.parse(str(data.get('start_date')))
            end_date = parser.parse(str(data.get('end_date')))
            if start_date > end_date:
                raise ValueError('Schedule start date is after its end date')
            orig_start_raw = data.get('orig_start_date') or data.get('start_date')
            orig_end_raw = data.get('orig_end_date') or data.get('end_date')
            orig_start_date = parser.parse(str(orig_start_raw))
            orig_end_date = parser.parse(str(orig_end_raw))
            search_key = data.get('search_key') or self.sobject.get_search_key()

            colors = data.get('colors')
            labels = data.get('labels')
            has_day_data = colors is not None or labels is not None
            day_data = jsondumps({'colors': colors, 'labels': labels}) if has_day_data else None

            if mode == 'cascade':
                start_delta = start_date - orig_start_date
                end_delta = end_date - orig_end_date
                if start_delta.days == 0:
                    start_delta = end_delta
                for task in tasks:
                    raw_old_start = task.get_value(start_date_col, no_exception=True)
                    raw_old_end = task.get_value(end_date_col, no_exception=True)
                    if not raw_old_start or not raw_old_end:
                        continue
                    old_start_date = parser.parse(str(raw_old_start))
                    old_end_date = parser.parse(str(raw_old_end))
                    task.set_value(start_date_col, old_start_date + start_delta)
                    task.set_value(end_date_col, old_end_date + start_delta)
                    if day_data is not None and task.column_exists('data'):
                        task.set_value("data", day_data)
                    task.commit()
            else:
                task = task_dict.get(search_key) or (
                    self.sobject if self.sobject.get_search_key() == search_key else Search.get_by_search_key(search_key)
                )
                if task:
                    task.set_value(start_date_col, start_date)
                    task.set_value(end_date_col, end_date)
                    if day_data is not None and task.column_exists('data'):
                        task.set_value("data", day_data)
                    task.commit()


__all__ = ['table_schedule', 'GanttElementWdg', 'GanttCbk']
