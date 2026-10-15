"""Read-only projection of real TACTIC database metadata for SystemInfoWdg.

No configurable SQL, paths, DSNs, licence strings or upgrade execution route.
"""
import logging
import re
from tactic.core.schema_health import inspect_schema,CONFIG_REQUIRED
LOG=logging.getLogger('tactic.native.schema')

def schema_diagnostics():
    from pyasm.search import Search,DbContainer
    from pyasm.biz import Project
    try:
        search=Search('sthpw/search_object')
        search.add_filters('search_type',list(CONFIG_REQUIRED))
        registry={o.get_value('search_type'):o.get_value('table_name') for o in search.get_sobjects()}
        projects=[Project.get_by_code('sthpw')]
        current=Project.get()
        if current and current.get_code() not in ('admin','sthpw'):
            projects.append(current)
        if not projects[0]:raise RuntimeError('No primary project registration')
    except Exception as exc:
        LOG.error('Native schema metadata unavailable: %s',type(exc).__name__)
        return {'read_only':True,'ready':False,'databases':[],
                'error':'metadata_unavailable','notice':'Не удалось прочитать регистрации схемы. Используйте MANAGE_TACTIC.bat check db для управляемой локальной SQLite.'}
    results=[]
    for project in projects:
        code=project.get_code()
        try:
            db=DbContainer.get(project.get_project_db_resource())
            def columns_for(table):
                if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,127}',table):
                    raise ValueError('Custom qualified table requires manual diagnostic')
                return db.get_columns(table,use_cache=False)
            report=inspect_schema(columns_for,registry,include_core=code=='sthpw')
            report.update(project=code,vendor=db.get_database_type())
        except Exception as exc:
            LOG.error('Native schema metadata query failed: %s',type(exc).__name__)
            report={'project':code,'ready':False,'checks':[],'error':'metadata_query_failed',
                    'notice':'Чтение метаданных не выполнено. Пароли, пути и текст SQL в этот ответ не включаются.'}
        results.append(report)
    return {'read_only':True,'ready':all(x['ready'] for x in results),'databases':results,
            'notice':'Проверены обязательные таблицы и поля перенесённого UI. Это не проверка всех данных, авторизации, триггеров или файлов.',
            'upgrade_notice':'Обновление БД из браузера не выполняется. Остановите сервер; для управляемой локальной SQLite используйте MANAGE_TACTIC.bat check db → MANAGE_TACTIC.bat db upgrade.'}
