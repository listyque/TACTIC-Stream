# TACTIC / Vue 0.18 — запуск

Полная инструкция: **README_VUE_RU.md**. Полный форк, готовая Vue-сборка.

Остановите предыдущую группу и сохраните резервную копию. **Не удаляйте local_data и не повторяйте INIT/SETUP/UPGRADE ради 0.18.** Из нового каталога TACTIC-5.0, со своими рабочими путями:

```bat
set "TACTIC_PYTHON=D:\TACTIC_OLD\TACTIC-5.0\.runtime\python\python.exe"
set "DATA=D:\TACTIC_OLD\TACTIC-5.0\local_data"
START_CLUSTER.bat --data-dir "%DATA%" --port 9123 --workers 3
```

Сохраните свой `--config`, если используется внешний XML. Для одного процесса — START_TACTIC.bat. Открыть http://127.0.0.1:9123/tactic/admin/ и обновить Ctrl+F5. Остановка — Ctrl+C. Node для запуска не нужен.

Custom Layout, Manage Views и SearchType-инструменты сохраняют исходный widget_config. Preview статический: Mako/JS не выполняются; вложенные поддержанные виджеты открываются в сохранённом layout. Физическое удаление/переименование/смена типа колонок НЕ включены.

Запуск сохранённого Python по умолчанию выключен. Это административный код с полными правами серверного процесса, НЕ песочница. Только на остановленной тестовой установке: `CONFIGURE_NATIVE.bat --data-dir "%DATA%" --writes on --scripts on`, подтвердить ENABLE, перезапустить.

В консоли START → RUNNING (долгие запросы) → END, один request_id. Новый журнал не копирует значения полей/пароли/tickets. Сырые legacy worker-логи остаются приватными.

Не удаляйте старые UI-каталоги. START_LEGACY меняет рендерер, не откатывает данные.
