"""Native Handler hook editor and external-agent draft/publication operations."""
import hashlib
import json
import re
from uuid import UUID

from pyasm.biz import Project
from pyasm.command import Command
from pyasm.common import Environment
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin
from tactic_stream.automation_plan import AutomationPlan
from tactic_stream.server.script_shelf import script_shelf_request, read_shelves
from tactic_stream.server.navigation import read_navigation

HOOK_TYPE = 'handler_script_hook'
HANDLER_ACTIONS = ('snapshot.open', 'snapshot.save', 'object.create', 'object.update', 'object.delete',
                   'object.duplicate', 'relation.update', 'task.create', 'task.update', 'task.delete')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()


def state():
    hooks = Search('config/trigger')
    hooks.set_show_retired(True)
    hooks.add_filter('trigger_type', HOOK_TYPE)
    hooks.add_order_by('code')
    records = [item.get_data() for item in hooks.get_sobjects()]
    scripts = Search('config/custom_script')
    scripts.set_show_retired(True)
    scripts.add_order_by('code')
    scripts = [item.get_data() for item in scripts.get_sobjects()]
    shelves = read_shelves()
    sql = hooks.get_sql()
    generations = [sql.get_value("SELECT revision FROM spt_%s_revision WHERE code='collection'" % name)
                   for name in ('custom_script', 'trigger', 'widget_config')]
    return dict(records=records, revision=digest([records, scripts, shelves['revision'], generations]),
                scripts=[dict(path=(row.get('folder') or '').strip('/') + '/' + (row.get('title') or ''),
                              language=row.get('language') or 'local_python', code=row['code'])
                         for row in scripts if row.get('s_status') != 'retired'],
                shelves=shelves['shelves'], navigation=read_navigation(), isolated_trial_available=False)


def shelf_buttons(document, current):
    def entries(items):
        for item in items:
            yield item
            yield from entries(item.get('children') or [])
    matches = [item for item in entries(current['navigation']['entries'])
               if item['display']['options'].get('search_type', '') + '@' + item['name'] == document['entry_key']]
    if len(matches) != 1:
        raise ValueError('Choose one existing native sidebar entry')
    view = matches[0]['display']['options'].get('script_shelf') or 'script_shelf@global'
    shelf = next((row for row in current['shelves'] if row['view'] == view and not row['personal']), None)
    if shelf and not shelf['valid']:
        raise ValueError('Repair the assigned shelf before adding an action')
    return list(shelf['configuration']['buttons']) if shelf else []


def save_hooks(rules, current):
    if not isinstance(rules, list) or len(rules) > 256:
        raise ValueError('Expected at most 256 Handler trigger rules')
    scripts = {row['path']: row for row in current['scripts']}
    existing = {row['code']: row for row in current['records']}
    prepared, retained = [], set()
    fields = {'ruleId', 'code', 'title', 'description', 'action', 'phase', 'searchType',
              'searchKeysText', 'process', 'context', 'script', 'enabled', 'order'}
    for order, rule in enumerate(rules):
        if not isinstance(rule, dict) or set(rule) - fields:
            raise ValueError('Invalid Handler trigger fields')
        if type(rule.get('enabled')) is not bool:
            raise ValueError('Trigger enabled must be boolean')
        for field in fields - {'enabled', 'order'}:
            if not isinstance(rule.get(field, ''), str) or '\x00' in rule.get(field, ''):
                raise ValueError('Invalid Handler trigger value: ' + field)
        for field in ('title', 'script', 'action', 'phase', 'searchType', 'process', 'context'):
            if len(rule.get(field, '')) > 256:
                raise ValueError('Trigger field is too long: ' + field)
        if not rule.get('title', '').strip() or rule.get('phase') not in ('before', 'after'):
            raise ValueError('Choose a trigger title and phase')
        action = rule.get('action')
        dcc = isinstance(action, str) and bool(re.fullmatch(r'dcc\.[a-z][a-z0-9_.]*', action))
        if action not in HANDLER_ACTIONS and not dcc:
            raise ValueError('Choose a native Handler action')
        script = scripts.get(rule.get('script'))
        languages = ('dcc_python',) if dcc else ('local_python', 'python', 'server_js')
        if not script or script['language'] not in languages:
            raise ValueError('Choose an available script for the action execution owner')
        code = rule.get('code', '')
        if code and (code not in existing or code in retained):
            raise ValueError('Trigger identity is missing or duplicated')
        retained.add(code)
        if rule.get('searchType'):
            SearchType.get(rule['searchType'])
        keys = list(dict.fromkeys(key.strip() for key in rule.get('searchKeysText', '').replace(',', '\n').splitlines() if key.strip()))
        data = dict(version=1, action=action, phase=rule['phase'], search_type=rule.get('searchType', ''),
                    search_keys=keys, process=rule.get('process', ''), context=rule.get('context', ''), order=order)
        prepared.append((code, dict(title=rule['title'].strip(), description=rule.get('description', ''),
            event='handler|' + '|'.join((rule['phase'], *action.split('.'))), script_path=rule['script'],
            trigger_type=HOOK_TYPE, data=json.dumps(data, ensure_ascii=False, separators=(',', ':')),
            s_status='' if rule['enabled'] else 'retired')))
    if any(rule['enabled'] for rule in rules):
        from tactic.command.python_cmd import check_script_execution
        from tactic_stream.server.api import Api
        check_script_execution()
        Api.check_method_access('execute_python_script')
    result = []
    for code, data in prepared:
        item = Search.get_by_code('config/trigger', code, show_retired=True) if code else SearchType.create('config/trigger')
        for field, value in data.items():
            item.set_value(field, value)
        item.commit()
        result.append(item.get_data())
    for code in existing.keys() - retained:
        Search.get_by_code('config/trigger', code, show_retired=True).delete()
    return result


class HandlerAutomationCmd(Command):
    def execute(self):
        _require_admin()
        project = Project.get_project_code()
        if self.kwargs.get('project_code') != project:
            raise ValueError('Handler automation project mismatch')
        action = self.kwargs.get('action')
        if action not in ('read', 'save_hooks', 'preview', 'save_draft', 'draft', 'activate', 'operation'):
            raise ValueError('Unknown Handler automation operation')
        sql = Search('config/trigger').get_sql()
        if not all(sql.table_exists(name) for name in ('spt_automation_operation', 'spt_automation_draft', 'spt_trigger_revision', 'spt_custom_script_revision')):
            raise ValueError('Upgrade the project schema before configuring Handler automation')
        writes = action in ('save_hooks', 'save_draft', 'activate')
        if writes:
            # One lock order shared by the normal script, hook and shelf editors.
            for logical in ('config/custom_script', 'config/trigger', 'config/widget_config'):
                sql.get_database_impl().lock_collection_table(sql, SearchType.get(logical).get_table())
        operation_id = self.kwargs.get('operation_id', '')
        key = ''
        if writes or action == 'operation':
            if not isinstance(operation_id, str) or str(UUID(operation_id)) != operation_id:
                raise ValueError('A canonical UUID operation_id is required')
            key = digest([Environment.get_user_name(), project, operation_id])
        if action == 'operation':
            row = sql.do_query('SELECT result FROM spt_automation_operation WHERE code=' + sql.quote(key))
            self.info = json.loads(row[0][0]) if row else dict(status='not_found', operation_id=operation_id)
            return
        fingerprint = digest(self.kwargs)
        if writes:
            receipt = sql.do_query('SELECT request_hash,result FROM spt_automation_operation WHERE code=' + sql.quote(key))
            if receipt:
                if receipt[0][0] != fingerprint:
                    raise ValueError('Operation ID was used with a different request')
                self.info = json.loads(receipt[0][1])
                return
        current = state()
        if action == 'read':
            self.info = current
            return
        if action in ('save_hooks', 'activate') and self.kwargs.get('expected_revision') != current['revision']:
            raise ValueError('Handler automation dependencies changed; reload before saving')
        if action == 'save_hooks':
            save_hooks(self.kwargs.get('rules'), current)
            result = state()
        elif action in ('preview', 'save_draft'):
            document = AutomationPlan.model_validate(self.kwargs.get('document')).model_dump()
            if document['search_type']:
                SearchType.get(document['search_type'])
            if document['kind'] == 'shelf':
                shelf_buttons(document, current)
            result = dict(document=document, validation='Python syntax only; no execution or sandbox trial',
                          revision=digest(document), dependency_revision=current['revision'])
            if action == 'save_draft':
                if self.kwargs.get('expected_revision') != result['revision']:
                    raise ValueError('Draft changed; preview it again')
                marker = sql.get_database_impl().get_parameter()
                sql._do_update('INSERT INTO spt_automation_draft (code,owner,document,revision) VALUES (%s)' % ','.join([marker] * 4),
                    parameters=[operation_id, Environment.get_user_name(), json.dumps(document), result['revision']])
                result['draft_id'] = operation_id
        else:
            draft_id = str(UUID(self.kwargs.get('draft_id', '')))
            rows = sql.do_query('SELECT owner,document,revision FROM spt_automation_draft WHERE code=' + sql.quote(draft_id))
            if not rows or rows[0][0] != Environment.get_user_name():
                raise ValueError('Draft is unavailable for this administrator')
            document = json.loads(rows[0][1])
            if action == 'draft':
                self.info = dict(draft_id=draft_id, revision=rows[0][2], document=document, dependency_revision=current['revision'])
                return
            if self.kwargs.get('draft_revision') != rows[0][2]:
                raise ValueError('Draft revision changed')
            from tactic.command.python_cmd import check_script_execution
            from tactic_stream.server.api import Api
            check_script_execution()
            Api.check_method_access('execute_python_script')
            folder, title = 'agent/' + draft_id, 'action'
            scripts = Search('config/custom_script')
            scripts.add_filter('folder', folder)
            scripts.set_show_retired(True)
            if scripts.get_sobject():
                raise ValueError('This draft was already activated; read its saved configuration')
            script = SearchType.create('config/custom_script')
            for name, value in dict(folder=folder, title=title, description=document['description'],
                                    language='local_python', script=document['source']).items():
                script.set_value(name, value)
            script.commit()
            path = folder + '/' + title
            if document['kind'] == 'hook':
                rules = []
                ordered = sorted(current['records'], key=lambda row: (json.loads(row.get('data') or '{}').get('order', 0), row['code']))
                for record in ordered:
                    data = json.loads(record.get('data') or '{}')
                    rules.append(dict(code=record['code'], title=record.get('title') or '', description=record.get('description') or '',
                        action=data.get('action'), phase=data.get('phase'), searchType=data.get('search_type') or '',
                        searchKeysText='\n'.join(data.get('search_keys') or []), process=data.get('process') or '',
                        context=data.get('context') or '', script=record.get('script_path') or '', enabled=record.get('s_status') != 'retired'))
                rules.append(dict(title=document['title'], description=document['description'], action='snapshot.save',
                    phase=document['phase'], searchType=document['search_type'], process=document['process'], context=document['context'],
                    script=path, enabled=True))
                save_hooks(rules, state())
                binding = dict(kind='hook', phase=document['phase'])
            else:
                shelf = read_shelves()
                buttons = shelf_buttons(document, current)
                buttons.append(dict(id=draft_id, title=document['title'], description=document['description'], icon=document['icon'], script=path))
                binding = script_shelf_request('save', dict(mode='shared', revision=shelf['revision'], title=document['title'],
                    entry_key=document['entry_key'], configuration=dict(scope='preset', entryKey='', buttons=buttons)))
            result = dict(draft_id=draft_id, script=path, script_key=script.get_search_key(), binding=binding, revision=state()['revision'])
        if writes:
            result.update(operation_id=operation_id, status='applied')
            marker = sql.get_database_impl().get_parameter()
            sql._do_update('INSERT INTO spt_automation_operation (code,request_hash,result) VALUES (%s)' % ','.join([marker] * 3),
                           parameters=[key, fingerprint, json.dumps(result, default=str)])
        self.info = result
