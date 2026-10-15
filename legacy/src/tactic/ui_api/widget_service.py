"""Authorized composed widget routes. Definitions always originate on server."""
from pathlib import Path
from .contracts import ApiError, clean_values, revision
from tactic.core.widget_containers import tab_model, tab_items, default_values, false


class WidgetService:
    def _tab_model(self, parent):
        from pyasm.common import Environment
        from pyasm.search import Search
        from pyasm.web import WidgetSettings
        base = (Path(Environment.get_install_dir()) / 'src/tactic/ui/config').resolve()
        def include_reader(name):
            path = (base / name).resolve()
            if not path.is_relative_to(base) or not path.is_file():
                raise ValueError('Недоступный include TabWdg')
            return path.read_text(encoding='utf-8')
        def db_reader(view):
            search = Search('config/widget_config')
            search.add_filter('category', 'TabWdg'); search.add_filter('view', view)
            obj = search.get_sobject()
            if obj:
                owner = obj.get_value('login', no_exception=True)
                if owner and owner != Environment.get_user_name():
                    raise ApiError(403, 'tab_owner', 'Чужая персональная конфигурация вкладок')
                return obj.get_value('config')
            return None
        try:
            return tab_model(parent.get('options', {}), include_reader, db_reader,
                             WidgetSettings.get_value_by_key)
        except (ValueError, TypeError) as exc:
            raise ApiError(400, 'tab_config', str(exc)) from exc

    def tab_children(self, parent):
        from pyasm.search import Search
        model, names, save_key = self._tab_model(parent)
        try:
            children = tab_items(parent, model, names, lambda expression, state: Search.eval(expression, state=state))
        except (ValueError, TypeError) as exc:
            raise ApiError(400, 'tab_config', str(exc)) from exc
        opts = parent.get('options', {})
        parent['container'] = {'view': model.view, 'revision': model.fingerprint(),
            'selected': next((c['id'] for c in children if c['selected']), None),
            'hide_header': opts.get('mode') == 'hidden',
            'show_context_menu': not false(opts.get('show_context_menu')),
            'allow_drag': not false(opts.get('allow_drag')),
            'save_state': save_key,
            'state_notice': 'Исходный save_state читается; native-настройки хранятся отдельно в sthpw/wdg_settings без перезаписи legacy XML.' if save_key else '',
            'source': 'tactic.ui.container.tab_wdg.TabWdg.get_display'}
        return children

    def bind_form_target(self, target):
        """Resolve legacy selector precedence, without privilege elevation."""
        from pyasm.search import Search
        opts = target.get('options', {})
        if opts.get('ticket'):
            raise ApiError(501, 'form_ticket', 'Устаревший ticket EditWdg не поддержан')
        obj = None; stype = target.get('search_type')
        if opts.get('search_key'):
            obj = Search.get_by_search_key(opts['search_key'])
        elif opts.get('expression'):
            obj = Search.eval(opts['expression'], single=True)
        elif opts.get('code'):
            self.require_type(stype)
            search = Search(stype); search.add_filter('code', opts['code']); obj = search.get_sobject()
        elif str(opts.get('search_id') or '-1') != '-1':
            self.require_type(stype)
            search = Search(stype); search.add_id_filter(int(opts['search_id'])); obj = search.get_sobject()
        has_selector = any(opts.get(n) for n in ('search_key', 'expression', 'code')) or str(opts.get('search_id') or '-1') != '-1'
        if has_selector and obj is None:
            raise ApiError(404, 'form_record', 'Запись из конфигурации EditWdg не найдена')
        if obj:
            actual = obj.get_base_search_type()
            if stype and actual != stype:
                raise ApiError(403, 'form_type', 'SearchType формы не совпадает с её записью')
            stype = actual
            # _object verifies the resolved object's search type and project.
            # Fixed-key binding below supplies the form's record scope.
            obj = self._object(stype, obj.get_search_key())
        self.require_type(stype)
        mode = opts.get('mode') or ('edit' if obj else 'insert')
        if mode not in ('edit', 'insert', 'view'):
            raise ApiError(501, 'form_mode', 'Режим EditWdg ещё не поддержан: ' + str(mode))
        if (mode == 'insert' and obj is not None) or (mode in ('edit','view') and obj is None):
            raise ApiError(400, 'form_mode', 'Режим формы противоречит заданной записи')
        if any(opts.get(n) for n in ('parent_key','connect_key','edit_cmd','cbjs_insert_path','cbjs_edit_path','cbjs_cancel','layout_view')):
            raise ApiError(501, 'form_action', 'Этот EditWdg требует ещё не перенесённого parent/connect/custom callback/layout adapter')
        target['search_type'] = stype
        target['form_binding'] = {'key': obj.get_search_key() if obj else None, 'mode': mode}
        return target

    def check_form_binding(self, opened, data, method, path):
        if opened.get('kind') != 'form':
            return
        if path in ('/view','/resolved-view') and method == 'GET':
            return
        binding = opened['form_binding']; key = data.get('key') or None
        if key != binding['key']:
            raise ApiError(403, 'form_binding', 'Нельзя подменить запись встроенного EditWdg')
        if path in ('/query', '/timeline', '/export-csv'):
            raise ApiError(400, 'form_not_table', 'EditWdg — форма, не таблица выборки')
        if method != 'GET' and binding['mode'] == 'view':
            raise ApiError(403, 'form_read_only', 'Форма работает в режиме view')
        if path == '/record' and method in ('POST','PATCH'):
            expected_method = 'POST' if binding['mode'] == 'insert' else 'PATCH'
            if method != expected_method:
                raise ApiError(403, 'form_method', 'Операция не соответствует режиму EditWdg')

    def embedded_form(self, method, data):
        opened = self.open_target(data.get('target'))
        if opened['kind'] != 'form':
            raise ApiError(400, 'form_target', 'Ссылка не является EditWdg')
        key = opened['form_binding']['key']; stype = opened['search_type']
        if data.get('key') not in (None, key):
            raise ApiError(403, 'form_binding', 'Подмена привязанной записи формы')
        if method == 'GET':
            result = self.form(stype, key)
            result['widget'] = {'mode': opened['form_binding']['mode'],
                'title': opened['options'].get('title') or opened['title'],
                'show_header': not false(opened['options'].get('show_header')),
                'show_action': not false(opened['options'].get('show_action')),
                'single': opened['options'].get('single') in (True, 'true')}
            return result
        self.check_form_binding(opened, dict(data, key=key), method, '/record')
        prepared = self.prepare_form(stype, key, data.get('values'))
        if prepared.get('dependency_notice'):
            raise ApiError(400, 'form_dependency', prepared['dependency_notice'])
        spec = prepared['spec']
        if method == 'PATCH' and spec['capabilities']['update']:
            values = clean_values(data.get('values'), spec['fields'])
            return self.update(stype, key, values, data.get('revision'), spec)
        if method == 'POST' and spec['capabilities']['create']:
            # Configured defaults follow the same field validation/action path.
            values = dict(prepared.get('defaults', {})); values.update(data.get('values') or {})
            return self.create(stype, clean_values(values, spec['fields']), spec)
        raise ApiError(403, 'read_only', 'Сохранение формы отключено')
