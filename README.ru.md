# TACTIC Stream

[English](README.md) · **Русский** · [Документация](tactic_stream/docs/index.md)

**Сервер TACTIC для самостоятельного развёртывания и рабочее пространство в браузере.**
Создавайте Item View для ассетов, шотов и других записей проекта. Ведите задачи
и публикации, настраивайте схемы, пайплайны и права в веб-интерфейсе на Vue
с ядром TACTIC на Python.

Stream использует SQLite для локального запуска и PostgreSQL для серверного
развёртывания. Отдельный настольный клиент **TACTIC-Handler** может подключаться
к Stream для работы с локальными файлами и Maya.

> **Прототип в разработке.** Perforce-like workspace и просмотр его данных
> в браузере — отдельный незавершённый прототип.

![Настроенный Item View проекта Orbit Studio в TACTIC Stream](tactic_stream/docs/assets/github-item-view.png)

## Item View

Создавайте именованные раскладки карточек и строк для каждого Search Type.
Размещайте превью, поля объекта и действия для открытия деталей или заметок.
Проверьте раскладку на данных проекта, сохраните её как представление
и переиспользуйте в блоках дашборда.
[Руководство по раскладкам объектов](tactic_stream/frontend/public/help/item_layouts.ru.md) · [Скриншот таблицы](tactic_stream/docs/assets/github-workspace.png)

## Возможности

- **Ведение проектов.** Поиск объектов, планирование задач, заметки и просмотр
  снапшотов в браузере.
- **Администрирование.** Типы объектов, пайплайны, раскладки, права доступа
  и ресурсы проектов.
- **Публикация и файлы.** Серверные операции с публикациями и репозиториями.
  Просмотр депо и списков изменений входит в Perforce-like прототип.
- **Интеграции.** Справка API работающего сервера и модель проектов, SearchType,
  SObject и команд TACTIC.

## Локальный запуск на Windows

Выполните команды из корня рабочей копии. Понадобятся Python 3.14 и чистый
локальный каталог данных.

```powershell
Set-Location tactic_stream
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
..\START_TACTIC_STREAM.bat
```

При первом запуске программа инициализирует SQLite, предлагает задать пароль
администратора и открывает настроенный локальный адрес. Готовый веб-интерфейс
входит в комплект. [Подробности запуска и CLI](tactic_stream/README.md#local-development)

Перед запуском новой версии с существующими данными сделайте резервную копию.
Скрипт обновляет схему перед стартом сервера. [Резервное копирование и восстановление](tactic_stream/docs/delivery/RECOVERY_ACCEPTANCE.md)

## Развёртывание и документация

| Задача | Где начать |
| --- | --- |
| Попробовать портативную сборку | [Поставка для Windows](tactic_stream/docs/delivery/WINDOWS_DELIVERY.ru.md) |
| Запустить отдельный сервер PostgreSQL | [Серверная поставка с Docker Compose](tactic_stream/docs/delivery/SERVER_DELIVERY.ru.md) |
| Обновить или восстановить установку | [Резервное копирование и восстановление](tactic_stream/docs/delivery/RECOVERY_ACCEPTANCE.md) |
| Сделать интеграцию | [Карта API сервера](tactic_stream/docs/admin_agent/SOURCES.md#ts-server-api) · [Совместимость](tactic_stream/docs/compatibility.md) |
| Посмотреть примеры плагинов | [Workspace Pulse](examples/workspace_pulse/README.ru.md) · [Studio Review](examples/studio_review/README.ru.md) |
| Работать с исходным кодом | [Среда разработки](tactic_stream/README.md) · [Архитектура](tactic_stream/docs/architecture.md) |

Проверяйте совместимость со схемами, плагинами и
сценариями вашей установки. Работающий сервер публикует справку по адресам
`/api/documentation` и `/api/compatibility`.

## Лицензионные уведомления

[Оригинальный TACTIC](tactic_stream/LICENSE.TACTIC) · [QuickJS-NG](tactic_stream/LICENSE.QUICKJS-NG) · [Vue](tactic_stream/frontend/public/LICENSE.VUE.txt) · [Наборы иконок](tactic_stream/frontend/public/licenses/icon-fonts/SOURCES.md)
