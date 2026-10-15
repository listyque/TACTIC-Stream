# Штатные разделы и текущая диспетчеризация

Статическое чтение file-only конфигурации; не проверка полного поведения и не экспорт рабочей БД.
`table` показывает список, а не подтверждает готовность специальных ячеек/форм. `unsupported` не заменять случайной таблицей.

## admin_views

| Пункт | Исходный handler | Native kind | SearchType / view |
|---|---|---|---|
| Create Project (`create_project`) | `LinkWdg` | `project-create` | `` / `table` |
| Global (`global_admin`) | `SideBarSectionLinkWdg` | `folder` | `` / `_global_admin` |
| Project (`project_admin`) | `SideBarSectionLinkWdg` | `folder` | `` / `_project_admin` |
| Separator (`separator`) | `SeparatorWdg` | `separator` | `` / `table` |
| Project Essentials (`project_essentials`) | `SideBarSectionLinkWdg` | `folder` | `` / `_project_essentials` |

## _global_admin

| Пункт | Исходный handler | Native kind | SearchType / view |
|---|---|---|---|
| Projects (`projects`) | `LinkWdg` | `table` | `sthpw/project` / `table` |
| Template Projects (`template_projects`) | `LinkWdg` | `table` | `sthpw/project` / `template` |
| Separator (`separator`) | `SeparatorWdg` | `separator` | `` / `table` |
| Users (`users`) | `LinkWdg` | `table` | `sthpw/login` / `table` |
| Groups (`groups`) | `LinkWdg` | `table` | `sthpw/login_group` / `table` |
| Users In Groups (`users_in_groups`) | `LinkWdg` | `group-membership` | `sthpw/login_group` / `user_to_group_planner` |
| Global Translations (`global_translations`) | `LinkWdg` | `table` | `sthpw/translation` / `table` |
| Separator (`separator`) | `SeparatorWdg` | `separator` | `` / `table` |
| Exception Log (`exception_log`) | `LinkWdg` | `table` | `sthpw/exception_log` / `table` |
| Debug Log (`debug_log`) | `LinkWdg` | `table` | `sthpw/debug_log` / `table` |
| Widget Settings (`wdg_settings`) | `LinkWdg` | `table` | `sthpw/wdg_settings` / `table` |
| Separator (`separator`) | `SeparatorWdg` | `separator` | `` / `table` |
| License (`license`) | `LinkWdg` | `license` | `` / `table` |
| System Info (`system_info`) | `LinkWdg` | `system` | `` / `table` |
| System Config (`system_config`) | `LinkWdg` | `system-config` | `` / `table` |
| Database Resource (`db_resource`) | `LinkWdg` | `table` | `sthpw/db_resource` / `table` |

## _project_admin

| Пункт | Исходный handler | Native kind | SearchType / view |
|---|---|---|---|
| Configuration (`project_configuration`) | `LinkWdg` | `search-types` | `` / `table` |
| Manage Users (`manage_users`) | `LinkWdg` | `users` | `` / `table` |
| Manage Security (`manage_security`) | `LinkWdg` | `security` | `` / `table` |
| Custom Layout Editor (`_custom_layout_editor`) | `LinkWdg` | `layout-editor` | `` / `table` |
| Lists of Items (`lists_of_items`) | `LinkWdg` | `search-types` | `` / `table` |
| Dashboards (`dashboards_homepage`) | `LinkWdg` | `unsupported` | `` / `table` |
| Reports (`reports_homepage`) | `LinkWdg` | `unsupported` | `` / `table` |
| Separator (`separator`) | `SeparatorWdg` | `separator` | `` / `table` |
| Project Schema (`project_schema`) | `LinkWdg` | `schema` | `` / `table` |
| Project Workflow (`project_workflow`) | `LinkWdg` | `pipeline` | `` / `table` |
| Manage Side Bar (`manage_side_bar`) | `LinkWdg` | `sidebar-editor` | `` / `table` |
| Separator (`separator`) | `SeparatorWdg` | `separator` | `` / `table` |
| Manage Views (`manage_views`) | `LinkWdg` | `views-manager` | `` / `table` |
| Manage sTypes (`manage_search_types`) | `LinkWdg` | `search-types` | `` / `table` |
| Separator (`separator`) | `SeparatorWdg` | `separator` | `` / `table` |
| Script Editor (`script_editor`) | `LinkWdg` | `script-editor` | `` / `table` |
| Plugins (`plugins`) | `LinkWdg` | `unsupported` | `` / `table` |
| Free Form Layout Tool (`freeform`) | `LinkWdg` | `unsupported` | `` / `table` |

## _my_admin

| Пункт | Исходный handler | Native kind | SearchType / view |
|---|---|---|---|
| Manage My Views (`manage_my_views`) | `LinkWdg` | `sidebar-editor` | `` / `my_view` |
| My Preference (`my_preference`) | `LinkWdg` | `table` | `sthpw/pref_list` / `user` |

## _project_essentials

| Пункт | Исходный handler | Native kind | SearchType / view |
|---|---|---|---|
| Project Tasks (`project_tasks`) | `LinkWdg` | `table` | `sthpw/task` / `table` |
| Project Milestones (`project_milestones`) | `LinkWdg` | `table` | `sthpw/milestone` / `table` |
| Notes (`project_notes`) | `LinkWdg` | `table` | `sthpw/note` / `table` |
| Work Hours (`project_work_hours`) | `LinkWdg` | `table` | `sthpw/work_hour` / `table` |
| Snapshots (`project_snapshots`) | `LinkWdg` | `table` | `sthpw/snapshot` / `table` |
| Translations (`project_translations`) | `LinkWdg` | `table` | `config/translation` / `table` |
| Separator (`separator`) | `SeparatorWdg` | `separator` | `` / `table` |
| Naming (`config_naming`) | `LinkWdg` | `table` | `config/naming` / `table` |
| Process (`config_process`) | `LinkWdg` | `table` | `config/process` / `table` |
| Widget Config (`config_widget_config`) | `LinkWdg` | `table` | `config/widget_config` / `table` |
| Server Triggers (`config_trigger`) | `LinkWdg` | `table` | `config/trigger` / `table` |
| Custom URL (`config_custom_url`) | `LinkWdg` | `table` | `config/url` / `table` |
| Notifications (`sthpw_notification`) | `LinkWdg` | `table` | `sthpw/notification` / `table` |
| Project Settings (`project_settings`) | `LinkWdg` | `table` | `config/prod_setting` / `table` |
| Separator (`separator`) | `SeparatorWdg` | `separator` | `` / `table` |
| Schema (`sthpw_schema`) | `LinkWdg` | `table` | `sthpw/schema` / `manage` |
| Pipelines (`sthpw_pipelines`) | `LinkWdg` | `table` | `sthpw/pipeline` / `manage` |

## project_view

| Пункт | Исходный handler | Native kind | SearchType / view |
|---|---|---|---|
