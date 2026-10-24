# TACTIC Stream

Свой тактик. Простой запуск. Рабочее название — **TACTIC Stream**.

Самостоятельный backend на Python 3.14, FastAPI и Uvicorn с Vue админкой, версия 0.112.199.
Он сохраняет понятия TACTIC и начинает перенос его API. Это начало новой
реализации; полная совместимость API 1:1 пока не достигнута.

Цель — сохранить публичный API оригинального TACTIC для любых существующих
клиентов, интеграций и проектов, чтобы они могли перейти на TACTIC Stream.
Объём переноса задают исходные контракты TACTIC. Handler — один из клиентов,
на которых проверяется совместимость.

Два целевых комплекта поставки и подключение готового Handler закреплены в
[HANDLER_DEPLOYMENT.md](HANDLER_DEPLOYMENT.md). Клиент Handler используется
без изменений; его основные операции проверены на SQLite локально и на
PostgreSQL через Apache. Windows EXE/Electron и комплектование Handler ещё
не готовы; эти проверки подтверждают backend, а не всю поставку.

Мобильные итемы открываются отдельными экранами со сдвигом: объект, содержимое,
связь/процесс, снапшот и версии. Касание или свайп влево открывают уровень;
«Назад», свайп вправо и история браузера возвращают список с его прокруткой.
Собжекты сохраняют скруглённые карточки, круглое превью и цвет типа; файлы,
связи и процессы отличаются визуально. Просмотр файлов и инспектор задач/
заметок используют существующие операции. Описание механизма — в EN/RU Help → Mobile.

Сквозное требование — запуск существующих кастомных серверных Python скриптов
без правок, как в оригинальном TACTIC: те же `pyasm`/`tactic` импорты, классы,
объекты, методы, контекст проекта/пользователя, результаты и ошибки, транзакции,
триггеры и эффекты в БД. При переносе ядра проверяется неизменённое тело скрипта
в обоих окружениях на временных данных. Пока зависимости скрипта не перенесены,
его совместимость остаётся незавершённой.

Интерфейс должен перестраиваться из исходных widget configs во время работы,
без пересборки Vue. Старые widget API сохраняют HTML контракты; современное
представление использует описание, независимое от frontend. Требования и
границы будущей реализации — в [UI_ARCHITECTURE.md](UI_ARCHITECTURE.md).

Актуальный [план оставшегося legacy — U01 / L01–L12](UI_ARCHITECTURE.md#legacy-plan)
отделяет незакрытый B07 от завершённых Frame-блоков: 40 упомянутых в конфигах
классов, затем поведение ядра/скриптов, процессы, проекты/плагины, БД и поставка.

Там же закреплён [контракт API для AI-помощника](UI_ARCHITECTURE.md#api-для-ai-помощника):
выборочный контекст с правами пользователя, draft/validate/preview/apply,
ревизии и идемпотентность, динамический Naming, изолированные script tests,
отдельная активация и тонкий MCP-адаптер. Это требования и план реализации;
новые AI операции и динамический Vue preview пока не доступны.

Целевые СУБД — PostgreSQL и MySQL; SQLite обеспечивает простой запуск без
отдельного сервера. Объекты и скрипты используют `Search`/`SObject`/`Sql`,
особенности базы — `DbResource`/`DatabaseImpl` и реализации vendors.
Первая установка должна сама создавать все нужные системные базы и таблицы;
создание проектной базы входит в команду создания проекта. Это обязательная
часть поддержки каждой СУБД, без ручной подготовки SQL пользователем.
Текущее перенесённое ядро запускается на SQLite и PostgreSQL. Для PostgreSQL перенесён
слой ядра: явные `DbResource`/`Sql`, `PostgresImpl`, метаданные, подготовка
`Insert`/`Update`, транзакции, savepoints, последовательности и JSON-счётчики.
В 0.23.0 `Search`/`SObject` читают проектные таблицы на ресурсе PostgreSQL из
`sthpw/db_resource`, включая метаданные, фильтры, связи, пагинацию и выбранные API чтения.
Проверены на PostgreSQL 18.6. В 0.24.0 конфигурация подключения и явные init/upgrade
создают новую PostgreSQL базу, системные таблицы, реестр и администратора.
В 0.25.0 системное чтение, авторизация администратора, аккаунты/группы/тикеты
и журнал работают на PG через native ядро. В 0.27.0 добавлены Task/Note/StatusLog
и завершение задачи в той же транзакции. В 0.26.0 добавлены обычные пользователи,
смена своего пароля, renewal и запуск сервера с монитором и воркерами на PG.
Это готовность текущего перенесённого объёма, не всего legacy API. MySQL ещё не перенесён.

Drupal CMS/session и коммерческое лицензирование TACTIC исключены из объёма:
ключи, сервер лицензий, лимиты, лицензионные методы и поле `license_type`.
Аккаунт блокируется через `s_status = 'retired'`. Это согласованное отличие
от оригинала. Старые хеши паролей и уведомления об авторских правах сохраняются.

Поставляемый пакет называется `tactic-stream`, команда запуска — `tactic-stream`.
Каталог и Python namespace — `tactic_stream`.
Совместимые импорты `pyasm`, названия классов ядра и XML-RPC адрес сохранены.

## Запуск

Linux-окружение Ubuntu/Apache/PostgreSQL в Docker запускается командой
`python deploy/docker/manage.py init`; подробности и команды обновления —
в [deploy/docker/README.md](deploy/docker/README.md). Админка этого окружения
доступна на порту 8082, его данные отделены от локального Windows-запуска.
Готовое окружение по умолчанию использует SQLite; новая системная установка
может использовать PostgreSQL через родной XML-конфиг. Автоматической миграции
существующей SQLite-базы в PostgreSQL нет.
В Ubuntu-контейнере Apache также установлен Webmin, HTTPS на localhost:10000;
его конфиг и изменения Apache сохраняются в отдельных volumes.

Двойной клик по `D:\code\TACTIC_VUE\START_TACTIC_STREAM.bat`. При первом запуске
он предложит задать пароль администратора, затем запустит сервер и откроет
`http://127.0.0.1:8081/` после готовности сервера. Окно показывает лог;
для остановки нажать Ctrl+C. Данные хранятся в `tactic_stream/data`.
Батник проверяет существующую настроенную базу через `init --if-needed`,
а не наличие файла SQLite. `TACTIC_DATA_DIR` задаёт другой каталог данных,
`TACTIC_CONFIG_PATH` — явный XML; они применяются ко всем трём шагам запуска.
Другой порт можно передать из консоли: `START_TACTIC_STREAM.bat --port 8082`.
Перед запуском BAT обновляет служебные таблицы существующей БД tactic_stream.
Повторное обновление ничего не меняет.
Встроенная справка → Guide → «Установка, обновление и приёмка» описывает
поддерживаемые vendors, резервирование, restart, сборку wheel и границы проверок.

Для установки окружения на другой машине или ручного запуска:

Из `D:\code\TACTIC_VUE\tactic_stream` в PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\tactic-stream.exe --data-dir .\data init
.\.venv\Scripts\tactic-stream.exe --data-dir .\data serve
```

После перемещения checkout обновить окружение через `python -m venv
--system-site-packages .venv`, затем выполнить `python -m pip install -e .`
командой выше. На Windows pip и остальные console scripts нужно переустановить,
поскольку они содержат абсолютный путь к Python. Данные находятся внутри проекта.

`init` запрашивает пароль нового администратора дважды. Создаёт собственную
пустую системную БД с восемнадцатью таблицами; существующий файл не перезаписывает.
Проекты, ассеты, задачи и пользователи legacy не копируются.
Пароль по умолчанию отсутствует. Повторять `init` перед каждым запуском не нужно.

При ручном запуске поверх предыдущей версии выполнить обновление один раз:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 run.py --data-dir .\data upgrade
```

Оно добавляет исходные таблицы `schema`, `project_type`, `transaction_log`,
`sobject_log`, `retire_log`, `change_timestamp`, `pipeline`, `trigger`, `notification`,
`sobject_list`, `pref_list` и `pref_setting`
с определениями в реестре. Правила и обработчики уведомлений не копируются.
Применяет миграцию `schema.project_code`, десять выбранных ADD COLUMN миграций
журналов, восемь ADD COLUMN миграций Pipeline и два исходных индекса transaction_log.
Для аккаунтов применяет шесть исходных ADD COLUMN: login.upn/display_name/data
и login_group.name/is_default/data. Старая колонка лицензирования при upgrade
остаётся неиспользуемой; новая БД её не содержит.
Существующие записи сохраняются.
Обновление выполняется в транзакции; конфликтующие определения не перезаписываются.

Сервер слушает `127.0.0.1:8081`. Доступны `/`, `/projects/<код>/`, `/docs`, `/health`,
`/api/compatibility` и исходный XML-RPC адрес `/tactic/default/Api/`.
`serve` можно запустить до `init`: документация и карта API доступны,
а запросы к БД возвращают ошибку. Данные при запуске сервера не создаются.

Альтернативный запуск из исходников: `python run.py --data-dir .\data serve`.
Для него FastAPI, Uvicorn и python-dateutil должны быть установлены в выбранный Python.

Регистрация пользователя выполняется администратором; пароли запрашиваются
интерактивно:

```powershell
.\.venv\Scripts\tactic-stream.exe --data-dir .\data register artist --first-name Ann --last-name Artist
```

`--group artists` добавляет пользователя в существующую группу; параметр
можно повторять. Команда использует исходный `Login.create`, проверяет все
группы перед записью и отзывает свой служебный билет после выполнения.

В текущем workspace уже создана `.venv` на Python 3.14.7 с доступом к установленным
FastAPI 0.141.1 и Uvicorn 0.52.4 через `--system-site-packages`; пакет установлен
в editable режиме. `setuptools`, `python-dateutil` и `six` установлены офлайн
из колёс `../legacy/.runtime/wheelhouse`. Для обычной установки на другой машине
использовать команды выше. Серверные зависимости зафиксированы в `pyproject.toml`.

## Монитор, воркеры и конфигурация

В 0.21.0 запуском управляет исходный по имени `pyasm.web.TacticMonitor`.
Монитор владеет дочерними процессами и слушающими сокетами. По умолчанию
он запускает три воркера на одном адресе `127.0.0.1:8081`; отдельный балансировщик
для локального запуска не требуется. Падение процесса приводит к его перезапуску.
Heartbeat проходит через event loop и пул обработки запросов: зависание цикла
или исчерпание пула обнаруживается по таймауту, после чего монитор завершает
этот воркер и запускает замену. Повторные сбои увеличивают задержку до 60 секунд.
Запросы, попавшие в зависший процесс, могут ждать до его завершения; монитор
не повторяет пользовательские запросы автоматически.

`init`, `upgrade` и первый `serve` создают `data/config/tactic-conf.xml`, если
собственного файла ещё нет. Существующий XML сохраняется. Шаблон входит в wheel;
его поля повторяют разделы Config самого TACTIC. `serve` создаёт конфиг и журналы,
но не создаёт БД. Config доступен как при старте, так и внутри серверного скрипта.
Сохранены XML v1 с атрибутами, v2 с элементами и раскрытие переменных окружения.
`Config.save_config()` требует администратора и публикует файл целиком через replace.

Выбор файла: `TACTIC_TMP_CONFIG_PATH`, затем `TACTIC_CONFIG_PATH`, затем
`<data-dir>/config/tactic-conf.xml`. `--config` задаёт TACTIC_CONFIG_PATH;
явно указанный отсутствующий XML вызывает ошибку. Параметры процессов применяются
при перезапуске монитора.

| Поле | По умолчанию | Назначение |
| --- | --- | --- |
| `install/hostname` | `127.0.0.1` | Адрес сервера; localhost приводится к IPv4. |
| `install/tmp_dir` | `<data-dir>/temp` | Временные файлы; относительный путь считается от data-dir. |
| `services/process_count` | `3` | Число процессов. |
| `services/thread_count` | `50` | Размер пула запросов каждого воркера. |
| `services/start_port` | `8081` | Общий порт. |
| `services/check_interval` | `1` | Интервал проверки в секундах. |
| `services/worker_timeout` | `120` | Максимальный возраст heartbeat. |
| `services/startup_timeout` | `60` | Срок получения первого heartbeat. |
| `services/shutdown_timeout` | `10` | Срок штатной остановки перед принудительным завершением. |
| `services/restart_delay` | `1` | Начальная задержка повторного запуска. |

`serve --workers 4 --port 8090` переопределяет число процессов и общий порт.
Для исходной схемы отдельных портов можно задать `services/ports` как
`8081|8082|8083`; переменная `TACTIC_PORTS` имеет приоритет. Каждый порт получает
свой воркер, число процессов определяется списком. CLI overrides общего порта
и конфликтующее число воркеров тогда отклоняются.

```powershell
.\.venv\Scripts\tactic-stream.exe --data-dir .\data status
.\.venv\Scripts\tactic-stream.exe --data-dir .\data stop
.\.venv\Scripts\tactic-stream.exe --data-dir .\data serve --workers 3
```

Ctrl+C, системные сигналы и `<tmp_dir>/log/stop.monitor` запрашивают штатную
остановку всех собственных воркеров; зависшие завершаются принудительно.
`monitor.json` содержит PID, состояние и число замен. `monitor.log` и
`worker.<index>.log` ротируются по 2 MiB с тремя архивами. ОС удерживает
`monitor.lock`, поэтому второй монитор той же конфигурации не вмешивается
в уже работающий сервер. PID из старого файла не используется для завершения
чужого процесса. При гибели родителя исправный воркер завершает себя.

Это перенос web lifecycle, а не всего старого monitor.py: очереди, scheduler,
watch folders, reload и attach режимы ещё не перенесены и отклоняются явно.
Сейчас database/vendor допускает Sqlite и PostgreSQL; MySQL ещё не перенесён.
Старые install/site параметры ещё не полностью
перенесены. Проверены семь сценариев реальных процессов и Config; они не
объявляются сравнением со старым HTTP сервером.

## PostgreSQL: первый слой ядра

В 0.22.0 `pyasm.search.PostgresImpl`, явные `DbResource(..., vendor='PostgreSQL')`
и `Sql` используют Psycopg 3.3.6. Драйвер — optional extra `tactic-stream[postgres]`;
SQLite-запуск не требует PostgreSQL или его драйвера. Соединение проверяет активного
пользователя в настроенной системной базе текущего request context.
Системная база и default resources берутся из собственного Config.

Перенесены исходные методы диалекта/DDL, метаданные типов/nullable/размера,
подготовка Insert/Update, commit/rollback, native Transaction без журнала,
savepoints, последовательности, regex и JSON-счётчики. `do_query` принимает
SELECT/VALUES и читающие CTE через server cursor. Savepoint с `transaction_read_only`
защищает от записи, управляющих SQL и нескольких statements; чтение видит pending
записи внешней транзакции, а выход восстанавливает её состояние. `SHOW`/utility SQL
через этот путь пока не поддержаны. `nextval` изменяет sequence и выполняется через
`do_update`; `currval` читается через `do_query`. Значение last_row_id не имитируется.

Исправлены исходные ошибки: quoted `now()`, boolean NULL, неверные `.nextval/.currval`,
reset sequence пустой таблицы, опечатка `get_db_resoure`, SQL identifiers/literals,
игнорирование length у serial и PostgreSQL Update с несколькими WHERE через запятую.
`use_cache=False` обновляет request metadata PostgreSQL; SQLite также обновляет metadata после DDL с этапа 0.50.0. Pool различает credentials/options, пользовательский autocommit
не может отключить native rollback. Разные connection identities с одним именем БД
в Transaction и несколько writable баз с PostgreSQL отклоняются до второго write:
согласованный commit между базами ещё не перенесён. SQLite-only raw transaction
сохраняет прежние возможности и не объявляется распределённо-атомарной.

```sh
python deploy/docker/manage.py check-postgres
```

Проверка использует текущие исходники в одноразовом контейнере, новую временную
SQLite-базу и случайную PG-схему. Проверяет CRUD, Unicode/кавычки, metadata refresh,
savepoint после SQL-ошибки, read guards, rollback/commit, request isolation,
ограничения обычного пользователя, неверный пароль и отключение транзакций, rollback
смешанной записи. Схема удаляется даже при неуспехе. 29 сравнений выбранных чистых
методов диалекта используют неизменённые исходные тела; известные исправления
проверяются отдельно. Это дополнение к прежним сравнениям SQLite и не полная
проверка старого PostgreSQL runtime. В 0.26.0 отдельно проверен текущий сервер
на временной системной PG базе: монитор, два воркера, health, Vue HTML, HTTP/JSON
и XML-RPC чтение/запись аккаунтов и корректная остановка процессов.

В 0.23.0 перенесён путь проектного чтения: исходные `project.database`,
`project.db_resource`, `sthpw/db_resource`, `DbResource.get_by_code` и
`Project.get_project_db_resource`. SQLite bootstrap/upgrade добавляет исходную
таблицу ресурса и колонку базы проекта транзакционно, без копирования подключений
или паролей из legacy. `Search`, `SearchType` и `SObject` используют ресурс проекта;
SQL placeholders, boolean и regex обрабатывает vendor. Фильтры, count, ids/codes,
joins/subqueries, связанные объекты и выбранный API чтения работают на PG.
Утилита проверяет отдельную временную проектную PG-базу и один неизменённый
скрипт на SQLite/PG, query и метаданные через API, pending read и rollback.
Эта проверка требует права CREATE DATABASE у тестового владельца Docker.
Системная SQLite остаётся отдельной, проектный SQLite-файл при чтении PG не создаётся.
Схема и временная база удаляются после проверки, рабочие данные не используются.

Исправления этой части: физическое имя проекта берётся из `project.database`,
join/subquery сравнивает полный ресурс соединения, обратная выборка связанных
объектов выполняется на ресурсе исходного поиска. PG table/view metadata не
раскрывает другие схемы; SObject возвращает настоящий vendor.
Ресурсы с паролями доступны только активным администраторам, включая joins и API.
Обычный пользователь читает через native Security/search_type/row правила.
Запись предметных SObject остаётся явно заблокированной. Следующий этап —
предметная запись и создание проектных баз исходной командой.

В 0.24.0 `init`/`upgrade` читают собственный `database/vendor`, `host`, `port`,
`user`, `password_file` (либо `password`) и `sobject_database` из tactic-conf.xml.
Для PostgreSQL нужен пакет `tactic-stream[postgres]` и право CREATE DATABASE;
служебное подключение установки идёт к базе `postgres`. Инициализация отказывается
менять любую существующую базу, даже пустую. Созданная этой командой база удаляется
при неуспешной установке; DDL/seed и upgrade выполняются транзакционно.
Определения таблиц и реестра общие с SQLite, serial/JSON преобразует PostgresImpl.
Проверены первый init, администратор/группа, отказ повторному init, идемпотентный
upgrade, откат при конфликте реестра и удаление базы после ошибки установки.
Первый bootstrap и работа текущего сервера проверяются раздельно.

В 0.25.0 Store читает системный реестр на настроенном ресурсе; логическое имя
sthpw соответствует physical sobject_database. Проверка активного администратора
в Sql не входит рекурсивно в Search/Store и читает ту же БД. Получение serial ID
перенесено из исходного SObject.commit: sequence/currval на том же соединении,
а явно заданный ID сохраняется. DatabaseImpl.get без vendor читает Config,
timestamp/expiry используют нужный диалект. Учтён исходный None результат
PostgresImpl.process_value для обычных timestamp; expiry, построенный самим vendor,
не отправляется в парсер текстовых дат.

На отдельной временной PG базе проверены вход/неверный пароль, renewal/revocation,
администратор через login_group, insert/update/delete выбранных account объектов,
transaction_log/sobject_log/change_timestamp и rollback неуспешной команды.
Одно неизменённое тело Python скрипта группы выполняется на SQLite и PG с одинаковым
предметным результатом. Все проверки создают свои данные; SQLite файл для PG системы
не нужен. Atomic journal сравнивает ресурсы, а не SQLite connection.in_transaction;
rollback очищает account/journal caches после PG записи. Согласованная запись
нескольких ресурсов ещё не перенесена.

В 0.26.0 обычный пользователь работает на PG в том же RequestContext/Security,
без SQLite файла. Смена своего пароля сохраняет исходный SObject/Transaction/
Trigger путь, журнал с настоящим автором и отзыв прежних тикетов. Native DML
для этого ограниченного системного пути связывает значения параметрами драйвера;
произвольный Sql.do_update остаётся доступен только реальному администратору,
включая вызовы из security-транзакции. Это явное ограничение перенесённого объёма:
полный raw SQL контракт legacy, произвольные unquoted выражения и Sudo-скрипты,
администрирующие чужие аккаунты от обычного пользователя, ещё не объявляются готовыми.
Собственные login/ticket изменения ограничены владельцем; журнал остаётся в той же
транзакции. Небезопасное выражение откатывает и предшествующие изменения.

Из исходного Sql взяты без изменения тел get_column_info, get_column_types и
is_in_transaction. Sql('sthpw') без явного ресурса читает конфигурацию, как в legacy.
Сохранено исходное database/server; database/host имеет приоритет, если задан.
Исправлены PG renewal с None от process_value и обработка атомарного JSON-счётчика
ошибок входа; vendor timestamp выражения распознаются внутри PostgresImpl.
Один неизменённый Python скрипт аккаунтов/группы/своего пароля выполняется на
SQLite и PostgreSQL с одинаковым предметным результатом.

Для новой установки на PG установить `tactic-stream[postgres]` и указать в
собственном tactic-conf.xml подключение к серверу и **новое** имя базы:

```xml
<config version="2">
  <database>
    <vendor>PostgreSQL</vendor>
    <server>127.0.0.1</server>
    <port>5432</port>
    <user>stream</user>
    <password_file>/path/to/postgres-password</password_file>
    <sobject_database>stream_system</sobject_database>
  </database>
</config>
```

```sh
tactic-stream --data-dir /path/to/tactic_data --config /path/to/tactic-conf.xml init
tactic-stream --data-dir /path/to/tactic_data --config /path/to/tactic-conf.xml serve
```

init создаёт системную базу, таблицы, реестр и аккаунт администратора; пароль
администратора вводится отдельно от пароля подключения к PostgreSQL. Существующую
базу init не трогает. Перенос уже работающей SQLite установки в PG этим не выполняется.
Текущее Docker окружение сохраняет рабочую SQLite базу, проверки PG используют новые
временные базы.

## Task, Note и StatusLog — 0.27.0

Из legacy взяты модули task.py, note.py, status.py и целые классы
RelatedTaskUpdateTrigger, TaskCompleteTrigger, StatusLogTrigger, DisplayNameTrigger.
Сохраняются наследование от SObject, импорты, имена и сигнатуры. Исходная схема,
реестр и выбранные upgrade-колонки создаются при init/upgrade на SQLite и PostgreSQL.
Виртуальные task/approval/dependency/progress/milestone/snapshot pipeline используют
исходные XML определения и не сохраняют строки при чтении.

Task.create и Note.create, связи с родителями, defaults, контексты, статусы,
actual_end_date, StatusLog и удаление работают через Command/Transaction/SObject.
insert/update/delete_sobject принимают эти системные типы; parent_key доступен
для Task/Note. Публичная запись пока требует администратора. API выполняется
локально с отключённой remote sync; очереди остаются отдельным незавершённым этапом.
Обычные пользователи читают заметки с исходным фильтром приватности: свои private
и public/NULL access. Этот фильтр применяется к строкам и count, включая поиск
по коду и ключу. JOIN к Note без перенесённой политики доступа явно отклоняется.
При ошибке откатываются данные, журнал, change timestamps и кеш записанных объектов.

Исправления относительно legacy проверяются отдельно от совпадающих результатов:

- Task.create больше не дублирует начальный StatusLog, который уже пишет CoreInit.
- TaskCompleteTrigger выполняется в той же транзакции, что статус: сбой обработчика
  откатывает обе операции. В сравнительном сценарии получается 5 журналов вместо
  6 и на 3 записи SObjectLog меньше: исчезают повторная начальная запись и отдельная
  транзакция завершения. Статусы, completion, родители, заметка и итоговые данные
  сравниваются с оригиналом; различия журналирования утверждаются явно.
- Pipeline читает строковое значение task_pipeline, а не сам ProjectSetting SObject.
- Старый Task.sort_shot_tasks использовал Python 2 cmp и sort(callback); сортировка
  теперь использует ключ. Исправлена опечатка timedelta/task_length в ветке дат.
- Палитра старого UI убрана из бизнес-кода; исходные цвета статусов сохранены.

TaskGenerator и базовый расчёт рабочих дней перенесены в 0.28.0 (см. ниже).
Полный CoreInit, custom Task workflow, TaskAutoSchedule, зависимое перепланирование,
Timecard/Milestone persistence и Snapshot ещё не готовы. Базовые состояния
process_state перенесены в 0.29.0.
Соответствующие неперенесённые операции не объявляются совместимыми. DisplayNameTrigger
доступен, но не включён в account startup до переноса полного CoreInit.

Проверка: неизменённый tests/scripts/business_contract.py запускается в реальном
оригинальном Python на временной SQLite базе, затем в Stream на SQLite и PostgreSQL.
XML-RPC отдельно проверяет Task/Note запись, родителей, завершение и откат пакета.
Рабочие пользовательские базы legacy не используются.

## Генерация задач по Pipeline — 0.28.0

Включены исходные Task.add_initial_tasks и TaskGenerator из task.py, методы
Pipeline.get_process_sobject/get_process_sobjects и пять календарных методов SPTDate.
Плоский граф без циклов создаёт задачи по процессам и выходным контекстам, учитывает
схождение ветвей, рабочие дни, XML/JSON workflow v1/v2, description, assigned_group
и встроенные task/approval pipeline. Узлы auto сами не создают задач, если их
task_creation не включён. Список processes сохраняет исходный отдельный алгоритм.
При пустом pipeline_code используется виртуальный publish граф.
schedule/projected_schedule возвращают несохранённые временные задачи.

XML-RPC/JSON получили create_task и add_initial_tasks с исходными сигнатурами.
Операции требуют администратора и идут через ApiClientCmd/Command, транзакцию,
журнал и StatusLog. Сбой посреди генерации откатывает весь набор, записи журналов,
change timestamps и кеш объектов. Объекты родителей могут читаться из проектных
баз; сами задачи записываются в настроенную системную базу. Запись конфигурации
Pipeline/process пока не перенесена.

Отдельно проверенные исправления legacy: skip_duplicate=False действительно
создаёт новые контексты /001, проверка дублей не путает output и output_extra,
JSON duration/bid_duration принимают целые числа, отрицательное число рабочих дней
сдвигает дату назад. В устаревшем режиме context устранена передача depend_id
в позицию assigned. Родитель без колонки pipeline_code использует publish fallback.
Дата начала прямого TaskGenerator.execute по умолчанию — сегодня, полдень;
даты из БД нормализуются перед сравнением, чтобы PostgreSQL timezone не вызывал TypeError.

Сравнение: tests/scripts/generation_contract.py запускается без изменения тела
в настоящем оригинальном Python и в Stream на временной SQLite установке:
граф, явные процессы, дубли, JSON числа, два режима preview и календарь.
Тот же DAG сценарий с повторным созданием проверен на реальном PostgreSQL и SQLite.
XML-RPC проверен напрямую и неизменёнными SDK оригинального TACTIC и Handler.

Иерархия, циклы, wildcard/межграфовые/expression связи, custom task pipelines
и настроенные TaskAutoSchedule режимы явно отклоняются. Состояния process_state
добавлены в 0.29.0, callbacks — в 0.30.0, ограниченный цикл графа — в 0.31.0.
Ошибки API пока частично
совместимы: обратный диапазон create_task даёт ValueError вместо legacy ApiException
с ExceptionLog; полный контракт ошибок и логирования ещё не перенесён.

## Состояния Workflow и сообщения — 0.29.0

workflow.py взят целиком из legacy с исходными классами и импортами pyasm.command.
Включены базовые методы состояния BaseProcessTrigger и BaseWorkflowNodeHandler:
get_process_state/get_process_status/log_message, store_state/retrieve_state/
restore_state/get_state, build_trigger_input, проверка входов и обновление задач.
Ниже описан этап 0.29.0; процессные обработчики включены в 0.31.0.
Наличие классов в модуле не означает готовности полного движка.

Как в оригинале, статусы пишутся в message/message_log и config/process_state;
данные и packages узла — в сообщения. Внутренний вызов использует исходную
SObject ветку ApiXMLRPC.log_message в текущей транзакции, без клиентского SDK
и соединения сервера с самим собой. PostgreSQL использует этот же путь с правами,
журналом и триггерами. API get_message/get_messages/log_message сохраняет исходные
сигнатуры; insert/update/delete_sobject принимают эти типы и process_state.
Запись требует администратора и настроенного системного ресурса.

init/upgrade автоматически создаёт исходные message, message_log и
spt_process_state с реестром. config/process_state сохраняет исходный database
{project}: admin использует системную базу. Запись состояния в отдельные проектные
базы ещё закрыта до создания проектных схем и согласованной межбазовой записи.
StatusLogTrigger для process_state включается при первом обращении к типу.
Rollback очищает также кеш Workflow; удаление состояния не оставляет старый объект
в этом кеше. Подписки и доставка уведомлений ещё не перенесены.

Исправления проверены отдельно от совпадающего поведения:

- get_state читает message из словаря, вместо попытки JSON-декодирования словаря.
- is_complete для входа без задачи проверяет тип входящего процесса.
- set_all_tasks восстанавливает прежний internal флаг в finally при сбое commit.
- SearchKey читает вложенный ключ родителя в code сообщения; исходный формат
  build_search_key сохранён. Символы ?/&/=/| внутри кода не становятся частями типа
  или старым type|id; обычные ключи и порядок project/db параметров сохранены.
- log_message возвращает OK на SQLite и PostgreSQL; legacy SQLite возвращал None.
- PostgreSQL принимает строковые статусы в исходной JSON колонке process_state,
  сохраняя то же значение SObject, что SQLite.

Проверки: неизменённый tests/scripts/workflow_contract.py в реальном оригинальном
Python и Stream; отдельные ожидания исправленных ошибок, состояния/история/
StatusLog, восстановление кеша после отката и запрет записи обычному пользователю.
Тот же сценарий проверен на настоящем PostgreSQL и SQLite. XML-RPC проверяет
сообщения и откат обновлений process_state, а исходные SDK TACTIC/Handler —
get_message/log_message; get_messages проверяется прямым XML-RPC вызовом.
Рабочие данные legacy не используются.

Python callbacks добавлены в 0.30.0, process handlers, TaskStatusChangeTrigger и
request-local Workflow.init — в 0.31.0. Полный CoreInit остаётся закрыт до переноса
его обязательных обработчиков, включая Snapshot.

## Серверные Python скрипты и callbacks — 0.30.0

PythonCmd/PythonTrigger и CustomScript перенесены из исходных модулей целиком;
старый startup импорт и демонстрационный main исключены. PythonCmd сохраняет
Mako выполнение, return, kwargs/input/server и исходные объекты в аргументах.
Mako 1.3.12 — runtime зависимость, проверенная на Python 3.14.
CustomScript.get_by_path и PythonTrigger используют исходные folder/title;
триггер сначала ищет config/custom_script, затем sthpw/custom_script.
Исправлен выбор PythonTrigger при NULL class_name; исключения базы при поиске
центрального скрипта больше не скрываются общим except.

Включён BaseProcessTrigger.run_callback: on_status, on_status_path и исходный
process event fallback. Контекст содержит sobject/pipeline/process/status/data,
входы/выходы и packages. В 0.30.0 cbjs/server_js явно отклонялись; с 0.112.39
PythonTrigger поддерживает server_js через JsCmd, cbjs остаётся неподдержанным.
Полный Workflow ещё
ограничен поддерживаемыми узлами, описанными в разделе 0.31.0 ниже.

Исходный tactic_client_lib SDK включён в пакет. Его local настройка использует
выбранные ApiXMLRPC методы в текущем request/Command/Transaction, без HTTP и
без отдельного коммита. Неперенесённые API методы и return_sobjects всё ещё
отклоняются. SDK не может менять проект или переживать контекст запроса.
Прямой PythonCmd поддерживает code/script_path/file_path; файл читается как UTF-8.

API execute_python_script(ticket, script_path, kwargs={}) возвращает исходный
{status, description, info}. Начиная с 0.64 по сети поддерживаются сохранённый
script_path, inline code и file_path, как в оригинальном PythonCmd; сохранённый
путь имеет приоритет над code/file_path. Проверяются api_method/api_cmd правила,
исполнение требует активной транзакции и настоящего сохранённого администратора;
Sudo не даёт права запускать Python. Это доверенный серверный код, не sandbox.
Права на исполнение отдельных скриптов и запуск обычным пользователем ещё не
перенесены. Ошибка откатывает и записи через local server, и журнал.

init/upgrade создаёт исходные custom_script/spt_custom_script и реестр на обеих
СУБД. config/custom_script сохраняет database={project}; доступная сейчас запись
проекта admin использует системную базу. Отдельные проектные базы и редактор
скриптов в Vue ещё не включены. config/process создаётся при установке начиная с 0.31.0.

Проверки: неизменённый tests/scripts/python_contract.py на настоящем оригинальном
ядре и Stream, тот же сценарий на SQLite/PostgreSQL, отдельное ожидание ошибки
NULL class_name, API отказ обычному пользователю, откат и исходные SDK TACTIC/Handler.

## Процессные обработчики Workflow — 0.31.0

Включены исходные обработчики плоского ациклического графа: action/auto,
manual/node и approval. Автоматические узлы вызывают Python callback и передают
управление дальше; ручные останавливаются на задаче. Pending/action/complete,
approved/not_required, reject/revise/error и custom события работают в текущем
Command/Transaction. TaskStatusChangeTrigger передаёт смену статуса задачи
в Workflow; approved и not_required нормализуются по исходным правилам.

Workflow.init() регистрирует события только в текущем request. init(startup=True)
и автоматическое включение во всех воркерах ещё закрыты вместе с полным CoreInit.
На этапе 0.31.0 завершение manual/node и not_required оставалось закрытым;
Snapshot-пакеты включены в 0.32.0. Иерархия, зависимости, condition/progress, межпроектные связи,
related callers, циклы и JavaScript также ещё не перенесены. Эти ограничения
проверяются до выполнения поддерживаемого графа; ошибки откатывают его эффекты.
Исполнение пока требует сохранённого администратора и активной транзакции.

init/upgrade создаёт исходную spt_process с workflow/subpipeline_code и реестр
config/process на SQLite и PostgreSQL. API insert/update/delete_sobject принимает
этот тип в admin на системном ресурсе, через права, триггеры и журнал. Изменение
настроек и rollback очищают кеши Pipeline и callback lookup. Pipeline CRUD и
создание отдельных проектных схем остаются следующими частями переноса.

Исправления оригинала проверены отдельными ожиданиями: reject не завершает
pipeline; завершение одной конечной ветки не завершает весь граф; approved
входы разблокируют объединение; custom direction=current использует process_obj,
вместо несуществующего processes_obj. Self-loop отклоняется общим preflight.

Проверка: неизменённый tests/scripts/engine_contract.py на оригинальном TACTIC
и Stream, тот же сценарий на SQLite/PostgreSQL; откат настроек, сообщений,
задач и журнала при сбое callback; запрет записи обычному пользователю.
Исходные SDK TACTIC/Handler проверяют CRUD config/process через настоящий XML-RPC.
Snapshot/File и пакеты ручного процесса добавлены в 0.32.0 ниже.

## Snapshot/File и завершение ручных процессов — 0.32.0

Модули snapshot.py и file.py перенесены целиком, с исходными классами и
наследованием SObject. Включены чтение Snapshot, выбор версии/ревизии/latest/current,
родители, XML файлы и ссылки, File метаданные и расчёт последовательностей.
При импорте File не запускаются внешние медиаконвертеры.
init/upgrade создаёт исходные snapshot/snapshot_type/file/file_access и реестр
на SQLite/PostgreSQL, добавляя выбранные исходные миграции. Рабочие данные legacy
не копируются. Запись этих объектов пока явно запрещена.

Ручной Workflow теперь завершает процесс после завершения всех его задач и
передаёт исходный пакет default/message следующему узлу. В default выбираются
is_latest Snapshot процесса со статусом Final, либо остальные последние Snapshot,
если Final отсутствует. complete/not_required, сохранение состояния, следующий
callback и журнал входят в одну транзакцию; ошибка откатывает также статусы задач.
Пакеты не копируют и не меняют файлы на диске.

XML-RPC get_snapshot сохраняет исходную сигнатуру, чтение версии/ревизии/context/
process и include_files. Пустой набор файлов возвращается как __files__=[].
Пути, include_full_xml, versionless и уровни пока дают UnsupportedContract.
Ошибки отсутствующего родителя пока используют native LookupError вместо полного
старого ApiException/ExceptionLog контракта. Это частичный API, не готовность check-in.

Исправления проверены отдельно на оригинале: кеш Snapshot разделяет ревизии
и видимость retired; OR запрос разных родителей больше не включает retired
строки из первой ветки; FileRange считает целое число кадров при шаге;
include_files не падает на Snapshot без файлов. Search использует исходный
Project.get_full_search_type: admin/sthpw не добавляются к типу автоматически,
явно указанный project сохраняется. Это исправляет прежнее расхождение Stream.
Сортировка Snapshot использует исходный timestamp; NULL строки сортируются
одинаково на SQLite и PostgreSQL: первыми при ASC, последними при DESC.
Это намеренное отличие от PostgreSQL default NULL порядка.

Проверки: неизменённые snapshot_contract.py и дополненный engine_contract.py
на настоящем оригинальном ядре и Stream; те же сценарии на SQLite/PostgreSQL;
откат ручного завершения при сбое следующего callback; исходные SDK TACTIC/Handler
через настоящий XML-RPC. Чтение и отказ неподдержанных операций не меняют БД.

Подготовка SnapshotBuilder и объектов без записи включена в 0.33.0 ниже.
Следующий участок — запись Snapshot/File и триггеры версий/is_latest/is_current
вместе с naming/versionless, затем репозиторий и FileUndo для атомарного check-in.
Workflow.init(startup=True) и полный CoreInit ещё ждут обработчиков версий,
иерархии и зависимостей; request-local Workflow.init остаётся доступным.

## SnapshotBuilder и подготовка объектов — 0.33.0

Перенесён целый исходный `pyasm.checkin.snapshot_builder` с обычным импортом
`from pyasm.checkin import SnapshotBuilder`. Поддерживаются файловые узлы,
ref/input_ref/cache/fref, вложенные группы, неизвестные ссылки, поиск по коду
Snapshot и имени файла. Отсутствующие ссылки используют исходные
Environment.get_warning/add_warning и TacticWarning в контейнере запроса.
Копирование узла сохраняет исходную семантику lxml: узел перемещается из старого
родителя, в том числе между документами; повторное добавление не создаёт дубль.
Цикл XML отклоняется до изменения дерева.

`Snapshot.create(..., commit=False)` собирает исходный объект с выбором следующей
версии/ревизии, данными, контекстом, процессом и пользователем. Исходный ранний
возврат сохранён: latest/current не устанавливаются автоматически до commit.
`Snapshot.set_booleans` и исходный `SObject.has_auto_current` доступны для
подготовки флагов без записи. `File.create(..., commit=False)` собирает метаданные
файла, включая размер существующего файла или явно заданный размер отсутствующего.
Каталоги пока отклоняются: их подсчёт размера и FormatValue ещё не перенесены.

Исправления отдельно сверены с оригиналом: fref использует node_name, а не
instance_name; явная версия с is_revision вычисляет следующую ревизию этой версии;
ручной выбор current использует родителя и контекст вместо неопределённых переменных.
Одинаковый скрипт выполняет сборку объектов и XML в обоих ядрах на собственных
фикстурах; тот же скрипт сверён на реальном PostgreSQL и SQLite. Проверяются
побайтовая неизменность БД, отказ записи и XML-ограничения.
Генератор контрактов больше не перезаписывает перенесённые Python-модули;
при повторном извлечении проверена неизменность всех исходников runtime.

Запись Snapshot/File, API create_snapshot и переключение latest/current
добавлены в 0.34.0 ниже. Versionless и файловый check-in ещё не готовы.
Подготовка не резервирует номер версии для конкурентного check-in.
Полная совместимость API остаётся целью; доступный транспорт не объявлен готовым
для установки пользовательских проектов и плагинов.

## Запись Snapshot/File и create_snapshot — 0.34.0

Исходные Snapshot.create и File.create сохраняют метаданные через общий
SObject/Command/Transaction, с проверкой администратора, журналом и откатом.
API `create_snapshot` доступен локальному SDK и XML-RPC с исходной сигнатурой:
контекст, тип снимка, описание, is_current, level_key, is_revision и triggers.
`triggers=False` сохраняет обязательный integral trigger, как в оригинале.
Создание снимка с ревизией и последующее чтение проверены неизменёнными SDK
TACTIC и Handler. Исходное чтение с revision=None выбирает ревизию 0;
для последней ревизии используется revision=-1.

Перенесён целиком SnapshotIsLatestTrigger: вставка/обновление снимают флаги
с предыдущих снимков нужного родителя и контекста, удаление пустого снимка
выбирает оставшийся снимок по исходному timestamp. Исходная неопределённость
выбора current после удаления current-снимка сохранена. Для parent без code
используется search_id; снимки с разными level и без level не смешиваются.
Исправлена потеря latest/current при переключении удерживаемого старого объекта:
его сохранённый флаг обновляется перед set_value. Этот баг оригинала отдельно
воспроизведён и проверен в том же серверном скрипте.

Целиком перенесён naming.py с оригинальным сопоставлением типа/контекста и правил
latest/current, а spt_naming и определение config/naming создаются автоматически.
Обычный strict-путь без правила versionless завершает update_versionless ранним
возвратом, как в TACTIC. Подходящее файловое versionless-правило даёт явный
UnsupportedContract до переключения флагов. Условия Naming включены в 0.36.0 ниже. Методы NamingUtil для полей включены в 0.35.0 ниже; изменение правил Naming ещё не включено.

Номера версий и переключение флагов сериализованы в слое SQL: SQLite получает
write reservation, PostgreSQL — блокировку таблицы Snapshot до конца транзакции.
Блокировка пока общая для таблицы; при росте check-in нагрузки её можно сузить.
Исходные DROP NOT NULL миграции Snapshot/File применяются при первой установке
и upgrade. SQLite перестраивает таблицу в транзакции, сохраняя строки,
дополнительные столбцы, индексы/триггеры и значение AUTOINCREMENT; PostgreSQL
снимает ограничение напрямую. Кодовые связи не требуют числового search_id.

Один скрипт проверяет создание, версии/ревизии, флаги, File/XML, удаление пустого
снимка и откат в оригинальном TACTIC и Stream; те же эффекты сверены на SQLite
и реальном PostgreSQL. Отдельно проверены конкурентное выделение версий,
права, изоляция code-less родителей/уровней и сохранность данных при upgrade.
Это сохранение метаданных: репозиторий, физические versionless-копии, FileUndo,
каталоги и файловый check-in **ещё не готовы**. Удаление снимка с файлами
отклоняется до записи. Полный API, создание проектов и установка плагинов
остаются отдельными незавершёнными этапами.

## Шаблоны NamingUtil — 0.35.0

Активированы исходные `NamingUtil.naming_to_file`, `naming_to_dir`, `eval_template`,
`build_naming`, `_get_timestamp` и `SObject.get_project`. Поддерживаются поля
SObject/Snapshot/File/проекта/пользователя, родитель, индексы компонентов контекста,
padding версий/ревизий, basefile/ext, даты и тип файла. `Common.get_filesystem_dir`
и `get_filesystem_name` перенесены без изменений; это работа со строками,
без создания каталогов и изменения файлов.

Исправлены отдельно воспроизведённые ошибки оригинала: `{ext}` в каталоге
обращался к несуществующей переменной; удаление `#` перезаписывало индекс
компонента; `{basefile}` терял переданное расширение. Числовые значения
преобразуются в строки, а `{identifier}` больше не подменяется форматированным
id. Необязательный File для basefile/ext даёт пустые значения.
Один неизменённый скрипт сравнивает результаты и ошибки в обоих ядрах;
те же вызовы выполняются на SQLite и реальном PostgreSQL, без записи данных.

Ветви `{@...}`/`{$...}` и условия Naming включены в 0.36.0 ниже.
Изменение правил, репозиторий, физические versionless-операции и файловый
check-in ещё не готовы.

## ExpressionParser и условия Naming — 0.36.0

Перенесён целиком исходный `pyasm/biz/expression.py`, с исходными классами
парсера и импортом `from pyasm.biz import ExpressionParser`. Активны выборки
`GET/GETALL/SOBJECT/SEARCH`, связи и фильтры, агрегаты, `IF/CASE`, строковые
операции, арифметика/сравнения, regex, printf/даты, переменные, относительные
даты, single/list/dictionary и входной Search. Naming выбирает правило по
исходному condition; NamingUtil использует выражения в имени и каталоге.

Один неизменённый серверный скрипт сравнивает эти вызовы в оригинальном TACTIC
и Stream, а затем на SQLite и реальном PostgreSQL. Отдельно воспроизведены
и проверены исправления: числовой фильтр оставлял свой буфер следующему фильтру,
пустой CASE падал, годовые переменные содержали буквальный `%d`, апострофы
терялись, кеш возвращал прежний env Snapshot, ошибка оставляла чужие extra_filters
и return_mode. Значения полей теперь передаются как данные; исходное превращение
строки в исполняемый Python-код исключено при сохранении порядка операций.
Кеш учитывает входные поля/объекты, фильтры, пользователя и Sudo; запись,
удаление и откат очищают результаты. Search.copy копирует запрос без загруженных
результатов и повторно проверяет текущие права.

`@PYTHON/@UPDATE/@VAR`, virtual/state/date/connect/site объекты,
FormatValue, старые UI цвета и файловые пути пока дают явный UnsupportedContract.
Дата поддерживается через переменные и RELTIME; это не готовность virtual/date
SObject. Публичный RPC `eval` и выражения в Search.add_op_filters ещё не включены.
Полная совместимость API остаётся незавершённой.

## RPC eval, UPDATE и PYTHON — 0.37.0

Включён исходный `eval(ticket, expression, search_keys=[], mode=None,
single=False, vars={}, show_retired=False)`. Сохраняются корневые search keys
(строка, список или словарь SObject, включая повторное XML-экранирование),
режимы, переменные, retired, scalar/list и словари SObject с исходными служебными
полями. Python XML-RPC возвращает `str(results)`, локальный ApiXMLRPC — само
значение, как оригинал. RPC передаёт выражение исходному ExpressionParser.

Исходные `@UPDATE` и `@PYTHON` включены: обновление идёт через SObject.commit,
а сохранённый скрипт — через PythonCmd и вложенный Command. Администраторский
RPC eval выполняется внутри Command даже для чтения; это обеспечивает атомарность
вложенных методов и откат при поздней ошибке. Обычное чтение не требует admin
и не открывает write-транзакцию: методы изменения/Python закрыты проверкой прав;
изменение и Python пока требуют подтверждённого администратора и активной
транзакции. Проверки стоят на выполнении метода, а не на поиске подстроки:
регистр, вложенный EVAL и переменные не обходят права. Применяются текущие
api_method/api_cmd ограничения и политика защищённых API записей, включая
COUNT и сокращение login. Локальные вызовы сохраняют текущие request/TX;
политики выражения восстанавливаются и после ошибки.

Исходное ядро и native SQLite проверяются одним неизменённым скриптом:
ответы, обновления, триггеры, локальное чтение, сохранённый Python и rollback.
Неизменённые SDK TACTIC и Handler проверяют чтение, обновление, скрипт и
откат через настоящий HTTP XML-RPC. Тот же сценарий записи добавлен к
проверке реального PostgreSQL/SQLite. Формат чтения сравнивается с настоящим
исходным ApiXMLRPC.eval, а не с имитацией клиента.

`VAR`, virtual/date/state/connect/site, FormatValue/UI palette, физические
LATEST/CURRENT и выражения в Search.add_op_filters остаются явно закрыты.
`@SEARCH` можно использовать в ядре; публичная сериализация самого Search
не реализована. Полная совместимость API ещё не достигнута.

## FileUndo и локальный репозиторий — 0.38.0

Перенесён целиком исходный класс `FileUndo` в `pyasm/search/transaction.py`,
с привычным `from pyasm.search import FileUndo`. Активны mkdir/rmdir,
remove с резервной копией, copy/move/create, файловый журнал и прямые undo/redo.
Пути внутри assets сохраняются относительно корня; внешние пути остаются
абсолютными, включая разные Windows drives. Операции требуют подтверждённого
администратора и активного Command/TX; undo/redo — того же администратора.

Файловые узлы входят в общий TransactionLog вместе с изменениями SObject.
При ошибке SQL откатывается, затем файлы восстанавливаются в обратном порядке.
Операция журналируется до IO; оставшийся pending не позволяет commit, даже
если пользовательский скрипт поймал IO exception. Резервные копии не удаляются
при неудачном откате; ошибка передаётся вызывающему коду. Успешно отменённые
узлы отмечаются, чтобы повтор отката не удалил уже восстановленные файлы.
Это откат в работающем процессе, не готовая recovery-система после kill/crash.

Исправлены перезапись резервных копий с одинаковым basename, потеря предыдущего
файла при overwrite, неверная интерпретация Windows-путей, mutable extra={},
копирование каталога внутрь себя и подавление/опасное удаление при ошибке undo.
`get_file_log` исправляет исходный rile_root и копирует узлы, сохраняя основной
журнал. MD5 считается потоково стандартным hashlib с тем же hex-результатом.

Целиком взят исходный `pyasm/checkin/repo.py`. В TacticRepo активны local,
inplace и preallocate: исходная регистрация File/type/MD5 и FileUndo.
Отсутствующие preallocated-файлы проверяются заранее; md5s='ignore' больше не
записывает отдельные символы этой строки. CheckinException сохраняет исходный
класс и импорт. BaseCheckin, repo copy/move через Naming, symlink/versionless,
S3 и публичные undo/redo пока не включены. Полный check-in API ещё не готов.

Один неизменённый скрипт запускается в оригинальном ядре и native SQLite:
файлы, MD5, типы, metadata, журнал и inplace/preallocate. Ошибка исходного
get_file_log проверяется отдельным ожиданием. Тот же скрипт и общий откат
файлов/записей проверяются на SQLite/PostgreSQL; отдельно проверены overwrite,
одинаковые имена cache, частичный IO и сбой записи журнала.

Дальше — исходные пути SObject/Snapshot и Naming, затем BaseCheckin/FileCheckin.

## Цепочка запуска оригинального TACTIC

Разобрана по исходникам `legacy/src`, без запуска оригинального сервера на рабочих данных.
Перенос продолжать по этой цепочке и зависимостям, сохраняя исходные имена ядра.

| Исходная точка | Что делает | TACTIC Stream |
| --- | --- | --- |
| `bin/monitor.py` → `pyasm.web.monitor.TacticMonitor._execute` | Batch admin, Config, список сервисов и портов, запуск/контроль процессов | Свой монитор, XML-конфиг, heartbeat, перезапуск, отдельные порты; scheduler/queues/watch folders ещё не перенесены |
| `bin/startup.py` → `tactic.startup.FirstRunInit` | Первый запуск, каталоги, стартовые ресурсы, PID, stdout/stderr, настройки веб-сервера | FirstRunInit создаёт свой каталог данных и сохраняет существующие файлы; явный init/upgrade, PID/status и журналы; старые демоданные не копируются |
| `CherryPyStartup` → `WebInit.execute` | Batch/environment/sites, очистка кэша триггеров, регистрация UI событий, CoreInit | ASGI/Vue и свой контекст; старые UI обработчики не нужны, CoreInit ещё требует переноса |
| `tactic.core.bootstrap.CoreInit.execute` | StatusLogTrigger для task/process_state, DisplayNameTrigger login, Workflow.init, Snapshot integral triggers | С 0.81 вызывается один раз при запуске каждого инициализированного воркера; без повторных статусных записей |
| `pyasm.command.workflow.Workflow.init(startup=True)` | Регистрирует process события, workflow/listen и TaskStatusChangeTrigger в каждом воркере | С 0.81 глобальная регистрация включена; отдельный процесс Workflow не нужен. Неперенесённые обработчики по-прежнему возвращают явную ошибку |
| `ApiXMLRPC.get_cmd/get_full_cmd` | Контекст клиента, Command/транзакция, печать метода/аргументов/времени | Общий Api.dispatch пишет метод, request ID, пользователь/проект, безопасные аргументы, результат/длительность |
| Apache `install/apache/tactic.conf` | BalancerMember для каждого Python порта | Docker Apache балансирует app:8081/8082/8083; процессы видны в backend контейнере |

В оригинале JobTask.start внутри CoreInit закомментирован; дополнительные сервисы
монитор включает по services/enable. Eager import модуля не означает запуск сервиса.
Предметная запись Task/Note/StatusLog перенесена в 0.27.0, генератор задач — в 0.28.0;
следующий этап — Workflow,
process config/state → CoreInit и workflow handlers → Snapshot и фоновые сервисы.
Нельзя включать пустые workflow обработчики: их транзакции и эффекты входят в совместимость.

Журнал API сохраняется в `temp/log/worker.N.log` с ротацией и выводится в консоль
воркера (`manage.py logs` в Docker). JSON и XML-RPC используют общую точку.
Пароли, тикеты, ответы и произвольные payload записи не выводятся; ошибки обозначены
именем класса. API сигнатуры и результаты сохранены. Уже работающие Windows воркеры
получат новый журнал после обычного перезапуска; обновление Docker не останавливает Windows.

## Каталог данных установки — аналог tactic_data

На Windows текущая установка использует `tactic_stream/data`, Docker — persistent
`/var/lib/tactic_stream` (`stream_data` volume). Расположение задаётся `--data-dir`
или TACTIC_DATA_DIR, данные отделены от src. Рабочая установка сохраняет прежний
путь; переименовывать её каталог при запущенных процессах не требуется.

`tactic.startup.FirstRunInit` выполняется при init/upgrade/serve и создаёт структуру:
config/tactic-conf.xml, db, assets, plugins, templates, dist, temp/log.
Для PostgreSQL каталог db остаётся частью структуры, сама база находится на сервере.
Существующие файлы и конфигурация сохраняются, исходные пользовательские данные
и demo DB не копируются, установка SQL выполняется только явным init.
При внешнем tactic-conf.xml FirstRunInit использует его и не создаёт второй
default конфиг, который мог бы скрыть выбранное подключение.

Перенесены исходные имена Environment.get_data_dir/manual, get_tmp_dir/include_ticket,
get_upload_dir, get_plugin_dir, get_template_dir, get_dist_dir, get_asset_dirs/get_asset_dir.
Пути читают install/tmp_dir, install/plugin_dir, checkin/asset_base_dir и прежний
checkin/base_dir_alias; относительные пути разрешаются от каталога данных.
Каталог plugins входит в sys.path, как в исходном first-run пути. Multi-site asset
providers и установка плагинов пока не перенесены. Исправлен выход из temp/upload
через небезопасный ticket или symlink; билетные папки остаются внутри своей базы.
Проверены пустой first-run без БД, повторный запуск с сохранением файлов, overrides
и aliases, временные upload каталоги и отказ path traversal.

## Админка

В `/` доступен Vue интерфейс: вход, выбор проекта, реестр SearchType,
таблица SObject, фильтр по колонке, сортировка, страницы по 50 записей и карточка
по search key. Интерфейс читает реальные данные собственного ядра; bootstrap
оставляет только системные записи, без демонстрационных проектов и объектов.
Редактирование объектов, создание проектов/типов и визуальный редактор Pipeline
пока не перенесены.

Английский — исходный язык интерфейса и язык по умолчанию, русский — второй.
Меню `Appearance` / «Оформление» доступно и до входа, и в рабочем окне.
Основная тема — Material Design 3 (`md3`); `material5` — экспериментальный
вариант из концепции ТХ, а не официальная спецификация Material Design 5.
Также доступен Fluent Design. Для каждой темы доступны светлый, тёмный и системный режимы.
Язык, тема и режим переключаются сразу, без сброса проекта, фильтра,
открытой карточки или сессии. Выбор сохраняется локально в браузере под ключом
`tactic_stream.appearance`; в этих настройках нет пароля или API билета.
При первом открытии после переименования прежние настройки и сессия браузера
переносятся на ключи `tactic_stream`; новые значения имеют приоритет.
Имена, значения записей, поля, search keys и тексты пользовательских скриптов
остаются данными проекта и не переводятся.

Текст компонентов, сообщения, заголовок документа и доступные подписи идут
через `frontend/src/i18n.js`: `t('English source')`, для параметров —
`t('Up to {count} records per page', { count: pageSize })`.
Русский словарь — `frontend/src/locales/ru.json`. Если перевода нет или он пуст,
отображается английский исходник. Новый язык добавляется JSON словарём
в `locales/` и записью в `languages` файла `appearance.js`; загрузку словарей
подхватывает сборка. Новые строки добавляются во все поставляемые словари
с теми же именами параметров. Это проверяет `tests/test_ui.py`.

Темы, наборы иконок и 19 палитр перенесены из каталога ТХ в
`frontend/src/appearanceCatalog.js`; общие CSS токены находятся
в `theme.css`, а правила расположения элементов — в `style.css`.
Компоненты используют роли цветов, размеры шрифта и скруглений, высоту
контролов и длительность анимаций из токенов. Формулы поверхностей, выделения,
контраст текста и motion повторяют Handler `Theme.qml`; Segoe UI и размеры
в пунктах — `Typography.js`. Touch targets остаются минимум 44 px.
Чтобы добавить тему, достаточно
записи в `themes` и переопределений токенов по `[data-theme="..."]`.
Светлый/тёмный режим выбирается независимо от темы, системный реагирует
на настройки ОС. При `prefers-reduced-motion` длительность анимаций равна нулю.
Эти правила закреплены в `AGENTS.md` для дальнейшего расширения админки.

В верхнем меню ⋮ → Configuration → Appearance находятся настройки интерфейса:
язык, стиль, цветовой режим, отдельные светлая/тёмная палитры для каждой темы,
набор иконок, анимации нажатия, наведения, переходов и меню. Конфиг открывается
отдельным полноэкранным dialog: общая шапка Reset/Apply/Save/Cancel, разделы
слева и карточки справа. Оформление видно сразу; Apply сохраняет и оставляет
экран открытым, Save сохраняет и закрывает, Cancel/Escape отменяет неприменённые
правки. XML-ключи, defaults и override доступны через Help/Details.
Графические backend-настройки Qt из ТХ не относятся к браузерному Vue.
Все строки настроек используют SettingRow с названием и пояснением,
выбор — AppSelect, переключение состояния — AppSwitch. Быстрое меню оформления
использует тот же AppearanceSettings. Новые локальные версии этих контролов
не добавляются; правило закреплено в AGENTS.md. Булевы настройки сервера имеют
отдельное действие Use default, сохраняющее исходное пустое значение XML.
Иконки используют те же официальные шрифты из Handler: Material Design Icons,
Font Awesome Solid/Outline и Fluent Regular/Filled. Automatic выбирает Material;
отсутствующие Outline-глифы используют Solid, как в ТХ. Пользовательских SVG нет.
Шрифты и лицензии включены в сборку, без внешнего CDN. После этого обновления
нужен перезапуск backend: маршрут assets теперь поддерживает `font/ttf`.

Раскрытые списки используют [нативный CSS select](https://developer.mozilla.org/en-US/docs/Learn_web_development/Extensions/Forms/Customizable_select):
`appearance: base-select` и `::picker(select)`. Меню, стрелка, подсветка и галочка
берут оформление из общих токенов; полосы прокрутки тонкие с прозрачной дорожкой, цвет меняется с темой. Клавиатура и доступность остаются нативными.
В браузерах без поддержки этого CSS сохраняется системный select.

`POST /admin/rpc` — небольшой JSON транспорт над теми же методами Api и билетами.

`/docs` — справочник и ручная консоль TACTIC API вместо стандартной страницы
Swagger с одной HTTP-оболочкой. Каталог `/api/documentation` показывает 129
исходных методов: доступность по SUPPORTED_METHODS, реальные сигнатуры/defaults
из Api, описание из оригинальных API/SDK и отдельный статус исключённых методов.
Доступность точки входа не означает подтверждённую полную совместимость.
Справка извлечена в api_manifest.json; capture_legacy.py сохраняет её при
повторном извлечении. Runtime не импортирует legacy или Handler.
По умолчанию показаны основные методы с готовыми примерами: проекты,
пользователи, задачи, SearchTypes, фильтрация, выбор колонок и следующая страница.
Выбор примера заполняет форму и ничего не выполняет. Аргументы редактируются
в подписанных полях с пояснениями; дополнительные параметры, ручной JSON,
Python-код и технические схемы раскрываются по необходимости. Поиск находит
все доступные методы, а фильтр позволяет открыть полный исходный каталог.
Консоль вызывает существующий `/admin/rpc`, с теми же правами, командами и данными;
тикет и проект задаются отдельно от args/kwargs. GET справки не выполняет методов.
Можно использовать существующую сессию админки или получить отдельный тикет:
пароль очищается после входа, новая сессия консоли хранится только в памяти вкладки.
Показаны ответы, структурированные ошибки, полное время HTTP-запроса,
копируемый Python XML-RPC пример и JSON-запрос без действующего тикета.
Методы записи отмечены явно и запускаются только кнопкой пользователя.
Запрос первых 10 `sthpw/search_object` через консоль и показанный stdlib XML-RPC
пример проверены на временной SQLite БД с одинаковым результатом. Справка и
консоль поддерживают EN/RU, общие темы/иконки и маленькие тач-экраны.
`/openapi.json` сохраняется для схемы HTTP-маршрутов, `/api/compatibility` —
для исходной инвентаризации и границ переноса. После обновления `/docs` нужен
обычный перезапуск backend; базы и конфигурация пользователя не меняются.
Исходный XML-RPC адрес и Python формат query сохранены. Пароль не сохраняется
в браузере; билет и выбранные проект/тип хранятся в localStorage и восстанавливаются
в новой вкладке и после перезапуска браузера/сервера. Старая сессия из sessionStorage
переносится при обновлении существующей вкладки. Сервер проверяет срок и отзыв
билета; истёкший билет удаляется из браузера. Кнопка «Выйти» отзывает билет
на сервере и очищает сохранённый вход.
Ошибки JSON админки возвращают английский `error` и стабильный `error_code`;
перевод выполняет интерфейс. Язык UI не меняет `ticket.language='python'`
и не участвует в форматировании исходного API. XML-RPC faults сохранены.

Фронтенд находится в `frontend/`: Vue 3.5.43, Vite 8.3.2, без роутера,
state manager и UI библиотеки. Версии и зависимости закреплены в package-lock.json.
Собранные HTML/CSS/JS входят в Python пакет, поэтому Node.js нужен только
для разработки интерфейса. Устройство сборки следует документации
[Vue](https://vuejs.org/guide/best-practices/production-deployment) и
[Vite](https://vite.dev/guide/).

Из `D:\code\TACTIC_VUE\tactic_stream\frontend`:

```powershell
npm ci
npm run build
```

Для разработки запустить backend на 8081 и `npm run dev`; Vite проксирует
`/admin/rpc` и `/health`. Runtime отдаёт файлы через importlib.resources,
включая запуск непосредственно из wheel. Лицензия Vue включена в пакет.

## Предметная основа

TACTIC — SQL система с реестром объектных типов. Запись `sthpw/search_object`
связывает logical search type с `database`, `table_name` и `class_name`.
Например, `contract/entity` может указывать на таблицу `entity` в базе
`{project}`. `Search` выбирает нужную базу и возвращает `SObject`, а search key
содержит тип, проект и `code` либо `id` записи.

Сейчас поддерживается SQLite: системная база `data/db/sthpw.db` и отдельные
проектные базы `data/db/<project>.db`. Определения системных таблиц взяты
из поставляемого seed TACTIC и shipped SQLite схемы; применены перечисленные
исходные миграции. Это выбранная часть схемы, не все миграции старого сервера.
Автоматического создания
проектных таблиц пока нет; тесты создают их только во временных каталогах.

Путь запроса прямой: `tactic_stream/server/app.py → server/api.py → pyasm/search/search.py → search/storage.py`.
`security.py` проверяет пользователя и билет. Контекст проекта живёт в
`ContextVar` и сбрасывается после запроса; параллельные проекты не делят
глобальное состояние. Поисковые SQL запросы используют параметры и проверенные
имена колонок; низкоуровневые построители сохраняют исходный формат TACTIC.

| Каталог | Назначение |
| --- | --- |
| `src/pyasm/common/` | Config, Container, Environment, Base/Common, Xml, даты и исключения. |
| `src/pyasm/search/` | `search.py`: SObject/Search/SearchType; Sql/DbResource/DatabaseImpl, Store, search keys, транзакции и журналы. |
| `src/pyasm/biz/` | Project/ProjectType, Schema, Pipeline, Task, Snapshot, настройки, предпочтения и метаданные триггеров. |
| `src/pyasm/security/` | Login, группы, Ticket, Security, Batch, аутентификация, пароли, AccessManager и Sudo. |
| `src/pyasm/command/` | Command, HandlerCmd и исполнение Trigger. |
| `src/pyasm/prod/service/`, `src/pyasm/web/` | Исходные входные импорты ApiClientCmd и TacticMonitor. |
| `src/tactic/command/` | Перенесённые исходные прикладные обработчики TACTIC. |
| `src/tactic_stream/server/` | `app.py` и `api.py`: HTTP/API; `startup.py` и `monitor.py`: конфигурация и процессы. |
| `src/tactic_stream/config/`, `compatibility/`, `web/` | Поставляемый XML, контракты/схемы/источники и собранная Vue админка. |
| `frontend/src/` | Vue компоненты, словари, оформление и общие токены. |
| `tests/` | Проверки исходных контрактов и реального runtime на временных данных. |
| `tools/` | Извлечение исходного baseline; runtime эти инструменты не импортирует. |

`pyasm` импорты покрывают только перечисленные классы, не весь серверный Python
API. SObject читается, позволяет подготовить изменения в памяти и построить SQL
через `get_statement()`/`commit(return_sql=True)`. Рабочие `commit()` и `delete()`
явно запрещены до переноса механизма записи.

Сохранена исходная структура поискового ядра: `SObject` — базовый класс,
от него наследуются `SearchType`, `Project`, `ProjectType`, `Schema`, `ProjectSetting`,
`TransactionLog`, `SObjectLog`, `RetireLog`, `Pipeline`; `ProjectPipeline` наследует Pipeline.
Доступны оба привычных вида импорта: `from pyasm.search import SObject` и
`from pyasm.search.search import SObject`. Так же работают `pyasm.biz.project`
и `pyasm.biz.schema`; каждый путь возвращает тот же класс.

В девятом этапе добавлен исходный ProjectSetting и deprecated имя ProdSetting.
Настройки читаются из `config/prod_setting` текущего проекта: обычные и JSON
значения, последовательности, пары и словари. Перенесены кеши SObject с
разделением по проекту и исходными sentinel значениями. Сохранена особенность
clear_cache: для config типов он очищает ключ без префикса проекта и поэтому
не сбрасывает текущий проектный кеш. Кеш всё равно ограничен запросом.

Генерация кода учитывает code_prefix/code_format, исходный случайный hex ключ
и id padding. Настройка autofill_pipeline_code=false позволяет готовить SQL
без выбора Pipeline. Выбор Pipeline добавлен в одиннадцатом этапе. Expressions
в префиксе, install.server конфигурация и запись ProjectSetting пока недоступны. Отсутствующий в реестре
config/prod_setting даёт пустое значение; ошибки зарегистрированного типа
завершаются явно. admin/sthpw create сохраняет исходный no-op.

В десятом этапе перенесены классы TransactionLog, SObjectLog и RetireLog,
импорты `pyasm.search.transaction_log`/`sobject_log` и кешируемые SObject.get_by_id/code.
TransactionLog.get_last учитывает текущие login и namespace; get_next_redo
выбирает самый ранний redo. Get фильтрует историю и ограничивает результат
100 строками. Search по transaction_log/sobject_log сохраняет исходную
сортировку по timestamp desc. Реестр sthpw/sobject_log по исходному seed
возвращает обычный SObject; отдельный класс SObjectLog доступен через импорт.

SObject.get_xml_value читает обычный и сжатый XML, учитывает root, существующие
записи кеша и исходное отсутствие записи результата в кеш. Сохранены CDATA
при strip_cdata=True и пробелы при remove_blank_text=False. Неверный XML
возвращает пустой root, как в исходнике; предупреждение идёт в лог сервера,
а не в старую UI очередь. DTD/entities и неперенесённые XML возможности
завершаются явной ошибкой. Common.compress_transaction/decompress_transaction
сохраняют формат zlib:hex; байты компрессора Python 3.14 могут отличаться.

Transaction.get_change_timestamp находит существующую запись либо готовит
новый SObject в памяти, кеширует его внутри Transaction и сбрасывает при reset.
Подготовка сама не сохраняет changed_on/changed_by в БД. TransactionLog.create,
удаление redo, SObjectLog.create и update_change_timestamps перенесены в последующих
этапах. RetireLog.create, undo/redo и remote queues остаются закрытыми.
Remote state=start сохраняет исходный no-op; admin sync также ничего не делает,
как в оригинале. Динамические interval выражения пока не перенесены.

TransactionLog и SObjectLog доступны доверенному серверному Python коду.
Через XML-RPC/JSON их данные закрыты до переноса правил доступа к полям:
transaction_log содержит ticket, а журнал может хранить изменения защищённых
записей. RetireLog доступен через перенесённые методы чтения.

В одиннадцатом этапе добавлены Pipeline/ProjectPipeline, Process и ProcessConnect
с импортами `pyasm.biz.pipeline`. Перенесены плоские XML графы, процессы,
связи, порты, контексты, action metadata и чтение task-pipeline настроек из
config/process. Выбор по коду сначала проверяет проектный config/pipeline,
затем системный sthpw/pipeline. Отсутствующий config реестр пропускается;
сломанная зарегистрированная таблица завершается ошибкой. Кеши изолированы
по запросам/проектам и сохраняют исходные особенности фильтрации.

SObject.get_defaults выбирает первый Pipeline по типу/проекту; get_statement
готовит SQL с этим значением и не исполняет его. Search.add_project_filter
использует параметры SQL. Для списка проектов сохранён исходный приоритет OR:
часть остальных условий может не применяться к отдельной ветке списка.
Это доверенный Python helper; внешний API его не публикует.

Встроенные Task шаблоны доступны с 0.27.0. Вложенные графы и автосоздание
отсутствующего default Pipeline остаются закрыты. Pipeline.get_defaults/update_dependencies/update_process_table,
save_version и create требуют ещё не перенесённой записи процессов и триггеров.
Подготовка UPDATE существующего Pipeline работает; INSERT и реальная запись
остаются закрытыми. Данные и граф из БД не изменяются чтением или подготовкой SQL.

В двенадцатом этапе перенесены TriggerSObj/Notification, исходные импорты
и выбор обработчиков из sthpw/trigger, проектного config/trigger, static/integral
реестров. Сохраняются порядок, точные event/process/search_type ключи, выбор
notification metadata и особенности кешей. Отсутствующий config/trigger
пропускается в get_db_triggers; сломанная зарегистрированная таблица даёт ошибку.
clear_db_cache по исходнику не очищает уже построенный event cache.

Trigger.call/call_by_key выполняют Python классы в том же процессе:
`same process,same transaction` вызывает execute сразу, а
`same process,new transaction` ставит обработчик в очередь после commit.
HandlerCmd сохраняет исходную обёртку handlers. Ошибка немедленного вызова
прерывает команду и откатывает её SQL; ошибки очереди идут в лог и не отменяют
уже завершённую команду. SObject._call_triggers формирует исходные события
объекта, типа, изменённых колонок и process/parent keys, пропуская timestamp.
Это внутренний Python механизм; API записи остаётся закрытым.

Загрузка доверенного fully-qualified class_name использует importlib.
Короткие имена классов, plugin loader, скрипты PythonTrigger, email и отдельные
процессы пока недоступны. Неперенесённые email/script/subprocess ветки
проверяются до исполнения любого выбранного обработчика. Серверные warning
очереди старого UI и multi-site хранилище не перенесены.
Долговечные журналы, политики прав и запись встроенных обработчиков нужны
для рабочего commit/delete.

Проверка неизменённого серверного скрипта выявила расхождение кеширования.
Search.get_by_code/get_by_id теперь возвращают исходный кешируемый SObject:
его staging виден повторному lookup, а прямой SQL не обновляет уже полученный
снимок. Сохранены исходные коллизии show_retired у этих Search методов;
в отдельных SObject.get_by_* исходник использует другой ключ для False.
add_id_filter/add_code_filter сохраняют исходное включение retired строк
при явном выборе идентификатора.

В тринадцатом этапе SearchType/SObject автоматически регистрируют исходные
TaskCreator, GlobalSearch, Folder, Task status, LoginGroup и Snapshot integral
определения. Сохраняются порядок, ключи кеша, флаги и исходная опечатка snapshot
флага. Временные определения готовятся через temp=True; это не запись trigger
строк и не разрешение пользовательских изменений колонок.

SearchType.create и Search создают классы из доверенного class_name реестра,
вместо фиксированного списка. Search передаёт SearchType объект, список колонок,
строку результата и исходную структуру fast_data; SObject сохраняет контекст
и преобразования boolean/дат. После любого исключения конструктора оригинал
повторяет вызов без fast_data; это поведение сохранено, предупреждение идёт в лог.
Добавлены полный SObjectFactory, кеш метаданных и get_virtual/set_virtual.
Синтетические незарегистрированные виртуальные таблицы пока не поддержаны.

common_exception.py и tactic/__init__.py взяты целиком без изменений.
Модули global_search_trigger.py и login_group_trigger.py сохранены целиком:
убраны legacy startup/ненужные eager импорты, six.string_types заменён Python 3.
Исходные отключённые Folder/LoginGroup execute остаются no-op. TaskCreatorTrigger
взят целым классом. RelatedTaskUpdateTrigger и TaskCompleteTrigger перенесены
в 0.27.0 вместе с Task/Note/StatusLog. Snapshot пока переносит только регистрацию;
автосоздание задач из Workflow, версии Snapshot, запись поискового индекса
и recursive collection SQL завершаются UnsupportedContract. Алгоритмы
ключевых слов и read/no-op ветки доступны; их запись упирается в закрытый commit.

## Совместимость

Из исходных `BaseApiXMLRPC` и `ApiXMLRPC` извлечены 128 публичных XML-RPC методов.
Добавлен `get_ticket_data`: исправлена ошибка исходника, повторно выставлявшая
`get_ticket.exposed`; инвентаризация теперь содержит 129 записей.
Это текущая инвентаризация одного транспорта; остальные публичные API/протоколы
требуют отдельной инвентаризации и проверки.
Отдельно отмечены 41 имени методов, найденные в вызовах Handler; это кандидаты
для проверки, поскольку статическое совпадение имени не доказывает API вызов.
Они помогают выбрать интеграционные сценарии. Целевой объём переноса — весь
публичный API оригинального TACTIC: сигнатуры, данные и ошибки, права, транзакции,
триггеры и файловые эффекты. Порядок определяется зависимостями ядра и покрытием
контрактов API.
Проверка `/api/compatibility` всегда сообщает `full_api_parity_verified: false`.
Сейчас доступны 25 XML-RPC методов с указанными ниже границами.

| Метод | Текущая граница |
| --- | --- |
| `fast_ping`, `ping` | Исходный ответ `OK`; `fast_ping` публичный, `ping` проверяет билет и проект. |
| `get_ticket`, `get_ticket_data` | Локальный активный пользователь; ключ или словарь своего Ticket. Группы и права проверяются при каждом запросе. |
| `query` | Postfix группы begin/and/or, сравнения, списки, contains/starts with/ends with, даты, сортировка по связанным таблицам, выбор колонок, distinct, limit/offset, single, show_retired, parent_key. |
| `get_column_info` | Метаданные физических SQLite колонок. |
| `get_column_names`, `get_table_info` | Имена колонок типа и таблицы его базы. |
| `get_by_code`, `get_by_search_key` | Чтение по code/id, включая retired, списки и старый формат ключа `type\|id`. |
| `get_parent`, `get_all_children` | Родитель и дети по определениям связей Schema. |
| `get_related_types`, `get_parent_type`, `get_child_types` | Типы связей с исходными порядком и наследованием. |
| `get_types_from_instance` | Типы концов instance связи. Чтение самих связей перенесено в Python ядре. |
| `insert`, `update`, `delete_sobject` | Администратор: аккаунты/группы/тикеты, Task/Note/StatusLog, Message/MessageLog и admin process_state через ApiClientCmd/Command/SObject; parent_key для Task/Note/process_state. Остальная предметная запись, metadata/collection/info и каскадное удаление закрыты. |
| `create_task`, `add_initial_tasks` | Администратор: задача с родителем/контекстом и генерация по ациклическому графу, включая вложенные pipelines; повторный запуск и skip_duplicate=False. Планирование even/even_day/from_end_date по настройке проекта/XML поддержано; Кастомные статусные pipelines задач поддержаны; неперенесённые ветви отклоняются. |
| `get_message`, `get_messages`, `log_message` | Исходные ключи, message/status/category, обновление и log_history; запись администратором через Command. Подписки/уведомления ещё закрыты. |
| `execute_python_script` | Администратор: сохранённый/inline/файловый Python скрипт, исходные kwargs и ответ status/description/info; local SDK в текущей транзакции. |

Сохранён исходный Python XML-RPC формат: `query` возвращает строковое
представление Python списка или словаря, включая `None`, а не JSON.
`get_by_*` возвращают XML-RPC словарь с `__search_key__` и `__search_type__`.
Билет клиента сохраняет поля `ticket`, `project`, `language`, `site`.

В предметном ядре добавлены `Search.get_count()`, чтение списков code/id,
описание SearchType, алгоритмы `SearchKey.get_by_sobject(s)` и сериализация
`SObject.get_sobject_dict()`. `get_json_value()` читает обычный JSON и исходный
формат `zlib:<hex>`. Перенесено преобразование boolean и дат, включая часовые
пояса. `get_count()` — метод Python ядра; отдельного XML-RPC метода с таким
именем в исходном контракте нет.

Сохранены особенности исходной реализации SQLite:

- Обычные объектные запросы по умолчанию сортируются по code; журналы
  transaction_log/sobject_log — по timestamp desc. Offset без limit игнорируется.
- Пустые IN и NOT IN возвращают пустой результат. Обработка Python None,
  строкового NULL и пустых строк зависит от формы фильтра, как в оригинале.
- Contains использует LIKE, поэтому `%` и `_` остаются шаблонами SQL.
- Distinct по колонке без s_status может включать retired записи. Локальный
  get_count считает строки, игнорируя distinct и пагинацию.
- Query заполняет отсутствующие запрошенные колонки значением None и сохраняет
  сырое поле metadata. Локальный get_sobject_dict в обычном режиме разбирает metadata.

Также поддержаны исходные директивы фильтров `@ORDER_BY`, `@LIMIT`, `@OFFSET`,
`@UNIQUE` и JSON представление списка фильтров. Произвольные SQL выражения
и TACTIC expressions пока завершаются явной ошибкой.

Schema читает XML из системной таблицы, учитывает `parent`, `__NONE__`, тип
проекта и исходную admin схему. Шесть predefined схем извлечены из SCHEMA_XML.
Сохранены выбор первой проектной схемы по id, приоритет прямых/обратных связей,
wildcard `*`, именованные `path`, `prefix` и disabled колонки. Кеши ограничены
одним запросом; проекты не делят определения связей.

Перенесены `Search.add_parent_filter`, `add_relationship_filter(s)`,
`SObject.get_parent`, `get_related_sobject(s)`, `get_all_children_search`,
`get_all_children`, `get_child`, `get_parent_search_key` и описание связей Schema.
Работают прямые code/id связи и ссылки search_type + search_code/search_id.
Сохранены проверенные особенности оригинала, в том числе включение retired
родителя при локальном wildcard lookup и ошибка implicit id связи без from_col.
XML-RPC get_parent отдельно учитывает show_retired, как исходный метод.

В четвёртом этапе перенесены `Search.add_join`, `add_search_filter`,
`add_relationship_search_filter`, `get_related_by_sobjects` и `SObject.get_values`.
Instance связи читаются через таблицу связей и возвращают исходное служебное
поле `_related_code`. JOIN сохраняет дубликаты строк; count считает строки
соединения. `get_related_by_sobjects` группирует результаты по search key
каждого исходного объекта, в том числе возвращает пустые группы.

Связанные Search используют IN/NOT IN подзапрос в одной базе; между отдельными
SQLite базами сначала читают значения. Сохранены исходные особенности:
подзапрос фиксируется при добавлении фильтра; свежий подзапрос не получает
автоматический retired фильтр; межбазовый `add_search_filter` игнорирует op и table.
Для ссылок search_type поддержаны исходные ветки `delay_null` и `use_multidb`.
Обратная межбазовая ветка, как в оригинале, выполняет подзапрос на sthpw.

Сортировка через code/id связи добавляет JOIN, в том числе по цепочке
`entity_in_collection.collection.name`. Работает через обычный XML-RPC `query`
и неизменённые клиенты. Доступ к служебным данным авторизации через такой JOIN
также запрещён. Сохранено поведение `add_parent_filter` для instance: этот метод
оставляет поиск без фильтра. Поэтому `query(parent_key=...)` для instance
не заменяет `add_relationship_filter`.

В пятом этапе перенесено состояние SObject: `data`, `update_data`, `quoted_flag`,
`has_updates`, `new_id`, `force_insert`, предыдущие данные и metadata cache.
`SearchType.create(search_type, columns=None, result=None)` создаёт объект
перенесённого класса из реестра с id=-1; ни объект, ни его изменения не записываются.
Сохранены исходные сигнатуры конструкторов SObject, SearchType и Schema.
Формат внутренних row dictionaries также остаётся доступен новому Search.

`set_value`, `set_data`, `set_update_data`, `set_json_value`, `set_data_value`
и `set_metadata_value` работают с буфером. `get_value` читает буфер при
`has_updates`, `get_data()` объединяет его с исходной строкой, а
`get_data(merged=False)` возвращает исходный словарь. Сохранены исходные
особенности: установка того же значения отмечает has_updates; возврат значения
не удаляет его из буфера; set_update_data сам не меняет этот флаг.
`set_id` хранит будущую замену id отдельно от текущего id; is_insert игнорирует
force_insert, как исходный метод. prev_data заполняется при сохранении,
поэтому до переноса commit она остаётся пустой.

Перенесены обработка boolean/NULL/пустых списков/дат, allow_none и nullable,
validate_set_value для наследников, пропуск неизвестных колонок, чтение имён,
дат и последовательностей. Работают `set_parent`, `set_sobject_value`,
`add_relationship`, `add_related_sobject`, `add_related_connection`,
`set_project` и `set_user`: они заполняют поля связей в памяти по Schema.
Сохранены классы SearchException, SObjectException и SObjectValueException,
их базовый TacticException и привычные pyasm импорты.

JSON в текстовой колонке сериализуется с исходной обработкой дат и сжимается
после 10 KiB в zlib:<hex>. Оба ядра читают этот формат; исходный JSON совпадает.
В этом окружении Python 3.14 использует zlib-ng: сам сжатый поток отличается
от потока старого Python. Совместимость байтов сжатия 1:1 не подтверждена.
Также сохранены исходные ошибки dict_keys в JSON encoder и поведение metadata
cache: set_json_value не сбрасывает уже прочитанную metadata.

В шестом этапе перенесён жизненный цикл Command/Transaction и отложенных Trigger.
Command выполняет check_security, регистрацию, preprocess, get_data, execute,
postprocess и commit; return execute, отличный от None, заменяет info даже при False/0/[]/{}.
Вложенные команды используют один Transaction. Участники получают start сразу,
commit при завершении внешнего уровня, rollback при ошибке в исходном порядке.
register_database регистрирует одно имя базы один раз. Проверен настоящий
commit/rollback SQLite участника на отдельной БД в памяти; это не интеграция
транзакций с проектными подключениями Store.

После успешной внешней команды выполняются notify_listeners и очередь Trigger.
Триггеры получают отдельный цикл команды; повторные event/class/JSON input
подавляются в пределах запроса. Ошибка отложенного триггера печатается в лог,
после неё очередь продолжается. Перенесены состояние Trigger, реестры static
и integral, их startup поведение и исходный отбор static по event/process.
DB dispatch и HandlerCmd добавлены в двенадцатом этапе; поддерживается один site.
Сериализация входа очереди поддерживает JSON; non-JSON, email, скрипты,
subprocess и встроенные listeners авторизации не перенесены.

Сохранены проверенные особенности исходного Batch пути: check() пропускается;
call_trigger=False всё равно запускает очередь; KeyboardInterrupt выполняет
commit; execute_transaction возвращает None; kwargs Trigger заменяются на {}.
Повторное выполнение той же Command с уже завершённым cached Transaction
даёт исходную ошибку счётчика. Сохранено исходное состояние стека после ошибок
вложенных команд, включая пойманную ошибку ребёнка. ContextVar изолирует
Container между запросами и восстанавливает внешний контекст после вложенного.

Command работает в RequestContext/Batch. Системная запись TransactionLog и
change_timestamp добавлена в этапах 18–19. Применение undo/redo, remote queues,
durable ExceptionLog, Pipeline listeners и UI ветка check не перенесены.

В седьмом этапе добавлены исходные Sql, DbResource и DbContainer для собственных
SQLite баз. Search.get_sql и lookup ресурсов SObject/Project используют этот
путь. DbContainer переиспользует подключения внутри запроса и регистрирует их
в Transaction. Sql сохраняет отдельный transaction_count, исходный автокоммит
do_update вне транзакции, row_count/last_row_id и результаты do_query/get_value.
Вложенные команды видят собственные SQL изменения через Search; ошибка команды
откатывает их. Завершение внешнего уровня коммитит зарегистрированные базы.
Общие SQL подключения между разными RequestContext запрещены. На выходе из
запроса они закрываются с откатом незавершённых изменений.

Store заимствует подключение текущей транзакции для чтения и не коммитит его
при выходе из with. Авторизатор SQLite сохраняет режим только чтения внутри
такого блока, включая уже подготовленные SQL statements. Другой явно заданный
Store читает свои файлы. Прямой Store.connection(write=True) внутри команды
по-прежнему запрещён: внутренние транзакционные операции выполняются через Sql.
Raw Sql — Python API доверенного серверного кода, доступный сейчас активному
admin. Он не заменяет SObject.commit и не опубликован через XML-RPC.

SqliteImpl исходного TACTIC не создаёт savepoint через методы Sql: эти методы
сохранены как no-op. Явные SQL команды SAVEPOINT/ROLLBACK TO/RELEASE работают и
проверены отдельно. Несколько баз, как в оригинале, коммитятся последовательно;
атомарность распределённого commit не заявляется. Повторное подключение после
ошибки do_query отключено, чтобы не потерять активную транзакцию. Ошибки commit
не подавляются, в отличие от старого Transaction, который печатает SqlException
и продолжает. do_query ограничен чтением; ATTACH/DETACH и load_extension запрещены.
Внешние vendors/resources, global pool и другие
методы большого исходного Sql ещё не перенесены.

Transaction.get_xml/get_transaction_log/create_log_node формируют XML в памяти.
SObjectUndo.log_undo и log_undo_for_delete сохраняют исходные action, search key,
from/to значения и порядок колонок; включая NULL, JSON, timestamp и boolean.
Это формирование журнала, без записи объекта или применения undo/redo.
Перенесены очистка журнала при rollback/commit и set_transaction с новым пустым
XML. Xml использует ElementTree и проверен по строкам оригинала для журнала;
поддерживает абсолютные пути, атрибуты и проверки наличия/равенства атрибутов,
соединённые `and`. Поддержаны remove_child и перемещение существующего дочернего
узла в конец того же родителя, как в lxml. Full XPath, namespaces,
comments/processing instructions, смешанное содержимое, файлы и остальные lxml
операции не перенесены. Ошибки XML parser могут иметь другие сообщения.

Если XML содержит действия и record_flag=True, commit откатывает изменения
и явно отказывает до вызова участников commit. Это временное отличие от
оригинала, который сохраняет TransactionLog уже после commit проектных баз.
set_record(False) сохраняет исходную ветку без долговечного журнала. Запись
TransactionLog остаётся закрыта, как SObject.commit/delete и API записи: до
переноса долговечного журнала, DB триггеров и правил доступа.

В восьмом этапе перенесена подготовка SQL в SObject: get_statement и ветка
commit(return_sql=True). Она сохраняет исходный порядок проверки прав,
set_defaults, store_version, validate, переопределения id и преобразования
значений. SQL не исполняется; буферы SObject меняются как в оригинале, включая
timestamp, new_id и last_statement. Подключения регистрируются в Transaction,
но SObjectUndo и счётчик Search:sql_commit при подготовке не заполняются.

В sql.py находятся исходные Insert/Update и Sql.quote. Insert сортирует имена
колонок, Update сохраняет порядок. Сохранены исходные флаги кавычек при повторной
установке значения, обработка bytes у Update и особенности add_filter/WHERE.
В частности, несколько фильтров Update соединяются запятыми, а не AND;
подготовка строки не гарантирует, что любой исходный SQL исполнится в SQLite.
execute и get_id_statement этих построителей явно закрыты до переноса их
vendor/Select/sequence веток. Низкоуровневый Sql.do_update по-прежнему принимает
строку; это отдельный внутренний API администратора.

DatabaseImpl/SqliteImpl предоставляют выбранные методы SQLite: тип базы,
метаданные колонок, process_value, get_timestamp_now, отсутствие sequences и
savepoint, preprocess/postprocess. SqliteImpl наследуется от DatabaseImpl;
неперенесённый PostgresImpl и интерфейсы других vendors не добавлены.
Исходные импорты pyasm.search и pyasm.search.database_impl сохранены.

Значения по умолчанию поддержаны для SObject, SearchType и hooks перенесённых
наследников. В одиннадцатом этапе добавлен выбор первого Pipeline по типу объекта
и проекту, включая общие и multi-project записи. Настройки читаются через
ProjectSetting; autofill_pipeline_code=false отключает выбор. Ветка sthpw/task
сохраняет исходный пропуск этой настройки.
В отличие от общего catch оригинала, UnsupportedContract из defaults
пробрасывается, чтобы не получить SQL с пропущенными настройками.
Обычные ошибки пользовательского get_defaults, как в исходнике, печатаются,
после них обработка timestamp продолжается. Проверка validate может изменить
объект или вызвать исключение; её возвращаемое значение игнорируется исходным
commit. Рабочая запись commit/delete и долговечный TransactionLog ещё закрыты.

Границы и различия, которые ещё нужно закрыть:

- Вход доступен активным локальным пользователям. Полные динамические access rules,
  внешние провайдеры, guest, 2FA, multisite и transaction tickets ещё не перенесены.
  Включённая 2FA завершает вход явной ошибкой без выдачи билета.
  Таблицы аккаунтов через API доступны только администратору; чтение
  transaction_log/sobject_log ещё закрыто до переноса правил выдачи полей.
- Подготовка изменений SObject учитывает sobject_column при установленном Security.
  Без Security доверенный контекст требует активного admin.
  Исходный temp режим и прямые set_data/set_update_data меняют только память.
  Translation, Xml значения в set_value и remote SObject не перенесены.
  SearchType.create сейчас требует существующую физическую таблицу и
  перенесённый класс из реестра. Байты сжатого JSON между zlib и zlib-ng отличаются.
- Many-to-many, `SObject.get_instances`/XML-RPC `get_instances` (они используют
  ExpressionParser), TACTIC expressions, полнотекстовый поиск и остальные
  специализированные SObject классы ещё не перенесены. JOIN между отдельными
  SQLite базами, JOIN для search_type ссылок с database-qualified таблицами,
  разные логические/физические имена таблиц, вычисляемые колонки и именованные
  path в сортировке пока завершаются явной ошибкой. Instance не перенесён в
  `children_alter_search`. Не перенесены
  динамические даты NOW/CURRENT_TIMESTAMP и исходный fallback неверной даты
  фильтра «is on» на сегодняшний день; пока нужна дата YYYY-MM-DD.
- API записи, транзакции, триггеры, команды, серверные скрипты, snapshot/check-in
  и файловое хранилище возвращают XML-RPC Fault 501.
- REST API, UI API, upload и local protocol не реализованы. Инвентаризация 128
  методов относится именно к XML-RPC, а не ко всем внешним контрактам TACTIC.
- Vue админка пока предоставляет просмотр. Старые renderer/widgets и UI API
  не перенесены; `/docs` остаётся документацией сервера.

Нельзя переключать существующий production проект на этот этап: успешные
проверки выбранных 24 методов не означают готовность полного Handler или совместимость
всех рабочих данных.

## Правила доступа и Environment

В пятнадцатом этапе модуль `pyasm/security/access_rule.py` перенесён целиком
с исправлением раннего выхода get_by_groups при пустом списке групп.
AccessRule и AccessRuleInGroup наследуются от нашего
SObject; AccessRuleBuilder создаёт, обновляет и удаляет правила в XML.
Сохранены привычные импорты `pyasm.security` и его исходных подмодулей.
Устаревшие таблицы access_rule/access_rule_in_group не добавляются в рабочую
БД автоматически; lookup проверен на зарегистрированных временных таблицах.

Весь AccessManager/Sudo сохранён с исходными методами и сигнатурами.
Перенесены уровни deny/view/edit/insert/retire/delete, aliases false/true/allow,
defaults, объединение правил, проекты, составные ключи, check_access и summary.
Сохранены особенности оригинала: для повторяющихся shorthand правил выбирается
больший уровень; старые group правила могут его заменить. Список ключей использует
первое найденное правило. Эти особенности проверены запуском одного и того же
`tests/scripts/access_contract.py` в обоих ядрах.

Environment содержит исходные accessors пользователя, групп, билета и объекта
окружения. Их состояние и счётчики Sudo хранятся в Container текущего запроса.
Security устанавливается явно через Environment.set_security доверенным
серверным кодом. Ни Environment, ни Sudo не создают неявного администратора.
При отсутствии Security setup/Sudo завершаются явной ошибкой; Sudo нельзя
переносить между запросами. Вложенные вызовы восстанавливают флаги после выхода
из последнего активного Sudo.

Исправлены три исходных бага. Пустые группы сразу дают `[]`, без ненужного
поиска AccessRuleInGroup и зависимости от зарегистрированной таблицы.
Выход из одного Sudo сохраняет флаг admin и временную группу, пока другой
Sudo активен. XML только с `<group>`-правилами теперь разбирается; оригинал
преждевременно возвращался, если не находил shorthand `<rule>` узлов.
Пять сценариев явно фиксируют намеренные отличия результатов от оригинала,
а проверка пустых групп дополнительно запрещает любой вызов Search.

В шестнадцатом этапе добавлены реальные Security/Login/группы и подключение
Environment к API. Вход обычных активных пользователей добавлен в двадцатом этапе.
Expression-backed access filters явно закрыты, как initialization/configuration
Environment. В отдельных Sudo проверках пятнадцатого этапа используется
одинаковый test double; новый security_contract.py проверяет настоящие классы.
Рабочий SObject.commit/delete, создание проектов и установка плагинов ещё
ожидают переноса зависимостей и проверки эффектов в БД.

## Объекты пользователей и контекст Security

В `pyasm/security/security.py` перенесены классы Login, LoginGroup, LoginInGroup,
Ticket и выбранные части Security. Сохранены исходные наследование, сигнатуры,
пути импорта и metadata классов. Перенесены чтение и поиск пользователей/групп,
UPN и namespace, прямые связи, генерация XML уровней доступа, defaults, билеты,
обход вложенных групп, настройка правил и управление контекстом пользователя.
Common.generate_alphanum_key и Login.encrypt_password используют привычные
сигнатуры и форматы. Алфавит генератора исправлен: старый код пропускал последние
символы диапазона. Пароли по умолчанию и возвращаемые defaults сохранены как
исходный контракт; создание пользователей и запись паролей ещё закрыты.

API после существующей проверки билета устанавливает настоящие Login, Ticket
и Security в Environment текущего запроса. После завершения запроса контекст
сбрасывается. Search применяет установленный Security при подготовке запроса,
включая count. Параметр Search(sudo=True) допускается при установленном Security
и сохраняет исходное поведение: в оригинале этот параметр не меняет фильтрацию;
действительный Sudo — отдельный объект. Защищённые security/log типы остаются
в шестнадцатом этапе были закрыты через внешний API; теперь account чтение разрешено
администратору, journal чтение остаётся закрытым. Тест прямого контекста
не открывает выполнение пользовательских Python скриптов через HTTP.

Исправлены исходные баги: раннее завершение обхода вложенных групп; сохранение
admin после sign_out и потеря admin после reset_access_manager; no-op clear_ticket;
игнорирование default в Security.get_access; cache Login.get_by_login, не
учитывавший namespace/use_upn; отметка успешной фильтрации до возможной ошибки.
При повторе неудавшегося фильтра запрос снова отказывает. Синтетическая default
группа формируется один раз с максимальным уровнем всех найденных настоящих
групп; циклы не зацикливают обход. Raw IN строки заменены параметрами, включая
имена пользователей/групп с апострофами. Ticket получает правильный SEARCH_TYPE,
поиск валидного билета использует UTC и отказывает при неправильной expiry.
Начальная авторизация отвергает retired аккаунты и неправильные expiry.
Ограничения шестнадцатого этапа по выдаче билетов и записи аккаунтов сняты ниже
в описании двадцатого этапа. Site, внешние провайдеры, guest и 2FA ещё закрыты
явными ошибками. Отсутствующий admin не создаётся виртуально.

Собственная БД получает шесть исходных ADD миграций: login.upn/display_name/data
и login_group.name/is_default/data. При добавлении upn выполняется исходное заполнение
из login для существующих собственных аккаунтов. Upgrade атомарен и повторяем;
пользователи из legacy не копируются. Запускальщик выполняет upgrade до serve.

## Локальный жизненный цикл аккаунтов и тикетов

В двадцатом этапе перенесены запись Login/LoginGroup/LoginInGroup/Ticket,
`Login.create`, управление членством, парольный вход, выдача и проверка билета,
истечение, продление и отзыв. Используются те же SObject, Transaction, Command,
журнал и commit/delete события. Администратор создаёт аккаунты и группы;
пользователь меняет собственный пароль. Переименование существующего аккаунта
или группы закрыто до переноса обновления зависимостей.

`Ticket.create` сохраняет SQLite expiry: исходник ошибочно заменял его SQL NULL.
Применяется настроенный interval или 10 часов; expiry=-1 создаёт бессрочный билет.
`commit=False` оставляет подготовленный объект без записи.
`update_session_expiry` использует `security.inactive_ticket_expiry`; без настройки
не продлевает билет. Смена пароля и перевод Login в retired отзывают его билеты.
`Security.sign_out` очищает текущую identity по исходному контракту; долговечный
выход транспорта удаляет Ticket. Vue кнопка выхода вызывает серверный путь.
JSON `/admin/session/logout` и `/admin/session/renew` — собственные маршруты
админки, не новые методы оригинального XML-RPC API.

Перенесены Authenticate/TacticAuthenticate, история и срок действия пароля,
настроенный лимит неудачных попыток и атомарный счётчик. SQL изменения JSON и
подготовка дат делегируются DatabaseImpl. Проверяется владелец билета;
неудачный вход очищает identity/Sudo, `test=True` сохраняет прежний контекст.
Вложенные реальные группы дают права администратора; временный доверенный Sudo
не превращается в постоянную группу. Удаление аккаунта/группы убирает связанные
membership строки. Ошибки commit откатывают SQL участников и очищают кеши.
Намеренные исправления оригинала имеют отдельные ожидания сравнительных тестов.

Добавлены исходные импорты Config, Batch, XmlRpcInit, XmlRpcLogin и TacticInit.
Config читает собственный `data/config/tactic-conf.xml` либо явный
`TACTIC_CONFIG_PATH`; поддерживает выбранные методы чтения/записи и XML v1/v2,
использует literal значения вместо eval. Batch использует собственную существующую
БД и контекст; legacy Site/install discovery не запускается. LDAP/AD/Unix,
security v1, guest и проверка 2FA ещё не перенесены. CMS/session исключён,
алгоритм проверки существующих паролей оставлен.

`insert/update/delete_sobject` исполняются через исходный класс ApiClientCmd
в административном контексте для четырёх account типов. Проверен путь проекта
`admin`; в других проектах неперенесённая remote-sync ветка может отказать с откатом.
Generic insert сохраняет переданный password как исходный API; создание аккаунта
с шифрованием использует `Login.create`/CLI. Raw SQL не заменяет проверки и Command.
Полный исходный механизм ограничений полей и предметная запись ещё впереди.

## Политика Search/SObject и подготовка удаления

В семнадцатом этапе перенесены исходные проверки search_type при создании Search,
sobject_column при set_value и handle_commit_security для подготовки изменений.
Default для пользовательских search types — deny, для отдельных системных типов —
allow; сохранены ключи типа/проекта и порядок проверок. Для Project правило поля
проверяется с project='*'. Temp и прямые буферы по исходному контракту меняют память.
Базовый SObject.check_access возвращает True, как оригинал; специализированные
классы могут его переопределять. Универсальную новую ACL модель не добавляли.

Search.check_security поддерживает ограниченный режим собственной БД; Config/Site
и исходный api_mode=open ещё не перенесены. Search(sudo=True) пропускает проверку
защищённых типов, но сохраняет ограничения search_type и row filters. Sudo остаётся
отдельным объектом. Внешний API устанавливает права реального пользователя;
account чтение разрешено администратору, journal чтение ещё закрыто.

Перенесены статические search_filter: правила одной колонки соединяются OR,
разные колонки — AND, отрицательные сравнения включают NULL по исходному алгоритму.
Исправлен исходный перевёрнутый разбор A|B: теперь это список, а не один литерал.
Оригинальный NOT IN с такой строкой давал ошибочный SQL. Expression/related фильтры
пока отказывают до изменения Search; неприменимые правила типа/проекта пропускаются.
Исправлен собственный get_count: теперь он применяет ту же политику строк, что rows.
Исправлен исходный обход ACL через identity кеш: перед выдачей объекта, загруженного
под Sudo, get_by_search проверяет его текущую видимость обычному пользователю.
Для видимого объекта сохраняются identity и pending state.

SObject.delete(return_sql=True) проверяет исходные права удаления, строит SQLite SQL
и по log=True добавляет исходный XML delete в журнал памяти. SQL не исполняется,
данные объекта не сбрасываются, delete триггеры не запускаются, как в исходной ветке.
Апострофы строкового id экранируются; проверено, что такой SQL не удаляет чужие строки.
Полные commit/delete ожидают долговечного журнала и обработчиков записи.

## Системная запись журналов

В восемнадцатом этапе SObject.commit умеет сохранять transaction_log, sobject_log
и change_timestamp в активной Transaction с установленным Environment Security.
Сохранены преобразование SQL значений, readback, generated code, prev_data,
prev_update_data, сброс pending state, ветка ingest, базовые hooks и исходные
исключения этих системных типов из триггеров. SQL по-прежнему доступен только
активному администратору собственной БД. Остальные SObject записи ещё отказывают.

TransactionLog.create сохраняет журнал с исходным порогом сжатия 10 KiB,
полями пользователя/проекта/билета, удалением всех redo текущего пользователя и
построением SObjectLog индексов. SObjectLog.create взят целиком. Индексация сохраняет
dedup, пропуск delete/excluded типов и поиск parent для дочерних объектов.
Удаление TransactionLog вызывает исходные события и очищает связанную sobject_list.
Для этого upgrade добавляет исходную таблицу/реестр sobject_list и search_code ADD.
GlobalSearch writer пока не перенесён. RetireLog.create ещё закрыт.

После удаления код/id варианты кеша инвалидируются: оригинал мог возвращать
удалённый redo объект из кеша. После rollback изменённых системных данных кеши
журналов очищаются: поиск не возвращает несуществующий откатившийся журнал.
В исходной схеме нет keywords колонки, хотя параметр
есть в create; теперь эта ветка отказывает до удаления redo. Если пользовательская
схема содержит эту колонку, аргумент сохраняется обычным путём. File/table/site
журналы также отказывают до изменения системных данных.

Этот явный системный путь проверен в одинаковом Command с set_record(False).
Он не открывает API записи или запуск пользовательских скриптов по HTTP.
Создание проектов и установка плагинов ещё впереди.

В девятнадцатом этапе перенесены автоматический Transaction.commit_log и
update_change_timestamps. При непустом XML и record=True журнал записывается в
текущую транзакцию sthpw вместе с данными, индексами и метками. Пустой XML,
record=False и неотменяемые команды не создают журнал; вложенные команды дают
один журнал. Record/sync по умолчанию скрыто не отключаются. Поиск объектов
для индекса может читать проектную БД; запись в другую БД с автоматическим
журналом явно закрыта до согласованного commit между базами.

Модуль pyasm.biz.preference перенесён целиком без изменений: PrefList и
PrefSetting сохраняют исходные lookup пользователя/проекта, fallback и кеш.
Их таблицы и реестр взяты из shipped seed, пользовательские предпочтения и
старые UI определения не копируются. Запись PrefSetting.create пока упирается
в общий отказ записи обычных SObject. Добавлены исходные SObject.set_now,
Sql.get_default_timestamp_now и SPTDate.convert_to_timezone.

Исправлены потеря changed_by при объединении существующей метки и проверка
is_undoable через Python 3 exec/eval. Ошибка журнала, метки, commit-хука или
SQLite commit откатывает данные; оригинал мог уже сохранить данные или проглотить
ошибку метки. SQL rollback выполняется также при неперенесённом file journal.
Стек команд очищается после этого отката, а также после ошибки commit-хука уже
завершённой транзакции; оригинал оставлял команду в стеке. Admin sync сохраняет исходный no-op;
для других проектов sync=True пока отказывает с откатом. set_sync(False) —
исходный явный способ локальной записи. Append существующего журнала,
undo/redo применение, удалённая очередь и межбазовая запись ещё закрыты.

## Проверки и источники

Linux-развёртывание отдельно проверено через `deploy/docker/manage.py check`:
Apache, Vue assets, JSON/Origin, XML-RPC, три native воркера, реальное подключение
к PostgreSQL 18.6 с паролем, UTF-8 и commit/rollback; HTTPS-вход Webmin и модуль Apache.
На собственных данных также проверены восстановление упавшего Linux-воркера,
`update`, удаление/пересоздание контейнеров с сохранением данных и тикета, его отзыв,
сохранение сертификата Webmin/конфига Apache и блокировка Unix root.
Это проверки развёртывания и драйвера, не подтверждение работы ядра на PostgreSQL.
Подсказка первого запуска проверена в Chromium через Apache на английском и русском.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -v
```

В наборе 176 тестов; три требуют отдельного настоящего PostgreSQL и по умолчанию
пропускаются, отдельная команда приведена выше. Среди них сравнение 79 сценариев чтения, 96 сценариев
Schema/связей, 121 сценария JOIN/подзапросов/instance и 168 сценариев состояния
SObject, а также 78 сценариев Command/Transaction/Trigger с настоящим исходным
ядром TACTIC. Последние сравнивают порядок hooks, счётчики, стек, результаты,
ошибки и очереди; fixtures реестров явно начинают с пустых списков через
Container. Служебные записи ExceptionLog старого ядра не входят в сравнение;
они создаются только во временной копии. Добавлены 54 сценария SQL/журнала:
18 для ресурсов, запросов, команд и транзакций; 30 для SObjectUndo; 6 для Xml.
SQL сценарии работают на отдельных копиях данных и начинают с новых подключений
через исходные методы DbContainer; собственная основная фикстура не меняется.
Сравниваются также точные строки XML журнала и состояние SQL счётчиков.
Добавлены 165 сценариев подготовки SQL: Sql.quote, Insert/Update, SQLite
метаданные и преобразования, SObject.get_statement/commit(return_sql=True),
defaults/validation/security hooks. Сравниваются точные строки SQL, ошибки и
состояние объекта после каждого вызова. В сценариях случайного ключа
os.urandom получает одинаковый контролируемый источник байтов; исходный метод
Common.generate_random_key остаётся неизменённым. Отдельно проверены подготовка
SQL внутри Command без записи строк и отказ неперенесённых defaults.
Добавлены 57 сценариев ProjectSetting, кеширования и генерации кодов;
их выполняет `tools/settings_probe.py`. Добавлен 71 сценарий классов журнала,
кешируемых lookup, XML значений, компрессии и подготовки change_timestamp;
их выполняет `tools/log_probe.py`. Добавлены 125 сценариев Pipeline, процессов,
связей, task-pipeline metadata, кешей, выбора defaults, SQL подготовки и
фильтров проектов; их выполняет `tools/pipeline_probe.py`.
Добавлены 155 сценариев выбора DB/static/integral триггеров, notification metadata,
вызова Python классов и handlers, ошибок, очередей, событий SObject, кеширования
Search lookup и отката SQL;
их выполняет `tools/trigger_probe.py`. Реестр SObject сценариев устанавливается
после первого поиска объекта, чтобы отдельно проверить dispatch без встроенных
Task/GlobalSearch/Folder обработчиков SearchType; их регистрация проверяется отдельно.
Один и тот же серверный скрипт `tests/scripts/trigger_contract.py` запускается
без переписывания импортов или тела в обоих ядрах: четыре сценария проверяют
два режима триггеров, успешную команду и rollback. Сравниваются результаты,
объект из кеша, события и фактические значения в БД. Скрипт использует доверенный
Sql с исходным set_record(False); рабочий SObject.commit этим не подтверждён.
Добавлен 71 сценарий регистрации встроенных триггеров, их no-op вызовов,
исключений, ключевых слов и пользовательских классов; tools/registry_probe.py
сравнивает определения, порядок, состояние и флаги запрошенных типов.
Пустые флаги сторонних типов, затронутых legacy ACL lookup, в это измерение
не входят. Одинаковый tests/scripts/registry_contract.py выполняется без правок
в обоих ядрах: fast_data, старые конструкторы, повтор после ошибки, SObjectFactory,
контекст, кеш, проекции и разные проекты. Регистрация Task/Snapshot проверяется
на fixture с generic SObject; предметные методы этих классов этим не подтверждены.
Добавлены 129 сценариев правил доступа, XML builder, lookup, уровней,
проектов и вложенных Sudo; `tools/access_probe.py` запускает неизменённый
`tests/scripts/access_contract.py` в обоих ядрах. AccessRule модуль проверен
по полному исходному тексту с одной ожидаемой правкой; остальные тела
AccessManager/Sudo, кроме пяти методов с защитами/исправлениями, — по AST.
Отдельно проверены изоляция запроса и неперенесённые ветки.
Добавлены 102 сценария объектов аккаунтов, defaults, UPN/namespace/cache,
уровней, билетов и настоящего Security. `tools/security_probe.py` запускает
неизменённый `tests/scripts/security_contract.py` в обоих ядрах. Семь сценариев
проверяют объявленные исправления исходного поведения. Проверены реальные
объекты в API запросе, отсутствие контекста после него, повтор отказавшего фильтра,
quoted names, общий уровень циклических групп, закрытые ветки и атомарный upgrade.
Добавлены 126 сценариев политики Search/SObject: типы, поля, ограничения чтения и
удаления, protected-type проверки, статические row filters, count до/после rows,
подготовка SQL удаления и XML-журнала. Тот же security_contract.py выполняется
в обоих ядрах. Исходный probe использует api_mode=closed для проверки поддержанного
режима. Восемь сценариев отдельно проверяют исправление pipe значений, два — обход
ACL через кеш после выхода из Sudo; ещё два подтверждают сохранение identity кеша
для объектов, которые остаются видимыми.
Добавлены 33 сценария системной записи журналов: тот же journal_write_contract.py
исполняется в обоих ядрах. Сравниваются возвращённые объекты и реальные строки
transaction_log, sobject_log, sobject_list, change_timestamp, включая удаление redo,
сжатие на границе 10 KiB, duplicate/delete references, id override, force_insert и rollback.
Generated timestamp заменён маркером; сжатие сравнивается по исходному XML.
Нативная проверка отдельно подтверждает валидность фактического timestamp и кода.
Пять сценариев явно фиксируют кеш удалённых/откатившихся записей и ранний отказ
отсутствующей keywords колонки.
Добавлены 19 сценариев автоматического журнала и предпочтений: вложенные команды,
record/undoable, изменения существующих меток, шесть timezone веток и ошибки записи.
Одинаковое тело скрипта исполняется в обоих ядрах; порядок выдачи задан по id.
Часы нормализуются в полях timestamp, changed_on и XML колонках timestamp,
случайные коды меток нормализуются явно. Формат времени и кодов проверяется отдельно.
Пять сценариев фиксируют исправления оригинала: is_undoable, две потери changed_by
и два случая частичной записи. Отдельно проверены deferred constraint при commit,
ошибка commit-хука и отказ от append/remote/file/межбазовой записи.
Добавлены 14 сценариев жизненного цикла аккаунтов: четыре совпадают с оригиналом,
десять имеют отдельные ожидания исправлений; прежний сценарий ошибки commit
также проверяет исправленный атомарный откат. Лицензионный сценарий исключён.
Всего проверено 1662 сценария на старом runtime.
В оригинальном get_change_timestamp остался Python 2 импорт `from search`.
Для выполнения его неизменённого тела probe явно связывает это имя с оригинальным
pyasm.search.search. Новое ядро использует свой обычный относительный импорт.
Отдельно проверены откат при неперенесённых ветках TransactionLog,
закрытие с откатом на выходе из запроса и запрет записи из блока чтения.
Проверяются также буферы изменений,
quoted_flag, классы и сообщения ошибок, копии/ссылки словарей, конструкторы,
metadata cache, NULL и установка связей. 1573 сценария сравнивают результаты и состояние без нормализации,
45 используют объявленную нормализацию сжатия, времени или случайных кодов,
44 фиксируют намеренные исправления исходных багов. Это не утверждение полной
API совместимости.
Оригинал запускается своим embedded Python
на отдельной временной копии фикстуры через `tools/legacy_read_probe.py`;
инструментирование команд находится в `tools/command_probe.py`, SQL и журнала —
в `tools/persistence_probe.py`, подготовка SQL — в `tools/statement_probe.py`.
На этой копии добавляются исходные служебные таблицы и выполняется Batch
авторизация; проверки ошибок Command создают там исходные ExceptionLog записи.
Рабочие БД legacy не участвуют; собственные БД нового ядра побайтово проверяются
на отсутствие изменений от чтения, staging и перенесённых команд.
Для новых XML-RPC методов сравниваются исходные тела функций после Batch,
без старого Command/decorator. Новый транспорт проверяется отдельно реальными
клиентами. Также проверены наследование SObject, изоляция кешей, ошибки XML,
циклические схемы и откат обновления БД при конфликте.

JSON транспорт и файлы админки проверяются через настоящий HTTP сервер.
Браузерный сценарий `frontend/tests/admin.mjs` проверяет вход, проекты,
фильтрацию, сортировку, страницы, карточку, экранирование HTML, игнорирование
запоздавшего ответа другого проекта, мобильную ширину, восстановление сессии,
выход и истёкший билет. Все данные этого сценария временные. Для его запуска
нужны Node.js, `npm ci` и Chromium от Playwright; без них тест явно пропускается.
Также проверяются английский старт при русской локали браузера, русский перевод
сообщений и заголовка, четыре сочетания темы/режима, сохранение настроек,
системный режим, повреждённые настройки и переключение оформления без API запросов
или потери введённого фильтра. Каталоги переводов проверяются на полноту
и совпадение параметров; компоненты — на использование переводов и общих токенов.
Раскрытый список дополнительно проверяется выбором мышью, клавишами Home/стрелки/Enter,
отменой через Escape, кликом снаружи и размещением внутри узкого/низкого окна.

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = 'D:\code\TACTIC_VUE\tactic_stream\.browser-cache'
cd frontend
npx playwright install chromium --only-shell
cd ..
```

Тесты также проверяют реальные запросы HTTP/XML-RPC,
исходные клиенты TACTIC и Handler без изменения их файлов, изоляцию проектов,
NULL/Unicode, формы результатов и отказ от неподдержанной записи. Алгоритмы
ключей и хеширования сравниваются с исходными реализациями; сигнатуры и SHA-256
сверяются со снимком. Серверные процедуры Handler пока не исполняются.
`six` закреплён среди серверных зависимостей: он нужен перенесённым исходным
модулям AccessRule/AccessManager и оригинальному SDK.

Для интеграционных проверок нужны `../legacy` и соседний `D:\code\th_codex`.
При отсутствии Handler или embedded Python соответствующий тест явно
пропускается. Проверка старого ядра охватывает чтение и перечисленный цикл
команд; полный старый HTTP сервер и авторизация ещё не сравниваются. При разборе старых
Python файлов Python 3.14 выводит SyntaxWarning о строках regex;
это предупреждения исходных файлов, которые тесты не изменяют.

Обновлять извлечённый baseline только намеренно, после проверки изменений:

```powershell
.\.venv\Scripts\python.exe -B -X utf8 tools\capture_legacy.py --handler D:\code\th_codex
```

Скрипт обновляет только ресурсы в `compatibility/`, включая journal_upgrade.json
с исходными определениями таблиц и миграций. Перенесённые Python модули он не перезаписывает.
В `spt_date.py` извлечены девять исходных методов SPTDate; импорты адаптированы
для самостоятельного пакета. Скрипт читает shipped
seed `legacy/src/install/start/db/sthpw.db` в режиме read-only. Рабочие данные
`legacy/local_data` не участвуют. Копия hasher сохранена без изменения;
лицензия исходного TACTIC — `LICENSE.TACTIC`.

## Следующие части переноса

1. Поддержка PostgreSQL, затем MySQL через исходные DbResource/Sql/DatabaseImpl:
   подключение, диалект, метаданные, bootstrap/upgrade, JSON/даты, транзакции
   и те же сравнительные сценарии на реальной базе.
2. Append существующего TransactionLog и согласованная запись между базами,
   оставшиеся Search фильтры и auth зависимости, изменение Pipeline/таблиц процессов,
   Workflow/process_state и встроенные обработчики записи; расширение предметного пути SObject.commit/delete
   и insert/update/delete
   с проверкой отката, журналов и побочных действий.
3. Оставшиеся методы Search/SObject, ExpressionParser и специализированные
   наследники SObject. Продолжать сверку с исходным TACTIC.
4. Серверное выполнение `execute_python_script`, `execute_cmd` и пользовательских
   процедур для любых клиентов; Snapshot, File, check-in и остальные группы
   публичного API. Проверять контракты по оригинальному SDK и интеграционным
   клиентам, включая Handler.
5. Создание проектов, установка плагинов и шаблонов через исходные команды/API.
   XML-RPC API, создание проектов и установка плагинов — отдельные этапы.
   Сообщать о готовности каждого для проверки реальных плагинов и шаблонов
   и подключения ТХ. Способ установки не привязывать к XML-RPC. Транспорт чтения уже
   существует вместе с выбранными account операциями и не означает готовности этого этапа.
6. Остальные публичные транспорты и протоколы; расширение Vue админки
   вслед за перенесёнными операциями ядра.

Переносить каждый следующий метод по его исходному поведению и зависимостям.
Полная совместимость требует совпадения результатов, ошибок, прав, транзакций
и файловых эффектов при вызове существующими клиентами.

## Пути и именование репозитория — 0.39.0

Целиком перенесены исходные `pyasm/biz/dir_naming.py`, `file_naming.py` и
`repo_handler.py`. SObject получил исходные методы репозитория и каталогов;
Snapshot и File используют ту же цепочку Project → DirNaming/FileNaming.
Сохраняются стандартные имена, версии/revision/context, последовательности,
явные выражения, override/default, сохранённые relative_dir/checkin_dir,
base_dir_alias, выбор классов в Project/ProjectType и пользовательские
классы/скрипты Naming. Активны серверные, web, env, client repo, local repo
и настроенные sandbox пути. Вычисление каталога само не создаёт его на диске;
параметр create выбирает новое именование вместо записанного пути, как в TACTIC.

В исходном TacticRepo включены copy/move/create. IO и изменения File проходят
через общий Command/Transaction/FileUndo; создание каталогов тоже журналируется.
copy сохраняет источник, move переносит исходник, create использует staged
upload. При rollback move возвращает исходник; upload после create сохраняется
в кэше для redo, как в оригинале. Проверяются режим, basename, числа объектов,
источников/MD5 и наличие исходных файлов. Полные BaseCheckin/FileCheckin ещё
не перенесены: это работа репозитория, не готовность публичного check-in API.

Исправлены None при отсутствующей File-записи, Windows absolute override,
потерянный явный project в get_dir_naming, позиционная передача ключей вместо
kwargs пользовательскому FileNaming и потеря Naming fallback после пустого
ответа пользовательского класса и двойная точка перед расширением sequence.
get_ext допускает отсутствие File. Вместо eval
для вызова метода подкласса используется getattr; исключения самого подкласса
не маскируются. Чтение каталога не записывает отсутствующий default ProdSetting.
File учитывает переданный Snapshot и собственный записанный каталог/alias;
Snapshot выбирает каталог нужного file type, а словарь путей сопоставляет File
по file_code, независимо от порядка строк в БД.

Неизменённый repository_contract запускается в настоящем оригинальном ядре
и native SQLite: имена, пути Snapshot/File, содержимое, MD5 и сохранение/перенос
источников. Дополнительный mkdir в журнале Stream проверяется отдельно как
исправление исходного нежурналируемого создания каталогов. Тот же скрипт и
поздний rollback проходят на SQLite/PostgreSQL; проверки затрагивают только
временные базы и каталоги. Отдельно проверены kwargs, fallback, отсутствующие
File-записи, переставленные file_code и отказ до IO при неверном имени/источниках.

Remote web URL, web-IP выбор RemoteRepo, Perforce/Subversion/S3, физические
versionless symlink/copy aliases и recovery после kill остаются явно закрыты.
API get_snapshot с include_paths ещё закрыт до переноса оставшейся сериализации.
Дальше — исходные BaseCheckin/FileCheckin: подготовка файлов, naming,
postprocess и полный жизненный цикл check-in в той же транзакции.

## BaseCheckin и FileCheckin — 0.40.0

Целиком перенесены исходные `pyasm/checkin/checkin.py` и `file_checkin.py`:
BaseCheckin, FileCheckin и привычные импорты. Обычный FileCheckin выполняет
исходный цикл: проверка lock, регистрация File, создание Snapshot и версии,
postprocess путей, Naming, перенос в репозиторий, commits, current/latest
и checkin-триггеры с исходными snapshot/files/search_key/update_data.
Весь цикл использует общий Command/Transaction/FileUndo; версии резервируются
до чтения, как требует параллельный check-in. Перенесены исходные
Snapshot.is_locked/lock/unlock: lock хранится на версии 1 соответствующего
контекста; запись требует администратора и активной транзакции.

Активны create (включая исходные mode=None/пустую строку), copy, move,
inplace и local, строгие правила Naming без физических versionless aliases,
несколько обычных файлов, явные file/dir expressions, версии/revision,
keep_file_name, source_paths, MD5 и single_snapshot. Auto/default naming
работает с do_update_versionless=False. Это готовность цикла ядра;
публичный simple_checkin/upload API пока не открыт.

Конструктор копирует входные списки вместо изменения данных вызывающего кода,
проверяет пустые/несогласованные аргументы и использует число файлов при
строковом file_paths/MD5. Исправлены file_sizes, сравнивавшиеся сами с собой,
и потеря явно заданных expressions в auto режиме. Пустой результат Naming
не сдвигает индекс следующего файла. Rename upload проходит через FileUndo,
а basename проверяется до IO; относительный путь не превращается в путь
от корня диска. Rollback hook команды не удаляет файлы повторно — общий
журнал восстанавливает их после rollback hooks.

local больше не принудительно становится latest в конце check-in.
Postprocess выбирает XML node и file type по file_code, а не неоднозначному
имени файла. Inplace использует commonpath/relpath вместо startswith/replace:
assets_old не считается вложенным в assets, повторные совпадения в пути
не удаляются, разные Windows drives обрабатываются корректно.
В SObject исправлен преждевременный versionless hook при triggers='none';
FileCheckin управляет этими этапами явно, как исходная реализация.

Неизменённый checkin_contract выполняется в настоящем оригинальном runtime
и native SQLite: режимы, файлы, MD5, флаги, revision, multiple files,
auto naming без aliases, lock/unlock и checkin callbacks. Отличия от исходных
багов (изменение caller lists, строковые пути/MD5, sizes, потерянные expressions,
local latest, prefix inplace) проверяются отдельно. Тот же успешный сценарий
и поздний rollback выполняются на SQLite/PostgreSQL в временных базах и
каталогах. Отдельно проверены одноимённые файлы, single_snapshot, права,
опасное имя от Naming и отказ до IO при неперенесённых зависимостях.
Consumed create uploads при rollback остаются в кэше для redo, как в TACTIC;
move возвращает источник, а copy сохраняет его.

Физические versionless aliases, append/group/preallocation check-in,
metadata parsers, ingest, level lookup, context indexing, pipeline command
listeners и privileged chown остаются явно закрыты. Код специализированных
классов сохранён из оригинала, но их конструкторы завершаются явной ошибкой.
Обычный check-in сейчас требует подтверждённого администратора; права обычных
пользователей для этого цикла ещё не объявлены готовыми. Не запускать shell
команды для смены владельца файлов.

Дальше — физические versionless операции и специализированные check-in
потоки, затем публичные upload/handoff/simple_checkin контракты и SDK проверки.


## CURRENT/LATEST и файловые ссылки — 0.41.0

Включены исходные Snapshot.get_versionless/update_versionless и FileUndo.symlink.
FileCheckin создаёт auto-LATEST, а правила Naming — CURRENT/LATEST для strict/auto:
Snapshot с version=-1/0, XML ref_snapshot_code, связанные File и физический
versionless путь. Имена классов, методов и параметры сохранены. На Linux
по умолчанию используется относительная символическая ссылка, на Windows — копия и .link.
Опциональный `checkin/versionless_mode` доступен в конфигурации: `copy`, `symlink`
или `hardlink`. Явный symlink поддерживается и на Windows с нужными правами/режимом
разработчика; hardlink — для файлов на одном томе. Настройка проекта ProdSetting
имеет прежний приоритет. Обновление заменяет ссылку, не пишет через неё. Все изменения
проходят через общий Command/Transaction и требуют подтверждённого администратора.

Чекин Tactic Handler в режиме inplace допускает append в versionless (-1/0),
как исходный TACTIC. Если DeleteCmd в этой же транзакции убрал заранее размещённый
файл в undo-кэш, inplace возвращает его через FileUndo.move перед регистрацией:
повторная загрузка не оставляет alias с отсутствующим файлом, undo/redo сохраняется.
Проверки запускают неизменённую create_snapshot_extended через XML-RPC, включая
main/web/icon, повторный чекин и only_versionless. supplied cg.zip проверяется
на SQLite/PostgreSQL. В ТХ опция «Local versionless files» относится к локальному
размещению; удалённые алиасы определяет конфигурация сервера. По умолчанию — Copy.

Заменяемые ссылки, копии и .link сохраняются в файловом кэше до завершения
транзакции; mkdir и symlink входят в журнал до IO. При ошибке возвращаются
предыдущие байты, ссылки и записи, даже если прежний источник уже изменился.
FileUndo undo/redo работает с asset-relative и внешними абсолютными путями,
без изменения рабочего каталога процесса. Незавершённое IO запрещает commit.
Старые журналы symlink без сохранённых файлов пока отклоняются до IO; их
миграция не подменяется удалением текущего файла.
Версионные файлы остаются целыми; старые alias пути и File удаляются после
подготовки замены. Исправлены молчаливый пропуск отсутствующего источника,
неверный выбор файла при повторении типов, потеря project_code/base_dir_alias/
source_path/MD5, коллизии имени и устаревший кэш файлов. При переключении latest
его флаг выставляется до обновления alias, чтобы ссылка действительно переключилась.

Неизменённый versionless_contract проверен в настоящем оригинальном runtime
и native SQLite: повторный auto/strict check-in, оба alias, ссылки XML, файлы,
флаги и сохранность версионных данных. На PostgreSQL тот же успешный сценарий
и поздний отказ сравниваются с SQLite. Отдельная native проверка подтверждает
восстановление существующего alias/metadata после позднего отказа, очистку старого
имени, сохранность alias при пропавшем источнике, promotion старой версии и
undo/redo/частичную ошибку копирования с восстановлением точного старого .link.
Эти исправления исходных багов не объявляются полным совпадением с ошибками legacy.

Публичный upload/simple_checkin API, каскад удаления Snapshot с физическими
файлами/versionless, append/group/preallocation, sequence versionless, metadata
parsers, ingest, levels, context indexing и pipeline command listeners ещё
закрыты явной ошибкой. Это следующий участок переноса; полной совместимости
API пока нет. В этом этапе frontend не менялся. Docker обновляется через
manage.py update без сборки образов; Windows сервер не перезапускается.


## Удаление Snapshot, файлов и зависимостей — 0.42.0

Перенесён целиком оригинальный класс tactic.ui.tools.DeleteCmd из delete_wdg.py,
без UI renderer/виджетов. Сохранены имя класса, импорты, kwargs выбора объектов,
related_types/auto_discover и порядок каскада. delete_sobject с
include_dependencies=True вызывает этот класс для уже перенесённых типов записи.
Snapshot.remove_file удаляет файлы указанного типа и обновляет XML.
SObject.delete/delete_sobject(include_dependencies=False), как в оригинале,
удаляет запись без физического каскада File; это разные операции.

DeleteCmd удаляет принадлежащие Snapshot File и физические файлы/каталоги
через общий Command/Transaction/FileUndo. Пути определяются по конкретному File,
его сохранённому каталогу и base_dir_alias. Чужие File в прямых XML references
не дают права удалять чужой файл. После удаления версии LATEST переключается
на оставшуюся версию; CURRENT удаляется, если не осталось помеченного current
источника. При удалении последней версии оба alias, их File и .link удаляются.
Триггер больше не назначает версии -1/0 latest и не обновляет удаляемый alias
рекурсивно. remove_file обновляет aliases после изменения XML, сбрасывает кэш
и выбирает XML nodes по коду. Любая ошибка команды откатывает БД и файлы.
Прямое выполнение команды также требует подтверждённого администратора и TX.

WorkHour перенесён целиком без изменений: SObject, исходные project/login defaults,
CRUD, триггеры, журнал и удаление через auto-discovery. Его таблица/реестр взяты
из readonly install seed, search_code — из исходной миграции. Первый init/upgrade
создаёт эту зависимость на SQLite/PostgreSQL без ручного SQL.

Неизменённый delete_contract выполнен в настоящем оригинальном runtime и native:
удаление средней/последней версии, remove_file, WorkHour auto-discovery,
метаданные без физического удаления и поздний отказ. Ошибки оригинала при
Windows rollback и чтении удалённого File из кэша проверяются отдельно;
исправленная логика не выдаётся за совпадение с этими багами. Успешный сценарий
и откат файлов/WorkHour выполняются одинаково на SQLite/PostgreSQL.
Native проверки покрывают существующие CURRENT/LATEST с поздним откатом,
чужой XML File, очистку последнего alias, API include_dependencies,
удаление импортированного directory Snapshot, права и отказ для sequence/levels.
Directory check-in ещё закрыт; импортированный directory Snapshot удаляется.

Sequence/level repository deletion, неперенесённые типы/связи, удаление проектов
и search types, append/group/preallocation, upload/simple_checkin и обычные
пользовательские права check-in ещё не объявлены готовыми. Следом —
специализированные check-in потоки, затем публичный upload/check-in API.
Frontend не менялся; Docker обновляется без сборки образов, Windows сервер
не перезапускается. Полная совместимость API 1:1 остаётся целью переноса.


## Append и группы кадров — 0.43.0

Включены исходные FileAppendCheckin, FileGroupCheckin, FileGroupAppendCheckin,
FileGroup.check_paths/create и Snapshot.add_file. Имена, наследование и сигнатуры
сохранены. Append дополняет существующий Snapshot без новой версии. Группы
представляются одним File с base_type=sequence, суммарным размером, file_range
и одним XML node; ####, %04d и %0.4d разворачиваются с исходным шагом кадров.
Группы поддерживают copy/move/create/inplace/local через общий admin/TX путь.
Snapshot.add_file пока принимает обычные файлы в None/copy/move/inplace;
создание иконок, upload/manual/preallocate остаются явно закрыты.

Перемещение/переименование кадров, CURRENT/LATEST, remove_file и DeleteCmd
используют общий FileUndo. Versionless хранит диапазон и XML группы, создаёт
отдельные ссылки/копии кадров, чистит устаревшие кадры и Windows .link. Пути
групп с одинаковым file_type берутся по каждому File, а не по первому типу.
Rollback после append и удаления восстанавливает исходные файлы, перемещённые
источники, File/Snapshot, flags и прежний XML aliases. Нулевой/отрицательный шаг,
обратный диапазон, несколько frame markers, отсутствующие кадры и неверный
basename не приводят к успешному пустому check-in.

Исправления исходника: append старой версии не забирает LATEST; Snapshot
перечитывается после блокировки версий; групповой copy/move использует исходные
пути после naming; inplace XML сохраняет use_naming=false; переименование и
создание каталогов журналируются; MD5 одиночного кадра считается из источника.
Append сохраняет режим alias исходного Snapshot, поэтому default strict аргумент
не оставляет уже существующий auto alias устаревшим. Проценты/решётки в имени
папки не разворачиваются как номера кадров, разделители пути сохраняются.
Проверка level_id в DeleteCmd читает исходный NULL без числового auto_convert:
пустое поле не ошибочно блокирует удаление на PostgreSQL, реальный level остаётся
закрыт до переноса levels.

Неизменённый append_group_contract сравнивается с настоящим оригинальным
runtime: обычный append, Snapshot.add_file массива, четыре режима групп,
FileGroupAppendCheckin, range/metadata и физические payloads. Ошибки legacy
при назначении LATEST, naming copy и чтении inplace проверены отдельными
ожиданиями. Native lifecycle с CURRENT/LATEST, одинаковыми типами файлов,
уменьшением диапазона, очисткой и поздним rollback выполняется на SQLite и
реальном PostgreSQL одним и тем же скриптом. Проверки ограничены этим участком
и затронутыми FileCheckin/versionless/delete контрактами.

Далее: preallocation и серверные upload/simple_checkin/add_file API, затем
оставшиеся зависимости check-in (levels, ingest, parsers и pipeline listeners).
Готовность XML-RPC записи файлов, создания проектов и установки плагинов —
отдельные milestones; полной совместимости API пока нет. Vue не менялась,
Docker обновляется без пересборки образов, Windows сервер не перезапускается.


## Preallocation и файловые методы XML-RPC — 0.44.0

Включены исходные FileCheckin.get_preallocated_path и Snapshot.get_preallocated_path,
get_preallocated_path/get_virtual_snapshot_path/add_file/remove_file API.
API методы скопированы целиком из оригинала с адаптацией native imports,
конвертации SObject и явными guards для неперенесённых зависимостей.
Сохранены исходные сигнатуры, включая mkdirs, словарь Snapshot вместо code,
массивы путей/типов и возврат Snapshot dictionary. Виртуальный путь не создаёт
Snapshot/File. mkdirs=False рассчитывает путь без Command и записи журнала;
создание папок требует администратора и активного TX, использует FileUndo.mkdir.
Расчёт существующего файла не оставляет pending updates в его кэшированном SObject.

Предварительно размещённый файл регистрируется через FileAppendCheckin или
FileGroupAppendCheckin(mode=preallocate), без физического переноса. Номер версии
сохраняется, File/range/XML/MD5/flags проходят общий check-in. Нельзя незаметно
зарегистрировать файл из неверной папки или второй раз зарегистрировать тот же
путь. Naming не переименовывает уже размещённый файл. Важно задавать одинаковый
checkin_type при расчёте пути и регистрации: strict и auto могут выбирать разные
каталоги. API get_preallocated_path и add_file по умолчанию используют strict.
Как в исходном FileUndo, rollback регистрации оставляет payload в undo cache,
а не теряет его; метаданные и созданные внутри команды пустые папки откатываются.

upload_file(ticket, filename, Binary) принимает XML-RPC Binary и bytes, в том
числе пустые файлы. get_upload_file_size возвращает размер либо 0. Загрузка
пишется через временный файл и общий журнал: неудачная замена восстанавливает
предыдущие байты. Windows/Unix путь клиента превращается в безопасный basename
до размещения в каталоге текущего ticket. Исправлена обработка bytes из native
XML-RPC parser и Windows separators на Linux. Сохраняется существующий лимит
XML-RPC HTTP body 1 MiB; крупные файлы требуют отдельного HTTP uploader.

add_file поддерживает обычные одиночные файлы/массивы, preallocate/inplace,
серверные copy/move, а также заранее загруженные файлы в режиме None/create/
manual/upload/uploaded. Эти staging modes проходят исходный repository create.
Scalar file_type распространяется на список файлов; входные списки не меняются.
Версия/флаги существующего Snapshot сохраняются; aliases обновляются после
последнего файла массива. Публичный remove_file вызывает исходный метод ядра.
Handoff directories и create_icon пока дают явную ошибку до файловых эффектов.

Неизменённый preallocation_contract выполнен в настоящем оригинальном runtime
и native: core/API пути, виртуальный Snapshot, локальный SDK, binary/empty upload,
регистрация размещённого файла, массив append и remove_file. Этот же успешный
скрипт сравнивается на SQLite и реальном PostgreSQL. Дополнительно проверены
native rollback замены upload и preallocation, undo cache, группы кадров,
неверные/повторные пути и права reader. Оригинальный TacticServerStub прошёл
реальный XML-RPC цикл с bytes/Binary, preallocation, add_file и remove_file.

Это ещё не готовность всего файлового API: TacticServerStub.upload_file использует
HTTP UploadServer, который пока не подключён; simple_checkin, group_checkin,
add_group и handoff ещё не перенесены. Далее — HTTP-загрузчик и simple_checkin,
затем оставшиеся зависимости/режимы. Создание проектов и установка плагинов
остаются отдельными milestones. Vue не менялась, Docker обновляется без rebuild,
Windows сервер не перезапускается.


### Этап 0.45.0 — HTTP UploadServer и simple_checkin

Перенесён исходный FileUpload и весь клиентский UploadMultipart. UploadServer
доступен по прежнему адресу /tactic/default/UploadServer/, без старого UI renderer.
Поддержаны create/append, возобновление по offset исходного клиента, Base64-части,
обычные browser multipart файлы, Unicode/пустые файлы и относительный subdir.
Каждый HTTP запрос проверяет живой ticket и права записи; пути остаются внутри
его upload-каталога. Замена и append проходят через общий FileUndo: ошибка
последующего файла откатывает весь запрос и восстанавливает прежнее содержимое.

Исправлены исходные ошибки клиента: пустые файлы не пропускаются, успешный retry
возвращает результат, ошибка не теряется, подключения/файлы закрываются, имена
и поля корректно передаются в UTF-8, base_dir проверяет реальное вложение пути.
Append не повторяется автоматически после потери ответа: исходный протокол
не содержит offset/idempotency поля, и retry мог бы продублировать данные.
Одна HTTP часть ограничена 64 MiB вместе с multipart/Base64; стандартный клиент
выбирает части до 32 MiB. Это отдельный лимит, XML-RPC/JSON остаются по 1 MiB.
Неизменённый исходный клиент с явно заданной большей частью получит HTTP 413.

Включено полное тело исходного simple_checkin с прежней сигнатурой: поиск SObject,
исходные source_path/context, FileCheckin, версии/current/latest, словарь Snapshot
и __file_sobjects__. Режимы upload/uploaded/manual адаптируются к create ядра;
передаваемый info копируется, общий default словарь не изменяется. Часть без
иконок проверяется неизменённым скриптом в обоих настоящих ядрах и на
SQLite/PostgreSQL; исходный и поставляемый TacticServerStub проходят реальный
HTTP→XML-RPC цикл. Отдельно проверены browser multi-file, откат замены,
Unicode subdir, права reader и лимиты.

Это всё ещё частичная готовность файлового API. create_icon=True (исходное
значение по умолчанию) пока возвращает явную ошибку до check-in: для рабочего
пути сейчас нужен create_icon=False. Metadata, levels, handoff, context indexing,
custom checkin_cls и другой transaction_ticket также ещё не перенесены.
Следующий этап — IconCreator/медиа зависимости исходного check-in, затем
оставшиеся group_checkin/add_group и handoff. Проекты и плагины — отдельные этапы.
Vue не менялась; Docker получает файлы без rebuild, Windows сервер не трогаем.


### Этап 0.46.0 — исходный IconCreator и default image check-in

Включён исходный IconCreator в pyasm/biz/file.py: те же имя класса, методы,
обычные/покадровые имена *_web/*_icon, texture_mode/icon_mode, чтение web/icon
размеров и пакетный add_icons. Перенесена обработка изображений на Pillow 12.3.0
(https://pypi.org/project/pillow/12.3.0/). Импорт модулей не запускает внешние
процессы и не ищет ImageMagick. Используются существующие настройки ProdSetting;
для admin/sthpw сохранён исходный fallback размеров 640×480 и 120×100.

Обычный simple_checkin теперь поддерживает исходный create_icon=True по умолчанию:
основной файл сохраняется вместе с доступными web/icon File-объектами. FileUpload,
API add_file и Snapshot.add_file используют тот же IconCreator. Исправлен
подтверждённый NameError оригинального Snapshot.add_file из-за отсутствующего
импорта IconCreator. Append выбирает каждое доступное превью отдельно, copy/move
используют действительные исходные пути превью. Совпадающие repository filenames
по-прежнему отклоняются с откатом, существующие файлы не перезаписываются.

Превью сначала кодируется в приватном временном файле, затем публикуется через
FileUndo.create. Замена и context=icon копирование входят в общий журнал;
ошибка после check-in восстанавливает прежние превью и откатывает метаданные.
Неизвестные не-изображения получают исходное поведение без превью. Ошибки записи
или кодирования распознанного изображения больше не маскируются успешным check-in.

Исправления исходной Pillow-ветки проверяются отдельно от совместимых случаев:
LA/палитровая прозрачность на белом фоне, все EXIF orientations через ImageOps,
ограничение высоты квадратных/широких превью, отсутствие увеличения маленьких
портретов, отрицательная высота -1 в настройках, повторный execute с теми же
output-каталогами, исключение None путей из add_icons и отказ от старого превью
при ошибке конвертации. Сохранены первый кадр, имена/форматы и PNG texture output.
Действует пиксельный предел декодера, записи требуют активного admin/Transaction.

Неизменённый icon_contract сравнивает обе настоящие реализации: IconCreator,
icon/texture режимы, batch helper, FileUpload, simple_checkin и API append.
Этот же скрипт выполняется на SQLite/PostgreSQL. Проверен реальный HTTP→XML-RPC
клиент с Unicode/прозрачным изображением, default create_icon, append и удалением.
PDF, видео/animated GIF, ffmpeg/ImageMagick, handoff, metadata/levels и context
indexing ещё дают явные ошибки; полная совместимость файлового API не объявляется.

Модуль drupal_password_hasher удалён из поставляемых исходников. Его оригинальный
алгоритм проверки/создания TACTIC $S$ хешей теперь находится в tactic_password_hasher
с классом TacticPasswordHasher; Django/Drupal конфигурационные инструкции удалены.
Хеши, соли/число итераций и существующие пароли не изменены, Drupal CMS/session
поддержки нет. В source manifest сохраняется исходный путь для атрибуции алгоритма.

Следующий этап — исходные внешние media handlers для PDF/видео, затем оставшиеся
file/group API и handoff. Vue не менялась; Docker обновляется без rebuild,
Windows сервер не перезапускается. XML-RPC охват пока 35 из 129 методов (27,1%):
это число подключённых методов с частичным scope, не процент полной 1:1 готовности.


### Этап 0.47.0 — пакет из 13 XML-RPC методов

Вместо отдельных мелких этапов перенесён связанный пакет исходных API методов:
update_multiple, insert_multiple, insert_update, get_unique_sobject, clone_sobject,
retire_sobject, reactivate_sobject, create_note, get_tasks, get_pipeline_xml,
get_pipeline_processes, get_preference и set_preference. Использованы исходные
тела/сигнатуры и существующие native Search/SObject/Command/Transaction.
Настройки разделены по текущему пользователю и проекту, без старого UI.

SObject получил исходные retire/reactivate/clone; все подклассы используют общий
путь. Retire пишет RetireLog и вызывает исходные четыре события. RetireLog.create
активирован из оригинала; PrefSetting/RetireLog пишутся через общий журнал.
Массовые записи атомарны: ошибка строки или поздняя ошибка команды восстанавливает
объекты, настройки, retirement и системный журнал.

Исправления оригинала: get_tasks заменяет отсутствующий Search.set_parent на
существующий add_parent_filter; update_multiple определяет id по параметру ключа,
сохраняет входной порядок и читает данные по входному ключу, включая aliases.
insert_update больше не меняет переданный словарь. Clone сохраняет полный search
type проекта и допускает отсутствующий id; retirement без code записывает search_id.
Отсутствующая retirement колонка даёт ошибку до SQL. Исходная сериализация игнорирует
use_id; Stream сохраняет исправление и проверяет id keys отдельно.

Один неизменённый скрипт сравнивает исходный runtime и native SQLite, а также
SQLite/PostgreSQL; get_tasks source AttributeError отмечен отдельным ожиданием.
Реальный XML-RPC клиент проверяет пакет, id keys, настройки разных проектов,
откат ошибочного batch и отказ non-admin в записи.

Охват подключённых методов — 48/129 (37,2%), прибавка 13 методов, или 10,1 процентного
пункта. Это число методов с работающим частичным scope; full_api_parity_verified
остаётся false. Запись пока administrator и настроенная системная БД; metadata,
collections, recursive/repository clones, subscriptions, полная работа с проектными
базами и прочие ограничения предыдущих этапов ещё не перенесены. PDF/видео отложены
ради укрупнения API этапов. Следующие пакеты — repository/path/snapshot/group API,
затем workflow/pipeline API; создание проектов и установка плагинов остаются
отдельными этапами. Docker обновляется из bind-mounted исходников без rebuild.


### Этап 0.48.0 — 14 repository/snapshot/group API методов

Перенесены исходные get_handoff_dir, get_paths, get_base_dirs, get_client_dir,
get_path_from_snapshot, get_expanded_paths_from_snapshot,
get_all_paths_from_snapshot, get_dependencies, get_all_dependencies,
group_checkin, add_group, query_snapshots, get_snapshots_by_relative_dir и
set_current_snapshot. Сохранены исходные сигнатуры, ключи/конверты ответов,
строковые поля результата group_checkin и decimal-count description. Код использует
существующие Snapshot, FileGroupCheckin/FileGroupAppendCheckin, Search/Config и
Command/Transaction/FileUndo; зависимость от старого Web/UI заменена Environment.

Работают upload/uploaded и inplace group check-in, append из upload, copy/move,
inplace и preallocate через общий journal. Upload проверяет ticket directory до
файловых действий; очистка входных кадров журналируется, inplace сохраняет файлы.
query_snapshots сохраняет list-ответ, включая single=True, projection и служебные
ключи, сортировку/пагинацию и flags paths/paths_dict/web_paths_dict/parent/files.
get_snapshot получил уже работающие path/dictionary flags. Все чтения используют
те же vendor-neutral SObject/Search/Sql и существующие права.

Исправления оригинала: get_path_from_snapshot больше не теряет search key из-за
повторного lookup; выбор нескольких file_types собирает все пути и учитывает
expand_paths. Shared Snapshot.get_paths_by_type разворачивает последовательности.
get_dependencies запрашивает файлы зависимостей, а не содержащего snapshot.
Shared ref-read методы передают mode и сравнивают tags как данные, включая кавычки.
set_current_snapshot использует исходный Snapshot.set_current, очищает прежний
current и обновляет alias. query parent разрешается по родителю каждого snapshot,
в том числе code-only. Relative-directory lookup учитывает base_dir_alias.
Config dictionaries читаются через literal_eval без исполнения Python из строки.

Один неизменённый скрипт проверяет оригинальный runtime и Stream, затем SQLite/PG:
group check-in двух версий, append кадров, queries/parents/files/paths и refs.
Старые latest/current cache defects проверены отдельными ожиданиями; общие поля и
пути сравниваются точно после удаления только installation-specific base directory.
Неизменённый клиент выполняет group_checkin/add_group(mode=upload), включая
обязательный get_handoff_dir. Чтение handoff пути не создаёт каталоги на сервере,
сохраняет client/server OS Config keys и ticket isolation; handoff check-in ещё guarded.
Клиент проверяет search keys, многотиповые sequences, missing-frame rollback,
current selection, projection, alias filtering, dependency mode и quoted tags.
Поздняя ошибка откатывает файловые/системные записи и repository в общем Command.

Охват — 62/129 (48,1%), +14 методов/+10,9 процентного пункта. Методы сохраняют
частичный scope, full_api_parity_verified=false: группы с metadata/handoff,
get_paths/get_snapshot level/versionless lookup, full XML и non-admin writes
остаются явными ограничениями. Создание проектов/установка плагинов ещё не готовы
к тестированию на пользовательских данных. Следующий большой пакет — workflow,
pipeline/task API и dependency mutation. Docker обновляется без image rebuild.


### Этап 0.49.0 — 13 workflow/pipeline/task/dependency API методов

Перенесены исходные get_task_status_colors, get_input_tasks, get_output_tasks,
create_pipeline, get_pipeline_xml_info, get_pipeline_processes_info, call_trigger,
call_pipeline_event, get_pipeline_status, add_dependency, add_dependency_by_code,
lock_sobject и unlock_sobject. Названия, сигнатуры и конверты ответов сохранены;
исходные тела подключены к общим Search/SObject, SnapshotBuilder, Trigger/Workflow
и Command/Transaction. call_pipeline_event регистрирует уже перенесённые обработчики
в текущем запросе, проверяет все входные графы до событий и выполняет их атомарно.
Worker-wide регистрация всех типов Workflow остаётся отдельной задачей.

Pipeline получил исходные create/get_defaults/update_dependencies/update_process_table
и get_template_pipeline. Системный sthpw/pipeline включён в тот же административный
путь записи, журнала и триггеров. Создание делает config/process для каждого процесса,
update_process_table обновляет порядок/цвета и удаляет устаревшие процессы.
Автозаполнение pipeline_code использует SObject.commit, а не SQL в обход журнала.
Создание разрешено для зарегистрированных типов; необходимый DDL, process templates,
project config/pipeline persistence и pipeline version cloning пока явно guarded.

Исправления оригинала: create_pipeline передаёт description/search_type в правильном
порядке и соблюдает connected=False; значения XML атрибутов экранируются, неполный
process_types отклоняется до эффектов. Код pipeline закрепляется перед созданием
process records; повторное создание этих записей после commit удалено. Defaults не
пишут вне активной Command, даже при запросе SQL. Shared connect lookup принимает
Process объекты и кавычки как данные. Изменение pipeline очищает XML/status colors.
add_dependency принимает snapshot dict и передаёт type; исходник терял оба случая.
call_pipeline_event не накапливает process| при списке объектов. Вложенный ticket
дефект original get_pipeline_status отсутствует в native local API.

Один неизменённый сценарий сравнивает оригинальный runtime и Stream: pipeline/core
process creation, metadata/hierarchy/contexts, соседние tasks, пользовательский
триггер, два workflow события, snapshot refs по code/file и lock/unlock. Ошибочные
исходные metadata/connected, дубли process, второе событие и вложенный ticket
проверяются отдельными ожиданиями. Реальный исходный XML-RPC клиент проверяет
пакет без изменений, отказы non-admin и ошибки входных данных. Поздняя ошибка
откатывает pipeline/process/task/snapshot/file/message/state/status/note и журнал.
Сценарий также сравнивается на SQLite и настоящем PostgreSQL.

Охват подключённых методов — 75/129 (58,1%), +13 методов/+10,1 процентного пункта.
Это частичный scope, full_api_parity_verified=false. Иерархические/другие node types,
сложные process templates, schema DDL и проектные записи ещё не перенесены; создание
проектов и установка плагинов пока не готовы к пользовательским данным. Следующий
пакет — связи/instances и определение search types/колонок, затем создание проектов
и установка плагинов. Docker обновляется из исходников без image rebuild.


### Этап 0.50.0 — связи, instances и определения search types

Подключены ещё 13 XML-RPC методов: add_instance, get_instances, remove_instance,
create_search_type, add_column_to_search_type, connect_sobjects,
get_connected_sobjects, get_connected_sobject, check_access, class_exists,
get_release_version, get_server_version, get_server_api_version.
Охват — **88/129 (68,2%)**, +13 методов / +10,1 процентного пункта.
Статусы остаются partial, full_api_parity_verified=false.

Целиком перенесён SObjectConnection. Методы instances взяты из исходного SObject;
связь instance и промежуточная таблица определяются в Schema. Search.eval возвращает
исходный ExpressionParser и теперь передаёт mode, который исходник терял.
Полные search types/key сохраняют проект, как остальные native методы.

Из SearchTypeCreatorCmd перенесены backend-части: регистрация в search_object,
исходные defaults/колонки, config/naming, создание таблицы через CreateTable,
добавление типа в Schema. Старые WebContainer forms, widget/sidebar renderer
исключены для Vue. has_pipeline добавляет pipeline_code по исходному API контракту.
Generic зарегистрированные SObject на системном ресурсе используют существующие
Command, Security, triggers, change timestamps и журнал; исходный GlobalSearchTrigger
обновляет sobject_list. Отдельного ORM или второй модели данных нет.

DDL типов остаётся в DatabaseImpl/SqliteImpl/PostgresImpl. CreateTable, ColumnAddCmd
и API добавления колонки используют активную администраторскую транзакцию.
Проверяется грамматика SQL-типа, идентификаторы экранируются, metadata/table caches
обновляются после DDL и rollback. TableUndo/AlterTableUndo записывают исходные XML
узлы table/alter; поздняя ошибка откатывает таблицу, registry, naming, schema,
обычные строки, индекс и журналы. Durable undo/redo схемы пока не перенесён.

Исправлены исходные баги: duplicate connection lookup игнорировал context;
смешанные отсутствующие targets удаляли connections во время чтения; фильтры
попадали в общий cache; get_sobjects терял дополнительные типы. Связи инвалидируются
при изменениях объектов. class_exists больше не выполняет exec/eval и работает на
Python 3 через importlib, lookup пока требует admin. Устранены столкновения
classmethod SearchType с instance-методами SObject; PostgreSQL registry insert
использует sequence search_object, а не sequence новой таблицы.

Один неизменённый сценарий connections/instances/core CreateTable/access/version
сравнен с настоящим оригинальным runtime. Ошибочный original class_exists NameError
и mismatch base/full search type в get_connections проверяются отдельными
ожиданиями, без нормализации результата. Новые native creator/column/CRUD вызовы
проверены исходным клиентом через настоящий HTTP/XML-RPC. Отдельная короткая
проверка PostgreSQL сравнивает сценарий с SQLite и проверяет atomic DDL rollback:

```powershell
.venv\Scripts\python.exe -B -X utf8 deploy/docker/manage.py check-postgres --suite schema
```

В bootstrap/upgrade добавлены исходная пустая connection и исходная миграция
search_object.type; рабочие legacy данные не копируются. Версия сервера сообщает
реальный Stream release; API version берётся из поставляемого исходного VERSION_API.

Граница этапа: записи/DDL работают на настроенном системном ресурсе, включая
проекты, явно использующие эту же базу. Отдельные проектные БД, коллекции,
parent/template/preview creation, другие SQL schemas и общий instance traversal
остаются guarded. Полная исходная команда создания типа со старыми renderer
эффектами не сертифицирована. Следующий пакет — жизненный цикл проекта/создание
проектной БД и перенос backend установки шаблонов/плагинов; эти отдельные этапы
ещё не готовы к тестированию на пользовательских данных.


## Этап 0.51 — создание проектной БД

Перенесена backend-команда `tactic.command.CreateProjectCmd` с исходными именами,
метаданными, полями Project/ProjectType и simple base schema. Она создаёт отдельную
SQLite или PostgreSQL БД, импортирует 15 пустых конфигурационных таблиц из исходного
config_schema.sql, применяет уже принятые backend-миграции и создаёт начальные
search types через существующую SearchTypeCreatorCmd. Никакого второго ORM нет.
Первые системные БД по-прежнему создаёт явный bootstrap; проектную — эта команда.

XML-RPC `execute_cmd` сохраняет исходную сигнатуру, JSON/dict args и ответ
status/description/info. Команды наследуются от Command и используют исходные
can_run/requires_key и api_cmd ACL. Доступ сейчас требует администратора;
класс проверяется до конструктора. Renderer values, command key files и
use_transaction=False завершаются явной ошибкой. Охват — **89/129 (69,0%)**;
статусы partial, full_api_parity_verified=false.

При создании БД проверяются и активные, и retired проекты, а также уже существующая
физическая БД. Ошибки не подавляются. В отличие от исходника, нет промежуточного
commit и upgrade subprocess. Только исключительно созданные командой БД получают
разрешение на запись вместе со sthpw. Они коммитятся первыми; системная публикация
проекта — последней. При обычной ошибке откатываются записи и удаляется только новая
БД, её соединения закрываются и исключаются из pool. Повторная попытка в том же
контексте работает. Это компенсация создания, **не** distributed transaction или
гарантия восстановления после аварийного завершения процесса/сервера.

Исправлены исходные баги: Batch не вызывал check(), создание БД подавляло ошибку,
полный project_stype удваивал namespace. KeyboardInterrupt откатывает всю команду
вместо исходного commit частичной работы; отличие в четырёх hooks и вложенной
команде проверено отдельно на настоящем оригинальном runtime. Project.set_project
сохраняет пользователя, Container, Transaction и pool в рамках одного запроса;
переключение пока требует admin и существующего не-retired проекта.

Один изолированный lifecycle-сценарий проверяет одинаковый набор таблиц на SQLite
и PostgreSQL, начальные типы, чтение, поздний rollback с объектом, отмену,
ошибку после commit новой БД перед commit системы, повторную попытку и права.
Исходный неизменённый SDK также создаёт проект и читает тип через настоящий HTTP/XML-RPC.

```powershell
.venv\Scripts\python.exe -B -X utf8 deploy/docker/manage.py check-postgres --suite project
```

Граница этапа: готово создание **пустого simple-проекта** и начальных типов.
Запись в уже существующие отдельные проектные БД пока guarded до согласованного
commit с системным журналом. Other base schemas, project image/theme, запись
main-project config, установка project templates/plugins и долговременный undo/redo
пока не перенесены. Sidebar/старый renderer исключены по Vue-only scope.
Для тестирования пользовательских шаблонов/плагинов этап ещё не готов.
Следующие зависимости — транзакции существующих проектных ресурсов, затем backend
ProjectTemplateInstallerCmd и PluginInstaller; установка плагинов остаётся
отдельным этапом, не способом установки «через XML-RPC».


## Этап 0.52 — запись в существующие проектные БД

Снята граница «только system или новая БД». Существующие проекты на настроенном
SQLite/PostgreSQL endpoint используют тот же SObject, Command, Security, triggers,
глобальный индекс, change_timestamp и системный журнал. CRUD и создание/изменение
таблиц проходят через исходные классы; отдельного слоя хранения и vendor-веток
в предметных объектах нет. Ресурс проверяется по активной записи Project и её
физической database/code; одно имя, переданное в Sql, не даёт разрешения
на предметную запись. Внешние DbResource и несколько соединений к одной физической
БД в одной Transaction пока ограничены.

Один неизменённый скрипт SObject обновляет два существующих проекта, создаёт запись,
удаляет другую и проверяет реальные эффекты. Он совпал с настоящим оригинальным
TACTIC при успешной операции и поздней ошибке до commit. Тот же скрипт запущен
на SQLite и PostgreSQL с одинаковыми результатами; проверены исходные проектные
таблицы, журнал, timestamps и глобальный индекс. Исходный SDK создаёт проект,
делает CRUD в его отдельной БД и получает ошибки через настоящий HTTP/XML-RPC;
JSON транспорт проверен тем же временным сервером.

Исправлен SQLite DDL rollback: sqlite3 автоматически начинает транзакцию для
обычного DML, но отдельный ALTER/CREATE до первого INSERT/UPDATE мог сохраниться
сразу. Native Sql теперь явно начинает физическую транзакцию перед записью,
когда Command уже активна; BEGIN IMMEDIATE для snapshot allocation сохраняется.
Колонка, добавленная перед поздней ошибкой, отсутствует после rollback на обоих
vendors; metadata cache тоже обновляется.

**Транзакционный предел:** оригинальный TACTIC коммитит БД последовательно и
подавляет SqlException при commit. Общей атомарности между БД у него нет.
Stream сохраняет последовательный commit, но публикует системный журнал последним
и не подавляет ошибку. Ошибка до начала commit откатывает все присоединённые БД.
Если существующая БД уже сохранилась перед ошибкой следующей, вызывающий код получает
PartialCommitException с именами уже сохранённых БД; XML-RPC возвращает Fault 500,
JSON — error_code=partial_commit. Успешный rollback в этой ситуации не заявляется.
Файлы и пользовательские rollback hooks сохраняются, чтобы не разрушать эффекты,
на которые уже ссылаются сохранённые строки. Перед повторной попыткой нужно
проверить БД и файлы. Проверка сбоя последнего системного commit подтверждает
сохранность строки/файла и явную ошибку на обоих vendors и через SDK.
Это **не** распределённая атомарная транзакция и не восстановление после аварии;
неопределённый исход commit при потере соединения также требует проверки.

```powershell
.venv\Scripts\python.exe -B -X utf8 deploy/docker/manage.py check-postgres --suite project
```

Добавленных XML-RPC методов в этом этапе нет: охват остаётся **89/129 (69,0%)**,
все статусы partial, full_api_parity_verified=false. Расширено поведение уже
подключённых методов для реальных отдельных проектов. Новые ограничения не скрыты
за успешными ответами. Шаблоны/плагины, arbitrary renderer/form values, other base
schemas и durable undo/redo ещё не перенесены. Следующий пакет — backend установки
плагинов и шаблонов проектов; эти этапы пока не готовы для пользовательских пакетов.


## Этап 0.53 — backend установки плагинов и шаблонов

Перенесены `tactic.command.PluginBase`, `PluginInstaller`, `PluginTools` и
`ProjectTemplateInstallerCmd`. Установщик принимает исходный `manifest.xml`,
каталог или ZIP; `.spt` сохраняет исходные разделители и исполняемый Python с
`SearchType.create`/`CreateTable`. Подключены регистрация `config/plugin`, импорт
объектов и определений типов/таблиц/схемы, unique, подстановка проекта, вложенные
плагины, include и Python-шаги. Установка — backend Command, независимо от
XML-RPC; существующий execute_cmd также умеет вызвать перенесённые классы.
В bootstrap/upgrade добавлены исходные пустые таблицы и определения
config/plugin, config/plugin_content и config/url. Renderer не переносился.

Требуются сохранённые права администратора и активная Command/Transaction.
Конструктор читает пакет; распаковка и замена каталога происходят при execute.
ZIP распаковывается в настроенный plugins/templates, пути и ссылки проверяются.
Файлы входят в FileUndo; ошибка до commit восстанавливает предыдущий каталог,
строки и DDL. Новая проектная БД шаблона создаётся штатным CreateProjectCmd;
ошибка импорта удаляет только принадлежащую этой операции новую БД. Для установки
в существующий проект сохраняется его физическая БД/DbResource. Транзакционный
предел последовательных commit нескольких БД из этапа 0.52 сохраняется.

Неизменённый скрипт directory/SPT/include/Python сравнен с настоящим оригинальным
TACTIC при успехе и поздней ошибке. Отдельно проверено исправление исходного
force_insert: original при повторном unique-импорте явного ID подавляет ошибки
дубликата и оставляет старые данные; Stream обновляет существующую запись.
На SQLite и PostgreSQL проверены тот же скрипт, регистрация ZIP, таблица/схема,
повторный импорт ID/pipeline, UTF-8, запрет обхода пути и подмены admin, откат
заменённого каталога, directory/ZIP шаблон, повторная установка и удаление новой
БД при сбое. PostgreSQL восстанавливает sequence через транзакционный ALTER
RESTART с учётом импортированных ID/seq_max; SQLite использует AUTOINCREMENT.

```powershell
.venv\Scripts\python.exe -B -X utf8 deploy/docker/manage.py check-postgres --suite plugin
```

Рабочий состав пакета: зарегистрированные предметные SObjects, custom_script,
process/process_state, naming, pipeline, plugin/plugin_content/url и типы,
поддержанные текущим ядром. Экспорт/uninstall/updater, SQL views, старый
WidgetDbConfig, остальные config-типы, темы/images и forced/move режим шаблона
ещё не перенесены. Неизвестные узлы manifest, отсутствующие payload и ошибки
импорта завершаются ошибкой; успешная частичная установка не заявляется.
Полную готовность любых пользовательских плагинов/шаблонов это пока не доказывает.
Следующий пакет — backend config-объекты и зависимости реальных шаблонов;
старый UI будет храниться как данные, без запуска legacy renderer.
Охват транспорта остался **89/129 (69,0%)**, все методы partial;
full_api_parity_verified=false.

## Этап 0.54 — конфигурация плагинов и шаблонов

Перенесён исходный backend-модуль `pyasm.search.widget_db_config` с классами
`WidgetDbConfig` и `WidgetDbConfigCache`: XML views, элементы и display options,
поиск, создание, редактирование, commit и объединение по приоритету. Имена Python
display/action классов сохраняются как данные для будущего Vue-интерфейса.
Подключены исходные записи `ProjectSetting.create/add_value_by_key` и отдельный
deprecated `pyasm.prod.biz.ProdSetting`, на который указывает исходный реестр.
Пакеты теперь импортируют config/widget_config, prod_setting, trigger и
client_trigger через общий SObject/Command с правами, журналом и транзакцией.
Client trigger хранится как определение; его исполнение в Vue ещё не подключено.

Bootstrap/upgrade создаёт исходные пустые таблицы и registry. Новая проектная
БД и установщик пакета в существующий проект применяют исходные миграции:
priority/title/description для widget_config и снятие устаревшего UNIQUE(key)
для prod_setting. Поэтому один ключ может иметь значения для разных search types.
SQLite сохраняет записи, объявленные индексы/триггеры и AUTOINCREMENT при
пересоздании таблицы; PostgreSQL снимает именованное ограничение. Миграции
установщика входят в текущую транзакцию; durable schema undo остаётся вне scope.

Запись, удаление и rollback обновляют кеши конфигурации и определения триггеров.
Project.switch сбрасывает DB-derived handlers, сохраняя static/integral
регистрации. Исправлены обнаруженные ошибки оригинала: перемещение элементов
удаляло элемент перед AttributeError, insert передавал неверные узлы,
import_node возвращал None и менял документ, NULL priority ломал сортировку,
низкоприоритетные defaults затирали атрибуты/action, а кеш оставлял прежние
триггеры после установки в том же запросе.

Неизменённый скрипт импорта widget/settings/trigger/client_trigger сравнен с
настоящим оригинальным runtime при успехе и поздней ошибке; различия для
исправленных движения и кеша триггеров проверены отдельными ожиданиями.
На SQLite и PostgreSQL проверены пакет, scoped settings, XML копирование и
слияние, attribute views, запрет renderer/Mako, ошибка XML, запись/удаление с
rollback, переключение проекта и прежний directory/ZIP/template lifecycle.

```powershell
.venv\Scripts\python.exe -B -X utf8 deploy/docker/manage.py check-postgres --suite plugin
```

Можно начинать проверку реальных backend-пакетов с перечисленными типами.
Исполняемый Mako, legacy Python renderer/default views, frontend client triggers,
остальные config-типы, экспорт/uninstall, SQL views, theme/images и forced/move
режимы ещё не перенесены. Произвольные пользовательские пакеты пока не объявлены
полностью совместимыми. Следующий этап — оставшиеся config-объекты и зависимости
manifest, затем проверка реальных пакетов и клиента ТХ. Охват XML-RPC остаётся
**89/129 (69,0%)**, все методы partial; full_api_parity_verified=false.

## Этап 0.55 — остальные backend config-объекты

Подключены исходные config/pipeline, custom_property, ingest_rule,
ingest_session и translation: registry, пустые таблицы и запись через общий
SObject/Command. Они создаются при bootstrap, создании проекта и upgrade
установщика в существующем проекте. Для pipeline применён исходный upgrade
реестра на `pyasm.biz.ProjectPipeline` и перенесён оригинальный get_defaults.
Pipeline.update_dependencies обновляет config/process по исходной логике;
изменения XML, удаление и rollback сбрасывают кеши проектного pipeline.

Перенесён `pyasm.biz.CustomProperty` с исходным delete(log=False): удаляется
определение, колонка остаётся. delete(log=True) удаляет колонку целевого типа
и определение в текущей транзакции, записывая alter/drop/type в журнал.
Права проверяются до DDL; используется фактический DbResource типа. Исправлен
исходный AssertionError из-за передачи строки в DbContainer.get. SQL-ошибки
удаления больше не подавляются. Durable schema undo/redo пока не подключён.

Расширенный неизменённый скрипт импорта сравнен с настоящим оригинальным TACTIC
при успехе и rollback. Для исходного дефекта CustomProperty заданы отдельные
ожидания. На SQLite/PostgreSQL проверены новые типы, pipeline/process,
обычное удаление колонки, отказ в правах, зависимый SQL view, откат колонки и
определения, прежний ZIP/template lifecycle. Проверка остаётся одной командой
`deploy/docker/manage.py check-postgres --suite plugin`.

Ingest rule/session и translation — хранимые определения. Сам ingest engine,
подключение legacy translation к Vue, renderer/Mako, экспорт/uninstall и
остальные ранее описанные ограничения ещё не перенесены. Следующий блок —
экспорт backend-пакетов и оставшиеся операции их жизненного цикла. Количество
подключённых XML-RPC методов остаётся **89/129**, полная совместимость не заявлена.


## Исправление 0.55.1 — Windows shared socket

Windows-воркеры с сокетами монитора явно используют stdlib SelectorEventLoop.
Uvicorn не видел внешний multiprocessing и выбирал однопроцессный Proactor,
поэтому второй IOCP для общего listener давал WinError 87 при accept.
Linux и standalone-запуск сохраняют auto loop. Точечная runtime-проверка
проверяет HTTP от обоих процессов на одном порту, XML-RPC, замену одного
процесса с повторной проверкой HTTP и штатную остановку.

## Этап 0.56 — экспорт backend-пакетов

Перенесены PluginCreator и экспорт PluginTools, TableDataDumper/TableSchemaDumper
с исходными именами и сигнатурами. Manifest выбирает SObjects/search types,
include/Python-файлы; создаются UTF-8 SPT, итоговый manifest, ZIP и опциональная
регистрация config/plugin. Сохранены include_id, ignore_columns, unique,
replace_variable и relative_dir_column. Код пакета может содержать namespace.
Экспорт выполняется в обычном администраторском Command; файл, manifest и ZIP
входят в FileUndo и восстанавливаются при ошибке вместе с данными.

Исправлены искажение тройных кавычек в скриптах, отсутствие файла пустой выборки,
путь versioned ZIP, устаревший manifest регистрации, контекст include и ресурс
системных объектов. Table schema сохраняет id/колонки/NOT NULL/UNIQUE через
SQLite/PostgreSQL драйверы. Исправлено выпадение NOT NULL у integer в CreateTable
и пустой локальный ID в SObject.commit перед PostgreSQL sequence lookup.
Каталог PostgreSQL учитывает [NOT NULL constraints PostgreSQL 18](https://www.postgresql.org/docs/18/catalog-pg-constraint.html).

Неизменённое тело export_contract сравнивается с настоящим оригиналом: обычный
экспорт/импорт совпадает, для дефектов quotes/empty/file rollback ожидания
раздельные. Общий lifecycle на двух СУБД экспортирует ZIP и устанавливает его
в другой проект: таблица/UNIQUE/NOT NULL, явные ID, настройки, точное тело скрипта,
pipeline $PROJECT и разложенные SPT. Проверены отказ в правах, выход за каталог,
неподдерживаемый manifest и поздний откат существующего пакета/ZIP.

```powershell
.venv\Scripts\python.exe -B -X utf8 deploy/docker/manage.py check-postgres --suite plugin
```

Экспорт доступен серверным скриптам и через существующий execute_cmd; отдельной
Vue-кнопки пока нет. Это исходный экспорт plugin-структуры, не полный backup БД:
defaults/CHECK/обычные индексы исходным дампером не сохраняются. SQL views,
foreign/exclusion/partial/expression/NULLS NOT DISTINCT unique indexes,
primary key без id, вложенный plugin-export и raw SQL data dump пока явно
ограничены. Следующий этап — uninstall и оставшийся lifecycle пакетов/шаблонов.
XML-RPC остаётся **89/129 (69,0%)**, все методы partial; цель 1:1 сохраняется.

## Этап 0.57 — uninstall и повторная установка

Перенесён исходный PluginUninstaller: обратный порядок manifest, удаление
SObjects, вложенных пакетов, include и Python undo_path, очистка plugin_content
и снятие регистрации config/plugin. Пакетные файлы и общие определения
search types/schema остаются, как в оригинале. Права проверяются до эффектов;
ошибка удаления больше не подавляется. Рекурсивные manifest, выход за каталог
и неизвестные nodes завершаются явной ошибкой. Публичный handle_nodes сохраняет
очистку регистрации, рекурсивные include откладывают её до конца обхода.

PluginTools.remove_search_type сохраняет оставшиеся строки таблицы в backup SPT
и использует перенесённый DropTable. В отличие от исходного backup, сохраняются
ID и явные NULL; повторная установка восстанавливает их и чинит sequence до
удаления прочитанного backup. DropTable пишет исходный cache/drop_*.sql и журнал,
работает в текущем SQL/FileUndo Command, не делает ранний commit/CASCADE.
Ошибки и поздний сбой восстанавливают таблицу, строки, регистрацию и файлы.
Объекты, выбранные sobject-узлами, удаляются перед резервированием оставшихся
строк таблицы — это исходная логика, backup не означает сохранение всего пакета.

SQLite/PostgreSQL драйверы блокируют таблицу перед чтением backup. PostgreSQL
сам запрещает DROP зависимой таблицы; SQLite проверяет incoming foreign keys
и реальные зависимости view через [compile-time authorizer](https://www.sqlite.org/c3ref/set_authorizer.html)
и EXPLAIN, включая вложенные views. Проверка не запускает тело view.
Исправлены pipeline-выборка после переноса проекта, оставшийся force_insert
после импорта и обнуление уже возвращённого результата при следующем SQL-запросе.

Неизменённый uninstall_contract сравнен с настоящим оригиналом: обычное удаление
и поздний rollback совпадают; для swallowed delete, потери ID/NULL literals,
pipeline и списка SQL-результатов заданы отдельные ожидания. Общий lifecycle
проверяет SQLite/PostgreSQL, uninstall через execute_cmd, reinstall/sequence,
сохранность общих определений, отказ в правах, зависимый view, откат таблицы/файлов,
вложенные пакеты, реальный undo_path и рекурсию. Команда та же:

```powershell
.venv\Scripts\python.exe -B -X utf8 deploy/docker/manage.py check-postgres --suite plugin
```

Удаление работает по установленному каталогу, code или search_key. Uninstall
из ZIP и удаление определений системных/config-таблиц пока явно ограничены.
Ограничения portable schema из 0.56 сохраняются: это не полный backup БД;
durable schema undo/redo и восстановление после аварии не подключены.
Следующий блок — оставшиеся команды жизненного цикла проектов/шаблонов и
проверка реальных пакетов. XML-RPC по-прежнему **89/129**, все методы partial.


## Этап 0.58 — стоимость базового запроса и команды шаблонов

Повторный query по sthpw/search_object (limit=51, 47 строк, Windows/Python 3.14,
отдельная временная SQLite база) занимал 189–198 мс. После изменения тот же
замер даёт 26–29 мс. Это локальный замер всего Api.dispatch, включая авторизацию;
не гарантия задержки на любой базе и не сравнение скорости с сервером legacy.

Authenticator.validate определяет владельца через исходные Ticket/Login,
проверяя expiry, retirement, UPN и запрет guest. Группы и правила загружаются
один раз при bind_security в фактическом контексте пользователя/проекта;
тикет при этом перепроверяется. Между запросами права и identity не кэшируются.
Восстановлено повторное использование метаданных в request Container:
Store.resolve учитывает Store/полный search type/проект, SearchType.column_info
учитывает проект/search type. Запись SQL, DDL, rollback и savepoint rollback
очищают соответствующие кэши; прямые Store writes также инвалидируют метаданные.
Исправлен отдельный баг: Sql, полученный до Command, при записи регистрируется
в активной транзакции, поэтому его DDL больше не делает ранний commit.

Перенесены CopyProjectFromTemplateCmd и ProjectTemplateCheckCmd с исходными
именами и сигнатурами. Copy делегирует существующему installer, отдельного
формата шаблонов нет. Check проверяет prefix проекта, совпадение project_type
и namespace search types. Исправлены два перевёрнутых условия исходника,
опечатка Seach и неверный sthpw/search_type вместо sthpw/search_object.
Отсутствующие/retired проекты и пустой prefix завершаются ошибкой; execute
требует действующий admin/Command. Неизменённый скрипт проверки выполнен
в настоящем оригинальном runtime с отдельными ожиданиями исходных багов.

Проверены отзыв групп, expiry/disabled аккаунты, контекст Security, повторные
чтения без новых SQL, переключение проектов, raw registry update и поздний
DDL rollback. Чтения совпадают с original runtime; общие lifecycle schema и
plugin/template ZIP/copy/reinstall прошли на SQLite/PostgreSQL.

Whole-project ProjectTemplateCreatorCmd/export ещё не перенесён. Существующие
ограничения installer/plugin/portable schema сохраняются. Следующий блок —
исходный экспорт целого проекта и его оставшиеся зависимости, затем реальные
пользовательские пакеты. XML-RPC остаётся **89/129**, все методы partial.


## Этап 0.59 — экспорт проекта в шаблон

Перенесён целиком исходный ProjectTemplateCreatorCmd с execute, export_template
и get_zip_path. Команда собирает оригинальный manifest и через существующий
PluginCreator выгружает определения search types, project/project_type/schema,
config/custom_script, widget_config, naming, client_trigger, process, trigger,
url, prod_setting, проектные группы, pipeline и уведомления. Формат тот же:
manifest.xml, SPT и ZIP. Пример внутри действующего admin Command:

```python
from tactic.command import ProjectTemplateCreatorCmd, ProjectTemplateInstallerCmd

creator = ProjectTemplateCreatorCmd(project_code='source_project', version='1')
creator.execute()
path = creator.get_zip_path()
ProjectTemplateInstallerCmd(path=path, project_code='new_project').execute()
```

Исправлена потеря типов собственного namespace проекта, когда project_type
назывался иначе. Экспорт читает текущую sequence без nextval/setval: оригинал
временно менял её, а для SQLite записывал seq_max=-1. Оба vendor сохраняют
максимум фактических ID и sequence; SQLite installer теперь восстанавливает
переданный floor даже после удаления строки с большим ID. Изменение floor
откатывается вместе с Command. Восстановление версионного ZIP и старых файлов
при поздней ошибке использует уже перенесённый FileUndo.

Запись метаданных sthpw/notification проходит общий admin/Command/SObject путь.
Изменения и переключение проекта очищают исходные notification/event кэши.
Отправка почты и GroupNotification остаются неперенесёнными.

Неизменённый экспорт сравнен с настоящим original runtime на временной SQLite
базе; исправления namespace, sequence и rollback имеют отдельные ожидания.
Общий lifecycle на SQLite/PostgreSQL проверяет версионный ZIP, автоматическое
создание проектной БД, точный текст скриптов/настроек, widget metadata, группы
и их project rules, pipeline, notification metadata, sequence floor и следующий
ID, отказ без admin, восстановление файлов/ZIP и rollback sequence.

```powershell
.venv\Scripts\python.exe -B -X utf8 deploy/docker/manage.py check-postgres --suite plugin
```

Можно начинать проверку реальных backend-плагинов и шаблонов простых проектов.
Это ещё не полная совместимость произвольного пакета: updater/move/force_database,
непростые базовые схемы, legacy UI renderer и прежние ограничения portable schema
остаются явными ошибками. Шаблон, как в оригинале, переносит структуру и настройки;
asset-строки и repository-файлы в него не входят. XML-RPC **89/129**, все методы
partial; новые backend-команды не увеличивают этот счётчик. Следующий блок —
оставшийся lifecycle шаблонов и зависимости реальных пользовательских пакетов.


## Этап 0.60 — настройки, подписки и XML-конфигурации API

Добавлены 13 методов с оригинальными именами и сигнатурами: subscribe,
unsubscribe, add_interaction, get_interaction_count, set_widget_setting,
get_widget_setting, get_plugin_dir, clear_upload_dir, fast_query,
set_config_definition, get_config_definition, update_config, add_config_element.
XML-RPC теперь **102/129**, все поддержанные методы по-прежнему partial:
это счётчик доступных методов, а не процент полной совместимости.

Перенесены исходные классы pyasm.web.WidgetSettings и pyasm.biz.Subscription.
Таблицы sthpw/subscription, interaction и wdg_settings вместе с оригинальным
registry создаются/обновляются автоматически на SQLite и PostgreSQL. Настройки
хранятся в БД, кэш живёт только внутри запроса и сбрасывается при записи,
удалении и откате. Подписки дополнительно разделены по проектам.

XML-методы используют перенесённый WidgetDbConfig и исходные встроенные
simple/admin/DEFAULT/children определения. Это метаданные для API, без запуска
legacy renderer. Пункты управления коммерческими лицензиями исключены при
захвате XML; исходные copyright-уведомления сохранены. Исправлены потеря login
при создании личной definition, изменение общей конфигурации вместо личной,
условие new_separator, перенос XML-узлов между документами, двойное экранирование
амперсанда, named-view root и изменение переданного display_options.

Записи используют существующие persisted-admin/Command/SObject/journal пути.
clear_upload_dir удаляет только каталог текущего тикета через FileUndo, без
создания отсутствующего каталога; файлы восстанавливаются при поздней ошибке.
fast_query требует security/enable_fast_query=true и администратора, сохраняет
текущую Security. Оригинал заменял её пустым объектом и терял доступ к проекту.
Ошибки XML-конфигурации возвращаются как ошибки API вместо HTML ExceptionWdg.

ProjectTemplateUpdaterCmd в оригинале пустой: совместимое имя теперь доступно,
но execute явно сообщает об отсутствии реализации. Для явного повторного
импорта уже перенесён ProjectTemplateInstallerCmd(new_project=False).
Deprecated form-backed WidgetSettings, legacy renderer, неперенесённые базовые
схемы/view_as_attr без @, durable transaction и ExceptionLog persistence пока
не поддержаны. Полные notification/email dispatch и регистрация взаимодействий
через отдельный движок также не добавлены.

Один и тот же скрипт сравнен с настоящим original runtime: нормальное поведение
совпадает, исходные баги имеют отдельные ожидания. Общий lifecycle на SQLite
и PostgreSQL проверяет настройки, Unicode/XML, личные definitions, builtin
metadata, уникальные имена, перестановку и удаление элементов, подписки,
взаимодействия, границы прав, RPC dispatch и откат SQL/журнала/файлов.

```powershell
.venv\Scripts\python.exe -B -X utf8 deploy/docker/manage.py check-postgres --suite plugin
```

Следующий блок — оставшиеся API команд/журналов/очередей и их исходные
зависимости. Проверка настоящих пользовательских плагинов и шаблонов остаётся
отдельной от уже пройденных backend lifecycle-проверок.


## Этап 0.61 — команды классов, очередь и checkout

Добавлены девять методов с оригинальными именами и сигнатурами:
generate_ticket, test_speed, test_error, get_connection_info,
execute_class_method, add_queue_item, checkout, get_full_snapshot_xml,
get_doc_link. Теперь **111/129** методов доступны, все остаются partial;
полная совместимость произвольного скрипта/API ещё не подтверждена.

Перенесён целиком исходный класс tactic.command.queue.Queue: add и get_next_job.
Таблица sthpw/queue, registry, исходные миграции data/message_code/interval
и queue_state_idx автоматически добавляются в новые и существующие базы.
Получение задания использует оригинальное условное UPDATE pending → locked:
один job получает только один потребитель. Даже пустая очередь требует
аутентифицированного администратора и активного Command; SQL и SObject
используют общий vendor/ресурсный путь. Исправлены возврат закэшированного
pending после успешного получения и замена явного приоритета 0 на 9999.
Оригинальное текстовое поле priority и его порядок сортировки сохранены.
Очередь, как в исходнике, исключена из undo-журнала, но её изменения участвуют
в обычном SQL rollback. JobTask, scheduler, автоматический запуск команд,
возврат зависших заданий и crash recovery пока не перенесены: add_queue_item
сохраняет задание, не запускает его немедленно. Произвольные sync-job типы и
server_code без соответствующего столбца в исходной схеме не поддержаны.

execute_class_method использует исходную логику Common.create_from_method
с теми же аргументами и конструктором без параметров. getattr заменяет eval;
недопустимое/приватное имя метода отклоняется до создания объекта. API требует
persisted-admin и активный Command через существующий check_script_execution;
это доверенное серверное выполнение Python, без отдельной песочницы.

checkout возвращает оригинальные client_lib_paths, sandbox_paths и web_paths,
выбирает snapshot/context/version и проверяет lock. Исправлены вызовы Trigger.call:
обеим checkout-событиям передаются caller/event/output, специфичное событие
получает проектный контекст. Оригинал пропускал callback; тест сравнивает эту
разницу отдельно. Level checkout остаётся явной UnsupportedContract. Sandbox
использует исходные checkin/win32_sandbox_dir или linux_sandbox_dir настройки.

Включён исходный Snapshot.get_full_snapshot_xml через уже перенесённые
SnapshotBuilder/File/DirNaming. Он добавляет version/description и файловые
checkin_dir/client_dir/web_dir/source_path. Формируется отдельный XML, исходный
кэш не меняется. Вместо XPath по имени файла обогащается сам file-node:
устранена исходная XmlException для имён с апострофом. Отсутствующий File
вызывает ошибку, никаких файловых операций метод не выполняет.

Перенесён исходный headless pyasm.web.Url и Environment.get_base_url/get_install_dir.
urllib.parse с doseq=True исправляет повторяющиеся параметры-списки, не меняя
входные значения. Legacy WebState остаётся исключённым. JSON и XML-RPC передают
ограниченный HTTP environment в Container текущего запроса; удалённые URL
используют его origin, затем install/base_url, затем оригинальный batch
install/hostname + security/protocol. Чужой запрос не разделяет этот контекст.

get_connection_info возвращает исходные поля keys/port/global_pool/thread_pool/
num_database_connections/databases, но считает только соединения своего запроса;
legacy глобальный пул не вводится. Диагностика соединений и test_speed доступны
администратору, поскольку test_speed возвращает сырые строки тикетов, как оригинал.
generate_ticket генерирует ключ, не создаёт авторизационный ticket; test_error
сохраняет оригинальную NameError. get_doc_link использует установочный alias.json
или захваченные исходные aliases; пункт установки коммерческой лицензии исключён.
Это совместимые данные ссылок, отдельный legacy-сайт документации не установлен.

Один и тот же скрипт сравнен с настоящим original runtime: команды классов,
JSON очереди, получение/пустая очередь, диагностические ответы, документационные
aliases, полный XML и checkout. Баги original имеют отдельные ожидания.
Короткий lifecycle на SQLite/PostgreSQL проверяет права и поздний rollback,
два одновременных потребителя восьми jobs без дублей, вызов через dispatch,
JSON-RPC HTTP-контекст, XML-RPC URL origin, quoted filename и Url list options.

```powershell
.venv\Scripts\python.exe -B -X utf8 deploy/docker/manage.py check-postgres --suite command
```

Следующий блок — исходный исполнитель очереди, его scheduler/monitor зависимости
и отдельные журналы ошибок. Durable undo/redo, resumed start/finish/abort,
TransactionState и sync execute_transaction остаются неперенесёнными.


## Этап 0.62 — исполнитель очереди и scheduler

JobTask выполняет исходный последовательный repeat-путь: pending → locked →
complete/error, три попытки, пять секунд между обычными ошибками. TacticException,
неперенесённые контракты и частичный commit не повторяются. Сохранены публичные
имена/сигнатуры, kwargs['job'], пользователь и проект задания, PythonCmd,
Workflow и Command. Исправлены потеря kwargs и ошибка max_jobs_completed.
Захват и host записываются одной транзакцией; завершение входит в транзакцию
команды. Это не распределённая атомарность нескольких баз или внешних сервисов.

Перенесены Scheduler/SchedulerTask/SchedulerTaskCmd и целиком MIT-модуль Kronos.
Доступны однократные, интервальные, ежедневные и еженедельные задачи; исходные
cron/day/month алгоритмы сохранены в Kronos. Исправлены weekly tuple/опечатка,
регистрация single task, отмена интервала и Thread.setDaemon на Python 3.14.
Каждая задача получает отдельный Batch, исходный ticket и собственный Store;
временная или проектная база не подменяется глобальным data-dir другого сервера.

services/enable = tactic|queue включает один процесс очереди под monitor;
process_count по-прежнему задаёт число веб-воркеров. Новые установки включают
очередь по умолчанию; старые конфиги требуют добавления queue. В конфиге этой
рабочей папки queue уже включена и вступит в силу после перезапуска батника.
Обычный worker_timeout ограничивает и длительную команду очереди, поэтому его
нужно выбрать под реальную продолжительность задач. Зависший worker убивается,
monitor дожидается завершения процесса и возвращает только его locked-задания
по точному host:PID. Живые и чужие блокировки не сбрасываются. Трассировки и
результаты заданий пишутся в temp/log/queue.log с ротацией.

Пройдены один lifecycle SQLite/PostgreSQL (успех, permanent error, retry,
rollback, исчерпание попыток, scheduler/weekly/cancel и чужие locks), неизменённый
сценарий успеха/ошибки в настоящем оригинальном runtime, публичные сигнатуры и
реальное зависание собственного временного Windows queue worker с восстановлением.

Пока ограничены: выполнение серверных команд требует admin, удалённая
синхронизация отключена как в native API; fork/multi-site/add_sobject, persistent
scheduler definitions и interval queue не объявляются перенесёнными. Отмена
работает между попытками и при восстановлении; принудительного прерывания
исполняющегося Python через изменение state нет. Stop scheduler отменяет
будущие запуски, уже выполняющаяся задача заканчивает свой Command.
Восстановление после смерти всего monitor/машины, гарантии для внешних эффектов
и постоянные exception_log/debug_log ещё предстоят. Счётчик XML-RPC остаётся
111/129: это перенос исполнителя, а не добавление транспортных методов.

Следующий блок — постоянные exception/debug журналы и оставшиеся транзакционные
контракты. Отдельно сравниваем скорость одинаковой выборки: после 0.58 query
на временной SQLite занимал 26–29 мс, прежние 201 мс относятся к версии до
исправления; legacy get_widget 75 мс включает SQL и генерацию HTML виджетов.

Контрольный замер 0.62, Windows/Python 3.14 вне sandbox: 51 строка
sthpw/search_object, cold 28.8 мс, медиана 27.3 мс, диапазон 26.0–28.7 мс
по десяти повторным Api.dispatch с авторизацией. База временная; этот замер
не доказывает преимущество над legacy get_widget на другом сервере/данных.
Docker обновлён без image build, в существующей конфигурации включена queue
с сохранением исходного tactic-conf.xml.before-queue.


## Этап 0.63 — постоянные exception/debug журналы

Перенесены исходные pyasm.search.ExceptionLog и pyasm.biz.DebugLog: имена,
сигнатуры, уровни, login/class/message/stack_trace и category сохранены.
Их таблицы и registry автоматически создаются/обновляются на SQLite/PostgreSQL;
exception_log сохраняет исходную регистрацию generic SObject без code,
debug_log — класс DebugLog и исходную миграцию code.

Доступен исходный XML-RPC log(ticket, level, message, category='default')
с возвратом True, а также JSON RPC и локальный SDK. Счётчик методов 112/129,
все по-прежнему partial. Запись/чтение диагностических данных в API требуют
администратора; обычная ролевая модель журналов пока не объявляется готовой.

DebugLog сохраняется отдельным Command и отдельным SQL-соединением, с выключенными
undo journal, remote sync и triggers. Возвращаемый SObject уже имеет постоянный ID.
Оригинал пытался отделить журнал через Transaction.get(force=True), но продолжал
использовать SQL-сессии основной команды: реальный сравнительный сценарий показал,
что DebugLog получает ID, а затем исчезает при rollback основной команды.
Это исправлено: журнал остаётся, незавершённые бизнес-данные откатываются.
Invalid level выдаёт ValueError вместо assert, который Python может отключить.

Command.execute_cmd записывает ExceptionLog после отката top-level команды
и после ошибки commit, когда Transaction уже откатилась. Вложенная ошибка даёт
одну запись, а не запись на каждый уровень. log_exception=False выключает
автоматическую запись и предотвращает рекурсию. Сбой диагностического соединения
попадает в обычный worker/queue.log и не заменяет исходную бизнес-ошибку.
CommandExitException и KeyboardInterrupt сохраняют прежний путь отмены.
Глобальный DbContainer.rollback_all из ручного ExceptionLog.log удалён:
ручная диагностика не должна неожиданно откатывать чужую команду.

Явные ограничения: независимая запись во время активной записи основной команды
в системную БД пока отклоняется одинаково на обеих СУБД. Это важно для SQLite;
не эмулируем отдельную транзакцию вложенным commit и не возвращаем фиктивный ID.
Standalone/API-вызовы и команды, записывающие только проектную БД, поддерживаются.
Обработку такого system-writer случая, восстановление после смерти всей машины,
диагностику неавторизованных/всех read-only API ошибок и providers уведомлений
нужно продолжить. services/notify_user вызывает явную ошибку: email не отправляем.

Проверены одним lifecycle на SQLite/PostgreSQL: постоянный debug/exception,
commit/rollback, вложенные ошибки, неизменность флагов основной Transaction,
активный system writer, права, отказ логирования без подмены исходной ошибки,
JSON/XML-RPC. Неизменённый standalone/commit/rollback/local API сценарий сравнен
с настоящим оригинальным ядром; потеря исходного debug-журнала проверена отдельным
ожиданием. Публичные сигнатуры прошли проверку. Полный набор UI/ядра не запускался.

Следующий блок — жизненный цикл транзакций/журналов и восстановление после
падения всего monitor; существующие API undo/redo/resume и remote sync остаются
явно незавершёнными.

Дополнение 0.63, 2026-10-06: простой XML-RPC query больше не открывает SQLite
соединение для каждого служебного чтения. Read-only соединения принадлежат одному
RequestContext, закрываются также при ошибке; активный Command использует своё
SQL-соединение. Search берёт колонки через существующий кэш SearchType, который
сбрасывается при изменениях/DDL/rollback. Тикеты и права заново проверяются на каждом
запросе. Для первых десяти sthpw/search_object на одной рабочей SQLite-базе:
33 соединения сменились двумя, обработка ядра снизилась примерно с 23–30 до 6–8 мс.
Живой XML-RPC через стандартный ServerProxy, 30 чередующихся запросов на старый
8081 и временный сервер с исправленным кодом: медианы 30,71 и 8,76 мс;
ответы совпали. При открытии нового HTTP-соединения для каждого запроса медианы
45,77 и 27,96 мс. Эти замеры не гарантируют время других методов/СУБД/нагрузок.

Продолжение оптимизации 0.63: предварительная проверка личности читает только
постоянный тикет/expiry и login/UPN/retirement через параметры драйвера; полная
Security заново проверяет всё в контексте пользователя/проекта. Удалены второй
обход групп в Sudo/_do_login и повторный Store.resolve каждой строки fast_data.
Канонические пути БД принадлежат запросу; конфиг использует копию неизменившегося
разобранного файла, изменения на диске видны новым запросам, reload перечитывает
файл. Стандартные даты разбираются datetime, остальные — прежним dateutil.

Формат API-журнала взят из get_simple_cmd оригинального api_xmlrpc.py:
print_primary_info/print_secondary_info, thread ID и последовательный номер,
timestamp/user/function/ticket, массив аргументов, Duration/Memory/Increment.
system.py перенесён целиком; Windows по-прежнему показывает нулевую RSS.
По явному требованию пользователя тикет показывается в журнале; пароли и вложенные
секреты продолжают скрываться. Запись одного блока не перемешивается между потоками.
Duration имеет исходную границу: после init, без аутентификации/подготовки проекта.
Дополнительный Total Duration показывает полный dispatch, включая эту подготовку.
Сравнивать прежний полный native Duration с исходным method Duration некорректно.

Контрольный живой XML-RPC, 30 чередующихся чтений первых десяти строк,
2026-10-06: медиана полного вызова через ServerProxy — 5,50 мс на рабочем 8081
и 5,72 мс на отдельном worker с текущими исходниками; ответы совпадают.
У нового worker журнал показывает медианы Duration 0,000 с и Total Duration
0,004 с, с округлением до миллисекунды. Это не означает полный запрос за 1 мс.
Legacy 9123 на том же постоянном HTTP-соединении — 96,37 мс; существенное влияние
поведения транспорта не позволяет считать эту разницу ускорением ядра.
Измерение native dispatch с записью в файл без HTTP даёт медиану 3,34 мс.
Проверены 21 точечный контракт ядра/конфига/логирования после последних изменений,
а также lifecycle Command на SQLite и PostgreSQL и исходные security-контракты.

Аудит CPython 3.14, 2026-10-06: Windows 11 Pro 26200, Core Ultra 9 275HX
(24 ядра/потока), CPython 3.14.7 x64 MSVC 1944. GIL включён; JIT доступен,
но повторные замеры не показали полезного эффекта, поэтому остаётся выключенным.
Временная fixture содержит 10 000 объектов с кодами, Unicode именами, числами,
timestamp и описанием; 5% retired. Полные сценарии включают авторизацию и INFO
журнал; HTTP замеры дополнительно включают получение и разбор ответа клиентом.
Скорость измеряется без cProfile/tracemalloc, память и профили — отдельными вызовами.

Внедрены три изменения: разрешение класса один раз внутри fast_data batch,
пропуск нулевого преобразования обычной naive GMT даты и прямой результат query
для выделенного JSON API. XML-RPC/local остаются со строковым Python envelope;
JSON fast_query и другие методы сохраняют прежний тип результата. Полный JSON
сценарий 10 000 объектов: медианы 522,04 → 153,86 мс (3,39×; новое HTTP-соединение для JSON), пик Python выделений
в серверном JSON pipeline 199,21 → 32,07 МиБ. Пик RSS worker в одинаковой
последовательности HTTP сценариев: 281,07 → 114,34 МиБ. Это накопленный high-water
процесса, а не размер одного ответа. Маленький XML-RPC запрос остаётся около 5 мс.

Измерены отдельно: JIT, индекс под filter/sort, ProcessPoolExecutor с передачей
полного ответа, ThreadPoolExecutor, InterpreterPoolExecutor и HTTP concurrency.
Индекс на тестовой amount/id ускоряет конкретный фильтр, но не добавляется ко всем
проектам. 4 процесса ускоряют batch из 16 чтений примерно в 3,14× при росте общей
RSS; сервер уже использует процессы, дополнительного пула внутри API нет.
CPU потоки с GIL замедляют batch; 4 клиентских потока для HTTP ожидания помогают.
InterpreterPoolExecutor отклонён Pillow._imaging; установленная free-threaded
сборка не импортирует текущие ABI колёса Pillow/Pydantic. NumPy/Numba/Cython/Nuitka
не установлены и не объявляются проверенными ускорителями; численные циклы
в измеренных сценариях отсутствуют. Альтернативные PGO/LTO/tail-call сборки не
сравнивались. compileall даёт небольшой выигрыш запуска, но его стоимость перед
каждым запуском больше экономии одного worker; автоматического шага в BAT нет.

Проверки: 50 адресных тестов успешны, затем ещё 3 проверки query/fast_query и
конкурентных транспортов; реальный Command lifecycle SQLite/PostgreSQL успешен.
Общий запуск: 294 теста, 4 skipped, 10 failures/12 errors. Ошибка порядка строк
в одном новом тесте исправлена и проверена отдельно. Остальные 9 failures/12
errors воспроизводятся на сохранённых исходниках до аудита; общий набор остаётся
незелёным. Среди старых проблем — duplicate registry fixtures, устаревшие ожидания
UnsupportedContract, export fixture, CLI fixture и анализатор строк переводов.

Воспроизводимые инструменты: tools/performance_probe.py (ядро, JSON pipeline,
batch writes, JIT/index/executors), tools/performance_http.py (запуск, клиентские
HTTP сценарии, ограниченная concurrency). Полные параметры, результаты,
диапазоны, команды и статусы вариантов — .test-tmp/performance/audit.json;
журналы тестов и cProfile лежат рядом. Все экспериментальные записи — только
в private fixture/её временных копиях; рабочие серверы не перезапускались.

Финальный HTTP keep-alive, 15 повторов: JSON 10 000 объектов 496.21 → 129.42 мс (3.83×); ответы совпали. Проверки Handler остановлены по указанию пользователя; дальнейшее заполнение API — отдельная задача.

## Этап 0.64 — inline Python API, XML каталог и traceback пользовательских скриптов

Исправлен отказ `execute_python_script('', {'code': ...})`: оригинальный TACTIC
принимает inline код через этот API, и Handler использует его для серверных
процедур. Теперь сохранённый путь, inline code и file_path проходят через тот же
PythonCmd, local SDK, Mako и Command. Сохранённый путь имеет исходный приоритет.
Настоящий сохранённый администратор, api_method/api_cmd правила и активная
транзакция по-прежнему обязательны; Sudo не открывает исполнение обычному пользователю.
Ошибка inline скрипта откатывает предметные записи и транзакционный журнал.

Исходный WidgetConfig/WidgetConfigView перенесён из tactic/core/widget_config
в pyasm/widget/widget_config.py; SObjectDefaultConfig и
WidgetClassHandler/TableElementClassHandler также взяты из оригинала.
Сохранены XML представления, порядок элементов, каскад определений, атрибуты,
параметры и карта widget keys/class paths. Старый HTML renderer не запускается.
Исходные config2 XML определения упакованы с сервером; коммерческие лицензионные
элементы login удалены. Добавлены Project.get_search_types/has_table и Schema.get_xml.
Проверка таблиц/колонок использует общий vendor слой на SQLite/PostgreSQL.

Исправлены баги перенесённого кода: use_cache=False действительно перечитывает
файл; XML деревья не разделяются глобально; WidgetConfigView владеет своим списком;
import_element_node возвращает независимую копию; запись/удаление/rollback
config/widget_config сбрасывают производные view/options кэши. Сломанный исходный
прототип get_by_edit_search_type использует основной resolver с EditWdg layout.
Общий Xml получил read_file и исходное извлечение вложенных параметров.
Файлы поддерживаются как UTF-8; DTD/entities отвергаются. Полный XPath, другие
кодировки файлов и defaults, которые вычисляет renderer, остаются незавершёнными.

Неизменённые процедуры Handler get_projects_and_logins и
query_search_types_extended для admin/sthpw прошли через настоящий XML-RPC
на временном сервере: проекты, пользователи/группы, типы объектов/колонки,
pipelines, schema и XML views. GUI Handler и рабочий native monitor в этом этапе
не запускались/не перезапускались. Рабочий 8081 подхватит новую версию после
перезапуска Stream.

Mako сохранена. server/kwargs/аргументы/return и текущий Command контекст остаются
исходными. На ошибке используется её RichTraceback и стандартный Python
TracebackException с цепочкой исключений: имя сохранённого скрипта или файла,
точные строки исходника без смещения служебной оболочки. Оригинальный класс
исключения и rollback не меняются. exception_log хранит этот traceback;
XML-RPC/JSON execute_python_script возвращают его исполнителю-администратору.
Ошибки аутентификации/прав и обычные ошибки транспорта остаются без подробностей.
Это улучшение серверной диагностики; встроенный traceback.format_exc() внутри
пользовательского скрипта не подменяется. Полный код больше не печатается повторно
при каждом сбое, и для форматирования ошибки не компилируется ещё один Mako шаблон.
Ускорение успешных сценариев от этого изменения не заявляется.

Проверки: адресные XML/cache/bootstrap/security тесты прошли; одно тело XML
metadata контракта и исходные Python callbacks/workflow сравнили с настоящим
legacy runtime. Проверены точная строка сохранённого скрипта в XML-RPC/JSON и
exception_log, отказ чужому тикету, исходный тип исключения и rollback.
Реальный Command lifecycle с новым inline/XML metadata контрактом прошёл
на SQLite/PostgreSQL через существующий Docker, без пересборки образов.
Журналы: .test-tmp/widget-config-checks.log, .test-tmp/widget-config-postgres.log,
.test-tmp/mako-traceback-checks.log. Общий набор тестов не перезапускался.
Количество методов не увеличено за счёт углубления контрактов; полноценная
совместимость всего API ещё не завершена.

## Этап 0.65 — локальные SObject и загрузка объектов ТХ

Серверный SDK поддерживает исходный query(..., return_sobjects=True): настоящие
SObject и их предметные наследники, single=True и пустой результат {}.
Обычный local query возвращает список/словарь напрямую, как в оригинале;
Python XML-RPC сохраняет строковый ответ, JSON — JSON. Передача живых Python
объектов через внешние транспорты явно отклоняется.

get_sobject_dict, _get_sobject_dict и _get_sobjects_dict доступны в локальном
ApiXMLRPC. Конвертация взята из оригинального Python 3 пути и используется
также при ответах транспорта: datetime и Decimal превращаются в строки без
потери точности; metadata сохраняется в исходном виде. Исправлены исходные
ошибки с игнорированием columns/use_id, смешанными типами/проектами и первым
None в наборе. Исходный SObject не получает служебные поля от сериализации.
SDK ограничен текущим запросом и его Security; защищённые типы проверяются.
Запись через возвращённый объект остаётся внутри Command и откатывается при сбое.

Неизменённая query_sobjects из соседнего ТХ прошла через XML-RPC: фильтры,
пагинация/счётчики, родители по code и id, снапшоты с файлами и zlib ответ.
Это проверка процедуры загрузки, а не готовности всего GUI ТХ. Конфигурация
таблиц с обработчиками старого renderer и остальные контракты API ещё в работе.
tools/handler_smoke.py включает эту процедуру в проверку живого сервера после
перезапуска Stream. Рабочий BAT монитор автоматически не перезапускался.

Проверки: исходный local SDK контракт сравнен с настоящим legacy runtime;
адресно проверены исправления конвертера, права/контекст, rollback SObject и
неизменённый внешний клиент Handler. Журналы:
.test-tmp/local-sobjects-checks.log, .test-tmp/local-sobjects-security.log.
Новые native object/Decimal чтения также прошли в реальном Command lifecycle
на SQLite/PostgreSQL через существующий Docker без пересборки:
.test-tmp/local-sobjects-postgres.log.

Исправлен KeyError asset_base_dir в ТХ: шаблон tactic-conf.xml теперь содержит
полную исходную секцию checkin из install/template/config/tactic_linux-conf_python3.xml.
Сохранены названия ключей, исходные клиентские пути, web_base_dir, version_padding
и sudo_no_password. Установщик задаёт asset_base_dir внутри собственного data.
FirstRunInit дополняет старые конфиги только отсутствующими настройками, сохраняя
заданные значения, комментарии и XML v1/v2; повторный запуск файл не переписывает.
Метод get_base_dirs возвращает содержимое конфига, как в легаси: без вычисленных
fallback значений и переписывания путей в ответе API. Этот контракт также
сравнен с настоящим оригинальным ядром.
Неизменённый Tactic.get_base_dirs из ТХ прочитал полный ответ XML-RPC;
первая установка, переопределения путей и исходный файловый API проверены:
.test-tmp/base-dirs-checks.log. Исправление загрузится после перезапуска Stream.

## Этап 0.66 — SObject Undo/Redo и исходный Milestone

Перенесены целиком исходный undo_cmd.py, методы SObjectUndo.undo/redo и класс
RunTransactionCmd. Частично доступны API undo, redo, execute_transaction:
вставка, обновление, смена кода и удаление SObject, восстановление по журналу,
передача XML/записи журнала, повторная доставка по исходному code без повторного
применения. Запись сохраняет Command, права администратора и rollback.
Файловый/schema/site replay, remote sync и возобновляемые transaction_ticket
ещё явно ограничены; полной совместимости этого блока пока нет.

Исправлены ошибки исходника и адаптации: Python 3 DictType, преждевременная
запись пустого журнала перед XML replay, старый код объекта после переименования,
сравнение GMT с местным changed_on, одинаковые timestamp при выборе операции
и устаревший кэш SObject после replay в одном запросе. Обычный цикл и смена
кода проверены на девяти ожидаемых состояниях; фактические ошибки оригинала
фиксируются отдельно и не объявляются совпадением результатов.

Пропущенные таблица и регистрация sthpw/milestone добавлены из поставляемого
sthpw.db. Используется уже перенесённый исходный Milestone(SObject), включая
project_code по умолчанию. Установка и штатный upgrade создают эти зависимости
на SQLite/PostgreSQL без пользовательских строк из легаси.
Рабочая база Windows обновлена: неизменённый Handler query_sobjects для
milestone прошёл на 8081. Исходники ТХ остались без изменений.

Проверки: .test-tmp/undo-final-checks.log, .test-tmp/undo-milestone-postgres.log,
.test-tmp/handler-milestones-live.json. XML-RPC проверяет права, поздний rollback,
повторную доставку и явный отказ неперенесённым операциям. PostgreSQL проверен
в существующем Docker без пересборки. Новые команды API загрузятся после
обычного перезапуска Stream; пользовательский монитор не перезапускался.

## Этап 0.67 — клиентские транзакции и файловый Undo/Redo

Перенесён исходный TransactionState целым модулем, включая получение состояния
по тикету, set/get/reset и восстановление проекта. Включены API start, finish,
abort, set_state, set_project, а также Transaction.resume/resume_by_id.
Несколько запросов дописывают один долговечный журнал XML/zlib. Как в оригинале,
данные фиксируются после каждого запроса; start/finish объединяет журнал для
общего отката, а не держит открытую SQL-транзакцию между HTTP-запросами.

Общий журнал охватывает SObjects, XML-RPC/HTTP загрузки и check-in. Undo/Redo
восстанавливает файлы; поздняя ошибка SQL или прерванное копирование компенсирует
файловые изменения. Скопированные байты сохраняются для Redo, даже если исходный
файл затем изменён. При групповом откате check-in возвращает потреблённый upload
для отката предыдущей загрузки; переименования тоже проходят через FileUndo.

Исправлены баги исходника: повторный set_state больше не возвращает первое
значение; append объединяет XML-узлы без зависимости от строк сериализатора;
finish индексирует и сжатые журналы; старт копирует uploads по ключу тикета,
а не по словарю аргументов. Копия SDK закрывает прежний ServerProxy при замене.
Проверка чистого запуска также выявила и устранила циклический импорт нового
TransactionState через security; проверки прав импортируются при вызове.
Ошибка одного участника rollback больше не мешает откату остальных SQL/файлов.
Владелец и срок действия тикета проверяются, активный журнал нельзя незаметно
сбросить повторным start. Конкурентные записи сериализуются нативным Sql:
SQLite BEGIN IMMEDIATE, PostgreSQL блокировка строки ticket FOR UPDATE.

Исходные схема и регистрация sthpw/transaction_state входят в автоматическую
установку/upgrade SQLite и PostgreSQL. Проверены исходный TransactionState
на реальном легаси runtime, неизменённый клиентский модуль легаси через XML-RPC,
20 вставок/10 обновлений, сжатые журналы, конкурентные записи и файловый abort.
Штатный upgrade рабочей базы Windows выполнен. Новый API загрузится после
перезапуска Stream; пользовательский монитор автоматически не перезапускался.
Адресные проверки и проверка PostgreSQL запускаются без пересборки Docker:

```powershell
$env:PYTHONPATH='tests'
.venv/Scripts/python.exe -B -X utf8 -m unittest test_client_transactions test_transport.Transport.test_original_client_grouped_edits_and_file_abort -v
.venv/Scripts/python.exe -B -X utf8 deploy/docker/manage.py check-postgres --suite command
```

Текущий предел: записи требуют администратора; откат схем БД, multi-site и
remote sync не перенесены. Исторические versionless-журналы без резервных копий
явно отклоняются. Произвольная загрузка HTTP в чужой transaction_ticket также
ещё не включена. Полная совместимость API и старого renderer не объявляется.

## Этап 0.68 — откат схем через API

Исходные `TableUndo`, `TableDropUndo`, `AlterTableUndo` подключены к существующим
`undo`, `redo` и `execute_transaction`. Создание/удаление обычных таблиц и
добавление/удаление колонок восстанавливаются через native SQLite/PostgreSQL.
Журнал сохраняет данные, поддерживаемые определения ограничений, DEFAULT,
nullable, индексы/триггеры и стандартный счётчик ID, включая удалённые высокие ID.
Восстановление колонки возвращает её сохранённые значения по ID и сохраняет
текущие значения остальных полей. Новые строки получают штатный DEFAULT базы.
Изменившаяся после удаления схема и невозможный NOT NULL явно отклоняются.
Ошибки DDL/записи данных откатывают операцию в существующей Command транзакции.

Исправлены исходные дефекты: API `add_column_to_search_type` не записывал
журнал, а column Redo терял значения удалённой колонки. Неизменённый скрипт
проверяется на настоящем оригинальном ядре с отдельными ожиданиями этих багов;
исходный SDK проверяется через временный XML-RPC сервер.
В регрессии плагинов также исправлен формат локального Python `fast_query`:
исходный undecorated метод возвращает сериализованную строку, даже когда
обычный локальный `query` возвращает список. Проверки Security сохранены.

```powershell
$env:PYTHONPATH='tests'
.venv/Scripts/python.exe -B -X utf8 -m unittest test_schema_replay.SchemaReplayParity.test_reads_match_actual_original_runtime test_transport.Transport.test_unmodified_source_client_schema_undo_redo test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
.venv/Scripts/python.exe -B -X utf8 deploy/docker/manage.py check-postgres --suite command
```

Ограничения: изменение типа колонки, неполные старые schema-журналы,
перенос между vendors и специальные таблицы пока не поддерживаются.
PostgreSQL таблицы с особыми grants/storage/policies/inheritance, нестандартные
последовательности, generated/array/custom типы и nondefault collation
отклоняются; DROP/rebuild не выполняют CASCADE. Резервная копия таблицы пока
целиком находится в XML/zlib журнале в памяти. Для больших таблиц нужен
потоковый формат резервных копий. Multi-site/remote sync остаются отдельным
незавершённым блоком. Количество доступных XML-RPC методов не изменилось:
расширены рабочие ветки уже перенесённых методов, не заявлена полная совместимость.

## Этап 0.69 — REST и обновление конфигурации проектов

`send_rest_request(ticket, method, url, params={})` использует стандартную
библиотеку: POST отправляет форму, остальные методы выполняют GET; возвращается
декодированный JSON, включая ответы с ошибочным HTTP статусом. Проверки с
оригинальным runtime используют собственный HTTP сервер. Доступ пока для
администраторов; разрешены HTTP/HTTPS, авторизация через URL не перенесена.

Явная команда `run.py --data-dir data upgrade` обновляет конфигурационные таблицы
активных зарегистрированных проектов на настроенном SQLite/PostgreSQL endpoint.
Каждая база обновляется собственной транзакцией; распределённой атомарности нет.
Рабочие базы в этом этапе не обновлялись.

По решению пользователя древний production-слой исключён из переноса:
Asset/Shot/Texture, production-схемы, Flash/Maya naming, SessionContents и API
`commit_session`/`get_md5_info`. Их таблицы и реестр не создаются при установке
или создании проекта. Существующие пользовательские таблицы не удаляются.
Проекты создаются через админку/CreateProjectCmd, плагины и шаблоны;
проектные SObject/SearchType, конфиги, pipeline, snapshot/check-in остаются ядром.
По последующему решению пользователя каталог и импорты `pyasm.prod` удалены
полностью: API находится в `pyasm.web.api_xmlrpc`, настройки проектов используют
`pyasm.biz.ProjectSetting`. Алиасов для старых импортов нет.

Из 129 методов исходной инвентаризации доступны 121 с ограничениями поведения,
2 явно исключены. Остаются `execute_js_script`, `set_application_state`,
`set_palette`, HTML методы `get_widget`/`get_column_widgets` и `missing_method`.
Это учёт транспорта, а не процент полной совместимости. Решение о старом HTML
renderer принимается отдельно; его ответы не заменяются современным JSON.
ТХ не изменён.


## Этап 0.70 — уровни snapshot, metadata и удаление prod

Расширены исходные ветки `get_snapshot`, `get_paths`, `query_snapshots`,
`get_virtual_snapshot_path`, `checkout`, `simple_checkin`, `group_checkin`,
`insert`, `update` и их batch/upsert вызовы. Доступны strict check-in по уровням,
metadata, полный XML snapshot и чтение versionless. JSON merge/replace живёт
в исходном `SObject.add_metadata`, запись сохраняет Command/security/journal.

Исправлены дефекты оригинала: обход пропускал непосредственный родительский
уровень, строковый `'-1'` выбирал CURRENT вместо latest, поиск versionless по
process добавлял `context IS NULL`. `add_ref_by_snapshot` сохраняет исходные XML
ссылки без дополнительной записи в отсутствующую `sthpw/dependency`.
Отличия от ошибочного поведения проверены отдельными ожиданиями на оригинале.

Удалён каталог `src/pyasm/prod`, deprecated ProdSetting и стандартный
ProdNodeNaming; неиспользуемые SnapshotType/FileAccess удалены вместе с
пустыми справочниками; старые Python импорты намеренно исключены без алиасов.
`ApiXMLRPC`/`ApiClientCmd` и блоки логирования перенесены в `pyasm.web.api_xmlrpc`.
В Windows рабочем реестре удалены 32 ранее внесённых исходных определения
`prod/*`, с резервной копией; другие определения и проектные таблицы сохранены.
В Docker SQLite также удалены пустые SnapshotType/FileAccess и обновлена
привязка класса настроек, без rebuild и полной миграции. В установочных
ресурсах исключённых записей нет. `config/prod_setting` использует
действующий `pyasm.biz.ProjectSetting`, имя таблицы и настройки сохранены.

```powershell
$env:PYTHONPATH='tests'
.venv/Scripts/python.exe -B -X utf8 -m unittest test_snapshot_levels.SnapshotLevelsParity.test_reads_match_actual_original_runtime test_snapshot_levels.SnapshotLevelsParity.test_level_checkin_late_failure_rolls_back_rows_and_files test_file_api.FileApiParity.test_reads_match_actual_original_runtime test_transport.Transport.test_unmodified_source_client_snapshot_levels_and_metadata test_configs.ConfigParity.test_reads_match_actual_original_runtime test_foundation.Foundation.test_deprecated_production_is_excluded_from_bootstrap_and_api test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
.venv/Scripts/python.exe -B -X utf8 deploy/docker/manage.py check-postgres --suite command
```

Пределы: level + versionless aliases, handoff/context indexing, metadata parsers,
специализированные repository/check-in классы остаются явными ошибками.
Доступны прежние 121 из 129 методов с ограничениями, 2 исключены;
расширение веток не означает полную совместимость API. ТХ не изменён.

## Этап 0.71 — два комплекта и существующий Handler

Закреплено уточнение ТЗ в [HANDLER_DEPLOYMENT.md](HANDLER_DEPLOYMENT.md).
Готовый Handler использует свой клиент, presets и запуск; локальная поставка
должна включать его. Инвентаризация выделяет 26 клиентских методов из 41
кандидата и сохраняет receivers/аргументы и RPC зависимости SDK.

Добавлена отдача repository через StaticFiles по исходному `web_base_dir`,
включая Range/HEAD. Исправлено сравнение путей в общем `handle_file_naming`:
на Windows разные разделители больше не вызывают перемещение файла в себя.

`tools/handler_deployment_check.py` проверяет неизменённый SDK и процедуры
Handler на временном SQLite и настоящем PostgreSQL через Apache с тремя
backend-воркерами. По 12 сценариев прошли в обоих режимах, включая создание
проектной БД, CRUD, задачи/заметки, транзакции и HTTP upload/download.
Рабочие БД и Handler не изменены, Docker не пересобирался. GUI Handler,
Windows EXE/Electron и все функции клиента ещё не завершены/не проверены.

## Этап 0.72 — видимая конфигурация сервера и требования к AI API

В sidebar появился «Server configuration»: обзор XML-конфига без редактирования,
поиск по ключу/названию/описанию, группы сервисов, сети, БД, файлового репозитория,
безопасности и каталогов. Для каждого параметра показаны назначение, значение,
fallback при отсутствии и необходимость перезапуска. `tactic|queue` дополнительно
показан как два сервиса с состоянием. Это значения конфига, а не текущего
монитора: CLI overrides могут отличаться, `TACTIC_PORTS` показан отдельно.

Каталог `server/configuration.py` документирует 51 параметр штатного Config,
включая ограничения неперенесённых handoff/sudo и неиспользуемого log_type.
Неописанные настроенные ключи видны отдельно, без раскрытия значений.
`POST /admin/configuration` требует действующий тикет и права администратора,
не возвращает пароли/API secrets/путь секретного файла. Читает XML v1/v2;
не изменяет конфиг, не перезапускает процессы и не меняет XML-RPC API Handler.
English/Russian и общие темы сохранены. Редактор и применение настроек
ещё предстоят; смена vendor/пути не должна изображать перенос данных.

Дополнение по AI закреплено в UI_ARCHITECTURE.md: общий серверный слой,
выборочный контекст, metadata catalog, draft/validate/preview/apply,
ревизии/идемпотентность, штатный Naming и изолированные script tests,
отдельная activation и MCP. Это план и проект контракта, не готовый AI API.

## Этап 0.73 — редактирование сервисов и воркеров

В конфигурации сервера теперь можно включать очередь, менять число web-воркеров,
потоки запросов, интервал проверки и таймауты запуска/остановки/зависания/рестарта.
Веб-сервис остаётся включённым. Редактор использует штатный XML и Config;
`parse_service_config` проверяет значения и при сохранении, и при запуске монитора.
По умолчанию воркеры разделяют один listener. При явном `services/ports` или
`TACTIC_PORTS` число воркеров определяется списком портов, поле недоступно.
Настройки БД, сети, безопасности и файловых путей пока доступны для просмотра.

`POST /admin/configuration/save` принимает `{ticket, changes, revision}`;
`changes` содержит только восемь разрешённых ключей `services/*` со строковыми
значениями. Проверяются существующие права администратора, origin и размер
запроса. Ответ включает обновлённый обзор и `saved`/`restart_required`.
Неверное значение возвращает 400 с указанием поля, конфликт ревизии — 409,
невозможность записать файл — 503. Конфигурация изменяется без автоматического
перезапуска: применить новые параметры монитора можно после рестарта backend.

Штатный `Config.save_config()` и установщик используют общую файловую блокировку
на Windows/Linux и проверяют ревизию прочитанного XML. Перед публикацией редактор
сохраняет предыдущую конфигурацию в соседний `tactic-conf.xml.previous`;
временный файл публикуется атомарно. Сохраняются XML v1/v2, комментарии,
секреты и неизвестные настройки. Блокировка `<имя XML>.lock` остаётся рядом;
редакторы, не использующие её, не участвуют в этой блокировке. Это защита записи
серверного XML, а не будущая история/идемпотентность AI API. Hot path Config
по-прежнему переиспользует parsed snapshot, хеш не считается на каждом API-вызове.

Черновик формы сохраняется при переключении между данными и конфигурацией,
при смене языка и темы. Есть отмена, сохранённые значения и ошибки полей.
Пройдено девять адресных проверок: Chromium/EN/RU/мобильная ширина,
права/секреты, XML v1/v2, конфликт двух запросов, ошибка диска, запуск/кэш Config,
настройки аутентификации и два независимых процесса на Windows. Та же проверка
межпроцессной записи прошла в одноразовом Linux-контейнере существующего образа
без пересборки или изменения рабочих данных.

Команды адресных проверок из каталога продукта:

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_configuration_write test_transport.Transport.test_configuration_edits_validate_preserve_xml_and_refuse_stale_writes test_transport.Transport.test_configuration_is_admin_only_read_only_and_masks_secrets test_transport.Transport.test_vue_admin_in_real_chromium test_monitor.Configuration test_security_lifecycle.SecurityLifecycle.test_password_history_expiry_and_attempts test_security_lifecycle.SecurityLifecycle.test_configured_authentication_modes_and_inactive_expiry -v
```

## Этап 0.74 — связи Search и сортировка API

В общем `Search.add_join` перенесены ветки ссылок `search_type`, `search_code`
и `search_id`: оба направления, выбор code/id по исходной Schema, полный
тип родителя с проектом и префиксы вроде `src_search_type/src_search_code`.
JOIN использует реальные `SearchType.table_name`, включая отличия от имени
SearchType. Поддержаны цепочки и несколько разных связанных таблиц от одного
источника. Повторный JOIN к уже подключённой таблице оставляет первую связь,
как в прежних сценариях. Отдельные SQL aliases для нескольких экземпляров
одной таблицы не добавлены. JOIN между отдельными ресурсами БД остаётся закрытым.

Сортировка понимает `path:namespace/type.column` и `path:type.column`;
выбранный path передаётся в штатный Schema resolver. Путь работает через
`query` и неизменённый XML-RPC SDK: например,
`order_bys=['alternate:contract/join_tag.name']`. Аргументы, Python-literal
ответы XML-RPC и названия методов сохранены. Присоединяемый тип независимо
проходит штатную проверку Search/Security; запрет чтения не обходится JOIN.

Скрипт `tests/scripts/search_join_contract.py` выполнен без изменений
в оригинальном ядре, новом SQLite и настоящем PostgreSQL. Проверены 12
сценариев: code/id в обе стороны, префиксы, цепочка, ветвление, физическое
имя таблицы, три формы сортировки и повторный JOIN. Обычная сортировка и
повторный JOIN совпали с оригиналом. Для остальных зафиксированы конкретные
исходные ошибки отдельно от ожидаемых результатов нового ядра: SQLite SQL
ошибочно квалифицирует таблицу именем БД; discriminator ребёнка использует
тип самого ребёнка; префикс игнорируется; вместо физической таблицы берётся
логическое имя; второй JOIN от того же источника пропускается; path теряется,
а разбор сортировки с `:` также подменяет имя колонки. Ошибки оригинала
не объявлены совпадающим поведением и не воспроизводятся намеренно.

Проверены существующие отношения/instance/схемы и rollback, `Search.copy`,
SQL guards, права joined type и настоящий HTTP XML-RPC с исходным клиентом.
Устаревшие ожидания отказа для перенесённых веток заменены проверками данных.
Все новые SQL-сценарии дали одинаковый результат на SQLite и PostgreSQL.
Проверки используют собственные временные БД/процессы; Docker не пересобирался,
рабочие БД и Handler не менялись. Число публичных методов осталось прежним:
это перенос внутренних веток существующего API, не полная совместимость.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_search_joins.SearchJoinParity test_search_links.SearchLinksParity test_schema.SchemaParity test_schema_api.SchemaApiParity test_transport.Transport.test_original_client_queries_named_relationships_and_physical_tables test_transport.Transport.test_real_xmlrpc_preserves_original_python_query_envelope -v
docker compose -f deploy/docker/compose.yaml run --rm --no-deps --entrypoint python -e PYTHONPATH=/opt/stream-src:/opt/python-packages:/opt/join-checks/tests:/opt/join-checks -e STREAM_POSTGRES_HOST=postgres -e STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password -v D:/code/TACTIC_VUE/tactic_stream/tests:/opt/join-checks/tests:ro -v D:/code/TACTIC_VUE/tactic_stream/tools:/opt/join-checks/tools:ro app -B -m unittest test_schema_postgres.SchemaPostgres.test_schema_connections_instances_and_ddl_match_sqlite -v
```

## Этап 0.75 — индексация check-in и метаданные файлов

Включён исходный аргумент `context_index_padding` в `FileCheckin` и
`simple_checkin`, включая XML-RPC с неизменённым SDK. Ширина 1..32 задаёт
минимальное число цифр; числовые ASCII-строки принимаются. Номер выбирается
при исполнении под существующей транзакционной блокировкой Snapshot,
а не в конструкторе: две одновременно подготовленные команды получают
разные контексты. Берётся максимальный числовой суффикс, учитываются вложенные
контексты, переполнение ширины и retired-снимки. Неудачная публикация
откатывается и не резервирует номер. Названия процессов и правила Naming
сохранены: правило пути/имени должно различать подконтексты, например
`dir_naming='admin/metadata/{snapshot.context}'`. Одно лишь добавление индекса
не меняет настроенные пользователем правила нейминга.

Перенесён исходный `pyasm.checkin.metadata` со всеми десятью публичными
классами и их сигнатурами: `ParserImportError`, `CheckinMetadataHandler`,
`BaseMetadataParser`, `PILMetadataParser`, `ExifMetadataParser`,
`ImageMagickMetadataParser`, `FFProbeMetadataParser`, `IPTCMetadataParser`,
`XMPMetadataParser`, `XMPKeywordsParser`. Экспорты доступны также через
`pyasm.checkin`. Неэкспортируемый устаревший `IPTCMetadataParserX` и пример
ручного запуска не перенесены.

Автоматический hook читает настройку `SearchType.metadata_parser`, сохраняет
метаданные первого файла в Snapshot и метаданные отдельных File вместе с
`metadata_search`. `icon`/`web` исключены по исходной логике. Настройка
`search_object.metadata_parser` добавлена SQL исходной миграции
`upgrade_v4_2_0_a01_005` через общий механизм первой установки и upgrade.
Рабочие базы этой итерацией не обновлялись; изменения доступны после штатного
upgrade и перезапуска backend.

Исправлены исходные дефекты: File ещё не связан со Snapshot при чтении
Dirname; `copy`/`move` пытаются парсить несуществующее новое имя до перемещения;
`auto` запоминает парсер предыдущего файла. Существующий входной файл и уже
вычисленный `checkin_dir` теперь используются в общем hook. Файлы парсеров
закрываются; XMP Keywords разбирает настоящие байты XML с пространствами
имён, ограничением 1 МБ и запретом DTD/entities. Глобальный Xml/XPath не менялся.
FFProbe сохраняет значения с `=`, работает без первого `index`; ошибки
утилиты не маскируются последующей ошибкой декодирования. Вызовы `identify`
и `ffprobe` проверяют код выхода и имеют таймаут 30 секунд.

Pillow уже входит в поставку. EXIF/IPTC/libxmp, ImageMagick `identify` и
FFmpeg `ffprobe` остаются дополнительными зависимостями с явной ошибкой
отсутствия. Их работа на реальных медиа здесь не заявляется: проверены
контракты ошибок/таймаутов и разбор вывода. Метаданные групп файлов с
шаблонами кадров и специализированные медиа-сценарии ещё требуют переноса.

Один скрипт выполнен в настоящем оригинальном runtime, SQLite и PostgreSQL:
парсеры, прямой MetadataHandler и обычные индексы совпали с оригиналом.
Ошибка оригинального автоматического hook записана отдельно; исправленный
hook проверен по содержимому File/Snapshot и файлов. Проверены конкурентная
нумерация на обеих БД, откат после ошибки парсера, nested/overflow индексы,
авто-выбор на смешанных файлах, upgrade существующей тестовой SQLite,
все публичные сигнатуры и исходный XML-RPC SDK через настоящий HTTP.
Существующие check-in/upload/icons регрессии прошли. Проверки используют
только собственные временные данные; Handler не изменялся.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_metadata_checkin.MetadataCheckinParity test_transport.Transport.test_original_client_indexed_checkin_and_metadata test_checkin.CheckinParity test_upload_checkin.UploadCheckinParity test_icons.IconParity -v
docker compose -f deploy/docker/compose.yaml run --rm --no-deps --entrypoint python -e PYTHONPATH=/opt/stream-src:/opt/python-packages:/opt/metadata-checks/tests:/opt/metadata-checks -e STREAM_POSTGRES_HOST=postgres -e STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password -v D:/code/TACTIC_VUE/tactic_stream/tests:/opt/metadata-checks/tests:ro -v D:/code/TACTIC_VUE/tactic_stream/tools:/opt/metadata-checks/tools:ro app -B -m unittest test_schema_postgres.SchemaPostgres.test_schema_connections_instances_and_ddl_match_sqlite -v
```

## Этап 0.76 — handoff без HTTP-загрузки

Включены исходные ветки `simple_checkin(use_handoff_dir=True)`,
`add_file(use_handoff_dir=True)`, `group_checkin` из handoff и
`add_group(use_handoff_dir=True)`. Аргументы, возвращаемые объекты и формат
XML-RPC сохранены. Вместо старого WebContainer используется уже перенесённый
Environment; публикация идёт через те же FileCheckin/FileAppendCheckin,
FileGroupCheckin/FileGroupAppendCheckin, Command и FileUndo.

Клиентский и серверный пути — два адреса одной общей папки. Например,
Windows-клиент видит `//server/share/handoff`, а Linux-сервер —
`/mnt/share/handoff`. Их задают существующие `checkin/win32_client_handoff_dir`
и `checkin/linux_server_handoff_dir`; остальные два ключа отвечают за другие
ОС. Все четыре параметра уже видны в админке; обновлены их английские и
русские описания. Монтирование общей папки выполняет окружение развёртывания.

`get_handoff_dir` возвращает клиентский путь для XML-RPC и серверный для
локального API. К каждому добавляется каталог тикета. Если серверный корень
не задан, используется клиентский; без настроек — временный `handoff`.
Серверные относительные пути разрешаются внутри tactic_data, клиентские пути
возвращаются как настроены. SDK сам создаёт клиентский каталог и в режимах
copy/move переносит туда файлы перед вызовом серверного API. Это существующий
механизм клиента; код Handler не изменялся.

Имена тикетов больше не обрезаются до 100 символов в общем directory helper:
обрезка могла смешать два каталога и нарушить соответствие клиентского и
серверного путей. Повторно использована прежняя валидация имени тикета.
Каталог, связанный симлинком за пределы корня, отклоняется. Чтение пути не
создаёт каталоги на сервере.

Общая проверка путей применяется к handoff и upload. Для последовательностей
проверяются реальные пути каждого кадра, а не только шаблон. Выход через
список абсолютных путей, симлинк кадра или вложенный auto-контекст отклоняется
до публикации. Прямой серверный `add_file` copy/move читает сопоставленный
handoff-путь; клиентский source path не используется как доступный серверу
исходный файл. SDK по-прежнему самостоятельно выполняет свои copy/move и
передаёт серверу create. Неизвестный режим add_group проверяется без assert.

Сохраняется исходная семантика FileUndo: при поздней ошибке записи откатываются,
файлы удаляются из репозитория, а потреблённые в режиме create данные остаются
в undo-cache. Возврат потреблённых файлов в handoff под прежними именами
этим режимом не обещается. Успешная публикация потребляет staged-файлы;
серверный add_file с mode=copy оставляет исходный handoff-файл.

Один handoff-скрипт выполнен без изменений в оригинальном runtime, новом
SQLite и настоящем PostgreSQL: публикация файла, append, группа кадров,
append группы, результаты и содержимое файлов совпали. Отдельно проверены
поздний rollback и сохранность всех входных байтов в cache, неизменённый SDK
через настоящий HTTP XML-RPC с разными client/server путями, server-side copy,
запрет внешнего списка файлов, настройки и исходные API-сигнатуры. Проверка
реальных симлинков пройдена в одноразовом Linux-контейнере; в Windows она
пропущена из-за отсутствия соответствующего права. Существующие upload/group
регрессии и сборка Vue прошли. Все данные тестовые; Docker не пересобирался.

Остаются отдельными незавершёнными ветками ingest, pipeline command listeners,
пользовательские check-in классы, privileged ownership и специализированные
медиа/метаданные последовательностей. Полная совместимость API не заявляется.
Новых миграций этого этапа нет; для применения backend нужен перезапуск.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_handoff.HandoffParity test_handoff.HandoffPaths test_transport.Transport.test_original_client_handoff_checkin_append_and_frame_groups test_transport.Transport.test_original_client_http_upload_and_simple_checkin test_file_api.FileApiParity -v
docker compose -f deploy/docker/compose.yaml run --rm --no-deps --entrypoint python -e PYTHONPATH=/opt/stream-src:/opt/python-packages:/opt/handoff-checks/tests:/opt/handoff-checks -e STREAM_POSTGRES_HOST=postgres -e STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password -v D:/code/TACTIC_VUE/tactic_stream/tests:/opt/handoff-checks/tests:ro -v D:/code/TACTIC_VUE/tactic_stream/tools:/opt/handoff-checks/tools:ro app -B -m unittest test_schema_postgres.SchemaPostgres.test_schema_connections_instances_and_ddl_match_sqlite test_handoff.HandoffPaths -v
```

## Этап 0.77 — зависимые действия Pipeline и пользовательский check-in

Из оригинального Command перенесены `set_as_approved`, `notify_listeners` и
`handle_pipeline`. Подтверждение меняет задачи выбранного процесса на Approved;
зависимые действия выбираются по event и `scope="dependent"`. Сохраняются
options, previous command, process name и передача исходного info в input/output
обработчика. Используется существующий HandlerCmd, без нового слоя команд.

Порядок транзакций исходный: обычный Command сначала фиксирует свои изменения,
затем вызывает listeners. Check-in вызывает `checkin/move` отложенным триггером.
Ошибка зависимого действия не отменяет уже сохранённый файл или caller.
Конструирование пользовательских Python-классов требует настоящих прав admin
в БД; изменённый в памяти Security/Sudo этого разрешения не даёт.

Убраны общий запрет check-in объектов с pipeline_code и запрет аргумента
`simple_checkin(checkin_cls=...)`. Класс проверяется до обработки файлов и
должен наследовать BaseCheckin. Исходный FileCheckin.get также выбирает
пользовательский класс из action `event="checkin" scope="current"`.
Сигнатуры API, SDK и механизм подключения Handler сохранены.

Исправления проверяются отдельно от совпадения с легаси. PipelineEventCaller
больше не глотает ошибку внутри отложенной транзакции: ошибочные записи
обработчика откатываются, traceback печатает штатный Trigger. В оригинальном
runtime воспроизведён нежелательный commit Note после такой ошибки.
Search.get_by_search_key сохраняет исходный полный ключ при поиске в кеше.
Простая project-квалификация типа с фиксированной БД sthpw разрешается в его
общий системный search_type: иначе после очистки кеша Note/Task/Snapshot
могли ссылаться на другой вариант имени и исчезать из поиска связей.
Исходный FileCheckin.get на Python 3 также теряет класс между exec/import и
eval: отдельно записан исходный NameError и успешный выбор класса в форке.
Отличие свежего search_type от оригинала явно проверено; типы проектных БД
и квалификация соединения не меняются.

Общий скрипт проверяет подтверждение, независимость других задач, порядок и
данные actions, event/scope, ошибки listeners, выбор check-in класса и байты
публикации в оригинальном runtime, SQLite и реальном PostgreSQL. Неизменённый
XML-RPC SDK проверяет custom class через настоящий HTTP, отказ неподходящего
класса до потребления upload и доступность Note после отдельного запроса.
Docker не пересобирался; рабочие данные, конфиги и Handler не изменялись.

Ingest, привилегированная смена владельца, специализированные media-зависимости
и оставшиеся hierarchy/dependency/condition/progress ветки Workflow ещё не
завершены. Произвольные классы из неперенесённых модулей остаются явной ошибкой.
Этот этап не включает глобальный CoreInit/Workflow startup и не объявляет
полную совместимость API. Миграций нет; backend требует перезапуска.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_command_listeners.CommandListenersParity test_command_listeners.DeferredListenerFailureParity test_transport.Transport.test_original_client_pipeline_and_custom_checkin -v
docker compose -f deploy/docker/compose.yaml run --rm --no-deps --entrypoint python -e PYTHONPATH=/opt/stream-src:/opt/python-packages:/opt/listener-checks/tests:/opt/listener-checks -e STREAM_POSTGRES_HOST=postgres -e STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password -v D:/code/TACTIC_VUE/tactic_stream/tests:/opt/listener-checks/tests:ro -v D:/code/TACTIC_VUE/tactic_stream/tools:/opt/listener-checks/tools:ro app -B -m unittest test_schema_postgres.SchemaPostgres.test_schema_connections_instances_and_ddl_match_sqlite -v
```

## Этап 0.78 — файловый ingest и отложенная запись check-in

Перенесён `tactic.command.ingestion_cmd`: IngestionCmd, CheckinRuleCmd,
CheckinRuleSaveCmd и IngestException. Сохранены имена, сигнатуры и путь вызова
через существующий execute_cmd/XML-RPC. Правила и ingest sessions используют
исходные config/ingest_rule и config/ingest_session; дополнительной схемы нет.
Работают scan/checkin, обход файлов по rule и file_list, ignore/filter,
выделение полей sobject/snapshot из пути, extra fields/keywords, поиск по
search_key/code/id и создание объектов через штатный SearchType.

Validation/process scripts выполняются исходным PythonCmd, с path, sobject,
parent и временным snapshot в input. IngestException или ложный результат
валидации добавляет путь в paths_invalid; неожиданная ошибка сохраняет traceback
и откатывает текущую команду. Публикация использует исходный локальный SDK и
обычный simple_checkin, включая handoff и Command/FileUndo. Исходные файлы
сохраняются при copy. Доступ к серверным путям и Python пока требует настоящих
persisted-admin прав и активной транзакции; это не sandbox.

Включён исходный FileCheckin(ingest_mode='ingest'): File/Snapshot получают
set_random_code и сохраняются после подготовки именования и файлов. Без явно
заданной версии используется исходная версия 1; автоматические versionless
снимки не создаются. Это отложенная запись отдельных объектов, не пакетный SQL.

Исправлены ошибки исходного модуля: Python 2 unicode/.message, неправильный
вызов статического column_exists и lookup ID, неинициализированный parent,
None вместо списков extra fields, неработавшие rule merge/file_list,
пропуск последнего символа/лишнего суффикса в шаблоне и переопределение ignore
фильтром. Шаблон теперь полностью сопоставляется с путём; regex разрешён только
в filter вида /.../. Отчёт содержит исходные шесть групп paths/tags/data,
без чтения/записи общего /tmp/scan. Удалён hardcoded путь CheckinRuleCmd,
вложенная команда проходит Command lifecycle; внутренний живой Snapshot от
check-in не попадает в сериализуемый отчёт XML-RPC.

Проверены исходный runtime и явные отличия его ошибочных веток, copy/move
bulk ingest, сканирование без публикации, сохранённые правила/session, списки,
валидация, исключения process script после первой публикации, поздний откат
файлов/строк, SQLite и реальный PostgreSQL, неизменённый SDK через HTTP XML-RPC.
Рабочие данные, конфиги и Handler не изменялись; Docker не пересобирался.

Публикация каталогов, script scan, экспериментальный ingestX, привилегированное
владение и оставшиеся Workflow hierarchy/dependency/condition/progress ветки
ещё не завершены. Незаконченный исходный IngestCreateSObjectCmd не переносится
как работающий API. Полная совместимость не заявляется. Миграций нет;
для загрузки новых команд нужен перезапуск backend.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_ingestion.IngestionParity test_transport.Transport.test_original_client_ingest_command_and_saved_rule -v
docker compose -f deploy/docker/compose.yaml run --rm --no-deps --entrypoint python -e PYTHONPATH=/opt/stream-src:/opt/python-packages:/opt/ingest-checks/tests:/opt/ingest-checks -e STREAM_POSTGRES_HOST=postgres -e STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password -v D:/code/TACTIC_VUE/tactic_stream/tests:/opt/ingest-checks/tests:ro -v D:/code/TACTIC_VUE/tactic_stream/tools:/opt/ingest-checks/tools:ro app -B -m unittest test_schema_postgres.SchemaPostgres.test_schema_connections_instances_and_ddl_match_sqlite -v
```

## Этап 0.79 — каталоги в check-in, ingest и XML-RPC

Подключена исходная directory ветка File.create: base_type=directory,
размер дерева через Common.get_dir_info, обычный FileCheckin/Naming/Repository
и FileUndo. Работают copy/move/inplace, вложенные файлы и пустые каталоги;
изменения БД и дерева откатываются при позднем исключении. Исходный SDK
`directory_checkin` обращается к существующему simple_checkin: новый API метод
не добавлялся. get_all_paths_from_snapshot(expand_paths=True) сохраняет исходное
поведение — корень и непосредственные дочерние пути, не рекурсивный список.

Directory ingest поддерживает rule и list, scan/checkin и тот же отчёт.
Исправлен отбор уровней: исходное условие пропускало непосредственные каталоги
шаблона, выбирая следующий уровень. Совпавшее дерево публикуется целиком один
раз; дочерние каталоги отдельно не импортируются. Поддерживаются списки без
завершающего слеша и корни файловой системы через normpath.
Серверный ingest вызывает тот же FileCheckin напрямую: исходный клиентский
helper удаляет весь handoff тикета через shutil.rmtree. Прямой серверный copy
сохраняет прочие handoff файлы и использует штатный транзакционный FileUndo.
Неизменённый клиентский SDK сохраняет собственное исходное поведение очистки
handoff; его код и Handler не переписывались.

Из оригинала перенесены FormatValue и TimeCode, а также SPTDate.now/get_time_ago.
Удалены смена глобальной locale при импорте, перезаписанный дубль __add__ и
неиспользуемый demo. Исправлены locale.format, types.IntType, None frames,
DICT/iteritems и проверка boolean после преобразования в строку. Размеры
форматируются с исходными порогами и усечённой одной десятичной цифрой, без
currency locale. Числа/даты сохраняют текущую locale; денежные форматы требуют
настроенную денежную locale и явно дают ошибку в C locale. Проектные настройки
даты и fps используют действующий ProjectSetting, исключённый prod не возвращён.
Совпадение всех возможных комбинаций форматирования не заявляется.

Общий API контроль handoff/upload проверяет содержимое переданной директории:
отказ ссылкам за пределы тикета и directory symlink/junction, которые могли
привести к рекурсивному копированию. Вычисление auto context проверяет только
границу пути; обход выполняется для выбранного дерева, а не всех соседних
загрузок. Дополнительных настроек и схемы нет.

Проверены неизменённый скрипт на оригинальном ядре и явные отличия ошибок,
реальный HTTP XML-RPC с исходным SDK, directory ingest/list, rollback copy/move,
сохранность постороннего handoff, SQLite и реальный PostgreSQL. Проверки ссылок
прошли в Linux. Рабочие БД/конфиги и Handler не изменялись, Docker не пересобирался.
Миграций нет; для новых модулей требуется перезапуск backend.

Script scan, экспериментальный ingestX, привилегированная смена владельца и
оставшиеся Workflow hierarchy/dependency/condition/progress ветки ещё впереди.
Полная совместимость API и готовность поставок этим этапом не объявляется.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_directory.DirectoryParity test_transport.Transport.test_original_client_directory_checkin_and_expanded_paths test_ingestion.IngestionParity -v
docker compose -f deploy/docker/compose.yaml run --rm --no-deps --entrypoint python -e PYTHONPATH=/opt/stream-src:/opt/python-packages:/opt/directory-checks/tests:/opt/directory-checks -e STREAM_POSTGRES_HOST=postgres -e STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password -v D:/code/TACTIC_VUE/tactic_stream/tests:/opt/directory-checks/tests:ro -v D:/code/TACTIC_VUE/tactic_stream/tools:/opt/directory-checks/tools:ro app -B -m unittest test_schema_postgres.SchemaPostgres.test_schema_connections_instances_and_ddl_match_sqlite test_directory.DirectoryPaths -v
```

## Этап 0.80 — условные ветки и вложенные Workflow

В исходном `pyasm.command.workflow` включены обработчики condition, progress,
hierarchy, input и output. События, публичные методы и запуск Python callbacks
сохраняются; новый движок или отдельный Workflow процесс не создавались.
Условие возвращает bool, имя/список выходных процессов либо streams коннекторов.
Не выбранные ветки получают not_required, False возвращает revise по исходному
направлению, on_success/on_fail исполняются через исходный PythonCmd.

Вложенный pipeline передаёт data, packages и стек родителей. Завершение возвращается
к вызвавшему процессу; повторное использование ребёнка разными hierarchy узлами
не смешивает состояния. config/process_state и ключи сообщений ребёнка используют
полный путь процесса, например `start/start/work`; корневые ключи не изменились.
TaskGenerator создаёт исходные вложенные задачи по настройкам v1/v2; сохраняет
политику task_creation, повторный запуск и skip_duplicate=False с суффиксом контекста.

Исправлены подтверждённые ошибки оригинала: двойной on_complete условия, поиск
on_success/on_fail только по имени процесса без pipeline_code, потеря packages
в выбранных streams и контекста при revise, потеря data в hierarchy. Output
выбирал первый зарегистрированный родительский процесс и мог завершить его до
остальных входов. Теперь выход ждёт входы, а родитель — все конечные ветки ребёнка.
Исправлены неверная сигнатура Pipeline.get_by_code при статусе Task, разрешение
корневого pipeline для вложенных задач и поиск дубликатов по полному process.
Отсутствующий/пустой ребёнок и рекурсивная иерархия отклоняются до callbacks и записи.

Один неизменённый сценарий сравнивается с реальным оригинальным движком для
11 графов. Ошибки оригинала имеют отдельные ожидания; это не заявление полного
совпадения поведения. Проверены SQLite/PostgreSQL, завершение и повторная генерация
вложенных задач, rollback callbacks/состояний/задач и исходный SDK через HTTP XML-RPC
call_pipeline_event/get_pipeline_status. Штатный check-postgres подключает tools
read-only, поэтому не требует сборки образа ради тестовых импортов.

Dependency/related callers, custom node UI/config handlers, серверный JavaScript
и worker-wide Workflow.init(startup=True)/CoreInit остаются закрыты. Request-local
Workflow.init доступен; автоматическая инициализация всего движка во всех воркерах
этим этапом не заявляется. Изменения bootstrap-схемы не нужны; версия 0.80.0,
для загрузки обработчиков требуется перезапуск backend.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_workflow_nodes.WorkflowNodes.test_reads_match_actual_original_runtime test_workflow_nodes.WorkflowNodes.test_hierarchy_failure_rolls_back_tasks_states_and_callbacks test_workflow_nodes.WorkflowNodes.test_hierarchy_preflight_and_task_regeneration test_transport.Transport.test_original_client_workflow_pipeline_tasks_and_dependencies -v
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```


## Этап 0.81 — зависимости Workflow и инициализация ядра в воркерах

Включены WorkflowDependencyNodeHandler и уведомления ProcessListenTrigger через
исходные события и call_pipeline_event, без нового транспорта. Зависимость
запускает процессы связанных объектов, ждёт их завершения и продолжает родителя.
Поддержаны сохранённые настройки v1/v2, XML-атрибуты, связанные/global выражения,
wait=false, revise/reject, пустой набор и уже завершённые дочерние объекты.
Несколько родителей сохраняются в process_state; следующий запрос после завершения
дочерней задачи уведомляет каждого со своим data/packages и стеком вложенности.

CoreInit выполняется один раз при старте каждого воркера уже установленной БД:
StatusLog для задач/состояний, DisplayName для логинов, события Workflow и integral
триггеры Snapshot. Повторная request-регистрация не удваивает обработчики.
StatusLog использует исходный контекст commit: вложенный TaskComplete больше не
стирает переход статуса. Штатный XML-RPC SDK проверяет весь цикл разными запросами.

Исправлены исходные ошибки v1 None.startswith, несогласованные настройки XML,
зависание пустых/завершённых зависимостей и раннее уведомление до callbacks.
Пользовательский SearchType сохраняет область проекта, даже если физически лежит
в sthpw; системные типы и admin/sthpw алиасы нормализуются одинаково при чтении.
Сравнительные проверки фиксируют ошибки оригинала отдельно от совпадающих веток.

Изменения Workflow сериализуются штатной транзакцией: BEGIN IMMEDIATE на SQLite,
блокировка таблицы process_state на PostgreSQL. Это намеренный предел пропускной
способности записей Workflow; переход к блокировкам отдельных объектов нужен при
подтверждённой нагрузке. Проверены два одновременных родителя и поздний rollback
callbacks/задач/состояний/уведомлений на собственных временных данных.

state хранится как text. Для установленного PostgreSQL штатный upgrade расширяет
varchar(256) без потери содержимого; свежая установка сразу создаёт text. Батник
выполняет upgrade перед стартом. Docker update использует обычный upgrade без
пересборки образа. Рабочие данные и запущенные серверы при разработке не менялись.

Остаются неперенесёнными зависимости альтернативных графов на том же объекте,
ProcessStatusTrigger, custom node UI/config и server JavaScript. Полная API
совместимость этим этапом не заявляется. Версия 0.81.0; нужен перезапуск backend.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_workflow_dependencies.Dependencies.test_reads_match_actual_original_runtime test_workflow_dependencies.Dependencies.test_simultaneous_callers_are_both_completed test_workflow_dependencies.Dependencies.test_late_dependency_failure_rolls_back_completion_and_waiters test_transport.Transport.test_original_client_dependency_completes_after_another_request -v
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```


## Этап 0.82 — сохранение pipelines, процессы и пользовательские обработчики

Целиком перенесены исходные tactic/core/pipeline_commands.py, process_commands.py
и process_constants.py. PipelineSaveCbk и ProcessInfoCmd/NewProcessInfoCmd работают
через существующий execute_cmd, общий Command и Search/SObject. Сохранены старые
импорты tactic.ui.tools и tactic.ui.tools.pipeline_wdg — это те же классы, без
дополнительных вызовов или HTML-виджетов. Код Tactic Handler не менялся.

Сохраняются XML графа и process_code, настройки v1/v2, описания, параметры задач,
Python-скрипты и привязки config/trigger, hierarchy/subpipeline, dependency,
status и progress. Исправлены повторное экранирование XML, молчаливое игнорирование
невалидных settings, потеря существующего script_path без нового тела скрипта,
запись wait=False только при наличии scope, пропуск конфиг-триггеров admin/sthpw.
Дубли узлов и чужой process_code отклоняются. Существующий код процесса нельзя
незаметно переименовать без миграции задач/ссылок. Отсутствующий color сохраняет
прежнее значение; пустое description очищается. Опции вызывающего кода не меняются.

CustomProcessConfig читает прежние workflow widget_config. Серверные элементы
process/save/delete создают зарегистрированный BaseWorkflowNodeHandler/Command,
исполняются с правами сохранённого администратора в активной транзакции. Конструктор
вызывается один раз; его ошибки и ошибки сохранения выходят наружу и откатывают
данные. Кеш конфигов обновляется общим commit/rollback. Элементы node/info и обычные
HTML виджеты остаются исключены: интерфейс строится Vue из тех же XML данных.

ProcessStatusTrigger подключён к уведомлениям workflow|SearchType после завершения
обработчика процесса. Родительский progress ждёт всех связанных дочерних процессов;
уведомление учитывает pipeline родителя и несёт data/packages. В исходном коде
зарегистрированный listener не имел издателя события. Проверена разница полного
цикла: оригинал остаётся in_progress, native завершается после второго ребёнка.

Одинаковые скрипты проверены на реальном оригинальном runtime и native. Намеренные
исправления исходных ошибок фиксируются отдельно. Проверены SQLite/PostgreSQL,
поздний rollback XML/настроек/триггеров/скриптов/журнала, кеш и права перед созданием
класса. Исходный SDK сохраняет граф старым class path, затем новый XML-RPC запрос
исполняет сохранённый скрипт и повторно привязывает его без передачи тела кода.

Не включены JavaScript runtime, HTML node/info, старый реестр sthpw/process,
зависимости альтернативного графа на том же объекте и миграция используемых имён
процессов. Полная API/UI совместимость пока не заявляется. Версия 0.82.0;
изменения схемы БД не требуются, для загрузки обработчиков нужен перезапуск backend.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_process_commands.ProcessCommands.test_reads_match_actual_original_runtime test_process_commands.ProcessCommands.test_custom_handler_rollback_cache_and_security test_transport.Transport.test_original_client_saves_pipeline_and_executes_saved_script -v
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```


## Этап 0.83 — версии pipelines и наследование процессов

Перенесены исходные Pipeline.save_version, set_to_latest/set_to_versionless и
серверные PipelinePropertyCbk/PipelineSaveCmd из tactic/ui/tools/pipeline_wdg.py.
Публичные пути tactic.ui.tools и tactic.ui.tools.pipeline_wdg сохранены;
классы импортируются напрямую из headless core. Нового API-транспорта нет:
команды вызываются execute_cmd, методы Pipeline — из execute_python_script
или существующего серверного Python-кода. Ответ создания содержит исходный
info.search_key. PropertyCbk сохраняет исходное объединение kwargs с workflow
и no-op при целочисленном version=2.

SObject.clone снова поддерживает related_types, используя существующие
get_related_sobjects/set_parent и транзакции. Repository File/Snapshot
через общий clone по-прежнему исключены. Версия pipeline получает новый code,
parent_code и следующий version; копируются определения процессов, action
triggers, progress listeners и сохранённые project Python scripts. XML
process_code, workflow owner/trigger/script references и trigger.data
переназначаются на новые объекты. Изменение текущего скрипта не меняет скрипт
созданной версии. Привязанные subpipeline/dependency graphs, внешние классы
и произвольные ссылки в пользовательском коде остаются общими: это история
pipeline с перечисленными зависимостями, а не неизменяемая ревизия всего проекта.
Записи сериализуются существующей Workflow-блокировкой SQLite/PostgreSQL;
ошибки отсутствующих script/trigger и поздние ошибки откатывают всю команду.

Наследование процессов использует исходный get_template_pipeline с именем
VFX Processes (существующая конфигурация, автоматического создания нет).
Атрибуты наследуются по имени процесса; name/xpos/ypos/process_code целевого
процесса сохраняются. checkin_mode читается из точно выбранного template
pipeline, без wildcard, который мог выбрать чужое определение.
PipelineSaveCbk сохраняет применённые атрибуты шаблона в конечном XML.

Намеренные исправления оригинала: source save_version не завершает копирование
скриптов, использует индекс в сортировке вместо имени и сохраняет старые XML
идентификаторы; source process cache может вернуть определение до изменения.
set_to_latest содержит undefined local и читает отсутствующий pipeline_code
вместо code; set_to_versionless ищет потомков вместо исходного parent.
Template update мог рекурсивно commit ещё не вставленный pipeline. Этот commit
отложен до штатной вставки; ошибки defaults больше не печатаются с продолжением
записи, а завершают Command с rollback.

Проверено на неизменённых вызовах оригинального runtime и stock XML-RPC SDK:
создание, свойства, версии 1/2, исполнение сохранённого скрипта после изменения
текущего, latest/versionless, шаблон с чужим decoy, rollback и отказ при retired
admin. Тот же контракт выполнен на SQLite и реальной отдельной PostgreSQL БД;
две одновременные записи получают версии 3/4. Исходные hashes и 129 сигнатур
API проверяются штатным foundation check. Рабочие данные и сервер не меняются.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_pipeline_versions.PipelineVersions.test_reads_match_actual_original_runtime test_pipeline_versions.PipelineVersions.test_versions_execute_templates_and_rollback test_transport.Transport.test_original_client_saves_pipeline_and_executes_saved_script test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```

Следующий блок: оставшиеся зависимости Workflow и изоляция состояний разных
pipelines на одном SObject; затем дальнейшие контракты ядра и UI. Переименование
process identifiers остаётся запрещено до переноса всех ссылок/задач.
В исходном UI найден незавершённый JS node_rename без серверной миграции;
фиктивную совместимость с ним не заявляем. Полная API parity пока не достигнута.


## Этап 0.84 — несколько Workflow pipelines на одном SObject

Снят запрет на same-object alternate dependencies: related_pipeline_code выбирает
другой pipeline того же объекта. Это исходная ветвь WorkflowDependencyNodeHandler,
исправленная поверх общих Command/Trigger/SObject и существующего lock Workflow.
Новой таблицы, модели задач или отдельного транспорта нет.

Основной graph сохраняет имена work, group/work и прежние ключи сообщений.
Дополнительный graph использует pipeline_code::process; например
SAME_ALT1::work или SAME_ALT1::gate/work. Это намеренное исправление исходной
коллизии; разделитель :: зарезервирован и не допускается в имени узла. Это
новая адресация, а не старый контракт таких имён: оригинал хранит состояния разных
pipelines вместе и в сравнительном сценарии уходит в RecursionError между
completion/listener. Исходные тела скриптов вызова выполняются в обоих ядрах;
ошибочное поведение source зафиксировано отдельно.

get_full_process_name — общий путь для process/status/state сообщений,
callback data/packages, process_state и задач. Existing process_state.pipeline_code
заполняется кодом корневого graph, cache различает owner/name. Старые строки с
пустым pipeline_code принадлежат основному graph; при его штатной записи получают
owner. Рабочая БД автоматически не менялась; новых колонок/DDL для этапа нет.
Task.pipeline_code по-прежнему обозначает task/status pipeline, его смысл сохранён.

Зависимость читает __PIPELINE__ и status в контексте целевого graph, не своего
вызывающего graph. status самого SObject учитывается только для его основного
pipeline. Список ожидающих callers, data/packages, parent paths и завершение
терминальных joins сохраняются; actual dispatch cycles заканчиваются ошибкой и
rollback. Задачи дополнительных graphs квалифицируются до поиска дубликатов;
изменение status маршрутизируется по namespace, затем штатно по hierarchy.
Автосоздание manual/approval задач использует текущий graph и полный parent path.

XML-RPC сигнатуры прежние, stock TacticServerStub без изменений:

```python
server.call_pipeline_event(search_key, "start", "pending")  # основной graph
server.call_pipeline_event(search_key, "SAME_ALT1::work", "pending")
server.get_pipeline_status(search_key, "SAME_ALT1::work")
server.update(task_search_key, {"status": "Complete"})
```

Проверены два дополнительных graphs с одинаковыми work/done и общий основной
work, независимое последовательное завершение через свежие запросы, исходный
SDK, callbacks/data/packages, late rollback, старое состояние без owner, вложенный
дополнительный hierarchy и отказ циклической зависимости. Обычные dependency/
hierarchy/progress и генерация задач сравнены с действующим original runtime.
Один и тот же сценарий с двумя дополнительными graphs выполнен на SQLite и
реальной отдельной PostgreSQL БД. Сервер и пользовательские данные не трогались;
Docker использует текущие файлы, без пересборки образа.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_same_object_workflow.SameObject.test_reads_match_actual_original_runtime test_same_object_workflow.SameObject.test_fresh_requests_completion_and_rollback test_same_object_workflow.SameObject.test_alternate_hierarchy_routes_task_to_its_root test_transport.Transport.test_original_client_same_object_alternate_workflows test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```

Следующий блок — оставшиеся используемые команды редактора Workflow и их
зависимости: безопасное удаление custom процессов и привязок, затем дальнейшая
сверка ядра/API. Process identifiers rename, HTML renderer, server JS и оставшиеся
специализированные package/Workflow ветви пока не объявлены совместимыми.
Полная API parity по-прежнему не достигнута.


## Этап 0.85: удаление Workflow процессов и принадлежащих им триггеров

Перенесён исходный путь PipelineSaveCbk → Pipeline.update_dependencies →
update_process_table → SObject.delete. CustomProcessConfig берёт delete-handler
из исходного workflow widget config, без HTML renderer. Общая обработка удаления
config/process работает также через XML-RPC delete_sobject и прямой SObject.delete
в штатной Command/Transaction, с прежними сигнатурами API.

Исправлен source FIXME: удалённый узел искался уже в новом XML, поэтому custom
handler не вызывался. Pipeline.on_update сохраняет тип удаляемого узла в существующем
workflow.node_type до перезагрузки graph; direct delete читает тип из текущего graph.
Handler получает node_type, pipeline_code, process, process_code, search_key и
вызывается один раз до удаления определения. Ошибки конструктора/execute больше
не проглатываются; изменения handler и дальнейшей команды откатываются вместе.
Намеренное отличие от source проверено на действующем оригинальном runtime:
там handler не вызывается, остаются action/progress triggers; source также
дублирует definitions при повторном update_dependencies из-за старого cache.

Удаляются config/trigger, привязанные process=process_code, и progress-listeners
из workflow.trigger_code / workflow.progress.trigger_code только при совпадении
владельца process_code и pipeline_code в trigger.data. Внешние listeners, скрипты,
задачи и история сохраняются. Если другая definition ссылается на принадлежащий
удаляемому процессу trigger, операция отвергается и откатывается: молча удалять
общую привязку нельзя. Копии definitions/triggers/scripts сохранённой версии
pipeline независимы и остаются рабочими после удаления исходных процессов.

Проверены исходный editor path, свежий API-запрос, неизменённый TacticServerStub
через XML-RPC, ошибки handler/поздней команды, shared trigger guard, независимая
версия graph и запрет выполнения handler для деактивированного администратора.
Сохранение process properties и версионирование pipeline проверены адресно.
Один и тот же сценарий удаления выполнен на SQLite и отдельной реальной
PostgreSQL БД; результат совпал, Docker образ не пересобирался.
Рабочие БД и процессы не менялись, Handler не редактировался.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_process_delete.ProcessDelete.test_reads_match_actual_original_runtime test_process_delete.ProcessDelete.test_delete_rollback_direct_api_and_security test_transport.Transport.test_original_client_deletes_workflow_processes test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```

Прямой delete_sobject(config/process) по исходному контракту удаляет definition,
но не редактирует XML графа: для удаления узла используется PipelineSaveCbk.
Этот этап не объявляет готовыми удаление всего используемого pipeline, rename
узлов с миграцией ссылок, смену типа с миграцией всех настроек, HTML или server JS.
Далее — оставшиеся команды Workflow и сверка неперенесённых ветвей ядра/API.
Полная API parity по-прежнему не достигнута.


## Этап 0.86: смена типа Workflow процесса через общий Pipeline

Исходный PipelineSaveCbk и ProcessInfoCmd/NewProcessInfoCmd сохраняют названия,
сигнатуры и порядок применения новых node settings. Исправлена исходная неполная
смена типа: source очищал workflow только при наличии settings и сохранённого
node_type; прежние action-триггеры, progress-listeners и subpipeline_code оставались.
Теперь Pipeline.on_update сравнивает старые/новые типы XML узлов и выполняет ту же
общую очистку принадлежащих процессу привязок, что используется при удалении.
Это работает при сохранении редактора, прямом Pipeline.commit и XML-RPC update.
Структурные изменения без settings не оставляют старые исполняемые настройки.

Custom delete-handler получает прежний node_type, исполняется один раз до сброса
его настроек; ошибки handler или последующей команды откатывают XML, definitions,
триггеры и побочные записи вместе. Ссылка другого процесса на удаляемый собственный
trigger по-прежнему запрещает изменение. Чужие listeners, скрипты, задачи, заметки
и независимые сохранённые версии не удаляются. Process id/code, description
и другие общие поля не сбрасываются. Сбрасываются workflow до version
и нового node_type, а также прежний subpipeline_code; после этого исходная команда
редактора применяет новые settings/node_kwargs. Версия формата workflow сохраняется
либо используется исходная 2. Повторное сохранение одинакового типа не вызывает
cleanup; исходный alias auto/action сравнивается через Process.get_type.

Отличия от source подтверждены одним неизменённым сценарием на оригинальном
runtime: source сохраняет два устаревших триггера и старый subpipeline, не вызывает
custom cleanup и из-за старого process cache теряет актуальные descriptions.
В новом ядре такие эффекты исправлены. Проверены custom/action/progress/hierarchy
→ manual без settings, raw XML-RPC update, manual → action с новым script,
выполнение нового action неизменённым TacticServerStub, повторное сохранение,
сохранность идентичностей/задач/версии, ошибка custom handler и поздний rollback.
Затронутые сохранение properties, удаление definitions и версии pipeline проверены
адресно. Тот же сценарий выполнен на SQLite и отдельной реальной PostgreSQL БД;
результаты совпали в существующей проверке schema. Docker образ не пересобирался.
Пользовательские базы, процессы и Handler не менялись.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_process_types.ProcessTypes.test_reads_match_actual_original_runtime test_process_types.ProcessTypes.test_raw_api_type_change_settings_versions_and_rollback test_transport.Transport.test_original_client_changes_workflow_process_types test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```

Текущие экземпляры процессов и состояние выполняющихся объектов автоматически
не перезапускаются и не мигрируют на новую семантику узла. Прямые команды свойств
ProcessInfoCmd/NewProcessInfoCmd по исходному контракту не меняют тип в XML графа;
тип меняется записью Pipeline. Переданные в новом XML/настройках callbacks остаются
данными вызывающего клиента. Этап не объявляет готовыми rename узлов с миграцией
ссылок, удаление всего используемого pipeline, HTML renderer или server JS.
Далее — оставшиеся используемые команды Workflow и неперенесённые ветви ядра/API.
Полная API parity по-прежнему не достигнута.


## Этап 0.87: snapshot-пакеты Workflow и передача результатов check-in

Доведена рабочая исходная ветка WorkflowManualNodeHandler.get_output_packages:
встроенные default/snapshot и message, сохранение пользовательских пакетов,
выбор Final среди latest и исходный fallback на остальные latest при отсутствии
Final. Исправлен выбор process: используется общий get_full_process_name,
то есть work для основного graph, gate/work для hierarchy и PK_ALT::work
для дополнительного pipeline. Одноимённые процессы больше не подбирают чужие
snapshot’ы на том же SObject; отсутствие snapshot’ов возвращает пустой список.
Устаревшие is_latest=False snapshot’ы исключаются исходным фильтром.

Сам генератор и правила выбора взяты из original workflow.py. Сигнатуры,
форматы snapshot_codes, типы пакетов, дополнительные поля существующего default
и содержимое message/custom сохранены. Удалены недостижимые локальные ветви
sobject/custom с незавершёнными переменными: source всегда создаёт ровно default
и message; это не готовая система произвольных packagers. Унаследованный custom
package передаётся без переинтерпретации. Новых API, моделей и wrappers нет.

Один и тот же неизменённый Inspect-сценарий выполнен на действующем оригинальном
runtime: primary package совпадает; source в nested/alternate/empty выбирает
snapshot основного work. Исправленное отличие зафиксировано явно. Сквозной stock
TacticServerStub/XML-RPC сценарий завершает primary и hierarchy задачи отдельными
запросами, получает nested_final в последующем action и тот же пакет в persisted
state. Custom/message поля сохраняются; поздняя ошибка action откатывает задачи,
process_state, сообщения, заметки и snapshot-записи, после чего повтор операции
завершается одним callback. Затронутый сценарий двух дополнительных pipelines
и его rollback проверен адресно. Один и тот же Inspect-контракт выбора пакетов
выполнен на SQLite и отдельной реальной PostgreSQL БД; результаты совпали.
Docker использовал исходники без пересборки образа.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_workflow_packages.WorkflowPackages.test_reads_match_actual_original_runtime test_transport.Transport.test_original_client_workflow_snapshot_packages test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```

Snapshot.process должен соответствовать выбранному процессу, включая полный
hierarchy/alternate namespace. Контракт Snapshot.create/create_snapshot/check-in
не менялся: process можно передать явно; исходный default берётся из context.
Автоматическое переименование ранее записанных snapshot’ов в новые namespaces
не выполняется. Исходные notify_listeners и старая fallback-ветка ProcessListen
содержат нерабочие/недостижимые заготовки; их наличие не считается новым покрытием.
Произвольные package generators, server JS и HTML renderer не объявлены готовыми.
Пользовательские БД, процессы и Handler не менялись. Далее — оставшиеся действующие
контракты Pipeline/Workflow и общая сверка ядра/API; полной API parity ещё нет.


## 0.88 — исходное планирование и зависимости задач

Сняты ограничения с существующих TaskAutoSchedule и Task.update_dependent_tasks
в pyasm/biz/task.py. Используются алгоритмы исходного TACTIC:

- even равномерно делит интервал start_date–due_date между задачами с округлением
  границ до секунды;
- even_day делит календарный интервал и приводит границы к полудню;
- from_end_date располагает задачи назад от due_date, сохраняя их длительности;
- зависимые задачи начинаются через календарный день после предыдущей, в полдень,
  сохраняют свой elapsed interval; циклическая ссылка пропускается с предупреждением.

TaskAutoSchedule остаётся обычным исходным классом: execute только меняет значения
SObjects в памяти, сохранение делает вызывающий код. Task.add_initial_tasks применяет
планировщик и коммитит созданные задачи внутри действующего Command/Transaction.
XML-RPC add_initial_tasks, его аргументы и формат ответа не менялись. Повторный
вызов сохраняет skip_duplicate; поздняя ошибка откатывает создание/даты/логи.

Выбор режима: явный schedule_mode, затем ProjectSetting schedule/mode, затем
XML <schedule><mode>...</mode></schedule>. Пустое значение сохраняет обычные даты,
рассчитанные генератором pipeline. schedule/mode теперь виден администратору в
каталоге конфига: описание EN/RU, default пустой, restart не нужен, read-only,
поскольку редактирование конфига пока ограничено штатными восемью services/*.

Исправлены исходные дефекты: явный schedule_mode больше не перезаписывается
настройкой проекта, список посещённых задач хранится в request-local Container
вместо общего Task.tasks_updated, отмечается фактически обработанный child.
Неизвестный режим, отсутствие обязательных дат и отрицательная длительность
вызывают явную ошибку. Пустые списки в календарных помощниках не делятся на ноль;
помощники принимают строки дат через имеющийся dateutil parser.

Семь неизменённых скриптовых сценариев сравниваются с реальным оригинальным
runtime: три прямых режима, три настроенных генерации и зависимое перепланирование.
Восьмой сценарий фиксирует намеренное исправление: оригинал игнорирует явный
schedule_mode='even_day' и использует настроенный even; Stream применяет аргумент.
Проверены цикл и полный откат родителя, задач и transaction/change logs. Штатный
TacticServerStub создаёт задачи по всем трём режимам отдельными XML-RPC запросами,
проверяет отсутствие дублей и откат ошибочной генерации. Семь основных сценариев
дали одинаковые результаты на SQLite и собственной временной PostgreSQL БД.
Образы Docker не пересобирались; пользовательские БД, конфиг, процессы и Handler
не изменялись. Публичные API-сигнатуры и исходные hashes сохранены.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_task_schedule.TaskSchedule.test_reads_match_actual_original_runtime test_task_schedule.TaskSchedule.test_validation_cycle_and_rollback test_transport.Transport.test_original_client_task_scheduling test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```

Исходные календарные правила не являются полноценным рабочим календарём: holidays,
рабочие часы и выходные в этих режимах не учитываются. Изменение даты через update
само по себе не запускает cascade; кастомный скрипт вызывает update_dependent_tasks
как в исходном ядре. Депрекейтед mode='context' сохраняет отдельную исходную ветку.
Custom TaskGenerator режимы/статусные pipelines, переименование процессов,
server JS и HTML renderer ещё не объявлены перенесёнными. Полной API parity нет.


## 0.89 — пользовательские статусные pipelines задач

Снят общий запрет кастомных task_pipeline в Task._check_generation и
SObject.commit: ссылка должна вести на существующий непустой граф. Генерация,
сохранение задачи и смена её статуса проходят штатные Security/Command/Transaction/
Trigger; исходные сигнатуры TaskGenerator, Task.create, add_initial_tasks,
update и execute_cmd не менялись. Нормальный generate_mode, schedule и
projected_schedule уже поддержаны; дополнительных действующих режимов в исходном
TaskGenerator нет, неизвестные значения по-прежнему отклоняются.

Действует исходный ProcessCustomTrigger: mapping в штатное событие, direction к
текущему/входному/выходному процессу и переходы по from_attr/имени следующего узла.
Исправлены исходные дефекты: In Progress нормализуется в process|action, завершение
нескольких задач читает тот же настроенный/заданный XML task_pipeline, что и
обработчик статуса, mapping из XML учитывается и имеет приоритет над metadata.
Первая Ready-задача не завершает процесс, пока остальные не готовы; сами задачи
сохраняют пользовательское имя Ready, а процесс получает complete.

TaskStatusChangeTrigger восстанавливает сохранённые data/packages узла перед
событием новой задачи: иначе переход в action перезаписывал ранее сохранённый
input пустыми значениями. Направленные/условные custom-переходы сохраняют
parent_pipelines/parent_processes, альтернативный namespace и переданные данные.
Циклическая цепочка статусных переходов останавливается явной ошибкой; путь
хранится в request-local Container и очищается при выходе, включая исключения.
Недействующий event mapping также вызывает ошибку. Неизвестный статус без узла
сохраняет исходное callback-only поведение. Отключённый в source обратный поиск
пользовательского имени для Pending не включался: этот отдельный контракт остаётся.

Семь одинаковых скриптов выполнены на реальном легаси и новом ядре: v1, v2,
XML mapping, hierarchy, альтернативный pipeline, output direction и branch.
Намеренные отличия фиксируются отдельными ожиданиями: source In Progress не
доставляется в action; XML Ready не завершает процесс; nested состояния теряют
путь, alternate задачи не получают namespace, branch теряет data/packages.
У source промежуточный complete-запрос дополнительно создаёт пустое overall-state;
Stream не добавляет его при незавершённых задачах. Дубликаты config/process,
которые создаёт source Pipeline.create, получают одинаковый fixture workflow,
а графы повторно разбираются с окончательным code; source-файлы не изменялись.

Те же семь сценариев дали одинаковые результаты на SQLite и отдельной временной
реальной PostgreSQL БД. Штатный TacticServerStub отдельными XML-RPC запросами
меняет статусы nested-задач, ждёт обе Ready, передаёт исходные data/packages в
последующий action и завершает hierarchy. Поздняя ошибка action и статусный цикл
откатывают все задачи, process_state, messages, notes и status logs; после исправления
конфига операция проходит один раз. Native-проверка подтверждает точные ошибки
циклов/неверных mapping и откат transaction/change logs. Проверены обычная
генерация с preflight, исходные snapshot packages и публичные API-сигнатуры.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_task_status.TaskStatus.test_reads_match_actual_original_runtime test_task_status.TaskStatus.test_cycle_and_invalid_mapping_roll_back test_transport.Transport.test_original_client_custom_task_statuses test_generation.GenerationParity.test_preflight_and_mid_generation_failure_leave_no_writes test_transport.Transport.test_original_client_workflow_snapshot_packages test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```

Новые API методы, wrappers, модели и настройки не добавлялись. Docker использовал
существующий образ и исходники без пересборки. Пользовательские БД/конфиг/процессы
и Handler не изменялись. HTML/info/node handlers, server JavaScript, генерация по
expression/cross-pipeline connections и процессные rename/reference migrations
не объявлены готовыми; полной API parity ещё нет.


## 0.90 — parent_key и коллекции в ядре/API

Существующие insert/update принимают parent_key для перенесённых schema relationships,
включая code/id. insert(collection_key=...) вызывает исходный SObject.add_to_collection.
В search.py перенесены get_collection_type/get_collections/add_to_collection и
SearchType.get_collection_type; сохраняются *_in_* таблицы, parent_code/search_code,
повторное добавление без дубля и исходное событие collection|SearchType.
При неизвестной связи parent_key возвращает ошибку, вместо молчаливой потери связи.
Коллекция и участник должны быть сохранены, иметь code и принадлежать одному типу,
логическому проекту и ресурсу. False-маркер, другой тип/проект и циклы не принимаются.
Проверка и вставка членства выполняются под блокировкой записи vendor в текущем Command.

get_child_codes_cte сохраняет сигнатуру исходного метода. Общий recursive UNION
на SQLite/PostgreSQL использует реальные имена таблиц и экранированные коды,
обходит все достижимые коды один раз; PostgreSQL ARRAY и ограничение depth<10 убраны.
GlobalSearchTrigger сохраняет исходное добавление/распространение keyword-данных.
Исправлены пустой relative_dir/name, одновременное rename+user_keywords и отсутствующий
collection map потомка. Удаление связи пересчитывает предков по оставшимся рёбрам:
альтернативный путь сохраняет keywords, исчезнувший предок больше не остаётся у потомков.

На реальном исходном runtime подтверждены и отдельно зафиксированы два отличия:
qualified parent_key оставляет source code/id связи пустыми; collection CTE падает
на SQLite из-за ARRAY. Остальное рабочее чтение/членство сравнивается без правок
исходных файлов. Один неизменённый сценарий добавления, вложенных keywords, rename
и удаления нескольких путей сравнивается на SQLite и реальном PostgreSQL.
Исходный SDK через временный XML-RPC сервер проверяет parent_key, collection_key,
ошибку с откатом нового объекта и SearchTypeCreatorCmd(sobject_collection=True).
У старой SDK insert-обёртки нет collection_key: используется исходный server.insert
с исходными позиционными аргументами, SDK не изменяется.

sobject_collection добавляет только исходную _is_collection колонку. Таблица *_in_*,
её SearchType, schema connections и keyword-колонки поставляются шаблоном/плагином;
creator оригинала также не создаёт их этой галочкой. Неполная схема даёт ошибку.
Полный CollectionAddCmd/RemoveCmd/DeleteCmd, удаление коллекции со всеми связями,
UI collections, API info и creator template/parent/preview остаются отдельными этапами.
Новые API методы и настройки не добавлены; полной API parity пока нет.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_collections.Collections.test_reads_match_actual_original_runtime test_collections.Collections.test_keywords_cycles_and_rollback test_transport.Transport.test_original_client_parent_and_collections test_schema_api.SchemaApiParity.test_search_type_creation_columns_records_and_failure_guards test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```

Данные проверки одноразовые. Docker использует существующий образ и монтирует
исходники; рабочие БД/конфиг/серверы и Handler не изменяются.


## 0.91 — команды управления коллекциями

Перенесён целиком backend-модуль tactic/core/collection_commands.py: CollectionAddCmd,
CollectionRemoveCmd, CollectionDeleteCmd. Сохранены исходные аргументы, info.message,
описания операций, таблицы членства и записи через Command/SObject с триггерами.
Действуют импорты tactic.ui.panel и tactic.ui.panel.collection_wdg, включая execute_cmd
с исходными class paths. HTML виджеты и renderer CollectionAddAction не переносились.

Удаление коллекции сначала удаляет её исходящие, затем входящие связи членства,
затем саму запись. Участники и вложенные коллекции сохраняются, их keywords
пересчитывает общий GlobalSearchTrigger. Поздняя ошибка откатывает объекты,
связи, keyword-данные, индексные записи и журналы в текущей транзакции.
Обычное удаление произвольного SObject не подменяется этой командой; каскад
всех иных schema-зависимостей не заявляется частью CollectionDeleteCmd.

В CollectionAddCmd список назначений проверяется до первой вставки. Исходный
runtime подтверждает баг: при [OTHER, SUB] и переносе родительской ROOT исходник
создаёт OTHER→ROOT, затем сообщает circular на SUB. Native возвращает те же
circular/parent_collection_names, без частичной записи и ложного Insert OK.
Обычные Insert OK/No insert и описания совпадают с оригиналом. Отдельно сравнён
старый source кэш: после фактического DELETE lookup возвращает старый SObject;
native lookup возвращает None, а физические удаления совпадают.

Команды проверяют marker, непустые ключи/коды и существование участников, одинаковые
SearchType/проект/ресурс. Выполнение требует текущий проект коллекции, чтобы исходные
keyword-триггеры не читали чужой проект. Проверки и изменения идут под блокировкой
таблицы членства; после ожидания повторно читаются сохранённые цели/участники.
Общий SObject.add_to_collection также отвергает ранее загруженную удалённую коллекцию.
Повторяющиеся ключи не создают дубликаты. Ограничения исходного get_parent_codes
сохранены: 1000 уровней, 10000 посещённых кодов и пакетное чтение по 200 кодов.

Неизменённый скрипт выполнил add/repeat/remove/delete и circular batch на настоящем
source runtime. Те же native сценарии с keyword-триггерами выполнены на SQLite и
отдельной временной PostgreSQL БД. Исходный TacticServerStub через XML-RPC проверил
все три import path, сообщения циклов, удаление входящих/исходящих связей,
сохранность участников и отказ удалить обычный объект. Два параллельно отправленных
SQLite XML-RPC добавления дали одну связь и ответы Insert OK/No insert;
этот HTTP concurrency сценарий на PostgreSQL отдельно не заявляется проверенным.
Native проверки подтверждают late failure rollback и ошибочные/исчезнувшие цели.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_collections.CollectionCommands.test_reads_match_actual_original_runtime test_collections.CollectionCommands.test_commands_keep_keyword_descendants_and_roll_back test_collections.Collections.test_reads_match_actual_original_runtime test_collections.Collections.test_keywords_cycles_and_rollback test_transport.Transport.test_original_client_parent_and_collections test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```

Новых API методов, таблиц, настроек или wrappers нет. Образ Docker не пересобирался;
рабочие базы/конфиги/процессы и Handler не изменялись. UI коллекций, создание неполной
collection schema, оставшиеся creator/schema команды и полная API parity не объявлены.


## 0.92 — backend редактора схемы

Из исходного schema_wdg.py извлечены активные SchemaSaveCmd и SchemaConnectorCbk.
Работают прежние class paths tactic.ui.tools и tactic.ui.tools.schema_wdg через
execute_cmd. SchemaSaveCmd регистрирует отсутствующие SearchTypes; для уже
существующих типов остаётся исходный no-op. В легаси команда падает с NameError
из-за отсутствующего импорта SearchTypeCreatorCmd; в Stream импорт исправлен.

Schema.add_search_type(parent_type) и edit_connection добавляют/удаляют исходную
hierarchy/code связь в XML. Сохранены сигнатуры, defaults и первый подходящий
connect при совпадающих from/to. При commit=False изменяется только XML в памяти;
для записи нужен последующий edit с commit=True и SObject.commit. Исходное ошибочное
изменение поля schema при add_search_type(parent, commit=False) не воспроизводится.
SearchTypeCreatorCmd снова принимает sobject_parent. Как в исходнике, это запись
связи в схему, а не неявное создание FK-колонки.

Колонки создаёт отдельный SchemaConnectorCbk через имеющийся локальный API.
Он также обновляет definition/edit/edit_definition и parent hidden-row config,
сохраняя оригинальные декларативные XML, SelectWdg/DatabaseAction и class strings.
Это данные для общего config resolver, не восстановленная генерация HTML.
Schema XML сохраняется отдельно: callback сам по себе не сохраняет граф редактора.
Кодовая связь использует исходный varchar(256); новая связь по id — integer.
values_expr берёт выбранную целевую колонку вместо безусловного code. Суффикс
_code/_id снимается только с конца имени, не из середины. Колонки и типы проверяются
до записи; DDL требует текущую транзакцию и действующего администратора.

Общий WidgetDbConfig._init создаёт view node для пустого config после присвоения view.
Оригинал создаёт лишний пустой edit_definition, Stream сохраняет один узел.
Schema edits очищают кэш отношений, DDL очищает активные schema caches; disabled
отношения не кэшируются как постоянные. Сравнение с реальным original runtime
фиксирует stale disabled после создания колонки, старый кэш после remove, лишний
XML view, текстовый id и NameError отдельно от совпадающих частей результата.

Неизменённый XML-RPC TacticServerStub проверяет регистрацию двух типов, оба class
paths коннектора, повтор без дубликатов конфигов, insert(parent_key) и отказ
невалидного имени колонки без записи второй колонки. Адресные native проверки:
late failure откатывает DDL, registry, naming/schema/config; запрещённый пользователь
не создаёт таблицы; disabled cache обновляется после создания колонки. Одни и те же
native code/id/cache/save/creator скрипты сравниваются на SQLite и временном PostgreSQL.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_schema_edit test_schema_api test_widget_config test_transport.Transport.test_original_client_schema_editor_commands test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```

Для создания SearchType в другом проекте сначала выбрать этот проект: чужой database
override теперь явно отклоняется, вместо записи naming/schema в текущий проект.
Не переносились SchemaManyToManyCbk (в исходнике незавершённый stub), canvas/HTML,
creator copy_from_template, preview и автоматические исходные renderer defaults.
Полная совместимость schema editor/UI и всех API не объявляется. Рабочие данные,
серверы, Handler и Docker image не изменялись.


## 0.93 — шаблоны таблиц и создание pipeline

SearchTypeCreatorCmd снова принимает copy_from_template и process при sobject_pipeline.
Сохранены исходные copy_template_table/create_pipeline и вызов через execute_cmd;
новых XML-RPC методов нет. Копируется структура без записей: defaults, NOT NULL,
CHECK, UNIQUE и индексы, включая expression/partial indexes. Новая таблица получает
независимую последовательность id. Registry, schema, naming и DDL используют
существующие Command/Transaction и журнал TableUndo.

SQL находится в DatabaseImpl: SQLite сам переименовывает структуру во временной
in-memory БД, PostgreSQL использует LIKE INCLUDING ALL и отдельную serial sequence.
Строковые defaults и имена колонок не заменяются поиском имени таблицы в тексте.
Foreign constraints, SQL triggers, generated/special tables и копирование между
разными ресурсами отклоняются с откатом; ограничения PostgreSQL schema replay
сохраняются. Копирование widget configs закомментировано и в исходной команде.

Pipeline получает исходный код project/table, процессы workflow version=2 и связи
между соседними процессами; XML экранирует пользовательские имена. Исправлены
конфликтующие source фильтры и удаление определений при первом commit до чтения XML.
Общий update_process_table использует sort_order с 1. Сохранённая версия копирует
свои определения вместо создания дубликатов. set_pipeline(cache=False) действительно
читает переданный XML. Store.tables/columns с именем базы выбирают её vendor.

Неизменённый скрипт выполнен на реальном исходном ядре и Stream. Исходник подтвердил
TypeError в TableUndo.log, потерю определений при первом commit и потерю графа с
амперсандом в имени. Исправления проверяются отдельными ожиданиями. Native проверки:
constraints/defaults/id, сохранность источника, late failure rollback, SQLite
undo/redo и выполнение сохранённого action script. Исходный SDK выполнил команды
через HTTP XML-RPC. Одинаковые native сценарии выполнены на SQLite и временном PostgreSQL.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_schema_template test_pipeline_versions test_pipeline test_transport.Transport.test_original_client_search_type_template_and_pipeline test_schema_api test_schema_edit test_workflow_api test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```

Preview, автоматические creator views/sidebar и полный контракт UI ещё не готовы.
Следующий блок — исходные декларативные настройки создаваемого SearchType и их
подключение к динамическому Vue. Рабочие данные, конфиги, серверы и Handler
не изменялись; Docker не пересобирался.


## 0.94 — исходные creator configs и динамическая таблица Vue

Из SearchTypeCreatorCmd перенесены create_config и add_sidebar_views: обычный
проектный тип получает definition/table/edit, ссылки SideBarWdg definition и
project_view. Сохранены исходные class paths/options, список служебных колонок,
pipeline/task_status_edit/notes и keywords в edit. Шаблон копирует таблицу без
изобретённого копирования configs; системный тип не получает проектные views.
Исправлен source пропуск custom columns при неполном/отсутствующем format.
Общий WidgetDbConfig.append сохраняет один узел view при повторном добавлении,
с действующими Command, Security, cache invalidation и rollback.

Новый JSON POST /admin/interface принимает ticket, project, search_type, view
(по умолчанию table). Для администратора возвращает schema_version=1, columns,
table/navigation: view, layout, attributes, configured, elements с
name/title/attributes/display/action. Разрешение XML использует WidgetConfigView
и WidgetDbConfig с исходным priority merge и packaged defaults. Возвращаются
декларации handlers/options; fallback Python renderer не импортируется.
Пустой view отличается от отсутствующего; неизвестный именованный view отклоняется.
Действуют общие body/content-type/origin ограничения и ticket authorization;
ответы no-store. XML-RPC методы и get_widget/get_column_widgets не менялись.

Vue открывает проектные LinkWdg/ViewPanelWdg ссылки, читает порядок/заголовки полей
и открывает детали объекта. После Refresh изменения XML видны без сборки Vue.
Переключение «Configured view / Database fields» и выбранный view сохраняются
между обновлениями страницы. Пустой view не подменяется всеми колонками таблицы.
Неподдержанные widgets/layouts показаны как недоступные; произвольные class paths
и script/action options не исполняются. Обычный пользователь сохраняет прежний
браузер полей через XML-RPC/JSON query и get_column_info в рамках выданных прав,
без доступа к новому админскому описанию конфигов.

Неизменённый скрипт сравнил фактические source XML с native. Отдельные ожидания
подтверждают исправления повторных sidebar views и пропавших custom columns.
SQLite/PostgreSQL выполнили одинаковые creator сценарии. Исходный XML-RPC SDK
изменил порядок, заголовок, неизвестный class path и пустой view, которые прочитал
новый HTTP endpoint. Проверены ошибки авторизации/view/project и late rollback.
Настоящий headless Chromium проверил ссылки, колонки, детали, изменение XML,
Refresh/reload, режим полей, пустой view, безопасный текст и non-admin view access.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_schema_template test_schema_edit test_widget_config test_transport.Transport.test_creator_views_refresh_from_original_xmlrpc test_transport.Transport.test_original_client_search_type_template_and_pipeline test_transport.Transport.test_admin_json_reads_share_auth_and_original_api test_ui test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
npm --prefix frontend run build
.\.venv\Scripts\python.exe -B -X utf8 tools\interface_browser.py
```

Все данные/серверы браузерной и PostgreSQL проверок временные. Docker использовал
существующий образ с исходниками; рабочие данные, конфиги, процессы и Handler
не изменялись. UI editor, полноценные widgets/formatting/actions, формы,
вложенный sidebar, preview и полная parity остаются незавершёнными. Следующий
связанный блок — исходные EditWdg метаданные и команды полей/форм, затем их Vue UI.

### 0.95 — серверная подготовка форм и штатное сохранение

Перенесены активные методы исходных EditWdg, EditCmd/EditMultipleCmd и восемь
действий: DatabaseAction, DefaultValueDatabaseAction, MultiDatabaseAction,
NonEmptyAction, RegexAction, NullAction, UniqueValueAction, XmlAction.
Базовые TextWdg/TextAreaWdg/CheckboxWdg/SelectWdg разрешают значения/defaults,
select options/queries/TSQL через ядро. Сохраняются исходные пути импорта,
выбор actions из XML, args/data/form values, SObject commit, Trigger, info,
Command/Transaction и общий откат, в том числе пакетных правок.
execute_cmd принимает исходный values dictionary и восстанавливает прежний
form context в finally. Восстановлены SearchType.get_tactic_type(s), доступ к
database impl и Common.get_next_code; frontend не содержит второй движок defaults.

Отдельный админский `POST /admin/form` описан в UI_ARCHITECTURE.md. Он возвращает
поля/значения/options/actions/choices, не подменяя HTML get_widget или XML-RPC.
Проверена неизменённая query_EditWdg из существующего Handler через исходный
XML-RPC SDK на базовой именованной форме. Handler checkout не изменён.

Исправлены регистр SQLite типов, потеря defaults 0/false, двойное XML escaping,
extra_labels split, scalar/mismatched select expressions, чтение args data в
Regex/Unique и проверка уникальности собственного объекта. Пробное чтение
метаданных/expressions не использует Sudo. Неизвестные input/action зависимости
дают явную ошибку; expression errors не превращаются в фальшивые select labels.

Поддержка пока ограничена базовыми inputs/actions и администратором. Календарь,
upload/task/process/pipeline inputs, полная widget inheritance/HTML/__dict__
совместимость, пользовательские JS validations/renderer callbacks, FilterData/
input persistence, custom HTML layouts и весь GUI Handler ещё не готовы.
`explicit_display` headless EditWdg только подготавливает metadata; get_display
отклоняет HTML. Vue-формы, config editor и preview подключаются следующим блоком.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_edit_form test_transport.Transport.test_edit_form_original_client_and_handler_script test_transport.Transport.test_creator_views_refresh_from_original_xmlrpc test_widget_config test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
.\.venv\Scripts\python.exe -B -X utf8 deploy\docker\manage.py check-postgres --suite schema
```

Исходный runtime сравнивает тот же form/action script на временной SQLite базе;
native SQLite/PostgreSQL сравнивают одинаковые metadata/edit/rollback сценарии.
Адресные проверки покрывают defaults, query/TSQL selects, insert/edit/bulk и
пакетный rollback; HTTP/SDK проверяют обновлённые значения, ошибки ticket/key/
project/default. Docker использовал имеющийся образ и bind mount исходников.
Рабочие БД, конфиги, процессы и legacy/local_data не изменялись; UI в этом этапе
не пересобирался. Новый endpoint потребует обычного перезапуска запускальника.

### 0.96 — динамические Vue формы создания и редактирования

Администратор открывает Create record из таблицы или Edit record из подробностей
объекта. RecordForm получает исходный edit/insert config через /admin/form при
каждом открытии. TextWdg/TextAreaWdg/CheckboxWdg/SelectWdg отображают серверные
значения, defaults и choices; заголовки/порядок меняются из XML без сборки Vue.
Неизвестные inputs, сложные значения и неподдержанные options, включая старые
JS callbacks, явно блокируют форму. Это базовые формы, не весь EditWdg renderer.

Save вызывает существующий execute_cmd/tactic.ui.panel.EditCmd с исходными
view, element_names, input_prefix и values. Значения сохраняются исходными,
соседние поля доступны действиям; readonly inputs не включаются в element_names.
Нет отдельного SQL или frontend defaults/naming движка. После UserException
видно сообщение действия, черновик сохраняется; XML-RPC ответы не менялись.
Dirty close/Escape требует подтверждения, обновление страницы предупреждает
о черновике; данные формы не пишутся в browser storage. Во время сохранения
повтор и закрытие заблокированы. Потеря ответа/ошибка 5xx блокирует повтор Save
до закрытия формы и проверки списка: Insert не повторяется автоматически.

Исправлены два исходных дефекта: DatabaseAction больше не теряет числовой 0,
а CheckboxWdg принимает XML keyword options/default/read_only. Оригинальное
преобразование zero возвращало None — проверено точным исходным телом метода,
это намеренное отличие. Предыдущие позиционные аргументы Checkbox сохранены.
Vue использует общий переводчик en/ru, native controls и MD3/material5 tokens.
Vite proxy добавлен для /admin/form; собранные web assets обновлены.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_ui test_edit_form.EditForm.test_defaults_actions_and_bulk_rollback test_transport.Transport.test_edit_form_original_client_and_handler_script test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
Set-Location frontend
npm run build
Set-Location ..
.\.venv\Scripts\python.exe -B -X utf8 tools\interface_browser.py
```

Chromium проверяет фактический built UI на собственном HTTP процессе и временной
SQLite базе: create/edit/defaults, zero/boolean/select, readonly, серверную
валидацию и отсутствие записи при ошибке, dirty keep/discard, потерю ответа после
реального commit без повторного Insert, обновление XML, неизвестные JS options,
escaping и отсутствие write кнопок у reader. Рабочие данные/процессы и Handler
не менялись. PostgreSQL сценарий 0.95 повторно ради этого UI не запускался.
Полный набор ядра не запускался. Для нового UI достаточно обновить страницу;
для изменённых backend методов нужен обычный перезапуск запускальника.

Следующий блок — исходные календарные/дата inputs и их серверные зависимости,
затем upload/task/process/pipeline. Config editor, вложенные layouts/sidebar,
preview, история/ревизии и AI authoring остаются отдельной работой; поддержки
произвольных Python/JS widgets или всей GUI Handler этим этапом не заявляем.

### 0.97 — календарные поля и серверное время

Из исходника перенесены ARGS_KEYS/get_value современного
tactic.ui.widget.CalendarInputWdg, BaseInputWdg.get_timezone_value и три
SPTDate helper. EditWdg выбирает исходный календарный handler для дат;
*_time остаётся TextWdg. XML options календаря сохраняются вместо потери
в исходной ветке выбора default widget.

Vue показывает date/datetime-local через штатные browser controls, используя
серверный descriptor. Часовой пояс берётся из серверной настройки/пользовательской
PrefSetting; браузерный часовой пояс не подменяет её. Исходные values остаются
отдельными от отображаемой даты. Неизменённые timestamps отправляются с явным
UTC/offset, поэтому сохранение соседнего поля не сдвигает время. Для изменённого
времени исходный DatabaseAction выполняет преобразование в UTC. SQL DATE
не преобразуется по часовому поясу; *_day timestamp использует полдень GMT,
чтобы выбранный день не сдвигался. Сохранение идёт через прежний EditCmd.

Исправлены source undefined date для *_day, повторный parsing локализованных
названий месяцев и молчаливая замена ошибочной даты текущим временем. Неверный
часовой пояс теперь отклоняется. SObject.commit сохраняет микросекунды datetime;
исходная потеря точности подтверждена отдельным сравнением с настоящим runtime.
Browser picker редактирует миллисекунды; полная точность неизменённого timestamp
сохраняется. JSON-RPC корректно сериализует date/datetime в command info как ISO:
прежде запись проходила, но успешный ответ ломался. XML-RPC формат не менялся.

Проверки на своих временных данных:

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_calendar_form test_transport.Transport.test_edit_form_original_client_and_handler_script test_ui test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved test_statements.StatementParity.test_reads_match_actual_original_runtime -v
.\.venv\Scripts\python.exe -B -X utf8 tools\interface_browser.py
```

9 адресных проверок прошли. Сравнение SQL отдельно учитывает исправление 0.83:
ошибка get_defaults прерывает запись, тогда как исходник печатает её и продолжает
INSERT. Запущен реальный Chromium: даты/defaults/очистка, timezone, сохранение
точности без сдвига, исходные формы и rollback, потерянный ответ без повторной
вставки, XML refresh и запрет записи reader. Исходный XML-RPC SDK выполняет
неизменённое тело Handler query_EditWdg с CalendarInputWdg. Это проверка процедуры,
не всей GUI Handler. frontend собран, версия 0.97.0.

Один и тот же календарный сценарий чтения/редактирования/отката прошёл также
на отдельной PostgreSQL-базе и SQLite:

```powershell
$docker=(Get-Command docker.exe -ErrorAction SilentlyContinue).Source
if (-not $docker) { $docker='C:\Program Files\Docker\Docker\resources\bin\docker.exe' }
& $docker compose --project-name tactic-stream-linux -f deploy/docker/compose.yaml run --rm --no-deps -T --user root -v 'D:\code\TACTIC_VUE\tactic_stream\tests:/opt/tests:ro' -e 'PYTHONPATH=/opt/stream-src:/opt/python-packages:/opt/tests' -e 'STREAM_POSTGRES_HOST=postgres' -e 'STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password' app python -B -m unittest test_schema_postgres.SchemaPostgres.test_calendar_forms_match_sqlite -v
```

Образ не пересобирался, рабочие данные/конфиг/процессы и Handler не менялись.
Полный suite не запускался. Для backend нужен обычный перезапуск запускальника.
Vue поддерживает browser mode; inline календарь, старый pyasm CalendarInputWdg,
Time/Interval/CalendarMonth, произвольные JS callbacks/форматы остаются явно
неподдержанными. Следующий блок — upload/task/process/pipeline inputs и actions;
config editor, nested layouts, preview/revisions и AI authoring остаются в плане.

### 0.98 — workflow inputs и исходный SubContextAction

Перенесены восемь связанных input классов: PipelineInputWdg, ProcessInputWdg,
ReviewProcessInputWdg, SubContextInputWdg, SearchTypeInputWdg,
SearchTypeWithPipelineInputWdg, ProcessGroupSelectWdg и TaskStatusSelectWdg.
Имена и исходные module paths сохранены; короткие имена разрешаются также через
существующий WidgetConfig factory. Бизнес-подготовка из исходных get_display
выделена в get_input без HTML. EditWdg.explicit_display готовит её в том же
request/project/security контексте; /admin/form отдаёт raw values и готовые choices.

Сохранены фильтры pipeline по suffix SearchType, текущему проекту и общим
pipeline, code/name labels, рекурсивные manual/approval/node процессы,
output contexts и текущий subcontext. SearchType selectors используют исходную
Schema без hierarchy, добавляют task и проверяют физический pipeline_code.
Назначение использует исходные process login_group/TSQL и label_attr; статусы
задачи сохраняют текущий статус и проверяют process_select/process view access.
Ни нового ORM, ни frontend движка workflow нет. Vue использует уже существующие
select/text controls; generated empty labels локализуются en/ru, пользовательские
labels/коды не переводятся. XML перечитывается при открытии формы, без rebuild.

Модуль tactic.core.context_actions скопирован целиком. SubContextAction меняет
или очищает хвост context через исходный postprocess/SObject.commit. Ошибка
при пустом base context откатывает и предыдущую запись EditCmd. Исправлен source
ProcessInputWdg: проверялось имя input вместо имени процесса, из-за чего следующий
процесс пропадал из списка при совпадении. Реальный source runtime подтверждает
этот дефект; для него задано отдельное ожидание.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_workflow_form test_calendar_form test_ui test_edit_form.EditForm.test_defaults_actions_and_bulk_rollback test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
Set-Location frontend
npm run build
Set-Location ..
.\.venv\Scripts\python.exe -B -X utf8 tools\interface_browser.py
```

12 адресных проверок прошли. Original runtime сравнивает metadata и действия;
при проверке choices перехватывается только HTML serialization Select/Text,
исходные get_display бизнес-ветки выполняются. Это не тест HTML parity.
Неизменённый XML-RPC SDK проверяет execute_python_script/execute_cmd, исходное
тело Handler query_EditWdg — task-форму с процессом/context, непустым назначением
и статусом. Проверено сохранение subcontext в отдельном свежем RPC запросе.
Отдельная controlled-access проверка исключает запрещённый статус, оставляя
текущий и разрешённый. Все проверки работают на собственных TEMP fixtures.

Настоящий Chromium проверил pipeline/process/context/status/group choices,
сохранение SubContextAction и его rollback, смену общего en/ru binding без потери
выбранного исполнителя, а также прежние primitive/calendar/unknown-response и
reader сценарии. При открытом modal язык меняется программно через native
preference binding; это не проверка клика по внешнему меню за modal.
Окончательный frontend build — 0.98.0.

PostgreSQL-проверка 0.97 расширена тем же workflow сценарием и descriptor:

```powershell
$docker=(Get-Command docker.exe -ErrorAction SilentlyContinue).Source
if (-not $docker) { $docker='C:\Program Files\Docker\Docker\resources\bin\docker.exe' }
& $docker compose --project-name tactic-stream-linux -f deploy/docker/compose.yaml run --rm --no-deps -T --user root -v 'D:\code\TACTIC_VUE\tactic_stream\tests:/opt/tests:ro' -e 'PYTHONPATH=/opt/stream-src:/opt/python-packages:/opt/tests' -e 'STREAM_POSTGRES_HOST=postgres' -e 'STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password' app python -B -m unittest test_schema_postgres.SchemaPostgres.test_calendar_forms_match_sqlite -v
```

Одинаковые чтение/edit/clear/rollback результаты прошли на SQLite и отдельной
PostgreSQL-базе; контейнер использовал существующий image и bind-mounted source.
Рабочие БД/конфиг/процессы, legacy и Handler не менялись; полный suite не запускался.
Нужен обычный перезапуск backend запускальника и refresh браузера.

Границы: это headless form preparation, не полный исходный __dict__/HTML runtime.
Inline cell switching, mapping нескольких task pipelines и старые JS behaviors
не перенесены. Ветки Handler, напрямую вызывающие get_display для PipelineInput
или пустого назначения, ещё не готовы; проверенная task-процедура их не покрывает.
Missing parent/pipeline отклоняется явно вместо пустого unusable source markup.
Process/group choices строятся по сохранённому parent/process при открытии;
реактивное разрешение по несохранённому draft отдельно не реализовано. Это не
готовность всех стандартных task forms, upload actions или полной GUI Handler.
Следующий блок — upload/parent/task inputs и их actions; config editor,
nested layouts, revisions/preview и AI authoring продолжаются отдельно.


### 0.99 — parent/upload inputs и исходные form actions

Перенесены TaskSObjectInputWdg, HiddenWdg, SimpleUploadWdg и пять actions:
UploadAction, DateAction, TimeAction, TaskDateAction, InitialTaskCreateAction.
Исходные имена и пути импорта сохранены. TaskDateAction оставляет отключённым
postprocess зависимых задач, как в оригинале; InitialTaskCreateAction вызывает
уже перенесённый Task.add_initial_tasks, а не отдельную генерацию задач.

TaskSObjectInputWdg возвращает серверный parent key для insert и код родителя
для edit. Vue показывает существующего родителя без редактирования, сохраняет
insert key через исходный DatabaseAction с parent_key=true. XML key остаётся
сырым, без HTML escaping. Отсутствующий/чужой родитель insert отклоняется;
lookup popup для потерянного родителя не подменяется фиктивным контролом.
Project label без parent_key сохраняется как исходная метадата; это не обещание
автоматической связи пустого ключа с проектом.

SimpleUploadWdg получает context из исходных options/get_icon_context. Vue
отправляет один выбранный файл через существующий UploadServer и затем исходные
name|path, name|ticket, name|context, name|column через execute_cmd/EditCmd.
UploadAction создаёт icons и FileCheckin в общем Command/Transaction. Новый
транспорт и второй механизм записи не добавлены. XML конфиги формы по прежнему
меняют интерфейс без rebuild. Forms/file operations остаются admin-only.
Один HTTP запрос ограничен существующим лимитом 64 MiB вместе с multipart;
chunk UI пока не поддержан. Одинаковые имена файлов в разных полях отклоняются.

Восстановлены два контракта ядра: set_sobject_value не фильтрует schema edge по
неиспользуемому исходным методом аргументу type; uploaded принимает исходный
create repository flow. Исправлены submitted revision checkbox/prefix и
обновление автоматически полученного file naming после set_revision. Явные
правила naming не переписываются. Чужой ticket и выход через symlink за upload
root запрещены; уборка файлов проходит через FileUndo. При позднем сбое строки,
snapshot/file rows и flags откатываются; consumed file сохраняется в исходном
undo cache, а не теряется. Повтор Save не выполняется автоматически.

Проверки этапа:

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_upload_form test_workflow_form test_checkin.CheckinParity test_search_links.SearchLinksParity test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
npm.cmd run build --prefix frontend
.\.venv\Scripts\python.exe -B -X utf8 tools/interface_browser.py
```

Сравнительный script выполняется настоящими исходным и новым ядрами на
временных данных: hidden parent, task insert/link, TimeAction/DateAction/
TaskDateAction, initial tasks, две версии upload и revision. Исходный дефект
checkbox и HTML escaping проверены отдельными ожиданиями. Неизменённый stock
SDK выполняет HTTP upload и XML-RPC EditCmd; извлечённое без правок тело
Handler query_EditWdg получает upload metadata. Chromium проверяет task parent,
выбор файла и check-in через Vue, а также прежние form/rollback/i18n сценарии.
Это проверка процедуры Handler, не всей GUI.

Реальный PostgreSQL проверяется существующим образом без rebuild:

```powershell
$docker='C:\Program Files\Docker\Docker\resources\bin\docker.exe'
& $docker compose --project-name tactic-stream-linux -f deploy/docker/compose.yaml run --rm --no-deps -T --user root -v 'D:\code\TACTIC_VUE\tactic_stream\tests:/opt/tests:ro' -e 'PYTHONPATH=/opt/stream-src:/opt/python-packages:/opt/tests' -e 'STREAM_POSTGRES_HOST=postgres' -e 'STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password' app python -B -m unittest test_schema_postgres.SchemaPostgres.test_calendar_forms_match_sqlite -v
```

Этот отдельный временный PostgreSQL database создаётся и удаляется самой
проверкой. Сравниваются calendar/workflow и новые parent/date/initial-task/
upload/revision результаты с SQLite. Рабочие базы, Handler и legacy не меняются.
Итог: 19 адресных тестов прошли за 34.415 s; отдельная PostgreSQL проверка —
за 4.182 s. Финальные frontend build и Chromium сценарий прошли.
Полный unittest discover и реальные пользовательские плагины на этапе не запускались.

Границы: MultiUpload/MultiZipUpload, rich UploadWdg, immediate client actions,
старые HTML/JS lookup/upload widgets и progress runtime остаются вне этого
блока. TimeAction доступен серверным скриптам с исходными hour/minute полями;
форма Vue с таким action пока явно блокируется до переноса соответствующего
input. HTML-dependent special cases Handler, переключение workflow choices
по draft и полный widget __dict__ ещё не завершены. Следующий блок — оставшиеся
составные inputs/actions и формы, затем config authoring/nested layouts/revisions.
Frontend version 0.99.0; для работающего backend нужен штатный перезапуск launcher
и refresh браузера. Самостоятельно рабочие процессы не перезапускались.

## 0.100 — multi-upload и составные поля

Перенесены исходный MultiUploadAction, старый **pyasm.widget.UploadWdg** и
MultiSelectWdg. Это номер этапа/версии, а не 100% готовности. Современный
tactic.ui.widget.UploadWdg — отдельный класс, он ещё не перенесён.

MultiUploadAction сохраняет specified/arbitrary файловые поля, типы файлов,
custom icon, context/subcontext, комментарий, ревизию, FileCheckin и событие
email через Trigger.call. Оригинальные FieldStorage inputs работают. Для
XML-RPC/Vue добавлен handoff уже загруженных через прежний UploadServer файлов:
`edit|primary|path`, `edit|primary|ticket`; для arbitrary —
`edit|attachments0|path`, `edit|attachments1|path` и соответствующие tickets.
Context/description/revision остаются под именем самого action:
`edit|attachments|context`, `edit|attachments|subcontext`,
`edit|attachments|description`, `edit|attachments|is_revision`.
У specified names/types задаются в action options; names/required — в display.

FileUpload использует уже staged файл без повторного копирования payload.
Single/multiple handoff разделяют проверку собственного ticket, basename,
существования файла и выхода через symlink. Перед обработкой пакета проверяются
повторные имена файлов. Запись и уборка проходят через Command/FileUndo;
при позднем сбое строки откатываются, consumed files остаются в undo cache.

Исправлены исходные ошибки: проверка иконки по имени поля вместо file type,
падение на пустом optional field, assert для разной длины names/types,
неэкранированный regex arbitrary field names и игнорирование submitted revision.
Дефект custom icon отдельно подтверждён настоящим исходным runtime: оригинал
ошибочно отвергает PNG thumbnail, наш action сохраняет main/icon_main/web/icon.

Vue получает независимое описание file slots и исходного context control;
выбор нескольких файлов, subcontext/comment/revision и множественный выбор
сохраняются штатными EditCmd/MultiUploadAction/MultiDatabaseAction.
MultiSelect использует исходное `||value||value||` разрешение; raw values
возвращаются отдельно от выбранных options. Неизменённая пустая upload-группа
не запускает action при редактировании других полей. Требования file slots
проверяются формой при insert или выборе файлов в группе.
Исправлена очистка definition/draft при закрытии составной формы.

Проверки только на временных данных, штатные сервисы не перезапускались:

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_upload_form test_checkin.CheckinParity test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
npm.cmd run build --prefix frontend
.\.venv\Scripts\python.exe -B -X utf8 tools/interface_browser.py
```

11 адресных тестов прошли за 15.026 s; настоящий исходный runtime, неизменённый SDK с HTTP upload
и XML-RPC execute_cmd, отдельный Chromium сценарий прошли. Реальный PostgreSQL
проверен предыдущей Docker командой test_calendar_forms_match_sqlite без rebuild;
создание/удаление собственной временной БД и сравнение multi-revision с SQLite
прошли за 4.505 s. Полный discover, реальная GUI Handler и плагины не проверялись.
Handler, legacy, рабочие базы/конфиги не менялись. Новых XML-RPC методов нет.

Следующие блоки: modern rich UploadWdg, MultiZipUploadAction с безопасной
распаковкой и исходными naming dependencies, time-only inputs/actions;
затем authoring XML, nested layouts, revisions/preview. Старый Java applet,
HTML/JS callbacks, immediate client actions и полный widget __dict__ не входят
в готовность этого этапа. Для применения backend изменений нужен штатный
перезапуск launcher, затем refresh браузера.

## 0.101 — ZIP-upload и поля времени

Из оригинала перенесены MultiZipUploadAction, DateDatabaseAction и
TimeDatabaseAction; TimeInputWdg адаптирован как headless input. Прежние
импорты, названия action/options, FieldStorage, EditCmd и FileCheckin сохранены.
Vue использует прежний UploadServer и additive `name|path`/`name|ticket`
handoff. ZIP распределяется между SObject по исходному контракту naming:
доверенный установленный Python-класс с методом `get_sobject_by_filename(name)`.
В XML action option `naming` указывается полный путь класса. Убраны eval и
исключённые prod resolvers; короткие имена и выражения не исполняются.
Объекты другого проекта отвергаются. Forms/file operations остаются admin-only;
custom resolver дополнительно проходит прежний gate исполнения скриптов.

Common.unzip_file сохраняет сигнатуру `(file_path, dir=None)`, но пишет через
FileUndo только внутри Command. Все entries проверяются до распаковки:
traversal, drive/backslash/NUL, reserved Windows names, symlinks/special entries,
дубликаты и file/directory collisions запрещены; существующие файлы не затираются.
Фиксированные границы — 10000 entries и 512 MiB суммарного распакованного размера;
это пока не параметры tactic-conf. HTTP multipart по-прежнему ограничен 64 MiB.
Каждый архив получает отдельную временную папку; после check-in она убирается
через журнал. Пустой архив и неизвестные naming filenames дают явную ошибку.

Исправлены подтверждённые дефекты исходника: cleanup пытается удалить уже
перемещённые check-in файлы, свежие экземпляры одного SObject разбиваются на
разные snapshots, вложенные пути распаковываются без создания parents.
Группировка теперь по search key. Subcontext и submitted revision учитываются,
как в остальной upload-группе; новые snapshot versions/revisions создаёт ядро.
При позднем сбое откатывается весь пакет, включая два объекта; staged ZIP
восстанавливается с исходными байтами. Потеря ответа не запускает повтор Save.

Native `<input type="time">` показывает HH:mm. TimeDatabaseAction сохраняет
дату timestamp и оставшуюся точность; DateDatabaseAction меняет дату заданных
через `column=a|b` полей, сохраняя время. SQL `time` теперь остаётся временем
без придуманной текущей даты; Search/SObject fast/raw paths это также учитывают.
Неизменённое поле сохраняет исходные секунды/микросекунды. Для прежнего TimeAction
Vue отправляет исходные `name|hour`/`name|minute`; display использует обратное
преобразование timezone предпочтений, поэтому повторное открытие не сдвигает часы.

Проверки на временных данных, без правок Handler/legacy и рабочих сервисов:

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_compound_form test_upload_form test_calendar_form test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
npm.cmd run build --prefix frontend
.\.venv\Scripts\python.exe -B -X utf8 tools/interface_browser.py
```

Исходное ядро реально исполняет тот же сравнительный script. Его ошибки
ZIP cleanup/grouping и SQL time, а также потеря timestamp precision имеют
отдельные ожидания. Для старого TimeDatabaseAction проба добавляет только
fixture alias `basestring = str` и явно сообщает о нём; исходные файлы не меняются.
Неизменённый stock SDK выполняет HTTP ZIP upload и XML-RPC EditCmd.
Chromium проверяет ZIP на два объекта, оба time actions, timezone round-trip
и сохранение неизменённой точности вместе с прежними form сценариями.
Реальный PostgreSQL проверяется Docker командой этапа 0.99 без rebuild:
`test_calendar_forms_match_sqlite` сравнивает clock/date/ZIP handoff с SQLite
в собственных создаваемых/удаляемых базах. Batch revision и поздний rollback
отдельно проверены на SQLite. Новых XML-RPC методов и зависимостей нет.

Итог финального прогона: 13 адресных тестов прошли за 23.803 s; отдельная
PostgreSQL проверка — за 6.163 s. Frontend build и Chromium сценарий прошли.
Это проверки контрактов, не performance benchmark. Полный discover не запускался.

Следующий блок — modern rich UploadWdg; затем authoring XML, nested layouts,
revisions/preview. Time interval/drag calendar, HTML/JS widgets, immediate actions,
полная GUI Handler и реальные пользовательские плагины здесь не проверены.
0.101 — версия этапа, не процент совместимости. Применение: штатный перезапуск
launcher для backend, затем refresh браузера; рабочие процессы не перезапускались.

## 0.102 — современный UploadWdg

Восстановлен **tactic.ui.widget.UploadWdg**, отличный от старого
pyasm.widget.UploadWdg. Из оригинала взяты constructor/ARGS_KEYS и business
ветки get_info_wdg: приоритет context_expr → context → setting, SelectWdg
выражения/настройки, recursive pipeline process names и корректное различение
`pipeline=true`/`pipeline=false`. Без этих опций остаётся текстовый context.
Отсутствующий pipeline даёт явную ошибку. SObject.get_icon_context перенесён
из исходного ядра: implicit SimpleUpload context снова работает на обычном SObject.

Vue использует уже существующую file-group с одним файлом, context/subcontext,
comment и revision. Передаются прежние имена `edit|attachment|path`, `|ticket`,
`|column`, `|context`, `|subcontext`, `|description`, `|is_revision` в UploadAction.
Пустая upload-группа пропускается при изменении других полей. XML меняет controls
без rebuild; новая бизнес-модель или транспорт не добавлены. Как прежде,
администратор сохраняет через EditCmd/Command/FileCheckin/FileUndo.

Исправлен подтверждённый source bug: rich widget показывал subcontext, но
UploadAction его игнорировал. Теперь context/subcontext действительно используется;
пустой base context отвергается до файлового IO, предыдущая запись объекта
откатывается, staged файл остаётся. Source omission и прежний checkbox revision
bug проверены отдельными ожиданиями, а не объявлены полным совпадением.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_upload_form test_compound_form test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
npm.cmd run build --prefix frontend
.\.venv\Scripts\python.exe -B -X utf8 tools/interface_browser.py
```

11 адресных тестов прошли за 28.033 s. В оригинальном runtime реально выполняется
get_info_wdg; перехватывается только созданный SelectWdg перед HTML serialization.
Сравниваются шесть context вариантов, edit, revision и subcontext. Неизменённый
stock SDK проходит HTTP upload и XML-RPC EditCmd для rich, single/multi/ZIP форм.
Chromium прошёл rich context/subcontext/comment и revision, вместе с прежними
form сценариями. PostgreSQL command из 0.99, test_calendar_forms_match_sqlite,
без Docker rebuild сравнила rich subcontext/edit и прежние contracts с SQLite
в собственной временной БД: 1 test, 7.192 s. Rich revision здесь отдельно проверена
на SQLite/Chromium, не объявляется отдельным PostgreSQL revision сценарием.
Первая baseline попытка упёрлась в доступ к sandbox TEMP; повтор вне sandbox
прошёл (1 test, 1.234 s). Рабочие сервисы/данные, Handler и legacy не менялись.

HTML/JS progress, immediate client actions, applets, get_display_old и полная
widget dictionary/Handler GUI compatibility не входят в этот блок. Новых
XML-RPC сигнатур и зависимостей нет; полный discover/реальные плагины не запускались.
Следующий блок — authoring исходных XML-конфигов, nested layouts и revisions/
preview. Для применения backend изменений нужен штатный перезапуск launcher.

## 0.103 — редактор исходных XML-конфигов

В админке появился **Edit interface XML**. Можно выбрать table/edit/insert/
definition/edit_definition или сохранённый именованный view, затем конкретную
DB source запись с её priority либо новое переопределение. По умолчанию выбирается
ведущая запись; прежние правила разрешения приоритетов не изменены. Исходный XML,
разрешённые WidgetConfigView метаданные и слои наследования показаны отдельно.
Комментарии, CDATA, неизвестные nodes/options и соседние views сохраняются
точной исходной строкой. Editor не пересобирает XML из проекции и не исполняет
произвольные classes/scripts при чтении или проверке.

Native admin-only `POST /admin/widget-configuration/read|check|save` принимает
ticket/project/search_type/view; check/save дополнительно source_id (null для
создания), xml и revision. Check использует исходный WidgetDbConfig.validate
и возвращает valid/revision/unified diff. Save повторяет проверку под блокировкой
БД, затем сохраняет через SObject.commit внутри штатного Command/Transaction.
Прежние XML-RPC методы/сигнатуры и пути записи не меняются. Source record
проверяется на принадлежность выбранному проекту/type/view. XML ограничен
512 KiB; DTD/entities отвергаются существующим Xml parser.

Revision включает raw DB sources, разрешённые слои и исходный sobject_log
marker. Поэтому native/XML-RPC записи, включая A→B→A, меняют revision. SQLite
BEGIN IMMEDIATE и PostgreSQL table lock защищают check/write от других процессов.
Stale save/create получает 409; новый override повторно не дублируется. Параллельная
правка остаётся в БД, черновик — в редакторе. Журнал, триггеры и cache invalidation
обрабатывает ядро. Table-wide lock и revision scope намеренно консервативны:
изменение другого config этого ресурса тоже может потребовать перечитать view.

UI требует Check XML перед Save, показывает diff, защищает dirty draft при
закрытии, блокирует повтор после неизвестного результата сохранения и обновляет
прежний динамический renderer без rebuild. Выбор другого source/view при dirty
draft недоступен. Английский fallback и русский словарь обновлены. HTTP routes
используют прежние admin_body/auth/CSRF/request_context; Vite proxy обновлён.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_widget_authoring test_widget_config test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
npm.cmd run build --prefix frontend
.\.venv\Scripts\python.exe -B -X utf8 tools/interface_browser.py
$docker='C:\Program Files\Docker\Docker\resources\bin\docker.exe'
& $docker compose --project-name tactic-stream-linux -f deploy/docker/compose.yaml run --rm --no-deps -T --user root -v 'D:\code\TACTIC_VUE\tactic_stream\tests:/opt/tests:ro' -e 'PYTHONPATH=/opt/stream-src:/opt/python-packages:/opt/tests' -e 'STREAM_POSTGRES_HOST=postgres' -e 'STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password' app python -B -m unittest test_schema_postgres.SchemaPostgres.test_widget_authoring_matches_sqlite -v
```

7 адресных tests прошли за 9.839 s; actual original WidgetConfig comparisons
сохранены. Новый authoring path отдельно проверяет raw XML/comments/CDATA,
неизвестный handler без исполнения, invalid XML/DTD, stale create/ABA, reader 403
и конкуренцию двух **отдельных spawn processes**. Тот же native сценарий на
SQLite/PostgreSQL прошёл за 3.329 s, с собственной создаваемой/удаляемой БД,
без Docker rebuild. Chromium прошёл validation/diff/save, изменение заголовка
таблицы без rebuild, HTTP 409 с сохранением draft и переключение table/edit.
Frontend build прошёл. Baseline cache invalidation — 1 test, 0.802 s.
Рабочие базы/сервисы, legacy и Handler не менялись; полный discover/реальные
плагины/Handler GUI не запускались. Архив/поставка этим этапом не создавались.

Check подтверждает исходную XML validation, не полный renderer preview и не
поведение скриптов. История ревизий в UI, полный AI apply/idempotency, защита
файловых sources при внешнем редактировании и распределённая атомарность остаются
незавершёнными. Файловые configs здесь только читаются; сохраняются DB overrides.
Следующий блок — nested layouts и preview тем же renderer, затем история/AI API.
Для применения нужен штатный перезапуск launcher и refresh браузера.


## 0.104 — предпросмотр XML и вложенные интерфейсы

В редакторе появился **Preview interface**: draft разрешается штатным
WidgetDbConfig.merge_configs и WidgetConfigView, затем показывает текущие
записи тем же ConfiguredView.vue, который использует рабочая таблица. Preview
не пишет конфиги, не запускает display handlers, actions или скрипты. Его
payload совпадает с check/save; ответ содержит valid/revision/diff/interface.
Маршрут — POST /admin/widget-configuration/preview, с прежними admin, ticket,
project и origin проверками. Изменение XML сбрасывает preview; устаревшая
revision даёт 409. JSON descriptor добавлен отдельно от исходного XML-RPC:
get_widget/get_column_widgets не заменены JSON-ответами.

Draft представляет отсоединённые WidgetDbConfig записи: выбранный source
заменяется, остальные priority сохраняются; новый source получает штатный
NULL priority. Request-local overlay привязан к фактическому DbResource,
SearchType и view. Исходный resolver сам собирает definition/ALL/file/generated
слои. Overlay и исходный cache восстанавливаются в finally, включая ошибки;
исходные строки/БД/journal не меняются. Preview не является snapshot-транзакцией
всех зависимостей: окончательный save заново проверяет revision под DB lock.

Исправлен найденный баг resolver: merge_configs добавляет унаследованный display
в объединённый Xml, но исходный get_by_search_type перечитывал config-строку
через get_xml_value и терял объединение. Теперь все шесть DB view/definition
веток используют get_xml объединённого WidgetDbConfig. Общий путь исправлен
для runtime, форм и preview. Неизменённый probe на двух исходных WidgetDbConfig
в реальном legacy runtime показывает merged_handler=pyasm.widget.TextWdg и
пустой raw_handler; native resolver отдельно проверен на сохранение display.
Это намеренное исправление дефекта источника, а не заявление полного совпадения
его ошибочного результата. Исходные DB XML строки сохранены.

Native renderer понимает layout tactic.ui.container.TabWdg. Его элементы
задают вкладки; ViewPanelWdg с search_type/view и table/default layout разрешает
дочерние представления. Вложенный TabWdg принимает config_xml или ищет исходную
category=TabWdg/view запись, учитывает selected. Для inline configs одинаковые
имена tab не считаются циклом. Дерево описано на сервере, независимо от Vue;
классы виджетов не импортируются ради исполнения. Неизвестные handlers/actions/
options отображаются явно как недоступные. Циклы, чужой project, отсутствующее
именованное view и превышение 8 уровней/64 resolved nodes отклоняются. Вкладки
используют tablist/tab/tabpanel и клавиатуру Left/Right/Home/End.

Границы этапа: это декларативная композиция и read-only дочерние таблицы по
50 записей, а не полный HTML/JS TabWdg/ViewPanelWdg. Сохранение персонального
состояния, создание/удаление вкладок, TSQL/state options, дополнительные фильтры,
сортировка/пагинация/редактирование дочерних таблиц, произвольные display scripts
и предпросмотр EditWdg ещё не поддержаны. Root database browser сохраняет свои
прежние paging/sort/inspect и формы. Preview показывает текущую страницу root;
дочерние данные читаются обычным query в рамках текущего ticket/project.

Проверки:

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_widget_preview test_widget_authoring test_widget_config test_configs.ConfigParity -v
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe -B -X utf8 tools/interface_browser.py
& $docker compose --project-name tactic-stream-linux -f deploy/docker/compose.yaml run --rm --no-deps -T --user root -v 'D:\code\TACTIC_VUE\tactic_stream\tests:/opt/tests:ro' -e 'PYTHONPATH=/opt/stream-src:/opt/python-packages:/opt/tests' -e 'STREAM_POSTGRES_HOST=postgres' -e 'STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password' app python -B -m unittest test_schema_postgres.SchemaPostgres.test_widget_authoring_matches_sqlite -v
```

10 адресных проверок ядра/конфигов/authoring прошли; отдельный расширенный
preview probe проверяет inline nesting и предел глубины. SQLite/PostgreSQL
сравнивают дерево, выбор priority, наследование display, состав полей и отсутствие
draft-записей; физические dtype/size/nullability остаются vendor metadata.
Существующий PostgreSQL authoring probe также проверяет конкурентную запись
двух отдельных процессов. Chromium проверяет read-only preview без записи,
неизвестный widget, nested tabs, keyboard, английский/русский, сохранение того же
layout без rebuild и прежние формы/upload. Docker image не пересобирался,
ТХ и рабочие данные/процессы не изменялись. Для работающего Windows launcher
новый backend загружается при следующем перезапуске.


Дополнительные исправления в 0.104: исходный get_options при обработке inline
<config> оборачивал все потомки, из-за чего третья вложенная вкладка теряла
элементы. Обрабатывается только внешняя пара тегов. Неизменённый probe в legacy
возвращает [] для внутреннего element, исправленное ядро — ['code']; тест
проверяет это намеренное отличие отдельно от остальных равных метаданных.
Metadata-only чтение подавляет lookup/import handler.has_config и имеет отдельные
cache keys, чтобы чтение native descriptor не изменяло дальнейшее SDK поведение.
Адресная проверка подтверждает отсутствие custom module lookup в metadata,
правильную работу штатного get_display_options после него и повторное безопасное
чтение descriptor. Расширенный probe: 2 inline configs с одинаковым именем tab
работают, 11 уровней отклоняются. Финальные source/preview/signature проверки
прошли (3 tests / 4.549 s), PostgreSQL authoring + preview — 1 / 5.012 s.

Финальная metadata cache проверка: 1 test / 5.524 s. Chromium финальной сборки 0.104 прошёл весь сценарий preview/nested tabs/keyboard/language и прежние формы; JS index-RLD9O48h.js, CSS index-B_hynJ-1.css. Удалён только собственный промежуточный JS этапа, предыдущие stage assets сохранены.


## 0.105 — независимый поиск в дочерних ViewPanel

Дочерние таблицы получили собственные filter, sort, limit/offset, Refresh,
размер страницы и Previous/Next. Каждый ConfiguredView хранит эти параметры
локально; KeepAlive сохраняет состояние уже открытых вкладок до смены контекста
или пересоздания родительского интерфейса. Неактивные вкладки не читают данные
при первом открытии layout. Исходный query получает обычные filters/order_bys/
limit/offset, а следующий ряд используется для hasNext без отдельного COUNT.
Изменение фильтра применяется кнопкой Find; Refresh и страницы используют
последний применённый фильтр. Сортировка сбрасывает offset, размер страницы —
также. Старый ответ не заменяет данные после изменения ticket/project/descriptor.
Смена языка сохраняет фильтр и страницу. Записи и XML при поиске не меняются.

Серверный descriptor поддерживает исходные ViewPanelWdg options search_limit,
order_by, do_initial_search, show_refresh, show_search_limit. Они читаются
штатным WidgetConfigView, исходный XML сохраняется. Native interface.panel
содержит числовой search_limit, список order_by и boolean flags. false/hidden
для do_initial_search отменяют начальное чтение; Find запускает обычный поиск.
false для show_refresh скрывает Refresh, false для show_search_limit — page-size
и pager. Native default page size остаётся 50. Заданный search_limit допускает
1..500; ограничение относится к native UI, а не к исходному XML-RPC query.
order_by поддерживает физические поля и asc/desc, включая несколько полей через
запятую. При пользовательской сортировке исходный order_by добавляется после
выбранного поля; штатный Search удаляет повтор того же sort column. SQL joins,
expressions и произвольные legacy options не объявляются поддержанными.
Некорректные известные параметры дают явную ошибку, неизвестные options
по-прежнему оставляют widget недоступным.

Рабочий интерфейс и XML preview используют один компонент и один query.
Дочерние записи остаются read-only: фильтрация/сортировка/страницы доступны,
создание/редактирование и вызовы действий — следующий этап. Root database
browser сохраняет свой existing paging/sort/inspect. SearchType/SObject и
исходные XML-RPC методы/форматы/права не менялись. Advanced SearchWdg, keyword/
TSQL filters, search_limit_mode, пользовательские сохранённые search settings,
число всех строк и snapshot-пагинация не реализованы этим этапом.

Проверки выполнены на собственной временной БД/HTTP сервере:

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_widget_preview test_widget_config.WidgetConfigParity.test_reads_match_actual_original_runtime -v
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe -B -X utf8 tools/interface_browser.py
& $docker compose --project-name tactic-stream-linux -f deploy/docker/compose.yaml run --rm --no-deps -T --user root -v 'D:\code\TACTIC_VUE\tactic_stream\tests:/opt/tests:ro' -e 'PYTHONPATH=/opt/stream-src:/opt/python-packages:/opt/tests' -e 'STREAM_POSTGRES_HOST=postgres' -e 'STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password' app python -B -m unittest test_schema_postgres.SchemaPostgres.test_widget_authoring_matches_sqlite -v
```

Перед изменением исходный Chromium сценарий 0.104 прошёл. 2 адресных проверки
прошли за 5.129 s: неизменённый XML option probe выполнен на реальном legacy
runtime, native preview проверяет flags/bounds/order validation и отсутствие
записи. Query probe на пяти заметках проверяет contains, два поля сортировки,
limit+1 и offset. Тот же probe прошёл на SQLite и настоящем временном PostgreSQL
(1 test / 5.316 s), вместе с прежним authoring/CAS/concurrent writers. Vendor
physical column metadata не нормализованы в продукте, сравниваются имена полей
и предметные результаты. Chromium проверяет 2+1 rows, конец страниц, смену
размера, asc/desc, last-applied filter, независимость/возврат вкладок, manual
initial search и скрытые controls, вместе с прежними preview/forms/upload.
ТХ, рабочие данные и процессы не изменялись; Docker image не пересобирался.
Для новых XML options работающий backend надо перезапустить через launcher.

Финальная build 0.105: index-CG_jQiPm.js / index-CLGdahQl.css. Упрощение computed sort direction сохранило тот же byte-identical bundle, проверенный Chromium. Source hashes/public signatures: 1 test / 0.015 s прошёл. Удалён только собственный промежуточный JS этого этапа; assets предыдущих этапов сохранены.

### 0.106 — рабочий редактор серверного конфига и единые слеши

Файловые пути Config, Environment, get_base_dirs и параметров запуска используют
`/` на Windows и Linux. UNC сохраняется как `//server/share`; клиентские каталоги
не разрешаются относительно серверной ОС. Нормализация применяется к известным
путевым настройкам и значениям alias maps, после разбора JSON. Исходный XML,
скрипты, пароли и прочие строки не переписываются при чтении.

В админке редактируются 38 поддержанных параметров: сеть, порты, сервисы и
воркеры, временный каталог, клиентские каталоги, URL репозитория, срок тикетов,
безопасность, расписание, checksum и padding. Разделы выбираются в навигации;
черновики сохраняются между разделами и при возврате из браузера данных.
Сохранение записывает только изменённые поля через исходный Config.save_config:
валидация до записи, исходная ревизия, межпроцессная блокировка, атомарная
публикация и предыдущий XML. Конфликт правок возвращает 409, секреты не читаются
в UI; удаление api_password — отдельная кнопка. Неизвестные поля не редактируются.

Новые запросы читают обновлённые настройки. Для сети, процессов, временного
каталога и repository URL показывается необходимость перезапуска launcher;
сохранение само сервер не перезапускает. Явные ports определяют число воркеров
и первый порт; TACTIC_PORTS отключает редактирование перекрытых полей.
Hostname из XML действительно попадает в monitor settings, CLI overrides
сохраняют приоритет. URL репозитория проверяется тем же кодом, что при запуске:
запрещены перекрытие маршрутов приложения/другого репозитория и неизвестные aliases.

Смена СУБД, серверного asset root, aliases и plugin root требует отдельной
миграции и остаётся read-only. authenticate_class, log_type и sudo elevation
не объявляются переключаемыми функциями. UI ориентируется на разделы,
черновики и явное Save/Reset существующего Handler; Handler не изменялся.

Воспроизводимые адресные проверки на Windows / Python 3.14:

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_transport.Transport.test_configuration_is_admin_only_read_only_and_masks_secrets test_transport.Transport.test_configuration_edits_validate_preserve_xml_and_refuse_stale_writes test_transport.Transport.test_configuration_supported_settings_paths_and_startup test_transport.Transport.test_repository_aliases_do_not_shadow_application_routes test_monitor.Configuration.test_standalone_xml_formats_precedence_and_validation -v
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_environment.DataDirectories test_configuration_write.ConfigurationWrite test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -v
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_monitor.Runtime.test_real_workers_api_recovery_and_graceful_stop -v
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_transport.Transport.test_vue_admin_in_real_chromium -v
```

Пять HTTP/startup проверок прошли; четыре Environment/межпроцессная запись/
source signatures — 0.272 s. Реальные два временных воркера, XML-RPC и их
восстановление/остановка монитором — 1 test / 3.313 s. Chromium — 1 test /
6.124 s: переходы/черновики, горячие настройки, restart notice, путь X:/work,
write-only секрет, EN/RU и узкий экран. Исправлены два тестовых допущения:
server handoff fixture теперь внутри временного каталога; monitor fixture
явно задаёт loopback в своём XML вместо сетевого адреса из шаблона.
Browser ожидание проверяет завершение Save, а не disabled во время Saving.

Общее mobile/touch требование относится ко всему проекту: обычный тап,
максимум долгое нажатие для контекстных действий, без обязательной мыши,
правой кнопки, hover или drag. На 320–360 px общая навигация сворачивается,
конфиг становится одноколоночным; controls и checkbox labels имеют touch
зоны от 44 px. Настоящий hasTouch Chromium context проверяет tap навигации,
выбор раздела/типа, сброс черновика; на 320/360 px нет overflow страницы.
Проверяется текущий UI; это не обещание готовности ещё не перенесённых редакторов.

Финальная сборка: index-C0yQNkHO.js / index-B4Wfq8wJ.css. Финальные четыре
адресные проверки HTTP-конфига, Chromium mobile/touch и API signatures прошли
за 6.491 s на этой сборке. Удалены только собственные промежуточные assets 0.106.
XML-RPC сигнатуры сохранены; представление слешей изменено по явному требованию.
PostgreSQL/Docker/реальный Handler на этом этапе повторно не запускались:
изменения касаются файлового конфига и транспорта, без SQL/vendor изменений.
Рабочие данные, XML-конфиги и процессы не изменены; commit/архив не создавались.
Следующий этап переноса: базовые виджеты операций перед углублением в ячейки и таблицу.

### 0.107 — оболочка приложения и базовые операции с объектом

Проект выбирается в верхней панели; аккаунт и выход собраны в меню пользователя.
На компьютере навигация остаётся слева, на узком экране открывается модальным
меню с обычным тапом, закрытием по Escape/фону и возвратом фокуса. Общая форма
на телефоне занимает экран; размер touch controls — от 44 px. Темы и EN/RU
используют прежние токены и словарь.

ПКМ по строке и явная кнопка `⋮` открывают один ObjectOperations: просмотр,
редактирование и создание объекта. Add/edit используют существующие формы
EditWdg и команды EditCmd, включая XML-настройки полей, валидацию, права,
транзакции и триггеры. Удаление, массовые операции и дочерние формы этим этапом
не реализованы; preview и дочерние таблицы сохраняют read-only режим.
Кастомные операции из XML — следующий блок перед виджетами ячеек.

Проверки на временных данных, без изменения Handler и рабочего сервера:

```powershell
$env:PYTHONPATH='src;tests'
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_transport.Transport.test_vue_admin_in_real_chromium -v
.\.venv\Scripts\python.exe -B -X utf8 tools/interface_browser.py
```

Сборка прошла; admin Chromium — 1 test / 8.437 s. Проверены desktop/touch,
320/360 px без overflow страницы, модальная навигация, переключение ширины,
темы, языки и восстановление сессии. Interface browser прошёл: ПКМ → edit →
save с проверкой результата через API, `⋮` → create, а также прежние XML,
preview, nested tabs, формы и uploads. Полный набор ядра не запускался:
SQL и XML-RPC контракты не изменены. Финальные assets:
index-4-FRnGGK.js / index-DY2K5jLO.css.

### 0.108 — retire/reactivate и удаление с зависимостями

Общее меню операций получило скрытие, возврат и удаление с подтверждением.
Show retired использует исходный query(show_retired=True), а retire/reactivate —
прежние XML-RPC методы. Меню учитывает XML-атрибуты insert/edit/retire/delete
текущего представления; явно false скрывает соответствующие действия даже
у администратора. Это правило современного renderer, не изменение XML-RPC ACL.
Retire доступен только при существующем retire column.

Удаление показывает группы зависимостей из исходных SearchType/Schema/SObject,
включая скрытые записи. Note/task/snapshot выбраны по умолчанию по примеру ТХ;
другие группы выбирает пользователь. Запись выполняет исходный DeleteCmd,
с Command/Transaction/FileUndo. Пустой выбор сохраняет связанные группы;
снимки удаляются с принадлежащими им файлами, собственные каталоги объекта
обрабатываются прежней командой. Прямое удаление File в этом меню не предлагается.
Количество зависимостей — предварительный просмотр; при подтверждении команда
работает с текущими записями выбранных групп. Произвольные схемы с ещё не
перенесёнными отношениями не объявляются поддержанными.

Исправлен лишний запрет DeleteCmd для пользовательских SearchTypes: он теперь
использует ту же границу системных/проектных write domains, что SObject.delete.
Неизвестные системные типы остаются запрещены. Native read/apply deletion
admin-only; requires_key исходной команды и execute_cmd API не ослаблялись.
После потери ответа/серверного сбоя UI блокирует повтор в этом окне и предлагает
проверить результат обновлением. Закрытие во время записи заблокировано.

Проверки: сборка прошла; native deletion — 1 test / 1.824 s (авторизация,
контекст, валидация выбора, rollback после удаления зависимостей, пустой выбор,
XML-флаги). Interface browser прошёл retire/cancel/reactivate, выбранное
удаление и сохранение прежних forms/XML/upload сценариев; настоящий touch
context проверил меню и отмену удаления на 360 px, non-admin apply — 403.
Финальные admin Chromium и исходные API signatures — 2 tests / 6.994 s.
Адресная команда:
`.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_transport.Transport.test_native_deletion_security_selection_and_xml_operations -v`.
Assets: index-TsgcL77-.js / index-Ccavlzpl.css. Рабочие данные/сервер, Handler
и Docker не изменялись; PostgreSQL на этом этапе повторно не запускался.
Следующий блок — дублирование и операции выбора нескольких объектов;
дочерние формы и произвольные custom XML actions ещё не подключены.

### 0.109 — создание копии и операции с выбранными объектами

Duplicate record открывает исходный EditWdg с XML-view insert и значениями
источника, без записи до Save. Новый объект создаёт прежний EditCmd: новый
код и служебные даты, обычная валидация/триггеры. Копируются редактируемые поля
формы, без дочерних объектов и repository files; это явно написано в форме.
ID/code/timestamp/last_update исключаются и при привязке поля через column.
Источник остаётся настоящим SObject при подготовке inputs: календарь сохраняет
его timezone и исходную точность. clone_sobject и query_EditWdg не изменялись.

Чекбоксы выбирают строки или текущую страницу; панель выбранных объектов
предлагает retire/reactivate/delete. Выбор сбрасывается при новом query и
не переносится незаметно между страницами/проектами. Массовые статусы выполняют
исходные SObject методы в одном Command, удаление — один исходный DeleteCmd.
Ключи id/code одного объекта объединяются сервером, лимит — 500 объектов;
состав зависимости считается без дублей. Повтор retire уже скрытого объекта
не создаёт повторных событий. Неизвестные/чужие ключи отклоняются до изменения.
Сбой до commit откатывает всю команду; прежнее ограничение нескольких БД
с PartialCommitException сохраняется. После неопределённого результата повтор
в том же окне заблокирован.

Проверки: два native HTTP теста — 2.924 s, включая rollback второго объекта
при retire и delete, сохранность зависимостей и объединение разных ключей.
Admin Chromium и публичные signatures — 2 tests / 8.148 s. Interface browser
проверил создание копии с новым ID/code, нулём, false и точной датой; источник
не изменился. Массовое скрытие/возврат/удаление и выбор страницы проверены
мышью, выбор/отмена массового удаления — настоящим touch на 360 px. Прежние
XML/forms/uploads сценарии прошли. Сборка: index-D7WqBqV-.js / index-KVhHyiQI.css.
Воспроизводимые команды остаются как в 0.107; native batch проверка:
`.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_transport.Transport.test_native_batch_operations_atomic_selection -v`.
Рабочие данные/процессы, Handler и Docker не изменены; PostgreSQL повторно
не запускался. Следующий блок — выбор полей массового EditMultipleCmd и
дочерние формы; расширенное дублирование связей/контента остаётся отдельным.

### 0.110 — массовая правка с явным выбором полей

Edit selected использует ту же RecordForm и исходный EditWdg/view edit.
Чекбокс Apply включает поле для всей группы; остальные inputs отключены и
их значения не отправляются. Начальные значения взяты из первого объекта,
различия текущих значений помечены. Можно применить исходное значение без
его изменения. Смена подключения, отмена draft и неопределённый результат
сохранения обрабатываются так же, как для одиночной формы. EN/RU, темы и
полноэкранная touch-форма на 360 px сохранены.

Native /admin/form принимает search_keys: все ключи проверяются до подготовки,
id/code aliases объединяются, лимит — 500 объектов. Descriptor содержит
канонические search_keys и mixed для существующих колонок. Обычный контракт
form и публичные XML-RPC сигнатуры сохранены. Запись идёт через прежний
execute_cmd / tactic.ui.panel.EditMultipleCmd: выбранные поля передаются в
update_data, исходные EditCmd/actions/security/triggers и общая транзакция
сохраняются. Обязательные исходные DefaultValueDatabaseAction и triggers
по-прежнему исполняются по настройкам проекта.

Text/TextArea/Checkbox/Select/MultiSelect, календарь и TimeDatabaseAction
используют существующие преобразования. Файлы, родительские/скрытые inputs,
compound TimeAction и неподдержанные inputs не выбираются для массовой
записи; UI предлагает изменять их отдельно. Копирование файлов или назначения
родителей этим режимом не обещается. Исправлены два найденных дефекта:
MultiDatabaseAction принимает data-список без вложенного списка (остальные
DatabaseAction не менялись); default EditWdg распознаёт числовые int2/int4/int8
из XML. Очистка строк сохраняет исходную семантику SObject: nullable значение
возвращается как null, а не подменяется пустой строкой.

Проверки на временной SQLite: адресный XML-RPC/native тест проверяет выбор
полей, zero/false/очистку/списки, запрещённый контекст и non-admin, а также
rollback обоих объектов после сбоя второго EditCmd. Interface browser прошёл
массовую правку с сохранением разных имён/статусов и точности timestamp,
отмену на настоящем touch 360 px, прежние операции/XML/forms/uploads.

```powershell
$env:PYTHONPATH='src;tests'
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_transport.Transport.test_batch_edit_selected_fields_and_rollback -v
.\.venv\Scripts\python.exe -B -X utf8 tools/interface_browser.py
```

Рабочие данные/сервер, Handler и Docker не изменялись; PostgreSQL повторно
не запускался. Следующий блок — операции дочерних объектов с исходными
parent_key/connect_key, затем кастомные действия XML перед виджетами ячеек.

### 0.110.1 — прокрутка и скрытие навигации

Исправлена высота sidebar-dialog в grid: список ограничен рабочей областью
и прокручивается внутри type-list. Верх сайдбара не сжимается; прокрутка
не передаётся странице. Кнопка навигации теперь доступна на любой ширине,
при скрытии desktop sidebar основная область занимает освободившееся место.
Desktop-выбор видимости сохраняется при переходах через мобильный breakpoint;
на узком экране используется прежний modal drawer.

Server configuration и API documentation перемещены из сайдбара в меню
«More options» (⋮) справа в верхней панели между Appearance и Account,
по актуальному Main.qml Tactic Handler. Конфиг закрывает это меню при открытии.
Новая строка переведена на русский; общий конфиг и его черновики сохранены.

Сборка и адресный admin Chromium — 1 test / 6.948 s — прошли. Проверены
реальная прокрутка колесом, desktop hide/show и ширина основного содержимого,
resize 1440→320→1440, настоящий touch 360 px, меню настроек и прежние
сценарии конфигурации/сессии/тем. Рабочий сервер и данные не изменялись.
Чтобы увидеть исправление, достаточно обновить страницу; backend не менялся.
Операции дочерних объектов остаются следующим этапом после этой UI-правки.

### 0.111 — дочерние объекты и исходные связи

Related objects доступно из контекстного меню строки и через обычную кнопку
⋮, как add_related в Handler. Отдельное окно выбирает дочерний SearchType из
исходной Schema/SearchType; запрос ограничен настоящим родителем. Используются
общие ConfiguredView, RecordForm, ObjectOperations и ObjectAction, без второго
движка форм или SQL updates во frontend. В этом окне пока выводится raw table;
доступны поиск/сортировка/страницы, просмотр, создание, копирование полей,
редактирование, статусы и удаление. Массовый выбор и вложенное раскрытие
нескольких уровней здесь не добавлены.

Native admin-only /admin/object-relations возвращает канонический search key
и типы связей. code/id/search_type/search_code/search_id обслуживаются штатной
схемой. Instance, prefix и самоссылки отмечены как недоступные; нельзя получить
вместо связанных объектов все строки. Файлы/snapshots создаются выделенным
check-in путём. Native /admin/form принимает parent_key/connect_key только
для создания, проверяет ключи, проект и существование объекта; parent_key
дополнительно проверяется по допустимой дочерней связи. Существующие запросы
form и публичные XML-RPC сигнатуры не изменены.

Исходный EditWdg получает parent_key, скрывает FK и готовит task-parent inputs.
RecordForm отправляет контекст в прежний EditCmd: add_relationship выполняется
перед commit, connect_key создаёт исходную SObjectConnection с context task.
Восстановлены исходные SObject.connect/get_connections; отсутствующий объект
завершает команду ошибкой, без частично созданной записи/соединений. Права,
триггеры и Command/Transaction остаются в общем серверном пути.

Исправлены найденные баги исходного ядра: Schema использовала пустой from_col
при проверке implicit id-связи; теперь проверяет вычисленное имя колонки.
Search.add_parent_filter теперь выбирает search_id, если у ссылки нет
search_code, включая родителей без code. Это намеренные отличия от ошибок
легаси: SchemaParity отдельно проверяет AttributeError оригинала и правильные
атрибуты нашего ядра, остальные schema/relationship случаи сравниваются обычно.
Валидация native key selection централизована для code/id ключей.

Проверки на временных данных: XML-RPC/native parent/create/connect/rollback,
защита чужого проекта/non-admin и серверный скрипт SObject.get_connections;
реальный исходный schema runtime, общая batch selection и публичные signatures
— 3 tests / 8.038 s. Interface browser прошёл create/cancel/edit/delete дочерней
записи с проверкой FK, прежние формы/XML/uploads; настоящий touch 360 px
проверил открытие связей, дочернюю форму и отмену без overflow страницы.

```powershell
$env:PYTHONPATH='src;tests'
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_transport.Transport.test_related_forms_original_commands_connections_and_rollback -v
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_schema.SchemaParity.test_reads_match_actual_original_runtime -v
.\.venv\Scripts\python.exe -B -X utf8 tools/interface_browser.py
```

Рабочие данные/сервер, Handler и Docker не изменены. PostgreSQL на этом этапе
повторно не запускался. Для новых native маршрутов требуется ручной перезапуск
launcher. Следующие блоки — instance link/unlink и декларативные custom actions;
затем виджеты ячеек и поведение таблицы.

Исправление совместимости сортировки: исходный Search.add_order_by возвращает
False для отсутствующего поля основного search type. Форк теперь сохраняет
это поведение вместо Fault 501, продолжая применять остальные поля сортировки.
Сравнение с исходным runtime покрывает отсутствующее поле, смешанную сортировку
и @ORDER_BY; неизменённый Handler query_sobjects проверен через XML-RPC с name
в order_bys для milestone без такой колонки. Проверки фильтров и joins сохранены.
Четыре адресные проверки прошли за 7.786 s; рабочие данные и Handler не изменены.

```powershell
$env:PYTHONPATH='src;tests'
.\.venv\Scripts\python.exe -B -X utf8 -m unittest test_read_parity.ReadParity.test_reads_match_actual_original_runtime test_read_parity.ReadParity.test_expressions_and_sql_remain_explicitly_unsupported test_transport.Transport.test_handler_bootstrap_procedures_run_unchanged test_search_joins.SearchJoinParity.test_join_guards_and_api_order_use_the_same_core -v
```

Форма задач Handler: удалён добавленный в форке запрет чтения доступного родителя
из другого проекта в TaskSObjectInputWdg. Подготовка metadata не является записью
связи; native parent_key validation, ACL, Command и rollback сохраняются.
ProcessInputWdg без родителя/pipeline оставляет пустую область, как исходный
EditWdg; native descriptor не выдумывает для неё текстовый ввод. Восстановлены
ProcessGroupSelectWdg/PipelineInputWdg.get_display, возвращающие подготовленный
SelectWdg, и инициализация его labels/values для неизменённого query_EditWdg.
SelectWdg.get_display в headless-режиме возвращает подготовленный control;
HTML rendering/transport по-прежнему исключён, результат HTML здесь не заявляется.
Проверен штатный task insert XML: priority, assigned/supervisor, process,
без родителя, с global/foreign родителями и pipeline; существующие workflow
сценарии сверены с реальным исходным ядром. Handler и рабочие данные не изменены.

Исправлена загрузка task workspace Handler: Search.get_select возвращает
Select с исходными projection/group/order методами. Восстановлены
set_quoted_mode('none'), выражения count(*)/CASE, aliases, GROUP BY/HAVING
и Search.add_empty_filter. Это часть существующего SQL builder Search,
без альтернативного API или изменений Handler. Копия Search имеет независимый
Select; выражения и raw WHERE сохраняют существующие права trusted Python
scripts, публичные raw SQL фильтры API по-прежнему запрещены. Полный автономный
Select executor/SQL builder пока не заявляется.

SQLite connections поддерживают split_part для исходных серверных скриптов.
Исправлен SQLite regex: вместо исходного LIKE используются регулярные
выражения с учётом EQ/NEQ и EQI/NEQI. Это намеренное отличие от ошибки
исходного SQLite vendor: anchors/alternation и literal underscore теперь
работают, как в используемых Handler выражениях PostgreSQL. Два изменившихся
read parity случая имеют отдельные ожидания исходного и исправленного результата;
полная эквивалентность всех PostgreSQL POSIX и Python regex не заявляется.

Адресная проверка исполняет неизменённый query_task_workspace_page через XML-RPC
на временных данных: paging, scope/facets, presets, все используемые sorts,
parent objects, contextual note counts, text и hasNotes. Перезапуск текущих
Python workers нужен для загрузки исправленного ядра.

Восстановлен headless путь таблиц Handler: `TableLayoutWdg`/`FastTableLayoutWdg`,
выбор стандартного `SimpleTableElementWdg`, native/legacy базовые column classes
и `RawTableElementWdg`. `WidgetConfigView.get_display_widget` готовит их options,
имена и row state; HTML/MooTools rendering остаётся исключённым. Поддержка
специализированных action/expression/task/thumbnail столбцов этим не заявляется:
неперенесённые обработчики продолжают возвращать явные ошибки.

`Search.get_by_search_keys`/`SearchKey.get_by_search_keys` выполняют исходное
пакетное чтение по типу и проекту, по code либо id. `keep_order` сохраняет порядок
внутри каждой группы, как в легаси; mixed code/id в одной группе запрещён.
Линейный индекс заменяет повторный list.index при сортировке. Исправлена исходная
потеря явно заданных falsey значений столбца; тест отдельно фиксирует поведение
оригинала и исправленного метода.

Неизменённый Handler `query_table_layout` проверен через XML-RPC на временной
SQLite БД: columns/titles/widths, resolvedClass, sortable, rows и отсутствие
cell errors. Проверены также пакетные ключи разных проектов и существующие
edit/config операции. Реальный PostgreSQL на этом этапе повторно не проверялся.
Для применения backend исправления нужно перезапустить Python workers.

Обычные `ProjectSelectWdg` и `UserSelectWdg` перенесены из старого
`prod_input_wdg.py` в `tactic.ui.input.project_user_select_wdg`. Ссылки на них
исправлены в штатных DEFAULT/access_rule/custom_property/milestone/notification/
queue/task/timecard XML-конфигах. Селектор проектов сохраняет исключение
`sthpw`/`admin` и default текущего проекта; селектор пользователей — пустой пункт,
логины и `default_user`. Исправлено повторное добавление `admin` в список.
Неизменённый Handler `query_EditWdg` проверен через XML-RPC для project_code
у milestone и унаследованного login у note, вместе с существующим edit сценарием.
Каталог/импорты `pyasm.prod` остаются исключёнными; остальные старые классы
этого namespace не считаются перенесёнными. Нужен перезапуск Python workers.

Восстановлены исходные `SearchType.get_sql_by_search_type` и
`Sql.table_exists`: выбор подключения проходит через
`Project.get_db_resource_by_search_type`/`DbContainer`, проверка таблицы —
через DatabaseImpl выбранной БД, без SELECT-пробы отсутствующей таблицы.
Неизменённый `search_types_request(action='load')` из админки Handler проверен
через XML-RPC для `sthpw/change_timestamp` и проектного типа в двух проектах.
Исходные тела двух методов отдельно сравнены на системной/проектных SQLite БД,
включая config/widget_config, повторное использование подключения и отсутствие
таблицы. Реальный PostgreSQL этим исправлением повторно не проверялся.
Для загрузки методов работающими workers нужен перезапуск Stream.

Восстановлена headless цепочка Access Rules: исходный `permission_list` в
`tactic.ui.panel.security_manager_wdg`, каталог
`GearMenuSecurityWdg.get_all_menu_names` и `SideBarBookmarkMenuWdg.get_config`.
`SidebarConfig.get_config` сохраняет исходный порядок view/definition,
priority, общих/личных определений и штатных XML. Загрузчик упакованных
XML перенесён из API в `tactic.core.sidebar_config` и используется теми же
API/Vue путями; второй системы конфигов нет. HTML панели не перенесены.
Неизменённый `security_request` Handler проверен через XML-RPC на временной
SQLite БД: load в admin/проекте, вложенные сохранённые ссылки, save,
отказ при устаревшей ревизии и неправильном access без изменения правил.
Встроенные permissions/menu names совпадают с исходными каталогами легаси;
проверено обновление кэша конфигов после записи. PostgreSQL отдельно не
перепроверялся. Для загрузки новых модулей нужен перезапуск Stream.

В Vue добавлен режим Administration через верхнее меню More options.
Порядок восьми разделов и подписи взяты из AdministrationView.qml Handler:
Search Types, Project schema, Workflow, Columns Editor, Sidebar Editor,
Users, Groups и Access rules. Слева общая навигация, справа существующие
ConfiguredView/RecordForm/ObjectOperations; выбор проекта остаётся в шапке.
Настройки оформления и конфигурация сервера остаются в общей Configuration.
Доступность входа в админку возвращает сервер после проверки прав;
действия продолжают проходить штатные серверные проверки.

Это базовые экраны данных: графические редакторы схемы/workflow, специализированный
редактор SearchTypes/полей, управление членством групп и матрица прав здесь ещё
не реализованы. Schema/workflow ограничены выбранным проектом, Sidebar Editor
выбирает SideBarWdg; Users показывает профиль без password и без повторного
полного чтения учётной записи в Object details. Создание SearchTypes/Schema
через обычную форму отключено, поскольку оно не заменяет создание таблиц/связей.
Back to workspace возвращает предыдущее представление. На узком экране используется
общая выдвижная навигация. Chromium проверяет восемь переходов, данные,
скрытие password, 320px и возврат в рабочее пространство. Handler не изменён.
Frontend собран; для применения нужно перезапустить Stream и обновить страницу.


Раздел Search Types теперь использует специализированный Vue-редактор вместо
таблицы реестра. Каталог, свойства, статистика, физические поля и связи читаются
процедурой search_types_request из Handler, перенесённой в SearchTypesCmd.
Команда вызывается через штатный execute_cmd; отдельного транспорта и Mako
для этого редактора нет. Создание выполняет исходный create_search_type /
SearchTypeCreatorCmd: реестр, таблица, схема и стандартные представления.
Добавление полей использует add_column_to_search_type в той же транзакции.

Восстановлен SearchType.clear_column_cache с адаптацией к ключам SQLite/PG
и безопасным удалением отсутствующего элемента кэша. Save проверяет исходную
ревизию свойств/полей после блокировки реестра, поэтому устаревший документ
не перезаписывает параллельную правку. Блокировка таблицы реестра намеренно
простая; большая конкуренция администраторов потребует более узких блокировок.
Удаление физических столбцов явно запрещено до переноса ColumnDropCmd /
AlterSearchTypeCbk; можно удалять только ещё не сохранённые поля черновика.

UI сохраняет черновик при отмене смены раздела/проекта, использует общие
SettingRow/AppSelect/AppSwitch/AppIcon и переводы EN/RU. На узком экране
каталог заменяется тем же select, управление доступно обычным тапом.
Неизвестный результат записи блокирует повторное сохранение до обновления.
Handler не изменён. Граф связей, naming editor, удаление/переименование
существующих полей и управление индексами этим этапом не реализованы.

Проверены XML-RPC создание/CRUD/добавление поля/отказ устаревшей ревизии и
невалидному типу, доступ по тикету, запрет удаления столбца, Chromium create/save,
сохранность черновика, экран 320px с hasTouch и существующая навигация приложения.
Шесть адресных проверок прошли; frontend собран. Реальный PostgreSQL в этом
этапе повторно не запускался. Для применения нужен перезапуск Stream.

Админка открывается отдельным полноэкранным dialog на общей оболочке
Configuration: шапка с действиями, выбор проекта и собственные разделы.
Рабочая навигация сохраняется; закрытие возвращает прежний проект,
представление, фильтры, сортировку, страницу и выделение без повторного запроса.
Close/Escape защищают несохранённые правки. На 320px раздел выбирается через
общий AppSelect. Это изменение оболочки, специализированные редакторы
по-прежнему переносятся по полному перечню функций Handler.
Frontend собран; достаточно обновить страницу, backend не изменён.

В Search Types перенесён Summary: шесть счётчиков, расположение данных,
унаследованные/прямые связи и карта M:N из исходной функции Handler.
Карта поддерживает zoom, колесо, middle-button pan, native touch scroll и reset.
Каталог показывает таблицы и признаки связей, project-only использует базу
владельца; каталог и редактор имеют отдельную прокрутку на desktop.
Summary/Details/Fields используют общие карточки, controls, иконки и EN/RU.
Это завершение блока Summary, не всего редактора Search Types: Workflow,
Naming, previews/check-in, изменение существующих колонок и мастер создания
ещё переносятся. Backend-команда расширена metadata.relationshipGraph;
для применения перезапустите Stream и обновите страницу.
Шесть адресных проверок прошли: XML-RPC статистика/M:N/унаследованные связи,
сохранение и ревизии, Chromium Summary/zoom/reset/touch, прежняя навигация
и общие UI-ресурсы. Использовалась временная SQLite-база; PostgreSQL этим
этапом повторно не проверялся. Handler и рабочие данные не изменялись.


В Search Types добавлена вкладка Workflow и рабочий редактор процессов; раздел
Administration → Workflow открывает тот же компонент. Pipeline/XML, параметры
узлов, скрипты, статусы задач, связи и расположение сохраняются через штатное ядро.
Зависимости процессов включают триггеры, уведомления, список naming и объекты
pipeline с пагинацией. Исходные callbacks trigger_wdg перенесены из legacy;
SObject.get_display_value возвращён исходным методом для отображения объектов.
При переносе исправлены небезопасная XML-интерполяция статуса уведомления,
недопустимое преобразование постороннего объекта в trigger и старые data при
переключении PythonClass trigger на событие вне task status.

Сохранены неизвестные элементы/атрибуты/комментарии XML, исходные process_code,
сохранение action script без исполнения, транзакции, права администратора,
read-only общих pipelines и проверка ревизий. UI защищает черновики XML/JSON,
использует общий стиль/controls/EN/RU и доступные на touch операции.

Проверки: XML-RPC создание/сохранение/layout/скрипт/правила/notifications,
конфликты ревизий, отказ переименованию и удалению managed rules, права и общие
pipelines; Chromium создание/связи/сохранение/зависимости/черновик/320px touch,
прежний Search Types и общая админка, исходные source hashes/signatures и UI
ресурсы. Все адресные проверки прошли, frontend собран. Использовалась временная
SQLite, PostgreSQL этим этапом не запускался. Рабочие данные и Handler не менялись.
Для применения перезапустите Stream и обновите страницу. Полный Search Types
ещё переносится: следующий блок Naming, затем preview/check-in, Fields и wizard.


Исправлено открытие стандартной формы создания: XML-опции hint/hint_text
поддерживаются и показываются как подсказки. Раньше штатный hint у code
отключал сохранение и скрывал всю форму. Неизвестные опции больше не скрывают
поля; сохранение остаётся заблокированным. Добавлен пункт Create record в ⋮
действий списка; меню, футер и действия строки открывают одну RecordForm.
Chromium проверил создание/сохранение через меню и +, тач 320px, защиту черновика
и безопасный отказ неизвестной опции. Backend и Handler не изменены;
frontend собран, для применения достаточно обновить страницу.


## Search Types: Naming и нативный предпросмотр

Administration → Search Types → Naming: создание/дублирование/обновление правил,
весь набор полей редактора Handler, advanced fields, latest/current/manual
version и защита черновика. Поиск объектов для preview имеет страницы по 50.
Вычисление выполняют Naming.get и общий код DirNaming/FileNaming, включая
TSQL и реальные связи. Обычный preview не создаёт Snapshot/File и не сдаёт файл.
Пользовательский Python/UPDATE/script/class требует отдельного подтверждения;
эта операция не является AI sandbox. Пути используют прямые слеши.

Сохранение config/naming идёт штатным commit с триггерами, ревизией и блокировкой
таблицы; устаревшая ревизия и повтор создания отклоняются. Формат XML-RPC
execute_cmd и существующие методы Naming/DirNaming/FileNaming сохранены.
Новая команда: tactic.ui.panel.naming_cmd.NamingCmd; action load/save/preview,
project_code, search_type; save принимает document (поля Naming), identity
(code правила, пустой для нового), expected_revision из load. Preview принимает
тот же document и sample: key, file, version, process, context, fileType,
snapshotType. allow_execution по умолчанию false; включение явно разрешает
обычное исполнение кастомного кода на сервере. Результат лежит в info исходного
конверта execute_cmd. Штатный check-in в admin/sthpw не применяет naming rules;
это отмечено в UI, правило при preview всё равно можно исследовать.

Проверки на отдельной временной SQLite и Chromium:

```powershell
$env:PYTHONPATH='src;tests'
.venv/Scripts/python.exe -B -X utf8 -m unittest test_transport.Transport.test_naming_editor_commands test_transport.Transport.test_naming_editor_in_chromium test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved test_ui
npm --prefix frontend run build
```

Охвачены TSQL, context wildcard/condition lookup, native get_from_db_naming,
manual version без записей, коллизии в File, custom script, admin-права,
конфликт ревизии, повтор создания, сохранение/дублирование в Vue, draft guard,
advanced fields и тач 320 px. Native NamingUtil также прошёл подслучай
naming_templates существующей runtime-сверки с легаси. Общая SnapshotParity
выявила отдельные несовпадения snapshot_api_files/snapshot_api_empty_files:
в admin квалифицированные search types канонизируются до базовых, поэтому
get_snapshot выбирает C1 вместо CA и не находит CE. Это не проверка готовности
всего API; расхождение требует отдельного исправления в блоке preview/check-in.
Новый PostgreSQL-контракт здесь не запускался. Handler не менялся.

Перезапустите Stream для новых backend методов и обновите браузер. Полный
Search Types ещё переносится: далее Details preview/check-in, существующие
Fields и wizard; отдельный вход в Naming из check-in workspace ещё не подключён.

Исправлена загрузка Create record для `sthpw/search_object`: исходная форма
требовала отсутствующий ColorInputWdg. Подготовка цвета перенесена в
`tactic.ui.input.color_input_wdg`; Vue использует общий AppColorInput с picker
и текстовым полем. Сохранены исходная стартовая палитра, override start_color
и запись через EditCmd; исправлен исходный сбой одиночного start_color.
Неподдержанные параметры форм продолжают блокировать запись. Проверены
HTTP/XML-RPC создание, чтение/очистка цвета и Chromium touch на 320 px.
Это создание записи реестра; физические таблицы создаёт create_search_type
через штатный SearchTypeCreatorCmd. Handler и рабочая база не изменялись.

Следующий блок Search Types: Details / изображение типа.

Закрыто отмеченное выше расхождение SnapshotParity: Project.get_full_search_type
сохраняет явно квалифицированную строку как оригинал. get_snapshot снова
выбирает CA/FA/CE. После очистки кэша add_parent_filter на системном проекте
находит ссылки с базовым типом и его admin/sthpw написанием; ссылки другого
обычного проекта не объединяются. Проверены оригинальное ядро, command listeners,
rollback и SearchLinks; добавлена адресная проверка вариантов родительской ссылки.

Details использует общий AppColorInput и Reset color. Общий ImagePicker повторяет
сценарий Handler: текущий preview / инициалы, локальный выбор читаемого изображения,
отмена выбора и защита черновика. Save сначала сохраняет свойства через штатный
SearchTypesCmd, затем отправляет файл в отдельную клиентскую Commit Queue.
Очередь принадлежит приложению, переживает закрытие админки и хранит исходный
ticket/project/searchKey. UploadServer и simple_checkin создают снимок icon,
web/icon файлы и versionless ссылки штатным ядром. Повтор доступен при известной
ошибке; неизвестный результат check-in не повторяется автоматически, чтобы не
создать вторую версию. Текущий preview читает get_snapshot, без собственного
файлового API и HTML renderer. sthpw/queue остаётся отдельной очередью команд.

Проверены Chromium 1440/320 px: неверное изображение, Undo, Reset color, создание
типа, независимость metadata от ошибки upload, закрытие редактора, Retry из
общей очереди и чтение сохранённого изображения при повторном открытии Details.
Временный HTTP-стенд теперь проходит FirstRunInit до подключения repository
routes, как штатный launcher. Проверены прежний редактор и исходные сигнатуры.
Новый PostgreSQL-прогон этим этапом не выполнялся; Handler не изменялся.

Это ветка изображений SearchType, а не полный перенос Commit Queue Handler:
общие file check-ins, побайтовый progress, восстановление очереди после закрытия
браузера и разрешение неизвестного результата через UI ещё не перенесены.
Полный Search Types остаётся незавершённым: следующий блок — существующие Fields
и мастер создания, затем интеграция общего check-in workspace.

Воспроизведение на временных данных:

```powershell
$env:PYTHONPATH='src;tests'
npm --prefix frontend run build
.venv/Scripts/python.exe -B -X utf8 -m unittest test_ui test_transport.Transport.test_search_type_preview_in_chromium test_transport.Transport.test_search_types_editor_in_chromium test_command_listeners.CommandListenersParity.test_system_parent_references_survive_cache_clear -q
```

## Search Types: Fields и мастер создания

Перенесены операции Fields из Handler: понятные типы с пояснениями и примерами,
поиск существующих полей, добавление в черновик, отметка удаления и Undo.
Служебные поля, системные типы и ключи связей защищены сервером. Save показывает
подтверждение удаления значений; прежняя ревизия не может перезаписать новые правки.

Создание типа проходит три шага: Details → Fields → Ready to create. Черновик
сохраняется при возврате между шагами; итог показывает изображение, свойства,
стандартные и дополнительные поля. Pipeline включён по умолчанию, как в Handler.
Save вызывает существующий SearchTypesCmd и native SearchTypeCreatorCmd;
изображение передаётся в уже подключённую клиентскую Commit Queue.

Серверная процедура основана на `thlib/ui/admin/search_types_api.py`
Handler; удаление использует перенесённые из оригинального TACTIC ColumnDropCmd
и ветку Remove Column в `tactic.ui.panel.AlterSearchTypeCbk`. Физическая колонка,
её значения и элемент definition XML меняются через общий Sql/Command/journal.
Ошибка следующей операции откатывает весь Save; штатные undo/redo восстанавливают
схему, данные и конфиг. Прямой вызов callback также требует admin-права.
Остальные alter modes исходного Search Type Manager ещё не перенесены.

Исправлен исходный баг ColumnAddCmd: `numeric` теперь создаёт числовую колонку,
а не попадает в ветку varchar. Это намеренное отличие от ошибочного оригинала.

Новый блок проверяется на временной SQLite, XML-RPC и Chromium (1440/320 px).
PostgreSQL-прогон этого блока отдельно ещё не выполнен. Handler не изменяется.
Полный Search Types остаётся незавершённым: отдельный мастер из schema canvas
и интеграция общего check-in workspace ещё требуют переноса.

```powershell
$env:PYTHONPATH='src;tests'
npm --prefix frontend run build
.venv/Scripts/python.exe -B -X utf8 -m unittest test_ui test_transport.Transport.test_search_types_editor_command test_transport.Transport.test_search_types_editor_in_chromium test_transport.Transport.test_search_type_preview_in_chromium test_transport.Transport.test_handler_admin_search_types_load_through_xmlrpc test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -q
```

## Project schema: граф, связи и создание SearchType

Administration → Project schema теперь открывает редактор собственного XML проекта,
используя общий RelationshipMap. Доступны зарегистрированные узлы, выбор группы,
координаты без drag, удаление из черновика, flow/network/grid, исходный XML и JSON
атрибуты. Колонки связей читаются штатным SearchType.get_sql_by_search_type;
отсутствующая таблица показана как отсутствующая и не создаётся при чтении.
Create missing columns, reverse/path и M:N адаптированы из schema_connections.py
Handler. M:N готовит отдельный instance тип с двумя связями, поддерживает rename
и Restore direct; физическая запись происходит только при Save schema.

New Search Type открывает прежний трёхшаговый мастер отдельным dialog. Исходная
ревизия схемы проверяется при создании; server response возвращает созданный узел.
Редактор переносит его в существующий черновик с сохранением остальных локальных
правок, вместо reload всей схемы. Сам тип и его таблица уже созданы, а позиции и
остальные правки схемы сохраняются отдельным Save schema. Файл preview идёт через
общую Commit Queue. Закрытие, выбор проекта/раздела и выход защищают черновик.

schema_request/schema_columns_request взяты из `thlib/ui/admin/schema_api.py` ТХ
и исполняются SchemaCmd через native Command/Sql/Schema. Registry lock общий с
SearchTypesCmd: ревизии проверяются после блокировки. Восстановлен отсутствовавший
Schema.set_xml; XML parser сохраняет комментарии и processing instructions,
включая дальнейшее создание SearchType. Validation-команды используют штатный
UserException для понятных сообщений JSON UI; исходные процедуры сохраняют свои
исключения. Код ТХ не изменяется и не импортируется сервером.

Проверки выполняются на собственных временных проектах: stale create/save,
key-column план, M:N таблица, ошибочная связь без частичной записи, finite positions,
admin-права, встроенная read-only схема, прежние native откаты; браузер проверяет
возврат из мастера, локальную связь/позиции, M:N rename/restore и 320 px touch.
Новые сценарии отдельно на PostgreSQL ещё не проверены.
Подтверждение физического удаления и анализ зависимостей перенесены следующим
этапом (см. ниже).
Remove from canvas удаляет только узел/связи, сохраняя таблицы и данные.

```powershell
$env:PYTHONPATH='src;tests'
npm --prefix frontend run build
.venv/Scripts/python.exe -B -X utf8 -m unittest test_ui test_transport.Transport.test_schema_editor_command_and_creation_revision test_transport.Transport.test_schema_editor_in_chromium test_transport.Transport.test_search_types_editor_command test_transport.Transport.test_search_types_editor_in_chromium test_transport.Transport.test_search_type_preview_in_chromium test_transport.Transport.test_handler_admin_search_types_load_through_xmlrpc test_schema_edit.SchemaEdit.test_rollback_and_permission_checks test_foundation.ExtractedContracts.test_source_hashes_and_public_signatures_are_preserved -q
```

## Project schema: удаление SearchType из проекта

У зарегистрированного пользовательского узла доступно Delete from project.
Отдельное окно SchemaTypeDeletion перенесено по сценарию Handler: сначала
сохранить или отменить черновик схемы; затем получить сведения об объектах
(включая архивные), алиасах таблицы, pipeline/process, ссылках task/note/snapshot/
file/work_hour/trigger/notification и других схемах. Удаление допускается только
для пустой таблицы без этих зависимостей. Подтверждение требует полного имени
SearchType; первоначальный фокус — Cancel. System/config типы, чужие базы и
встроенные схемы не удаляются через этот экран. Remove from canvas остаётся
отдельной операцией, сохраняющей таблицу и данные.

schema_delete_request адаптирована из Handler schema_delete_api.py и работает
через SchemaDeleteCmd и исходную tactic.ui.tools.DeleteSearchTypeCmd. Процедура
использует vendor-блокировки вместо PostgreSQL SQL в предметной логике: свежая
ревизия/проверки и удаление выполняются под одним registry lock и блокировками
таблиц до завершения native Command. Ожидание новых блокировок ограничено 3 s.
Непредвиденный SQL сбой не проглатывается как в старой команде. Пустые pipeline
удаляются до DROP/регистрации, чтобы undo восстановил тип и таблицу до pipeline.
Shared регистрация {project} сохраняется для других проектов; удаляется только
таблица текущего проекта. XML-комментарии/PI и незатронутые элементы сохраняются.
Это штатный журнал нескольких БД, без обещания распределённого atomic commit.

Восстановлены public SearchType.get_db_resource_by_search_type и
Project.get_by_search_type. Первый использует тот же resolver, что get_sql_by_search_type,
включая фиксированные/общие базы. Исправлен FileUndo: резервные файлы хранятся
в temp/undo отдельно от удаляемого temp/cache, инфраструктура создаётся до
журналирования mkdir. Ранее сохранённые пути журнала продолжают использоваться.

Окно поддерживает тач/320 px, прокрутку деталей, ошибки и повторную проверку.
После потери ответа операции повторное удаление блокируется до закрытия окна
и Reload схемы. Регистрация/таблица/пустые pipeline/узел и связи проверены на
SQLite и реальном PostgreSQL: stale review, архивные объекты, алиасы, зависимости,
поздний откат, undo/redo, сохранение shared регистрации; права проверены на SQLite.
Chromium проверяет desktop/touch, полный идентификатор, изменение данных после
review, успешное удаление и потерю ответа после commit. PostgreSQL прогон
использует отдельные одноразовые базы и существующий образ, без пересборки Docker.

```powershell
$env:PYTHONPATH='src;tests'
npm --prefix frontend run build
.venv/Scripts/python.exe -B -X utf8 -m unittest test_schema_delete test_ui test_transport.Transport.test_schema_editor_in_chromium test_file_undo.FileUndoParity.test_rollback_restores_overwrites_and_same_basename_backups test_file_undo.FileUndoParity.test_file_log_copy_redo_and_guarded_dependencies -q
docker compose -f deploy/docker/compose.yaml run --rm --no-deps -T --user root -v D:/code/TACTIC_VUE/tactic_stream/tests:/opt/tests:ro -e PYTHONPATH=/opt/stream-src:/opt/python-packages:/opt/tests -e STREAM_POSTGRES_HOST=postgres -e STREAM_POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password app python -B /opt/tests/test_schema_postgres.py SchemaPostgres.test_schema_deletion_matches_sqlite
```

## Навигация проекта: дерево и XML-редактирование

Дерево проекта использует исходный SidebarConfig, приоритет tactic_handler /
project_view, именованные папки, inline children, разделители, is_visible и
серверные link permissions. Явно пустое или отфильтрованное по правам меню не
подменяется реестром SearchTypes. Сохранены поиск с родительской веткой,
сворачивание, keyboard/touch, открытие независимых разделов и подсветка после
перезапуска. Иконки XML FAS_/FAR_/MDI_ разрешает общий AppIcon по оригинальным
Handler charmaps соответствующих поставленных шрифтов.

Edit navigation открывает общий XML-редактор SideBarWdg с источниками, diff,
Check/Preview/Save. Предпросмотр использует то же дерево и не пишет в БД;
Save проверяет дерево под существующей блокировкой/ревизией и native Command.
Циклы не публикуются. Правки обновляют дерево и названия открытых вкладок без
пересборки Vue. Исправлена общая ABA-проверка ревизии XML: учитываются записи
исходного журнала с явным ?project=admin из обычных XML-RPC update.

Полный визуальный Sidebar Editor ТХ ещё не завершён: каталог/операции над
элементами, групповые настройки, saved searches, presets и shelves требуют
отдельного переноса. Runtime и XML authoring проверены на временной SQLite;
новый блок отдельно на PostgreSQL ещё не проверен. Handler не изменён.

```powershell
$env:PYTHONPATH='src;tests'
npm --prefix frontend run build
.venv/Scripts/python.exe -B -X utf8 -m unittest test_widget_authoring test_widget_preview test_transport.Transport.test_project_navigation test_transport.Transport.test_workspace_tabs_in_chromium test_transport.Transport.test_vue_admin_in_real_chromium test_ui -q
```

## Реальный CG-шаблон и тестовый проект

Проверен предоставленный `D:/code/TACTIC_VUE/cg.zip`: обычная загрузка шаблона,
`ProjectTemplateInstallerCmd`, исходный SidebarConfig и все восемь SearchTypes.
Архив и Handler не изменены. При импорте сохраняются JSON document-конфиги
и XML со смешанным содержимым; отсутствующие файлы пустых таблиц обрабатываются
как в оригинальном PluginTools. Код нового проекта переносится также в ссылки
task/subpipeline внутри workflow JSON и pipeline XML.

В `cg_test` локальной Windows-поставки и Docker создано 32 объекта: четыре
категории, пять ассетов, два эпизода, три шота, три текстуры, четыре связи
ассет–ассет, пять связей эпизод–ассет и шесть связей ассет–текстура.
Добавлены 13 задач и 47 заметок, включая ответ на заметку и заметки к задачам.
Набор содержит вложенность Robot → Body → Arm и повторное использование Tool
в нескольких ассетах/эпизодах. Проверяются 45 прямых, обратных и пакетных связей.
Повторное наполнение идемпотентно. По разрешению пользователя в тестовом проекте
архивированы восемь активных Telegram callbacks; исходный код сохранён.

`tools/check_cg_template.py` работает через публичный JSON/XML-RPC API.
`install` загружает шаблон, `create` создаёт новый проект, `seed` наполняет
существующий тестовый проект и отключает его Telegram callbacks.
`refresh` исправляет только ссылки на pipelines в ранее импортированном проекте,
не переимпортируя скрипты. Для `--password-file ''` пароль читается из
`STREAM_CHECK_PASSWORD`; по умолчанию используется локальный секрет Docker.

```powershell
.venv/Scripts/python.exe -B tools/check_cg_template.py install
.venv/Scripts/python.exe -B tools/check_cg_template.py create --code cg_test
.venv/Scripts/python.exe -B tools/check_cg_template.py seed --code cg_test
$env:PYTHONPATH='src;tests'
.venv/Scripts/python.exe -B -m unittest test_cg_template.CgTemplate
```

Тест переиспользует существующий lifecycle для SQLite и PostgreSQL; проверяет
полный откат импорта, сохранность конфигов и отсутствие дубликатов при повторе.
Для контейнерного прогона монтируются tests, cg.zip и tools/cg_sample_data.py,
пути задаются через `STREAM_CG_TEMPLATE` и `STREAM_CG_SAMPLE`.
Vue открывает проект, импортированную навигацию и наполненные Assets Category.
Часть виджетов колонок и Handler presentation mode `continious` ещё не перенесены;
этот режим не подменяется обычной таблицей.


## 0.112.0 — Search/Select и читаемые JS-модули (2026-10-10)

Search и owned Select используют общие фильтры/JOIN и compiler, сохраняют
параметры, область доступа, пагинацию и отдельное состояние копий.
`dumps()` / `loads()` сохраняют колонки/aliases, фильтры, группировку и страницу;
загрузка проверяет права и ресурс получателя, очищает кэш объектов и отклоняет
невалидное состояние без частичного изменения. Исправлена исходная потеря
проекции. Проверены исходное ядро, неизменённый XML-RPC SDK, SQLite,
изолированная PostgreSQL и откат записи после ошибки.

JS-модули имеют читаемые постоянные имена (`ColumnsEditor.js`) и source maps.
Ленивая загрузка сохранена; ETag и `public, no-cache` обновляют JS после сборки.
Проверены HTTP-выдача/304/смена содержимого и ленивые экраны в Edge.
Справка ядра и отладки обновлена на EN/RU. Полная совместимость API,
межресурсные direct JOIN, DISTINCT ON и MySQL этим выпуском не заявляются.


## 0.112.1 — восстановление рабочего пространства без принудительной админки

Свежий вход не подставляет admin, проект и вкладку Projects. Последний логин
запоминается после успешного входа; выбранный проект и вкладки восстанавливаются
для своего аккаунта, включая повторный вход после выхода. Пустое пространство
остаётся пустым, недоступный проект не подменяется admin. Права администратора
берутся из проверенной identity, поэтому его инструменты доступны без открытой
таблицы. API-справочник также не подставляет admin в логин и проект.


## 0.112.2 — адреса без внутренних идентификаторов вкладок

В URL остаются проект, Search Type, вид или skey; внутренний ID поисковой вкладки
хранится в истории браузера. Назад/Вперёд и обновление возвращают нужную вкладку,
а закрытая вкладка не создаётся заново при переходе по истории.


## 0.112.3 — проекция записей родителя и детей в API

get_parent/get_all_children используют общий сериализатор и учитывают columns,
сохраняя служебные ключи. Исправлено повторение исходной потери проекции.
Проверены исходный runtime и XML-RPC SDK, серверный Python, retired, права
читателя, два проекта и rollback. Проекция заметок/родителя совпала на временных
SQLite и PostgreSQL. API-справочник и статья о модели ядра обновлены EN/RU.
Instance JOIN в get_all_children и полный паритет API этим не объявляются.


## 0.112.4 — дети и фильтр родителя через instance-связи

get_all_children и query(parent_key=...) используют общий JOIN instance-связей.
Исправлены исходные ошибки отсутствующей ветки детей, неверного обратного ключа
и нефильтрованного parent-запроса. Проверены исходный runtime/SDK, оба направления,
права промежуточного типа, разные ключи, проекция, два проекта и откат.
Создание/чтение/удаление линков совпало на SQLite/PostgreSQL. Справка EN/RU обновлена.
Self-instance дети, межресурсные instance JOIN и полный API не завершены.

## 0.112.5 — пакетный поиск instance-связей

add_relationship_filters ограничивает JOIN переданными объектами;
add_relationship_search_filter учитывает оператор и фактический ключ схемы
в обе стороны. Исправлены исходные нефильтрованный список и проигнорированный
not in. Группировка get_related_by_sobjects работает при разных ключевых
колонках, aliases поиска не подменяют реальный ключ. Смешанные источники на
разных ресурсах отклоняются до JOIN. Проверены исходный runtime, XML-RPC SDK,
серверный Python, права, rollback и SQLite/PostgreSQL; справка EN/RU обновлена.
not in фильтрует строки JOIN; это не поиск объектов без выбранных связей.
Self-instance, межресурсные JOIN и полный паритет API не завершены.

## 0.112.6 — фактические ключи при проекциях и JOIN

get_sobject_codes/get_sobject_ids возвращают ключи основного типа вместо
первого выбранного поля. Общий быстрый путь сохраняет aliases, строки JOIN,
дубликаты, distinct, явную сортировку и страницу; custom hooks выполняются
один раз, текущие права проверяются заново. Тот же путь извлекает ключи
instance-источника. Проверены исходный runtime, XML-RPC SDK/серверный Python,
Sudo, read-policy, rollback и SQLite/PostgreSQL; справка EN/RU обновлена.
Произвольные агрегатные проекции, self-instance и межресурсные JOIN
не объявлены завершёнными. Полного покрытия API пока нет.


## 0.112.7 — направленное чтение связей одного типа

Self-instance дети, query(parent_key), single/list/Search-фильтры и карты
связей используют общий путь ядра с parent/child концами схемы и SQL aliases.
Дерево результатов использует его же. Исправлена подмена связанных объектов
самим владельцем. Проверены оба направления, code/ID ключи, повторные связи,
циклы, оборванные ссылки, права, проекция/пагинация, Select restore и откат.
13 сценариев настоящего исходного runtime, 85 Windows регрессий, неизменённый
XML-RPC SDK/серверный Python, PostgreSQL и временный cg.zip прошли.
Справка EN/RU обновлена. Направления same-type add_instance/get_instances/
remove_instance требуют отдельной проверки; межресурсные JOIN и полный API
не завершены. Пользовательский cg_test не менялся.


## 0.112.8 — направленная запись связей одного типа

SObject/API add_instance, get_instances и remove_instance используют общий
native Search и явные child(owner)/parent(member) концы схемы. Исправлены
перезапись одного конца и удаление обратных/посторонних связей. Проверены
code/ID, дубликаты, self-links, retired, ошибки концов, права чтения и откат
insert/delete-триггеров. 16 сценариев исходного runtime, 91 Windows регрессия,
stock SDK/XML-RPC, PostgreSQL/SQLite и временный cg.zip прошли. Справка EN/RU
обновлена. Бизнес-запись пока требует администратора по существующему guard;
пользовательский write parity, межресурсные JOIN и полный API остаются открыты.
Пользовательский cg_test не менялся.


## 0.112.9 — проектные записи обычного пользователя

CRUD и instance-связи проектных типов используют общие права проекта,
операции типа, полей и текущей строки. Восстановлены штатные журнал/индекс/
очистка собственного redo. Произвольный SQL и системные операции не открыты.
17 сценариев исходного runtime отделяют исправленные ACL пробелы от исходного
поведения. 111 Windows проверок, stock SDK/XML-RPC от обычного пользователя,
отдельный PostgreSQL/SQLite, rollback, аккаунты/сообщения и временный cg.zip
прошли. Справка EN/RU обновлена; cg_test не менялся. Системные/файловые права,
StatusLog/Workflow, обычная persistent diagnostics и полный API не завершены.

## 0.112.10 — диагностика обычного пользователя

Штатные DebugLog/ExceptionLog и API log записывают аутентифицированного автора
в отдельной собственной Command-транзакции. Ошибка команды сохраняется после
отката; прямой доступ обычного пользователя к системным таблицам не открывается.
Исправлен остаточный стек после ошибки вложенной команды: следующая операция
снова является корневой и откатывает свои данные. Batch после входа закрывает
административные соединения и создаёт контекст фактического пользователя.
Исходное ядро, неизменённый XML-RPC SDK, SQLite/PostgreSQL и связанные контракты
проверены. EN/RU описание внутреннего пути находится в справке «Модель ядра».
Независимая диагностика при уже активной системной записи пока явно отклоняется;
StatusLog/Workflow эффекты обычного пользователя, файловые права и полный API
остаются следующими задачами.

## 0.112.11 — задачи и StatusLog обычного пользователя

Task CRUD и create_task проходят через штатные Command/SObject и исходные ACL:
логический проект задачи, операция типа, видимость строки, поля и редактируемый
родитель проектного типа. Переназначение родителя/проекта задачи пока закрыто.
StatusLog записывается с аутентифицированным автором внутри той же транзакции;
временное разрешение касается одного SObject истории, без общих Sudo/admin прав.
Исправлен проект истории при запросе из другого проекта. Повтор статуса не
добавляет запись; завершение и история откатываются при позднем отказе.
Проверены исходное ядро, неизменённый SDK/XML-RPC, SQLite/PostgreSQL, отказы ACL,
отозванные staged/bound права и rollback массовой операции/триггера/журнала.
Справка EN/RU о внутренних механизмах и методах API обновлена.

Далее по плану: обычные Workflow process_state и их StatusLog, сообщения/заметки
и права скриптов, затем файловые права и остаток API. Сейчас process_state
ещё требует администратора; проверено, что отказ откатывает предшествующие
задачу/историю. Это завершение Task/StatusLog пути, не полной Workflow/API parity.

Уточнение проверки 0.112.11: сохранён штатный импорт плагина с явным ID,
а тест read-policy теперь действительно загружает строку под Sudo и проверяет
отказ после выхода. Для включённого Workflow статусный триггер всё ещё требует
административного script preflight до process_state; настоящий отказ и откат
проверены отдельно. Обычные задачи без такого Workflow доступны, но полный
пользовательский Workflow остаётся следующим пунктом.

## 0.112.12 — декларативный Workflow обычного пользователя

Снят общий запрет запуска графа для обычного пользователя: штатные переходы
задач и call_pipeline_event проверяют видимого редактируемого проектного родителя.
Состояния, сообщения с историей и автоматические заметки ошибок создаются
исходными классами в транзакции перехода, с точечными разрешениями на конкретный
SObject, автором запроса и фактическим проектом. Подмена ссылок/SQL, отзыв прав
колонок и поздняя ошибка откатывают переход. Прямые записи эффектов остаются закрыты.

Сверены настоящий исходный runtime, неизменённый SDK/XML-RPC и изолированные
SQLite/PostgreSQL. Общие права на Python/custom callbacks не открыты: script ACL,
полный охват межпроектных графов, права файлов и полный API остаются в плане.
Внутренние scopes и ограничения описаны в Core model Help на русском/английском.

## 0.112.13 — явное разрешение PythonCmd обычному пользователю

Используется исходный api_cmd key tactic.command.PythonCmd: явный allow и доступ
к текущему проекту разрешают сохранённый/inline Python, Workflow callbacks и
PythonTrigger. Mako, local SDK, автор запроса и транзакционный откат сохранены.
Отсутствие grant, Sudo/fake admin и неактивная учётная запись не дают запуска;
обычные административные callers и произвольные SQL/config/node handlers закрыты.

Это доверенный серверный Python, не песочница или ACL отдельного пути.
Сверены настоящий исходник, неизменённый SDK/XML-RPC, SQLite/PostgreSQL, права
объектов/колонок и rollback. В проверках api_method исправлена подмена всей
конфигурации: теперь проверяется настоящий HTTP 403, а не случайный отказ vendor.
Права файлов, полный охват межпроектных графов и полный API остаются в плане.

## 0.112.14 — межпроектные зависимости Workflow

Определения процессов читаются из конфигурационной БД проекта pipeline.
Общий путь Trigger.call выбирает фактический проект объекта перед подбором и
исполнением process-события; пользователь, соединения и Command сохраняются,
контекст возвращается в finally. PythonCmd grant и сохранённые callbacks относятся
к проекту callback. Дублирующий кеш NodeHandler удалён: используется штатный
Pipeline кеш с существующей инвалидацией после изменения определений.

Исправлен исходный varchar(256) для проектного process_state.state PostgreSQL:
создание/import проекта и Store.upgrade переводят его в text без потери JSON.
Повторная миграция сохраняет уже записанные длинные данные ожидания.
Четыре неизменённых чтения исходного runtime отделяют исправление ошибки выбора
конфигурационной БД от совпадающего поведения внутри проекта.
Обычная межпроектная dependency с задачей, inline/saved callbacks, обратным
завершением, отказами project/type/grant и поздним откатом обеих проектных БД
проверена на SQLite/PostgreSQL и через неизменённый XML-RPC SDK.

Сохранены отдельные commit каждой БД, как в TACTIC; распределённой атомарности нет.
Межпроектные hierarchy/progress и конфигурационные overrides, права файлов и
полный API остаются непроверенными. Внутренний путь и границы — в Core model EN/RU.

Восстановлены устаревшие фикстуры проверок триггеров и создания проектов:
реестр/table config/trigger уже создаётся штатным bootstrap; тест межпроектной
записи больше не вызывает случайно заменённый одноимённый контракт прав пользователя.
В source-сравнении явно учтён ранее исправленный баг: чтение списка static triggers
в оригинале мутирует кеш и дублирует startup handlers, native возвращает копию.

## 0.112.15 — файловые права upload/simple_checkin

Обычный активный пользователь может загрузить файл в каталог своего ticket
и выполнить штатный check-in редактируемого проектного объекта. Проверяются
проект, родитель, операции snapshot/file и поля; metadata не меняет принадлежность
объекта, проекта или существующего file к snapshot. Нативный SQL повторно проверяет
staged values, в том числе JSON PostgreSQL. FileUndo разрешается только в контексте
upload/check-in; произвольные файловые команды и SQL остаются закрытыми.

Проверены две версии, versionless, image main/web/icon и поздний откат на временных
SQLite/PostgreSQL, через неизменённый SDK/XML-RPC и прямой native FileCheckin.
Старые файлы и строки восстанавливаются; потреблённый create upload сохраняется
в штатном durable undo-cache. После окончания check-in rollback восстанавливает
только узлы, созданные проверенным FileUndo. Самописный XML не даёт этого права.

Остальные файловые write API, API inplace/local/custom-классы пока закрыты обычному
пользователю; HTTP/append/group/check-out/undo/redo ещё требуют проверки.
Полная файловая/API совместимость не заявлена. Внутренний путь и права описаны
в существующих темах Check-in и Core model EN/RU. Устаревшие тесты чтения snapshot
и directory draft обновлены под уже перенесённое поведение; диагностический журнал
ошибок учитывается отдельно от отката предметных строк.

## 0.112.16 — файловые права append/group

Обычный активный пользователь может выполнять add_file, group_checkin и add_group
через исходные Command/Checkin/FileUndo. Сохранены проверка проекта, редактируемого
родителя, snapshot/file, полей и принадлежности metadata; файлы ограничены каталогами
upload/handoff своего ticket. Group File/FileGroup заполняет search_code до первого
commit вместо прежней вставки неполной записи. Сигнатуры фабрик и API сохранены.

SQLite/PostgreSQL и неизменённый SDK/XML-RPC проверяют массив append, группы,
диапазоны/шаги/metadata, реальные versionless aliases, ACL, границы путей и поздний
откат старых файлов/строк. Strict aliases требуют явного latest/current naming,
как в TACTIC. SDK manual group читает handoff; manual append — ticket upload.
HTTP upload (в том числе автоматический SDK upload), check-out и undo/redo обычного
пользователя ещё не проверены; full_api_parity_verified=false. API local/inplace/свои
классы остаются admin-only. Ограничения create undo-cache и partial commit сохранены.
Подготовка файлов, примеры и внутренний путь — в существующих Check-in/Core model EN/RU.

## 0.112.17 — HTTP upload обычного пользователя

HTTP UploadServer теперь допускает активного аутентифицированного пользователя
к staging своего ticket без admin/project-привилегий, как исходный UploadServerWdg.
SDK передаёт только ticket; выбранный проект не угадывается. Читатель также может
подготовить файл, но repository check-in сохраняет project/parent/type/column ACL.
HTTP-only ticket_upload пропускает только проверку проекта для личного staging;
persisted active identity, API method restrictions, Command и границы путей сохранены.
Binary XML-RPC upload по-прежнему проверяет проект. Произвольный FileUndo закрыт.

Проверены SQLite/PostgreSQL и неизменённый SDK/XML-RPC+HTTP: Unicode/binary chunks,
resume, empty, automatic simple/group/append, invalid/retired identity, пути,
чужой ticket и поздний rollback нескольких файлов. Multipart/limits и файловые
undo/link контракты проходят. Справка Check-in/Core model EN/RU описывает внутренний
путь и различие staging/check-in. Чанк HTTP коммитится отдельно; offset задаёт клиент,
а повтор неопределённого append не идемпотентен. Check-out и undo/redo журнала
обычного пользователя ещё не проверены; full_api_parity_verified=false.

## 0.112.18 — checkout обычного пользователя

Checkout допускает читателя с project/type/record/column view для родителя,
snapshot, выбранных File и level внутри проекта запроса. Скрытые/отсутствующие
File-ссылки отклоняются до callbacks; admin-выбор версии и исходные пути сохранены.
Callback caller исправлен на текущую Command: ошибки перестали маскироваться
ApiXMLRPC.errors. Sudo и repository-write scope не добавлены; запись обработчиков
проверяет реальные права пользователя. Same-transaction ошибка второго callback
откатывает первый и его журнал, сохраняя repository bytes.

Проверены SQLite/PostgreSQL, неизменённый SDK/XML-RPC+HTTP copy/download/sandbox,
версии/current/versionless, все типы, level, locks и отказы project/type/record/column/method.
Сравнение с исходным Command API/level-контрактом и check-in проходит. Справка EN/RU
описывает границы RPC/client IO, настройки sandbox и исходную публичную static alias
модель. Клиентское копирование после RPC не входит в серверный rollback. Cross-project
checkout пользователя закрыт; group frame expansion/level aliases и undo/redo журнала
обычного пользователя остаются незавершёнными. full_api_parity_verified=false.

## 0.112.19 — undo/redo собственного CRUD проекта

Обычный пользователь выполняет штатный UndoCmd/RedoCmd/SObjectUndo для сохранённых
собственных CRUD-журналов текущего проекта. Канонические owner/namespace/payload/direction
проверяются после row lock PostgreSQL/BEGIN IMMEDIATE SQLite; повторный конкурентный
undo отклоняется. Тип операции инвертируется для undo и проверяет текущие project/type/
record/column права. Скрытые/отсутствующие update/delete объекты теперь дают отказ.
Integral-индекс Global Search восстанавливается только для объектов того же журнала,
со штатным узким Sudo индексной строки, без общего повышения прав пользователя.

Проверены SQLite/PostgreSQL и неизменённый SDK: insert/update/code rename/delete,
default/explicit выбор, сброс redo-ветки, отказ прав/поддельного staged журнала,
поздний undo/redo rollback строк/индекса/журнала и конкурентный повтор undo.
Прежние 26 admin/object/file/schema/client-transaction/source-contract тестов проходят.
Справка EN/RU Objects/Core model описывает внутренний replay и его границы.
Пользовательский file/upload/check-in/schema/task/note/другой-system/multisite replay,
execute_transaction и resumed-session операции остаются закрыты; ignore_files не обходит
границу. Исходные timestamp/ID и partial-commit разных БД сохранены.
full_api_parity_verified=false; file/system replay пользователя — следующий блок.

## 0.112.20 — undo/redo собственного check-in с файлами

Штатные SObjectUndo/FileUndo/FileUndoReplay открыты для сохранённого собственного
check-in журнала обычного пользователя. Восстанавливаются snapshot/file, версии и
versionless вместе, без повторной генерации alias при is_latest/is_current replay.
Проверены owner/project/direction, видимые editable родители, repository ACL и пути,
SQLite/PostgreSQL и исходный SDK, первая/вторая версия, append и кадры, поздние metadata/IO
ошибки и частичный redo. Компенсация использует точные попытанные файловые узлы после
закрытия check-in scope; целый undo-кэш сохраняется. Help Check-in/Core model EN/RU и
API undo/redo обновлены. Нет общего sudo или новых зависимостей.

Изолированный upload, ignore_files check-in replay, schema/task/note/другие-system/
multisite и resumed sessions остаются закрыты. Native numeric ID/timestamp и отдельные
commit БД сохранены; distributed/crash recovery не заявлен. full_api_parity_verified=false.
Repository Sync/S3 исключены. Следующий блок — пользовательский task/note replay.

## 0.112.21 — собственные задачи/заметки и undo/redo

Обычному пользователю открыт штатный create_note для собственного автора и видимого
редактируемого объекта проекта. Native SObjectUndo проигрывает собственные task/note
журналы с текущими ACL и неизменными parent/author/thread. ID заметок сохраняются при
восстановлении, поэтому ответы не теряют parent_id; конфликт ID отклоняется с откатом.
Исторические insert-журналы сохраняют ID перед undo. Сравнение одним тестом с исходным
TACTIC подтверждает намеренное исправление потери связи ветки. Проверены SQLite/PostgreSQL,
исходный SDK, task/note CRUD, code rename, ответы, приватность и права, исторические ID,
конфликты и поздний rollback пакета. Help Core model/Tasks/Task Inspector и API EN/RU обновлены.

Смена статуса с status_log/Workflow/process_state/message и другими системными эффектами
пока отклоняет весь replay, без пропуска истории. Reparenting и системные родители заметок
остаются закрыты; прежние schema/upload/multisite/resumed-session и partial-commit границы
сохранены. full_api_parity_verified=false. Repository Sync/S3 исключены.
Следующий блок — replay Workflow/статусной истории задач.

## 0.112.22 — undo/redo статусов задач и Workflow одного проекта

Собственные сохранённые task-status/Workflow журналы проигрывают штатный SObjectUndo
вместе с status_log, process_state, сообщениями/packages, историей сообщений и своими
заметками. Workflow сообщения теперь записываются существующим logger в точном write
scope; marker полного журнала позволяет отказать старым журналам с отсутствующими backups.
Текущие original parent/source/ACL и точный per-node scope запрещают чужие записи и подмену
SQL. ID task/state сохраняются для status_log; исправлено повторное преобразование GMT
при native redo, PostgreSQL JSON согласован через штатный dialect converter. Проверены
SQLite/PostgreSQL, исходный SDK и одинаковый original/native probe, права/read filters,
late rollback данных/журнала. Help Core model/Tasks/Task Inspector и API EN/RU обновлены.

Cross-project, исторические Workflow без message backups, adoption пустого pipeline owner,
неперенесённые системные журналы, schema/отдельный upload/multisite/resumed replay закрыты.
Внешние отправленные эффекты не отменяются; partial commit разных БД сохранён.
full_api_parity_verified=false. Repository Sync/S3 исключены.

## 0.112.23 — undo/redo Workflow между проектными БД

Собственные полные Workflow-журналы проигрывают запуск/возврат зависимостей между
физическими проектными БД вместе с изменениями объектов, задачами, своими заметками,
состояниями процессов, историей и сообщениями. Канонический журнал сохраняет исходные
namespace/автора/направление; ACL проверяются по фактическому проекту каждого родителя.
Другой проект открывается только для записей проверенных Workflow-родителей того же журнала.
Штатный SObjectUndo, точный поузловой scope и контроль SQL сохранены; callbacks не повторяются.
SQLite/PostgreSQL и исходный SDK проверяют обе стороны зависимости, свои заметки, ID,
отзыв прав в любом проекте, скрытые записи, неверный namespace и откат после записи в обе БД
вместе с историей/индексами/журналом. Неизменённый original/native probe фиксирует дефекты
оригинала: состояние в БД вызывающего проекта и сообщения после undo; новое ядро исправляет
оба. Справка Core model/Tasks/Task Inspector и API EN/RU обновлена.

Исторические неполные backups, adoption пустого pipeline_code, произвольный межпроектный
CRUD/файловый replay, неперенесённые system/schema/отдельный upload/multisite/resumed закрыты.
Внешние отправленные эффекты не отменяются; partial commit разных БД сохранён.
full_api_parity_verified=false. Repository Sync/S3 исключены.
Следующий блок — replay adoption старого пустого pipeline_code в process_state.

## 0.112.24 — undo/redo назначения pipeline старому process_state

Собственные полные Workflow-журналы теперь отменяют и повторяют штатное назначение основного
pipeline родителя старому состоянию с пустым pipeline_code. Проверяются видимые исходные
pipeline/процесс, текущий владелец по направлению и записанная цепочка update; точный поузловой
scope сохраняет ожидаемого владельца до/после, а остальные поля владения неизменяемы.
Произвольная смена владельца и прямые системные записи не открываются. ID и прежние данные
состояния сохраняются. SQLite/PostgreSQL, исходный SDK и неизменённый original/native probe
проверяют назначение/undo/redo, межпроектные зависимости и свои заметки, права, подмены
текущего состояния/родителя/журнала/SQL, скрытые процессы и поздний откат обеих БД/журнала.
Оригинал оставляет старого владельца пустым и сообщения после undo; новое ядро исправляет
назначение и полное восстановление. Справка Core model/Tasks/Task Inspector и API EN/RU обновлена.

Исторические неполные backups, произвольный межпроектный CRUD/файловый replay, неперенесённые
system/schema/отдельный upload/multisite/resumed закрыты. Внешние отправленные эффекты
не отменяются; partial commit разных БД сохранён. full_api_parity_verified=false.
Repository Sync/S3 исключены.

## 0.112.25 — checkout обычного пользователя между проектами

Checkout полного search key другого проекта выбирает snapshot, naming/sandbox и callbacks
в проекте родителя. Сохраняются пользователь, права, Command, транзакция и SQL pool;
исходный контекст восстанавливается после успеха/исключения. Доступ проверяется для всех
связанных проектов, строк и загруженных полей, в том числе level третьего проекта.
Python callback требует PythonCmd grant именно в проекте родителя. Sudo и права записи
не добавляются. SQLite/PostgreSQL и неизменённый XML-RPC SDK проверяют реальные версии,
типы/level, copy/download/sandbox, запреты/блокировки/скрытые ссылки, callbacks и поздний
rollback. Неизменённый original/native probe отдельно показывает пропущенный оригиналом
checkout callback и правильный контекст native обработчика. Help Check-in/Core model и API EN/RU обновлена.

Grouped frame expansion, level-scoped aliases и replay произвольных межпроектных callbacks
ещё не проверены. Клиентский IO после RPC не откатывается сервером; статические repository
URL сохраняют публичную модель Apache, а разные БД — partial commit.
full_api_parity_verified=false. Repository Sync/S3 исключены.

## 0.112.26 — checkout реальных кадров последовательности

Checkout разворачивает выбранные sequence File через штатные FileRange/FileGroup в
согласованные client_lib_paths/sandbox_paths/web_paths до callbacks. Для * сохраняется
порядок XML и смеси типов; конкретный тип выбирает первый File, как раньше. Пути обычных
файлов/каталогов, сигнатуры API, права и транзакционная модель сохраняются. Исходный SDK
теперь копирует/скачивает кадры и помещает их в sandbox; оригинальный checkout возвращал
один шаблон, что явно показано неизменённым source/native probe.

32 регрессионных теста, SQLite/PostgreSQL и неизменённый SDK проверяют hash/printf,
шаг/отрицательные кадры, версии/current/latest, несколько sequence типов с обычным
файлом, реальные байты, ACL, повреждённые диапазоны и поздний rollback callbacks.
Встроенная Help Check-in/Core model и API EN/RU обновлена.

Level aliases и replay произвольных межпроектных callbacks ещё не проверены. Ошибка
клиентского IO после RPC может оставить частичные локальные копии; сервер её не откатывает.
Публичная семантика статических repository URL и partial commit разных БД сохранены.
full_api_parity_verified=false; Repository Sync/S3 исключены.

## 0.112.27 — latest/current aliases по уровням

Штатные Snapshot/check-in и get_snapshot/get_paths выбирают и обновляют versionless
по точным level_type/level_id; область без уровня остаётся отдельной. Публичные
сигнатуры сохранены. is_current=False оставляет прежний current, коды aliases стабильны.
Существующий путь вне выбранного alias не перезаписывается: неправильный naming
отклоняется, строки и файловые операции откатываются через Command/FileUndo.

SQLite/PostgreSQL, неизменённый SDK и исходное ядро проверены на приватных данных:
три области, версии, байты, права записи, поздняя ошибка и коллизия путей.
Original/native probe явно показывает исправленную ошибку выбора одного snapshot
для всех уровней. Справка Check-in/Core model/API EN/RU дополнена.

Следующий незавершённый контракт — удаление level snapshot и переназначение aliases.
Level-specific replay, межпроектное создание aliases и MySQL здесь не проверены.
Существующие границы публичных repository URL и partial commit независимых БД
сохранены; full_api_parity_verified=false; Repository Sync/S3 исключены.

## 0.112.28 — проход Administration целиком

Пройдены восемь разделов и вложенные вкладки по текущему QML ТХ. Свежие снимки
Qt/QML и Chromium при 1400×940 и 900×620 собраны в
[сравнение админки](.screenshots/administration-current/index.html).
Схема QML/controller → native storage/command → Stream и скрытые параметры
описаны в существующей справке Administration на EN/RU.

Перенесены сворачивание навигации 250/56 px, независимые черновики разделов,
отметки правок, закрытие с показом незавершённого редактора и блокировка проекта.
Подогнаны каталоги, вкладки, формы, splitter колонок, Sidebar, Users/Groups и
матрица прав. Графы поддерживают native input/output-порты, предварительную линию,
круглый Progress, рамку и групповое перемещение, клавиши и сохранение. Исправлена
ошибка штатного Progress-handler: default process больше не передаётся как None.

Проверены Chromium-сценарии и 33 native SQLite-регрессии, включая сохранение,
конфликты, потерю ответа, права, unknown XML и откат. Полезные дополнительные
инструменты Stream оставлены доступными. Страницы Add node переносят каталог типов
схемы и сетку видов процессов. Дополнительные прямые инструменты и растеризация
шрифта отличаются от ТХ; полное пиксельное совпадение не заявлено.
Этот прогон не включает новую приёмку MySQL/PostgreSQL. Configuration и рабочие
панели остаются следующими крупными блоками; full_api_parity_verified=false.


## 0.112.29 — Configuration: восемь страниц и общие controls

После прохода Administration закрыт общий ColorField/ColorPicker: swatch,
HSV-плоскость, hue, HEX, отдельный черновик, клавиатура и подтверждение.
Используется в обычных формах и редакторах. Сравнение Administration теперь
содержит 36 актуальных Qt/QML ↔ Chromium пар.

Configuration получила восемь страниц текущего ТХ, навигацию 216px, независимые
черновики, Reset/Apply текущей страницы, Save всех без закрытия, общий Cancel,
preview оформления и обработку ошибок хранилища. Палитры перенесены как плитки
36px/круг 18px. Дополнения браузера оставлены в видимом разделе.
Применённые defaults управляют новыми поисками, чек-ин заданиями, Task Manager
и Inspector; сохранённое состояние пользователя/проекта важнее defaults.

В репозиториях есть сводка, отдельное переносимое/разворачиваемое окно с каталогом,
общим Config-черновиком, именем/цветом/клиентскими путями и Advanced settings.
Проверка серверных путей — штатная Command/Environment/FileUndo с пробой записи.
Серверные корни/default/активные алиасы остаются readonly до отдельной миграции
существующих файлов. Имена/цвета читаются из штатного JSON-поля без
перезаписи XML. Проекты активируются явно; редактирование/создание штатные,
экспорт шаблона использует ProjectTemplateCreatorCmd и реальный ZIP.

Кэш разделяет раскрытие веток и данные сеанса. Есть очистка раскрытия вкладок
с сохранением фильтров/доков и refresh серверных каталогов/активного поиска.
Настольные дисковые кэши, DCC, пресеты отдельного ТХ и Qt rendering не заявлены
как browser-функции. Repository Sync и S3 исключены.

Справка EN/RU описывает действия, defaults, владельцев, ключи хранения и границы.
Свежие сравнения восьми страниц и редактора репозиториев:
`.screenshots/configuration-current/index.html`. Снимки ТХ получены настоящим
Qt/QML с автономными фикстурами, без изменения его исходников/настроек.
Полное пиксельное совпадение, PostgreSQL/MySQL и полная API parity не заявлены.

## Configuration и начало рабочих панелей — 0.112.30

Завершены browser Enabled/Default, создание репозиториев, редактирование штатных
корней/URL и проверка доступности черновика. Смена корня проверяет готовую копию
существующих файлов по native путям/SHA-256; сама ничего не переносит. Перед
сменой остановить чекины, после сохранения перезапустить backend. Новые чекины
браузера используют выбранный алиас, ревизии сохраняют свой; исходный SDK без
явного алиаса использует прежний Naming. S3/Repository Sync исключены.

Description перенесён из текущих DescriptionEditor.qml/state_detail_editing.py:
общий док, объект/процесс/снапшот, native update, ошибки с сохранением черновика,
Pin/Unpin для форм check-in. Видимый список независимых черновиков сохранён
как дополнение Stream. Черновики живут в памяти, параллельные правки не объединяются.
Свежая галерея: `.screenshots/description-current/index.html`. Остальные рабочие
панели пункта 3 ещё не завершены; следующий — полный Snapshot Browser.
Возможности и границы опубликованы в встроенной EN/RU Help.

## Snapshot Browser — 0.112.31

Новый общий док следует выбранным объекту, процессу, задаче или версии; native
история, превью, Fit/Fill, три режима, splitter, Show All/More и точные действия
с файлом. Native FileUndo откатывает удаление при ошибке, соседние версии сохранены.
Справка EN/RU: dock.snapshot; свежие сравнения: `.screenshots/snapshot-browser-current/index.html`.
Metadata member rows sequence/UDIM/UV ещё не перенесены; обычный пользователь
и Qt-only форматы не объявлены проверенными. Пункт 3 продолжается.

## Ядро и API — 0.112.37

Сверены восемь изменившихся исходников ТХ; текущие SHA записаны после аудита, а не приняты за доказательство полной совместимости. В исходном каталоге 129 exposed методов: доступны 122 входные точки, пять контрактов ещё не перенесены, два production-метода исключены. `full_api_parity_verified` остаётся false.

Обычные объектные операции используют native ACL; RetireLog получает узкую внутреннюю область записи. Remote/local SDK делят проверку родителя чекина и восстанавливают вложенные права. Поздняя ошибка откатывает запись и append файла; native plugin undo/redo корректно обрабатывает nullable defaults. Пользовательские SObject-конструкторы получают исходные поля fast_data плюс native TIME metadata, без внутреннего кеша фабрики.

Встроенная EN/RU тема «Совместимость ядра и API» описывает исполнение, XML-RPC, права, транзакции, source/runtime проверки и точный остаток: set_palette, get_widget, get_column_widgets, set_application_state и execute_js_script (HTML/PyV8). Browser DTO/JS не подменяют их исходные ответы. Repository Sync, S3, TH/DCC и commit_session/get_md5_info исключены.

Проверка происхождения/каталога: tools/audit_api.py; измеряемый общий набор: tools/verify_api.py. Счётчики сохраняют только названия методов и исходы, без аргументов и билетов. Свежие кадры справки: .screenshots/api-block6-help-en.png и api-block6-help-ru.png. Общая приёмка и актуальные ограничения перечислены в UI_ARCHITECTURE.md.

Общий прогон: 923 теста, 909 прошли, 13 пропущены; единственный сбой выявил гонку открытия Configuration во время восстановления адреса после reload. После её исправления пять затронутых Chromium-сценариев прошли, включая задержанный ответ navigation, вход/сессию, layouts и полный mobile/desktop workbench. Общий набор повторно целиком не запускался. Все 122 входа API измерены: 121 успешный, test_error — ожидаемая ошибка. Сводка и исходные отчёты: .screenshots/api-block6-verification.json. Тестовые процессы завершились; рабочий сервер сохранён. Для применения серверных изменений перезапустите штатный батник.

## Сквозная приёмка и поставка — 0.112.38

Предоставленный cg.zip загружается и создаёт проект через штатный браузерный
мастер; внутри manifest шаблон называется niki_friends. На частных проектах
проверены 32 объекта, 13 явных задач, 47 заметок и 45 связей, вложенные/общие
ассеты, эпизоды/шоты, категории и текстуры. Native SQLite/PostgreSQL сценарий
также проверил late rollback, отсутствие дублей, две версии файла и latest,
сохранение старой версии и неизменённый extended check-in текущего ТХ.
В тестовых проектах выключены только согласованные Telegram callbacks;
рабочий cg_test не изменялся.

START_TACTIC_STREAM.bat использует init --if-needed на настроенном Store
вместо проверки файла SQLite. Явный init сохраняет запрет пересоздания базы.
Общий data-dir/config применяется ко всем шагам; два настоящих запуска BAT
сохранили проект, файл и preferences после upgrade/restart. Браузерный probe
получил корень приложения после готовности workers. Старый UI /admin/ удалён;
родные /admin/... JSON API остаются.

Vite теперь пересоздаёт generated output из current build и frontend/public;
старые chunks не накапливаются. Vue license notice перенесён в public, JS/maps
включены в wheel. Чистый пакет уменьшился с 236191305 до примерно 15,6 МБ.
Отдельная установка вне src прошла оба CLI запуска и остановки, проверку
текущего manifest, 44 JS/source maps, HTTP/ETag и EN/RU Help. Встроенная статья
«Установка, обновление и приёмка» описывает vendors, сохранение данных,
backup/update/restart, чистую сборку и cache/reload.

Полный обнаруженный набор: 926 запусков (888 уникальных IDs, включая
существующие повторы импортированных TestCase). После точечного повтора
Windows результат — 913 passed, 13 skipped. Исходный native-отчёт содержит
один FAIL из-за отсутствовавшего main guard временного partition runner для
Windows spawn. Исправлен runner; все 3 CLI-теста прошли отдельно. Старый
отчёт сохранён и не выдан за первоначальный clean pass. Transport/browser
части прошли 62 + 61 тест без повторов. Все 11 PG-пропусков дополнительно
пройдены на PostgreSQL 18.6; всего 16 реальных PG-тестов. Два symlink-пропуска
Windows проверены теми же сценариями на Linux. Неизменённый SDK ТХ прошёл
12 проверок на SQLite и 12 через частный Apache/PG; deployment-check также
подтвердил origin, assets, отдельные listeners 8081–8083 и TEMP rollback.
В PG-тесте исправлен ожидаемый тип timestamp-отказа; validator не ослаблен.

Свидетельства: .screenshots/delivery-verification.json и указанные в нём
исходные runtime отчёты; свежие кадры delivery-cg-create.png,
delivery-cg-created.png и results-tree/cards/versions-*.png. Собственные
серверы, workers, Chromium и контейнеры завершаются в cleanup; рабочие
процессы и базы не останавливались и не мигрировались. Python-изменения
подхватятся при следующем обычном запуске/обновлении рабочего сервера.

Остаётся: MySQL, будущий EXE/Electron комплект, пять HTML/PyV8 API контрактов.
Два старых production-входа, Repository Sync, S3 и TH/DCC bridge исключены.
full_api_parity_verified=false. Windows symlink-привилегия, физический телефон
и полное попиксельное Qt/браузер совпадение этим прогоном не подтверждены.
Стабильные JS имена требуют reload открытых вкладок после обновления;
бесшовный rolling update разных версий не заявлен.

### Native HTML / server JavaScript (0.112.39)

The five remaining API entries are connected: request-local `set_palette`, native HTML `get_widget`, nested cell HTML `get_column_widgets`, `top_layout` state and `execute_js_script`. 127/129 exposed methods are available; two deprecated production methods stay excluded. This is not full behavior parity: unported widget classes, full interactive HTML tables and old application shells fail explicitly. Server JavaScript is synchronous trusted administrator code on QuickJS-NG with native API/Command rollback, and is visible in Script Editor/Shelf. EN/RU built-in Help explains original SDK quirks, execution targets and boundaries. Repository Sync and S3 remain excluded.

Final regression: 945 runs, 932 passed, 13 skipped, no failures/errors
(`.screenshots/api8-final-full.json`). The skipped cases require PostgreSQL or
Windows symlink privilege. Native HTML/palette comparison, Chromium editor/shelf,
Vite build and isolated wheel HTML/JS/state smoke passed. Original PyV8 was not
run; complete old HTML shells remain unsupported. Owned test Python processes
finished; the existing server was left running and needs a normal restart.

### Native API variants and scope (0.112.40)

Dictionary API `info` and affected objects reach native command listeners.
Command keys retain fixed kwargs, user/ticket ownership and resolved-class
policy; `use_transaction=False` skips nested hooks while preserving outer
rollback. Native SQL Delete, palette expressions, level-scoped snapshot
deletion and named `view_as_attr` XML save/reload/reorder are restored, with
source defects and security boundaries documented in EN/RU built-in Help.

The variant matrix distinguishes verified calls, explicit failures and scope
exclusions. `tools/audit_api.py --contracts-output <file>` produces a diagnostic
guard inventory, not a count of missing features. 127/129 entry points are
available; two deprecated production methods are excluded; full behavior
parity is still false. Further full old HTML-shell migration is excluded by
user decision; existing working HTML APIs/dependencies are retained. MySQL is
deferred. The next planned block is 11: final desktop UI matching to Handler.

### Browser update reconnection (0.112.42)

Messages and Task Inspector follow the shared cursor batch instead of separate
timers. Background reads use a 30-second deadline and coalesce identical
in-flight calls. A disconnected server pauses and cancels background reads;
reconnection performs one current synchronization without replaying requests.
Normal intervals and exponential reconnect delays have random variation;
continued failures retry every 60–75 seconds. Focus/Retry cannot bypass backoff.
Hidden tabs suspend reads and resynchronize on return, preserving drafts.
Explicit writes/uploads retain their own result handling and are never replayed.

Built-in EN/RU Server Help explains the schedule, scope and load estimates.
`frontend/tests/update_requests.mjs` verifies coalescing, cancellation, no replay
and deadlines; `update_outage.mjs` mounts the real components in Chromium and
checks outage recovery, drafts, project changes and 100 staggered polling loops.
This is bounded polling, not SSE/WebSocket delivery or a server capacity benchmark.

## 0.112.43: опциональный SSE

Configuration → Server → «Получение обновлений» и меню соединения позволяют
выбрать SSE вместо периодического опроса. Нативные commit, включая XML-RPC/ТХ
и Python-скрипты, пробуждают подписчиков между воркерами; rollback не уведомляет.
В простое нет полного опроса и пустых пакетов данных; служебные heartbeat
поддерживают авторизацию/присутствие. Ограничения доставки, прокси и нагрузка
описаны в существующей EN/RU Help → Server configuration.

## 0.112.44: первое серверное ядро файловых проектов

Новый режим включается только при создании: `CreateProjectCmd(project_mode="file_project")`
либо встроенным `ProjectTemplateInstallerCmd(template_code="perforce_like")`.
Обычное создание по-прежнему использует `project_mode="classic"`. Шаблон
`config/file_project.json` поставляется в пакете; режим фиксируется типом проекта.
Переключения существующего проекта и автоматической миграции нет.

Предметный код расположен в новых `pyasm.biz.file_project`, `file_catalog` и
`tactic.command.file_project_cmd`; HTTP-модуль только передаёт двоичные данные.
Это native SearchType/SObject/Command, без SQL в предметных командах. Каталог,
версии, checkout, workspace/Have, черновики и sync-задачи находятся в проектной
БД. Файлы — приватные неизменяемые blobs в `data/file-projects/<project>/blobs`,
разбитые на 256 каталогов по префиксу UUID;
общедоступные routes репозиториев их не раскрывают. Depot сейчас логическое
пространство этого хранилища, без привязки к публичным classic repository aliases.

Каталог — неизменяемое B+tree с максимум 256 элементов на страницу. Правки
поступают чанками до 1000 путей; страницы сбрасываются в БД порциями по 16,
кэш чтения содержит до 64 страниц. Stream и changelist держат только корень.
Submit меняет корень stream и статус changelist в одной проектной транзакции,
с проверкой исходной ревизии. Ветка использует общий исходный корень, затем
публикует свой. Нет миллионного XML snapshot, физических versionless копий
или прохода по всем файлам при submit. Удаление сохраняет tombstone и историю.

### Вызовы API

Все операции: `server.execute_cmd("tactic.command.file_project_cmd.FileProjectCmd", args)`;
ответ — стандартный `info`. Основные аргументы:

| action | Аргументы / результат |
| --- | --- |
| capabilities | Лимиты, версия схемы, режим |
| create_depot | code, optional title; только admin |
| create_stream | code, depot, optional parent; собственный корень и ревизия |
| create_workspace | code, stream, local_root; локальный путь — только metadata |
| create_change | workspace, optional description; возвращает code, edit_revision |
| upload_begin | change, size для одного файла; либо request_id, files[{path,size}] до 1000 |
| upload_batch | change, items[{blob,data}] с base64; завершённые небольшие файлы, суммарно до 4 MiB |
| upload_chunk | change, blob, offset, data; один кусок до 4 MiB, безопасный повтор того же диапазона |
| upload_finish | change, blob, optional sha256; проверяет длину и SHA-256 потоком |
| uploads | change, optional after/limit; индексированное восстановление списка uploads и offsets |
| checkout | change, paths до 1000, mode=ordinary/exclusive |
| edit | change, chunk, edit_revision, operations[{path,blob}] или {path,delete:true}; идемпотентный chunk |
| submit / revert / status | change; revert сохраняет подготовленные данные, status показывает состояние |
| list | stream, optional published_change/prefix/after/limit; либо собственный change для черновика |
| changes | Пагинация своих changelists, after/limit; индекс по владельцу и code |
| history | stream, path, optional published_change/limit; до 1000 переходов по истории |
| have | workspace, optional root/prefix/after/limit; подтверждённое содержимое workspace |
| workspace_status | workspace; локальный корень, Have и code активного sync после реконнекта |
| sync_begin | workspace, optional prefix; фиксирует опубликованный корень |
| sync_next | sync; до 1000 записей и ack_revision, без продвижения до подтверждения |
| sync_ack | sync, ack_revision, paths всего чанка после локальной записи; обновляет Have и прогресс |
| sync_status / sync_cancel | sync; состояние либо явная отмена |

`published_change` из первой страницы фиксирует каталог для последующих страниц
и скачиваний, даже если stream уже обновился. Sync хранит этот корень и
подтверждённый курсор в БД; реконнект повторяет текущий чанк. На workspace
допускается один активный sync. Миллион файлов не создаёт миллион jobs.

Binary HTTP использует заголовок `X-Tactic-Ticket`:

- `PUT /file-project/upload?project=...&change=...&blob=...&offset=...`: сырые байты до 4 MiB.
- `GET /file-project/download?project=...&stream=...&path=...&published_change=...`:
  отдельный файл, native HTTP Range для возобновления больших файлов.
- `GET /file-project/sync-download?project=...&sync=...`: потоковый tar текущего
  чанка; включает существующие файлы размером до 4 MiB, без временного архива
  и сборки его в RAM. Большие файлы скачиваются отдельно через Range, tombstones
  обрабатывает клиент по manifest из sync_next. Заголовок X-Tactic-Ack-Revision
  связывает архив с подтверждением. Нет отдельного запроса на каждый маленький файл.

### Права, триггеры и атомарность

Проверяется authenticated identity, доступ к проекту, `file_depot` с code/project
и native SearchType/record/column ACL. Для depot используются native уровни
`view` (чтение) и `edit` (запись); `allow` даёт полный доступ. Например:
`<rule group="file_depot" code="main" project="files" access="view"/>`.
Также необходимы соответствующие права на внутренние `file_project/*` SearchTypes;
для workspace/Have/sync нужны insert/edit на metadata даже при read-only depot.
Сырой query/insert/update внутренних типов закрыт; пользователь работает fixed API.
Черновики, uploads, workspace и sync проверяют владельца. Depot-specific deny
проверяется раньше wildcard. Метод/команда проверяют обычные api_method/api_cmd ACL.

Native SObject validation и synchronous triggers сохраняются. Наличие настроенного
native/SQL-триггера переводит пакетную запись в последовательный путь, сохраняя
возможность анализировать предыдущие записи. Триггер, требующий другой БД или
отложенной новой транзакции, вызывает отказ до публикации и откат всего submit.
Это явная граница атомарности, а не игнорирование триггера. Автоматический classic
global-search index и system change_timestamps не создаются для новых записей;
файловая история хранится в том же проекте. Classic Undo/Redo не публикует/откатывает
changelists: revert относится к pending, а исправление опубликованного результата
создаёт новый changelist. Правки обычных проектов сохраняют прежний путь.

### Проверки и границы первого блока

SQLite: isolated template + два файловых проекта рядом с classic, 1000 записей
одним changelist, ordinary/exclusive checkout, отказ триггера после смены корня,
запрет другой БД, ordinary-user ACL и отзыв прав колонок, idempotent uploads/edit/ack,
удаление с историей, закреплённый sync и HTTP binary/Range/tar. Native classic
project creation, file undo, SQL, explicit client transactions, browser check-in
и серверная check-in queue проходят отдельные regression tests.

`tools/file_project_benchmark.py --files 1000000` создаёт **синтетический каталог**
на временной SQLite через native schema/SObject/Command. Финальный Windows-прогон:
построение страниц — 5.65 с, submit — 15.63 мс, первая/последняя страница 1000
элементов — 11.25/10.23 мс, sync_begin — 13.84 мс, sync_next — 10.61 мс.
Время включает Api.dispatch, но не сеть, миллион version/checkout записей или bytes.
Отдельно проверяется `--checkin-files 1000`: 1000 разных физических файлов по
512 bytes (500 KiB суммарно), новые UUID и разные bytes. Descriptor batch —
556.16 мс, upload/fsync — 1710.89 мс, edit/version/checkout — 964.18 мс,
submit — 15.36 мс. Уже загруженные данные → завершённый чекин — 979.54 мс;
весь путь — 3246.59 мс. Проверено содержимое нескольких записанных файлов.
Пиковый working set всего процесса с миллионным каталогом и этой выборкой —
68.93 MiB. Это не миллион реальных файлов, не GUI/сетевой замер и не гарантия
секундного SLA для произвольного hardware/триггеров. PostgreSQL/TB не проверены.

TH/TS интерфейсы ещё не подключены. Merge/rebase между конкурирующими changelists,
shelve, changelist edit leases, mappings нескольких depot, локальный reconcile,
квоты/GC и администрирование retention — следующие блоки. Пока конфликт любого
изменения head stream требует явного разрешения: автоматической перезаписи нет.
История ограничена head-окном; cursor для глубоких историй пока явно отклоняется.
Большой upload_finish делает один полный проход SHA-256 по файлу **до** блокировки
записи, затем повторно проверяет blob/changelist и сохраняет результат; worker-проверка
и глобальное управление TB transfers ещё не реализованы. Это рабочее первое ядро,
а не готовая замена P4V и не доказательство production ёмкости.

## 0.112.45 — устойчивость файлового ядра: конкуренция, аварии и реальная metadata

Файловые операции остаются в отдельных модулях file_project; Classic default и
интерфейсы TH/TS не менялись. Общее ядро получило узкие opt-in изменения: native
вставку с пропуском существующего unique code, bounded row lock wait и безопасный
порядок приватного файлового отката. Бизнес-операции используют Command/Search/
SObject; SQL диалект остаётся в Sql, без прямого бизнес-SQL в файловых командах.

Исправлены воспроизведённые ошибки:

- Файловый rollback раньше освобождал DB lock, позволяя чужому повтору загрузки
  попасть под truncate/unlink предыдущего запроса. UploadUndo откатывается первым.
- После аварийного хвоста rollback повторного запроса восстанавливал фактическую
  длину мусора вместо committed offset. Используется подтверждённая длина;
  отсутствие committed prefix отклоняется, нулевое дополнение запрещено.
- Ошибка ответа COMMIT могла удалить уже закоммиченные bytes. После начала COMMIT
  приватные uploads сохраняются независимо от результата ответа. uploads/status
  определяют durable состояние; повтор использует committed offset/receipt.
  Незакоммиченный хвост может остаться до повтора или будущего GC.
- На PostgreSQL два workspace падали на unique page code при одинаковом Have.
  Native insert-if-absent и сравнение JSON сохраняют immutable page; native insert
  callback запускается только для реально вставленной страницы.
- Занятый changelist мог ждать PostgreSQL row lock бесконечно. Файловая команда
  задаёт пять секунд; SQLite использует native busy timeout. Клиент может повторить.

Профиль PostgreSQL выявил повторную проверку принадлежности БД для каждой строки:
на 1000 путей — тысячи read transactions. require_single_database проверяет
зарегистрированный ресурс один раз; can_write_resource сравнивает bound identity.
Неизвестная/другая БД отвергается. Это не кэш прав: native ACL каждой записи и поля
сохраняются. Существующие checkout теперь тоже используют commit_records; native
callbacks/SQL triggers включают последовательный fallback.

На свежих 10000-path выборках локальной PostgreSQL 18.6 (Docker), через Api.dispatch:

| Операция | До | После |
| --- | ---: | ---: |
| Первый edit 1000 новых путей | 9351.33 мс | 1972.58 мс |
| Edit 1000 существующих путей в новом changelist | 20361.17 мс | 5949.81 мс |
| Последующий submit | 390.72 мс | 343.90 мс |

Каждый прогон создаёт новую БД, новый changelist и новые uploads; это не reuse
кэша конкретной тысячи файлов. Скорость не включает клиентскую сеть/передачу
payload; физический payload мал и совместно используется логическими путями.
Заявлять «1000 файлов меньше секунды» по PostgreSQL пока нельзя.

### Воспроизводимые изолированные проверки

`tools/file_project_checks.py` запускает одинаковые контракты SQLite; `--postgres`
поднимает отдельный postgres:18.6 с временным паролем, случайным loopback портом
и без persistent volume. Готовность проверяется по TCP, чтобы не принять
временный bootstrap server за рабочий. Контейнер удаляется в finally, наличие
проверяется после удаления. Рабочая конфигурация/БД/сервер не используются.

Проверены два пользователя и ordinary/exclusive conflicts, concurrent submit,
параллельные повторения upload_begin/chunk/edit/sync_ack, pinned sync/reconnect,
порядок configured native callbacks, project/depot/column ACL и запрет другой БД.
Отдельный subprocess аварийно выходит во время upload/edit/submit и после commit.
Проверены отсутствие частичной публикации, восстановление bytes и безопасный retry
после потерянного ответа. Поздний native callback после 1000 version/checkout
записей и ошибка самого COMMIT откатывают metadata целиком; prepared uploads
сохраняются. Перезапуск ОС/сбой питания и внешние эффекты произвольных scripts
не входят в доказанную атомарность проектной БД.

`tools/file_project_scale.py --files 1000000` создаёт реальные version/checkout
через upload/edit/submit API чанками по 1000. Проверяет persisted counts, head/tail,
history, Have, изменение новой тысячи и историю [2,1]. Два маленьких физических
payload совместно используются логическими путями: это metadata capacity test,
а не миллион физических files/TB transfer. `--postgres` использует тот же
одноразовый Docker; `--output` сохраняет JSON с измерениями и памятью.

Финальный metadata прогон SQLite: **1000000 version + 1000000 checkout**, 6826
catalog pages до следующей правки; 1000 последовательных edit-чанков. Создание —
1567.27 с (26 мин 7 с), submit — 17.39 мс, list head/tail 1000 — 10.98/10.42 мс,
history — 8.44 мс, sync_next — 13.40 мс, sync_ack 1000 — 22.42 мс. Пик процесса
68.69 MiB; при росте 25k → 1M рабочий пик удерживался примерно в 64–67 MiB.
Большой прогон стартовал до последних оптимизаций DB ownership/checkout: его
edit timings — baseline, не замер этих оптимизаций. Следующая новая тысяча
существующих путей: edit 1679.65 мс, submit 15.47 мс; история [2,1] проверена.
Параллельно выполнялись другие изолированные проверки на том же компьютере.

Отдельный актуальный чекин **1000 различных физических файлов** по 512 bytes:
edit 920.28 мс + submit 28.19 мс = 948.47 мс от уже загруженных bytes. Descriptor/
upload/fsync/edit/submit целиком — 9471.32 мс (upload/fsync — 8040.45 мс).
Это SQLite, 500 KiB суммарно, Api.dispatch без клиентской сети и GUI; не TB/SLA.

File-project команды отвергают активный Classic start/finish/abort journal,
включая пустой: иначе metadata без Classic Undo-журнала переживала abort.
Публикация/отмена файлового changelist выполняется его submit/revert API.

TH/TS интерфейсы, million-file PostgreSQL/TB IO, merge/rebase/shelve, квоты/retention/GC
и production многопользовательская нагрузка не проверены/не реализованы этим блоком.


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

Завершён серверный блок 3 file_project: привязка depot к штатным repository aliases,
read-only/writable mappings из нескольких depot, исключения, выбор workspace,
Have по реальным ревизиям и chunked reconcile локального манифеста с Have/head.
Ветки фиксируют submitted snapshot родителя и разделяют immutable каталог/байты.
Cross-stream merge использует общую настоящую базу, учитывает удаления, конфликты
и происхождение integrated_from. Источник фиксируется на всё задание; target head
проверяется перед завершением и submit. Merge checkpoint публикуется только вместе
со всем changelist; rollback native callbacks не оставляет частично опубликованных
правок. Прямых SQL бизнес-операций нет, сохранены Search/SObject/Command, ACL и triggers.

После полного sync следующие полные sync сравнивают immutable корни и пропускают
неизменившиеся поддеревья. Запросы ограничены 1000 записями, mappings — 256 правилами;
инвентаризации всего workspace в памяти нет. Private blob directories находятся вне
публичных repository; дополнительные HTTP aliases также не открывают их. Rebinding
depot влияет на новые uploads, старые версии сохраняют физическую привязку.
Classic и workspace без mappings сохраняют прежний контракт. TH не изменялся.

Проверки: 49 тестов SQLite API/catalog (47 passed, 2 PostgreSQL-only skipped),
14 новых native PostgreSQL сценариев passed, включая отдельный HTTP server,
права на несколько depot, CAS выбора workspace, реальные bytes/history,
многочанковый merge, stale heads, rollback Have/index/merge и incremental sync.
Инструменты: tests/test_file_workspace.py и tools/file_project_checks.py --postgres;
временные процессы/контейнеры завершаются и проверяются после тестов.

Изолированный **синтетический** каталог/Have 1000000: branch 28,31 мс,
unchanged sync begin/next/ack 26,46/18,62/33,85 мс; один изменённый файл
27,80/21,80/38,95 мс. Peak 60,39 MiB. Это native Api.dispatch без сети и скачивания;
Have заранее подготовлен fixture, не миллион физических version/checkout записей.
Артефакт .test-tmp/file-workspace-million.json; tools/file_project_benchmark.py
--files 1000000 --checkin-files 0. Реальная передача TB и production SLA не измерены.

Контракт и примеры — EN/RU Help → Project creation. Пересекающиеся/overlay назначения
явно запрещены, merge только внутри depot; автоматического текстового merge нет.
Клиент передаёт размеры/SHA локальных файлов и подтверждает Have только после записи;
сервер не читает диск пользователя. Интерфейсы ТХ/ТС и большой transfer pipeline —
следующие блоки, этот этап завершает серверные операции.

Дополнительно прошли 26 Classic SQL/FileUndo/client-transactions/project-creation
сценариев (25 passed, 1 отдельный PostgreSQL-only skipped). Vue 0.112.49 собрана,
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

## File-project GUI: Handler and Stream

Project mode selects the interface: `file_project` opens the new workspace; Classic retains its queue and docks. Handler is the desktop working client (native operations, streaming SDK, disk reconciliation/journals). Stream is the paged browser viewer and server administrator, with no local filesystem transfer UI. Setup includes native workspace mappings; browser storage administration exposes quotas, retention and safe GC. ACL and trigger checks stay in the fixed native FileProjectCmd; active uploads cannot be submitted mid-stage and cancel/failure restores the original draft by root flip.

User documentation: EN/RU Help → Project creation; Handler Help → Perforce-like workspace. Tests: `test_file_workspace_ui`, `test_handler_file_workspace_ui` (installed Handler/PySide6), and `frontend/tests/file-workspace.mjs` (Microsoft Edge/Playwright). Fixtures own their HTTP/file-worker resources and fresh temporary projects. Physical million-file/TB GUI throughput, continuous local watching and automatic text merge are not implemented or measured here.


## 0.112.63 — authoritative managed Search tab reads

Handler selects a managed record read command inside its server-side query procedure from registered Search Type metadata, rather than relying on a cached client policy. Stale or missing policy metadata no longer sends administrator depot searches through guarded generic Search. Column filters, bounded pages, count flags and compressed/raw payloads retain their contracts; generic file-record guards and non-administrator denial remain in force. Handler only retries an unsupported optional keyword, not a 403 traceback containing `include_progress`.

Stream already routes equivalent Search/result/cell reads through the native managed command. Regression checks cover both clients: real local XML-RPC/HTTP with owned projects, all ten managed tables, stale/missing client metadata, filters, pagination, cross-project rejection and one-request non-admin denial. Classic server-procedure and result-organization tests pass. EN/RU Help is synchronized. Production services are not restarted. The existing Qt shutdown GC warning remains; this change does not modify QObject lifetimes.

## 0.112.62 — independent Perforce-like trees and configurable work views

Handler and Stream use a left Depot/Workspace tree selector and a separate right work-tab strip. Selecting or expanding a tree node never changes the active work tab or its changelist list. Files follows the selected tree by default; custom file sources and path filters remain independent. View opens/restores Files, Pending, Submitted, History, Shelved, Reverted, Conflicts and Transfers; existing editor commands stay in their operation menus.

Tabs have icons and close controls, can be added, renamed, moved and filtered from View, and persist per user/project. Handler additionally isolates stored layouts by server; browser storage is origin-scoped. Pending requests an explicit bounded state set including shelves without changing the legacy single-state API. Changelists retain unique project numbers, expandable file children, native shelving and copy-number commands.

Workspace browsing reuses the indexed Have catalog, mapping/owner/depot checks, root pinning and immediate-child cursors. Handler can browse its reconciled local cache with indexed subtree skips, including untracked/local state; Stream shows server-known Have rather than claiming browser filesystem inspection. Classic paths are unchanged. No production restart or million-file GUI benchmark is included.

Validation uses owned temporary projects: Chromium and native Qt exercise folder/changelist independence, checkout, shelving, conflicts, atomic submit, history, narrow geometry and custom-tab create/restore/close. Native Workspace child browsing checks mapped paths, page bounds, pinned roots and owner denial; indexed local browsing checks 1,100 descendant entries and literal `%` prefixes. Shared EN/RU labels are checked. Known PySide shutdown GC warnings remain; no unrelated broad theme-resource gate is claimed clean.

## 0.112.61 — metadata-driven Search tabs and complete schema presentation

Registered record classes declare native read commands, availability, read-only operations and project applicability. Both clients consume this metadata instead of filtering project Search Types by namespace. An empty managed-project sidebar shows the registered catalogue. Bounded administrator reads, table cells and result-items run through the native file command; generic file writes and immutable revision guards remain unchanged. Interface errors preserve their actual security reason.

Both schema views display coincident old nodes in a local grid without modifying the stored XML or dirtying the draft. Technical XML is indented while retaining custom elements and comments. Stream exposes flow, network and grid in the Canvas toolbar, matching Handler. Saving remains explicit.

Stream uses shared browser crypto IDs without randomUUID and attaches Task Manager's ResizeObserver after its deferred Teleport has mounted. These JavaScript failures have no Qt counterpart. Handler reads server-declared policies and retains Python IDs/native QML geometry. Tests use owned temporary projects; no production restart or user schema write is included.

Validation: native administrator result-items and table cells returned HTTP 200; managed reads retain ordinary-user denial, page bounds and generic file guards. Chromium exercised the ten registered types/nodes, XML, partial node movement and all three layouts with randomUUID removed, and checked browser errors. Handler XML-RPC page/table reads and QML schema/technical controls passed. The unrelated full UI theme-resource gate still detects an existing literal CSS colour; PySide shutdown garbage-collection warnings remain. Neither is hidden by the focused checks.

## 0.112.60 — file-project docks, object searches and administrator schema summaries

File projects retain ordinary object Search tabs. Their file workspace occupies
the native Commit Queue dock and can share a tab stack with Search or maximize
the working area. Handler resolves mode during cached project restoration and
controller startup. Stream hides Classic Queue at its actual teleported element
and routes all queue buttons by project mode.

SearchTypesCmd reads managed-table counts inside the authenticated native file
scope. Admin schema loading covers all ten file tables without enabling generic
access to those records or changing write constraints, regular ACLs and rollback.
The wider direct-read relaxation was rejected by automatic approval review and
was not applied. No production server restart or old release archive is included.

## 0.112.59 — native file-project depot and changelist trees

Handler and Stream show depot/stream/directories on the left and numbered,
expandable changelists with selectable files in the main area on the right.
Disclosure uses bounded load-more, compact icons and explicit state/owner.
FileProjectCmd.browse uses B+tree range seeks to skip descendants. Published
cursors retain a consistent tree; Refresh switches to the latest head. Changelist
numbers come from the native monotonic project table ID; UUID command identities
remain unchanged. Native status, move and unshelve accept project numbers such
as `#42` through the same owner/depot checks. No ACL bypass or direct business
SQL is added; Classic retains its interface.

Qt/Chromium checks exercise expansion/collapse, directory selection, changelist
files, paging, icon presence and narrow windows. Catalog checks cover 70000
descendants, adjacent file/directory names, deletion and Unicode path bounds.

## 0.112.58 — file-project selection stays on the native API

Handler skips Classic metadata/navigation/search restoration for file projects.
Stream also ignores retained Classic searches when opening or reloading a file
project. Depot/stream/workspace access remains in FileProjectCmd; Classic retains
its navigation and tabs. Tests cover cached/fresh Handler selection and browser
reload with a stale depot tab. EN/RU project help is synchronized.

XML-RPC and browser RPC retain source locations for SecurityException inside
authorized Python scripts; pre-execution refusals remain generic. Browser RPC
distinguishes permission_denied from authentication_failed to preserve a valid
session after an operation is rejected. Native ACL and rollback remain enforced.

## 0.112.57 — file-project delivery and recovery qualification

Native file-project capabilities expose whether `files` is configured. The shared
Handler/Stream SDK rejects new bulk uploads before server allocation when it is
disabled, preserving journals and completed-task retries. Saving Configuration
does not restart the server. Lost seal/Have replies are recovered with a new client
without duplicate publication. Qt fixture teardown destroys all owned engines and
clears their type registrations; warnings are not suppressed.

Installation, builtin `perforce_like` template, native ACL, recovery, backup and
release limits: [English](FILE_PROJECT_DELIVERY.en.md),
[Русский](FILE_PROJECT_DELIVERY.ru.md). The packaging command is
`python tools/file_project_delivery.py --handler PATH --output NEW_DIRECTORY`.
It builds the standard server wheel and a Handler source runtime, excludes saved
settings/tickets/databases/logs, and records SHA-256 inventory. It does not claim a
Windows EXE/Electron or production/manual acceptance.

The two-user HTTP scenario exposed temporary storage-lock contention being treated as a fatal upload error. File-mode guard failures now return marked HTTP 503 before domain mutation, SDK metadata retries are bounded, and workers retain queued/running tasks. Native ACL/hooks/checksum errors retain their original rollback behavior. A minimal Python/PySide Property-only program reproduces shutdown ResourceWarning; it remains an explicit runtime acceptance issue.

### File workspace lifecycle and Files inspector

The Files pane now includes Details, Checked Out By and bounded content Preview.
Handler owns local watching/Reconcile, read-only checkout handling and external
comparison; Stream provides the matching server inspection/admin views. Native
review, shelf replacement/history, ownership handoff, conflict comparison/undo,
paired rename resolution and per-file transfer inspection retain the existing
Command/Search/SObject rights, callbacks and publication rollback.

The full [three-stage checklist](FILE_WORKSPACE_UI_PLAN.md) retains all 124
requirements; 29/35 Stage 2 requirements are accepted. See the updated
[delivery notes](FILE_PROJECT_DELIVERY.en.md) and EN/RU Help for source deployment,
client/server restart, recovery and remaining qualification. This change does
not certify million-file/TB throughput, production PostgreSQL or packaged GUI
delivery. The recorded PySide6 shutdown warning remains open.

## File workspace batches and editing flow — 2026-10-13

Release 0.112.81 adds native server-owned pinned query/range mutation jobs with
whole-batch rollback, responsive cancellation and lost-COMMIT reconciliation.
Handler's blank Pending menu, checkout materialization, modified-file badges,
editor activation, local preparation/review and view close controls form the
editing flow. Stream keeps inspection/admin and equivalent remote menus.
Mappings use structured editors and native preview; cancelling setup restores
the active root. The complete 124-item checklist is retained; Stage 3 is 4/18
accepted. Fresh million-record catalog data and explicit physical/TB/SQLite
limitations are in FILE_PROJECT_DELIVERY.en.md / .ru.md and
benchmarks/file_project_scale_2026-10-13.json. Restart server/Handler after
updating their sources; no production service is restarted by this change.


## 0.112.82 — 2026-10-13

- Read current changelist metadata with the first native file page instead of rejecting expansion against an old UI revision. Keep pinned continuation pages, edit rights, trigger execution and mutation revision guards. Synchronize Handler and Stream inspection behavior and EN/RU Help.
- Handler 0.6.0.40 removes retained tab snapshots and duplicate tree lists from Qt bindings, routes navigation through its separate read worker and preserves independent Pending/Submitted views. Real pointer latency and native/browser folder regressions are recorded without claiming production transfer or whole-plan completion.


## 0.112.83 — 2026-10-13

- Record stopped downloads as server-side blocked tasks. Resume the same pinned selection and atomically replace a stopped task for another file/folder/revision in the same workspace/local root, preserving local edits, partial bytes and confirmed Have. Keep running/other-root downloads protected and retain native rights, triggers and rollback.
- Synchronize Handler 0.6.0.41, shared SDK behavior, Transfers inspection and EN/RU Help. Older abandoned running tasks may still require explicit cancellation; lost-connection recovery remains bounded by server reachability.


## 0.112.84 — 2026-10-13

- Synchronize local-drop context, Add confirmation terminology and EN/RU Help with Handler 0.6.0.42. Handler stages new local files through the native upload API, preserves nested workspace paths and uses a bounded themed confirmation dialog. Stream retains remote inspection/administration without accessing desktop filesystem bytes.

## 0.112.85 — 2026-10-13

- Keep native mouse release clicks on shared buttons, menus and tabs when the pointer drifts slightly outside their edge, matching Handler's drag threshold. Retain native disabled, touch/keyboard activation and tab dragging without synthesizing duplicate clicks.
- Remove focus outlines and the dock title's accidental vertical scrollbar. Keep horizontal tab scrolling, use hand cursors on dock grips, and move floating panels by the free title area while the grip owns docking. Verify saved Commit Queue visibility remains per Search tab, matching Handler.

## 0.112.86 — 2026-10-13

- Match NotificationsView's three toolbar rows and full-width filters instead of wrapping the description and filters onto the same line. Keep the notification panel's border, padding and spacing on narrow screens; segmented labels stay on one line with ellipsis, matching Handler.
- Verify current QML content geometry, EN/RU desktop, 320/360px, nonmodal workspace access, keyboard filters and history clearing with isolated browser fixtures.

## 0.112.87 — 2026-10-13

- Open Saved Searches as a bounded, rounded work dialog instead of inheriting the fullscreen Configuration shell. Keep rounded frames on restored configuration editors, while retaining maximize, title dragging, resizing, mobile layout and unsaved-filter guards.
- Remove remaining component and descendant focus-outline rules, including shared title bars and result surfaces. Keep keyboard actions and selected-row backgrounds; focused unselected file rows use background highlighting.

## 0.112.88 — 2026-10-13

- Rename Configuration's main Cancel action to Close in Stream and Handler 0.6.0.43, preserving unsaved-setting confirmation. Synchronize EN/RU Help and existing UI selectors.
- Retain rounded desktop corners in maximized windows. Preserve shared window controls when a Vue-rendered title bar removes their host during an update; keep their geometry and restore state. Detect fullscreen layout without counting opening-animation scale.

## 0.112.89 — 2026-10-13

- Center shared checkbox marks inside the full indicator instead of its top-left corner. Match Handler's selected-text color, regular/compact icon sizes and indicator corners, including Messages notification controls.
- Verify five icon packs across three light/dark themes, mixed/disabled states and native label, keyboard and touch activation; capture the current Handler checkbox as reference.

## 0.112.90 — 2026-10-13

- Match current Handler's Messages popup types: members, files, conversation search and pin history open beside their controls; creation, membership editing, rename and edit history remain centered nonmodal popups. Remove the added window frames, retain genuine modal confirmations/message editing and nonmodal forwarding.
- Replace the stretched inline message search with a compact popup that applies on Enter/Search and clears explicitly. Keep focus, outside/Escape dismissal, parent closing and captured editor context.
- Prevent generic menu styles from shrinking emoji cells: desktop uses an eight-column 40px grid with 26px glyphs; touch retains 44px cells and 32px glyphs. Verify real Messages in an isolated browser against fresh QML popup/emoji captures.

## 0.112.91 — 2026-10-13

- Retain rendered conversation timelines, images, previews and scroll in the existing twelve-chat LRU, matching Handler's cached message surfaces. Switching to an unchanged cached chat does not reload history; changed summaries/events refresh the same visible timeline in the background.
- Keep hidden bubble/image/grid geometry and defer media resize writes beyond ResizeObserver's layout pass. Preserve reading position during refresh, separate search results from cached history, ignore stale responses and clear retained content on logout or loss of conversation access.
- Verify DOM/image/blob identity and scroll across twelve animation frames with delayed history responses, fast repeated switches, pending cold-chat responses, search/clear, LRU eviction and logout. Existing integration selectors target the active timeline.

## 0.112.92 — 2026-10-13

- Add Administration → Raw database in Stream and Handler 0.6.0.44: list physical tables in system/registered project databases, edit JSON cell values, create rows with defaults, stage full-row deletion, export the entire saved table to CSV and confirm DROP TABLE by its full name.
- Require administrator access server-side, escape identifiers and values, check row revisions under a table lock and roll back failed batches. Preserve composite keys and physical row identities; redact secret fields and nested JSON credentials. Generated/binary/secret cells remain read-only. Raw SQL bypasses SObject validation, object triggers and undo history; CSV is limited to 50000 rows.
- Validate SQLite CRUD, conflicts, rollback, row identity and denials on private data; exercise the built browser UI and real Handler QML. PostgreSQL has a dialect implementation but its real connection is not validated in this change. Shared UI resource checks still report unrelated QuickFilterOptions ALL and changelist translation failures.


## 0.112.93 — 2026-10-13

- Synchronize complete-selection menu restrictions, native depot write hints and clear drag/drop target captions with Handler 0.6.0.45. Keep server permissions, revision/lock checks, native triggers and transactional rollback authoritative.
- Add nonempty-changelist move/revert choices and a full-change move using the existing pinned server selection and files task. Ignore visible name/path/status filters; preserve local files and require an explicit owned target in the same stream.
- Support current-project changelist links and shelf-to-target Unshelve preview in both clients. Preserve source shelf views and show the pending target; cancel preview before integration changes. Correct checkbox selection and uploaded-versus-modified-after-upload badges. Synchronize EN/RU Help and the original 124-item acceptance checklist; Classic remains separate.

## 0.112.94 — 2026-10-13

- Replace the Raw database rounded cell fields with a compact continuous table in Stream and Handler. Shared square editors remain transparent until focused; preserve keyboard/touch editing, drafts and all server operations.

## 0.112.95 — 2026-10-13

- Persist native download pauses for insufficient client disk space, including required/available byte counts. Validate before updating task state; preserve owner/depot permissions, acknowledgment revisions, triggers, Have and resumable partial bytes. Clear obsolete space information on resume.
- Synchronize the SDK with Handler 0.6.0.47: validate absolute download roots and check the current bounded manifest page before requesting its payload. A shortage is a recoverable bottom-Log warning, not a publication or local-data loss.
- Close the workspace-switching/root-space-mapping checklist block in Handler and the shared API. Browser scope is inspection and administration; no desktop editing UI is added. Update EN/RU Help and operational documentation.

## 0.112.96 — 2026-10-13

- Verify all four raw table cell corners on idle, focused, new and deleted cells; support an optional browser screenshot for visual inspection. Fresh browser and Handler QML rendering use square cells. Document interface reload after updates.

## 0.112.97 — 2026-10-13

- Apply Raw database square-cell styling through the native forwarded CSS class instead of a new shared-field Boolean prop. A component already loaded before the prop was added could ignore it and retain rounded fields when opening a newer raw editor chunk. Keep idle cells transparent and active cells square; disable native input appearance. Reproduce the failure with the pre-prop field component, then verify the fix across all three themes in light/dark mode. Handler already uses square QML cells and requires no corresponding code change.

## 0.112.98 — 2026-10-13

- Add the bilingual Table View widget database to shared Help: purpose groups, source-review and migration stages, current limitations, ten native XML examples and real Vue component captures. Link it from Overview and retain CSV/JSON/HTML audit exports.
- Exclude the explicit SnapshotServerElementWdg stub from migration. Do not reject working inherited aliases merely because their body contains pass; retain source evidence and leave unreviewed widgets awaiting a reproducible legacy scenario.
- Render TaskCompletionWdg with the current TH completion bar: 18px track, 10px margins, bounded percentage and accessible text/value. Compare fresh native QML and browser geometry, colors and typography on the same fixture values. Preserve native task calculation and permissions; grouped/footer totals remain unavailable.
- Verify native XML/descriptor examples, ten real presenters, captured references, error/clamping states, actions, bilingual Help and 320px without live database requests. Remaining legacy widgets and full table parity are not claimed.

## 0.112.99 — 2026-10-13

- Align Raw database with Handler 0.6.0.49: identical grid dimensions, square editors, filters, toolbar and navigation order, row actions, direct save, inline discard/drop confirmation and pagination. Retain selectable read-only values, finite JSON validation and recovery after failed writes. Synchronize EN/RU Help and record the ongoing TH/TS interface parity requirement.
- Compare real QML and browser rendering on the same private fixture, theme, language and window size; verify responsive layouts and editing/CSV/drop flows without production data. Native file selection and browser downloads retain their platform behavior.

### 0.112.100 — file workspace completion qualification

Handler 0.6.0.50 provides the working desktop. Stream now routes file projects to inspection and storage administration; file checkout/edit/shelve/submit remain in Handler. The native server adds paged real branch/merge graph provenance, bounded reconciliation counts, revoked Have-access checks and file-level errors. Managed records skip only absent trigger lookups; custom callbacks remain sequential and every matching handler still runs per file. Interrupted byte writers return a marked retryable busy response without taking over the lease.

The complete 124-requirement checklist is retained in `FILE_WORKSPACE_UI_PLAN.md`. Fresh-file, HTTP, million-catalog, desktop and native database evidence is recorded separately from physical TB and native external-input acceptance. No production server was restarted.

## 0.112.101 — 2026-10-13

- Qualify full Raw database pages and second-page saves in the real browser on a private 75-row/12-column fixture. Keep existing Stream operations and synchronize EN/RU Help with Handler 0.6.0.51.
- Add a reproducible real-QML raw-page construction profile. Handler now creates visible row editors through ListView instead of every cell in the page; offscreen drafts, sticky headings and square grid geometry remain covered by native checks. Server procedures are unchanged.

## 0.112.102 — 2026-10-13

- Synchronize Raw database EN/RU Help with Handler 0.6.0.52: native shared TextField creates its text context menu on demand instead of eagerly for every visible cell. Preserve the Stream grid and operations; browser behavior already creates native menus on demand.
- Extend the QML profile to accept a locally saved raw load response and count instantiated menus. Qualify the same 50-row/9-column real page across native RPC and Stream JSON: responses agree; RPC takes about 54ms and JSON 41ms. Native UI presentation drops from about 1.9s to 0.16s on that data after lazy menus. These are local measurements, not a network latency guarantee.


## 0.112.103 — 2026-10-13

- Build the used Table View checklist from all 449 shipped/template/saved widget configs, including definitions, dynamic and embedded class references. Preserve exact locations/options, explicit exclusions and unresolved references. Read local databases mode=ro; do not modify user configurations.
- Implement the Array/XML/JSON/SnapshotVersion value block and synchronize Handler typed transport/QML. Preserve raw SDK/CSV values, decode native compressed XML for safe display, retain parse diagnostics, sorted JSON and version padding, and correct NULL array/version errors.
- Compare source display bodies and original/native Handler transport, capture four paired current-QML/Vue fixtures, and verify escaping, empty/error values, height/scroll, EN/RU Help and 320px. Add fourteen checked XML examples, Help checklist and source hashes. XML/JSON general inline editing and remaining used widgets remain open.

## 0.112.104 — 2026-10-13

- Qualify Raw database heading/first-row separation on short and full browser pages. Stream already reserves header space; retain its table behavior and synchronize EN/RU Help with Handler 0.6.0.55. Handler now reserves 40px before the first asynchronous page arrives instead of growing a zero-height ListView header after rows exist. Check fresh creation, sticky scroll/return and native Windows at 150% scale.

## 0.112.106 — 2026-10-14

- Fix XML-RPC Fault 500 after successful Raw database queries containing integer cells or row keys beyond signed 32-bit range. A response-local marshaller emits int/i8/biginteger tags while retaining standard encoding for other types and leaving request marshalling, fault privacy and authentication unchanged. Preserve the existing raw JavaScript precision guard.
- Reproduce the actual overflow through HTTP/XML-RPC, then compare RAW responses with JSON and save a large value through the unchanged Handler SDK. Verify signed boundaries, nested values, ordinary packets, script diagnostics and malformed XML. Synchronize EN/RU Help with Handler 0.6.0.58. Restart the Stream server to load the transport fix; writes that reported a serialization error may already have committed.

## 0.112.107 — 2026-10-14

- Add bounded native `read_batch`, `read_page` and `workspace_snapshot` for file projects. Reuse read records within one request, keep current authorization, batch checkout holders and avoid repeated selected/expanded file pages and task reads. Stream inspection startup uses one metadata batch; Handler's full desktop workflow uses snapshots. Classic check-in remains separate.
- Filter changelist state before pagination, order recent numbered changes first and retain continuation while filling filtered pages. Update the owner index on handoff and support idempotent Create request ids through normal SObject/Command transactions. Keep empty changes for explicit review/deletion.
- Owned before-sequence replay versus snapshot: 16→1 API calls, 521→58 SELECTs including security/schema reads, 175.1→23.2ms without network delay. Keep bounded pages for large depots and document that one HTTP request still contains multiple necessary database reads. Skip catalog reloads after transfer cancellation and fetch the desktop inspector only while Files is visible.
- Synchronize desktop/server Help and verify browser inspection without adding desktop file actions. Fix an invalid inline TaskCell pointer expression encountered by the production Vue build, preserving its pointer guard behavior.

## 0.112.108 — 2026-10-14

- Reuse schema definitions and project routes within the existing native request cache across qualified/base Search Type forms. Keep structural DML/SQL-trigger/rollback invalidation and current permissions. Refresh's owned paired replay drops from 58 to 35 SELECTs; no rights or schema checks are removed.
- Read file Details/Preview together in the shared browser/desktop inspector and batch active changelist list/files. Add native bounded file_entries for Reconcile rename validation. Read history versions in indexed segments and related changes in batches; follow the authorized previous chain, including forks/moves, and verify each submitted root. Thirty-version history falls from 113 to 56 SELECTs, with version/change reads falling from 30+30 to 2+1.
- Synchronize Handler/Stream SDK polling: unchanged progress backs off to two seconds, changed progress resets the interval, and status no longer causes a desktop workspace snapshot. An owned deterministic thirty-second wait uses 20 polls versus 121; completion may appear one interval later. Preserve errors, cancellation, timeout and native atomic mutation semantics. Fifty rename sources use one bounded read instead of fifty.
- Synchronize EN/RU Help with Handler 0.6.0.60 and qualify native HTTP, real Qt and browser preview. Fix the native trigger guard when called without an active transaction, discovered by registry parity checks; keep atomic transaction restrictions. Correct the historical Force test to explicitly unlock the intentionally read-only local mapping before simulating a user's local edit.

## 0.112.109 — 2026-10-14

- Port the current adapted Handler Table View registry: 45 names / 21 classes, including details, native check-in target, Explorer path, files, metadata and guarded Delete cells. Preserve stock TaskElementCbk selection and Handler display parameters without executing legacy HTML/JS. Explicitly retain the historical ExploreElementWdg alias.
- Match Handler table geometry and delegates, rounded header, compact process/task cards, relative dates, text elision and selection. Add virtualized rows, bounded 500-object reads, header context actions, width/reorder/hide/row height, auto-fit, grouping and saved table presets on native WidgetConfig revisions. Preserve cells while refreshing.
- Connect native single/batch inline editors through edit/edit_definition and action.column, including aliased category SelectWdg, checkbox and compound TimeAction. Check all revisions before native EditCmd writes, retain unknown-result guards, protected fields and rollback. Task status/user editors occupy the original cell; date edits use the shared calendar, staged task edits retain one owner.
- Match the existing Columns Editor catalog/Wizard/XML composition, splitters, column focus and width controls; keep unknown XML/comments and native revision-checked writes. Fix the shared optional-label TextField render failure. Synchronize EN/RU Help, examples, active legacy checklist and fresh paired QML/Vue captures under reports/table-view-2026-10-14.
- Handler 0.6.0.61 fixes first-column Wizard initialization and first-character inline commits found during comparison. Real Qt key events and offline QML smoke pass. The browser uses server upload and copied native paths; local desktop folder/DCC/move/link operations remain outside the browser port. Font rasterization, physical phones, other DPI and other database engines are not claimed identical.

- Final native browser regression also covers preserved task previews during inline edits, delayed-close cancellation after pinning, recovery from an unknown batch-save response, live note/task updates with local drafts retained, bounded append reads, and Inspector reading-position/draft restoration. Keep hidden DOM nodes from overwriting remembered scroll positions. Old browser tests now target current dock roles, pickers, header menus and large-row dates rather than removed modal/pencil controls.

- Check-in table actions open the existing Drop Plate dock on desktop, preserving the target project/process/context; the phone keeps its upload form. Target row operations derive project from the native target key. Retain explicit Drop Plate contexts and use the shared checkbox import with exact filename case.


## 0.112.110 — 2026-10-14

- Reuse persisted tickets in file-task threads and the queue executor, scoped by store and submitting login. Recheck expiry, account ownership/retirement and current permissions on every Batch; retain ordinary Batch and transport contracts. Three real file jobs keep a constant ticket count; consecutive non-admin check-ins reuse a credential and fail after ACL revocation.
- Add eight non-unique journal indexes through the existing SQLite/PostgreSQL upgrade. Qualify SQLite upgrade idempotency, unchanged duplicate markers and indexed plans for object/field conflicts, activity cursors, script/object history, editor revisions, journal joins and code lookup. Apply only those eight indexes to the live SQLite system database in 0.83 seconds; ticket/journal/object-log/change row counts remain unchanged.
- Record the expired-ticket dry-run, unfinished-transaction/upload protection and bounded cleanup plan in UI_ARCHITECTURE.md. Preserve sobject_log: history and editors depend on it. Its own change_timestamp markers are candidates for a later reduction; generic update/replay paths and dynamic clients must be qualified first. Read-only inspection covers 210 saved definitions. Synchronize maintenance Help with Handler 0.6.0.62.
- Validation: 38 security, queue/check-in, Raw database, client transaction and index checks, three real file-worker/permission/transfer checks and three activity/script-history checks pass; the Stream production build and paired EN/RU maintenance Help checks also pass. No cleanup or journal deletion is enabled. Server restart is required for ticket reuse; SQLite indexes already apply. Live PostgreSQL was not run because Docker Desktop's engine is unavailable.


## 0.112.111 — 2026-10-14

- Add nine measured non-unique indexes for user preferences, global-search objects, parent publications, repository paths, directed links and group membership. Existing schema owners supply the indexes to SQLite/PostgreSQL upgrades. Apply them to the live SQLite system database in 0.326 seconds without changing records. On private 50000-row tables, nine lookup shapes fall from 1.9–5.5ms to 0.057–0.066ms with equal results. Raw 6000-row index-write overhead is about 2.7ms; these are SQL lookup measurements, not whole-request gains.
- Reuse SearchKey parsing within the current RequestContext, capped at 256 entries with copy-on-return. Preserve malformed inputs, nested codes, custom string behavior and fresh account/ACL checks. Alternating full-dispatch A/B on 10000 objects improves median 112.054ms to 104.322ms with identical output; tiny pages have no material gain. Preserve five native benchmark result hashes and record reproducible timing/profile artifacts under benchmarks/engine_micro_2026-10-14.
- 80 targeted key, lookup, links, snapshots, permissions, queue/check-in and transaction checks pass. Repeat the SDK transport check with network access after a sandbox-only startup failure. Synchronize maintenance Help with Handler 0.6.0.63, including service ticket replacement on expiry/revocation for ordinary accounts. Updated parsing needs a server restart; local SQLite indexes already apply. No ticket cleanup/journal deletion is enabled; live PostgreSQL is not qualified.

## 0.112.112 — 2026-10-14

- Synchronize EN/RU file-workspace Help with Handler 0.6.0.64: shared MD3 confirmations use a short heading, wrapping explanation and compact named actions, with Cancel/Escape and one acceptance dispatch. Qualify English/Russian narrow/wide light/dark desktop layouts. Stream keeps its agreed read-only inspection/admin scope; no browser changelist mutation UI or file API behavior is changed.

## 0.112.113 — 2026-10-14

- Synchronize EN/RU file-workspace Help with Handler 0.6.0.65: local active-workspace drops add files quietly, outside/mixed Explorer roots receive one OK notice before any native request, and external copying is removed. Retain mappings, rights and edit revisions, recursive bounded worker discovery and internal Depot/pending/shelf flow. Rejecting a drop keeps existing recovery and connection state. Stream keeps its agreed inspection/admin interface; browser filesystem mutations are not added. Qualify native Qt/HTTP drops, path boundaries and localized notice layouts.

## 0.112.114 — 2026-10-14

- Add native revert_plan/revert_files for bounded owned workspace selections, normal permissions and one atomic Command across changes. Keep native remove_files hooks, revision validation, rename partners, receipt replay and storage/GC fencing. Whole-change revert now checks its edit revision and active operations.
- Handler 0.6.0.66 exposes direct file Revert and a shared-control options dialog for files/groups/changelists. Delete files not in depot defaults off; when enabled, the desktop moves eligible new local files to Trash only after confirmed native server success, rechecking current Head, other opens, mappings and fingerprints. Tracked and rename-lineage files are preserved, expected cleanup failures retain bytes with a warning. Large cleanup plans use disk-backed 1000-file pages. Stream's browser remains inspection/admin only; no filesystem mutation UI is added.
- Synchronize EN/RU Help and qualify native HTTP, atomic trigger rollback without local deletion, stale/foreign requests, idempotent replay, changed/newly published files, 1003 paths and actual Qt menus/dialogs in localized narrow/wide light/dark layouts. Reload Stream and Handler together for the new API.

## 0.112.115 — 2026-10-14

- Synchronize the shared file SDK with Handler 0.6.0.67: bounded metadata-only local checkout/comparison, changes-only Reconcile results, review without upload, and upload only on confirmed Submit/Shelve in this workflow. Verify uploaded hashes against the reviewed snapshot and retain current local fingerprints; preserve native permissions, transactions and recovery journals.
- Handler following Files/History views now respond to tree file selection and retain independent fixed/pinned tabs. Changelist/shelf target dialogs are centered, modal, movable and use shared action controls. Stream retains browser inspection/admin only; synchronize EN/RU Help without adding a browser desktop-files workflow.
- Qualify fresh 1003-file metadata-only registration, selective shelving, submit, unchanged/modified local copies, no-byte cancelled review, changed-during-upload rejection, explicit recovery, native Revert regression checks and real localized Qt interaction/layout. These checks do not certify million-file/TB throughput or the production workspace.

## 0.112.116 — 2026-10-14

- Extend the existing native `delete_change` command with a bounded explicit batch of changelist codes/edit revisions. Reuse owner/depot authorization, active-operation guards, revision receipts and native triggers; the enclosing transaction rolls back the entire batch on failure. Empty pending changelists and owned shelves retain existing retirement/GC semantics, with no local filesystem mutation.
- Handler 0.6.0.68 exposes multiselect deletion with a pinned shared confirmation and Delete-key support. Qualify native rollback/retry/permissions and real EN/RU Qt interaction at narrow/wide sizes. Synchronize user Help; no browser desktop-file workflow is added.

## 0.112.117 — 2026-10-14

- Index schema connection lookups within the existing request-local relationship cache; retain native XML/DDL invalidation, explicit uncached reads, wildcard/path/type priority and inherited resolution. Reuse the existing TEL object cache once per batch instead of repeatedly serializing all roots for every result. These shared engine changes serve both Handler and Stream and introduce no vendor-specific SQL or permission caching.
- On an owned SQLite fixture, authenticated native RPC discovery of 1000 roots/children/leaves/snapshots/files improves from 370.349 to 86.361 ms; TEL field extraction from 166.319 to 20.660 ms; 1000 inherited lookups from 134.864 to 13.066 ms. Responses and SQL counts match. Preserve measurements/profiles and the reproducible private probe; do not equate this workload with a full desktop sync or transfer throughput.
- Qualify 106 executed schema/TEL/link/file/SDK/rollback checks; six PostgreSQL checks remain skipped because the service is unavailable. Synchronize EN/RU engine maintenance Help with Handler. Restart server workers to load this fix.

## 0.112.118 — 2026-10-14

- Add native Submit selection/unchanged/reopen/conflict-guard options. Publish the selected files and any remaining/reopened pending change in the same normal Command transaction, preserving rights, triggers and rollback. Stream catalogs in bounded chunks instead of materializing the full manifest.
- Add restricted changelist metadata and existing Task Manager task links. Enforce native task field/process/status permissions; apply requested statuses through a separate native task command after successful file publication, with revision checks and safe retries. A failed task update does not undo already published files.
- Support Handler 0.6.0.71's dedicated Submit window, metadata-only Save/Apply, selected-byte uploads and separate shelf inspection. Synchronize the shared SDK and EN/RU Help without adding a browser file-editing workflow. Qualify native, HTTP and real Qt behavior; restart Stream and Handler together to load the new contract.

## 0.112.119 — 2026-10-14

- Save only modified RAW rows/cells, new rows and explicit deletions in both Stream and Handler. Background updates to untouched displayed records no longer cause false save conflicts. Retain full row revision checks for edited/deleted records, atomic rollback, schema checks, permissions, JSON/default handling and uncertain-write recovery.
- Qualify eight backend checks, twelve real QML checks, native Handler-source XML-RPC and Stream JSON transport (two cases), and actual Vue Save input/payload/conflict/delete/insert flows. The new QML regression fails on the old method. Synchronize EN/RU Help; restart Handler and refresh Stream. No production writes or live PostgreSQL qualification.

## 0.112.120 — 2026-10-14

- Add one bounded native changelist inspection command for Handler's View changelist window: metadata, files, visible related shelves and permitted Task Manager links. Enforce existing metadata rights before reading contents and pin subsequent file pages to their edit revision. Reuse native Search and shelf inspection without writes or schema changes.
- Support Handler 0.6.0.73's separate Files, Shelved Files and Tasks tables, explicit Edit and pinned window identity. Qualify 13 native, HTTP and real Qt checks, including paging, restricted metadata, description saving and Submit regressions. Synchronize EN/RU Help; the browser remains inspection/admin only. Restart Stream and Handler; live PostgreSQL and production data remain unqualified.


## 0.112.121 — 2026-10-14

- Fix table task hover previews: one horizontal scroller, full-height cards, exact Handler padding/width and reserved scrollbar space. Eliminate nested scrolling and CSS load-order-dependent card spacing; match current native popup surface/radius. Four tasks fit at 456 × 68 without either scrollbar.
- Qualify fresh current Handler QML and Vue paired dark/light captures, selected-row previews, Russian labels, pixel scales 125/150%, row heights 58/84, narrow 320px scrolling and last-card actions. Synchronize EN/RU Table View Help. The production Chromium/native-server regression also passes status/assignee/date saves, preview pin/dismiss, draft retention and live updates. Refresh Stream to load the frontend fix; no backend or user records change.

## 0.112.122 — 2026-10-14

- Support Handler's Revert unchanged files with bounded, owner/revision-checked native selections of files matching their checkout bases. Reuse the existing bulk removal worker, preserving native rights, triggers and atomic rollback across more than 1000 matches. No new byte upload or local file deletion is involved.
- Synchronize the SDK comparison, cancellation and disk-backed candidates with Handler 0.6.0.74 and EN/RU Help. Qualify 1003-file late-trigger rollback, mixed changes, stale revisions, permission rejection, cancellation/local changes during comparison, actual HTTP Handler dispatch and Qt menu activation; normal Revert checks remain passing. Restart both applications. Browser file editing remains out of scope; live PostgreSQL and physical million-file/terabyte acceptance remain unqualified.

## 0.112.123 — 2026-10-14

- Include authorized workspace metadata in the existing bounded file-history response without per-row queries. Restricted changelists hide this metadata from other readers; native file permissions and published-version lineage remain unchanged.
- Support Handler 0.6.0.75's tabular History with lower Details/Integrations/lazy Preview, persisted splitter and explicit 1000-revision truncation notice. Qualify real Qt themes/languages/sizes, selection/preview, native privacy, merge lineage and query-count regression checks. Synchronize EN/RU Help; browser file editing remains out of scope. Restart Stream and Handler. Labels, older-history pagination and live PostgreSQL qualification remain unavailable/unverified.


## 0.112.124 — 2026-10-14

- Display the localized Select status hint for an unset task status in the shared task field editor, matching Handler. Disable the hint instead of offering a blank selectable item; keep configured status values and native validation. Table, inspector and task workspace callers share the fix.
- Qualify actual Vue EN/RU labels, selected empty value, disabled hint and no task draft during language changes. Update paired Table View Help and rebuild the frontend. The focused browser scenario also selects a real status and checks the staged value/save request. The broader native-server Inspector regression is not qualified in this run: two attempts stop before the table-field checks, at related-task navigation and status-history waits. Refresh Stream; no backend restart or data migration is needed.

## 0.112.125 — 2026-10-14

- Let native read_page and workspace_snapshot return immediate folder-file pages through the existing authorized catalog/Have browse paths, preserving cursors and skipping descendant ranges. Handler 0.6.0.76 keeps siblings visible when selecting a file, reuses a shared Files/History inspector and avoids a second file read on refresh.
- Apply restricted-changelist description privacy consistently to file_info as well as history. Qualify bounded sibling paging, one-request refresh, native permissions and actual HTTP/Qt selection/preview in EN/RU light/dark layouts. Synchronize Help; browser file editing remains out of scope. Restart Stream and Handler. Production PostgreSQL and physical million-file/terabyte acceptance were not run.

## 0.112.126 — 2026-10-14

- Replace RAW inline editing with a separate cell editor in Handler and Stream. Display ordinary text without JSON wrapping; convert values by physical column type, retain exact large integers/decimals and JSON text, and provide explicit Value/NULL/new-row Database default modes. Apply stages the cell; Cancel/Escape dismiss it; table Save retains sparse atomic conflict-checked writes. Protected cells open a read-only viewer.
- Reuse the native WindowHost/FloatingWindow and shared browser window controls, multiline fields and mode selectors. Qualify fourteen real QML checks, actual Vue input/keyboard/save/conflict flows, three parser/SQLite scalar-round-trip tests and 39 shared Python/JavaScript conversion cases. Compare identical values in EN/RU, narrow/wide, light/dark layouts; field/selector dimensions match in eight cases. Synchronize Help and translations. Server procedures are unchanged; restart Handler and refresh Stream. Live PostgreSQL and higher-DPI native Windows qualification remain unverified for this change.

## 0.112.127 — 2026-10-14

- Add native stream specification updates and validated real mainline/development/release creation for Handler 0.6.0.78. Preserve published roots and original branch lineage when changing Parent; serialize depot topology edits, check settings revisions and owner locks, and retain native authorization/triggers/rollback. Graph paging notices spec changes and distinguishes reparenting from original branch provenance.
- Support Handler's shared stream editor, hierarchy and graph entry points with bounded read batches; synchronize EN/RU Help. Virtual/task/sparse streams, inherited stream views and automatic merge/copy policies remain unsupported and are explicitly rejected or identified, rather than simulated as independent copies. Browser file-workflow editing remains out of scope. Restart Stream and Handler; production PostgreSQL qualification was not run.

## 0.112.128 — 2026-10-14

- Fix Handler 0.6.0.79 RAW heading stacking: overlay headings now render above the default ListView delegate level, covering row text, hover surfaces and delete actions during scrolling. Preserve the existing opaque theme surface, grid dimensions and virtualization. The corresponding Stream heading already behaves correctly.
- Reproduce the native failure before the one-line fix and qualify sixteen rendered header comparisons in each client on identical fifty-row data, dark/light themes, narrow/wide windows and vertical/horizontal scrolling. All fourteen native RAW checks and the existing real Vue cell/save flows pass. Synchronize EN/RU Help. Restart Handler and refresh Stream; production Windows display scaling was not tested.

## 0.112.129 — 2026-10-14

- Synchronize Handler 0.6.0.80 file-workspace toolbar Help and real QML regression coverage: align tab/button centers and reserve the scrollbar strip only on overflow. Browser inspection has no equivalent desktop toolbar; server and browser behavior are unchanged.

## 0.112.130 — 2026-10-14

- Synchronize Handler 0.6.0.81 SSE recovery and diagnostic Help. Handler reconnects after EOF/interrupted responses and records failures with default ERROR logging, endpoint/status/network details and no request ticket. Browser SSE already handles EOF as transient; server behavior is unchanged. Qualify the native Handler/Stream integration and 33 Handler transport/service checks.

## 0.112.134 — 2026-10-14

- [x] Persist Command file intents before IO, including physical undo/redo; recover aborted owners and preserve committed effects using evidence written inside each participating DB transaction. Retain backups and reject repository writes when a commit is partial or unavailable; keep administrator reads available. Resolved evidence is cleaned automatically. Per-operation fsync adds durability cost for small Classic files; the separate bulk-transfer path retains its bounded batch IO.
- [x] Fix Windows sharing for notification/feed/client readers. Retain failed committed publications for retries, preserve dirty feeds until publication succeeds, serialize per-channel publishers and log watcher failures.
- [x] Apply `single=True` in SQL and project generic dictionary columns with required identity/retirement fields. Preserve custom/local object contracts; applying the supplied offset to a single read is an intentional source bug fix. Isolated 500-row probe: 500 → 1 materialized rows, 16.33 → 0.22 MiB peak Python memory for the same 77-byte response.
- [x] Reuse file identity checks only within the current transaction, invalidating native account/group/session changes and keeping path/parent checks. Isolated 100-file probe: 426 → 33 SQL statements, 402 → 4 login checks. No blanket file-throughput improvement is claimed.
- [x] Replace GC restarts with a root write barrier, bounded multi-level marking and resumed sweep. Capture late native page callbacks, retain newly queued pages, merge nested reservations without losing quota accounting and count confirmed purges idempotently. GC completes during continuous real submits and protects history/shelves/Have/active transfers.
- [x] Review and refresh 11 current Handler reference hashes and the RPC inventory; the legacy hash/API signature gate passes. Qualify 188 related engine tests, 76 final changed-path tests, 125 Handler controller/QML contract checks and 11 real isolated PostgreSQL 18.6 tests plus four crash checkpoints. SQLite skips two vendor-specific races; those pass in PostgreSQL. Test servers/clusters are stopped. Full API/GUI parity, soak/power-loss and the deferred physical terabyte run are not claimed.
- Restart TACTIC Stream manually to load a consistent worker generation. Recovery evidence is internal and provisioned transactionally by native Sql on first file use; no project search types or application models are added. Do not delete unresolved `temp/file-transactions` journals or their `temp/undo` payloads to bypass recovery.

## 0.112.135 — 2026-10-14

- Reuse request-owned independent identity readers when opening native Sql connections; recheck account activity and groups each time, avoid the duplicate active-account query, end each PostgreSQL read transaction and close readers on request exit/failure. No permissions or connections are cached between requests.
- Avoid empty metadata read scopes when another Search Type representation resolves entirely from the existing request cache. Preserve native metadata invalidation, project/resource selection and read restrictions.
- Build ordinary generic query keys with native batch SearchKey. Preserve code/id fallback, project identity, projected columns, custom key overrides, distinct and local SObjects; XML-RPC result bytes match the previous method on the same private data. No client-side implementation change is required for Handler or Stream. Synchronize EN/RU Help and the source adaptation ledger.
- Compare saved previous methods with current methods on the same private 10,000-row fixture, alternating before/after over 40 samples per size; these are full `Api.dispatch` medians, including authentication and Python-literal output, without network/HTTP/client rendering. SQLite 1/1,000/10,000 rows: 9.219/15.267/70.733 → 8.079/12.420/54.763 ms; connections 6 → 4 and SQL statements 29 → 27. Actual isolated PostgreSQL 18.6: 261.567/272.354/311.392 → 246.843/245.980/272.814 ms; connections 6 → 5 and SQL statements including read-scope commands 100 → 93. Results describe these fixtures, not production latency or bulk-transfer throughput.
- Qualify 140 related regression tests, then repeat 53 security/metadata tests and 52 final metadata/file-project tests; SQLite skips two PostgreSQL-only races. Six real PostgreSQL file-project checks pass, plus fresh grant/revocation/retirement/cleanup checks on both vendors. All owned test servers/clusters are stopped. Restart TACTIC Stream manually; production load, power-loss and the deferred physical terabyte run were not tested.

## 0.112.138 — 2026-10-14

- Synchronize Handler 0.6.0.88 compound searches: replace per-note SObject loading for parent/process/task-branch counters with native grouped counts. Preserve privacy, code/id parents, previous retirement behavior and custom Note constructors/getters. Stream's `Search.get_group_counts` validates physical columns, uses the same native filters/read scope as `get_count` and returns alias-safe group tuples without granting raw SQL expression access. Original TACTIC retains its native Select path; parent and task-branch results match before/after in the actual original runtime.
- Reuse at most 32 immutable compiled PythonCmd entries per worker for identical source up to 65,536 characters; larger scripts retain request-only reuse. Never retain templates, request inputs, results or module globals across requests. Read current saved/file source and recheck account/permissions before every invocation; content changes invalidate by content key. Verify concurrent execution isolation, exactly-once Mako global blocks, cache bounds, source traceback mapping and late rollback.
- On the same private SQLite fixture, alternate saved previous/current methods over 20 samples per variant. Full `Api.dispatch` compound-search medians excluding network/rendering: no notes 25.393 → 9.285 ms; 25,000 matching notes 152.486 → 17.494 ms, with 25,000 → 0 materialized note objects and equal parsed JSON results. Actual isolated PostgreSQL 18.6: no notes 278.692 → 239.240 ms; 25,000 notes 364.923 → 223.714 ms. These figures describe the test fixtures, not the unidentified 19:36 production outlier.
- Qualify compiler/count/privacy/custom-class/API checks, unchanged Handler XML-RPC/procedure integration, original-runtime comparisons and current client/Help checks. Synchronize EN/RU Help and reviewed reference hashes. Test servers/clusters are stopped; restart Stream and Handler manually. Production load/soak, full GUI/API parity and the deferred physical terabyte run were not tested.

## 0.112.140 — 2026-10-14

- Allow Task Manager + with no selected object in Handler and Stream, including Perforce-like file projects. Reuse native project-owned tasks, standard task statuses and current-user defaults; no asset or synthetic work object is created. Keep normal drafts, row revision checks, Inspector, notes, hours and changelist task links. Existing object-selected creation remains supported.
- Resolve a missing parent to the current real project in native task scope/catalog operations, reject another project's owner, and retain canonical project identity in browser drafts. Handler project choices avoid schema/network work on the UI thread and consume the existing worker status catalog.
- Qualify 127 Handler controller/catalog/QML checks, actual Vue plus/editor/save/context-menu Inspector input against an isolated file project, native stale/cross-project rejection and task-to-changelist publication, plus existing file-submit and XML-RPC task regressions. Synchronize Help and Handler 0.6.0.90. Restart Stream and Handler; PostgreSQL/live-user data and a complete Task Manager layout parity audit were not run for this change.

## 0.112.141 — 2026-10-14

- Move the complete Administration Users directory, Profile/Account/Groups editor, field definitions, confirmations and adaptive layout to local users.ui.mjs/users.state.mjs copies in both products. Keep native QML/Vue controls and existing server transports; remove the superseded independent markup and styles. Include License type when the server schema supports it.
- Preserve masked passwords, immutable existing logins, draft/permission guards, retired-account search and selection, membership edits, explicit save/discard confirmation and unknown-write recovery. Keep shared English/Russian validation messages and independent product packaging.
- Fix Frame icon aliases, visible house scrollbars, wrapped row-label alignment, button content insets and full translated button labels. The paired harness uses visible browser scrollbars and checks internal glyphs/indicators and label bounds as well as outer geometry.
- Qualify 108 Groups and 132 Users states in Material QML and Edge (EN/RU, light/dark, wide/narrow), native keyboard/touch and 150% geometry, browser touch/password/membership/save/conflict flows, isolated SQLite account writes, local module copies and native update packaging. Reports are tools/frame_groups/output/groups-report.html and tools/frame_users/output/users-report.html. Refresh Stream and restart Handler. Live PostgreSQL and other OS scaling settings were not tested for this UI change.

## B14 remaining surfaces — 2026-10-19

Stream 0.112.167 / Handler 0.6.0.118 share Knowledge Base, schema confirmation,
Timesheet, reports and work-hour presentation. API/journal retain browser
capabilities; native rich text, ACL, revisions, drafts and mutation owners stay
in their existing hosts. Complete source ownership, evidence commands, restore
points and remaining limits: [frame_remaining.md](docs/frame_remaining.md).
B07's 40 usable legacy widget classes remain open; Batch Manager is unchanged.

## 0.112.168 — 2026-10-19

- Refresh the remaining-legacy plan with L01–L12, clear acceptance and exclusions;
  retain the completed Frame checkpoints and unfinished B07 status. Assign all
  40 pending configured canonical classes once across seven workflow blocks.
- Re-run the shipped XML/CG inventory without working databases: 239 entries,
  34 referenced adapted / 40 pending / 27 production-excluded / 3 unfinished;
  the portable catalogue remains 37 classes and 87 aliases. The JSON pipeline
  document reported by the XML scanner is documented as a non-widget entry.
- Correct stale Help/deployment snapshots: 127 of 129 API entries are partial,
  two are excluded; behavioral parity remains unverified. Preserve independent
  clients, native capabilities and deferred MySQL. This release changes planning,
  documentation and version metadata only; it implements no planned legacy block.

## 0.112.169 — 2026-10-19

- Connect L02's four configured legacy columns to existing native note/task owners
  and independent Frame adapters: old Discussion, SObjectTask, TaskParentSpacing,
  and formatted message cells. Preserve task-column width and inline assignment/
  date flags; retain original context prefix text. Message JSON becomes plain
  formatted text with author and shared progress, without executing message HTML.
- Match bare and project-qualified note/task parent references while checking
  the logical project of bare records. Normalize batch lookup keys; another
  project's equal parent code must not enter the result. Keep Command writes,
  ACL, stale revision handling and rollback with existing owners.
- The catalogue now has 41 classes / 98 named aliases; the shipped XML/CG census
  has 38 adapted / 36 pending classes. B07 remains open. Old Submission notes
  stay excluded with pyasm.prod; setting subcontexts, old CGI filters and the old
  HTML calendar/preview are not claimed as full legacy presentation parity.

## 0.112.170 — 2026-10-19

- Use the existing DisclosureButton for normal and XML-configured result cards. The clicked arrow becomes the native-sized spinner, without Loading data rows shifting the tree. Keep branch errors and Retry.
- Retain loaded metadata on search-tab activation. Explicit refresh and changed record inputs still reload; root loading finishes before saved descendant restoration. Cached expansion/tab return makes no result-items request. The first uncached server request remains asynchronous.
- Add a production-component browser regression for held responses, configured cards, keyboard activation, failures/retry, cached reuse and late replies; compare with Handler's existing disclosure controls.
- The real Episode → Shot profile exposed 1980 reparses of a roughly thousand-file snapshot while describing two shots. Reuse the existing request-local, XML-source-checked file index for the first file type too; mutable external XML and malformed/missing attributes retain their original behavior. No path/result cache is added.
- On the same live Episode 01 → Shot data, the request fell from about 4.30 s to 0.204 s. The already running server contains mixed old/new workers and needs a full restart for consistent application of the fix. Focused browser/native/snapshot/naming checks and the shipped web build pass; verification limits are recorded in docs/frame_search.md.

## 0.112.171 — 2026-10-19

- Verify the existing browser profile activity lifecycle against the Handler zero-width hidden-document fix: create six preview cards, reveal all 25 only on demand, preserve complete long snapshot filenames and first-card identity, and collapse without refetching records.
- Add a real UserProfile browser regression and synchronized EN/RU profile Help. Record native before/after frame measurements and Qt bytecode/cache versus AOT boundaries in docs/frame_support.md. Stream runtime UI and portable Frame descriptions are unchanged in this correction.

## 0.112.172 — 2026-10-19

- Refresh the source-only UI/config audit: 453 QML + 298 Vue files, all 751 classified; 36 used legacy widget classes still pending. Distinguish seven retained predecessor admin forms from their current Frame replacements; do not infer active migration work from missing direct imports.
- Sort the remaining plan by relative effort, preserving L01–L12 identities and splitting L07 implementation/acceptance without duplicating classes. Put the confirmed inline tags/keywords Frame gap first (U01), followed by L02 option completion and service cells; preserve exclusions and dependency gates.
- Record that classification is not runtime/pixel acceptance and that the B14 gate is historical evidence. No UI runtime or Handler source changes are part of this planning update.

## 0.112.173 — 2026-10-20

- Group the existing effort-sorted legacy queue into three implementation stages, keeping independent distribution/legacy transition as a separate fourth stage. Preserve every U/L subblock, its internal order, exclusions and dependency/acceptance gates.
- Clarify that executing stage 1 means U01, L02, L07a, L03 and L05 together; the inline tags editor alone does not close it. Retain the detailed 14-subblock queue as an expandable reference. This is a planning-only change; runtime and source-audit results are unchanged.

## 0.112.177 — 2026-10-21

- Продолжен файловый блок этапа 2: табличный CheckoutButtonElementWdg открывает общий Frame-список файлов фиксированной версии в отдельном окне ТХ и браузерном диалоге ТС. Браузер скачивает выбранный файл; ТХ использует native File и существующую файловую очередь.
- Отмена и закрытие прекращают текущую операцию; ответы старой сессии игнорируются. Локальная перезапись требует явного подтверждения. Исправлены поздняя отмена, защита локального файла при завершении передачи и кодирование native URL с #/%.
- Открытие списка читает метаданные без обхода локального диска; проверка выбранного файла остаётся в worker. В обоих клиентах совпадает порядок файлов, а узкий русский футер и выбранная строка проверяются вводом.
- Общий нативный индикатор прогресса закреплён за Material: цвет и толщина больше не зависят от порядка загрузки старых Qt-модулей.
- Здесь принимаются обычные файлы; sequence/UDIM checkout, другие L04 workflows и общая B07-приёмка остаются открыты. Проверки и примеры: docs/frame_table.md.

## 0.112.176 — 2026-10-20

- Продолжен объединённый этап 2: FileAppendLinkTableElement открывает общую Frame-форму в отдельном нативном окне ТХ и браузерном диалоге ТС. Добавлены тип файла и сохранение имени; конкретная версия снапшота фиксируется до загрузки.
- Append использует FileAppendCheckin/FileUndo, проверяет полную ревизию и все имена перед записью, откатывает позднюю ошибку. При неизвестном результате повтор блокируется; отмена не удаляет исходные локальные файлы.
- У каждого черновика отдельная папка загрузки. Ctrl+V вставляет изображение даже из поля с фокусом; обычная вставка текста сохраняется. Проверены настоящая кнопка ячейки, HTTP-загрузка/байты и парные состояния формы.
- Проверки и ограничения: docs/frame_table.md. Остальные файловые действия и завершение этапа 2 остаются открытыми.

## 0.112.175 — 2026-10-20

- Начат объединённый этап 2: остаток первого этапа включён в его приёмку. Старый HTML Custom Layout Editor исключён; существующие portable CustomLayout определения сохранены.
- Добавлены отдельные вложенные таблицы с собственными запросом, выделением, фильтром и страницей, повторным раскрытием из кэша и штатными редакторами. Проверяется реальное CG `columns/tasks_parent`; пароль login не передаётся в данные вложенной строки.
- Добавлены типизированные временные ячейки и общий Frame-скелет расписания/дневных часов с переходами в существующие Gantt и Timesheet. Старые inline/cascade callbacks, файловые операции и итоговая приёмка B07 остаются открытыми; регистрация адаптера не означает полного переноса.
- ТХ и ТС сохраняют независимые поставляемые копии. Парные проверки и ограничения: `docs/frame_table.md`, `tools/frame_table/output/index.html`.

## 0.112.174 — 2026-10-20

- Deliver the shared inline tags editor and 16 additional typed table adapters. Keep explicit drafts, current-user preferences, captured script/selection context, safe confirmation and transactional link/record revisions in the existing owners.
- Run original client JavaScript through its existing SDK in a browser worker or an isolated Qt JS process; native windows remain QML. Retain independent product resources and use shared Frame descriptions for service cells, parallel tasks, instance links, portable CustomLayout and confirmations.
- Preserve all CG layouts. Slash references resolve to dotted names. Keep nested FastTable/HiddenRow, file-ingest DOM callbacks, unrestricted Mako and bottom reports explicitly open in L01/L04/L07b/L11; adapter registration is not full B07 acceptance. See docs/frame_table.md for evidence and the remaining stage-1 dependency.


## 0.112.198 — 2026-10-24

- Fix configured table scripts failing with DataCloneError: serialize the API record context at the Worker boundary, including nested Vue proxies; release the Worker and activity on a synchronous send failure.
- Restore ordinary nested-table fields from their record data when no computed cell is returned, retaining zero and false. Search file tables by filename instead of internal file code.
- Support SnapshotFilesWdg hidden rows through the existing nested table in Stream and Handler 0.6.0.144. File membership comes from the selected snapshot XML; links use native File paths. Preserve file type, directory metadata, frame range and size. Empty snapshots stay empty.
- Recursive disk contents of directory packages and Maya/applet scenarios are outside this checkpoint; this does not close general legacy compatibility. Restart the BAT server to load Python changes, then reload browser tabs.


## 0.112.199 — 2026-10-24

- Migrate SnapshotInfoWdg owner captions to tactic.ui.table and the independent Handler 0.6.0.145 value catalogue. Keep original name-code labels, batch parent lookups, code-only references and missing-parent n/a without restoring pyasm.prod.
- Fix the Checkin Log log view instead of certifying only checkin_history. Remove its RenderSubmission action because the production subsystem is excluded. Exercise Code, Files and the original native query projection on the same snapshot.
