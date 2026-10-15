---
group: Guide
icon: code
order: 94
---
# Internal structure: database-clock timestamp filters

> Dynamic timestamp values in native Search, their vendor-specific SQL and the original API quoting rules. The database computes the clock; timestamp values are not evaluated as arbitrary SQL.

## Where the clock is computed

`Search.add_filter()` resolves the column's type, asks its `DatabaseImpl` for a validated timestamp expression, and includes that expression in the query. The database evaluates it when executing the statement. Stream does not replace it with the application server's Python clock at filter construction time.

```python
from pyasm.search import Search

search = Search('cg/assets')
search.add_filter('timestamp', 'NOW', op='<')
objects = search.get_sobjects()

# Portable original interface for vendor-specific clock arithmetic
search = Search('cg/assets')
cutoff = search.get_database_impl().get_timestamp_now(offset=1, type='day', op='-')
search.add_filter('timestamp', cutoff, op='<')
objects = search.get_sobjects()
```

The selected type must actually have a timestamp column. Supported declared types are `timestamp`, `datetime` and `datetime2`. A text column containing the word `NOW` does not become a clock expression.

## Values and vendors

| Value | SQLite | PostgreSQL |
| --- | --- | --- |
| `NOW`, including lowercase/mixed case | Database `CURRENT_TIMESTAMP` | Database `now()` |
| `CURRENT_TIMESTAMP`, any case | Database current timestamp | Database current timestamp |
| `DATETIME(...)` | Zero arguments, or literal string/numeric/NULL arguments and SQLite modifiers | Refused: this is SQLite syntax. |
| `now()` and generated interval expressions | Use the portable `get_timestamp_now` interface instead. | Supported `now()`, and `now() + '0.5 day'::interval` / subtraction forms. |
| `CURRENT_TIMESTAMP(0)` through `(6)` | Refused | Supported database precision. |

For example, SQLite accepts `DATETIME('now','-1 day')`, `DATETIME('now','start of day')` and `DATETIME(0,'unixepoch')`. String arguments use SQL single quotes, with doubled apostrophes for escaping. Nested SQL, identifiers and additional statements are not accepted as automatic timestamp expressions. A valid SQLite modifier call that returns SQL NULL retains that database result; it is not replaced with the current time.

SQLite normalizes both the timestamp column and the dynamic result through the existing `spt_timestamp` function. Equal instants with different UTC offsets compare equally, and stored microseconds remain significant. SQLite's `DATETIME` function still has its own precision behavior; Stream does not invent fractional digits it discarded. PostgreSQL retains its native timestamp and transaction-clock semantics. Neither vendor's clock is the time on the user's phone.

Day columns such as `due_date` retain their existing wall-calendar behavior. A clock token still includes time; it is not automatically midnight. The four-part `between` date helper requires actual parseable dates, strips time and includes the end day. It does not accept `NOW` as a date endpoint.

## Original API quoting rules

```python
# Original XML-RPC SDK: the special NOW token works in an operator filter
objects = server.query('cg/assets', filters=[['timestamp', '<', 'NOW']])
```

Three-part API filters use quoted values. `NOW` is the original special case that overrides quoting. `CURRENT_TIMESTAMP` and `DATETIME(...)` in that same three-part filter remain literal strings. SQLite may compare them as text; PostgreSQL may reject them as invalid timestamp input. Do not mistake those results for a computed clock.

Direct Search with `quoted=None` or `False` permits the supported clock expressions. An explicit `quoted=True` keeps `CURRENT_TIMESTAMP` and `DATETIME(...)` literal; `NOW` preserves its special original behavior. Two-part API filters use default quoting and can therefore recognize a dynamic value, but their operator is equality.

For operator comparisons with generated offsets, use authorized server Python and the original `Search` / `get_timestamp_now` example above. This adds no parameter or method to XML-RPC.

## Validation, permissions and transactions

The native `DatabaseImpl.get_timestamp_filter` helper validates supported clock syntax. It is also used by `process_value`, so automatic timestamp values in native Select/Insert/Update preparation share the validation. Malicious function suffixes, subqueries or extra SQL statements are rejected. Explicit raw SQL in trusted SQL builders remains a separate existing contract; this does not enable arbitrary SQL through API filter values.

Search type, project and API permissions remain active. An authenticated reader can use a permitted clock filter without script execution privileges. `@UPDATE` / `@PYTHON` inside other filter expressions retain their administrator and Command requirements. A rejected timestamp value rolls back preceding writes in that same Command.

SQLite `process_value('timestamp', None, 'timestamp')` now keeps a nullable value unquoted instead of calling `startswith` on `None`. Invalid numeric timestamp input to that processor raises a clear `TypeError` instead of the source's `AttributeError`; numeric SQLite time arguments must be inside a supported `DATETIME(...)` call.

## Verification and limits

Forty-two cases run against the actual original runtime with an identical clock installed only on private SQLite test connections. Source defects have independent expectations: case-sensitive NOW conversion, qualified columns, offset comparison, unsafe SQL prefixes, nullable/invalid processor values and the original PostgreSQL processor's quoted `now()` result. The latter is a processor comparison, not a claim that the original PostgreSQL server was run.

Thirty-one Windows tests cover the unchanged XML-RPC SDK, server Python, authenticated reader, null/retired rows, clock offsets, timestamp precision, SQL builders, filter writes/rollback and ticket lifecycle. Actual isolated PostgreSQL checks the clock, intervals, precision, native Select and rollback. Tests are in `tests/test_dynamic_timestamp_filters.py`, `tests/test_datetime_filters.py`, `tests/test_statements.py` and `tests/test_expression_paths.py`.

Complex automatic SQL expressions remain unfinished. Supported Select/Search filters, joins, paging and copies, plus remaining serialization/replacement limits, are described in [Search/Select help](search_select.en.md). This is not full API or all-vendor parity; MySQL is not included in these checks.

[Search filters](search_filters.en.md) · [Core model](core_model.en.md) · [Site](site_context.en.md)
