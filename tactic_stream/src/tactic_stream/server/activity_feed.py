"""Handler Activity Feed on the native TACTIC journal; read-only."""
from datetime import date

from pyasm.biz import Project, Schema
from pyasm.common import Environment
from pyasm.common.errors import SecurityException
from pyasm.search import Search, SearchType
from .activity_query import query_user_recent_activity
from .security_groups import user_identities

KINDS = ('status', 'publication', 'note', 'task', 'create', 'change', 'delete', 'work_hour')
FILTERS = {'all': KINDS, 'my_objects': KINDS, 'my_tasks': ('task',),
           'notes': ('note',), 'publications': ('publication',)}


def instance_relations():
    schema = Schema.get()
    catalog, seen = {}, set()
    while schema and schema.get_code() not in seen:
        seen.add(schema.get_code())
        for node in schema.xml.findall('connect'):
            if node.get('relationship') == 'instance' and node.get('instance_type'):
                catalog[node.get('instance_type')] = [node.get('from'), node.get('to')]
        schema = schema.parent_schema
    return catalog


def activity_feed_request(payload):
    feed = payload.get('filter', 'all')
    offset, users = payload.get('offset', 0), payload.get('users', [])
    day, counts = payload.get('day', ''), payload.get('counts_only', False)
    exclude = payload.get('exclude_own', False)
    if not isinstance(feed, str) or feed not in FILTERS or type(offset) is not int or not 0 <= offset <= 100000:
        raise ValueError('Invalid activity filter or offset')
    if not isinstance(users, list) or len(users) > 100 or any(not isinstance(value, str) or not value or len(value) > 256 for value in users):
        raise ValueError('Invalid activity users')
    if type(counts) is not bool or type(exclude) is not bool or not isinstance(day, str):
        raise ValueError('Invalid activity options')
    if day and (date.fromisoformat(day).isoformat() != day):
        raise ValueError('Invalid activity day')
    security = Environment.get_security()
    # Audit XML contains old values even when an object has been deleted.
    if feed in ('all', 'my_objects') and not security.check_access('search_type', 'sthpw/transaction_log', 'view'):
        raise SecurityException('Activity journal requires transaction-log read access')
    login, project = Environment.get_user_name(), Project.get_project_code()
    if Project.get_by_code(project) is None:
        raise ValueError('Activity project does not exist')
    if project not in ('admin', 'sthpw') and not (security.check_access('project', {'code': '*'}, 'allow', default='deny')
            or security.check_access('project', {'code': project}, 'allow', default='deny')):
        raise SecurityException('Activity project is not accessible')
    result = query_user_recent_activity(login=login if feed == 'my_objects' else '', project_code=project,
        kinds=FILTERS[feed], assigned_login=login if feed == 'my_tasks' else '',
        offset=offset, limit=26, day=day, logins=users, counts_only=counts,
        include_day_counts=counts, exclude_login=login if exclude else '', instance_relations=instance_relations())
    records = result.get('records', []) if isinstance(result, dict) else result
    identities = user_identities(Search('sthpw/login').get_sobjects()) if security.check_access('search_type', 'sthpw/login', 'view') else []
    directory = {row['login']: row for row in identities}
    decorate_activity(records, directory)
    return dict(records=records[:25], hasMore=len(records) > 25, nextOffset=offset + min(25, len(records)),
        dayCounts=result.get('dayCounts', []) if isinstance(result, dict) else [], users=identities)


def decorate_activity(records, directory):
    """Apply the same author, type and pipeline presentation in object reports."""
    pipelines = {}
    for record in records:
        identity = directory.get(record.get('actor'), {})
        record.update(actorLabel=identity.get('displayName') or record.get('actor') or '',
            actorAvatar=identity.get('avatarUrl', ''), actorInitials=identity.get('initials', ''), actorColor=identity.get('avatarColor', ''))
        for type_field, title_field, color_field in (('targetType', 'targetTypeTitle', 'typeColor'), ('itemType', 'itemTypeTitle', 'itemTypeColor')):
            code = record.get(type_field)
            definition = SearchType.get(code, no_exception=True) if code else None
            if definition:
                record[title_field] = definition.get_title()
                record[color_field] = definition.get_value('color', no_exception=True) or ''
        pipeline_code, process = record.get('pipelineCode'), record.get('process')
        if pipeline_code and process:
            if pipeline_code not in pipelines:
                pipelines[pipeline_code] = Search.get_by_code('sthpw/pipeline', pipeline_code)
            pipeline = pipelines[pipeline_code]
            node = pipeline.get_process(process) if pipeline else None
            if node:
                record['processColor'] = node.get_attribute('color') or ''
                task_pipeline_code = node.get_task_pipeline() or 'task'
                if task_pipeline_code not in pipelines:
                    pipelines[task_pipeline_code] = Search.get_by_code('sthpw/pipeline', task_pipeline_code)
                task_pipeline = pipelines[task_pipeline_code]
                for field in ('statusBefore', 'statusAfter'):
                    status_node = task_pipeline.get_process(record[field]) if task_pipeline and record.get(field) else None
                    record[field + 'Color'] = status_node.get_attribute('color') or '' if status_node else ''
        record['dayKey'] = str(record.get('timestamp') or '')[:10]
