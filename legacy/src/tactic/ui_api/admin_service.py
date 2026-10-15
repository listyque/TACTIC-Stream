"""Finite native administration commands. No arbitrary class/method execution endpoint."""
from pathlib import Path
import platform
import re
from .contracts import ApiError, json_safe, revision, text
from .version import BUILD_VERSION
from .system_diagnostics import schema_diagnostics
from tactic.core.config_model import parse_xml, xml_text

USER_FIELDS = ('first_name', 'last_name', 'display_name', 'email', 'phone_number')


class AdminService:
    def admin_operation(self, method, path, data):
        from pyasm.common import Environment, Config
        from pyasm.search import Search, SearchType
        from pyasm.security import Login
        if not Environment.get_security().is_admin():
            raise ApiError(403, 'admin_only', 'Нужны права администратора')
        opened = self.open_target(data.get('target'))
        allowed = {'/users': ('users',), '/security': ('security', 'users'),
                   '/project-create': ('project-create',), '/system': ('system',)}
        if opened['kind'] not in allowed.get(path, ()):
            raise ApiError(403, 'target_denied', 'Операция не разрешена этим настроенным экраном')
        if path == '/system' and method == 'GET':
            import cherrypy
            from pyasm.biz import Project
            from .cluster_runtime import public_status
            cluster = public_status()
            # No environment dump, filesystem paths, DSNs, secrets or licence keys.
            search = Search('sthpw/project'); count = search.get_count()
            return {'core_version': (Path(Environment.get_install_dir()) / 'VERSION').read_text().strip(),
                    'ui_version': BUILD_VERSION, 'python': platform.python_version(),
                    'platform': platform.system(), 'http_server': cherrypy.__version__,
                    'database_vendor': Config.get_value('database', 'vendor'),
                    'project': Project.get_project_code(), 'projects': count,
                    'database_checked': True, 'schema': schema_diagnostics(), 'cluster': cluster, 'allow_writes': self.allow_writes,
                    'allow_uploads': self.allow_uploads, 'admin_only': True,
                    'notes': ['Счётчик проектов получен живым запросом к БД.',
                              'Сессии общие для процессов группы.' if cluster['enabled'] else 'Однопроцессный режим; сессии хранятся в памяти.',
                              'Не является аудитом безопасности или полной диагностикой сервера.']}
        if path == '/project-create':
            return self.project_operation(method,path,data)
        if path == '/users':
            columns = self._stub().get_column_info('sthpw/login')
            permitted = [f for f in USER_FIELDS if f in columns]
            # Orders and labels come from the original user widget configuration.
            model = self._model('sthpw/login', opened['options'].get('view') or 'manage_user')
            field_names = [n for n in model.names() if n in ('login',) + USER_FIELDS]
            if 'login' not in field_names: field_names.insert(0, 'login')
            fields = [{'name': n, 'label': model.describe(n)['title']} for n in field_names]
            if method == 'GET':
                search = Search('sthpw/login'); search.add_order_by('login'); search.set_limit(2000)
                items = []
                for obj in search.get_sobjects():
                    values = {f: json_safe(obj.get_value(f, no_exception=True)) for f in ('login',) + tuple(permitted)}
                    items.append({'key': obj.get_search_key(), 'values': values, 'revision': revision(values)})
                return {'items': items, 'fields': fields, 'edit_fields': [{'name': f, 'label': model.describe(f)['title']} for f in permitted],
                        'limit': 2000, 'can_write': self.allow_writes, 'password_is_write_only': True}
            if method in ('POST', 'PATCH'):
                values = data.get('values', {})
                if not isinstance(values, dict) or any(k not in permitted for k in values):
                    raise ApiError(400, 'user_fields', 'Недопустимые поля пользователя')
                for key, value in values.items():
                    if not isinstance(value, str) or len(value) > 500 or '\x00' in value: raise ApiError(400, 'user_value', 'Некорректное значение пользователя')
                password = data.get('password')
                if password is not None and (not isinstance(password, str) or not 10 <= len(password) <= 1024):
                    raise ApiError(400, 'password', 'Новый пароль должен содержать от 10 до 1024 символов')
                if method == 'POST':
                    login = data.get('login')
                    if not isinstance(login, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.@-]{0,99}', login) or login.lower() in ('admin', 'root', 'guest'):
                        raise ApiError(400, 'login', 'Некорректный или зарезервированный логин')
                    if password is None: raise ApiError(400, 'password', 'Задайте начальный пароль')
                    def create():
                        search = Search('sthpw/login'); search.add_filter('login', login)
                        if search.get_sobject(): raise ApiError(409, 'exists', 'Пользователь уже существует')
                        obj = Login.create(login, password, first_name=values.get('first_name'), last_name=values.get('last_name'),
                                           display_name=values.get('display_name'), project_code=self._project())
                        for key, value in values.items(): obj.set_value(key, value)
                        obj.commit()
                        return {'created': True, 'key': obj.get_search_key()}
                    return self._write(create)
                def update():
                    obj = self._object('sthpw/login', data.get('key'))
                    current = {f: json_safe(obj.get_value(f, no_exception=True)) for f in ('login',) + tuple(permitted)}
                    if revision(current) != data.get('revision'): raise ApiError(409, 'conflict', 'Пользователь изменён')
                    if obj.get_value('login') == 'admin' and password is not None:
                        raise ApiError(403, 'admin_password', 'Пароль встроенного admin меняется в конфигурации сервера, не в таблице пользователей')
                    for key, value in values.items(): obj.set_value(key, value)
                    obj.commit()
                    if password is not None: obj.set_password(password)
                    return {'saved': True, 'key': obj.get_search_key()}
                return self._write(update)
        if path == '/security':
            fixed=opened.get('options',{}).get('native_fixed_group')
            if fixed and method=='POST' and not data.get('key'):
                raise ApiError(403,'group_binding','Виджет существующей группы не создаёт другую группу')
            if method == 'GET' and not data.get('key'):
                search = Search('sthpw/login_group'); search.add_order_by('login_group'); search.set_limit(1000)
                return {'items': [{'key': o.get_search_key(), 'name': o.get_value('login_group'), 'description': o.get_value('description')}
                                  for o in search.get_sobjects()], 'can_write': self.allow_writes, 'limit': 1000}
            if method == 'POST' and not data.get('key'):
                group = text(data.get('name'), 'name', 100)
                if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,99}', group) or group.lower() in ('admin', 'root', 'default'):
                    raise ApiError(400, 'group', 'Некорректное или зарезервированное имя группы')
                def create():
                    search = Search('sthpw/login_group'); search.add_filter('login_group', group)
                    if search.get_sobject(): raise ApiError(409, 'exists', 'Группа уже существует')
                    obj = SearchType.create('sthpw/login_group'); obj.set_value('login_group', group)
                    obj.set_value('access_rules', '<rules/>'); obj.commit()
                    return {'created': True, 'key': obj.get_search_key()}
                return self._write(create)
            fixed=opened.get('options',{}).get('native_fixed_group')
            if fixed and fixed!=data.get('key'):raise ApiError(403,'group_binding','Этот виджет привязан к другой группе')
            obj = self._object('sthpw/login_group', data.get('key'))
            raw = obj.get_value('access_rules') or '<rules/>'
            if method == 'GET':
                root = parse_xml(raw)
                return {'key': obj.get_search_key(), 'name': obj.get_value('login_group'), 'xml': raw,
                        'rules': [dict(n.attrib) for n in root.findall('rule')], 'revision': revision(raw),
                        'can_write': self.allow_writes and obj.get_value('login_group') != 'admin'}
            if method == 'PATCH':
                if obj.get_value('login_group') == 'admin': raise ApiError(403, 'admin_group', 'Встроенная группа admin защищена')
                raw_new = data.get('xml')
                try:
                    root = parse_xml(raw_new)
                    if root.tag != 'rules': raise ValueError('Ожидается <rules>')
                except (ValueError, TypeError) as exc: raise ApiError(400, 'rules_xml', str(exc)) from exc
                def save():
                    current = self._object('sthpw/login_group', data.get('key'))
                    if revision(current.get_value('access_rules') or '<rules/>') != data.get('revision'):
                        raise ApiError(409, 'conflict', 'Правила доступа изменились')
                    current.set_value('access_rules', raw_new); current.commit()
                    return {'saved': True, 'notice': 'Правила записаны; для существующих сессий может потребоваться повторный вход.'}
                return self._write(save)
        raise ApiError(405, 'method', 'Метод не поддерживается')
