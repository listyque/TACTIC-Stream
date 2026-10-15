"""Native CellEditWdg and Save Changes, over the original command lifecycle.

A batch contains changed values only, never arbitrary command paths/extra_action.
All rows and definitions are checked before the first original action executes.
"""
from contextlib import contextmanager
import copy
import json
from .action_log import execute_traced
from .contracts import ApiError, clean_values, revision, safe_element, view_name
from tactic.core.field_policy import field_access
from tactic.core.cell_edit_config import cell_config, save_config, CellConfigModel

MAX_ROWS = 100
MAX_CELLS = 1000
# Known data-input actions. Custom Python remains on the legacy path until its
# input contract has a native adapter; it is never replaced by DatabaseAction.
ACTION_CLASSES = {'DatabaseAction', 'ExplicitDatabaseAction', 'NonEmptyAction',
                  'ExplicitNonEmptyAction', 'TaskDateAction', 'ExplicitTaskDateAction',
                  'DefaultValueDatabaseAction', 'NullAction', 'LoginAction',
                  'PasswordAction', 'ExplicitPasswordAction', 'SubContextAction'}


class TableEditService:
    def _table_edit_target(self, data):
        opened = self.open_target(data.get('target'))
        if opened['kind'] != 'table':
            raise ApiError(400, 'table_edit', 'Редактор ячеек доступен только для TableLayoutWdg')
        opts = opened.get('options', {})
        # Do not silently skip original custom save hooks or related inserts.
        for name in ('save_class_name', 'save_cmd', 'extra_action', 'extra_data', 'parent_key', 'connect_key'):
            if opts.get(name):
                raise ApiError(501, 'table_save_adapter', 'Таблица требует отдельного адаптера: '+name)
        return opened

    def _table_save_options(self, opened):
        opts = opened.get('options', {})
        view = view_name(opts.get('edit_view') or 'edit_item')
        xml = opts.get('edit_config_xml') or opts.get('config_xml')
        if xml:
            from tactic.core.view_resolution import inline_xml
            xml = inline_xml(xml)
        return view, xml

    @contextmanager
    def _cell_context(self, opened, names):
        stype = opened['search_type']
        _, xml = self._table_save_options(opened)
        view, save_xml = self._table_save_options(opened)
        # CellEditWdg gets the edit-config XML attached by the table. edit_item
        # overrides it exactly as in the original implementation.
        config = cell_config(stype, xml)
        actions = save_config(stype, names, view, save_xml)
        model = CellConfigModel(config, actions, names)
        old = getattr(self, '_native_cell_model', None)
        self._native_cell_model = (stype, model)
        try:
            yield model
        finally:
            self._native_cell_model = old

    def _checked_cell_form(self, opened, key, names, pending=None):
        from pyasm.common import Environment
        fields = {f['name']: f for f in opened['spec']['fields']}
        if not names or any(not safe_element(n) or n not in fields for n in names):
            raise ApiError(403, 'cell_field', 'Поле отсутствует в разрешённой таблице')
        for name in names:
            field = fields[name]
            attrs = field.get('config_attributes') or {}
            visible, editable = field_access(Environment.get_security(), self._project(), opened['search_type'], name, attrs)
            options = field.get('display_options') or {}
            if not visible or not editable or attrs.get('edit') in (False,'false') or options.get('read_only') in (True,'true'):
                raise ApiError(403, 'cell_read_only', 'Ячейка запрещена для редактирования: '+name)
        with self._cell_context(opened, names) as model:
            result = self.prepare_form(opened['search_type'], key, pending or {})
            result['cell_config_revision'] = revision({'model':model.fingerprint(),
                                                       'table':opened['spec']['revision']})
        if result.get('dependency_notice'):
            raise ApiError(400, 'cell_dependency', result['dependency_notice'])
        result['spec']['view'] = self._table_save_options(opened)[0]
        return result

    def _check_actions(self, stype, key, values, view, xml):
        from tactic.core.native_edit import NativeEditCmd
        cmd = NativeEditCmd(sobject=self._object(stype,key), view=view, data=values,
                            input_prefix='__NONE__', config_xml=xml)
        cmd.search_type = stype
        for handler in cmd._get_action_handlers():
            if type(handler).__name__ not in ACTION_CLASSES:
                raise ApiError(501, 'cell_action', 'Не перенесён input-контракт action: '+type(handler).__name__)
            # Form/value expressions belong to a separate adapter. Defaults are
            # trusted server definitions and keep their original action.
            if handler.get_option('expression') and type(handler).__name__ != 'DefaultValueDatabaseAction':
                raise ApiError(501, 'cell_action_expression', 'Вычисляемый action требует отдельного адаптера')

    def table_fill_preview(self, opened, data):
        """Validate per-row CellEdit definitions, never execute an action or commit.

        UI acceptance stages these values in the existing grid buffer. Save
        Changes subsequently checks EVERYTHING again and executes EditMultipleCmd.
        This is not a new database bulk UPDATE and not a saved permission token.
        """
        spec, stype = opened['spec'], opened['search_type']
        if not self.allow_writes or not spec['capabilities']['update']:
            raise ApiError(403, 'read_only', 'Запись этой таблицы отключена')
        if data.get('table_revision') != spec['revision']:
            raise ApiError(409, 'config_conflict', 'Конфигурация таблицы изменилась')
        rows, name = data.get('records'), data.get('field')
        if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS:
            raise ApiError(400, 'table_rows', 'От 1 до 100 выбранных строк')
        if not isinstance(name, str) or not safe_element(name) or 'value' not in data:
            raise ApiError(400, 'cell_field', 'Нужно поле и явное значение, включая NULL')
        keys = [item.get('key') if isinstance(item, dict) else None for item in rows]
        if any(not isinstance(k, str) for k in keys) or len(set(keys)) != len(keys):
            raise ApiError(400, 'table_keys', 'Ожидаются уникальные ключи строк')
        result = []
        view, xml = self._table_save_options(opened)
        for item in rows:
            pending = item.get('pending', {})
            if not isinstance(pending, dict) or len(pending) > 100:
                raise ApiError(400, 'cell_pending', 'Некорректный буфер строки')
            values = dict(pending); values[name] = data['value']
            form = self._checked_cell_form(opened, item['key'], list(values), values)
            if form['record']['revision'] != item.get('revision'):
                raise ApiError(409, 'conflict', 'Выбранная запись изменилась', {'key':item['key']})
            if item.get('config_revision') and item['config_revision'] != form['cell_config_revision']:
                raise ApiError(409, 'config_conflict', 'Определение редактора изменилось', {'key':item['key']})
            field = next((f for f in form['spec']['fields'] if f['name'] == name), None)
            if not field or not field['supported'] or field['read_only']:
                raise ApiError(403, 'cell_read_only', 'Недоступный редактор для поля '+name)
            clean = clean_values(values, form['spec']['fields'])
            self.check_native_write(stype, clean, item['key'])
            action = str(field.get('action') or 'DatabaseAction').rsplit('.', 1)[-1]
            if action not in ACTION_CLASSES:
                raise ApiError(501, 'cell_action', 'Action требует отдельного адаптера: '+action)
            # Never instantiate or execute action handlers merely for preview.
            # Save Changes performs its full original action/transaction checks.
            # Keep exact user numeric strings in the draft. clean_values already
            # validated them; JSON numbers would round large integer input in JS.
            result.append({'key':item['key'], 'field':field, 'original':form['record']['values'].get(name),
                           'value':data['value'], 'revision':form['record']['revision'],
                           'config_revision':form['cell_config_revision'], 'table_revision':spec['revision']})
        return {'items':result, 'table_revision':spec['revision'], 'writes_performed':False,
                'notice':'Проверены редакторы, типы и ревизии. Данные ещё не записаны. '
                         'Окончательные actions/триггеры выполняются только при Save Changes.'}

    def table_edit_operation(self, method, path, data):
        opened = self._table_edit_target(data)
        stype, spec = opened['search_type'], opened['spec']
        if path == '/table-fill-preview':
            if method != 'POST': raise ApiError(405, 'method', 'POST required')
            return self.table_fill_preview(opened, data)
        if path == '/cell-editor' and method in ('GET', 'POST'):
            key, name = data.get('key'), data.get('field')
            pending = data.get('pending') or {}
            if not isinstance(pending, dict):
                raise ApiError(400,'cell_pending','Ожидаются изменённые поля строки')
            if not isinstance(name,str) or len(pending)>100 or any(not isinstance(n,str) for n in pending):
                raise ApiError(400,'cell_field','Некорректное имя поля или слишком много полей')
            names = list(dict.fromkeys(list(pending) + [name]))
            form = self._checked_cell_form(opened, key, names, pending)
            if data.get('revision') and form['record']['revision'] != data['revision']:
                raise ApiError(409,'conflict','Запись изменилась; обновите её до редактирования')
            field = next((f for f in form['spec']['fields'] if f['name']==name), None)
            if not field or field['read_only'] or not field['supported']:
                raise ApiError(403,'cell_read_only',(field or {}).get('reason') or 'Для этой ячейки нет разрешённого редактора')
            if pending:
                clean_values(pending, form['spec']['fields'])
            return {'field':field, 'value':form['record']['values'].get(name),
                    'revision':form['record']['revision'], 'config_revision':form['cell_config_revision'],
                    'table_revision':spec['revision'], 'save_view':form['spec']['view'],
                    'source':'CellEditWdg: edit + inline edit + DB edit_item',
                    'key':key}
        if path != '/table-changes' or method != 'POST':
            raise ApiError(405,'method','Метод не поддерживается')
        if not self.allow_writes or not spec['capabilities']['update']:
            raise ApiError(403,'read_only','Запись этой таблицы отключена')
        rows = data.get('records')
        if not isinstance(rows,list) or not 1 <= len(rows) <= MAX_ROWS:
            raise ApiError(400,'table_rows','От 1 до 100 изменённых строк')
        keys = [r.get('key') if isinstance(r,dict) else None for r in rows]
        if any(not isinstance(k,str) for k in keys) or len(set(keys)) != len(keys):
            raise ApiError(400,'table_keys','Ожидаются уникальные ключи строк')
        if any(not isinstance(r.get('values'),dict) or not r['values'] for r in rows) or sum(len(r['values']) for r in rows)>MAX_CELLS:
            raise ApiError(400,'table_cells','От 1 до 1000 изменённых ячеек')
        if data.get('table_revision') != spec['revision']:
            raise ApiError(409,'config_conflict','Конфигурация таблицы изменилась. Буфер сохранён; перечитайте представление.')
        view, xml = self._table_save_options(opened)
        def apply():
            pending = []
            for item in rows:
                names = list(item['values'])
                form = self._checked_cell_form(opened,item['key'],names,item['values'])
                if form['record']['revision'] != item.get('revision'):
                    raise ApiError(409,'conflict','Изменённая строка уже обновлена другим запросом',{'key':item['key']})
                if form['cell_config_revision'] != item.get('config_revision'):
                    raise ApiError(409,'config_conflict','Определения редакторов изменились',{'key':item['key']})
                values = clean_values(item['values'],form['spec']['fields'])
                self.check_native_write(stype,values,item['key'])
                self._check_actions(stype,item['key'],values,view,xml)
                pending.append(values)
            from tactic.core.native_edit import NativeTableEditMultipleCmd
            cmd = NativeTableEditMultipleCmd(search_keys=keys, view=view,
                element_names=list(dict.fromkeys(n for values in pending for n in values)),
                update_data=json.dumps(pending,ensure_ascii=False),
                extra_data=json.dumps([{} for _ in rows]), extra_action=json.dumps([{} for _ in rows]),
                input_prefix='__NONE__', config_xml=xml, trigger_mode=True)
            execute_traced(cmd)
            return {'updated':len(rows), 'cells':sum(len(v) for v in pending),
                    'keys':cmd.info['search_keys'], 'transaction':'TACTIC Command / EditMultipleCmd',
                    'save_view':view}
        from pyasm.common import UserException
        try:
            return self._write(apply)
        except UserException as exc:
            # The original transaction has already rolled back. Report its
            # validation error, not a success or a partial-save notification.
            raise ApiError(400, 'action_validation', str(exc)[:500]) from exc
