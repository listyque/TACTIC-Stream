"""Task calendar/Gantt calculations copied from Tactic Handler (EPL-1.0).

Sources: thlib/ui/task_data.py and thlib/ui/task_workspace/gantt_schedule.py.
Pure projections/transformations; persistence remains in TaskWorkspaceEditCmd.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta

from pyasm.command import Command
from pyasm.security.security import _require_admin

def parse_datetime(value):
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("T", " ").rstrip("Z")
    for candidate in (normalized, normalized[:19], normalized[:10]):
        for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(candidate, pattern)
            except ValueError:
                continue
    return None


def progress_value(info):
    value = info.get("progress") or info.get("completion") or 0
    try:
        return max(0, min(100, int(float(str(value).rstrip("%")))))
    except (TypeError, ValueError):
        return 0


def due_state(value, today=None):
    parsed = parse_datetime(value)
    if not parsed:
        return "unscheduled"
    current = today or date.today()
    due = parsed.date()
    if due < current:
        return "overdue"
    if due == current:
        return "today"
    if (due - current).days <= 3:
        return "soon"
    return "scheduled"


def calendar_cells(year, month, records, today=None, milestones=None):
    """Build a fixed six-week month projection from loaded task records."""
    tasks_by_day = {}
    for record in records:
        parsed = parse_datetime(record.get("end"))
        if not parsed:
            continue
        key = parsed.date().isoformat()
        tasks_by_day.setdefault(key, []).append({
            "taskCode": str(record.get("taskCode") or ""),
            "parentKey": str(record.get("parentKey") or ""),
            "parentTitle": str(record.get("parentTitle") or "sObject"),
            "process": str(record.get("process") or ""),
            "processLabel": str(
                record.get("processLabel") or record.get("process") or "Task"
            ),
            "status": str(record.get("status") or "No status"),
            "statusColor": str(
                record.get("statusColor")
                or record.get("processColor")
                or "#607d8b"
            ),
            "assignedLabel": str(
                record.get("assignedLabel") or "Not assigned"
            ),
            "dueState": str(record.get("dueState") or "scheduled"),
            "selected": bool(record.get("selected")),
        })

    for tasks in tasks_by_day.values():
        tasks.sort(key=lambda task: (
            task["dueState"] != "overdue",
            task["parentTitle"].casefold(),
            task["processLabel"].casefold(),
        ))

    milestones_by_day = {}
    for source in milestones or []:
        due = parse_datetime(source.get("dueDate") or source.get("due_date"))
        if not due:
            continue
        key = due.date().isoformat()
        milestones_by_day.setdefault(key, []).append({
            "code": str(source.get("code") or source.get("value") or ""),
            "label": str(
                source.get("label")
                or source.get("description")
                or "Milestone"
            ),
            "completion": int(source.get("completion") or 0),
            "taskCount": int(source.get("taskCount") or 0),
        })

    first_weekday, days_in_month = calendar.monthrange(year, month)
    start = date(year, month, 1).toordinal() - first_weekday
    current = today or date.today()
    result = []
    for offset in range(42):
        value = date.fromordinal(start + offset)
        key = value.isoformat()
        tasks = tasks_by_day.get(key, [])
        day_milestones = milestones_by_day.get(key, [])
        overdue_count = sum(
            task["dueState"] == "overdue" for task in tasks
        )
        result.append({
            "date": key,
            "day": value.day,
            "inMonth": value.month == month,
            "today": value == current,
            "taskCount": len(tasks),
            "overdueCount": overdue_count,
            "tasks": tasks,
            "milestoneCount": len(day_milestones),
            "milestones": day_milestones,
            "selected": False,
        })
    return result


def gantt_layout(records, today=None, milestones=None):
    """Build flat Gantt geometry from already filtered task records."""
    current = today or date.today()
    scheduled = []
    unscheduled = []
    drawable = []
    starts = []
    ends = []
    milestone_sources = []
    for source in milestones or []:
        value = parse_datetime(source.get("dueDate") or source.get("due_date"))
        code = str(source.get("value") or source.get("code") or "")
        if not code or not value:
            continue
        milestone_sources.append((source, value.date()))
        starts.append(value.date())
        ends.append(value.date())

    for source in records:
        record = dict(source)
        start_value = parse_datetime(record.get("start"))
        end_value = parse_datetime(record.get("end"))
        issue = ""
        if not start_value and not end_value:
            issue = "Start and deadline are not set"
        elif not start_value:
            issue = "Start is not set"
        elif not end_value:
            issue = "Deadline is not set"
        elif end_value.date() < start_value.date():
            issue = "Deadline precedes start"

        section_scheduled = source.get("_ganttSectionScheduled")
        if section_scheduled is None:
            section_scheduled = not issue
        section = "scheduled" if section_scheduled else "unscheduled"

        record.update({
            "ganttScheduled": not issue,
            "ganttStartDay": 0,
            "ganttDurationDays": 0,
            "ganttStartLabel": (
                start_value.date().isoformat() if start_value else ""
            ),
            "ganttEndLabel": end_value.date().isoformat() if end_value else "",
            "ganttIssue": issue,
            "ganttColor": str(
                record.get("statusColor") or record.get("processColor") or ""
            ),
            "ganttSection": section,
            "ganttSectionFirst": False,
            "ganttWarning": "",
            "ganttGroupStartDay": 0,
            "ganttGroupDurationDays": 0,
            "ganttGroupProgress": 0,
        })
        if section_scheduled:
            scheduled.append(record)
        else:
            unscheduled.append(record)
        if not issue:
            starts.append(start_value.date())
            ends.append(end_value.date())
            drawable.append(record)

    if starts:
        range_start = min(starts)
        range_start -= timedelta(days=range_start.weekday() + 7)
        range_end = max(ends)
        range_end += timedelta(days=(6 - range_end.weekday()) + 7)
    else:
        range_start = current - timedelta(days=current.weekday() + 7)
        range_end = range_start + timedelta(days=41)
    if (range_end - range_start).days < 27:
        range_end = range_start + timedelta(days=27)

    for record in drawable:
        start_value = parse_datetime(record["start"]).date()
        end_value = parse_datetime(record["end"]).date()
        record["ganttStartDay"] = (start_value - range_start).days
        record["ganttDurationDays"] = (end_value - start_value).days + 1

    warning_parts = {}
    for record in drawable:
        code = str(record.get("taskCode") or "")
        parts = []
        end_value = parse_datetime(record.get("end")).date()
        if end_value < current and int(record.get("progress") or 0) < 100:
            parts.append("Task is overdue")
        if not str(record.get("assigned") or ""):
            parts.append("Task has no assignee")
        if end_value.weekday() >= 5:
            parts.append("Deadline falls on a weekend")
        warning_parts[code] = parts

    by_user = {}
    for record in drawable:
        login = str(record.get("assigned") or "")
        if login:
            by_user.setdefault(login, []).append(record)
    for values in by_user.values():
        values.sort(key=lambda item: item["ganttStartDay"])
        latest_end = -1
        for index, record in enumerate(values):
            start = record["ganttStartDay"]
            end = start + record["ganttDurationDays"] - 1
            # An earlier interval with the furthest end, or the next start,
            # proves overlap. We need a flag, not every intersecting pair.
            if latest_end >= start or (
                    index + 1 < len(values)
                    and values[index + 1]["ganttStartDay"] <= end):
                warning_parts[str(record.get("taskCode") or "")].append(
                    "Assignee has overlapping tasks"
                )
            latest_end = max(latest_end, end)

    for record in drawable:
        parts = warning_parts.get(str(record.get("taskCode") or ""), [])
        record["ganttWarning"] = "\n".join(dict.fromkeys(parts))

    def prepare_section(values, section):
        counts = {}
        for record in values:
            key = str(record.get("groupKey") or "")
            if key:
                counts[key] = counts.get(key, 0) + 1
        previous = None
        summaries = {}
        for record in values:
            key = str(record.get("groupKey") or "")
            if not key or not record.get("ganttScheduled"):
                continue
            start_day = int(record.get("ganttStartDay") or 0)
            end_day = start_day + int(record.get("ganttDurationDays") or 1)
            summary = summaries.setdefault(key, {
                "start": start_day,
                "end": end_day,
                "progress": 0,
                "count": 0,
            })
            summary["start"] = min(summary["start"], start_day)
            summary["end"] = max(summary["end"], end_day)
            summary["progress"] += int(record.get("progress") or 0)
            summary["count"] += 1
        for index, record in enumerate(values):
            key = str(record.get("groupKey") or "")
            record["ganttSection"] = section
            record["ganttSectionFirst"] = index == 0
            record["groupFirst"] = bool(key) and key != previous
            record["groupCount"] = counts.get(key, 0)
            summary = summaries.get(key)
            if summary:
                record["ganttGroupStartDay"] = summary["start"]
                record["ganttGroupDurationDays"] = (
                    summary["end"] - summary["start"]
                )
                record["ganttGroupProgress"] = round(
                    summary["progress"] / summary["count"]
                )
            previous = key

    prepare_section(scheduled, "scheduled")
    prepare_section(unscheduled, "unscheduled")

    day_count = (range_end - range_start).days + 1
    tick_step = 7 if day_count <= 180 else 14 if day_count <= 730 else 28
    ticks = {}
    cursor = range_start
    while cursor <= range_end:
        offset = (cursor - range_start).days
        ticks[offset] = {
            "date": cursor.isoformat(),
            "label": "{:02d} {}".format(
                cursor.day, calendar.month_abbr[cursor.month]
            ),
            "offsetDay": offset,
            "major": False,
        }
        cursor += timedelta(days=tick_step)
    cursor = date(range_start.year, range_start.month, 1)
    if cursor < range_start:
        cursor = (
            date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1)
        )

    def tick_item(value, label, span_days=1, major=False):
        return {
            "date": value.isoformat(),
            "label": label,
            "offsetDay": (value - range_start).days,
            "spanDays": span_days,
            "major": major,
        }

    day_ticks = []
    day_step = max(1, (day_count + 719) // 720)
    cursor = range_start
    while cursor <= range_end:
        day_ticks.append(tick_item(
            cursor,
            "{:02d} {}".format(cursor.day, calendar.month_abbr[cursor.month]),
            day_step,
            cursor.day == 1,
        ))
        cursor += timedelta(days=day_step)

    week_ticks = []
    cursor = range_start
    while cursor <= range_end:
        week_ticks.append(tick_item(
            cursor,
            "{:02d} {}".format(cursor.day, calendar.month_abbr[cursor.month]),
            7,
            cursor.day <= 7,
        ))
        cursor += timedelta(days=7)

    month_ticks = []
    cursor = date(range_start.year, range_start.month, 1)
    if cursor < range_start:
        cursor = (
            date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1)
        )
    while cursor <= range_end:
        month_ticks.append(tick_item(
            cursor,
            "{} {}".format(calendar.month_abbr[cursor.month], cursor.year),
            calendar.monthrange(cursor.year, cursor.month)[1],
            cursor.month == 1,
        ))
        cursor = (
            date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1)
        )

    quarter_ticks = []
    quarter_month = ((range_start.month - 1) // 3) * 3 + 1
    cursor = date(range_start.year, quarter_month, 1)
    while cursor <= range_end:
        marker = max(cursor, range_start)
        quarter_ticks.append(tick_item(
            marker,
            "Q{} {}".format((cursor.month - 1) // 3 + 1, cursor.year),
            90,
            cursor.month == 1,
        ))
        next_month = cursor.month + 3
        cursor = (
            date(cursor.year + 1, next_month - 12, 1)
            if next_month > 12
            else date(cursor.year, next_month, 1)
        )
    while cursor <= range_end:
        offset = (cursor - range_start).days
        ticks[offset] = {
            "date": cursor.isoformat(),
            "label": "{} {}".format(
                calendar.month_abbr[cursor.month], cursor.year
            ),
            "offsetDay": offset,
            "major": True,
        }
        cursor = (
            date(cursor.year + 1, 1, 1)
            if cursor.month == 12
            else date(cursor.year, cursor.month + 1, 1)
        )

    today_offset = (current - range_start).days
    if not 0 <= today_offset < day_count:
        today_offset = -1
    weekend_spans = []
    cursor = range_start
    while cursor <= range_end:
        if cursor.weekday() == 5:
            weekend_spans.append({
                "offsetDay": (cursor - range_start).days,
                "durationDays": min(2, (range_end - cursor).days + 1),
            })
            cursor += timedelta(days=2)
        else:
            cursor += timedelta(days=1)
    overview = [{
        "startDay": int(record.get("ganttStartDay") or 0),
        "durationDays": int(record.get("ganttDurationDays") or 1),
        "color": str(record.get("ganttColor") or ""),
        "warning": bool(record.get("ganttWarning")),
    } for record in scheduled]
    if len(overview) > 400:
        bucket_days = max(1, (day_count + 179) // 180)
        buckets = {}
        for item in overview:
            key = item["startDay"] // bucket_days
            bucket = buckets.setdefault(key, {
                "startDay": key * bucket_days,
                "durationDays": bucket_days,
                "color": item["color"],
                "warning": False,
            })
            bucket["warning"] = bucket["warning"] or item["warning"]
        overview = [buckets[key] for key in sorted(buckets)]
    milestone_markers = [{
        "code": str(source.get("value") or source.get("code") or ""),
        "label": str(
            source.get("label") or source.get("description") or "Milestone"
        ),
        "dueDate": due_date.isoformat(),
        "offsetDay": (due_date - range_start).days,
        "completion": int(source.get("completion") or 0),
        "taskCount": int(source.get("taskCount") or 0),
    } for source, due_date in milestone_sources]
    return {
        "rangeStart": range_start.isoformat(),
        "rangeEnd": range_end.isoformat(),
        "days": day_count,
        "todayDay": today_offset,
        "scheduled": len(scheduled),
        "unscheduled": len(unscheduled),
        "ticks": [ticks[key] for key in sorted(ticks)],
        "tickSets": {
            "days": day_ticks,
            "weeks": week_ticks,
            "months": month_ticks,
            "quarters": quarter_ticks,
        },
        "weekends": weekend_spans,
        "overview": overview,
        "milestones": milestone_markers,
        "warnings": sum(
            bool(record.get("ganttWarning")) for record in scheduled
        ) + len(unscheduled),
        "records": scheduled + unscheduled,
    }


def date_value(original, target):
    """Move a date while preserving the original time when it exists."""
    parsed = parse_datetime(original)
    if parsed is None:
        parsed_time = datetime.min.time()
    else:
        parsed_time = parsed.time()
    return datetime.combine(target, parsed_time).strftime("%Y-%m-%d %H:%M:%S")


def next_workday(value, direction=1):
    direction = 1 if direction >= 0 else -1
    while value.weekday() >= 5:
        value += timedelta(days=direction)
    return value


def add_workdays(value, amount):
    value = next_workday(value, 1 if amount >= 0 else -1)
    direction = 1 if amount >= 0 else -1
    for _index in range(abs(int(amount))):
        value += timedelta(days=direction)
        value = next_workday(value, direction)
    return value


def workday_duration(start_value, end_value):
    if end_value < start_value:
        return 1
    return max(1, sum(
        1 for offset in range((end_value - start_value).days + 1)
        if (start_value + timedelta(days=offset)).weekday() < 5
    ))


def schedule_dates(
    record, range_start_value, start_day, duration_days, working_days=False,
):
    range_start = parse_datetime(range_start_value)
    if range_start is None:
        return {}
    start_date = range_start.date() + timedelta(days=int(start_day))
    duration_days = max(1, int(duration_days))
    if working_days:
        start_date = next_workday(start_date)
        end_date = add_workdays(start_date, duration_days - 1)
    else:
        end_date = start_date + timedelta(days=duration_days - 1)
    return {
        "start": date_value(record.get("start"), start_date),
        "end": date_value(record.get("end"), end_date),
    }


def shifted_selection_edits(
    primary_record, desired_start_value, selected_records, working_days=False,
):
    """Shift peer records by the primary record's staged date delta."""
    original_start = parse_datetime(primary_record.get("start"))
    desired_start = parse_datetime(desired_start_value)
    if original_start is None or desired_start is None:
        return {}
    delta = desired_start.date() - original_start.date()
    edits = {}
    for code, record in selected_records:
        other_start = parse_datetime(record.get("start"))
        other_end = parse_datetime(record.get("end"))
        if other_start is None or other_end is None:
            continue
        start_date = other_start.date() + delta
        if working_days:
            start_date = next_workday(
                start_date, 1 if delta.days >= 0 else -1
            )
            duration = workday_duration(
                other_start.date(), other_end.date()
            )
            end_date = add_workdays(start_date, duration - 1)
        else:
            end_date = other_end.date() + delta
        edits[str(code)] = {
            "start": date_value(record.get("start"), start_date),
            "end": date_value(record.get("end"), end_date),
        }
    return edits


def batch_schedule_edits(
    records, action, amount=1, working_days=False,
):
    """Return pure date edits for a Gantt multi-selection action."""
    action = str(action or "")
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        amount = 1

    prepared = []
    for code, record in records:
        start_value = parse_datetime(record.get("start"))
        end_value = parse_datetime(record.get("end"))
        if start_value is not None and end_value is not None:
            prepared.append((
                str(code), record, start_value.date(), end_value.date(),
            ))
    if not prepared:
        return {}

    anchor_start = min(item[2] for item in prepared)
    anchor_end = max(item[3] for item in prepared)
    sequence_cursor = anchor_start
    edits = {}

    for code, record, start_date, end_date in prepared:
        if action == "shift":
            if working_days:
                next_start = add_workdays(start_date, amount)
                next_end = add_workdays(end_date, amount)
            else:
                delta = timedelta(days=amount)
                next_start = start_date + delta
                next_end = end_date + delta
        elif action == "align-start":
            next_start, next_end = anchor_start, end_date
        elif action == "align-end":
            next_start, next_end = start_date, anchor_end
        elif action in {"extend", "shorten"}:
            delta = amount if action == "extend" else -amount
            next_start = start_date
            next_end = (
                add_workdays(end_date, delta)
                if working_days
                else end_date + timedelta(days=delta)
            )
            if next_end < next_start:
                next_end = next_start
        elif action == "sequence":
            if working_days:
                duration = workday_duration(start_date, end_date)
                next_start = next_workday(sequence_cursor)
                next_end = add_workdays(next_start, duration - 1)
                sequence_cursor = add_workdays(next_end, 1)
            else:
                duration = (end_date - start_date).days + 1
                next_start = sequence_cursor
                next_end = next_start + timedelta(days=duration - 1)
                sequence_cursor = next_end + timedelta(days=1)
        else:
            return {}

        edits[code] = {
            "start": date_value(record.get("start"), next_start),
            "end": date_value(record.get("end"), next_end),
        }

    return edits


def checked_records(values):
    """Bound client-supplied presentation data; it grants no access to stored tasks."""
    if not isinstance(values, list) or len(values) > 500:
        raise ValueError('Choose at most 500 task records')
    fields = {'taskCode', 'parentKey', 'parentTitle', 'process', 'processLabel', 'status',
              'assigned', 'assignedLabel', 'start', 'end', 'groupKey', 'group'}
    result, seen, dates = [], set(), []
    for source in values:
        if not isinstance(source, dict):
            raise ValueError('Invalid task schedule record')
        record = {}
        for name in fields:
            value = source.get(name, '')
            if not isinstance(value, str) or len(value) > 4096:
                raise ValueError('Invalid task schedule text')
            record[name] = value
        key = record['taskCode']
        if not key or key in seen:
            raise ValueError('Task schedule identities must be unique')
        seen.add(key)
        value = source.get('progress', 0)
        if type(value) not in (int, float) or not 0 <= value <= 100:
            raise ValueError('Task progress must be between 0 and 100')
        record['progress'] = value
        if '_ganttSectionScheduled' in source:
            if type(source['_ganttSectionScheduled']) is not bool:
                raise ValueError('Invalid original schedule section')
            record['_ganttSectionScheduled'] = source['_ganttSectionScheduled']
        record['dueState'] = due_state(record['end'])
        for name in ('start', 'end'):
            parsed = parse_datetime(record[name])
            if parsed:
                if not 2 <= parsed.year <= 9997:
                    raise ValueError('Task dates are outside the supported display range')
                dates.append(parsed.date())
        result.append(record)
    if dates and (max(dates) - min(dates)).days > 36600:
        raise ValueError('Task schedule range exceeds 100 years')
    return result


class TaskScheduleCmd(Command):
    """Project a loaded page or calculate pending dates without reading/writing tasks.

    These results are presentation data, never a write authorization. Save still
    prepares native tasks, checks field rights/revisions and runs Task.commit.
    """
    def check_security(self):
        _require_admin()
        return True

    def execute(self):
        _require_admin()
        records = checked_records(self.kwargs.get('records', []))
        action = self.kwargs.get('action', 'projection')
        if action == 'projection':
            year, month = self.kwargs.get('year'), self.kwargs.get('month')
            if type(year) is not int or not 2 <= year <= 9997 or type(month) is not int or not 1 <= month <= 12:
                raise ValueError('Choose a valid calendar month')
            sources = self.kwargs.get('milestones', [])
            if not isinstance(sources, list) or len(sources) > 500:
                raise ValueError('Choose at most 500 milestones')
            milestones = []
            dates = [parse_datetime(row[name]).date() for row in records for name in ('start', 'end') if parse_datetime(row[name])]
            for source in sources:
                if not isinstance(source, dict) or any(not isinstance(source.get(name, ''), str) or len(source.get(name, '')) > 4096 for name in ('value', 'label', 'dueDate')):
                    raise ValueError('Invalid milestone projection')
                parsed = parse_datetime(source.get('dueDate'))
                if parsed:
                    if not 2 <= parsed.year <= 9997:
                        raise ValueError('Milestone date is outside the supported display range')
                    dates.append(parsed.date())
                    marker = {name: source.get(name, '') for name in ('value', 'label', 'dueDate')}
                    for name in ('completion', 'taskCount'):
                        value = source.get(name) or 0
                        if type(value) is not int or not 0 <= value <= 100000000:
                            raise ValueError('Invalid milestone plan projection')
                        marker[name] = value
                    milestones.append(marker)
            if dates and (max(dates) - min(dates)).days > 36600:
                raise ValueError('Task schedule range exceeds 100 years')
            return dict(calendar=calendar_cells(year, month, records, milestones=milestones),
                        gantt=gantt_layout(records, milestones=milestones))
        if action not in ('batch', 'schedule') or not records:
            raise ValueError('Unsupported schedule operation or empty selection')
        working_days = self.kwargs.get('working_days', False)
        if type(working_days) is not bool:
            raise ValueError('Invalid working days option')
        if sum(abs((parse_datetime(row['end']) - parse_datetime(row['start'])).days) for row in records
               if parse_datetime(row['start']) and parse_datetime(row['end'])) > 200000:
            raise ValueError('Selected schedule durations exceed the calculation limit')
        if action == 'batch':
            operation, amount = self.kwargs.get('operation'), self.kwargs.get('amount', 1)
            if operation not in ('shift', 'align-start', 'align-end', 'sequence', 'extend', 'shorten') or type(amount) is not int or not -3650 <= amount <= 3650:
                raise ValueError('Invalid schedule batch operation')
            if any(parse_datetime(row['start']) and parse_datetime(row['end']) and parse_datetime(row['start']) > parse_datetime(row['end']) for row in records):
                raise ValueError('Deadline precedes start')
            return dict(edits=batch_schedule_edits([(row['taskCode'], row) for row in records], operation, amount, working_days))
        primary = next((row for row in records if row['taskCode'] == self.kwargs.get('primary')), None)
        start, duration, origin = self.kwargs.get('start_day'), self.kwargs.get('duration'), self.kwargs.get('range_start')
        if primary is None or type(start) is not int or not -3650 <= start <= 36600 or type(duration) is not int or not 1 <= duration <= 3650 or not isinstance(origin, str) or len(origin) > 64 or not parse_datetime(origin):
            raise ValueError('Invalid task schedule dates')
        changes = schedule_dates(primary, origin, start, duration, working_days)
        edits = {primary['taskCode']: changes}
        if self.kwargs.get('move_selected') is True:
            edits.update(shifted_selection_edits(primary, changes['start'],
                         [(row['taskCode'], row) for row in records if row is not primary], working_days))
        return dict(edits=edits)
