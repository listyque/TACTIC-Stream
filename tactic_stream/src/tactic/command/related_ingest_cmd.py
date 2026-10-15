"""Handler relation ingest/preflight on the native upload command and transaction."""
import json
import os

from pyasm.command import Command
from pyasm.biz import Project
from pyasm.search import Search, SearchKey, SearchType
from pyasm.security.security import _require_admin
from tactic_stream.server.result_items import objects, relations, relation_search
from tactic_stream.server.interface import read_interface
from tactic_stream.server.api import upload_file_name
from .ingest_paths import prepare_ingest_path


DEFAULTS = dict(title='Quick ingest', filter='', ignore='', pattern='', usePattern=False,
    column='name', ignoreExtension=True, updateMode='insert', process='publish', context='publish',
    contextMode='case_sensitive', keywords='', keywordMode='default', extraData={},
    validationScript='', processScript='', createIcon=True)


def flag(value):
    return value.strip().lower() in ('1', 'true', 'yes', 'on', 'update') if isinstance(value, str) else bool(value)


def rule_options(row, column):
    data = row.get('data') or {}
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        raise ValueError('Invalid ingest options')
    extra = data.get('extra_data') or dict(zip(data.get('extra_name') or [], data.get('extra_value') or []))
    if isinstance(extra, str):
        extra = json.loads(extra)
    pattern = data.get('rule') or row.get('rule') or ''
    return dict(DEFAULTS, title=row.get('title') or 'Quick ingest', filter=data.get('filter') or '',
        ignore=data.get('ignore') or '', pattern=pattern, usePattern=bool(pattern), column=data.get('column') or column,
        ignoreExtension=flag(data.get('ignore_ext', True)), updateMode='update' if flag(data.get('update_mode')) else 'insert',
        process=data.get('process') or 'publish', context=data.get('context') or 'publish',
        contextMode=data.get('context_mode') or 'case_sensitive', keywords=data.get('keywords') or '',
        keywordMode=data.get('keyword_mode') or 'default', extraData=extra,
        validationScript=data.get('validation_script') or '', processScript=data.get('process_script') or '',
        createIcon=flag(data.get('create_icon', True)))


class RelatedIngestCmd(Command):
    def execute(self):
        _require_admin()
        key = self.kwargs.get('parent_key')
        if not isinstance(key, str) or not key:
            raise ValueError('Choose a parent object')
        parent = next(iter(objects(SearchKey.extract_base_search_type(key), [key]).values()))
        target, path = self.kwargs.get('search_type'), self.kwargs.get('path') or ''
        branch = next((row for row in relations(parent) if row['search_type'] == target and row['path'] == path), None)
        if not branch or branch['relationship'] not in ('code', 'id', 'search_type', 'search_code', 'search_id', 'instance'):
            raise ValueError('Select a child relation before ingesting files')
        permissions = read_interface(target)['operations']
        if not permissions.get('create') or not permissions.get('checkin'):
            raise ValueError('This child relation cannot ingest files')
        column = 'name' if SearchType.column_exists(target, 'name') else 'code'
        action = self.kwargs.get('action')
        if action == 'rules':
            rows = [dict(code='', title='Quick ingest', applicable=True, options=dict(DEFAULTS, column=column))]
            for rule in Search('config/ingest_rule').get_sobjects():
                row = rule.get_sobject_dict()
                try:
                    data = rule.get_json_value('data') or {}
                    if not isinstance(data, dict):
                        raise ValueError('Invalid ingest options')
                    applicable = data.get('search_type') in (None, '', target) and data.get('action', 'file') in ('', 'file') and data.get('action_type', 'checkin') in ('', 'checkin')
                    options = rule_options(row, column)
                    self.validate(options, target)
                    rows.append(dict(code=rule.get_code(), key=rule.get_search_key(), title=rule.get_value('title') or rule.get_code(), applicable=applicable, options=options))
                except (ValueError, TypeError):
                    rows.append(dict(code=rule.get_code(), title=rule.get_value('title') or rule.get_code(), applicable=False, options={}))
            self.info['rules'] = rows
            return self.info
        options = dict(DEFAULTS, column=column)
        supplied = self.kwargs.get('options') or {}
        if not isinstance(supplied, dict) or set(supplied) - DEFAULTS.keys():
            raise ValueError('Invalid ingest options')
        options.update(supplied)
        self.validate(options, target)
        names = self.kwargs.get('filenames')
        if not isinstance(names, list) or not 1 <= len(names) <= 100 or any(not isinstance(name, str) or upload_file_name(name) != name for name in names):
            raise ValueError('Choose up to 100 uploaded files')
        prepared = [prepare_ingest_path(name, options) for name in names]
        for name, item in zip(names, prepared):
            if item['accepted']:
                self.validate(dict(options, extraData=item['extraData'], context=item['context']), target)
            item['name'] = str(item.get('extraData', {}).get(options['column']) or (os.path.splitext(name)[0] if options['ignoreExtension'] else name))
            item['matches'] = []
        accepted = [item['name'] for item in prepared if item['accepted']]
        search = relation_search(parent, branch)
        search.add_filters(options['column'], accepted)
        matches = search.get_sobjects() if accepted else []
        for item in prepared:
            if not item['accepted']:
                continue
            item['matches'] = [row.get_search_key() for row in matches if str(row.get_value(options['column'])).casefold() == item['name'].casefold()]
            item['conflict'] = bool(item['matches']) or sum(other['accepted'] and other['name'].casefold() == item['name'].casefold() for other in prepared) > 1
        if action == 'scan':
            self.info['files'] = prepared
            return self.info
        if action != 'checkin' or len(names) != 1:
            raise ValueError('Ingest one file per child object')
        item = prepared[0]
        if not item['accepted']:
            self.info.update(skipped=True, reason=item['reason'])
            return self.info
        decision = self.kwargs.get('decision', 'new')
        if decision not in ('new', 'duplicates', 'skip', 'update'):
            raise ValueError('Choose how to resolve matching items')
        if item.get('conflict') and decision == 'new':
            raise ValueError('Matching items changed. Check conflicts again before ingesting.')
        if item.get('conflict') and decision == 'skip':
            self.info.update(skipped=True, reason='Matching item already exists')
            return self.info
        existing = ''
        if decision == 'update':
            expected = self.kwargs.get('search_key')
            if len(item['matches']) != 1 or item['matches'][0] != expected or not permissions.get('edit'):
                raise ValueError('Update requires exactly one matching child item')
            existing = expected
        from .ingest_hooks import ingest_rule_preflight
        from .ingestion_cmd import IngestException
        from tactic.ui.tools.ingest_wdg import IngestUploadCmd
        preflight = ingest_rule_preflight(target, key, names[0], options['column'], options['ignoreExtension'],
            item['extraData'], options['validationScript'], options['processScript'], existing)
        if not preflight['accepted']:
            raise IngestException(preflight['reason'])
        extra = dict(item['extraData'])
        extra.update({name: value for name, value in preflight['data'].items() if name not in ('id', 'code', '__search_key__', '_search_type', 'project_code', 'search_type', 'search_id', 'timestamp')})
        attrs = parent.get_schema().get_relationship_attrs(target, parent.get_base_search_type(), path=path or None)
        attrs = parent.get_schema().resolve_relationship_attrs(attrs, target, parent.get_search_type())
        if branch['relationship'] in ('code', 'id'):
            extra[attrs['from_col']] = parent.get_value(attrs['to_col'])
        args = dict(search_type=target, parent_key=key, filenames=names, update_data={}, extra_data=json.dumps(extra),
            process=options['process'], context=preflight['snapshot_data'].get('context') or item['context'],
            update_mode='true' if existing else 'false', ignore_ext='true' if options['ignoreExtension'] else 'false',
            column=options['column'], keywords=options['keywords'], keyword_mode=options['keywordMode'],
            context_mode=options['contextMode'], create_icon=options['createIcon'], project_code=Project.get_project_code())
        if existing:
            args['search_key'] = existing
        command = IngestUploadCmd(**args)
        Command.execute_cmd(command)
        snapshot = command.info['snapshots'][-1]
        child = Search.get_by_code(target, snapshot['search_code'])
        if not child:
            raise LookupError('Ingest snapshot has no parent Search Object')
        # Handler links the exact newly created child in the same transaction.
        if not existing:
            if branch['relationship'] == 'instance':
                from .sobject_link_cmd import SObjectLinkCmd
                Command.execute_cmd(SObjectLinkCmd(parent_key=key, search_type=target, path=path, insert_search_keys=[child.get_search_key()]))
            else:
                if branch['relationship'] in ('code', 'id'):
                    child.set_value(attrs['from_col'], parent.get_value(attrs['to_col']))
                else:
                    child.set_sobject_value(parent)
                child.commit()
        self.info.update(snapshot=snapshot, search_key=child.get_search_key())
        return self.info

    def validate(self, options, target):
        for name in ('title', 'filter', 'ignore', 'pattern', 'column', 'updateMode', 'process', 'context', 'contextMode', 'keywords', 'keywordMode', 'validationScript', 'processScript'):
            if not isinstance(options[name], str) or len(options[name]) > 4096:
                raise ValueError('Invalid ingest options')
        if options['column'] not in ('name', 'code') or not SearchType.column_exists(target, options['column']):
            raise ValueError('Choose an existing name or code column')
        if options['updateMode'] not in ('insert', 'update') or options['contextMode'] not in ('case_sensitive', 'case_insensitive') or options['keywordMode'] not in ('default', 'simplified', 'none') or not options['process'].strip() or not options['context'].strip():
            raise ValueError('Invalid ingest options')
        for name in ('usePattern', 'ignoreExtension', 'createIcon'):
            if type(options[name]) is not bool:
                raise ValueError('Invalid ingest options')
        extra = options['extraData']
        if not isinstance(extra, dict) or len(extra) > 100 or any(name in ('id', '__search_key__', '_search_type', 'project_code', 'search_type', 'search_id', 'search_code', 'timestamp') or not SearchType.column_exists(target, name) or isinstance(value, (dict, list)) for name, value in extra.items()):
            raise ValueError('Extra values must use editable Search Object columns')
