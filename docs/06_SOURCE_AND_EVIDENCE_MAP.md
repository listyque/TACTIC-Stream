# Карта исходников и доказательств — снимок 0.20

Пути ниже относительно корня TACTIC-5.0. Диапазоны строк относятся к проверенному архиву, после правок могут сместиться. Это индекс, не утверждение о полном ручном code review каждого файла.

## Ключевые точки чтения

| Файл | Определения / строки |
|---|---|
| `src/tactic/ui_api/mount.py` | install L17–L89 |
| `src/tactic/ui_api/routing.py` | native_page L6–L18 |
| `src/tactic/ui_api/api.py` | Request L28–L35; Response L39–L42; Api L45–L268 |
| `src/tactic/ui_api/tactic_backend.py` | TacticBackend L20–L181 |
| `src/tactic/ui_api/config_backend.py` | ConfigBackend L29–L574 |
| `src/tactic/ui_api/extended_backend.py` | ExtendedBackend L53–L453 |
| `src/tactic/core/config_model.py` | parse_xml L21–L31; xml_text L34–L35; revision L38–L39; view_node L42–L47; title L50–L56; ConfigSource L60–L74; ConfigModel L77–L168; target_spec L264–L285; SidebarProjection L288–L338; reorder_view L341–L354; patch_pipeline_positions L357–L375 |
| `src/tactic/core/view_resolution.py` | inline_xml L16–L22; resolve_table L25–L51; table_options L54–L78; configured_sort L81–L96 |
| `src/tactic/core/cell_edit_config.py` | cell_config L9–L21; save_config L24–L48; CellConfigModel L51–L81 |
| `src/tactic/core/widget_containers.py` | false L19–L20; tab_model L23–L84; tab_items L87–L115; default_values L118–L132; edit_base_model L135–L164; resolve_edit L167–L187 |
| `src/tactic/core/native_edit.py` | ExplicitDatabaseAction L10–L29; ExplicitTaskDateAction L33–L35; ExplicitNonEmptyAction L37–L39; NativeEditCmd L41–L50; validated_form_values L59–L72; ExplicitPasswordAction L76–L81; NativeEditCmd L85–L96; NativeTableEditMultipleCmd L101–L103 |
| `src/tactic/ui_api/table_edit_service.py` | TableEditService L24–L218 |
| `src/tactic/ui_api/ui_state_service.py` | storage_key L16–L19; _names L22–L25; validate_state L28–L119; UiStateService L122–L188 |
| `src/tactic/ui_api/action_log.py` | plain L48–L52; names L55–L58; query_shape L61–L80; RequestTrace L83–L189; ensure_monitor L192–L205; command_started L208–L212; execute_traced L215–L224; resolved L228–L230; authenticated L233–L235; parameters L238–L240; client_events L243–L272; short_target L275–L281; human L284–L311; JsonFormatter L314–L315; ConsoleFormatter L318–L319; NativeAccessFilter L322–L331; configure L334–L359; emit L362–L369; ActionLogTailer L372–L408 |
| `tools/local/control.py` | clean_path L33–L43; checked_int L46–L55; validate_profile L58–L73; read_profile L76–L87; save_profile L90–L114; make_parser L117–L154; parse L157–L168; effective L171–L195; Plan L199–L203; plan_command L206–L256; display_plan L259–L264; execute L267–L301; update_profile L304–L323; settings_menu L326–L352; interactive L355–L416; main L419–L443 |
| `tools/local/cluster.py` | atomic_json L29–L33; Cluster L36–L171; preflight L174–L181; main L184–L222 |
| `tools/local/cluster_gateway.py` | is_balanced L26–L28; filtered_headers L31–L34; RoutingPool L37–L59; Gateway L62–L159 |
| `tools/local/cluster_worker.py` | watchdog L15–L25; run_worker L28–L46; main L49–L54 |

Для полной сигнатуры и методов класса см. `inventory/native_code_index.json`; JSON сохраняет несколько одноимённых class definitions как отдельные entries.

## Все native/core/tools Python-модули

Docstring ниже — первый текст исходника, иногда с историческим номером выпуска. Его наличие не считается доказательством готовности. Хеш каждого модуля и точные методы находятся в JSON.

| Файл | Строк | Назначение по docstring / определениям |
|---|---:|---|
| `src/tactic/core/__init__.py` | 1 | Server-side services extracted from TACTIC UI. No eager UI imports. |
| `src/tactic/core/admin_commands_017.py` | 700 | Original administration commands separated from presentation (0.17). |
| `src/tactic/core/bootstrap.py` | 110 | Business bootstrap; does not import web widgets. Called once by WebInit. |
| `src/tactic/core/cell_edit_config.py` | 81 | CellEditWdg config resolution, without rendering any legacy HTML. |
| `src/tactic/core/checkin_policy.py` | 43 | Fail-closed boundaries of native single-file check-in. |
| `src/tactic/core/collection_commands.py` | 206 | Original collection commands moved out of the widget module. |
| `src/tactic/core/config_commands.py` | 24 | Legacy configuration test command kept separate from metadata imports. |
| `src/tactic/core/config_model.py` | 375 | Presentation-free projection of TACTIC widget configs. |
| `src/tactic/core/config_options.py` | 62 | Original WidgetConfig option shapes without importing a display class. |
| `src/tactic/core/context_actions.py` | 45 | Original SubContextAction, moved out of the presentation package. |
| `src/tactic/core/context_menus.py` | 76 | Typed native actions for original SmartMenu activation scopes. |
| `src/tactic/core/design_document.py` | 179 | Lossless *targeted* editing of original widget_config documents. |
| `src/tactic/core/edit_commands.py` | 658 | EditCmdException, EditCmd, EditMultipleCmd, RelatedDatabaseAction |
| `src/tactic/core/field_policy.py` | 17 | Field and sidebar access rules extracted from TableLayoutWdg / panel_wdg. |
| `src/tactic/core/filter_data.py` | 166 | FilterData |
| `src/tactic/core/format_value.py` | 491 | Non-HTML formatting algorithm extracted from original FormatElementWdg. |
| `src/tactic/core/graph_model.py` | 203 | Loss-preserving native graph editing over the original TACTIC XML. |
| `src/tactic/core/license_commands.py` | 53 | RenewLicenseCbk |
| `src/tactic/core/message_commands.py` | 72 | ChatCmd moved from tactic.ui.app.message_wdg into server-side code. |
| `src/tactic/core/messaging.py` | 125 | Presentation-free semantics of TACTIC subscriptions and message rendering. |
| `src/tactic/core/native_edit.py` | 103 | JSON value adapter around the ORIGINAL EditCmd and field action sequence. |
| `src/tactic/core/native_settings.py` | 46 | Persistent native-UI switches; separate from original TACTIC XML configuration. |
| `src/tactic/core/notification_filters.py` | 29 | Original hidden My Notifications filter, extracted without UI imports. |
| `src/tactic/core/pipeline_commands.py` | 196 | Original workflow save command, moved out of its visual editor. |
| `src/tactic/core/process_commands.py` | 715 | Original process-property operations extracted from pipeline_wdg.py. |
| `src/tactic/core/process_constants.py` | 2 | Shared trigger storage namespace; originally TriggerToolWdg.FOLDER_PREFIX. |
| `src/tactic/core/project_creation.py` | 80 | Native project creation keeps CreateProjectCmd's lifecycle. |
| `src/tactic/core/query_model.py` | 447 | Bounded, typed queries and compatibility with TACTIC's saved search format. |
| `src/tactic/core/schema_commands.py` | 794 | Original SearchType creation command, extracted from the widget module. |
| `src/tactic/core/schema_health.py` | 48 | Read-only structural readiness checks for the stock native UI, not a DBA audit. |
| `src/tactic/core/search_code_migration.py` | 40 | Original 4.0 parent search_id -> search_code repair, callable in-process. |
| `src/tactic/core/search_filters.py` | 444 | Original GeneralFilterWdg's server-side column filter engine. |
| `src/tactic/core/security_commands.py` | 53 | Group membership command extracted from the original admin widget module. |
| `src/tactic/core/sidebar_config.py` | 339 | Original TACTIC sidebar configuration order, extracted from panel_wdg.py. |
| `src/tactic/core/sidebar_edits.py` | 78 | Bounded, loss-preserving edits of ONE original sidebar view. |
| `src/tactic/core/sqlite_upgrade.py` | 443 | SQLite dialect adapter for the *managed offline* TACTIC upgrade. |
| `src/tactic/core/system_config_model.py` | 110 | Data projection of DbConfigContentWdg, without HTML or restart side effects. |
| `src/tactic/core/table_settings.py` | 107 | Original BaseTableLayoutWdg.get_setting, independent of presentation imports. |
| `src/tactic/core/task_choices.py` | 56 | Metadata providers extracted from TACTIC task input widgets. |
| `src/tactic/core/timeline_model.py` | 52 | Date-window projection of configured Gantt intervals, not a scheduler. |
| `src/tactic/core/view_edits.py` | 91 | Targeted widget_config edits; preserve every unmodified XML extension. |
| `src/tactic/core/view_resolution.py` | 96 | Resolve the TABLE-specific config branches of BaseTableLayoutWdg.__init__. |
| `src/tactic/core/widget_config.py` | 1875 | WidgetConfigException, WidgetConfig, WidgetConfigView |
| `src/tactic/core/widget_containers.py` | 187 | Data-only parts of TabWdg/EditWdg. No Wdg construction or browser code. |
| `src/tactic/core/work_hours.py` | 185 | Original WorkHoursElementAction extracted from the presentation package. |
| `src/tactic/ui_api/__init__.py` | 1 | Native Vue transport within the existing TACTIC server. |
| `src/tactic/ui_api/action_log.py` | 408 | Bounded, structured native action log. NEVER serializes request/response bodies. |
| `src/tactic/ui_api/admin_service.py` | 136 | Finite native administration commands. No arbitrary class/method execution endpoint. |
| `src/tactic/ui_api/admin_workspace.py` | 63 | Server-owned child views of the stock administration widgets. |
| `src/tactic/ui_api/api.py` | 268 | Finite application API mounted in TACTIC; tests inject a separate fixture backend. |
| `src/tactic/ui_api/cell_value_service.py` | 106 | Native values for explicit original display handlers (never column-name guesses). |
| `src/tactic/ui_api/cluster_runtime.py` | 48 | Local cluster hooks; never evaluate class paths or accept public proxy headers. |
| `src/tactic/ui_api/collection_service.py` | 174 | Native collection tools over original _is_collection / *_in_* storage. |
| `src/tactic/ui_api/column_service.py` | 182 | Typed cell presentation over original field configs; raw data stays separate. |
| `src/tactic/ui_api/config_backend.py` | 574 | TACTIC-native UI service. Sidebar and screens originate in original configs. |
| `src/tactic/ui_api/contracts.py` | 197 | Transport-independent input validation. No TACTIC or web-framework imports. |
| `src/tactic/ui_api/csv_service.py` | 132 | Bounded native CSV export of the SAME authorized, configured table Search. |
| `src/tactic/ui_api/design_service.py` | 317 | Native Custom Layout / Manage Views, backed only by original widget_config. |
| `src/tactic/ui_api/extended_backend.py` | 453 | Version 0.5 source-fork backend: native semantic providers and original config routes. |
| `src/tactic/ui_api/file_payload.py` | 9 | Private server-side file delivery descriptor; never serialized to browser JSON. |
| `src/tactic/ui_api/global_admin_service.py` | 313 | Native handlers for the original Global administration widgets. |
| `src/tactic/ui_api/graph_service.py` | 330 | Native schema/workflow operations backed by the existing TACTIC commands. |
| `src/tactic/ui_api/history_service.py` | 92 | Read original history tables; retire/reactivate via original SObject methods. |
| `src/tactic/ui_api/menu_service.py` | 54 | Read-only context menu descriptor resolved from authorized widget target. |
| `src/tactic/ui_api/message_service.py` | 335 | Native message/subscription UI over the original TACTIC tables and commands. |
| `src/tactic/ui_api/mount.py` | 89 | Native UI at normal /tactic/PROJECT paths, within the original CherryPy server. |
| `src/tactic/ui_api/project_service.py` | 106 | Finite ProjectCreateWdg workflow. No arbitrary template/file/class input. |
| `src/tactic/ui_api/record_service.py` | 178 | Notes, schema relationships, versions and file delivery through original TACTIC models. |
| `src/tactic/ui_api/relationship_service.py` | 114 | Instance membership through SObject.add_instance/remove_instance. |
| `src/tactic/ui_api/routing.py` | 18 | Classify native page requests without intercepting XML-RPC/REST/assets. |
| `src/tactic/ui_api/script_service.py` | 219 | Native saved-script editor, preserving ShelfEditWdg storage/save semantics. |
| `src/tactic/ui_api/search_type_service.py` | 190 | Project SearchType editor: original registry + column/config commands. |
| `src/tactic/ui_api/security_service.py` | 261 | Original TACTIC security matrices and explicit group assignment (native 0.17). |
| `src/tactic/ui_api/session.py` | 63 | Short-lived, in-memory browser sessions. TACTIC tickets never leave the server. |
| `src/tactic/ui_api/shared_sessions.py` | 77 | Private local SQLite transport sessions shared by a single native cluster. |
| `src/tactic/ui_api/sidebar_service.py` | 103 | Native ManageViewPanelWdg over the original config/widget_config model. |
| `src/tactic/ui_api/system_diagnostics.py` | 44 | Read-only projection of real TACTIC database metadata for SystemInfoWdg. |
| `src/tactic/ui_api/table_edit_service.py` | 218 | Native CellEditWdg and Save Changes, over the original command lifecycle. |
| `src/tactic/ui_api/tactic_backend.py` | 181 | Adapter for the public TACTIC 5.0 source API; mounted INSIDE its CherryPy process. |
| `src/tactic/ui_api/task_service.py` | 182 | Native task workspace using the original Task/Pipeline/EditCmd services. |
| `src/tactic/ui_api/thumbnail_service.py` | 109 | Registered preview files for the ordinary ThumbWdg table column. |
| `src/tactic/ui_api/timeline_service.py` | 59 | Server-paginated date windows over the original configured TACTIC Search. |
| `src/tactic/ui_api/ui_state_service.py` | 188 | Per-user view state in ORIGINAL sthpw/wdg_settings / WidgetSettings. |
| `src/tactic/ui_api/upload_service.py` | 100 | Original simple_checkin at the end of a bounded resumable staging session. |
| `src/tactic/ui_api/upload_store.py` | 311 | Bounded, disk-backed staging, NOT an alternative TACTIC asset repository. |
| `src/tactic/ui_api/version.py` | 4 | Single source of native UI version for runtime and build diagnostics. |
| `src/tactic/ui_api/version_service.py` | 102 | Snapshot browsing and original set_current_snapshot; no direct flag updates. |
| `src/tactic/ui_api/view_service.py` | 162 | Resolve/edit actual TACTIC views; no client-local replacement configuration. |
| `src/tactic/ui_api/widget_service.py` | 136 | Authorized composed widget routes. Definitions always originate on server. |
| `src/tactic/ui_api/work_hour_service.py` | 169 | Configured work-hour cells executed by the original WorkHoursElementAction. |
| `tools/local/cluster.py` | 229 | Local TACTIC native cluster: one gateway and three ORIGINAL server processes. |
| `tools/local/cluster_gateway.py` | 159 | Bounded localhost-only WSGI reverse proxy used with bundled Cheroot. |
| `tools/local/cluster_worker.py` | 56 | One ORIGINAL TACTIC process owned by the local supervisor. Not a fixture. |
| `tools/local/configure_native.py` | 44 | Explicit local configuration of native UI write switches. No database access. |
| `tools/local/control.py` | 452 | Shared controller for three local TACTIC launchers. Standard library only; delegates to original tools. |
| `tools/local/launch.py` | 269 | Run the ORIGINAL TACTIC CherryPy server, with a private project-local runtime. |
| `tools/local/local_lock.py` | 48 | Cooperative local server/upgrade lock, with shared cluster lifetime ownership. |
| `tools/local/managed_sqlite.py` | 237 | Stage/validate/publish a managed LOCAL SQLite upgrade; no in-place retry. |
| `tools/local/sqlite_worker.py` | 85 | Internal worker: run ORIGINAL TACTIC upgrade methods only on staged databases. |
| `tools/local/startup_probe.py` | 28 | Inspect objects produced by actual CherryPyStartup, without starting a listener. |
| `tools/local/validate_pip_zipapp.py` | 34 | Reject a cached HTML/partial download before invoking the official pip zipapp. |
| `tools/native_ui/audit_config_parity.py` | 69 | Differential comparison of original TACTIC metadata on SHIPPED XML only. |
| `tools/native_ui/audit_source.py` | 125 | Reproducible inventory/diff against the uploaded TACTIC archive. |
| `tools/native_ui/inventory_widgets.py` | 72 | Index all first-party UI candidates and static call/config references. |

## Frontend components

Фактический build-list находится в `tools/native_ui/build.cjs`. Ниже исходные SFC, не 50 независимых legacy-экранов: часть — поля, меню, диалоги и панели.

| Компонент | Строк |
|---|---:|
| `frontend/src/App.vue` | 213 |
| `frontend/src/components/AdminPanel.vue` | 51 |
| `frontend/src/components/AdvancedFilter.vue` | 13 |
| `frontend/src/components/CodeEditor.vue` | 14 |
| `frontend/src/components/CollectionPanel.vue` | 39 |
| `frontend/src/components/ConfigAudit.vue` | 7 |
| `frontend/src/components/ConfigEditor.vue` | 32 |
| `frontend/src/components/ConfiguredForm.vue` | 32 |
| `frontend/src/components/ConfiguredTable.vue` | 264 |
| `frontend/src/components/ConfiguredTabs.vue` | 32 |
| `frontend/src/components/ContextMenu.vue` | 29 |
| `frontend/src/components/CsvExport.vue` | 7 |
| `frontend/src/components/CsvImportPanel.vue` | 17 |
| `frontend/src/components/CustomLayoutEditor.vue` | 22 |
| `frontend/src/components/EmbeddedForm.vue` | 18 |
| `frontend/src/components/FieldInput.vue` | 17 |
| `frontend/src/components/FilePanel.vue` | 28 |
| `frontend/src/components/FilterGroup.vue` | 27 |
| `frontend/src/components/GlobalSettings.vue` | 23 |
| `frontend/src/components/GraphEditor.vue` | 45 |
| `frontend/src/components/GroupMembership.vue` | 16 |
| `frontend/src/components/HistoryPanel.vue` | 16 |
| `frontend/src/components/LayoutPreview.vue` | 59 |
| `frontend/src/components/ManageViews.vue` | 23 |
| `frontend/src/components/MessageCenter.vue` | 41 |
| `frontend/src/components/MessageContent.vue` | 9 |
| `frontend/src/components/ProjectWizard.vue` | 38 |
| `frontend/src/components/RecordInspector.vue` | 29 |
| `frontend/src/components/RelationTree.vue` | 7 |
| `frontend/src/components/RelationTreeRow.vue` | 18 |
| `frontend/src/components/RelationshipEditor.vue` | 17 |
| `frontend/src/components/ScriptEditor.vue` | 52 |
| `frontend/src/components/SearchTypes.vue` | 39 |
| `frontend/src/components/SecurityMatrix.vue` | 41 |
| `frontend/src/components/SidebarEditor.vue` | 34 |
| `frontend/src/components/SidebarNode.vue` | 17 |
| `frontend/src/components/SubscriptionPanel.vue` | 11 |
| `frontend/src/components/TableColumns.vue` | 19 |
| `frontend/src/components/TableToolbar.vue` | 101 |
| `frontend/src/components/TaskPanel.vue` | 43 |
| `frontend/src/components/TaskTimeline.vue` | 44 |
| `frontend/src/components/UploadQueue.vue` | 67 |
| `frontend/src/components/UserGroups.vue` | 17 |
| `frontend/src/components/UserManager.vue` | 13 |
| `frontend/src/components/ViewDesigner.vue` | 26 |
| `frontend/src/components/WidgetCell.vue` | 26 |
| `frontend/src/components/WidgetDefinition.vue` | 7 |
| `frontend/src/components/WidgetHost.vue` | 55 |
| `frontend/src/components/WidgetTable.vue` | 59 |
| `frontend/src/components/WorkHoursPanel.vue` | 20 |

## Как читать статические статусы

1. `PARTIAL_RENDERER_CANDIDATE`: краткое или полное имя совпало с явной регистрацией renderer. Нужно проверить фактический экспорт и supported options; это не full parity.
2. `NATIVE_REFERENCE_REQUIRES_REVIEW`: имя/путь встретились в native-коде. Это может быть command, dependency или unsupported guard, а не реализованный интерфейс.
3. `NO_NATIVE_MAPPING_EVIDENCE`: индекс не нашёл такого свидетельства. Нельзя автоматически объявлять класс ненужным или полностью отсутствующим: он может обслуживаться общим механизмом, наследованием или динамической конфигурацией.
4. `NOT_INDIVIDUALLY_REVIEWED`: у файла нет индивидуального поведенческого заключения в этом handoff.
5. `VENDORED_SUPPORT_NOT_SCREEN`: известный vendor-каталог; это поддерживающие JS/CSS, не собственный TACTIC UI-screen.
6. `PARSE_ERROR_REVIEW_REQUIRED`: AST не разобран; файл не отбрасывать как успешно просмотренный.

Перечень кандидатов сформирован поставляемым сканером inventory_widgets.py и дополнен свежими регистрациями/ссылками. Его встроенный исторический словарь REVIEWED не использован как текущая готовность. Поддержка UI объявляется в `UI_PARITY_MATRIX.json` на уровне конкретного семейства и ограничений, не выводится автоматически из совпадения строки.

Legacy-ref cap: до 120 фрагментов на класс, native-ref cap: до 100. Полные количества и усечение указаны отдельно. Short-name collisions — candidates. Working DB configs, external plugins и генерируемые class paths не были предоставлены этому статическому проходу.

`api_route_index.json` содержит 85 найденных literal путей и места ссылок. Это не OpenAPI и не полная таблица HTTP methods/permissions. Gateway flags читаются отдельно; допустимость метода определяется Api.dispatch/service.
`explicit_unsupported_guards.json` содержит 30 явных raise ApiError(501...) в выбранном коде. Это не весь backlog: существуют diagnostics, read_only, ошибки других кодов, отсутствие renderer и частичная реализация без 501.

## Источники исторических свидетельств

`evidence/RELEASE_0.20_Verification.json` и `RELEASE_0.20_README_RU.md` — сохранённые выпускные документы. Их тесты не повторялись при handoff.
`evidence/source-maps/` — включённые в архив исторические карты перемещений классов/файлов. Они помогают найти исходные алгоритмы, но не заменяют современную матрицу. Ограничение раннего выпуска может быть позже снято; проверять фактический код.
`SNAPSHOT_FACTS.json` — только свежая проверка хешей и статической структуры.

В начальном обсуждении Vite/TypeScript/Vue Flow были предложением. Здесь они не дописаны в описание кода задним числом. Fail-before-publication отчёты прошлых попыток также не считаются source-релизами.

## Разница между архивной и функциональной целостностью

CRC/SHA совпадение доказывает, что передан ожидаемый набор байтов. Оно не доказывает, что приложение запускается, поддерживает все виджеты или безопасно работает с production-данными. Функциональная приёмка требует отдельно указанных тестов на определённой конфигурации и платформе.
