"""Typed native actions for original SmartMenu activation scopes.

Only action IDs cross the browser boundary. Source callback strings are never
executed. Unsupported legacy actions stay identifiable, not mapped to another
operation. Menus are UI affordances, NEVER authorization for a write endpoint.
"""

def action(id, label, legacy='', enabled=True, reason='', children=None):
    result = dict(id=id, type='action', label=label, legacy_label=legacy,
                  enabled=bool(enabled), reason=reason)
    if children is not None:
        result['children'] = children
    return result


def pending(id, label, legacy, reason):
    return action(id, label, legacy, False, reason)


def separator():
    return {'type':'separator'}


def menu_items(scope, context):
    c = context
    if scope == 'row':
        result = [action('inspect','Открыть запись / файлы / связи'),
            action('edit','Редактировать','Edit',c.get('can_edit'), 'Редактирование отключено или edit_class не перенесён'),
            action('files','Check-in / файлы','Check in New File',c.get('can_upload'), 'Загрузка отключена'),
            pending('preview','Изменить preview','Change Preview Image','Специальная icon check-in ветка ещё не перенесена')]
        if c.get('can_retire'):
            result += [separator(),action('state', 'Восстановить…' if c.get('retired') else 'Архивировать…',
                'Reactivate' if c.get('retired') else 'Retire')]
        if c.get('can_delete'):
            result += [pending('delete','Удалить…','Delete','Каскадное удаление и DeleteWdg требуют отдельного переноса')]
        if c.get('subscribable'):
            result += [separator(), action('history','История изменений','Item Audit Log'),
                       action('subscription','Подписка / отписка','Subscribe / Unsubscribe')]
        result += [separator(),action('save_cell','Сохранить изменения ячейки','Save All Changes',c.get('pending_cell'),
            'Нет несохранённой inline-ячейки; пакетный legacy pending-buffer не переносился')]
        return result
    if scope == 'column':
        return [action('sort_asc','По возрастанию','Order By (Ascending)',c.get('sortable')),
            action('sort_desc','По убыванию','Order By (Descending)',c.get('sortable')),separator(),
            pending('legacy_group','Группировать все результаты','Group By','Серверная группировка legacy ещё не перенесена'),
            action('group_page','Группировать текущую страницу','',c.get('storage')),
            action('ungroup','Убрать группировку','Remove Grouping'),separator(),
            action('definition','Определение колонки','Edit Column Definition',c.get('admin')),
            action('columns','Колонки представления','Column Manager',c.get('column_manager')),
            action('hide_column','Скрыть колонку в этой таблице','Remove Column',c.get('column_manager')),
            action('restore_columns','Показать настроенные колонки','',c.get('column_manager')),separator(),
            action('audit','Источник widget_config'),
            pending('new_column','Создать новую колонку','Create New Column','DDL-редактор колонки не переносился в это меню')]
    if scope == 'sidebar':
        return [action('open','Открыть в основной вкладке','Open Link In New Tab'),
            action('popup','Открыть в отдельной панели','Open Link In New Window'),separator(),
            action('sidebar_config','Редактировать sidebar','Edit Side Bar',c.get('admin')),
            pending('remove_link','Удалить ссылку','Remove Link','Удаление через исходный update_config ещё не подключено; доступен редактор XML'),
            action('definition','Определение ссылки',enabled=c.get('admin'))]
    if scope == 'tab':
        result = [action('refresh','Обновить вкладку','Refresh'),
                  action('rename','Переименовать вкладку','Rename Tab'),
                  action('open_main','Открыть в основной вкладке','Copy To Main Tab'),
                  pending('tear_off','Отделить вкладку','Tear Off','Перенос живого DOM/состояния между контейнерами ещё не перенесён')]
        if c.get('removable'):
            result += [separator(),action('close','Закрыть вкладку','Close Tab'),
                       action('close_others','Закрыть остальные','Close All Except This Tab')]
        result += [separator(),action('definition','Определение виджета','View Definition',c.get('admin'))]
        return result
    if scope == 'form-field':
        return [action('definition','Определение поля','Edit Column Definition',c.get('admin')),
                action('reset_field','Вернуть исходное значение',enabled=c.get('editable')),
                action('null_field','Установить NULL',enabled=c.get('nullable') and c.get('editable'))]
    if scope == 'widget':
        return [action('refresh','Обновить виджет'),action('definition','Определение виджета',enabled=c.get('admin'))]
    raise ValueError('Неизвестная область контекстного меню')
