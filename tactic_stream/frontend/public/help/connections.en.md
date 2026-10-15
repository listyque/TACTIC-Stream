---
group: Guide
icon: code
order: 91
---
# Internal structure: connect relationships

> Directed `sthpw/connection` relationships, contexts, filters and `connect` expressions. This describes working Stream core behavior and verified corrections to the original implementation.

## Connections and schema relationships

`SObjectConnection` lives in `pyasm/biz/sobject_connection.py` and inherits the ordinary SObject. Rows are stored in `sthpw/connection`: `src_search_type` / `src_search_id` identify the source; `dst_search_type` / `dst_search_id` identify the destination; `context` describes the connection's purpose.

Types include their project where required: `contract/entity?project=one` and `contract/entity?project=two` identify different resources. Equal ids in different tables or projects do not identify the same object.

This differs from `<connect>` in a project's XML schema. The schema describes relationships resolved through columns or instance tables; `sthpw/connection` stores specific directed object pairs. Both use Search/SObject and their permissions, but neither replaces the other.

## Creation and direction

Run this example in server Python inside the normal command/transaction context. Objects are loaded from the current project.

```python
from pyasm.search import Search
from pyasm.biz import SObjectConnection

first = Search.get_by_code('contract/entity', 'A')
second = Search.get_by_code('contract/entity', 'B')
link = SObjectConnection.create(
    first, second, context='reference', direction='dst'
)
```

This creates one `first → second` row. The original default `direction='both'` also creates the reverse row. If the same outgoing pair and context already exist, the method warns and returns `None`; it does not create a duplicate. With `both`, the returned row belongs to the last, reverse direction.

An empty creation context becomes `reference`. An empty read context means no context filter and may select relationships with different purposes.

The original read methods use different direction conventions:

| Call | Selection |
| --- | --- |
| `get_connections([first], direction='dst')` | Outgoing rows with `first` as src. |
| `get_connections([first], direction='src')` | Incoming rows with `first` as dst. |
| `get_sobjects(links, direction='dst')` | Destination objects of those rows. |
| `get_sobjects(links, direction='src')` | Source objects of those rows. |
| `get_connected_sobjects(first, direction='dst')` | Pair of incoming rows and their source objects. |
| `get_connected_sobjects(first, direction='src')` | Pair of outgoing rows and their destination objects. |

These two families use seemingly contradictory direction names, but that is the original contract. Do not infer one method's direction from another method.

```python
links = SObjectConnection.get_connections([first], context='reference')
targets = SObjectConnection.get_sobjects(links)
```

Creation, deletion and rollback use normal SObject/Command/Transaction mechanisms. Deleting a connection row does not delete its destination object.

## Connect expressions

`connect` in `pyasm/biz/expression.py` reads outgoing connections of the initial objects. `@CONTEXT` filters connection rows; ordinary fields filter destination objects.

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

XML-RPC supplies initial objects through `search_keys`:

```python
codes = server.eval(
    "@GET(connect['@CONTEXT','reference'].code)",
    search_keys=['contract/entity?project=one&code=A']
)
```

Without initial objects, `connect` does not search every system connection. You can provide an explicit initial query:

```python
codes = server.eval(
    "@GET(contract/entity['code','A'].connect['@CONTEXT','reference'].code)"
)
```

When initial objects are supplied, the first type in a path is interpreted as a relative schema relationship, not a repeated absolute search. With a supplied `first`, normally start the path directly with `connect`.

A nonmatching context, missing connection or inaccessible destination returns an empty result. A dangling connection is not deleted while reading. Ordinary Search excludes retired objects; parser `show_retired` does not reconfigure the internal queries of the special `connect` context. If a connection table has an added `s_status` column, its ordinary filtering also applies; the base schema does not contain that column.

## Types, filters and Search

Stream's `get_sobjects()` groups destinations by their full type, then looks up ids in the corresponding table/project. The original used the first connection's type for every id, potentially returning entirely different objects. This correction has separate mixed-type and mixed-project tests.

With initial objects, `@SEARCH(connect[...])` returns a native Search only for a single full destination type. Mixed destinations raise an explicit error: one Search cannot represent multiple tables/projects. An empty result does not become a fabricated Search either. Use `@SOBJECT` to retrieve mixed destination objects.

The original chained `@SEARCH(contract/entity[...].connect[...])` returns a Search of the connection table projected to `dst_search_id` for subsequent queries, not a destination-object Search. Ordinary destination filters are not applied in that intermediate branch. Use `@SOBJECT` or `@GET` for resolved objects. XML-RPC does not serialize Search as objects; local Search is available in server Python.

Context filter `EQ` uses a regular expression. The original SQLite bug that substituted LIKE has independent source/native expectations.

## Permissions, caching and verification

Initial and destination objects pass ordinary Search/API checks. Reading a connection does not grant access to its destination in a protected project. Nested read policies check connection queries and destination types; API errors restore the previous policy.

The `get_connected_sobjects()` cache accounts for user, `Sudo` mode, query and filters. With a nested read policy, resolved destinations are not reused from cache. This fixes a reproduced leak where a Sudo result remained accessible after leaving elevated mode. Writes, deletions and rollback invalidate connection/expression caches.

Twenty-six scenarios are compared with the original core: directions, contexts and filters, mixed types/projects, empty or missing destinations, retirement, Naming and Search. Corrections to source bugs have independent expectations. Checks include the unchanged XML-RPC SDK, server Python, ordinary-user permissions, Sudo/read-policy caching and SQLite rollback; creation, reading and rollback also run against PostgreSQL.

Tests: `tests/test_expression_connections.py`, `tests/test_schema_api.py` and the PostgreSQL scenario in `tests/test_expression_paths.py`. These checks do not establish full Search/API parity.

[Objects and expressions](core_model.en.md) · [Overview](overview.en.md) · [Administration](administration.en.md)
