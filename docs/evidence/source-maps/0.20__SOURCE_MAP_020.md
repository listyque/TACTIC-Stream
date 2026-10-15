# 0.20 — три BAT, один внутренний контроллер

## Реальные входы

* START_TACTIC.bat → `tactic_bootstrap.ps1`, entry=start → `control.py start` → прежний cluster.py либо launch.py.
* SETUP_ENV.bat → тот же bootstrap, entry=setup → прежний setup_env.ps1. Python не требуется для выбора этого пути.
* MANAGE_TACTIC.bat → entry=manage → меню/явная команда control.py → прежние служебные инструменты.

## Делегирование

`check env/db/startup` → launch.py --check / --check-local-db / --check-startup.
`db init/upgrade/restore` → launch.py --init-sqlite / --upgrade-local / --restore-local.
`configure` → configure_native.py. `build` → tools/native_ui/build.cjs.
`settings` сохраняет только локальные пути/режим, до подключения БД.

Не изменялись командная бизнес-логика, SQL-upgrade, безопасность данных, widget_config, session/RPC или балансировка. Из прежних служебных и серверных модулей изменены только сообщения с именами удалённых BAT. Из фронтенда — только подсказка в GlobalSettings. Сборка меняет также свою строку версии.

## Что удалено

BUILD_VUE, CHECK_ENV, CHECK_LOCAL_DB, CHECK_STARTUP, CONFIGURE_NATIVE, INIT_LOCAL_SQLITE, RESTORE_LOCAL_SQLITE, START_CLUSTER, START_LEGACY, UPGRADE_LOCAL_SQLITE .bat. Обходные дубликаты в подпапки не добавлены. Старый START_TACTIC заменён новым входом с режимом по умолчанию cluster (3 процесса); --single сохраняет возможность однопроцессного запуска.

## Тесты

`test_console_020.py` — stdlib plans/profile/menu/source contracts и subprocess/сигналы.
`run_console_020.py` — реальные вызовы прежних инструментов, read-only сравнение seed и обязательные подтверждения.
`test_bootstrap_020.ps1` — отдельный необязательный Windows PowerShell smoke, включён, но в этой среде не исполнялся.

Справочные первоисточники по аргументам: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_powershell_exe?view=powershell-5.1 ; https://docs.python.org/3/library/subprocess.html#security-considerations
