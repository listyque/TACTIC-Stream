# ![TACTIC Stream](tactic_stream/docs/assets/readme/wordmark.svg)

**Производственная платформа, которая связывает данные, людей, процессы и файлы.**

[English](README.md) · **[Начать работу](#начать-работу)** · [Почему Stream](#почему-stream) · [Обзор возможностей](tactic_stream/docs/presentations/product-tour.ru.md) · [Документация](tactic_stream/docs/index.md)

Опишите устройство вашей студии, задайте маршрут работы и соберите команду в общем браузерном пространстве. TACTIC Stream объединяет настраиваемые объекты, исполняемый workflow-движок, планирование, ревью и версии опубликованных файлов. TACTIC Handler дополняет его нативным настольным клиентом.

![Item View TACTIC Stream: визуальные ассеты в настоящем рабочем пространстве проекта](tactic_stream/docs/assets/product-tour/item-view.png)

> **Прототип в разработке.** Stream активно развивается. Perforce-like File Workspace также остаётся прототипом.

## Почему Stream

Форк развивает модель данных, workflow, права и публикации TACTIC в современном Python-сервере и Vue-интерфейсе. **Stream** — связанный путь от входящей работы через ревью к сдаче результата.

- **Сохранить основу TACTIC.** Объекты, отношения, пайплайны и snapshots остаются базовыми понятиями производства.
- **Сделать проект настраиваемым.** Визуальные редакторы открывают доступ к схемам, workflow, неймингу, sidebar, раскладкам и правилам доступа.
- **Связать браузер и desktop.** Tactic Frame описывает общие интерфейсы для Vue и нативного Qt Quick; Handler добавляет локальные репозитории и Maya.

[Что унаследовано от TACTIC, что меняет Stream и зачем →](tactic_stream/docs/presentations/product-tour.ru.md#зачем-существует-проект)

## Начать работу

| Вариант запуска | С чего начать |
| --- | --- |
| **Windows / SQLite** | [Инструкция для переносимого пакета](tactic_stream/docs/delivery/WINDOWS_DELIVERY.en.md): локальное приложение, репозиторий и дополнительный нативный Handler. |
| **Linux / PostgreSQL** | [Развёртывание сервера](tactic_stream/docs/delivery/SERVER_DELIVERY.en.md): Docker Compose, Apache и отдельная база данных. |
| **Из исходников** | [Локальная разработка](tactic_stream/README.md#local-development): Python 3.14, editable-установка и лаунчер репозитория. |

При первом запуске установщик предложит задать пароль администратора. Откройте или создайте проект, настройте его данные и подключите команду.

## Возможности Stream

### За графом стоит исполняемый движок

Опишите ручную работу, действия, условия, согласования и зависимости. Сервер исполняет настроенные переходы, а графический редактор и инспектор процесса показывают их правила. Задачи и публикации остаются связаны с объектами, которые проходят этот маршрут.

![Редактор Workflow: связанные этапы производства и ревью](tactic_stream/docs/assets/product-tour/workflow.png)

[Workflow: от описания к исполнению →](tactic_stream/docs/presentations/product-tour.ru.md#workflow--исполняемый-движок-процессов)

### Соберите интерфейс под вашу команду

Работайте через Item View, непрерывное дерево или таблицу. Разделяйте и объединяйте доки, чтобы объекты, задачи, заметки и превью оставались рядом. Sidebar Editor, Item Layouts и редакторы страниц адаптируют навигацию и представления под отдел.

![Композиция доков: визуальные объекты, задачи и превью публикаций](tactic_stream/docs/assets/product-tour/docks-planning.png)

[Item View →](tactic_stream/docs/presentations/product-tour.ru.md#рабочее-пространство-начинается-с-объекта) · [Доки →](tactic_stream/docs/presentations/product-tour.ru.md#доки-собрать-интерфейс-под-конкретную-работу) · [Sidebar Editor →](tactic_stream/docs/presentations/product-tour.ru.md#sidebar-editor-навигация-как-часть-рабочего-процесса)

### У плана появляются исполнители и сроки

Task Manager, Gantt и календарь связывают назначения, расписание и прогресс. Notes сохраняют решения ревью у объекта, Messages поддерживает разговор команды. Обзор объекта и история сервера помогают восстановить контекст событий.

![Gantt: производственные задачи в расписании команды](tactic_stream/docs/assets/product-tour/gantt.png)

[Планирование →](tactic_stream/docs/presentations/product-tour.ru.md#планирование-и-ежедневная-работа) · [Notes и Messages →](tactic_stream/docs/presentations/product-tour.ru.md#общение-с-сохранением-контекста)

### Файлы сохраняют производственный контекст

Чекин связывает файлы с объектом, процессом и версией. Naming Editor задаёт имена и пути репозитория, Snapshot Browser возвращает к нужной публикации. Нативный Handler расширяет этот сценарий локальной синхронизацией Repository Sync и действиями со сценами Maya.

![Snapshot Browser: публикации Survey Drone и предпросмотр файлов](tactic_stream/docs/assets/product-tour/snapshot-browser.png)

[Чекин, версии, нейминг и сдача →](tactic_stream/docs/presentations/product-tour.ru.md#от-рабочего-файла-к-отслеживаемой-публикации)

### Превратите данные в рабочую страницу

Соберите показатели, диаграммы, Item View и действия в Dashboard Editor. Создайте обзор производства, страницу отдела или рабочее место ревьюера, реагирующее на выбранный объект.

![Кастомный дашборд: показатели проекта, загрузка команды и визуальные записи](tactic_stream/docs/assets/product-tour/dashboard-overview.png)

[Дашборды и визуальное создание страниц →](tactic_stream/docs/presentations/dashboards.ru.md)

### Задайте вопрос в контексте проекта

Встроенный помощник изучает реальные записи, объясняет результаты и готовит операции через доступные инструменты. Сохраняйте выбранный объект в контексте разговора и проверяйте, на чём основан ответ.

![Помощник проекта изучает производственные записи](tactic_stream/docs/assets/product-tour/assistant.png)

[Чат-бот: провайдеры, инструменты и возможности →](tactic_stream/docs/presentations/assistant.ru.md)

### Соберите общий справочник команды

База знаний связывает разделы и статьи с объектами проекта. Пишите в Visual или Markdown, прикладывайте файлы, сохраняйте черновики и публикуйте инструкции с историей редакций.

![База знаний: чеклист сдачи, связанный с производственным ассетом](tactic_stream/docs/assets/product-tour/knowledge-base.png)

[База знаний: подготовка и публикация материалов →](tactic_stream/docs/presentations/knowledge-base.ru.md)

Встроенная справка объясняет само приложение: контекстные статьи, поиск по темам, русский и английский языки и выгрузка Markdown доступны прямо в рабочем пространстве.

![Встроенная справка: документация приложения и каталог тем с поиском](tactic_stream/docs/assets/product-tour/help.png)

[Презентация встроенной справки →](tactic_stream/docs/presentations/help.ru.md)

## Развивайте платформу под свой процесс

| Область | Подробнее |
| --- | --- |
| **Модель и администрирование** | [Схемы и визуальные редакторы](tactic_stream/docs/presentations/product-tour.ru.md#administration-настройка-самого-проекта), [пользователи и права](tactic_stream/docs/presentations/product-tour.ru.md#пользователи-группы-и-итоговые-права), [конфигурация](tactic_stream/docs/presentations/product-tour.ru.md#configuration-подключение-хранение-и-ежедневные-настройки). |
| **Контекст и события** | [Обзор объекта](tactic_stream/docs/presentations/product-tour.ru.md#обзор-объекта-целостная-производственная-запись) и [история сервера](tactic_stream/docs/presentations/product-tour.ru.md#история-на-сервере-понять-что-произошло). |
| **Скрипты и интеграции** | [Script Editor и полки](tactic_stream/docs/presentations/product-tour.ru.md#script-editor-полки-и-автоматизация), [серверные API](tactic_stream/docs/admin_agent/SOURCES.md#ts-server-api), [окружение разработчика](tactic_stream/README.md). |
| **Язык интерфейса** | [Tactic Frame](tactic_stream/docs/presentations/product-tour.ru.md#tactic-frame-единое-описание-два-нативных-интерфейса): общее описание UI, нативные контролы Vue и Qt Quick. |

**[Полный обзор продукта →](tactic_stream/docs/presentations/product-tour.ru.md)** · [Вся документация](tactic_stream/docs/index.md)

Скриншоты сняты в текущем приложении на изолированном Orbit Studio; данные и иллюстрации демонстрационные. Stream и Handler поставляются независимо. Совместимость с оригинальным TACTIC описана в [карте проверок и ограничений](tactic_stream/docs/compatibility.md).

Основан на [Southpaw TACTIC](https://github.com/Southpaw-TACTIC/TACTIC). [Лицензия TACTIC](tactic_stream/LICENSE.TACTIC) · [Лицензии компонентов](tactic_stream/docs/presentations/product-tour.en.md#scope-and-provenance).
