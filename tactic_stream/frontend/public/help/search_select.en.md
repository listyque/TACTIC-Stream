---
group: Guide
icon: code
order: 95
---
# Internal structure: Search and its Select

> Search and the Select returned by get_select() now build one query. Bound filters, permissions, joins, copies and paging survive switching between the original interfaces.

## One query, two original interfaces

`Search` resolves the registered search type, project, resource and SObject class. `Select` owns the SQL selection, grouping, ordering and paging. The object returned by `search.get_select()` belongs to that Search; it is not an independent query that can silently discard its filters.

```python
from pyasm.search import Search

search = Search('cg/assets')
search.add_filter('pipeline_code', 'asset')
select = search.get_select()
select.add_filter('name', 'Robot')
select.set_limit(20)
select.set_offset(0)
objects = search.get_sobjects()
```

Use your actual registered type, columns and pipeline code. Ordinary filter values remain bound database parameters. A value containing apostrophes or SQL text does not become executable SQL.

Search and its Select share the ordered WHERE and JOIN lists. Postfix `begin` / `and` / `or` operators therefore retain the order of mixed calls. Setting the page on either interface updates the same Select page; the last setter wins. Offset without a limit retains the original no-pagination behavior. Normal reads retain retirement and custom/security filters.

## Direct execution and counts

```python
search = Search('cg/assets')
search.add_filter('name', 'Robot')
select = search.get_select()
select.add_column('code')
select.set_limit(1)

statement = select.get_statement()
assert statement == search.get_statement()
rows = select.execute(search.get_sql())
total = search.get_count()
```

Direct Select execution returns SQL tuples, whereas `get_sobjects()` constructs SObjects. Existing XML-RPC serialization converts tuples to arrays. For basic row queries, both Search count and Select count ignore paging. Existing grouped/distinct Select counts use the native subquery-count implementation; Search's basic count still counts matching source rows. Do not assume those count modes mean the same thing for aggregate projections.

The owned Select executes on its Search resource. Passing another project's Sql connector is rejected; changing the base tables or replacing the query with `set_statement()` is also rejected. A standalone `Select()` retains its separate, trusted SQL-builder contract.

Object results retain the original Search cache. After changing a previously executed Search, use `get_sobjects(redo=True)` to fetch again.

## Copies, removal and SQL text

`search.copy()` and `search.get_select().copy()` detach filters, parameters, joins and paging. Adding a filter to the copy does not change the original. The copied Search checks the current user's access again instead of inheriting a previous administrator's permission. A null/denied Search produces an empty direct Select query too; the original core incorrectly allowed direct Select to read its rows.

`get_wheres()` exposes native clauses, including parameter markers rather than the original embedded literal values. To remove a generated clause, pass that actual clause to `remove_where()`; its corresponding bound parameters are removed with it. Direct mutation of the clause list without synchronizing parameters is rejected when compiling or executing. This is not a serialization format.

SQL rendering recognizes markers only outside quoted strings, identifiers, comments and PostgreSQL dollar quotes. Literal `?` and `%s` remain text. PostgreSQL bound execution also escapes literal percent signs for psycopg, across object, code, id, count and related-query paths.

## Permissions and direct joins

Typed Select filters use the same metadata validation and bound values as Search. `add_where()`, unquoted SQL values, raw projections and direct SQL joins retain the existing authenticated administrator/script boundary. The generic native Sql connector also requires an active administrator; a reader uses permitted Search/API reads, not a raw Sql shortcut. Copying a denied query does not reopen its scope.

Direct same-resource joins use the original Select join builder and populate the Search's joined-column metadata. Search schema joins continue to use the configured relationships. Direct cross-resource joins remain unsupported. See [connection help](connections.en.md) for relationship directions and [filter help](search_filters.en.md) for expression permissions and transactions.

For fast main-type code/ID lists with existing projections or joined fields,
use `Search.get_sobject_codes()` / `get_sobject_ids()`. They extract the actual
base-table key rather than the first selected value. Existing aliases, JOIN
duplicates and paging are retained; details and limits are in
[Core model Help](core_model.en.md).

## Saving and restoring Select

```python
search = Search('cg/assets')
search.add_filter('name', 'Robot')
select = search.get_select()
select.add_column('code', as_column='asset_code')
select.set_limit(20)
state = select.dumps()

receiver = Search('cg/assets')
receiver.get_select().loads(state)
receiver.add_filter('name', 'Robot')
rows = receiver.get_select().execute()
```

`dumps()` returns the original Select JSON shape: tables, columns and aliases, ordered WHERE/JOIN lists, grouping/HAVING, ordering, distinct and page. Bound values are quoted into serialized SQL conditions; literal parameter-like text stays literal. Effective null/retirement restrictions are included. JSON contains query values, but no connection, password, Search owner or permission grant.

`loads()` restores state into the receiving Select without replacing its Search, project, database resource or connector. It rechecks current Search access, retains receiver restrictions and rebuilds joined-column metadata, including old exports without `join_tables`. New typed filters use bound parameters again. Successful loading clears cached SObjects; an invalid load leaves the existing query and parameters unchanged. A failure inside server Python also rolls back preceding writes through the usual Command transaction.

Loading SQL conditions into an owned Select requires an authenticated administrator/script context. A reader cannot use saved state to gain raw SQL access. Base-table replacement, foreign databases/schemas, replacement statements, raw filter dictionaries, unbound parameters and unsupported join syntax are rejected. Unknown JSON owner/connector/permission fields do not change the receiver. This is query state, not a transfer of permissions or automatic SQL translation between vendors.

The original export mistakenly wrote aliases into `columns`; its loader looked for another field and silently returned full rows. Native exports retain real columns and aliases. Original unprojected exports remain readable; damaged original projections with lost column names are rejected instead of guessed.

## Verification and remaining limits

Thirty-one scenarios were executed on the real unchanged original core and the native SQLite runtime: mixed filters, nested groups, lists/nulls/booleans, quoted values, direct SQL, paging/counts, joins and copies. Null scope and inherited retirement have separate source/native expectations: direct owned execution retains Search restrictions that the original direct Select skipped. Windows checks also cover the unchanged XML-RPC SDK, preceding-write rollback, reader access, parameter removal, source signatures and existing query/security contracts. Isolated PostgreSQL checks mixed filters, literal percent/marker text, direct joins, copies, object/code/id reads, counts and null scope.

Sixteen serialization scenarios also run on the unchanged original core and native SQLite, with separate expectations for original projection loss and scope bypasses. Native checks cover invalid-load atomicity, cached objects, aggregate/distinct/quote modes, reader refusal and unchanged XML-RPC SDK rollback. Isolated PostgreSQL verifies aliased projections, joins without exported join metadata, literal percent/parameter text, new bound filters and failed-load rollback.

Replacement SQL/base tables, raw filter dictionaries, cross-resource direct joins, PostgreSQL-specific `DISTINCT ON` parity and MySQL are not complete. This does not establish full API or administrator UI parity. Database-clock syntax and quoting remain described in [timestamp help](timestamp_filters.en.md).

Since 0.112.7, native self-instance relationship queries use separate SQL aliases for the link and source tables. Owned Select dumps/loads preserve these aliases and their validated table columns, including simultaneous parent/child constraints. See [Directed same-type instance reads](help:core_model) for endpoint definitions and remaining write contracts.
