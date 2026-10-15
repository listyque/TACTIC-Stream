"""Finite ProjectCreateWdg workflow. No arbitrary template/file/class input."""
import re
from urllib.parse import quote
from .contracts import ApiError, text, revision

RESERVED = {'admin', 'sthpw', 'default', 'unittest', 'template', 'public'}


def project_fields(data):
    allowed = {'project','target','code','title','type','description','revision'}
    if set(data) - allowed:
        raise ApiError(400, 'project_fields', 'Неизвестные параметры создания проекта')
    code = data.get('code')
    if not isinstance(code, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,29}', code) or code in RESERVED:
        raise ApiError(400, 'project_code', 'Код: 1–30 строчных латинских букв, цифр или _, первый символ — буква; системные имена запрещены')
    title = text(data.get('title'), 'title', 200)
    typ = text(data.get('type') or 'default', 'type', 100)
    description = data.get('description', '')
    if not isinstance(description, str) or len(description) > 10000 or '\0' in description:
        raise ApiError(400, 'description', 'Некорректное описание')
    return {'code': code, 'title': title, 'type': typ, 'description': description}


class ProjectService:
    def _project_creation_types(self):
        # Restrict to stock schemas whose original migrations are supported. A
        # registered project template is NOT interchangeable with a project type.
        items = [{'code':'default','title':'Пустой проект','description':'Штатная конфигурационная база, собственные SearchType добавляются после создания.'},
                 {'code':'simple','title':'Базовый проект (simple)','description':'Штатный тип simple и конфигурация TACTIC; свои сущности создаются в проекте.'}]
        return items

    def _project_preflight(self, data):
        from pyasm.biz import Project
        from pyasm.search import Search
        from pyasm.common import Environment, Config
        if not Environment.get_security().is_admin():
            raise ApiError(403, 'admin_only', 'Нужны права администратора')
        target = self.open_target(data.get('target'))
        if target.get('kind') != 'project-create':
            raise ApiError(403, 'target_denied', 'Нужен настроенный ProjectCreateWdg')
        fields = project_fields(data)
        if fields['type'] not in {t['code'] for t in self._project_creation_types()}:
            raise ApiError(400, 'project_type', 'Этот тип/шаблон пока не поддержан мастером; существующая база не копируется')
        search = Search('sthpw/project'); search.set_show_retired(True); search.add_filter('code', fields['code'])
        if search.get_sobject():
            raise ApiError(409, 'project_exists', 'Проект с этим кодом уже зарегистрирован (возможно, архивный или создан частично). Повторное создание запрещено.')
        impl = Project.get_database_impl()
        if impl.database_exists(fields['code']):
            raise ApiError(409, 'database_exists', 'База с этим именем уже существует. Она не будет перезаписана или подключена автоматически.')
        vendor = Config.get_value('database', 'vendor')
        return fields, revision({'fields':fields, 'target':target.get('options',{}), 'vendor':vendor})

    def project_operation(self, method, path, data):
        from pyasm.common import Environment
        from pyasm.biz import Project
        if not Environment.get_security().is_admin():
            raise ApiError(403,'admin_only','Нужны права администратора')
        opened = self.open_target(data.get('target'))
        if opened.get('kind') != 'project-create':
            raise ApiError(403,'target_denied','Операция не разрешена этим виджетом')
        if method == 'GET' and path == '/project-create':
            return {'types':self._project_creation_types(), 'can_write':self.allow_writes,
                    'steps':['Данные проекта','Исходная схема','Проверка','Готово'],
                    'unsupported':['Импорт зарегистрированного шаблона, preview и установка темы ещё не перенесены.'],
                    'storage':'sthpw/project + original project database + config/widget_config'}
        if method != 'POST':
            raise ApiError(405,'method','Метод не поддерживается')
        fields, token = self._project_preflight(data)
        if path == '/project-preflight':
            return {'ready':True,'revision':token,'summary':fields,
                    'notice':'Будут созданы настоящая база и проект TACTIC. DDL/файлы нельзя считать полностью обратимыми транзакцией.'}
        if path != '/project-create':
            raise ApiError(404,'route','Неизвестная операция')
        if data.get('revision') and token != data['revision']:
            raise ApiError(409,'project_changed','Параметры изменились после проверки; проверьте снова')
        def create():
            from tactic.core.project_creation import NativeCreateProjectCmd
            old = self._project()
            try:
                cmd = NativeCreateProjectCmd(project_code=fields['code'], project_title=fields['title'],
                       project_type=fields['type'], description=fields['description'], use_default_side_bar=True)
                cmd.check(); cmd.execute()
                # Set context for the final read, not just a success string.
                Project.set_project(fields['code'])
                from pyasm.search import Search
                s = Search('config/widget_config'); s.add_filter('view','project_view')
                if not s.get_sobject():
                    raise RuntimeError('Original sidebar was not initialized')
                from pyasm.security import Site
                site = Site.get_site() or ''
                return {'created':True, 'code':fields['code'], 'title':fields['title'],
                        'project_url':'/tactic/'+(quote(site,safe='')+'/' if site else '')+quote(fields['code'],safe='')+'/',
                        'notice':'Проект, конфигурационная база и исходный sidebar созданы. Откройте проект.',
                        'schema_checked':bool(cmd.info.get('native_schema_checked'))}
            except ApiError:
                raise
            except Exception as exc:
                # Original CreateProjectCmd commits before Upgrade; do not falsely
                # promise rollback or automatically re-run a failed creation.
                raise ApiError(500,'project_creation_incomplete',
                    'Создание не завершено. Часть проекта могла сохраниться. Не повторяйте создание с тем же кодом; проверьте Projects и журнал сервера.',
                    {'project_code':fields['code'],'automatic_retry':False}) from exc
            finally:
                Project.clear_cache(); Project.set_project(old)
                self._stub().set_project(old)
        return self._write(create)
