"""Native saved-script editor, preserving ShelfEditWdg storage/save semantics.

Saved scripts use the original storage. Explicitly enabled script-run selects a
saved Python record and calls the original execute_python_script API; not a sandbox. Existing workflow/client-trigger consumers may execute saved scripts
later; editing therefore requires the ORIGINAL view_script_editor permission.
"""
import ast
from .contracts import ApiError, json_safe, revision
from tactic.core.config_model import parse_xml

STYPE = 'config/custom_script'
LANGUAGES = ('javascript', 'server_js', 'python', 'expression', 'xml')
FIELDS = ('code', 'folder', 'title', 'language', 'description', 'script', 'timestamp', 's_status')
MAX_SCRIPT_BYTES = 256 * 1024


def script_permission():
    from pyasm.common import Environment
    if not Environment.get_security().check_access('builtin', 'view_script_editor', 'allow'):
        raise ApiError(403, 'script_permission', 'Исходное право builtin/view_script_editor запрещает редактор скриптов')


def number(value, name, minimum, maximum):
    if isinstance(value, bool) or (not isinstance(value, (str, int))):
        raise ApiError(400, name, 'Некорректное целое число: ' + name)
    if isinstance(value, str) and not value.isdecimal():
        raise ApiError(400, name, 'Некорректное целое число: ' + name)
    value = int(value)
    if not minimum <= value <= maximum:
        raise ApiError(400, name, 'Число вне допустимого диапазона: ' + name)
    return value


def validate_source(value):
    if not isinstance(value, str) or '\x00' in value or len(value.encode('utf-8')) > MAX_SCRIPT_BYTES:
        raise ApiError(400, 'script_size', 'Скрипт: текст без NUL, не более 256 КиБ UTF-8')
    return value


def clean_script_values(values, current=None):
    if not isinstance(values, dict) or set(values) - {'folder', 'title', 'language', 'script', 'description'}:
        raise ApiError(400, 'script_fields', 'Разрешены folder, title, language, script, description')
    for name in ('folder', 'title', 'language', 'script'):
        if name not in values:
            raise ApiError(400, 'script_fields', 'Отсутствует поле ' + name)
    # Original save_script_cbk defaults and leading-slash rule, not a filesystem.
    folder, title, language = values['folder'] or 'default', values['title'], values['language'] or 'javascript'
    if not isinstance(title, str):
        raise ApiError(400, 'script_title', 'Нужно название скрипта')
    title = title.lstrip('/')
    for name, val in (('folder', folder), ('title', title)):
        if not isinstance(val, str) or not val.strip() or len(val) > 255 or any(ord(c)<32 for c in val):
            raise ApiError(400, 'script_'+name, 'Некорректный виртуальный путь: ' + name)
    if not isinstance(language, str) or (language not in LANGUAGES and language != (current or {}).get('language')):
        raise ApiError(400, 'script_language', 'Неизвестный язык; существующее значение можно сохранить без изменения')
    result = {'folder': folder, 'title': title, 'language': language, 'script': validate_source(values['script'])}
    if 'description' in values:
        description = values['description']
        if not isinstance(description, str) or '\x00' in description or len(description) > 10000:
            raise ApiError(400, 'script_description', 'Некорректное описание')
        result['description'] = description
    return result


def syntax_check(language, source):
    source = validate_source(source)
    if language not in ('python', 'xml'):
        return {'checked': False, 'valid': None, 'executed': False,
                'notice': 'Для этого языка синтаксическая проверка не реализована. Код не выполнялся.'}
    try:
        if language == 'python':
            ast.parse(source, filename='<TACTIC saved script>', mode='exec')
        else:
            parse_xml(source)
    except SyntaxError as exc:
        return {'checked': True, 'valid': False, 'executed': False, 'line': exc.lineno,
                'column': exc.offset, 'message': exc.msg}
    except (ValueError, RecursionError) as exc:
        return {'checked': True, 'valid': False, 'executed': False, 'message': str(exc)[:500]}
    except Exception as exc:
        # XML ParseError is not necessarily SyntaxError on every XML backend.
        import xml.etree.ElementTree as ET
        if not isinstance(exc, ET.ParseError):
            raise
        return {'checked': True, 'valid': False, 'executed': False,
                'line': exc.position[0], 'column': exc.position[1], 'message': str(exc)[:500]}
    return {'checked': True, 'valid': True, 'executed': False,
            'notice': 'Проверен только синтаксис. Имена, импорты и поведение workflow не проверялись.'}


class ScriptService:
    def _script_target(self, data):
        script_permission()
        opened = self.open_target(data.get('target'))
        if opened['kind'] != 'script-editor':
            raise ApiError(403, 'script_target', 'Редактор не определён этим widget_config')
        self.require_type(STYPE)
        return opened

    def _script_row(self, obj, include_source=True):
        fields = FIELDS if include_source else tuple(f for f in FIELDS if f != 'script')
        values = {name: json_safe(obj.get_value(name, no_exception=True)) for name in fields}
        result = {'key': obj.get_search_key(), 'values': values}
        if include_source:
            source = values.get('script')
            if source is not None and (not isinstance(source, str) or len(source.encode('utf-8')) > MAX_SCRIPT_BYTES):
                raise ApiError(413, 'script_size', 'Этот существующий скрипт превышает предел редактора 256 КиБ; данные не изменены')
            result['revision'] = revision(obj.get_sobject_dict())
        return result

    def script_operation(self, method, path, data):
        from pyasm.search import Search
        target = self._script_target(data)
        if path == '/script-check' and method == 'POST':
            return syntax_check(data.get('language'), data.get('script'))
        if path == '/script-diff' and method == 'POST':
            import difflib
            obj=self._object(STYPE,data.get('key'));record=self._script_row(obj)
            if record['revision']!=data.get('revision'):raise ApiError(409,'conflict','Скрипт уже изменён; сохраните черновик отдельно')
            source=validate_source(data.get('script'))
            diff=''.join(difflib.unified_diff((record['values']['script'] or '').splitlines(True),source.splitlines(True),fromfile='saved',tofile='draft'))
            return {'diff':diff[:512*1024],'truncated':len(diff)>512*1024,'executed':False}
        if path == '/script-run' and method == 'POST':
            import json
            if not getattr(self,'allow_script_execution',False):raise ApiError(403,'script_execution_disabled','Запуск сохранённого Python выключен: нужен отдельный allow_script_execution')
            if set(data)-{'project','target','key','revision','confirm','parameters'}:raise ApiError(400,'script_run_input','Только ключ сохранённого скрипта и input-параметры')
            if data.get('confirm')!='RUN_SAVED_SCRIPT':raise ApiError(400,'confirmation','Требуется RUN_SAVED_SCRIPT')
            params=data.get('parameters',{})
            if not isinstance(params,dict) or len(json.dumps(params,ensure_ascii=False,allow_nan=False).encode('utf-8'))>32768:raise ApiError(400,'parameters','input — JSON-объект до 32 КиБ')
            def run_saved():
                obj=self._object(STYPE,data.get('key'));record=self._script_row(obj)
                if record['revision']!=data.get('revision'):raise ApiError(409,'conflict','Сохранённый скрипт изменён')
                val=record['values']
                if val.get('language')!='python' or val.get('s_status')=='retired':raise ApiError(400,'script_language','Выполняется только активный сохранённый Python-скрипт')
                path_value=(val['folder']+'/' if val['folder'] else '')+val['title']
                if not val['folder'] or any(x in val['title'] for x in ('/','\\')):raise ApiError(400,'script_path','Требуется однозначная папка и имя сохранённого скрипта')
                s=Search(STYPE);s.add_filter('folder',val['folder']);s.add_filter('title',val['title'])
                if s.get_count()!=1:raise ApiError(409,'script_duplicate','Неоднозначный script_path')
                from .action_log import command_started
                from tactic.command import PythonCmd
                command_started(PythonCmd(script_path=path_value))
                result=self._stub().execute_python_script(path_value,{'input':params})
                try:
                    safe=json_safe(result)
                    if len(json.dumps(safe,ensure_ascii=False).encode('utf-8'))>256*1024:safe={'notice':'Результат превышает 256 КиБ; код выполнен, повтор не требуется'}
                except Exception:safe={'notice':'Код выполнен; возвращённый объект не сериализуется в JSON'}
                return {'executed':True,'result':safe,'revision':record['revision'],'notice':'Выполнен сохранённый PythonCmd. Внешние эффекты не отменяются кнопкой Undo.'}
            return self._write(run_saved)
        if path == '/scripts' and method == 'GET':
            limit = number(data.get('limit', 40), 'limit', 1, 100)
            offset = number(data.get('offset', 0), 'offset', 0, 1000000)
            query = data.get('q', '')
            if not isinstance(query, str) or '\x00' in query or len(query) > 200:
                raise ApiError(400, 'script_search', 'Поиск до 200 символов')
            search = Search(STYPE)
            # Explicit literal SQL LIKE; do not use vendor-dependent regex EQI.
            if query:
                from pyasm.search import Sql
                escaped = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
                # A quote-safe value and fixed column names, never client SQL.
                search.add_where('("title" LIKE %s ESCAPE %s OR "folder" LIKE %s ESCAPE %s)' %
                                 (Sql.quote('%'+escaped+'%'), Sql.quote('\\'), Sql.quote('%'+escaped+'%'), Sql.quote('\\')))
            folder = data.get('folder')
            if folder is not None:
                if not isinstance(folder, str) or len(folder) > 255: raise ApiError(400,'script_folder','Некорректная папка')
                search.add_filter('folder', folder)
            total = search.get_count()
            search.add_order_by('folder'); search.add_order_by('title'); search.add_order_by('id')
            search.set_limit(limit); search.set_offset(offset)
            # Do not fetch every script body just to display the directory.
            for name in FIELDS:
                if name != 'script': search.add_column(name)
            items = [self._script_row(obj, False) for obj in search.get_sobjects()]
            return {'items': items, 'total': total, 'offset': offset, 'limit': limit,
                    'has_more': offset+len(items)<total, 'languages': list(LANGUAGES),
                    'can_write': self.allow_writes, 'can_execute': bool(getattr(self,'allow_script_execution',False)),
                    'initial': {k: target.get('options', {}).get(k) for k in ('script_path', 'search_key')},
                    'manage_target': target['id']+'/~scripts-table', 'storage': STYPE}
        if path == '/script' and method == 'GET':
            key = data.get('key')
            if key:
                obj = self._object(STYPE, key)
            else:
                # Original script_path uses dirname + basename; it is a DB key,
                # never a local path read. Keep '/' as the stored separator.
                path_value = data.get('script_path')
                if not isinstance(path_value, str) or not path_value or len(path_value)>511:
                    raise ApiError(400,'script_path','Нужен key или script_path')
                folder, _, title = path_value.rpartition('/')
                search=Search(STYPE);search.add_filter('folder',folder);search.add_filter('title',title)
                search.set_limit(2);rows=search.get_sobjects()
                if len(rows)>1:raise ApiError(409,'script_duplicate','Несколько скриптов с этим путём; выберите запись по ключу')
                if not rows:raise ApiError(404,'not_found','Скрипт не найден')
                obj=rows[0]
            return {'record':self._script_row(obj), 'can_write':self.allow_writes, 'can_execute':bool(getattr(self,'allow_script_execution',False))}
        if path == '/script' and method in ('POST', 'PATCH'):
            def save():
                obj = self._object(STYPE, data.get('key')) if method == 'PATCH' else None
                current = self._script_row(obj) if obj else None
                if current and current['revision'] != data.get('revision'):
                    raise ApiError(409,'conflict','Скрипт изменён после открытия. Сохраните свой текст отдельно и перечитайте запись.')
                if obj and obj.get_value('s_status',no_exception=True)=='retired':
                    raise ApiError(409,'script_retired','Скрипт архивирован; сначала разберите его состояние')
                values = clean_script_values(data.get('values'), current['values'] if current else None)
                matches=Search(STYPE);matches.add_filter('folder',values['folder']);matches.add_filter('title',values['title'])
                matches.set_limit(3);duplicates=matches.get_sobjects()
                if any(not obj or str(item.get_id())!=str(obj.get_id()) for item in duplicates):
                    raise ApiError(409,'script_duplicate','Такой folder/title уже существует. Используйте другое название или откройте существующую запись.')
                # Same persistence boundary as original shelf_wdg.save_script_cbk.
                stub=self._stub()
                result=stub.update(obj.get_search_key(),values) if obj else stub.insert(STYPE,values)
                key=result.get('__search_key__') if isinstance(result,dict) else None
                if not key and obj:key=obj.get_search_key()
                if not key:
                    raise RuntimeError('Original script API did not return __search_key__')
                return {'saved':True,'record':self._script_row(self._object(STYPE,key)),
                        'executed':False,'notice':'Сохранено в config/custom_script. Существующие триггеры и workflow могут использовать этот код.'}
            return self._write(save)
        raise ApiError(405,'method','Операция редактора не поддерживается')
