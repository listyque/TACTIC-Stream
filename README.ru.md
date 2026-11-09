# TACTIC Stream

### От входящей работы до готового результата

Настраиваемая производственная платформа: данные проекта, workflow, команда и опубликованные файлы в одном рабочем пространстве. Python · Vue · Tactic Frame.

[English](README.md) · [Почему Stream](#purpose) · [Полный обзор](tactic_stream/docs/presentations/product-tour.ru.md) · [Начать работу](#start)

![TACTIC Stream: визуальный обзор ассетов проекта](tactic_stream/docs/assets/product-tour/item-view.png)

> **Прототип в активной разработке.** Perforce-like File Workspace также остаётся прототипом.

<a id="purpose"></a>
## Основа TACTIC. Рабочее пространство Stream.

Stream продолжает модель TACTIC: настраиваемые сущности, связи, pipelines, права и версии файлов. Форк развивает её вместе с современным Python-сервером, браузерным интерфейсом и визуальными редакторами. Название отражает непрерывную передачу работы — от задачи через ревью к публикации.

[Зачем появился форк и что он меняет →](tactic_stream/docs/presentations/product-tour.ru.md#purpose)

<a id="workspace"></a>
<a id="docks"></a>
<a id="sidebar"></a>
## Интерфейс под работу вашей команды

Item View, дерево и таблицы показывают одни и те же записи с разной детализацией. Доки соединяют объекты, задачи и превью в рабочее место. Редакторы карточек, страниц и sidebar позволяют настроить его под отдел или конкретный процесс.

![Компоновка для планирования и ревью: объекты, задачи и публикации](tactic_stream/docs/assets/product-tour/docks-planning.png)

[Item View →](tactic_stream/docs/presentations/product-tour.ru.md#workspace) · [Доки →](tactic_stream/docs/presentations/product-tour.ru.md#docks) · [Sidebar Editor →](tactic_stream/docs/presentations/product-tour.ru.md#sidebar)

<a id="workflow"></a>
## Workflow связывает этапы производства

Опишите маршрут объекта: ручная работа, действия, условия, согласование и зависимости. Серверный движок выполняет настроенные переходы, а граф и инспектор помогают видеть логику процесса.

![Workflow: граф производственного процесса](tactic_stream/docs/assets/product-tour/workflow.png)

[Workflow engine: от определения до исполнения →](tactic_stream/docs/presentations/product-tour.ru.md#workflow)

<a id="planning"></a>
<a id="communication"></a>
## План, исполнители и решения — вместе

Task Manager, Gantt и календарь помогают распределять работу и сроки. Notes сохраняет обсуждение объекта или этапа; Messages — разговор команды. Из обзора объекта и серверной истории можно восстановить контекст решения.

![Gantt: задачи команды на временной шкале](tactic_stream/docs/assets/product-tour/gantt.png)

[Планирование →](tactic_stream/docs/presentations/product-tour.ru.md#planning) · [Messages →](tactic_stream/docs/presentations/product-tour.ru.md#communication) · [Обзор объекта →](tactic_stream/docs/presentations/product-tour.ru.md#object-overview) · [История →](tactic_stream/docs/presentations/product-tour.ru.md#history)

<a id="files"></a>
## Файлы сохраняют производственный контекст

Check-in связывает публикацию с объектом, процессом и версией. Naming Editor определяет имена и размещение. Snapshot Browser показывает опубликованные файлы и превью; Handler добавляет локальный Repository Sync и интеграцию с Maya.

![Snapshot Browser: две настоящие публикации Survey Drone](tactic_stream/docs/assets/product-tour/snapshot-browser.png)

[Публикация, версии и naming →](tactic_stream/docs/presentations/product-tour.ru.md#files)

<a id="assistant"></a>
<a id="dashboards"></a>
## Данные проекта становятся рабочими инструментами

| Встроенный ассистент | Кастомные дашборды |
| --- | --- |
| ![Ассистент готовит сводку по данным выбранного объекта](tactic_stream/docs/assets/product-tour/assistant.png) | ![Дашборд производства: метрики, статусы, загрузка и ассеты](tactic_stream/docs/assets/product-tour/dashboard-overview.png) |
| Вопросы по реальным записям, подготовка изменений и видимые операции. **[Отдельная презентация →](tactic_stream/docs/presentations/assistant.ru.md)** | Метрики, диаграммы, Item View и действия на странице команды. **[Отдельная презентация →](tactic_stream/docs/presentations/dashboards.ru.md)** |

<a id="frame"></a>
<a id="scripting"></a>
<a id="administration"></a>
<a id="people"></a>
<a id="object-overview"></a>
<a id="history"></a>
<a id="configuration"></a>
## Настройка от схемы данных до интерфейса

**Tactic Frame** описывает общие интерфейсы для Vue и нативного Qt Quick. Визуальные редакторы, Script Editor, полки инструментов и серверные API позволяют развивать проект вместе с производством.

[Tactic Frame →](tactic_stream/docs/presentations/product-tour.ru.md#frame) · [Скрипты →](tactic_stream/docs/presentations/product-tour.ru.md#scripting) · [Администрирование →](tactic_stream/docs/presentations/product-tour.ru.md#administration) · [Пользователи и права →](tactic_stream/docs/presentations/product-tour.ru.md#people) · [Конфигурация →](tactic_stream/docs/presentations/product-tour.ru.md#configuration)

<a id="start"></a>
## Начать работу

[Windows / SQLite](tactic_stream/docs/delivery/WINDOWS_DELIVERY.ru.md) · [Linux / PostgreSQL](tactic_stream/docs/delivery/SERVER_DELIVERY.ru.md) · [Запуск из исходников](tactic_stream/docs/presentations/product-tour.ru.md#start) · [Вся документация](tactic_stream/docs/index.md)

Снимки сделаны в текущем приложении на изолированном Orbit Studio; данные и иллюстрации демонстрационные. [Границы совместимости](tactic_stream/docs/compatibility.md) · [Лицензия TACTIC](tactic_stream/LICENSE.TACTIC) · [Исходный Southpaw TACTIC](https://github.com/Southpaw-TACTIC/TACTIC).
