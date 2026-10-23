# Ubuntu / Apache / PostgreSQL

## Standalone server delivery

The source-mounted development environment below remains available.
For installation without a checkout, build `python -m tools.server_delivery
--output <new-directory>` from `tactic_stream` and use the exported directory's
`manage.py load`, `init`, `update`, and `check`. It contains all three Docker images,
relative Compose secrets and named persistent volumes. Its native bootstrap creates
a new PostgreSQL system database. See [installation and update](../../SERVER_DELIVERY.en.md)
and [установка и обновление](../../SERVER_DELIVERY.ru.md).

## Source-mounted development environment

Контракт двух комплектов и подключение неизменённого Handler:
[HANDLER_DEPLOYMENT.md](../../HANDLER_DEPLOYMENT.md). Отдельная проверка
`tools/handler_deployment_check.py` использует собственные PostgreSQL базы
и Apache контейнер; рабочую базу стенда не мигрирует.

Запускать из корня `tactic_stream`. Нужны Docker с Compose и Python 3.10+
на машине, с которой запускается скрипт. Отдельная Ubuntu в WSL не требуется:
Apache и backend работают в контейнерах Ubuntu 26.04. В backend устанавливается
Python 3.14, собирается Vue и ставится наш пакет из исходников.

```sh
python deploy/docker/manage.py init
```

Первый запуск собирает образы, создаёт отдельные volumes, поднимает окружение
и запрашивает новый пароль администратора дважды. Пароля по умолчанию нет.
`init` откажется перезаписывать существующую системную БД.

Приложение: http://127.0.0.1:8082/ . `/admin/` не является UI-адресом.
Все HTTP и XML-RPC запросы идут через Apache;
внутри backend остаётся наш `TacticMonitor` с тремя воркерами и своим XML-конфигом.
Как в оригинальном TACTIC, каждый слушает свой порт 8081/8082/8083;
Apache proxy_balancer распределяет запросы между ними. Python процессы находятся
в app контейнере. На Windows пять Python процессов — три воркера, монитор
и Windows launcher виртуального окружения, который ожидает основной Python.
Backend и PostgreSQL не публикуют порты на хост. Apache сохраняет Host,
поэтому проверка Origin работает и на внешнем порту 8082.

```sh
python deploy/docker/manage.py up      # запуск уже созданного окружения
python deploy/docker/manage.py update  # исходники, upgrade БД, перезапуск без сборки
python deploy/docker/manage.py rebuild # Python/OS/Dockerfile: пересборка образов
python deploy/docker/manage.py check   # HTTP, XML-RPC, воркеры, реальный PostgreSQL
python deploy/docker/manage.py check-postgres # новый Sql/диалект на временной PG-схеме
python deploy/docker/manage.py status
python deploy/docker/manage.py logs
python deploy/docker/manage.py stop
```

Исходники `src` смонтированы read-only в `/opt/stream-src`; Python использует их
через PYTHONPATH. Backend импортирует свой src, каталоги legacy не монтируются.
Изменения Vue: `npm run build` в frontend; новые assets сразу доступны через Apache,
перезапуск не нужен. Изменения Python: `manage.py update` останавливает backend,
устанавливает изменённые закреплённые Python зависимости в volume python_packages,
затем выполняет штатный
`upgrade` и запускает сервисы. Если миграция завершилась ошибкой, backend остаётся
остановленным. Перед обновлением рабочей системы сделать резервную копию данных.
`up` не выполняет миграции и не собирает образы. `init` собирает при первой установке;
`rebuild` пересобирает по явному запросу для изменения Python/OS или Dockerfile.
Новые Python зависимости доступны через /opt/python-packages в PYTHONPATH и
сохраняются при пересоздании контейнера; обычный update не скачивает совпадающие версии.
`update` не пересоздаёт Apache/PostgreSQL без изменений их compose-конфигурации.
Образы содержат исходный пакет, bind mount содержит текущую версию кода;
стенд требует доступного checkout. Для переноса без checkout нужен `rebuild`
и удаление bind mount/PYTHONPATH из конфигурации на целевой машине.
После up/init/update управляемый site-файл tactic-stream.conf обновляется из
apache.conf, предыдущая версия сохраняется как tactic-stream.conf.previous.
Включаются нужные proxy модули, выполняется configtest и graceful reload;
при ошибке проверки прежний site-файл восстанавливается. Остальные файлы Apache
и настройки Webmin сохраняются. Отдельно: `python deploy/docker/manage.py apache-config`.
`stop` удаляет контейнеры и сеть, сохраняя volumes. `down -v` не входит в скрипт.

Webmin установлен из официального подписанного APT-репозитория в том же
Ubuntu-контейнере, что и Apache. Адрес: https://127.0.0.1:10000/ , логин `root`.
Случайный пароль находится в `.local/webmin-password`; это отдельный пароль
Webmin, Unix-аккаунт root остаётся заблокированным. При первом запуске создаётся
собственный самоподписанный сертификат. Браузер попросит принять его для localhost.
`check` доверяет конкретному сертификату контейнера и проверяет настоящий вход
и модуль Apache. Порт Webmin всегда привязан к 127.0.0.1;
другой порт задаётся `STREAM_WEBMIN_PORT`.
Если пароль root изменён через Webmin, обновить локальный файл для `check`.

Webmin управляет Ubuntu-контейнером Apache. Docker socket и каталоги хоста ему
не предоставлены; backend и PostgreSQL управляются через Compose. Системного
systemd в контейнере нет. Конфигурация Webmin и Apache сохраняется в собственных
volumes `tactic-stream-linux_webmin_config` и `tactic-stream-linux_apache_config`.
Изменения Apache через Webmin переживают пересоздание контейнера. После первого
запуска обновления `apache.conf` из образа автоматически не заменяют конфиг volume;
менять действующий конфиг через Webmin или `docker compose exec apache`.

Данные Windows-запуска и `legacy` в контейнеры не копируются.
Собственные данные Linux хранятся в `tactic-stream-linux_stream_data`, включая
`config/tactic-conf.xml`, SQLite и журналы. PostgreSQL использует отдельный
`tactic-stream-linux_postgres_data`. Постоянный случайный пароль PostgreSQL находится
в `.local/postgres-password`, подключается как Compose secret и исключён из Git
и Docker build context. Сохранять его вместе с резервной копией PostgreSQL.
Скрипт не создаёт новый пароль, если обнаружил существующий volume без файла.

**Конфигурация по умолчанию использует SQLite; поддерживается новая установка
на PostgreSQL.** Bootstrap, CRUD, метаданные, схемы/связи, транзакции, создание
проектов, cg.zip, плагины, задачи/заметки, snapshots, очередь и монитор/воркеры
проверяются отдельно на настоящем PostgreSQL 18.6. Рабочая SQLite установка
автоматически не преобразуется в PostgreSQL; MySQL пока не реализован.
`check-postgres` использует текущие исходники и тест из checkout в отдельном
одноразовом контейнере, собственный SQLite-контекст в /tmp и случайную временную
PG-схему, временные проектную и системную базы, которые удаляет после проверки.
На системной базе запускает собственный монитор с двумя воркерами и проверяет
реальные HTTP/JSON и XML-RPC запросы, renewal, запреты записи и остановку процессов.
Проверка требует CREATE DATABASE, доступного у тестового владельца Docker.
Соседний `legacy` нужен только для
чтения и сравнения выбранных исходных методов диалекта; рабочие данные legacy
не используются. Эта проверка не объявляет совместимость со всем legacy API.
Compose создаёт PostgreSQL сервис с БД `sthpw` и пользователем `stream`.
`check` проверяет текущие UI-ресурсы, корень приложения, origin и настроенные
workers; SQL проверка использует только TEMP-таблицы. При системном PostgreSQL
подключается к настроенному ресурсу; при SQLite отдельно проверяет PostgreSQL
сервис. Это не объявляет SQLite-данные мигрированными. Частный стенд можно
проверить через `STREAM_DEPLOY_URL` и тот же `TACTIC_DATA_DIR`/XML-конфиг;
`handler_deployment_check.py` проверяет так собственный Apache/PG экземпляр.

Другой порт задаётся переменной `STREAM_HTTP_PORT`; адрес привязки — `STREAM_BIND`.
Например, PowerShell: `$env:STREAM_HTTP_PORT = '8090'`, затем `manage.py up`.
По умолчанию публикация только на `127.0.0.1`. Этот конфиг — HTTP для локального
развёртывания; при публикации в интернете сначала настроить TLS на Apache и
доверенные proxy headers в backend. Конфиг Apache находится в `apache.conf`.

В 0.27.0 Task/Note/StatusLog, статусный журнал и завершение задачи проверены
одним скриптом на SQLite и PostgreSQL, а также через XML-RPC. init/upgrade
создаёт их таблицы и реестр. Обновление по-прежнему использует mount исходников
и `manage.py update`, без сборки Docker образа.
