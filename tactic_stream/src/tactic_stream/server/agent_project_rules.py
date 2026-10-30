"""Shared project chat preferences stored as an ordinary native project setting."""
import hashlib

from pyasm.biz import Project, ProjectSetting
from pyasm.search import Search

KEY = 'agent/chat_rules'
LIMIT = 16000


def read():
    # Bypass request-local setting caches when checking a concurrent editor's revision.
    ProjectSetting.clear_cache()
    value = ProjectSetting.get_value_by_key(KEY) or ''
    return dict(project=Project.get_project_code(), text=value,
                revision=hashlib.sha256(value.encode('utf-8')).hexdigest())


def capture(capabilities):
    rules = read()
    if rules['text'] and not capabilities.get('project_rules'):
        raise ValueError('Reconnect the agent to load project chat rules')
    return rules


def save(value, expected_revision):
    if Project.get_project_code() in ('admin', 'sthpw'):
        raise ValueError('Select a user project before editing chat rules')
    if not isinstance(value, str) or len(value) > LIMIT or '\x00' in value:
        raise ValueError('Project chat rules must be text of at most 16000 characters')
    sql = Search(ProjectSetting.SEARCH_TYPE).get_sql()
    sql.get_database_impl().lock_collection_table(sql, 'prod_setting')
    current = read()
    if value == current['text']:
        return current
    if expected_revision != current['revision']:
        raise ValueError('Project chat rules changed. Reopen the editor before saving.')
    ProjectSetting.create(KEY, value, type='text', description='Shared instructions for project agent chats')
    return read()
