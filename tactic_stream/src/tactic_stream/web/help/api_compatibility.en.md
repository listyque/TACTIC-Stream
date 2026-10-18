---
group: Guide
icon: code
order: 91
---
# Core and API compatibility

> The catalog contains 129 original exposed TACTIC methods. Release 0.112.40 has 127 available entry points and two exclusions. Availability and matching signatures do not prove every argument or side effect. `full_api_parity_verified` remains `false`.

## Inspecting a method

The API reference contains original signatures/docstrings, EN/RU explanations, input fields and JSON execution. Python examples use the original XML-RPC SDK. `/api/documentation` exposes the same catalog; `/api/compatibility` lists methods, Handler call sites and limitations. JSON and XML-RPC share the core, but their response formats can differ.

For example, original XML-RPC `query` returns a Python literal string. `TacticServerStub.query` decodes it into records; JSON and the local SDK return records directly. When using `xmlrpc.client.ServerProxy`, account for this original representation rather than treating string length as object count.

The running server imports neither the `legacy` directory nor Handler. Native `pyasm`/`tactic` classes live in the package. Original sources are references for inspection and isolated tests only.

## Native execution paths

| Area | Mechanism | Important boundary |
| --- | --- | --- |
| Authentication and reads | Ticket, Security, Search, SearchKey, Select, Schema | Project/type/column/parent rules remain in the core; direct SQL does not bypass policy |
| Objects | insert/update/batch, get_unique_sobject, clone, retire/reactivate, delete | Writes use Command/SObject; system editors still require an administrator |
| Relations | parent, instance, connection, hierarchy, dependencies | Direction, project, relation type and permissions are checked; unsupported variants fail explicitly |
| Tasks and notes | Task, Pipeline, Workflow, Note, Discussion | Parent/author permissions, states, logs and triggers remain native |
| Files | Snapshot, FileCheckin, FileAppendCheckin, FileGroup, FileUndo | Ticket uploads, versions/revisions/versionless, locks, naming, metadata and rollback; Repository Sync and S3 excluded |
| Server scripts | PythonCmd, local TacticServerStub, native imports | Python requires an administrator or an explicit `api_cmd` grant and project access |
| Configuration/admin | XML configs, SearchType/schema, widget definitions, users/groups, plugin installation | Browser metadata is not presented as original HTML widget output |
| Undo | Command, Transaction, SObjectUndo, FileUndo | SQL, journals, triggers and files must complete consistently |

`missing_method(func, args)` preserves the original diagnostic `False`. It does not execute an unknown operation. Calling an unknown RPC by name still returns Fault 501. Diagnostic fallback arguments are omitted from request logs.

## Ordinary account permissions

Object methods do not require an administrator merely because of their names. Current project, object and column ACLs decide access. A reader cannot create or modify an object/snapshot; denying `s_status` blocks retirement. Accounts, system settings, arbitrary commands and script execution have separate protections.

Check-in write authority is tied to a visible parent. Remote XML-RPC and the local SDK inside PythonCmd use the same check. Nested calls restore previous authority. Snapshot authors come from authentication; changing the parent/project cannot bypass access rules.

Internal RetireLog creation retains the current author and native generated code. This does not authorize arbitrary `insert('sthpw/retire_log', ...)`. A later failure rolls back both the object and its log.

## Transactions and file rollback

Project-defined SObject classes retain the original `fast_data` constructor fields and retry without `fast_data` after a constructor exception. Native TIME support additionally supplies `time_cols`; the batch class-resolution cache stays internal. Nullable SQL defaults are skipped when no value exists; this lets native plugin undo/redo apply the remaining defaults instead of failing on `set_value(None)`.

Browser task workspace responses retain the original task/parent fields and add explicit `__process__`, `__status__`, `__hours__` and parent `__preview__` metadata for the visible process controls, time summary and previews. These additions are checked separately from the unchanged Handler procedure.

Original SDK `server.start/finish/abort` and local Command use native Transaction. Server Python inside a command does not open independent HTTP transactions for nested calls. A late failure rolls back previous edits and snapshot creation.

FileUndo reserves payloads under `temp/undo`, separate from ordinary `temp/cache`: undoing creation of a cache directory must not erase its backup. Directory creation, move/copy, file replacement and versionless links have distinct journal nodes. Distributed atomic commit across physical databases is not claimed; partial commit failures are reported explicitly.

File operations stay within verified repository/ticket paths. Versionless links are optional in Configuration. They do not enable Repository Sync or S3. See **Check-in**, **Drop Plate** and **Commit Queue** Help for their controls and limits.

## HTML and server JavaScript contracts

The five entry points `set_palette`, `get_widget`, `get_column_widgets`, `set_application_state` and `execute_js_script` are available. Native HTML/palette/buffer processing, column cells, top_layout state and original JsCmd/custom_script lookup are restored. QuickJS-NG replaces PyV8; Script Editor and Script Shelf expose server JavaScript.

By user decision on 2026-10-11, further migration of the full old HTML application/table shell and grouped/hierarchical HTML is excluded. Existing working methods and common dependencies remain. Missing widget classes still fail explicitly. JavaScript is synchronous and administrator-only, with no browser/DCC/PyV8 Python-object bridge. See [Native HTML and server JavaScript API](help://html_api) for arguments, SDK examples, source quirks and verification boundaries.

`commit_session` and `get_md5_info` belong to the excluded deprecated production layer. Repository Sync, S3, desktop/DCC connections and old UI URLs are also outside the transfer.

Available methods still have unsupported variants: SQL/expression forms, remaining deletion dependencies and widgets. These must fail explicitly before an unsupported write. Dictionary API `info` is supported. The delivery block checks SQLite, real PostgreSQL 18.6 and the supplied `cg.zip` on private fixtures; it does not migrate or certify the user's production databases. MySQL is deferred by user decision. Windows symlink checks are skipped if the test process lacks the OS privilege to create links. See [Installation, updates and acceptance](help://delivery).

Some corrections intentionally differ from source bugs. Unknown timezones are rejected instead of silently using the machine timezone. Read-only Select execution retains denied-type filtering and empty results; copying SQL state does not grant administrator authority.

## Reproducing verification

Run `.venv/Scripts/python.exe -B -X utf8 tools/verify_api.py` from the application directory. It runs the existing unittest suite against private fixtures and writes `.screenshots/api-block6-runtime.json`: test outcomes and successful/rejected call counts per method. Arguments, tickets and user data are never recorded. Pass unittest module names to run a narrower set.

Counts establish exercised entry points, not every method branch. Direct native calls and child-process calls are not counted. Use `--output <file>` to retain separate reports without overwriting an earlier run. `tools/audit_api.py` refreshes current static Handler call sites; that inventory is not runtime coverage either.

Tests use the unchanged SDK and freshly extracted Handler procedures: extended check-in, batch naming, note history/editing, chat lifecycle, permissions and late rollback. Eight changed Handler reference files were reviewed separately. Their hashes identify references but do not by themselves prove GUI equivalence.

## Command metadata and bound command keys

`insert`, `update` and `insert_update` accept an `info` dictionary. Native ApiXMLRPC accumulates this request-local metadata and its affected SObjects; ApiClientCmd passes them to command listeners along with `function_name` and `args`. This is command metadata, not extra database columns or the method's wire result. A later RPC starts fresh. Invalid non-dictionary info is rejected before an object write.

```python
row = server.insert('cg/assets', {'name': 'Prop'},
                    info={'label': 'Create prop', 'source': 'browser'})
server.update(row['__search_key__'], {'description': 'Reviewed'},
              info={'phase': 'review'})
```

`HtmlElement.generate_command_key(class_name, kwargs)` binds a native Command class and fixed arguments in the current user's ticket directory. `execute_cmd('$key', args, values)` merges caller arguments with the bound ones: bound arguments win; `values` populate the original Web form. A key cannot change the class's access policy or be transferred to another account/ticket. Classes requiring a key cannot be called directly by name.

`use_transaction=False` runs `cmd.execute()` directly, skipping the nested Command's preprocess/postprocess/listener hooks. It does **not** make the outer API write non-transactional: a later exception still rolls back its writes. Generate keys only in trusted server code; the API reference accepts an existing key, not arbitrary widget creation by a reader.

## Native SQL Delete and palette expressions

Server Python can import `Delete` from `pyasm.search`, just as it imports Select/Insert/Update. It supports `set_database(Sql or DbResource)`, `set_table`, `add_filter(name, value, op)` and `get_statement`. Execute it with `Sql.do_update(delete)` inside an authenticated Command. Raw writes require administrator access and the correct resource, and fail inside a read scope.

```python
from pyasm.search import Delete, DbResource, DbContainer
resource = DbResource.get_default('cg_test')
delete = Delete()
delete.set_database(resource)
delete.set_table('scratch')
delete.add_filter('code', 'DEMO')
DbContainer.get(resource).do_update(delete)
```

The example assumes an existing disposable table. Do not use raw Delete for ordinary object deletion: it bypasses SObject triggers, dependency cleanup and FileUndo. Use `server.delete_sobject` for those operations. Stream fixes the source builder's trailing `AND`, quotes literals, treats equality with None as `IS NULL`, and rejects an empty filter instead of allowing a whole-table wipe.

`@COLOR(color)`, `@COLOR(#123456,10)`, `@PALETTE(DARK)` and `@GRADIENT(background,5,-10)` use the native request palette. Unknown color names retain the original fallback color; they are not database expressions. Gradient offsets/ranges accept data literals; arbitrary Python evaluation is excluded. Headless server calls can generate a gradient without an HTTP Web adapter. These expressions do not change the Vue theme.

## Verified variants and remaining boundaries

| Variant | Evidence / current boundary |
| --- | --- |
| Dictionary info, affected SObjects, request isolation | `test_api_remaining`: same original method bodies and native results; listener and invalid-input checks |
| Command keys, bound args, form values, direct mode | Same original calls; identity, resolved-class policy and late rollback tested separately |
| Delete SQL builder | Source comparison exposes and corrects dangling AND; quote/NULL/empty-filter/read-scope/rollback checks |
| Palette expressions | Same expressions in original runtime and Stream; unsafe arguments rejected |
| Snapshot level deletion | Real files and alias rows: rollback restores bytes; removing one level retains other levels and the default aliases; source level-selection bug is corrected |
| Named `view_as_attr` XML | `add_config_element`/WidgetDbConfig reload and reorder `<view name="...">`, including names without @; separate from HTML rendering |
| Other method branches | Existing SDK/native suites exercise reads, writes, schema, workflows, files, queue, configuration and undo; no claim of exhaustive branch parity |
| Raw Select filters / serialized replacement / cross-resource joins | Some forms remain unsupported; replacing a protected Search's resource or escaping ACL/read scope is a security boundary, not a migration task |
| Domain dependencies, expression relations, workflow events | Unsupported classes/types/events still fail explicitly; an available method is not support for every possible domain |
| Remote/multi-site resources and distributed commit | Not certified; local SQLite and PostgreSQL do not imply remote replication or atomic commits across databases |
| Executable Mako widget configurations | Not migrated; declarative XML metadata continues to work |
| QuickJS vs PyV8 | Native synchronous JS client preserved; async/DOM/DCC/arbitrary Python objects excluded; original PyV8 engine not tested |
| Full old HTML shell, S3, Repository Sync, deprecated production layer | Explicit exclusions; existing working HTML methods retained |
| MySQL | Deferred; no driver or acceptance claim |

For source-level diagnostics, run `tools/audit_api.py --contracts-output .screenshots/api9-contracts.json`. It records every explicit UnsupportedContract guard's module, function, line and source message. The inventory includes protections and agreed exclusions as well as missing variants; its count is neither a missing-feature count nor runtime coverage. Pair it with this matrix and `tools/verify_api.py` evidence before extending a contract.

## Browser API console and journal details

The API console retains its existing authorization, validation and explicit request execution. Filtering, method rows and parameter fields use Frame controls. Closing it cancels a pending catalogue read and clears its temporary credentials; an already submitted API operation may still finish on the server. Transaction details retain server-filtered XML and hidden-record notices; a late copy completion cannot update another transaction. These are browser capabilities, not additional native Handler windows.
