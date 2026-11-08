---
reference: Handler
group: Workflows
icon: publish
order: 15
---
# Check-in and Commit Queue

> Check-in tools prepare files, metadata, naming, previews, and repository destinations before
> submitting operations to TACTIC.

## Main controls

Save snapshot leaves Context empty when no separate context was chosen; the queued operation uses the selected process. Explicit contexts are preserved. Revisions and attachments keep the existing snapshot context. On phones, Back uses the same unsaved-file guard as Cancel, the file controls and filename switch are compact, and Cancel/Add to Commit Queue stay at the bottom while the form scrolls.

In the phone item browser, Upload on an object/process prepares a check-in with that context.
Upload on a snapshot instead attaches to its existing physical version using native `add_file`,
then updates versionless. It preserves the original file and version number. New file names
follow the project's existing native naming expressions, so versionless and physical filenames
can differ. Existing filenames are rejected; after an unknown RPC outcome, refresh before retrying.
See [Mobile application](help://mobile) for the direct file preview and version navigation.

Large text files show the beginning and a notice when the preview is shortened.
Download the file for its full contents. Supported audio and video play directly
from the web repository.

Drop Plate accepts files and matches them to objects. Naming Editor controls templates.

Commit Queue reviews prepared operations, options, dependencies, progress, errors, retry,
cancellation, and final submission. Preview images are added directly to a selected queue operation;
message and note attachments stay in their own drafts.

Dragging files over an object shows a smooth shared target for Publish and Attachment. Add Icon is
offered only when every dragged file is a TACTIC preview image: JPEG, PNG, or TIFF.

When Save Snapshot or an item drop contains multiple files, choose one grouped snapshot or separate
queued check-ins in file order. This choice applies only to the current batch and does not change
the Drop Plate default.

Dragging files onto a child relation creates one child Search Object per file, links it to the
expanded parent, uses the filename without its extension, and checks the file into publish. The new
object, snapshot, and direct or instance relation are committed together.

Before any upload, ingest checks the selected parent's existing children. Matching names pause the
batch and ask whether to update the exact existing items, skip them, explicitly create duplicates,
or cancel.

Add files on the relation opens the batch editor first. The batch editor can use project Ingest
Rules for file filters, path patterns, extra values, update matching, validation scripts, and
process scripts.

Scripts run in TACTIC with path, sobject, parent, and snapshot; the built-in Quick ingest remains
available when the optional rule table is absent. Commit Queue reveals the operation editor only
after an item is selected.

An empty queue shows a short starting hint instead of disabled settings and actions. The selected
object and snapshot preview share one summary.

The optional snapshot context branch is added or edited directly in that summary; an unchanged base
process is not presented as a custom context. Advanced options and the generated filename preview
expand on demand, and secondary preview or batch actions live in overflow menus.

Auto-clean remains in the queue header. The primary footer action submits all ready operations;
current and checked-only submission remain in the overflow menu.

Repository selectors show configured titles such as General while native codes such as base stay
internal. Process pipeline check-in modes control sequence, directory, multi-file, and versionless
behavior.

Files without an extension use the $FILENAME matching template and keep their exact name through
repository staging and TACTIC snapshot creation; no trailing dot or invented FILE extension is added.
When the selected repository resolves to the same path in Handler and TACTIC, Upload registers the
staged files in place instead of uploading and writing them a second time. When Auto-clean is enabled,
the Commit Queue removes each successful operation
and closes itself after the entire visible queue finishes without an error.

A failed or cancelled operation keeps the window open for review and retry. After a successful
check-in created in the current session, the affected branch refreshes while its parent sObject
remains selected. A publish started on the top-level sObject expands it and selects the direct
versionless `latest` snapshot without expanding its versions or the duplicate `publish` process.

Restored queue operations and completions after navigation stay silent. The existing process row
updates its disclosure state and snapshot count in place when that refreshed branch is published;
reopening the tree is not required.

When an attachment check-in creates the first attachment snapshot for an object, the result tree
adds and reveals the Attachment process even if built-in processes are normally hidden; an explicit
process-visibility filter still wins.

## Usage notes

- Review the target object, process, context, repository, and filenames before starting a queued
  operation.
- A DCC scene save prepares data; the standalone application performs the check-in.
- At narrow widths, the queue and operation panels stay inside their split bounds; secondary labeled
  actions become icon buttons with tooltips instead of overlapping the neighboring panel.
- Matching Templates keeps template rows inside their pane, reserves a scrollbar gutter, and moves
  secondary ordering actions into an overflow menu at narrow widths.

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

## Files left by a failed check-in

Check-in overwrites an existing destination file that has no registered snapshot reference. Native FileUndo retains its previous contents and restores them if saving fails. Files belonging to saved snapshots remain protected, except the existing latest/revision replacements. Inplace files staged by the client before its server command can remain after a failed command; server rollback does not remove those pre-existing inputs. Retry only failed operations, since completed queue entries remain saved.

## Template mappings

Process mapping and Context mapping in Matching Templates accept both existing
choices and typed custom values. An empty mapping applies to all processes or
contexts. Mandatory templates remain locked. Test a filename before saving;
changing templates rematches prepared Drop Plate files without publishing them.


## Full check-in from a task table

Check-in (Full) on a task or note normally targets its parent object and keeps its process and context. A numeric context suffix (for example model/001) uses the process context. A configured self target uses the task or note itself. The button prepares the existing Drop Plate/check-in workflow; it does not publish files on its own. After updating Handler Python code, restart Handler to load the corrected table procedure.

The table Check-in button toggles Drop Plate: click to show it, click again to hide it. Hiding keeps files on the plate. A plate covered by another dock tab is brought forward. Stream reopens the same target without clearing files; switching targets retains its discard check. Task Work keeps its explicit open action.
