# Тестирование, запуск и выпуск после передачи

## 1. Что уже доказано и чем

В этом handoff **заново проверены архив, хеши и статическая структура**, но приложение, тесты и браузер повторно не запускались. `SNAPSHOT_FACTS.json` отражает только эту проверку.

Сохранённый отчёт **выпуска 0.20** сообщает:

| Проверка выпуска | Количество | Граница |
|---|---:|---|
| Python unit | 1304 | Изолированные методы, конфигурации и отдельные SQL/FS-сценарии; не 1304 сквозных пользовательских сценария |
| JavaScript methods | 177 | Методы компонентов; не все реальные DOM/browser interactions |
| Controller subprocess | 25 | Настоящие дочерние Python-процессы на Linux, не Windows BAT |
| Original cluster HTTP | 352 | Настоящие TACTIC/SQLite/commands/login; тестовая подпись лицензии изолирована |
| Cluster orchestration | 63 | Включает успешный запуск дочерних наборов; не прибавлять повторно к их сценариям |
| Build | 50 SFC | Компиляция и сверка готовых assets |
| XML metadata parity | 11370 | 80 файлов / 487 views; не полное поведение каждого виджета |

В самом выпуске 0.20 **не выполнялись**: Windows BAT / Windows PowerShell 5.1, загрузка окружения из сети, browser-наборы этого выпуска, PostgreSQL/MySQL, network filesystem locks. Существуют прежние browser-отчёты других версий, но они не становятся новым прогоном после изменения кода.

Оригинальные сквозные runner создают отдельные полные копии штатных SQLite seed и применяют исходные миграции. `--isolate-license` — явная тестовая изоляция подписи, не обход в production. `--bridge` — тестовый HTTP-мост при запрете обычной браузерной навигации, не доказательство native cookies/CSP/navigation/WebCrypto. У пользователя нужно пройти обычный браузер без него.

## 2. Текущие команды пользователя: только три BAT

В корне должны остаться `START_TACTIC.bat`, `SETUP_ENV.bat`, `MANAGE_TACTIC.bat`. Не копировать старые имена из исторических README как новые entry points.

Рабочие окружение и БД сохраняются. Пример из нового корня исходников:

```bat
set "TACTIC_PYTHON=D:\TACTIC_ENV\python\python.exe"
START_TACTIC.bat --data-dir "D:\TACTIC_TEST\local_data" --port 9123 --workers 3
```

Одиночный и legacy варианты:

```bat
START_TACTIC.bat --single --data-dir "D:\TACTIC_TEST\local_data"
START_TACTIC.bat --legacy --data-dir "D:\TACTIC_TEST\local_data"
```

Примеры параметров и диагностики:

```bat
MANAGE_TACTIC.bat settings --python "D:\TACTIC_ENV\python\python.exe" --data-dir "D:\TACTIC_TEST\local_data" --mode cluster --save
START_TACTIC.bat --dry-run
MANAGE_TACTIC.bat check env
MANAGE_TACTIC.bat check db --data-dir "D:\TACTIC_TEST\local_data"
MANAGE_TACTIC.bat check startup --data-dir "D:\TACTIC_TEST\local_data"
```

**`check startup` не read-only:** выполняет оригинальную инициализацию, потенциально с записями и auto_upgrade согласно пользовательскому XML. `check db` диагностирует managed SQLite и может вернуть код 3 без автоматического запуска миграции.

SETUP устанавливает Python/dependencies, не PostgreSQL-сервер. Его URL и versions в manifest не проверялись в ходе handoff. Проверку актуальности/доступности зависимостей выполнять отдельной задачей до изменения manifest.

## 3. Повтор unit/build в developer-окружении

Из корня исходников, совместимым Python с зависимостями проекта:

```text
python -W ignore -m unittest discover -s tests/native_ui -v
node tests/native_ui/test_grid_state_012.cjs
node tests/native_ui/test_table_toolbar_013.cjs
node tests/native_ui/test_fill_state_014.cjs
node tests/native_ui/test_ui_state_015.cjs
node tests/native_ui/test_admin_state_017.cjs
node tests/native_ui/test_design_state_018.cjs
node tests/native_ui/test_compact_shell_019.cjs
node tools/native_ui/build.cjs
python tools/native_ui/audit_config_parity.py --out config-parity.json
```

Это примеры существующих важных JS-наборов, не утверждение, что они единственные. Для всех актуальных `test_*.cjs` использовать приведённый в `tools/run_js_suites.py` runner handoff (он запускает каждый файл отдельным Node-процессом, сохраняет код возврата, не вычисляет выдуманный суммарный test count).

Пример вызова helper (из произвольной папки):

```text
python docs/handoff-0.20/tools/run_js_suites.py --root . --output D:\TEMP\tactic-js-check
```

В ходе подготовки handoff проверена только справка этого helper; JS-наборы им здесь не запускались.

`-W ignore` выше соответствует исторической команде тестов; не скрывать warnings в production launcher и отдельно оценивать настоящие предупреждения среды.

### Контроллер и кластер

```text
python tests/native_ui/run_console_020.py --output D:\TEMP\tactic-control-check
python tests/native_ui/run_cluster_019.py --output D:\TEMP\tactic-cluster-check --skip-browser
```

В 0.20 **нет отдельного `run_cluster_020.py`**. Включённый `run_cluster_019.py` запускает прежние группы original HTTP и controller-independent сценарии. Его JSON содержит историческую метку `version=0.19`; при повторе после изменений внешняя сводка должна отдельно указывать фактический commit/архив исходников и команду. Не изменять test result задним числом ради нужного номера.

Для обычного browser-прогона убрать `--skip-browser` и указать `--chromium` с настоящим исполняемым файлом. Только если отсутствует нужная криптография в изолированной CI, явный `--isolate-license` с обязательной отметкой ограничения. Только после реально подтверждённой блокировки навигации — `--bridge`; первым целевым испытанием у пользователя должен быть режим без bridge.

Runner создаёт свои disposable данные; не подставлять туда рабочий каталог. На Linux кластерные тесты запускать непривилегированным пользователем с правами на собственные временные каталоги. Test log может содержать значения исходного сервера: перед публикацией фильтровать.

### Windows smoke test

```powershell
powershell -NoProfile -File tests/native_ui/test_bootstrap_020.ps1 -Python "D:\TACTIC_ENV\python\python.exe" -Output "D:\TEMP\tactic-bootstrap-report.json"
```

Скрипт проверяет PS-разбор и преобразование arguments; с `-Python` также исполняет дочерний процесс. Не скачивает runtime и не изменяет БД. Его успех всё равно не заменяет настоящий start/stop кластера, locks, offline upgrade и UI в Windows.

## 4. Минимальная новая проверка перед каждым изменением UI

Для каждой переносимой функции сохранить:

| Измерение | Сценарий |
|---|---|
| Источник | file default, DB shared, personal, inline config_xml, config_code; нужная ветка legacy |
| Контекст | основной экран, вкладка TabWdg, вложенный layout/HiddenRow, восстановленный state |
| Данные | нормальные, пустые, NULL/0/false, большие числа, кириллица, архивные/удалённые связи |
| Действия | click/doubleclick/rightclick/keyboard, edit buffer, save, refresh, navigation |
| Запись | original command, original action, trigger, rollback, повторное чтение |
| Сбой | устаревшая запись/конфиг, второй submit, потеря ответа, недоступный worker |
| Права | запрещённый project/type/field/action и прямой запрос без UI |
| Persistence | после нового login/браузера/server-worker restart; не только текущий Vue store |

Достаточно небольшого целевого набора для конкретного PR, но нельзя обозначать его полным regression suite.

## 5. Выпуск без потери промежуточного результата

1. Сначала commit исходников и тестов. Сохранять checkpoint до длительного runtime-прогона, а не только после удачной финализации.
2. Проверить baseline version/hash и реальный diff. Не считать failed packaging release базой следующего этапа.
3. Собрать Vue из SFC; проверить `NATIVE_UI_VERSION`, `frontend/package.json`, `build-manifest.json` и наличие всех новых компонентов.
4. Выполнить тесты. Зафиксировать точные команды, версии сред, время, код возврата, число, scope и flags. `timeout` и `failed` остаются отдельными статусами. Исторические цифры не суммировать.
5. Сформировать README текущего выпуска, source map, limitations, patch и hash manifest. Патч должен применяться к чистой предыдущей версии и приводить к тем же хешам.
6. В архив включить полное дерево исходников, compiled assets, исходные тесты и отфильтрованные отчёты; исключить `.git`, runtime, caches, `.pyc`, рабочие/private тестовые БД и конфиги, профили, sessions, secret/raw logs, payload и font files. Штатные upstream seed не подменять тестовой БД.
7. Проверить ZIP CRC, каждый hash manifest и наличие трёх BAT. Только после этого публиковать файл с номером релиза.
8. При неудаче публиковать ясный статус и сохранить checkpoint, не переименовывать предыдущий архив в новый и не описывать неподтверждённый код как готовый.

## 6. Откат

Переключение `--legacy` возвращает renderer, **не отменяет команды, данные или миграции**. Для исходников нужна предыдущая версия; для данных — собственная проверенная резервная копия.

`MANAGE_TACTIC db restore` — восстановление **прерванной установки** staged-upgrade, не произвольный rollback после новых пользовательских записей. Нельзя удалять журнал или руками ставить state=upgraded для обхода ошибки. Перед offline-операциями остановить всю группу и другие процессы, открывшие базу.
