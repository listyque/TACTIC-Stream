# Интерфейс TACTIC Stream: конфиги и совместимость

Требования пользователя, зафиксированные с 2026-10-06. Готовность конкретных
частей отмечена отдельно; описание цели само по себе не означает её реализацию.

<a id="legacy-plan"></a>
## Действующий план завершения нужного legacy — обновлён 2026-10-22

Единственная актуальная очередь до самого конца: **три этапа**. Разделы с более
ранними датами ниже — история и технические требования, а не дополнительные очереди.
Прежний этап «Базовые UI и адаптеры» закрыт как контрольная точка; его остатки
(L02/L03/L05/L07a) входят в пункты этапа 1. Прежние этапы 2/3/4 стали 1/2/3,
пункты 2.x → 1.x, 3.x → 2.x, 4 → 3. **Этап 1 (B07) и пункт 2.1 (L10) закрыты.**

### Где остановились

Контрольная точка **Stream 0.112.184 / Handler 0.6.0.131** (2026-10-22):
закрыты пункты 1.0–1.3 (L01, L04 и весь блок L03).

- Уже подключены базовые табличные адаптеры, inline-теги, заметки/сообщения/задачи,
  служебные ячейки, статусы/назначения, вложенные таблицы, связи, summaries,
  DependencyLink и ParentGroup. Их используемые опции и права ещё требуют общей приёмки.
- Закрыт файловый блок 1.2: checkout последовательностей и UDIM по `file_range` и
  `metadata` через существующие владельцы передачи (`SnapshotCheckoutController` / `SnapshotCheckout.vue`),
  настроенные поля публикации (`ThumbInputWdg`, `UploadWdg` с `names` и `MultiUploadAction`, `SimpleUploadWdg`),
  а также `folder_drop` / `FileIngestCmd` на `DropElementWdg` с явной кнопкой выбора файлов и drop.
- Закрыт блок 1.3 (остаток L03): сохранённые layouts (`CustomLayoutElementWdg`, включая вложенную обёртку `columns.thumb_view` → `custom_col` с `icon_size`, а также `HiddenRowElementWdg` → `CustomLayoutElementWdg` `episodes/columns/script` с `show_resize_scroll`), callbacks и script actions (`ButtonElementWdg` с пустым `language` → `'javascript'`, контекст `targetSearchKey` и выбранных записей в `ConfiguredView.vue`), сохранение комментариев и проверка конфликта ревизий при сохранении XML в `ColumnsEditorController`, и сверка ссылок без найденного определения (`asset_panel_wdg`, `cost_breakdown` / `asset_cost_breakdown`, `task_edit` / `inline_add_item`, `custom_col` без `<display>`).
- Срез **239 XML/CG-записей**: 71 упомянутый класс с адаптером, 0 без адаптера,
  30 исключённых production-зависимостей, 3 явно недописанных. Полный переносимый
  каталог — 74 класса / 180 aliases. **Наличие адаптера не означает готовность всех опций.**
- Полный Frame gate (156 стадий `check_platform.py`) проходит на текущих исходниках;
  парный отчёт `tools/frame_table` свежий (1248 состояний). Остальные парные отчёты
  `tools/frame_*` устарели по отпечаткам `shared_ui/core` и обновляются в пункте 1.5.

### Три этапа и их статус

| Этап | Статус | Что осталось |
| --- | --- | --- |
| 1. Сложные таблицы и закрытие B07 | **Текущий** | 1.0–1.3 закрыты; выполнить 1.4 → 1.5. |
| 2. Ядро, интеграции и БД | После этапа 1 | 2.1 L10 → 2.2 L09 → 2.3 L08 → 2.4 L11. |
| 3. Поставка и переход с legacy | Завершающий | L12: независимые комплекты, чистая установка, upgrade, перенос, backup/restore. |

### Этап 1: сложные таблицы и закрытие B07

#### 1.0. Принять последнюю контрольную точку — закрыт

- [x] Полный `check_platform.py --handler-root "d:/grav/Tactic Stream/TH"` на зафиксированных
  исходниках; подтверждённые регрессии исправлены.
- [x] Отпечатки парного отчёта таблиц актуальны.

#### 1.1. Остаток связей и вложенных таблиц — L01 — закрыт

- [x] Используемые query/selection/group scopes, фильтры, загрузка и сохранение
  состояния вложенных таблиц; удерживаемые строки вне текущей страницы.
- [x] Настоящие browser drop-события ParentGroup и instance links,
  альтернатива без drag, задержанные ответы, смена вкладки/проекта и закрытие.
- [x] Создание дочерних записей из нужного вложенного scope;
  недостающие опции редактора и итоги закрываются в 1.5.

#### 1.2. Файлы, последовательности и ingest — L04 + файловый остаток L03 — закрыт

- [x] Добавить checkout последовательностей и UDIM по исходным ranges/metadata,
  используя существующие владельцы передачи; проверить большие группы, отмену,
  частичный сбой и замену локальных файлов.
- [x] Довести используемые опции append/checkout/publish и требуемые настроенные
  поля публикации; сохранить naming, конкретную версию, проект, повтор и FileUndo.
- [x] Перенести рабочий `folder_drop` / FileIngest callback с явной кнопкой выбора
  файлов, исходными параметрами и тем же результатом без legacy DOM.

**Готово, когда:** проверены реальные файлы и байты, версии, ошибка/повтор и откат
в обоих применимых клиентах. Локальные/DCC-возможности остаются возможностями ТХ.

#### 1.3. Сохранённые layouts и настраиваемые действия — остаток L03 — закрыт

- [x] Довести подтверждённые сохранённые layouts, callbacks и script actions
  с правильным контекстом строки/выделения и понятными ошибками.
- [x] Сверить ссылки без найденного определения с доступными исходниками/конфигами;
  неизвестное определение сохранить как нерешённый случай, не придумывать и не удалять.
- [x] Проверить сохранение исходных options и revisions через существующий редактор.

**Готово, когда:** у каждого используемого сценария есть определение, рабочий пример
и проверка действия. **Старый Custom Layout Editor не переносим.** Сохранённые полезные
CustomLayouts остаются; произвольный HTML/DOM/Mako не становится языком Frame и не запускается в QML.

#### 1.4. Gantt и учёт времени внутри таблицы — L06 — закрыт

- [x] Довести пять адаптеров: GanttWdg, GanttElementWdg, TimecardInfoTableElement,
  WeekTableElement, WorkHoursElementWdg.
- [x] Реализовать используемые операции из ячейки: даты, длительность, часы,
  перенос/каскад, сохранение/отмена, неделя и пересчёт итогов.

**Готово, когда:** действуют исходные параметры и записываются правильные данные.
Готовые Task Manager/Gantt/Timesheet переиспользуются; Calendar остаётся отдельным доком.

#### 1.5. Полная приёмка таблицы и редактора — L07b и остатки базовых UI — закрыт

- [x] Пройти реально используемые options всего каталога, включая старые адаптеры
  заметок/сообщений/задач, статусов и служебных ячеек. Неподдержанные опции не игнорировать.
- [x] Довести inline/forms, редактор колонок во вложенном scope, grouping и
  `bottom` / `group_bottom` / `total_summary`.
- [x] Проверить обычного пользователя и admin: права на объекты/поля/действия,
  приватность, межпроектные операции, физическую идентичность и ревизии форм/конфигов.
- [x] Проверить конфликт, удалённую/retired запись, неизвестный результат сохранения,
  повтор, rollback и сохранность черновика.
- [x] Обновить EN/RU примеры, снимки и все устаревшие парные отчёты `tools/frame_*`;
  пройти общий gate и связанные пользовательские сценарии на финальных исходниках.

**Готово, когда:** подтверждённые используемые сценарии B07 приняты целиком,
а оставшиеся ограничения перечислены по конкретным конфигам/вызовам. Только тогда закрываем этап 1 (`B07` закрыт).

### Этап 2: ядро, интеграции и БД

| Пункт | Блок | Остаток и условие готовности |
| --- | --- | --- |
| 2.1 | L10 — проекты, plugins, schema/import/export — **закрыт** | Сверены и проверены CreateProjectCmd, ProjectTemplateInstallerCmd (включая живое клонирование is_template=True и полный откат БД/файлов), ProjectTemplateCreatorCmd, ProjectTemplate*Cmd, PluginInstaller / PluginCreator / PluginUninstaller / PluginReloader, ProjectArchiveAction, а также паритет серверных schema_cmd / schema_delete_cmd / workflow_cmd / search_types_cmd с ТХ schema_api / schema_delete_api / workflow_api / search_types_api на SQLite и PostgreSQL 18.6. |
| 2.2 | L09 — Workflow, Triggers, уведомления | Проверить исполнение нужных узлов/handlers/событий, sync/async, расписания, recipients/privacy и доставку без дублирования. Редактор графа не доказывает выполнение. |
| 2.3 | L08 — API, native Python, TEL/Naming | По подтверждённым callers закрыть оставшиеся контракты, контекст, параметры, ошибки и эффекты; классифицировать UnsupportedContract, не снимать защитные guards. |
| 2.4 | L11 — SQLite/PostgreSQL | Пройти одинаковые сценарии на двух реальных СУБД (Docker PostgreSQL 18.6 и локальный SQLite): DDL, даты/JSON, конкуренция, транзакции, rollback и восстановление. MySQL отложен. |

### Этап 3: поставка и переход с legacy

| Пункт | Блок | Остаток и условие готовности |
| --- | --- | --- |
| 3 | L12 — независимая поставка и переход | Чистые Windows и серверное окружение: установка/upgrade, штатный запуск, перенос согласованных проектов, резервная копия и восстановление БД/repository/config на копиях. Проверить браузер, настоящий ТХ и frozen EXE. |

Зависимость ядра, необходимую текущему сценарию, делаем в его пункте; остальное
не расширяет его объём. ТХ и ТС сохраняют независимые репозитории и поставки.

### Как выполняем пункты

- Один заход — один пункт с конкретным результатом. Перед кодом — инвентарь реально
  используемых опций/вызовов (чтение); неиспользуемое не пишем.
- Внутри пункта гоняем только затронутые стадии:
  `check_platform.py --handler-root "d:/grav/Tactic Stream/TH" --only "<regex>"`
  (`--list` — все стадии). Частичный прогон пишет `partial.json` и не считается gate.
- Перед коммитом пункта — полный gate (параллельно, ~3–4 мин; `--jobs 1` — последовательно).
  Стадии из поля `retried` в `gate.json` упоминаются в отчёте. Парные отчёты обновляем
  только для затронутой области; все остальные — в 1.5.
- Пункт закрыт коммитом в ТС и ТХ (версии, CHANGELOG, документация) и push в `backup`.
- После коммита ТС — `deploy/docker/manage.py update` и `check`: контейнер видит исходники через
  read-only mount, но держит старый код в памяти до перезапуска. Локальный SQLite
  (editable install) подхватывает исходники при перезапуске `START_TACTIC_STREAM.bat`.
- Если пункт не принят, прямо перечислить остаток; регистрация класса, ссылка на
  готовую панель и число снимков сами по себе не закрывают пункт. Сроки заранее не обещаем.

Точные классы, XML-примеры и ограничения: [чеклист B07](docs/frame_table.md#legacy-checklist).

<details>
<summary>Исторический состав 14 подблоков: справочник, не текущая очередь</summary>

Масштаб S → M → L → XL → XXL обозначает относительную трудоёмкость:
от компактного сценария с готовым владельцем до системной совместимости и поставки.

| Очередь | Блок | Масштаб | Что делаем и как принимаем |
| --- | --- | --- | --- |
| 1 | U01 — активный остаток Frame | S | Общий inline keywords/tags editor: одинаковые draft, подсказки, добавление/удаление тегов, Save/Cancel, focus и обновление строки в ТХ/ТС. Без переноса мёртвых форм админки. |
| 2 | L02 — доводка подключённых 4 адаптеров | S–M | Проверить используемые legacy options, контексты/приватность, открытие готовых Notes/Messages/Tasks и обновление счётчиков. Основание — конкретные XML/callers; не переписывать приложения. |
| 3 | L07a — служебные/admin cells, 7 классов | M | Login/Security/preferences/update/template/summary/notification cell через существующих owners. Ячейка recipient/trigger не означает доставку почты; template update может потребовать часть L10. |
| 4 | L03 — configurable actions/layout/drop, 3 класса | M | Реальное действие/script с контекстом строки/выделения; XML options сохраняются редактором, ошибки/отмена/ACL явные, у drop есть альтернатива без drag. |
| 5 | L05 — task/process/parallel status/work, 6 классов | M–L | Из таблицы меняются статус и назначение через текущих owners, с допустимыми переходами, revision, ACL и конфликтами. |
| 6 | L06 — table Gantt/timecard/week/hours, 5 классов | L | Исходные временные параметры, редактирование часов/дат и итоги через готовые schedule/time owners. Отдельный Calendar dock сохраняется. |
| 7 | L01 — связи/nested/hidden rows/summaries, 8 классов | L | Настроенная дочерняя таблица действительно читает/добавляет/связывает объекты; отдельный query/selection scope, состояние, фильтры и итоги. |
| 8 | L04 — publish/append/checkout/load/render/submission, 7 классов | L–XL | Проверить реальные файлы, версии, naming, очередь, повтор и FileUndo. Локальные/DCC операции остаются native capabilities. |
| 9 | L07b — общая приёмка B07 | L–XL | После U01 и L01–L07a проверить весь каталог и используемые options, inline/forms и bottom/group_bottom/total_summary. Закрыть только подтверждённые сценарии. |
| 10 | L10 — проекты/plugins/schema/import/export | XL | Установка, update/export/import/uninstall и частичный сбой сохраняют схему, данные и файлы по исходному контракту. |
| 11 | L09 — Workflow/Triggers/уведомления | XL | Исполняются реальные узлы/handlers/события; проверены транзакция, повтор, ошибка и доставка без дублирования. UI graph сам этого не доказывает. |
| 12 | L08 — остаток API/native Python/TEL | XL–XXL | Неизменённые используемые скрипты дают согласованные результаты, контекст, ошибки и эффекты в исходном и новом ядре. Объём уточняется по подтверждённым caller-контрактам. |
| 13 | L11 — общая SQLite/PostgreSQL матрица | XXL | Одинаковые сценарии на двух реальных СУБД, DDL/изоляция/конкуренция/rollback/восстановление. |
| 14 | L12 — независимые поставки и переход | XXL | Чистая Windows и Apache/PostgreSQL проходят установку, upgrade, перенос поддержанных проектов и backup/restore на копиях. |

</details>

Сортировка не отменяет зависимости: необходимая текущему виджету часть L08,
L09 или L10 делается **в его блоке**, а не ждёт своей строки. L07b зависит от
закрытия всех табличных групп; L11/L12 завершают уже проверенные по ходу работы
сценарии. Каждый блок включает оба нужных UI, примеры, проверки и документацию.

Актуальные числа каталога приведены в начале этого плана; старые оценки
в исторических разделах не являются текущим статусом. Исключён namespace
`pyasm.prod` и подтверждённые зависимые обёртки, а не все определения
в каталоге `config/.../prod`.

### L08–L12: границы оставшегося backend и поставки

**L08 — ядро и скриптовые контракты.** Для каждого остатка записать исходного
caller/конфиг, поддерживаемые аргументы и воспроизводимый сценарий. Проверять
Search/SObject/связи, TEL/expression/Naming, Command/rollback и request/login/site
context по уже существующим сравнительным harness. Среди кандидатов на проверку:
`related_type` в expression, генерация задач по pipelines/expressions,
неперенесённые режимы ingest, multi-site auth/batch, persistent/filter input state.
Это кандидаты из исходных guards, не утверждение, что каждый вариант нужен
проекту или полностью отсутствует. `UnsupportedContract` сначала классифицировать:
реальный пробел, намеренная граница безопасности либо согласованное исключение.
Не снимать transaction/Sudo/request-context guards ради зелёной проверки.
API/import/signature readiness не засчитывается как поведенческий паритет.

**L09 — выполнение процессов.** Пройти используемые pipeline node types и
иерархические процессы, зарегистрированные handlers/listeners, trigger inputs,
sync/async и расписания. Отличить выполненное UI-редактирование graph/trigger
от исполнения на backend. Для email/notification проверить recipients, privacy,
ошибку доставки и повтор без дублирования; событие в UI и NotificationTrigger
cell сами по себе отправку не доказывают. Внешние transport/subprocess сценарии
включать по реально используемому legacy-контракту, на собственных фикстурах.
Готовые B10/B11/B13 не переписываются; устраняются подтверждённые зависимости.

**L10 — жизненный цикл проекта.** Сверить уже реализованные CreateProjectCmd,
plugin/template install/export/update/uninstall, manifest/schema/seed и файловый
naming с оригиналом; реализовать оставшиеся используемые ветки. Включить
schema DDL/types/constraints/resources и XML/data/pipeline import/export там,
где есть исходный вызов. Проверить откат частичного сбоя, upgrade существующего
проекта и повторный запуск. Не создавать вторую модель проектов и не считать
одну успешную установку CG доказательством совместимости любого плагина.

**L11 — общая проверка БД.** Разворачивать отдельные временные SQLite и реальные
PostgreSQL, выполнять одинаковые native/API/script сценарии, metadata/DDL,
создание проекта, межпроектные ресурсы, даты/JSON, конкурентные записи, rollback
и восстановление. Это завершающая матрица; проверки на нужной СУБД обязательны
и внутри предыдущих блоков. Рабочая Docker SQLite не становится PostgreSQL
автоматически от прохождения тестовой фикстуры. MySQL остаётся отложенным
по решению пользователя 2026-10-11 и не блокирует этот план.

**L12 — поставка и проверяемый переход.** Два комплекта из
[HANDLER_DEPLOYMENT.md](HANDLER_DEPLOYMENT.md): локальная Windows
EXE/Vue/Electron + комплектный Python/headless backend/SQLite и существующий
Handler; серверный Apache/headless backend/PostgreSQL с независимыми клиентами.
Проверить чистую установку, штатный запуск/остановку, upgrade, экспорт/перенос
согласованных проектов и backup/restore БД, repository и config на копиях.
Зафиксировать поддерживаемые исходные версии и ограничения; Git-архив кода
не заменяет резервную копию данных. Не обещать универсальный автоматический
мигратор по результатам одного проекта. Финальная матрица включает браузер,
неизменённый SDK и полный GUI Handler с обычным пользователем и admin.

### Единое правило готовности для каждого блока

1. Исходный класс **с наследованием**, callers/config/options и конкретные
   исходные сценарии изучены. Рабочие реализации используются; явно недописанные
   исключаются с доказательством. TODO или `pass` у alias не означают недописанность.
2. Есть минимальный XML и воспроизводимые тестовые данные без рабочих БД,
   пользовательских файлов, credentials и данных `legacy/local_data`.
   Скрипты проверяются без переписывания под Stream; результаты, ошибки,
   транзакции и эффекты сравниваются с исходным TACTIC. Исправленные исходные баги
   отмечаются отдельными ожиданиями.
3. Соответствующий UI использует уже готовые Frame controls и один скелет,
   размещённый по доменным папкам. Handler и Stream хранят самостоятельные копии,
   а не требуют общего checkout/bundle. Права и запись остаются у существующих
   native/backend owners. Для платформенного различия есть явная capability.
4. Проверены реальные операции, отказ в правах, stale revision, отмена/сбой/откат,
   пустые и большие наборы. Для UI сняты свежие source-checked Qt/Vue состояния
   на одинаковых данных/теме/языке/масштабе/размере; отдельно проверены клавиатура,
   touch/узкая компоновка и весь нужный Frame gate. Метрики старого выпуска
   не выдаются за результат нового.
5. EN/RU Widget Database/предметная Help содержат путь вызова, исходные options,
   XML-пример, снимки и проверенные ограничения. Чеклист, API contract status
   и отчёт обновлены только по прошедшим сценариям. Diff просмотрен, сделаны
   отдельные коммиты в затронутых репозиториях и backup на NAS.

### Что не возвращаем в объём

- Полный `pyasm.prod`, старые production-схемы/Flash/Maya naming,
  `commit_session`, `get_md5_info`, неиспользуемые SnapshotType/FileAccess,
  Drupal/лицензирование, S3 и полный старый HTML shell. Уже работающие HTML widget/API контракты
  сохраняются; перенос таблицы не даёт права подменить их JSON.
- Три явно недописанных виджета: `WikiElementWdg`, CG publish `PublishElementWdg`,
  `SnapshotServerElementWdg` — с исходными причинами в B07-каталоге.
- Новый WebEngine/WebView в QML, отдельный браузерный Repository Sync,
  новый web Batch Manager. Native Repository Sync уже перенесён в B12 и остаётся;
  Batch Manager сохраняет свой существующий web UI и самостоятельный QML запуск.
- Повторная перерисовка уже принятых Frame экранов и новые возможности без
  исходного сценария. AI API — отдельная будущая возможность, не обязательное
  условие закрытия legacy и не замена совместимости исходных скриптов.

**Контрольная точка прежнего этапа «Базовые UI» — 2026-10-20** остаётся историческим результатом.
Её зависимости от nested tables, сохранённых layouts и ingest принимались частями;
актуальный остаток находится в пунктах 1.1–1.5 выше. Готовые экраны повторно
не переносим, старый HTML/Mako Custom Layout Editor остаётся исключённым.

## B14 remaining surfaces — 2026-10-19

Stream 0.112.167 / Handler 0.6.0.118 share Knowledge Base, schema confirmation,
Timesheet, reports and work-hour presentation. API/journal retain browser
capabilities; native rich text, ACL, revisions, drafts and mutation owners stay
in their existing hosts. Complete source ownership, evidence commands, restore
points and remaining limits: [frame_remaining.md](docs/frame_remaining.md).
B07's 40 usable legacy widget classes remain open; Batch Manager is unchanged.

## B13 scripts and native tools — delivered, 2026-10-18

Stream 0.112.166 / Handler 0.6.0.117 connect Script Editor/source commands,
shelf bar/editor, native triggers, DCC options, Handler Server and selected-object
Database tools to independent Frame descriptions. Existing execution, revision,
ACL, transport and native window owners stay in each product. Batch Manager's
scheduler and existing web UI remain intact. The shipped `side_tools/frame_tool`
example demonstrates a small script-created native UI from existing controls.
The final gate passes 134 stages; current evidence includes 384 original/native
pairs and 144 native/Vue compositions. Source map, capabilities and limits:
[frame_scripts.md](docs/frame_scripts.md). B07 stays open; B14 is next.

## B12 files and repository queues — delivered, 2026-10-18

Stream 0.112.165 / Handler 0.6.0.116 connect File Workspace, check-in/ingest,
Drop Plate, matching, Commit Queue, native Repository Sync, repository prompts
and screenshot selection to independent shared descriptions. Existing file,
request, revision, transfer and mutation owners remain native to each host.
The browser remains the production inspection/admin interface; native local/DCC
operations are declared capabilities. Source map, evidence and the resolved
combined native timer-test regression are in [frame_files.md](docs/frame_files.md).
The final gate passes 121 stages. This checkpoint **does not close B07**.

## B11 communication — 2026-10-18

Stream 0.112.164 / Handler 0.6.0.115 share conversation/header/body/composer
presentation, message forms and child panels, attachment staging, activity
cards/calendar, notification history and toasts. Existing stores, request and
mutation owners remain separate. Neutral emoji/people pickers keep their native
controls in both engines. Scope, capabilities and reproducible acceptance are in
[frame_messages.md](docs/frame_messages.md). B07's remaining widgets stay open.
The checkpoint passed 111 mandatory platform stages, 214 native communication
cases, eight temporary-server checks and 384 source-checked Qt/Vue capture pairs.

## B10 production scheduling — 2026-10-18

Stream 0.112.163 / Handler 0.6.0.114 share production Gantt, its timeline/rows,
operation menus, pointer/zoom/progress rules, the separate Calendar dock,
milestone presentation and explicit schedule form. Existing task drafts,
revisions, server authorization and native/web mutation owners are retained.
Source map, capabilities and evidence: [frame_schedule.md](docs/frame_schedule.md).
B07 legacy-widget gaps and B11 Messaging remain separate.

## B09 task surfaces — 2026-10-18

Stream 0.112.162 / Handler 0.6.0.113 use independent task descriptions under
`shared_ui/features/tasks`: workspace/quick toolbar, task rows/expanded fields,
scope/filter/options/columns, bulk editor, menus and native management summary.
Existing task request/draft/revision/permission/mutation owners remain in place.
Details, capabilities and reproducible evidence: [frame_tasks.md](docs/frame_tasks.md).
Gantt/Calendar scheduling is B10; the B07 legacy-widget gaps remain open.

## B08 object surfaces — 2026-10-17

Stream 0.112.161 / Handler 0.6.0.112 share object forms/reports/operations,
description, snapshot/watch surfaces and Inspector fragments, including measured
note bodies and edit/delete children. Query, ACL, revisions, drafts and native
file/mutation owners remain in their existing products. See
[scope, reproduction and platform limits](docs/frame_objects.md). B07's unfinished
legacy widgets remain open; complete Task Manager and Messaging stay B09/B11.

## B07 checkpoint — 2026-10-17

Stream 0.112.160 / Handler 0.6.0.111 share Table View geometry/paint, menus,
typed inline editor scenes, cell rules and a 37-class catalogue. Existing query,
revision, ACL and mutation owners remain authoritative. This is not completion
of B07: the shipped/CG census still contains 40 usable classes needing full
workflows. See [the current scope and reproduction guide](docs/frame_table.md).

## Tactic Frame foundation migration — 2026-10-15

Current work proceeds from foundation through controls, hosts and the main
window to screen contents. The live acceptance ledger is
[`docs/shared_ui_foundation_plan.md`](docs/shared_ui_foundation_plan.md).
Its historical Frame execution plan groups that work into 14 full-day batches,
targeting roughly eight hours each including both hosts, original comparisons,
integrated checks, documentation and commits. B01 closes the remaining workspace,
dock and session lifecycle; individual controls remain internal checklist items.
Earlier phase IDs below are historical coverage references, not delivery units.
The B02 control kit and executable atlas are documented in
[`docs/frame_control_catalog.md`](docs/frame_control_catalog.md): 144 shared
examples, native house adapters, standalone offline browser artifact, strict
layout/text-color checks and explicit rendering limits. The old 372-state
gallery remains detailed state/input evidence, not the complete library.
Portable modules and native adapters are organized by responsibility; Handler
and Stream still ship independent copies. Source is formatted and remains
readable. No browser engine is embedded in QML.

B06 search composition and ownership are documented in
[`docs/frame_search.md`](docs/frame_search.md): condition cards and suggestions,
presets, tag/quick-filter headers and editor parts, local process visibility,
sorting/grouping, paging and result-card geometry use independent Frame modules.
Existing query, revision, ACL and mutation owners remain in place. Browser
collections virtualize variable-height rows and tiles; native ListView/GridView
remain native. Table View/cell migration stays in B07.

The navigation drawer now uses one Frame container and keyboard/exit policy in
both hosts, verified against the archived native header/list geometry. Its real
native and browser input/paired captures are reproduced by `tools/frame_navigation`.
Project chooser, expanded cards and search-tab painting now use the shared
`shell/projects.ui.mjs` and `controls/tabs/workspace.ui.mjs` modules. Their actual
input and archived/native/browser comparisons live in `tools/frame_projects`.
The section rail now uses `controls/tabs/section.ui.mjs` for panel/row paint,
close geometry, action records and vertical drag decisions. Both input adapters
retain real grabs and existing selection/reorder/close owners. Project comparisons
also check actual text/background color roles and coherent focus/hover states.
Existing persistence, previews, ACL filtering and loaders retain their owners;
B01 now closes the integrated workspace/session lifecycle: shared root host
composition, dock/tab/layout restore, desktop/phone retention and stale-session
response protection. Whole-window original/native/browser evidence is in
`tools/frame_workspace/output/index.html`; complete desktop/phone and session
journeys are included in the mandatory platform gate. B02 now completes the
reusable-control kit and executable catalog: 3,456 actual pairs, zero external
geometry differences, 28,716 font/color checks and 42 passing platform stages.
Design-advance measurement resolves the former 48 project metadata-bound
differences; all 984 paired project checks pass. The expanded report retains
428 text-metric diagnostics, at most 1.046875 logical px here, separately from
strict geometry/style checks. Physical IME/touch, rasterization and compositor
acceptance remain explicit. B03 now closes the original Administration review:
464 original/current pairs, 2,388 current Handler/Stream pairs, 343 native tests,
real command/save/readback journeys and 42 passing platform stages. The release
uses one existing compact form composition, restores plain checkbox captions and
column ordering, completes Russian diagnostics and retains native drawer focus.
Handler 0.6.0.107 and Stream 0.112.156 remain independent products. Detailed scope,
intentional layout updates, original archive warning and verification limits are
in the B03 checkpoint of the plan. The next batch is B04, support/identity and
connection lifecycle. Empty search contents remain B06.

The previous Administration reports below compared two Frame implementations.
They remain historical checkpoints. B03 adds the independently archived original
comparison and actual mutation acceptance; current reports must still be
recaptured after source changes. Original/current review pairs and strict current
Handler/Stream geometry are separate evidence, not blanket pixel parity with the
old administration layout. The live fourteen-batch plan is the status authority
for the historical phase descriptions below.

Phase 1 supplies a verified subset of the control contract: state paint, metrics, strict local
calendar logic, DateChoice/UserChoice, anchored icon selection and common tree
navigation. The executable control catalog and paired gallery cover actual
Qt/Vue controls; 372 states do not mean 372 control types or the full kit.
The source-linked atlas at `tools/frame_controls/output/ui-elements.html`
separates primitives, neutral composite controls, infrastructure and business
forms/fragments, with explicit unverified families and classification work.
The plan records exact checks and remaining OS/legacy limits. Phase 1 stays open.
Both products remain separately packaged. Window/workspace migration is phase 2.

The current 0.112.150 shell checkpoint adds shared dock keyboard/footer rules
and main user/configuration/connection menu catalog/row composition. Native
procedural menus and platform capabilities remain explicit. The next shell
work is the complete navigation container and project/tab/session composition.
Current evidence and limits are recorded at the top of the foundation plan.

## Tactic Frame: Administration — previous checkpoint

Все десять разделов и вложенные редакторы переведены на общий скелет и переходы
Tactic Frame. На этом этапе две независимые сборки содержали по 37 локальных `.mjs` модулей;
обычная сборка не читает соседний checkout. Запросы, ACL, ревизии и предметные
операции сохраняют существующих владельцев Python/сервер/Vue API.

| Раздел | Объём общего UI/state | Парных состояний |
| --- | --- | ---: |
| Groups | Каталог, параметры, участники, подтверждения | 108 |
| Users | Профиль, аккаунт, группы, пароли, retired, guards | 132 |
| Access rules | Scopes, матрицы, редактор правил, defaults, XML/JSON/inherited | 264 |
| Search Types | Создание, поля, детали, preview, связанные workflows и Naming | 228 |
| Project schema / Workflow | Граф, позиции/связи, process settings, XML, история | 108 + 408 |
| Columns | Каталог/views, свойства виджетов, wizard, XML и preview | 156 |
| Raw database | Строки/ячейки, NULL/DEFAULT/большие числа, CSV, paging, drop guards | 180 |
| Layouts | XML-дерево, шаблоны, элементы/контейнеры/grid, проверка и preview/save | 60 |
| Sidebar | Дерево, параметры, права групп, XML, preview | 204 |
| Naming | Правила, формы, шаблоны, диагностика, подтверждения | 156 |
| Workflow / Process dependencies | Зависимости, уведомления, действия и XML/скрипты | 144 |
| Schema / Delete type | План удаления, проверка имени, подтверждения и unknown-write | 60 |
| Оболочка | Навигация, проект, шапка/actions, адаптация и guards | 48 |

Всего 2256 парных состояний: EN/RU, dark/light, desktop/среднее/узкое окно.
Стенды нажимают настоящие контролы, вводят текст и проверяют граф/state,
геометрию, цвета, шрифты, полосы/индикаторы и значки. Они используют изолированные
данные и не выполняют удаление типа на боевом сервере. Qt округляет ширины букв,
Chromium использует дробные метрики: центрирование содержимого кнопки сверяется
с измеренной шириной её подписи, а размеры контролов проверяются отдельно строго.

Состояние экземпляров сохраняется между разделами; закрытие раскрывает скрытый
черновик. Проект блокируется также на время дочерней операции. Ссылки Workflow
из типа/схемы и Manage Groups из Sidebar ведут в основной раздел, без второго
редактора. Новый тип из схемы остаётся дочерним редактором; его Cancel не удаляет
уже созданный на сервере тип.

Нативный Layout Editor использует QML и отдельный SourceEditorService с house
ScriptCodeEditor. Инициализация WebEngine и старый браузерный мост удалены из
этого пути. В ТХ Open view запускает системный браузер без ticket в URL; в ТС
открывает рабочее представление. Сервер должен поддерживать layout-authoring API.
Сохранение требует проверки точного XML и подтверждения. Неизвестный результат
записи блокирует повтор до успешного чтения.

Контракт и владельцы модулей: `docs/shared_ui_contract.md`. Физические каталоги:
ТС — `src/tactic_stream/shared_ui`, ТХ — `thlib/ui/qml/tactic_frame`.
Синхронизация только явной командой `tools/sync_tactic_frame.py`; манифест
проверяет совпадение файлов. Каталог проверок и парных снимков —
`tools/frame_admin/output/index.html`. Готовность переноса не сертифицирует
боевую БД, PostgreSQL или системную рамку/композитор Windows.

Неиспользуемые старые QML-файлы сохранены: автоматическая проверка не разрешила
их удаление. Они не подключены к новым экранам. Configuration и рабочий Гант
этой задачей на Frame не переводились.

## Мобильные итемы — 2026-10-11

Уточнение 2026-10-12: мобильный таск-инспектор использует оформление менеджера задач.
Общий `phone-panel-heading` задаёт шрифт и регистр как dock heading, включая
диалог с `v-window`: стандартный стиль заголовка desktop-диалога больше его не перекрывает.
`TaskInspectorHeader` сохраняет desktop-компоновку ТХ, на телефоне использует
`ItemSurface`/квадратное `ItemPreview` 42px, отступы, скругление и тень карточки менеджера.
Выбор процесса, задачи, обновление и раскрытие полей доступны компактными controls.
`mobile_refinements.mjs` сравнивает вычисленные стили обоих экранов на 320/360/390px,
проверяет точный процесс задачи и сохранение черновика после возврата.
В ТХ соответствующего мобильного экрана нет; его desktop-инспектор не изменён.

Инспектор на телефоне открывается в рабочей панели `notes` внутри DockWorkspace,
под общей шапкой приложения. `mobile_inspector_page.mjs` проверяет 320/390/640px:
главная шапка видима, навигация нажимается, composer помещается в оставшийся viewport,
Back возвращает к исходному объекту или менеджеру задач без потери черновика.

`MobileResults.vue` показывает один уровень существующих узлов `ResultPresentation`.
Касание/свайп влево открывает объект, связь, процесс, снапшот или его версию;
свайп вправо, кнопка и browser Back возвращают предыдущий экран. Внутри итема
скрыты поиск, вкладки и пагинация корня. Карточки собжектов сохраняют скругления,
круглое превью и цветовой акцент; файлы/связи/процессы имеют отдельные признаки.
Нового серверного API нет: `loadChildren` и `loadBranch` используют result-items,
штатные права, прямые публикации и защиту по типам предков.

По вкладке сохраняются `mobilePath` и `mobileScroll`; раскрытие desktop-дерева
отдельное. `history.state.mobileResult` принадлежит конкретной вкладке/проекту/SearchType,
не добавляет идентификаторов в URL. App делегирует собственные события этой
истории мобильному представлению, чтобы Back не запускал повторные запросы
открытия URL. Preview имеет отдельный шаг истории через события общего
FilePreview; закрытие не оставляет лишнего шага. Окна с правками не закрываются
самовольно при переходе. Touch-обработка отделяет касание, горизонтальный свайп,
вертикальную прокрутку и pinch zoom; анимация использует общую тему/reduced motion.
Пагинация корня получает scroll из внутреннего viewport, пагинация связей —
существующий `hasNext`/`nextOffset`. Инспектор, меню операций и файловый preview
остаются общими. У ТХ нет такого телефонного экрана: это явная адаптация Stream.
Поведение описано в EN/RU Help → Mobile/Results; проверка — `mobile_items.mjs`
на частном cg-шаблоне через `tools/result_browser.py`, плюс регрессии дерева и видов.
Реальные iOS/Android-устройства этим проходом не проверялись.

Уточнение мобильной компоновки 2026-10-12: заголовок содержимого остаётся плоским
прямоугольником с данными собжекта и возвратом, без дублирования карточки. Действия —
28px icon-only с общими badges, а не растянутые текстовые кнопки. Выбор процессов/задач
использует desktop `notes`; телефонный Tasks после выбора открывает TaskManager
с отдельным object/process scope, Notes — существующий Inspector. Counts связей и
версий берутся из native result-items. Shared MobilePage управляет swipe/history scroll;
сворачивание поискового chrome пересчитывает viewport после изменения его высоты.
Исправление 2026-10-12: окончание обычного `busy` больше не восстанавливает позицию
из отложенного scroll-cache. `restoreOnLoad` включается только для реального открытия/
возврата во время загрузки, новый wheel/pointer ввод отменяет ожидание. Воспроизведение:
колесо до 150px + клик чтения до 180ms debounce сбрасывал scrollTop на 0.
`mobile_scroll.mjs` проверяет этот сценарий, ввод во время чтения/ожидания восстановления,
возврат, устойчивость геометрии при скрытии/появлении chrome и у конца списка.
В QML ТХ нет этого мобильного presenter/debounce, соответствующего дефекта там нет.
Дополнительно устранён сдвиг строк при скрытии search/tabs: `chromeInset` сохраняет
высоту убранных панелей внутри прокручиваемого корня, `overflow-anchor:none` исключает
повторную компенсацию браузером. Начальная зона 128px предотвращает пустой отступ
при малом движении. В `mobile_scroll.mjs` и `mobile_refinements.mjs` сравниваются
реальные координаты строк и пройденная дистанция, а не только конечный scrollTop.
Мобильные собжекты получили равные поля 12px, центральную ось превью/меню/перехода,
ряд компактных действий по оси текста; прямоугольная шапка содержимого сохранена.
FilePreviewContent используется и модальным FilePreview, и прямым экраном снапшота;
открытие snapshot сразу читает файл через navigation-link, версии остаются отдельным уровнем.
Snapshot Add files вызывает существующий native add_file для latest physical snapshot,
сохраняя оригинальные файлы и обновляя versionless; дубликаты имён и неизвестный
результат RPC защищены от повторного сохранения. Проверка сценариев — mobile_refinements.mjs.

## Текущий порядок работы — 2026-10-11

Мобильная геометрия 2026-10-12: workspace-results без внешних полей, 4px боковые
поля списка, прямоугольный заголовок во всю ширину. Внутренний grid текста ограничен
minmax(0,1fr); object/header actions вынесены компактным рядом под текст, процессы
сохраняют действия сбоку. WindowControls добавляет телефонный Back через Teleport
в начало общего header; переход вызывает native cancel, а не обход guarded close.
ObjectCheckin принимает принудительный close только при force === true, не при событии
cancel. Проверка: mobile_layout.mjs, EN/RU 320/360/390, вложенная Help, черновик заметки,
защита файловой формы; реальных мобильных устройств в этом проходе нет.

NotificationStack на телефоне использует preview 24px, 8px padding и короткое «Готово»
для стандартного server completion. Detail метода скрыт только в этом toast, сохраняется
в history. Длинные предупреждения/ошибки прокручиваются в пределах 64px; action/reply
сообщений и активити сохранены. Desktop presentation проверяется отдельно при resize.
Отдельная notification_history.mjs остановилась на сверке toolbar истории (100px вместо
124px Qt-эталона), до проверки toast; это расхождение истории осталось за текущим проходом.

Исправление восстановления панелей 2026-10-12: DockWorkspace передаёт флаг restoring
при apply/startup/появлении прав. App и TaskManager инициализируют сохранённые панели
без повторного opened и изменения активного дока; CommitQueue уже восстанавливает jobs
при mount и не требует повторного modal open. Close очереди на телефоне возвращает
Results, не удаляя jobs. Вторичные телефонные панели имеют компактный заголовок/Back.
Общий v-window применяется только к HTML dialog: section встроенного дока не получает
app-window и фиксированную полноэкранную геометрию. ТХ сохраняет previous_active в
docks_layout._reconcile; аналога ошибочных браузерных CSS/телефонной панели у него нет.
Проверка: mobile_panel_restore.mjs, workspace_layout.mjs, window_controls.mjs.

По уточнению пользователя результат теперь принимается крупными блоками экранов,
а не очередным отдельным контрактом API. Записи ниже сохраняют историю переноса;
этот порядок имеет приоритет над их очередью следующих шагов. Текущая версия
0.112.91 включает проход Administration и восьми страниц Configuration,
Description/Snapshot Browser, Knowledge Base, Drop Plate/Commit Queue, задачи/общение, доки/лейауты и мобильную компоновку, свежие сравнения
Qt/QML и Chromium и общие исправления структуры/поведения. Свидетельства и
оставшиеся различия перечислены ниже; полное совпадение каждого пикселя не заявлено.

1. **Administration целиком.** Все восемь разделов: Search Types (Summary,
   Workflow, Naming, Details, Fields и создание), Project schema, Workflow
   (pipeline/process/status settings, зависимости, scripts/notifications),
   Columns Editor, Sidebar Editor, Users, Groups, Access rules. Общая шапка,
   сворачивание навигации, списки, splitters, вкладки, формы и все вложенные окна
   сверяются по текущему QML ТХ. Backend дорабатывается там, где этого требуют
   операции редактора. Полезные дополнительные функции Stream сохраняются
   видимыми; автоматическая раскладка нод входит в них.
2. **Configuration целиком.** Сервер/подключение и поддержанные параметры,
   оформление, общие предпочтения, проектные настройки, задачи, check-in и
   repository paths, кэш. Проверяются все controls, объяснения/defaults,
   Reset/Apply/Save/Cancel, preview, черновики, сохранение и поведение после
   повторного открытия/рестарта. Опции desktop/DCC и исключённого Repository
   Sync не выдаются за работающие browser-настройки; границы описываются явно.
3. **Рабочие панели целиком.** Snapshot Browser, Description, Knowledge Base,
   Drop Plate и полноценная Commit Queue со сквозным check-in; Task Manager/
   Inspector, заметки/сообщения, контекстные меню, доки и layouts. Затем
   мобильная адаптация уже проверенных экранов. Состав и неполная готовность
   этих экранов отражены в следующей таблице.
4. **Общая совместимость и поставка.** После экранных блоков закрываются
   оставшиеся обязательные контракты ядра/API, проверяется MySQL, выполняются
   исходный SDK/скрипты, установка cg.zip и сквозные сценарии поставки.
   Repository Sync, S3 и ранее согласованные исключения сохраняются.

### Следующие чанки — после 0.112.32

Administration и Configuration закрыты в описанном браузерном объёме;
блок рабочих панелей ещё открыт. Следующие результаты принимаются целыми
пользовательскими сценариями. Перед первым чанком завершены вложенные строки
metadata-групп sequence/UDIM/UV и обычные права чтения Snapshot Browser.
Уже принятые состояния Description/Snapshot Browser заново не переписывать.

1. **Knowledge Base целиком — выполнено в 0.112.32 в браузерном объёме.**
   Дерево/разделы, полный текст, чтение/оглавление, Visual/Markdown, серверные
   и локальные черновики, публикация, native-вложения, история и права.
   Свежие 16 пар QML/Chromium, встроенная EN/RU Help и проверки перечислены ниже.
2. **Drop Plate + Commit Queue + check-in — выполнено в 0.112.33 в браузерном объёме.** Подготовка файлов/папок и групп,
   объект/процесс/контекст, naming и версии, описание, отправка, Retry/Cancel,
   ошибки и результат в Snapshot Browser. Полный путь от добавления файла до
   сохранённой версии; native backend исправляется внутри этого чанка.
3. **Task Manager + Task Inspector + заметки/сообщения — выполнено в 0.112.34 в описанном ниже admin UI объёме.** Согласованные выбор
   объекта и процесса, создание/редактирование задач, статусы, заметки и
   вложения. Заметки входят в Inspector, как в ТХ. Проверить переходы между
   панелями, сохранение, обновление данных и предусмотренные исходником режимы.
4. **Рабочее пространство целиком — выполнено в 0.112.35 в браузерном объёме ниже.** Полные контекстные меню SObject, check-in
   и копирование skey; управление доками, общие переносимые/разворачиваемые окна,
   splitters, сохранение и восстановление layouts и вкладок. Результат:
   настроить рабочее место и получить его обратно после перезагрузки/входа.

   **Приёмка 0.112.35.** Док-шапка 38px и круглые действия 30/14px сверены со
   свежими DockPanel/DockTitleLabel. Грип — поверхность drag/context; вне зон
   стыковки док плавает внутри браузера. Все восемь resize-краёв, Escape/blur/
   pointer cancellation, заголовочная клавиатура, axis-cursors и общий контролл
   вкладок стека. Основное/расширенное меню объекта и отдельные process/snapshot/
   relation/file/multiselect действия; реальные check-in/revision/Clipboard,
   sKey/web/new tab и confirmed native delete. Файловый DTO хранит code выбранного
   файла, включая второй файл снапшота; выдача байтов и chat privacy проверены.
   Личное сохранение включает split/stack/order/z/float/maximize, активные проект/
   раздел/вкладку, запрос/черновик/страницы/scroll/selection и историю последних
   20 закрытых вкладок. Выбранный контекст восстанавливается без кеширования
   record-пayload или паролей. Серверные native-пресеты сохраняют только
   layout/panels с revision/assigned-view guards; поздний ответ не заменяет
   раскладку другой вкладки. Сброс геометрии сохраняет вкладки и пресеты.
   8 пар текущих QML/Chromium: `.screenshots/workspace-current/index.html`;
   исходники/SHA-256 и размеры PNG рядом. 9 Chromium-сценариев, 8 native/UI
   проверок (PostgreSQL пропущен без DSN), Node docks/workspace/tab-widths;
   логи `workspace-release-browser.log`, `workspace-release-native.log`,
   `workspace-release-final.log`, `workspace-release-empty-process.log`,
   `workspace-build.log`. Existing EN/RU
   Results/Windows/Common controls описывают внутреннее сохранение и границы.
   **Границы:** отдельные окна ОС/DCC/локальные папки требуют исключённого
   desktop-подключения. Диалоги не открываются заново из сохранённого леяута;
   неподготовленные записи не становятся частью пресета. Каталог доков содержит
   реализованные браузерные панели, без заглушек всех отчётов ТХ. Repository
   Sync/S3 исключены. Firefox/Safari, реальные телефоны и MySQL этим блоком
   не проверялись. Это принятый браузерный объём, не 100% UI/API ТХ/TACTIC.
5. **Мобильное приложение целиком.** После проверки desktop: компактные итемы,
   задачи, заметки и сообщения; убрать быстрый sidebar, лишние рамки и кнопки,
   оставить действия, доступные с телефона. Сложные desktop-редакторы явно
   недоступны. Мобильное переключение не теряет черновики и desktop-layout.

   **Приёмка 0.112.36.** На телефоне до 700px быстрый sidebar, dock-шапки,
   разделители и desktop-настройки вида/колонок скрыты. Одна панель выбирается
   в навигации. Компактное непрерывное дерево показывает превью 32px,
   переносимые названия и одно меню действий; обычный тап открывает исходные
   object/process/relation операции. Task Manager показывает вертикальные
   строки с процессом/статусом, выбором и группировкой; полное редактирование,
   native save, вехи и timesheet доступны через явные действия. Inspector
   оставляет высоту заметкам, сворачивает поля задачи и поддерживает вложения.
   Messages переключает список/чат, сохраняет черновик при Back, Enter добавляет
   строку; отправка выполняется кнопкой. Snapshot Browser расположен вертикально,
   без splitter: файл открывается кнопкой, его операции доступны отдельным меню.
   Общие окна и меню учитывают visual viewport клавиатуры и safe area; pinch
   zoom сохраняет масштаб браузера. Выбор мобильной панели отделён от desktop
   layout/tree/visibility/maximize, восстанавливается после reload; даже исключённый
   на телефоне развёрнутый Drop Plate возвращается в прежнем desktop-состоянии.
   Черновики задачи/заметки/чата и выбранный настольный вид сохраняются.
   Сложные редакторы, Script Editor/Shelf, диагностика, Drop Plate и управление
   леяутом остаются на desktop с объяснением в меню телефона. Полезные Stream
   дополнения и настольные виды сохранены.

   Свежие неизменённые QML/controller ТХ и Chromium: 6 разделов галереи
   `.screenshots/mobile-current/index.html`, PNG/размеры/SHA рядом; телефонная
   компоновка — намеренная адаптация, а не настольный ТХ в уменьшенном масштабе.
   Touch-сценарий на 320/360/390/700px и 640×360 landscape проверяет настоящие
   записи статуса задачи, заметки с файлом, сообщения и открытие снапшота,
   синтетическую клавиатуру, reload и возврат desktop 1280px. Desktop-регрессии
   проверяют окна/меню, таблицу/колонки/Gantt/Calendar/вехи, presets/layouts,
   вкладки, снапшоты, общение и справку; Node — docks/workspace/tab geometry.
   Логи `mobile-regression.log` (два прежних ожидания phone UI обновлены),
   `mobile-final.log`, `mobile-acceptance-final.log`, `mobile-tabs-final.log`,
   `mobile-release.log`, `mobile-build.log`; исходные QML-кадры — `mobile-native-reference.log` и
   `mobile-main-reference.log`. Встроенная EN/RU тема **Мобильное приложение**
   доступна из меню телефона; Results/Windows/Tasks/Communication описывают
   сохранение и ограничения.
   **Границы:** реальные Android/iOS-клавиатуры, Safari/Firefox не проверены;
   локальные выбранные файлы после reload требуют повторного выбора. Права
   configured task editor остаются существующими (администратор); мобильная
   компоновка не расширяет доступ. Repository Sync/S3/TH-DCC исключены.
   Общая проверка происхождения исходников выявила восемь изменённых файлов
   соседнего ТХ относительно записанного манифеста; её результат — FAIL,
   а не полная зелёная приёмка ядра. `mobile-current/source-drift.json`
   сохраняет обе ревизии. Мобильные сценарии, вкладки и UI-проверки завершены
   успешно; исходные хеши без аудита не заменены. Временные Python/Qt серверы
   завершены, список оставшихся пользовательских процессов — `mobile-processes.json`.
6. **Оставшаяся совместимость TACTIC/API.** Сверить каталог и реальные вызовы
   исходного SDK/скриптов, закрыть недостающие native контракты, проверить
   права, транзакции и откаты. Представить конкретный перечень покрытых и
   оставшихся операций; не объявлять API готовым на 100% без этой проверки.
   Сначала разобрать восемь текущих изменений Handler из `mobile-current/source-drift.json`
   (query, tasks, server updates, application composition, Drop Plate/Commit Queue,
   global functions), проверить контракты и обновить происхождение исходников.

   **Проверенный объём 0.112.37.** Аудит текущих query/tasks/server updates,
   application composition, Drop Plate/Commit Queue и global functions завершён:
   восемь новых SHA записаны после проверки исходников и неизменённых процедур,
   а не автоматически приняты как доказательство UI/API parity.
   Каталог содержит 129 исходных exposed методов: 122 доступных входа,
   пять оставшихся контрактов и два исключённых production-метода.
   `missing_method` возвращает исходный диагностический False; неизвестный RPC
   продолжает давать Fault 501. Обычные get_unique/insert_update/clone/retire/
   reactivate/snapshot/lock/current используют native проектные/объектные/
   полевые ACL. RetireLog сохраняет текущего автора и generated code через
   узкую внутреннюю область записи; произвольное добавление системных логов
   остаётся запрещено. Remote/local SDK используют общую parent-bound область
   чекина, вложенные вызовы восстанавливают её; поздняя ошибка откатывает
   объект, журнал, снапшот и append файла. Native plugin undo/redo пропускает
   nullable defaults без значения. Кеш фабрики не передаётся пользовательскому
   SObject-конструктору; его исходные поля и повтор без fast_data сохранены,
   native TIME metadata явно описана как дополнение.

   Встроенная EN/RU **Совместимость ядра и API** описывает маршруты native
   исполнения, права, журналы/откат, особенности XML-RPC, текущий ТХ, видимые
   расширения Task Workspace и оставшиеся контракты. Таблицы Markdown переносят
   содержимое вместо обрезания. Свежие кадры:
   `.screenshots/api-block6-help-en.png`, `api-block6-help-ru.png`.
   `tools/audit_api.py` сверяет статический каталог; `tools/verify_api.py`
   выполняет существующий общий набор и записывает runtime-счётчики без
   аргументов, билетов и пользовательских данных. Изолированные фикстуры
   восстанавливают собственные данные, пути импорта и startup-состояние:
   закрытый web-сервер не оставляет Workflow/StatusLog обработчики в последующих
   headless сравнениях с исходным Batch. Старый six из ТХ
   не попадает в последующие spawned Python-процессы. Старый смешанный UI
   сценарий разделён: вход/сессия/отзыв билета остаются в admin.mjs, экраны
   проверяют действующие administration/table_cells/mobile_complete suites.

   **Итоговая проверка.** Общий набор выполнил 923 теста: 909 прошли,
   13 пропущены (11 требуют отдельного PostgreSQL, два — Windows symlink
   privilege), один выявил гонку Configuration после reload. Восстановление
   адреса могло вернуть раздел data уже после открытия диалога и оставить его
   пустым. Общая кнопка и showConfiguration теперь ждут busy/openingLink;
   регрессия удерживает второй ответ navigation и проверяет недоступность
   открытия до завершения перехода. После исправления прошли все пять
   затронутых Chromium-сценариев: Configuration, вход/сессия, layouts,
   полный mobile и desktop workbench. Повтор всего набора после этого
   локального UI-исправления не заявлен. Логи: `api-block6-release-final.log`,
   `api-block6-configuration-fixed.log`; отдельный API → Engine → Generation
   прогон — 16 тестов без ошибок (`api-block6-startup-engine-fixed.log`).

   Все 122 доступных входа измерены: 121 имеют успешный вызов, test_error
   подтверждён штатным исключением/Fault 500. Это измерение входов, не branch
   coverage или full parity. Сохранены исходный полный runtime отчёт и
   отдельный повтор; `.screenshots/api-block6-verification.json` связывает
   результаты без исправления статистики старого неуспешного прогона.
   Сборка frontend прошла. Проверка PID и времени создания подтвердила
   завершение собственных тестовых Python/Chromium-потомков; рабочий сервер
   и существующие процессы ТХ сохранены (`api-block6-process-cleanup.json`).

   **Остаток:** set_palette (request Palette/HTML), get_widget и
   get_column_widgets (родной HTML renderer), set_application_state
   (HTML top_layout), execute_js_script (серверный PyV8/Python bridge).
   Их DTO или browser JS не выданы за исходный контракт.
   commit_session/get_md5_info, S3, Repository Sync и TH/DCC исключены.
   Доступность входа и его измеренный вызов не равны проверке всех аргументов
   и побочных эффектов: `full_api_parity_verified` остаётся false.
7. **Общая приёмка и поставка.** Штатное создание проекта из cg.zip,
   взаимосвязи ассетов/эпизодов/текстур, задачи/заметки и файловые версии;
   реальные поддерживаемые DB vendors, запуск батника, обновление и рестарт.
   Свести оставшиеся ограничения и результат общих регрессий.

   **Результат 0.112.38.** Предоставленный cg.zip принят штатным upload и
   браузерным мастером проекта: имя шаблона niki_friends взято из manifest,
   имя архива не подменяет идентификатор. На частных проектах проверены
   32 объекта, 13 явных задач, 47 заметок, 45 направленных связей: вложенные
   и общие ассеты, эпизоды/шоты, категории и общие текстуры. Повторное
   заполнение идемпотентно; выключены только Telegram callbacks с сохранением
   кода. Остальные native triggers работают. Две версии upload/check-in,
   latest/versionless и неизменённая процедура текущего ТХ проверены на
   Windows SQLite и Linux PostgreSQL; содержимое предыдущих версий сохранено.

   PostgreSQL 18.6 прошёл 16 проверок bootstrap/upgrade, native SQL/CRUD,
   метаданных, схем/связей, проектных ресурсов, plugins, command/queue/diagnostics,
   SQL builders, expressions и native layouts. Два Windows-пропуска границ
   symlink дополнительно пройдены теми же тестами на Linux.
   Отдельный SDK-прогон подтвердил 12 сценариев на SQLite и те же 12 через
   частный Apache/PostgreSQL, включая HTTP upload/download/range и права.
   Deployment-check дополнительно проверил origin, текущие UI assets,
   три отдельных listener 8081–8083 и TEMP commit/rollback. Его прежние
   /admin/ UI адреса и предположение о портах исправлены; рабочий стенд
   не перезапускался и не мигрировался. Старая PG-проверка ожидала другой
   тип исключения при timestamp-инъекции: исправлено ожидание ValueError,
   проверки отказа до SQL и отката оставлены. Это не ослабление validator.

   BAT больше не распознаёт базу по data/db/sthpw.db. Новый init --if-needed
   проверяет настроенный Store; явный init по-прежнему отказывается от
   существующей базы. TACTIC_DATA_DIR/TACTIC_CONFIG_PATH применяются к init,
   upgrade и serve. Настоящий BAT дважды запущен на частной Windows базе:
   проект, файл и preferences пережили upgrade/restart; browser-probe
   получил корень только после готовности workers. Monitor/workers остановлены.

   Vite пересоздаёт generated web из актуальной сборки и frontend/public,
   вместо накопления старых assets; LICENSE.VUE.txt перенесён в public.
   Wheel включает JS source maps. Чистая сборка уменьшилась с 236191305
   до примерно 15,6 МБ. Пакет установлен отдельно от src: проверены оба
   запуска CLI, current manifest, все 44 JS/maps, HTTP/ETag, EN/RU Help,
   отсутствие /admin/ alias и штатная остановка. Импорты pyasm/tactic/API
   подтверждены из установленного пакета; переиспользованы 12 SDK-сценариев
   проекта, задач/заметок, upload/check-in/download и ACL. Созданный проект
   сохранился при втором запуске. Встроенная статья
   «Установка, обновление и приёмка» описывает владельцев данных, vendors,
   настройки запуска, обновление, cache/reload и границы поставки.

   Полный обнаруженный набор — 926 запусков, 888 уникальных test IDs:
   некоторые существующие unittest modules импортируют чужие TestCase
   и тем самым повторяют сценарии. Windows результат после точечного повтора:
   913 passed, 13 skipped; 11 PG-пропусков и два symlink-пропуска проверены
   отдельно на Linux. Исходный native-отчёт содержит один FAIL: временный
   partition runner не имел Windows spawn main guard. Исправлен runner,
   приложение не менялось; все 3 CLI-теста повторно прошли. Transport/browser
   части прошли 62 + 61 тест без повторов. Старый неуспешный отчёт сохранён;
   он не выдан за чистый первоначальный прогон. Общая регрессия, связывающие
   отчёты/хеши и финальный контроль процессов —
   .screenshots/delivery-verification.json.

   **Остаток:** MySQL не реализован; Windows EXE/Electron ещё не упакованы.
   На момент 0.112.38 пять HTML/PyV8 API контрактов остаются pending, два production-входа
   исключены; full_api_parity_verified=false. Repository Sync, S3 и TH/DCC
   bridge не входят в объём. Windows symlink требует права ОС; Windows
   CG/browser-проверки используют copy, Linux CG — native symlink шаблона.
   Физический телефон и полное попиксельное совпадение Qt/браузера этим
   delivery-прогоном не сертифицируются. Стабильные JS имена требуют reload
   открытых вкладок после обновления; бесшовный rolling update не заявлен.

8. **Исходный HTML API и серверный JavaScript (0.112.39).** Подключены
   set_palette, get_widget, get_column_widgets, set_application_state и
   execute_js_script. Исходные HTML buffers/widgets, Palette и top_layout
   работают в контексте запроса; JsCmd и оригинальный JS SDK исполняются
   синхронно через QuickJS-NG и текущие API/ACL/Command. Серверный JS доступен
   в Script Editor и Script Shelf; контракты и ограничения описаны в EN/RU Help.
   Полная старая HTML оболочка приложения/таблицы и отсутствующие классы
   виджетов остаются неподдержанными и возвращают явную ошибку. Доступно
   127 из 129 входов, два согласованных исключения; полный паритет не заявлен.
   Подробности и результаты проверки — в разделе блока 8 ниже.

### Блоки 9–13 после 0.112.39

Нумерация продолжает завершённые чанки 1–8. Результаты блока 9 записаны
в конце файла; пункты 10–13 — будущие работы. Основные экраны заново не переписываются;
полезные дополнения Stream остаются доступными пользователю.

9. **Закрыть оставшиеся варианты legacy/API.** Составить проверяемый список
   действующих ограничений по исходному коду и неизменённым клиентским вызовам,
   а не только по наличию 127 методов. Перенести необходимые зависимости
   действующих методов и метаданных, оставшиеся
   поддерживаемые варианты API info, SQL/выражений, команд и удаления.
   Проверять каждый контракт на оригинальном runtime: аргументы, формат
   результата, права, побочные эффекты и откат. Отдельно описать границы
   QuickJS относительно исходного PyV8. Результат — конкретная матрица
   проверенных и ещё неподдержанных вариантов и актуальная EN/RU Help;
   доступность входа не выдаётся за полный поведенческий паритет.

   Уточнение пользователя 2026-10-11: полную старую HTML оболочку больше
   не переносить. Уже работающие HTML методы и общие зависимости сохраняются;
   get_widget/get_column_widgets остаются ограниченными перенесёнными классами.
   Основной UI остаётся Vue; существующий server_js входит в проверку API.

10. **MySQL и общая проверка баз данных — отложено пользователем 2026-10-11.**
    MySQL сейчас не переносить: необходимость поддержки ещё не подтверждена.
    После пункта 9 следующим идёт пункт 11. Исходный объём на будущее:
    перенести родной MySQL ресурс/
    драйвер и диалект, bootstrap/upgrade, системные и проектные схемы,
    метаданные, транзакции и права. Проверить реальные SQLite/PostgreSQL/MySQL
    одними сценариями: создание cg.zip, CRUD, связи, Workflow, задачи/заметки,
    версии файлов, очереди, rollback/undo/redo и повторный запуск.
    Смена vendor не означает миграцию пользовательской базы; тестирование
    выполняется на собственных данных. Документировать настройку и границы.

11. **Итоговая подгонка desktop UI под текущий ТХ.** Снять свежие эталоны
    текущих QML/controllers и браузера в одинаковых теме, масштабе и размерах.
    Пройти главный workspace, навигацию/вкладки, Administration/Configuration,
    все рабочие панели, окна, контекстные меню и управление доками.
    Исправить расхождения размеров, шрифтов, цветов, иконок, состояний,
    анимаций и поведения в общих controls. Проверить drag/maximize, splitters,
    клавиатуру, dirty/error guards и восстановление layouts; полезные
    дополнительные возможности сохранять видимыми. Результат — галерея
    актуальных сравнений и сценарии приёмки по каждому экрану.

12. **Итоговая мобильная приёмка и браузеры.** Проверить уже сделанную
    мобильную компоновку на узком экране: items, Inspector/задачи, заметки/
    сообщения, composer, вложения, поиск и переходы skey, reload и вкладки.
    Убрать оставшийся desktop chrome и недоступные на телефоне операции;
    проверить тач, экранную клавиатуру, ориентацию, прокрутку и возврат.
    Расширить проверки на Firefox и WebKit; реальные Android/iOS/Safari
    проверять при доступности устройств, эмуляцию не выдавать за такую
    проверку. Все ограничения описать в видимой справке.

13. **Автономная Windows-поставка и итоговая приёмка релиза.** Подготовить
    предусмотренную EXE/Electron поставку без обязательной ручной установки
    Python. Проверить первый запуск, установку/обновление, сохранение баз,
    файлов, пользовательских настроек и layouts, восстановление после
    ошибки и штатную остановку monitor/workers. После блоков 9–12 выполнить
    общий SDK/browser/CG прогон из установленного пакета, проверить ресурсы,
    версии, документацию и описанные исключения. Рабочий сервер и данные
    пользователя не использовать как тестовую fixture.

Repository Sync, S3, старый production-слой и подключение TH/DCC остаются
исключёнными. Работа с физическими устройствами и доступными DB vendors
отмечается отдельно от эмуляции и пропусков; EXE/Electron пока не реализованы.

Для каждого UI-чанка: актуальные QML/controller ТХ, совпадение структуры,
размеров, цветов и поведения, свежие сравнительные кадры, встроенная EN/RU
справка и проверки изменённых сценариев. Общий прогон выполняется при закрытии
чанка; повторяется раньше при изменении общего компонента или найденной
регрессии. Доработки backend/совместимости отдельно перечислять в результате,
чтобы время на них не выглядело временем только на вёрстку. Не расходовать
полный повторный прогон на каждую косметическую правку. Собственные тестовые
процессы останавливать в finally. Repository Sync, S3 и подключение TH/DCC
остаются исключёнными; полезные дополнения Stream сохраняются видимыми.

### Результат чанка 3: задачи и общение — 0.112.34

Task Manager проверен целиком: карточки процессов, компактные строки, таблица,
Gantt, Calendar, выбор точной задачи, полные формы, пакетные черновики, расписание,
undo/redo черновика, конфликты и неопределённый ответ сохранения. Из менеджера
открывается Inspector именно для выбранной задачи; смена вида не теряет правки.

Task Inspector перенесён по текущим TaskInspector.qml/CommunicationView.qml:
46px context header, 32px preview, 148px task/related panel, 80/32px WorkHoursSummary.
Процессы получают цвета и счётчики, основная/дополнительная задачи — свои цели
заметок. Используются общие поля, status/user controls, slider, меню и composer.
Короткая история стоит внизу; длинная сохраняет позицию по цели при закрытии и
повторном открытии. Активный Inspector обновляется раз в 30 секунд, сохраняя
грязные поля и исходную ревизию. Текст черновика сохраняется после reload под
авторизованным current_user и точным контекстом, по контракту ComposerDrafts ТХ.

Заметки принимают текст, изображения из буфера, перенос файлов и только вложение
без текста через штатный native FileCheckin. Карточки не дублируют web/icon как
отдельные исходные файлы; preview/download работают. Messages проверен вместе с
личными/групповыми чатами, drafts/reload, вложениями и приватным чтением, историей,
pins, forwarding, delayed/retry send, EN/RU Help и узким viewport. Исправлены выбор
первого видимого чата и глобальный контекст без принудительного проекта admin.

Backend: исправлены duplicate color/user keys каталога процессов, пакетное чтение
identity, счётчики заметок всех веток и native approved/total. Блокировка версий
в chat/avatar check-in сохраняет родителя доверенного Checkin:writing; создание
файлов использует предусмотренное edit-разрешение, сохраняя проверки владельца,
проекта, parent/file anchors, приватного скачивания и отката. Обычный аккаунт
загружает собственный аватар идемпотентно; чужой профиль и проект отклоняются.

Свежая галерея — `.screenshots/collaboration-current/index.html`: 11 пар текущего
неизменённого QML ТХ и Chromium, исходные размеры, даты и SHA-256. Source fixtures
используют настоящие Tasks/Communication/Messages/Attachment controllers без
соединения с сервером ТХ; данные кадров различаются, полного пиксельного совпадения
не заявляем. EN/RU описание поведения и структуры добавлено во встроенную Help.

Проверки: native задачи/статусы/расписание/заметки, сообщения, updates/navigation,
own avatar, scoped check-in/FileUndo и security users; Chromium Inspector, Messages,
общие окна, полный Task Manager и quick process views; production build и версии.
Логи — `.screenshots/collaboration-*.log`. Тестовые базы временные; cleanup в finally.

Видимые дополнения Stream сохранены: отдельные Notes в Appearance, ответы/история
правок, полные task actions, переход к связанной задаче, переносимые/изменяемые окна.
Разворачивание/restore, Alt+arrows/Alt+Shift+arrows и Escape rollback общих окон
проверены; зоны resize больше не прокручиваются поверх форм. Saved dock layouts
завершаются отдельно в чанке 4, полная мобильная приёмка — в чанке 5.

Граница: настроенные браузерные Task/Discussion команды пока admin-only;
обычные SDK task/note права проверяются отдельно и не означают доступность этих
редакторов обычному аккаунту. Messages/profile работают с разрешёнными обычными
аккаунтами. Browser date picker, локальные file handles и reply selection после
reload, production PostgreSQL/MySQL и физические телефоны не выданы за проверенные.
Полная совместимость API остаётся в чанке 6. Repository Sync, S3, TH/DCC исключены.

### Результат блока Configuration — 0.112.30

Закрыт общий native ColorField/Picker в Administration и обычных формах;
36 пар находятся в `.screenshots/administration-current/index.html`.
В Configuration перенесены восемь страниц, палитры, отдельный Repository Editor,
навигация и черновики. Apply/Reset текущей страницы не теряют остальные;
Save сохраняет все без закрытия; Cancel учитывает pending edits.
Проверены preview/discard, ошибка localStorage, повторное открытие/reload,
defaults нового поиска/задач, обычный пользователь, native XML scope/conflict,
проверка путей, реальные ZIP/права и previews check-in. Свидетельства и актуальные
QML/controller SHA-256: `.screenshots/configuration-current/index.html`.

Итоговая приёмка: 19 совместных transport/browser-сценариев прошли
в `.screenshots/repository-acceptance-final.log`; семь native/UI-проверок
(общие ресурсы, блокировка Config и исходные check-in/alias guards) —
в `.screenshots/working-panels-native.log`. Последняя проверка Description,
process-контекста и общих ресурсов — `.screenshots/description-final.log`.
Preferences/docks и обе галереи проверены отдельно. Свежие Source/Chromium
снимки Configuration при 1400/900 и Description при 440/720; сборка 0.112.30.
Проверенные временные процессы завершены; пользовательский сервер/ТХ сохранены.

Карта владельцев, defaults и границы вынесены в встроенную EN/RU справку
`configuration`, все её страницы и `appearance`. Browser-дополнения видимы.
Настольные persistent record caches/endpoint presets/DCC/Qt rendering не перенесены;
Enabled/Default и добавление алиасов перенесены. Корень меняется после проверки
готовой копии файлов (пути/SHA-256); сохранение само файлы не переносит.
Для смены корня остановить чекины; после сохранения перезапустить HTTP-маршруты.
Native SDK без явного алиаса сохраняет прежний Naming. Ревизия остаётся
в своём репозитории. Проверены новый алиас, удаление используемого,
отсутствующая/изменённая копия, native get_paths и HTTP-файл после рестарта.
Это границы проверенного browser-блока, а не заявление 100% совпадения всего ТХ.
Пункт 2 завершён в согласованном browser-объёме; Repository Sync/S3 исключены.
Пункт 3 начат с Description: актуальные QML/state, native update, процессы/снапшоты,
черновики, Pin для check-in и общий док. Свежие свидетельства:
`.screenshots/description-current/index.html`. Остальной пункт 3 ещё не завершён.
Мобильная адаптация по-прежнему следует после desktop-панелей.

Для каждого раздела Administration/Configuration требуется одна карта:
актуальный QML и controller ТХ → соответствующий legacy-код TACTIC → экран/
команда Stream → операции и состояния → EN/RU Help → свидетельство проверки.
Уровни готовности различаются: **предусмотрено исходником**, **реализовано**,
**проверено сценарием**, **сверено визуально**. Наличие пункта меню или статьи
справки само по себе не повышает уровень готовности.

Критерий завершения блока: все разделы и связанные окна пройдены; есть свежие
скриншоты ТХ и Stream при одинаковой теме/масштабе/размере, проверены создание,
правка, сохранение, сброс, конфликты, права и восстановление контекста; скрытые
параметры/ограничения описаны в существующей Help. Отчёт содержит доступные
сравнения экранов и оставшиеся согласованные ограничения. Тестовые процессы,
серверы и приватные данные очищаются до отчёта.

### Administration — результат прохода 0.112.28

`tools/capture_handler_reference.py --administration-only` запускает текущий Qt/QML
ТХ на изолированных данных. `test_transport.Transport.test_administration_in_chromium`
снимает действующий Stream на отдельном нативно созданном проекте с реальными
таблицами, схемой, pipeline и XML виджетов. Восемь страниц при 1400×940 и 900×620,
вложенные вкладки и свёрнутая навигация собраны для сравнения в
`.screenshots/administration-current/index.html`. Это renderer исходника и
браузера, а не старые пользовательские скриншоты; количество/имена fixture-записей
могут различаться. Карта QML/controller → native storage/command → Stream →
проверенные сценарии опубликована в существующей EN/RU Help → Administration.

- Общее окно: независимые черновики посещённых разделов, сворачивание 250/56 px,
  отметки правок, блокировка проекта, закрытие с показом незавершённого редактора,
  возврат к исходному workspace; скрытые редакторы не подменяют подписи/toolbar.
- Все разделы: каталоги, tabs, формы и splitter-компоновка по текущему QML;
  Summary с заголовками вне карточек, вертикальный splitter колонок, Item/Access/
  Technical и TH/TACTIC/XML Sidebar, Profile/Account/Groups, Details/Members и scopes
  матрицы. Цвета и шрифты используют общие токены и controls.
- Графы: input/output-порты, предварительная линия, круглый Progress, рамка и
  групповое перемещение, Ctrl/Shift, +/−, стрелки, F/Home/Esc/Ctrl+S; Native XML,
  прямые/M:N-связи и существующая защита записи сохранены. Штатный обработчик
  Progress исправлен в ядре: resolved process больше не заменяется локальным None.
- Проверки: native создание/изменение/удаление, конфликты и потеря ответа, права,
  откат, сторонние XML-атрибуты и повторное открытие; браузерные сценарии разделов,
  связанных форм и независимых черновиков. Тесты используют приватные данные и
  завершают свои серверы/браузеры в teardown/finally.

Полезные дополнительные инструменты Stream остаются видимыми: раскладки, прямое
создание связи, расширенные XML/JSON, фильтры определений и maximize/restore.
Каталог Add node схемы перенесён; дополнительные прямые инструменты расположены
следом. Добавление процесса Workflow использует отдельную страницу имени и сетки
штатных типов с возвратом к выделению. Отличается растеризация шрифта Qt/браузера. SQLite-прогон не заменяет
отдельную приёмку MySQL/PostgreSQL; заданный class path не означает миграцию его
runtime. Полное пиксельное совпадение и весь legacy API не отмечаются готовыми.
Configuration прошёл отдельную приёмку в 0.112.29; следующий крупный блок — рабочие панели.

## Фактическая готовность крупных экранов: сверка 2026-10-09

Эта сводка уточняет границы записей о выполненных отдельных изменениях ниже.
Успешный тест команды, формы или контрола не означает перенос всего экрана.
Проверены текущие исходники Stream и соответствующие QML/справка Handler;
новая визуальная приёмка этих экранов в рамках этой сверки не проводилась.

| Экран / сценарий | Фактическое состояние Stream | Что ещё требуется |
| --- | --- | --- |
| Snapshot Browser | 0.112.31: общий док следует объекту/процессу/задаче/снапшоту, native история и страницы по 50, превью, Fit/Fill, три режима и splitter, Show All/More, точные операции файла и откат FileUndo. Свежие 14 QML/Chromium пар. 0.112.32 завершает metadata member rows sequence/UDIM/UV и обычный доступ к разрешённому владеющему объекту. Форматам только Qt нужны браузерные производные. Подключение TH/DCC, S3/Sync исключены. | Общий контекст выбранного объекта/процесса; выбор контекста, версии и файла; превью и таблица файлов; переключение компоновки, splitter, Fit/Fill, Show all/More; операции с точным файлом и защита от устаревших ответов. |
| Description | Перенесён 0.112.30: настоящий док с native update объектов/снапшотов, локальным текстом процессов, Edit/Save/Discard, ошибкой/повтором, Pin/Unpin для новых check-in форм. Видимый список сохранённых черновиков — дополнение Stream. Native/browser состояния при двух размерах. Черновики в памяти сессии, native update использует последнюю запись; полное совпадение растеризации шрифта не заявлено. | Владелец описания (объект, процесс, снапшот), Edit/Save/Cancel, сохранность черновика при смене выделения и ошибках, Pin/Unpin описания для подготовки check-in. |
| Knowledge Base | 0.112.32: общий док, native проектный каталог/права, дерево/разделы/поиск, оглавление, Visual/Markdown, локальные и серверные черновики, публикация/конфликты, организация, история транзакций, FileCheckin-вложения/библиотека, DeleteCmd, связанные объекты и skey. 16 свежих QML/Chromium пар; SQLite и Chromium проверены. Производственные vendors и физические телефоны остаются вне этого прогона. | Дерево разделов, статьи Markdown, поиск, оглавление, редактор, вложения и их библиотека, история, переходы по ссылкам; чтение/редактирование/публикация по исходным правам. |
| Drop Plate | В 0.112.33 перенесены файловые группы, папки/буфер, фильтры, объект/процесс/контекст, 19 native Matching Templates с полным редактором и передача выбранных файлов в Commit Queue. | Браузерные File handles и относительные пути; локальные абсолютные пути и desktop/DCC исключены. Свежие QML/Chromium и EN/RU Help: раздел чанка 2 ниже. |
| Меню SObject | Есть реальный чекин, preview/clipboard, подтверждённая ревизия, копирование skey/web link, новая вкладка, выделение и Unlink instance. Add files в relation создаёт связанные объекты через native IngestUploadCmd, поддерживает правила и конфликты имён. Проверены Chromium и native rollback. Полный перенос меню не завершён. | Глубокое Duplicate и его сохранённые профили, меню файлов с copy path/image и Delete Whole Tree versionless; проверить все контексты и права. Папки/Watch Folder требуют пока не подключённого desktop. |
| Commit Queue | В 0.112.33 перенесена полная браузерная подготовка/правка операций: описание, native naming/версии/репозиторий/контекст, preview, групповые правки, порядок, дубликаты, отправка выбранных/всех, автоочистка, ошибки/Retry/Cancel/Result unknown и точный Snapshot Browser. Док или общее переносимое окно. | Локальные способы Copy/Move/Inplace требуют desktop-подключения и отключены с пояснением. Восстановление метаданных после reload требует повторно выбрать файлы. Native backend/ACL/rollback и границы проверки: раздел чанка 2 ниже. |
| Сохранение лейаутов | Есть серверные presets и меню Save current layout, но `docks.js` знает Results, Task Manager, Commit Queue и Description; видимые неперенесённые панели и detached-окна отклоняются. | Полный состав перенесённых доков, их позиции/размеры/активные вкладки, доступные сохранение и восстановление; совместимость исходного документа лейаута. Мобильная компоновка не перезаписывает desktop-геометрию. |
| Administration | Обновлено 0.112.28: восемь разделов и вложенные вкладки пройдены, текущий QML/Chromium снят при двух размерах; сохранение/конфликты/права/откат проверены. Независимые черновики, навигация, splitter-компоновка и Add node перенесены; EN/RU карта исходников опубликована. | Полное совпадение каждого пикселя не заявлено: Qt/браузер растеризуют шрифт по-разному; полезные прямые инструменты Stream оставлены видимыми. Проверка конкретных сторонних runtime-классов и новая MySQL/PostgreSQL-приёмка не входят в этот SQLite-прогон. Свежие свидетельства и границы — в разделе результата выше. |

### Исторический план совместимости legacy TACTIC — 2026-10-09

Ниже сохранены история исходных контрактов и промежуточные результаты.
**Этот список не является текущей очередью работ.** Актуальные L01–L12,
исключения и критерии — [в начале документа](#legacy-plan). На 2026-10-19
из 129 методов 127 доступны частично, два исключены; полный паритет не подтверждён.
Прежнее исключение Repository Sync заменено последующим B12: native сценарий
перенесён; отдельную браузерную реализацию не создаём. S3 остаётся исключённым.

1. **API и native Python, по одному контракту.** Первый блок — SQL-конструкторы
   Select/Insert/Update — перенесён и проверен. `@LATEST`/`@CURRENT` активированы
   и проверены через исходные связи snapshots/files и Naming. `@FORMAT`/FormatValue
   и суффикс `format=` подключены к исходному formatter. Для `@VAR` проверен
   фактический контракт исходника: пустой результат без присваивания и выполнения
   вложенных выражений; переменные передаются через `vars`/`$NAME`. Это не готовая
   операция присваивания. 16 сценариев сравнены с исходным ядром, включая Naming;
   неполные аргументы дают SyntaxError вместо исходного IndexError. Исходный
   XML-RPC SDK, серверный Python и откат записи проверены; всего 12 целевых тестов.
   Native virtual SObject и контексты `state`/`date` восстановлены без таблицы в БД:
   исходные метаданные, временные поля и сериализация; сохранение/удаление явно
   отклоняются. 19 сценариев сравнены с исходным ядром, включая даты и Naming;
   исходный SDK, серверный Python, права колонок, вложенные read policies,
   изоляция state и откат проверены. Прошли 17 целевых Windows тестов и реальный
   PostgreSQL. Справка `core_model` доступна в каталоге на EN/RU и из Обзора.
   Контекст `connect` подключён к native SObjectConnection. 26 сценариев сверены
   с исходным ядром: контекст и фильтры, типы/проекты, направления, Naming и Search.
   Отдельно подтверждены исправления исходных mixed-type/id и SQLite EQ ошибок.
   Устранена воспроизведённая утечка кэша после Sudo; вложенные read policies
   не получают назначения из кэша. Прошли 20 целевых Windows тестов и PostgreSQL,
   включая исходный SDK, серверный Python, права, запись/удаление и откат.
   Справка `connections` доступна на EN/RU; смешанный Search и исходная
   промежуточная проекция цепочного Search явно описаны как ограничения.
   Базовый провайдер Site экспортирован из pyasm.security; контекст `site`
   работает в выражениях, Naming и исходном SDK без строки в БД. Исправлены
   отсутствие временной идентичности при пустом code и пропущенный classmethod
   у get_site_data. 37 сценариев сверены с исходником с отдельными ожиданиями
   его ошибок. API явно отказывает в передаче самого провайдера как записи;
   поля читаются через @GET. Именованные сайты и внешние провайдеры ещё не
   перенесены: отказ сохраняет Security/стек и откатывает предшествующие записи.
   Прошли 18 целевых Windows тестов и отдельный PostgreSQL тест. Справка
   `site_context` доступна на EN/RU из каталога и статьи о модели ядра.
   Выражения в значениях add_op_filters восстановлены через исходный Search.eval:
   two/three-part, шаблоны, single, null, списки/pipe, группы и JSON. 30 сценариев
   совпали с реальным исходным ядром. API eval и четыре пути фильтрации используют
   одну временную область проверок вложенных чтений/методов с восстановлением.
   Admin query/fast_query/children/snapshots участвуют в исходном ApiClientCmd;
   пишущие выражения сохраняются при успехе и откатываются при ошибке следующего
   фильтра. Читатель не получает права на вложенные закрытые типы или запись.
   Прошли 30 целевых Windows тестов и PostgreSQL; исходный SDK не изменён.
   Справка `search_filters` добавлена на EN/RU в каталог и статью о модели ядра.
   2026-10-10: clock-фильтры timestamp/datetime/datetime2 включены через
   DatabaseImpl: NOW/CURRENT_TIMESTAMP, SQLite DATETIME с literal-аргументами,
   PostgreSQL now()/generated intervals/precision. Время вычисляет СУБД; SQLite
   нормализует обе стороны до UTC, сохраняя точность колонок. Общий validator
   используется Search и автоматическим process_value SQL-конструкторов.
   Исходные quoted-правила API сохранены: в triple-фильтре NOW специальный,
   CURRENT_TIMESTAMP/DATETIME остаются литералами; date-range требует даты.
   42 сценария проверены с исходным runtime; баги регистра/qualified-колонок,
   offset-сравнения, SQL-подстановок и nullable/type ошибок имеют независимые
   source/native ожидания. Проверка исходного PostgreSQL processor отделена
   от реальной native PostgreSQL. Прошёл 31 целевой Windows тест и PostgreSQL,
   включая исходный SDK, читателя, Select, откат и жизненный цикл tickets.
   Справка `timestamp_filters` на EN/RU доступна из каталога и статей о ядре/фильтрах.
   Все пять новых статей ядра и их ссылки сохранены в frontend/public/help,
   чтобы сборка не возвращала старый каталог; после сборки проверены 52 статьи
   на обоих языках. Поиск справки одинаково нормализует текст и имена методов.
   2026-10-10: Search и owned Select используют общие WHERE/JOIN и один compiler;
   прямые типизированные фильтры, смешанные postfix-группы, JOIN, пагинация,
   SQL-выполнение и копии сохраняют bound-параметры и текущие права. Исходные
   обходы null/retired прямым Select исправлены с независимыми ожиданиями.
   Маркеры в SQL-литералах/комментариях не подставляются; PostgreSQL literal %
   сохраняется во всех путях чтения. Чужой Sql-ресурс, замена таблиц/SQL и
   owned dumps/loads явно отклоняются; обычный Sql остаётся admin-only.
   31 сценарий проверен на исходном runtime. Прошли 76 связанных Windows тестов,
   отдельный тест Columns Editor и реальная PostgreSQL; исходный SDK, откат,
   копирование с повторной проверкой ACL и source-сигнатуры подтверждены.
   Исправлены устаревшие тестовые ожидания half-open диапазонов дат, Command
   ресурсов admin query, исключённого prod namespace и корня файлов Handler.
   Справка search_select добавлена на EN/RU, каталог содержит 53 темы.
   2026-10-10: сериализация owned Select завершена в поддержанной области.
   Исходный JSON сохраняет значения WHERE, порядок групп/JOIN, колонки/aliases,
   aggregate/distinct/quote mode и страницу. Владелец, подключение и права
   не передаются; загрузка заново проверяет текущий Search и его ACL.
   Невалидная загрузка атомарна, успешная сбрасывает кэш объектов;
   метаданные JOIN восстанавливаются даже без исходного join_tables.
   Исправлена исходная потеря проекции с независимыми source/native ожиданиями.
   Прошли 16 сценариев настоящего исходного runtime, 86 связанных Windows
   тестов и изолированная PostgreSQL: исходный SDK, права читателя,
   проекции/JOIN, literal-маркеры, новые bound-фильтры и откат записи.
   Справка search_select обновлена на EN/RU, сборка и рабочий каталог 53 тем
   проверены. Replacement SQL/таблицы, raw-словари, произвольные/межресурсные
   direct JOIN, DISTINCT ON и MySQL по-прежнему не объявлены завершёнными.
   2026-10-10, 0.112.3: get_parent/get_all_children учитывают columns через
   существующий сериализатор, сохраняя служебные ключи. Исходная потеря проекции
   проверена отдельно от правильных ожиданий. Настоящий исходный runtime/SDK,
   серверный Python, retired, два проекта, обычный читатель, вложенные фильтры
   и откат проверены; 23 целевых Windows теста и отдельная PostgreSQL прошли.
   API-справочник и core_model обновлены EN/RU.
   2026-10-10, 0.112.4: get_all_children и query(parent_key=...) используют общий
   instance JOIN для разных endpoint-типов на одном ресурсе. Исправлены исходные
   ошибки обратного поиска и отсутствующей фильтрации родителя; проверены
   разные ключевые колонки, права на промежуточный тип, проекция и откат.
   Прошли 55 связанных Windows тестов, исходный runtime/SDK, серверный Python
   и SQLite/PostgreSQL create/read/remove. API-справочник и core_model — EN/RU.
   Self-instance children и межресурсные JOIN остаются открыты.
   2026-10-10, 0.112.5: пакетный instance-поиск ограничивает JOIN переданными
   ключами, учитывает in/not in и направление; группировка использует ключ
   схемы, а aliases проекции источника не подменяют этот ключ. Права на
   промежуточный тип, пустые/заранее загруженные поиски и rollback проверены.
   20 дополнительных сценариев настоящего исходного runtime, 62 Windows
   теста и отдельная SQLite/PostgreSQL проверка прошли. Справка core_model EN/RU.
   Следующая обнаруженная ошибка — fast helpers get_sobject_codes/ids выбирают
   первый столбец существующей проекции; после JOIN это может быть id вместо code.
   2026-10-10, 0.112.6: эта ошибка исправлена в общем fast extraction для code/ID
   и instance-ключей. Исполняемая копия сохраняет проекцию/aliases, строки JOIN,
   distinct и страницу, но берёт фактическую колонку основного типа. Hooks
   выполняются один раз; права/read-policy проверяются заново, Sudo не даёт
   постоянного права основного типа. 22 сценария исходного runtime, 75 Windows
   тестов и отдельная SQLite/PostgreSQL проверка прошли; справка EN/RU обновлена.
   2026-10-10, 0.112.7: чтение self-instance завершено через общие parent/child
   endpoint paths и aliases таблиц линков/источника. Дети, parent_key, single/list/
   Search-фильтры, карты и Results tree используют один путь. 13 исходных сценариев,
   85 Windows регрессий, отдельные SQLite/PostgreSQL и временный cg.zip прошли;
   справка EN/RU обновлена.
   2026-10-10, 0.112.8: same-type add_instance/get_instances/remove_instance
   используют явные направленные концы и общий Search. Проверены 16 сценариев
   исходного runtime, 91 Windows регрессия, неизменённый SDK/XML-RPC, откат
   insert/delete-триггеров, PostgreSQL и временный cg.zip. Запись пока доступна
   только администраторам по существующему guard ядра в том выпуске.
   2026-10-10, 0.112.9: обычные project-type CRUD и instance записи теперь
   используют права проекта/операции типа/полей/текущей строки и ограниченный
   bound DML. 17 исходных сценариев, 111 Windows проверок, stock SDK/XML-RPC,
   PostgreSQL, journal/index/own-redo, откат и временный cg.zip прошли.
   2026-10-10, 0.112.10: persistent diagnostics обычного пользователя перенесена;
   проверены автор, независимая запись, stock SDK, SQLite/PostgreSQL и откат.
   Исправлены остаточный стек вложенной ошибки и административный контекст Batch.
   Следующий приоритет — ordinary-user StatusLog/Workflow эффекты, затем
   файловые права и оставшиеся параметры транзакционных API.
   Определения/аккаунты и raw SQL не открыты правом проекта; полный API не готов.
   Следующий блок — оставшиеся контракты запросов и связей SObject,
   затем параметры файловых и транзакционных методов
   и публичные Python-импорты. Проверять реальный результат и эффекты
   неизменённого скрипта/клиента, а не число методов.
2. **Административные операции:** изменение типов/ограничений колонок; оставшиеся
   Workflow handlers, listeners и миграции процессов; email и subprocess triggers;
   expression-фильтры прав и отсутствующие режимы аутентификации.
3. **Управление плагинами, шаблонами и расписаниями.** Backend install/export/
   uninstall уже частично работает. Завершить неподдержанные manifest/schema
   варианты, дать отдельный менеджер в UI; перенести persistent scheduler definitions.
4. **Остальные native inputs и декларативные конфиги:** поддержка исходных
   специализированных контролов, действий и inline-состояний через общий renderer.
5. **Базы и внешние ресурсы:** MySQL, оставшиеся DDL/import/export варианты и
   согласованная межбазовая запись. SQLite и PostgreSQL проверять отдельно.
6. **Сквозная приёмка API/админки:** шаблон проекта → данные/связи → задачи/заметки
   → check-in → обновление/удаление/откат, права обычного пользователя и ошибки.
   Рабочий cg_test не заменять временной fixture; Telegram остаётся выключенным.

Последний блок: исходные `@FORMAT` и StringMode `format=` используют общий
`pyasm.common.FormatValue`: scalar/list/empty, fps таймкода, неизвестные форматы
без выдуманных aliases, настройки проекта DATE/DATETIME и Naming. 77 одинаковых
вызовов сверены с настоящим legacy runtime; семь исправлений исходных ошибок
(locale.format в Python 3, boolean/DICT, отсутствующие аргументы) проверены
независимо. Прошли 20 целевых Windows-тестов и отдельный PostgreSQL-тест:
реальные числовые/boolean поля, исходный SDK eval/Python, прежний SDK сценарий,
вложенная политика чтения и rollback. Валюты и текстовые даты сравниваются при
одинаковых тестовых локалях. Рабочие запросы не меняют process-wide locale;
для денежных форматов требуется настроенная monetary locale. Её bootstrap и
полный паритет локалей остаются отдельным разрывом, включая минимальный Linux
образ. Полную готовность FormatValue/API этим не объявляем. Временный сервер
завершён, отдельная PostgreSQL БД удалена; cg_test не изменён.

Предыдущий блок: `@LATEST`/`@CURRENT` возвращают исходные пути файлов через
связи SObject → Snapshot → File: контексты, latest/current flags, несколько
объектов, asset/web roots, single/empty и Naming. 20 сценариев сверены с настоящим
legacy runtime; два из них независимо подтверждают исправленную исходную ошибку
с апострофом в контексте. Неизменённый XML-RPC SDK проверяет eval и серверный
Python. Всего 16 целевых тестов Windows и отдельный PostgreSQL-тест прошли:
права исходного объекта, вложенная политика чтения, обновление кэша и rollback.
Временный сервер завершён, отдельная PostgreSQL БД удалена; cg_test не изменён.
Смешанные типы/связи родителей без code и остальные выражения этим блоком не
закрыты. Общая готовность API остаётся `false`.

Предыдущий блок: исходный Select с фильтрами/JOIN/group/order/paging/count,
исполнение Insert/Update, получение ID и поддержка объектов-конструкторов в Sql.
25 проверок Windows на временных данных и отдельная проверка PostgreSQL прошли;
оригинальный runtime и неизменённый XML-RPC SDK использованы. SQLite full-text
остаётся явным ограничением, PostgreSQL full-text проверен. В общей старой
ReadParity остаются три несовпадения date_on/date_between/date_open_range:
воспроизводятся с прежним Select, проверка текущих UTC timestamp filters проходит.
Полную готовность API, всех SQL builders или админки этим не объявляем.
Отдельный Select работает самостоятельно; прямое выполнение/сериализация Select
из Search и новые filter/join/paging-вызовы на нём пока явно отклоняются:
параметризованные фильтры и ACL Search компилируются отдельным существующим путём.
Их нельзя незаметно отбросить при использовании перенесённого SQL-конструктора.

### Актуальный план завершения UI — 2026-10-09

Уточнение пользователя после этой сверки: перед следующими экранами и дальнейшей
мобильной адаптацией завершить desktop-диалоги, контекстное меню объектов и меню
управления доками. Грип в Results отсутствует; вход в управление — существующие
три точки справа от поиска из текущего SearchWorkspaceView.qml.

Последний проверенный блок: глубокое Duplicate — пять страниц текущего Handler,
связи/прямые дети, текущие снапшоты, задачи, ветки заметок и вложения; сохранённые
выборы и Quick Duplicate. Production build, native/Chromium проверки,
регрессии relation Add files и TH image check-in прошли на временных SQLite-проектах.
Это не означает 100% паритета экрана, API или поставки. Подробности и ограничения
— в записях «relation Add files» и «глубокое Duplicate» ниже.

1. **Текущий этап: закончить desktop-меню, диалоги и управление доками.**
   Relation ingest («Add files») перенесён для браузерных файлов и проверен.
   Глубокое Duplicate и сохранение выборов также проверены. Следующий блок — меню
   точного файла с copy path/image, затем versionless Delete
   Whole Tree с исходным подтверждением. Проверить меню объекта/процесса/снапшота/
   файла/связи и выделения, все окна на общих controls, размеры/типографику,
   drag/maximize/close/dirty/error, меню доков в исходном месте. Не объявлять
   завершённым весь этап по успешному тесту одного меню.
2. **Snapshot Browser целиком.** Первым разобрать путь выделение → объект/процесс
   → снапшот → файл. Использовать `SnapshotBrowser.qml`, его Toolbar/OptionsMenu,
   `controllers/snapshot_details.py`, `workspace_models/state_snapshot_state.py`
   и связанные модели/запросы, а не переименовать FilePreview в новый экран.
3. **Description** с исходными черновиками и закреплением описания для check-in.
4. **Drop Plate и полная Commit Queue** как один сквозной сценарий подготовки,
   проверки, отправки и последующего появления версии в Snapshot Browser.
5. **Knowledge Base** со связанными редакторами, вложениями, историей и правами.
6. **Полное сохранение/восстановление лейаутов** с добавленными доками. Регистрацию
   каждого нового дока и его участие в сохранении делать в его этапе;
   здесь проверить весь набор совместно и исходные presets ТХ.
7. **Administration по одному разделу:** Search Types, Project schema, Workflow,
   Columns Editor, Sidebar Editor, Users, Groups, Access rules.
8. **Завершить мобильную адаптацию после desktop-подгонки.** Компактные items,
   Tasks/Inspector/Notes/Messages и файлы; скрыть лишние кнопки, рамки и fast-menu;
   явно ограничить редакторы, которые не помещаются. Смена ширины сохраняет
   черновики и desktop-настройки. Уже работающий мобильный UI не удалять.

API/совместимость проверять в каждом этапе, используя исходные классы и команды
TACTIC. Отдельная итоговая проверка: полный сквозной cg_test с шаблоном/связями/
тасками/заметками/файлами, Handler XML-RPC, PostgreSQL, целевые браузеры, запуск
BAT и завершение воркеров. Ранее найденную нестабильность расширенного
workspace_tabs проверить после исправления повторного открытия Administration;
успех project_navigation не заменяет этот сценарий. Telegram в cg_test остаётся
отключённым. Repository Sync и шаблоны синка исключены; TH/DCC-подключение для
браузерных локальных операций на текущем этапе не добавлять. Полезные дополнения
Stream сохранять доступными опциями.

Перед каждым этапом — перечень исходных операций, состояний и зависимостей.
Закрывать этап только после сквозного сценария на тестовом проекте, проверок
ошибок/прав/смены контекста и сравнения свежих снимков ТХ и Stream при одинаковых
теме, масштабе и размере. Дополнительно проверить доступное мобильное поведение,
не переводя этап в мобильный редизайн до desktop-приёмки. Проценты по
числу компонентов, импортов или пройденных тестов не использовать.

Согласованные исключения сохраняются: Repository Sync целиком; подключение к
локальному TH/DCC пока не входит в веб-этап. Это не исключает обычные серверные
check-in/check-out, upload/download, снапшоты и файловые операции TACTIC.

## Компоненты UI по системе Handler

Основа — `D:/code/th_codex/docs/ui_component_policy.md` и
`ui_component_map.md`. Переносим разделение ответственности и поведение
компонентов; QML остаётся образцом, реализация использует Vue и браузер.

| Слой | Размещение | Ответственность |
| --- | --- | --- |
| Общие controls | `frontend/src/controls` | Ввод, кнопки, иконки и строки настроек; props/model/events, без RPC и предметных данных |
| Предметные компоненты | Рядом с экраном в `features/<раздел>` | Представление данных раздела, события пользователя; без собственных запросов и глобальной навигации |
| Экраны | `features/configuration`, `administration`, `objects`, `interface`, `documentation` | Композиция, запросы, черновики и ошибки; один владелец состояния каждой операции |
| Хост приложения | `App.vue`, `main.js` | Размещение, открытие/закрытие окон, возврат в workspace |

Уже вынесены AppIcon, AppSelect, AppSwitch, SettingRow. Добавлен AppButton;
им пользуются шапка Configuration и операции Naming. Остальные существующие
кнопки и обязанности App.vue ещё требуют последовательного перевода при
работе с соответствующими экранами; перемещение файлов само по себе не
означает завершение этого перевода. Пустых папок/контроллеров «на будущее» нет.

| Handler control | Vue-компонент / текущая граница |
| --- | --- |
| MaterialIcon | `controls/AppIcon.vue`: общие semantic names и официальные наборы из Appearance |
| Switch | `controls/AppSwitch.vue`: общий model, нативный ввод с клавиатуры/тач и disabled |
| ColorInputWdg | `controls/AppColorInput.vue`: нативный picker и текст одного значения; пустое/нестандартное значение сохраняется текстом |
| ComboBox | `controls/AppSelect.vue`: нативный select, общие подпись, options и оформление |
| SettingsRow | `controls/SettingRow.vue`: название, пояснение, control slot, адаптивная строка |
| Button / CompactIconButton | `controls/AppButton.vue`: label/icon, iconOnly, highlighted/destructive; нативный button, события, type, disabled и ARIA |
| ColorField | `controls/AppColorInput.vue`: общий picker/text для форм объектов и Details SearchType; Reset — AppButton |
| ImagePicker | `controls/ImagePicker.vue`: выбранный File, текущий URL / инициалы, проверка изображения и Undo; не вызывает API |
| PythonSyntaxHighlighter | `controls/CodeBlock.vue` и `pythonSyntax.js`: безопасный вывод Python, общий tokenizer и syntax-роли из Theme.qml Handler; без RPC. Эти же роли и tokenizer использовать в редакторе скриптов |
| SectionTabRail | `controls/SectionTabRail.vue`: только открытые разделы; раскрытие названия поверх workspace, закрытие, reorder мышью и через меню на touch |
| SearchWorkspaceView / SearchTabs | `controls/WorkspaceTabs.vue`: независимые поиски внутри раздела, переключение, добавление, закрытие, reorder и восстановление из истории |
| NavigationDrawer / SidebarTreeRow | `features/workspace/NavigationTree.vue`: папки, вложенные links, разделители, поиск с родительской веткой, keyboard/touch; метаданные из штатного SidebarConfig |

Workspace повторяет два уровня Handler (`SectionTabRail.qml`, `SearchWorkspaceView.qml`,
`controllers/navigation.py`, `search_tabs.py`). Навигация открывается поверх рабочей
области ниже app bar; шапка остаётся доступной. Клик на уже открытом разделе
возвращает его вкладки. Последняя поисковая вкладка раздела не закрывается;
закрытие самого раздела удаляет его рабочее состояние. Каждый проект имеет
собственный набор открытых разделов и поисков.

`App.vue` владеет вкладками и запросами. `features/workspace/workspace.js` сохраняет
параметры поисков и порядок вкладок отдельно для пользователя в localStorage.
Результаты, выделение, viewport и экземпляры ConfiguredView сохраняются в памяти
при переключениях, включая временно закрытые поиски. После перезапуска параметры
восстанавливаются, а записи заново читаются с сервера; результаты и tickets
не входят в сохранённое состояние workspace. Возврат из Configuration/Administration
сохраняет исходный поиск. Полный перенос всех экранов и видов результатов Handler
этим не объявляется: дерево/карточки и прочие виды результатов — отдельные этапы.

Навигация проекта читается отдельным `/admin/navigation` через исходный
`tactic.core.sidebar_config.SidebarConfig`. При наличии `tactic_handler` он
приоритетен, даже если пуст; иначе используется `project_view`. Папки раскрывают
именованный view или inline children. Сервер применяет исходные link permissions,
is_visible и личные defaults; скрытая по правам или явно пустая навигация не
подменяется реестром типов. Если определений нет, остаётся браузер SearchTypes.
Циклы, глубина более восьми views и более 256 пунктов дают явную ошибку.

Кнопка Edit navigation открывает общий WidgetConfiguration в режиме SideBarWdg:
исходные источники/наследование, Check XML, diff, предпросмотр тем же NavigationTree
и Save с ревизией, native Command/journal и блокировкой. Preview ничего не записывает.
Проверка полного разрешённого дерева выполняется и при Save; циклический XML
не публикуется. После сохранения дерево, названия и иконки открытых разделов
обновляются без пересборки клиента. Icon Manager имена FAS_/FAR_/MDI_ разрешаются
общим AppIcon через официальные charmaps соответствующих поставленных шрифтов.

Полный визуальный Sidebar Editor Handler пока не перенесён: его каталог,
перестановка/создание элементов, групповые visibility controls, saved searches,
layout presets и script shelves остаются отдельным блоком. Такие link options
не игнорируются при открытии: неподдерживаемые пункты недоступны в renderer.
Этот этап переносит runtime дерева и общий XML authoring, а не объявляет
готовность полного SidebarEditorView.

Справочник `/docs` использует общие AppButton/AppSelect/SettingRow, цвета и
размеры MD3. Описание метода и сигнатура видны сразу; исходный docstring доступен
перед формой запроса. Ответ занимает всю ширину блока и прокручивается внутри
высокого окна; его высоту можно менять. Собственные пояснения всех 129 методов
на EN/RU находятся в `compatibility/api_help.json`; исходные docstring остаются
в `api_manifest.json`. Статус переноса отображается отдельно от справки:
наличие описания не означает полной реализации метода.

AppButton по умолчанию `type="button"`; submit задаётся явно. label — исходная
строка перевода, icon — семантическое имя; iconOnly сохраняет доступное имя и
подсказку. disabled, click и остальные атрибуты проходят на нативный button.
Сложное содержимое задаётся slot. Drag, badges и другие возможности
CompactIconButton этим этапом не перенесены; новых локальных вариантов не
добавлять, необходимое поведение расширяет общий control.

До создания нового виджета проверять существующие controls и компоненты
Handler. Один semantic control имеет одну реализацию во всех экранах.
Appearance/theme/i18n остаются общими владельцами шрифтов, цветов, размеров,
иконок, motion и переводов. Общие popup/dialog/menu и остальные controls
переносятся целиком по требуемым сценариям, а не копированием на каждый экран.
В браузере сохраняем нативные focus, keyboard, touch activation и scroll;
Qt-обработчики не копируем поверх уже работающих браузерных событий.
Минимальная зона нажатия — 44 px; новые виды карточек/таблиц пока не добавляем.

WidgetConfig/View по-прежнему задаёт интерфейс через независимое описание;
`features/interface/ConfiguredView.vue` — существующий Vue-renderer. Библиотека
controls обслуживает этот renderer и штатные экраны, а не заменяет XML новым
клиентским конфигом. Backend и правила TACTIC не дублируются во Vue.
Перечисленные границы — правило дальнейшего переноса; полная библиотека
controls Handler и все его экраны пока не перенесены.

## Основное требование

Уточнение пользователя 2026-10-07: UI из Handler переносится целиком по
функционалу и поведению, с адаптацией под Vue и touch. Базовая форма или
навигация не считаются завершённым переносом экрана. Сначала изучаются исходные
QML, контроллеры и серверные процедуры, затем закрывается весь перечень сценариев.
Ранее согласованные исключения (Drupal, лицензирование, древний prod и другие)
остаются исключениями. Минимализм реализации не сокращает объём функционала.

Уточнение пользователя 2026-10-07: Repository Sync из Handler не переносится.
Исключены окно и очередь синхронизации, шаблоны/presets и их редактор, настройки,
автоматический синк и специализированные серверные процедуры. Это исключение
из требования переносить экраны целиком; эту подсистему не учитывать как
незавершённую работу UI. Общие snapshots/check-in/check-out/upload/download,
настройки путей repository и обычная серверная queue сохраняют свои задачи.

Текущий Search Types незавершён. Критерий его переноса включает:

- Каталог с названием, таблицей, превью, цветом, признаками link/M:N и связями;
  поиск, Only current project по фактической БД и Hide config types.
- Summary: total/active/retired, поля, pipelines/processes, сведения о размещении,
  прямые и унаследованные связи, карта связей с zoom/pan/reset и touch controls.
- Workflow: связанные pipelines, общие/проектные данные, создание и открытие
  рабочего редактора процессов; не переход к сырой таблице pipeline.
- Naming: полный редактор правил в контексте выбранного типа и проверки
  существующим движком, включая его состояния и переходы.
- Details: название, описание, выбор/сброс цвета и preview с реальным check-in
  и отображением результата; pipeline option при создании.
- Fields: существующие поля и их свойства, новые поля в черновике, отмена
  добавлений, удаление существующих столбцов с исходными запретами и подтверждением.
- Создание: Details / Fields / Review, проверка этапов, стандартные и добавленные
  поля, preview, pipeline option и реальные эффекты штатной команды создания.
- Общие Create/Reload/Discard/Save/Help, блокировки и защита черновиков, конфликты
  ревизий, ошибки отсутствующей таблицы, завершение preview-загрузки и обновление.

Источник перечня — AdminSearchTypesView.qml, SearchTypeSummary,
SearchTypeWorkflows, редактор полей/preview, SearchTypesEditor и naming controller
Handler. Перечень дополняется по зависимостям исходников; снимок экрана не
ограничивает функционал только видимыми на нём элементами. Результаты переноса
Search Types и последующих Users/Groups описаны в отдельных разделах ниже.

TACTIC перестраивается через самого себя. Widget configs — определения
интерфейса: пользователь изменяет их в TACTIC, сохраняет и получает изменённые
таблицы, формы, панели, навигацию и действия без пересборки Vue.

Основное представление — Vue. Конфиги, проекты, права, запросы и команды
не должны зависеть от версии Vue или выбора другого frontend.

## Ориентир главного экрана: Tactic Handler

Уточнение пользователя 2026-10-07: расположение и поведение основных controls
сверять с экраном Handler и `thlib/ui/qml/Main.qml`, а не только с общей темой.
Слева в верхней панели — menu/close для навигации, затем кнопка выбора проекта
с аватаром, названием и стрелкой, открывающая список проектов. Справа —
компактные иконки системной активности, подключения, очереди отправки,
ленты активности, темы, меню ⋮ и аватар пользователя. Конфиг открывается
из ⋮, пользовательские действия — из аватара. Переносить назначение действий
вместе с иконками; состав сверять с работающими возможностями Stream.

Левая навигация имеет заголовок, редактирование, закрытие и собственный scroll;
элементы — иконка и читаемое название. Навигация открывается поверх рабочей
области на всех размерах экрана, под верхней панелью, без изменения ширины
результатов. Область работы без открытого SearchType показывает пустое состояние
с подсказкой выбора. Второстепенные действия могут уходить в меню; выбор проекта,
конфиг и основные операции остаются доступны обычным тапом с зонами от 44 px.
Это целевой ориентир; перечисление не означает, что все панели уже перенесены.

Главный экран: одна строка поиска, кнопка фильтров и меню действий ⋮.
Поиск через Enter проверяет текстовые name/title/code/description/search_type/
display_name/login/email одним OR-фильтром штатного query; фильтр конкретного
поля добавляется через AND. Сортировка, обновление, исходный XML и выбор
configured view/database fields находятся в ⋮. Операции выделения также
собраны в отдельном ⋮. Футер содержит диапазон, номер страницы, стрелки и
кнопку создания «+», когда операция разрешена. Результаты занимают оставшуюся
высоту и прокручиваются независимо от оболочки, в том числе touch-жестом.
Узкий desktop rail открывает доступные проектные представления, не является
системой вкладок. Новые виды items/cards, parser/autocomplete/tags поиска и
Script Shelf Handler в эту правку не входят; текущая таблица сохранена.

Реализован первый проход shell: иконки из официальных шрифтов верхних действий, выбор проекта
с аватаром через native customizable select, Edit/Close навигации, круглые
иконки её записей и иконки кнопок основных операций. System logs, Background
queue и Change history открывают существующие SearchTypes; это не отдельные
панели notifications/commit queue Handler. Edit navigation открывает штатный
список widget configs с фильтром SideBarWdg для редактирования через общие формы.
Меню закрываются при клике снаружи и Escape; Escape открытого native picker
закрывает сначала picker. На узком экране второстепенные действия находятся
в ⋮. Sidebar/drawer и picker имеют открытие/закрытие с motion, меню — плавное
появление, кнопки — feedback при нажатии. Длительности 140–280 ms задаются
общими theme tokens; prefers-reduced-motion отключает движение в обеих темах.
Сборка и адресная Chromium-проверка прошли, включая реальный touch 360 px.

## Один источник конфигурации

Оформление приложения следует ConfigurationAppearancePage Handler: стиль,
режим, палитры для каждой темы, язык, официальный набор иконок и отдельные
настройки анимаций. Configuration объединяет Appearance и Server configuration.
Локальные UI-предпочтения хранит appearance.js; серверный XML остаётся источником
настроек backend. AppIcon разрешает имена штатных действий через глифы тех же
шрифтов Handler; custom SVG для них не используются. При добавлении действия
дополнить общий icons.js именами/кодами из официальных charmaps, без рисунков.

Конфиг использует одну навигацию разделов слева и общий лейаут настроек справа,
как ConfigurationView Handler; у серверных разделов нет второй вложенной
навигации. SettingRow задаёт название, пояснение, разделитель и положение
контрола для всех настроек. AppSwitch — единственный переключатель состояния,
AppSelect — общий выбор значения в настройках. AppearanceSettings используется
в полном конфиге и быстром меню, сохраняя одного владельца appearance.js.
Булевы серверные значения отображаются AppSwitch, с отдельным действием
возврата к default; пустое значение сохраняет исходную семантику XML.
На узком экране разделы находятся над настройками, строки перестраиваются;
переключатель имеет область нажатия 44 px независимо от размера дорожки.

Сохраняются исходные XML, `config/widget_config`, имена элементов, class paths,
views и правила `WidgetConfig`/`WidgetConfigView`. Определения из плагинов и
пользовательские переопределения участвуют в исходном порядке разрешения.

Сервер разрешает конфиг в контексте проекта и пользователя. Современный
renderer получает обычные данные: элементы, типы отображения, параметры,
вложенность и определения действий. Это описание не содержит Vue компонентов,
сгенерированных Vue templates или зависимостей от внутренних API Vue.
Точную схему ответа следует определить на первом переносимом сквозном view,
используя уже существующие методы чтения метаданных, без универсального движка
или второй системы конфигов.

Последующее уточнение пользователя: если клиентам достаточно описания,
генерацию HTML можно исключить, а работу с оригинальным сервером выбирать
отдельным режимом клиента. Это будет явным исключением из совместимости HTML
API, не подменой их результата JSON. Перенос renderer не является обязательной
зависимостью работ над ядром и современным UI.

Статическая проверка текущего Handler: прямые вызовы `get_widget` найдены
только в поставляемом SDK, рабочие вызовы `get_column_widgets` не найдены.
Однако `query_EditWdg` создаёт исходный `tactic.ui.panel.EditWdg`, вызывает
`explicit_display()`/`get_widgets()` и извлекает данные для четырёх UI путей:
редактор объекта, дублирование, настройка колонок и каталог полей задач.
Эту семантику предстоит сохранить через разрешение конфигов/метаданные;
отсутствие прямых HTML API вызовов не означает отсутствие зависимостей от
классов виджетов. Handler в рамках этой проверки не изменялся и его полный
runtime не проверялся.

Vue сопоставляет типы отображения с компонентами. Изменение поддерживаемых
настроек и композиции меняет интерфейс во время работы. Сохранение конфигов
обновляет соответствующие представления и их кэши; для нескольких workers
нужна согласованная актуализация, а не только локальное сбрасывание кэша.

Действия обращаются к существующим API/Command. Сервер сохраняет проверки
прав, транзакции, триггеры и обработку ошибок. Редактирование конфигов через
сам TACTIC должно использовать эти же пути записи.

## Транспорт RPC и журналирование

JSON `/admin/rpc` и XML-RPC `/tactic/{project}/Api/` используют общий
API-dispatcher и исходный блок логирования TACTIC. Парная HTTP-регрессия
проверяет методы, positional/kwargs, ошибки, скрытие секретов в аргументах,
уникальные request_id и отсутствие дублирующих блоков. Другие HTTP endpoints
не считаются вызовами `/admin/rpc`.

С 2026-10-15 ТХ сохраняет `rpc_transport` отдельно в каждом серверном пресете:
`xmlrpc` по умолчанию для Legacy/Stream либо `json` для Stream. Настройка доступна
на странице сервера и в редакторе пресетов, тест подключения использует черновик.
Вход и рабочие вызовы идут через выбранный SDK transport. JSON `/admin/rpc`
принимает необязательный codec `tactic-sdk-v1` для бинарных данных, datetime
и литеральных словарей с зарезервированным ключом; обычный браузерный контракт
не меняется. Ответ после завершённой записи, который нельзя сериализовать,
даёт серверную ошибку; транспорт не повторяет запись и не переключается сам.
Браузер ТС не имеет выбора транспорта подключения к Legacy: это настройка ТХ.

## Два формата представления

`get_widget(ticket, class_name, args={}, values={}, libraries={}, interaction={})`
сохраняет исходный контракт: HTML строка. `get_column_widgets(ticket,
search_type, search_keys, element_name)` сохраняет вложенные списки HTML.
Совпадение формы результата без исполнения исходного поведения недостаточно.

Структурированное описание для Vue получает отдельный API. Нельзя менять
ответы старых методов на JSON или добавлять в них обязательный параметр режима.
Оба пути используют общие конфиги, предметные объекты и команды.

Для старых Python виджетов, генерирующих HTML и JS, нужен выделенный renderer
совместимости с исходными зависимостями и правилами доступа. Его код не должен
попадать в обычный путь Vue. Режим выбирается явно; готовность каждого виджета
проверяется по его исходному поведению. Пока зависимости не перенесены,
сохраняется явная ошибка, а не успешный пустой результат.

В Vue совместимое представление подключается в одном выделенном компоненте.
Изоляцию старого JS (включая возможность iframe) надо проверить на реальных
виджетах: обращения к `parent`, `spt`, DOM и навигации могут требовать адаптации.
Простая вставка HTML через `v-html` не обеспечивает исполнение этих контрактов.
Переключение представления не меняет данные или формат сохранённых конфигов.

## Границы динамической настройки

Композиция и настройки уже поддерживаемых кирпичиков не требуют сборки.
Совершенно новый тип виджета может требовать нового кода. Для таких типов
предстоит определить подключение frontend ресурсов плагина во время работы;
произвольный старый JS автоматически Vue компонентом не становится.

При обновлении Vue может потребоваться адаптация renderer и его компонентов.
Конфиги проектов, плагины с декларативными настройками и предметная логика
не должны переписываться из-за смены версии frontend. Версия описания UI
обновляется независимо от версии Vue; новые renderers используют тот же контракт.

## Порядок переноса

1. Завершать зависимости ядра и API, сохраняя исходные конфиги и class paths.
2. Перенести один сквозной view: разрешение конфига, данные, Vue отображение,
   действие, изменение конфига из UI и обновление без сборки.
3. Проверить тот же view через старые widget API и реальный клиент.
4. Расширять каталог виджетов и возможности плагинов по исходным контрактам.

В 0.94 перенесены исходные creator definition/table/edit и sidebar configs.
Админский `POST /admin/interface` возвращает schema_version=1, project,
search_type, columns и table/navigation: view, layout, attributes, configured,
elements (name/title/attributes/display/action). Handler/options берутся из
исходных конфигов; renderer-inferred defaults и классы renderer не запускаются.
Пустой view сохраняется; неизвестный именованный view отклоняется. Vue использует
обычные колонки, порядок и заголовки, плоские LinkWdg/ViewPanelWdg ссылки и чтение
объекта. Refresh перечитывает конфиги, изменение XML не требует сборки. Режим
полей БД сохраняет прежний доступ обычных пользователей с выданными правами.

HTML renderer, произвольные классы, форматирование, config actions, вложенные
секции sidebar и формы ещё не реализованы. Неподдержанные widgets/layouts видны
как недоступные; они не исполняются и не заменяются успешным пустым ответом.
Редактор XML в UI, согласованное применение ревизий и API AI/MCP ещё предстоят.
Проверки и команды текущего этапа — README 0.94.

В 0.95 добавлена серверная подготовка базовых форм исходным `EditWdg`:
приоритеты edit/insert/именованных views, edit_definition, XML overrides,
порядок, заголовки, описания, ignore/edit flags, parent fields и defaults.
`TextWdg`, `TextAreaWdg`, `CheckboxWdg`, `SelectWdg` предоставляют данные;
HTML методы остаются исключёнными. `explicit_display` у headless EditWdg
подготавливает inputs для существующей `query_EditWdg` Handler.

Админский `POST /admin/form` принимает ticket/project/search_type и необязательные
view/search_key/default. Возвращает schema_version=1, project/search_type/view,
search_key/mode/input_prefix/element_names/skipped и fields: name/title/class_name,
values/options/attributes/action, labels/choices для SelectWdg. Это описание
формы, не замена HTML/XML-RPC API. Значения отображения и select queries/TSQL
разрешаются сервером; SQL/бизнес-логику Vue дублировать не должен.
Сохранение выполняется исходными EditCmd/EditMultipleCmd через существующий
execute_cmd с args/values и общими Command/Transaction/SObject/Trigger.

Новый endpoint admin-only; общий business-write слой пока также требует admin.
Число перенесённых inputs/actions ограничено: календарь, загрузка, task/process/
pipeline inputs, кастомные layouts/HTML/JS ещё не готовы. Неизвестные классы и
типы отклоняются. Renderer forms, config editor и preview в Vue — следующий блок.
Неизменённая процедура Handler проверена на базовой именованной форме через
XML-RPC; это не проверка всего GUI Handler. Команды/границы — README 0.95.

## API для AI-помощника

Дополнение пользователя от 2026-10-06. Ниже — целевой контракт и обязательный
план реализации; описанные новые операции пока не являются доступными endpoints.
Критерий готовности этого дополнения ещё не выполнен.

### Общее ядро, клиенты и полномочия

AI получает контекст и предлагает изменения через операции существующего
headless TACTIC. Чтение использует Search/SObject и Security, изменения —
предметные классы и Command с обычными транзакциями, триггерами и журналом.
XML-RPC Handler сохраняет методы, аргументы, результаты и авторизацию.
Новые операции получают отдельный версионируемый контракт; не меняют смысл
старых методов. Его DTO и бизнес-правила одинаковы для SQLite/PostgreSQL,
локального/серверного подключения и браузера/Electron.

Подключение модели — заменяемый адаптер вне ядра: он принимает разрешённый
контекст, возвращает предложенные операции и использует их опубликованные
схемы. Конкретный provider/SDK не импортируется в Search/SObject/Command.
Внешний AI подключается через тонкий MCP-адаптер этих же операций, схем и
ошибок. MCP не реализует второй редактор, исполнитель или систему прав.
Прямые функции и уже существующие классы; отдельный универсальный agent engine
или иерархия provider-классов этому контракту не нужны.

Каждый запрос выполняется от имени пользователя. Сервер отдельно проверяет
чтение, изменение, тестовое исполнение, активацию и применение. Доступ к
проекту не означает доступ ко всем его объектам, исходникам и настройкам.
Выборка фильтруется по правам на объекты и поля до сериализации, включая
diff, историю, разрешённое наследование, примеры и документацию. Секреты и
закрытый исходный код не включаются в контекст. Переданный frontend идентификатор
выбранного объекта/виджета повторно проверяется сервером.

Возможность автоматического применения задаётся выданными серверными
полномочиями: какие операции/проекты/ресурсы разрешены, срок действия и
ограничения. Ответ модели или клиентский `auto_apply=true` не выдаёт права.
При необходимости подтверждается конкретный подготовленный diff;
изменённый после подтверждения проект требует новой проверки/подтверждения.
Контекст и текст скриптов — данные для модели, а не источник полномочий.

### Контекст и каталог

`context.get` принимает проект, выбранные разделы, фильтры и ограничение
размера/пагинацию. Возвращает только запрошенное и доступное пользователю:

- Проекты, SearchTypes, поля, связи, pipelines и доступные операции.
- Widget catalog: стабильный type ID, исходный class path, schema свойств,
  события/схемы их аргументов, разрешённые дочерние типы и примеры.
- XML источники, их ревизии и порядок наследования; разрешённое представление
  с происхождением элементов/параметров. `WidgetConfigView.get_xml()` возвращает
  только первый XML: это нельзя выдавать за полностью разрешённый конфиг.
- Разрешённые скрипты, их входы/выходы, ревизии и привязки; правила нейминга.
- Схемы/документацию API, текущие ограничения совместимости и примеры вызовов.
- Контекст открытого UI: SearchType, view, выбранные widget IDs/search keys,
  фильтры, язык и тему. Его сообщает frontend; сервер проверяет ссылки и права.

Каталог различает известный class path, поддержку серверных метаданных и
поддержку Vue-renderer. Неперенесённый виджет нельзя объявлять доступным
лишь потому, что его имя есть в исходном словаре WidgetClassHandler.

### Группы операций

Имена ниже — проект контракта. Итоговые JSON Schema каждого запроса/ответа,
ошибки и примеры публикуются из одной серверной спецификации для HTTP и MCP.
Версия контракта независима от версии Vue; discovery возвращает только
доступные операции и фактически реализованные возможности.

| Операция | Основные аргументы | Результат |
| --- | --- | --- |
| `context.get` | `project`, `sections[]`, filters, pagination, optional UI context | Выбранные разрешённые разделы, ревизии, pagination |
| `widgets.describe` | `project`, optional `types[]` | Типы, schemas свойств/событий, вложенность, примеры, renderer support |
| `layouts.get` | `project`, `search_type`, `view`, optional login scope | Исходные XML и ревизии, разрешённое описание и provenance |
| `layouts.prepare` | target, `xml`, `base_revision`, `idempotency_key` | Draft, diff, ошибки и затрагиваемые ресурсы |
| `layouts.preview` | `draft_id`, UI context, bounded sample search keys | Проверенное описание для того же Vue-renderer и preview token |
| `scripts.get` | `project`, path/key, revision | Исходник, input/output schemas, привязки, ревизия |
| `scripts.prepare` | target, source, input/output schemas, `base_revision`, `idempotency_key` | Draft кода без исполнения и активации |
| `scripts.test` | `draft_id`, test dataset, inputs, bounded timeout | Test run ID; ограниченное окружение, статус, результат и журнал |
| `scripts.test_result` | `run_id` | Статус, output, stdout/stderr, traceback с исходными строками, duration/limits |
| `scripts.activate` | key, `base_revision`, successful `run_id`, bindings, `idempotency_key` | Проверенная активация/привязки, новая ревизия |
| `naming.get` | `project`, rule key/filter | Исходные правила и ревизии |
| `naming.prepare` | target, rule fields, `base_revision`, `idempotency_key` | Draft исходного Naming, diff и проверка полей |
| `naming.evaluate` | `draft_id`/rule revision, search keys, snapshot/file context, date/extension/parameters | Имена/пути, trace разрешения, коллизии, ограничения проверки |
| `schema.prepare` | project, typed SearchType/field/relation changes, base revisions, idempotency key | План штатных команд, diff и затрагиваемые определения/объекты |
| `processes.prepare` | project, pipeline/automation changes, base revisions, idempotency key | Проверенный план штатных команд и привязок |
| `changes.validate` | `draft_id` | Ошибки, предупреждения, зависимости/ревизии, validation token |
| `changes.apply` | `draft_id`, validation/preview tokens, `idempotency_key` | Сохранённые ресурсы, новые ревизии, состояние применения и journal reference |
| `revisions.get` | authorized target, pagination/revision | История, автор, diff/исходник, привязанные проверки |
| `api.describe` | optional `operations[]` | Версия, JSON Schema аргументов/ответов, ошибки и примеры |

XML остаётся в `config/widget_config`; код — в `config/custom_script`
или действующем системном scope; нейминг — в `config/naming`.
Не заводим параллельные AI Layout/Script/Naming модели. История и draft
содержат ревизии/предложения этих ресурсов; применённые данные читает
обычный TACTIC. Schema/process операции используют действующие команды
создания SearchTypes, полей, связей и pipelines. Неперенесённые возможности
отказывают явно до изменения данных.

### Подготовка, проверка, предпросмотр, применение

Этапы отдельные. Подготовка может сохранить приватный draft, но не меняет
действующие конфиги, не исполняет код и не создаёт repository файлы.
Diff включает before/after, XML/code unified diff, структурные изменения,
затрагиваемые search keys и зависимости. Проверка проверяет XML, типы
виджетов, поля/связи, привязки и схемы; синтаксис кода не означает проверку
его поведения. Все ошибки имеют код, путь к параметру и исходную строку,
когда она известна; не сериализуются через `repr(exception)`.

Предпросмотр использует тот же динамический Vue-renderer, что рабочий UI,
с теми же языком/темой и разрешением конфига. Активные действия в preview
отключены или обращаются только к тестовым данным. AI не генерирует Vue
templates/HTML для отдельного preview и не требует rebuild для сохранения
поддерживаемого XML view. Привязка к непроверенному/неактивному скрипту не
должна начать исполняться при применении layout.

Ревизия ресурса — непрозрачный серверный идентификатор конкретного изменения,
не только timestamp или hash текущего содержимого. Возврат прежнего текста,
undo/redo, импорт плагина и повторное создание дают новую ревизию.
Она обновляется в общем пути сохранения конфигов/скриптов/нейминга, включая
UI, XML-RPC, native scripts и installer. Полный исходник ревизии и автор
сохраняются; существующий Command journal используется для аудита, но его
наличие само по себе не заменяет историю исходников.

При apply сервер повторно проверяет права, точный draft и ревизии всех
изменяемых ресурсов и зависимостей: inherited configs, каталог, schema,
script bindings. Изменение между prepare/preview и apply даёт
`revision_conflict`, без молчаливого overwrite. Compare-and-write и запись
результата операции выполняются с vendor-appropriate блокировкой/условным
обновлением в штатной транзакции, а не через раздельные SELECT и UPDATE.
Ревизия `null` означает создание и требует отсутствия целевого ресурса.

Idempotency key хранится устойчиво к рестарту и нескольким workers, в scope
пользователя/проекта/операции, вместе с fingerprint payload и результатом.
Повтор того же запроса возвращает прежний результат; другой payload с тем же
ключом даёт `idempotency_conflict`. Это применяется к prepare, test,
activate и apply. Если ключ истёк, старый подтверждённый apply не становится
автоматически новой записью. Параллельные запросы не создают дубликаты.

Для составных изменений сохраняются реальные транзакционные границы ядра.
Многобазовая запись не объявляется распределённо атомарной. Неподдерживаемый
scope отклоняется до записи; при возможном `partial_commit` возвращаются
фактически применённые ресурсы и сохранённое состояние операции.
Повторный запрос не запускает уже совершённые эффекты ещё раз.
Результаты подготовки/проверки нельзя принимать за успешное применение.

### Динамический нейминг

Правило проверяет существующий Naming/NamingUtil и его выражения/TSQL/скрипты,
в исходном контексте SObject/Snapshot/File. Учитываются parent/child,
расширение, дата/время, параметры, version/context и настройки repository.
AI не подставляет строки своим вторым интерпретатором шаблонов.
Trace объясняет выбранное правило и источники вычисленных значений.
Объяснение строится в том же проходе вычисления, без повторного запуска
скрипта ради trace.

Preview ничего не резервирует и не создаёт на диске. Проверяются коллизии
между выбранными объектами, в доступном file registry и repository с учётом
vendor/файловой системы. Недоступные пользователю данные не раскрываются
через сообщение о коллизии. Результат сообщает scope, момент проверки и
непроверенные ограничения. При реальном check-in правило вычисляется снова
и конфликты проверяются в исходном пути записи: preview не устраняет гонку.
Готовые пути/имена не кэшируются постоянно; изменяемые данные/правила/время
и результаты custom scripts не считаются статическими.

Нейминг может исполнять скрипты. Такой evaluate требует права на исполнение
и безопасного тестового контекста либо отказывает явно. Read-only запрос
не получает скрытые полномочия на выполнение произвольного кода.

### Пробный запуск и активация скриптов

Создание исходника, синтаксическая проверка, пробный запуск, сохранение и
активация — разные операции. Код исполняется существующим механизмом TACTIC,
с исходными bindings/server/project/user и понятным traceback. Описания
входов/выходов имеют JSON Schema; тест проверяет результат, ожидаемые ошибки
и эффекты, а не только успешную компиляцию. Неподдерживаемые языки отклоняются.

Пробный запуск — отдельный ограниченный процесс с тестовыми БД/repository,
без рабочих секретов/тикетов. Сервер ограничивает время, память, output,
файлы/сеть/процессы средствами ОС; по timeout завершает весь созданный набор
процессов. Обычный subprocess с timeout, Mako и rollback рабочей транзакции
не являются песочницей. Windows и Linux isolation проверяются отдельно;
пока нужная изоляция недоступна, операция сообщает `sandbox_unavailable`.

Тестовые данные выбираются явно и с правами пользователя; создание fixtures
не копирует произвольно всю рабочую БД. Test run сохраняет identity, source
revision, inputs, dataset revision, лимиты, результаты/эффекты и журнал.
Активация требует права исполнения и успешной подходящей проверки именно
этой ревизии, с актуальными входами/зависимостями. Одного прошедшего теста
недостаточно для доказательства корректности во всех рабочих сценариях.

### Форматы, ошибки и примеры

В запросах target идентифицирует существующий ресурс, без DB vendor:
`{project, search_type, view}` для layout, `{project, search_key}` для
сохранённого script/naming; при создании — устойчивое имя/путь в этом scope.
Revision/token — непрозрачная строка; search keys сохраняют семантику TACTIC.
Схемы имеют `additionalProperties: false`, ограничения размеров/числа
объектов и явные обязательные поля. Публичный ответ не содержит API-тикет.

Общая ошибка: `{code, message, path, details, retryable}`. `path` — JSON
Pointer параметра; details может содержать только разрешённые сведения.
Коды: `unauthenticated`, `forbidden`, `not_found`, `invalid_argument`,
`invalid_xml`, `unsupported_widget`, `invalid_binding`, `syntax_error`,
`test_failed`, `timeout`, `sandbox_unavailable`, `naming_collision`,
`revision_conflict`, `idempotency_conflict`, `unsupported_scope`,
`partial_commit`, `internal_error`. Стек/исходные строки скрипта отдаются
только имеющему право на этот исходник; internal errors имеют request ID.

Пример целевого запроса `layouts.prepare` — имена проекта/type/view ниже
иллюстративные, class paths должны проходить реальный каталог renderer:

```json
{
  "target": {"project": "demo", "search_type": "demo/asset", "view": "table"},
  "xml": "<config><table><element name=\"code\"/><element name=\"name\"/></table></config>",
  "base_revision": "rev_17",
  "idempotency_key": "layout-demo-table-001"
}
```

Целевая JSON Schema этого запроса (границы выбраны для первого контракта;
сервер должен отклонять превышение, а не молча обрезать содержимое):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["target", "xml", "base_revision", "idempotency_key"],
  "properties": {
    "target": {
      "type": "object", "additionalProperties": false,
      "required": ["project", "search_type", "view"],
      "properties": {
        "project": {"type": "string", "minLength": 1, "maxLength": 256},
        "search_type": {"type": "string", "minLength": 1, "maxLength": 1024},
        "view": {"type": "string", "minLength": 1, "maxLength": 256}
      }
    },
    "xml": {"type": "string", "minLength": 1, "maxLength": 1000000},
    "base_revision": {"type": ["string", "null"], "minLength": 1, "maxLength": 256},
    "idempotency_key": {"type": "string", "minLength": 1, "maxLength": 128}
  }
}
```

Prepare result содержит `draft_id`, `draft_revision`, `diff`, `affected[]`,
`errors[]`, `warnings[]`, `dependencies[]`. Validate token связывает точный
draft revision с проверенными зависимостями. Preview token дополнительно
связывает UI/test context; изменение draft аннулирует оба токена.
Полная schema результата и всех остальных операций входит в реализацию
`api.describe`; свободный `args: object` её не заменяет.

Пример следующего шага после успешных validate и preview:

```json
{
  "draft_id": "draft_demo_table_001",
  "validation_token": "validation_demo_table_001",
  "preview_token": "preview_demo_table_001",
  "idempotency_key": "apply-demo-table-001"
}
```

### Порядок реализации и критерий готовности

1. Дочитать и проверить metadata/context API с правами пользователя;
   построить каталог поддерживаемых widgets и schemas операций.
2. Сделать один динамический view и его draft/validate/preview/apply через
   тот же Vue-renderer. В общем пути сохранения ввести историю, атомарную
   проверку ревизий и устойчивую идемпотентность для всех клиентов.
3. Добавить Naming evaluate/trace/collisions на штатном движке; сохранить
   динамические зависимости и отсутствие filesystem effects в preview.
4. Добавить script drafts/input-output schemas, изолированные тесты и
   отдельную активацию; затем schema/pipeline/automation commands.
5. Подключить модель отдельным адаптером и MCP поверх готовых операций.

На SQLite локально и PostgreSQL через Apache проверяется один пользовательский
сценарий: помощник получает разрешённую схему, составляет XML layout,
готовит script и naming, показывает diff/preview и тестовый результат,
затем применяет разрешённые изменения. UI обновляется без rebuild.
Повтор apply не создаёт дубликаты; параллельная правка даёт conflict;
чужой проект/исходник/исполнение запрещены; timeout оставляет рабочие данные
целыми; после рестарта нескольких workers ревизии/результаты актуальны.
Неизменённый Handler продолжает свои операции на том же экземпляре.

Текущее состояние: перенесены базовые XML/config/script/naming механизмы,
но нет authoring API, draft/revision протокола, sandbox и динамического
Vue preview. Текущие write/script API имеют ограничения admin. Успешные
прежние проверки XML-RPC не доказывают готовность AI-помощника.

### 0.96: Vue forms на серверном EditWdg

RecordForm открывает текущий edit/insert descriptor /admin/form и отображает
только четыре перенесённых primitive input класса. Значения/defaults/select
choices приходят с сервера; frontend сохраняет raw значения и передаёт sibling
values исходному EditCmd. Readonly поля отображаются, но исключаются из списка
actions. Неизвестный класс, многозначное/объектное значение или неподдержанный
display option явно блокируют форму. Старые JS callbacks не исполняются.

Create/Edit доступны в admin UI; database browsing reader сохраняется отдельно.
Dirty close/Escape требует подтверждения; beforeunload предупреждает о draft.
Во время записи закрытие и повтор заблокированы. Потеря ответа не вызывает
retry: пользователь проверяет список прежде новой попытки. Draft живёт только
в памяти компонента. Server UserException при JSON execute_cmd возвращается
как validation_failed со штатным сообщением; остальные transport ошибки и
XML-RPC не менялись. Это ещё не revision/idempotency протокол AI authoring.

Проверены built Vue/Chromium/временная SQLite и неизменённый клиентский вызов.
Новые specialized inputs/layouts, upload, вложенный sidebar, config editor и
preview продолжаются отдельно; frontend renderer не наследуется от HtmlElement
и не требует rebuild при изменении поддержанного исходного XML.

### 0.97: CalendarInputWdg в декларативной форме

Современный tactic.ui.widget.CalendarInputWdg получает серверный input descriptor
рядом с исходными values. type/value задают browser control; unchanged_value
сохраняет полный timestamp и явный UTC/offset. value_suffix задаёт полдень GMT
для *_day timestamp; SQL DATE остаётся датой. Vue не вычисляет timezone/naming:
новые значения преобразует исходный DatabaseAction, выбранный timezone виден
пользователю. Picker редактирует миллисекунды; неизменённое значение сохраняет
микросекунды. Это транспорт native формы, не замена XML-RPC widget методов.

Поддержан browser mode; inline, старый pyasm Calendar, Time/Interval и старые
JS options явно блокируются. JSON-RPC использует stdlib ISO encoding date/datetime
для успешных результатов команды, XML-RPC прежний. Серверная логика остаётся
в EditWdg/EditCmd/SObject; новый frontend может читать тот же descriptor.

### 0.98: workflow choices и действия context

Исходные workflow input get_display business branches выделены в headless
get_input. EditWdg.explicit_display готовит control в исходном контексте;
/admin/form сохраняет class_name/raw values и описывает select/text с серверными
choices. Vue поддерживает явный набор восьми классов; новые неизвестные классы
не становятся произвольным select. Generated empty labels проходят i18n,
пользовательские labels остаются данными.

Pipeline/group/process/status/schema логика живёт в перенесённых модулях TACTIC.
Сохранение по прежнему EditCmd, SubContextAction.postprocess использует общий
SObject/Transaction, ошибка откатывает предыдущее сохранение. Choices отражают
сохранённые parent/process на момент открытия, не вычисляются по draft в Vue.
Inline switching, HTML get_display ветки Handler, upload/parent inputs и полная
widget __dict__ parity остаются незавершёнными. Неизменённая проверенная Handler
task-процедура покрывает непустое назначение/status, а не все её special cases.


### 0.99: parent и single-file form upload

/admin/form описывает HiddenWdg, TaskSObjectInputWdg и SimpleUploadWdg как
hidden/parent/file controls. Существующий task parent readonly; insert скрытый
ключ берётся из исходного XML и обрабатывается DatabaseAction.parent_key.
Generated project/no-parent labels проходят i18n; коды объектов — сырые данные.
SimpleUploadWdg сохраняет исходный context/column и API handoff field names.

Vue использует прежний UploadServer, затем execute_cmd/EditCmd/UploadAction.
Upload и запись формы — два запроса: staged file ещё не snapshot; неуспешная
запись откатывается общей транзакцией. Consumed sources остаются в оригинальном
undo cache. Browser File сохраняется в draft для явной новой попытки; потеря
ответа блокирует повтор Save. При смене контекста после upload команда записи
не отправляется. Разные upload fields требуют разных имён файлов; один запрос
ограничен существующим 64 MiB multipart limit.

Никакого legacy HTML/JS/DOM adapter в renderer не добавлено. Immediate client
upload actions и составной TimeAction input явно отклоняются. Rich/multi/zip
uploads, lookup popup, вложенные layouts и authoring/revisions остаются в плане.

### 0.100: составные upload и multiple select

Старый pyasm.widget.UploadWdg описывается как группа file slots с исходными
names/required, context из values/setting/pipeline либо text, subcontext,
description и revision. Это отдельный класс от modern tactic.ui.widget.UploadWdg.
Vue передаёт файлы прежнему UploadServer, затем отправляет исходные compound
имена в EditCmd/MultiUploadAction; handoff path/ticket — additive вариант
поверх сохранённых FieldStorage inputs. Context и file naming вычисляет ядро.
Staged files не копируются повторно. Ошибка откатывает общий Command/FileUndo;
потеря ответа по-прежнему блокирует автоматический повтор записи.

MultiSelectWdg возвращает raw values отдельно от выбранных options; wrapped
pipe values разрешаются исходным _is_selected. Checkbox group отправляет массив
в MultiDatabaseAction, который сохраняет оригинальный формат и сортировку.
Неизменённая пустая multi-upload группа исключается из element_names при
сохранении других полей. Несовместимые names/actions/options блокируют Save.
Vue business models и новая система файлового транспорта не добавляются.
Rich modern upload, ZIP/naming, time-only, nested layouts и authoring — следующие
блоки; наличие этих descriptors не доказывает готовность HTML или Handler GUI.

### 0.101: ZIP-группа и time input

Существующая file-group поддерживает MultiZipUploadAction. Archive staging
использует прежний UploadServer; распределение файлов, naming resolver,
snapshots, subcontext/revision и rollback остаются в исходном серверном action.
Vue не распаковывает ZIP и не вычисляет соответствие имён объектам. Resolver
из доверенного XML обязан быть установленным классом с полным Python path;
исключённый prod namespace не возвращается. Ошибка откатывает весь Command.

TimeInputWdg descriptor содержит HH:mm `value` и исходное `unchanged_value`.
Native input type=time отправляет неизменённый raw clock без потери точности.
Для исходного TimeAction форма отправляет отдельные hour/minute; timezone
display обратен DatabaseAction conversion. TimeDatabaseAction меняет часы
timestamp либо SQL time, DateDatabaseAction — дату перечисленных columns.
СУБД выбирается прежним Sql/DatabaseImpl; нового date/time слоя во Vue нет.
Interval/drag calendar и неизвестные widget options явно блокируют Save.

Следующие блоки — rich UploadWdg, config authoring, nested layouts и revisions/
preview. Текущие descriptors остаются независимыми от Vue; HTML compatibility
и полная widget __dict__ parity не объявляются готовыми.

### 0.102: современный UploadWdg

Modern tactic.ui.widget.UploadWdg использует тот же compound renderer с одним
file slot. Context SelectWdg готовится сервером из original context_expr,
context, setting или pipeline; Vue получает choices/value и исходный column.
Форма отправляет прежние UploadAction compound field names, без индексов
arbitrary MultiUploadAction. Comment/revision/subcontext живут в той же draft
группе; неизменённая пустая группа не запускает upload action при обычном edit.

UploadAction обрабатывает subcontext в общем серверном пути, включая XML-RPC
и Python scripts. При пустом context ошибка возникает до IO; файлы/объекты
используют прежние Command/FileUndo boundaries. Старые HTML/JS callbacks и
immediate client_action явно неподдержаны. Следующие блоки — XML authoring,
nested layouts, revisions/preview; новой Vue business model нет.

### 0.103: source XML authoring и revision guard

Редактор читает отдельные исходные DB записи и resolved WidgetConfigView layers;
конфиги не сериализуются из неполной descriptor проекции. Exact source string
сохраняет comments/CDATA/unknown XML/sibling views. Проверка — оригинальный
WidgetDbConfig.validate без импорта display/action handlers; diff — stdlib.
Сохранение — штатный Command/SObject.commit, с прежним журналом и invalidation.

Admin native read/check/save API использует прежние auth/CSRF/контекст, не
изменяет XML-RPC. Revision fingerprint включает исходные sources, разрешённые
слои и sobject_log, поэтому замечает обычные API/script изменения и A→B→A.
Table lock делает сравнение и запись атомарными на SQLite/PostgreSQL; два
отдельных процесса проверены. Repeated stale create — conflict, не повтор записи.
Другие config edits того же ресурса могут консервативно инвалидировать revision.

Vue выбирает view/source, показывает исходный XML/разрешённые слои/diff, сохраняет
dirty draft при конфликте и не повторяет ambiguous write. Refresh использует
прежний renderer; смена XML не требует rebuild. Это начало authoring, не полный
AI contract: history UI, dependency/filesystem locking, stable AI idempotency,
nested layouts, executable preview и script sandbox ещё не завершены.


### 0.104: общий renderer и draft preview

ConfiguredView.vue обслуживает рабочую таблицу и read-only preview; это один
renderer, а не второй HTML шаблон. POST /admin/widget-configuration/preview
использует исходный WidgetConfigView resolver с отсоединёнными WidgetDbConfig
записями и request-local overlay по DbResource/type/view, без commit. Overlay
восстанавливается при успешном разрешении и при ошибке. Новый renderer может
использовать тот же descriptor, columns и обычный query без переноса XML merge
во frontend. XML-RPC HTML API не меняет формат.

TabWdg descriptor расширен elements[].interface: дочерний search_type, columns
и table descriptor. ViewPanelWdg table/default и TabWdg config_xml/category view
сохраняют исходные имена/параметры. Native layout adapter разрешает дерево
до 8 уровней/64 nodes с проверкой циклов и проекта; handlers/scripts не исполняет.
Vue лениво читает данные активной вкладки штатным query. Дочерние таблицы пока
read-only, максимум 50 записей. Tab saved-state, actions/expressions и полный
ViewPanel controls остаются отдельными этапами. Preview не гарантирует атомарный
snapshot всех зависимостей, а save сохраняет существующую revision проверку.

Metadata-only descriptor resolution never imports display classes for has_config; original SDK option resolution keeps separate cache keys. Inline configs wrap only their outer view, preserving deeper elements. Both source defects have explicit source/native checks.


### 0.105: дочерний ViewPanel query

Interface descriptor добавляет panel.search_limit/order_by/do_initial_search/
show_refresh/show_search_limit из исходных XML options ViewPanelWdg. Общий
ConfiguredView держит filter/sort/page локально и вызывает существующий query;
бизнес-логика, ACL и vendor SQL остаются на сервере. KeepAlive хранит состояние
посещённых вкладок в текущем layout, без eager fetch неоткрытых view. Локальный
filter draft отделён от применённого filters, async request id проверяет контекст.
Preview разрешает read-only поиск по данным, сохраняя запрет записи/действий.
Размер страницы 1..500 и literal column ordering — ограничения native renderer,
не изменения исходного XML-RPC. Advanced SearchWdg и saved search state остаются
отдельными контрактами; дочерние формы/CRUD пока не подключены.

### 0.106: серверный конфиг как экран приложения

Ориентир — разделы, черновики и явное сохранение в Configuration Tactic Handler.
ServerConfiguration.vue показывает выбранный раздел; поиск охватывает все
разделы. Несохранённые изменения отмечаются в навигации, сохраняются при смене
раздела/экрана; beforeunload защищает черновик. Сервер отдаёт типы/choices для
38 явно поддержанных полей; общая ревизия защищает Save всех изменений.
Неизвестные параметры и операции миграции не превращаются в работающие inputs.
Секреты возвращаются только как configured, ввод нового значения/удаление
раздельны. Restart notice зависит от изменённых ключей, сервер сам не перезапускается.
Известные путевые настройки нормализованы в Config, не форматтером Vue;
исходники XML и произвольные строки сохраняются. UI и XML-RPC получают `/`.

Сквозной mobile/touch контракт: маленькие экраны 320–360 px, обычный тап;
для контекстных действий допустимо долгое нажатие. Мышь/правая кнопка/hover
и drag не обязательны для операций. Явные controls, выбор через меню и
touch-зоны от 44 px относятся ко всем таблицам, формам, файлам и редакторам.
Общая навигация сворачивается на мобильном, Escape/выбор типа закрывает её;
desktop sidebar сохраняется. Таблицы прокручиваются внутри контейнера.
Responsive и hasTouch Chromium проверены; неперенесённые экраны ещё не готовы.

### 0.107: оболочка и базовые операции

Контекст проекта находится в app bar; навигация одна для desktop и mobile.
На узком экране native dialog обеспечивает modal/focus/Escape, на широком
та же навигация занимает боковую панель. Аккаунт и appearance имеют явные
кнопки; формы на телефоне занимают экран. Оболочка не меняет XML resolver.

ObjectOperations.vue — общий вход в просмотр/edit/create объекта: ПКМ по
строке или обычный тап по `⋮`. Меню лишь выбирает действие, существующие
RecordForm/EditWdg/EditCmd разрешают форму и выполняют запись на сервере.
Смена ticket/project/type и обновление данных закрывают меню. Preview и
дочерние таблицы остаются read-only. Перенос продолжается с базовых операций
и их исходных XML-настроек, затем с виджетов ячеек и поведения таблицы.

### 0.108: подтверждение и выбор зависимостей

Interface descriptor добавляет operations с create/edit/retire/delete и
retire_column. Современный renderer уважает явные XML false; это управление
представлением, серверные ACL остаются обязательными независимо от меню.
ObjectAction.vue показывает подтверждение retire/reactivate и группы удаления.
Show retired передаётся существующему query. Native /admin/object-deletion/read
и /apply используют текущую авторизацию и исходный DeleteCmd, с локальной
синхронной публикацией транзакции. Generic execute_cmd по-прежнему требует
исходный command key; native endpoint разрешает только эту admin операцию.
Невыбранные зависимости сохраняются, snapshot-owned файлы и directory markers
обрабатывает сама команда. Preview не фиксирует снимок БД: при подтверждении
обрабатываются текущие связанные записи выбранных групп. Ошибка/потеря ответа
не запускает автоматический повтор; ambiguous write требует обновления данных.
Следующие базовые операции — дублирование и выбор нескольких объектов.

### 0.109: field-only duplication и выбор страницы

Native form принимает source_key отдельно от search_key. Для копии исходный
EditWdg читает настоящий источник с view insert и mode insert; descriptor
не отдаёт источник как цель записи. Вставка остаётся EditCmd с новым identity.
ID/code/служебные даты исключаются по имени и column; копирование контента и
связей этим режимом не обещается. Поля, timezone и precision готовит сервер.

Selection принадлежит App и текущим rows; ConfiguredView лишь показывает
чекбоксы и сообщает выбранные записи. Refresh/filter/sort/page/project очищают
выбор. ObjectAction обслуживает один объект и список одинаково. Native
/admin/object-status использует ObjectStatusCmd и исходные retire/reactivate;
deletion read/apply принимает search_keys и передаёт список в исходный DeleteCmd.
Сервер проверяет все ключи до мутаций, объединяет aliases id/code одного SObject,
подсчитывает связанные группы без повторов. Общая Command/Transaction отвечает
за rollback; распределённый атомарный commit нескольких БД не добавлялся.
Preview/дочерние таблицы остаются read-only; массовая правка полей — следующий
путь через исходный EditMultipleCmd с явным выбором изменяемых полей.

### 0.110: явный выбор полей EditMultipleCmd

RecordForm обслуживает одиночный объект и выбор страницы. Native form
валидирует search_keys через общий selected_objects, возвращает канонические
ключи и mixed текущих колонок; исходный EditWdg готовит inputs первого объекта.
UI явно объясняет источник значений. Apply выбирает поле, только выбранные
элементы передаются в исходный EditMultipleCmd/update_data; никаких SQL updates
или второго form engine. Общий Command/Transaction сохраняет rollback всех
редактируемых объектов, исходные field actions и update_multi triggers.
Служебные default actions проекта по-прежнему выполняются исходной командой.

Неподдержанные и compound upload/parent/hidden/TimeAction inputs не выбираются
в массовой форме. Одиночная форма и API сохраняют свои возможности. List-data
исправлен непосредственно в MultiDatabaseAction, не меняя scalar семантику
DatabaseAction. Unknown write outcome блокирует повтор в том же окне. Touch
не требует контекстного меню: Edit selected доступен обычной кнопкой, Apply —
label с зоной 44 px; форма на малом экране использует существующий dialog.
Дочерние формы и произвольные XML actions остаются следующим этапом.

### 0.110.1: исправление навигации

Sidebar-dialog получает явную высоту grid-области и overflow hidden,
а type-list — собственную прокрутку с min-height 0. Desktop sidebar можно
скрыть тем же верхним navigation toggle; grid освобождает колонку содержимому.
Desktop-видимость независима от mobile modal drawer и сохраняется при resize.
Конфиг и API docs находятся в верхнем меню ⋮ рядом с Account, по Main.qml ТХ.
Следующий этап — дочерние формы через исходные parent_key/connect_key.

### 0.111: связанные записи и создание с родителем

RelatedObjects — окно предметного сценария, переиспользующее общую таблицу,
формы и операции. Native relations descriptor строится исходной Schema и
SearchType; канонический parent key передаётся query и EditWdg/EditCmd.
Raw listing в этом окне сохраняет фильтр родителя при поиске, сортировке и
pagination; другие поля и формы разрешаются прежними XML views. Row actions
работают и через ПКМ, и через ⋮. Preview и обычные составные readonly панели
не получили write controls.

Instance/prefix/self relations пока явно недоступны в related browser.
Multi-select и многоуровневое раскрытие здесь не реализованы. Native form
parent_key/connect_key проверяет отдельно от search_key и передаёт только
подготовленный контекст в существующий execute_cmd. Исходные SObjectConnection,
triggers и общая транзакция обеспечивают запись и rollback. HTML, новый
протокол/XML-RPC методы и второй механизм связей не добавлялись.

### Search Types: Summary и каталог

Summary показывает total/active/retired, fields/pipelines/processes, размещение
данных, прямые и унаследованные связи и признаки M:N. Статистика считается
существующей серверной процедурой в базе владельца типа; отсутствующая таблица
даёт неизвестные значения, а не нули. Только актуальные данные после Reload.
Функция build_local_relationship_graph целиком взята из Handler, без Qt;
проекция приходит в metadata.relationshipGraph штатной SearchTypesCmd.
Новый транспорт или SQL для карты не нужны.

RelationshipMap отображает эту проекцию: направленные связи, подписи,
выделение выбранного типа, zoom 40–200%, wheel, middle-button pan, reset.
Touch использует штатную прокрутку контейнера, кнопки масштаба доступны
без мыши; клавиатура переключает Summary/Details/Fields. Противоположные
связи рисуются раздельными дугами. SVG служит диаграммой, иконки — прежние
официальные шрифтовые наборы.

Каталог фильтруется по фактической базе проекта (projectLocal), показывает
таблицы, цветовые метки, обычные/связующие типы и число связей. На desktop
каталог и документ прокручиваются отдельно, на mobile каталог — AppSelect.
Оформление карточек переиспользует configuration-group и SettingRow.
Details/Fields сохраняют прежние операции и ревизии; Discard обновляет
документ с подтверждением. Полный Search Types ещё не завершён: Workflow,
Naming, previews/check-in, изменение существующих полей и мастер создания
остаются в исходном перечне, Users/Groups пока не расширяются.


## Реализованный этап: Workflow и зависимости процессов

В Search Types появилась вкладка Workflow с проектными и общими pipelines,
счётчиками процессов, созданием и открытием самостоятельного редактора.
Раздел Administration → Workflow использует тот же редактор. На desktop каталог,
граф и свойства размещаются рядом; на mobile каталог сворачивается, граф имеет
нативную прокрутку, формы идут ниже. Добавление/связи, координаты и множественный
выбор доступны controls без мыши. Не вводились виды карточек/объектов/таблиц.

Серверные workflow_request/process_rules_request взяты из Handler; графический
документ и три алгоритма расположения — из его documents.py/graph_layout.py.
Сохранение выполняют Pipeline.update_dependencies и исходная NewProcessInfoCmd;
скрипты и workflow triggers сохраняются штатным жизненным циклом. process_code
сохраняется в XML, как в PipelineSaveCbk. Комментарии, processing instructions,
неизвестные атрибуты и элементы не удаляются. Названия сохранённых процессов
защищены; используемые процессами задачи/снимки и правила блокируют удаление.

Редактор содержит свойства штатных видов узлов, установленные дополнительные
виды, task status/subpipelines, назначения, скрипты/команды и статусы. Зависимости
процесса используют исходные trigger_wdg callbacks: task_status, parent_status,
task_create, task_date, custom_script, python_class, notification. Сгенерированные
правила доступны только для чтения; naming и объекты pipeline показаны отдельными
разделами, объекты имеют пагинацию и просмотр. На Save действия не исполняются.

Админ-права проверяет сервер; общие pipelines нельзя менять в проектном редакторе.
Ревизии и штатные транзакции защищают запись; результат неизвестного сохранения
блокирует повтор до reload. Буферы XML/JSON входят в защиту черновика. Родительский
экран блокирует смену раздела/проекта, пока дочерний редактор открыт.

Полный Search Types ещё не завершён: далее Naming, preview/check-in,
существующие Fields и мастер создания. Эти пункты не заменены ссылками на таблицы.
Проверки этого этапа использовали временную SQLite и Chromium; новое поведение
на PostgreSQL отдельно ещё не проверялось. Handler не менялся.


## Search Types: Naming

Вкладка Naming использует полный набор полей из NamingEditorController и
NamingEditorView.qml Handler: список, создание, дублирование, сохранение,
сброс, versionless/manual flags и advanced fields. Кнопки раздела занимают
общую шапку админки. Один черновик относится к одному правилу; смена правила,
вкладки/раздела/проекта и закрытие защищены от потери изменений. Неизвестный
результат Save блокирует повтор до reload. Ошибки валидации приходят через
штатный UserException; сериализация результата execute_cmd не менялась.

NamingCmd load/save/preview работает через Search/SObject/Command с текущим
проектом и admin-правами. Save блокирует таблицу config/naming, проверяет
ревизию набора правил данного типа и вызывает родной commit с триггерами.
Повторный Save новой записи с прежней ревизией не создаёт второй объект.
Остальные поля сохранённой записи не затираются.

Предпросмотр отличается от локальной симуляции Handler: требуется настоящий
Search Object; Naming.get выбирает правило штатным алгоритмом, а общая часть
DirNaming/FileNaming вычисляет каталог, имя и sandbox. Эти же методы вызывают
штатные get_from_db_naming при check-in. Snapshot и File только в памяти;
manual_version не коммитит Snapshot. Контекст/тип снимка, расширение, дата,
параметры, parent/child и TSQL обрабатывает существующий движок. Latest/current
показаны отдельно; коллизии проверяются по relative_dir/file_name и алиасу
репозитория в File, не по постоянному кэшу готового имени. Смена черновика или
sample скрывает устаревший результат. Для admin/sthpw прямо указано исходное
ограничение: их native check-in не применяет config/naming.

Python-выражения, UPDATE, script/class overrides требуют отдельного явного
подтверждения выполнения в обычной серверной среде. Это обычная admin-операция,
не изолированный script test для AI. AI sandbox этим этапом не реализован.
Неперенесённые операции ExpressionParser не подменяются симуляцией.

На узком экране список правил и форма идут вертикально, параметры preview
собраны в компактную сетку. Новые views/card renderers не добавлялись.
Проверены временная SQLite, XML-RPC и Chromium (1440/320 px); новое поведение
PostgreSQL в этом этапе отдельно не проверялось. Handler не изменён.
Следующий блок Search Types — Details preview/check-in, существующие Fields и
мастер создания. Вход в Naming из рабочего check-in окна Handler/Vue остаётся
отдельной интеграцией; текущий экран встроен в Search Types.

Details preview/check-in подключён в SearchTypes: metadata сохраняет исходный
SearchTypesCmd, файл передаётся в `features/checkin/CommitQueue.vue` через App.
Это клиентская очередь изображений типа, отдельная от серверного sthpw/queue.
Она сохраняет контекст подключения, состояние и файл после закрытия редактора;
завершённые File освобождаются. UploadServer / simple_checkin / get_snapshot
остаются единственным серверным путём. Известную ошибку можно повторить;
неизвестный результат не повторяется автоматически. Очередь живёт в памяти
вкладки, beforeunload предупреждает о несохранённых файлах. Полная Commit Queue
Handler, byte progress, восстановление после reload и UI reconciliation ещё
не перенесены. Следующий блок Search Types — Fields и мастер создания.

Fields и встроенный мастер создания перенесены следующим блоком. Полями владеет
черновик SearchTypes; SearchTypeFields получает document/metadata и испускает
add/remove-draft/toggle-deletion без API. Каталог типов и стандартных полей взят
из Handler. Поля защищаются серверными columnRemovalBlocks; подтверждение удаления,
ревизии и штатный Command/Sql сохраняют данные при отмене или ошибке.

Мастер использует шаги Details/Fields/Ready to create с Back/Next и общим Save.
Fields сохраняет локальную незавершённую форму между шагами. Общий ItemPreview
обслуживает ImagePicker и итог мастера, без второго renderer изображений.
После создания выбранный файл отправляется в существующую очередь приложения.
Проверяется также 320 px с touch-входом. Отдельный creation-only вход из редактора
схемы и общий check-in workspace ещё не подключены; весь Search Types пока
не объявляется завершённым.

## Project schema и создание типа из схемы

Project schema использует SchemaEditor вместо общей таблицы. Сохранённый XML
и revision приходят из SchemaCmd; локальные движения и связи меняют только
черновик, без запросов во время pointer input. Общий RelationshipMap обслуживает
Summary, Workflow и Schema. Узлы можно добавлять из реестра, выбирать отдельно
или группой, перемещать через координаты и удалять из схемы, сохраняя таблицы.
Алгоритмы flow/network/grid остаются исходными graph_layout из Handler.

Связи имеют выбор ключей с серверным каталогом колонок, Create missing columns,
reverse, path и advanced JSON. M:N создаёт план отдельного instance SearchType
с двумя code connections; можно переименовать новую таблицу или восстановить
прямую связь. Таблицы/колонки создаются только на Save штатным ядром. XML,
комментарии, processing instructions, дополнительные атрибуты и элементы
сохраняются; редактируется только собственная схема выбранного проекта.
Системные admin/sthpw схемы доступны только для чтения.

New Search Type открывает отдельный dialog с тем же SearchTypes в creationOnly
режиме. Создание проверяет исходную schema_revision на сервере. Возврат переносит
только созданный узел и новую ревизию в текущий черновик; остальные несохранённые
узлы, связи и план колонок не перезагружаются. Координаты нового узла сохраняются
отдельным Save schema. Обновление metadata и preview использует прежнюю Commit
Queue, без второго check-in пути. Смена проекта/раздела, закрытие админки и выход
защищены общими проверками черновиков и дочернего dialog.

Серверные schema_request/schema_columns_request перенесены из Handler schema_api.py
в SchemaCmd; используются native Search/Schema/Command/Sql. Авторинг схемы и
создание типа берут один registry lock до проверки ревизии. Исходные процедурные
исключения сохраняются; admin-команды переводят ожидаемые ValueError в штатный
UserException, чтобы JSON UI показывал причину вместо общей ошибки параметров.
Восстановлен исходный Schema.set_xml с адаптацией к текущему XML runtime.

Проверены SQLite/XML-RPC/Chromium 1440/320 px и прежние контракты ядра. Создание
из черновика/планирование M:N отдельно на PostgreSQL ещё не проверены.

SchemaTypeDeletion — отдельный дочерний экран с закреплёнными project/ticket/type
и исходной ревизией схемы, по Handler schema_delete.py/confirmation QML. Он
получает проверку зависимостей от SchemaDeleteCmd и не меняет родительский
черновик до успешного ответа. Удаление доступно только при чистой схеме и полном
идентификаторе в подтверждении. Cancel получает фокус первым; на узком экране
детали прокручиваются, действия остаются доступными. Проверку можно отменить,
начатое удаление закрывать нельзя. Новые зависимости/stale review показывают
ошибку и требуют Review again; неизвестный результат требует закрыть окно и
Reload схемы. canLeave/beforeunload защищают открытое окно и незавершённый результат.
После успеха родитель принимает новый XML/revision и очищает выделение/кэш колонок.
Remove from canvas сохраняет регистрацию, таблицу и данные; это другая операция.

Физическое удаление проверено на SQLite и реальном PostgreSQL (пустая таблица,
зависимости, поздний rollback, native undo/redo и shared регистрация). Chromium
проверяет изменения после review и потерю HTTP-ответа после фактического commit,
помимо тач-сценария на 320 px. UI использует прежние AppButton, общий dialog/theme
и английские строки с русским переводом; собственных controls/API транспорта нет.

## Создание проектов

ProjectCreation переносит четырёхшаговый мастер Handler: Details, Preview Image,
Template, Review. Открывается отдельным dialog из выбора проекта, общего меню
и операции Create в списке Projects. Поля: title/code с исходной нормализацией,
category/description, namespace, main-project и template flags, preview и theme.
Шаблоны приходят с сервера: проекты с is_template, установленные ZIP и реально
имеющиеся builtin packages. ProjectTemplates устанавливает, скачивает и удаляет
пакеты с подтверждением; удаление пакета не удаляет созданные из него проекты.

Vue отправляет штатные CreateProjectCmd, ProjectTemplateInstallerCmd и
CopyFileToAssetTempCmd. Серверный каталог доступен только администратору;
пакеты проходят существующую проверку PluginInstaller, операции файлов — FileUndo.
Main project сохраняется в tactic-conf.xml с проверкой ревизии и компенсацией
при ошибке транзакции. Копирование серверного шаблона экспортирует его актуальное
состояние. После создания сохраняются метаданные и открывается навигация проекта.
Если открытие не удалось, повторяется открытие уже созданного проекта, а не
CreateProjectCmd. Неопределённый результат требует обновить каталог перед повтором.
Закрытие защищает черновик; смена авторизации запрещает применение старой формы.

Проверен сквозной Chromium-сценарий: duplicate code, preview check-in, install/
download/delete ZIP, empty/server/ZIP creation, opening retry, navigation XML и
touch на 320 px. Отдельная проверка жизненного цикла проверяет main-project config
и его откат при ошибке SQL commit. Handler не изменялся.

## Редактор сайдбара

Administration → Sidebar Editor и карандаш Navigation открывают один редактор
дерева вместо таблицы config/widget_config и общего XML-popup. Чистые алгоритмы
перенесены из thlib/ui/sidebar_editor.py, sidebar_icons.py; экран следует
SidebarEditorView.qml, SidebarEntrySettings.qml и SidebarTechnicalSettings.qml.
Handler читается только как исходник и не используется во время выполнения.

TH (tactic_handler) и TACTIC (project_view) — независимые корневые представления.
Сохранены definitions/references, вложенные sections, folding, group preview,
добавление link/section/separator, удаление ссылки без потери definition,
перестановка соседей, Simple/XML выбранного элемента и Item/Access/Technical.
Поля title/icon/visibility/search type/search preset/result mode/layout/shelf,
child view/widget type/class/view сохраняют исходные имена и XML-семантику.
Выбор иконки использует комплектные Font Awesome и Material Design charmap.

Серверные read/edit/save доступны только admin. Правила link permissions
сливаются с access_rules групп без удаления посторонних правил; переименование
переносит права. Сохранение конфигов и групп использует одну штатную Command
с native SObject.commit, журналом, блокировками таблиц и проверкой ревизии.
XML с DTD/entities, циклы дерева и чрезмерные размеры отклоняются. Черновик,
включая ещё не применённый XML, защищён при закрытии/смене контекста.

Configure search открывает существующий Vue table workspace, Search Library
и редактор быстрых фильтров. Manage groups открывает общий экран групп в дочернем
dialog; тот же компонент используется в Administration → Groups. После сохранения
групп и возврата обновляются права и список групп, сохраняется выбранный пункт
и корень сайдбара. Вход, как и переключение разделов в Handler, требует сохранить
или отменить изменения сайдбара.
Поля режимов результатов/layout/shelf сохранены для Handler; новые Vue виды
и dock arrangement не реализуются в рамках этого редактора.

Проверены SQLite lifecycle (права, XML, конфликт и поздний атомарный rollback),
Chromium с тач-входом на 320 px и создание проекта с открытием новой навигации.
Отдельного прогона нового редактора на PostgreSQL пока нет.

## Search Library и быстрые фильтры

View actions → Saved searches и Quick filters доступны в обычном workspace
и Configure search редактора сайдбара. Перенесены Handler FilterEditorController,
SearchPresetBar, AdvancedSearchView, QuickFilterEditorController/View и
QuickFilterCatalog: редактирование условий, включение, перестановка, AND/OR,
save as/update/rename/duplicate/delete, копирование tactic-search-ссылки,
выбор/очистка фильтров, порядок и видимость групп, копирование текущего выбора.
Черновики защищены при закрытии и обновлении; неопределённый результат записи
требует загрузить актуальный конфиг перед повтором.

Хранилище остаётся config/widget_config: исходные link_search:<name>:<type>
и <type>@<element>, prefix main_body/search_ops и quick_filters@<scope>.
Rename сохраняет view; update сохраняет description, сторонние XML-узлы
и дополнительные packed prefixes. Условия, keyword и порядок восстанавливаются
в workspace. Каждая вкладка хранит свои условия/выбор/layout; новая вкладка
получает общие defaults своего элемента, без копирования поиска соседней вкладки.
Save for this tab и Save as defaults on server — разные операции.

Все чтения и запросы выполняются в обычном RequestContext с текущими правами.
Только администратор меняет shared presets/defaults; обычный пользователь может
применять поиски и сохранять локальные настройки своей вкладки. Каталог фасетов
использует всю разрешённую выборку, исходный потолок 64 значения и metadata
values/choices/options. Администратор получает COUNT/GROUP BY через native Search;
для обычного пользователя выполняется одно чтение разрешённых полей и подсчёт
в Python, без выдачи права произвольных SQL-выражений. Task process/status/assigned
объединяются в один relationship search, чтобы условия совпадали на одной задаче.
MY TASKS разрешается в текущий login непосредственно при запросе.

Expression использует штатный Search.eval и запрещает исполнение/запись;
match/do not match честно помечены медленными. Вложенные legacy search_ops levels
отклоняются, поскольку редактор Handler также представляет плоские условия.
Сохранение использует Command, native SObject, блокировку и проверку ревизии.
Маршруты /admin/search-configuration/* дополняют существующий XML-RPC.
Код и форматы подключения Handler не изменялись.

Проверены один жизненный цикл на временных SQLite и PostgreSQL (условия,
expression, defaults, rename/delete, метаданные, конфликт, права) и Chromium
Sidebar Editor → Configure search → Search Library/Quick filters на 320 px.
Это не заявление о полном переносе всех legacy packed prefixes: специализированные
group/interval, пределы исходных скриптов и внешний приём tactic-search-ссылок
в Vue ещё требуют переноса. Новые режимы результатов и dock arrangement остаются
за пределами текущего этапа.

## Группы и участники

SecurityGroups.vue переносит group drafts из AdministrationController и
SecurityGroupsView.qml целиком в рамках текущей admin-политики: список групп
с описаниями и числом участников, Members / Group details, поиск пользователей,
создание, неизменяемый идентификатор, описание, назначение/снятие участников,
Reload / Discard / Save и защита формы при закрытии, смене раздела/проекта/сессии.
Отдельный раздел и дочернее окно используют один компонент и одну серверную логику.
Groups больше не показывается общей таблицей sthpw/login_group.

Перенесены операции thlib/ui/security_store.py на native LoginGroup / Login,
Login.add_to_group / remove_from_group. Дельты membership сохраняют параллельные
изменения других участников; правка описания использует ревизию самой группы.
Command обеспечивает атомарный откат метаданных и назначений. Создание с тем же
идентификатором/результатом идемпотентно; конфликтующие данные отклоняются.
access_rules, access_level, project_code и sub_groups этим экраном не заменяются.
Состав группы и доступ к пунктам сайдбара остаются отдельными операциями.

Ревизии каталога читаются одним агрегатом журнала, без N+1 по группам. Для него
явно отключён default_order Search: штатное включение timestamp в GROUP BY
разбивало один маркер на несколько строк, особенно заметно на PostgreSQL.
UserIdentity использует общий ItemPreview, initials/color_hash из Handler,
native avatar snapshots и отображение retired-пользователей. Новые контролы
AppCheckbox / UserIdentity не вызывают API и не зависят от окон/проектов.

Сервер проверяет admin до чтения/записи; проверка подстроки "supervisor" в имени
группы из исходного security_store не даёт полномочий. Делегированное управление
группами supervisor ещё требует штатной политики аккаунтов и не объявляется
перенесённым. Native XML-RPC и существующий Handler не изменены.

Проверены SQLite/PostgreSQL lifecycle (создание/retry, дельты, retired, ревизии,
immutable identifier, поздний rollback, права), Chromium через Sidebar → Manage
groups, возврат к выбранному пункту, отдельный раздел Groups и защита формы.
На 320 px проверены обычные тапы и отсутствие горизонтального переполнения.

## Access rules

SecurityRules.vue переносит Administration SecurityRulesEditor и весь состав
AdminSecurityView / Matrix / Rules / RuleEditor / Technical из Handler:
матрицы проектов, Sidebar links, Menu actions, Search Types, процессов и статусов
задач; отдельные правила Search Objects, полей, built-in permissions и search
restrictions. У матриц поиск строк/групп, переключение ячеек, клавиатурные стрелки,
пояснение выбранной ячейки и Use inherited rule. На таче пояснение доступно тапом,
включая заблокированные ячейки. Матрица прокручивается внутри своего контейнера.

Правила можно добавлять, удалять, выбирать серверную цель или вводить идентификатор
и wildcard, менять исходные уровни доступа. Advanced rules содержит access_level,
привязку группы к проекту, sub_groups, полный XML, выбранное правило в JSON,
серверные defaults и единый список всех правил, включая custom scopes.
Комментарии, сторонние узлы, корневые и дополнительные атрибуты XML сохраняются.
Apply to draft и Save to server раздельны; неприменённый текст защищён от смены
выбора. Общий черновик всех групп защищён при закрытии и смене контекста.

securityRules.js повторяет native-key / lookup / highest-grant projection
security_matrix.py: locked/custom/inherited нельзя трактовать как независимые
checkbox-права. Search restrictions фильтруют объекты и не предоставляют доступ.
Серверная security_request взята из thlib/ui/admin/security_api.py, использует
Search / LoginGroup / AccessManager / Command. Штатная блокировка таблицы и
ревизия всего документа защищают многогрупповую запись; все изменённые группы
проверяются до первого commit. Ошибка поздней записи откатывает весь набор.
XML entities/DTD, неизвестные поля, некорректные уровни/проекты, отсутствующие
подгруппы и циклы отклоняются. Названия групп с "supervisor" не дают полномочий:
экран остаётся admin-only, как существующий экран Groups. Это ограничение
делегированного управления, а не перенос исходной небезопасной проверки имени.

Проверены SQLite/PostgreSQL lifecycle и Chromium: матрица/наследование,
XML/JSON/дополнительные атрибуты, редактирование полей, сохранение/повторная
загрузка, защита закрытия, тач на 320 px. На мобильном экране выбор scope заменяет
широкую полосу вкладок тем же AppSelect. XML-RPC и код Handler не изменены.

## Выбор проектов

ProjectChooser.vue переносит ProjectChooser.qml, карточки ProjectCard и правила
фильтрации ProjectModel. Кнопка текущего проекта содержит общий ItemPreview,
название и официальную иконку раскрытия. Она закрывает sidebar/меню перед
открытием отдельного окна с затемнением. Native auto popover обеспечивает
переключение той же кнопкой, закрытие вне окна и Escape; фокус возвращается
к кнопке проекта. Сохранены категории, счётчики, lifecycle labels, описание,
тип/категория проекта, preview и initials fallback. ПК — три колонки,
планшет — две, маленький телефон — одна; список прокручивается внутри окна.

Фильтры Retired/Templates/Built-in по умолчанию выключены и сохраняются между
открытиями в текущей сессии. Как в Handler, Templates включает все шаблоны,
включая retired; Retired дополняет обычные проекты; Built-in независимо
включает admin/sthpw. Категории и пользовательские названия не переводятся.
Создание проекта использует существующий пункт More options и тот же wizard.
После смены проекта сохраняются его разделы/вкладки/поиски; повторный выбор
текущего проекта не перезагружает workspace.

get_project_catalog адаптирует project scope get_projects_and_logins и
ProjectModel preview priority: обычные проекты фильтруются штатным Security,
встроенные отмечаются отдельно. Snapshots icon/publish и файлы читаются пакетно;
выбираются versionless/latest image previews и используются HTTP пути File.
Repository Sync, локальные загрузки синка и его presets не добавлены.
Каталог обновляется при bootstrap и открытии созданного проекта; для изменений
каталога из другого клиента сейчас требуется перезагрузка страницы.

Проверены обычный пользователь с допуском только к одному проекту, отказ по
невалидному тикету, реальное превью, все три фильтра, категоризация, возврат
фокуса, 320 px touch и переключение с сохранением вкладок. XML-RPC неизменён.

## Пользователи

SecurityUsers.vue переносит AdminUsersView, AdminUserDetails и AdminUsersEditor
Handler. Каталог серверный, включает архивные аккаунты и preview через общий
UserIdentity/ItemPreview. Поиск по имени, логину и почте, фильтр архивных, выбор
профиля из уже загруженного каталога без дополнительного запроса. Вкладки
Profile / Account / Groups, контактные и технические поля, пароль, архивирование
и восстановление, все обычные группы с описанием, проектом и default marker.
Create/Reload/Discard/Save работают в общей шапке; перед сохранением есть
подтверждение, dirty/busy/неопределённый результат защищают смену раздела,
проекта и закрытие. Пароль не читается из БД в UI и очищается после сохранения,
смены сессии и уничтожения формы. Доступные поля определяются реальной схемой.

security_users.py адаптирует query_admin_users, create_user_profile и
mutate_user_profile к штатным Login.create/set_password/retire/reactivate,
add_to_group/remove_from_group и общей Command. Пустые поля создания сохраняют
нативные defaults, включая UPN и default group. Credentials и служебные поля
исключены из проекции каталога. SHA256 исходного аккаунта/членств проверяется
под общей блокировкой таблиц; конфликты не затирают внешние правки. Профиль,
пароль и группы записываются одной транзакцией с откатом. Нельзя сменить
существующий логин, архивировать текущий аккаунт или удалить своё членство
в группе admin. Нативные изменения пароля/архивирование аннулируют тикеты.
JSON read/save — /admin/security-users/{action}, XML-RPC не изменён.

На телефоне используются общий picker вкладок, одна колонка полей и общая
прокрутка страницы редактора вместо зажатой области формы. Все controls,
цвета, иконки и EN/RU общие. Проверены Chromium/touch 320 px, native lifecycle,
конфликт после внешней смены групп, пароль, retirement/recovery, откат и
отказ обычному пользователю на SQLite/PostgreSQL.

Согласованные исключения: license_type не возвращается; repository sync
и локальный кэш изображений Handler не переносятся — preview использует
существующие HTTP-пути. Как в Groups/Access Rules, действует admin-only policy;
небезопасная проверка supervisor по подстроке имени группы не переносится.
Это не утверждение о готовности остальных экранов/всего API.

## Редактор колонок

ColumnsEditor.vue переносит административный каталог ColumnsEditorView,
DefinitionCatalogEditor и DefinitionCatalogWizard Handler. Сохранены поиск по
view/type/code/login/category/widget_type, выбор SearchType, Wizard/XML, выбор
элемента, title/hidden/width/display widget, Reload/Discard/Save. Неизвестные
классы, параметры, атрибуты, комментарии и processing instructions сохраняются;
мастер меняет только выбранную настройку. Неподдержанный layout открывается
в режиме XML. Как в исходном экране, каталог редактирует существующие определения;
Create/Delete здесь отсутствуют. Полностью квалифицированный TableLayoutWdg
также распознаётся мастером, названия SearchTypes берутся из штатного поля.

columns_editor.py адаптирует каталог и save_catalog_xml из thlib/ui/columns_editor.py
к native Search/WidgetDbConfig/Command. Каталог читает исходный текст без запуска
Mako/HTML и может показывать определения, не поддержанные Vue-renderer. Запись
остаётся штатным commit(triggers=False); прежние identity/login/category/code
сохраняются. Ревизия включает содержимое и native журнал записей, проверяется под
блокировкой таблицы. Конфликт или ошибка записи не затирают исходный документ.
DTD/entities, некорректный XML и чужой проект отклоняются; доступ admin-only.
JSON /admin/columns-editor/{read|save}, XML-RPC и код Handler не изменены.

Edit columns / Edit input definitions доступны из общего меню представления,
открывают соответствующий документ и колонку. Закрытие возвращает workspace;
после сохранения затронутое представление перечитывается без пересборки Vue.
ConfiguredView применяет native hidden/width/title. Общие controls, темы, иконки
и EN/RU; на 320 px каталог и форма используют общую вертикальную прокрутку.
Проверены Chromium/touch, сохранение/фильтры/черновики, native SQLite/PostgreSQL,
внешние правки A→B→A, откат и отказ обычному пользователю.

Выбор display widget сохраняет исходный класс, но не означает готовность его
Vue-renderer: сложные ячейки и контекстное меню заголовка таблицы остаются в
следующем этапе таблиц. Неизвестные виджеты явно показываются как недоступные.

## Базовые виджеты ячеек

TableCell.vue следует TacticTableCellDisplay Handler: текст, native boolean
через AppCheckbox, форматированный текст и ссылка. Native FormatValueMixin
перенесён из legacy/tactic/core/format_value.py целиком; FormatElementWdg получает
оригинальные value/width методы, LinkElementWdg — metadata/column creation.
Оба публичных пути класса и widget aliases сохраняются. HTML не строится.
Исправлены устаревший locale.format, глобальная смена locale, date-объекты драйвера
и расчёт KB через currency slicing: последний использует уже исправленный
pyasm.common.FormatValue. Числовое округление, проценты, шаблоны даты, timecode,
локальные настройки timezone/DATE/DATETIME используют штатные алгоритмы.

describe_composition выдаёт типизированные дескрипторы поддержанных колонок.
Для format/link /admin/table-cells читает все выбранные записи пакетно через
native Search: не больше двух запросов на code/id группы, без SQL на каждую
ячейку. Порядок и дубликаты восстанавливаются явно; неизвестные/чужие ключи
отклоняются. Source XML читается на сервере; произвольные Python-классы из него
не импортируются и не запускаются. Для обычного текста и bool дополнительного
запроса нет. Ошибка одного форматтера остаётся в конкретной ячейке; ошибка
транспорта явно показывается, старый результат другого контекста не применяется.
Поддержаны HTTP(S), mailto и абсолютные локальные URL; executable URL schemes,
protocol-relative ссылки, backslash и управляющие символы не открываются.

Общий AppCheckbox используется для выбора страницы/строк, включая native
indeterminate. Заголовок открывает выбранный элемент Columns Editor через
явную touch-кнопку или ПКМ; workspace сохраняется. Ссылки и controls имеют
44 px зоны нажатия; тело таблицы использует общую Typography.body.
Проверены native SQLite/PostgreSQL, вызов widget через WidgetConfigView,
Chromium, один batch на страницу, выбор без повторной загрузки и 320 px touch.

Этот этап не завершает таблицы: Notes/Tasks/action widgets,
inline edit, summary/grouping, resize/reorder и полное контекстное меню ТХ ещё
не перенесены. Boolean ячейка пока только отображает значение, как исходный
boolean presenter ТХ. Неизвестные options/classes явно неподдержаны; их XML
сохраняется редактором. Доступ к configured UI остаётся admin-only; обычный
пользователь сохраняет существующий database browser. XML-RPC не изменён.

## Вычисляемые ячейки

ExpressionElementWdg, ExpressionValueElementWdg и ExpressionRecalculateCmd
перенесены из исходного tactic/ui/table/expression_element_wdg.py. Исходные
импорты, widget aliases, ARGS_KEYS и методы native SDK сохранены. get_text_value
использует alt_expression, return=single/list и display_format, записывает
результат на SObject в памяти, как в оригинале; сам ничего не коммитит.
Виртуальная вычисляемая колонка не требует физического поля в БД.

Vue получает get_cell_value через тот же /admin/table-cells. Выражения выполняет
существующий ExpressionParser: контекст проекта/пользователя, переменные объекта,
TSQL, absolute, show_retired и сохранённый use_cache. display_expression получает
переменную VALUE; value/boolean/check используют общий TableCell, AppCheckbox
и официальные иконки. Возвращается текст, не исполняемый HTML/JavaScript.
ExpressionValueElementWdg вычисляет выражение из значения физической колонки;
при отображении доступен env_sobjects['sobject'], как в исходном get_display.
SDK сохраняет исходное поведение get_text_value при ошибке: 0; Vue показывает
ошибку вычисления в ячейке. Вычисление Vue не меняет SObject и данные в БД.

calc_mode=fast рассчитывает словарь для всей страницы один раз на выражение.
Он хранится только в экземпляре колонки и сбрасывается при смене объектов или
options. Absolute и выражения с SOBJECT_ID/CODE выполняются в обычном режиме:
пакет с переменными первой строки давал бы неверные результаты. Для сортировки
простого @GET(.column) используется физическая колонка; произвольное вычисляемое
значение не выдаётся за сортируемый SQL столбец.

Исправления исходника: убран незакрытый Sudo, eval словаря заменён literal_eval,
поправлены lstrip('@GET('), обращение is_insert к списку, bool show_retired/cache,
соединение числовых/boolean списков и пересчёт, который повторно читал старый cache.
ExpressionRecalculateCmd вызывается штатным execute_cmd, получает definition,
пишет через SObject/Command с исходными проверками прав и триггерами. Ошибка одной
строки откатывает весь пересчёт. HTML методы остаются явно исключёнными.

Проверены native SDK и API, пакетный расчёт, переменные, формат/списки, отсутствие
утечки Sudo, сохранение и откат на SQLite/PostgreSQL; Chromium и touch 320 px.
Поддержка bottom/group_bottom, группировки, link_expression/link_view, icon mode
и JS eval listener не завершена; такие конфиги не объявляются готовыми. Нативные
metadata-флаги группировки сохранены, сама группировка таблицы ещё впереди.

## Превью файлов

ThumbWdg перенесён из legacy/src/pyasm/widget/file_wdg.py в исходный namespace
pyasm.widget. Сохранены ARGS_KEYS, native preprocess/get_data/get_info,
get_link_path/get_file_info/get_file_info_list и настройки экземпляра.
Выбор latest/version snapshot, каскад icon → publish context → publish process
→ любой context, прямые Snapshot и первый reference snapshot используют
существующие Snapshot/File/Search. Redirect/redirect_expr доступны native SDK;
Vue пока не объявляет эти параметры поддержанными. Deprecated ProdSetting
заменён действующим ProjectSetting; pyasm.prod не возвращается.

get_cell_value — новый типизированный результат для Vue, а не перенос HTML
get_display. Его image/files/context/version/snapshot_key получаются из того же
выбранного snapshot. get_text_value возвращает URL как расширение нового
renderer; старое извлечение текста из HTML не переносилось. Snapshot выбираются
пакетно для страницы, File читаются одним пакетом. Дубликаты объектов не запускают
лишние каскады. Сброс info/snapshot устраняет повтор превью предыдущей строки
при отсутствии файла. HTTP URL кодируются по компонентам, включая пробелы,
Unicode, # и ?; Windows pathname2url больше не ломает схему URL. Native словарь
по типу файла сохранён, дополнительный список содержит отдельный URL каждого
файла, включая несколько файлов одного типа. Пути используют прямые слеши.

TableCell использует общий ItemPreview и AppButton, открывает FilePreview
через native dialog. Превью, контекст/версия, имена/типы/размеры/пути и штатные
ссылки открытия/скачивания доступны без отдельного запроса. original выбирает
основной URL для изображения; filename/file_type управляют подписью ячейки.
Изображения raster загружаются лениво; повреждённое/отсутствующее изображение
имеет общую fallback-иконку. PDF/видео не выдаются за готовый media viewer:
исходные файлы можно открыть или скачать. Конфиги читаются сервером, Vue не
выполняет произвольные Python/JS классы. Browser protocol ограничен HTTP,
небезопасные URL отсекаются общим safe_link. Доступ configured UI admin-only.

Dialog вынесен Teleport в body, закрывается кнопкой/Escape, на 320 px занимает
экран и прокручивается. Исправлены абсолютные скрытые подписи общего checkbox:
горизонтальное перемещение таблицы больше не расширяет документ. EN/RU и
официальные иконки сохранены. Проверены upload/check-in → native SDK → ячейки
на SQLite/PostgreSQL, один batch snapshots/files, специальные символы URL,
отсутствующий snapshot, открытие/скачивание в Chromium и touch 320 px.
XML-RPC и исходники Handler не изменены. HTML/actions/detail/JS, произвольные
размеры thumbnail, версии в UI, media viewer и полные Notes/Tasks ещё впереди.

## Обсуждения и ячейка заметок

Из legacy/tactic/ui/widget/discussion_wdg.py перенесены вычислительные методы
DiscussionWdg, DiscussionElementWdg и команда DiscussionAddNoteCmd с исходным
call_triggers. HTML/JS методы и BaseRefreshWdg не импортируются: headless
DiscussionWdg использует существующее состояние BaseTableElementWdg. Сохранены
публичные module/package пути, ARGS_KEYS, get_notes/get_text_value и штатные
Search/Schema/Note. Выбор notes выполняется пакетно для страницы, через исходные
relationship filters, process/context и process ACL. Note.alter_search продолжает
фильтровать private notes. use_parent читает обсуждение родителя задачи/снимка;
счётчик Vue считает корневые заметки, ответы остаются в обсуждении.

Исправлены исходные unbound has_process для sobject option, накопление родителей
при повторном использовании и чтение всех notes при пустом списке родителей.
Boolean use_parent нормализован; смена options очищает прежний результат.
CSV export использует уже прочитанные ответы вместо запроса для каждой заметки
и принимает datetime от драйвера. Source selector bodies отдельно выполнены
без изменений над native объектами и сравнены по выбранным ID; это сравнение
алгоритма выборки, не запуск всего старого HTML runtime.

DiscussionAddNoteCmd сохраняет Note.create, нормализацию numeric context,
родительский FileCheckin(checkin_type='strict'), IconCreator и connection
context='attachment'. Note, Snapshot, File, connections и triggers участвуют
в общей транзакции. Проверка существования upload-файлов, containment и текущего
ticket проходит до записи. Повторяющиеся файлы запрещены. Отсутствующий process
для вложения берётся из созданной Note, вместо исходного None/attachment.
Ответ — дополнительный parent_id с проверкой исходного объекта и наследованием
процесса/контекста/access. Note.create получил необязательный access аргумент,
чтобы private ответ не публиковался даже в первом commit; прежние вызовы сохранены.
Email не реализован: mail_cc/mail_bcc явно отклоняются до
изменений; адреса не игнорируются и успех отправки не подделывается.

DiscussionReadCmd возвращает типизированные записи и HTTP-вложения из двух
штатных форм: Snapshot на Note и parent Snapshot с attachment connection.
DiscussionChangeNoteCmd адаптирует Handler change_note: собственная заметка
редактируется/удаляется в течение часа; чужая — действующим администратором.
Небезопасное разрешение supervisor по подстроке не переносится. Запись проверяет
revision под native блокировкой таблицы, сохраняет editHistory и выполняет
note.commit/delete через Command. Корневая заметка с ответами не удаляется,
пока ответы не удалены: исходный direct delete оставлял сирот. Native журнал
и triggers остаются активными. Поле note.metadata json добавлено в общий
business_upgrade для новой установки и upgrade SQLite/PostgreSQL; это
расширение для истории Handler, а не поле исходной seed-таблицы.

Vue NotesPanel открывается из XML DiscussionElementWdg через общий TableCell.
Процессы/счётчики и compact icon используют AppButton/официальные иконки.
Окно показывает timeline/ответы, редактирование/историю, подтверждение удаления,
скачивание/общее FilePreview; composer принимает файлы и clipboard images.
Enter отправляет, Ctrl+Enter добавляет строку. Черновики body/files/reply хранятся
в памяти отдельно по session/project/object/process/context и переживают закрытие
окна; новый пользователь не получает старый черновик. Неоднозначный сетевой
исход требует Refresh и проверки перед повтором, автоматического replay нет.
Поздний ответ чужого контекста не применяется. Всё проходит через существующий
execute_cmd/upload API, отдельный транспорт notes не добавлен. На 320 px —
полноэкранный dialog и общая вертикальная прокрутка; labels/errors имеют EN/RU.

Проверены native SQLite/PostgreSQL: lifecycle, ответы/use_parent, attachment
check-in и HTTP paths, stale revision, пустые/чужие uploads, отказ reader,
истечение edit window и откат notes/attachments/connections после trigger error.
Chromium проверяет черновики между объектами, отправку с файлом, ответ,
редактирование/историю/удаление, обновление счётчиков и touch 320 px.
Доступ configured UI/новым discussion commands пока admin-only.

Это рабочее обсуждение; следующая часть Task Inspector описана ниже.
Live updates, user avatars, связанные sObject ссылки, private UI, email и
остальные legacy display options пока не перенесены. В обычном NotesPanel
процесс выбирается из заметок/настроек колонки; в режиме задач — из pipeline.
Клиент хранит drafts только до перезагрузки, импортированные деревья отображает
до 50 уровней. Неизвестные options не объявляются поддержанными. Handler не менялся.
# Серверные зависимости виджетов задач

Перенесены вычислительные методы `TaskElementWdg` из
`legacy/src/tactic/ui/table/task_element_wdg.py`: ARGS_KEYS, подготовка задач
по Schema, фильтры process/context/parent_process, task_filter, порядок
процессов pipeline, виртуальные незаполненные задачи, права колонок,
назначения и цвета статусов. Публичные импорты класса и модуля сохранены.
`get_text_value()` возвращает исходный `context:status:assigned` CSV.
`get_cell_value()` дополнительно отдаёт данные задач с именами полей из
Handler `task_cell_records`: taskSearchKey/taskCode/process/context/status/
statusColor/assigned/bidStart/bidEnd. Виртуальные задачи явно имеют
`hasTask=false`, пустые ключи и не записываются в БД.

Исправлены игнорирование аргументов get_tasks, повторное использование
виртуальных объектов между родителями, накопление состояния при повторной
подготовке, изменение переданного списка processes и отсутствие проверки
прав процессов без pipeline. Подготовка выполняется один раз на страницу.
Глобальный Sudo и скрытые CGI-фильтры не перенесены; явный старый filter_data
вызывает UnsupportedContract, а не молча игнорируется.

Перенесены SObjectAttr и SimpleStatusAttr, исходная арифметика завершённости
TaskCompletionWdg: целые проценты статусов, устаревший статус как ноль в
среднем, порядок этапов без заданных процентов, None для отсутствующих задач.
Отбор задач и статусов использует существующие Search/Task/Pipeline и права
процессов. Пустые наборы задач кэшируются в пределах страницы; pipeline
разрешается один раз на уникальный код. SObjectConfig и универсальный
SObject.get_attr с разрешением пользовательских атрибутов этим переносом
не реализованы.

TaskCompletionWdg отображает вычисленный процент. TaskElementWdg показывает
кнопки конкретных задач и виртуальных процессов, открывающие Task Inspector.
Полный перенос TacticTaskCards и Task Inspector всё ещё **не завершён**:
hover/pinned preview и полный workspace задач остаются в текущем этапе.
Связанные объекты и progress-процессы инспектора перенесены ниже. Новые configured UI запросы
по-прежнему доступны только администраторам.

Проверки: tests/scripts/task_cells_contract.py внутри test_columns_editor —
SQLite/PostgreSQL, несколько задач одного процесса, исходный селектор на
нормальном сценарии, переданные аргументы, отсутствие N+1 для пустых строк,
виртуальные родители, ACL, нулевые/устаревшие/неявные проценты и task_expr.
Chromium использует существующий test_native_table_cells_in_chromium.
Handler не изменялся; тестовые записи живут в временных тестовых базах.

## Редактор задач и ветки обсуждения

Из Handler изучены TaskInspector.qml, TacticTaskCards.qml, communication.py,
tasks.py, workflow_data.py и справка dock.notes.en.md. Перенесён следующий
набор состояний: процесс pipeline, выбор конкретной задачи того же процесса,
редактор статуса/исполнителя/руководителя/дат/часов/прогресса/описания,
Discard/Save, создание отсутствующей задачи и переход к полной native форме,
сворачивание деталей, независимые черновики и ошибки сохранения.

TaskInspectorCmd использует существующий execute_cmd и native Task.commit,
Search, Pipeline и Security. Сохранение проходит через штатные права,
workflow, status_log и общий transaction rollback. Под table lock сверяется
ревизия задач процесса, родителя, pipeline и process workflow; stale revision
не перезаписывает изменения. Повтор создания с прежней ревизией отклоняется.
Workflow defaults соответствуют Handler: properties, начальный статус,
назначения, task pipeline, дни duration от начала часа, плановые часы,
целый прогресс с ограничением 0–100. Неконечные значения явно отклоняются.
Action/condition/dependency/progress не выдаются за обычные редактируемые задачи.

NotesPanel владеет запросами и черновиками, TaskDetails — presenter общих
controls. Selector задачи остаётся доступен при свернутых деталях. Выбор
задачи сохраняется в памяти отдельно по сессии/проекту/родителю/процессу;
сворачивание — в localStorage по пользователю. Основная ветка определяется
как в Handler: обычный context раньше суффиксов, затем timestamp/code.
Основная задача пишет notes родителю, дополнительные — собственной задаче.
Для единственной задачи объединяются сохранившиеся заметки обеих веток.
Статусные записи выбранной задачи отображаются в общей хронологии и не
получают действий редактирования заметок. Ответы, файлы, preview, изменение
и удаление notes используют существующие discussion commands.

Неоднозначный исход сохранения требует Refresh перед повтором; автоматического
replay нет. Поздние ответы другой сессии/проекта не применяются. Перезагрузка
страницы с несохранёнными черновиками вызывает native предупреждение браузера;
сами черновики остаются в памяти до перезагрузки. На 320 px поля идут в одну
колонку, всё окно прокручивается; controls имеют прежние touch targets и EN/RU.

Проверки task_cells_contract: SQLite/PostgreSQL, первичная/дополнительная и
одиночная ветки, точный task key и отказ чужому процессу, native status log,
workflow defaults, редактирование/создание, stale/repeated requests, неверные
поля/даты/логины/числа, rollback после native commit и отказ reader.
Chromium проверяет выбор/сворачивание/черновики/правку статуса/создание,
открытие полной native формы и touch 320 px. Исправлен Pipeline.get_process_names:
exclude теперь действует и без recurse, чтобы action-узлы не становились fillers.

## TaskElementCbk и операции над задачами

Перенесён callback из legacy/src/tactic/ui/table/task_element_wdg.py с публичными
путями tactic.ui.table.TaskElementCbk и tactic.ui.table.task_element_wdg.TaskElementCbk.
Сохранены set_sobject/set_data, JSON полей column|NEW|process, column|EDIT|id,
assigned|COPY|id_suffix и assigned|DELETE|id; bid означает bid_duration.
Поддержаны исходная вложенная web-форма data.data и web_data.process_data,
postprocess add_initial_tasks, обратный порядок создания процессов и отдельные
commit статусов, назначений, часов именно в исходной последовательности.
Clone/delete/commit идут через штатные SObject, права, триггеры и журнал.
Конкретные созданные объекты доступны через стандартный get_sobjects(); info
callback по-прежнему пустой. Для headless execute_cmd добавлены kwargs search_key,
data (JSON или dict), processes; пользовательский Python может использовать
исходные setters без изменений. Runtime не импортирует legacy или Handler.

Исправления исходника: NEW не теряется без скрытого process_data или при неполном
списке процессов; bid_duration|EDIT и bid|EDIT одинаково работают; входной список
порядка не изменяется; missing IDs проверяются множеством, повтор одного ID не
считается пропавшей задачей. Чужой родитель и невидимый процесс не принимаются.
Это намеренные отличия от ошибочного поведения оригинального callback.
DatabaseAction теперь вызывает конструктор Command: прямому API-запуску больше
не мешают отсутствующие transaction/update/pipeline поля. Общая правка проверена
также существующими тестами форм; дополнительный слой выполнения не добавлен.

TaskInspectorCmd copy/delete вызывает этот callback в той же транзакции и под
прежней проверкой ревизии. Vue позволяет выбрать исполнителя для отдельной копии
задачи, подтверждает удаление, сохраняет заметки и файлы вне операции удаления.
Копия выбирается по фактическому объекту callback, а не угадывается поиском после
триггеров. Отмена подтверждения не пишет в БД; удаление при неотправленной заметке
или вложении блокируется, включая изменения черновика уже после подтверждения.
Ошибки/неоднозначный исход/смена контекста используют прежние guards NotesPanel.
Новые UI действия admin-only; публичный callback использует native права без Sudo.

Проверки: нормальный NEW-сценарий исходного класса через AST на native ядре,
CRUD/copy/delete/initial tasks, JSON/setters/web-values, отсутствующие/чужие IDs,
process ACL, rollback после commit и неизменённый Python вызов с повторным чтением.
SQLite/PostgreSQL используют одинаковые ожидания; браузер — выбор исполнителя,
создание копии, отмену/подтверждение удаления и защиту черновика. Это не проверка
всего legacy runtime и не завершённый полный Task Inspector/TacticTaskCards.
Связанные объекты и progress-процессы добавлены в следующем разделе.
Следующие зависимости: hover/pinned панели, аватары и live updates. Handler не изменялся.

## Связанные задачи и progress-процессы инспектора

Из Handler взяты communication._load_related_tasks, TaskInspector.qml,
workflow_data.process_task_configuration и арифметика query_sobjects(include_progress).
Progress остаётся в выборе процессов и в исходном TaskElementWdg, но не становится
редактируемой задачей родителя. TaskInspectorCmd возвращает process_type и related;
save/copy/delete для progress отклоняются сервером. Публичные XML-RPC методы
и клиент Handler не менялись. Новая UI-команда по-прежнему admin-only.

Related Search Type определяется атрибутами узла, workflow и properties.
Связь выбирает штатный Schema/SObject.get_related_sobjects, включая обратное
направление и ID. Задачи читаются одним Task.get_by_sobjects на весь набор,
родители сопоставляются по реальным колонкам связи с Task, без угадывания code.
Коллизии кодов разных типов не смешиваются. Native Search скрывает retired записи;
применяется прежняя видимость процессов, foreign-project контекст отвергается.

Список показывает все доступные задачи связанных объектов, как в Handler;
счётчик отдельно применяет настроенный related process и статусы config/process
с непустым workflow.mapping. Это исходная арифметика: количество подходящих задач
делится на количество объектов, поэтому несколько исполнителей могут дать 3 / 2.
Это не процент завершённости. Без заданного related process считаются все задачи.
Без нужной настройки процесса/task pipeline счётчик не выдаётся за рассчитанный.
Кэш результатов БД не добавлен: изменение схемы/workflow/задач видно при Refresh.

NotesPanel владеет запросами и переходами; RelatedTasks — presenter общих controls.
Есть состояния unconfigured, missingType, unrelated, пустые объекты/пустые задачи
и обычный общий error с Refresh. Можно открыть точную связанную задачу и вернуться:
черновик заметки родителя и черновик задачи сохраняются независимо. Заметки progress
пишутся родителю через прежние native discussion commands. EN/RU, официальный
значок progress, тач-кнопки 44 px и одна прокрутка окна на 320 px сохранены.

Проверки: реальный созданный проект на SQLite и PostgreSQL, code/ID/reverse связи,
несколько исполнителей, исходная арифметика 3 / 2, ACL, неправильный Search Type,
нет связи/конфигурации, отсутствие N+1 задач, обновления схемы/workflow и удаление.
Chromium проверяет выбор progress, переход/возврат/черновики, отправку заметки,
пустую конфигурацию и тач 320 px. Тесты редактируют автоматически созданные
config/process вместо добавления дубликатов; рабочие данные не засевались.

Полный Inspector/TacticTaskCards всё ещё не завершён: hover/pinned preview,
аватары и live updates, object preview и встраивание WorkHoursSummary,
обновление выбранного scope отдельного Task Manager связанными объектами.

## Preview объекта и учёт времени в инспекторе

Из Handler перенесены арифметика WorkHoursController._summary, WorkHour,
WorkHoursSummary.qml и поля/операции WorkHourEditorDialog.qml, mutate_work_hour.
Native WorkHour сохраняет исходный SObject и defaults, теперь считает regular,
overtime и approved; overtime не суммируется дважды. Учитывается проектная
bid_duration_unit (hour/minute) через ProjectSetting. План, утверждённые часы,
ожидающие утверждения, остаток, перерасход и progress считаются из текущей БД.
Свёрнутая сводка показывает approved/planned, как Handler.

TaskInspectorCmd возвращает object и work_hours в том же запросе. Заголовок
объекта использует общий ItemPreview и исходный ThumbWdg, нажатие открывает
существующий FilePreview с метаданными объекта и файлами репозитория. Никакого
repository sync, локального скачивания или второго механизма выбора snapshot.
Для progress preview доступен, сводка времени отсутствует; без реальной задачи
время не записывается.

WorkHoursCmd читает и изменяет записи выбранной задачи через Search/WorkHour/
Command. Есть создание, редактирование, обычные/сверхурочные часы, дата,
исполнитель, описание, сохранение с утверждением, утверждение/отмена и удаление
с подтверждением. Изменение исполнителя действительно сохраняет login.
Проверяются типы, конечность чисел, точность 0.01 часа, диапазон и суммарный
лимит 24 часа за день в проекте, включая старые regular+over_time записи.
Запись другого проекта/задачи не принимается. Native commit/delete сохраняют
права, триггеры, журнал и rollback; исходная ревизия проверяется под блокировкой
таблицы work_hour, поэтому повтор создания не добавляет дубликат.

Исправлен общий Search.add_filter для day-колонок: SObject хранит их без
UTC-сдвига, и фильтр также сохраняет календарную дату. Раньше Windows UTC+3
сдвигал начало суток и пропускал записи в проверке дневного лимита.
Остальные timestamp-фильтры сохраняют прежнее преобразование часового пояса.
Ожидаемые ошибки команды используют штатный UserException, чтобы JSON UI
показывал причину отказа. XML-RPC сигнатуры и Handler не изменялись.

NotesPanel владеет запросами и черновиком, WorkHoursSummary/TimeEntryPanel —
presenters общих controls. Незавершённый ввод не теряется при отказе сервера;
неизвестный результат записи требует Refresh, устаревшая ревизия не заменяется
автоматически. Контекст и задача проверяются при получении ответа. Есть EN/RU,
native date/number, keyboard/Escape, тач 44 px и одна прокрутка окна на 320 px.
Как прочие configured UI commands, новый путь пока admin-only. Ставки/зарплаты
не возвращаются. Рабочие базы не засевались тестовыми записями.

Проверки: SQLite и PostgreSQL, арифметика и legacy overtime, дневной лимит,
NaN/дата/исполнитель/поля, другая задача, stale/retry, rollback после commit,
отказ неадминистратору. Chromium: реальный snapshot preview, create/edit/
approve/delete, читаемая ошибка лимита, сохранение полей задачи и тач 320 px.

Это табель выбранной задачи. Общий недельный Timesheet Handler с выбором
пользователей/проектов, групповыми операциями и отчётами ещё не перенесён.
Полный Inspector всё ещё ждёт hover/pinned preview, аватаров/live updates
и расширения scope отдельного Task Manager связанными объектами.

## Недельный табель и отчёты

Перенесены операции TimesheetView.qml, WorkReportsView.qml и их серверные
процедуры из Handler: понедельник–воскресенье, произвольная дата недели,
Previous/Next, выбор сотрудника, общие Logged/Approved/Pending/Overtime,
индивидуальные edit/approve/revoke/delete, множественный выбор, массовое
утверждение/возврат в pending и Clear selection. Удаление подтверждается;
черновик защищён при Close/Escape, ошибке и Refresh. Выделение сбрасывается
после успешной перезагрузки списка, как в Handler.

Шесть отчётов: My Work Hours, Bid vs Actual, Approval, Team Hours,
Process Hours и Labor Cost. Сохранены группы, дата/пользователь и доли полос;
My Hours без выбранного пользователя показывает текущего пользователя.
Командные/процессные/стоимостные отчёты охватывают текущий проект, как исходная
процедура. Labor Cost отдельно проверяет штатное право чтения hourly_wage,
недоступный отчёт исключается из каталога. Не возвращаются отдельные ставки,
пароли или другие данные Login. Отсутствие ставок отображается явно.

Исправлены ошибки исходной арифметики: отчёты включают legacy regular+over_time,
не удваивают overtime и используют Decimal; недельный диапазон включает всё
воскресенье, а не только полуночь. Bid vs Actual действительно сравнивает
planned и logged, как серверный исходник, поэтому описание уточнено. План
учитывает bid_duration_unit через ProjectSetting. Кэша результатов БД нет.

WorkHoursCmd имеет режимы task/week/report; прежний task-вызов сохраняется.
Недельные записи читаются вместе, задачи — одним пакетным Search. Исторические
записи без задачи видны и допускают approve/revoke/delete, но не выдают edit
за работающий. Идентичности, проекты и процессы проверяются сервером; записи
другой недели/пользователя не попадают в массовую операцию. Все записи меняются
одной native Command-транзакцией под прежней блокировкой work_hour; ошибка
после второго commit откатывает всю группу. Revision включает неделю, фильтр,
записи и задачи. При наличии активной задачи включается её полная ревизия
учёта времени, чтобы создание вне отображаемой недели/пользователя также
защищалось от повторов. Фильтр сотрудника отделён от login редактируемой записи.

Timesheet.vue теперь единственный владелец запросов/черновика; NotesPanel
передаёт контекст и слушает сохранение. TimeEntryPanel остаётся presenter
общих AppButton/AppSelect/AppCheckbox и native date/number. Open timesheet
в инспекторе открывает недельный режим, Log time — тот же редактор записи.
В More options приложения доступен Weekly timesheet для текущего проекта.
Без активной задачи Log time отключён, как в Handler. После появления общего
Task Manager нужно связать его выделенную задачу с этим входом. Сейчас новую
запись можно добавить из инспектора, а существующую — редактировать в табеле.

EN/RU, официальный набор иконок, тач 44 px, keyboard/Escape, компактная сводка
2×2 и одна прокрутка окна на 320 px. Generic CSS dialog ограничен его шапкой
и простыми definition lists: он больше не перекрывает styled summaries и
вложенные заголовки. Project switch/logout инвалидируют контекст запросов.
Неизвестный результат записи требует Refresh; revision черновика не обновляется
автоматически. Штатный configured UI по-прежнему admin-only; supervisor/finance
доступ без admin и единый dock workspace остаются отдельным незавершённым этапом.
XML-RPC сигнатуры и Handler не менялись; ProdSetting/repository sync не добавлены.

Проверки SQLite/PostgreSQL: нормализация недели, всё воскресенье, другой проект,
историческая запись, выбор сотрудника, отсутствие N+1 задач, bulk rollback,
stale/retry вне недели, шесть отчётов, минуты, ставки и запрет доступа. Chromium:
standalone вход, дата/Previous/Next/user, выбор и массовые изменения, редактор,
черновик при Escape, отчёты и обе панели на тач 320 px. Все fixtures временные;
рабочие проекты и ставки не менялись.

## Участники и обновление инспектора

Из communication._record/_status_record и user_identity Handler перенесено
отображение участников обсуждения, истории статусов и исполнителей задачи:
display name, login, initials, стабильный цвет, аватар из native icon/publish
snapshot. Используется существующий UserIdentity/ItemPreview. Проекция
user_identities выделена из уже перенесённого каталога групп и используется
там же; пароли, ставки и поля аккаунта в обсуждение не возвращаются. Retired
участники сохраняют идентичность в истории, неизвестный login остаётся виден.
Аватары выбираются штатным Snapshot, ссылки проходят общий safe_link.

DiscussionReadCmd получает только участников выбранного обсуждения.
TaskInspectorCmd собирает авторов, историю и исполнителей всех веток в один
пакет идентичностей, без повторного чтения аватаров для каждого сообщения.
У progress процесса есть тот же общий timeline с идентичностями.

Открытый NotesPanel обновляется каждые 30 секунд и при возвращении видимой
вкладки браузера. Перекрывающиеся запросы, скрытая вкладка, закрытый инспектор,
дочерний диалог, редактирование самой заметки, подтверждение операции и
неизвестный результат записи приостанавливают автоматическое чтение.
Task/note drafts не заменяются полученными данными: их исходные revision и
baseline сохраняются. Новые заметки/статусы/часы/профили обновляются в текущем
контексте. Timeline следует за концом только если пользователь уже там;
ручная прокрутка сохраняется. Ошибка автообновления показана отдельно и не
стирает ошибку редактирования; повтор через Refresh. Конфликт revision задачи
использует UserException, чтобы UI показывал причину отказа без traceback.

Проверены проекция и единый пакет участников, SQLite/PostgreSQL; Chromium
с настоящим avatar snapshot и правками из второго клиента, появление новой
заметки, сохранность двух черновиков, отказ устаревшему save, прекращение
запросов после закрытия и тач 320 px. Рабочие БД не засевались fixtures.

Это обновление открытого инспектора, не общий ServerUpdateService из Handler:
единый batched poll приложения/его настройка ещё не перенесены. Вход в профиль,
аватары/счётчики внутри task picker и отдельный Task
Manager с его scope остаются незавершёнными. Configured UI пока admin-only;
Handler и публичные XML-RPC сигнатуры не менялись.

## Preview задач в ячейке

Из Handler TacticTaskCell перенесены открытие по наведению через 260 мс,
закрытие через 180 мс после ухода указателя, закрепление и закрытие при
прокрутке таблицы. Явная кнопка открывает закреплённый список на таче и с
клавиатуры. Native popover закрывается по Escape и нажатию снаружи; карточки
прокручиваются внутри него горизонтально, включая экран 320 px.

TaskCell и TaskCards — presenters без API. Карточки показывают процесс,
контекст, цвет статуса/процесса, исполнителя с аватаром и плановые даты.
TaskElementWdg добавляет идентичности одним пакетом для всей страницы,
используя существующую безопасную проекцию user_identities.
Пакетное чтение ячеек сохраняет project qualifier входящих code/id keys:
раньше bare lookup в admin терял связи с кастомными Task/Snapshot и показывал
виртуальные задачи вместо существующих. Общая загрузка исправлена, без
изменения публичной семантики Project.get_full_search_type.

Нажатие заголовка задачи открывает Task Inspector. Быстрые действия статуса,
исполнителя и дат открывают один общий TaskTableEditor. TaskField переиспользует
те же контроллы в Inspector и таблице; presenter не делает запросов.
ConfiguredView готовит пакет и хранит черновики. При выделении нескольких
строк правка применяется к выделенным родителям с тем же process/context,
как set_task_value из Handler columns_editor.py. Точная задача исходной ячейки
сохраняется и при id/code alias; у остальных родителей выбирается задача с
тем же context. Виртуальная задача не записывается до Save.

Общая панель Save/Discard перенесена из SearchResultTable.qml. Черновики
сохраняются между вкладками, отмена удаления рабочей области защищает их от
потери, beforeunload предупреждает при выходе. Панель остаётся видимой при
горизонтальной прокрутке на 320 px. Поповер закрывается при прокрутке страницы
и resize, допускает прокрутку внутри своего содержимого.

TaskTableEditCmd использует штатные правила Inspector, native Search/Task,
права полей и процесса, revisions и Command. Весь пакет проверяется до записи
и сохраняется одной транзакцией с обычными triggers и журналом; поздняя ошибка
откатывает весь пакет. Устаревшие revisions не позволяют повторно создать
виртуальную задачу. При потерянном ответе повторный Save блокируется; явный
Check сверяет серверное состояние с исходной revision и желаемыми значениями.
Только подтверждённое unchanged позволяет повторить запись; saved очищает
черновики, conflict или ошибка проверки сохраняют блокировку и черновик.

Отдельный Task Manager, advanced/Gantt pending bar и QML pooling/release
coordinator пока не перенесены. Configured UI остаётся admin-only; Handler и
публичные XML-RPC сигнатуры не менялись. Repository sync не переносится.

Проверки: native SQLite/PostgreSQL, смешанные code/id keys, единый пакет
исполнителей без секретных полей; Chromium — hover/pin/unpin, Escape,
клавиатурный вход и фокус, закрытие при прокрутке, тач 320 px, точная задача,
сохранение исполнителя/дат и обновление ячейки после native Save. Дополнительно:
SQLite/PostgreSQL — пакет существующих/виртуальных задач, повтор Save,
невалидная последняя строка, поздняя ошибка commit, ACL и конфликт revision;
Chromium — staged Save/Discard, несколько строк, сохранение между вкладками,
потерянный ответ с успешной проверкой и общий редактор на 320 px.

## Task Manager: серверная загрузка и области

Изучены TasksWorkspaceView/TaskDockView, TasksController, TaskWorkspaceStore,
field_catalog и контракт Task Inspector/веток заметок Handler. Полный экран
включает области object/multiple/search_type/user/team/project, страницы и
scope-wide facets, фильтры/quick presets, sort/group, видимые колонки, выбор и
массовые операции, staged create/edit/delete, конфликты, переходы к объекту,
Inspector/заметкам/табелю, milestones, календарь и Gantt с изменением расписания,
undo/redo, working days/resource mode. Этот экран пока НЕ перенесён целиком.

Завершён общий серверный блок чтения: TaskWorkspaceCmd в исходном разделе
tactic/ui/table, через существующий execute_cmd. Пакетная процедура
query_task_workspace_page взята из Handler целиком: заменены только
server.set_project на проверку текущего проекта, SDK-сериализация на её
нативный метод и JSON-строка на словарь. Для чтения нет Mako-компиляции и
runtime импортов Handler. Scope-фильтры адаптированы из TaskWorkspaceStore.

Вход: action=read (default), scope=object (default), identity (search key,
SearchType, login или group code согласно scope), search_keys для multiple,
limit=1..500 (default 100), offset>=0 и query. Query принимает filters,
quickFilters, sort/group/descending, today и scopeProcess. Свободные SQL/filters,
подмена текущего login и переданные клиентом labels не принимаются; подписи
сотрудников читаются из native Login. Область project всегда ограничена
текущим проектом. Пустой выбор объектов или пустая группа не раскрывает весь
проект. Parent id/code keys разрешаются штатным Search. Типы без кода пока
явно отклоняются, а не показывают чужие задачи.

Ответ: tasks, parents, total, facets, offset, limit плюс scope/identity,
loaded и hasMore. Facets относятся ко всей области до пользовательских
фильтров; task badges сохраняют исходное владение root/contextual notes.
Process ACL применяется до загрузки rows, totals и facets. Новая команда
пока admin-only, как остальные configured UI команды; native read/column/row
permissions и serializer остаются общими. Публичные XML-RPC сигнатуры и ТХ
не изменялись; repository sync не возвращается.

Проверки на временных SQLite/PostgreSQL: все шесть scopes, родительские
id aliases, страницы, пустые области, note branch counts, ограничения ввода,
доступ и восемь сортировок/группировка в сравнении с неизменённым скриптом ТХ.
Проверен также существующий XML-RPC execute_cmd. Рабочие проекты не засевались.
Каталог полей и staged CRUD описаны ниже. Следующий блок — полное
Vue-представление Task Manager; новый незавершённый экран не добавлен.

## Task Manager: каталог полей и пакетные изменения

TaskWorkspaceCmd action=catalog принимает необязательный search_key родителя.
Возвращает priorityChoices, milestoneChoices, fields с editable, processes,
users/teams (только коды и подписи), project, parent_key и revision.
Приоритет разрешается штатным EditWdg из XML
insert-конфига, включая выражения values/labels; значение 0 сохраняется.
Milestones читаются из текущего проекта, процессы и поля учитывают native ACL.
В runtime нет импорта Handler, генерации HTML или компиляции Mako.

TaskWorkspaceEditCmd через тот же execute_cmd принимает action=prepare/save
и plans из 1..500 записей. Каждая запись: operation=create/update/delete,
search_key родителя, process; для create — draft_id и необязательный context,
для update/delete — точный task_key. Prepare ничего не записывает: возвращает
форму, workflow defaults, доступные статусы/пользователей/поля и revisions.
Save принимает эти plans с data; delete вместо data требует related_types.

Общие правила Task Inspector проверяют статус, пользователей, плановые даты,
часы, прогресс и права полей. Дополнительные process/context/priority/milestone
проверяются в этом же native пути. Смена процесса новой задачи требует нового
Prepare, чтобы применить его workflow defaults. Весь пакет проверяется до
записи и сохраняется одной Command-транзакцией с Task.commit и обычными triggers.
Поздняя ошибка commit/delete откатывает предшествующие операции. Устаревший
пакет, включая повтор уже сохранённого create, отклоняется; смена конфигурации
или milestones A → B → A также обнаруживается через штатный журнал.

Удаление использует существующие read_deletion и DeleteCmd: Prepare возвращает
зависимости и deletion_revision, Save — явно выбранные related_types. Пустой
список не выбирает дочерние записи; обязательные внутренние действия остаются
штатными. Изменение зависимостей требует повторного preview. Используются
native права, журнал, FileUndo и транзакции, отдельного SQL DELETE нет.

Проверено на временных SQLite/PostgreSQL: несколько новых задач с разными
context, отсутствие записей до Save, отказ повтора, изменения процесса/приоритета,
права полей, конфликт справочника, изменение зависимости, поздний сбой commit
и delete, полный rollback. Создание/изменение/удаление прошло через XML-RPC.
Команды пока admin-only. Полный перенос Task Manager, selection
bridge и подтверждение исхода после потерянного ответа остаются незавершёнными;
долговечная квитанция операции для этой команды пока не реализована.

## Task Manager: рабочая таблица Vue — частичный перенос экрана

Вход в таблицу — Task Manager в общем меню приложения; Tasks for selected
objects в меню выделенных записей открывает object/multiple scope того же
проекта. Отдельный полноэкранный dialog не меняет рабочие вкладки и sidebar.
TaskManager владеет запросами, черновиками, выбором и контекстом;
TaskWorkspaceTable/TaskWorkspaceEditor — presenters без API. Они используют
AppButton/AppSelect/AppCheckbox и общий TaskField. Язык/темы/иконки общие.

Работают project/user/team/selected/SearchType scopes, страницы 20..500,
scope-wide facets и quick presets, поиск, deadline/notes/колоночные фильтры,
sort/group/collapse, выбор видимых колонок и нескольких задач. Заголовок
Object остаётся обязательным. На 320 px таблица занимает оставшуюся высоту
dialog и прокручивается внутри себя; фильтры/настройки раскрываются отдельно.

Create/Edit/Bulk/Delete готовятся native командами и остаются черновиками до
Save. В массовой форме применяются только явно включённые поля с пересечением
доступных вариантов/прав. Смена процесса новой задачи повторно читает его
defaults, сохраняя description/priority/milestone. Неизменённый пустой статус
не записывается вместо штатного default. Draft identity работает и на LAN HTTP,
без обязательного crypto.randomUUID/secure context. Удаление показывает штатные
зависимости с явным выбором, тоже до Save. Inspector/заметки и табель времени
переиспользуются из существующих экранов; переход к объекту использует хост.

Refresh/смена области не переписывают revisions черновиков. Ошибка сохраняет
черновик. Reload draft revisions показывает текущие серверные и локальные
значения; принятие новых revisions и Save — отдельные действия. Зависимости
удаления после конфликта требуют нового preview. Потерянный ответ блокирует
повторную запись; черновик не теряется, доступны Refresh и явный Discard.
Автоматическое доказательство saved/unchanged для нового Manager пока не готово.
Закрытие, Escape и beforeunload защищают черновики и текущую запись.

Проверка Chromium на временной SQLite: массовый edit, виртуальная create,
staged delete, native Save, concurrent edit/review/rebase, потерянный ответ,
Inspector/табель, 320 px, touch и отсутствие page errors. Native catalog/CRUD
прошли PostgreSQL. Рабочие проекты не засевались, Handler не изменён.

Перенос Task Manager НЕ завершён целиком. Milestones, inline/expanded строки,
порядок/ширина колонок и keyboard range selection описаны в следующих блоках.
Остаются сохранение dock sessions и общий live-update/selection bridge. Repository sync
в него не входит. Границы календаря/Gantt описаны ниже.

### Календарь и Gantt Task Manager — рабочий блок частичного экрана

TaskScheduleView — presenter без API/черновиков; TaskManager остаётся владельцем
запросов, выбранных задач, всех черновиков и Save. Таблица/календарь/Gantt
переключаются в одном workspace. Native TaskScheduleCmd получает только уже
загруженные данные представления: он не читает БД и не даёт разрешений на запись.
Предел — 500 задач/вех, ограниченный диапазон и объём преобразований. Команда
admin-only, как текущие workspace команды. Сохранение проходит прежними
TaskWorkspaceEditCmd/Task.commit, с проверкой прав полей, workflow, конфигов,
исходной ревизии, триггерами, журналом и атомарным rollback.

В task_schedule.py целиком извлечены исходные parse_datetime/progress_value/
due_state/calendar_cells/gantt_layout и все функции gantt_schedule.py из ТХ.
Qt, Handler runtime и дополнительная модель Task не требуются. Поведение дат
сохранено: перемещение меняет календарную дату, сохраняет часы/минуты/секунды;
исходный parser ТХ не сохраняет timezone/subseconds. Working days здесь означает
понедельник–пятницу, как в исходном ТХ, без календаря праздников.

Календарь: шестинедельная сетка с понедельника, текущий день, прямой выбор месяца,
предыдущий/следующий месяц, native фильтр по deadline выбранного дня, сброс,
задачи/вехи и вход в общий Inspector. На телефоне видны все семь колонок,
счётчики и прокручиваемый список задач выбранного дня; действия доступны тапом.

Gantt: запланированные/неполные даты отдельными секциями, группы/collapse,
progress, диапазон/ticks/weekends/today/milestones, обзор и переход по шкале,
масштабы days/weeks/months/quarters/fit, zoom и предупреждения исходного ТХ
(срок/выходные/отсутствие исполнителя/пересечение загрузки). Resource mode
временно включает сортировку/группы по login, при выключении восстанавливает
предыдущее состояние. Метки разных пользователей не объединяют их identities.

Даты/длительность/прогресс редактируются явной формой с полевыми правами и
черновиком до Save. Мышью можно двигать и менять края полосы; перенос выделенных
задач использует shifted_selection_edits, тач использует ту же форму и кнопку
Move selected tasks together. Массовые shift/align/extend/shorten/sequence
используют исходные batch_schedule_edits. Undo/redo (до 50 состояний и Ctrl+Z /
Ctrl+Shift+Z) меняет только даты/прогресс и сохраняет description/остальные поля.
Save/Discard/rebase/структурные изменения сбрасывают историю. Ошибки оставляют
черновики; потерянный ответ по-прежнему блокирует повтор записи.

Оба вида честно показывают текущую загруженную страницу, как bounded workspace,
а не выдают её за весь проект: при offset/hasMore есть пояснение. Проекции
обновляются из текущих черновиков; устаревший асинхронный ответ не заменяет новый.

Проверено: сравнение чистых функций с неизменённым исходным ТХ; native projection,
transform и Save дат/прогресса на временных SQLite/PostgreSQL; Chromium —
weekday shift, сохранение времени суток, drag нескольких задач, undo/redo с
другими черновиками, progress, resource mode, native day filter и touch 320 px.
Рабочие базы не засевались, ТХ не менялся, зависимостей не добавлено.

Полный перенос Task Manager и всех деталей Gantt ещё не завершён: остаются
progress drag handle, расширенные mouse/keyboard selection
и pinned/preview/цвета pipeline, dock sessions/live-update/selection bridge,
автоматическое подтверждение исхода неизвестной записи и перечисленные выше
операции таблицы. Они не объявляются готовыми наличием трёх переключаемых видов.

### Вехи проекта

Перенесены MilestoneController и MilestoneManagerView.qml из ТХ: поиск,
создание нескольких черновиков, редактирование названия/срока, отдельные Save,
Discard и Delete для каждой строки, подтверждения закрытия/обновления/удаления,
план связанных задач (completion по native status pipeline, завершённые,
просроченные, начало плана, процессы и сумма часов), пустые/ошибочные состояния.
MilestoneManager владеет API и черновиками; MilestonePanel только отображает их.
Открытие из Task Manager, поля вехи и маркеров календаря/Gantt ведёт к одному
редактору. Изменения существующей вехи видны на маркерах до Save; новые маркеры
появляются после сохранения, как в ТХ. Привязка задач остаётся штатным task Save.

Нативная MilestoneCmd работает через Search/Milestone/Command. Один запрос
читает связанные задачи для всех вех, без N+1. Учитываются права на поля и
процессы. Ревизия каждой вехи включает штатный change_timestamp с transaction_code
и ловит A→B→A; независимые строки не конфликтуют после сохранения другой строки.
Создание не перезаписывает существующий объект: дубли имён проверяются сервером
под блокировкой. После успешной записи выполняется чтение уже завершённого
журнала, при этом остальные черновики сохраняют исходные ревизии. Конфликт
требует явного просмотра и принятия текущей ревизии; неизвестный результат
записи блокирует повтор до просмотра серверных данных и отмены черновика.

Исправлены ошибки исходного контроллера: новый draft получает настоящий native
код после Save даже при других несохранённых строках (повторный insert не
происходит); удаление учитывает retired-задачи, которые могут быть восстановлены;
NaN/Infinity не попадают в статистику. Late commit failure откатывается штатным
Command вместе с триггерами/журналом. ТХ не изменён, sync-репозиториев нет.

Проверки: временные SQLite/PostgreSQL — CRUD, native ABA, duplicate/date validation,
ACL и rollback; Chromium — несколько новых/существующих drafts, конфликты,
поиск/удаление, привязка задач, общие маркеры, потерянный ответ создания без
повторного insert, desktop и touch 320 px. Полный
Task Manager остаётся незавершённым в перечисленных выше областях.

### Таблица Task Manager: раскрытие, ячейки, выделение и колонки

Поведение адаптировано из TaskBrowserTable.qml, TaskHiddenDetails.qml и
TasksController. Раскрытая строка показывает все native editable fields,
включая priority/milestone/supervisor, независимо от компактных колонок.
Нажатие ячейки открывает редактор соответствующих полей; на таче доступны
те же действия. Используется один TaskWorkspaceEditor/TaskField и общий
черновик TaskManager для таблицы, Calendar и Gantt. Ввод сразу меняет
черновик, запись выполняется только общей native prepare/save командой.
Отдельного Save строки нет. Исходные revisions и field rights сохраняются;
обновление метаданных не принимает серверные revisions за пользователя.
После Save/Discard раскрытые строки перечитываются одним prepare-пакетом.

Активная строка отделена от массового выбора. Работают Ctrl/Meta toggle,
Shift range, checkbox selection, Home/End/стрелки, Space и Ctrl/Meta+A.
Select all относится к видимым строкам; выделение свёрнутых групп сохраняется.
Порядок, видимость и ширина колонок сохраняются для пользователя и проекта
в localStorage; обязательный Object, известные уникальные keys и диапазон
40..480 сохраняют исходные правила нормализации. Для зоны нажатия ширина
отображаемой колонки не меньше 48 px. Есть мышиный/клавиатурный resize,
доступный тач-ввод ширины, перемещение колонок и Reset. Меню заголовка
содержит sort/group/hide; те же настройки доступны общей кнопкой колонок.
Hover-редактор Qt заменён явным нажатием; drag-reorder заменён доступными
кнопками перемещения. Escape закрывает редактор ячейки, уже введённые правки
остаются общим черновиком до Save/Discard.

Chromium на временной SQLite проверяет общий expanded/inline draft, Save,
Discard, Ctrl/Shift/keyboard selection, свёрнутые группы, сохранение настроек,
mouse/keyboard resize и touch 320 px. Native write contract не менялся;
его SQLite/PostgreSQL проверки описаны выше. Полный экран ещё не завершён:
дополнительные детали Gantt, dock sessions, shared live-update/selection bridge
и автоматическое подтверждение неизвестного результата записи остаются.

### Главное окно: сверка с живым Handler, 8 октября 2026

Перенос всего главного окна пока не завершён. Текущий блок приводит общую
оболочку к Main.qml, SearchWorkspaceView.qml, NavigationDrawer.qml и ActionMenu:
шапка 44 px, поиск/вкладки 48 px, футер 58 px, project control 36 px,
menu rows compactControlHeight с padding 6 px, spacing 1 px и menuRadius.
Размеры контролов соответствуют Handler; прежний минимум touch 44 px отменён
пользователем в пользу масштабирования браузера. Один общий стиль popup меню,
официальные наборы иконок, EN/RU для статуса подключения. Configuration и
Administration первые в меню. Repository Sync Queue по-прежнему исключена.

Sidebar открывается поверх рабочего пространства; лишние заголовок, фильтр
SearchTypes и технические подписи убраны. Карандаш открывает настоящий Sidebar
Editor с независимыми источниками TH/TACTIC. Saved searches перенесены к кнопке
фильтра перед вкладками, сортировка — справа на полосе вкладок, справка — рядом
с поиском. Те же операции доступны в административных таблицах. Запросами,
фильтрами, сортировкой и состоянием вкладок по-прежнему владеет App.

Снимок реально открытого Handler: `.screenshots/main-parity/handler-main.png`.
На момент захвата в нём открыт Tasks dock; это не старый скриншот документации.
Browser captures на текущем UI Test, Collection и реальной Windows SQLite:
`stream-main-after.png`, `stream-menu-after.png`, `stream-navigation-after.png`,
`stream-mobile-after.png` в том же каталоге. Desktop viewport 1707×996,
deviceScaleFactor 1.5; мобильный 360×740. Команды: `python -B
tools/capture_handler_ui.py` из корня и `node tests/capture_main.mjs
http://192.168.2.55:8081 after` из frontend; второй использует viewport.json
первого. Browser закрывается в finally, тестовые серверы — teardown Transport.
Проверки workspace tabs и project navigation проходят на временной SQLite,
включая drafts/selection/scroll, переключение проектов, touch 320 и редактор.

Остаются профили лейаута и остальные dock-панели, script shelf, tags, дополнительные режимы
результатов и загрузки, полный набор действий главного меню, точный total count,
формы и содержимое Task Manager/Task Inspector. Снимки этих двух экранов и меню,
присланные пользователем сегодня, являются отдельными актуальными ориентирами;
похожая шапка и работающие кнопки не означают полного переноса экрана.

### Главное меню и сохранность рабочего состояния, 8 октября 2026

По `menu_schema.py` и controllers lifecycle/navigation/connection перенесены
Save Preferences и Reload Cache. Первое явно сохраняет существующие настройки
оформления и пользовательские вкладки в браузере, сообщает об ошибке storage;
не записывает записи, тикеты, выделение и черновики в БД. Второе обновляет
каталог проектов, SearchTypes, navigation и текущие данные, не пересоздавая
Vue-вкладки и их черновики. Поздний ответ после смены проекта/вкладки или
открытия админки игнорируется; сетевая ошибка оставляет рабочее состояние.
Закрытие админки восстанавливает scroll после DOM flush, скрытая область
не перезаписывает сохранённую прокрутку нулём.

Общий control AppMenu на native details заменил локальные command menus:
главное, user, view, selection, sort и search tabs. Поведение ActionMenu:
ArrowUp/Down с обходом disabled, Home/End, Escape с возвратом фокуса,
закрытие после команды и по нажатию снаружи. Popup ограничивается шириной
экрана. Controls не вызывают API. Размеры SectionTabRail взяты из QML:
row 42, button 38, badge 30, gap 3 и padding 7 px. Удалена мобильная
циклическая зависимость control-height/touch-target; рабочая область изолирует
свои sticky layers, чтобы pending changes не перекрывали главное меню.

Focused Chromium проверки на отдельных временных SQLite: workspace tabs
(storage failure, network failure, поздний ответ, selection/scroll и touch 320)
и native table cells (реальный task draft после Reload Cache и последующий
Save/Discard). Каждую команду запускают отдельным процессом, поскольку native
cells устанавливает собственный sidebar в общей fixture Transport:
`python -B -m unittest test_transport.Transport.test_workspace_tabs_in_chromium`
и `python -B -m unittest test_transport.Transport.test_native_table_cells_in_chromium`.
Снимки `stream-*-after.png` обновлены с работающего Windows экземпляра.
Test server и браузер завершаются teardown/finally.

Главное окно остаётся незавершённым. Current view to All Tabs в Handler копирует
режим результатов и splitter ratio; Reset workspace layout сбрасывает docks
и tool windows. Reset теперь реализован для перенесённых dock-панелей (ниже).
Current view to All Tabs требует переноса соответствующего состояния,
его нельзя заменять копированием фильтров или закрытием вкладок. Остальные
границы готовности перечислены в предыдущем блоке.

### Dock-хост главного окна, 8 октября 2026

`features/workspace/DockWorkspace.vue` размещает существующие результаты,
Task Manager и Commit Queue. Основой служат DockHost.qml, DockPanel.qml,
DockMenu.qml и workspace_models/docks_tree.py, docks_records.py,
docks_placement.py Handler; SHA-256 зафиксированы в source_manifest.json.
`docks.js` сохраняет исходную форму stack/split дерева, схлопывание пустых
веток, размещение относительно панели и активную вкладку stack.
Root right использует 66/34, root center и относительные splits — 50/50.

Доступны left/right/top/bottom, объединение в stack и swap, перетаскивание,
floating внутри рабочей области, maximize/restore, shared splitter и resize.
Splitter и floating resize доступны с клавиатуры. Pointer cancel возвращает
предыдущую геометрию и режим maximize. Скрытая панель остаётся в дереве;
проекция видимых панелей освобождает её место. Vue Teleport переносит уже
существующие экраны, не создавая второй контроллер запросов или черновиков.
Скрытие и Reset не закрывают поисковые вкладки и не удаляют task drafts или
ожидающие check-in. Повторное открытие Task Manager не перечитывает его данные.
Reset возвращает results-only layout; панели доступны через меню оболочки.

Состояние сохраняется для login в `tactic_stream.docks.<login>` localStorage:
дерево, видимость, floating bounds и z. Чтение проверяет типы, известные и
уникальные panel IDs, глубину и диапазоны геометрии. Это пользовательское
состояние браузера; общие проектные presets через WidgetDbConfig ещё не
перенесены. Записи, авторизация, selection и drafts в этот storage не входят.
Task Manager показывается только при доступности его административных прав;
действующие серверные проверки прав остаются обязательными.

При ширине рабочей области меньше 640 px или высоте меньше 440 px панели
переключаются одной полосой вкладок, не меняя сохранённое desktop-дерево.
Минимумы браузерной проекции 240×160 и floating 280×200 адаптированы к экрану;
это не native минимумы Qt. Desktop stacking и floating возвращаются при
увеличении области. Размеры touch controls не увеличиваются принудительно.
Поиск задач, create, milestones и refresh находятся в общей toolbar;
дублирующий заголовок внутри dock удалён.

Проверки: `node tests/docks.mjs` из frontend и две адресные Transport-проверки
`test_workspace_tabs_in_chromium` / `test_task_manager_in_chromium` на временной
SQLite. Проверены split/stack/swap/скрытие и повреждённый storage, keyboard
resize, отмена drag после maximize, восстановление stack после reload,
отсутствие повторного запроса при reopen, сохранность search tabs и task
drafts после hide/reset, последующее сохранение задачи и mobile 320 px.
Команда из tactic_stream: `.venv/Scripts/python.exe -B -m unittest
test_transport.Transport.test_workspace_tabs_in_chromium
test_transport.Transport.test_task_manager_in_chromium` с PYTHONPATH=src;tests.
Frontend собран штатным `npm run build`.

Живой Windows экземпляр снят `tests/capture_main.mjs` по той же команде и
viewport, что выше: `stream-docks-after.png` и `stream-floating-after.png`.
На этой итерации открытого окна Handler не обнаружено: новый снимок Handler
не получен. Сверка выполнена по QML и ранее снятому handler-main.png.
Browser закрывается в finally, временный сервер в teardown Transport.

Полный dock/UI перенос не завершён: отдельные OS/Electron окна,
остальные панели, порядок
вкладок stack и полная native минимальная геометрия остаются. Task Manager
и Task Inspector требуют отдельной полной сверки содержимого и UX с Handler;
работающий dock-хост не означает готовность этих экранов 1:1.

### Проектные пресеты и лейауты поисковых вкладок, 8 октября 2026

Перенесены workspace_layout_presets.py и WorkspaceLayoutPresetMenuSection.qml
Handler: в меню лейаута есть список с числом панелей/назначений, refresh,
apply, replace, save-as с вводом имени и delete с подтверждением. Применение
доступно читающему проект пользователю; запись проверяет admin на сервере.
Сохраняется исходная shared запись `config/widget_config`: category
`workspace_layout`, search_type `SideBarWdg`, пустой login и стабильный view
`workspace_layout@<uuid>`. XML `<config><view name="…"><values type="json">`
хранит нативный документ `{panels: [...], layout: {...}}` с полями DockPanel.
Сигнатуры XML-RPC не изменены: Handler читает и пишет эти же записи штатным API.
AST-сверка исходных XML-функций проверяет одинаковую оболочку и данные.

Новый HTTP endpoint `/admin/workspace-layout/{read,save,delete}` использует
тот же RequestContext/Auth/Command/Search/SObject и журнал. Все записи идут
под существующей межпроцессной блокировкой таблицы конфигов и проверяют
ревизию, включая marker журнала. Не теряются сторонние поля записи при replace;
duplicate title и malformed geometry/tree отклоняются. Delete проверяет живые
`display/layout_preset` ссылки сайдбара под той же блокировкой, даже если клиент
показывает старый assigned count. Ошибка/конфликт сохраняют открытый dialog;
неизвестный результат записи блокирует повтор до refresh.

Sidebar Editor уже использовал исходное поле layout_preset; теперь такие
ссылки открываются рабочей навигацией и применяют документ при первом открытии
поискового раздела. После этого раскладкой владеет конкретная поисковая вкладка:
capture перед переключением, apply её сохранённого документа при возвращении.
Документ сохраняется с настройками вкладки в localStorage; данные, selection и
черновики остаются в своих экранах. Apply обновляет существующие панели и не
переоткрывает контроллер задач с потерей draft, не меняет active stack через
сигнал инициализации содержимого. Смены проекта и поздние ответы защищены
поколением запроса; Sidebar save обновляет библиотеку активного проекта.

Формат native сохраняется. Пресеты с видимой ещё не перенесённой панелью или
отдельным OS окном явно недоступны для apply, а не превращаются в другую
раскладку. Скрытые native панели не мешают браузерной проекции. Replace является
явной заменой документа текущей раскладкой Stream, поэтому не сохраняет чужие
скрытые панели из заменяемого пресета. Сам экран редактора не изменяет Handler.

Проверки: `node tests/docks.mjs`; `python -B -m unittest test_workspace_layout`
(SQLite и опциональная PostgreSQL при STREAM_POSTGRES_HOST/password file);
Transport `test_workspace_layout_in_chromium`, `test_workspace_tabs_in_chromium`,
`test_task_manager_in_chromium`. PostgreSQL lifecycle реально выполнен через
`docker compose --project-name tactic-stream-linux -f deploy/docker/compose.yaml
run --rm --no-deps -T -v D:/code/TACTIC_VUE/tactic_stream/tests:/opt/tests:ro
-e PYTHONPATH=/opt/tests:/opt/stream-src:/opt/python-packages
-e STREAM_POSTGRES_HOST=postgres
-e STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password
app python -B -m unittest test_workspace_layout.WorkspaceLayout.test_postgres_native_layout_lifecycle`.
Тест создаёт уникальную stream_layout_* БД и удаляет её в finally; контейнер
автоматически удаляется. Browser lifecycle очищает собственные sidebar/preset
записи и закрывает браузер в finally; Transport останавливает временный сервер.
Снимок `.screenshots/workspace-layout-mobile.png` получен на временных данных.
Общий AppMenu ограничивает submenu границами переданного контейнера, чтобы
оно не обрезалось краем рабочего пространства на телефоне.

### Футер основного workspace, 8 октября 2026

Сверка выполнена по текущему SearchWorkspaceView.qml Handler и свежим снимкам
в `.screenshots/handler-current/`. Футер показывает диапазон и общее число
записей, текущую/последнюю страницу, переход по номеру, размер страницы
20/25/50/100/200/500, существующую Commit Queue и создание объекта. Используются
общие AppButton/AppMenu и установленный набор font icons. На узком workspace
размер страницы заменяется компактной кнопкой; меню открывается вверх и
ограничено границами рабочей области. На 320 px футер не создаёт горизонтальную
прокрутку. Размер страницы и позиция принадлежат конкретному поисковому табу.

Основные запросы записей проходят через существующий search-configuration/query:
`include_total: true` возвращает `{records, total}`. Count использует тот же
нативный Search, фильтры, project/security context и show_retired, без limit и
offset. Это дополнительный SQL COUNT в том же HTTP-запросе, а не отдельный
сетевой вызов. Без include_total ответ по-прежнему список; XML-RPC query не
изменён. Общее число записей хранится только в памяти таба, не в localStorage.

Проверки: `test_search_configuration.SearchConfiguration.test_native_search_library_defaults_query_and_conflict`
на SQLite и PostgreSQL; `test_transport.Transport.test_workspace_tabs_in_chromium`
на временной SQLite. Проверены фильтрованный count, retired, выбор колонок,
следующая страница, переход по номеру, сохранение размера в независимых табах,
геометрия и доступность меню на desktop/320 px, существующий lifecycle workspace.
Снимки `.screenshots/workspace-tabs-pagination.png`,
`workspace-tabs-pagination-menu.png`, `workspace-tabs-pagination-mobile.png`
сняты браузером на временных данных. Frontend собран через npm run build.
Docker получает исходники и web-assets через bind mount; для серверного Python
кода перезапускается app, образ не пересобирается. Windows launcher требует
перезапуска уже работающего сервера после обновления Python-кода.

Полный перенос главного окна ещё не завершён: режимы отображения результатов,
оставшиеся панели и их полное поведение требуют отдельных итераций.

### Непрерывная загрузка workspace, 8 октября 2026

Перенесено поведение `search_tabs.py:set_loading_mode/load_more` и
`SearchResultSurface.qml:requestMoreFromScroll`: глобальный для пользователя
режим Pages/Continuous, сброс активного поиска при переключении, догрузка
следующего пакета при движении к концу списка и явная кнопка Load more.
Переключатель в общем футере использует AppMenu/AppButton и штатные font icons.
В Continuous скрыты страницы и page-size control, диапазон заменён общим числом
результатов. Остальные табы перечитываются при активации, если загружались в
другом режиме. Предпочтение хранится в `tactic_stream.loadingMode.<login>`;
records и следующий offset остаются только в памяти поискового таба.

Догрузка проходит тем же native Search запросом. Она не скрывает таблицу, не
сбрасывает выделение и открытые предметные редакторы. Ошибка сохраняет уже
загруженные строки и предлагает Retry; автоматическая догрузка при ошибке
останавливается. Запросы сериализованы, страницы объединяются по search key;
offset продвигается по исходному числу строк даже при пересечении страниц.
Поздний ответ после смены проекта/таба/режима или открытия Administration
игнорируется существующим request generation. Открытие Configuration во время
догрузки также отменяет принятие её ответа. Одно движение прокрутки разрешает
один следующий пакет; восстановление viewport само не вычитывает всю БД.
Следующие пакеты используют параметры выполненного поиска; неприменённый текст
в поле поиска не меняет текущую выборку и сохраняется при догрузке.

ConfiguredView при append сохраняет серверные ячейки прежних объектов и
запрашивает одним пакетом недостающие ключи. Обычный refresh, смена определения,
проекта или replacement строк заново вычисляют все динамические ячейки.
Это состояние отображаемых записей, не постоянный кэш результатов скриптов.

Проверки: `python -B -m unittest
test_transport.Transport.test_workspace_tabs_in_chromium
test_transport.Transport.test_native_table_cells_in_chromium` с PYTHONPATH=src;tests.
Проверены append/error/retry, пересечение страниц, выделение, поздний ответ,
scroll, смена режима, восстановление предпочтения после reload, touch и 320 px.
Реальные native server cells проверены на дополнительных объектах временной БД:
один запрос новых ключей, сохранение предыдущего вычисленного содержимого.
Снимки `workspace-tabs-continuous.png` и `workspace-tabs-loading-mode.png`
сняты при 1440×1000/DPR1, как свежий Handler reference; mobile — 320×740.
Попытка снять Windows instance на 192.168.2.55:8081 получила connection refused;
он не запускался агентом. Браузеры закрыты в finally, временные серверы — teardown.

Серверный API и XML-RPC не изменены. Пересборка Docker или перезапуск app для
этой итерации не нужен: собранные web assets уже доступны через bind mount.
Полный SearchWorkspaceView ещё не объявлен готовым: результатные представления,
script shelf, tags и остальные действия поисковой панели остаются в плане.

### Облако тегов workspace, 8 октября 2026

Перенесён отдельный блок `TagCloudPopup.qml` и `view_state.py:_query_tag_catalog`:
кнопка Tags перед фильтрами, счётчик выбора, поиск по каталогу, ALL,
сброс выбора, Reload, частотный размер chips, пустые состояния и ошибки.
TagCloud.vue использует общие AppMenu/AppButton/font icons. Общий стиль
quick-filter-chip применяется также в QuickFilterEditor. Окно 440×288 px
ограничивается рабочей областью; на 320 px доступен тот же поиск и tap-выбор.
Расчёт позиции общего AppMenu исправлен: scale-анимация больше не искажает
конечные границы. Browser canvas измеряет текущий шрифт; строки пакуются как
в Handler, в DOM остаются только строки viewport и соседние строки.
Tab/Shift+Tab прокручивают и фокусируют ещё не смонтированные chips;
ArrowDown из поля переводит фокус на первый тег, Escape закрывает меню.

Native `/admin/search-configuration/tags` читает весь доступный SearchType
пакетами по 2000 через штатный Search, с проверкой прав и исключением retired.
Выбирается первое поле keywords/tags/tag. Разделители — запятая, точка с
запятой и whitespace; регистр объединяется через casefold, сохраняется первое
написание, считаются все вхождения. Сортировка — count DESC, label;
weight = log1p(count)/log1p(maximum). Каталог не зависит от текущих фильтров.
Отличие от TH: перечитывается при каждом открытии и Reload; постоянного кэша
изменяемой БД нет. Ошибка Reload сохраняет предыдущий каталог и выбор.

Query принимает tags/tag_column и сохраняет исходный LIKE `%tag%` контракт
Handler. Несколько тегов объединяются в отдельную OR-группу под остальными
фильтрами и ACL; исправлен исходный случай `(base AND tag1) OR tag2`.
Выбор и колонка хранятся в состоянии поискового таба, восстанавливаются после
reload. Ввод основного поиска/применение сохранённого поиска сбрасывает теги,
как в Handler. Поздний ответ каталога после смены проекта/таба игнорируется.
XML-RPC методы и их форматы не менялись.

Проверки: `test_search_configuration.SearchConfiguration.test_native_search_library_defaults_query_and_conflict`
на SQLite и PostgreSQL; `test_transport.Transport.test_tag_cloud_in_chromium`
и существующий workspace tabs scenario. Браузерный сценарий проверяет 1500
тегов, OR, keyboard, локальный поиск без HTTP, выбор между табами/reload,
ошибку обновления, свежесть после изменения БД, поздний ответ, touch и 320 px.
Команда: `.venv/Scripts/python.exe -B -m unittest <test>` с PYTHONPATH=src;tests.
Тест использует отдельный временный проект, браузеры закрываются в finally,
временный сервер — teardown. Свежие TH QML references сняты командой
`D:/Python314/python.exe -B tools/capture_handler_reference.py --tags-only`;
снимки Stream — `.screenshots/tag-cloud.png` и `tag-cloud-mobile.png`.

Docker app перезапущен для нового Python endpoint без пересборки образа.
Полный SearchWorkspaceView ещё не завершён: script shelf, parser/autocomplete,
представления результатов и остальные панели остаются отдельными блоками.

### Подсказки основной строки поиска, 8 октября 2026

Перенесено поведение `TacticSearchField.qml` и
`search_suggestion_data.py/search_helpers.py`: debounce 180 ms, native запрос
до 50 объектов, до 20 уникальных строк по title/description/keyword, описание
в одну строку, совпавшее ключевое слово, выбор мышью/стрелками, Enter и Escape.
AppSearchField владеет общим combobox/popup и не вызывает API; WorkspaceSearch
владеет запросом и отменой принятия поздних ответов. Popup использует native
HTML popover, общий AppButton/font icons/CSS tokens, строки высотой 34 px,
текущий размер поля и границы workspace. ResizeObserver пересчитывает границы;
длинный список прокручивается, клавиатура держит выбранную строку в viewport.
Escape закрывает подсказки без очистки текста и отменяет принятие ответа.
Ошибка показывает сообщение, сохраняя черновик и текущую таблицу.

Native `/admin/search-configuration/suggestions` использует штатные
Search/ApiXMLRPC и проверки доступа, без постоянного кэша. Поле заголовка —
name/title/code; для системных сущностей без этих полей добавлен fallback
login. Запрос как в Handler: OR из EQI по заголовку, keywords и description.
Retired не входят в подсказки. Пустые значения и строки skey://,
tactic-search:// не запрашивают каталог. Эти ссылки этим блоком не разрешаются.

Обычный Enter пока сохраняет существующий текстовый поиск Stream; выбор
подсказки задаёт точное `=` по заголовку/keywords/description и сохраняет этот
режим в поисковом табе, включая reload и возврат из Administration. Средняя
кнопка открывает новую вкладку с точным code; для объектов без code применяется
id. Для тача та же операция доступна явной кнопкой у строки. Новая вкладка
сохраняет текущий dock layout, получает собственные фильтры и название объекта;
исправлено переопределение собственного названия подписью New Search N.
На workspace уже 720 px Refresh/Tags и краткая справка перенесены в ⋮;
строка поиска получает свободную ширину, фильтры остаются рядом.

Проверены SQLite/PostgreSQL и Chromium: debounce без main query при вводе,
dedup/projection, точный выбор, новые вкладки без contains по code, reload,
стрелки/Enter/Escape, 20 строк и scroll, ошибки, поздний ответ после перехода,
явная touch-кнопка и границы 320×740. Команды с PYTHONPATH=src;tests:
`.venv/Scripts/python.exe -B -m unittest
test_search_configuration.SearchConfiguration.test_native_search_library_defaults_query_and_conflict
test_transport.Transport.test_search_suggestions_in_chromium`.
Также прошли существующие tag cloud и workspace tabs сценарии.
Свежий TH reference: `D:/Python314/python.exe -B
tools/capture_handler_reference.py --search-only`; снимки Stream:
`.screenshots/search-suggestions.png` и `search-suggestions-mobile.png`.

Backend app перезапущен в существующем Docker без пересборки образа;
собранные assets доступны через bind mount. Временные серверы/браузеры
закрыты проверками. Полный SearchWorkspaceView ещё не завершён: Script Shelf,
ссылки/грамматика основного поиска, виды результатов и остальные панели
продолжают учитываться отдельно. XML-RPC контракты не менялись.

### Виды результатов и группировка — 2026-10-08

Переключатель в поисковой панели использует шесть исходных имён Handler:
continious, tiles, table, compact, splitted_vertical, splitted_horizontal.
Группировка независима: none/status/pipeline, только загруженная страница;
пустые значения идут последними, заголовки показывают число объектов.
Группы сворачиваются в таблице и остальных видах; выбор группировки в Cards
переключает на дерево, как в Handler. Вид, группировка, раскрытие веток,
путь карточек и размер панели версий сохраняются отдельно по поисковым табам.
Continuous tree остаётся видом, Pages/Continuous loading — способом загрузки.

ResultPresentation владеет запросами/состоянием; ResultItem — общий presenter.
Дерево раскрывает процессы, versionless -> реальные версии и зарегистрированные
связи native Schema, включая self-instance Assets -> Assets; карточки открывают
уровень ветки с Back/All items. Split выводит версии выбранного объекта/процесса
справа или снизу; размер меняется нативным slider, включая клавиатуру/тач.
ThumbWdg предоставляет preview и ссылки файлов; формы, операции, NotesPanel и
Inspector повторно используются. Метаданные читаются пакетами по 500 объектов,
дети/версии — страницами по 50 с Load more; глобальных кэшей БД нет.
POST /admin/result-items использует существующий ticket/context и admin gate,
проверяет проект/тип ключей, разрешённые schema paths, offsets/limits.
XML-RPC API и исходники Handler не изменялись.

По замечанию пользователя уменьшены общие токены плотности: controls 32 px,
toolbar 40 px, footer 44 px, result row 68 px, compact 44 px, preview 48/32 px,
card preview 96 px. Размеры Material5 сохраняют свою разницу +2 px.
На узком экране details доступны в общем меню действий; tasks/notes остаются
явными кнопками, вложенность занимает меньше ширины. Шрифтовые иконки и общие
EN/RU controls сохранены; специальных увеличенных touch targets нет.
После уточнения пользователя уменьшены именно иконки: общий AppIcon 16 px;
navigation, toolbar/menu и операции 14 px, кнопки операций 24 px. Исправлено
обрезание счётчиков внутри icon buttons.

Проверки: test_cg_template.CgTemplate — реальный cg.zip и sample, SQLite/PG,
Robot -> Body/Tool и Episode -> Shots, paging, чужие ключи/paths, запрет доступа,
два настоящих check-in и versionless -> [2,1] с файлами.
frontend/tests/result_views.mjs — шесть видов, дочерние ассеты, Cards drilldown,
группы, preview/download, отдельные вкладки, reload и touch360 без overflow.
test_transport.Transport.test_workspace_tabs_in_chromium — существующие tabs,
pagination/docks и touch320 после изменения плотности. npm build прошёл.

Полная функциональная/визуальная паритетность SearchWorkspaceView ещё не заявлена:
Script Shelf, иерархические subpipelines, pinned/hover previews и сложные
произвольные branch widgets остаются отдельными частями переноса. В импортированном
CG Assets link с Script Shelf пока блокируется, а In Progress preset не найден;
проверка видов открывает обычную Assets вкладку через штатное восстановление
workspace, не подменяя XML проекта. Эти два ограничения требуют следующего
переноса; нельзя считать новый переключатель готовностью всей навигации CG.

### Уточнение переноса дерева из Handler — 2026-10-08

Предыдущие уменьшенные размеры строк заменены исходными значениями
WorkspaceResultItem.qml: объект 100/64 px, preview 68/42 px, процесс 32 px,
связь 38 px, шаг вложенности 24 px, промежуток 3 px. Под строками workspace,
поверхности строк panel; описание использует secondaryText. Общий AppIcon
повторяет opticalScale .78, поправки MDI 1.22/Fluent 1.08 и минимум 11 px.
Гарнитура Segoe UI проверена через Chromium platform fonts, а не только CSS.

Сервер передаёт цвета типов/процессов, порядок связей перед процессами,
счётчики задач/заметок, metadata настроенных полей и progress из native workflow.
Число связанных объектов разрешается при раскрытии владельца штатным Search.
Связи instance читаются тем же направленным запросом, включая self-instance;
SObjectLinkCmd использует логику edit_multiple_instance_sobjects из Handler,
native Command/connection writes и native EditCmd для создания с привязкой.
Проверены повторная привязка, отвязка, self-instance и rollback на временной БД.
ID полей RecordForm теперь уникальны для каждого экземпляра формы.

tools/handler_result_reference.py снимает свежий эталон исходного QML через
тестовый модуль Handler; исходники и данные Handler не изменяет. Это рендер
компонента, а не снимок всего приложения. tools/result_browser.py импортирует
реальный cg.zip во временную БД и запускает браузерные проверки; сервер
закрывается в finally. result_tree_parity.mjs проверяет геометрию, гарнитуру,
разделение цветов workspace/panel, glyph, порядок/счётчики и раскрытие эпизода.
result_views.mjs проверяет все шесть видов, группы, версии и mobile360.
Сборка, SQLite и обе браузерные проверки прошли; PG в этом этапе не проверялся.

Перенос дерева остаётся незавершённым: форматирование сложных metadata,
подписи категорий, прямые publish snapshots, subpipelines, hover/pinned previews,
полные quick-action menus и точное восстановление отменённого collapse.
RelatedObjects/RecordForm переиспользуют действующие формы; их визуальная
паритетность с редакторами Handler ещё не заявлена. Импортированный insert
Assets содержит неподдержанный Preview: форма открывается, но сохранение
блокируется. Проверка открытия формы не считается готовностью этого сценария.

### Пункт 1: главное окно и общие controls — 2026-10-08

Эталон взят из текущих Main.qml, Theme.qml, NavigationDrawer.qml,
SidebarTreeRow.qml, SectionTabRail.qml, SearchWorkspaceView.qml, ProjectChooser.qml
и controls Handler. tools/capture_handler_reference.py запускает исходное
приложение через application.main с временным профилем и синтетическими данными:
это свежие снимки живого QML, без изменения исходников/настроек Handler.
Основной размер сравнения 1440×1000, dark/md3, масштаб 100%.
Снимки находятся в .screenshots/handler-current: main/navigation/main-menu/
project-chooser — Handler, stream-main/stream-navigation/stream-menu/
stream-project-chooser — браузер с реальным импортированным cg.zip.
Хеши исходного QML записаны в compatibility/source_manifest.json.

Геометрия: app bar 44 px, rail 48 px, search/tab rows по 48 px, footer 58 px;
controls 36/compact32 px, без увеличения зон для тача. Убраны повторный dock
отступ и перекрывающий native radius старый CSS. Drawer шириной до 360 px
открывается поверх workspace, сохраняет его геометрию и собственную прокрутку.
Перенесены отступы и вложенность строк, цвета SearchTypes, section rail badge,
ширина раскрытия по подписи, закрытие/перестановка и keyboard/touch входы.
Project chooser повторяет исходные размеры, карточки, фильтры и типографику.
Общий DockGrip повторяет 6 точек DockDragGrip.qml; SVG не добавлялись.

AppButton/AppMenu используют общий pointer ripple MaterialRipple.qml, без
масштабирования всего контрола при нажатии. Меню открываются и закрываются
через scale .9↔1 (72 ms OutQuint) и opacity (48 ms OutCubic); drawer —
104 ms OutCubic / 72 ms InCubic. Настройки соответствующих групп анимаций и
системный reduced motion учитываются. Встроенный ряд действий не создаёт
контекст наложения, закрывающий вложенные меню результатами.

WorkspaceTabs сохраняет историю, reorder, keyboard selection и compact close
поведение; overflow/history кнопка появляется по необходимости. Применение
текущего вида ко всем вкладкам проекта переносит result mode и split ratio,
сохраняя индивидуальные запросы. Footer имеет native pagination/range/load/
create controls. Responsive меню сохраняет DOM цели Teleport: смена ширины
не уничтожает кнопки sort/group/view. На 320/360/720 px результаты остаются
основной прокручиваемой областью, без горизонтального overflow страницы.

NavigationMixin search_view перенесён как загрузка всех link_search presets
в namespace search_type@sidebar_name отдельными вкладками; поиск единственного
точного имени больше не блокирует импортированные CG ссылки. Испорченные
presets сообщают ошибку. Аватар текущего пользователя читает только его native
Login и общий user_identities через /admin/session/identity. Account data и
credentials не выдаются; запрос чужого login запрещён контрактом. XML-RPC
Handler не менялся. Обе ветки отказа и разрешённый результат проверены.

Проверки: npm run build; main_window.mjs (геометрия, меню/клавиатура, ripple,
overlay, chooser, view propagation, mobile); result_views.mjs; Chromium checks
workspace_tabs/project_navigation/workspace_layout и общий admin сценарий
(themes/configuration/touch/search/request ordering/session lifecycle).
Последний обновлён под уже существующие отдельные admin editors и текущий
query transport; hidden retained dialogs не считаются открытыми экранами.
Тестовые серверы завершаются в finally, оригинальные QML процессы — по quit
и timeout cleanup. PostgreSQL и Electron в этом этапе не перепроверялись.

Это перенос базового слоя пункта 1, а не завершение всего Main/Handler:
полная функциональная паритетность состава меню/верхних shortcuts, Script Shelf,
Activity Feed/Transaction Log и произвольные панели CG layout ещё не достигнуты.
Transaction Log честно возвращает unsupported; complex layout сообщает
неперенесённые панели. Мобильные экраны предметных редакторов остаются отдельным
пунктом плана. Эти ограничения нельзя считать завершёнными по наличию кнопок.

### Продолжение пункта 1: Debug Log — 2026-10-08

Из текущих DebugLogView.qml, debug_logging.py и help_articles/debug_log.en.md
перенесены Sources, Activity, детали события, фильтры уровней/групп/поиска,
выбор клавиатурой, изменение размеров панелей, история, импорт компактных
JSONL v1, возврат к live, очистка, копирование события и команды запроса.
Эталон получен запуском исходного QML с временным профилем:
capture_handler_reference.py --debug-only; исходники Handler не менялись.
Снимки: .screenshots/handler-current/debug-log.png и stream-debug-log.png.

Веб-адаптация хранит сессии браузера в IndexedDB, вместо Copy Session Path
скачивает JSONL того же формата. Qt/DCC события доступны через импорт JSONL;
поток серверных Python логов в браузер на этом этапе не переносился.
Записываются выбранные browser console/error и запросы веб-интерфейса.
Global конфигурации управляет записью, отдельные фильтры окна — отображением.
По умолчанию включены ERROR и CRITICAL, как в Handler; полный Global экран
Handler этим разделом не считается перенесённым. Ограничения явно заданы:
10000 событий на сессию, импорт до 32 MB. Тексты отдельных событий не обрезаются.

Пароли, тикеты и другие секретные поля, включая positional get_ticket,
маскируются до записи; известные значения маскируются также в сообщениях,
ответах и traceback. Произвольный текст импортированного стороннего журнала
может содержать неизвестные браузеру секреты: импорт не считается универсальным
сканером секретов. Выход очищает историю и память; ответ предыдущей сессии
не записывается после смены sessionId. Upload сохраняет метаданные, без байтов
файла; его команда воспроизводит multipart с явными заменяемыми placeholders.
Ошибки журналирования не заменяют исходную ошибку запроса.

AppSplitter — общий control с pointer cancel/blur/unmount cleanup и keyboard
управлением. На 320/360 px те же фильтры уровней перемещаются в компактное
AppMenu без дублей; Sources выбираются через общий AppSelect. Общий clipboard
helper применяется в журнале, справочнике и search library; copy работает
также по LAN HTTP через user-activated browser copy command.

Регрессия пустого экрана на LAN HTTP была вызвана eager crypto.randomUUID(),
доступным только в secure context. Генерация sessionId использует доступный
по HTTP crypto.getRandomValues. lan_startup.mjs проверяет именно insecure
context, отсутствие randomUUID, видимый вход и отсутствие pageerror.
Проверки: production build; debug_log_data.mjs (секреты, циклы, JSONL,
повреждённые сессии, исполнение multipart команды без сети); main_window.mjs;
debug_log.mjs (HTTP, конфигурация, история, импорт/экспорт, большие детали,
copy, splitters, мобильные размеры, очистка при выходе); Chromium LAN startup,
общий admin и API documentation/console. Серверы завершаются в finally.
Полная функциональность Main, Script Shelf и Activity Feed/Transaction Log
остаётся незавершённой. PostgreSQL и Electron в этом продолжении не проверялись.

### Продолжение пункта 1: UI responsiveness — 2026-10-08

Перенесён следующий самостоятельный экран меню: UiPerformanceView.qml,
UiPerformanceMonitor из ui_performance.py, формат отчёта и именование вкладок
из controllers/tab_switch_performance.py. Запуск/пауза, очистка, JSON copy,
summary count/overBudget/p95/maximum, выбор строки/детали, Handler/First frame/
Ready frame и красная граница медленных измерений используют общие controls,
палитру, шрифты и официальный шрифтовой icon pack. Запись изначально выключена;
после закрытия окна продолжается только если пользователь включил её.
История ограничена 250 событиями, pending — 64, ожидание кадра — 5 сек.
Скрытая диагностика не публикует список; visible/hidden/close, pause, logout
и unmount имеют явный cleanup. Clear также отменяет pending измерения, чтобы
старые результаты не возвращались после очистки. Сессии остаются в памяти,
выход очищает их и выключает запись. Значения полей и нажатые клавиши не читаются.

Браузерная граница кадра отличается от QQuickWindow.frameSwapped: два rAF
ограничивают возможность отрисовки, не подтверждая GPU presentation. Поэтому
статус называется Browser frame, а ограничение объяснено в самом окне.
Начальный кадр не завершает асинхронную операцию: ready считается после
публикации результата/Vue nextTick и последующего кадра. Failed, Superseded,
Window closed и No frame не получают успешное ready время. Handler длительность
асинхронной операции включает ожидание; отдельные requestAndSchemaMs и
publicationMs показывают измеренные этапы. Для Search tab: <title> отчёт
содержит cached/restorationMs. Именованными границами сейчас покрыты загрузка
результатов/следующей страницы и переключение поисковой вкладки; произвольные
серверные/DCC операции и все остальные контроллеры этим покрытием не объявляются.
Input наблюдается во всех окнах/меню этого браузерного документа.

Свежий оригинальный QML снят capture_handler_reference.py --performance-only
на временном профиле: ui-performance.png. Native content 1008×660 сравнивается
с web dialog 1008×700, где дополнительные 40 px занимает заголовок веб-окна.
Размер строки 54 px, числовые колонки 96/96/88 px, detail 95 px, отступ 16 px.
Браузерные снимки: stream-ui-performance.png и варианты 320/360 px.

Проверки: production build; ui_performance_data.mjs (opt-in, bounded history,
first/ready separation, input privacy, hidden publication, failed/superseded,
closed host, timeout, wheel coalescing, cleanup); ui_performance.mjs (LAN HTTP,
реальный delayed request, cached tab, JSON copy, clear/pause, keyboard,
native geometry/fonts, mobile, EN/RU, logout); повторные main_window.mjs и
debug_log.mjs. Временные серверы завершаются в finally; оригинальный QML —
quit/timeout cleanup. Изменений Handler, новых зависимостей и новых API нет.
Пункт 1 целиком ещё не закрыт: Script Shelf, Activity Feed/Transaction Log,
верхние shortcuts и произвольные CG panels остаются незавершёнными.
Другие браузеры, PostgreSQL и Electron в этом продолжении не проверялись.


### 2026-10-08 — пункт 1: Script Shelf

Полка открывается кнопкой `<>` рядом с поиском; редактор — карандашом на полке
или через главное меню Script Shelf. Источник: текущие ScriptShelfBar.qml,
ScriptShelfEditorView.qml, ScriptTreePicker.qml и script_shelf.py Handler.
Состоянием полки и черновика владеет features/scripts/ScriptShelf.vue;
App остаётся хостом. Дерево скриптов использует NavigationTree с поисковым
текстом полного пути. Общий AppMenu получил overlay через HTML popover,
чтобы дерево не обрезалось прокручиваемым списком. Общий AppSegmentedButton
повторяет SegmentedButton.qml, включая стрелки/Home/End. IconPicker получает
iconOnly; штатная семантическая иконка play-arrow разрешается через тот же
каталог. Выбор сохраняет текущий формат Handler `set:name`; все пять каталогов,
включая Fluent Regular/Filled, используют оригинальные charmaps. Старые
FAS_/FAR_/MDI_ продолжают читаться. Highlighted AppButton использует
Theme.selectedText/on-selected.

Перенесены Mine/Shared, личная полка всех вкладок/данного пункта сайдбара,
общая полка проекта и именованные общие полки вкладок, создание/переименование/
удаление, Apply to this tab, полный редактор кнопок (скрипт из дерева, иконка,
подпись, описание, порядок и удаление), отмена черновика, защита закрытия,
справка EN/RU и вывод результата. Удаление показывает точное имя набора.
Полка имеет высоту 48 px; действия 40×40 с иконкой 16 px, компактный переключатель
26×46, строки редактора 88 px. Native content 864×660 сравнивается с web
864×700, где 40 px занимает заголовок. Мобильный редактор перестраивается
в одну колонку, сохраняя скролл содержимого и те же операции.

Хранение — исходный XML config/widget_config с search_type=SideBarWdg,
category=script_shelf и view=script_shelf@…; shared default — script_shelf@global.
Личный набор фильтруется по login. Личная tab-полка имеет приоритет над личной
общей, включая пустой набор; Shared выбирает назначенный preset, затем global.
Ключ — SearchType@имя пункта сайдбара, одинаковый для всех поисковых вкладок
этого пункта. Черновик не подменяет выполняемые сохранённые кнопки.

POST /admin/script-shelf/{read,save,assign,delete,script} использует текущую
авторизацию, RequestContext, нативные Search/SObject/Command и общий revision
с журналом. Save и назначение выполняются атомарно, deletion удаляет ссылки
script_shelf из конфигов сайдбара. Устаревший revision даёт 409; ошибка назначения
откатывает вставку. Повтор исходного запроса после потери ответа не создаёт
второй набор: старый revision отклоняется. Подтверждённые конфликты и неизвестный
исход запроса требуют reload; обычную ошибку валидации можно исправить в черновике.
XML сравнивался с неизменёнными чистыми функциями оригинального Handler.

По явному уточнению пользователя поддерживаются только JavaScript в браузере
и Python на сервере; local_python, dcc_python, server_js/expression и DCC export
не выполняются этой веб-полкой. Подключение к Handler исключено на этом этапе.
JavaScript загружается из сохранённого config/custom_script отдельным
авторизованным запросом и запускается как async function(context) через Blob
ES module; URL освобождается в finally. CSP добавляет только blob: к script-src,
сохраняет запрет eval и inline scripts. Это доверенный код в контексте страницы,
не sandbox. context содержит project, searchType, searchKeys, rpc(method,args,
kwargs) с текущим аккаунтом и захваченным проектом, refresh(). Пример есть в Help.
Python выполняется существующим execute_python_script с script_path, сохраняя
оригинальный формат и действующую проверку прав. XML-RPC не изменён.

Ограничение ядра открыто показано через canWrite: запись конфигураций и серверный
Python пока требуют активного администратора. Обычный пользователь может читать
доступные общие наборы и запускать доступный JS; чужие личные наборы не выдаются.
Нативные права на бизнес-запись для других ролей не обходятся через Sudo и не
объявляются завершёнными. Полный Script Editor остаётся отдельным незавершённым
экраном: полка выбирает уже сохранённые скрипты, как в Handler.

Проверки: tests/test_script_shelf.py (XML native comparison, scopes/ownership,
JS source boundary, malformed buttons, stale revisions, rollback and delete
assignments, unchanged XML-RPC Python call); frontend/tests/script_shelf.mjs
(реальный временный CG, LAN HTTP, CSP, Python/JS с RPC, полные пути дерева,
личный и общий наборы, назначение/удаление, поисковые вкладки, черновики,
EN/RU/keyboard/touch 320/360), icons.mjs, main_window.mjs, sidebar_editor.mjs
на временной CG-фикстуре и production build. Старый tools/interface_browser.py
не прошёл: его сценарий кликает скрытый sidebar без открытия; это отдельная
устаревшая проверка, не подтверждение готовности всех форм.
Свежие снимки оригинала: capture_handler_reference.py --shelf-only,
script-shelf-bar.png и script-shelf-editor.png; браузерные — stream-script-shelf-… .
Временные серверы и браузеры закрываются в finally. Handler не изменяется.
В этом этапе PostgreSQL, другие браузеры и Electron не проверялись.
Пункт 1 целиком остаётся открытым: Script Editor, Activity Feed/Transaction Log,
верхние shortcuts и сложные CG panels ещё требуют переноса.

### 2026-10-08 — пункт 1: Script Editor

Редактор открывается через главное меню Script Editor. Источники — текущие
ScriptEditorView.qml, controls/ScriptCodeEditor.qml, script_editor.py,
script_editor_features.py и script_history.py Handler. Оригинальный Handler
и его настройки не изменены. Выполнение ограничено явно согласованными
целями: JavaScript в браузере и Python на сервере, без подключения к Handler.
Кнопка Handler/DCC Script Triggers отключена с пояснением: она относится к
клиентским action hooks, а не к серверным триггерам TACTIC.

Состояние экрана принадлежит features/scripts/ScriptEditor.vue. Общий
CodeEditor содержит только редактирование текста; он не обращается к проектам
и серверу. Подсветка Python/JavaScript общая с CodeBlock справочника API.
Используются AppButton/AppMenu/AppSelect/AppSplitter/AppSearchField,
AppSegmentedButton и WorkspaceTabs(kind=script), официальные шрифтовые иконки,
тема и EN/RU. Scripts переиспользует дерево полки и NavigationTree; Outline
показывает функции/классы и переводит курсор к символу. WorkspaceTabs различает
search/script через data-kind; закрытие последней вкладки разрешено редактору.

Перенесены New/Save, Folder/Title/Language, обновление и скрытие дерева,
несколько независимых вкладок, их порядок и закрытие с Save/Discard/Cancel,
удаление сохранённого скрипта, Copy Script Runner, штатные сохранённые ревизии,
выбор и запуск выделения, F5/Ctrl+Enter/Ctrl+S, undo/redo и меню 120 изменений,
cut/copy/paste, размер текста, поиск/замена с case/whole-word/regex, подсветка
совпадений, комментарии, отступы и дублирование строк. Автодополнение использует
ключевые слова, идентификаторы текущего исходника и имена server.* из имеющегося
справочника API. Native Python AST/import/signature completion и
квалифицированный outline перенесены следующим блоком ниже; этот первоначальный
перечень сам по себе не заявляет полного функционального паритета редактора.

Output находится над Source, как в актуальном QML: высота 120 px,
перетаскиваемая граница, wrap/clear/collapse и собственная прокрутка. Вывод
хранится отдельно в каждой вкладке, ограничен 200 KB. Scoped console JS
попадает в Output, включая циклические объекты; глобальная console страницы
не подменяется. Серверный Python исполняется прежним execute_python_script;
print остаётся в серверном журнале, результат и ошибки показываются в Output.
JavaScript исполняется общим revocable Blob module с context/project/searchType/
searchKeys/rpc/refresh и текущей авторизацией. Это доверенный код страницы,
не sandbox. Copy Script Runner использует сохранённый путь и явный проект;
JavaScript читает сохранённый исходник через текущий rpc без встроенного ticket.
На HTTP программная вставка недоступна: Ctrl+V/браузерное меню продолжают работать.

Черновики, вывод, выбранная вкладка, панели и размер текста сохраняются в
localStorage отдельно для login/project. Refresh и восстановление обновляют
чистые вкладки с сервера, сохраняя грязные вкладки и их исходные revision.
При конфликте черновик остаётся, повтор записи блокируется до reload/review.
Сохранение не перетирает текст, изменённый во время запроса. Смена проекта
сохраняет предыдущие черновики под предыдущим ключом и отбрасывает старые ответы.

POST /admin/script-editor/{read,save,delete,history,revision} работает через
обычную сессию/RequestContext и native Search/SObject/Command. Изменения
используют штатные триггеры и audit; native collection lock SQLite/PostgreSQL
защищает проверку revision вместе с записью. Повтор исходного запроса создания
отклоняется устаревшим revision, не добавляя второй скрипт. Чтение проверяет
search_type view; действующее ядро разрешает запись/исполнение администратору,
это явно показано через canEdit. История реконструируется скопированной
процедурой Handler из transaction_log/sobject_log, отдельного журнала нет.
Единственное изменение её алгоритма — порядок timestamp,id при равном времени:
SQLite хранит timestamp с секундной точностью, поэтому нужен устойчивый порядок
INSERT/UPDATE. Исходный XML-RPC контракт сохранён.

Свежий native reference снят capture_handler_reference.py --editor-only:
script-editor.png, content 1100×760. Web dialog 1100×800 включает отдельные
40 px заголовка; toolbar 32 px, input 30 px, tabs 38 px, дерево 200 px,
его поиск 36 px. Source/Output используют оригинальные роли theme и Consolas.
Мобильный экран сохраняет те же операции, располагает дерево под исходником
и ограничивает его высоту 160 px. Снимки stream-script-editor.png и варианты
320/360 px получены браузером; оригинал снят с временным профилем.

Проверки: tests/test_script_editor.py (native storage, права, stale/retry,
слеши/валидация, project isolation, audit revisions и прежний XML-RPC запуск),
frontend/tests/code_editing.mjs (редактирование, границы поиска, символы,
completion, оба токенизатора), frontend/tests/script_editor.mjs (реальный CG,
LAN HTTP/CSP, Python/JS/выделение, runner, syntax/search/replace/undo/outline,
history, черновики после reload, размер текста, EN/RU/touch320/360),
script_shelf.mjs и main_window.mjs, production build. Временные серверы,
браузеры и QML-процессы завершаются в finally/timeout cleanup.

Пункт 1 остаётся открытым: Activity Feed/Transaction Log, верхние shortcuts
и сложные CG panels; уточнение editor completion/outline приведено ниже.
PostgreSQL, другие браузеры и Electron в этом продолжении не проверялись.

### 2026-10-08 — пункт 1: нативный AST-анализ Script Editor

Qt-независимые функции _node_signature … completion_items из текущего
thlib/ui/script_editor_features.py перенесены целиком в server/script_features.py.
Outline использует ast, исключает комментарии/строки и сохраняет qualifiedName,
depth, kind, line/endLine и сигнатуру, включая async и вложенные методы.
Completion сохраняет native label/insertText/cursorOffset/detail/start/end:
ключевые слова и builtins, имена исходника, импортированные модули/алиасы,
стандартную библиотеку, локальные классы, self/cls и экземпляры этих классов.
Импортированные проектные модули читаются как AST, не импортируются и не
исполняются; importlib используется только для фиксированного native списка
стандартной библиотеки. Ошибочный хвост исходника обрабатывается исходным
_safe_tree; дополнительно RecursionError/ValueError дают пустое дерево.
Вместо исключённых th/Handler/DCC runtime targets зарегистрированы фактический
TacticServerStub для server и доступные native Search/SearchType. Сигнатуры
server.* читаются из исходного SDK, без создания второй таблицы методов.

POST /admin/script-editor/analyse проверяет текущую сессию, проект, admin и
search_type view, типы source/cursor/manual, размер и UTF-16 границы. Python
смещения преобразуются в браузерные UTF-16, включая emoji; позиция между
суррогатами отклоняется. Анализ не записывает скрипт, audit и не запускает код.
Запросом владеет ScriptEditor.vue; CodeEditor только выдаёт событие analyse и
получает результат. Устаревшие ответы от другого исходника/буфера/проекта
отбрасываются. Анализ структуры продолжает обновляться после потери фокуса,
а завершённая/отменённая подсказка не открывается старым ответом заново.

Автоматические подсказки запускаются через native 140 ms; Ctrl+Space — вручную.
Список показывает название, сигнатуру/пояснение и вид символа; строки 34/46 px,
иконки 14 px, поверхность и secondaryContainer=rowHover соответствуют QML.
Положение рассчитывается у курсора с ограничением внутри доступного контейнера;
на 320 px ширина ограничивается экраном. Выбор кликом/тапом, Tab или пробелом
вставляет callable скобки и помещает курсор внутрь. Enter оставляет обычный
перенос строки; Ctrl+Enter запускает выделение даже при открытых подсказках.
Outline фильтрует qualifiedName, делает отступ 14 px на уровень, показывает
строку, переключается Ctrl+Shift+O и переводит фокус в фильтр. Alt+Up/Down
циклически переходят по символам, F12 — к определению текущего имени;
Ctrl+Shift+K удаляет строку. Tab без выделения вставляет пробелы до следующего
стопа, с выделением меняет отступ блока, как в ScriptCodeEditor.qml. Поиск
Scripts и Outline имеет отдельное состояние; общий переводчик и Help EN/RU
сохраняются. JS продолжает использовать существующий браузерный анализ имён
и функций; полного JavaScript AST/type resolver здесь не заявляется.

Проверки: test_script_features.py сравнивает исходные чистые функции Handler
с адаптацией на AST/stdlib/self/async/незавершённом коде, проверяет callable
позиции, docstrings, отсутствие исполнения и безопасный разбор; расширенный
test_script_editor.py проверяет анализ, границы emoji и отказ обычному читателю.
script_editor.mjs проверяет server.query(), aliases, вложенный Outline,
исключение fake определения в строке, переходы, native Tab, selection execution
при открытой подсказке, опоздавший ответ старого исходника и тап на 320 px.
Снимки script-completion.png/script-outline.png получены из реально запущенного
актуального QML в временном профиле; stream-script-completion.png и
stream-script-outline.png — из браузера. Код и настройки Handler не меняются.
Production build и регрессии Script Shelf/Main проверяются на временном CG.
PostgreSQL и другие браузеры в этом блоке не проверены; общая готовность
главного окна и всего Script Editor не выводится только из AST-проверок.


### 2026-10-08 — Activity Feed и общие рабочие окна

Текущий Activity Feed больше не подменяется таблицей System Logs. Исходный
query_user_recent_activity из Handler перенесён целиком в server/activity_query.py.
Тонкий read-only /admin/activity-feed использует текущую сессию/проект, штатные
Search/SObject/Security и XML audit; фильтрует недоступные SearchTypes и endpoints
instance-связей в событиях и календарных счётчиках. Приватные заметки фильтрует
исходный Note.alter_search. XML-RPC и пользовательские данные не меняются.

ActivityFeed.vue владеет запросами, фильтрами, календарём, чтением и уведомлениями;
ActivityEventCard/ActivityCalendar получают данные и испускают события. Пять
исходных фильтров, поиск по загруженным событиям, выбор пользователей с Apply,
Exclude own, календарь полной истории, дни, раскрытие длинного текста, пагинация,
переход к объекту и заметкам процесса; задачи открывают существующий инспектор.
Первичная загрузка не выдаёт старые события за новые; чужие новые события дают
счётчик/опциональное уведомление, открытие снимает непрочитанное. Poll каждые
30 секунд и при возврате вкладки, с перебором новых страниц и отсечением старых
ответов. Счётчик работает и при выключенных уведомлениях. Применение цветов
через CSSOM сохраняет CSP без unsafe-inline. Взяты исходные роли цветов, размеры
40/34 px аватаров, 15 px segmented icons, 20 px event icon и общие шрифтовые наборы.
Календарь имеет исходную модальность/scrim/focus через общий AppMenu; users popup
остаётся немодальным. Снимки activity-feed/activity-calendar сняты с актуального
живого QML, stream-activity-* — в браузере, на одной activity-fixture.json.

Полная паритетность ленты пока не заявляется: произвольные skey/tactic-search
ссылки в тексте ещё ждут общего маршрутизатора rich text, текст безопасно
экранируется; вместо автоматического заполнения короткой страницы есть Load more.
Transaction Log и прочие оставшиеся части пункта 1 не закрыты этим блоком.

По прямому уточнению пользователя все рабочие модальные окна используют общий
WindowControls и директиву v-window. Она дополняет существующую шапку, сохраняя
нативный dialog DOM ref и все проверки несохранённых правок/исполнения.
Шапку можно перетаскивать указателем; двойной щелчок или Alt+F10 разворачивает
на экран и восстанавливает прежний размер/позицию. Alt+стрелки при фокусе на шапке
перемещают окно; Shift увеличивает шаг. Геометрия ограничена экраном, отмена
жеста возвращает её, resize/menu reposition используют общий путь. Изначально
полноэкранный конфиг можно восстановить в ограниченное обычное окно.
На <=760 px рабочие окна занимают доступный экран; desktop кнопка скрыта.
Подключены редакторы, формы, создание проектов, инспекторы, журналы, конфиг и
админка. Inline/docked sections, sidebar, popup menus и короткие подтверждения
остаются своими controls. Новый рабочий dialog обязательно получает v-window,
локальные копии перемещения/maximize не допускаются. Observer ограничен своим
окном, не выбирает шапку вложенного dialog и освобождает controls/listeners при
удалении шапки или окна. Повторное открытие не дублирует кнопки.

Проверки: test_activity_feed.py (SQLite transport, реальные audit/notes, ACL,
календарь и пагинация); activity_feed.mjs (реальный cg.zip, фильтры/поиск/users,
календарь, раскрытие, заметка в процессе, уведомления/счётчик и touch320/360);
window_controls.mjs (конфиг, Script Editor и Debug Log, maximize/restore,
клавиатура, mobile и повторное открытие); icons.mjs/docks.mjs, регрессии
Script Editor/Shelf/Main и создание объектов/защита черновиков. Production build.
Временные Python/браузеры/Qt захваты завершаются в finally; исходный Handler
и его настройки не меняются. PostgreSQL и другие браузеры в этом блоке не проверены.

### 2026-10-08 — Activity Feed: догрузка и обновление открытой истории

Закрыта отмеченная выше недоработка автоматического заполнения коротких страниц.
Поведение взято из текущих ActivityFeedView.requestMoreIfNeeded и общего
ScrollBar.takePaginationPermit. Общий controls/pagination.js отвечает только за
геометрию, разрешение жеста и освобождение обработчиков; API и состоянием
загрузки по-прежнему владеет ActivityFeed. Короткая лента заполняется при
открытии, фильтрации и увеличении окна. Для переполненной ленты нужна прокрутка
колёсиком, клавиатурой или тачем до конца; перемещение позиции программно и
перетаскивание scrollbar не запрашивают страницы. Финальные кадры отпускания
ползунка защищены, закрытая лента не догружается. Отдельная кнопка Load more
убрана; поиск и справка EN/RU описывают автоматическую догрузку.

Фоновое обновление перечитывает исходные страницы до прежнего хвоста открытой
истории, а не склеивает первую страницу со старым массивом. Это устраняет
пропуски при появлении более 25 новых событий и сохраняет корректный следующий
offset/hasMore. Повторяющиеся eventId удаляются штатным frontend helper.
Видимое событие сохраняет положение по пикселям; если оно удалено, сохраняется
прежний scrollTop с обычным ограничением браузера. Обновление, пришедшее во время
активной загрузки, обрабатывается после неё. Старый ответ предыдущего фильтра
или проекта не изменяет текущий список. Ошибка оставляет уже загруженные записи
и останавливает догрузку до явного Retry.

Проверено в Chromium на временном сервере с штатно установленным cg.zip:
activity_feed.mjs — реальные события/заметки, фильтры, календарь, уведомления;
activity_paging.mjs — разрешения прокрутки, resize, поиск на последней странице,
пакет из 40 новых событий без пропусков, сохранение видимого события, ошибки,
запоздавший ответ, отложенный poll и touch320. window_controls.mjs — регрессия
общих окон. Production build прошёл. Свежие activity-feed/activity-calendar
сняты с настоящего QML ТХ; stream-activity-* — из браузера на том же fixture.
Исходники/настройки Handler и XML-RPC контракт не менялись; тестовые процессы
завершаются в finally.

Пункт 1 целиком остаётся открытым: общая маршрутизация skey/tactic-search в
rich text, Transaction Log и остальные ранее перечисленные части главного окна.
Другие браузеры и PostgreSQL в этом frontend-блоке не проверены.

### 2026-10-08 — ссылки в ленте и адреса рабочего пространства

Закрыт отмеченный выше общий маршрут skey/tactic-search в тексте ленты.
Исходные rich_text.linkify_plain_text, search_links, search_suggestions,
parce_skey и SkeyPreviewController изучены в текущем Handler. Общий
controls/richText.js экранирует текст, выделяет исходные пять схем ссылок,
сохраняет переносы строк и завершающую пунктуацию. Ссылки раскрытых значений
изменений используют тот же control. Он не знает проектов и серверного API;
преобразование href задаёт доменный workspace/links.js. Обычный клик передаёт
внутреннюю ссылку хосту; Ctrl/Meta/Shift и открытие в новой вкладке сохраняют
поведение браузера. Внешние ссылки открываются с noopener.

Внутренний read-only /admin/navigation-link разрешает code/id и актуальные
сохранённые поиски через штатные Search/SearchType/SearchKey и конфигурации.
Заметки/таски разрешают полиморфного родителя по исходным метаданным Handler;
снимки/файлы используют Snapshot и ThumbWdg, сохраняя точную версию/контекст.
Права проекта, SearchType и родителя проверяются сервером отдельно; приватность
заметок остаётся штатной Note.alter_search. Проекция login не выдаёт пароль.
XML-RPC контракт и исходники/настройки ТХ не меняются.

App остаётся хостом переходов: открывает существующие окна объекта, заметок,
таска и файлов; состояние ссылки принадлежит вкладке поиска. Сохранённый поиск
переиспользует preset-link вкладку и перечитывает серверные фильтры. Адрес
браузера отражает проект/тип/представление или точную внутреннюю ссылку;
заголовок отражает активную вкладку и проект. Скопированный адрес работает
после входа в новой сессии, перезагрузка и Назад/Вперёд восстанавливают контекст.
Открытое рабочее окно блокирует переход без потери черновика; только read-only
окна объекта/preview закрываются при переходе из истории. Ответ прежнего
проекта/вкладки не меняет новый контекст.

Проверки: test_navigation_links.py — родитель/идентификаторы/presets, приватность,
ACL и ошибки; rich_text.mjs — экранирование/URL/модифицированный клик;
navigation_links.mjs — реальный CG, повторное использование вкладок, новая
сессия, reload/история, черновик, запоздавший ответ и touch320. Регрессии
test_activity_feed.py/test_search_configuration.py, activity_feed.mjs,
window_controls.mjs, main_window.mjs, workspace_tabs.mjs и production build
прошли. Пустое рабочее пространство также отражается в URL: закрытый последний
раздел не открывается заново при перезагрузке. Свежие activity-rich-links (живой
QML ТХ) и stream-activity-rich-links сняты на одной реальной заметке из тестового
CG. В исходном QML цепочка QString.arg переинтерпретирует проценты URL-encoding
в rich text; веб обрабатывает ссылки отдельно от форматирования предложения.

Пункт 1 целиком ещё открыт: Transaction Log и ранее перечисленные части
главного окна. Специализированные preview Knowledge/сообщений/профилей и полная
паритетность всех SkeyPreviewController сценариев этим блоком не заявляются.
PostgreSQL и другие браузеры не проверялись; временные процессы завершаются.

### 2026-10-08 — пункт 1: Transaction Log

В актуальном Handler нет отдельного QML-экрана Transaction Log: журнал —
штатный SearchType. Источник структуры — исходный
`transaction_log-conf.xml`: таблица Code/Login/Timestamp/Description/Namespace/Type,
Details как HiddenRowElementWdg с FastTableLayoutWdg/log, затем XmlWdg.
Change history теперь открывает это разрешённое XML-представление. Details
раскрываются внутри таблицы; отдельное рабочее окно здесь не добавляется.
Общие AppButton и CodeBlock обеспечивают кнопки, экранированную подсветку XML,
копирование, обновление и повтор после ошибки. Предел высоты исходного XmlWdg
600 px ограничивается доступной высотой экрана; широкая таблица прокручивается
в своём контейнере, Details остаются читаемыми на 320 px.

Данные читает native Search/SObject. Внутренние JSON-операции допускают только
администратора с правами текущего проекта и типа; namespace ограничивает выдачу.
Список, фильтры, сортировка и подсказки используют разрешённые столбцы без ticket
и сырого transaction. XML проверяется, исходная zlib-компрессия распаковывается;
секретные поля/атрибуты, JSON и позиционные строки backup маскируются. Операции
недоступного проекта/типа и недоступные через native Note заметки скрываются.
Защита общего XML-RPC чтения журнала сохраняется. Перенос поддерживает только
точный исходный descriptor Details; произвольный HiddenRowElementWdg runtime
не заявляется. Native Command и undo/redo не менялись; старый HTML transaction
popup и отдельный UI undo/redo этим блоком не переносились.

Проверки: test_transaction_journal.py (native journaling, zlib, границы проекта,
страницы, подсказки, проекции, маскирование, ошибочный XML, права),
test_search_configuration.py и test_navigation_links.py. Chromium на реальном
CG-шаблоне: поиск/подсказки/сортировка/страницы, Details, экранирование, повтор
после ошибки, reload и touch320; navigation_links.mjs и main_window.mjs.
Снимки: .screenshots/handler-current/stream-transaction-journal.png и
stream-transaction-journal-mobile.png. Production build проверен.
result_views.mjs также прошёл: шесть видов, группировка, дочерние связи,
версии, сохранение состояния и мобильный лейаут. Его устаревшая подстановка
вкладок в localStorage заменена открытием Assets через штатный URL, чтобы
проверять реальный маршрут и не конфликтовать с восстановлением адреса.

Изолированный повтор test_activity_feed.py прошёл; первый параллельный прогон
не нашёл ожидаемое событие change — нестабильность проверки остаётся отмеченной.
Случайный расширенный прогон test_transport также выявил ошибки в старых
контрактах и браузерных сценариях. Он не считается успешным, полная транспортная
совместимость не заявляется. Пункт 1 целиком ещё открыт; PostgreSQL и другие
браузеры этим блоком не проверялись. Временные серверы и браузеры завершаются.

### 2026-10-08 — пункт 1: управление подключением и интервал обновлений

Из актуальных Main.qml/connectionMenu, ActionMenuRow.qml, ConnectionMixin и
ServerUpdateService изучены Ping now, состояния подключения, ширина 330 px,
компактный индикатор ниже 900 px и интервалы 5/10/30/60 секунд с default 30.
Живой QML снят новым --connection-only с временным профилем: connection-menu.png;
браузерный снимок — stream-connection-menu.png. Исходники и настройки ТХ не менялись.

ConnectionMenu — предметный компонент над общими AppMenu/AppButton/AppIcon.
Ping использует действующий native XML-RPC-compatible метод через JSON transport,
без нового серверного метода. Ошибка доступна для повторной проверки, истёкшая
сессия обрабатывается существующим logout. Старый ответ после смены проекта,
билета или уничтожения компонента игнорируется. Один экземпляр меню через
Teleport перемещается из app bar в меню «три точки» на <=700 px; отдельного
мобильного дубля нет. Общие заголовки AppMenu теперь используют исходные 10 px/
28 px и secondary text; отметка выбранного интервала справа использует существующую
menu-check. Палитры, иконки и анимации остаются общими.

networkSettings — один владелец браузерного интервала, с сохранением и проверкой
значения при чтении. Connection и Configuration/Global читают одно значение;
настройка использует SettingRow/AppSelect, preview и существующие Reset/Apply/
Save/Cancel. ActivityFeed меняет задержку своего единственного таймера, не
запускает параллельный запрос при изменении интервала и завершает таймер при
выходе. Успешный/неуспешный фоновый запрос обновляет статус подключения; отказ
в правах на ленту не выдаётся за отсутствие сервера. Истёкший билет возвращает
на вход. Настройка относится к браузеру, а не к monitor check_interval XML-конфига.

Проверки: connection_menu.mjs — недопустимое сохранённое значение/default,
реальная частота запросов без второго таймера, общий конфиг, Apply/Save/Cancel/
reload, ping/error/retry, запоздавший ответ при смене проекта, authentication,
единственный экземпляр меню при resize и touch320. activity_feed.mjs,
activity_paging.mjs и main_window.mjs прошли; production build проверен.
Временные Python/браузеры и QML-процессы завершены.

Это перенос управления подключением и текущим опросом активности. Полная
ServerUpdateService паритетность не заявляется: общий пакет сообщений/реакций/
активности/тасков/presence, cache cursor и native transient retry ещё требуют
переноса соответствующих серверных читателей и экранов. Не показываем фиктивную
надпись про готовый пакет. Пункт 1 остаётся открытым; PostgreSQL, Electron и
другие браузеры этим frontend-блоком не проверялись. Отмеченные выше ошибки
общего транспортного прогона этим блоком не исправлялись.

### 2026-10-08 — пункт 1: общий цикл серверных обновлений

Из текущих ServerUpdateService, tactic_query.query_server_updates,
ActivityFeedController.apply_server_batch, TasksController.apply_server_batch и
application_composition перенесён общий batch reader. Сервер использует native
Search/SearchKey и local TacticServerStub; runtime Handler не импортируется.
Внутренний /admin/server-updates получает проект из авторизованного контекста,
проверяет курсоры/TTL/права; XML-RPC контракт не изменён. Пакет включает messages,
reactions/delivery, activity, presence, cacheChanges/cacheRetired и serverClock.
Глобальные heartbeat-команды выполняются в sthpw, как в исходной процедуре.
Автоматической установки chat schema из фонового запроса нет: отсутствие metadata
явно отражается messagesInitialized=false и пояснением в Connection menu.

Проверяются доступ к проекту, типам и родительским объектам, вложенные task/note/
work_hour связи, private notes и подписки на чат. Секретные системные типы не
попадают в cache invalidations читателя. Для удалённых note/task/work_hour без
проверяемого родителя invalidation читателю не выдаётся. Пишущий local API пока
требует admin: у остальных heartbeat/delivery только читаются, не имитируются
успешными; presenceHeartbeatApplied=false. Чтение metadata не открывает raw SQL.
Presence insert использует native metadata argument: исходная передача metadata
в data ошибочно создавала дополнительный вложенный ключ; это намеренно исправлено.

ServerUpdates — один владелец таймера, запросов и четырёх курсоров. Без overlap,
с generation guard проекта/билета, timeout 30 секунд, остановкой на logout/unmount,
паузой скрытой вкладки и возобновлением при возвращении. Интервал берётся из уже
общего networkSettings. Native transient retries 2/4/8/16 секунд молчат первые
четыре сбоя, пятый показывает ошибку/Offline; далее задержка 30 секунд. Успех
очищает ошибку, истёкший билет возвращает на вход. Ошибка не продвигает курсоры.

ActivityFeed больше не имеет отдельного таймера: обогащение существующим читателем
выполняется по initial/activity/project invalidation пакету, сохраняя unread,
уведомления, фильтры, календарь, paging, burst continuity и scroll anchor.
Глобальный presence invalidation чужого проекту не запускает опрос ленты.
Task Manager обновляет открытые данные по пакету. При открытом редакторе/черновике/
занятом запросе сообщает о новых данных; Refresh сохраняет исходные ревизии
черновиков. Конфликт записи остаётся явным. Пакет другого проекта игнорируется.
Экран Messages и persistent client cache пока не перенесены; наличие транспортных
данных не заявляется готовностью этих экранов. ServerClock возвращён, отдельная
синхронизация клиентских часов ещё не подключена.

Две зависимости исправлены в ядре. Transaction публикует staged change timestamps
и без Undo XML: chat/presence не создают пустую Undo-запись, но live cursor участвует
в той же атомарной транзакции. SQLite timestamp predicates через vendor helper
сравнивают UTC instants с полной точностью микросекунд; прежнее сравнение строк
UTC с локальным offset теряло последующие события. Null/даты без времени и другие
vendors сохраняют свои исходные пути. Индексы для больших timestamp выборок здесь
не измерялись: SQLite normalizer применяется к колонке. Native timestamps-only
cursor/limit 101 сохранён; массовые события с одинаковым timestamp ещё требуют
отдельной проверки/исправления, полной надёжностью всех потоков это не объявляется.

Меню сверено с новым живым QML capture (--connection-only, временный offline profile):
connection-menu.png и stream-connection-menu.png. Используются исходный текст,
semantic dynamic-feed/sync/schedule/check-circle во всех пяти шрифтовых наборах,
общие menu controls, размеры и палитра. Отличие — пояснение ненастроенной chat schema.

Проверки: test_server_updates — unchanged Handler script comparison, реальные
сообщения/реакции/квитанции, presence без дублей, отсутствие пустого Undo journal,
rollback, ACL/private notes, schema отсутствует/подготовлена и аргументы;
test_datetime_filters — =/!=/</<=/>/>= для UTC/local offsets и микросекунд;
native Command commit/rollback/context isolation и ClientTransactions — всего
6 проверок прошли. test_activity_feed и test_search_configuration прошли отдельно.
server_updates.mjs — реальные Task writes, сохранение черновика и revision conflict,
idle без второго poller, retry/recovery, курсоры, stale responses, visibility,
session shutdown; connection_menu.mjs/activity_feed.mjs/activity_paging.mjs/
main_window.mjs и production build прошли. Все проверочные процессы завершаются.
Пункт 1 целиком остаётся открытым; PostgreSQL, Electron, другие браузеры и большие
одновременные batch нагрузки не проверялись. Общая транспортная совместимость и
готовность API на 100% по этим проверкам не заявляются.

### 2026-10-08 — исправлены назначения кнопок главного окна

Сверена текущая Main.qml: System activity открывает `notifications`, облако —
`commit_queue`, часы — `activity_feed`. Удалены старые topbarActions, которые
подменяли два последних назначения таблицами sthpw/queue (Tactic Dispatcher)
и sthpw/transaction_log. Таблицы остаются обычными проектными представлениями,
верхние кнопки их больше не открывают. Действия доступны также в узком меню;
проект, выбранная вкладка, поиск и адрес страницы не переключаются.

SystemActivity перенесён из NotificationsView.qml: история текущей сессии,
фильтры All/Server/Check-in/Client, иконка/цвет состояния, время и детали,
безопасные rich links, пустое состояние и очистка. Как в NotificationController,
история ограничена 200 событиями и подавляет повторы в пределах пяти секунд.
Repository sync исключён по указанию пользователя. Источники — сообщения и
ошибки приложения, ошибки/завершение API операций, уведомления Activity Feed,
результаты check-in; фоновые тихие retries не добавляют ошибки до своего лимита.
История очищается при смене сессии, данные запросов/ответов в неё не копируются,
текст использует существующее маскирование секретов. Новых polling timers нет.

Окно использует общие controls, CSS палитру, выбранные официальные шрифтовые
наборы, безопасное форматирование ссылок и v-window для перемещения/maximize.
Свежий QML capture на временном offline профиле: system-activity.png;
браузер: stream-main-shortcuts.png, stream-system-activity.png и версии 360/320.
Отдельные классы ленты и System Activity используют общую геометрию окна;
на мобильном экране фильтры сохраняют иконки и доступные ARIA подписи.

Проверены клики всех трёх верхних кнопок, отсутствие подменяющих table queries,
сохранение рабочего контекста, фильтры/очистка истории, maximize/restore и touch
360/320. Регрессии main_window, connection_menu, activity_feed и activity_paging
прошли; сборка и проверки всех пяти шрифтовых наборов/истории прошли.
Проверочные Python/Qt/браузерные процессы завершаются в finally.

Границы: исправление Commit Queue открывает существующую очередь preview
check-in; полный CommitQueueView ТХ с произвольными операциями ещё не перенесён.
История System Activity отделена от Native NotificationStack (toast/tray/replies)
и полной детализации фонового progress; эти части не объявляются готовыми.
Electron, другие браузеры и PostgreSQL этим изменением не проверялись.

### 2026-10-08 — геометрия поисковых вкладок главного окна

В общий WorkspaceTabs перенесён fittedTabWidth из текущего SearchWorkspaceView.qml:
активная вкладка сохраняет естественную ширину, соседние уменьшаются до 96/84 px;
компактный режим ограничивает естественную ширину 180 px. Подпись центрируется
относительно всей вкладки со смещением вверх на 1 px, закрытие расположено справа
с отступом 4 px. Свежий QFontInfo показывает Segoe UI Regular для native Font.Medium:
поисковые вкладки используют соответствующее браузерное Regular, без синтетической
жирности. Script Editor сохраняет свои размеры и оформление.

Активная вкладка остаётся видимой после программного переключения, закрытия,
восстановления, изменения ширины и перезагрузки. Прокручивается только tablist,
без перемещения страницы, диалога и результатов. Тот же владелец реагирует на
изменение подписей/языка и загрузку шрифта; ResizeObserver/listeners удаляются.

Проверки: tab_widths.mjs — 126 точных сравнений неизменённой формулы QML;
search_tab_geometry.mjs — реальные сохранённые CG-поиски, 1440/1000/720/360/320 px,
центровка, touch, overflow, close/history/reload и отсутствие ошибок страницы.
main_window.mjs, script_editor.mjs и production build прошли.
capture_handler_reference.py --tabs-only снимает текущий QML и фактические размеры
во временном offline-профиле; search-tabs-*.png и stream-search-tabs-*.png сохранены.
Текстовые метрики Qt и Chromium различаются до 7 px на длинных подписях;
это не заявляется полным совпадением растеризации по пикселям. Полный drag-motion,
нативный список действий вкладок и пункт 1 целиком остаются открытыми.
PostgreSQL, Electron и другие браузеры здесь не проверялись.

### 2026-10-09 — меню поисковых вкладок и отдельная история

SearchWorkspaceView/ActionMenuRow сверены с текущим контроллером search_tabs и
closed_search_tabs. Выпадающий select заменён списком открытых вкладок: иконка,
название, отметка активной, вторичная кнопка закрытия. История отделена от этого
списка и стоит после result actions: badge количества/99+, Clear history,
разделитель и восстановление в исходном порядке закрытия. Последняя вкладка
не закрывается. Состояние и черновики остаются у существующего владельца App.vue.

Строки используют общий AppMenuItem из AppButton/AppIcon; общий AppMenu закрывает
popover до вызова действия, чтобы не перекрывать подтверждения владельца экрана.
Стрелки перемещают фокус между строками, Tab достигает кнопок закрытия, Escape
возвращает фокус на trigger. При исчезновении trigger доступна активная вкладка.
Названия пользователя отображаются текстом без перевода. Новая semantic tab
сверена с MaterialIcon и доступна во всех пяти официальных шрифтовых наборах.
Кнопки Move left/right сохранены как веб-адаптация для тача/клавиатуры; native QML
список их не содержит. Меню Script Editor сохраняет свой прежний контракт.

search_tab_geometry.mjs проверяет 15 вкладок, automatic first focus, secondary
close, сохранение активного поискового черновика при закрытии соседей, count,
restore/clear/reload, последнюю вкладку, перемещение и ограниченную прокрутку
на 1000/360/320 px. main_window, script_editor, connection_menu, icons,
126 сравнений fittedTabWidth и production build прошли. Проверочные процессы
закрываются в finally. Свежие исходные QML popup captures: search-tabs-menu-*.png,
search-tab-history-320.png; браузерные снимки имеют префикс stream-.
Пункт 1 остаётся открытым: полная анимация и жесты перетаскивания ещё не перенесены;
точное совпадение растеризации, Electron и другие браузеры не подтверждены.

### 2026-10-09 — движение горизонтальных вкладок

WorkspaceTabs использует Pointer Events вместо HTML5 drag: вкладка следует за
указателем, увеличивается до 1,03; соседи сдвигаются на её ширину с native
motionMedium/OutCubic. Порог 10 px подтверждён живым QApplication.styleHints;
displacedX сверяется с неизменённым QML в 720 случаях. Подсветка WorkspaceTabVisual
сохраняет native 8/12% и цвет активного состояния. Порядок меняет существующий
владелец только при отпускании, без API-записи и переключения активной вкладки.

Mouse/touch используют один жест. Escape, потеря фокуса/capture, второй палец,
изменение размеров и unmount отменяют его; вертикальная прокрутка и pinch zoom
разрешены. Передача implicit touch capture от кнопки к вкладке не считается
отменой. Layout-геометрия исключает scale предыдущего жеста. Listeners/capture
удаляются при завершении. Reduced motion использует существующие theme tokens.
Script Editor сохраняет имевшийся web reorder через тот же компонент; native
ScriptEditorView собственного DragHandler не содержит, это общая web-адаптация.

При восстановлении browser address существующая вкладка сохраняет черновик;
явное открытие ссылки по-прежнему обновляет её. Проверка ссылки/доступа сервером
сохраняется. Это исправляет сброс текста сохранённого поиска после reload.

Проверены реальные CG-поиски: оба направления, отсутствие commit до drop,
сохранение порядка/черновика после reload, Escape/blur/resize, touch cancel и
второй палец. Script Editor проверяет reorder вместе с несохранённым кодом.
Свежие drag-снимки текущего Qt и браузера: search-tabs-drag.png и
stream-search-tabs-drag.png. Вертикальный SectionTabRail остаётся отдельным
следующим блоком; весь пункт 1 и полное совпадение по пикселям не объявлены готовыми.

### 2026-10-09 — движение разделов вертикальной полосы

SectionTabRail использует Pointer Events для mouse/pen в раскрытой строке;
соседи сдвигаются на native 42 + 3 px, источник следует за указателем без scale.
Раскрытие остаётся поверх UI, не меняя ширину рабочего поля. Поповер отображает
поверхность native delegate: 256 px при минимальной внешней ширине 260, без
добавленной рамки; clip раскрытия использует motionMedium/OutCubic, hover/press
подсветка — ItemSurface 8/12%. Close icon 14 px. Title занимает доступную ширину.

Mouse reorder не переключает активный раздел и не меняет поисковый черновик.
Escape/blur/resize/cancel/unmount снимают capture/listeners; popup следует за
прокрученной строкой и скрывается, когда она ушла из viewport. После drop
раскрытие привязано к новому положению. Hover latch 350 ms сохранён. Touch
сохраняет обычную прокрутку и имеющиеся long-press действия Move up/down/Close;
вертикальный drag не перехватывает touch scroll.

Свежий живой QML capture выявил дефект native indexAt(rail.width/2, center):
X=160 не попадает в соседние collapsed delegate шириной 48. При наведении на
строку 2 Qt возвращает target=3 (последнюю). Web определяет строку по её Y;
сам displacedY сверяется с неизменённым QML в 180 случаях. Это осознанное
исправление попадания в строку в ТС; Handler не изменён. Геометрия и снимки
section-rail-hover/drag сохранены вместе с browser stream- версиями.

section_tabs.mjs проверяет overlay, оба направления, commit только при release,
popup alignment после drop, порядок/черновик после reload, отмену, hover latch
и touch long-press на 360/320. Пункт 1 целиком и точное совпадение растеризации
не объявлены готовыми; Electron и другие браузеры не проверены.

### 2026-10-09 — прокрутка длинной полосы разделов

Живой текущий Qt проверен с 24 разделами: pixelDelta 90 перемещает contentY
ровно на 90; геометрия и снимки section-rail-long/scrolled сохранены. Handler
и пользовательский профиль не изменены. Веб-проверка использует более 20
реальных SearchTypes из импортированного cg.zip, без искусственных DOM-строк.

Исправлены две ошибки общего SectionTabRail. Отмена touch hold через inline
clearTimeout в Vue template вызывала несуществующий _ctx.clearTimeout, поэтому
свайп оставлял таймер меню активным. Отмена теперь идёт через setup-функцию;
движение и pointercancel действительно снимают таймер. Resize отменяет gesture,
hold и transient popup, чтобы раскрытая строка не оставалась за пределами rail.
Resize listener снимается при unmount. Это веб-адаптация отдельного popover:
в QML раскрытая строка остаётся частью делегата, а не отдельным верхним слоем.

section_scroll.mjs проверяет wheel/keyboard scroll isolation, следование popup
за строкой, закрытие при выходе строки из viewport, resize, Navigation и
Configuration, обычный touch scroll на 360/320 без меню, перестановки и смены
выделенного раздела. section_tabs.mjs дополнительно проверяет resize во время
drag: порядок не сохраняется, popup закрывается. Сборка и проверки section_scroll,
section_tabs, main_window прошли. Снимки stream-section-rail-scroll-360/320
проверены визуально. Полная точность по пикселям, Electron и другие браузеры
не подтверждены; весь пункт 1 остаётся открытым.

### 2026-10-09 — восстановление рабочего окна и владение состоянием вкладки

Сверены NavigationMixin._write_search_cache/_restore_section_tabs и применение
workspace_layout текущего Handler. Исправлен сброс сохранённой страницы: режим
загрузки теперь хранится вместе с вкладкой, старый cache без этого поля читается
как pages. Сохраняются ключи выделенных объектов, но не их данные. При чтении
ключи проверяются по типу/длине, устраняются дубликаты, предел 5000 соответствует
native верхней границе размера страницы. После загрузки выделение пересекается
с фактически возвращёнными сервером объектами; устаревшие ключи отбрасываются.
Поздний ответ не восстанавливает выделение поверх нового запроса/другой вкладки.

После авторизованного bootstrap поверхность повторно восстанавливается через
существующий restoreSearchTab, когда shell и его refs уже смонтированы. Это
возвращает сохранённую прокрутку и доки, а не пытается применить их к отсутствующему
DOM. Повтор не делает новый запрос строк, если вкладка уже загружена.

App.searchStateTab — ссылка на существующую вкладку, которой принадлежат текущие
поля App; это не второй набор состояния. Capture и показ результатов используют
этого владельца. Во время асинхронного перехода события закрытия старой панели
больше не записывают старые поля во вкладку нового проекта. Исходный layout
запоминается до Object.assign/nextTick, поэтому закрытие старого Task Manager
не заменяет layout целевой вкладки. Состояние очищается при logout/empty workspace.

workspace_restore.mjs воспроизводил сброс второй страницы, потерю scroll и
перенос открытого дока в другой проект. Теперь проходят сохранение страницы,
выделения, scroll, active project/section/tab, отбрасывание недоступного ключа,
reload на 320 px и работающий Task Manager снизу после запуска из другого
проекта. Снимки stream-workspace-restored-320/dock просмотрены. Чистые проверки
workspace_state/docks, сборка, search_tab_geometry, main_window, section_tabs и
navigation_links прошли. Drag-проверка ждёт доступного стабильного tab control
перед низкоуровневыми событиями мыши.

Этот блок проверяет pages. Восстановление всех ранее загруженных порций длинной
infinite-выдачи ещё не доведено; весь пункт 1, Electron и другие браузеры остаются
открытыми. Изменений Handler, backend API и схемы БД здесь нет.

### 2026-10-09 — восстановление непрерывной выдачи

Перенесён порядок NavigationMixin._write_search_cache / restored_page_offsets
и SearchRuntimeMixin._query_saved_projection: вкладка сохраняет смещения
загруженных порций и при повторном открытии запрашивает их последовательно.
Все порции публикуются вместе, с устранением повторов по search key. Смена
вкладки отменяет публикацию старого запроса; при возвращении незавершённая
выдача восстанавливается целиком. Reload Cache использует тот же путь.

В cache сохраняются только параметры выполненного запроса из разрешённого
списка. Набранный без Enter текст остаётся отдельным черновиком и не меняет
восстанавливаемый запрос. Ticket, project, search_type, columns и произвольные
поля из сохранённого query не принимаются: контекст берётся из действующей
сессии/вкладки, права и фильтры проверяет существующая серверная операция.
При отправке нового поиска прежний выполненный запрос сбрасывается сразу,
чтобы отмена не возвращала старую выдачу. Данные объектов и schema не кэшируются.

Предел cache смещений — первые 256, как в Handler. Web принимает только
неотрицательные safe integers, устраняет повторы и сортирует, вместо native
приведения строк/дробей/отрицательных значений. Размер порции ограничен
действующим серверным контрактом 1–500; слишком большой сохранённый размер
возвращается к 50. Намеренное отличие: total/nextOffset/hasNext берутся из
новых ответов сервера, а не старого cache. Если выдача сократилась, восстановление
останавливается при её окончании, выделение пересекается с текущими объектами.
Next offset считается по числу сырых строк порции, независимо от дедупликации.

При ошибке восстановления сохраняются исходные смещения, query, выделение
и scroll; существующая Retry повторяет всю загрузку. Промежуточные строки
не выдаются за готовый результат, а пустой viewport не перезаписывает scroll
незагруженной вкладки. Ошибка обычного append сохраняет уже загруженные строки.

workspace_infinite.mjs на реальном CG проверяет три порции после reload,
черновик/выполненный запрос, выделение из второй порции и scroll, ошибку второй
порции/Retry, отмену Reload Cache сменой вкладки, отмену отправленного поиска,
ошибку append, пересекающиеся порции/raw offset, сокращение серверной выдачи
и 320 px. workspace_restore, search_tab_geometry и main_window прошли;
workspace_state проверяет malformed cache, ограничение смещений/размера,
удаление чужого контекста и отсутствие данных объектов. Сборка прошла,
снимок stream-workspace-infinite-320 просмотрен. Тестовые серверы/браузеры
закрываются harness в finally.

Восстановление этой выдачи проверено. Полная готовность пункта 1, Electron,
другие браузеры и точность всех поверхностей до пикселя остаются открытыми.
При стартовом bootstrap рабочее окно пока скрыто до окончания восстановления;
проверенная отмена относится к повторной загрузке уже открытого окна.

### 2026-10-09 — доступное окно во время стартового восстановления

Сверены Main.qml (видимый host и независимый loading progress) и
SearchRuntimeMixin._restore_cached_tab/_show_tab_if_current текущего Handler.
После проверки ticket, каталога проектов/SearchTypes, identity и навигации
Vue монтирует рабочее окно до загрузки строк. Начальный URL обрабатывается
один раз перед выбором результатов, без последующего возврата на стартовую
вкладку. Удалён второй restoreSearchTab после bootstrap. Sign-in проходит
тот же порядок; просроченный ticket возвращает форму входа.

Во время загрузки доступны существующие вкладки/навигация. Переключение
отменяет публикацию стартового запроса; его поздний ответ не меняет активную
вкладку или адрес. При возвращении незавершённая выдача загружается целиком.
Tab.loaded становится true после восстановления выделения и viewport;
при переходе в уже загруженную вкладку её строки берутся из памяти, но viewport
также проходит эту фазу. aria-busy учитывает всю фазу восстановления, а ошибка
не оставляет панель навсегда busy. Никакой второй копии состояния не добавлено.
Dock changed, как capture, проверяет владельца полей: события старого/ещё
не восстановленного host не заменяют layout целевой вкладки.

Найдена воспроизводимая браузерная особенность: в Chromium таблица со шрифтовыми
контролами меняет геометрию между beforeunload и pagehide. Тест фиксировал
scroll 700 / content 3510 перед уходом и scroll 562 / content 2790 в pagehide.
Теперь beforeunload сохраняет живой viewport. Pagehide повторно сохраняет
параметры/выделение/layout, но не измеряет уходящую поверхность. Обычный scroll
обновляет позиции текущей загруженной вкладки в памяти, включая горизонтальную
прокрутку, без сериализации всего workspace на каждом событии; hidden/loading
и чужая вкладка исключены. Обработчики удаляются при unmount.

workspace_startup.mjs на реальном CG задерживает вторую из трёх сохранённых
порций: рабочее окно остаётся доступным; на 1280 и touch320 можно перейти
в другую вкладку, затем вернуть исходные строки, выделение и scroll. Cache
проверяется до reload, при ожидающем старте, после отмены и позднего ответа.
Отдельно задерживается identity: до завершения проверки shell и запросы строк
не появляются. Просроченная сессия очищается, показывается вход. Снимки
stream-workspace-startup-1280/320 просмотрены. workspace_restore,
search_tab_geometry и navigation_links прошли после изменения старта.
Финальные workspace_startup, workspace_infinite и main_window также прошли;
чистые workspace_state/docks и production build успешны.

Ранее указанное ограничение скрытого до конца восстановления стартового окна
снято. Полная готовность пункта 1 и точность остальных поверхностей, Electron
и другие браузеры остаются открытыми. Backend, XML-RPC и Handler не изменены.


### 2026-10-09 — индикатор System Activity в главном окне

Источник — текущий Main.qml notificationActivityButton и controls/BusyIndicator.qml.
Новый режим capture_handler_reference.py --progress-only запускает настоящий Handler
на временном автономном профиле и завершает его после снимков. Измерены extent
36×36 / 220×36, поверхность 34×32 / 218×32, порог compact строго <760 px,
спиннер 22 px, иконка 20 px, Body 9.25 pt Medium и motionMedium 56 ms OutCubic.
Свежие system-progress-*.png и system-progress-geometry.json находятся в
.screenshots/handler-current; браузерный тест сравнивает размеры с этим JSON.

SystemActivityButton — предметный presenter поверх общих AppButton/AppIcon и
BusyIndicator, без API и второго владельца запросов. App отдаёт существующие
фазы загрузки результатов/добавления порции/восстановления viewport/Reload Cache.
Ручной Ping испускает busy из ConnectionMenu, снимая его в finally, при смене
проекта/билета и unmount; старый ответ не завершает новый запрос. Постоянный
ServerUpdates остаётся тихим. Кнопка открывает ту же историю Notifications и
остаётся доступной при загрузке, включая края полного extent 36×36.

Один экземпляр presenter через Teleport переезжает в settings-menu при <=700 px,
как существующий ConnectionMenu: без дубля действия, с тем же состоянием и
описанием текущей работы. На 701–759 px в шапке остаётся компактный спиннер;
с 760 px появляется текст с ellipsis и title. RU/EN переключаются общим t.
Hover/press 8%/12%, ripple и palette используют общие владельцы. Keyboard focus
сохраняет браузерный индикатор. Reduced motion отключает раскрытие и вращение.

Дуга не заменена фиксированным вращающимся бордером: использованы параметры
[исходного Qt Material BusyIndicator](https://codebrowser.dev/qt6/qtdeclarative/src/quickcontrols/material/impl/qquickmaterialbusyindicator.cpp.html):
span 10–300°, рост OutQuad 700 ms, сокращение InQuad 700 ms, rotation 720°/4200 ms,
pen 2 px при extent 22. CSS conic-gradient/mask и зарегистрированные angle
properties передают эти фазы без SVG, зависимости или JS frame loop. Сдвиг
старта 290° на цикл сохраняет непрерывность; 36 циклов замыкают период 50.4 s.
Тест останавливает CSS animations на 0/350/700/1050/1400 ms и проверяет углы.
Qt рисует дискретные кадры QPainter, CSS — непрерывные; raster/text rendering и
фаза после повторного запуска не объявлены пиксельно идентичными Qt.

system_progress.mjs проверяет геометрию live-QML, порог, arc phases, нормальное
завершение/ошибку Ping, reduced motion, историю во время запроса и touch320/360.
main_shortcuts, connection_menu, main_window и workspace_startup прошли после
переноса; production build успешен. Снимки desktop/compact/mobile просмотрены.

Пункт 1 целиком ещё открыт. В эту фазу не включены запросы, которыми владеют
отдельные редакторы/инспекторы; их привязка к глобальной активности и native
NotificationStack/tray/replies остаётся в плане. Firefox/Safari/Electron и
старые браузеры без @property не проверены. Handler/backend/XML-RPC не изменены.


### 2026-10-09 — общая стопка уведомлений главного окна

Источник — текущие NotificationStack.qml, NotificationToastWindow.qml и
NotificationController Handler. capture_handler_reference.py --toasts-only
запускает настоящий Qt на временном автономном профиле, сохраняет снимки
notification-stack/progress и JSON геометрии, затем завершает приложение.
На одинаковых данных измерены ширина 420 px, высоты 70/77 px, превью 46 px,
закрытие 28 px, промежуток 8 px и поля текста. Снимки ТХ и Stream, включая
320/360 px, просмотрены. Шрифты/иконки/palette берутся из общих controls.

NotificationStack — presenter поверх AppButton/ItemPreview/AppProgress; запросов
и отдельной истории у него нет. Один notifications.js обслуживает активные
карточки и существующую историю System Activity. Максимум 3 карточки от старых
к новым, история 200 от новых к старым; активный дубль подавляется, после
закрытия действует окно 5 секунд. Таймеры 3200/5000/8000 ms соответствуют
обычному/ошибке или предупреждению/Activity Feed. Clear history не закрывает
карточки и не сбрасывает дедупликацию. Reset при смене сессии, выходе и unmount
отменяет таймеры и очищает данные. Progress обновляет одну постоянную карточку,
без таймера/закрытия/записи в историю. Она исчезает по завершении операции.

Удалены отдельные workspace/activity popup. App передаёт ошибки, завершение,
Activity Feed и существующие фазы загрузки в общего владельца. Save Preferences
уведомляет прямо из операции: повтор после исчезновения карточки не теряется
из-за одинакового значения Vue watch. Activity action открывает тот же feed.

Адаптация OS Window к браузеру — manual popover в верхнем слое, Teleport в
последний открытый dialog. Так кнопки доступны при modal inertness; открытие
и закрытие окон не забирают фокус. Карточки ограничены viewport, с отступами
18 px, без придуманной анимации появления. AppProgress переносит формулу Qt
Material из qquickmaterialprogressbar.cpp: x=v*w, width=v*(w-x), два сегмента,
1240 ms OutCubic + 520 ms пауза, цикл 1760 ms, высота 4 px и track accent25%.
Reduced motion оставляет статичный сегмент. CSS/Qt raster и начальная фаза
не объявлены пиксельно одинаковыми.

notifications.mjs проверяет таймеры/лимиты/дедупликацию/clear/reset/progress;
notification_stack.mjs — live-QML размеры, три источника, повтор сохранения,
Activity Feed, интерактивность под окнами, touch320/360, выход и формулу
анимации на 300/1000/1600 ms. main_shortcuts, activity_feed, main_window,
navigation_links, system_progress, workspace_tabs, native_table_cells и production
build прошли. В старых тестах ожидания отделены от истории и активных карточек;
новый проект проверяется после выбора его типа, а независимый mobile context
получает layout через штатный Save Preferences. Открытие меню ожидается до
измерения. Поведение продукта этими уточнениями не подменено.

Пункт 1 целиком остаётся открыт. Messages, quick replies, OS tray/beep,
глобальная активность отдельных редакторов/инспекторов не перенесены этой
фазой. Firefox/Safari/Electron и старые CSS engines не проверены.
Handler/backend/XML-RPC не изменены.


### 2026-10-09 — запросы редакторов в общей индикации

Текущие Main.qml, SearchRuntimeMixin._set_loading и
NotificationController._loading_changed задают одну глобальную активность.
Прежние фазы результатов/Reload Cache/Ping сохранены. Общий HTTP post и upload
в api.js теперь публикуют минимальные pending entries; App подаёт их в уже
перенесённые SystemActivityButton и application-progress NotificationStack.
Новые спиннеры, запросы и история не создаются; controls API не вызывают.

Адаптация к параллельному веб-клиенту: каждый запрос снимает свою запись в
finally, включая ошибки fetch/HTTP/JSON/сериализации. Завершение одного не
гасит остальные. Session/project/workspaceProject/unmount сбрасывают список;
поздний ответ удаляет только собственную прежнюю запись. В payload quiet не
передаётся, серверные аргументы/результаты и разрешения остаются прежними.

Тихие запросы — ServerUpdates, Activity Feed poll/live reload, автообновление
Task Manager/NotesPanel, поисковые подсказки и анализ Script Editor. Они не
запускают глобальный progress и не показывают generic completion; ошибки и
Debug Log сохраняют прежнюю обработку. Ручные загрузки/сохранения редакторов,
инспекторов, конфигурации, форм и upload показываются через общий владелец.
Сообщение Working…/Uploading переводится общим t; прежние именованные фазы
главного окна имеют приоритет. Данные запросов в pending не копируются.

request_activity.mjs проверяет overlap, quiet, reset/late completion, upload,
network/JSON/serialization failure и отсутствие глобального progress при входе.
request_activity_browser.mjs использует реальные CG операции: два запроса задач,
quiet refresh из shared poll, смена проекта во время skey-разрешения, поздний
ответ при новом запросе Script Editor, modal failure, 320/360 px и logout.
Полные Script Editor, Task Inspector/native_table_cells, workspace_startup,
system_progress и notification_stack прошли; debug_log_data и build успешны.
Свежий capture_handler_reference.py --progress-only проверил текущий Qt,
снимки desktop/task loading и mobile/editor loading просмотрены.

Это индикация HTTP-запросов и прежних фаз главного окна. Локальное исполнение
браузерного JS и IndexedDB остаётся состоянием соответствующих экранов.
Messages/quick replies/OS tray, другие браузеры и пункт 1 целиком остаются
открытыми. Handler/backend/XML-RPC не изменены.

### 2026-10-09 — исполнение скриптов в общей индикации

Изучены текущие ScriptEditorView.qml (busy), script_editor.py
(_start_local/_run_server/_done/_failed) и script_shelf.py (run/executing).
Свежий capture_handler_reference.py --editor-only снял собственное временное
офлайн-окно Qt; Handler и его пользовательский профиль не изменены.

Редактор и Script Shelf теперь используют beginActivity/endActivity из
существующего владельца pending в api.js. Состояние Running… держится до
получения и обработки результата JS/Python, а не только до ответа HTTP.
Вложенный rpc освобождает свою запись, сохраняя запись исполняющегося скрипта.
Finally освобождает её при успехе, ошибке и устаревшем ответе. Смена проекта
или сессии очищает pending; позднее завершение удаляет только собственную
запись. Существующие права, CSP module execution, захват контекста, защита
generation, блокировка закрытия, stdout/ошибки и результат сохранены.
SystemActivityButton и application-progress остаются общими; новый спиннер,
таймер или второй журнал не добавлены. Running… использует общий переводчик.

Это веб-адаптация индикации жизненного цикла исполнения, а не заявление,
что нативный Main.qml уже связывает busy каждого редактора с global loading.
Локальный браузерный JS из предыдущего блока теперь учтён; IndexedDB остаётся
состоянием экрана. Синхронный JS по-прежнему исполняется в главном потоке:
анимация и принудительное прерывание такого кода этим изменением не добавлены.

request_activity проверяет вложенные запросы, reset и позднее завершение.
Полные CG script_editor/script_shelf проверяют Python, JS/CSP, stdout,
асинхронный успех/ошибку, смену проекта при работающей полке, защиту от
устаревшего окна результата и 320/360 px. request_activity_browser,
notification_stack, system_progress и build прошли. Просмотрены текущий Qt,
desktop/shelf и mobile/editor снимки. Messages/quick replies/OS tray,
остальные браузеры и пункт 1 целиком ещё не завершены.

### 2026-10-09 — геометрия истории системной активности

NotificationsView.qml, NotificationController, ItemSurface.qml,
SegmentedButton.qml, SectionLabel.qml, EmptyState.qml и MaterialIcon.qml
сверены с текущим Handler. capture_handler_reference.py --notifications-only
снял настоящее временное офлайн-окно Qt на 806/760/759/684/683/360/320 px
и записал геометрию панелей, toolbar и строк в system-activity-geometry.json.
Handler, его настройки и серверные данные пользователя не изменены.

SystemActivity использует ширину собственного содержимого для icon-only
фильтров (<760); общий AppSegmentedButton сохраняет radio/keyboard/ARIA и
добавляет штатные tooltip и iconOnly. Его внутренний inset равен Qt: 3px
вместе с CSS border, gap 6px. Repository Sync явно исключён: четыре фильтра.
Check-in использует исходный semantic commit-queue; общий resolver теперь
содержит соответствие для всех пяти наборов (Outline наследует Solid glyph).

Panel margin12 и внутренний inset10, toolbar padding10/gap8, history right
margin8, row right gap12/spacing6 взяты из QML. CSS padding9 учитывает border1,
который Qt Rectangle не вычитает из anchors. ItemSurface перенесён как
декоративные pseudo-elements: inset1/border1, отдельная rail3/top6/bottom6,
hover overlay primaryText8% и 48/56ms OutCubic через текущие motion tokens.
Строка даты меняет grid 2→1 при ширине строки <620, независимо от viewport.
Заголовок toolbar обрезается в одну строку как исходный SectionLabel.
Empty state использует исходный icon30/title10pt/weight600/gap8.
Полная дата в tooltip форматируется общей timestampFullLabel с текущим
языком; sourceType message/activity не переводит текст автора через t.

notification_history.mjs сравнивает размеры Qt/Chromium с допуском 2px на
метрики текста, оба точных порога, inset rail, filters/keyboard/tooltips,
полную дату, empty state, выделяемый текст, экранирование HTML, безопасную
внешнюю ссылку, прокрутку, clear и русский/light/реальные 320/360 px.
Общие web titlebar40/border1 и compact-host margin8 учитываются отдельно
при сравнении содержимого с grabWindow Qt. Полные main_shortcuts,
activity_feed и script_shelf прошли; icons/rich_text/notifications/build
прошли. Native, desktop и mobile/light снимки просмотрены.

Это проверка геометрии и перечисленных сценариев истории, а не готовность
пункта 1 или всей системы сообщений. Messages/quick reply/tray ещё впереди.
Инерция/тайминги Qt SmoothListView и растеризация Qt/Chromium не заявлены
одинаковыми; история использует браузерную прокрутку. Другие engines не
проверены. Backend и XML-RPC не менялись.

### 2026-10-09 — серверная совместимость Messages перед переносом экрана

Изучены MessagesController в communication_feed.py, текущие chat-процедуры
tactic_query.py, SDK wrappers tactic_classes.py, MessagesView.qml,
communication.en.md и явная инициализация в knowledge_api.py. Messages остаётся
незавершённым экраном: список/поиск разговоров, личные заметки и группы,
участники/названия/preview, composer/drafts/mentions, история с восстановлением
прокрутки и группировкой авторов, ответы/пересылка/выделение, edit history,
реакции/emoji, pin/pin history, вложения и skey previews, delivery/read receipts,
presence, shared polling, уведомления и quick replies должны переноситься
вместе. Подмена таблицей и подключение к desktop Handler не добавлены.

В общем Search восстановлены исходные get_database_impl/get_database_type
через собственный DbResource. Отсутствующий первый метод ломал неизменённые
send_chat_message/forward_chat_messages. Api.insert исправляет баг исходного
_insert: data.metadata передаётся add_metadata как весь словарь, согласованно
с update, вместо лишнего metadata.metadata. Иначе создание группы теряло title
и summary. Отдельный аргумент metadata по-прежнему дополняет значения.
SObject.add_metadata отклоняет значения, которые не являются словарём.
Существующие некорректно вложенные данные автоматически не переписываются.

test_chat_compatibility извлекает 15 текущих процедур Handler через AST и
исполняет их неизменённое тело через настоящий XML-RPC на временной SQLite.
Проверены явная DDL-инициализация text metadata (чтение не добавляет колонки),
личные заметки, группы/участники/rename, повтор создания без дубликатов,
сообщение и snapshot-вложение с chat_attachment, ответ, delivery/read и повтор
read, реакции, edit history/один час, pin/unpin/history, paging/search,
пересылка без дублирования источника/адресата, personal clear, soft delete,
сводки, отказ чужому участнику и атомарный rollback сообщения/связи/summary.
Файл вложения не загружался: здесь проверена связь и авторизация snapshot.

StatementParity сравнивает insert/update metadata с настоящим legacy ядром:
исходный nested результат и исправленный плоский результат проверяются
раздельно. Проверочный native insert выполняется с откатом, чтобы сохранять
read-probe fixture. Устаревший тест SQLite cache теперь проверяет существующие
DDL-инвалидацию и принудительное обновление use_cache=False; продукционный
кэш не менялся. Четыре прежних registry расхождения воспроизведены с поведением
ядра до этой правки в памяти отдельного процесса: legacy дважды включает
startup static trigger, native включает один раз. Comparator явно проверяет
это уже существующее исправление; реализация триггеров не менялась.

Границы: новый веб-экран/JSON endpoint и quick replies ещё не добавлены.
Произвольный Python через XML-RPC остаётся admin-only: обычным пользователям
нужны авторизованные фиксированные серверные операции, права не расширены.
В неизменённой forward_chat_messages обнаружен исходный баг: пустой чат имеет
NULL status и исключается фильтром !=deleted. Тест отдельно фиксирует отказ;
пересылка после обычного сообщения работает. Исправление этого запроса входит
в перенос серверной процедуры для веба, а не в изменение SQL-семантики ядра
или кода Handler. Совместимость этих chat-сценариев с PostgreSQL, конкурентные
создания/записи, настоящая загрузка файлов и UI пока не проверены. Пункт 1 открыт.


### 2026-10-09 — фиксированные серверные операции Messages

Добавлены `POST /admin/messages/{action}`: JSON с `ticket`, `project` и только
аргументами указанной операции. Ответ `{result: ...}`, ошибка
`{error: описание, error_code: код}`; ответы `Cache-Control: no-store`.
403 — истёкшая сессия/права/участие/роль, 400 — неверные аргументы или
ограничение операции, 501 — неперенесённая зависимость; нет исполненного
клиентского Python и нет переключения на администратора.

| action | Аргументы помимо ticket/project | Результат исходной процедуры |
| --- | --- | --- |
| list | — | initialized, missingColumns, capabilities, conversations |
| initialize | —; только администратор | list после явного добавления metadata text |
| people | — | users с общей безопасной identity-проекцией |
| create | recipients=[], title='' | conversationId, created |
| rename | message_code, title | title |
| members | message_code, recipients=[], replace=false | added, removed |
| delete | message_code | deleted |
| clear | message_code личных заметок | cleared |
| history | message_code, limit=31, offset=0, search_text='' | messages, pinnedMessage |
| read | message_code, timestamp UTC YYYY-MM-DD HH:MM:SS | lastCleared, receiptsUpdated |
| send | message_code, message='', attachment_keys=[], reply_to=null | message |
| edit | message_log_code, message | edited, editHistory |
| delete-message | message_log_code | deleted |
| reaction | message_log_code, emoji | reactions |
| pin | message_log_code, unpin=false | native pin/history |
| forward | message_log_keys=[], target_message_codes=[] | native forwarded results |
| authorize-attachment | message_code, snapshot_code | allowed |

Например, после получения ticket: `POST /admin/messages/create` с
`{"ticket":"...","project":"one","recipients":["bob"]}` вернёт conversationId;
затем `POST /admin/messages/send` с
`{"ticket":"...","project":"one","message_code":"полученный код","message":"Привет"}`.
`history` принимает тот же message_code. message_log_code/reply_to и элементы
message_log_keys — code или skey только sthpw/message_log; attachment_keys —
skey только sthpw/snapshot. limit 1–100, offset 0–100000, списки до 100 элементов,
текст до 500000 символов, title до 512, emoji до 16. Чужие типы/проекты и
неизвестные аргументы отклоняются до выполнения процедуры.

Все 15 процедур скопированы из текущего Handler (EPL-1.0, LICENSE.HANDLER),
хранение — исходные message/message_log/subscription/connection, транзакции,
триггеры, change timestamps и журнал общего ядра. Участники и роли исходные:
личные заметки/direct доступны пользователю, группы/участники/delete —
администратору или supervisor, rename — владельцу или supervisor; собственные
edit/delete ограничены одним часом. Требуются view ACL и edit соответствующих
таблиц для записи. Список и история у read-only участника не переписывают
receipts/summary; явный deny остаётся запретом. Вложения требуют также view
snapshot/file; обычная загрузка нового snapshot ещё не перенесена.

Внутренний Chat:writing ограничивает серверную запись четырьмя типами чата и
нативным журналом, проверяет ACL SObject и разрешает лишь нужные SDK-методы.
Это не Sudo: login/Environment Security остаются настоящими, generic Python,
произвольный CRUD, security-объекты и SQLite DDL не разрешаются. Чтение настроек
проекта при native commit сохраняет текущий project; записи разрешены только
в системный DbResource. PostgreSQL использует существующий параметризованный
путь системных записей. finally восстанавливает capability при любом исходе.
Грубая native блокировка message сериализует создание/участников/metadata;
переход на более узкую блокировку нужен только при подтверждённой нагрузке.

Отличия от исходного тела процедур: пустая цель пересылки с NULL status
доступна; log_message не меняет создателя и время создания разговора;
get_json_value читает сжатую metadata без потери истории/реакций; read-only
чтение не выполняет недоступные исправления; удалённое сообщение не выдаёт
доступ к attachment. Неизменённые XML-RPC процедуры Handler по-прежнему
проверяются отдельно, код TH не изменён. Тестовая fixture ObjectSecurity
использует существующую registry-запись config/custom_script вместо дубликата.

На временной SQLite проверены ordinary/reader/supervisor/admin, получение
safe identities, участие/роль/ACL, replies, delivery/read, edit/reactions/pins,
attachments к существующему snapshot, clear/delete, compressed metadata,
восстановление scope, запрет generic API/DDL/посторонних таблиц, поздний rollback,
конкурентные создание и реакции. Persistent diagnostics для отказов обычного
пользователя пока ограничены администратором: Command пишет предупреждение
в серверный журнал, исходный отказ и откат сохраняются.

Границы: новый UI Messages, quick replies, реальная загрузка файла и проверка
Messages на PostgreSQL остаются открыты. Веб-операции ещё не подключены к экрану;
пункт 1 не закрыт. Следующий шаг — весь экран по текущим QML/controllers,
включая composer/drafts, timeline/paging, emoji/attachments, уведомления и
общий polling; свежие Qt/browser screenshots нужны при переносе UI.

### 2026-10-09 — первый блок экрана Messages

Экран подключён к 17 фиксированным native операциям. MessagesView владеет
запросами/сессией/черновиками; ConversationList, MessageBubble и MessageComposer
отображают данные и события. Окна используют общий v-window (перемещение и
максимизация), меню/поиск/кнопки/разделитель/аватары — общие controls. Вход один:
Messages в меню аккаунта; уведомление открывает нужный разговор в том же окне.
Сервер возвращает permissions по операциям: read-only не получает активные
write controls, сервер продолжает самостоятельно проверять каждую операцию.

Перенесены разговоры/избранное, создание, rename, состав участников, удаление,
текстовая история/поиск/подгрузка, авторские группы 5 минут, read/delivery,
reply/jump, реакции, pins/history, selection/forward, edit/history/delete.
Черновик текста и ответа отдельный для каждого разговора и аккаунта браузера,
переживает закрытие/перезагрузку. Запоздалая отправка очищает только исходный
черновик; ответы прежней сессии отбрасываются. Диалог редактирования сохраняет
идентификатор исходного разговора. История сохраняет видимый якорь при обновлении
и подгрузке; cache ограничен 12 разговорами. Общие server-updates инициируют
обновление, локальная сверка раз в 5 секунд работает лишь у открытого окна и
видимой страницы. Toast Messages использует общую NotificationStack и 8 секунд.

EmojiPicker общий: исходные 3944 fully-qualified emoji Unicode 17, поиск и
категории, отложенная загрузка JSON; исходный NotoColorEmoji и Unicode/OFL licenses
поставляются с web assets. PNG-фоны ТХ проходят общий безопасный static route;
packaging включает PNG, TTF и licenses. Зависимости не добавлены, исходный TH
не изменён. Руководство/tooltip и часть действий ещё требуют полного переноса.

Свежий Qt capture `tools/capture_handler_reference.py --messages-only` использует
изолированный профиль и offline fixture. Снимок `.screenshots/handler-current/messages.png`
сверен с браузером `.screenshots/messages-web.png`: панели 252/min210, заголовок
58, conversation rows 68, аватары 34/40, native фон/цвета групп/типографические
роли. Точная визуальная готовность всего экрана пока не заявляется. На 320/360
список и переписка переключаются, без горизонтального overflow и обязательного
right-click; `.screenshots/messages-mobile.png` показывает текущий тач-вид.

`frontend/tests/messages.mjs` проверяет реальные HTTP операции на временной
SQLite: черновики, send/reply/edit/reaction/pin/forward/search/rename/members/create,
reload, 35 сообщений с paging без дублей, задержанную отправку со сменой чата,
изоляцию черновиков после смены пользователя, 320/360 touch. Общая NotificationStack
прошла прежнюю Qt geometry/timers/modal/touch/logout проверку. Серверные checks
Messages/ServerUpdates/assets прошли, включая permissions reader/edit и PNG/font
MIME/закрытые пути. Тестовые серверы/Chromium закрываются в finally.

Открыто в этом же пункте: upload/download/media previews вложений, смена preview
разговора, вставка вложений из clipboard, quick replies, оставшиеся native
контекстные действия/tooltip/help и окончательная визуальная сверка. Эти действия
в текущем UI явно обозначены незавершёнными; наличие формы/меню не означает их
готовность. Messages и пункт 1 ещё не закрыты; PostgreSQL Messages не проверен.

## Messages: вложения, 2026-10-09

Следующий блок в том же пункте подключён: выбор файлов, drag-and-drop и paste
в поле ответа, отправка без текста, файл в черновике, повтор отправки без второго
check-in, скачивание, просмотр изображения/текста и смена картинки беседы.
Chat files получает страницы всей истории и файлы пересланных сообщений.
После перезагрузки локальный File недоступен: интерфейс просит выбрать его заново;
при совпадении имени и размера сохраняет исходный token. Уже загруженный snapshot
в черновике повторно не создаётся. Локальные blob URL освобождаются при удалении,
смене пользователя и закрытии владельца; запоздавшие ответы старой сессии игнорируются.

`AttachmentCard` и `ResponsiveFlow` перенесены из текущих одноимённых QML controls:
64 px строка файла, 44 px badge, 14 px radius, Typography bodyLarge/label,
ограниченный натуральным размером web preview, две колонки от 210 px и spacing 8.
Изображение занимает всю строку. Открытие использует общий FilePreview/v-window.
Controls не знают HTTP, ticket или проект; AttachmentItem получает loadFile от экрана.
Снимки нынешнего QML сделаны offline с временным профилем, исходники ТХ не изменены:
`.screenshots/handler-current/messages-attachments.png`. Браузерные снимки:
`.screenshots/messages-attachments-web.png` и `messages-attachments-mobile.png`.
Это проверка текущего блока, а не подтверждение полной визуальной идентичности экрана.

Сервер добавляет фиксированные upload/file/files к прежним 17 операциям Messages.
Использованы существующие multipart parser/64 MiB body limit, FileCheckin, IconCreator,
DirNaming, Snapshot, File и FileUndo. Для обычного пользователя внутренний
Chat:attachment допускает только snapshot/file данного разговора и пути staging,
native naming directory и undo; исходный пользователь и его edit ACL сохраняются.
Скоуп живёт до завершения Command, чтобы late failure откатывал файлы и строки,
затем восстанавливается. Generic XML-RPC права не расширены. UUID и digest обеспечивают
повтор одного upload без дубля и отклоняют другое содержимое с тем же идентификатором.
Загрузка и отправка сообщения отдельны: при ошибке send snapshot остаётся в черновике.

Файлы выдаются через авторизованный POST, no-store/nosniff, с проверкой членства,
snapshot/file связи и resolved пути в репозитории. Непосланный файл доступен только
загрузившему его участнику, preview — участникам беседы, отправленный — по активному
message_log. Удалённое сообщение не даёт доступа. Исправлено native authorize_chat_attachment:
учтена явная forwardedFrom ссылка активного целевого сообщения на активный источник;
копии файлов и произвольное чтение исходного разговора не создаются. UI и gallery
используют существующие attachment records исходного сообщения.

Проверки на временной SQLite: обычный пользователь, idempotency/mismatch, preview,
forward/download/gallery, чужое членство/file, выход за repository/project/FS scope,
late check-in rollback. Браузер: реальный HTTP PNG/text, download, безопасный text preview,
gallery, preview беседы, восстановление черновика, send retry без повторного upload,
paste, forwarded file preview, 320/360 touch и прежние операции Messages.
Старые UploadForm/repository fixtures обновлены с tmp/cache на уже существующий tmp/undo.
Общий HTTP error handler сохраняет флаг object status отдельно от HTTP status, чтобы
Messages ошибки возвращали invalid_request. UploadServer/File API также проверяются.
Qt/Chromium и временные серверы закрываются в finally.

Открыто в этом пункте: quick replies, все действия native attachment context menus,
категории/поиск Chat files, оставшиеся tooltip/help и окончательная сверка всего Messages.
FilePreview поддерживает media elements/PDF, но video/audio/PDF здесь ещё не проверены.
Messages на PostgreSQL ещё не проверен. Отменённые файловые черновики оставляют штатные
непривязанные snapshots: их очистка пока не реализована. Это ограничение, не готовые 100%.

## Messages: quick reply из уведомления, 2026-10-09

Перенесено текущее поведение NotificationStack.qml / NotificationController /
MessagesController.send_quick_reply: Reply раскрывает однострочный редактор прямо
в уведомлении, Enter/Send отправляет ответ в его conversationId через существующий
Messages send. Выбранный разговор, история его навигации, текст, reply target и файлы
обычного черновика не переключаются и не подменяются. После успеха обновляются
список разговоров и видимая история этого чата; само уведомление закрывается.

Внутренний владелец активных уведомлений хранит replyOpen/replySending/replyError/text
и их таймеры. Native message lifetime — 15000 ms; открытие редактора останавливает
таймер, Cancel/Escape сохраняет набранный текст, закрывает редактор и начинает новый
15000 ms интервал. Ошибка сохраняет текст и редактор, повтор доступен. При отправке
поле/Send/Cancel заблокированы, повторный submit не создаёт второй запрос. Ограничение
трёх активных уведомлений сначала удаляет записи без открытого редактора, как в ТХ.
Закрытие уведомления не меняет session history. Logout очищает активные редакторы и
таймеры; старый результат/ошибка не появляется в новом аккаунте и не завершает его сессию.

NotificationStack — presenter; HTTP и generation guard находятся в MessagesView.
App.vue соединяет события/refs, не содержит второй реализации send. Использован общий
AppTextField по TextField.qml, AppButton и существующий общий top-layer host/popover.
Права отправки берутся из серверных permissions; backend проверяет права и членство
существующим контрактом send. Отдельного server API/доступа к произвольному Python нет.
Уведомление показывает отправителя, excerpt и название разговора в порядке native QML.
Репозитори-синк не добавлен. Поля интерфейса проходят через общий en fallback/ru переводчик.

Свежий offline Qt capture с собственным временным профилем:
`.screenshots/handler-current/notification-quick-reply-edit.png`, error/collapsed
снимки и `notification-quick-reply-geometry.json`. Browser: `quick-reply-web.png`,
`quick-reply-error.png`, `quick-reply-mobile.png`. При ширине 420 px проверены native
высоты 123/148 px, поле x=14/y=75/width=286/height=36 и Send width=72; focus border
общего AppTextField приведён к одному native контуру. Исходники/настройки ТХ не менялись.

`frontend/tests/quick_replies.mjs`: реальные временные SQLite/HTTP send, отказ/повтор,
неизменность обычного черновика/выбранного чата, отсутствие второго submit во время
ожидания, сохранение текста при Cancel/Escape, остановка/возобновление таймеров,
320 px touch, logout и запоздавший authentication_failed после входа другого аккаунта.
`notifications.mjs` проверяет timers/eviction/read-only/draft state; прежняя
`notification_stack.mjs` проверка геометрии/активации/progress/modal/touch также прошла.
Сценарии quick_replies/messages запускаются на отдельных свежих временных базах:
они используют разные пароли тестового artist. Собственные тестовые процессы завершаются.

Quick reply закрыт как отдельный блок. Пункт Messages остаётся открыт: категории/поиск
Chat files, оставшиеся tooltip/help и сверка всего экрана.
PostgreSQL и video/audio/PDF ещё не проверены; очистка непривязанных snapshots также открыта.

### Messages: действия вложения — 2026-10-09

По актуальным MessagesView.qml и communication_feed.py перенесены шесть пунктов
attachment menu: Download, Show folder, Download and open, Copy file path,
Copy web link, Copy image. Один AttachmentItem обслуживает timeline и Chat files;
использует общий AppMenu, общий downloadBlob и существующий FilePreview с private
loadFile. Контекстное меню открывается кнопкой, правой кнопкой и удержанием 500 ms;
смещение более 10 px отменяет удержание для прокрутки. После открытия фокус остаётся
в меню: Escape закрывает меню, а не окно Messages. Popup ограничен viewport.

Show folder недоступно с пояснением: браузер не открывает папки компьютера пользователя.
Copy image использует оригинальный файл и Clipboard API: нужен HTTPS/localhost и
разрешение; на обычном HTTP пункт недоступен с пояснением. PNG копируется непосредственно,
остальные поддержанные изображения преобразуются браузером в PNG. Через ТХ/OS bridge
не выполняются команды; репозитори-синк не добавлен.

Fixed `file-info` переиспользует все проверки `attachment_file`: участник чата,
действующее сообщение/forwarded source, связь snapshot/file и resolved repository path.
Возвращает фактический путь с `/` и разрешённые snapshot/file metadata. Отображаемое
имя вложения может отличаться от имени файла, присвоенного штатным неймингом TACTIC.
Меню копирует этот фактический путь. Messages имеет 21 fixed operation.

Copy web link создаёт URL `/projects/<код>/?chat=…&snapshot=…&file=…`; ticket и пароль
не включаются. App сохраняет/восстанавливает адрес, Messages проверяет доступ и открывает
FilePreview; перезагрузка работает с действующей сессией. Недоступная ссылка показывает
ошибку в Messages без открытия файла; закрытие preview убирает attachment параметры.

Свежий offline Qt popup из неизменённого ТХ: `handler-current/messages-attachment-menu.png`.
Browser: `messages-attachment-menu-web.png`, `messages-attachment-menu-mobile.png`.
`tests/test_messages.py`: чужой пользователь, удалённое сообщение и выход за repository
отклоняются также для file-info. `frontend/tests/messages.mjs`: реальные временные
SQLite/HTTP, Download в обоих местах, copy path/web link, reload, недоступная ссылка,
PNG в настоящем clipboard на localhost, HTTP disabled state, right click/hold/motion
cancel/Escape и viewport 320/360. Chromium проверен; PostgreSQL, другие браузеры и
clipboard конверсия не-PNG форматов пока не проверены. Категории/поиск галереи и полная
сверка Messages остаются следующими блоками; весь Messages ещё не объявлен завершённым.

### Chat files: список и переход к сообщению — 2026-10-09

Уточнён текущий исходник ТХ: MessagesView.qml `filesPopup` и контроллер
`conversationAttachments`. В актуальном ТХ **нет категорий и отдельного поиска файлов**.
Прежнее упоминание этих функций в плане было ошибочным. По умолчанию перенесён исходный
набор ТХ; добавление поиска/категорий остаётся отдельным расширением по выбору пользователя.

Галерея теперь строится из загруженной истории Messages, показывает имя файла,
отправителя и относительное время через существующий общий formatter Activity.
Счётчик означает количество загруженных появлений файлов, не количество всех файлов
чата. Повтор одного snapshot в разных сообщениях сохраняется: строка привязана к
messageId, нажатие закрывает галерею и центрирует/подсвечивает соответствующее сообщение
тем же `jump`, что используется для reply/pin. При недоступном forwarded source его
файлы не показываются; разрешённые пересланные файлы сохранены как в прежнем веб-сценарии.

«Load earlier messages» и прокрутка в конец списка используют единственный существующий
history loader и его generation/request/participant guards. Загружается история
сообщений, а не второй независимый набор snapshots. Fixed API `files` сохранён для
совместимости клиентов; UI больше не имеет отдельного loadGallery/offset/cache.

AttachmentItem остаётся одним presenter для timeline и списка файлов; в списке первичное
действие — переход к сообщению, меню — прежние private download/open/copy. Меню наложено
на строку, не добавляет ей высоты. Строка 60 px, gap 6 px, иконка 18 px, отступ 12 px,
rail/separator и hover/pressed цвета по текущему PopupAction/ItemSurface. Рабочий dialog
использует общий v-window: его шапка добавляет перемещение, maximize/restore и Close
вместо native frameless popup. После вычета 12 px Qt shadow и учёта общей шапки сохранены
измеренные native list 328×349 px; на мобильном экране работает общий оконный layout.

Свежие Qt `handler-current/messages-chat-files.png` и `messages-chat-files-geometry.json`
получены из текущего неизменённого ТХ с временным профилем. Browser `messages-chat-files-web.png`
и `messages-chat-files-mobile.png`. Реальный временный SQLite/HTTP тест `messages.mjs`
проверяет геометрию списка/строки, metadata/count, пустую загруженную страницу, более ранние
вложения, автоматическую pagination, forwarding и jump, меню/download и 320 px layout.
Pure assert проверяет повтор snapshot в разных сообщениях и недоступный forwarded source.
Backend/права на скачивание не менялись; новых пакетов нет. PostgreSQL и другие браузеры
не проверены. Весь Messages остаётся незавершённым: rich sKey preview/menu, оставшиеся
tooltip/help и полная сверка экрана — следующие блоки.

### Messages: sKey-карточки и переходы — 2026-10-09

Из текущих неизменённых `thlib/ui/skey_previews.py`, `SKeyPreviewCard.qml`,
`SnapshotSummary.qml`, `ItemPreview.qml` и `ItemSurface.qml` перенесены состояния
объекта, задачи, snapshot, файла, заметки, сообщения, пользователя, проекта и статьи.
Заметка показывает текст, первые четыре связанные карточки и шесть вложений со
счётчиками оставшихся; сообщение — автора, время и исходный текст. Общие ItemPreview,
ItemSurface, AttachmentCard, ResponsiveFlow, BusyIndicator и AppMenu сохраняют
распределение control → presenter → screen → host. Новых библиотек нет.

Операции — открыть, скопировать sKey, повторить недоступное превью; right click,
долгое нажатие и видимая touch-кнопка используют один общий обработчик. Вложенный
контролл получает свой контекстный жест и клик, не открывая одновременно меню/объект
родителя. Безопасный текстовый renderer убирает sKey из тела при показе карточек;
обычные ссылки и текст остаются. EN/RU используют общий переводчик и пять официальных
наборов шрифтов иконок. Время обновляется существующим poll Messages.

Messages запрашивает дескрипторы пакетами по 50, с guards аккаунта, проекта и чата.
Обновление сервера и Refresh повторно разрешают ссылки без промежуточного удаления
готовых карточек. Черновик и scroll сохраняются перед открытием объекта. App открывает
объект общим rich-link resolver либо восстанавливает целевой чат и сообщение; тот же
путь работает из адресной строки. Глобальный message_log не переключает проект на
sthpw. Приватный snapshot открывается существующим FilePreview и каноническим URL
project/chat/snapshot/file без credentials.

Фиксированный API поверх прежнего endpoint:

```json
POST /admin/navigation-link
{"ticket":"SESSION_TICKET","project":"cg_test","keys":["skey://cg/assets?project=cg_test&code=DEMO_ARM"]}
```

Результат — `result.previews` в порядке первых появлений уникальных ключей.
`status` равен `ready` или `error`; `searchKey` связывает ответ с карточкой, `kind`
выбирает presenter. Поля title/subtitle/detail и специальные поля типа доступны только
после серверного разрешения. Чтение других проектов заново проверяет права на проект
и SearchType. Формат массива, размер 1–50, длина каждого ключа ≤16384 и отсутствие
переносов/NUL проверяются до чтения; неправильный контракт возвращает 400. Нет доступа,
удалённый или отсутствующий объект дают отдельную карточку error с общей причиной,
без тела сообщения и метаданных чужого объекта. Старый одиночный аргумент `link`
сохраняет прежний контракт; `keys` и `link` вместе запрещены. XML-RPC не изменён.

English: the authenticated endpoint accepts 1–50 unique native sKey references and
returns ordered, permission-filtered preview descriptors. Loading is a client state;
each unavailable reference gets an isolated generic error. Opening still uses the
original single-link resolver. Chat/message/file previews require active membership
and authorized source attachments; they do not grant access through a copied link.

Членство в переписке, видимость исходного сообщения и доступ к файлу проверяются до
выдачи полей. Private Chat attachments никогда не получают публичный repository URL:
миниатюра загружается через существующий authenticated file transport в Blob URL,
отзываемый при смене scope/cleanup. Ошибка отдельной миниатюры не ломает остальные
готовые карточки. Профили пользователей проходят прежнюю безопасную проекцию, без
паролей/служебных данных. Repository Sync и подключение к работающему ТХ не добавлены.

`STREAM_SKEY_CAPTURE=1 tools/capture_handler_reference.py --messages-only` снимает
реальные QQuickItem из текущего ТХ с временным профилем и завершением собственного Qt
процесса. `.screenshots/handler-current/skey-{kind}.png` и `skey-geometry.json`
сравниваются с `.screenshots/skey-*-web.png` при одинаковой ширине 293 px: обычная
карточка 72 px, snapshot 88, тестовая заметка 191, сообщение 62, статья 78.
Web сообщение отличается на 0.33 px из-за дробной метрики шрифта Chromium.
Геометрия проверяется browser assert с допуском 1 px для динамических карточек;
320/360 не имеют горизонтального overflow и позволяют открыть меню обычным tap.

Проверки: `test_navigation_links` — bounded/dedup/invalid inputs, nested note/file,
чужая/удалённая переписка, приватный snapshot/file, обычный участник без admin,
межпроектные чтения и legacy snapshot с пустым parent metadata.
`skey_previews.mjs` — реальные CG/SQLite/HTTP/Chromium, loading/retry, безопасный текст,
вложенные меню/клики, private image, draft, открытие/reload URL, внешняя правка/Refresh
и мобильные размеры. `messages.mjs`, `quick_replies.mjs` и `icons.mjs` прошли;
production build собран. Собственные тестовые серверы и Qt/browser процессы завершены.

Перенос всего Messages ещё не завершён. Следующий блок: оставшиеся tooltip/help
и полная сверка экрана. PostgreSQL и другие браузеры не проверены; пакетный HTTP
контракт не означает пакетного SQL для каждого дескриптора.

### Snapshot metadata — 2026-10-09

`server/file_presentation.py` переносит чистую проекцию текущих Handler
`MatchTemplate/FileObject` и `_snapshot_chips`: все 13 типов file/no_ext/layer,
sequence, UDIM, UV и их комбинации. Источник — сохранённые check-in metadata,
не угадывание по имени и не обход файлового репозитория. Поля Context, Range,
Frames, Layer, Tiles, Maya идут в native порядке. Для tiled sequence сохранено
текущее строковое представление Frames из ТХ. Диапазоны остаются сжатыми:
200 миллионов кадров не превращаются в список в памяти. Отсутствующие или
повреждённые metadata возвращают обычное имя файла; singleton следует native
fallback. Production не импортирует Qt или код работающего ТХ.

Snapshot получает friendly author через прежнюю безопасную проекцию пользователя
и native каталог названий/цветов репозиториев. Клиентские настройки репозиториев
ТХ недоступны без соединения с ним, поэтому пользовательские подписи/цвета в вебе
задаются общей серверной настройкой `checkin/repository_display`, например:

```json
{"custom_0":{"title":"Studio","color":"#607d8b"}}
```

Настройка доступна в существующем редакторе конфигурации, проверяет JSON, aliases,
названия и hex/RGB цвета; использует прежние permissions/revision/save. Она меняет
только представление. Пути, check-in, права на файлы и Repository Sync не меняются.
Это адаптация клиентских предпочтений к серверному веб-приложению, а не перенос
всего native редактора Repositories.

SnapshotSummary использует общий MiddleElide (Text.ElideMiddle, расширение остаётся
видимым), native metadata/description chips и selected state. Размеры сверены
с настоящими QQuickItem: карточка 88 px, title 13 px, labels 12 px, captions 11 px,
иконка открытия 17 px, chip 17 px. Дробные pt в браузере округляются в этом presenter
до фактической пиксельной метрики Qt. Свежие native/web снимки при ширине 293 и
640 px и font/color measurements находятся в `.screenshots/handler-current/`
и `.screenshots/skey-snapshot*-web.png`. Растеризация шрифтов Qt и Chromium
остаётся разной; одинаковые метрики не означают побитовое совпадение изображений.

Проверено: `test_file_presentation` сравнивает результат с исходными неизменёнными
классами текущего ТХ для 13 типов; тест требует соседний checkout `th_codex`.
Вместе с `test_navigation_links` и `test_configuration_write` прошли 7 тестов.
`skey_previews.mjs` создаёт настоящие snapshot через штатный simple_checkin,
проверяет sequence/UDIM/UV через защищённый HTTP resolver, размеры/метаданные,
EN/dark, RU/light, 320/360 touch, reload и переходы. Регрессия `messages.mjs`
и production build прошли. Временные серверы, Qt и браузеры завершаются в finally.

### Messages: общие tooltip, справка и сохранение истории — 2026-10-09

`controls/tooltip.js` и `tooltip.css` — один общий визуальный контроль по текущему
Handler `controls/ToolTip.qml`. AppButton и AppMenu используют его вместо browser
title для иконок/триггеров. Дополнительная подсказка AppButton передаётся через
`tooltip`, без второй реализации или второго popup на том же элементе.
Задержка 500 ms, время показа 5000 ms, inverse theme, 8 px от anchor/края экрана,
padding 7/12 px, максимум пять строк, enter/exit через общий popup motion.
Popover находится в top layer и принадлежит своему modal dialog; tooltip не
перехватывает pointer events. Наведение и keyboard focus поддерживаются;
touch не требует hover. Escape закрывает видимую подсказку, сохраняя окно чата.
Scroll, resize, click, закрытие окна и unmount отменяют pending/show state;
aria-describedby добавляется и восстанавливается. Пользовательский текст попадает
только в textContent. Отдельная native опция suppressToolTips пока не перенесена.

Messages показывает native delivery tooltip с числом прочтений/доставок; иконка
доставки отсутствует у Favorites без адресатов. Доставленное сообщение использует
двойную галочку, прочитанное — акцент. Полная дата, автор последней правки и список
авторов реакции используют тот же контроль. Существующие события и серверные
проверки операций сохранены.

`controls/HelpArticle.vue` — общий presenter одного справочного материала, с
прокруткой, summary и разделами, поверх прежнего v-window (перемещение/maximize/
restore). Messages передаёт данные из `messagesHelp.js`. Это адаптация актуальной
`help_articles/communication.en.md` и `.ru.md` к работающим web Messages: чаты и
черновики, отправка/вложения/ошибки, действия/права, sKey/доставка/уведомления.
Технические desktop-only указания про tray и недоступные функции не обещаются
в веб-справке. Открытие/закрытие Help не меняет выбранный чат или черновик.
Полный каталог и поиск тем HelpView, открытие/редактирование Markdown-файла и
справка других экранов не перенесены этим блоком.

При проверке истории устранены два разрыва. Граница refresh теперь учитывает
native timestamp/id ordering, сохраняя старые сообщения той же секунды. После
серии новых сообщений перенесён алгоритм MessagesController._load_messages:
догрузка до пересечения с retained history или конца истории. Обычный poll читает
одну страницу; web catch-up использует последовательные страницы по 30, сохраняя
ограниченный HTTP контракт вместо native удвоения размера запроса. Scope/request
guards действуют после каждой страницы. Offset описывает непрерывный загруженный
диапазон; отсутствующие в полном серверном ответе сообщения не сохраняются как
старый cache. Это исправление причины пропусков, не увеличение случайной задержки.

Свежий неизменённый ТХ снят через
`STREAM_MESSAGES_HELP_CAPTURE=1 tools/capture_handler_reference.py --messages-only`:
`messages-tooltip.png`, `messages-help.png` и font/geometry evidence в
`.screenshots/handler-current/`. Web evidence: `messages-tooltip-web.png`,
`messages-help-web.png`, `messages-help-ru-mobile.png`.

Дальнейшая полная сверка Messages остаётся отдельным незавершённым блоком:
native меню чата по context gesture из списка, badges участников/упоминаний,
last-seen и jump-to-latest, контур/типографика bubble и расположение метаданных,
emoji-only размер и состояния composer. Native тематический Help-каталог и
точная растеризация Qt/Chromium также не объявляются готовыми.

Проверки этого блока: production build (199 modules), `messages.mjs` и `icons.mjs`
прошли. Browser проверяет задержку/timeout, размещение tooltip над нижним краем,
ARIA, отсутствие двойного title, focus/Escape, delivery/edit metadata, Help
maximize/restore и черновик, RU/light 360 px, burst catch-up, свежие/старые файлы,
полный сброс отображаемых сообщений после Clear Favorites и прежние операции.
Пять официальных icon catalogs сохранены. Временные Qt/HTTP/browser процессы
завершены; PostgreSQL и другие браузеры этим блоком не проверялись.

### Messages: меню списка, badges, presence и jump-to-latest — 2026-10-09

Закрыт следующий блок сверки с текущими `MessagesConversationList.qml`,
`MessagesView.qml`, `MessagesTimeline.qml`, `CompactIconButton.qml` и
`communication_feed.py` из неизменённого Handler:

- ПКМ по чату выбирает этот чат и открывает тот же `chat-actions`, что используется
  в шапке. История загружается параллельно и не отбирает focus у меню.
  Общий `contextActions` обеспечивает touch hold 500 ms с отменой при движении,
  Shift+F10/ContextMenu; обычный вход через меню шапки сохранён. Операции,
  подтверждения, права и редакторы остаются у единственного MessagesView.
- Непрочитанные упоминания обозначены отдельным `@` 18 px, рядом со счётчиком
  unread. Строка непрочитанного чата получает rail исходного цвета. После
  успешного read локальные unread/mentionCount очищаются вместе, а серверный
  список остаётся источником данных.
- В AppButton перенесён общий badgeCount: 16 px, error background, surface border,
  caption font, значения выше 99 отображаются `99+`. Кнопки Chat members и Chat
  files используют participantCount/attachmentCount существующего контракта.
  Badge не обрезается круглой кнопкой; общий ripple теперь имеет собственный
  clipping container и завершается вместе с ним. Другие callers сохранены.
- Presence использует `online`, а не наличие записи в серверном batch. Есть
  Online, Last seen с общим relative timestamp formatter, Offline без времени
  и Status unavailable без известного heartbeat. Цвет/точка статуса — как в QML.
  Favorites показывает число notes, остальные чаты — messages.
- Timeline сохраняет отдельный scroll viewport. При удалении от нижнего края
  на 36 px появляется круглая кнопка 44 px, с иконкой 23 px и отступом 16 px.
  Она возвращает к последнему загруженному сообщению и исчезает у нижнего края.
  Используются общие motion tokens; при нулевой анимации прокрутка мгновенная.
  Cache, anchor, догрузка истории и черновики сохранены.

EN/RU, темы, общие window controls и защищённые серверные операции сохранены;
новые API, зависимости и изменения Handler не требуются. Источник presence,
счётчиков и прав — существующий backend, не фиктивные состояния frontend.

Свежий оригинальный QML снят через
`STREAM_MESSAGES_NAVIGATION_CAPTURE=1 tools/capture_handler_reference.py --messages-only`:
`messages-counters-presence.png`, `messages-conversation-menu.png`,
`messages-jump-latest.png` в `.screenshots/handler-current/`. Offscreen software
Qt при длинной истории показывает артефакты clipping пузырей за пределами
viewport; этот снимок используется для геометрии кнопки, не как доказательство
полного визуального совпадения. Web evidence:
`.screenshots/messages-conversation-menu-web.png` и
`.screenshots/messages-jump-latest-mobile.png`.

Production build: 199 modules. Реальный HTTP/SQLite/CG-template browser test
`messages.mjs` прошёл, включая expired/fresh/unknown heartbeat, badges,
прочтение упоминания, ПКМ, keyboard context, сохранение черновика, настоящий
CDP touch hold и touch jump на 320 px, прежние файлы/историю/RU/light/360 px.
`main_window.mjs`, `search_tab_geometry.mjs` и `icons.mjs` прошли после общего
ripple изменения. PostgreSQL, другие браузеры и реальный телефон не проверялись.

Остаток полного переноса Messages: контур/типографика пузырей и расположение
метаданных, emoji-only размер, состояния composer и полный native Help-каталог.
Этот блок не означает 100% готовности всего Messages.


### Messages: пузырь, метаданные, цитаты и composer — 2026-10-09

Следующий блок выполнен по текущим `MessagesTimeline.qml`,
`MessageTimelineFrame.qml`, `MessageBodyText.qml`, `MessageReactionChip.qml`,
`MessageReplyPreview.qml`, `MessageForwardPreview.qml`, `MessageComposerField.qml`
и `MessageSendButton.qml`, с проверкой `communication_feed.py`, `Theme.qml` и
`Typography.js`. Handler не изменён.

- Вместо отдельного треугольного хвоста используется исходный замкнутый curved
  contour, с зеркальным outgoing и хвостом только у последнего сообщения группы.
  Surface/radius принадлежат общей теме; рамка выделения — tertiary. Контур SVG
  повторяет QML Shape и не является новым набором иконок действий.
- Геометрия зависит от ширины timeline, как в оригинале: при ширине ниже 380 px
  avatar 34, outer margin 8, padding 10, минимум пузыря 104 px; иначе
  40/12/13/116. Максимум обычного пузыря 70% и 520 px; media занимает разрешённую
  ширину. Групповые отступы, header/content spacing и border включают хвост.
- Имя, relative time с полной tooltip, delivery и Edited находятся в header;
  pin/reaction/menu и checkbox выбора — внутри верхнего края пузыря, 26 px,
  с исходными compact icons 17 px из общего token.
  Контекстные операции переиспользуют прежнее меню; touch сохраняет явный вход.
  Правка/удаление, серверные права и окно истории правок сохранены.
- Обычный текст использует фактическую геометрию Qt rich text: Segoe UI 13 px,
  строка 17 px при 96dpi. Sender — 12 px. Значения принадлежат общим CSS tokens.
  Алгоритм emoji-only перенесён из QML вместе с диапазонами и счётом clusters:
  для 1/2/3 эмодзи соответственно 42/36/31.5 pt; смешанный текст и больше трёх
  остаются обычным текстом. Реакции — 28 px, emoji 18 px, исходный cyan tint.
- Единственный MessageReference обслуживает ответ в timeline, ответ в composer
  и forwarded preview: исходные 54/62 px, rail 4 px, icon 18 px, 2/3 строки,
  attachment count и display name. Composer-цитата имеет только Cancel reply;
  timeline-ответ переходит к сообщению, forward открывает исходный чат.
  Недоступный original не активируется, его body не показывается. Переход
  защищён от смены project/session/chat и прекращается при ошибке history.
- Composer растёт от 44 до 124 px, затем прокручивается внутри поля. Sending
  делает поле readOnly, оставляя выделение/копирование текста; EmojiPicker
  скрывается, Send показывает Sending. До 620 px контейнера Send компактный.
  При фокусе остаётся единственная рамка поля 2 px; общая browser outline
  не накладывается второй раз. Compact icons берутся из общего token 17 px.
  Enter, включая Shift+Enter, отправляет; Ctrl/Meta+Enter вставляет строку.
  IME и autoRepeat не отправляют. Выбор упоминания клавиатурой вставляет login;
  Escape закрывает список, сохраняя окно и черновик. Пустые списки не рисуются.

Свежий оригинальный Qt снят через `STREAM_MESSAGES_BUBBLE_CAPTURE=1`
`tools/capture_handler_reference.py --messages-only`: `messages.png`,
`messages-bubble-geometry.json`, `messages-emoji-only.png`,
`messages-composer-multiline.png`, `messages-composer-sending.png`,
`messages-references.png` в `.screenshots/handler-current/`. Web evidence:
`.screenshots/messages-web.png`, `.screenshots/messages-emoji-only-web.png`,
`.screenshots/messages-references-web.png`. Source hashes и adaptations записаны
в compatibility manifest; native software rasterization не подменяется browser
скриншотом и не объявляется идентичной по каждому пикселю.

Production build: 200 modules. Реальный HTTP/SQLite/CG-template Chromium test
проверяет обычную строку 17 px, composer 44/124 и внутреннюю прокрутку, IME,
упоминания/Escape, readOnly pending, in-header Edited, select/outline,
composer dismiss, forwarded original, deleted quote, 1–3 emoji-only и overflow
на 320 px; прежние вложения, права, history, drafts/account isolation,
RU/light и touch 320/360 сохранены. Пять официальных наборов иконок проверены.

Полный перенос Messages ещё не завершён: отдельная карточка/профиль отправителя
и полный native Help-каталог остаются зависимостями. Точную растеризацию Qt
и Chromium, другие браузеры, PostgreSQL и реальный телефон этот блок не закрывает.


## 2026-10-09: профиль пользователя и профиль отправителя

Перенесены текущие `UserProfileView.qml`, `UserProfileEditorDialog.qml`,
`UserWorkSummary.qml`, `UserGroupMembershipEditor.qml` и presentation ranking
`group_authority.py`. Оригинальный ТХ не изменён. Актуальные окна сняты через
`STREAM_USER_PROFILE_CAPTURE=1 tools/capture_handler_reference.py --messages-only`:
`user-profile.png`, `user-directory.png`, `user-profile-editor.png`.

Профиль открывается из имени/аватара сообщения и из меню аккаунта. Каталог
Users группируется по native primary group, ищет по login/name/email;
на маленьком экране открывается поверх профиля. Размеры preview 168/54/34 px,
editor 680×690, metrics 22 px, hours 18 px, SummaryChip 30 px и поля 36 px
взяты из QML. Окна используют общую drag/maximize/restore систему, контролы,
официальные иконки и темы. `ProfileInfoRow` и `SummaryChip` — общие presenter.

Действия: собственный профиль/пароль/аватар; административное создание
пользователя, account fields, membership и общие access levels групп;
пять показателей задач, группировки по статусу/процессу, часы недели;
шесть свежих событий с раскрытием и переходом к полному Activity Feed.
Переходы используют существующие Messages, TaskManager с user/filter и
ActivityFeed с user; перекрывающее окно Messages закрывается перед открытием
основных задач/объектов/sKey. Неподтверждённый черновик редактора защищён.

Серверные процедуры mutate/create/query_user_profile_data извлечены из ТХ
и выполняются через native Login/Search/Command. Устаревший login schema
дополнен nullable address через существующий повторяемый upgrade механизм;
это собственное дополнение для адреса в актуальном Handler UI, не оригинальная
SQL-миграция. Проект, поля, процесс, файлы и полномочия проверяются сервером.
Сохранена существующая политика: управление аккаунтами/группами и просмотр
чужих часов требуют настоящих admin rights; слово supervisor в названии
группы этих прав не выдаёт. Обычный пользователь изменяет только разрешённые
поля своего профиля. Credentials не возвращаются, пароль пустой в draft.

Ревизия включает данные пользователя, membership, параметры групп и icon
snapshots. Проверка идёт под native locks; устаревший draft даёт 409.
Аватар проходит Image.verify (JPG/PNG/WEBP, до 10 MiB), IconCreator и обычный
FileCheckin icon с versionless update; token/name/content/actor предотвращают
дубли при повторе. FileUndo разрешает только staging/undo и именованные
пути нужного login в настроенном repository. Обычные XML-RPC writes не получают
новых полномочий. Shared user_identities не возвращает avatar URL при запрете
чтения snapshot/file. Лицензирование, Repository Sync и соединение с ТХ исключены.

Проверки: production build; реальный HTTP/SQLite/CG-template Chromium
`frontend/tests/user_profile.mjs` (полный цикл, конфликт, запреты чужого
профиля/полей/проекта/процесса/файлов, own avatar и повтор без дублей,
навигация, maximize/restore, native preview dimensions, RU/light/touch320);
Messages и пять наборов иконок; backend Messages, SecurityUsers,
SecurityGroups и native Security parity/upgrade прошли.
Широкий набор kernel/snapshot/foundation: 51/56 успешны. Пять сбоев требуют
отдельного обновления: два snapshot tests всё ещё ожидают UnsupportedContract
для уже перенесённых read options/FileGroup; checkin_contract ищет undo bytes
в старом cache вместо undo; Foundation ищет TH source в legacy и ожидает
другой тип ошибки для исключённого prod. Эти ветви не зависят от UserProfile
scope; весь набор не объявляется успешным.

Web screenshots: `user-directory-web.png`, `user-profile-web.png`,
`user-profile-editor-web.png`, `user-profile-mobile.png`,
`user-profile-mobile-light-ru.png` в `.screenshots/`.
Следующий блок Messages — полный native Help-каталог. Не закрыты точная
растеризация Qt/Chromium, PostgreSQL в этом блоке, другие браузеры/реальный
телефон и пять вышеуказанных kernel checks. Тестовые серверы и Qt/Chromium
завершаются в finally; пользовательские процессы не останавливаются.

## 2026-10-09: каталог справки из актуального Handler

`features/help/HelpView.vue` заменяет прежнюю четырёхсекционную Messages HelpArticle.
Это общий экран каталога из актуальных HelpView.qml / HelpController: темы,
группы, иконки, поиск по всему тексту, выбор и раскрытие текущей темы, отдельная
прокрутка статьи, перезагрузка и выбор перевода с English fallback. Help доступна
из главного меню и из Messages с выбранной communication. Открытие/закрытие не
меняет чат или черновик. Общие AppButton/AppTextField/ItemSurface/MarkdownText и
v-window предоставляют drag, keyboard move, maximize/restore, темы и EN/RU.
На 320 px каталог раскрывается поверх статьи и закрывается после выбора темы.

Установлены 47 тем / 94 Markdown-файла. Overview, Windows и Communication
адаптированы к вебу. Остальные 44 темы сохраняют полный исходный текст ТХ с
явной пометкой «Оригинальная справка ТХ»: описание desktop-функции не означает
её готовности в Stream. Перенос всех этих инструкций на веб не объявляется
завершённым. Исключены шесть специализированных тем Repository Sync,
Watch Folders, DCC clients/Handler Server/triggers и Maya configuration.
Наличие упоминаний desktop-возможностей внутри оригинальных reference-статей
не добавляет их UI, backend или зависимостей в Stream.

Исходные статьи лежат в frontend/public/help и копируются в пакет web/help.
Редактирование установленного Markdown и Reload не требуют рестарта/сборки;
изменение исходников frontend/public требует обычной публикации build.
Каталог index.json определяет набор тем. Browser Open article file открывает
text/plain в новой вкладке; Download сохраняет Markdown для внешнего редактора.
Браузер не запускает системный редактор и не пишет его файл обратно на сервер.
Это явная адаптация native QDesktopServices, а не заглушка успешного сохранения.
Адреса существующей бизнес-логики/XML-RPC не изменены.

MarkdownText использует markdown-it 15.0.2 для таблиц, списков, quotes, fences,
ссылок и локальных packaged images. HTML отображается как текст; исполняемые,
file/private URLs и внешние images не выполняются/не загружаются. Межстатейные
ссылки переключают тему, fragment links переходят к заголовку. Python/JS/XML
используют существующие syntax tokens. Статический маршрут принимает только
help index, Markdown и ограниченные raster media, сохраняет path protections,
nosniff и no-store. Package-data и notices включены в поставку.

Свежий актуальный Qt захват: STREAM_MESSAGES_HELP_CAPTURE=1 с тем же размером
1008×760, `.screenshots/handler-current/messages-help.png` и help-geometry.json.
Исправлен локальный QFontInfo импорт в нашем capture fixture; ТХ не изменён.
Измеренный Qt body — Segoe UI 12 px; native document spacing и typography
заданы общими токенами. Строка темы 58 px, иконка 17 px, title 12 pt,
topic pane clamp236–292, gap10, margins12/10 взяты из QML. Shared icon-only
AppButton anchor теперь имеет ту же круглую borderless геометрию, что button.

Проверки прошли: production build (228 modules), реальный HTTP/SQLite/CG-template
Chromium Help и полный прежний Messages test. Проверены все 94 статьи,
front matter/errors/order, full-text search/no results, EN fallback, опасный
Markdown, source popup/download, reload с новым текстом и 503/recovery,
selected-topic scroll, native row/icon/body geometry, drag/keyboard move,
maximize/restore и RU/light/touch320. Messages проверяет возврат черновика,
attachment/history/permissions/forward/search/account isolation и touch320/360.
Лог `.screenshots/help-final.log`; web screenshots help-catalog-web.png,
help-catalog-mobile.png, help-catalog-ru-mobile.png, messages-help-web.png.
Наши Python/Qt/Chromium процессы завершены и отсутствие проверено.

Следующий блок — итоговая сверка всего Messages с актуальным ТХ по состояниям.
Не проверены PostgreSQL/другие браузеры/реальный телефон и точная растеризация
Qt против Chromium. Пять ранее отмеченных kernel checks остаются отдельной
задачей; ядро ради изменения справки повторно не запускалось.


### 2026-10-09 — Messages: общий UserPicker и участники

Перенесены текущие UserPicker.qml/UserSearch.js/UserGroupSection.qml из ТХ:
один API-free компонент создания чата/изменения участников, поиск по логину,
имени и группам, 54px строки/36px аватары/36px поиск, текущий пользователь
виден и недоступен для выбора. Групповые заголовки используются также в Users.
Нативные счетчики, требование названия для группы, пустой выбор и сообщение
об отсутствии полномочий сохранены. Общий server user_directory заменяет
дублирование проекции; явный запрет чтения групп скрывает названия, ранжирование
group_authority остается только оформлением и не выдает права.

Chat members: 58px строки/34px аватары, текущий пользователь первым,
переход к общему UserProfile с возвратом к Messages. Подтверждения удаления
чата/очистки Избранного объясняют штатное архивирование/сохранение Избранного.
Общие draggable/maximizable окна сохранены; размеры содержимого рассчитаны
без 12px тени Qt Popup.Window. SearchField больше не создает вложенные forms;
проверено, что Enter в поиске не применяет форму чата.

Свежие неизмененные QML screenshots: handler-current/messages-create-chat.png,
messages-edit-members.png, messages-members.png и JSON геометрии. Web:
messages-create-chat-web.png, messages-edit-members-web.png,
messages-members-web.png, messages-create-chat-mobile.png. Код ТХ не менялся.
Messages HTTP/SQLite tests проходят; полный Chromium Messages проходит.
Проверка UserProfile выполняется отдельно: его fixture создает artist заново,
поэтому совместный запуск с messages.mjs в одной базе конфликтует по login.code.

Отдельный известный сбой search_suggestions: после reload точный поиск
Blue Extra теряется (28 вместо 1 результата). Воспроизведен с прежним
SearchField; это не регрессия изменения контейнера. Логи
messages-people-search.log и messages-people-search-baseline.log. Селекторы
теста привязаны к основной строке поиска вместо всех скрытых экземпляров.
Следующий шаг: восстановление поисковой вкладки, затем оставшиеся вспомогательные
окна Messages (rename/forward/history) и их размеры/состояния по текущему QML.
PostgreSQL, настоящий телефон и точная растеризация Qt/Chromium не проверены.
Ранее отмеченные пять kernel checks остаются отдельной задачей.

Итог блока: production build успешен; полный messages.mjs проходит,
user_profile.mjs на отдельной чистой базе проходит; 4 серверных теста
Messages/SecurityGroups/SecurityUsers проходят. Финальные логи:
messages-people-final.log (Messages проходит; следующий UserProfile в той же
базе ожидаемо конфликтует по fixture), messages-people-profile.log
(изолированный UserProfile PASS), messages-people-backend.log (4/4 OK).
Финальный код SearchField и production build восстановлены после baseline.
CIM audit: No owned test processes remain — Python/Qt/Chromium завершены.

### 2026-10-09 — Восстановление workspace по адресу браузера

Закрыт следующий пункт плана: reload больше не заменяет сохраненную поисковую
вкладку новым поиском без настроек. Обычный адрес содержит project, search_type,
view и локальный tab ID. Маршрутизация выбирает существующую вкладку только при
совпадении проекта, типа и представления; восстановлением запроса, черновика,
страницы, выделения, прокрутки и доков по-прежнему управляет общий workspace.
Back/Forward переключает сохраненные вкладки. Старый адрес без tab восстанавливает
текущую подходящую секцию; неизвестный tab открывает обычный поиск. ID вкладки
не переносит ее настройки между браузерами. Приоритет skey/tactic-search и
проверка доступа сервером сохранены. Сверено с текущим search_tabs.py ТХ;
код Handler не изменялся.

На 320px единственная кнопка Script shelf перенесена в существующее меню
действий представления, чтобы оставить место основной строке поиска.

Проверки: rich_text.mjs, workspace_state.mjs, Chromium search_suggestions
(точный поиск, фильтр/сортировка, reload, старый/неизвестный tab, Back/Forward,
touch320), workspace_tabs, workspace_restore, workspace_infinite и
workspace_startup прошли. Production build успешен. Логи:
workspace-address-search.log, workspace-address-restore.log,
workspace-address-infinite.log, workspace-address-build.log. Restore log
содержит исторический сбой селектора alert в infinite; после уточнения
селектора полный infinite/startup прошел в workspace-address-infinite.log.
Предыдущий известный сбой Blue Extra (28 вместо 1) устранен.
Свежие снимки: search-suggestions-mobile.png,
handler-current/stream-workspace-restored-320.png и
handler-current/stream-workspace-restored-dock.png в .screenshots.

Финальный CIM audit: No owned test processes remain. PostgreSQL, физический
телефон, другие браузеры и Electron не проверены в этом блоке.
Следующий пункт: оставшиеся окна Messages (rename/forward/history) по QML.

### 2026-10-09 — Messages: переименование, пересылка и истории

Сверены текущие MessagesView.qml, communication_feed.py и вложенные
Controls.Popup/Dialog/TextArea/ItemSurface из неизмененного Handler. Сняты
свежие офлайн QML окна: messages-rename, messages-edit, messages-forward,
messages-edit-history, messages-pin-history с JSON геометрии в
.screenshots/handler-current. Захват запускает существующий Handler на
синтетических данных; его код и настройки не изменяются.

Rename использует общий AppTextField, Enter и кнопку Rename; пустое или
пробельное имя не отправляется. Edit использует общий API-free AppTextArea
по TextArea.qml, поле 130px с начальным фокусом и проверкой непустого текста.
Forward: 460×540, строки 54px через ItemSurface/AppCheckbox, описание чатов,
количество выбранных сообщений, один или несколько адресатов, проверка
непустого выбора. Прямая Forward начинает выбор с одного сообщения;
Forward из панели выделения сохраняет весь выбор. Cancel/Escape/Close
сбрасывают адресатов и выделение; ошибка сохраняет их для повторной отправки.

Истории правок и закреплений имеют самостоятельную прокрутку, metadata с
автором/датой и обычный текст без HTML-интерпретации. Для закреплений общий
ItemSurface и AppButton выполняют переход к сообщению; окно закрывается
после успешного перехода. Перенесены исходные summaries для ссылок,
вложений без текста, пересылок и ответов. Переводятся подписи, а не данные.
Размеры popup рассчитаны без 12px тени Qt и с общей рабочей шапкой веба.
Все окна сохраняют общий v-window: перемещение, maximize/restore и mobile.
Идентичность dialog задается режимом редактора: геометрия истории больше
не возвращается после resize в окно пересылки. Второй владелец состояния
или новая серверная операция не добавлялись.

Production build успешен; HTTP/SQLite test_messages — 2/2 OK.
Chromium messages.mjs проверяет операции, одиночный/множественный выбор,
отмену и retry после ошибки, пустые поля, Enter, истории/вложение без текста,
геометрию/maximize, touch320/360, файлы, ссылки, черновики и изоляцию аккаунтов.
Логи: messages-aux-native.log, messages-aux-browser.log,
messages-aux-backend.log, messages-aux-build.log. Свежие web снимки:
messages-rename-web/mobile.png, messages-edit-web.png,
messages-forward-web/mobile.png, messages-edit-history-web/mobile.png,
messages-pin-history-web.png. Все находятся в .screenshots.

Этот пункт закрывает оставшиеся вспомогательные окна Messages; весь проект
не объявляется завершенным. Следующий пункт — Task Manager по текущему QML.
PostgreSQL, физический телефон, другие браузеры/Electron и точное совпадение
растеризации шрифтов Qt/Chromium в этом блоке не проверены.
Финальный полный Chromium прогон прошел после подключения общего ItemSurface
к истории закреплений. JSON переводов/provenance валиден.
Финальный CIM audit: No owned test processes remain — Python/Qt/Chromium завершены.

## 2026-10-09: Task Manager — панель управления и контекст

Продолжение пункта 3. Свежий эталон снят из текущих TasksWorkspaceView.qml,
TaskWorkspaceModeSwitcher.qml и контроллера tasks.py через изолированную
fixture самого Handler. Его код и настройки не изменялись. Ширины native
кадров: 1280, 1232, 320 и 272 px; отдельно снята загруженная native таблица.
tools/capture_task_manager_reference.py ждёт завершения анимаций и закрывает
окно/контроллеры в finally. Снимки и геометрия — .screenshots/handler-current.

TaskManager остаётся единственным владельцем запросов и черновиков.
Поиск использует AppSearchField с debounce/Enter; шапка занимает 58 px.
Область и фильтры больше не создают отдельные строки над результатами.
Существующие shared AppMenu/AppSelect/AppCheckbox используются через
TaskWorkspaceScope и TaskWorkspaceFilters без второго состояния или API.
На ширинах меньше 380/520 px те же selectors переходят в overflow;
группировка/сортировка доступны прямо в шапке от 720/1180 px.
Table/Gantt и Calendar находятся в компактном футере. Load More добавляет
уникальные search keys к загруженным задачам и сохраняет bulk selection.
Высокие overlay AppMenu выбирают доступную сторону кнопки и прокручиваются,
сохраняя доступ к trigger и Escape/focus. Скрытие dock закрывает его popup.

Selected следует за выделением в рабочем SearchType, а Search Type scope —
за активным типом. Запоздавшие ответы чтения инвалидируются; сохранение или
редактор не отменяются при смене родителя. Обновление откладывается до закрытия
редактора, исходные черновики и ревизии сохраняются. Активная задача также
задаёт родителя для создания. Query, scope, user/team, группировка, сортировка,
колонки и положение календаря валидируются и сохраняются по аккаунту/проекту;
черновики и отмеченные строки не записываются в localStorage.

Проверено: полный Chromium Task Manager (edit/inline/expanded, Save/Discard,
ревизии/lost reply, Calendar/Gantt, milestones, мышь и touch320), отдельный
реальный UI сценарий Selected A/B с задержанным ответом и сохранением черновика,
дозагрузка 23 задач без повторов/потери выделения и восстановление состояния
при переходе one → two → one. Серверные проверки — 4/4: неизменённая процедура
Handler, XML-RPC edit и исходные schedule projections/границы входных данных.
Production build прошёл. Логи: task-manager-foundation-browser.log,
task-manager-context.log, task-manager-foundation-backend.log,
task-manager-foundation-build.log и task-manager-native.log в .screenshots.

Пункт 3 остаётся в работе: quick process cards/compact list и точное отображение
строк native TaskBrowserTable ещё не перенесены полностью. Эти возможности
не подменяются неработающими кнопками выбора вида. PostgreSQL, физический
телефон и другие браузеры в этом блоке не проверены.
Финальная дозагрузка использует offset/loaded серверной страницы независимо
от удаления дублей из списка. После окончательной сборки контекстный Chromium
прогон повторён успешно; финальный CIM audit подтвердил отсутствие оставшихся
моих процессов Python/Qt/Chromium.

### 2026-10-09 — Task Manager: quick процессы и переключение поверхностей

Перенесены текущие `TaskProcessPanel.qml` и `TaskWorkspaceSurfaceSwitcher.qml`:
карточки процессов выбранного объекта, компактные строки и возврат к advanced
workspace. Карточки высотой 119 px, шаг сетки 126 px, порог колонок 224 px;
компактные строки 44 px. Native шапка 58 px, общий footer 58 px, компактные
кнопки 28 px. Размеры взяты из QML; на touch они не увеличиваются.

`TaskManager` остаётся единственным владельцем запросов/черновиков. API-free
`TaskProcessPanel` получает готовые процессы и испускает изменения. Выбор
другой задачи внутри процесса сохраняет черновик предыдущей ветки. Save/Reset
одной карточки не очищает остальные правки; общий Save использует ту же native
команду, что таблица. Add/Edit/Delete открывают существующий общий редактор
и dependency preview; удаление остаётся черновиком до Save. Inspector использует
общий NotesPanel с выбранной task branch. Вид сохраняется по аккаунту/проекту,
query/group/calendar advanced workspace сохраняются при переключениях.

Серверный `TaskWorkspaceCmd(action=processes)` использует native parent ACL,
pipeline/process/task scope и существующий `workspace_edit_plan`. Возвращает
пустые процессы, все task branches, defaults, цвета, статусы, допустимых
исполнителей и исходные ревизии. Автоматический первый статус `Task.create`
не подставляется вместо отсутствующего workflow default в пустой карточке.
`user_directory` предоставляет публичные аватарки/группы; это не выдаёт прав.
Native action/condition/dependency/progress исключаются из quick task list.

Добавлены общие `StatusSelect` (ComboBox colorRole/actionField) и `UserComboBox`:
один исполнитель, аватарка, поиск, группировка и клавиатура/тап. Переиспользуются
AppSelect, AppMenu, AppSearchField, ItemPreview и UserGroupSection. Compact
UserGroupSection сохраняет прежнюю normal geometry для других callers.
Изменённый AppSelect умеет отключённые options. Строки EN/RU проходят общий t.

Исправлен host refresh после task Save: выделенный объект остаётся выбранным,
завершение restore выставляет tab.loaded, поэтому notification progress не
остаётся навсегда. Обычные refresh других экранов сохраняют прежнее поведение.
Тестовая схема spt_process приведена к native полю subpipeline_code, чтобы
настоящий pipeline update проходил без обхода validation.

Проверено: production build; новый real XML-RPC/SQLite процессный контракт;
Chromium quick create/edit/delete/Inspector, поиск пользователя, выбор branch,
сохранение одной задачи/черновиков остальных, три поверхности, touch320;
прежний полный Task Manager (Calendar/Gantt/milestones/edit/revisions) и
контекстный прогон Selected/late reply/pagination/preferences. Свежие QML
кадры: `.screenshots/handler-current/task-process-{cards,compact}-{1232,272}.png`;
web: `.screenshots/task-process-cards*.png`. Qt использует изолированную TH
фикстуру; код/настройки пользовательского ТХ не изменяются.

Пункт 3 остаётся в работе: точный перенос native TaskBrowserTable и скрытых
деталей, дальнейшая доводка поведения общего task workspace. Нет заявления о
100% screen/API parity. PostgreSQL, физический телефон и другие браузеры для
новой серверной проекции не проверены; compact rows прокручиваются внутри
контейнера на маленьком экране.
Финальный CIM audit: моих Python/Qt/Chromium процессов не осталось (0).

### 2026-10-09 — Task Manager: строки таблицы и раскрытые детали

Сверены текущие TaskBrowserTable.qml, TaskHiddenDetails.qml,
TaskTableEditorCell.qml, TaskPendingChangesBar.qml и вложенные controls ТХ.
Перенесены строки 58 px, шапка 34 px, превью объекта 34 px, аватарки 22 px,
цветная полоса 3 px и подпись процесса/context под объектом. Process остаётся
в сохранённых native preferences; текущий QML не рисует отдельный столбец.
Столбцы скрываются на тех же порогах ширины; сохраняются native dense widths,
ограничение ширины Object и заполнение свободной ширины Status.
Выделенная строка, checked/range selection, группировка, клавиатура,
настройки столбцов и явные операции остались у TaskManager. Один клик по
объекту выбирает строку; двойной клик и пункт меню вызывают общий guarded
переход к объекту. Inspector вызывается своим действием.

TaskHiddenDetails — предметный presenter без API и собственных черновиков.
Сетка 1/2/3/4/5 колонок на порогах 440/720/960/1280, поля 36 px, gaps 8 px,
description 58 px и micro typography из общего токена. StatusSelect,
UserComboBox, AppSlider, TaskField, AppTextArea и AppButton общие. Priority,
Milestone и Supervisor видны в деталях независимо от компактных столбцов.
Описание существующей задачи read-only до Edit; blur/Finish сохраняет его
в общий черновик, Escape восстанавливает прежний текст. Слайдер 0..100/step 5
использует native track 4 px/handle 16 px и работает с клавиатурой/тачем.
Плановые часы учитывают bid_duration_unit: UI показывает часы, minute
storage сохраняет минуты. Проверен настоящий Save в обоих режимах.

Read action получает labels/colors из Pipeline, превью через ThumbWdg и
фактические/плановые часы через пакетный WorkHour и его get_summary.
Публичные профили пользователей берутся из существующего user_directory.
Исходный query_task_workspace_page, XML-RPC сигнатуры и write commands
не меняются. Серверные права и исходные ревизии сохраняются. Чтение
задачи без статуса больше не вызывает get_process(None).
ItemPreview соблюдает native darker fallback и явно заданный outlined.

Панель Save/Discard компактная, 42 px, находится в области результатов.
В браузере она занимает 42 px: это явная адаптация native zero-height
overlay, иначе он перекрывает Select-all/настройки колонок и ломает
повторное выделение при сохранённом черновике. Контекстный тест это проверяет.
Нет дополнительной большой панели под футером.

Проверки: production build, полный Chromium Task Manager (inline/expanded,
Escape/slider keyboard, native Save, minutes/hours, revisions/conflict,
create/delete/Inspector/time, calendar/Gantt/milestones и touch320),
отдельные Selected/late reply/pagination/preferences и quick-process
регрессии; native XML-RPC/SQLite catalog/write/metadata. Свежие QML кадры:
`.screenshots/handler-current/task-table-{rows,expanded}-{1232,272}.png`;
web: `.screenshots/task-manager-mobile-details-{clean,desktop}.png` и
`.screenshots/task-manager-mobile-expanded.png`. Снимки получены через
изолированные fixtures: данные native/web различаются, поэтому это проверка
геометрии/состояний, а не доказательство полного pixel parity на одном проекте.

Пункт 3 остаётся незавершённым: native lazy ComboBox inline popups,
DateField/SpinBox вместо platform inputs, дальнейшая доводка Gantt/details.
Новая read projection не проверена на PostgreSQL, физическом телефоне и
в других браузерах. Нет заявления о 100% screen/API parity.
Финальный CIM audit после последнего прогона: моих тестовых процессов 0.


### 2026-10-09 — мобильный режим всего приложения

По уточнению пользователя телефон использует отдельную компоновку. Настольный
Handler остаётся источником поведения и общего контрола, но его рамки, боковая
полоса, управление доками и все кнопки не переносятся целиком на телефон.
Общий порог мобильного представления — 700 CSS px (`frontend/src/mobile.js`),
переход не размонтирует владельцев черновиков и не меняет серверные права.

- Оболочка: боковая полоса отсутствует; открытые разделы переключаются/закрываются
  через проектную навигацию. В доках показывается одна активная панель, остаются
  вкладки Results/Tasks/Queue и закрытие. Перемещение, размеры, float, presets и
  управление раскладкой на телефоне недоступны. Настольная раскладка сохраняется.
- На телефоне скрыты команды админки, создания проектов, Script Editor/Shelf,
  Debug Log/UI responsiveness, редактирования XML/схем/полей/quick filters.
  Обычные поиск, объекты, создание/редактирование записей, задачи, сообщения,
  заметки, профили, очередь и конфигурация остаются. В меню есть пояснение
  о настольных редакторах. Входы в Administration/Create project проверяют
  размер экрана; скрытие кнопок не заменяет серверную ACL.
- Configuration: один выбор раздела вместо сетки кнопок, одна короткая шапка
  Save/Cancel/Menu; Reset/Apply/Help в общем меню. Отмена, ревизии и сохранение
  серверных настроек используют прежних владельцев и guards.
- Общий v-window на телефоне занимает экран без внешнего отступа и рамки.
  Это относится также к инспекторам, формам и вспомогательным диалогам.
- Messages: сначала список, затем отдельный экран чата. В чате возврат,
  название, Menu и закрытие; участники/файлы/поиск/обновление/справка и уведомления
  доступны через меню. Настольная шапка скрыта, рамки колонок и splitters убраны,
  сообщения используют ширину телефона. Реакции добавляются через меню сообщения.
  Enter вставляет строку, отправка — явная кнопка; переключение чатов хранит
  черновики. Открытие списка не помечает текущую беседу прочитанной. Выбор беседы
  не открывает экранную клавиатуру автоматически. Буферный file button скрыт,
  системный выбор файлов остаётся. Нативный paste event остаётся доступен.
- Задачи: на телефоне список и раскрытые детали; Gantt/Calendar на этом этапе
  доступны с компьютера. Настольный выбор view не перезаписывается телефоном.
  Inspector: детали и часы по умолчанию свёрнуты; операции задачи и часы в меню,
  лишние рамки убраны, история/композер занимают оставшуюся высоту. Enter в заметке
  вставляет строку, отправка — отдельный тап. При редактировании детали остаются
  раскрытыми, чтобы Save/Discard были доступны. Refresh появляется при ошибке.

Проверки: сборка Vite; новый mobile_workspace.mjs проверяет 320/360 px, отсутствие
desktop chrome, закрытие/выбор разделов, Messages back/search/drafts/Enter/send,
full-screen, настройки и Task Manager, восстановление desktop. Существующие
workspace_tabs/workspace_layout/task_manager проверяют сохранение настольных
сценариев; task_manager дополнен мобильным Inspector/заметками и разворачиванием.
Свежие снимки — `.screenshots/mobile-workspace.png`, `mobile-messages-320.png`,
`mobile-messages-360.png`, `mobile-tasks.png`, `mobile-task-inspector.png`.

Это общий мобильный каркас и перечисленные сценарии, не полная приёмка каждого
предметного экрана. В плане остаётся мобильная проверка файлов, профилей,
Activity Feed/Queue, всех форм и отдельных представлений объектов; мобильная
работа клавиатуры, safe areas, вложенных меню и больших вложений требует проверки
на физических Android/iOS. При переходе с уже открытого настольного редактора на
узкую ширину его черновик остаётся открытым: не закрывать/терять правки автоматически.
PostgreSQL в этом UI-этапе не проверялась. Общая старая статическая проверка
`test_components_use_translation_and_shared_theme_roles` пока отклоняет literal
placeholder props общих controls (HelpView и другие) и не учитывает текущий перенос
QML размеров; её результат не является успешной UI-приёмкой. Переводы и ресурсы
языков проверяются отдельно.


Итог проверки этого этапа: Vite build, `test_mobile_workspace_in_chromium`,
`test_workspace_tabs_in_chromium`, `test_workspace_layout_in_chromium`,
`test_task_manager_in_chromium` и две проверки словарей/ресурсов прошли.
Мобильный сценарий также проверяет выбор/сохранение реакции из меню сообщения.
Статический общий UI-аудит остаётся с описанным выше failure; полный набор ядра
ради UI изменений не запускался. После закрытия всех временных серверов/браузеров
read-only CIM аудит показал 0 собственных тестовых процессов.

### 2026-10-09 — мобильные профили, Activity Feed и существующая очередь

Изучены текущие UserProfileView.qml, ActivityFeedView.qml и
CommitQueueActionMenus.qml в Handler. Мобильное представление использует тот же
общий порог 700 CSS px; настольные операции и владельцы запросов сохранены.

- Профиль: аватар 56px, единое меню действий, весь профиль прокручивается вместе
  со статистикой и историей. Каталог пользователей открывается на всю ширину;
  выбор пользователя возвращает к профилю. Личный профиль и аватар редактируются
  через прежний редактор. Создание аккаунтов, управление группами и служебными
  полями доступны с компьютера. При смене ширины открытые черновики сохраняются.
- Activity Feed: снаружи остаются поиск и одно меню. Категория, пользователи,
  календарь, обновление, уведомления и справка находятся внутри. История занимает
  оставшуюся высоту без дополнительных рамок. Поиск/выбранные фильтры переживают
  переход к настольной компоновке; paging, права и native batch не менялись.
- Commit Queue: убраны повторный заголовок дока и пояснение; операции Retry/Cancel
  открываются из меню конкретной записи, список прокручивается отдельно.
  UploadServer/simple_checkin, pending-file guards и запрет автоматического
  повтора при неизвестном результате сохранены. Это адаптация существующей
  очереди preview check-in: полный перенос CommitQueueView Handler и общее
  создание файловых операций с телефона этим этапом не объявляются готовыми.
  Repository Sync по-прежнему исключён.

`test_mobile_activity_profile_in_chromium` работает на временной SQLite через
реальные HTTP операции. Проверены 320/360px, сохранение профиля, dirty Cancel,
сохранение черновика при resize, каталог, фильтры журнала и календарь. Для очереди
проверены отказ upload/отмена, успешный повтор и потеря ответа уже сохранённого
check-in: native snapshots присутствуют в БД, кнопка повтора отсутствует.
Ввод операции очереди задаётся тестом её существующему владельцу, поскольку
её исходные preview редакторы доступны с компьютера.

Vite build, новый сценарий, прежний `test_mobile_workspace_in_chromium` и две
проверки словарей/ресурсов прошли. Снимки: `.screenshots/mobile-profile-320.png`,
`mobile-activity-320.png`, `mobile-activity-360.png`,
`mobile-activity-desktop-restored.png`, `mobile-commit-queue.png`.
Проверка выполнена в Chromium с touch; физические Android/iOS, экранная
клавиатура и PostgreSQL не проверялись. Остальные мобильные экраны и полный
набор ядра этим этапом не принимались; прежнее ограничение статического
общего UI-аудита остаётся описанным выше.

### 2026-10-09 — мобильные формы, файлы и связанные объекты

Изучены текущие SObjectValueEditor.qml, SObjectInfoView.qml и LinkSObjectsView.qml
Handler. Используются общие controls и v-window; новый backend не добавлен.
RecordForm на телефоне имеет компактную шапку, прокрутку полей и постоянную
нижнюю кнопку Save. Открытие не фокусирует текстовое поле автоматически.
Черновик/файлы/контекст, unsupported inputs, dirty Cancel, native commands и
блокировка неизвестного результата сохранены. Совпадающий с названием поля
повторный title убран; отдельные описания остаются.

FilePreview оставляет площадь содержимому: общий select выбирает файл, а пути,
метаданные и исходные Open/Download находятся в File details. Desktop получает
прежнее содержимое. Request generation и освобождение blob URL сохранены.
ObjectOperations использует общие кнопки и semantic icons без изменения прав,
операций и подтверждений. Окна сведений получили компактные common controls.

RelatedObjects имеет компактный выбор типа/создание и меню уже связанных
объектов. Выбор, dirty Cancel и Save links принадлежат прежнему владельцу.
В ConfiguredView выбор поля, page size и Refresh перенесены в меню телефона;
поиск/Find остаются снаружи, пагинация компактна, редактирование колонок доступно
на desktop. Исправлен цикл ConfiguredView → ResultPresentation → RelatedObjects:
ранняя регистрация замораживала undefined и выводила неизвестный HTML-тег.
Getter получает готовый компонент после инициализации модулей на всех ширинах,
не подменяя серверную схему или данные.

`test_mobile_objects_in_chromium` создаёт отдельный временный проект через
CreateProjectCmd/SearchTypeCreatorCmd и реальные XML формы. Проверены 320/360px,
native create/edit и последняя строка длинной формы, resize черновика, dirty
Cancel, потеря ответа после состоявшейся записи и запрет повторного сохранения.
Связи читаются из временной исходной схемы: query фильтрует/page size работает,
unlink сохраняется SObjectLinkCmd и проверяется по native instance mappings.
Просмотрщик проверен с контролируемыми асинхронными Blob: поздний первый файл
не заменяет второй, текст прокручивается, детали/desktop/close работают.

Снимки: `.screenshots/mobile-object-form.png`, `mobile-file-preview-320.png`,
`mobile-file-preview-360.png`, `mobile-related-objects.png`. FilePreview здесь
проверяет UI-контракт; реальные repository/download ACL, крупные видео/PDF,
мобильная клавиатура, PostgreSQL и физические Android/iOS не принимались.
Полный перенос LinkSObjectsView и всех legacy input widgets не объявляется
завершённым. Общий статический UI-аудит имеет прежнее описанное ограничение.

В native table regression обнаружено перекрытие Notes закреплённой колонкой
Actions: hit-test мобильного tap попадал в соседний td. На телефоне эта колонка
теперь прокручивается вместе с таблицей. Desktop закрепление сохранено.
Тот же сценарий без задержек/программных click прошёл после исправления;
сохранены desktop notes/reply/edit/history/delete и мобильные preview/notes/tasks.
Пустая часть окна связей получает фон окна вместо отдельного серого блока.

Vite build и оба теста UI-каталогов прошли. Native table и mobile objects прошли
в совместном запуске; record creation прошёл отдельно на чистой временной БД.
Проверка record creation после native table в одной Transport fixture выявила
существующую зависимость порядка: native table заменяет admin/project_view
своей тестовой навигацией. Production навигация для обхода этого не менялась.
Финальная проверка mobile objects после изменения фона прошла (15.433s).
После проверок CIM audit: принадлежащих тестам Python/Node/Chromium процессов 0.

### 2026-10-09 — боковая полоса открытых разделов

Сняты актуальное открытое окно Handler (`main-parity/handler-main.png`) и
исходный QML на синтетических данных (`handler-current/section-rail-hover.png`,
`section-rail-drag.png`, `section-rail-long.png`, `section-rail-scrolled.png`).
Изучены SectionTabRail.qml, ItemSurface.qml, Theme.qml и цепочка
NavigationModel → NavigationMixin → SectionTab. Цвет SearchType и XML-иконка
используются также в Handler; они сохранены, одноцветный режим не выдумывался.

Исправлен контраст glyph: прежний on-primary зависел от палитры приложения,
а не от затемнённого цвета badge. Общая readableText из appearance.js теперь
используется с теми же коэффициентами/порогом и Qt.darker 1.35/1.65, как в ТХ.
Fallback акцент пустого раздела — исходный #607d8b. Кружок 30px, icon size 16px,
surface 38px/radius 9px, строка 42px/шаг 45px, selection rail 3×28px. В раскрытии
добавлена отсутствовавшая метка текущего раздела; ограничение popup снизу учитывает
его настоящую высоту 38px. Сохранены hover latch 350ms, закрытие, reorder,
keyboard/context menu/long press и мобильное скрытие desktop rail.

Сборка и browser workspace tabs + оба UI catalog checks прошли (21.619s).
Проверены красный/жёлтый badge и согласование свёрнутого/раскрытого положения.
Vue-снимок: `.screenshots/workspace-tabs-rail.png`. Разные проекты/данные снимков
не выдаются за попиксельное сравнение целого приложения. Физические touch-устройства
и все шрифтовые наборы в этой проверке не принимались. Полезные дополнительные
возможности не удалялись; правило их сохранения/доступного выбора внесено в AGENTS.md.

### 2026-10-09 — заметки как часть таск-инспектора

NotesPanel уже владел режимами DiscussionReadCmd и TaskInspectorCmd, но вход
из кнопок заметок всегда отключал taskMode. Основной open теперь использует
тот же TaskInspectorCmd, что task-кнопки: объект, процесс, задачи/ветви,
история статусов и обсуждение живут в одном окне/владельце. Все существующие
callers (table/results, Activity Feed и note skey) получают этот режим без
отдельных копий UI/API. Explicit openTask остаётся инспектором независимо
от настройки. Native команды, права, ревизии, вложения и unknown write guards
не изменялись. Пока задачи нет, пустая сетка её полей не показывается;
создание и редактирование через прежние команды/формы сохранены.

Предыдущий режим только заметок сохранён: Appearance → Object notes →
Standalone notes, с EN/RU пояснением в общей AppearanceSettings (quick/full).
Настройка discussionView сохраняется существующим appearance owner, принимает
только notes/inspector, по умолчанию inspector; Cancel/Reset конфигурации
возвращают исходное значение. Открытое окно не переключает режим посреди работы.
Черновики обсуждений/задач остаются у прежнего владельца и не удаляются.

Native table Chromium: Task Inspector из Notes, preview/no-task состояние,
видимый/сохраняемый standalone выбор, восстановление черновика, note attachment,
reply/edit/history/delete и прежние task/work-hour сценарии прошли (21.714s
вместе с двумя UI-каталогами). Mobile Activity/Profile: native Activity Feed
и note skey открывают инспектор, восстанавливают общий черновик, 24 заметки
прокручиваются внутри timeline над composer. Исправлен оставшийся overflow:visible
из старого media620, создававший наложение заметок под composer.
Финальный мобильный сценарий и Vite build прошли; снимок
`.screenshots/mobile-notes-inspector.png`. CG-specific standalone
activity_feed/navigation_links scripts обновлены по контракту заголовка, но
в этой проверке не запускались; их входы проверены новым временным native сценарием.
Полное визуальное совпадение всего TaskInspector.qml и физические телефоны
этим изменением не объявляются завершёнными.

### 2026-10-09 — desktop: диалоги, контекстное меню и управление панелями

По уточнению пользователя грип в Results удалён, без замены кнопкой слева.
Текущий `SearchWorkspaceView.qml` открывает `DockMenu.qml` из трёх точек справа
от поиска; тот же вход использует Stream. Меню перемещается к фактическому DOM
контейнеру после его монтирования, чтобы начальная загрузка вложенных Teleport
не оставляла его в исходном месте. Проверены первый вход, смена проекта и
возвращение с телефонного размера на desktop.

Состав групп соответствует источнику: Browsing, Tasks and reports, Tools,
Layout presets, Reset layout. Показаны только существующие панели; отсутствующие
Snapshot Browser / Description / Knowledge Base не изображаются работающими.
Сохранены дополнительные Float/Maximize и прежние операции представления:
Tools → View actions. В админке и на телефоне их существующий вход сохранён.
Геометрия общего AppMenu — исходные 280px поверхности и 32px строки,
официальные semantic aliases для всех пяти пакетов, hover-delay из темы;
подменю открывается рядом и меняет сторону у края окна. Общий компонент
владеет Escape, направлением клавиатуры, закрытием соседних/дочерних меню
и сохранением открытого каталога при secondary-действиях presets.

ObjectOperations использует общий popup AppMenu вместо собственного диалога
с отдельной шапкой. Существующие операции, права, родительские подтверждения
и защита контекста сохранены; полный набор исходных SObjectActions ещё не перенесён.
WindowControls размещает Maximize/Restore рядом с Close во всех своих окнах.
RecordForm использует surfaceContainerHigh, padding20 и title16 из Dialog.qml;
ObjectAction использует общий AppButton для закрытия. Drag, dirty/save guards
и native dialog refs сохранены. Это подгонка chrome, а не объявление полного
совпадения содержимого всех рабочих диалогов.

Сняты актуальное живое главное окно Handler и оригинальные QML DockMenu /
Configuration через `capture_handler_reference.py --menus-only` с тестовыми
данными. Снимки: `.screenshots/handler-current/dock-management-menu.png`,
`.screenshots/workspace-layout-desktop-menu.png`,
`.screenshots/object-creation-touch-desktop-dialog.png` и desktop-context.
Chromium creation/context/columns/workspace плюс EN/RU/theme каталоги — 5 проверок
прошли; отдельный возврат desktop — прошёл. Vite build прошёл. Все временные
серверы и процессы захвата завершены, список процессов проверен.
Широкий admin.mjs остановился до входа на старом ожидании заголовка
«TACTIC Stream — Administration» вместо текущего «TACTIC Stream»;
старый статический regex-тест переводов останавливается на HelpView/AppTextField
placeholder, переводимом самим общим контролом. Эти проверки не объявляются
прошедшими; их ожидания и HelpView этим изменением не менялись.

### 2026-10-09 — пропорции общих кнопок и центрирование иконок

Причина смещения на скриншоте пользователя воспроизведена в native форме:
AppIcon имел box16, но pack-specific font-size22 давал glyph21. В результате
grid-track расширялся за box, а иконка оказывалась ниже и правее центра.
Убраны значения размера из классов пакетов: класс выбирает только официальный
шрифт и прежний оптический коэффициент MaterialIcon.qml. Общий box — 1em,
grid-tracks ограничены размером box; компактные кнопки используют icon17,
маленькие 24px кнопки — icon15. Ручных translate/margin для глифов нет.

Исправлены пары размеров task surface/pending и preset actions. Общая круглая
кнопка не сжимается flex-контейнером; min-width/min-height из обычных кнопок
не растягивают маленькие круги. Стили строк меню, текстовых заголовков таблицы
и configuration chrome не задают радиус, padding, высоту или выравнивание
icon-only. Administration Close использует AppButton. Назначения кнопок,
disabled/ACL и guards сохранены; прямоугольные строки, chips и disclosure-area
не превращены в круглые кнопки.

`button_geometry.mjs` проверяет реальные controls Configuration и RecordForm:
пять пакетов × три темы, отдельно обычный контекст вне шапки; shape, центры
контейнера/глифа, Canvas ink bounds после fonts.ready, пропорцию, maximize/restore
и компактные flex-контексты на 1280/320. Снимки button-geometry-{pack}.png и
button-geometry-record-header.png. Нативные Chromium button/search/creation/
workspace/columns — 5 проверок прошли за 30.086s; Task Manager прошёл отдельно
в предыдущем наборе. Icon resolver и Vite build прошли.

Регрессия общего меню также закрыта: clearTimeout из Vue-шаблона обращался к
неопределённому instance-методу; шаблон вызывает объявленный cancelHover.
Холодный мобильный старт после прежнего переноса View actions давал ошибку
Vue emitsOptions и оставлял Loading data. Вход привязан к фактическому DOM ref
после монтирования, как desktop DockMenu. Mobile console errors учитываются
тестом подсказок; прежнее ожидание Script shelf на телефоне заменено проверкой
его отсутствия согласно действующей мобильной политике пользователя.
Новые мобильные функции этим изменением не добавлялись.
Все пиктограммы всех экранов и другие браузерные растеризаторы не объявляются
прошедшими отдельную визуальную приёмку; проверены общие механизмы и эти сценарии.

### 2026-10-09 — нажатие по рисунку иконки кнопки

Общий icons.css исключает декоративный AppIcon внутри button/link/summary/
role=button из hit testing: действие получает попадание и по рисунку, и по фону.
Самостоятельный AppIcon поиска сохраняет свой click-handler. Нативный disabled
и клавиатурные действия не меняются. button_geometry.mjs проверяет реальные
координатные клики/тапы, включая меню, maximize/restore, Close на 320px, hover
с открытой подсказкой, disabled и самостоятельный поиск. Chromium geometry,
search suggestions, record creation и workspace layout прошли; Vite build
прошёл. Firefox/Safari и все отдельные экраны этим набором не проверены.

### 2026-10-09 — раздельная загрузка JavaScript

main.js выбирает отдельный динамический entry App.vue или ApiDocumentation.vue.
Vite/Rolldown выделяет Vue, официальные каталоги иконок и словари в собственные
файлы с хешами; действующий HTTP transport уже отдаёт такие assets с immutable
cache. Общий asyncComponent показывает BusyIndicator/статус во время загрузки
и понятную переведённую ошибку при недоступном чанке. Configuration и восемь
разделов админки загружаются при монтировании соответствующего раздела;
TaskScheduleView/TaskProcessPanel — при выборе поверхности, Markdown — при
открытии статьи. ScriptEditor загружается перед первым open: App сохраняет
markRaw-компонент, монтирует его, ждёт nextTick и только затем обращается к ref.
Повторное открытие сохраняет прежний экземпляр/черновик; загрузка другой сессии
не открывает окно. Остальные постоянные владельцы imperative refs сохранены.

Build entry: 26.19 KB, App: 649.87 KB вместо прежнего общего index 1,927.22 KB.
Это размеры файлов без HTTP-сжатия, а не измерение времени загрузки. Реальный
холодный вход в workspace в Chromium запросил 13 JS-файлов, 1,537,055 байт
суммарно; редакторы админки, скриптов и Markdown не скачивались при старте.
lazy_loading.mjs проверяет отсутствие этих запросов, задержанную загрузку с
видимым статусом, однократную загрузку при повторном открытии, черновик скрипта,
открытие Markdown и ошибку намеренно прерванного App JS. /docs/ не запрашивает
App entry. Build manifest используется этой проверкой, не является runtime API.
Старые assets не удаляются сборкой, чтобы уже открытые вкладки могли продолжить
загрузку своих хешированных зависимостей. Основной App всё ещё больше 500 KB;
выделение иконок/словарей улучшает независимое кеширование, не убирает их из
первого запуска. Firefox/Safari и реальные мобильные сети не проверены.

Проверки LAN startup, docs console, геометрии/кликов общих кнопок, Columns Editor,
workspace layout, Task Manager и Task Process Panel прошли. Два расширенных
touch-сценария schema/search_types не прошли: выбор ключей связи перед Save и
тап New Search Type после CDP-swipe/resize. Такие же сбои воспроизведены в
отдельной сборке с обычными импортами редакторов; эти сценарии не объявляются
прошедшими. Диагностика сохранена в .screenshots/split-*-isolated.log и
split-eager-check.log; производственная сборка этим сравнением не заменялась.

### 2026-10-09 — навигация из пустого workspace

Исходный NavigationDrawer.qml закрывается при движении мыши на scrim дальше
drawerWidth + 120px. В вебе центральная кнопка «Open navigation» находится уже
за этим порогом: первый небольшой pointermove закрывал только что открытый
список. Сбой воспроизведён координатным движением мыши в Chromium до правки.
Теперь hover-dismiss включается после pointerenter самой панели; каждое новое
открытие сбрасывает этот признак. Исходный порог выхода, закрытие кнопкой,
наружным кликом, Escape и выбором пункта сохраняются. Тач не запускает
mouse-dismiss. navigation.mjs проверяет центральный вход/путь к панели,
отступы 60/160px, повторное открытие, наружный клик, клавиатуру и выбор типа
на 320px тапами. Эта проверка и native record creation прошли; Vite build
прошёл. Снимок .screenshots/navigation-from-empty.png. Firefox/Safari не проверены.

### 2026-10-09 — вид результатов по умолчанию

Как controller.py текущего Handler, новые вкладки используют «Continuous tree»
(`continious`). Общий defaultResultView применяется при открытии типа и при
восстановлении вкладки без корректного сохранённого вида. Явный view_mode
боковой панели и сохранённый выбор пользователя сохраняются. Серверный XML
view `table` остаётся отдельным параметром. Node workspace_state и Chromium
navigation проверили default, переключение на таблицу и восстановление после
перезагрузки; production build прошёл. Firefox/Safari не проверены.

### 2026-10-09 — курсоры разделителей

AppSplitter и границы доков используют ew-resize/ns-resize по оси изменения
размера, как SizeHorCursor/SizeVerCursor в DockResizeEdge.qml. Разделитель
версий наследует такой же курсор и на самом input; при узкой компоновке
«Versions on the right» курсор становится вертикальным. Курсоры изменения
табличных колонок остаются col-resize, как SplitHCursor в Handler.
workspace_layout.mjs проверяет элемент под реальным курсором у доков, версий
и Script Editor в обеих ориентациях. До правки проверка воспроизвела col-resize
вместо ew-resize; после правки весь сценарий прошёл. Production build прошёл,
тестовые процессы завершены. Firefox/Safari не проверены.

### 2026-10-09 — адрес рабочего проекта

Корень `/` отдаёт рабочее приложение, а launcher открывает этот адрес после
готовности собственных воркеров. Канонический адрес проекта — `/projects/<код>/`;
search_type/view/tab, skey/tactic-search и приватные ссылки вложений сохраняются
в query. Прямой вход по пути проекта восстанавливает его текущую вкладку;
путь задаёт контекст skey без project даже до входа в систему. History API
сохраняет навигацию назад/вперёд. Стартовый title — TACTIC Stream, после входа
его обновляет существующий владелец заголовка проекта/объекта.

По явному уточнению пользователя старый UI `/admin/` удалён без alias/redirect,
query-project fallback удалён. Ресурсы, help/media и лицензии переведены на
`/ui/`; API POST endpoints сохраняют собственные маршруты. Новые пространства
projects/ui защищены от перекрытия repository mounts. Ссылки Messages и
возврат из документации используют новые адреса. Browser fixtures обновлены.
Node rich_text, HTTP HTML/CSP/assets/404/mount checks, Chromium project history,
bare path, saved view/reload, fresh sign-in via skey, lazy chunks/help and LAN
startup прошли; docs console прошла. Реальный launcher проверен на временной
конфигурации с двумя HTTP-воркерами и отключённой очередью для сценария без БД.
Работа очереди без инициализированной БД этим сценарием не проверяется.
Все собственные тестовые процессы останавливаются. Firefox/Safari не проверены.
Расширенный workspace_tabs не объявляется прошедшим: проверка адаптирована
к async root и явно выбирает Table для табличных сценариев, но далее встречает
нестабильный фокус клавиатурного меню и отсутствие меню вида после закрытия
Administration. Проверка новых маршрутов navigation.mjs отдельно прошла.

### 2026-10-09 — читаемый JavaScript и жизненный цикл меню

Указанный пользователем AppMenu-CLfSASMl.js:1:5325 разрешён в selected из
AppMenu.vue. Native Clear history удаляет условный AppMenu до всплывающего
click; следующий обработчик selected читал contains у null, а отложенный
toggle — open у null. Это воспроизведено до правки в Chromium, включая console
error (Vue ловит исключение, поэтому одного pageerror недостаточно).
selected/toggled прекращают обработку после размонтирования. Native повтор
той же операции и сценарии доков проходят без исключений.

Сборка сохраняет читаемые JS-функции (minify:false), CSS по-прежнему сжат;
sourcemap:true генерирует внешние .js.map/.css.map. Сервер отдаёт их как JSON
только внутри защищённого web/assets пути. Имена AppMenu/ScriptEditor и хеши
версий сохраняют назначение модулей и независимый кеш. DevTools использует
sourceMappingURL для исходного Vue/JS, тогда как сохранённый Error.stack в
Debug Log остаётся нативным стеком с читаемыми именами/строками сборки.
lazy_loading.mjs проверил HTTP карты, исходный AppMenu.vue и точное совпадение
строки contains через установленный source-map-js. Deferred editors, drafts,
Help/Markdown, docs isolation и interrupted download/error сохранились.
Холодный запуск запросил 13 JS, 2,256,811 байт без HTTP-сжатия вместо предыдущих
1,537,569; карты отдельно запрашиваются отладчиком. Это цена читаемой сборки,
не замер времени загрузки. Production build, native menu regression, dock
layout, static paths/fonts и source-map/lazy checks прошли. Firefox/Safari
и автоматическое разрешение сохранённых стектрейсов в Debug Log не проверены.

### 2026-10-09 — меню SObject и настоящий браузерный чекин

Инвентарь действий взят из текущих Handler item_actions.py/item_operations.py
и ItemCheckinDialogs.qml. Общий ObjectOperations открывается по ПКМ и кнопке
с тремя точками. Добавлены Save snapshot, Change Preview, Save from Clipboard,
подтверждённая ревизия, Copy Search Key (skey://), Copy Web Link с путём проекта,
Open On New Tab, пакетные действия выделения и Unlink instance без удаления
объекта. Процесс сохраняет собственный контекст и не предлагает удалить owner;
снапшот разрешает исходный SObject. Существующие info/edit/duplicate/delete
используют прежние штатные формы и проверки разрешений.

ObjectCheckin — общая перетаскиваемая/разворачиваемая форма: выбор файлов,
drop/paste, процесс/контекст/описание, исходные имена, одна группа или отдельные
снапшоты. Clipboard API на HTTPS/localhost; на HTTP доступна вставка Ctrl+V.
Файлы после передачи принадлежат CommitQueue, которая сохраняет captured
ticket/project и raw Files до успешного чекина или явной отмены. Failed можно
повторить; Result unknown требует проверки результата и не повторяется
автоматически. Уход с несохранёнными файлами защищён. Очередь докуется в
workspace либо открывается общим диалогом поверх админки/на телефоне.

Один файл использует native simple_checkin; группа — UploadedCheckinCmd с
проверкой проекта, ticket upload paths, имён, типов параметров и существования
файлов, затем тот же native FileCheckin, IconCreator и Command/Transaction.
Ревизия может сохранить имя TH: TacticRepo разрешает замену только пути файла
предыдущего снапшота того же owner/context/process/version. FileUndo сохраняет
и восстанавливает прежние байты при откате. Обычная коллизия по-прежнему ошибка.

Chromium на временной native БД проверяет реальные upload/download, ревизию,
группу, preview, Clipboard image, процесс, новые вкладки, выделение, меню связей
и Unlink. Native тесты проверяют rollback после файлового IO, отказ в чужих
путях/проекте, дубликаты имён, non-admin и существующий Handler image check-in.
Регрессия SearchType preview/Retry проверяет очередь поверх админки и повторное
открытие редактора. Для этого цели Teleport внутри Administration сохраняются
в DOM после закрытия диалога. Production build выполнен.

Это завершение базовых действий SObject, не полный паритет всех меню Handler:
relation ingest, глубокие Duplicate profiles, file path/image clipboard menu
и versionless Delete Whole Tree ещё требуют переноса. Локальные папки и Watch
Folders явно disabled с пояснением отсутствия desktop connection. DCC не
подключён; Repository Sync исключён. Firefox/Safari и эта группа изменений
на PostgreSQL не проверены. Пользовательские проекты тестами не изменяются.

### 2026-10-09: relation Add files — native ingest и правила Handler

Сверены текущие `ingest.py`, `ingest_preflight.py`, `ingest_relation.py`,
`IngestFilesView.qml`, `IngestRuleEditor.qml`, `IngestConflictDialog.qml`
и native `tactic.ui.tools.IngestUploadCmd`. Исходный класс IngestUploadCmd
перенесён из legacy без GUI-импортов; публичный alias `tactic.ui.tools` сохранён.
Добавлены проверки ticket upload paths/проекта, nullable extra values и обязательное
пробрасывание исключения, которое оригинал терял без message_key.

ПКМ/три точки на связи → Add files открывает общий draggable/maximizable диалог:
файлы, встроенное Quick ingest и сохранённые config/ingest_rule, фильтры и шаблон,
process/context, keywords, JSON extra values, preview и серверные scripts.
Скрипты проверки/обработки открываются в общем Script Editor; сохранение и удаление
правила используют native insert/update/delete. Есть RU/EN. Две панели,
высоты строк файлов/правил, compact icon buttons и выбранное правило сверены
со свежим QML-эталоном. Эталон снимается `tools/capture_handler_ingest.py`
через настоящий controller из тестового модуля Handler, на offline данных;
это не снимок пользовательского проекта или приёмка всего интерфейса.

Перед загрузкой имена сверяются только с выбранной связью родителя. Conflicts:
Cancel/Create duplicates/Skip existing/Update existing; неоднозначный update
недоступен. Параметры и owner/project/ticket передаются общей CommitQueue,
которая сохраняет raw File при ошибке и не повторяет Result unknown автоматически.
При закрытии формы с файлами требуется явное подтверждение. Очередь сохраняет
модальный режим, даже если передавшая файлы форма закрылась в тот же event loop.
Отмена ещё не начатых операций доступна в очереди; активный native check-in
завершается своей транзакцией, браузер не прерывает его посреди файловых операций.

RelatedIngestCmd вызывает исходные prepare_ingest_path/ingest_rule_preflight,
IngestUploadCmd и native linking внутри одной Command transaction. Code/id
привязка по точному path применяется до naming/check-in, instance — через
SObjectLinkCmd. Результаты скриптов, файл, объект, snapshot и связь откатываются
вместе при отказе или поздней ошибке. JSON/pattern не могут подменить id/project
или защищённые поля. Native интерфейсные create/edit/checkin разрешения учитываются;
доступ к серверным скриптам остаётся admin, как в текущем API.

Проверки: production build; шесть тестов на временных SQLite-проектах.
Chromium: реальная загрузка, сохранение/чтение/удаление правила, фильтр,
новый объект, обновление, duplicate/skip, неоднозначный update, защита черновика,
Script Editor и повторное открытие; существующие меню/check-in/preview также прошли.
Native: instance/code/alternate/id, точный parent, pattern/context, Python hooks,
откаты после файловой записи и привязки, недопустимые пути/поля/чужой проект.
Регрессии: TH XML-RPC image check-in, preview retry и обычные/grouped/revision
check-in с FileUndo, исходный server-side ingest. Свежие снимки:
`.screenshots/handler-current/ingest-files.png` и `.screenshots/object-menu-ingest.png`.

Ограничения этого браузерного блока: доступные File uploads, без серверных
произвольных каталогов/zip/sequence ingest. Другой native IngestionCmd для
серверных правил не заменён. PostgreSQL/Firefox/Safari и end-to-end TH relation
ingest не проверены этим прогоном. Repository Sync и TH/DCC connection исключены.
Полный этап desktop-меню остаётся открытым; далее — глубокое Duplicate и профили.


### 2026-10-09 — глубокое Duplicate и сохранённые выборы

Источники: текущие `thlib/ui/sobject_duplicate.py`, `DuplicateSObjectView.qml`,
`SObjectFieldFrame.qml`, справка duplicating_objects и две процедуры
`analyze_sobject_duplicate` / `duplicate_sobject_advanced` из `thlib/tactic_query.py`.
Сняты свежие офлайн-снимки реального QML через его тестовый контроллер:
`.screenshots/handler-current/duplicate-{fields,relations,snapshots,messages,review}.png`.
Веб-снимки этих страниц и RU — `.screenshots/duplicate-*.png`.

Основное Duplicate… теперь открывает мастер Fields → Relations → Snapshots →
Tasks and messages → Review. Native EditWdg даёт описания полей и значения
селекторов; идентификаторы и поля связей не редактируются. Сохраняются родительские
и instance-связи на исходные объекты, выбранные прямые дочерние объекты получают
копии. Процессные снапшоты, задачи, ветки заметок и вложения выбираются отдельно;
зависимости флажков совпадают с контроллером Handler. Окно использует общие controls,
палитру, типографику, меню, drag/maximize и RU/EN. Старое копирование только полей
оставлено как явно доступная дополнительная команда «Duplicate fields only».

Remember хранит только режимы связей и шесть флагов содержимого, по
login/project/Search Type в localStorage этого браузера. Quick Duplicate доступен
при наличии этих выборов и каждый раз заново читает источник. Изменённые значения
полей не сохраняются в профиле. Черновик сохраняется при отказе; повторный анализ
не стирает введённое. Потерянный ответ запрещает повторный submit до проверки
объектов. Захваченные source key/ticket/project защищены от смены контекста.
Все три места вызова меню обновляют свои результаты после успешного завершения.

На сервере используются native SObject/Schema/Search, Note.copy_note, clone,
FileCheckin и одна Command/FileUndo transaction. Исправлены недостающий исходный
Search.add_group_aggregate_filter и группировка текущих снапшотов по реальному
code/id владельца. Схема обходится с именованными путями и направлением
самоиерархии. Файлы проверяются перед записью, затем копируются через FileCheckin
в независимое владение нового объекта вместо общих inplace-путей. Это не меняет
семантику обычного TH inplace check-in. Native stale-source UserException даёт
понятное сообщение; граница проверяет проект, create permission, редактируемые
скалярные поля, режимы связей и флаги процессов. Revision проверяет данные анализа,
а не является глобальной блокировкой всей истории файлов/сообщений.

Проверены пять сценариев: native глубокая копия с веткой заметок и тремя видами
вложений, независимость путей/байтов, отсутствующий файл, откат после реального
файлового копирования, более высокая версия у другого владельца; самоиерархия с
сохранением/отключением родителя и только прямыми детьми; Chromium RU/EN,
сохранение/перезагрузка/изоляция по проектам, свежие поля Quick Duplicate,
зависимости флажков, stale-source reanalysis, unknown-result/dirty guards и
геометрия окна; регрессия контекстного меню с ingest/preview/revision/grouped
check-in; TH XML-RPC image check-in. Production build выполнен; новая форма
загружается отдельным lazy JS chunk. Прогоны — временные SQLite-проекты,
`cg_test` не изменялся. Тесты закрывают серверные потоки и Chromium.

Границы: PostgreSQL, Firefox/Safari, production cg_test и конфиги с пользовательскими
редакторами полей не проходили этот прогон. Профили не синхронизируются между
браузерами и не импортируются из локальных настроек TH. Desktop/DCC action hooks
и соединение с TH не добавлялись; native серверные commit/trigger правила остаются.
Это завершение конкретного блока, а не всего этапа desktop-меню. Далее — меню
точного файла и versionless Delete Whole Tree.


### 2026-10-10 — читаемые имена JS без хешей

Vite entry/chunk filenames теперь assets/[name].js: ColumnsEditor.js,
AppMenu.js, ScriptEditor.js и соседние .js.map. Ленивые экраны, отдельные
Vue/icons/locales и читаемые функции/source maps сохранены. Для JS и карт
сервер вместо immutable использует public,no-cache и ETag SHA-256 содержимого.
If-None-Match (включая weak/list/wildcard) возвращает 304 без тела; после
изменения содержимого возвращаются новая версия и новый ETag. CSS/шрифты и
политика справки не менялись. Требуется перезапуск Python-воркеров для новых
заголовков и обновление страницы после развёртывания; изоляция одновременно
открытых старых/новых версий при rolling deployment не реализована.

Production build и граф 37 записей manifest прошли. Две HTTP-проверки на
собственном сервере подтвердили пути/MIME/кеш и изменение версии JS/maps.
Существующий lazy_loading.mjs прошёл в установленном Edge: 13 стартовых JS,
6 отложенных экранов, HTTP source map с точной исходной строкой Vue,
редакторы/черновики, отдельный docs root и ошибка загрузки. Комплектный
Playwright Chromium отсутствует; Firefox/Safari не проверялись. Описание
добавлено в существующую справку debug_log на EN/RU и включено в сборку.
Тестовый сервер и браузер завершены в finally.


### 2026-10-10 — 0.112.1: запуск без принудительного admin

Начальные login/project/workspaceProject/type пустые. Свежий вход и новый
проект не создают вкладку Projects. При загрузке нет fallback на admin или
sthpw/project; недоступный сохранённый проект оставляет выбор пустым.
Последнее успешно использованное имя хранится в tactic_stream.lastLogin,
выбор — в tactic_stream.selection.<login> без ticket/пароля. Существующий
workspace.<login> восстанавливает разделы/активную вкладку/черновики/вид/фильтры,
выделение/прокрутку/layout. Сессия авторизуется до восстановления записей.
Явный проект/skey в URL сохраняет приоритет. Явный logout очищает ticket и URL,
но сохраняет выбор и рабочие пространства своего аккаунта.

API-справочник получает логин/проект из сохранённой сессии вместо admin.
Нет project navigation/layout запросов без выбранного проекта. Session identity
добавляет administration, вычисленный native Security.is_admin; доступность
инструментов администратора больше не зависит от загруженной таблицы.
Первоначальный отдельный стартовый экран не реализован, используется
существующее пустое рабочее пространство и штатный выбор проекта.

Пройдены Edge workspace_session (пустой логин/проект/вкладки, закрытие страницы,
два поиска/активная вкладка/черновик, пустой проект после reload, logout и два
аккаунта, недоступный проект, инструменты администратора без таблицы),
navigation (включая свежий вход по skey), lazy_loading и documentation.
Node workspace_state и help-search, две native HTTP проверки identity/health
и production build прошли. 53 темы справки сохранены; startup/restoration
описаны в configuration.projects на EN/RU. Сценарии других браузерных проверок
теперь явно вводят свой fixture-login/проект вместо зависимости от дефолтов;
весь браузерный комплект не запускался. Firefox/Safari не проверены.
Серверы и браузеры тестов завершаются в finally.


## 2026-10-10 — 0.112.2: URL без внутренних ID поисковых вкладок

workspaceAddress оставляет проект, search_type/view или skey. ID активной
вкладки сохраняется в history.state.tab, а открытые вкладки — в существующем
хранилище рабочего пространства своего аккаунта. Запись истории различает
вкладки даже при одинаковом URL. Вход/Назад/Вперёд выбирают только реально
сохранённую вкладку для данного проекта, Search Type и view; закрытая вкладка
не создаётся повторно. Внешняя ссылка не передаёт внутренний ID отправителя.
Query-параметр tab больше не записывается и не читается.

Пройдены production build, Node rich_text/workspace_state и Edge navigation:
две вкладки с одинаковым адресом, Назад/Вперёд, reload, закрытая вкладка,
скопированный URL в новом контексте, вход по skey. Edge workspace_session
проверяет восстановление после закрытия страницы и раздельное состояние
аккаунтов. Help configuration.projects обновлена EN/RU. Firefox/Safari и весь
браузерный комплект не запускались. Свои тестовые серверы и браузеры завершаются
в finally.


### 2026-10-10 — 0.112.3: проекция родителя и детей в API

get_parent/get_all_children используют существующие _get_sobject(s)_dict.
columns=[] сохраняет полную запись; непустой список ограничивает поля,
__search_key__/__search_type__ остаются, отсутствующее поле равно None.
Оригинальный API терял проекцию внутри _get_sobjects_dict: source-поведение
и правильная проекция имеют отдельные ожидания. Core SObject.get_parent
по-прежнему игнорирует deprecated columns. Серверный show_retired=True и
исходный клиентский False не изменены; это различие теперь явно описано.

Пройдены 23 Windows теста schema/local_sobjects/search_expression_filters,
включая реальный исходный runtime, неизменённый XML-RPC SDK, локальный клиент
серверного Python, два проекта, wildcard/prefix/id/code родителей, missing/
retired, читателя и запрет вложенного чтения, откат пишущего фильтра.
Отдельная временная PostgreSQL база внутри Docker-сети проверила родителя и
заметки с теми же проекциями, что SQLite, и удалена в finally. Тестовый
контейнер --rm; пользовательские контейнеры и cg_test не менялись.
API-справочник и core_model обновлены EN/RU, production build и совпадение
Help в public/runtime проверены. Все 129 методов остались в справочнике.
get_all_children instance JOIN и полный паритет API этим не завершены.

### 2026-10-10 — 0.112.4: дети через instance-связь

SObject.children_alter_search и Search.add_parent_filter используют существующий
Search.add_relationship_filter. Исправлен обратный одиночный поиск: фильтр
применяется к таблице родителя и фактической ключевой колонке. В исходнике
children строил несуществующую прямую колонку, обратный поиск фильтровал другую
таблицу, а query(parent_key=...) для instance вообще не ограничивал результат.
Эти дефекты имеют отдельные исходные и правильные ожидания.

Сохранены исходные дубликаты по числу связей, фильтрация retired целевого типа
и отсутствие автоматического retired-фильтра промежуточной таблицы. Полная
запись сохраняет _related_code; columns использует обычный сериализатор API.
Проверяются права на оба endpoint-типа и промежуточный тип. Межресурсная связь,
self-instance children без разных путей/aliases и буквальный relationship=
many_to_many явно отклоняются; type=many_to_many с relationship=instance
не исключён. Дополнительный API или другая модель связей не создавались.

Прошли 55 Windows тестов schema/search_links/search_joins/search_select/
select_serialization/schema_api/search_expression_filters: настоящий исходный
runtime, неизменённый XML-RPC SDK, серверный Python, обе стороны, пустые связи,
разные ключевые колонки, проекция, два проекта, права и откат. Отдельная
временная PostgreSQL база проверила add_instance → get_all_children в обе
стороны → remove_instance на тех же данных, что SQLite, и удалена в finally.
Тестовый контейнер --rm; пользовательские контейнеры и cg_test не менялись.
API-справочник и core_model обновлены EN/RU; production build и Help проверены.
Self-instance children, межресурсные JOIN и полный паритет API остаются открыты.

### 2026-10-10 — 0.112.5: пакетные instance-фильтры

Search.add_relationship_filters фильтрует присоединённый источник по списку
фактических ключей схемы и op. Search.add_relationship_search_filter извлекает
эти ключи через обычный compiler/connector с bound-параметрами. Копия Search
с отдельной ключевой проекцией сохраняет фильтры, JOIN, страницу, ресурс и
повторную проверку ACL; aliases входной проекции не заменяют реальные значения.
_related_code в пакетном пути содержит ключ схемы: группировка
get_related_by_sobjects работает и при разных ключевых колонках сторон.

Исправлены исходные игнорирование списка/op, неверное направление ключа и
ошибочное чтение первого поля произвольной проекции. Source/runtime и правильные
ожидания разделены; исходный count пустого instance-поиска тоже неверен.
in/not in фильтруют строки JOIN: цель с выбранной и другой связью может
вернуться через другую. Пустой вход при обоих операторах не даёт результатов;
delay_null в instance-ветке не меняет это поведение. Явно переданные retired
источники допускаются; источник-Search учитывает собственный show_retired.
Дубликаты и retirement промежуточных строк сохранены. Смешанные source-типы
и источники на чужом ресурсе явно отклоняются до JOIN.

Прошли 20 дополнительных исходных runtime-сценариев и 62 Windows теста:
обе стороны, in/not in, пустой вход, preload objects/count, разные колонки,
aliases, права промежуточного типа, XML-RPC SDK, серверный Python и rollback.
Suite содержит ещё одну условную PostgreSQL expression-проверку, пропущенную
на Windows; отдельная реальная PostgreSQL fixture проверила пакетный поиск,
группировку и оператор вместе с SQLite. Временная база удалена в finally,
контейнер --rm; пользовательские контейнеры и cg_test не менялись.
core_model и подсказка серверного Python обновлены EN/RU. Число API-методов
не изменилось. Self-instance aliases, межресурсные JOIN, агрегатные проекции
источника и полный паритет API не объявлены завершёнными.

### 2026-10-10 — 0.112.6: fast code/ID при проекциях и JOIN

get_sobject_codes/get_sobject_ids и instance-source extraction используют общий
Search._get_sobject_values. Штатное добавление ключевой колонки в исходный Select
сохранено; исполняемая копия добавляет реальную колонку базовой таблицы в конец
проекции, сохраняя остальные поля/aliases, JOIN, параметры, distinct и страницу.
SQLite Row берёт последнее значение, PostgreSQL dict — значение последней
одноимённой колонки. Исходные helpers ошибочно возвращали первое выбранное
поле; фактические исходные результаты и правильные ключи проверяются отдельно.
Список не получает неявную сортировку и не превращается в DISTINCT по ключу.
Дополнительная проекция копии не остаётся в вызывающем Search.

Custom alter_search вызывается один раз; текущие права основного типа и
вложенная read-policy проверяются при исполнении копии. Sudo-created Search
не сохраняет право на запрещённый основной тип после выхода из Sudo.
Retirement-состояние возвращается в исходный Search, как при прежнем чтении.
Loaded SObject cache и несохранённые атрибуты не подменяют значения БД.
NULL-код сохраняется как None; пустой/запрещённый основной поиск даёт [].

Прошли 22 дополнительных source-runtime сценария и 75 Windows тестов:
имя/звёздочка/aliases/JOIN, дубликаты, NULL/retired, страница, второй проект,
повторные вызовы, custom hooks, read-policy/Sudo, Select сериализация,
SQL/expression-пути, исходный XML-RPC SDK, серверный Python и rollback.
Две условные PostgreSQL проверки в Windows suite пропущены; отдельный реальный
PostgreSQL/SQLite контракт проверил оба ключа, JOIN, aliases и пагинацию.
Тестовые серверы закрываются в finally, временная база удаляется, контейнер --rm.
Пользовательские данные и контейнеры не менялись. core_model/search_select
обновлены EN/RU; API-методы/сигнатуры не добавлялись. Grouped/aggregate проекции,
self-instance aliases, межресурсные JOIN и полный паритет API остаются открыты.


### 2026-10-10 — 0.112.7: направленное self-instance чтение

Search использует общий _get_relationship_attrs/_add_instance_relationship.
Self-instance определения должны иметь оба явных code/id endpoint path:
parent — связь к участнику, child — связь к владельцу (соглашение Handler).
Default/parent читают участников; child читает владельцев. Фильтрация идёт
по фактическим ключам схемы; таблица линков и таблица источника получают
разные aliases. Оборванный источник остаётся NULL и не проходит key filter.
Один Search может содержать ограничения обоих направлений; copy и Select
dumps/loads сохраняют aliases. Структура объекта результата и search key
остаются обычными. Неизвестный путь и неполные концы схемы отклоняются.

Single/list/Search-фильтры, children, query(parent_key), maps и Results tree
используют этот путь. Убрана отдельная self-instance ветка result_items,
её поведение проверено на временной копии пользовательского cg.zip.
Публичные подписи Search/API не менялись, runtime legacy/Handler не импортируется.
Same-type identity fallback остаётся, если instance-связь не определена.
13 настоящих исходных сценариев отделяют исходный identity/error дефект
от направленных native ожиданий. code/ID ключи, дубликаты, retired цели/
линки, циклы/self-ссылки, пустые/оборванные связи, два проекта, карты,
NOT IN, projection/page, hooks, aliases/copy/Select restore, отказ обычному
читателю в доступе к link type, nested policy и Command rollback проверены.
85 Windows регрессий прошли (87 всего, две условные PostgreSQL проверки
пропущены); PostgreSQL relationship/alias check запущен отдельно и прошёл.
Неизменённый XML-RPC SDK проверяет детей/query/серверный Python и откат;
изолированный cg.zip проверяет фактическое дерево/счётчики/операции линков.

Справка core_model/search_select и API get_all_children/query/server Python
обновлена на EN/RU. Полные same-type add_instance/get_instances/remove_instance
контракты направлений и записи не объявлены завершёнными: следующий шаг плана.
Межресурсные JOIN, произвольные агрегатные ключи и полный API остаются открыты.
Пользовательский cg_test не менялся; тестовые серверы, контейнер и базы
закрываются собственными finally и проверяются после завершения.


### 2026-10-10 — 0.112.8: запись направленных self-instance связей

Schema._get_self_instance_edges проверяет два явных code/id path и разные
колонки линка; чтение и SObject._get_self_instance_search используют его же.
Владелец — child path, участник — parent. add_instance сохраняет оба конца,
get_instances возвращает исходящие активные записи линков, remove_instance
удаляет все активные дубликаты точной направленной пары. Обратные связи,
другие участники и retired-линки остаются. Дубликаты, self-links и циклы
не запрещены. Отсутствие совпадений при удалении — no-op. Результат не является
списком детей; get_all_children остаётся отдельным контрактом.

Проверяются фактические ключи сохранённых объектов, доступ к типам, один проект
и ресурс; несохранённые/устаревшие/отсутствующие концы и неполная схема
отклоняются. Штатные commit/delete, триггеры, логирование и Command сохранены.
Исходные ошибки перезаписи одного конца и ненаправленного удаления проверены
16 сценариями настоящего original runtime и независимыми native ожиданиями.
91 Windows регрессия прошла (93 всего, две условные PostgreSQL пропущены);
отдельная PostgreSQL/SQLite проверка, stock SDK/XML-RPC, серверный Python,
успешные commit, откат insert/delete-триггеров и временный cg.zip прошли.
SQL NULL сравнивается по сырым данным, а не по get_value vendor defaults.

Ограничение: _check_business_write всё ещё требует администратора для обычных
бизнес-записей. Link read ACL проверены отдельно, разрешающий edit ACL обычного
пользователя не обходит этот guard. Это не завершённый паритет ordinary-user
записи; следующий шаг — сверка общей write policy с исходным ядром.
Публичные подписи не менялись; legacy/Handler не импортируются в runtime.
EN/RU core_model и справка трёх API/серверного Python обновлены. Межресурсные
JOIN и полный API остаются открыты; пользовательский cg_test не менялся.


### 2026-10-10 — 0.112.9: обычные пользователи и проектная запись

SObject._check_business_write проверяет пользователя запроса, Command/resource,
project allow, search_type insert/edit/delete, фактический проект колонок,
текущую видимость существующей строки и отложенные колонки. API допускает
insert/insert_multiple/update/update_multiple/delete_sobject/add_instance/
remove_instance; системные типы и остальные команды остаются защищены отдельно.
Общий _do_security_dml использует placeholders vendors и ограничивает SQLite
авторизацию одной таблицей/statement с восстановлением в finally. Native SQL
вне разрешённого object DML не получает новых прав; DDL/read guards сохранены.

GlobalSearchTrigger создаёт/обновляет/удаляет интегральный индекс через штатный
Sudo с finally, не поднимая общие права вызывающего пользователя. Сохраняются
Command, триггеры, XML удаления, объектный журнал и change timestamps. Очистка
redo ограничена фактическим login/type в конечном SQL и сохраняет чужие записи.
17 сценариев настоящего original runtime и отдельные native ожидания отмечают
исходные пробелы type/project write ACL. Исправлены вставка с view/edit и
staging колонок по чужому текущему проекту; правила проверяются заново в commit.

111 Windows проверок прошли (113 всего, два условных PostgreSQL пропущены).
Отдельная настоящая PostgreSQL/SQLite проверка CRUD/link/journal/index/redo,
неизменённый SDK/XML-RPC от обычного пользователя, типы/поля/другой проект,
staging/row filters, raw SQL denial, откат триггеров/массовой правки,
существующие аккаунты/сообщения и временный cg.zip прошли. Справка core_model
и семь API операций обновлена EN/RU; публичные подписи и 129 методов сохранены.
Пользовательский cg_test и сервисы не менялись; собственные тесты закрываются.

Незавершённо: обычные системные/конфигурационные записи, файловые права,
StatusLog/Workflow эффекты и persistent diagnostics. Последняя пока может
дать дополнительное сообщение отказа при попытке сохранить ошибку обычного
пользователя; исходная ошибка и rollback сохраняются. Полный API не готов.

### 2026-10-10 — 0.112.10: обычная диагностика и границы команд

DebugLog/ExceptionLog и API log сохраняют только аутентифицированного автора
через отдельную собственную Command-транзакцию. Узкая область Diagnostics:writing
содержит сам SObject, разрешая его вставку и штатный generated-code update;
SQL binder повторно проверяет автора, ресурс и фактические поля. Прямые записи,
удаление диагностических строк и произвольный SQL обычному пользователю запрещены.
Метод API сохраняет исходную подпись/True и учитывает api_method restrictions.

Воспроизведён и исправлен исходный дефект Command: после nested failure pop
удалял только последнюю команду, оставляя корневую. Следующая операция считалась
вложенной и не откатывала свою запись. Ошибка корневой команды теперь очищает
весь стек, диагностическое исключение сохраняется один раз после rollback.
У Batch вход обычного пользователя оставлял RequestContext login=admin и SQL
соединения инициализации. Закрывается весь принадлежащий ему начальный контекст;
новый содержит фактический login и Security без административных соединений.

Проверены исходный ordinary/admin runtime, исходный SDK по HTTP XML-RPC,
автор/уровень/метод/raw SQL, nested и следующий rollback, постоянные записи
после ошибки, прежние аккаунты/сообщения/Workflow и изолированные SQLite/PG.
EN/RU справка «Модель ядра», Debug Log и метод log обновлены. Полный API не готов.
Независимое логирование при активном system writer по-прежнему явно отклоняется,
сохраняя вызывающую транзакцию. Deferred/email diagnostics не перенесены.
Далее: StatusLog/Workflow эффекты обычных пользователей, файловые права и
оставшиеся контракты транзакционных API. Исторические ограничения 0.112.9 выше
описывают тот выпуск, текущая диагностика закрыта в указанной области.

## Рабочие панели: Snapshot Browser — 0.112.31

Пункт 2 завершён в согласованном browser-объёме. В пункте 3 после Description
перенесён основной экран Snapshot Browser: текущие QML/controllers/state, общий
док, native выборка и file editor/delete. Точное удаление через Snapshot/FileUndo
проверено с принудительной ошибкой commit, откатом SQL/байтов и сохранностью
соседних версий. Исправлена общая SQLite типизация varchar/char/numeric с параметрами
и чтение readonly MetadataElementWdg без старого HTML renderer.

Справка dock.snapshot EN/RU описывает вызовы, defaults, действия, права и границы.
Галерея `.screenshots/snapshot-browser-current/index.html`: семь состояний
при 440×500 и 880×650, исходный неизменённый QML с native-record fixture
и реально отрисованный Chromium-компонент. Растеризация Qt/Chrome отличается;
полный pixel parity и полный сеанс подключённого Handler не заявлены.

Snapshot Browser ещё требует отдельных metadata member rows sequence/UDIM/UV.
После их завершения идут Knowledge Base, Drop Plate и полная Commit Queue;
затем весь Task Manager/Inspector, сообщения, контекстные меню и layouts.
Мобильный блок остаётся после подгонки desktop. Это не завершение пункта 3.

Приёмка 0.112.31: 22 совместных transport/browser сценария —
`.screenshots/snapshot-browser-acceptance.log`; пять дополнительных сценариев
навигации, quick-task, мобильных форм/профиля и search suggestions —
`.screenshots/snapshot-browser-regression.log`. Все прошли. 22 native/UI
проверки delete/preallocation/XML/метаданных/типов/ресурсов —
`.screenshots/snapshot-browser-native.log`; три финальных проверки EN/RU
ресурсов — `.screenshots/snapshot-browser-translations.log`. Отдельная
калибровка Snapshot Browser/Configuration/геометрии — три сценария
в `.screenshots/snapshot-browser-test.log`. Сборка и 14 пар/overlay проверены.

Сопутствующий общий баг: progress-узел без workflow.search_type ошибочно
сопоставлялся с обычной процессной веткой и ломал result-items. Проверка
связанного типа и именно relation-ветки теперь соответствует query_sobjects
исходного Handler. В UI-тестах явно задаётся обычная native sidebar fixture,
не используется отрицательная kernel schema или старое ожидание автоматической
вкладки/внутренних tab ID в адресе. Код пользовательского сервера/Handler
не перезапускался; backend-изменения применяются после его штатного рестарта.


## Первый следующий чанк: Knowledge Base — 0.112.32

Закрыт браузерный сценарий базы знаний. Источники: текущие Knowledge*.qml,
KnowledgeRichTextToolbar, KnowledgeAttachmentLibrary, RevisionHistoryPopup,
knowledge.py/knowledge_api.py и RichTextDocumentController в ТХ. Серверная
процедура перенесена целиком с EPL-1.0 provenance; HTML/Qt renderer остаётся
настольным, веб использует существующий MarkdownIt и общие controls.

- Общий лениво загружаемый док Browsing → Knowledge Base, дерево, разделы,
  поиск по тексту, чтение, оглавление и структура header/editor/library из QML.
- Двухэтапное создание, Visual/Markdown, headings/emphasis/lists/checklists,
  таблицы, ссылки, изображения с шириной/drag-handle, quotes, alignment,
  undo/redo и общая подсветка Python/JS/XML. Опасные HTML/URL очищаются.
- Локальные черновики отдельно для пользователя/проекта, server draft,
  Publish/Save и защита конкурентной записи. Перезагрузка проверена для
  существующей несохранённой статьи и ещё не сохранённой новой статьи.
  Настоящий skey открывает статью; временные editor IDs в адрес не попадают.
- Организация дерева с cycle check, Save order/Discard и ревизией каталога.
  Связь с выбранными SObject и book action у связанных опубликованных статей.
- Native журнал транзакций и preview старой ревизии; ID события устраняет
  неоднозначность изменений в одну секунду. Возврат не перезаписывает статью.
- Native FileCheckin/Snapshot/File/FileUndo для вложений, разные физические
  оригиналы/web/icon, Unicode-имена, permanent URL, загрузка/paste/drop/retry,
  retire и общий DeleteCmd с выбором зависимостей.
- Явная инициализация проекта, без DDL при чтении. Обычные пользователи читают
  допущенные публикации; чужие drafts скрыты также через skey и снапшоты.

**Исправления совместимости и общих компонентов.** Local TacticServerStub.get_login
теперь читает настоящий bound Login вместо None. SQLite разрешает подключение
активным обычным аккаунтам для native metadata reads; запреты raw DML/schema
сохранены и проверены. Общий док уведомляет о доступности после измерения геометрии,
поэтому восстановленная панель загружает данные. ResultPresentation восстанавливает
ветку, раскрытую во время обновления записей. Help reload сохраняет открытую
навигацию. AttachmentCard получила исходные activationIcon/activationLabel;
прежние callers сохраняют defaults. Отдельный остаток Snapshot Browser закрыт:
13 metadata patterns, страницы членов групп по 50, ограниченная память и native
лексикографический порядок; право проверяется также у владельца задачи.

**Справка и свидетельства.** Обновлены существующие dock.knowledge EN/RU и
внутренний контракт dock.snapshot. Экранные сравнения:
`.screenshots/knowledge-current/index.html` — 8 состояний × 2 ширины,
`source-manifest.json` — текущие SHA-256, `projection.json` — частная native-fixture.
Qt-кадры воспроизводятся `tools/capture_knowledge_reference.py`; Chromium-кадры
снимаются с настоящего Vue-компонента в сквозном транспортном тесте. Применяется
тестовый QObject/controller harness ТХ; подключённый рабочий сеанс ТХ не заявлен.
Растеризация Qt/Chromium и локальный формат дат могут различаться.

**Проверки.** Native: bootstrap/SQL/security/object permissions/Python scripts/
deletion + Knowledge Base + FileObject metadata. Browser: Knowledge Base (включая
reload drafts, image check-in/resize, history и native deletion), Snapshot Browser,
Description, workspace layouts, Help и SObject context/deletion. Логи находятся
в `.screenshots/knowledge-*.log`; production-данные эти fixtures не меняют.

**Границы.** Загруженные вложения сохранены нативно, но File-объекты ещё не
отправленной очереди не переживают reload: файлы выбираются повторно. Clipboard
подчиняется HTTPS/разрешениям браузера. Рабочие PostgreSQL/MySQL и физические
телефоны этим блоком не проверялись. Repository Sync, S3 и TH/DCC исключены.
Следующий чанк — Drop Plate + полная Commit Queue + сквозной check-in.

Итоговые свидетельства: 62 функциональные проверки большого native-прогона
прошли; изменившийся параллельно хеш живого `thlib/tactic_query.py` обновлён и
проверен отдельно (`knowledge-provenance.log`). Ещё 17 проверок Knowledge /
FileObject / SearchLinks прошли после защиты ссылок на private draft files.
Все семь выбранных транспортных/Chromium сценариев прошли после исправлений;
карта повторных прогонов — `.screenshots/knowledge-current/verification.json`.
Проверка списка процессов подтвердила отсутствие собственных тестовых процессов;
существующее дерево рабочего `serve --open-browser` оставлено работающим.

## Чанк 2 — Drop Plate / Commit Queue, 0.112.33

Блок завершён в согласованном браузерном объёме. Следующий — чанк 3:
Task Manager / Task Inspector / заметки и сообщения; в этом проходе он не начат.

**Экраны.** Drop Plate принимает файлы, каталоги, drag-and-drop и реальные
файлы буфера. Штатные FileObject/MatchTemplate собирают последовательности,
UDIM/UV, слои и комбинированные группы. Matching Templates переносит 19
актуальных defaults, enable/create/duplicate/reorder/delete, обязательные
fallbacks, process/context mapping, preview/test и Save/Cancel черновика.
Выбранные группы переносятся в очередь без отправки, как в ТХ.

Commit Queue хранит захваченный объект/проект/процесс/контекст и файлы.
Доступны описание, naming preview, репозиторий, версия/ревизия, versionless,
исходные имена, создание/выбор/вставка preview, управление preview, правки
отмеченных строк, порядок, дубликаты Replace/Add another/Ignore, явная отправка
всех/отмеченных/текущей, автоочистка и точный результат в Snapshot Browser.
Версии предварительного плана резервируются по порядку ожидающих операций;
новая проверка останавливает старый проход расчёта. Файлы после reload выбираются
заново; неизвестный результат не отправляется повторно автоматически.
Док и вложенные переносимые/разворачиваемые окна используют общие controls.
Видимые дополнения Stream: Naming Editor, восстановление метаданных очереди,
защита Result unknown и регулируемый splitter редактора шаблонов.

**Ядро.** BrowserCheckinCmd использует extracted Handler extended naming/check-in,
native Command, Snapshot version lock, FileAppendCheckin, IconCreator и FileUndo.
Единственная разрешённая обычным пользователям команда проверяет native права
объекта/проекта/snapshot/file/полей; произвольный execute_cmd этим не открывается.
Общий commit File metadata восстанавливает все inplace-члены группы из remove
того же активного журнала: это исправляет и неизменённый скрипт ТХ. Native
DeleteCmd удаляет все metadata-члены, сохраняя rollback/undo/redo. Корневой
inplace checkin_dir разрешается в HTTP-путь через тот же repository alias;
реальная загрузка имени с пробелами проверена. Чужие назначения не перезаписываются.

**Сверка.** Галерея `.screenshots/checkin-current/index.html`: четыре пары текущего
неизменённого QML и Chromium (Drop Plate, очередь basic/advanced, Matching Templates),
плюс групповые правки и результат Snapshot Browser. Измеренные logical size/DPI
и SHA-256 десяти исходников сохранены рядом. Qt запускается с native тестовыми
контроллерами без рабочего подключения ТХ; PNG не перекрашиваются и не правятся.
При сравнении учитывается DPI, растеризация Qt/Chromium может различаться.

**Проверки.** 46 native-регрессий check-in/delete/upload/metadata/batch;
заключительные 3 BrowserCheckin + source hashes/signatures; 6 Chromium-сценариев:
Drop Plate/очередь (папки/группы, CRUD шаблонов, планы/порядок/дубликаты,
групповые правки, preview, явная отправка и reload recovery), SObject check-in/
revision/ingest/download, SearchType preview, mobile cancel/retry/unknown,
Snapshot Browser и workspace layouts. Логи: `.screenshots/checkin-core-regression.log`,
`checkin-final-flow.log`, `checkin-release-browser.log`, `checkin-build.log`.
Справка дополнена в существующих EN/RU Drop Plate, Commit Queue и Core model.

**Границы.** Upload — браузерный способ передачи; локальные Copy/Move/Inplace/
Preallocate и DCC требуют исключённого desktop-подключения. Абсолютные локальные
пути не дают браузеру доступа к файлам. Clipboard/захват экрана подчиняются HTTPS
и разрешениям. Versionless copy/hardlink/symlink остаются опциональной штатной
настройкой: hardlink требует один filesystem, symlink — право ОС, незаметного
fallback нет. Hardlink группы проверен на Windows; права Windows symlink,
рабочие PostgreSQL/MySQL и физические телефоны этим блоком не проверены.
Repository Sync и S3 исключены. Все тесты используют отдельные данные;
рабочий сервер для приёмки новой серверной команды нужно перезапустить.

### Блок 8 — исходный HTML API и серверный JS (0.112.39)

Пять ранее отсутствовавших входных точек подключены. Перенесены исходные Widget/Html/HtmlElement/EventContainer/Palette/BaseRefresh, цикл ячеек TableLayout и SimpleTableElement, XML состояния PageNav/Bootstrap. Буферы и WebState принадлежат запросу; Palette не выполняет Python из настройки. Полная старая оболочка приложения/таблицы и неперенесённые классы завершаются явной ошибкой. Vue продолжает собственный рендеринг.

Исходные JsCmd и JS SDK используют QuickJS-NG вместо PyV8: синхронный JSON bridge, текущие API/ACL/Command, откат при ошибке. Серверный JS доступен через общий Script Editor/Shelf и исходный PythonTrigger. Promise/циклический результат запрещены; без DOM/DCC/произвольных Python-объектов. Нативный top_layout сохраняется отдельно от раскладок веб-доков; исправлены вложенные options и создание пользовательской записи при записи.

Проверки: `test_html_api`, `test_html_parity`, исходный embedded runtime, существующие metadata/script/transport regressions и Chromium Script Editor/Shelf. EN/RU Help `html_api` описывает контракты, параметры, ограничения и SDK-баги. 127 доступных методов / 129 exposed; два исключения, полный паритет false. Следующий блок должен расширять конкретные неподдержанные варианты, а не менять HTML на DTO.

Итоговый общий прогон: 945 запусков, 932 passed, 13 skipped, 0 failures/errors
(`.screenshots/api8-final-full.json`). Пропуски требуют отдельного PostgreSQL
или права Windows symlink; исходный PyV8 не запускался. Отдельно прошли 14
HTML/исходный-runtime проверок после последней правки диагностики, Chromium
Script Editor/Shelf с серверным JS и сборка Vite. Итоговый wheel установлен
в изолированный каталог: HTML/JS/top_layout исполняются из пакета, включены
JS SDK, зависимость QuickJS-NG, лицензия и EN/RU Help. Все собственные Python
процессы завершились, шесть ранее существовавших процессов сохранены
(`.screenshots/api8-final-process-cleanup.json`). Рабочий сервер не перезапускался;
для применения 0.112.39 требуется штатный перезапуск.

### Блок 9 — варианты native API и границы совместимости (0.112.40)

Восстановлены request-local `info` и затронутые SObject в ApiXMLRPC/ApiClientCmd;
ключи команд с привязанными kwargs, владельцем login/ticket и проверкой
разрешённого класса; прямой режим `use_transaction=False` с сохранением внешнего
отката. Добавлен исходный SQL builder Delete с исправлением завершающего AND,
экранированием, NULL и отказом от пустого фильтра. Работают исходные
COLOR/GRADIENT/PALETTE, включая headless gradient без выполнения Python из
аргументов. Снят устаревший запрет удаления snapshots уровней; latest/current
алиасы очищаются только в своём уровне, другие уровни/default сохраняются.
`view_as_attr` без @ проходит создание/validate/перечитывание/reorder через
общий WidgetDbConfig. Никакие бизнес-модели или XML-RPC ответы не заменены DTO.

`test_api_remaining` сравнивает исходные тела методов и одинаковые вызовы
ключей/форм/палитры; отдельно проверены права, неверный ввод и поздний откат.
SQL Delete исправляет видимый дефект исходника; удаление уровня проверяется
на настоящих bytes/rows, включая promotion предыдущей версии и откат.
Прошли 65 целевых проверок существующих команд/XML/HTML/уровней; сборка Vite
и чистая установка wheel с неизменённым SDK, двумя запусками и сохранением
проекта. Пакет содержит 44 текущих JS chunks с maps; workers завершены штатно.

EN/RU Help «Ядро и совместимость API» содержит примеры, матрицу вариантов,
различия с исходными багами и оставшиеся границы. Семь методов справочника API
получили двуязычные пояснения. `tools/audit_api.py --contracts-output` сохраняет
статический перечень явных UnsupportedContract guards с module/function/line;
в текущем `.screenshots/api9-contracts.json` 375 записей. Это защиты, исключения
и неподдержанные формы, а не 375 отсутствующих функций или runtime-покрытие.

Доступны 127/129 входов; два production-входа исключены, полный поведенческий
паритет false. Raw SQL/serialized/cross-resource формы, отдельные предметные
зависимости/события и remote/multi-site варианты имеют явные ограничения;
Mako widget execution не перенесён. QuickJS синхронный, без PyV8 object bridge.
Полная старая HTML-оболочка дальше не переносится по решению пользователя;
работающие методы и зависимости сохранены. MySQL отложен. Следующий блок — 11,
актуальные QML/Chromium сравнения и окончательная подгонка desktop UI.

Итог проверки блока 9: общий прогон 955 сценариев — 941 passed, 13 skipped,
одна ошибка тестовой Config-подмены, менявшей путь ticket-каталога вместо
единственной security-настройки. Исправлена только fixture; все 18 повторных
проверок нового API и каталога прошли. Итого 942 сценария прошли, 13 пропущены;
это составной результат, не второй полный прогон. Пропуски требуют PostgreSQL
или Windows symlink privilege; в этом блоке эти среды повторно не проверялись.
Свидетельства: `.screenshots/api9-full.json`, `api9-after-fixture.json`,
`api9-final-evidence.json`, `api9-wheel-acceptance.json`. Итоговый wheel
0.112.40 проверен из независимой установки; source checkout не импортировался.
Для применения backend изменений нужен обычный перезапуск рабочего сервера.
Финальная проверка процессов: собственных Python — 0; шесть исходных рабочих
процессов сохранены (`.screenshots/api9-process-cleanup.json`).

### Внеочередное исправление: обновления браузера при выключенном сервере — 0.112.42

Убран независимый 5-секундный опрос Messages и 30-секундный опрос NotesPanel.
Они следуют существующему ServerUpdates с курсорами; TaskManager также
синхронизируется после восстановления, сохраняя ревизии и черновики.
Фоновые чтения объединяются по полному контексту запроса, ограничены 30 секундами,
отменяются и отклоняются без очереди при сбое общего опроса. Записи и загрузки
не воспроизводятся автоматически. Скрытые вкладки приостанавливают чтения;
возврат синхронизирует открытые панели даже при пустом пакете, поскольку их
предыдущее чтение могло отмениться после продвижения общего курсора.
Повторы растут до 60–75 секунд; обычный интервал имеет разброс ±15%, ошибки —
0–25%. Фокус, online, Retry и смена интервала не обходят задержку.
Настройка остаётся в Connection/Configuration → Server, подробности — в EN/RU Help.
TH изучен: один worker и single-shot timer уже есть; дополнительные браузерные
таймеры и visibility-сценарий относятся к Stream. Серверный контракт не менялся.
Проверки: `frontend/tests/update_requests.mjs`, `update_outage.mjs`,
`server_updates.mjs`, `messages.mjs`, `tests/test_ui.py`, `test_server_updates.py`.
100 опросов в Chromium проверяют разброс, а не производительность рабочей БД.
SSE/WebSocket и нагрузочный стенд рабочего сервера в этот блок не входят.

### 0.112.43 — опциональный SSE вместо периодического опроса

Общий ServerUpdates принимает тот же пакет по POST SSE, с ticket/курсорами в
теле запроса. Выбор опубликован в NetworkSettings и ConnectionMenu; черновик,
Apply/Save/Cancel, локальное сохранение и периодический режим сохранены.
Transaction публикует маркеры только после успешного внешнего commit; чтение,
rollback и фоновый presence heartbeat не публикуют изменения. Per-type маркеры
в data/cache общие для процессов; один наблюдатель на ASGI-воркер объединяет
изменения для подписчиков, без собственного опроса БД для каждого клиента.
Нативная Security перепроверяется при чтении и heartbeat. В простое идут
комментарии keepalive; событие присутствия только при изменении online/offline.
Типовая инвалидация покрывает burst и одинаковые временные отметки курсоров.
Переподключение/смена проекта/скрытие/размонтирование закрывают старый поток;
записи не повторяются, черновики сохраняются. SSE — браузерное дополнение;
GUI ТХ и его существующий polling не изменены, полной паритетности нет.
EN/RU Help → Server configuration описывает внутреннее устройство и границы:
общий writable data/cache одного сервера, отсутствие гарантии exactly-once,
окно между commit и уведомлением, записи в обход SObject, настройки прокси.
Проверки: test_server_events, test_server_updates, транзакционные parity tests,
server_event_stream.mjs, server_events.mjs и прежние сценарии опроса/сообщений.
Скрин выбора: .screenshots/sse-configuration.png. Не заявлено нагрузочное
тестирование production PostgreSQL/100 реальных пользователей или Apache SSE.

### 0.112.44 — отдельное серверное ядро file_project

Первый блок реализован в новых pyasm.biz.file_project/file_catalog и
tactic.command.file_project_cmd. Создание — project_mode=file_project или
встроенный шаблон perforce_like; существующие проекты остаются classic.
API и schema/table ACL используют native Command/Search/SObject. Immutable
страницы, per-stream корень, версии, ordinary/exclusive checkout, workspace/Have,
черновики, uploads и persistent sync находятся в проектной БД. Submit атомарно
обновляет только корень и changelist; ошибки триггеров откатывают обе записи.
Batch сохраняет native validation/column ACL и callbacks, при настроенном
callback использует последовательный путь. Приватные blobs отделены от classic
repository static routes. Binary HTTP, Range и потоковый tar чанка — только
transport к этим же командам. Память ограничена страницами и чанками.

TH/TS UI не подключены: Classic CommitQA не переделан, P4V-панель пока план.
Особый режим проекта — server capability, а не глобальный флаг сервера.
Полный контракт, ACL-пример, измерения синтетического миллионного каталога и
проверенные ограничения записаны в README, раздел 0.112.44, и EN/RU Project Help.
PostgreSQL/TB, merge/rebase, shelve, edit lease, mappings нескольких depot,
reconcile, retention/GC и worker-проверка больших upload — дальнейшие блоки.

### 0.112.45 — проверка устойчивости файлового ядра

Блок 1 Perforce-like плана: настоящая временная PostgreSQL 18.6, конкурирующие
пользователи, duplicate requests, process death до/после COMMIT, native ACL,
callback sequence и откат metadata. Исправлены shared-page race, файловый откат
после освобождения DB lock, мусорный хвост после аварии, нулевое дополнение
отсутствующих bytes и удаление files при неопределённом результате COMMIT.
Bounded locks, одна проверка project DB при atomic binding и native пакетное
сохранение существующих checkout. По PostgreSQL 1000 новых путей: около 2 с;
1000 существующих: около 6 с. Subsecond цель не заявляется.

Инструменты: tools/file_project_checks.py (--postgres — owned disposable Docker),
tools/file_project_scale.py (реальные version/checkout через API, bounded chunks),
tests/test_file_project_resilience.py и аварийный subprocess fixture. Полные
измерения/права/ограничения — README 0.112.45 и EN/RU Project Help.
Интерфейсы TH/TS ещё не подключены; следующий продуктовый блок — редактирование
changelists, shelves и конфликты, затем depot/stream/workspace и большие transfers.


### 0.112.46 — общий сборщик обновлений, подписки веба и ТХ

Один процесс `updates` под TacticMonitor объединяет native commit-сигналы. SObject сохраняет конечные проект/участников в транзакции, без SQL после commit; rollback, ticket/journal bookkeeping и presence-only writes не уведомляют. Веб-воркеры наблюдают один revision feed и отправляют подходящие `changes`; рассылка не вызывает `query_server_updates` для каждого подписчика. Начальная синхронизация и presence/auth heartbeat сохраняются. Клиенты объединяют уведомления за 200 мс и читают нужные каналы, с native ACL и защитой черновиков. ТХ использует асинхронный Qt transport, видимый выбор Configuration/Connection, прежний XML-RPC poll остаётся доступен. Проектные записи направляются по проекту записи, сообщения — по delivery recipients; неполные метаданные допускают широкую рассылку типа.

EN/RU Help описывает протокол, ownership, задержки, настройки и ограничения. Источник состояния — штатные Search/Command/журналы; event feed не хранит пользовательские пакеты. Подписка по типам, не отдельным SObject; включённые activity notifications требуют событий проекта при закрытой панели. External SQL, несколько независимых standalone ASGI hosts, durable exactly-once и production benchmark 100 пользователей не покрыты. Проверки: native transport/transactions/messages, actual Qt Handler service against Stream, Chromium drafts/reconnect/modes, 100 shared-feed subscriptions, Qt coalescing, real collector crash/restart и остановка собственных процессов. Артефакты: `.screenshots/collector-native.json`, `collector-handler-native.json`, `collector-browser.log`, `handler-collector-focused.log`.

### 0.112.47 — файловые changelist, shelve/unshelve и разрешение конфликтов

Параллельный backend `file_project` получил update_change, change_files, remove_files,
move_files, shelve, unshelve_begin, rebase_begin, integration_next/finish/cancel,
conflicts и resolve. Classic-модули и классический чекин не изменены.
Схема версии 1 сохраняется: shelf — неизменяемый change, содержимое changelist —
отдельный immutable B+tree. Shelve сохраняет ссылки на готовые данные без копирования;
move передаёт файлы и ordinary/exclusive checkout в одной native Command transaction.

Rebase и unshelve сравнивают base/ours/theirs только для открытых путей, чанками до
1000. Видимый черновик переключается целиком после обработки всех чанков и разрешения
конфликтов; опубликованный stream меняется только атомарным submit. При повторном
изменении head завершение отклоняется. Resolve выбирает ours/theirs или готовый blob
результата ручного merge. Read и Range-download умеют читать shelf и стороны конфликта.
Stage сохраняется между запросами и переживает перезапуск; cancel освобождает новые
checkout чанками, сохраняя исходный черновик. Native права project/depot/row/column,
триггеры и откат применяются ко всем записям. Request ID и edit revision защищают
повторы/гонки; callback видит все страницы до сохранения ссылки на корень.

История учитывает только реально опубликованные ревизии: повторные правки черновика,
переносы и shelve не создают ложную историю публикации. Старые pending changelist
без рабочего каталога поддерживают ограниченную миграцию index_change, включая
checkout-only пути и exclusive-режим. EN/RU Help описывает API и восстановление.

Замер tools/file_change_benchmark.py на SQLite: реальный каталог 10000 путей,
1000 различных загруженных файлов, 500 KiB. Shelve 27,97 мс, move 1347,89 мс,
rebase 575,58 мс, unshelve 995,38 мс, submit 25,66 мс; пик 78,54 MiB.
Это вызовы серверного API без сети/GUI; build/upload измеряются отдельно.
Артефакт: .test-tmp/file-change-sqlite.json. Запуск tools/file_project_checks.py
с --postgres использует только собственный временный контейнер и удаляет его.

UI ТХ/ТС, cross-stream merge, автоматический текстовый merge и TB IO — следующие
блоки. Миллион путей в новом work-каталоге и production-нагрузка здесь не измерялись.


### 0.112.47 — проверка SSE и устранение пропусков

Подписки обоих клиентов охватывают справочники, config/widget_config,
config/custom_script и config/trigger. ТХ сохраняет уже существующую доставку
в Script Shelf/Script Editor/Trigger/Quick Filter; веб обновляет каталоги полки
и редактора с сохранением буферов и объединением событий во время занятости.
Первая синхронизация каждого SSE-канала явно инвалидирует подписанные типы,
включая запуск с сохранённым кэшем без journal cursor. Это может вызвать
повторное чтение моделей при смене подписки; в простое рассылок нет.
Связи и журналы статусов направляются по project_code записи. Получатели
нескольких сообщений одной транзакции объединяются; chat_attachment использует
участников уже захваченного message_log, без запросов к БД после commit.
Проверки: native маршрутизация и объединение участников, первый пакет без
курсора, подписки ТХ, Chromium с живым каталогом скриптов и несохранённым буфером.
Сохраняются ограничения 0.112.46: локальный feed, не durable queue, внешний SQL
не охвачен, heartbeat авторизации/присутствия зависит от числа клиентов.

Проверка блока changelist: все 32 file-project API сценария прошли на настоящем
изолированном PostgreSQL; SQLite прошёл новые сценарии, каталожный diff и Range HTTP.
Полная проверка PostgreSQL заняла 585,23 с. Проверены права обычного пользователя,
чужие blobs/changelist, shared shelf, конкурентные повторы, поздние native callbacks,
откат публикации и финального переключения, отмена двух чанков и восстановление.
Сборка Vue 0.112.47 успешна, канонические и опубликованные EN/RU Help совпадают.

PostgreSQL-замер с каталогом 10000 и 1000 различными uploaded файлами: shelve 447,91 мс,
move 9441,99 мс, rebase 2264,98 мс, unshelve 6052,07 мс, submit 301,98 мс;
пик 96,80 MiB. Build/upload отдельно, сеть/GUI не включены. Замер пересекался по времени
с изолированными тестами другого собственного контейнера и не является production SLA.
Артефакт: .test-tmp/file-change-postgres.json. Цель массовых операций <1 с не достигнута.

Общая Classic/SSE регрессия выявила независимый падающий сценарий
ServerEventsTransport.test_native_project_routing_and_chat_recipient_union:
в его fixture у message_log нет metadata. Проверка SQL/FileUndo/client transactions
успешна; Classic backend в рамках changelist не менялся. Эта ошибка не скрывалась.


### 0.112.48 — завершение блока SSE и список соединений

Опциональная доставка обновлений в Stream и Handler завершена. Общий серверный
services/update_interval доступен в существующем XML Configuration (0.1–2 s,
default 0.5, restart required). Клиентская задержка объединения событий доступна
в обоих Server Configuration (100/200/500/1000 ms, default 200), сохраняется штатно
и не сбрасывает активное соединение. Список реальных SSE-соединений доступен
администратору в Configuration → Server: все веб-воркеры, login/project/client/IP,
connected time, PID, channels/types; Refresh сохраняет черновик настроек.
Каждый воркер атомарно публикует только метаданные соединений, без тикетов и БД:
изменения списка за collection interval, живой lease каждые 20 s, expiry 45 s
после аварии, удаление собственной записи при shutdown. Poll/XML-RPC/presence
в этот список не входят. WNS/Web Push не реализованы и не включаются заглушкой.
Проверки и ограничения: существующие native/Qt/Chromium SSE-контракты, новые
multiworker/disconnect/expiry/ACL/draft/settings сценарии; production benchmark
100 настоящих клиентов не выполнен. Открытые несвязанные UI-тесты ТХ сохраняются.

### 0.112.49 — depot, stream, workspace и merge реальных ревизий

Серверный блок 3 Perforce-like завершён отдельными file_workspace/file_merge и
FileView рядом с Classic: repository bindings (private sibling storage), несколько
depot через read-only/writable mappings и исключения, CAS выбора workspace,
Have реальных версий, reconcile bounded локальных SHA/size manifest. Ветки разделяют
проверенный submitted snapshot родителя; merge сравнивает реальную общую базу,
записывает previous/integrated_from, обрабатывает удаления и ручные конфликты.
Публикация root и merge checkpoint атомарна через штатные Command/SObject/triggers;
права project/depot/row/column и rollback сохранены. Classic не переключается в
новый режим, старые workspace без mappings сохраняют legacy sync. TH не менялся;
новые экраны TH/TS и большой transfer pipeline остаются следующими блоками.

Sync фиксирует все источники при старте; Have обновляется только после ack чанка.
После полного sync сравнение immutable roots пропускает неизменившиеся поддеревья,
без full Have scan. Изменённые mappings вызывают очистку только tracked путей;
local_root/case policy change сбрасывает Have metadata, не файлы. Локальные bytes
серверу недоступны: клиент должен hash/verify и защищать dirty files перед ack.
Ограничения: 1000 source entries/RPC, 256 правил с непересекающимися положительными
destination prefixes; cross-depot merge/автоматический text merge не предоставлены.

Проверки: 49 SQLite API/catalog tests (47 passed + 2 PostgreSQL-only skips),
14 новых native PostgreSQL сценариев passed, реальные bytes/history/Range/tar,
многопользовательские права, CAS, multi-chunk merge, callback rollback и sparse sync.
Синтетический native каталог/Have миллион файлов: branch 28,31 мс,
unchanged begin/next/ack 26,46/18,62/33,85 мс, один изменённый файл
27,80/21,80/38,95 мс; процесс peak 60,39 MiB. Сеть, физический миллион ревизий и
TB transfer не включены. Артефакт .test-tmp/file-workspace-million.json;
tools/file_project_benchmark.py --files 1000000 --checkin-files 0.
Детальный контракт обновлён в канонической EN/RU Help → Project creation.

Classic SQL/FileUndo/client-transactions/project-creation: 26 тестов
(25 passed, 1 отдельный PostgreSQL-only skipped). Сборка Vue 0.112.49 успешна;
каноническая и опубликованная EN/RU Help совпадают.


SSE cleanup дополнительно проверен при отключении до первого пакета и ошибке
отправки заголовков (ASGI 2.3/2.4). Подписка удаляется в finally ответа даже
если генератор ещё не стартовал; повторная очистка идемпотентна. Список проверен
на двух настоящих веб-воркерах, включая отключение и graceful shutdown.


### 0.112.50 — непрерывное дерево: QML, hover и действия

Проверен текущий WorkspaceResultItem.qml ТХ и общий набор ItemSurface, DisclosureButton,
ItemQuickActions и ItemCountActionButton. Эталон снимается из изолированного Qt-контроллера
инструментом tools/capture_continuous_reference.py; версии исходников сохранены SHA-256.
Галерея обычного состояния, hover, pressed и selected: .screenshots/continuous-current/index.html.
Это проверка реального QML делегата, не интеграционный запуск всего пользовательского ТХ.

В вебе одиночный клик выбирает строку, стрелка/двойной клик раскрывают, Shift раскрывает
рекурсивно; превью является областью выбора. Ctrl/Cmd и Shift выбирают совместимых
соседей, правый клик сохраняет множественный выбор, средний открывает отдельную вкладку.
Одиночный выбор не добавляет лишнюю панель над деревом; bulk-панель остаётся для
нескольких объектов. При наведении на заголовок доступны Save/Open snapshot, у объекта
— меню родительских/дочерних связей; у task/note-кнопок — выбор процесса/конкретной задачи.
Новые действия используют существующие ObjectOperations, RelatedObjects, ObjectCheckin
и NotesPanel. Дополнительные сведения/ellipsis убраны с hover дерева, сохранены
в контекстном меню и других видах. Knowledge Base остаётся постоянным действием.

Исправлены цвета нулевых счётчиков и размеры badge общего AppButton; сохранены
100/38/32 px строки объектов/связей/процессов, 24 px отступы. Disclosure не получает
hover-фон/ripple. Отпускание hover контролов — 500 мс; открытое меню удерживает
контролы, прокрутка подавляет mouse hover. Заголовок имеет приоритет при нехватке места.
Versionless раскрывается непосредственно в версии; снапшот показывает native file_display
и repository_display, размер, версию/ревизию, автора, timestamp и метаданные.
Строки процессов следуют pipeline/builtin-процессам ТХ; subcontext не становится
дублирующей строкой процесса. Процесс включает subcontexts, но дочерние версии
конкретного снапшота фильтруются по точному context. Снапшот наследует цвет процесса. Родительские связи проходят существующий Schema/Search, с проверкой
наличия связи; произвольный search type не принимается. EN/RU Help обновлена.

Проверки: три Chromium-сценария continuous_interactions/result_tree_parity/result_views;
5 проверок cg.zip/file_presentation, 11 нативных QML-проверок ТХ. Временный сервер
и воркер завершаются finally; Windows spawn больше не повторяет модульный setup runner.
Repository Sync/Watch Folder/DCC исключены; браузер открывает файл через preview/download.
Перенос всего desktop drag/drop и настройка double-click-save не входят в эту проверку.


### 0.112.51 — массовая передача файловых проектов

Добавлен отдельный files worker, bounded manifests, streaming HTTP uploads/tar/Range,
докачка с локальным журналом, пакетные checksum и общий прогресс. Native API проверяет
права на каждом шаге, сохраняет hooks и атомарный submit. Classic не переключается;
files включается отдельной опцией. Квоты резервируются до allocation и освобождаются
после физического GC. Retention/quarantine/GC защищают историю и живые ссылки.
Непрерывные правки могут повторять GC marking; предел описан в EN/RU Help.

Новые реальные SQLite/HTTP-наборы: 1000 × 4 KiB — upload+submit 7,137 с,
загружены → подтверждённый submit 1,974 с,
staging+submit 1,425 с; 1004 файла / 756 MiB — upload+submit 12,012 с,
загружены → подтверждённый submit 1,904 с, download+Have 6,896 с,
peak общего client/server процесса 146,65 MiB. SHA-256 всех файлов совпали.
Цель <1 с пока не достигнута. Миллион synthetic catalog entries:
first/tail 1000 — 22,49/25,94 мс, sparse Have с одним изменением —
28,66 + 23,34 + 43,06 мс, peak 60,84 MiB. Это метаданные, не физический TB-test.

Проверки и протоколы: tests/test_file_transfer.py, tests/test_monitor.py,
tools/file_project_checks.py --postgres, tools/file_transfer_benchmark.py,
каноническая EN/RU Help → Project creation. GUI ТХ/ТС не подключён в этом блоке.

Проверки блока: 66 сценариев SQLite (64 passed, 2 PostgreSQL-only skipped),
17 успешных PostgreSQL-прогонов выбранных сценариев, 27 Classic/SQL/FileUndo/
client-transactions/project-creation/mappings (26 passed, 1 skipped),
перезапуск и остановка собственного files worker, admin configuration API и Chromium.
Vue 0.112.51 собрана; EN/RU Help совпадает с опубликованной копией.
Собственные PostgreSQL-контейнеры и test monitor PID отсутствуют.


### 0.112.52 — публикации и рекурсия непрерывного дерева

Publish-контексты выводятся сразу под объектом, перед связями и процессами,
тем же описателем файлов, который используется внутри процесса. При раскрытии
связи дерево исключает возврат к типу объекта среди предков; сама схема и меню
связей сохраняются. Первая связь объекта с собственным типом остаётся доступной.
Повторный объект-предок не вставляется в дочерний список.

Подписи select/category берутся из native SelectWdg и XML edit_definition.
Метаданные следуют порядку полей записи ТХ; вложенные объекты показывают description
и raw category, а встроенные процессы имеют подписи Icon, Attachment, Publish.
Пустое полное имя автора заменяется login; пустое описание снапшота — переводом
No description. Проверяемый сценарий: Robot Arm → publish → Texture → Brushed Metal,
включая восстановление после reload. Help обновлена на EN/RU.

Свидетельства: .screenshots/continuous-topology/ — Chromium и текущий неизменённый
WorkspaceItemModel/QML ТХ на одних native-записях импортированного cg.zip.
Запросы связей/counts, пути fixture repository и snapshots подаются из изолированного
проекта, без пользовательского подключения ТХ. Полный живой desktop и остальные
ветки проекта этим сравнением не проверены; полный pixel parity не заявлен.

Проверки 0.112.52: 35 существующих тестов модели/метаданных ТХ, 5 native
CG/file-presentation проверок ТС, Chromium topology/interactions/six-views.
Отдельная проверка границы страниц использует реальные записи с подменой
страницы ответа: offset считает все серверные строки, включая исключённого предка.
Сборка прошла; попутно невалидный JS octal escape в LocalFiles заменён
эквивалентным Unicode escape без изменения ключей IndexedDB. Собственный сервер
и multiprocessing workers завершены. PostgreSQL в этом проходе не проверялась.

### 0.112.53 — общие разделители и полосы прокрутки

Оформление перенесено из текущих Controls.SplitterHandle/ResizeGripVisual и
Controls.ScrollBar ТХ в общий frontend/src/controls/panelChrome.css. Разделители
редакторов, доков, Snapshot Browser и результатов используют короткую ручку
3 × 40 px с одинаковыми normal/hover/pressed/focus состояниями. Общий AppSplitter
заменяет range input между результатами и версиями; сохранённые проценты остаются
в состоянии раздела. Мобильный режим скрывает ручку и раскладывает обе панели
вертикально, оставляя шапку версий читаемой при небольшой высоте.

Chromium/Electron используют нативные scrollbar parts: постоянный gutter 12 px,
thumb 5/8 px, цвета и прозрачность текущей темы ТХ. Они общие для прокручиваемых
панелей, попапов, диалогов и редакторов, включая горизонтальную прокрутку.
Браузеры без WebKit scrollbar parts используют стандартный thin fallback;
совпадение геометрии hover в них не заявлено.

Проверка: frontend/tests/panel_chrome.mjs монтирует реальные AppSplitter,
ResultPresentation, SnapshotBrowser и DockWorkspace. Мышь, клавиатура и настоящий
touch проверяют изменение размера; scrollbar thumb перетаскивается в Chromium,
gutter остаётся неизменным. Проверены MD3/material5, light/dark, масштаб 200%,
360 px и восстановление настольного split ratio. Временные Vite/Chromium
закрываются в finally; флаг Playwright --hide-scrollbars отключён для проверки
настоящей полосы. Свежие снимки текущих Qt/QML controls и Chromium находятся в
.screenshots/panel-chrome-current. EN/RU Common controls обновлены.

Полный рабочий desktop ТХ и серверные сценарии не прогонялись: его компоненты
использованы без изменений как эталон. Firefox/Safari отдельно не проверялись.
Dev-стенд также показывает существующее предупреждение о лишних ticket/project
у HelpView, вызываемого из NotesPanel; это не runtime-ошибка нового оформления.

## File-project workspace clients

- `features/fileWorkspace/FileWorkspace.vue` is a lazy, project-scoped browser inspection/admin screen selected by project_mode=file_project. Its bounded command route dispatches the fixed native FileProjectCmd with ticket/project identity. Classic docks and queue retain their existing components.
- Desktop state belongs to Handler FileWorkspaceController; CommitWorkspaceView selects the separate QML screen by project type. Disk/SHA/network work runs in the existing commit worker pool; queued progress is throttled and generation-scoped. Reconciliation and resumable transfer journals live outside workspace roots.
- File pages cap at 200, native manifests at 1000, history at 1000 published revisions, text previews at 256 KiB. Native guards block mid-upload Submit and restore the entire original draft on cancellation/failure. Browser polls an active task page every two seconds and aborts monitoring on unmount.
- Full local scan/upload/Get latest/manual merged-file operations are desktop-only. Stream exposes catalogs, native changelist administration, conflict sides/ours/theirs, owner-scoped tasks, storage policy CAS and fenced GC. EN/RU Help describes these boundaries.

### 0.112.55 — общие выбор пользователя и календарь ТХ

UserComboBox использует текущий UserComboBox.qml: аватар 22 px в поле, аватар
32 px и строки 48 px в списке, группы, поиск, отметку выбранного пользователя
и общий попап 286 px. Обычные поля показывают стрелку, actionField сохраняет
компактный вид ТХ. TaskField и назначение копии задачи используют тот же контрол.
В UserPicker исправлен цвет подписи выбранной строки.

AppDateField переносит Controls.DateField.qml: попап 304 px с понедельника,
переключением месяцев, выбором дня, часами/минутами, Сегодня и Очистить.
Поля показывают локализованную дату, в фокусе доступен исходный текст.
Дата/время задачи сохраняет прежний формат; режим только даты применяется
в планировании, вехах и табеле. CalendarInputWdg форм записей и дублирования
использует этот же контрол. Прежние baseline/unchanged_value и value_suffix
RecordForm сохранены; неизменённые даты не теряют часовой пояс и микросекунды.
Время календаря не участвует в валидации окружающей формы как отдельное поле.

Проверка: frontend/tests/pickers.mjs монтирует реальные TaskHiddenDetails,
TaskField, RecordForm и общие controls. Проверены поиск/выбор, клавиатура,
тач, disabled/read-only, високосные даты и границы месяцев, обязательность
и ошибочный ввод, исходная точность и суффикс в перехваченном запросе EditCmd,
MD3/material5 light/dark, русский интерфейс 360 px и DPR 2. Временные
Vite/Chromium закрываются в finally. Снимки текущих QML controls и браузера
находятся в .screenshots/pickers-current; для Qt-снимков попапы показаны в
owner overlay вместо отдельного нативного окна. Common controls EN/RU обновлены.

Сохранение на рабочем сервере, полный desktop ТХ и Firefox/Safari не проверялись.
Дополнительный panel_chrome.mjs проходит проверки desktop/scrollbars, но падает
на прежнем ожидании мобильной .result-versions: текущий ResultPresentation.split
отключается при mobile. Этот отдельный экран в правке пикеров не изменялся.

File-project layout reuses the house compact icon controls, action menus, modal editors and splitters. Files occupy the main panel, History/Conflicts/Transfers occupy a resizable lower panel, and the narrow layout hides the tree until requested. Native command payloads and Classic routing are unchanged by the presentation change. GUI checks include actual menu activation and keyboard description editing.

### 0.112.64 — Гант ТХ и отдельный календарный док

TaskScheduleView заменён отдельными TaskGanttView и TaskCalendarView. task_calendar
зарегистрирован в docks.js, меню Tasks and reports, мобильном выборе панели
и сохранении раскладок. Calendar открывает док, не заменяет таблицу или Гант.
Один TaskManager владеет областью, запросами, черновиками и исходными ревизиями;
календарь получает его проекцию через Teleport в постоянный dock-task_calendar.
При открытии только календаря Tasks не показывается принудительно. Дата задаёт
тот же query.filters.day; явная очистка снимает фильтр. Входы по текущему проекту
и восстановление раскладок используют существующие контекстные guards.

Гант перенесён по свежим TaskGanttView.qml / TaskGanttProgressHandle.qml ТХ:
шапка 54 px, секции 28 px, группы 27 px, строки 50 px, полосы 27 px, ручки
дат 12 × 22 px, прогресса 18 × 22 px. Подписи остаются на месте, шкала
и шапка синхронизированы с учётом scrollbar gutter. Base day width 10–28 px,
zoom .15–5 и day width 2–80 px. Колесо над шапкой меняет масштаб под указателем,
Shift+колесо и перетаскивание пустой шкалы/средней кнопкой прокручивают время.
Обзор поддерживает drag и клавиатуру. DOM строк и вертикальных границ ограничен
видимой областью; 500 строк не создают 500 элементов расписания.

Перенос, обе ручки дат, создание дат на пустой строке и прогресс проходят через
существующий TaskScheduleCmd/stageSchedule. Правки не отправляют сохранение сами;
сохраняются время, описание и ревизии подготовленного плана. Escape, pointercancel
и потеря фокуса отменяют жест. Undo/Redo остаются в общем черновике. Без мыши
доступен редактор расписания, а прогресс поддерживает клавиатуру. Пакетные
действия, ресурсная группировка, рабочие дни, вехи, предупреждения и Load more
сохранены. Предметная секция черновика остаётся исходной до сохранения:
checked_records принимает строго boolean _ganttSectionScheduled, уже используемый
в исходном gantt_layout ТХ; непроверенные client DTO не получают прав записи.

Календарь повторяет шестинедельную сетку текущего TaskCalendarView.qml и compact
режим, счётчики, цветные точки статусов, сегодняшний день и вехи. Дополнительный
список событий Stream сохранён кнопкой Agenda. EN/RU Help и предпочтения обновлены:
Task Browser Initial view выбирает Table/Gantt, календарь управляется раскладкой доков.

Проверки: frontend/tests/gantt_calendar.mjs монтирует реальные TaskManager и
DockWorkspace на временном Vite/Chromium с перехваченным API. Проверены масштаб
под курсором, прокрутка, перенос/resize/create/progress, отмена, общий черновик
и ревизии, undo/redo, фильтр дня, отдельный док, capture layout, виртуализация
500 строк, MD3/material5 light/dark и touch mobile. Перехват prepare не выполняет
запись в пользовательскую БД. tests/test_task_schedule.py сравнивает расчёты
и преобразования с текущим ТХ, проверяет пределы DTO и исходную секцию черновика.
Свежие Qt/QML и Chromium снимки находятся в .screenshots/gantt-current.

Полный сценарий сохранения на рабочем сервере и Firefox/Safari не проверялись.
Стенд показывает прежнее предупреждение лишних ticket/project у HelpView из NotesPanel.


## Мобильный Менеджер задач по UX поиска (0.112.66)

При ширине до 700px полный Менеджер задач использует карточки и отдельный экран одной задачи.
Карточка показывает объект, процесс/контекст, статус, исполнителя, срок, прогресс и заметки.
Тап/свайп влево открывает поля задачи; кнопка Назад, свайп вправо и Back/Forward браузера
меняют экран, сохраняя прокрутку списка и подготовленный черновик. Чекбоксы выделяют задачи
для существующих пакетных действий. Прокрутка вниз скрывает строку поиска, вверх возвращает её.

MobilePage — общий владелец мобильного свайпа, анимации, прокрутки и шапки для MobileResults
и MobileTasks. API, права, исходные ревизии и Save/Discard остаются в TaskManager;
мобильные поля используют TaskWorkspaceEditor/TaskField и общие user/date controls.
После Save/Refresh открытая задача заново подготавливается; staged plans сохраняют исходную
ревизию. Смена ширины не изменяет выбранный настольный вид и не теряет черновики.
Календарь остаётся отдельной панелью. У текущего TH нет соответствующего экрана мобильной
навигации: этот UX намеренно следует основному мобильному поиску Stream.

Проверка mobile_tasks.mjs на временном Vite/RPC fixture: Chromium mobile 320px,
тапы и реальные touch-свайпы, группировка/выделение, scroll/Back/Forward, исходная ревизия,
Save без записи при вводе, возврат на десктоп и обратно, границы user/date picker,
MD3/Material5 light/dark и регрессия мобильного поиска. Снимки .screenshots/mobile-tasks-current.
Физические iOS/Android и запись в пользовательскую БД этой проверкой не покрыты.


## 0.112.68 — file-workspace basic interaction

The complete 16-topic backlog is retained in FILE_WORKSPACE_UI_PLAN.md, grouped
into three stages. The desktop owns local files; Stream owns browser inspection
and administration. Scoped selections, context menus, target pickers, real
drag/drop, independent work views, Head/Have/checkout state, column settings,
navigation and preference restoration use the existing controls and native API.
Exact-path sync and atomic published-revision restore preserve permissions,
triggers, immutable bytes, dirty local files and changelist rollback. Selection
snapshots are private and paged; whole-query mutation jobs remain a scale-stage
requirement. Explicit selections/loaded branches are bounded to 1000 entries.
EN/RU file_workspace Help is synchronized with Handler. Temporary-project QML,
Chromium, filesystem, failure-injection and native ACL tests provide evidence;
physical million-file/TB and packaged deployment acceptance remain separate.

## 0.112.69 — project mode survives connection notifications

Handler 0.6.0.32 resets its file workspace on the existing sign-out/server-switch
signal instead of every server-status notification. The full bootstrap ends with
an online notification; it and subsequent ping/reconnect notifications now retain
the server-defined project mode, workspace, selection and loaded QML dock.
Project switches still select the appropriate native/Classic presentation.
Stream already derives its mode from the project catalog independently of network
status; its Chromium regression now checks offline and a real ping without
remounting the file view or exposing Classic queue. No server ACL/API changes.
EN/RU file_workspace Help is included in the browser catalog and agrees with
Handler. Focused bootstrap/QML checks reproduce the old failure and pass after
the fix; the related QML/native/browser suite passed 22 checks on temporary data.
The previously recorded PySide6 shutdown ResourceWarning remains unresolved.

## 0.112.70 — bounded operation Log and expected sync conflicts

Handler 0.6.0.33 and Stream provide a compact bottom Log with operation timestamps,
results, paths where relevant, collapse/expand, copy/clear and explicit Debug Log
access. Records are limited to 1000 per project instance and contain summaries,
not per-file transfer callbacks or returned server rows. Worker/view refresh
snapshots cannot erase the journal. Classic components remain separate.
The shared FileTransferClient.download now returns state=blocked with reason=
local_modified_or_untracked, path and the existing task instead of raising for
this expected condition. No traceback is built, no local bytes are overwritten
and the Handler controller returns before Reconcile. SDK callers must inspect
state and resolve their local conflict before resuming the retained task; errors
in native API permissions, integrity checks and unexpected failures retain their
existing exceptions. Unexpected file-worker failures go to the operation journal
and full Debug Log diagnostics without a forced exception modal/stdout traceback.
Browser operations use the same journal semantics; local filesystem checks belong
to Handler. The final related SDK/QML/native/browser checks pass (48 checks;
one initial glyph regression corrected and its browser scenario rerun).
The existing PySide6 interpreter-shutdown ResourceWarning remains recorded.
Mass-transfer throughput was not measured for this UI/error-handling change.


## Настоящий док Инспектора задач (0.112.75)

В ТХ Task Inspector уже является панелью notes справа (docks_records.py/DockMenu.qml);
его host исправлять не потребовалось. В Stream прежний модальный путь был ошибкой:
App теперь содержит один общий NotesPanel с dockTarget=#dock-notes, который рендерит
section внутри DockWorkspace. Открытия из ResultPresentation, ConfiguredView, TaskManager,
активности и skey-ссылок проходят через общий injected openTaskInspector. Модальная форма
Notes остаётся отдельным явным выбором Appearance → Object notes.

Панель notes включена в реестр, меню Tasks and reports, мобильный выбор панели, вкладки,
плавающую геометрию, maximize/restore и capture/decode/account/per-search-tab layouts.
DockWorkspace владеет шапкой и геометрией; v-window применяется только к отдельному диалогу
Notes. При закрытии дока его экземпляр и черновики остаются смонтированными.

Поиск и активная строка TaskManager передают точного родителя, процесс и task search key.
Видимый desktop-инспектор следует выделению; на телефоне выбор не переключает панель
самовольно, Notes открывает её явно, Back возвращает в исходную панель.
Исходные проект/ticket/тип и callback saved сохраняются от вызвавшего экрана. Черновики
заметок и полей сохраняют контекст; task draft сохраняет исходную revision. Задержавшееся
чтение не заменяет текущую цель. Незавершённые правки заметки и подтверждения действий
защищены при смене цели; сохранение не подменено новым API. Видимая dock-панель получает
тихие обновления без требования фокуса внутри модального dialog.

Проверки: inspector_dock.mjs на изолированном Vite/RPC fixture проверяет одну section и
отсутствие модального Inspector, точные task/project, исходные revision/callback,
возврат черновика, смену выделения, guard/stale reads, float/stack/reload, MD3/Material5
light/dark, phone320 Back/Help и отдельное окно Notes. docks.mjs проверяет native notes
в capture/decode. Обновлены прежние браузерные callers/assertions, ожидавшие dialog.
Свежий неизменённый TH QML снят tools/capture_collaboration_reference.py в
.screenshots/collaboration-current; снимки Stream — .screenshots/inspector-dock-current.
Физические мобильные устройства и запись в пользовательскую БД этим fixture не проверены.

Дополнительно inspector_dock.mjs проверяет guarded-close Administration перед открытием
дока, повторное открытие последней точной задачи и failed-read/Retry: до успешного чтения
TaskInspector composer и send блокируются, чтобы не заменить task note_target родителем.
Этот guard относится к комбинированному чтению Stream; контроллеры TH и их host не менялись.

## Мобильная Commit Queue и диагностика браузера

Мобильная очередь использует существующий CommitQueue и док под основной шапкой приложения.
Начальный экран содержит компактные строки файлов, состояние, ошибки и нижнюю отправку.
Файловая панель, описание и параметры раскрываются по строке или Check-in details;
дубликаты и общие ошибки видимы независимо от раскрытия. Очистка, автоочистка и порядок
сохранены в меню. Состояния Missing files/Result unknown, защитные подтверждения,
проверка плана и native check-in не заменены новым мобильным механизмом.

DebugLog отправляет аутентифицированные ошибки API/JS/console.error через штатный API log
в sthpw/debug_log независимо от локальных фильтров. Контекст приходит из App session/project,
для запроса используется его исходный контекст. Секреты маскируются; серверные поля сообщения,
стека и деталей ограничены 8192 символами каждое. Прямая отправка имеет таймаут 3 секунды,
не повторяется и не проходит через собственный API logger. Update polling исключён;
выход очищает контекст. Общий query технических журналов остаётся защищённым.

В рабочей SQLite exception_log #666 найден WinError 1314 из DiscussionAddNoteCmd при
обновлении versionless через symlink. В cg_test значение config/prod_setting versionless_mode
изменено через native API с symlink на hardlink, с записью диагностики; старые файлы
не мигрировались. Настройка остаётся явной: нет скрытого fallback symlink → copy.

Проверки: debug_log_data.mjs (секреты, выключенные локальные уровни, console.error,
выход, отсутствие рекурсии); mobile_commit_queue.mjs на временном SQLite CG-проекте
(320/390 px, PNG upload, сбой HTTP и Retry, байты файла, сохранение предыдущей версии,
запись ошибки в SQLite); result_browser.py проверяет native PNG-вложение заметки и
os.path.samefile для main/web/icon versionless. test_browser_checkin/test_user_diagnostics:
13 проверок; desktop test_drop_plate_commit_queue_in_chromium прошёл.
Справка дополнена в EN/RU Commit Queue, Debug Log и Check-in Options.
Все тестовые серверы и воркеры останавливаются в finally; физический телефон не проверен.

Мобильное изображение SObject теперь заполняет левую часть карточки и прямоугольной шапки:
CSS mask-gradient затухает вправо, за текстом и действиями. Используется тот же ItemPreview
и его исходная картинка, без второго DOM-превью, дополнительных запросов или blur-слоёв.
При отсутствии/ошибке картинки CSS возвращает прежние инициалы. Картинка не перехватывает
тапы; полоса типа сущности сохраняется. Это отдельное оформление Stream для телефона,
у TH нет соответствующего мобильного экрана. Desktop ItemPreview не менялся.
mobile_preview.mjs проверяет native PNG, dark/light 320/390, геометрию фона и прямоугольной
шапки, тап по картинке, меню/Back, ошибку загрузки и desktop clipping. Снимки в
.screenshots/mobile-items/index.html; описание в EN/RU Mobile application.

## Остановка запросов при истёкшей сессии (0.112.76)

При JSON-ошибке `authentication_failed` ServerUpdates останавливает опрос и закрывает существующий общий доступ к фоновым запросам до события `session-expired`. Ожидающие чтения отменяются; focus/online/таймер не повторяют запрос со старым тикетом. Новый вход через штатное создание сессии возобновляет обновления. Изолированная браузерная проверка: `frontend/tests/session_expiry.mjs`.

В ТХ 0.6.0.38 устранён отдельный цикл XML-RPC: сигнал Debug Log об истёкшем тикете больше не ставит чтение чатов в очередь, когда `authentication_required` уже установлен. Общий опрос и чтение истории также ждут авторизации; наличие старого тикета и объектов логинов не означает действующую сессию. Проверены 81 тест контроллеров чатов/обновлений, включая настоящий сигнал Debug Log и сохранение черновика. Локальный JSONL эпизода около 00:51 не найден; срок/причина недействительности конкретного тикета не установлены. Серверный формат XML-RPC и проверка прав сохранены.

## Компактный футер мобильного инспектора

На телефоне TaskInspectorHeader и note-composer образуют единую нижнюю панель без отдельного
заголовка дока. Объект, процесс, выбор задачи, Back, Help и ввод остаются доступными; раскрытие
полей, refresh и учёт времени находятся в Task actions. Timeline использует остальную высоту.
Главная шапка приложения и desktop Inspector не менялись. Back испускается NotesPanel и
возвращает исходную панель через существующий DockWorkspace.show; черновики и guards сохранены.
При отсутствии объекта/ошибке чтения есть нижняя навигация. Отдельные мобильные Notes используют
собственный Back вместо автоматических оконных контролов. Очистка tooltip при responsive
удалении teleported WindowControls сделана идемпотентной.
Проверены native mobile_inspector_page.mjs и mobile_refinements.mjs (320/390/640, footer до 96px,
процесс, точная задача, Help/Back, сохранение черновика), а также inspector_dock.mjs с desktop,
float/stack/restore, guards/read errors и дополнительным Notes. Help обновлена в EN/RU.
У ТХ нет соответствующего мобильного экрана; физический телефон не проверен.

Дополнительно прошёл native test_task_manager_in_chromium: создание и сохранение задачи,
мобильный draft, раскрытие/сворачивание Inspector, Calendar/Gantt, milestones и возврат desktop.

## Облако тегов по текущему ТХ (0.112.77)

Свежий эталон снят из текущих TagCloudPopup.qml и QuickFilterChip.qml через изолированную Search workspace фикстуру: `.screenshots/tag-cloud-current/th-tags.png`, геометрия/веса и хеш исходника — `reference.json`. Сам ТХ не менялся: его 11 существующих QML-проверок облака прошли.

В ТС стили меню больше не снимают рамку, форму и font-weight общего quick-filter-chip. Частотный шрифт, округление высоты 32–44px, выравнивание верхних краёв, selectedText, ограничение ширины 260px и ellipsis совпадают с правилами ТХ. Поверхность шириной 440px имеет высоту восемь theme control heights, отступы 12px, компактные кнопки 28px и один прокручиваемый viewport с зарезервированным gutter. Shared AppTextField заменил сырой input с дополнительным контуром фокуса; поиск получает фокус сразу, до ответа каталога. Локальные enter/exit transitions выключены как в источнике.

Текущий каталог переиспользуется при повторном открытии; явное обновление всегда читает сервер, ошибка сохраняет прежние чипы. Контекст ticket/project/Search Type/tab сбрасывает каталог и исключает поздний ответ. Сохранены выбор OR, ALL/reset, независимый локальный поиск и виртуальные строки с клавиатурным переходом за пределы viewport. Существующий integration test_tag_cloud сценарий позднего ответа теперь явно вызывает Reload вместо ожидания запроса при cached reopen.

Изолированный `frontend/tests/tag_cloud_parity.mjs` проверяет геометрию и стили настоящего компонента, локальный поиск, выбор/сброс, cached reopen, ошибки/поздние ответы, 1500 тегов, scrollbar gutter, длинные названия, Tab/Shift navigation, три темы, RU и touch при 320px. Скриншоты ТС — `ts-tags.png`, `ts-tags-ru.png`, `ts-tags-mobile.png`; обновлена существующая Help/Search EN/RU. Backend и пользовательская БД не менялись; физический телефон и реальный query с выбранными тегами в этом проходе не проверялись.

## Единая мобильная панель поиска

В поиске на телефоне WorkspaceTabs показывает одну строку высотой 40px: название активной
вкладки, поиск и меню действий. Название открывает штатный AppMenu с открытыми видами,
вкладками, созданием, закрытием и историей восстановления. Desktop tablist остаётся в том же
компоненте и возвращается при изменении ширины. Состояние вкладок и URL используют прежний
Workspace; отдельного мобильного хранилища нет.

WorkspaceSearch раскрывается по кнопке с анимацией высоты/прозрачности общей строки.
Enter выполняет штатный запрос и скрывает поле; Escape/Close сохраняет текст. Переход в другую
вкладку сбрасывает только видимость поля. Быстрые фильтры, сортировка/группировка, saved searches,
refresh, теги и создание доступны в Result actions, без дублирующих кнопок сверху и снизу.
Меню используют top-layer overlay, поэтому свёрнутый search-header не обрезает фильтры/теги.
Главная шапка приложения сохраняется.

Native mobile_search_toolbar.mjs проверяет 320/390px, реальный query и field filter,
закрытие/восстановление вкладки с текстом, Escape, Tags, Saved searches, RU, отсутствие
горизонтального overflow и переключение/создание desktop-вкладок после изменения ширины.
mobile_refinements.mjs дополнительно проверяет сохранение прокрутки при скрытии панели,
контексты задач/заметок, preview/upload и native versionless. Оба прошли на временном SQLite
CG-проекте; сервер и multiprocessing workers остановлены в finally. Справка Mobile/Search
обновлена в EN/RU, снимки добавлены в .screenshots/mobile-items/index.html.

## Кнопка быстрых фильтров по текущему ТХ (0.112.78)

Свежий эталон SearchQuickFilterPopup.qml снят через настоящий SearchWorkspaceView.qml и его изолированный контроллер: `.screenshots/quick-filters-current/th-quick-filters.png`, `reference.json` с хешем источника и составом групп. Сам ТХ не менялся: его 11 QML-тестов popup прошли.

SearchQuickFilters.vue заменяет прежнюю форму поле/значение в рабочей строке поиска. Группы categorical fields, процессов и статусов используют круглые общие quick-filter-chip с ALL, цветами workflow и немедленным применением через App.applyQuickFilters. Счётчик отражает выбранные значения; сброс группы/всего выбора и восстановление общих настроек используют состояние той же вкладки. Выбранные значения вне текущего каталога остаются снимаемыми. Пользователи выбираются общим UserPicker с поиском, группами, текущим пользователем и совместным выбором My Tasks/других исполнителей; каталог identities берётся существующим user-profile/read. Цвета процессов/статусов дополнены в нативном quick_groups без изменения запроса или прав.

Каталог текущего контекста переиспользуется при открытии и передаётся существующему QuickFilterEditor при Edit. Проект, тип, scope и вкладка инвалидируют чтение. Редактор не принимает поздний ответ в новый контекст; обычный пользователь не раскрывает группы/опции, скрытые серверной конфигурацией. Root.menuToggled координирует selector, assignee popup и прочие меню поиска. Дополнительный фильтр Stream по полю и Show retired сохранён в раскрываемом FieldFilter; Administration использует тот же presenter. Существующий search_suggestions.mjs адаптирован к новому пути.

QuickFilterOptions.vue измеряет wrapping через общий packTagRows, включая иконки/цветовые маркеры, и создаёт только строки текущего viewport. Один владелец прокрутки оставляет gutter; клавиатура прокручивает к не созданным строкам. AppMenu.maxHeight удерживает предел 400px и в мобильном top-layer меню; остальные меню без этого prop сохраняют свой контракт. Стили общих чипов и UserPicker защищены от generic menu styles. Help/Search EN/RU обновлена.

Изолированный `frontend/tests/quick_filter_popup.mjs` проверяет реальные Vue views и App.applyQuickFilters: выбор/сброс/defaults, сохранение прочих слоёв запроса, кеш, UserPicker, Edit, отсутствие серверно скрытых групп, фильтр по полю, устаревшие значения и ответы, виртуальные 20×64 options, Tab/Shift+Tab, RU, три темы и touch 320px. `tests/test_search_configuration.py` проверяет workflow colours, нативную SQLite query и совместный related-task фильтр process/My Tasks без смешивания разных задач. Повторно прошёл tag_cloud_parity.mjs. Скриншоты ТС находятся рядом с эталоном. Production DB, PostgreSQL в этом проходе и физический телефон не проверялись; работающий пользовательский сервер не перезапускался.


## Общая справка всех экранов (0.112.79)

Ориентир: SearchWorkspaceView.qml текущего TH вызывает windowModel.open_help("search") из
обычной кнопки и компактного меню. В Stream App.vue владеет единственным HelpView и
предоставляет openHelp через существующий provide/inject. Поиск, лента активности,
создание проекта, Sidebar Editor, Duplicate, полка/редактор скриптов, Messages и
Notes/Task Inspector открывают полный каталог на соответствующей статье. Обработчики
help доков, Configuration, файлов и очереди по-прежнему направлены в это же окно.
Локальные help-dialog, встроенные переключаемые подсказки и экземпляры HelpView внутри
Messages/Notes удалены. Контекст и несохранённые черновики исходного окна сохраняются.
Документация API остаётся отдельной явно названной ссылкой с иконкой книги; индикатор
ошибки полки использует warning и сохраняет переход в редактор.

Пояснения редактора и полки скриптов сохранены в существующих EN/RU статьях. В каталог
добавлены Activity Feed и Mobile guide: прежняя кнопка Mobile guide ссылалась на
несуществующий id mobile. Overview описывает общее окно и возврат к исходному экрану.

Проверки: shared_help.mjs — реальные кнопки восьми экранов и панели CodeEditor,
один переиспользуемый HelpView, весь каталог/статьи, доступность при ошибке Duplicate,
сохранение черновика проекта, EN/RU, поиск и переход Mobile guide на 320 px, Escape.
inspector_dock.mjs использует один HelpView корня и проверяет мобильные Help/возврат,
черновики и исходные save callbacks. Все запросы выполняются на изолированных fixtures,
пользовательская БД и запущенные TH/Stream не меняются. Снимок:
.screenshots/shared-help-current/ts-shared-help-mobile.png. TH использует общий Help
уже сейчас; его код в этой правке не менялся. Физический телефон не проверялся.


## Переводы интерфейса по словарю текущего TH (0.112.80)

Ориентир: thlib/ui/localization.py, thlib/ui/translations/ru.json и
thlib/ui/qml/controls/Button.qml текущего Handler. Совпадающий английский исходный
текст в Stream использует точный русский перевод TH: синхронизированы 2025 общих
ключей, изменены 692 отличавшиеся формулировки. В частности Search Type → Серч-тайп,
Task Manager → Диспетчер задач, Task Inspector → Инспектор задачи, Appearance →
Внешний вид, Workflow → Воркфлоу, Snapshot → Снапшот. Специальные сообщения Stream
сохраняют собственные ключи; английский исходный текст остаётся fallback. Форматы
плейсхолдеров сверены; значения имени проекта, процесса и других серверных данных
подставляются без перевода. Отдельные Markdown-статьи не являются словарём UI.

AppButton теперь реализует уже использовавшийся в callers translateLabel=false:
исходное серверное имя сохраняется в тексте, aria-label и резервной подсказке
иконки. Раньше prop отсутствовал и имена, совпадающие с ключом словаря, могли
переводиться даже при явном отключении. Использованы существующие контракт и
проверки AppCheckbox/AppSelect; новый механизм локализации не добавлялся.

Проверки: localization.mjs сравнивает все общие ключи с текущим соседним Handler,
валидирует непустые переводы/плейсхолдеры и на реальных Vue controls проверяет
EN/RU без пересоздания состояния, английский fallback, сохранение черновика,
имени объекта/процесса, текста/ARIA/tooltip кнопки и исходных опций select.
Снимок: .screenshots/localization-current/ts-handler-translations.png.
Фикстуры локализованных кнопок обновлены на формулировки TH; локализованные
заголовки статей остаются независимыми. Messages test ожидает общее окно Help,
как после 0.112.79. TH в этой правке является эталоном и не изменяется.

## Сужающийся край и плавное превью объекта

MobileResults заменяет rail собжект-карточки цельным левым краем: border-left 2px
с унаследованным радиусом поверхности и нулевыми border-top/bottom. Разница внешней
и внутренней дуги плавно сужает край к нулю на углах; отдельных горизонтальных частей
и маски, оставлявшей щель рядом с контуром, больше нет. Превью занимает
ту же область с картинкой и без неё: исходный ItemPreview используется один раз,
CSS mask затухает вправо, ::after с backdrop-filter и gradient mask плавно добавляет
размытие. Fallback акронима имеет цветовой gradient без круговой обрезки; ошибка
картинки не меняет геометрию. Desktop и прямоугольная мобильная шапка сохраняют форму.
У текущего TH ItemPreview/ItemSurface нет такого мобильного сценария.
Native mobile_preview.mjs проверяет dark/light 320/390, край 2px с нулевыми концами
и совпадающими радиусами, gradient/blur,
единственный img, отсутствующую картинку и её fallback, тапы, шапку и desktop.
mobile_refinements.mjs проверяет переходы/прокрутку и контексты задач/заметок.
Справка Mobile EN/RU и галерея mobile-items обновлены; тестовые процессы остановлены.

Центр исходной картинки и акронима привязан к прежнему 42px превью: 33px от левого
края карточки и 57px в шапке с Back. Широкая область gradient/blur не определяет
фокус изображения. mobile_preview.mjs дополнительно проверяет оба центра и вертикальное
центрирование на 320/390px; для desktop эти мобильные правила не действуют.

## Выбор файлов в мобильном просмотре

FilePreviewContent использует общий AppMenu вместо текстового AppSelect: строки AppButton
с ItemPreview (иконка документа), исходным именем, расширением, prettySize и типом файла.
menuitemradio/aria-checked отмечает текущий файл. Длинные имена сокращаются; top-layer меню
ограничено viewport и прокручивается вертикально. Выбор вызывает прежний selectFile:
таймауты/ошибки, защита от позднего ответа и освобождение Blob URL сохраняются.
Общий компонент обслуживает отдельный FilePreview и встроенный MobileResults; desktop
и сценарий единственного файла не менялись. У TH нет соответствующего мобильного выбора.
Native mobile_refinements.mjs прошёл с выбором вложения в versionless и физической версии.
test_mobile_objects_in_chromium прошёл: 12 файлов, длинное имя, иконки/размеры/галочка,
320/360px без горизонтальной прокрутки, Escape, поздний ответ, desktop возврат и
связанные операции объекта. Справка Mobile EN/RU и галерея обновлены.


## Типы окон, диалогов и доков по текущему TH (0.112.84)

Перечень всех существующих dialog/component-dialog ТС проверен по
thlib/ui/workspace_models/windows.py (_defaults, show_window/show_child_window/close_window),
qml/FloatingWindow.qml, qml/controls/Dialog.qml, вложенным диалогам соответствующих
экранов и workspace_models/docks_records.py. Не переносились исключённые Repo Sync,
Watch Folders, DCC, обновлятор desktop-программы или отсутствующие новые предметные экраны.

Рабочие utility windows используют v-window={type:'window'} и нативный show,
модальные рабочие окна — showModal и общий v-window, короткие подтверждения и
локальные формы — themed dialog без рамки рабочего окна. Немодальные popup, которые
явно такие в TH (Script Editor confirmations, Forward messages, File comparison),
используют type:'popup' без кнопок геометрии. Справка остаётся единственным общим
HelpView приложения и теперь немодальна, как FloatingWindow(help) в Handler.

window.js сохраняет imperative refs, guarded cancel/close и контекст владельца.
Немодальное окно использует manual popover в top layer без scrim. При открытии из
блокирующего окна оно становится его DOM-потомком, чтобы native inert не запрещал
ввод; закрытие владельца закрывает дочернее представление, сохраняя данные компонента.
Из обычного немодального экрана utility windows открываются независимо. Повторное
show поднимает существующее окно и возвращает его из свёрнутого состояния. Escape
обрабатывается только фокусированным окном и сохраняет cancel.prevent/dirty guards.
Маршруты rich links и Commit Queue проверяют dialog:modal, а не любое открытое окно.

Общие WindowControls содержат перемещение, resize, maximize/restore и, для utility
windows, minimize/restore. В браузере minimize сворачивает содержимое до заголовка
на текущем месте; системная панель задач и DWM-рамка принадлежат desktop TH и не
создаются страницей. На телефоне рабочие окна используют прежний полный экран/Back;
короткие подтверждения сохраняют собственный компактный вид. Экраны, которых нет
как отдельного окна в TH, используют соответствующий общий тип; их работающие
возможности сохраняются.

Табель, Work Reports и Labor Cost выделены в timesheet/work_reports/cost_reports:
три экземпляра существующего Timesheet с независимыми режимами, недельными фильтрами,
проектами и черновиками. Task Inspector сохраняет свой отдельный Log time presenter;
его переходы к недельному табелю/отчётам открывают общие доки с захваченным проектом.
Labor Cost читает прежний WorkHoursCmd и не меняет финансовые проверки сервера.
Смена проекта не уничтожает черновик: пользователь сначала сохраняет/отменяет правку.

Новые доки и остальные существующие панели используют _default_stack_target TH:
правые панели группируются с notes, Drop Plate — с tasks, Commit Queue — с results.
Правило применяется при первом размещении отсутствующей панели; сохранённые
пользовательские положение, floating, табы и split ratios не сбрасываются.

Проверки: window_types.mjs сверяет 19 прямых соответствий реестра Handler и проверяет
реальные modeless/owned/modal состояния, доступность основного окна, порядок окон,
guarded Escape, minimize/restore/maximize/move, обычный popup без WindowControls,
три независимых дока, read-only команды и сохранение черновика при смене проекта,
float и touch Back на 320px. shared_help.mjs: восемь настоящих экранов, общий каталог,
EN/RU, source draft и Escape; inspector_dock.mjs: dock/float/restore, guards, callbacks,
темы и phone Back; gantt_calendar.mjs: отдельный календарь, Гант, ревизии, resize,
undo/redo, виртуализация и mobile; docks.mjs и localization.mjs прошли. Сборка Vite
прошла. Live БД/сервер/TH-клиент не менялись. Физический телефон не проверялся.
Снимок: .screenshots/window-types-current/ts-modeless-help.png.

### Полный перечень проверенных представлений ТС

window = немодальное рабочее окно; dialog = блокирующее рабочее окно с рамкой;
popup = короткая модальная форма/подтверждение; popup nonmodal = немодальный popup.
Для динамических presenters тип выбирается из роли/режима, а не из названия статьи.

| Файл / ref | Тип после сверки |
| --- | --- |
| App.vue / navigation | навигационный popup |
| App.vue / configurationDialog | window |
| App.vue / administrationDialog | dialog |
| App.vue / sidebarSearchDialog | dialog |
| App.vue / details | window |
| controls/AppMenu.vue / panelElement | popup |
| controls/ColorPicker.vue / dialog | popup |
| controls/IconPicker.vue / dialog | popup |
| features/activity/ActivityFeed.vue / dialog | window |
| features/activity/SystemActivity.vue / dialog | window |
| features/administration/ProcessRules.vue / dialog | dialog |
| features/administration/ProcessRules.vue / object | window |
| features/administration/SchemaEditor.vue / creationDialog | dialog |
| features/administration/SchemaTypeDeletion.vue / dialog | popup |
| features/administration/SidebarEditor.vue / groupDialog | dialog |
| features/administration/WorkflowEditor.vue / dialog | dialog / inline |
| features/checkin/CommitQueue.vue / dialog | window / dock |
| features/checkin/CommitQueue.vue / namingDialog | window |
| features/checkin/CommitQueue.vue / previewsDialog | popup |
| features/checkin/DropPlate.vue / templatesDialog | window |
| features/checkin/IngestFiles.vue / dialog | window |
| features/checkin/IngestFiles.vue / deleteDialog | popup |
| features/checkin/ObjectCheckin.vue / dialog | popup |
| features/configuration/Configuration.vue / repositoryEditor | window |
| features/configuration/Configuration.vue / confirmClose | popup |
| features/configuration/Configuration.vue / confirmClear | popup |
| features/debug/DebugLog.vue / dialog | window |
| features/debug/UiPerformance.vue / dialog | window |
| features/fileWorkspace/FileWorkspace.vue / reviewDialog | popup |
| features/fileWorkspace/FileWorkspace.vue / shelfDialog | popup |
| features/fileWorkspace/FileWorkspace.vue / targetDialog | popup |
| features/fileWorkspace/FileWorkspace.vue / columnsDialog | popup |
| features/fileWorkspace/FileWorkspace.vue / tabEditor | popup |
| features/fileWorkspace/FileWorkspace.vue / comparisonDialog | popup nonmodal |
| features/fileWorkspace/FileWorkspace.vue / editor | popup |
| features/fileWorkspace/FileWorkspace.vue / setupDialog | popup |
| features/fileWorkspace/FileWorkspace.vue / storageDialog | popup |
| features/help/HelpView.vue / dialog | window |
| features/interface/WidgetConfiguration.vue / dialog | dialog |
| features/knowledge/KnowledgeBase.vue / confirmation | popup |
| features/knowledge/KnowledgeBase.vue / deletion | popup |
| features/knowledge/KnowledgeBase.vue / moveDialog | popup |
| features/knowledge/KnowledgeEditor.vue / insertion | popup |
| features/messages/MessagesView.vue / dialog | window |
| features/messages/MessagesView.vue / editor | popup nonmodal (forward) / popup modal |
| features/objects/DuplicateSObject.vue / dialog | window |
| features/objects/FilePreview.vue / dialog | window |
| features/objects/NotesPanel.vue / dialog | window / dock |
| features/objects/ObjectAction.vue / dialog | dialog |
| features/objects/RecordForm.vue / dialog | window (sObject) / dialog (task) |
| features/objects/RelatedObjects.vue / dialog | window |
| features/objects/RelatedObjects.vue / details | window |
| features/objects/TimeEntryPanel.vue / dialog | window / dock |
| features/projects/ProjectCreation.vue / dialog | dialog |
| features/projects/ProjectTemplates.vue / dialog | dialog |
| features/scripts/ScriptEditor.vue / dialog | window |
| features/scripts/ScriptEditor.vue / confirmation | popup nonmodal |
| features/scripts/ScriptEditor.vue / historyDialog | popup nonmodal |
| features/scripts/ScriptShelf.vue / dialog | window |
| features/scripts/ScriptShelf.vue / confirmation | popup |
| features/scripts/ScriptShelf.vue / outputDialog | window |
| features/tasks/MilestonePanel.vue / dialog | window |
| features/tasks/TaskManager.vue / dialog | window / dock |
| features/tasks/TaskManager.vue / scheduleDialog | popup |
| features/tasks/TaskManager.vue / editor | popup |
| features/tasks/TaskManager.vue / deleteDialog | popup |
| features/tasks/TaskManager.vue / rebaseDialog | popup |
| features/users/UserProfile.vue / dialog | window |
| features/users/UserProfile.vue / editor | popup |
| features/workspace/DockWorkspace.vue / nameDialog | popup |
| features/workspace/DockWorkspace.vue / deleteDialog | popup |
| features/workspace/QuickFilterEditor.vue / dialog | dialog |
| features/workspace/ResultPresentation.vue / details | window |
| features/workspace/SearchLibrary.vue / dialog | dialog |
| features/workspace/SearchLibrary.vue / nameDialog | popup |

Всего 75 объявлений; отдельные inline-доки Snapshot/Description/Knowledge/Drop Plate/Files проверены по хостам App/DockWorkspace, их content не превращается в dialog.


Проверка безопасности немодального контекста: Script Shelf захватывает исходную
вкладку, проект/ticket и ревизию редактора. Смена вкладки не перенаправляет Save/Assign;
смена проекта блокирует запись и сохраняет черновик до закрытия/возврата. Повторное
open поднимает окно без selectNow/reset; canLeave включён в явный Sign out. Ingest
Files сохраняет выбранные файлы и захваченные parent/branch/project при смене основного
проекта; повторное open не меняет цель уже открытого окна. Смена ticket по-прежнему
очищает авторизованный контекст. window_types.mjs проверяет настоящее сохранение
шелфа только в API-fixture (исходные tab_a/revision), отказ от потери черновика и
сохранение исходного проекта/родителя/файлов ингеста. Никакие пользовательские
проекты или скрипты этим тестом не изменяются.

## Клики и заголовки доков (0.112.85)

Общие AppButton и summary AppMenu захватывают мышь до native pointerup: сдвиг
менее 10px за край кнопки сохраняет один native click. При большем движении
захват освобождается для обычной отмены/перетаскивания; touch, keyboard и
disabled не заменены программной отправкой click. Порог сверён с TH
ActivationHandler.qml (TapHandler.DragThreshold) и существующим переносом вкладок.

Серая вертикальная полоса в шапке была вторым скроллбаром внешнего контейнера:
вкладки 34px вместе с обычной горизонтальной полосой не помещались в 36px.
Внешний контейнер теперь только обрезает, внутренний сохраняет горизонтальную
прокрутку с компактной полосой 2px. Ripple clip исключён из измерения подписей
вкладок. Обводки focus/focus-within отключены по явному запросу пользователя;
клавиатурные обработчики, selection/active markers и focus background сохранены.

Плавающая панель переносится за свободный заголовок (float-move), без изменения
дерева доков и без зон стыковки. Кнопки, меню, вкладки и грип не запускают этот
жест. Грип сохраняет docking/move с open/closed hand cursor. Escape, отмена
указателя и потеря фокуса восстанавливают прежнее положение. Закреплённая панель
по-прежнему переносится только грипом. Floating Results тоже получает заголовок.

Видимость Commit Queue не унифицирована между Search tabs: это соответствует
TH controllers/navigation.py _capture_current_workspace_layout /
_apply_tab_workspace_layout и docks_records.py capture_layout, сохраняющим
все панели в отдельной раскладке вкладки. Содержимое очереди не зависит от
того, видна ли её панель. Это поведение оставлено по условию пользователя.

button_activation.mjs проверяет настоящие pointerdown/move/up по координатам,
включённые анимации, 4px сдвиг за край (до исправления терял click), отмену
дальнего движения, mouse/keyboard/touch, native disabled, перенос вкладок,
сгруппированные доки, перенос floating title и Escape, отсутствие вертикального
скроллбара и обводок, сохранение видимости Queue и неактивные немодальные окна.
Все API fixture; рабочий сервер и пользовательская БД не затронуты.

## Мобильный UI: комплект правок 2026-10-13

Task Manager использует панель 40px, поиск по кнопке и Select all tasks в существующем
меню. Акцент карточки — 1px. На странице полей убраны два дублирующих действия и
пояснение про Save; действия остаются в меню. Размер 42px ItemPreview ограничен
аватаром карточки/шапки и не влияет на UserComboBox: исполнители/руководители сохраняют
круг 22px. Inspector контекст и Back возвращены наверх под главную шапку, ввод остаётся внизу.

TaskManager.load(true) владеет отдельным backgroundRequest, привязанным к request ID.
Фон не включает busy/loading, не сбрасывает выделение/подготовленные поля и не публикует
неизменившийся result/catalog. Новые события во время чтения объединяются в один следующий
запрос. Новая операция инвалидирует старый ответ; появившийся редактор/черновик запрещает
применять фоновое чтение. Проверены стабильная DOM-геометрия, реальное изменение счётчика,
сохранение исходной ревизии и смена контекста. Нового таймера опроса не добавлено.

NotificationStack фильтрует обычный Server operation completed только на телефоне:
история не удаляется, desktop, сообщения, ошибки и предупреждения сохранены. Вкладки
имеют фиксированное мягкое скругление; меню/стрелка связи стоят по одной оси. Превью
собжекта занимает полную высоту без внутренних верхнего/нижнего отступов.

ObjectCheckin: мобильный Back вызывает прежний close/discard guard; тело формы прокручивается,
Cancel/Add to Commit Queue закреплены внизу. Сохранение имён — один ряд, clipboard — компактная
кнопка. Пустой контекст передаётся в очередь как выбранный process, поэтому не становится
preview-checkin; явный context и контекст существующей ревизии/append сохраняются.
FilePreviewContent сохраняет native loadFile/download и переносит действия в footer
MobilePage через DOM target; standalone viewer использует тот же нижний ряд. Описание
следует сразу за media/text. Desktop-владелец и защита поздних Blob-ответов не менялись.

Прошли mobile_tasks.mjs (две темы, draft, фон/объединение событий), native
test_task_manager_in_chromium и test_task_manager_context_in_chromium;
mobile_refinements, mobile_inspector_page, mobile_layout, mobile_search_toolbar,
mobile_preview на временном SQLite CG-проекте; native mobile_commit_queue с настоящим
PNG, Retry, прежней физической версией и hard-linked versionless; общий viewer в
test_mobile_objects_in_chromium. Help обновлена EN/RU, свежие снимки — mobile-items/index.html.
У Handler нет соответствующей мобильной компоновки; native команды и desktop сохранены.
Физический телефон не проверялся; все собственные тестовые процессы остановлены.

## Компоновка уведомлений по текущему TH (0.112.86)

NotificationsView.qml использует ColumnLayout с тремя строками, а общий CSS
ActivityFeed переводил toolbar SystemActivity в row wrap: пояснение и фильтры
попадали в одну строку, фильтры не заполняли ширину, Check-in переносился.
SystemActivity теперь сохраняет column nowrap, gap 8px и полную ширину сегментов.
При сужении не наследует снятие padding/background/border от мобильной ленты.
AppSegmentedButton сохраняет иконку 15px и однострочную подпись с elide, как
общий SegmentedButton.qml; остальным фильтрам не добавлены локальные копии.

Свежий offscreen QML NotificationsView снят 2026-10-13 с текущим TH, официальными
icon fonts и системным Segoe UI. .screenshots/notifications-current/th-geometry.json
повторно подтвердил прежний эталон: margin 12px, внутренний inset 10px, toolbar
124px на desktop/759px и 140px на 320/360px, filters 36px. PNG Qt и Chromium
лежат рядом. notifications_layout.mjs сравнивает геометрию эталона, три строки,
EN/RU без переноса сегментов, mobile overflow, keyboard filters, Clear history
и доступ к workspace из немодального окна. Fixture не читает/пишет рабочую БД.

Browser title bar остаётся общим WindowControls; нативная Windows/DWM рамка TH
не воспроизводится offscreen или внутри браузерной вкладки. Состав четырёх
существующих Stream-групп сохранён: отдельного клиента Repository Sync браузер
не реализует, поэтому дополнительная пустая группа не добавлена.

При переходе desktop → phone DockWorkspace выбирает среди реально показанных
настольных панелей: учитывает активную вкладку стека, floating и maximize.
Сохранённый compactActive скрытой/неактивной панели больше не вызывает пустой
Task Manager поверх Search. Начальное восстановление непосредственно на телефоне
сохраняет прежний выбор. mobile_panel_resize.mjs воспроизводит старый сбой на
нативной временной SQLite-базе и проверяет закрытую панель, неактивную вкладку,
открытые задачи и повторный переход после Back; mobile_panel_restore.mjs проверяет
восстановление и очередь как панель. Оба Chromium-теста, docks.mjs и Vite build
прошли. В QML Handler DockHost нет соответствующего phone breakpoint: это адаптация
браузерного представления, без изменения его desktop layout. EN/RU Mobile Help
обновлена; физический телефон не проверялся.

Мобильный фон объекта и его шапки в ResultItem использует файл типа web из
существующего ThumbWdg preview.files, с fallback к preview.image при отсутствии
web. Desktop сохраняет icon; схема API и QML Handler не меняются, поскольку
полноразмерного мобильного фона в Handler нет. mobile_preview.mjs на нативной
SQLite-базе проверил точный URL web в карточке/шапке, отсутствие web, ошибку
загрузки и прежний desktop icon в dark/light 320/390. Vite build прошёл.

Knowledge Base: SQLite debug_log зафиксировал 2026-10-13 ошибку preload CSS
KnowledgeBase-BcXAPNXn.css от предыдущей сборки. Teleport в док перенесён из
KnowledgeBase в его владельца App, поэтому async loading/error теперь находятся
внутри dock-knowledge, а не сжимаются соседним flex-элементом workspace. CSS
получает стабильные имена при Vite build; ui_asset проверяет JS/CSS через ETag
и Cache-Control public,no-cache. Нативные knowledge_base_in_chromium и проверка
упакованных assets прошли; knowledge_dock_load.mjs воспроизвёл отказ CSS,
проверил loading/error на desktop/390px, восстановление и 304 по ETag.
EN/RU Help обновлена. Соответствующей ошибки загрузки браузерного CSS в QML
Handler нет; его KnowledgeBaseView изучен без изменений. Рабочий сервер
192.168.2.55:8081 отдаёт новый CSS, но ещё использует прежний immutable header:
для применения backend-политики нужен перезапуск; пользовательский сервер
агентом не перезапускался. Тестовые серверы и браузеры остановлены.

TaskGanttView: у title-кнопки с нулевыми отступами убран унаследованный pill
radius, который обрезал первые буквы названия/процесса. Текст сохраняет правый
ellipsis. Header queue/activity теперь используют штатный AppButton badgeCount
вместо result-count в icon-only слоте. AppMenu получил такой же счётчик для
аккаунта (messageUnread), как Main.qml Handler; badge находится рядом с аватаром,
а не внутри ItemPreview. Общие icon-button badges/action-count имеют visible
overflow и отступ -4px над правым краем; статические счётчики процессов сохраняют
своё размещение. Смещение отличается от Handler (-1px) по замечанию пользователя.
Нативный header_badges.mjs проверил desktop/390/320, 99+, ноль, границы экрана и
открытие меню; gantt_calendar.mjs подтвердил текст и все прежние операции
расписания. Build прошёл, EN/RU Communication Help обновлена. QML не имеет
браузерного rounded clip у title-кнопки; соответствующий CSS исправлен в Stream.

Task Manager Sort/Group сохраняют semantic icon из текущего Handler tasks.py
(schedule/history/person/process/status/sobject/priority/milestone/supervisor).
Существующие Stream Search Type/Project используют schema/workspaces из Handler.
AppSelect отображает option.icon через общий AppIcon в native base-select;
selectedcontent сохраняет иконку выбранного значения без второй кнопки/обводки.
Если base-select не поддержан, остаётся прежний текстовый native select.
Resolver дополнен недостающими алиасами для пяти наборов, соответствующие glyphs
проверены icons.mjs. gantt_calendar.mjs подтвердил все пункты двух меню, выбранную
иконку и смену due/recent, а также операции расписания. Нативный
task_manager_in_chromium прошёл (36.4s). QML уже имеет эти option.icon, исправление
сделано в Stream. EN/RU Tasks Help обновлена; Safari отдельно не проверялся.

## Рамка сохранённых поисков и оставшиеся focus outlines (0.112.87)

SearchLibrary наследовал fullscreen configuration-dialog (border 0), поэтому
после уменьшения окна сохранял прямоугольный Configuration shell. Он использует
общий record-dialog с ограниченной desktop-геометрией 920x720 и scroll внутри
редактора. WindowControls сохраняет скруглённую рамку также у восстановленных
configuration-dialog редакторов. Maximize и phone layout остаются полноэкранными.
Нативная рамка FloatingWindow.qml текущего TH принадлежит Windows/DWM; этот CSS
исправляет браузерную рамку, не изменяя окно или геометрию запущенного Handler.

Положительные outline правила на :focus/:focus-visible/:focus-within и .focused
удалены из общих controls и экранов: header, menus, code blocks, pickers, preview,
notification activation, knowledge editor, debug search и result surface.
Последняя обводилась как дочерний элемент и не подпадала под прежний :focus reset.
Клавиатурные обработчики не удалены; selected file rows сохраняют selection,
focused unselected rows используют hover background. Pending/error/drop маркеры
предметного состояния не являются focus rings и сохраняют свой контракт.

window_types.mjs теперь открывает настоящий SearchLibrary через API fixture:
bounded/rounded geometry, header focus, Alt+arrows, maximize/restore, сохранение
рамки, dirty close/Keep editing/Discard и отсутствие mobile overflow. Проверяет
также рамку восстановленного configuration editor. Снимок:
.screenshots/window-types-current/saved-searches-rounded.png. Отдельная проверка
CSS подтвердила отсутствие положительных outline у focus states/descendants.
Все запросы теста изолированы; рабочие saved searches и сервер не изменяются.

## Закрытие Configuration и скругление развёрнутых окон (0.112.88)

Основная кнопка Configuration называется Close/Закрыть, как запрошено
пользователем. Её прежний cancel()/request_close() остаётся guarded close:
чистое окно закрывается, dirty показывает Save/Discard/Continue editing.
Repository reset и отмена локальных подтверждений не переименованы. ТХ
0.6.0.43 синхронизирует только эту основную кнопку и EN/RU Help, сохраняя
objectName configurationCancel для существующих вызывающих компонентов.

Скругление обнулялось общим app-window-maximized. Desktop теперь сохраняет
theme dialog radius и в этом состоянии; phone layout по-прежнему занимает
экран. Начальное fullscreen определяется offsetWidth/offsetHeight, поэтому
scale вступительной анимации не меняет определение состояния окна.

При проверке настоящего Configuration обнаружено, что Vue update мог удалить
вставленный host WindowControls, пока observer считал неизменившийся header
уже обработанным. windowDirective возвращает тот же host в header, сохраняя
компонент, его saved/placed geometry и maximize state; новые controls поверх
старых не создаются. window_types.mjs проверяет реальный KeepAlive Configuration:
initial maximize, change page, dirty Close/Continue editing/Discard,
restore/maximize и сохранение скругления/кнопок. QML layout check ТХ проверяет
Close на основной кнопке; выполнен offscreen с QT_QUICK_CONTROLS_STYLE=Basic.
Снимок: .screenshots/window-types-current/configuration-rounded.png.

## Центрирование общего checkbox (0.112.89)

AppIcon имеет общий размер 1em. В checkbox абсолютное inset:0 оставляло этот
фиксированный размер, поэтому компактная галочка смещалась на 2px влево и
вверх. Общий selector app-checkbox-indicator задаёт иконке width/height:100%,
сохраняя центрирование glyph через существующую сетку без ручных смещений.
Цвет — on-selected, размер обычной иконки 15px, компактной 13px, радиус
индикатора min(5px, item-radius), как в текущем controls/CheckBox.qml ТХ.
Нативный input, disabled, indeterminate, label и keyboard/touch не заменены.

checkbox_geometry.mjs проверяет центр контейнера и рисунка после загрузки
шрифтов: пять наборов, три темы, light/dark; label click, Space, tap по glyph,
disabled и mixed state. Изолированный QML capture подтверждает центрирование
17/13 и 19/15 в текущем ТХ, где исправление не требуется. Снимки находятся в
.screenshots/checkbox-current/. Сборка и fixture не обращаются к рабочей БД.

## Всплывающие панели Messages и размеры эмодзи (0.112.90)

Текущий MessagesView.qml использует Controls.Popup для списка участников,
файлов, поиска, создания, изменения состава, переименования и историй. ТС
ошибочно превращал их в модальные dialog с общим оконным заголовком.
MessagesView теперь использует существующий AppMenu overlay для этих панелей.
Участники, файлы, поиск и история закреплений привязаны к кнопке; создание,
изменение состава, переименование и история правок центрируются в окне Messages,
как в ТХ. Общий AppMenu получил centered для этих существующих сценариев,
сохранив размещение/ограничение по boundary, Escape/outside и возврат фокуса
в anchor; скрытый trigger фокусирует поле панели перед её действиями.
Редактирование сообщения и подтверждения удаления/очистки остаются модальными;
пересылка остаётся немодальной. Завершение сохранения закрывает только тот
экземпляр редактора, из которого операция отправлена.

Поиск больше не является AppSearchField с flex:1 внутри вертикальной панели.
Небольшой popup хранит searchDraft до Enter/Search, очищает применённый запрос
через Clear и не меняет высоту таймлайна. Панель участников имеет поверхность
306x366, файлов 356x406; размеры исключают 12px native shadow с каждой стороны,
без добавленного оконного заголовка. EN/RU Help и старые интеграционные
селекторы переключены на панели, включая применение/сброс поиска.

В EmojiPicker общий account-panel selector перебивал font-size/выравнивание
кнопки. Предметный selector emoji-picker/emoji-grid/app-button сохраняет Noto
Color Emoji, 26px на desktop (ТХ: 19pt), восемь колонок и высоту 40px; мобильный
вариант остаётся 32px/44px. Поле поиска emoji не растёт по вертикальному flex.

messages_ui.mjs монтирует настоящий MessagesView с изолированными ответами API:
anchor/размеры, немодальность, Escape/outside/повторный клик, доступ к workspace,
поиск/clear/focus, centered create/rename, members/pin/edit history, modal edit,
nonmodal forward, EN/RU, mobile 320px и закрытие владельца. button_activation
и quick_filter_popup проверяют существующих потребителей AppMenu. Снимки
.screenshots/messages-ui-current/ содержат новые панели ТС и текущие QML
members/search/EmojiPicker: modal=false, 40px emoji cell, 19pt glyph.
Интеграционный messages.mjs с записью в БД не запускался на пользовательской БД.

## Переключение чатов без пересоздания лент (0.112.91)

ТХ хранит отдельные модели в MessagesController._conversation_cache и отдельные
MessagesTimeline в messageSurfaceModel. Cached restore меняет current/visible,
сохраняя элементы, картинки и position; серверная история загружается только
при dirty или изменившемся lastTimestamp. В ТС старый Map хранил только массивы
данных, поэтому единственная лента пересоздавала MessageBubble, AttachmentItem
и blob-превью при каждом возврате.

Существующий Map стал shallowReactive, состояния лент тоже shallowReactive.
MessagesView остаётся единственным владельцем запросов и активных данных;
активные records/pinned/history/previews синхронизируются с соответствующим
состоянием. Шаблон держит стабильные keyed viewport для максимум 12 чатов и
переключает v-show без анимации. Сохраняются scroll/follow, preview objects и
URL; загрузчик файла фиксирует chat владельца. Неизменившийся загруженный чат
открывается без history read. Dirty events или lastTimestamp вызывают background
refresh без loading overlay и без сдвига места чтения; первая незагруженная
история скрыта до готовности и использует Loading conversation.

Search получает отдельную ленту, не перезаписывая сохранённую полную историю.
Применение/сброс теперь запускает запрос прямо из applySearch: прежний debounce
watch на search мог повторно запросить историю после смены чата. Старые responses
защищены epoch/historyRequest/chat/query; cached restore отменяет предыдущий
loading state. Смена аккаунта очищает все ленты и URL; list pruning удаляет
недоступные чаты. Изменение проекта очищает link previews, сохраняя общую для
аккаунта переписку. LRU pruning освобождает невостребованные приватные preview URL.

MessageBubble сохраняет contour size при display:none. AttachmentCard и
ResponsiveFlow сохраняют положительную ширину скрытых элементов и переносят
изменение ширины из ResizeObserver в следующий animation frame; callback
отменяется при unmount. Это сохраняет размеры изображений при возврате и
исключает наблюдавшиеся ResizeObserver feedback loops.

messages_ui.mjs сначала воспроизвёл потерю DOM при cached restore. После фикса
он проверяет те же viewport/message/avatar/attachment img и blob URL, размеры
изображения, scroll=450 и отсутствие пустого/loading кадра на 12 последовательных
animation frames при задержке history 300ms. Проверены повторные переключения
без history read, поздний ответ холодного чата, search/clear без потери полной
истории, 12-chat LRU eviction, logout и прежние UI сценарии панелей/эмодзи.
ТХ: test_cached_conversation_is_presented_without_history_reload и
test_cached_stale_conversation_refreshes_in_background прошли без изменений.
messages/mobile_workspace/skey_previews integration selectors теперь ограничены
viewport[data-current=true]; эти suites с записью в БД здесь не запускались.

Область Task Manager: вместо вложенного AppSelect TaskWorkspaceScope показывает
прямые AppMenuItem с иконками и checked, как scopeMenuActions текущего Handler.
Заголовок имеет короткую подпись scopeTitle и актуальную scope-иконку; текстовая
кнопка использует button-radius вместо 50%, поэтому не становится эллипсом.
Выбор пользователя/команды и прежние changeScope/identityChanged guards сохранены.
Project/Selected/Search Type закрывают popup после выбора. Нативный
task_manager_in_chromium прошёл (39.1s), gantt_calendar.mjs проверил прямые пять
пунктов, Project→User, закрытие, identity и операции расписания. QML уже имеет
прямое scope menu; исправлена адаптация Stream. EN/RU Help и короткое Selected
обновлены. Физический телефон отдельно не проверялся.


## Raw database editor (0.112.92)

Integer transport correction 0.112.106 / Handler Help 0.6.0.58: a real native raw procedure completed but standard XML-RPC response serialization raised `OverflowError: int exceeds XML-RPC limits`. `server/xmlrpc_response.py` extends the response marshaller locally with i8/biginteger tags; ordinary packets match stdlib encoding and request marshalling remains untouched. The existing self-contained RAW procedure and JavaScript exact-integer/string boundary stay identical in TH/TS. An owned HTTP test uses the unchanged Handler SDK to load/compare JSON/save integer cells and keys at signed 32-bit and JavaScript/64-bit boundaries; additional checks cover signed large/nested responses, faults and XML declaration rejection. The Stream service must reload the new transport code. A response failure occurs after dispatch, so callers must reload uncertain writes before retrying.

Follow-up 0.112.102 / Handler 0.6.0.52: row virtualization alone left eager `TextContextMenu` creation in every visible shared TextField. The shared control now retains one menu created at its first right click. Real `change_timestamp` page data (50×9) agrees between native RPC and Stream JSON; transport is approximately 54/41ms, while native presentation fell from roughly 1.9s to 0.16s. A later profile measured 0.11s on a different page with 153 editors and zero unopened menus. `tools/profile_raw_database.py --page <saved-load-response.json>` reproduces presentation without database writes. A complete Qt-worker/XML-RPC/QML transition also passed against an owned temporary server; live full-transition measurement could not finish after the running server stopped accepting connections. Native Windows and offscreen checks cover menu creation/reuse, selection preservation and read-only actions.

Paging qualification 0.112.101 / Handler 0.6.0.51: native RAW uses the existing Qt ListView virtualized row pattern, retaining the same grid and draft controller. Newly visible editors read current text through `cell_text` because the QVariant list is a snapshot. `tools/profile_raw_database.py` measures a private 50×12 page: 600 editors / 8.4s before; 84 editors / 1.15s construction and 0.87s next-page construction after. These are local UI measurements, not network latency guarantees. Native tests cover offscreen edited values and full-page navigation; the real browser check covers 75×12 pagination and second-page save. The shared server procedure is unchanged.

Parity update 0.112.99 / Handler 0.6.0.49: body padding 20px, gaps 12/8px, row-number column 84px, value columns 230px, sticky headers 40px and cell height equal to the themed control height. At content width below 900px the actions occupy a second toolbar row. Both interfaces use direct draft save, inline discard/drop confirmations, finite JSON values, selectable read-only cells and uncertain-write recovery. `tools/raw_database_handler_reference.py` and `tools/raw_database_browser.py` capture the same private fixture at 1400×940, English, MD3 dark; Qt and browser font rasterization and native file dialogs/downloads remain platform differences.

Administration has a separate raw section in both Stream and Handler 0.6.0.44.
`server/raw_database.py` owns the self-contained physical-table procedure;
Handler sends the same source through its existing server-procedure transport.
`RawDatabase.vue` and `AdminRawDatabaseView.qml` retain drafts inside the existing
Administration host. Handler reuses AdminDocumentEditor for async execution and
stale-result rejection. Server routes authenticate tickets and require a persisted
administrator; the procedure independently checks administrator security.
Writes deliberately use raw Sql within Command, bypassing object validation,
SObject triggers and undo. Table locks and per-row hashes protect atomic batches.
Secrets and embedded JSON credentials are redacted; binary/generated/secret cells
are read-only. CSV is limited to 50000 rows and cannot preserve NULL versus empty
text. DROP does not repair Search Types, links or repository files.

Checks: `tests/test_raw_database.py`, `tools/raw_database_browser.py` (set
PLAYWRIGHT_CHANNEL=msedge when using installed Edge), Handler
`tests.test_raw_database.RawDatabaseQmlTests`. Real PostgreSQL validation remains
open; the existing shared UI resource tests report unrelated translation defects.

Mobile section picker: Assets/Textures и остальные openSections теперь имеют
24px круглый ItemPreview с сохранёнными section.accent/icon; текущий раздел
отмечен checked. WorkspaceTabs mobile-leading slot показывает ту же эмблему
рядом с названием поисковой вкладки, счётчиком и стрелкой. Данные sections и
поисковые состояния не менялись, desktop tablist остаётся прежним. Native
mobile_search_toolbar.mjs проверил реальный Assets→Textures→Assets, цвета
кнопки/пунктов, 24px/50% на 320/390, поиск/фильтры/закрытие/restore, RU и desktop.
EN/RU Mobile Help обновлена; build прошёл. Использованы текущие section circle
и icon Handler/SectionTabRail; физический телефон отдельно не проверялся.

Регрессия mobile section circles: браузер со старым CSS оставлял стандартные
112px у ItemPreview вместо 24px. Свежий предыдущий тест этого не покрывал.
Размер width/height/minWidth/flex и 50% radius теперь задаются самим владельцем
двух эмблем через inline style в App; дублирующие CSS правила удалены, контракт
ItemPreview.previewSize и остальные превью не менялись. Native browser fixture
со срезанными новыми mobile-section CSS воспроизвёл 112≠24 до исправления,
после исправления проходит с текущим/старым CSS и deviceScaleFactor=3.
Проверены все эмблемы меню и кнопки, 320/390, переключения, поиск/restore/RU
и desktop. PNG: mobile-section-circles-menu-stale-3x.png. Рабочий сервер теперь
отдаёт CSS public,no-cache, но прежний immutable cache в открытом браузере
сохранялся; geometry эмблем больше от него не зависит. Тестовые процессы закрыты.


## Declarative SObject layouts (2026-10-13)

Plan and boundaries: use the existing WidgetConfigView → interface descriptor →
Vue renderer path. A view is an arrangement of reusable visual elements, not
an inheritance hierarchy of the application's built-in result modes. Collections
(grid, list, tree, table) repeat object items; groups arrange their children.
A separate custom Continuous Tree is the shipped example in
`src/tactic_stream/config/search_type/widget/DEFAULT-conf.xml`, view `continuous_example`.
The same source supplies the ready `table_example`, `cards_example` and all
three creation templates. The cards example uses the existing 280px grid with
large preview, title, description, details and notes badge; its XML is shared
with the Cards template rather than duplicated in `config/layouts`.
Its ConfiguredResultItem uses ItemLayout; the original ResultItem.vue and standard
Continuous Tree remain unchanged. Type/project
config records override that source through ordinary WidgetConfigView resolution.
Other existing result modes remain available.

Administration/Layout Editor owns drafts, selection, sample records, geometry,
check/preview, saved source and uncertain-save state. It creates blank views,
ships cards/table/tree templates, copies views, edits variants and nested groups,
and offers placement by cells, drag or explicit move buttons. Named layouts can
also be reused by a view widget; references are resolved server-side with cycle,
depth and composition budgets. Widgets: image, title, description, text, link,
button/badge, group, reused view and existing item metadata/snapshot/knowledge/
relationship/quick-action presenters. Bindings read SObject columns or prepared
item data. Actions reuse existing SObject operations.

The tree example now composes the original item DOM using XML groups and the
shared result-part styles (`flow=contents`, bounded role/tag/when attributes).
It keeps preview shapes/sizes, title quick actions and fit checks, metadata,
snapshot dates/files/status, task/note badges, hover holding and mobile menus.
Grid placement remains available within a group or for the whole item; the
editor explains shared placement and hides ineffective row/column controls.
No copy of ResultItem.vue or separate native-item visual component is embedded
in the template. New styles and conditions use a bounded renderer contract.

`test_item_layout_parity.py` mounts Original and XML ConfiguredResultItem on
identical fixture data/theme/language/viewports. 60 screenshot pairs cover main
and child objects, images, process/relation/version branches and snapshots,
including offline and long filenames, hover/selection and desktop/phone.
Pixel comparison permits one channel level for Chromium border antialiasing;
the task action is checked separately. Files: `.screenshots/item-layout-parity`.
Chromium also opens `table_example` without saving, verifies its columns and
object-details action, then copies templates and saves custom views. Empty XML
is rejected before DOMParser to avoid its styled parsererror CSP warnings.
That item-baseline test compares the user's existing Stream ResultItem. Handler
now hosts the same Vue editor and renderer in Administration through Qt WebEngine;
standard native items remain separate. The dedicated host uses the selected server,
project, authorized ticket and native appearance. Draft/busy/uncertain state blocks
project switching and closure, while a distinct URL signal prevents state changes
from reloading a draft. The private WebEngine profile is destroyed on session end.
This feature requires a Stream server; it does not add layout endpoints to Legacy
TACTIC. New custom views open in the embedded Stream workspace.

The editor has an example/copy chooser, element list, clickable preview and
kind-specific content/position properties. XML, styles and conditions are folded
into advanced settings. EN/RU Help contains card, table, group and overlap recipes.
`test_item_layout_handler.py` compares actual Qt and browser editor bodies on the
same private server at 1190×903 and 850×700, in EN/RU and dark/light MD3. The native
check uses real mouse/keyboard input, creates and saves a copy, opens Help and then
opens the saved cards view and ready table/tree examples. Downloads use a native
save dialog; new-window links open externally without replacing a draft. Table
preview and runtime share ItemLayoutTable. Window frames and platform font rasterization are
separate from the shared body. Files: `.screenshots/item-layout-handler/`.

Authoring still uses `/admin/widget-configuration` with native Command transactions,
journaling and revision conflicts. No frontend script evaluation, raw HTML or
parallel configuration store. The server rejects unsupported widgets, options,
invalid geometry/bindings and cyclic containers/references. Changes are reviewed
in resolved preview and diff before Save. Saved views open from the editor,
View actions, or existing sidebar view targets. Help: `item_layouts` (EN/RU).

This does not execute arbitrary legacy CustomLayoutWdg/Mako/Python. Newly composed
widgets need only configs; new executable visual primitives need a renderer and
new server actions need their existing native authorization/command contract.
The custom table template uses item widgets; existing editable specialized table
cells keep the Columns Editor/ConfiguredView implementation.

Validation: `test_item_layout.py` verifies shipped XML, input rejection, native
save/preview, revision conflicts, unchanged standard view, nested reuse and cycle
rollback. `frontend/tests/item_layout_data.mjs` checks data bindings, variants
and unsafe URL rejection. `test_item_layout_browser.py` runs Chromium against
private fixture data: original item remains active in the standard tree;
custom cards, object-details action, tree expansion, table, reused widget,
move controls, dirty guard, check/save/open/reload and phone display pass.
Screenshots: `.screenshots/item-layouts/`. Existing `test_widget_authoring.py`
and `test_widget_preview.py` pass. Frontend production build passes.

## 0.112.98 — source-reviewed Table View widget database

Shared Help now exposes widget_database and table_widget_examples in EN/RU.
The inventory separates purpose, readiness, scope, legacy source review and
migration decision; the complete HTML/CSV/JSON exports live in
reports/table-view-2026-10-13. There are 193 table classes plus a compatible
TextWdg input alias: 10 connected basic presenters, the restricted journal
HiddenRow, 138 unconnected classes, 43 previously excluded pyasm.prod classes,
and one explicit unfinished SnapshotServerElementWdg stub. No fully migrated
legacy class contract is claimed. TODO and pass in a working alias are not
exclusions. PlaceHolderElementWdg is deliberately empty infrastructure.

The user-approved workflow is source/callers/inheritance review, reproducible
XML and data, paired legacy/TH and Stream captures, documented options/actions,
authorization and limits, then implementation and verification. Unreviewed
classes are not automatically migration targets. SpreadsheetElementWdg is a
running-total renderer, not a full spreadsheet editor. The broken source
ExploreElementWdg catalog name is distinguished from ExplorerElementWdg and
its valid ExplorerTableElementWdg inherited alias.

The first incremental implementation adds CompletionCell, matching current
TH TacticCompletionCell.qml geometry (18px, 10px), roles/colors, caption font,
0–100 clamping and progress semantics. Native TaskCompletionWdg selection,
ACL and percentage computation remain authoritative; describe_cell now returns
kind=completion. Column width comes from the element attribute. Footer/group
summaries and full old display/action contracts remain unavailable.

Verification: report.py checks descriptors with a Store-free RequestContext;
document.py uses WidgetConfig.get to validate all ten XML examples. The native
capture_th.py loads the current QML component directly without Handler startup
or server calls. frontend/tests/table_widget_catalog.mjs mounts actual Vue
presenters and shared Help in an isolated Vite page, checks TH measurements,
clamping/errors, preview/notes signals, EN/RU articles and 320px, and publishes
bundled help/media screenshots. These are typed fixture values, not full
legacy CGI execution or every example against a database. Own browser/Vite
resources close in finally. No live database/server/client was restarted.


Layout catalog regression (2026-10-13): Layout Editor now uses `layout_views`,
which resolves only SObject layouts; its selector no longer consumes the generic
widget-config list. Service records such as `quick_filters@cg/assets@th_assets`
remain owned by Quick Filter Editor. Invalid names are excluded from generic
view choices, while ordinary named table/tab views remain in workspace actions.
After a failed read the layout selector keeps `continuous_example` available;
invalid incoming names return to that example. Native tests preserve both scoped
and simple quick-filter configs, and Chromium tests reproduce a failed read,
select a working view and complete creation/save/open afterwards. Handler has no
corresponding layout builder; its quick-filter format is unchanged.


## 0.112.103 — used Table View value block and checklist

The user scope now includes every table-widget mention in every widget config,
including definition, dynamic classes and embedded templates. The reproducible
tools/used_table_widgets.py scans shipped XML, the CG export and every local
project spt_widget_config read mode=ro. 449 configs contain 108 distinct class
references/canonical classes; agreed production and unfinished-source exclusions
still apply. HTML/CSV/JSON checklist entries record exact location and option
names. Source presence does not prove runtime execution. Broken class names and
non-XML source records remain explicit. No live user config is rewritten.

The ArrayTableElementWdg, XmlWdg, JsonElementWdg and SnapshotVersionElementWdg
source display algorithms now return typed cells. Array NULL and version NULL
formatting defects are fixed. XML/JSON/version raw SDK values remain unchanged;
XML decompression is display-only, malformed XML keeps a diagnostic and text,
JSON retains original key sorting/indentation/empty semantics. Browser text is
never executable HTML; JSON height is bounded to 600px, its original sortable
False is retained. Short Xml/Array/Thumb/Text class paths are resolved explicitly.

Handler action_cell_values uses get_cell_value on native servers and matching
source-value calculations on original servers; TacticStructuredTableCell shares
read-only controls and theme/typography. Both transports and source display
bodies are covered by test_table_value_widgets.py without a Store.

The source-reviewed used-read-only Array/version scenarios are checked off.
XML/JSON display is checked; their general inline editor stays open. This does
not claim completion of all 108 references or the whole legacy table contract.
Help grows to fourteen validated XML examples, paired native QML/Vue captures
for the four value types, source/parser/NULL errors, safe text, height/scroll and
320px tests. Table-wide inline editing, summaries, layout/actions and remaining
used widgets are separate pending checklist blocks. All own checks close their
resources; user servers/clients are neither restarted nor stopped.


## 0.112.105 — Gantt fractional viewport sizing (2026-10-14)

TaskGanttView's ResizeObserver reads fractional contentRect extents for both the
root and scrolling body, publishes them together on the existing animation frame,
and retains entries across successive deliveries. Rounded clientWidth/clientHeight
could oversize an empty canvas (750px against a 749.75px viewport), creating
scrollbar feedback. A source-browser regression fails that fractional-overflow
case before the fix and passes empty, ordinary and overflowing projections at
100/125/150%, two fractional dock sizes, idle-frame stability and real wheel input.
The existing Gantt/calendar gesture and virtualization check passes. Native QML
already uses real-valued extents; its corresponding isolated check uses the same
projection fixture, sizes, Russian MD3 dark and scale factors without changing
its geometry algorithm. These checks establish scroll stability, not complete
Gantt layout parity or verification in the user's running session.

The production build also exposed a TableCell import of a nonexistent timestampTooltip.
The caller now uses the existing timestampFullLabel formatter for its fallback
tooltip, preserving prepared server tooltips. Production build and the complete
Gantt/calendar gesture fixture pass.

## Current Handler Table View port — 2026-10-14

ConfiguredView owns native cell reads, saved-view XML and revisions, inline plans,
scoped row operations and staged task changes. TableView is the virtualized presentation
and input layer; tableColumns.js is the existing Handler width/hide/fit algorithm.
TableCell/TaskCell/TaskCards remain typed presenters using shared controls. Keep
structured XML/JSON read-only as in current Handler; do not infer executable legacy
HTML or arbitrary JS/action support from a widget class name.

Native TableCellEditCmd resolves edit/edit_definition inputs and their action.column,
checks selection, rights and every row/config revision before the first EditCmd,
and relies on the outer native transaction for rollback. TimeAction uses its original
compound Web input and restores the surrounding Web context. Unknown outcomes and
connection changes retain drafts and prevent blind repeat writes. Column mutations
use existing WidgetConfig APIs and preserve unowned XML. No additional persistence,
transport or action factory is introduced.

Current coverage is 45 registered Handler names / 21 adapted classes; complete legacy
contracts remain separately tracked. Paired current QML/Vue captures and measurements
are in reports/table-view-2026-10-14/table-view-parity.html. The desktop bridge is
still excluded: Explorer copies the native local path; browser check-in uses upload.

## Background tickets, journal indexes and cleanup plan — 2026-10-14

Completed in this change:

- File-task threads and the queue executor opt into Batch ticket reuse. The cache
  belongs to the executor and stores only keys indexed by data directory and login;
  it does not retain Security, groups, ACLs or SObjects. Each Batch rechecks the
  persisted ticket and account and builds the current permissions. Expiry or
  revocation requires a new service credential; a retired account still fails.
  Ordinary Batch callers and the XML-RPC/JSON authentication contracts are unchanged.
- A real file worker completes three successive transfers without ticket growth.
  The queue reuses a submitter's ticket across jobs and refuses the next check-in
  after that submitter's repository permissions are revoked. Account expiry,
  retirement, database isolation and a stolen cached key are also checked.
- Eight non-unique indexes join the existing SQLite/PostgreSQL journal upgrade.
  Fresh initialization creates them; `python run.py upgrade` adds them to existing
  system databases. Existing duplicate object markers remain intact. Ticket keys
  and transaction-state tickets already have unique indexes; do not add duplicates.

| Indexed columns | Read that needs them |
| --- | --- |
| change_timestamp(search_type, search_code) | Commit merge and field-level Undo conflict checks |
| change_timestamp(timestamp) | Global activity range and chronological paging |
| change_timestamp(project_code, timestamp) | Per-project activity and update cursors |
| change_timestamp(search_type, timestamp) | Message reactions and type-specific changes |
| sobject_log(search_type, search_id, timestamp, id) | Script/knowledge history and object audit |
| sobject_log(search_type, id) | Latest editor/configuration revision |
| sobject_log(transaction_log_id) | Activity joins to native transactions |
| sobject_log(code) | Native code-key object resolution |

All eight were applied to the running local SQLite system database in one short
DDL transaction (0.83 seconds). Counts stayed at 457 tickets, 5090 transactions,
29802 object logs and 58170 change markers. Its object-marker lookup now uses
change_timestamp_object_idx; a local 100-read sample averaged 0.067ms. Upgrade
idempotency, preservation of existing duplicate rows and eight actual query plans
pass on SQLite. PostgreSQL uses the same index SQL through its existing native
upgrade, but a live PostgreSQL run remains open: Docker Desktop's engine was not
running. No service was restarted and no application records were deleted.

The sobject_log table and change markers *about* that table have different roles:

| Data | Current dependencies | Decision |
| --- | --- | --- |
| sobject_log records | Script/knowledge history, activity, task audit and optimistic revisions in Columns, widget configuration, sidebar and security editors; corresponding Handler queries | Preserve the journal |
| change_timestamp rows with search_type=sthpw/sobject_log | Written by SObject._finish_commit; included by generic update queries and Raw database; generic replay can consult markers by any type/code | Candidate for reducing future writes, not yet removed |

No dedicated business reader of the second category was found in Stream or the
current Handler. The main activity fallback excludes sthpw types, but the update
transport still fetches generic markers before client handling. The limit is
applied before those rows are interpreted, so simply stopping their writes can
change paging/cursors. Read-only scanning of 210 saved script/config definitions
found no explicit combined sobject_log/change_timestamp reference or
get_change_timestamp call. This does not rule out dynamically constructed user
scripts or external clients.

Next stages, in order:

1. **Expired-ticket dry run.** Use the existing expiry parser/UTC rules. Report
   counts only, split by category, age and blocking references. Never include keys
   in diagnostics. NULL/permanent expiry stays untouched. A 24-hour grace period
   after expiry is the proposed first policy; malformed dates are reported, not
   silently deleted.
2. **Protect unfinished work.** Resolve transaction_state before deletion. An
   expired ticket with an open transaction remains blocked until abandonment is
   explicitly defined. Check active/queued file and check-in tasks, leases and
   ticket-owned uploads. transaction_log.ticket and the upload directory participate
   in file Undo/Redo; expired authentication alone does not authorize deleting the
   journal or its staged files. Historical ticket references and retention require
   separate decisions; do not cascade into them.
3. **Bounded cleanup.** After the dry run is qualified, reuse the existing queue/
   scheduler for one periodic maintenance job. Delete small batches only, recheck
   persisted expiry and blockers under the same transaction/lock, and allow safe
   renewal to win a race. Add an expiry index with this actual cleanup query. Keep
   browser/Handler ticket renewal, password revocation and active worker recovery
   in the regression set. Cleanup is not implemented or enabled in this change.
4. **Qualify redundant markers.** On private data, compare TH/TS activity, update
   cursors, editor revisions, script history, Undo/Redo and rollback with and without
   sobject_log markers. Filter unwanted service markers on the server before LIMIT
   if the generic stream currently needs it. Only then stop creating that category
   and separately plan bounded removal of old markers. Keep sobject_log itself,
   transaction_log and markers for real objects.

Server workers must restart to load ticket-reuse code. The already-created SQLite
indexes take effect independently of that restart. No client-side ticket cache or
new Handler/Vue workflow is needed: both clients use these shared backend services.

## Engine micro-optimizations — 2026-10-14

This pass measures hot lookup shapes before changing them. It adds nine non-unique
indexes in the existing preference, persistence, snapshot, connection and security
schema owners; Store._get_upgrade collects their indexes into the same native
SQLite/PostgreSQL upgrade. No object data, uniqueness, ACL or query filters change.

| Lookup | Before / after, milliseconds | Index |
| --- | --- | --- |
| User/global preferences | 2.235 / 0.063 | pref_setting(login, project_code) |
| Global-search object by code | 4.479 / 0.062 | sobject_list(search_type, search_code) |
| Global-search object by id | 4.040 / 0.062 | sobject_list(search_type, search_id) |
| Publication by parent code/context | 5.459 / 0.066 | snapshot(search_type, search_code, context, version) |
| Publication by parent id/context | 3.892 / 0.065 | snapshot(search_type, search_id, context, version) |
| Repository file path | 3.835 / 0.061 | file(relative_dir, file_name) |
| Outgoing object links | 3.748 / 0.058 | connection(src_search_type, src_search_id) |
| Incoming object links | 3.734 / 0.061 | connection(dst_search_type, dst_search_id) |
| Login group memberships | 1.913 / 0.057 | login_in_group(login) |

These are median SQLite query/fetch times over 21 reads on private tables with
50000 rows each, not complete client-request timings. Query plans now SEARCH an
index instead of walking the table/code index; sorts over the small selected
subset remain when needed. All nine result hashes match. A raw insert batch of
1000 rows into each of six tables costs 11.052ms before and 13.724ms after; this
measures index write overhead, excluding native Command/journal work. The report
and reproducible probe are benchmarks/engine_micro_2026-10-14/index_comparison.json
and tools/engine_index_probe.py. Its databases are private and automatically removed.

SearchKey also reuses pure parsing results within the current request, bounded to
256 entries. It returns fresh mutable dictionaries, preserves malformed-key errors
and nested identity text, and does not cache custom str subclasses. Parsed fields
are not identity, account status, groups, ACLs, object data or database metadata.
Existing permission checks still run; the cache disappears with RequestContext.
The same-source A/B alternates old/new parsing for 21 measured calls on one private
fixture, verifies response hashes and excludes profiler overhead:

| Complete native dispatch | Before / after, milliseconds |
| --- | --- |
| 10 rows | 8.365 / 8.448 — no useful speedup |
| 1000 rows | 18.909 / 17.931 |
| 10000 rows | 112.054 / 104.322 |
| TSQL names, 9500 live objects | 110.213 / 104.413 |

key_comparison.json records the paired run; before/ and after_keys/ retain the
existing performance_probe summaries/profiles. All five baseline native workload
response hashes match. The cache adds about 8–10KiB in the large read workloads.
Do not describe SQL lookup speedups as whole-engine or network speedups.

Nine indexes were added to the running local SQLite system database in 0.326s,
without changing counts in ten affected/journal/session tables. Parser reuse needs
a server-worker restart; the indexes already apply. 77 lookup/link/snapshot/level/
file-index/connection/security/check-in/client-transaction checks and three key
contract/cache/record checks pass. The SDK transport case was repeated successfully
with local network access after a sandbox-only startup failure. Live PostgreSQL
remains unqualified because Docker Desktop's engine was unavailable. Both clients
use this shared backend; no separate QML/Vue caching or permission shortcut exists.

## Schema and TEL tree discovery — 2026-10-14

Tracing Handler's `repository_sync.py::_collect_sobjects` confirmed that direct
schema relations already load whole hierarchy levels in bounded batches. Custom
relations retain the native per-parent fallback. This change preserves that path;
it does not claim that every current sync uses TEL or that transfers became faster.

Two shared-engine CPU paths were measured and fixed:

- TEL's relationship/column loops rebuilt `str(self.sobjects)` for every result
  inserted into the per-request object cache. A thousand roots and two thousand
  related objects repeatedly serialized the same large root list. Each loop now
  obtains the existing cache once and passes it to `cache_sobjects`; standalone
  calls retain their original behavior. Namespace, aliases, result order,
  duplicates, leaf mapping and fresh permission checks are preserved.
- Schema relationship lookup scanned all XML connections up to four times per
  miss and forced uncached inherited lookups. A lookup index groups existing XML
  nodes by `(from,to)` within the schema's existing relationship cache. Clearing
  that cache also clears the index, including native direct XML edits and DDL
  invalidation. Explicit `cache=False` reads still scan current XML. Direct,
  reverse, wildcard, path-only fallback, type and inheritance priority are
  unchanged. Inherited resolution now honors the caller's cache flag; parent
  edits remain visible because the child does not copy inherited results.

`tools/relation_performance_probe.py` creates only a disposable SQLite database:
1000 roots, 1000 children, 1000 leaves, 1000 snapshots/files and 500 unrelated
connections. Measurements include authenticated native Python RPC dispatch and
result construction, exclude fixture creation and profiling, and use seven
samples. Results and profiles live in `benchmarks/relations_2026-10-14`.

| Scenario | Before, ms | After, ms | Speedup |
| --- | ---: | ---: | ---: |
| TEL tree plus snapshot/file discovery | 370.349 | 86.361 | 4.29x |
| TEL field read over 1000 roots | 166.319 | 20.660 | 8.05x |
| 1000 inherited relationship resolutions | 134.864 | 13.066 | 10.32x |

All three response SHA-256 values match. SQL statement counts are unchanged:
39/28/26 SELECTs respectively, including authentication and metadata; there are
no write statements. This is a CPU improvement, not an index/transaction change.
Date, timezone and group-variable preparation remain unchanged: its public parser
state contract and small measured share did not justify another change.

106 executed regression checks pass: schema read/edit/delete/replay/template/API,
TEL formats/variables/virtual contexts/paths/connections, expression permissions,
self-instance reads/writes, snapshots, native SDK XML-RPC and rollback. Three new
regressions were demonstrated to fail on the saved pre-change methods. Six opted-in
PostgreSQL checks were skipped because no PostgreSQL service or Docker engine is
available. No vendor-specific SQL was introduced; live PostgreSQL timing remains
unqualified. Native desktop sync over a real repository/network is not measured
by this synthetic server workload. Reload server workers to load the engine fix.

## Raw database sparse saves — 2026-10-14

Handler and Stream previously sent every displayed row and every editable cell
when saving one cell. The server correctly checks the supplied row revisions;
therefore a background edit to an untouched displayed `sthpw/message` record
could reject the whole draft as a conflict.

Both clients now compare cell text with their loaded baseline and send only
modified cells in modified existing rows, new rows and explicitly deleted rows.
Original row keys/revisions and page offset remain in the request. New blank
cells retain database defaults. Existing server table locks, row revision checks,
schema revision checks, administrator enforcement and batch rollback stay intact.
A background edit to the selected row still rejects the write, even if it edits
another field. The fix does not merge or overwrite concurrent row edits.

Validation: eight isolated backend CRUD/security/conflict checks, twelve actual
Handler QML interaction/layout checks, and two native HTTP/XML-RPC checks pass.
The Vue fixture exercises real input and Save clicks, verifies the exact sparse
payload, preserves a background edit, rejects a target conflict, and sends deleted
and new rows without untouched neighbors. The new QML regression fails with the
old save method. Native transport uses the actual Handler self-contained procedure
source, matching Stream's procedure. Private test data only; no production writes.
The browser fixture reports an existing shared AppSelect compiler warning; the
changed save path has no page errors or Qt warnings. Live PostgreSQL remains
unqualified. No server change is needed for this fix: restart Handler and reload
Stream to load the client code. Existing error/unknown-outcome reload behavior
remains unchanged.

## Raw cell window and plain values — 2026-10-14

The RAW grid now opens a separate cell window by click, Enter or F2. Handler uses
a registered `raw_cell` modal through the existing WindowHost/FloatingWindow model,
owned by Administration, with required-context restore disabled. Stream uses the
existing browser window directive and native modal dialog. Shared multiline text
fields, selectors, buttons and scrollbars retain their theme/keyboard behavior.
Read-only/secret/generated cells remain read-only viewers. The grid stays square
and keeps visible-row virtualization in Handler.

Text displays and edits without JSON serialization quotes or escape sequences.
Physical column types determine conversion: integers remain exact (large values
use decimal strings on the wire), booleans accept true/false or 1/0, floats require
finite numbers, decimals retain their input precision, JSON validates but passes
its exact source text (including JSON null/string scalars and large integers).
Other declarations, including dates and untyped/custom columns, use plain text
and the database's native validation. JSON columns still use JSON syntax.

Each cell has explicit Value/NULL/new-row Database default state. This avoids
reserved text sentinels: a Value containing `NULL` or an empty string remains text.
New untouched cells omit their values for database defaults. Apply/Ctrl+Enter
updates only the local table draft; Cancel/Escape/window close changes no cell.
Table Save remains the previous sparse atomic write with original row keys and
revisions. Editor generations prevent applying after a table/project/page reload;
native cell state is cleared when its owning window closes. No server API or
permission policy changed.

Fourteen actual QML checks, the real Vue browser editor flow, three conversion /
SQLite scalar round-trip checks and 39 identical Python/JavaScript vectors pass.
The browser flow includes Cancel/Apply, literal NULL versus SQL NULL/empty text,
numeric validation, 64-bit integer preservation, new/deleted rows, sparse writes,
background updates and real target conflict retention. Native checks also cover
owner modality, readonly viewing, virtualization, defaults and keyboard opening /
application. Screenshots and measurements in `reports/raw-cell-2026-10-14` compare
the same `value · TEXT · Row 1` with text `old`, at 96-DPI test configuration, in
EN/RU, dark/light and 640/480px native client areas. The browser's 642/482px outer
box includes its two-pixel border. Editor sizes match (596/436 × 216px), as do
selector sizes (612/452 × 32px), across all eight comparisons. OS window chrome,
browser maximize control and font rasterization remain platform-specific. Browser
phone layouts use the shared full-screen window behavior, without a native phone
counterpart. Live PostgreSQL and higher-DPI Windows interaction are not qualified.

The existing shared AppSelect compiler warning and RelatedObjects ineffective
dynamic import warning remain outside this change; no page errors or Qt warnings
occurred in the checked editor flows. Restart Handler and reload Stream to load
the client changes; server workers do not need a restart for this feature.

## RAW heading occlusion during scrolling — 2026-10-14

Handler's `AdminRawDatabaseView.qml` overlay header had z=1, equal to Qt
ListView's default delegate stacking level. Later delegates could paint text,
hover backgrounds and delete actions above its already opaque theme rectangles.
Raise only the header to z=2; row virtualization, geometry, cell editing and
server requests are unchanged. Stream's sticky th surface already hides rows
and requires no runtime change.

The native async-first-load check now compares rendered heading pixels before
and after scrolling: fifty rows with id/value/number/protected password, dark and
light themes, 1400/900px windows, horizontal positions 0/120 and vertical positions
100/493. It failed on the original implementation and passed after the fix.
The real Vue fixture uses the same data and equivalent table viewport widths,
checking sixteen header-image pairs plus sticky position and existing cell/save
flows. Browser baselines engage sticky positioning by scrolling one pixel to
avoid the collapsed-border half-pixel offset at the initial top. All fourteen
native RAW checks pass. Tests use Qt offscreen software rendering at 96 DPI and
headless Edge; production Windows scaling remains unqualified. Synchronize both
EN/RU Help articles; restart Handler to load its QML update. No backend changes.

## File-project tasks without selected work objects — 2026-10-14

Task Manager can create a project-level task when no work object is selected.
This reuses Task.get_defaults' original project ownership, not a new task table
or placeholder asset: sthpw/task stores project_code plus the real sthpw/project
identity in search_type/search_code. The standard task pipeline supplies statuses;
the creator is initially assigned so the task appears in My tasks. Existing
object-selected creation keeps its original parent and workflow defaults.

Stream task_scope resolves an omitted parent to Project.get(), validates project
ownership after resolving task parents, and retains native field ACL, command
transactions, triggers and row revisions. Catalog preparation exposes the manual
task process for a project owner. Vue retains the returned canonical project key
in drafts and no longer disables + merely because Results has no selection.
Handler resolves the cached project with a native SObject, uses local project
process choices and reads status choices from its existing worker field catalog.
Project task presentation does not query Search Type schemas on the UI thread.
Opening a project task context uses the existing search-key opener when the owner
is not already a loaded Results row. No cleanup or ticket policy changes.

Verification: 127 Handler controller/catalog/QML checks, including real plus
input, staged insert/save, project Inspector routing and schema-free status
catalog updates. A real Vue fixture uses its usual editor and context menu,
through HTTP to a private file-project database, without mocking task writes.
Native API tests cover create/edit/Inspector, stale and cross-project rejection,
submit task discovery and published changelist links. Existing file-submit and
XML-RPC linked-task checks remain in scope. Only SQLite and headless Qt/Edge are
qualified here; the user's live data and PostgreSQL were not used. Existing task
layouts are independent QML/Vue screens, not a completed Tactic Frame migration.
Restart both clients/server; no database migration is required.
