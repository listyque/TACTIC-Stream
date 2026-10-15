"""Handler time entry operations, using native WorkHour and transactions."""
import datetime
import hashlib
import json

from pyasm.biz import Project, ProjectSetting, Task, WorkHour
from pyasm.biz.work_hour import hours_value
from pyasm.command import Command
from pyasm.common import Environment, SecurityException, UserException
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin
from .task_inspector import task_scope
from .task_element_wdg import TaskElementWdg


REPORTS = [
    dict(value='my_hours', label='My Work Hours', description='Daily logged time'),
    dict(value='bid_actual', label='Bid vs Actual', description='Planned and logged hours'),
    dict(value='approval', label='Approval', description='Approved and pending time'),
    dict(value='team', label='Team Hours', description='Hours by user'),
    dict(value='process', label='Process Hours', description='Hours by process'),
    dict(value='labor_cost', label='Labor Cost', description='Authorized wage-based cost'),
]


def entry_record(entry):
    return dict(search_key=entry.get_search_key(), day=str(entry.get_value('day'))[:10],
        login=entry.get_value('login'), category=entry.get_value('category') or 'regular',
        hours=float(entry.get_total_hours()), overtime=float(entry.get_overtime_hours()),
        status='approved' if entry.is_approved() else 'pending', description=entry.get_value('description'),
        start_time=str(entry.get_value('start_time') or ''), end_time=str(entry.get_value('end_time') or ''))


def week_bounds(value):
    try:
        start = datetime.date.fromisoformat(str(value))
        start -= datetime.timedelta(days=start.weekday())
        end = start+datetime.timedelta(days=7)
    except (ValueError, OverflowError):
        raise UserException('Choose a valid week') from None
    return start, end


def week_entries(start, end, login=None):
    if login is not None and (not isinstance(login, str) or len(login) > 256):
        raise UserException('Choose a valid timesheet user')
    search = Search('sthpw/work_hour'); search.add_filter('project_code', Project.get_project_code())
    search.add_filter('day', str(start), op='>='); search.add_filter('day', str(end), op='<')
    if login:
        search.add_filter('login', login)
    search.add_order_by('day desc'); search.add_order_by('start_time desc'); search.add_order_by('code')
    return [entry for entry in search.get_sobjects() if TaskElementWdg.can_view_process(entry.get_value('process'))]


def weekly_hours(start, end, login, selected_task=None):
    entries = week_entries(start, end, login)
    codes = list({entry.get_value('task_code') for entry in entries if entry.get_value('task_code')})
    tasks = Search('sthpw/task'); tasks.add_filter('project_code', Project.get_project_code()); tasks.add_filters('code', codes)
    tasks = {task.get_code(): task for task in tasks.get_sobjects()}
    # Include the active task outside this week/user too: repeated create must
    # invalidate the revision even if the new record leaves the current filter.
    active = task_hours(selected_task)['revision'] if selected_task else ''
    revision = hashlib.sha256(json.dumps(dict(project=Project.get_project_code(), start=str(start), login=login,
        entries=[entry.get_data() for entry in entries], tasks={code: task.get_data() for code, task in sorted(tasks.items())},
        active=active), sort_keys=True, default=str).encode()).hexdigest()
    records = []
    for entry in entries:
        task = tasks.get(entry.get_value('task_code'))
        records.append(dict(entry_record(entry), task_key=task.get_search_key() if task else '',
            parent_key=task.get_parent_search_key() if task else '', task_title=entry.get_value('task_code'),
            process=entry.get_value('process'), can_edit=bool(task)))
    totals = dict(logged=sum((item.get_total_hours() for item in entries), hours_value(0)),
        approved=sum((item.get_total_hours() for item in entries if item.is_approved()), hours_value(0)),
        overtime=sum((item.get_overtime_hours() for item in entries), hours_value(0)))
    totals['pending'] = totals['logged']-totals['approved']
    users = Search('sthpw/login'); users.add_order_by('display_name')
    users = [dict(value=user.get_value('login'), label=user.get_value('display_name') or user.get_value('login')) for user in users.get_sobjects()]
    result = dict(entries=records, revision=revision, week_start=str(start), week_end=str(end-datetime.timedelta(days=1)),
        login=login, users=users, summary={name: float(value.quantize(hours_value('0.01'))) for name, value in totals.items()})
    return result, entries, tasks


def work_report(start, end, login, key):
    if key not in {report['value'] for report in REPORTS}:
        raise UserException('Choose a work hours report')
    # Unlike the original procedure, count legacy regular+over_time as well,
    # and include the whole Sunday instead of an inclusive midnight boundary.
    entries = week_entries(start, end, (login or Environment.get_user_name()) if key == 'my_hours' else None)
    rows = {}; message = ''; localized = key in ('bid_actual', 'approval')
    rates = {}
    if key == 'labor_cost':
        if not Environment.get_security().check_access('sobject_column',
                dict(search_type='sthpw/login', column='hourly_wage', project=Project.get_project_code()), 'view'):
            raise SecurityException('Hourly wages are not accessible')
        users = Search('sthpw/login'); users.add_filters('login', list({entry.get_value('login') for entry in entries}))
        rates = {user.get_value('login'): hours_value(user.get_value('hourly_wage')) for user in users.get_sobjects()}
        if not any(rates.values()):
            message = 'No authorized hourly wages are configured.'
    if key == 'bid_actual':
        tasks = Search('sthpw/task'); tasks.add_filter('project_code', Project.get_project_code())
        tasks.add_filter('bid_end_date', str(start), op='>='); tasks.add_filter('bid_end_date', str(end), op='<')
        planned = sum((hours_value(task.get_value('bid_duration')) for task in tasks.get_sobjects()
                       if TaskElementWdg.can_view_process(task.get_value('process'))), hours_value(0))
        rows['Planned'] = planned/60 if ProjectSetting.get_value_by_key('bid_duration_unit') == 'minute' else planned
        rows['Logged'] = sum((entry.get_total_hours() for entry in entries), hours_value(0))
    else:
        for entry in entries:
            if key == 'approval':
                label = 'Approved' if entry.is_approved() else 'Pending'
            elif key in ('team', 'labor_cost'):
                label = entry.get_value('login') or 'Unassigned'
            elif key == 'process':
                label = entry.get_value('process') or 'Unspecified'
            else:
                label = str(entry.get_value('day'))[:10]
            value = entry.get_total_hours()
            if key == 'labor_cost':
                value *= rates.get(entry.get_value('login'), 0)
            rows[label] = rows.get(label, hours_value(0))+value
    total = sum(rows.values(), hours_value(0))
    can_view_costs = Environment.get_security().check_access('sobject_column',
        dict(search_type='sthpw/login', column='hourly_wage', project=Project.get_project_code()), 'view')
    return dict(report=key, reports=[report for report in REPORTS if can_view_costs or report['value'] != 'labor_cost'],
        week_start=str(start), week_end=str(end-datetime.timedelta(days=1)), message=message, unit='cost' if key == 'labor_cost' else 'hours',
        rows=[dict(label=label, value=float(value.quantize(hours_value('0.01'))), localized=localized,
                   share=float(value/total) if total else 0) for label, value in sorted(rows.items(), key=lambda item: item[1], reverse=True)])


def task_hours(task):
    search = Search('sthpw/work_hour')
    search.add_filter('project_code', Project.get_project_code())
    search.add_filter('task_code', task.get_code())
    search.add_order_by('day desc'); search.add_order_by('code')
    entries = search.get_sobjects()
    revision = hashlib.sha256(json.dumps(dict(task=task.get_data(), entries=[entry.get_data() for entry in entries]),
        sort_keys=True, default=str).encode()).hexdigest()
    return dict(summary=WorkHour.get_summary(task, entries), revision=revision,
        entries=[entry_record(entry) for entry in entries])


class WorkHoursCmd(Command):
    def check_security(self):
        _require_admin()
        return True

    def execute(self):
        _require_admin()  # Same admin-only scope as the configured UI.
        action = self.kwargs.get('action', 'read')
        mode = self.kwargs.get('mode', 'task')
        if mode not in ('task', 'week', 'report') or mode == 'report' and action != 'read':
            raise UserException('Unsupported timesheet mode')
        if mode in ('week', 'report'):
            start, end = week_bounds(self.kwargs.get('week'))
            login = self.kwargs.get('login', Environment.get_user_name())
            if not isinstance(login, str) or len(login) > 256:
                raise UserException('Choose a valid timesheet user')
            if mode == 'report':
                return work_report(start, end, login, self.kwargs.get('report', 'my_hours'))
        if action not in ('read', 'create', 'update', 'delete', 'approve', 'reject'):
            raise UserException('Unsupported time entry operation')
        if action != 'read':
            search = Search('sthpw/work_hour'); sql = search.get_sql()
            # ponytail: table lock serializes daily limits; row locks if time-entry writes contend.
            sql.get_database_impl().lock_collection_table(sql, SearchType.get('sthpw/work_hour').get_table())
        parent = task = None; process = ''; selected_task = None
        if mode == 'task' or self.kwargs.get('task_key'):
            parent, process, _tasks, task, _defaults, _revision, pipeline = task_scope(
                self.kwargs.get('search_key'), self.kwargs.get('process'), self.kwargs.get('task_key', ''))
            node = pipeline.get_process(process) if pipeline else None
            if task is None or node and node.get_type() == 'progress':
                raise UserException('Choose an existing task')
            selected_task = task
        if mode == 'week':
            result, entries, tasks = weekly_hours(start, end, login, selected_task)
        else:
            result = task_hours(task)
        if action == 'read':
            return result
        if self.kwargs.get('expected_revision') != result['revision']:
            raise UserException('Time entries changed. Reload before saving.')
        if mode == 'week' and action in ('approve', 'reject'):
            keys = self.kwargs.get('entry_keys', [self.kwargs.get('entry_key')])
            if not isinstance(keys, list) or not 1 <= len(keys) <= 1000 or any(not isinstance(key, str) for key in keys):
                raise UserException('Choose time entries to change')
            keys = set(keys)
            matched = [entry for entry in entries if entry.get_search_key() in keys]
            if len(matched) != len(keys):
                raise UserException('Some time entries are outside the selected week or user')
            for entry in matched:
                entry.set_value('status', 'approved' if action == 'approve' else 'pending'); entry.commit()
            return weekly_hours(start, end, login, selected_task)[0]
        entry = Search.get_by_search_key(self.kwargs.get('entry_key')) if self.kwargs.get('entry_key') else None
        if mode == 'week' and action != 'create':
            if not isinstance(entry, WorkHour) or entry.get_id() not in {item.get_id() for item in entries}:
                raise UserException('Some time entries are outside the selected week or user')
            if action == 'delete':
                entry.delete(); return weekly_hours(start, end, login, selected_task)[0]
            task = tasks.get(entry.get_value('task_code'))
            if task is None:
                raise UserException('Choose an existing task')
            parent, process, _tasks, task, _defaults, _revision, _pipeline = task_scope(task.get_search_key(), task.get_value('process'))
        if action == 'create' and task is None:
            raise UserException('Choose an existing task')
        if action != 'create' and (not isinstance(entry, WorkHour) or
                entry.get_value('task_code') != task.get_code() or entry.get_value('project_code') != Project.get_project_code()):
            raise UserException('Time entry does not belong to this task')
        if action == 'create' and entry is not None:
            raise UserException('Unexpected time entry')
        if action == 'delete':
            entry.delete()
        elif action in ('approve', 'reject'):
            entry.set_value('status', 'approved' if action == 'approve' else 'pending'); entry.commit()
        else:
            data = self.kwargs.get('data')
            if not isinstance(data, dict) or set(data) - {'day', 'hours', 'category', 'login', 'description', 'approve'}:
                raise UserException('Unsupported time entry fields')
            try:
                day = datetime.date.fromisoformat(str(data.get('day')))
            except ValueError:
                raise UserException('Choose a valid time entry date') from None
            duration = hours_value(data.get('hours'))
            if not 0 < duration <= 24 or duration != duration.quantize(hours_value('0.01')):
                raise UserException('Hours must be between 0.01 and 24')
            category = data.get('category', 'regular')
            if category not in ('regular', 'overtime'):
                raise UserException('Choose regular or overtime hours')
            entry_login = data.get('login')
            if entry_login is not None and not isinstance(entry_login, str):
                raise UserException('Choose an existing user')
            entry_login = entry_login or Environment.get_user_name()
            if Search.get_by_code('sthpw/login', entry_login) is None:
                raise UserException('Choose an existing user')
            description = data.get('description', '')
            description = '' if description is None else description
            if not isinstance(description, str) or len(description.encode()) > 1024*1024:
                raise UserException('Time entry description must be text no larger than 1 MiB')
            if not isinstance(data.get('approve', False), bool):
                raise UserException('Invalid time entry approval')
            daily = Search('sthpw/work_hour'); daily.add_filter('project_code', Project.get_project_code())
            daily.add_filter('login', entry_login); daily.add_filter('day', str(day), op='>=')
            daily.add_filter('day', str(day+datetime.timedelta(days=1)), op='<')
            total = sum((item.get_total_hours() for item in daily.get_sobjects()
                         if entry is None or item.get_id() != entry.get_id()), hours_value(0))
            if total+duration > 24:
                raise UserException('Daily work hours cannot exceed 24')
            if entry is None:
                entry = SearchType.create('sthpw/work_hour'); entry.set_parent(parent)
                entry.set_value('task_code', task.get_code()); entry.set_value('process', process)
                entry.set_value('project_code', Project.get_project_code()); entry.set_value('status', 'pending')
            for name, value in dict(day=str(day)+' 00:00:00', login=entry_login, category=category,
                    straight_time=float(duration), over_time=float(duration) if category == 'overtime' else 0,
                    description=description).items():
                entry.set_value(name, value)
            if data.get('approve'):
                entry.set_value('status', 'approved')
            entry.commit()
        return weekly_hours(start, end, login, selected_task)[0] if mode == 'week' else task_hours(task)
