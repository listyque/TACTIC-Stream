# Compact workspace shell — 0.19

| Источник | Изменение | Сохранено |
|---|---|---|
| `frontend/src/App.vue` | Удалён page hero; действия в tabbar; безопасное обновление редактора | Вкладки, права меню, renderer dispatch, существующие endpoints |
| `CustomLayoutEditor.vue` | Удалён повторный title; индикатор черновика в toolbar | Секции, исходный XML, сохранение, preview и вложенные widgets |
| `ManageViews.vue` | Вместо title только selector SearchType | Каталог, layers, copy/delete/save и дизайнер |
| `ScriptEditor.vue` | Компактные команды без title-блока | Ace, предупреждения, save/diff/run и состояние |
| `SearchTypes.vue` | Создание рядом с каталогом, без hero | Метаданные, поля, исходные команды и CSV |
| `SidebarEditor.vue` | XML-команда в той же панели, что раздел | Исходные операции над widget_config |
| `SecurityMatrix.vue` | Компактная группа команд | Категории и исходные callbacks |
| `GlobalSettings.vue`, `AdminPanel.vue` | Без дублирующего названия страницы | Секции/поля конфигурации, диагностика и сохранение |
| `MessageCenter.vue`, `CollectionPanel.vue` | Только действия и контекст | Кнопки, записи, навигация и preview |
| `ProjectWizard.vue` | Шаги без рекламного вступления | Все стадии, поля и реальное создание проекта |
| `ConfigEditor.vue` | Удалён повторный section-intro | XML, слои, поля и сохранение |
| `ConfiguredForm.vue` | Скрыт повторный title embedded-вида; исправлено доступное имя при show_header=false | Диалоговый title, поля, section headings, defaults/actions/save |
| `styles.css` | Общая compact-toolbar, отступы и геометрия | Темы, пользовательские заголовки внутри Shadow DOM, меню и таблицы |

Серверные Python-источники и SQL/config/BAT не изменены. Конкретные изменённые файлы и SHA-256 — в `changes-from-0.18.json`, текстовый diff — в `changes-from-0.18.patch`.

Новые проверки: `test_compact_shell_019.cjs` (реальные методы App и source-contract), `run_browser_compact_019.py` (исходный backend и реальный собранный Vue), `run_cluster_019.py` (полный прежний HTTP-набор и новый браузерный набор).

Удаляется chrome приложения, не заголовки, заданные пользователем как содержимое Custom Layout. Видимые заголовки диалогов и настоящих разделов форм намеренно остаются компактными: это функциональная ориентация внутри окна, а не повторный title страницы.
