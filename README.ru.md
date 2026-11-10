# ![TACTIC Stream](tactic_stream/docs/assets/readme/wordmark.svg)

**Управление ассетами и производством.**

[English](README.md) · **[Начать работу](#запуск-и-первый-проект)** · [Почему Stream](#что-изменилось-в-stream) · [Обзор возможностей](tactic_stream/docs/presentations/product-tour.ru.md) · [Документация](tactic_stream/docs/index.md)

TACTIC Stream объединяет модель проекта, задачи, workflow и версионное хранение файлов. В нём студия описывает свои объекты — ассеты, шоты, документы — и настраивает работу с ними. Основной интерфейс работает в браузере; для локальных файлов и Maya есть настольный клиент TACTIC Handler.

![Item View TACTIC Stream: ассеты проекта](tactic_stream/docs/assets/product-tour/item-view.png)

> **Прототип в разработке**, в том числе Perforce-like File Workspace.

## Что изменилось в Stream

Основа Stream — TACTIC с его настраиваемыми объектами, связями, pipelines и правилами публикации. Форк развивает эту систему на Python 3.14, с новым браузерным приложением на Vue и визуальными редакторами. Сервер и интерфейс меняются вместе: настройка схемы, процессов и представлений входит в само приложение.

Название Stream относится к прохождению работы через этапы производства. У ассета есть задачи и решения ревью, а сданные файлы записаны в snapshots. Эти связи нужны при передаче между отделами: завершённая задача и готовый к использованию файл — разные вещи. Общее описание интерфейсов Tactic Frame используется в Stream и нативном Handler.

[Что унаследовано от TACTIC, что меняет Stream и зачем →](tactic_stream/docs/presentations/product-tour.ru.md#что-изменилось-в-stream)

## Запуск и первый проект

| Вариант запуска | С чего начать |
| --- | --- |
| **Windows / SQLite** | [Инструкция для переносимого пакета](tactic_stream/docs/delivery/WINDOWS_DELIVERY.en.md): локальное приложение, репозиторий и дополнительный нативный Handler. |
| **Linux / PostgreSQL** | [Развёртывание сервера](tactic_stream/docs/delivery/SERVER_DELIVERY.en.md): Docker Compose, Apache и отдельная база данных. |
| **Из исходников** | [Локальная разработка](tactic_stream/README.md#local-development): Python 3.14, editable-установка и лаунчер репозитория. |

При первом запуске установщик предложит задать пароль администратора. Откройте или создайте проект, настройте его данные и подключите команду.

## Работа в Stream

### Движок Workflow

В Workflow настраивается маршрут работы, в том числе параллельные этапы, условия и согласования. Сервер обрабатывает события по правилам pipeline: создаёт задачи, вызывает действия и отправляет уведомления. В редакторе виден граф целиком и параметры каждого узла.

![Редактор Workflow: связанные этапы производства и ревью](tactic_stream/docs/assets/product-tour/workflow.png)

[Workflow: от описания к исполнению →](tactic_stream/docs/presentations/product-tour.ru.md#workflow-граф-и-исполнение)

### Настройка рабочего пространства

Панели с объектами, задачами, превью и заметками можно расставить рядом, объединить во вкладки и сохранить раскладку. Sidebar Editor задаёт навигацию отдела, Item Layouts — карточки объектов, редактор страниц — дашборды. Эти настройки используют данные одного проекта.

![Композиция доков: визуальные объекты, задачи и превью публикаций](tactic_stream/docs/assets/product-tour/docks-planning.png)

[Item View →](tactic_stream/docs/presentations/product-tour.ru.md#item-view-и-поиск) · [Доки →](tactic_stream/docs/presentations/product-tour.ru.md#доки-и-раскладки) · [Sidebar Editor →](tactic_stream/docs/presentations/product-tour.ru.md#sidebar-editor)

### Task Manager и Gantt

В Task Manager назначаются исполнители, даты и статусы. Gantt показывает расписание и пересечения работ. Из задачи можно открыть объект и его обсуждение; переписка доступна в Messages. Изменения плана и статусов сохраняются в истории проекта.

![Gantt: производственные задачи в расписании команды](tactic_stream/docs/assets/product-tour/gantt.png)

[Планирование →](tactic_stream/docs/presentations/product-tour.ru.md#планирование) · [Notes и Messages →](tactic_stream/docs/presentations/product-tour.ru.md#messages-и-notes)

### Публикации и версии файлов

Чекин сохраняет файл у объекта и процесса, присваивает версию и применяет правила имён и каталогов. Snapshot Browser показывает публикации и их содержимое. В Handler доступны локальная синхронизация репозитория и открытие сцен в Maya.

![Snapshot Browser: публикации Survey Drone и предпросмотр файлов](tactic_stream/docs/assets/product-tour/snapshot-browser.png)

[Чекин, версии, нейминг и сдача →](tactic_stream/docs/presentations/product-tour.ru.md#чекин-и-чекаут)

### Дашборды

Dashboard Editor собирает на одной странице показатели, диаграммы, таблицы и Item View. К выбранному объекту можно привязать подробности и действия. На снимке — сводка по задачам и загрузке команды с навигатором ассетов.

![Кастомный дашборд: показатели проекта, загрузка команды и визуальные записи](tactic_stream/docs/assets/product-tour/dashboard-overview.png)

[Дашборды и визуальное создание страниц →](tactic_stream/docs/presentations/dashboards.ru.md)

### Помощник проекта

Помощник читает записи выбранного проекта, составляет отчёты и готовит изменения через доступные ему инструменты. В примере ниже он разобрал Survey Drone: моделинг отмечен завершённым, а публикации модели ещё нет. Подробности вызванных операций доступны рядом с ответом.

![Помощник проекта изучает производственные записи](tactic_stream/docs/assets/product-tour/assistant.png)

[Чат-бот: провайдеры, инструменты и возможности →](tactic_stream/docs/presentations/assistant.ru.md)

### База знаний и справка

В базе знаний хранятся инструкции, требования к сдаче и технические заметки. Статьи можно связать с объектами проекта и дополнить файлами. Редактор работает в Visual и Markdown; есть черновики, публикация и история редакций.

![База знаний: чеклист сдачи, связанный с производственным ассетом](tactic_stream/docs/assets/product-tour/knowledge-base.png)

[База знаний: подготовка и публикация материалов →](tactic_stream/docs/presentations/knowledge-base.ru.md)

Встроенная справка описывает инструменты и настройки приложения. Она открывается из рабочих окон, поддерживает поиск, русский и английский языки и выгрузку статьи в Markdown.

![Встроенная справка: документация приложения и каталог тем с поиском](tactic_stream/docs/assets/product-tour/help.png)

[Презентация встроенной справки →](tactic_stream/docs/presentations/help.ru.md)

## Конфигурация и разработка

| Область | Подробнее |
| --- | --- |
| **Модель и администрирование** | [Схемы и визуальные редакторы](tactic_stream/docs/presentations/product-tour.ru.md#администрирование-проекта), [пользователи и права](tactic_stream/docs/presentations/product-tour.ru.md#пользователи-и-права), [конфигурация](tactic_stream/docs/presentations/product-tour.ru.md#configuration). |
| **Контекст и события** | [Обзор объекта](tactic_stream/docs/presentations/product-tour.ru.md#обзор-объекта) и [история сервера](tactic_stream/docs/presentations/product-tour.ru.md#activity-feed-и-история-проекта). |
| **Скрипты и интеграции** | [Script Editor и полки](tactic_stream/docs/presentations/product-tour.ru.md#script-editor-и-автоматизация), [серверные API](tactic_stream/docs/admin_agent/SOURCES.md#ts-server-api), [окружение разработчика](tactic_stream/README.md). |
| **Язык интерфейса** | [Tactic Frame](tactic_stream/docs/presentations/product-tour.ru.md#tactic-frame): общее описание UI, нативные контролы Vue и Qt Quick. |

**[Полный обзор продукта →](tactic_stream/docs/presentations/product-tour.ru.md)** · [Вся документация](tactic_stream/docs/index.md)

Скриншоты сняты в текущем приложении на изолированном Orbit Studio; данные и иллюстрации демонстрационные. Stream и Handler поставляются независимо. Совместимость с оригинальным TACTIC описана в [карте проверок и ограничений](tactic_stream/docs/compatibility.md).

Основан на [Southpaw TACTIC](https://github.com/Southpaw-TACTIC/TACTIC). [Лицензия TACTIC](tactic_stream/LICENSE.TACTIC) · [Лицензии компонентов](tactic_stream/docs/presentations/product-tour.en.md#compatibility-limitations-and-licenses).
