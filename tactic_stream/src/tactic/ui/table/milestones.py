"""Handler project milestones on native Search/SObject/Command.

Source: thlib/ui/milestones.py, MilestoneController (EPL-1.0).
"""
import hashlib
import json
import math
from datetime import date

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment, SecurityException, UserException
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin
from .task_element_wdg import TaskElementWdg
from .task_inspector import task_fields
from .statistic_wdg import TaskCompletionWdg


def task_completion(task, info, status_widget):
    """Handler _task_completion, using the native status attribute."""
    try:
        value = status_widget.get_status_attr(task).get_percent_completion()
    except (AttributeError, KeyError, TypeError, ValueError):
        value = info.get('completion') or info.get('progress') or 0
    try:
        value = float(str(value or 0).rstrip('%'))
        return max(0.0, value) if math.isfinite(value) else 0.0
    except (TypeError, ValueError):
        return 0.0


def milestone_plan(tasks):
    """Handler _milestone_plan: completion follows status, not manual progress."""
    completion, starts, processes = [], [], {}
    overdue, planned_hours = 0, 0.0
    today = date.today().isoformat()
    status_widget = TaskCompletionWdg()
    status_widget.preprocess()
    for task in tasks:
        info = task.get_data()
        percent = task_completion(task, info, status_widget)
        completion.append(percent)
        start = str(info.get('bid_start_date') or '')[:10]
        end = str(info.get('bid_end_date') or '')[:10]
        if start:
            starts.append(start)
        if end and end < today and percent < 100:
            overdue += 1
        process = str(info.get('process') or info.get('context') or '')
        if process:
            processes[process] = None
        try:
            hours = float(info.get('bid_duration') or 0)
            if math.isfinite(hours):
                planned_hours += hours
        except (TypeError, ValueError):
            pass
    return dict(completion=round(sum(completion) / len(completion)) if completion else 0,
                taskCount=len(tasks), completedCount=sum(value >= 100 for value in completion),
                overdueCount=overdue, planStartDate=min(starts) if starts else '',
                processSummary=' / '.join(processes), plannedHours=round(planned_hours, 1))


def read_milestones():
    _require_admin()
    project = Project.get_project_code()
    security = Environment.get_security()
    fields = []
    for name in ('description', 'due_date'):
        keys = [dict(search_type='sthpw/milestone', key=name, project=project),
                dict(search_type='sthpw/milestone', project=project)]
        column = dict(search_type='sthpw/milestone', column=name, project=project)
        if security.check_access('element', keys, 'view', default='edit') and security.check_access('sobject_column', column, 'view'):
            fields.append(dict(name=name, editable=security.check_access('element', keys, 'edit', default='edit')
                               and security.check_access('sobject_column', column, 'edit')))
    search = Search('sthpw/milestone'); search.add_filter('project_code', project)
    search.add_order_by('due_date'); search.add_order_by('description')
    objects = search.get_sobjects()
    changes = Search('sthpw/change_timestamp')
    changes.add_filters('search_type', ['sthpw/milestone', Project.get_full_search_type('sthpw/milestone'),
                                      'sthpw/milestone?project=' + project])
    changes.add_filters('search_code', [obj.get_code() for obj in objects])
    timestamps = {obj.get_value('search_code'): obj.get_data() for obj in changes.get_sobjects()} if objects else {}
    revision = hashlib.sha256(json.dumps(dict(project=project, fields=fields,
        records=[obj.get_data() for obj in objects], journal=timestamps),
        sort_keys=True, default=str).encode()).hexdigest()
    visible = {field['name'] for field in fields}
    records, grouped = [], {}
    task_visible = {field['name'] for field in task_fields()}
    if objects and 'milestone_code' in {field['name'] for field in task_fields(('milestone_code',))}:
        tasks = Search('sthpw/task'); tasks.add_filter('project_code', project)
        tasks.add_filters('milestone_code', [obj.get_code() for obj in objects])
        for task in tasks.get_sobjects():
            if TaskElementWdg.can_view_process(task.get_value('process')):
                grouped.setdefault(task.get_value('milestone_code'), []).append(task)
    process_visible = 'process' in {field['name'] for field in task_fields(('process',))}
    for obj in objects:
        plan = milestone_plan(grouped.get(obj.get_code(), []))
        # Hidden columns must not leak through summaries or derived dates.
        if 'status' not in task_visible:
            plan['completion'] = plan['completedCount'] = None
        if not {'status', 'bid_end_date'} <= task_visible:
            plan['overdueCount'] = None
        if 'bid_start_date' not in task_visible:
            plan['planStartDate'] = ''
        if 'bid_duration' not in task_visible:
            plan['plannedHours'] = None
        if not process_visible:
            plan['processSummary'] = ''
        records.append(dict(code=obj.get_code(), search_key=obj.get_search_key(),
            revision=hashlib.sha256(json.dumps([obj.get_data(), timestamps.get(obj.get_code()), fields],
                sort_keys=True, default=str).encode()).hexdigest(),
            description=obj.get_value('description') if 'description' in visible else '',
            dueDate=str(obj.get_value('due_date') or '')[:10] if 'due_date' in visible else '', **plan))
    keys = [dict(code='sthpw/milestone'), dict(code='sthpw/milestone', project=project), dict(code='*'), dict(code='*', project=project)]
    return dict(records=records, fields=fields, revision=revision, project=project,
                canCreate=all(any(field['name'] == name and field['editable'] for field in fields)
                              for name in ('description', 'due_date')) and security.check_access('search_type', keys, 'insert', default='allow'),
                canDelete=security.check_access('search_type', keys, 'delete', default='allow'))


class MilestoneCmd(Command):
    def check(self):
        _require_admin()
        return True

    def execute(self):
        _require_admin()
        action = self.kwargs.get('action', 'read')
        if action not in ('read', 'create', 'update', 'delete'):
            raise ValueError('Unsupported milestone operation')
        if action != 'read':
            # Match TaskWorkspaceEditCmd lock order. Also serialize duplicate names.
            # ponytail: collection locks; narrow locks if measured contention warrants it.
            for name in ('sthpw/task', 'sthpw/milestone'):
                sql = Search(name).get_sql()
                sql.get_database_impl().lock_collection_table(sql, SearchType.get(name).get_table())
        current = read_milestones()
        if action == 'read':
            return current
        code = self.kwargs.get('code', '')
        if not isinstance(code, str) or len(code) > 256 or action == 'create' and code:
            raise ValueError('Choose a valid milestone')
        selected = next((row for row in current['records'] if row['code'] == code), None)
        if action != 'create' and selected is None:
            raise ValueError('Milestone does not belong to this project')
        if selected and self.kwargs.get('expected_revision') != selected['revision']:
            raise UserException('Milestones changed. Review the current data before saving.')
        # Creation has no previous object to overwrite; locked name validation
        # allows independent new drafts and concurrent unrelated milestone edits.
        obj = Search.get_by_search_key(selected['search_key']) if selected else SearchType.create('sthpw/milestone')
        if action == 'delete':
            if not current['canDelete']:
                raise SecurityException('Milestone deletion is not permitted')
            tasks = Search('sthpw/task'); tasks.add_filter('milestone_code', code)
            tasks.add_limit(1)
            # Retired tasks still reference the milestone and can be restored.
            tasks.set_show_retired(True)
            if tasks.get_sobjects():
                raise UserException('This milestone is assigned to tasks and cannot be deleted')
            obj.delete()
        else:
            data = self.kwargs.get('data')
            if not isinstance(data, dict) or set(data) != {'description', 'due_date'}:
                raise ValueError('Provide a milestone name and due date')
            for name, value in data.items():
                if not any(field['name'] == name and field['editable'] for field in current['fields']):
                    raise SecurityException('Milestone field is not editable')
                if not isinstance(value, str) or len(value) > 4096 or any(ord(char) < 32 for char in value):
                    raise ValueError('Invalid milestone name or date')
            description = data['description'].strip()
            if not description:
                raise UserException('A milestone name is required')
            if any(row['code'] != code and row['description'].casefold() == description.casefold() for row in current['records']):
                raise UserException('A milestone with this name already exists')
            try:
                due = date.fromisoformat(data['due_date'])
                if due.isoformat() != data['due_date']:
                    raise ValueError()
            except ValueError:
                raise UserException('Choose a valid milestone due date') from None
            if action == 'create':
                if not current['canCreate']:
                    raise SecurityException('Milestone creation is not permitted')
                obj.set_value('project_code', Project.get_project_code())
            obj.set_value('description', description); obj.set_value('due_date', due.isoformat())
            obj.commit()
        result = read_milestones()
        result.update(selected='' if action == 'delete' else obj.get_code(), before_revision=current['revision'])
        return result
