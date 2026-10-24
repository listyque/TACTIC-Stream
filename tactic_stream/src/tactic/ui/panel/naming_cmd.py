"""Naming editor operations; fields/defaults follow Handler's naming_editor.py.

Evaluation uses the same Naming/DirNaming/FileNaming code as native check-in.
"""
import hashlib
import json
import os
from uuid import UUID

from pyasm.command import Command
from pyasm.common import Container, Environment
from pyasm.common.errors import UserException
from pyasm.biz import Naming, Project, Snapshot, DirNaming, FileNaming
from pyasm.search import Search, SearchType
from pyasm.search.keys import SearchKey
from pyasm.security.security import _require_admin

FIELDS = ('search_type', 'dir_naming', 'file_naming', 'sandbox_dir_naming',
          'snapshot_type', 'context', 'latest_versionless', 'current_versionless',
          'manual_version', 'ingest_rule_code', 'condition', 'class_name',
          'script_path', 'checkin_type', 'base_dir_alias', 'sandbox_dir_alias')
BOOLEANS = ('latest_versionless', 'current_versionless', 'manual_version')


def naming_request(action, project_code, search_type, identity='', document=None,
                   expected_revision='', sample=None, object_offset=0,
                   allow_execution=False, operation_id=''):
    _require_admin()
    if project_code != Project.get_project_code():
        raise UserException('Naming project does not match the current project')
    if action not in ('load', 'save', 'preview', 'apply', 'operation'):
        raise UserException('Unknown naming operation')
    if SearchKey.extract_base_search_type(search_type) != search_type:
        raise UserException('Use the base Search Type for naming rules')
    definition = SearchType.get(search_type)
    # Resolve before reading/writing another project's configuration.
    sql = SearchType.get_sql_by_search_type(SearchType.build_search_type(search_type, project_code))
    if not sql.table_exists(definition.get_table()):
        raise UserException('The Search Type database table is missing')
    if not isinstance(allow_execution, bool):
        raise UserException('allow_execution must be boolean')
    sql = SearchType.get_sql_by_search_type(SearchType.build_search_type('config/naming', project_code))
    if not sql.table_exists('spt_naming_revision'):
        raise UserException('Upgrade the project schema before editing naming rules')
    if action in ('save', 'apply'):
        # ponytail: naming table lock; use per-type locks if editors contend.
        sql.get_database_impl().lock_collection_table(sql, SearchType.get('config/naming').get_table())
    receipt_key = ''
    if action in ('apply', 'operation'):
        try:
            if not isinstance(operation_id, str) or str(UUID(operation_id)) != operation_id:
                raise ValueError()
        except ValueError:
            raise UserException('A canonical UUID operation_id is required') from None
        receipt_key = hashlib.sha256(json.dumps([
            Environment.get_user_name(), project_code, operation_id]).encode()).hexdigest()
    if action == 'operation':
        receipt = sql.do_query('SELECT result FROM spt_naming_operation WHERE code=%s' % sql.quote(receipt_key))
        if not receipt:
            return {'operation_id': operation_id, 'status': 'not_found'}
        result = json.loads(receipt[0][0])
        if result['search_type'] != search_type:
            raise UserException('Operation belongs to another Search Type')
        return result
    query = Search('config/naming')
    query.add_filter('search_type', search_type)
    query.add_order_by('context')
    query.add_order_by('code')
    rows = query.get_sobjects()
    generation = sql.get_value("SELECT revision FROM spt_naming_revision WHERE code='collection'")
    revision = hashlib.sha256(json.dumps([project_code, search_type, generation, [row.get_data() for row in rows]],
                            sort_keys=True, default=str).encode()).hexdigest()
    current = next((row for row in rows if row.get_code() == identity), None)
    if identity and not current and action != 'apply':
        raise UserException('Naming rule no longer exists for this Search Type')

    if action in ('save', 'preview', 'apply'):
        if not isinstance(document, dict) or set(document) - set(FIELDS):
            raise UserException('Invalid naming fields')
        data = {field: document.get(field, False if field in BOOLEANS else '') for field in FIELDS}
        if data['search_type'] != search_type:
            raise UserException('Naming Search Type cannot be changed')
        for field, value in data.items():
            if field in BOOLEANS:
                if not isinstance(value, bool):
                    raise UserException('Naming flags must be boolean: ' + field)
            elif not isinstance(value, str):
                raise UserException('Naming values must be strings: ' + field)
        if data['checkin_type'] not in ('', 'auto', 'strict'):
            raise UserException('Check-in type must be Auto, Strict or empty.')
        if not any(data[field].strip() for field in ('dir_naming', 'file_naming', 'script_path', 'class_name')):
            raise UserException('Enter directory/file naming or a script/class override.')
        if action == 'apply':
            if allow_execution:
                raise UserException('Agent naming apply cannot enable custom code execution')
            fingerprint = hashlib.sha256(json.dumps(
                [search_type, identity, data, expected_revision, sample],
                sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
            receipt = sql.do_query('SELECT request_hash,result FROM spt_naming_operation WHERE code=%s' % sql.quote(receipt_key))
            if receipt:
                if receipt[0][0] != fingerprint:
                    raise UserException('Operation ID was already used with a different request')
                return json.loads(receipt[0][1])
            if identity and not current:
                raise UserException('Naming rule no longer exists for this Search Type')
        rule = SearchType.create('config/naming')
        for field, value in data.items():
            rule.set_value(field, value, temp=True)
        rule.validate()
        if action in ('save', 'apply'):
            if not expected_revision or expected_revision != revision:
                raise UserException('Naming rules changed on the server. Reload before saving.')
            if action == 'apply':
                preview = preview_naming(rule, current, sample, False)
                if not preview['matches']:
                    raise UserException('Draft naming rule does not match the selected sample')
            saved = current or SearchType.create('config/naming')
            for field, value in data.items():
                saved.set_value(field, value)
            saved.commit()
            if action == 'apply':
                result = {'operation_id': operation_id, 'status': 'applied',
                          'search_type': search_type, 'identity': saved.get_code(),
                          'key': saved.get_search_key(), 'document': data,
                          'base_revision': expected_revision}
                # Receipt and rule use the same project connection and commit together.
                parameter = sql.get_database_impl().get_parameter()
                sql._do_update('INSERT INTO spt_naming_operation (code,request_hash,result) VALUES (%s)' %
                               ','.join([parameter] * 3), parameters=[receipt_key, fingerprint, json.dumps(result)])
                return result
            return naming_request('load', project_code, search_type, saved.get_code(), object_offset=object_offset)
        return preview_naming(rule, current, sample, allow_execution)

    objects = Search(search_type)
    objects.add_order_by('id')
    count = objects.get_count()
    offset = max(0, int(object_offset))
    objects.set_limit(50)
    objects.set_offset(offset)
    items = [{'key': obj.get_search_key(), 'label': obj.get_display_value()} for obj in objects.get_sobjects()]
    return {'revision': revision, 'identity': identity, 'supports_idempotent_apply': True,
            'rules': [{'identity': row.get_code(), 'key': row.get_search_key(),
                       'document': {field: bool(row.get_value(field, no_exception=True)) if field in BOOLEANS
                                    else str(row.get_value(field, no_exception=True) or '') for field in FIELDS}}
                      for row in rows],
            'items': items, 'itemCount': count, 'itemOffset': offset}


def preview_naming(rule, current, sample, allow_execution):
    if not isinstance(sample, dict) or set(sample) - {
            'key', 'file', 'version', 'process', 'context', 'fileType', 'snapshotType'}:
        raise UserException('Invalid naming preview parameters')
    for field in ('key', 'file', 'process', 'context', 'fileType', 'snapshotType'):
        if field in sample and not isinstance(sample[field], str):
            raise UserException('Preview values must be strings: ' + field)
    obj = Search.get_by_search_key(sample.get('key', ''))
    if not obj or obj.get_base_search_type() != rule.get_value('search_type') or obj.get_project_code() != Project.get_project_code():
        raise UserException('Select a Search Object in the current project for preview')
    filename = str(sample.get('file') or 'example.ma').replace('\\', '/')
    if '/' in filename or filename in ('.', '..'):
        raise UserException('Example file must be a filename without a directory')
    version = sample.get('version', 1)
    if isinstance(version, bool) or not isinstance(version, int) or not 1 <= version <= 9999:
        raise UserException('Preview version must be between 1 and 9999')
    # Explicit admin execution uses the normal engine. It is not an AI sandbox.
    executable = bool(rule.get_value('script_path') or rule.get_value('class_name')
                      or any(any(token in str(rule.get_value(field)).upper() for token in ('@PYTHON', '@UPDATE'))
                             for field in ('condition', 'file_naming', 'dir_naming', 'sandbox_dir_naming')))
    if executable and allow_execution is not True:
        raise UserException('This preview requires explicit permission to execute custom code.')
    snapshot = Snapshot.create(obj, sample.get('snapshotType') or 'file',
                               sample.get('context') or 'publish', version=version, commit=False)
    snapshot.set_value('process', sample.get('process') or 'publish', temp=True)
    file = SearchType.create('sthpw/file')
    file.set_value('file_name', filename, temp=True)
    file.set_value('base_type', 'file', temp=True)
    file.set_value('type', sample.get('fileType') or 'main', temp=True)
    file_type = file.get_type()
    # Naming selection stays native, with the edited rule replacing its saved row.
    # The Container belongs to this request; restore caches even if evaluation fails.
    container = Container.get_instance().get_data()
    cache = {key: value for key, value in container.items() if key.startswith('Naming:')}
    policy_key = 'Expression:check_method_access'
    previous_policy = Container.get(policy_key)
    def check_preview_access(method):
        nonlocal executable
        executable = True
        if not allow_execution:
            raise UserException('This preview requires explicit permission to execute custom code.')
        if previous_policy:
            previous_policy(method)
    Container.put(policy_key, check_preview_access)
    try:
        for key in cache:
            Container.remove(key)
        candidates = [row for row in Search('config/naming').get_sobjects()
                      if not current or row.get_search_key() != current.get_search_key()]
        candidates.append(rule)
        Container.put('Naming:namings', candidates)
        selected = Naming.get(obj, snapshot, file_path=filename)
        matches = selected is rule
        versions = [('version', version)]
        if rule.get_value('latest_versionless'):
            versions.append(('latest', -1))
        if rule.get_value('current_versionless'):
            versions.append(('current', 0))
        results = []
        for mode, value in versions:
            snapshot.set_value('version', value, temp=True)
            selected_for_mode = Naming.get(obj, snapshot, file_path=filename)
            dirname = DirNaming(obj, snapshot, file_type=file_type, file_object=file)
            file_naming = FileNaming(obj, snapshot, file_object=file, ext=os.path.splitext(filename)[1])
            directory = dirname.get_from_naming(rule) or ''
            sandbox = dirname.get_from_naming(rule, 'sandbox') or ''
            name = file_naming.get_from_naming(rule, commit=False) or ''
            directory = str(directory).replace('\\', '/')
            name = str(name).replace('\\', '/')
            collisions = Search('sthpw/file')
            collisions.add_filter('relative_dir', directory)
            collisions.add_filter('file_name', name)
            alias = rule.get_value('base_dir_alias') or ''
            if alias:
                collisions.add_filter('base_dir_alias', alias)
            else:
                collisions.add_op_filters(['begin', ['base_dir_alias', 'is', 'NULL'], ['base_dir_alias', ''], 'or'])
            collisions.set_limit(10)
            results.append({'mode': mode, 'directory': directory, 'file': name,
                'sandbox': str(sandbox).replace('\\', '/'),
                'path': '/'.join(part for part in (directory.rstrip('/'), name) if part),
                'version': snapshot.get_value('version'), 'matches': selected_for_mode is rule,
                'selectedRule': selected_for_mode.get_code() if selected_for_mode and selected_for_mode is not rule else '',
                'collisions': [{'key': row.get_search_key(), 'snapshot': row.get_value('snapshot_code')}
                               for row in collisions.get_sobjects()] if directory and name else []})
        return {'results': results, 'matches': matches, 'executedCustomCode': executable}
    finally:
        if previous_policy is None:
            Container.remove(policy_key)
        else:
            Container.put(policy_key, previous_policy)
        for key in list(container):
            if key.startswith('Naming:'):
                Container.remove(key)
        for key, value in cache.items():
            Container.put(key, value)


class NamingCmd(Command):
    def execute(self):
        return naming_request(**self.kwargs)
