---
group: Guide
icon: code
order: 91
---
# Внутренняя структура: связи connect

> Как работают направленные связи `sthpw/connection`, контексты, фильтры и выражения `connect`. Это описание работающего ядра Stream и его проверенных отличий от исходника.

## Connection и связь схемы

`SObjectConnection` находится в `pyasm/biz/sobject_connection.py` и наследует обычный SObject. Записи хранятся в системной таблице `sthpw/connection`: источник задают `src_search_type` / `src_search_id`, назначение — `dst_search_type` / `dst_search_id`; `context` определяет назначение связи.

Типы включают проект там, где это необходимо: `contract/entity?project=one` и `contract/entity?project=two` — разные адреса. Одинаковый `id` в разных таблицах или проектах не означает один объект.

Это отдельный механизм от `<connect>` в XML-схеме проекта. Схема описывает разрешение отношений по колонкам и instance-таблицам; `sthpw/connection` хранит конкретные направленные пары объектов. Обе системы используют Search/SObject и их права, но не заменяют друг друга.

## Создание и направление

Следующий пример выполняется в серверном Python, внутри штатной команды и транзакции. Объекты берутся из текущего проекта.

```python
from pyasm.search import Search
from pyasm.biz import SObjectConnection

first = Search.get_by_code('contract/entity', 'A')
second = Search.get_by_code('contract/entity', 'B')
link = SObjectConnection.create(
    first, second, context='reference', direction='dst'
)
```

Так создаётся одна запись `first → second`. Исходное значение `direction='both'` по умолчанию создаёт также обратную запись. Если та же исходящая пара и context уже существуют, метод выдаёт предупреждение и возвращает `None`; он не создаёт дубликат. Возвращённая запись при `both` относится к последнему, обратному направлению.

Пустой context при создании заменяется на `reference`. В чтении пустой context означает отсутствие фильтра и может выбрать связи разных назначений.

У методов чтения разные исходные соглашения:

| Вызов | Что выбирает |
| --- | --- |
| `get_connections([first], direction='dst')` | Исходящие записи, где `first` — src. |
| `get_connections([first], direction='src')` | Входящие записи, где `first` — dst. |
| `get_sobjects(links, direction='dst')` | Объекты назначения выбранных записей. |
| `get_sobjects(links, direction='src')` | Объекты-источники выбранных записей. |
| `get_connected_sobjects(first, direction='dst')` | Пара «входящие записи, их источники». |
| `get_connected_sobjects(first, direction='src')` | Пара «исходящие записи, их назначения». |

Названия направлений двух семейств выглядят противоречиво, но это исходный контракт. Не меняйте направление по аналогии с другим методом.

```python
links = SObjectConnection.get_connections([first], context='reference')
targets = SObjectConnection.get_sobjects(links)
```

Для создания, удаления и отката используются обычные SObject/Command/Transaction. Удаление записи связи не удаляет объект назначения.

## Выражения connect

`connect` в `pyasm/biz/expression.py` читает исходящие связи начальных объектов. `@CONTEXT` фильтрует запись связи, обычные поля фильтруют объект назначения.

```python
from pyasm.biz import ExpressionParser

codes = ExpressionParser().eval(
    "@GET(connect['@CONTEXT','reference'].code)", first
)
filtered = ExpressionParser().eval(
    "@SOBJECT(connect['@CONTEXT','reference']['code','B'])", first
)
count = ExpressionParser().eval(
    "@COUNT(connect['@CONTEXT','reference'])", first
)
```

В XML-RPC начальные объекты передаются через `search_keys`:

```python
codes = server.eval(
    "@GET(connect['@CONTEXT','reference'].code)",
    search_keys=['contract/entity?project=one&code=A']
)
```

Без начальных объектов `connect` сам не ищет все записи системы. Начальный поиск можно задать явно:

```python
codes = server.eval(
    "@GET(contract/entity['code','A'].connect['@CONTEXT','reference'].code)"
)
```

Если начальные объекты уже переданы, первый тип в пути выражения трактуется как относительная связь по схеме, а не как повторный абсолютный поиск. Поэтому при переданном `first` обычно требуется путь сразу с `connect`.

Неподходящий context, отсутствующая связь или недоступное назначение дают пустой результат. Висящая запись с отсутствующим объектом назначения не удаляется при чтении. Обычный Search исключает retired-объекты; параметр парсера `show_retired` не перенастраивает внутренние поиски специального контекста `connect`. Если у таблицы connection добавлена колонка `s_status`, её обычная фильтрация также сохраняется; в базовой схеме этой колонки нет.

## Типы, фильтры и Search

`get_sobjects()` в Stream группирует назначения по полному типу, затем ищет id в соответствующей таблице и проекте. Исходник ошибочно использовал тип первой связи для всех id; это могло возвращать совершенно другие объекты. Исправление отдельно проверено для смешанных типов и проектов.

`@SEARCH(connect[...])` с начальными объектами возвращает native Search только при одном полном типе назначения. Смешанный набор отклоняется явной ошибкой: один Search не может представлять несколько таблиц/проектов. Пустой набор также не становится выдуманным Search. Получить смешанный набор объектов можно через `@SOBJECT`.

Исходный цепочный `@SEARCH(contract/entity[...].connect[...])` возвращает Search таблицы connection с проекцией `dst_search_id` для дальнейшего поиска, а не Search объектов назначения. Обычные фильтры назначения в этой промежуточной ветке не применяются. Для готовых объектов используйте `@SOBJECT` или `@GET`. XML-RPC не сериализует Search как объекты: локальный Search доступен в серверном Python.

`EQ` в фильтре context использует регулярное выражение. Ошибка исходного SQLite, который подменял его LIKE, проверяется отдельно от исправленного результата Stream.

## Права, кэш и проверка

Начальные объекты и назначения проходят обычные проверки Search/API. Право на чтение связи не даёт право на объект назначения в закрытом проекте. Вложенные read policies проверяют обращения к connection и к типам назначений; после ошибки API восстанавливает предыдущую policy.

Кэш `get_connected_sobjects()` учитывает пользователя, режим `Sudo`, запрос и фильтры. При активной вложенной read policy готовые назначения не берутся из кэша. Это исправляет воспроизведённую утечку: результат чтения с Sudo раньше мог возвращаться после выхода из повышенного режима. Запись, удаление и откат инвалидируют кэш связей и выражений.

Проверены 26 сценариев с исходным ядром: направления, context и фильтры, смешанные типы/проекты, пустые и отсутствующие назначения, retired, Naming и Search. Отличия для ошибок исходника имеют отдельные ожидания. Проверены неизменённый XML-RPC SDK, серверный Python, права обычного пользователя, Sudo/read-policy кэш и откат на SQLite; создание, чтение и откат также проверены на PostgreSQL.

Тесты: `tests/test_expression_connections.py`, `tests/test_schema_api.py` и PostgreSQL-сценарий в `tests/test_expression_paths.py`. Это не подтверждает полную совместимость всех вариантов Search или API.

[Объекты и выражения](core_model.ru.md) · [Обзор](overview.ru.md) · [Администрирование](administration.ru.md)
