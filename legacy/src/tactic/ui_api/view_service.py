"""Resolve/edit actual TACTIC views; no client-local replacement configuration."""
import json
import re
import uuid
from pathlib import Path
import xml.etree.ElementTree as ET
from tactic.core.config_model import ConfigModel, ConfigSource, parse_xml, view_node, xml_text, target_spec
from tactic.core.view_edits import patch_view
from .contracts import ApiError, revision


class ViewService:
    def view_operation(self, method, data):
        from pyasm.common import Environment
        from pyasm.search import Search, SearchType
        if not Environment.get_security().is_admin():
            raise ApiError(403, 'admin_only', 'Редактирование представлений доступно администраторам')
        stype, view = data.get('search_type'), data.get('view') or 'table'
        if not isinstance(stype, str) or not re.fullmatch(r'[A-Za-z0-9_/.\-]{1,200}', stype):
            raise ApiError(400, 'search_type', 'Некорректный тип конфигурации')
        if not isinstance(view, str) or not re.fullmatch(r'[A-Za-z0-9_@.:-]{1,200}', view):
            raise ApiError(400, 'view', 'Некорректное имя view')
        if stype == 'SideBarWdg':
            from tactic.core.sidebar_config import SidebarConfig
            model = ConfigModel.from_tactic(SidebarConfig.get_config(stype, view, personal=view.startswith('my_view_')))
        else:
            self.require_type(stype)
            model = self._model(stype, view)
        if method == 'GET':
            rows = Search('config/widget_config'); rows.add_filter('search_type', stype); rows.add_order_by('view'); rows.set_limit(500)
            choices = sorted(set(['table', 'edit', 'insert'] + [o.get_value('view') for o in rows.get_sobjects() if o.get_value('view')]))
            return {'search_type': stype, 'view': view, 'elements': model.elements(),
                    'attributes': model.attributes(), 'revision': model.fingerprint(),
                    'layers': [{'view': s.view, 'origin': s.origin, 'xml': s.text} for s in model.sources],
                    'views': choices, 'can_write': self.allow_writes,
                    'columns': self._stub().get_column_info(stype) if stype != 'SideBarWdg' else {}}
        if method != 'PATCH':
            raise ApiError(405, 'method', 'Метод не поддерживается')
        if model.fingerprint() != data.get('revision'):
            raise ApiError(409, 'conflict', 'Наследуемая конфигурация изменилась')
        login = data.get('login') or None
        if login not in (None, Environment.get_user_name()):
            raise ApiError(400, 'scope', 'Допустим общий или собственный personal override')
        operations = data.get('operations')
        def save():
            search = Search('config/widget_config'); search.add_filter('search_type', stype); search.add_filter('view', view)
            search.add_filter('login', login); search.add_order_by('priority desc')
            obj = search.get_sobject()
            if obj:
                original = obj.get_value('config')
                existing = view_node(parse_xml(original), view)
                if existing is None or [el.get('name', '') for el in existing if el.tag == 'element'] != model.names():
                    raise ApiError(409, 'scope_order', 'Порядок выбранного override отличается от разрешённого view. Отредактируйте этот слой в XML-редакторе.')
            else:
                # New override contains inherited ORDER only. Definitions continue
                # to resolve through the original lower layers instead of being flattened.
                root = ET.Element('config')
                tag = ET.SubElement(root, 'view', {'name': view}) if '@' in view else ET.SubElement(root, view)
                for name in model.names():
                    ET.SubElement(tag, 'element', {'name': name})
                original = xml_text(root)
            try:
                updated = patch_view(original, view, operations)
            except ValueError as exc:
                raise ApiError(400, 'view_patch', str(exc)) from exc
            if not obj:
                obj = SearchType.create('config/widget_config'); obj.set_value('search_type', stype)
                obj.set_value('view', view); obj.set_value('login', login)
                if stype == 'SideBarWdg': obj.set_value('category', 'SideBarWdg')
            obj.set_value('config', updated); obj.commit()
            return {'saved': True, 'key': obj.get_search_key(), 'revision': revision(updated)}
        return self._write(save)

    def saved_view(self, data):
        from pyasm.common import Environment
        from pyasm.search import Search, SearchType
        from tactic.core.sidebar_config import SidebarConfig
        from .contracts import clean_query
        target = self.open_target(data.get('target'))
        if target['kind'] not in ('table', 'form'):
            raise ApiError(400, 'view', 'Сохранить поиск можно из таблицы')
        label = data.get('title')
        if not isinstance(label, str) or not label.strip() or len(label) > 200:
            raise ApiError(400, 'title', 'Нужно название представления')
        query = clean_query(data, target['spec']['fields'], target['spec'].get('default_sort'))
        if query.get('record_state','active') != 'active':
            raise ApiError(400,'retire_mode','Режим архива нельзя без потери сохранить в старом формате; вернитесь к активным записям')
        login = Environment.get_user_name(); view = 'my_view_' + login.replace('\\', '_')
        element_name = 'native_' + uuid.uuid4().hex[:12]
        opts = {k: v for k, v in target['options'].items() if k != 'class_name' and not k.startswith('native_')}
        if 'native_parent_key' in target['options']:
            raise ApiError(400, 'related_view', 'Сохранение поисков из временной связанной таблицы ещё не поддержано')
        from tactic.core.query_model import merge_saved
        try:
            vendor = Search(target['search_type']).get_database_impl().get_database_type()
            rules = merge_saved(opts.get('filter') or [], query.get('where'), target['spec']['fields'], vendor)
        except ValueError as exc:
            raise ApiError(400, 'filter', str(exc)) from exc
        opts.update(search_type=target['search_type'], view=target['view'], filter=json.dumps(rules, ensure_ascii=False))
        orders = [o for o in query.get('sorts', [query['sort']]) if o['field'] is not None]
        if orders:
            opts['order_by'] = ', '.join(o['field'] + ' ' + o['direction'] for o in orders)
        # Validate/encode options before entering the write operation.
        from tactic.core.config_options import append_option
        option_tree = ET.Element('options')
        try:
            for key, value in opts.items(): append_option(option_tree, key, value)
        except ValueError as exc:
            raise ApiError(400, 'view_options', str(exc)) from exc
        def save():
            search = Search('config/widget_config'); search.add_filter('search_type', 'SideBarWdg')
            search.add_filter('view', view); search.add_filter('login', login); search.add_order_by('priority desc')
            obj = search.get_sobject()
            if obj:
                root = parse_xml(obj.get_value('config')); node = view_node(root, view)
                if node is None: raise ApiError(400, 'view', 'Personal view отсутствует в записи')
            else:
                model = ConfigModel.from_tactic(SidebarConfig.get_config('SideBarWdg', view, personal=True))
                root = ET.Element('config'); node = ET.SubElement(root, view)
                for name in model.names(): ET.SubElement(node, 'element', {'name': name})
                obj = SearchType.create('config/widget_config'); obj.set_value('search_type', 'SideBarWdg')
                obj.set_value('category', 'SideBarWdg'); obj.set_value('view', view); obj.set_value('login', login)
            el = ET.SubElement(node, 'element', {'name': element_name, 'title': label.strip()})
            display = ET.SubElement(el, 'display', {'class': 'tactic.ui.panel.ViewPanelWdg'})
            for child in option_tree:
                display.append(child)
            obj.set_value('config', xml_text(root)); obj.commit()
            return {'saved': True, 'view': view, 'name': element_name, 'key': obj.get_search_key()}
        return self._write(save)

    def tab_children(self, parent):
        """Mirror TabWdg's include/category lookup without constructing TabWdg."""
        from pyasm.search import Search
        from pyasm.common import Environment
        options = parent['options']; view = options.get('view') or 'tab'
        raw = options.get('config_xml')
        if raw and not raw.lstrip().startswith('<config'):
            # ConfigModel retains a structured option as <config_xml>...</config_xml>.
            wrapper = parse_xml(raw)
            if wrapper.tag == 'config_xml' and len(wrapper): raw = xml_text(wrapper[0])
        if not raw and view != 'tab':
            base = Path(Environment.get_install_dir()) / 'src/tactic/ui/config'
            for include in options.get('include', '').split('|'):
                if not include: continue
                file = (base / include).resolve()
                if not file.is_relative_to(base.resolve()) or not file.is_file():
                    raise ApiError(400, 'include', 'Некорректный include tab-конфигурации')
                candidate = file.read_text(encoding='utf-8')
                if view_node(parse_xml(candidate), view) is not None: raw = candidate
            if not raw:
                search = Search('config/widget_config'); search.add_filter('category', 'TabWdg'); search.add_filter('view', view)
                obj = search.get_sobject(); raw = obj.get_value('config') if obj else None
        if not raw:
            return []
        model = ConfigModel(view, [ConfigSource(raw, view, 'TabWdg configuration')])
        result = []
        for index, el in enumerate(model.elements()):
            child = target_spec(el['handler'], el['options'], el['attributes'])
            child.update({'id': parent['id'] + '/~tab/' + str(index), 'title': el['title'],
                          'name': el['name'], 'config_view': view})
            result.append(child)
        return result
