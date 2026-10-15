"""Validated Command boundary for Handler's duplication procedures."""
import hashlib
import json

from pyasm.command import Command
from pyasm.common import UserException
from pyasm.search import SearchKey
from tactic_stream.server.result_items import objects
from tactic_stream.server.interface import read_form, read_interface
from .sobject_duplicate import analyze_sobject_duplicate, duplicate_sobject_advanced

CHOICES = ('copySnapshots', 'copyTasks', 'copyProcessMessages', 'copyTaskMessages',
           'copyProcessAttachments', 'copyTaskAttachments')


class SObjectDuplicateCmd(Command):
    def execute(self):
        key = self.kwargs.get('search_key')
        if not isinstance(key, str) or not key:
            raise ValueError('Select an object to duplicate')
        base = SearchKey.extract_base_search_type(key)
        objects(base, [key])
        if base in ('sthpw/file', 'sthpw/snapshot') or not read_interface(base)['operations'].get('create'):
            raise ValueError('This object cannot be duplicated')
        analysis = json.loads(analyze_sobject_duplicate(key))
        revision = hashlib.sha256(json.dumps(analysis, sort_keys=True).encode()).hexdigest()
        form = read_form(base, search_key=key)
        widgets = {(field['options'].get('column') or field['name']): field for field in form['fields']}
        if self.kwargs.get('action') == 'analyze':
            for field in analysis['fields']:
                field['widget'] = widgets.get(field['name'])
            self.info.update(analysis=analysis, revision=revision)
            return self.info
        if self.kwargs.get('action') != 'duplicate':
            raise ValueError('Choose analyze or duplicate')
        if self.kwargs.get('revision') != revision:
            raise UserException('Source content changed. Analyze again before duplicating.')
        options = self.kwargs.get('options')
        if not isinstance(options, dict) or set(options) != {'fields', 'relations', 'processes'}:
            raise ValueError('Invalid duplication options')
        fields, relations, processes = options['fields'], options['relations'], options['processes']
        if not all(isinstance(value, dict) for value in (fields, relations, processes)):
            raise ValueError('Invalid duplication options')
        allowed = {field['name'] for field in analysis['fields']
                   if widgets.get(field['name'], {}).get('options', {}).get('read_only') not in (True, 'true')
                   and not widgets.get(field['name'], {}).get('input', {}).get('read_only')}
        if fields.keys() - allowed or any(isinstance(value, (dict, list)) for value in fields.values()):
            raise ValueError('Use only editable object fields')
        available = {relation['key']: {option['value'] for option in relation['options']} for relation in analysis['relations']}
        if relations.keys() - available.keys() or any(mode not in available[name] for name, mode in relations.items()):
            raise ValueError('Choose an available relationship mode')
        available_processes = {process['name'] for process in analysis['processes']}
        if processes.keys() - available_processes:
            raise ValueError('Choose an existing process')
        for choice in processes.values():
            if not isinstance(choice, dict) or choice.keys() - set(CHOICES) or any(type(value) is not bool for value in choice.values()):
                raise ValueError('Invalid process content choices')
            if choice.get('copyTaskAttachments'):
                choice.update(copyTaskMessages=True, copyTasks=True)
            if choice.get('copyTaskMessages'):
                choice['copyTasks'] = True
            if choice.get('copyProcessAttachments'):
                choice['copyProcessMessages'] = True
        # Native setters retain numeric/date/null conversion and transaction ACLs.
        self.info['result'] = json.loads(duplicate_sobject_advanced(key, options))
        return self.info
