---
group: Guide
icon: code
order: 90
---
# Internal structure: objects and expressions

> How TACTIC Stream connects types, objects, fields, request context and expressions. This article grows with the core migration. Verified behavior is distinguished from remaining limitations.

## Call path

A client request passes through the HTTP/XML-RPC handler, `ApiXMLRPC.dispatch`, project/user context and the corresponding core method. Server Python uses the same `pyasm`/`tactic` classes as the API. The running server does not import the original `legacy` or Handler.

Writes use `Command.execute_cmd`, which connects changes to a transaction, journal and triggers. Constructing a Python object and changing its fields does not save a database record. A failed command must roll back preceding writes; file operations also use a file undo journal.

## SearchType, Search and SObject

| Concept | Purpose | Implementation |
| --- | --- | --- |
| `SearchType` | Type metadata: table, class, namespace, database and fields. Ordinary types are registered in `sthpw/search_object`. | `pyasm/search/search.py` |
| `Search` | Object queries with filters, relationships, ordering and access checks. | `pyasm/search/search.py` |
| `SObject` | One object: field values, pending changes, serialization and commit/delete. Assets, tasks and notes share this base. | `pyasm/search/search.py` |
| `Project` | Active project and resolution of full types and database resources. | `pyasm/biz/project.py` |
| `DbResource` / `Sql` | Connection and SQL dialect routing, separate from the domain model. | `pyasm/search/sql.py` |
| `SearchKey` | An object address, such as `cg/assets?project=cg_test&code=DEMO_ARM`. | `pyasm/search/keys.py` |

SObjects hold loaded values in `data` and pending changes in `update_data`. `get_value()` includes changes; `get_data()` returns merged data by default. `set_value()` validates the value and column permissions but does not save the object. Persistent objects are saved with `commit()` in a normal command context.

`get_sobject_dict()` adds `__search_key__` and `__search_type__`. The API also converts values to its transport representation. A core Python object and the dictionary returned to a client are different representations of the result.

## Project writes and ordinary-user permissions

Since 0.112.9, ordinary users can create, update and delete **project types**
(types outside `sthpw/` and `config/`) and their instance links through the
existing SObject, Command and XML-RPC APIs. This does not grant system or
definition editing, file operations or arbitrary server Python/SQL.

| Check | Required behavior |
| --- | --- |
| Identity and transaction | Authenticated request user, active native Command, registered project resource. |
| Project | A matching `project` rule must grant `allow`. |
| Type | `insert` for creation, `edit` for update, `delete` for removal; missing rules deny. Access levels are cumulative, as in AccessManager. |
| Fields | `sobject_column` checks use the object's actual project; staged fields are checked again at commit. |
| Existing row | A fresh Search must still find it under current view/type/filter policy; a cached object cannot bypass a changed rule. |

For example, a group with these rules can edit existing assets in `cg_test`
but cannot create or delete them:

```xml
<rules>
  <rule group="project" code="cg_test" access="allow"/>
  <rule group="search_type" code="cg/assets" project="cg_test" access="edit"/>
</rules>
```

Use `insert` to include creation, or `delete`/`allow` to include deletion.
An instance type needs its own rule: permissions on an asset do not grant
permission to create its link record. Source `handle_commit_security()` only
restricted custom scripts, and column checks could allow a view/edit user to
insert rows without a type/project write grant. Stream intentionally closes
these gaps; 17 actual original-runtime cases have separate native expectations.

`ApiXMLRPC.check_method_access` admits ordinary object CRUD and add/remove
instance calls; SObject owns their permissions. `Sql._do_security_dml` binds
the validated object's values on SQLite/PostgreSQL. SQLite permits one target
table for that statement and resets authorization in `finally`; raw SQL/DDL
does not inherit this permission. Ordinary SQLite native connections outside
an active Command remain guarded. Generic native SQL API parity is not claimed.

Commit/delete retain triggers, transaction XML, object logs/change timestamps
and global-search index updates. The integral index uses a bounded native
`Sudo`, restored even on failure; ordinary callers cannot directly edit it.
New writes clear only the current user's redo rows, using an ownership/type
predicate in the final SQL. Deletion appears in transaction XML; as in the
source it is skipped in SObjectLog indexing. Trigger failures and late bulk
permission failures roll back object, index and journal changes.

Verified: unchanged SDK over real XML-RPC as an ordinary user, type/field/project
denials, stale staged permissions, current row filters, raw SQL denial,
committed journal/index/redo effects, existing account/message flows and
isolated SQLite/PostgreSQL. The supplied cg template also passes privately.
Other system/definition and file writes and per-path Workflow script ACLs
need separate migration. Task/status history, Workflow effects and diagnostics are described below.
Full API parity remains unverified; project rules do not bypass these limits.

## Tasks and status history

Since 0.112.11 ordinary users can insert, edit and delete `sthpw/task` through
native SObject/Command and existing API object methods; `create_task` also uses
this path. The logical project is the task's `project_code`, including when
the current request is in another project. Project `allow`, task type operation
rights (`insert`, `edit`, `delete`), current row visibility and column rules
are required. Staged fields and actual bound SQL fields are checked again.

A task must reference a visible, editable **project-type** parent in its own
project. Stored `search_code` and `search_id`, when supplied, must agree with
that parent. An ordinary user cannot change existing task `project_code`,
`search_type`, `search_code` or `search_id`: dependency propagation is still
unmigrated and raises `UnsupportedContract`. Project/system-parent tasks retain
the administrator path. These grants do not open definitions, arbitrary SQL,
server Python, `add_initial_tasks` or other protected API methods.

`StatusLog.create(sobject, value, prev_value=None)` keeps the original signature
and native relationship fields. `StatusLogTrigger` logs changed nonempty task
statuses, including an initial status; repeating a status adds nothing.
`Task.create` uses the trigger or its original manual history path when
triggers are disabled, without duplicating the initial row. An API task created
without a status has no initial status row. A log contains its source reference,
authenticated login, previous/new statuses, source project, timestamp and native
generated code. Unlike the original current-project bug, history for a task
in another project keeps the task's actual project.

The source is rechecked before history creation. `StatusLog:writing` temporarily
identifies **one history SObject**, permitting insertion and its generated-code
assignment. The shared guard/binder verifies identity, row, system resource and
operation; the scope is restored in `finally`, including commit failure. There
is no general Sudo/admin grant. Direct ordinary-user editing or deleting
history and raw SQL remain blocked.

History shares the caller's transaction. Task completion's `actual_end_date`,
status history and journals roll back on late trigger, bulk or log failure.
This differs from persistent diagnostic logs, which use an independent command.


Verified against the actual original runtime (including independent expected
correction for cross-project history), unchanged SDK over HTTP XML-RPC, and
the same isolated SQLite/PostgreSQL scenario: completion/no-op, type/project/
parent/field denials, revoked staged fields and final SQL, forged references,
history/raw SQL denial, failed bulk/trigger/log rollback and scope cleanup.

A forced insert with an explicit ID is checked as an insert, not as an edit of
a missing row; native plugin/template import retains its original identity.
Existing rows still receive a fresh read-policy check when edited or deleted.


## Workflow effects and ordinary users

Since 0.112.12 the original declarative Workflow engine accepts ordinary-user
task transitions and `call_pipeline_event(search_key, process, event, data={})`.
The parent must be a visible editable project object. Its project/type/current
row/column permissions are rechecked; task changes retain their own ACLs.
An alternate pipeline must belong to the same project/type or be shared.
Hierarchy/dependency targets receive the same parent checks and graph preflight.
Native graph validation, transaction registration and state locking remain.

`Workflow:writing` temporarily identifies **one effect SObject and its parent**.
The shared SObject guard and SQL binder permit its own insert/update/generated
code and verify parent code/ID/type, actual project database, authenticated
author, immutable existing ownership, fresh read policy and final column ACLs.
They do not grant administrator/Sudo privileges or general table/SQL access.
`Workflow:message_source` binds the native messaging helper to the parent's
`skey|process|status` or `skey|process|state`. `Workflow:note_source` permits only
the original automatic `process/error` note created during a revise event.
Each scope is restored in `finally`, including generated-code or commit errors.
Direct API writes to state/history/messages/notes remain separately protected.

Process states, overall/dependency state, packages, messages and their history,
automatic error notes, tasks, StatusLog and journals share the caller transaction.
Permission denial, a late trigger/write failure or a protected callback rolls
back the whole transition. State storage and message project ownership follow
the **actual parent project**, even when the request's current project differs.
The earlier alternate-pipeline migration fills the original empty state
`pipeline_code`; otherwise the compared ordinary-user task status and ordered
message contents match the original runtime.

Python callbacks now use the explicit trusted-execution grant described below.
Custom node handlers stay administrator-only; server JavaScript remains unsupported.
Dedicated tests cover actual source runtime, unchanged SDK/XML-RPC, native
error notes, field/parent/row denials, forged references and bound SQL, revoked
staged fields, callback/late-write rollback, cross-context effect storage and
the same SQLite/PostgreSQL scenario (`tests/test_user_workflow.py`).
Cross-project dependencies are described below; other graph variants and file permissions remain unverified.

## Trusted Python execution grants

Since 0.112.13 ordinary users may run the existing `PythonCmd`, `PythonTrigger`,
saved/inline Workflow Python callbacks and `execute_python_script` when their
native group access rules explicitly grant the source `api_cmd` key
`tactic.command.PythonCmd`, together with access to the current project:

```xml
<rules>
  <rule group="project" code="cg_test" access="allow"/>
  <rule group="api_cmd" key="tactic.command.PythonCmd" project="cg_test" access="allow"/>
</rules>
```

Use `key`, not `code`, for this source command rule. The permission is checked
even when `security/api_cmd_restricted` is unset. Unlike the original permissive
default, ordinary execution without an explicit grant stays closed. Restricted
`api_method` rules still apply to external `execute_python_script` calls.
An administrator retains the original execution path; a temporary Sudo or
in-memory admin flag does not replace authenticated persisted privileges.

`check_script_execution(..., python=True)` is used only by PythonCmd,
PythonTrigger and its dispatcher preflight. It checks the request identity,
active persisted account, current project, native command rule and active
Command transaction. Existing administrative callers keep `python=False`:
this grant does not open template/plugin/config editing, raw SQL, custom node
handlers or Expression `@PYTHON`. Script paths, inline code, Mako input/kwargs,
local SDK identity and transaction behavior keep their source contracts.

This is **trusted server Python, not a sandbox**. Granted code can import
Python modules and access the server filesystem/process; grant it only to
trusted authors. No separate per-script-path ACL or restricted Python language
is implemented. The grant does not give permission to edit stored scripts or
change Script Editor UI rights. Native SDK writes still check object/field ACLs.
Callback errors roll back tasks, state, messages/history and prior native
object writes; independently persisted diagnostic logs retain their own policy.

Actual original runtime comparisons cover ordinary inline and saved Workflow
callbacks updating the parent through the unchanged local SDK. Tests also cover
real SDK/XML-RPC execution and api_method refusal, native PythonTrigger, missing
grants, project/type/field denials, fake admin/Sudo, required transactions,
late Python rollback and the same SQLite/PostgreSQL scenario. File permissions,
other cross-project graph variants and full API parity remain unfinished.

## Cross-project dependencies

Since 0.112.14 a dependency may start a child Workflow in another project,
wait for its task, and complete its caller when that child finishes. Each
project keeps its own configuration database and process states; shared tasks,
messages and history retain the actual object project and authenticated author.

`Pipeline.get_process_sobject()` reads `config/process?project=<pipeline owner>`.
The Workflow handler uses that existing generation-aware Pipeline cache, rather
than a second cache tied to the caller's project. The unchanged source lookup
looks in the caller's configuration database and loses a foreign process; this
is an explicit bug correction, checked in both directions with same-project controls.

For native `process|...` events containing a Pipeline and SObject, `Trigger.call`
selects the object's actual project before finding or executing triggers. It
temporarily replaces only the project's request field: the user, ticket,
connection pool and Command transaction stay the same. `finally` restores the
previous context after success, denial or callback failure. This also selects
the callback project's saved scripts and its explicit `PythonCmd` grant.
A grant in the calling project does not authorize Python in the child project.
Ordinary callers still need edit rights on every affected parent object.

The original project schema capped `spt_process_state.state` at 256 characters;
dependency waiter JSON can exceed that limit. PostgreSQL project creation,
plugin/template config upgrades and `Store.upgrade()` now migrate that column
to `text`, preserving existing values. Repeat upgrades preserve long states.
SQLite already accepts long values without the varchar limit.

Verified on two physical project databases: dependency start, pending child
task, return completion, inline/saved callbacks in their owning projects,
project/type/Python grant denials, and late callback rollback of objects,
states, tasks, messages, StatusLog and transaction journals. The same scenario
passes SQLite/PostgreSQL and the unchanged SDK over real XML-RPC; test servers
and databases are disposed. These checks cover dependencies, not every
cross-project hierarchy, progress listener or configuration override.

Before commit, failures roll back all participating connections. TACTIC's
separate per-database commits remain: there is no distributed atomic commit.
A later commit failure reports already committed databases; those rows cannot
be claimed to have rolled back. File permissions and full API parity remain open.

## Persistent diagnostics

Since 0.112.10, authenticated users can use the original `DebugLog.log(level,
message, category)`, `DebugLog.debug(message, category)`, `ExceptionLog.log(error,
message=None)` and XML-RPC `log` methods. Levels are `critical`, `error`,
`warning`, `info` and `debug`; an invalid level raises `ValueError`.
Native logging returns its SObject; API `log` returns `True`.

`DebugLog` records login, level, category and message. `ExceptionLog` records
login, exception class, message and traceback, with normalized path separators.
The author must match the authenticated request; anonymous or forged authors
are rejected. API method restrictions and column rules still apply.

The shared `_write_log` helper opens an independent request context and native
`Command` on the system resource. Its transaction disables undo recording and
sync; logging disables triggers. `Diagnostics:writing` temporarily identifies
**one new SObject**, authorizing only insertion and its native generated-code
update. The SQL binder checks the actual author, resource, operation and bound
fields. The scope is removed in `finally`; there is no general system-table,
SQL or administrator grant. Direct journal-table API writes stay restricted.

After a failed command, `Command.execute_cmd` rolls back the caller, clears
the entire failed nested stack, then stores its exception once. The next
command receives a fresh root boundary and can roll back normally. A diagnostic
connection failure is reported without replacing the original business error.
`Batch` closes its administrative authentication context and connections after
ordinary login, then creates a context for the actual authenticated user.

If the caller already wrote to the system database, independent logging raises
`UnsupportedContract`: it does not silently share or roll back that writer.
This avoids an SQLite writer conflict and has the same contract on PostgreSQL.
Durable deferred logging and email notifications are not implemented.

Verified: ordinary/admin calls against the actual original runtime, unchanged
SDK over HTTP XML-RPC, method/identity/raw SQL denials, preserved debug records
after rollback, one exception for nested failure, next-command rollback,
authentication lifecycle, and the same private SQLite/PostgreSQL scenario.
This database diagnostic path is separate from browser/Handler JSONL sessions.

## Virtual SObject

`sthpw/virtual` is TACTIC's original temporary type. `SearchType.get()` creates its metadata without registering a database row. Metadata specifies `pyasm.search.SObject`, database `sthpw` and nominal table name `unknown`; no physical table exists.

Fields are assigned at runtime. Column information and SQL types are empty; normal serialization collects fields from `data` and `update_data`, including `id`. The original normal mode returns all virtual fields even when `columns` is supplied. Fast mode honors that list.

```python
from pyasm.search import SearchType

obj = SearchType.create('sthpw/virtual')
obj.set_value('label', 'Temporary result')
result = obj.get_sobject_dict()
```

A new object has `id = -1` and key `sthpw/virtual?id=-1`. This identifies a temporary object; it is not a link to a saved asset. `commit()` and `delete()`, including SQL requests through `return_sql`, raise an explicit error because there is no persistent table. Field values remain in memory for subsequent reads.

Virtual objects retain `set_value()` permission checks. They cannot bypass column rules or access restrictions on database objects.

## Expression contexts: state, date and vars

`ExpressionParser` lives in `pyasm/biz/expression.py`. Its `eval()` receives initial objects, result mode and contexts. `@GET` reads values; `@SOBJECT` returns objects.

`state` is a dictionary supplied explicitly to the current parser call. It is not global application configuration or the transaction API `set_state`. The parser puts its values into a virtual SObject and skips fields whose value is `None`.

```python
from pyasm.biz import ExpressionParser

result = ExpressionParser().eval(
    '@GET(state.label)', state={'label': 'Selected process'}
)
# ['Selected process']
```

Zero and `False` are retained. Reading an omitted field of a new object normally returns an empty string. Repeated calls with different `state` must not reuse a previous state's result.

`date` creates a virtual object with `today` and `now`, both read from the server clock during evaluation. In the original contract, `today` includes time: it is not midnight or the date on the user's phone.

```python
result = ExpressionParser().eval('@GET(date.now)')
date_objects = ExpressionParser().eval('@SOBJECT(date)')
day = ExpressionParser().eval("@FORMAT(@GET(date.now),'31/12/1999')")
```

A core date field may contain a `datetime`; API record dictionaries represent it as a string. Use `@FORMAT` for stable formatting; unknown format names preserve the input value. Date and monetary formats may depend on project settings and the server locale.

`vars` is a separate mechanism that substitutes values through `$NAME`.

```python
result = ExpressionParser().eval('$LABEL', vars={'LABEL': 'Publish'}, single=True)
# 'Publish'
```

The original `@VAR(NAME,value)` does not assign a variable: it returns an empty list and does not evaluate nested arguments. Single mode returns `None`. Incomplete calls raise `SyntaxError` in Stream instead of the original `IndexError`.

XML-RPC `server.eval()` accepts `vars` but does not accept `state`. Supply `state` from server Python through `ExpressionParser.eval()` or `Search.eval()`. Do not add it to the client API call.

## Request context, cache and permissions

`RequestContext` contains the active Store, user, project and Container. Requests have isolated contexts; Container holds temporary metadata and results within that scope. Parser cache keys account for initial objects, state and user. Writes and rollback invalidate expression results.

The API installs access checks for nested expression calls and restores them after success or failure. Reading `state`/`date` also checks the virtual type; populating fields retains the original column permission checks. Reading a temporary date does not grant access to protected types. Arbitrary server Python is restricted to permitted users.

`NamingUtil` uses the same parser to evaluate templates and supplies its naming-context objects. Parser changes are therefore tested in Naming as well as the API.

Expression-valued filters now use the original Search.eval path. Their value rules, API permissions and Command behavior are documented in [Search filter help](search_filters.en.md).

Database-clock filters and their original quoting rules are documented in [timestamp filter help](timestamp_filters.en.md). SQLite compares supported dynamic timestamp values as instants; PostgreSQL retains its database clock and interval semantics.

Search and its owned Select share filters, copies and paging; see [Search/Select help](search_select.en.md).

## Parent and child records through the API

`server.get_parent(search_key, columns=['name'])` reads the parent defined by the schema.
`server.get_all_children(search_key, child_type, filters=[], columns=['code'])` reads
children through the same native Search relationship and filter path. A nonempty
`columns` list limits the returned fields; an empty list returns the full record.
`__search_key__` and `__search_type__` remain available even when not requested.
A missing requested field is `None`; a missing parent is `{}` and no children is `[]`.

The server's `get_parent` default includes retired parents; the unchanged Python
client defaults to excluding them. Pass `show_retired` explicitly when needed.
Children retain the native default that excludes retired records. Project/type and
nested expression permissions still apply. A writing filter belongs to the active
Command and rolls back if a later filter fails.

The original API serializer overwrote `columns` with all record keys. Stream fixes
that defect through its existing shared serializer; source behavior and corrected
projection have separate assertions. The deprecated `columns` argument on the
core `SObject.get_parent()` remains ignored as in the source: API projection is
a serialization step, not a different relationship lookup.

Checks: `tests/test_schema.py` compares the original runtime, exercises the unchanged
XML-RPC client and server Python, retirement, two projects, reader permissions and
rollback. `tests/test_schema_postgres.py` compares parent/note projection on isolated
SQLite and PostgreSQL. Instance JOIN support and its limits are described below;
these checks do not establish full relationship or API parity.

### Children through an instance table

For a schema connection with `relationship="instance"`, `get_all_children()`
uses the same `Search.add_relationship_filter()` as related-object lookup.
Search joins the target, instance table and source, then filters the joined
source column by the supplied object. `query(parent_key=...)` uses this path
too; the original parent filter silently left these requests unfiltered.
The original single-object reverse filter used the wrong table and assumed
matching key names; Stream fixes both errors in the shared method.

```python
# For an instance relationship declared between these project types:
children = server.get_all_children(
    'cg/scenes?project=cg_test&code=DEMO_EP01',
    'cg/assets', columns=['code', 'name'],
)
```

The instance type and both endpoints must be readable. Missing links return
`[]`; denied instance access raises an error rather than revealing related
records. Additional filters, projections, counts and transaction rollback
use the existing Search/API paths. The JOIN retains one result per matching
instance row, so multiple links may repeat the same target. It excludes
retired target records by default but does not add a new retirement rule
for joined instance rows. Full records include `_related_code` from the
joined source; a requested column list can omit it.

This covers different registered endpoint types and directed same-type
instance reads on the same database (see below). Cross-resource instance
lookup is rejected before joining. The
literal relationship mode `many_to_many` remains unsupported. This does
not exclude `type="many_to_many"` connections that use `relationship="instance"`.

Original-runtime comparisons have independent expectations for the missing
children branch, reverse-key bug and unfiltered parent query. Tests cover
both directions, duplicate/retired/empty targets, unequal join key names,
reader permissions, rollback, unchanged XML-RPC and server Python. Private
SQLite/PostgreSQL checks cover creation, reading and removal of links.

### Batch instance lookup and filtered searches

`Search.add_relationship_filters(sobjects, op='in', path=None, type=None)`
restricts an instance JOIN to the supplied source keys. The original branch
joined every source row and ignored both the list and operator. Stream uses
the schema's actual source column in either direction. Inputs must belong to
one source type and the same resource as the target; mixed types/projects on
different resources are rejected before joining.

`Search.get_related_by_sobjects(sobjects, related_type, filters=[], path=None,
show_retired=False)` returns a dictionary keyed by each input's search key.
Missing matches have an empty list. Target filters apply before grouping;
multiple links remain multiple rows. In this batch path `_related_code`
contains the actual schema key, which can be a name or ID rather than `code`.
This lets grouping work when endpoint key columns differ.

`Search.add_relationship_search_filter(search, op='in', delay_null=False,
use_multidb=None, path=None)` executes the source search's filters and paging,
extracts its actual key column and applies the same JOIN filter. Key extraction
uses the same fast value-extraction path as code/ID helpers, so selected aliases
do not replace the schema key. Current access rules are rechecked. Preloaded objects/counts do not
freeze this lookup. The source's retirement setting is respected; explicitly
passed objects are not discarded solely because they are retired.

```python
# Server Python; requires an instance connection in the project schema.
from pyasm.search import Search

selected = Search('cg/scenes')
selected.add_filter('code', 'DEMO_EP01')
assets = Search('cg/assets')
assets.add_relationship_search_filter(selected)
records = assets.get_sobjects()
```

`not in` compares each joined source key. A target linked to both selected and
unselected sources can still appear through an unselected link; this is not
an anti-JOIN meaning “has no selected links”. Empty inputs match no records
for either operator. This instance branch returns `True` for a provided
source Search even when it finds nothing; `delay_null` does not postpone that
empty result. Joined-instance retirement and duplicate behavior are unchanged.
Same-type lookup uses directed links when an instance connection exists;
identity fallback remains for types without that instance connection.
Cross-resource instance queries remain unfinished. Arbitrary aggregate
source projections are not verified.

Checks include 20 additional original-runtime batch/search scenarios, both
directions, `in`/`not in`, empty and preloaded searches, unequal key columns,
aliased projections, intermediate-type permissions, server Python through
the unchanged XML-RPC SDK, rollback and isolated SQLite/PostgreSQL.

### Directed same-type instance reads

Since 0.112.7, `get_all_children`, `query(parent_key=...)`, single/list/search
relationship filters and `get_related_by_sobjects` share the native directed
instance lookup. The Results tree uses that same path. In the original kernel,
same-type lookups returned the input object or failed instead of following
the link table. Source comparisons retain those results as explicit defects;
Stream expectations follow the existing Handler endpoint convention.

The project schema must define the self connection and both named endpoints:

```xml
<connect from="cg/assets" to="cg/assets" relationship="instance"
         instance_type="cg/asset_in_asset"/>
<connect from="cg/asset_in_asset" to="cg/assets" relationship="code"
         from_col="search_code" to_col="code" path="parent"/>
<connect from="cg/asset_in_asset" to="cg/assets" relationship="code"
         from_col="parent_code" to_col="code" path="child"/>
```

Handler names the link-to-member endpoint `parent` and the link-to-owner
endpoint `child`. Without `path`, or with `path='parent'`, a relationship
lookup returns the owner's members. With `path='child'` it returns the
member's owners. An explicitly named self connection also returns members.
Unknown paths and missing/disabled endpoint definitions raise an error;
they do not silently choose an endpoint or return the owner itself.

```python
from pyasm.search import Search

owner = Search.get_by_code('cg/assets', 'DEMO_ROBOT')
members = owner.get_all_children('cg/assets')
owners = Search('cg/assets')
owners.add_relationship_filter(members[0], path='child')
records = owners.get_sobjects()
```

Both endpoint definitions can use `code` or `id` relationships. The actual
schema keys drive filters and `_related_code` grouping, including ID keys.
The query aliases the link table and source object table separately, so two
directional constraints can coexist. Copying and saving/restoring Select
retain these aliases. Result objects still have the target's ordinary
SearchType and search key. Dangling source links do not become valid objects.

Duplicate links remain duplicate results; cycles and self-links are read
one edge at a time, without recursive traversal. Target retirement, source
search paging/projection, row-based `not in`, counts and ordinary instance
access checks are retained. Missing links produce an empty list. Tests cover
13 actual-source cases, unchanged XML-RPC/server Python, denied link access,
rollback, code/ID keys, alias restoration and isolated SQLite/PostgreSQL.
The supplied `cg.zip` tree was also checked in a private project.

### Directed same-type instance writes

Since 0.112.8, `owner.add_instance(member)` populates both link columns:
`child` endpoint path identifies the owner and `parent` identifies the member,
as in the schema example above. Both paths must be enabled code/id edges with
different link columns. The original runtime resolved the same path twice,
overwriting the owner with the member; native writes correct that defect.

```python
owner = Search.get_by_code('cg/assets', 'DEMO_BODY')
member = Search.get_by_code('cg/assets', 'DEMO_ARM')
link = owner.add_instance(member)
outgoing_links = owner.get_instances('cg/assets')
owner.remove_instance(member)
```

The corresponding XML-RPC methods use search keys. `get_instances` returns
outgoing **link records**; `get_all_children` returns member objects. Duplicate
links and self-links are allowed. Removal deletes every active link for the
exact ordered pair; reverse links, unrelated members and retired links stay.
No matching link is a no-op. A retired endpoint can still be addressed by ID;
a missing member does not hide its existing outgoing link record.

Writes and removal validate saved, currently accessible endpoints with unchanged
keys in one type, project and database resource. Invalid schema or stale,
missing, unsaved and cross-project endpoints are rejected. Link reads use
normal type permissions. Since 0.112.9, ordinary project-type instance writes
use the shared project/type/field/current-row policy described above. System
and file writes remain separately guarded.

Mutations use native commit/delete, triggers, transaction logging and Command
rollback. Tests compare 16 code/ID cases against the actual original runtime
with independent expected directions, and check successful committed writes,
duplicate/removal behavior and rollback after actual insert/delete trigger
failures. The unchanged SDK/XML-RPC, real PostgreSQL versus SQLite and a private
`cg.zip` project pass. Cross-resource joins, arbitrary aggregate key projections
and full API parity remain unfinished.

### Fast code and ID lists

`Search.get_sobject_codes()` and `Search.get_sobject_ids()` read the database
without constructing SObjects. They return the actual `code` or `id` of the
main Search type. The original helpers returned the first selected value:
an existing `name` projection or JOIN could turn a code list into names or IDs.
Stream fixes this with independent expectations in original-runtime checks.

```python
from pyasm.search import Search

search = Search('cg/assets')
search.add_column('name', as_column='code')
search.add_filter('name', 'Robot')
codes = search.get_sobject_codes()  # Actual asset codes, not the aliased names.
ids = search.get_sobject_ids()     # Actual numeric IDs.
```

The usual key-column addition remains visible in the caller's Select. Existing
projections and aliases stay intact. A query copy appends the real main-table
column for extraction through the normal compiler and connector. This keeps
filters, JOIN rows, duplicates, distinct flags, explicit ordering and paging;
it does not add implicit ordering. Repeated code/ID calls do not leave the
private extra projection in the original Search. Loaded object caches are not
used to supply values, and uncommitted SObject attributes do not replace
database values. A stored NULL code remains `None`; empty/denied searches return
`[]`. Retirement and bound parameters use the regular Search rules.

Custom `alter_search` runs once per Search, as before. Execution copies recheck
current main-type permissions and nested read policy; a query created under
Sudo cannot keep that main-type permission after Sudo ends. Code/ID helpers
and instance-source extraction share this path. Writes preceding a later
failure still roll back through Command.

Twenty-two source-runtime scenarios cover projections, stars, aliases, joined
fields, null/retired rows, paging and a second project. Native checks also cover
repeated calls, custom hooks, read-policy restoration, Sudo, unchanged XML-RPC
SDK/server Python and rollback. Isolated SQLite/PostgreSQL exercise both keys,
JOIN duplicates, aliases and pagination. Arbitrary grouped/aggregate source
projections and cross-resource JOIN are not verified by these checks.

## Verification and limits

Nineteen virtual-object and `state`/`date` scenarios are compared with the original core: dynamic fields, serialization, dates under identical clocks, formatting and Naming. Checks include the original XML-RPC SDK, server Python, permissions, state isolation and rollback. Tests live in `tests/test_expression_virtual.py`; PostgreSQL uses an isolated database in `tests/test_expression_paths.py`.

The `connect` context is connected to native SObjectConnection; directions, filters, permissions and Search limits are documented in [connection help](connections.en.md). Full expression/API parity has not been established. The default `site` provider is restored; its hooks, configuration and named-site limits are documented in [Site help](site_context.en.md). Named sites, custom providers and the old UI palette remain unfinished. Automatic monetary locale initialization is also unfinished.

S3 repository and Handler Repository Sync are excluded from migration scope by user decision. Ordinary file repositories, check-in/check-out and snapshots remain part of the core.

[Overview](overview.en.md) · [Script Editor](script_editor.en.md) · [Repository configuration](repository_configuration.en.md)

## Ordinary-user upload and check-in — 0.112.15

`upload_file` stages bytes in the authenticated ticket's upload directory.
`simple_checkin` resolves a visible project object and runs the original
`BaseCheckin → FileCheckin → Snapshot/File → TacticRepo → FileUndo` stages in
the same Command transaction. Version allocation, metadata, naming, flags,
versionless copies, main/web/icon previews and check-in triggers are retained.
This is the existing repository model; Handler Repository Sync and S3 stay excluded.

The active authenticated user needs `project` allow, `search_type` edit for
the parent, insert/edit for `sthpw/snapshot` and `sthpw/file`, and edit access
to the affected columns. Existing rows keep their parent/project and file snapshot
identity. File rows are inserted before the snapshot, then bound to its generated
code in the original order. Final bound DML rechecks identity, permissions and staged
values, including PostgreSQL JSON. The version lock checks the same parent scope.

Only ticket uploads and native `FileCheckin` are admitted by the ordinary-user API.
API `inplace`, `local`, custom classes and other file write methods remain admin-only.
Arbitrary FileUndo and SQL outside this scope remain closed. Trusted server Python
can call native FileCheckin with its original modes; Python execution is not a sandbox.
Project naming must map main/web/icon to distinct paths; collisions are rejected.

Late failure restores old versions/versionless files and all uncommitted rows.
Consumed `create` uploads remain in durable undo-cache, matching the original TACTIC
model; re-upload before retrying. Command rollback can restore its own validated
FileUndo nodes after check-in scope ends; manually inserted journal nodes acquire no
such authority. Separate database commits retain the existing partial-commit limit.

Isolated SQLite/PostgreSQL checks cover denied project/parent/type/column rules,
two versions, versionless contents, image previews and late API/native rollback.
The unchanged XML-RPC SDK exercises simple_checkin against a temporary server.
Full ordinary-user HTTP upload, append/group/check-out, journal undo/redo and all
file API methods still need verification. See `tests/test_user_checkin.py`.

## Ordinary-user append and frame groups — 0.112.16

`add_file` and `add_group` resolve the existing snapshot and its visible parent;
`group_checkin` resolves the object directly. The dispatcher admits these operations
to the same native check-in scope as `simple_checkin`. Project allow, editable parent,
snapshot/file operation permissions and affected columns are checked under the actual
user. Metadata cannot move a file to another snapshot or change parent/project ownership.
The original FileAppendCheckin/FileGroupCheckin/FileGroupAppendCheckin, naming, triggers,
Command and FileUndo perform the work. Group File/FileGroup drafts now receive
`search_code` before their first commit, so parent authorization sees complete identity.
Their public constructors/factories keep their original signatures and default behavior.

Files must be staged in the authenticated ticket directories. With the unchanged SDK,
`add_file(snapshot_code, "extra.txt", "reference", mode=None)` and
`add_group(snapshot_code, "image.####.exr", "frames", "1-3", mode=None)` read ticket upload.
`group_checkin(search_key, "render", "image.####.exr", "1-3", mode=None)` reads ticket
server handoff, as in TACTIC. Binary `upload_file` can stage ticket uploads; handoff
requires files placed at the configured server path. Do not use the SDK's `mode="upload"`
for already staged files: it attempts an additional HTTP upload from the client disk.
The API's group `mode="upload"` reads ticket upload directly. API local/inplace/custom
classes remain admin-only; other file write methods retain their existing restrictions.

Under strict naming, physical aliases require explicit `latest_versionless` or
`current_versionless` naming definitions. Existing latest aliases update after append
and group check-in without overwriting versioned files. Naming must keep file types
and versions separate. No forced alias is created when source naming disables it.

SQLite/PostgreSQL and unchanged SDK/XML-RPC checks cover array append, sequences with
`####`/`%04d`, stepped `1-3/2` ranges and metadata, actual latest alias contents,
project/parent/type/column denials, path containment, missing frames and late failure.
The second array append can fail after the first; the outer Command restores all rows
and prior versioned/alias contents. Consumed create uploads remain in durable undo-cache;
re-upload before retrying. Cross-database commits retain the existing partial-commit limit.
Ordinary-user HTTP upload (including SDK automatic upload), check-out and journal
undo/redo still need verification. Full API parity is not claimed; Repository Sync
and S3 remain excluded. Test: `tests/test_user_checkin.py`.

## HTTP ticket staging for ordinary users — 0.112.17

The original SDK sends only a ticket to `/tactic/default/UploadServer/`; its
`set_project()` changes the XML-RPC envelope, not the HTTP upload form. UploadServer
therefore follows original UploadServerWdg: an active authenticated user may stage
files in their private ticket directory before selecting a project/object. A reader
may stage files too. This grants no permission to check them into a repository.
Check-in continues to require project allow, editable parent and snapshot/file/
column permissions. Binary XML-RPC `upload_file(ticket, filename, data)` retains its
project check. No accessible project is guessed and no admin grant is added.

`Api.http_upload → Command → FileUpload → FileUndo` reuses the native create/append
and rollback stages. The HTTP-only `Checkin:writing.ticket_upload` scope skips only
the project check for this private staging request; persisted active identity,
authenticated user, configured API method restrictions and a Command transaction
remain mandatory. The request context ends after the operation. Arbitrary FileUndo
outside an authorized operation remains closed. Upload paths and symlink targets
must stay within the authenticated ticket directory; a foreign transaction ticket
and custom upload_dir remain explicitly unsupported.

The unchanged SDK can now run `upload_file(local_path, chunk_size=113)`,
`simple_checkin(search_key, context, local_path, mode="upload")`,
`group_checkin(search_key, context, "image.####.exr", "1-3", mode="upload")`,
`add_file(snapshot_code, local_path, file_type, mode="upload")` and
`add_group(snapshot_code, "image.####.exr", file_type, "1-3", mode="upload")`.
Those automatic modes upload from the client disk, then invoke the original XML-RPC
operation. This differs from the manual already-staged calls described above.

Tests cover binary/Unicode chunks, offset resume, empty files, automatic SDK calls,
invalid/retired identity, path and foreign-ticket guards, and a failed second file
that restores the first replacement. SQLite/PostgreSQL execute the same native path.
HTTP requests are limited to 64 MiB including multipart/base64 overhead, so clients
must split larger files. Each chunk is a separate committed transaction: earlier
successful chunks survive a later failed request. Resume offset is a client-provided
chunk index, not a server-verified byte offset. Original append has no idempotency
token; retry after an ambiguous response can duplicate bytes. Server check-in
rollback retains the existing create undo-cache behavior. Ordinary-user check-out
and journal undo/redo remain unverified; full API parity is not claimed.
Tests: `test_user_checkin.UserHttpCheckin/UserHttpTransport` and UploadServer tests
in `tests/test_transport.py`. Repository Sync and S3 remain excluded.

## Ordinary-user checkout — 0.112.18

`checkout(search_key, context="publish", version=-1, file_type="main", level_key=None)`
resolves three corresponding lists: `client_lib_paths`, `sandbox_paths`, `web_paths`.
The server selects a Snapshot, applies the original version-1 context lock and runs
`checkout` followed by `checkout|<base_search_type>` callbacks. It does not copy files.
Explicit versions, current (`None`), versionless (`-1`), all types (`*`) and a specified
level were checked on private SQLite/PostgreSQL data. Sandbox paths require the native
`checkin/win32_sandbox_dir` or `checkin/linux_sandbox_dir` configuration for the client's OS.

An ordinary user must have `project allow` for the parent's actual project (which may
differ from the request project since 0.112.25), and `search_type view` for the parent, `sthpw/snapshot`, `sthpw/file`
and optional level. Explicit `sobject` or `sobject_column` view denials also stop the
operation before callbacks. All loaded columns of these records must be visible:
the callback receives the full native Snapshot dictionary and naming can read object
fields. Missing or hidden selected File references are rejected. This is a conservative
operation-level check, not a general-purpose filtered-record serialization policy.
Administrator checkout retains its existing selection semantics. Configured
`api_method_restricted` still checks the checkout method's grant.

The callbacks receive the running Command, fixing the previous `ApiXMLRPC.errors`
failure that masked callback exceptions. No sudo or repository-write scope is opened.
Read-only checkout succeeds without write callbacks; a callback that edits a parent
requires that user's edit rights. Python callbacks additionally require the existing
explicit `api_cmd` grant for `tactic.command.PythonCmd`. Same-transaction callback
failure rolls back previous callback writes and their journal entries. Deferred
callbacks keep the native post-commit boundary; they cannot roll back a committed caller.

The unchanged SDK performs local IO only after RPC succeeds:

```python
server.checkout(search_key, context="publish", version=2,
                file_type="*", to_dir=existing_directory, mode="copy")
server.checkout(search_key, context="publish", version=2,
                file_type="*", to_dir=existing_directory, mode="download")
server.checkout(search_key, context="publish", version=2,
                to_dir=existing_directory, to_sandbox_dir=True)
```

Copy/download and sandbox copies were verified through a temporary XML-RPC/HTTP server.
Client copy/download failure cannot undo a successful server RPC and may leave partial
client files. Static repository HTTP aliases retain the original public Apache-style
behavior; checkout ACLs do not add per-user authorization to those static URLs.
Locked/missing snapshots retain the native ApiException identity locally; XML-RPC's
existing generic fault handling hides these diagnostics. ExceptionLog records the cause.
Cross-project and sequence checkout are covered below.
Level alias authoring/readback is covered below in 0.112.27; unrelated cross-project callback replay remains unverified.
Tests: `test_user_checkout.UserCheckout/UserCheckoutTransport`, `CommandApiParity`,
`SnapshotLevelsParity`. Full API parity remains false; Repository Sync and S3 are excluded.

## Owned project CRUD undo/redo — 0.112.19

Ordinary users can call the original API through the unchanged SDK:

```python
server.undo()                         # latest own undo journal in this project
server.redo()                         # oldest own redo journal in this project
server.undo(transaction_id=journal_id)
server.redo(transaction_id=journal_id)
```

The native path is `ApiXMLRPC → UndoCmd/RedoCmd → TransactionLog → SObjectUndo`.
Undo reverses insert/update/delete into delete/edit/insert; redo applies insert/edit/delete.
Current project allow, type-operation grants, explicit record grants and editable columns
are checked before replay. Record grants without a rule inherit the already-checked type
operation; an explicit deny still wins. Deletion does not require editing individual columns.
Actual row writes also retain the existing native checks. A missing or filtered ordinary-user
update/delete target now fails, instead of silently marking a journal completed.

The journal must be persisted, belong to the authenticated user and current project, and have
the correct `undo`/`redo` type. Its canonical row is locked and reread: PostgreSQL uses row
`FOR UPDATE`, SQLite uses `BEGIN IMMEDIATE`. A changed or staged payload and repeated/stale
direction are rejected. Concurrent undo of the same ID permits one replay; the second fails.
Configured API method restrictions apply independently. These checks are inside TransactionLog,
so the native local caller also cannot replay a forged transient/staged journal.

CRUD journals include integral `sthpw/sobject_list` rows for Global Search. These are replayed
too, using the existing narrow Sudo pattern only around each index operation. The index's
project and parent type/code/original ID must match an object in that same verified journal;
other system rows are refused. Original ID anchors are accepted because source rename/replay
journals can retain an earlier code in the index. This restores the recorded index payload;
it does not regenerate historical indexes or change the source's identity/timestamp policy.
There is no blanket sudo for the user or journal. Failed undo/redo rolls back earlier writes,
index changes, journal direction and change timestamps inside the active native transaction.
New ordinary writes invalidate that user's redo branch, as in the source.

This release covers **project SObject CRUD and its integral search index**, including multiple
objects and code rename. It does not enable ordinary-user replay of file/upload/check-in,
schema, task, note, other system or multi-site journals. Any such node rejects the whole journal
before replay; `ignore_files=True` cannot bypass this boundary. Arbitrary `execute_transaction`,
client start/finish/abort and other resumed-session operations keep their previous restrictions.
Administrator file/schema/client-session replay remains available and was regression checked.

Tests: `test_user_undo.UserUndo/UserUndoTransport` on SQLite/PostgreSQL and a temporary
XML-RPC server with the unchanged SDK. Checked CRUD/default/explicit selection, redo invalidation,
late undo/redo failures, index rollback, concurrent duplicate undo, owner/project/direction,
type/record/column/method/read-filter denials, staged XML tampering and a real private upload
journal rejection. Existing source Undo/FileUndo/SchemaReplay/TransactionState comparisons pass.
Independent database commits retain the native partial-commit boundary; this is not a distributed
transaction. Full API parity remains false. The remaining ordinary-user file/system replay is
the next compatibility block; Repository Sync and S3 are excluded.

## Own check-in undo/redo (0.112.20)

Ordinary users can now replay their persisted own check-in journals with the unchanged
`undo(transaction_id=...)` / `redo(transaction_id=...)` API. This adds files to the project
CRUD/index replay introduced in 0.112.19. Native **SObjectUndo, FileUndo and FileUndoReplay**
restore snapshot/file records, versioned bytes and versionless aliases together. Tested:
first/second version, appending a file type, and frame sequences using FileGroup/FileRange.

The canonical journal is locked and reread, with current owner/project/direction checks.
Preflight requires each original parent to remain visible/editable in the current project,
repository view and inverse-operation type/record/column rights, and unchanged ownership
anchors. Each file path must match that parent's file metadata (including sequence frames
and .link sidecars), the journal's private ticket upload directory or its durable undo cache.
Directory links cannot escape these roots. Only the current validated journal node receives
a temporary Checkin:writing scope; it is restored in finally. There is no journal-wide sudo.

Complete journals already contain the versionless records and file operations, so replay
does not regenerate versionless aliases when restoring is_latest/is_current. Doing both
would delete file records that later journal nodes still need. XML numeric identity fields
are compared consistently with stored numeric IDs. A later SQL/metadata/IO failure compensates
the exact completed/attempted file nodes even after the check-in scope closes. A partial redo
destination is removed when its complete cache survives, preserving the original bytes.

User check-in replay requires **all its files**: ignore_files=True is rejected. Standalone
upload-only journals, schema/task/note/other-system/multisite replay and resumed client sessions
remain guarded. Historical versionless nodes without backup state require migration.
Repository metadata may receive regenerated numeric row IDs as in native SObjectUndo; code
and original parent anchors are retained. Independent database commits retain the existing
partial-commit boundary; replay is not a distributed transaction or a filesystem crash-recovery
service. SQLite/PostgreSQL, unchanged SDK XML-RPC, actual bytes/metadata, denied rights/paths,
late errors and partial writes are tested. Full API parity remains false; Repository Sync/S3
are excluded.

## Task/note writes and undo/redo (0.112.21)

Ordinary users can call the native `create_note` API for a visible editable **project object**.
The current authenticated user is the note's author; passing another `user`, editing another
author's note, changing ownership or moving a note/task to another parent is refused. A right
to read private notes does not grant a right to edit them. Existing project/type/record/column
permissions still apply. Replies require a visible thread on the same project object. A note
with replies cannot be deleted until its replies are deleted, including private replies.
The integrity query uses scoped sudo only to detect children; their contents are not exposed.

Native `SObjectUndo` now replays ordinary users' **own persisted journals** containing tasks
or their own notes. The existing owner/project/direction lock is retained. Before mutation,
preflight verifies the current original parent, its visibility/edit rights, task/note visibility,
inverse-operation record/type/column rights and immutable parent/author/thread metadata.
Task creation, detail changes and deletion; note creation, editing, code rename, deletion and
reply threads are verified on SQLite/PostgreSQL and through the unchanged XML-RPC SDK.
Late batch failures roll back both data and journal state.

Notes retain their numeric ID during insert/delete replay: `parent_id` links must still
identify the same thread. A historical insert journal without this anchor records it before
undo and saves the amended canonical XML. An occupied ID causes a rollback, never an update
of the occupying note. The same source/native probe demonstrates the intended bug fix:
original TACTIC recreates the root ID and leaves a dangling reply; native replay retains both.
Other SObject types keep their existing numeric-ID replay behavior.

**Scope limit:** a task status change can also generate `sthpw/status_log`, Workflow state,
messages and other system effects. Those journals remain refused **in full** until every
effect has a replay permission boundary. No history nodes are ignored. A separately recorded
own Workflow note is supported. Notes whose parent is a system object, reparenting, schema,
standalone-upload, multisite and resumed-session replay remain guarded. Independent-database
commits retain their partial-commit boundary; distributed atomicity is not claimed. Repository
Sync/S3 are excluded and full API parity remains false.

## Task status and complete Workflow replay (0.112.22)

Own saved journals can now undo/redo task status changes and **single-project Workflow**
transitions together: tasks, status history, process states, status/state messages (including
package data), message history and own notes. Native SObjectUndo performs every recorded
effect in order. Replay does not rerun Python callbacks or send notifications. A late failure
rolls back earlier data changes and the journal's direction.

Original SObjectUndo excluded messages from journals. Native Workflow now records them through
the same logger under the exact Workflow:writing scope and marks the XML root
`workflow_replay="complete"`. Non-Workflow messaging keeps its existing journaling behavior.
Historical Workflow state/message journals without this marker are refused; their missing
message backups cannot be reconstructed safely. Plain task status history without Workflow
states/messages can replay without the marker.

Preflight retains the canonical owner/project/direction lock. Every effect requires its
visible editable original project parent; status history also requires its original source
in the same journal with matching ID. History must retain the authenticated author. Current
view, inverse-operation, record and column denials are enforced. Derived effects follow their
authorized parent by default, as forward Workflow does; this grants no direct system-table
writes. A per-node Workflow:replay scope permits only that record and operation. Bound SQL
must match the staged object after the existing vendor conversion, including PostgreSQL JSON.
The scope is restored in finally. Another record and a forged payload remain denied.

Task/process_state IDs now survive insert/delete replay, like note IDs, so status_log links
remain valid. An occupied ID fails rather than updating another row. Other business-object
numeric-ID behavior is unchanged. Stored GMT dates remain GMT during redo; converting them
as new local input caused a native timezone shift. The unchanged source/native probe checks
both the source's partial Workflow restoration/stale messages and native complete restoration;
date preservation is checked with an explicit non-UTC server timezone and UTC user preference.
SQLite/PostgreSQL, stock SDK, pending/in-progress/complete, messages/packages, history,
revoked/read-filter rights, per-node/SQL denials and late rollback are tested.

**Remaining boundaries:** cross-project replay, old Workflow journals without message backups,
legacy empty-pipeline owner adoption, unsupported system effects, schema, standalone upload,
multisite and resumed sessions remain guarded as a whole. External effects already sent by
the original operation are not undone. Independent database commits retain partial-commit
semantics; distributed atomicity and full API parity are not claimed. Repository Sync/S3
remain excluded.

## Workflow replay across projects (0.112.23)

Own complete Workflow journals can now undo/redo dependency transitions across physical
project databases. Starting a dependent process and returning its completion restore the
recorded business changes, tasks, own notes, process states, status history and messages
together. The existing native SObjectUndo and per-node Workflow:replay scope perform replay;
Python callbacks are not run again. Task/note/state IDs retain their original links.

The journal still belongs to its initiating project: its canonical owner, namespace and
undo/redo direction are locked and checked. Reading the same journal from the other project
does not authorize replay. Each effect's original visible editable parent determines the
actual project for project, view, inverse-operation, record and column rights. Status history
requires its source in the same journal with matching original ID. Cross-project business
changes, tasks, own notes and index rows are permitted only for those validated Workflow
parents, not for arbitrary foreign-project records. No journal-wide sudo is introduced.

SQLite, PostgreSQL and the stock XML-RPC SDK check both dependency directions, callback
results/notes, preserved IDs, revocations in either project, hidden parents, record/column
denials and wrong namespace. Injecting a failure after writes to both project databases rolls
back their changes plus system history, indexes and journal direction. This tests failure
before physical commit; it does not provide distributed atomicity. The unchanged script
comparison records the original's wrong caller-database state routing and stale messages
after undo; native replay restores states in their actual databases and backs up messages.

**Remaining boundaries:** Workflow journals without complete message backups, legacy empty
pipeline-code adoption, unrelated cross-project CRUD and cross-project file replay,
unsupported system effects, schema, standalone upload, multisite and resumed sessions remain
guarded. Already sent external effects cannot be undone. Independent database commits retain
partial-commit semantics. Full API parity is not claimed; Repository Sync/S3 remain excluded.

## Replay of legacy pipeline adoption (0.112.24)

Legacy process_state rows can have an empty pipeline_code. Forward native Workflow already
adopts such a row into its parent's primary pipeline during the normal status transition.
Own complete journals now undo that assignment to empty and redo the recorded owner while
restoring status, state data, messages and history together. The existing row and ID survive.

Preflight permits only a recorded update from empty to the parent's original visible primary
pipeline. Its process definition must remain visible; __PIPELINE__ is the aggregate exception.
The original state ID is checked. The current owner must match the undo/redo direction, and all recorded changes must form the
same owner chain. Each journal node receives its own expected before/after pipeline value:
updates before adoption still belong to the empty owner, later updates to the recorded owner.
The existing runtime ownership/ACL and staged SQL checks then enforce that exact value.
Other ownership fields remain immutable. Arbitrary switches between nonempty pipelines,
changing the parent's pipeline, insert/delete replacement of an adopted row, and direct
ordinary-user process_state writes are not authorized by this exception.

SQLite/PostgreSQL and the stock SDK check adoption in both project databases, dependency
start/completion, preserved IDs/state/own notes, revoked pipeline-column rights, hidden process
definitions, forged current/parent/journal owners and bound SQL, and late rollback. An unchanged
script runs in both kernels: the original leaves the legacy owner empty and messages stale;
native Workflow adopts the owner and undo restores the old empty value and state data.

Historical Workflow journals without complete message backups still cannot be reconstructed.
Unrelated cross-project CRUD/file replay, unsupported system effects, schema, standalone upload,
multisite and resumed sessions remain guarded. Already sent effects are not undone. Independent
database commits retain partial-commit semantics; distributed atomicity and full API parity
are not claimed. Repository Sync/S3 remain excluded.

## Checkout across projects — 0.112.25

A full parent search key may refer to another project. Checkout checks that project's
access, then resolves the Snapshot, naming/sandbox paths and config callbacks in the
parent's project. Only the project field changes temporarily: the same user, security,
Command, transaction and SQL pool remain active. Finally restores the original request
context after either a successful call or an exception, including a nested Command call.

Every referenced project's access and each loaded record/column are checked, including
a level in a third project. A Python callback needs PythonCmd permission in the parent's
project. A grant or checkout trigger from the caller's project does not replace it.
Read-only callers do not gain edit rights through checkout. Same-transaction callback
errors roll back writes and journal entries; the existing deferred/partial-commit
boundaries remain unchanged. The journal remains in the initiating request project;
unrelated cross-project callback undo/redo is not part of this checkout verification.

Private SQLite/PostgreSQL tests and the unchanged SDK check real versioned/versionless
files, all file types, same/third-project levels, copy/download/sandbox, record/column/project
denials, locks, missing references, class/saved-Python callbacks and late rollback.
The same probe runs unchanged in both kernels: the original omits its checkout callback;
native executes the parent's callback and restores the caller project. Sequence checkout
is covered below; level-scoped aliases are covered below in 0.112.27. Client IO after RPC cannot be rolled
back by the server; static repository URLs retain public Apache semantics.

## Sequence checkout — 0.112.26

Checkout expands a selected sequence File into concrete frame paths using its stored
FileRange and native FileGroup. For example, image.####.png with 1-5/2 returns
image.0001.png, image.0003.png, image.0005.png in each of client_lib_paths, sandbox_paths
and web_paths. Corresponding entries describe the same frame. With file_type="*",
sequence and ordinary-file entries retain snapshot XML order; a specific type retains
the original first matching File selection. Ordinary files/directories keep their paths.
Snapshot path helpers keep their existing explicit expand_paths behavior.

The unchanged SDK consumes these lists for copy, HTTP download and sandbox checkout.
The original server returned the literal pattern, which its SDK could not copy as a
file. An unchanged probe checks that difference against the actual original runtime.
Callbacks receive the expanded paths. Existing actual-parent project and user ACLs
remain enforced; no repository write or sudo grant is added. Corrupt sequence ranges
or inconsistent path/reference counts fail before callbacks. Checkout does not repair
metadata or silently omit frames from a range. Server RPC does not copy client files.

Private SQLite/PostgreSQL and stock SDK tests cover hash/printf inputs, stepped and
negative frames, explicit/current/latest versions, several sequence types with a static
file, actual downloaded/copied bytes, denied rights, corrupt ranges and late callback
rollback. A client error after successful RPC can leave partial local copies and cannot
undo committed callbacks. Static repository URL semantics are unchanged. Level-scoped
aliases are covered below; unrelated cross-project callback replay remains unverified; full API parity
is not claimed. Repository Sync/S3 remain excluded.

## Level-scoped latest/current aliases — 0.112.27

For an object, context and level_key, check-in now creates and updates separate
LATEST (-1) and CURRENT (0) alias Snapshots with the level's exact search type and ID.
The no-level scope is separate too. get_snapshot(..., level_key=..., versionless=True)
and get_paths(..., level_key=..., versionless=True) select that exact alias. Without
level_key they select only an unscoped alias; a missing alias returns an empty result.
Snapshot.get_versionless retains its original public signature and unscoped meaning.
The native private helper carries level identity for API and check-in calls.

Example: level A's check-ins v1 and v2 create stable latest/current alias codes.
With is_current=False on v2, latest refers to v2 while current still refers to v1.
Level B's files and aliases remain unchanged. Strict naming must provide separate
latest/current paths and separate paths for each level, for example
{project.code}/{context}/{snapshot.level_id}/latest and the corresponding current
directory. System projects retain the original database-naming exclusion.
An existing destination not owned by the selected alias is rejected rather than
overwritten. Fix the naming convention before retrying; the failed check-in rolls
back its rows and repository operations through native Command/FileUndo.

Private SQLite/PostgreSQL and the unchanged XML-RPC SDK verify three independent
scopes, versions, actual bytes, stable codes, write ACL denials, late trigger failure
and a collision between two levels. One unchanged script in both runtimes makes the
source defect explicit: original API returns the same final versioned snapshot for
all requested levels; native returns the six correctly scoped aliases. This is an
intentional correction, not a claim that the buggy results match.

Level alias deletion/promotion and level-specific durable journal replay are not
verified in this release; level snapshot deletion remains explicitly guarded.
Cross-project alias authoring and MySQL are not part of these checks. Static public
repository URLs and independent database partial commits retain their existing
boundaries. Full API parity remains false; Repository Sync/S3 remain excluded.

## Browser grouped check-in

Drop Plate and Commit Queue call `execute_cmd` with `tactic.command.browser_checkin_cmd.BrowserCheckinCmd`. Its `match`, `templates` and `plan` actions read native matching/naming without repository writes. `checkin` verifies ticket/project, owner edit access, snapshot/file/field rights and uploaded basenames in the ticket directory. This exact trusted command is available to permitted ordinary users; arbitrary `execute_cmd` remains an administrator operation.

`file_matching.py` is extracted from Handler `global_functions.py`; `checkin_query.py` contains its extended naming/check-in procedures. The extraction tool records necessary runtime adaptations: explicit local SDK, explicit process and compressed sparse frame ranges. Sources and adaptations are recorded in the compatibility manifest.

Native Snapshot version locks protect allocation. Files are staged with FileUndo, derivatives use IconCreator, and native FileAppendCheckin registers them in the same Command. Metadata owns every sequence/tile member. DeleteCmd removes the whole owned group. When Handler commits group metadata after inplace registration, the shared SObject commit path reclaims members removed by that same active transaction, with replayable journal moves. Undo/redo and rollback retain both database and filesystem effects; this does not create a second unjournaled copy. Paths outside the selected repository or already owned by another snapshot fail.

`versionless_mode` comes from project `config/prod_setting` through ProjectSetting, then server `checkin/versionless_mode`. Values are `copy`, `hardlink`, `symlink`. Browser whole groups honor the setting for latest links to numbered members; versionless-only uses copies. Hardlinks require one filesystem; symlinks require OS permission. There is no silent fallback after a link failure. Sparse metadata remains compressed and member listing is paged.

Repeated browser or server queued check-ins retain the `latest` snapshot code: update its definition and register new File objects through native FileAppendCheckin. Old File records are deleted through SObject; FileUndo removes only paths absent from the new group and their sidecar links. Matching paths have already been replaced by journaled staging and are not removed again. Numbered versions remain intact, check-in/File triggers and permissions still apply, and failures roll back rows and file contents. Existing latest snapshots are updated instead of deleted/recreated; an explicit DeleteCmd still deletes the whole group. The Handler client and its ordinary inline procedure are unchanged.

Server queue assembly retains the original file extension so IconCreator selects the native image or video handler. Unknown binary extensions such as `.toc` skip preview generation; an explicit preview image is processed as before. Known damaged images still produce warnings, and extensionless files still reach the image decoder.

Browser File handles are kept in memory. Recovery stores metadata per login in `tactic_stream.commit_queue.<login>`; it cannot restore file permissions. Pattern preferences are stored in `tactic_stream.matching_templates`. These names document implemented mechanisms, not additional server APIs. SQLite/native scripts/Chromium are verified; production PostgreSQL/MySQL and physical phones are separate acceptance checks.

## Task collaboration containers and native commands (0.112.34)

TaskManager.vue owns filtering, selected task identities and local create/edit/schedule plans.
TaskWorkspaceCmd reads the configured catalog, TaskWorkspaceEditCmd prepares validated plans and
saves them, and TaskScheduleCmd projects and commits schedules. Quick process cards and compact
rows use these same commands; they do not invent an independent task store.

NotesPanel.vue owns the Inspector's object/process/exact-task context, drafts and revision guards.
TaskInspectorHeader.vue and TaskDetails.vue present data and emit actions. TaskInspectorCmd combines
native task fields, process choices, related task counters, WorkHoursSummary and notes/history.
DiscussionReadCmd/AddNoteCmd/ChangeNoteCmd handle canonical note targets and ownership. Rich identities
are read in batches. DiscussionReadCmd returns the authenticated current_user; NotesPanel uses
that identity for local text draft keys rather than persisting an expiring ticket. Text restoration
checks the exact target; file handles and reply selections stay in memory. Parent/process notes and secondary task notes remain distinct, while process
counters include both. Refresh runs every 30 seconds only in an active Inspector; it keeps dirty
values and the original save revision. Delayed responses cannot write into a changed target.

Attachment-only notes use FileCheckin inside Command, with FileUndo and generated preview metadata.
Chat attachments and own profile avatars retain their validated owner scope and the existing edit
permission for repository rows. Bare version-lock probes preserve Checkin:writing's parent rather
than pretending to be partially initialized snapshots. Parent/project/file anchors, private download
membership, deletion permissions and transactional rollback still apply.

HTTP validates the complete request before using the system namespace for explicitly empty project
values on Messages, updates, profiles and link reads. Missing/null project values are still invalid.
Project-bound link targets still require their selected project and current rights. This global
communication context does not choose or persist an admin project for the workspace.

Configured task and Discussion UI commands currently require admin. Public SDK permission contracts, real production
DB vendors, hardware/browser variations and complete API coverage are separate acceptance work.
