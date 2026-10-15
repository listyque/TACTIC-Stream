# Карта изменений 0.16

## Исходная семантика

`src/config2/search_type/widget/sthpw/pipeline-conf.xml`, definition/editor: ButtonElementWdg → spt.tab.add_new → PipelineToolWdg(search_key). `src/config2/search_type/widget/sthpw/schema-conf.xml`, definition/create: ButtonElementWdg → spt.tab.add_new → SchemaToolWdg({}). XML-файлы не изменены. В manage view таблицы должны оставаться таблицами.

## Изменённые механизмы

| Код | Изменение |
|---|---|
| tactic/core/config_model.py | Явные stock short/module aliases уже поддержанных уникальных виджетов; без выбора по случайному basename. |
| ui_api/global_admin_service.py | Строгое сопоставление двух оригинальных callbacks, ограниченные derived targets, выбранный pipeline, current-project schema, open_mode=tab. |
| ui_api/graph_service.py | search_key как initial selection; проверка области доступа; прежние команды через diagnostic execute_traced. |
| ConfiguredTable.vue | stock open_mode=tab → основная вкладка; остальные popup/HiddenRow не меняют места. |
| App.vue / WidgetHost.vue | Refresh key действительно обновляет граф; исходный target сохраняется. |
| ui_api/action_log.py | Безопасная краткая серверная трасса + явные клиентские события, per-worker rotating log, cluster tailer. |
| ui_api/api.py | RequestTrace, реальный authenticated actor, ID/результат/длительность, ограниченный CSRF-защищённый /client-events. |
| ui_api/extended_backend.py | Диагностика уже разрешённого target/handler/kind; не разрешение произвольного метода. |
| ui_api/config_backend.py / table_edit_service.py | Наблюдение прямых original command.execute без подмены результата/транзакции. |
| pyasm/command/command.py | Вызов уже загруженного диагностического модуля через sys.modules после исходной проверки, без обязательного native-импорта legacy. |
| ui_api/tactic_backend.py | Пропуск пустого Site.set_site в обычной single-site среде. |
| ui_api/mount.py | Подключение лога, устранение дублирующих native access lines, без отключения legacy/error logging. |
| tools/local/cluster.py | Общий терминал получает только safe JSONL workers, не их сырой stdout. |
| frontend/src/api.js | Ограниченный producer явных действий, correlation hint, без input/clipboard/body logging и retry. |
| App/ContextMenu/ConfiguredTabs/Form/Table/GraphEditor | Явные события на пользовательских действиях. Не универсальный DOM-event recorder. |

## Регрессии и неопределённость

0.15 уже содержала GraphEditor; отсутствие класса не было причиной. Воспроизведены отсутствие штатных cell buttons, игнорирование row-selected initial key и неправильное popup-размещение нового адаптера. Основные stock ссылки отдельно проверены; пользовательские переопределения из рабочей БД не предоставлены и не объявляются все исправленными.

Первый сквозной прогон остановился на действительном лимите входов; добавлен интервал только в тестовый runner, security limiter не изменён. Второй выявил popup вместо исходной spt.tab.add_new; исправлено размещение и добавлены JS/HTTP/browser регрессии. Итоговые показатели берутся только из завершённого последнего прогона.
