# Карта источников и изменений · 1.0

Основа: полный архив 0.9, не несобранная 0.10. Это выборочная семантическая карта реализованных изменений; полная статическая инвентаризация находится в inventory/. Пункт «рассмотрен» не означает полного parity.

| Источник legacy | Реализация/изменение | Проверка и незакрытое |
|---|---|---|
| tactic/ui/container/tab_wdg.py:get_display | core/widget_containers.py:tab_model/tab_items, ui_api/widget_service.py, ConfiguredTabs/WidgetHost | Inline/saved/include/category, hidden indices, selected/load, server state. Native write TabSaveStateCmd не вызывается: именованный view не заменяется tab |
| tactic/ui/container/tab_wdg.py:add_context_menu | core/context_menus.py scope=tab, ConfiguredTabs.vue | Local close/rename/reorder, main tab, refresh; tear-off явно pending |
| tactic/ui/panel/edit_wdg.py:init/get_config | edit_base_model/resolve_edit, bind_form_target/embedded_form, ConfiguredForm/EmbeddedForm | Настоящее legacy get_config тело сравнивается при injected DB context; read/create/edit binding; parent/connect/custom callbacks/layout_view заблокированы |
| tactic/ui/panel/edit_wdg.py:get_header_context_menu | scope=form-field, WidgetDefinition.vue | Реальный edit field spec; local reset/null, metadata; не универсальный callback renderer |
| tactic/ui/panel/base_table_layout_wdg.py:get_smart_header_context_menu_data | scope=column, ConfiguredTable.vue | Сортировка/config designer/local hide; grouping страницы явно отличается от legacy server Group By |
| tactic/ui/panel/base_table_layout_wdg.py:get_data_row_smart_context_menu_details | scope=row, ConfiguredTable/RecordInspector | Selection-aware edit/bulk, history/state/files/subscription; cascade delete/icon preview не подменены |
| tactic/ui/panel/panel_wdg.py:add_link_context_menu | scope=sidebar, SidebarNode/App | Main tab/independent panel, sidebar XML editor, definition; removal через update_config ещё pending |
| Исходные get_handler/default resolution | config_backend._edit_base_model/_view_model; config_model target kind | Табличные поля не подменяют edit view; config_xml передаётся прежней NativeEditCmd |

## Подключение к серверу

`api.py` маршрутизирует `/embedded-form` и `/context-menu` к ConfigBackend/ExtendedBackend в существующем процессе. Generic record/form/query paths повторяют binding для прямой формы. Menu GET не является выдачей write capability; реальные endpoints проверяют права/ревизии независимо.

`WidgetService`, `MenuService` — новые mixins, не отдельные сервера и не новые таблицы. Existing Command/transaction/model paths сохранены. Sidebar resolver и source XML не заменены статическими JavaScript-массивами.

## Frontend

Новые ContextMenu, WidgetDefinition, EmbeddedForm, ConfiguredTabs, WidgetTable, WidgetHost. Последний — рекурсивный диспетчер разрешённых типов; глобальная регистрация компонентов нужна для взаимной вложенности Tabs/Host, шаблоны предкомпилированы.

Существующие ConfiguredForm/Table/App/SidebarNode и Inspector подключены к общим scope-меню. FieldInput исправляет показ date/datetime без преобразования сырого значения до редактирования. MessageCenter учитывает active для скрытого контейнера. В мобильной навигации закрывается sidebar также при открытии уже существующей основной вкладки.

## Tests и их изменения

`test_widgets_10.py`, `run_http_10.py`, `run_browser_10.py` — новые regression suites. `fixture_10.py` только test backend; production никогда не импортирует fixture. `serve_fixture.py` выбирает его для ВСЕХ старых и новых наборов, каждый получает отдельный чистый процесс.

В прежних browser тестах locator действия Inspect изменён с role=button на role=menuitem: доступная семантика меню стала явной. Hardcoded #form-title заменён на prefix matcher, поскольку у встроенных и модальных форм теперь уникальные heading IDs. Сами проверяемые пользовательские операции сохранены. Тестовый collaborator task form получил новый _edit_base_model hook; разрешение оригинального edit порядка дополнительно проверяется отдельными differential-тестами.

`run_validation_10.py` повторяет build, XML-parity, все unit и прежние HTTP/browser наборы, затем новые. Финальным считается только validation/verified/summary.json. Промежуточные ошибки хранятся отдельно и не складываются в число пройденных тестов.

## Не изменено в этой итерации

BAT/launcher/migrations/runtime-manifest, kernel VERSION, original seed DB bytes, правила лицензирования и логин. Не снимались admin-only/allow_writes=false/allow_uploads=false. Не вводился auto-upgrade или новый DDL.
