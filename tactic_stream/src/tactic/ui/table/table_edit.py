"""Handler table cell edits through the native EditWdg catalog and EditCmd."""
import hashlib
import json

from pyasm.command import Command
from pyasm.search import Search, SearchType
from pyasm.security.security import _require_admin
from tactic_stream.server.interface import read_interface, read_form
from tactic_stream.server.object_operations import selected_objects
from tactic.ui.panel import EditCmd
from pyasm.web import Web, WebContainer


class TableCellEditCmd(Command):
    def check_security(self):
        _require_admin()
        return True

    def execute(self):
        _require_admin()
        search_type = self.kwargs.get('search_type')
        view = self.kwargs.get('view', 'table')
        column = self.kwargs.get('column')
        action = self.kwargs.get('action', 'prepare')
        if action not in ('prepare', 'save', 'check') or not isinstance(column, str):
            raise ValueError('Invalid table cell operation')
        if action == 'save':
            for name in ('config/widget_config', search_type):
                sql = Search(name).get_sql()
                sql.get_database_impl().lock_collection_table(sql, SearchType.get(name).get_table())
        interface = read_interface(search_type, view)
        element = next((item for item in interface['table']['elements'] if item['name'] == column), None)
        if not interface['operations']['edit'] or not element or element['attributes'].get('edit') in (False, 'false'):
            raise ValueError('This table column is read-only')
        cell = element.get('cell', {})
        if not cell.get('editable'):
            raise ValueError('This table cell has no inline editor')
        edit_name = cell['editor']
        edit_view = cell.get('editor_view', 'edit')
        records = selected_objects(search_type, self.kwargs.get('search_keys'))
        plans, field, first_field = [], None, None
        for record in records:
            from tactic.ui.widget.misc_input_wdg import TaskStatusElementWdg
            from tactic_stream.server.table_cells import WIDGETS
            if WIDGETS.get(element['display']['handler']) is TaskStatusElementWdg:
                status_widget = TaskStatusElementWdg(name=column, **element['display']['options'])
                status_widget.set_sobject(record)
                status_widget.assert_editable()
            form = read_form(search_type, edit_view, record.get_search_key(), element_names=[edit_name])
            field = next((item for item in form['fields'] if item['name'] == edit_name), None)
            if not field:
                raise ValueError('This column is not in the native edit view')
            if first_field is None:
                first_field = field
            target = field['action']['options'].get('column') or field['options'].get('column') or field['name']
            if target in ('id', 'code', 'project_code', 'timestamp', 'login') or field['options'].get('read_only') in (True, 'true') or field.get('input', {}).get('read_only'):
                raise ValueError('This table column is read-only')
            if not SearchType.column_exists(search_type, target) or field.get('input', {}).get('type') in ('file', 'multi-upload', 'parent', 'hidden'):
                raise ValueError('This table cell has no inline editor')
            revision = hashlib.sha256(json.dumps([record.get_data(), element, field], sort_keys=True, default=str).encode()).hexdigest()
            plans.append(dict(search_key=record.get_search_key(), expected_revision=revision))
        if action == 'prepare':
            return dict(field=first_field, plans=plans)
        expected = self.kwargs.get('plans')
        if not isinstance(expected, list) or len(expected) != len(plans) or any(not isinstance(item, dict) for item in expected):
            raise ValueError('Reload the table cell before saving')
        if {item.get('search_key') for item in expected} != {item['search_key'] for item in plans}:
            raise ValueError('Table selection changed. Reload before saving.')
        value = self.kwargs.get('value')
        if isinstance(value, (dict, tuple)) or isinstance(value, list) and not all(isinstance(item, (str, int, float, bool)) for item in value):
            raise ValueError('Invalid table cell value')
        if len(json.dumps(value, default=str).encode()) > 512 * 1024:
            raise ValueError('Table cell value is too large')
        if action == 'check':
            states = []
            for record, plan in zip(records, plans):
                original = next(item for item in expected if item['search_key'] == plan['search_key'])
                actual = record.get_value(target, no_exception=True)
                if field.get('input', {}).get('type') in ('date', 'datetime-local', 'time'):
                    from dateutil import parser
                    actual_date = parser.parse(str(actual)) if actual else None
                    wanted_date = parser.parse(str(value)) if value else None
                    if field['input']['type'] == 'time':
                        actual_date = actual_date.strftime('%H:%M') if actual_date else ''
                        wanted_date = wanted_date.strftime('%H:%M') if wanted_date else ''
                    matches = actual_date == wanted_date
                elif field['class_name'].rsplit('.', 1)[-1] == 'CheckboxWdg':
                    checked = lambda item: item in (True, 1, '1', 'true', 'on', 'yes')
                    matches = checked(actual) == checked(value)
                else:
                    matches = str(actual or '') == str(value or '')
                states.append('saved' if matches else 'unchanged' if plan['expected_revision'] == original.get('expected_revision') else 'conflict')
            return dict(state=states[0] if len(set(states)) == 1 else 'conflict')
        for plan in plans:
            original = next(item for item in expected if item['search_key'] == plan['search_key'])
            if plan['expected_revision'] != original.get('expected_revision'):
                raise ValueError('Records or definitions changed. Reload before saving.')
        # Every revision is checked before the first native action; the outer Command rolls back the batch.
        changed = []
        for record in records:
            options = dict(data={edit_name: value})
            previous_web = WebContainer.get_web()
            if field['action']['handler'] in ('TimeAction', 'pyasm.command.TimeAction', 'pyasm.command.edit_wdg_action.TimeAction'):
                from datetime import time
                parsed = time.fromisoformat(str(value))
                options = dict(element_names=[edit_name])
                WebContainer.set_web(Web({**getattr(previous_web, 'params', {}), 'edit|' + edit_name + '|hour': parsed.hour, 'edit|' + edit_name + '|minute': parsed.minute}))
            try:
                command = EditCmd(search_key=record.get_search_key(), view=edit_view, **options)
                Command.execute_cmd(command)
            finally:
                WebContainer.set_web(previous_web)
            changed.extend(command.get_sobjects())
        from tactic_stream.server.api import ApiXMLRPC
        return dict(search_keys=[record.get_search_key() for record in records], records=ApiXMLRPC._get_sobjects_dict(changed))
