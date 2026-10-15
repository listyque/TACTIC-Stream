# Карта изменений 0.8

Основа — полный source fork 0.7. Исходные admin/DEFAULT XML и resolver конфигураций не изменялись.

| Исходная область | Изменение | Граница |
|---|---|---|
| tools/local/setup_env.ps1 + runtime-manifest | Официальный /pip/zipapp/version.pyz; проверка невалидного кэша | Версия/CRC не являются криптографическим pin pip; Windows не запускался |
| tools/local/launch.py | Явные sibling paths для isolated Python, CHECK/RESTORE, lifetime lock | Не отключает зависимости, licence, вход |
| tools/local/managed_sqlite.py | Backup → stage → worker → validate → publish → journal/recover | Только управляемый LOCAL SQLite, не внешний vendor |
| tools/local/sqlite_worker.py | Оригинальные миграции на копиях, реальные integrity/foreign-key checks | Production использует настоящую лицензию; в CI это отдельно оговорённая заглушка |
| tactic/core/sqlite_upgrade.py | Проверяемый адаптер исходного SQL + data-preserving SQLite rebuild | Не универсальный SQL переводчик, unknown/custom отказ |
| BaseUpgrade | Optional managed offline execution; каждый метод транзакционен | UI бизнес-Command/Transaction не менялись |
| Upgrade.execute | Не ставить last_version_update проекту с SQL errors | Чужие legacy DB/vendor не тестировались |
| SthpwUpgrade.upgrade_v4_0_0_b03_002 | In-process fix_search_code, ошибки не теряются | Может корректно остановиться на отсутствующем родителе |
| src/bin/fixes/fix_search_code.py | Делегирование callable, прежний CLI сохранён | Уже заполненные search_code сохраняются |
| SystemInfoWdg native target / AdminPanel | Read-only real metadata + явная версия | Не DBA audit/upgrade editor; конфигурационный маршрут прежний |
| NATIVE_UI_VERSION, api, build | Единый источник версии 0.8 | Core VERSION остаётся 5.0.0.a02 |

Новые тесты отделяют unit collaborators от настоящих полной seed-миграции и SQLite-файлов. Во всех full-seed CI-тестах факт подмены только Licence.get отмечен прямо; это не доказательство полноценного запуска. Unit-тесты публикации с fake worker доказывают публикацию/rollback, а не SQL-корректность; SQL проверяется отдельными случаями.

Полный перечень и хеши — `changes-from-0.7.json`, текстовый патч — `changes-from-0.7.patch`. Исторические отчёты 0.2–0.7 не выдаются за проверки 0.8.
