# Perforce-like file projects: installation and acceptance

This feature uses new `file_project` projects alongside Classic projects. Handler
provides the working desktop; Stream provides inspection and administration.
The builtin `perforce_like` template ships in the server wheel; no database dump
or separately downloaded template is needed. Never change a Classic project's
type to install this mode.

## Installation

1. Back up the system database, every project database, configuration and private
   blob storage together before upgrading. On a fresh Python 3.14 installation,
   install the supplied wheel (`python -m pip install "./tactic_stream-VERSION-py3-none-any.whl[postgres]"`
   for PostgreSQL; omit `[postgres]` for SQLite). Existing installations use
   `python -m tactic_stream --data-dir PATH upgrade` with their own configuration.
   A new installation first uses `python -m tactic_stream --data-dir PATH init`;
   enter its new administrator password interactively.
2. In Stream Configuration, enable `files` alongside the current `tactic` and
   optional `queue` services: `services/enable=tactic|queue|files`. Save, then
   explicitly stop/start the server during a maintenance window. Save itself
   does not restart anything. The `files` worker performs verification, staging
   and retention/GC. Check the monitor's running services after restart; a
   configured service is not proof that its process is healthy.
3. Create a **new** project in the project wizard using **Perforce-like file
   project**. The native equivalent, on an authenticated administrator client
   whose current project is `admin`, is:

   ```python
   server.execute_cmd('tactic.command.ProjectTemplateInstallerCmd', {
       'template_code': 'perforce_like', 'project_code': 'files_demo',
       'project_title': 'Files Demo',
   })
   ```

   This goes through the existing Command/CreateProjectCmd/schema installation.
   Reusing an existing project code fails; the template does not overwrite it.
4. Create depot(s), a main stream and workspaces in the file project's Workspace
   actions. Bind each depot to an existing writable repository alias. Private
   blobs live in its sibling `NAME.file-projects`, outside public asset aliases;
   an unbound depot uses `DATA/file-projects`. Give the service account access to
   those directories. Database-only backups cannot restore file contents.
5. Grant users native project/search-type permissions and `file_depot` view/edit
   access for the intended project/depot. Test with an ordinary user: read-only
   users must not upload/checkout/submit; one user's tasks and pending changes
   must not become writable by another. Service execution rechecks the original
   owner's rights; it never publishes their files as administrator.
6. Extract the supplied Handler **source runtime** into a fresh application folder.
   Install its pinned `requirements.txt`, then use `launch.py`/`launch.pyw` and
   the existing server preset/login screen. No saved tickets/settings are shipped.
   Select the new project, create/select your workspace and set its local root.
   Use normalized depot-to-local mappings and exclusions; separate workspaces
   for independent clients. The Classic project keeps its Classic Commit Queue.
7. Set byte/file quotas, parallelism and retention in Stream Storage
   administration before a large run. Defaults are unlimited quotas, 4 byte
   transfers, 7-day abandoned-upload/task retention, 30-day reverted retention,
   permanent shelves and history. GC must preserve published history, shelves,
   Have and active tasks. Start with GC dry-run; never manually delete blobs.

Apache must proxy `/file-project/` as well as the normal API, preserve Range
responses, and permit streaming bodies of at least 64 MiB. Client metadata is
bounded to 1000 entries/3 MiB per command; data batches/blocks are bounded to
64 MiB. Use PostgreSQL for shared installations; SQLite serializes writers.
There is also a project storage-policy lock for quota/reference/GC fencing:
parallel byte transfer does not imply parallel publication transactions.
Contention before the storage-policy lock is acquired returns a marked HTTP 503;
the SDK repeats that same metadata request with bounded backoff. The worker keeps
the queued/running task on temporary contention. This does not retry arbitrary
503 responses, failed triggers, checksums or permission errors.

## Daily operation and recovery

| Scenario | Required result |
| --- | --- |
| Reconcile | Explicit scan shows new/modified/missing files against Have and current server content; hashing stays off the UI thread. |
| Checkout | Ordinary checkout permits multiple holders; exclusive checkout rejects another holder. Locks do not overwrite local files. |
| Upload | Aggregate files/bytes and current path are visible. Upload stages a draft; Submit separately publishes the whole changelist. |
| Shelve/unshelve | Shelf bytes/revisions remain immutable. Unshelve creates a bounded integration; resolve conflicts and finish before Submit. |
| Submit failure | Native rights, hooks and the complete changelist transaction are retained. No subset is published. Refresh before deciding whether to retry a lost response. |
| Get latest | Pinned manifests, SHA verification, durable local replacement, then Have acknowledgement. Modified/untracked local content is protected unless explicitly forced. |
| Stop waiting | Cooperatively stops client work, retaining the server task/journal/partial bytes for Resume. It is distinct from cancelling the server task. |
| Cancel server task | Cancels staging and restores the original pending draft; confirmed published data stays intact. Large integrations may need multiple cancellation chunks. |
| Connection loss | Sign in again if needed, keep the workspace root and upload journal, then Resume. Never create a replacement task merely because a reply was lost. |
| Worker/server restart | Durable tasks are discovered after restart. Retried offsets, manifests, seal, submit and Have do not duplicate versions. |
| Local source changed | Resume refuses a changed source fingerprint. Cancel the old task and start a fresh transfer for the new data. |
| Quota/checksum/ACL failure | Show the server error; do not publish. Correct the cause, inspect the retained draft/task and retry or cancel explicitly. |

Uploads keep their SQLite journals outside the workspace. Do not remove journals
or `.tactic-BLOB.part` download files when you intend to resume. If `files` is
disabled, new uploads fail before server allocation; completed uploads can still
be inspected/retried. Enabling it requires an explicit server restart. A temporary
worker failure with `files` enabled remains resumable and is visible in monitor
status and task progress.

## Qualification and release limits

Archive uploads read at most 1000 blob records in one native Search query. The
storage-policy and changelist locks cover transfer and legacy upload writers;
each blob retains its native edit authorization, SHA verification and commit
hooks. A failure rolls back all metadata and new private bytes in that batch.
Marked storage contention is retried for at most 120 seconds per command/block,
with visible waiting progress and cancellation. Failed upload lease cleanup
also retries marked contention; expiry remains the fallback after worker/network
loss. Ordinary permission, checksum and hook failures keep their refusal/rollback.

Run `tools/file_project_checks.py` (SQLite) and `--postgres` (a new disposable
PostgreSQL container), `tests/test_file_workspace_ui.py` (real Edge browser),
`tests/test_handler_file_workspace_ui.py` (real offscreen Qt), and
`test_monitor.Runtime.test_owned_file_worker_restart_and_real_transfer`.
`tools/file_transfer_benchmark.py` creates fresh random bytes and verifies an
HTTP upload/submit/download/Have roundtrip. `tools/file_project_scale.py` measures
catalog/version/Have metadata; it does not transfer a million physical files.
All fixtures own their resources and remove their processes/containers afterward.

The delivery's `verification/` contains portable native/transfer/monitor fixtures.
With the wheel installed, run `python verification/tools/file_project_checks.py`;
add `--postgres` for the disposable Docker checks. For worker recovery, set
`PYTHONPATH` to `verification/tests` and run `python -m unittest
test_monitor.Runtime.test_claimed_upload_recovers_after_file_worker_process_death`.
Its injected process death leaves a committed 60-second task lease; recovery is
bounded by that lease, not instantaneous. SHA-256 for each supplied file is in
`manifest.json`; the qualification report is separate from manual acceptance.

On the checked Python 3.14/PySide6 6.11.1 and 6.11.2 runtimes, enabling Python
ResourceWarning diagnostics reproduces an uncollectable `Property` at interpreter
shutdown even with one plain QObject property and no application/network/threads.
This warning is not suppressed or counted as a clean resource-acceptance pass.
The regression fixtures still stop their workers and delete their owned windows.

The delivery contains a server wheel, Handler sources and recorded evidence.
It is **not** a Windows EXE/Electron or a production acceptance certificate.
Physical million-file/TB runs, the target network/storage, installation on a
clean target Windows machine, and full Handler manual release acceptance must
be signed off separately. Keep the existing application release gates; never
mark those scenarios passed from an offscreen or metadata-only test.

## SDK sync outcomes

FileTransferClient.download returns state=complete on completion. A modified or
untracked local target returns state=blocked, reason=local_modified_or_untracked,
path and the existing task ID without throwing or overwriting that file. SDK
callers must inspect state before reporting completion. Preserve local changes
and retry with the retained task after resolving the conflict; the API does not
silently enable force. Unexpected transport/integrity errors still raise.

## Historical sync API

Handler 0.6.0.34 / Stream 0.112.71 add native `revision_snapshot` and
administrator-only `revision_upgrade`. New projects include change indexes on
`stream_code/state/submitted_revision/submitted_at` and version indexes on
`stream_code/path/number`; existing projects upgrade through native schema APIs
and at most 1000 SObjects per resumable transaction. Rights and triggers remain
active; a failed trigger rolls back metadata and the upgrade cursor together.
Legacy rows can only recover their existing second-resolution timestamp; new
submissions retain microseconds. No Classic schema is altered.

SDK `download(workspace, root, ...)` and native `sync_begin`/download
`transfer_begin` accept one of `file_revision`, `changelist`, `revision`, or
`at_date`. Changelist is its public number or code; `revision` is the submitted
stream counter; `file_revision` is #N independently for each selected path.
Use `paths` for bounded explicit local paths, `prefix` ending in `/` for a
recursive local subtree, and `source_stream`/`source_depot` for a mapped root.
Mappings and exclusions still apply. Date-only selectors include the UTC day;
ISO timestamps may include offsets, otherwise UTC is used. A folder's submitted
state can remove previously synced files that did not exist then; unavailable
per-file #N leaves that path/Have intact and returns `missing_revisions` plus
an example `missing_path`.

`force=True` must be explicit. It re-downloads even when Have matches, repairs
missing/dirty targets and permits selected tracked removals; preserve local
changes first. A matching blocked task is atomically restarted for Force.
Another scope/root/revision must be completed or cancelled before starting.
For Force, repeat the scope rather than passing an old SDK `task`; ordinary
resume retains its task ID. Expected dirty-file results remain `blocked`.
Small archives and ranged large downloads read the pinned sync manifest,
never a concurrently advanced Head. Have is acknowledged only after verification
and local replacement. A write racing with download is still rejected.

The full download dialog lives in Handler; Stream shares inspection API/SDK and
Help. Physical million-file/TB and PostgreSQL acceptance are not established by
these temporary SQLite/HTTP/QML tests. Case-insensitive subtree scans currently
scan their mapping in bounded pages; they do not yet have a folded prefix index.

## Recursive checkout metadata

Handler 0.6.0.35 / Stream 0.112.72 send folder drops as native `checkout`
arguments: `directories` contains source prefixes ending in `/` (or `""` for
the stream root), and `local_directories` contains workspace prefixes. Optional
`paths` retains the existing explicit-file contract. The combined input contains
1..1000 roots; descendant files are not expanded on the client. Overlapping
source/local prefixes and explicit files are deduplicated against the target
change's immutable `base_root`. Excluded/unmapped paths are skipped; read-only
mappings, ownership and ordinary/exclusive locks keep their native checks.

The server processes at most 1000 paths per chunk in the existing command
transaction, saving the change/edit revision once. A late lock/trigger failure
rolls back every preceding chunk and its locks/pages; the same request ID may
retry after rollback and returns its receipt after success. The result's `paths`
field is the opened-file count. This is metadata checkout; it transfers no file
bytes and does not publish a changelist. Folder contents follow the base revision;
rebase the target if newer Head files are needed. Classic is untouched.

Verification includes 1105 descendants, overlaps, mapped exclusions/read-only
denial, late second-chunk conflicts and trigger failures, idempotent retry, real
Handler Qt drag/drop and Stream Chromium drag/drop. Million-file checkout has
not been certified: the current command remains one potentially long database
transaction, and local-folder filtering can scan its source catalog in pages.
The existing PySide6 shutdown ResourceWarning remains recorded.

## Lifecycle source delivery (0.112.75 / Handler 0.6.0.37)

Deploy server and Handler sources together, restart their existing launchers and
reload the web UI. The new inspector/lifecycle commands require the matching
server. This change does not restart or alter production services automatically.
Files Details / Checked Out By / Preview and server comparison are available in
both clients; local watching, Reconcile, filesystem permissions and external
comparison remain Handler responsibilities. Classic keeps its existing path.

The native `change_preview`, `integration_preview`, `compare_shelf`, `update_shelf`,
`offer_change`, `accept_change`, `resolved_files`, `undo_resolve`, `file_info`,
`file_preview`, `compare_files` and `transfer_items` actions use existing
Command/Search/SObject/security boundaries. Shelf replacement is optimistic and
archives prior contents. Publication remains whole-change atomic. Handoff still
uses one transaction; a million-file handoff needs separate bulk-job acceptance.
Old pending summaries can be upgraded through paged `index_change` before submit.

The complete 124-item scope and evidence are in
[FILE_WORKSPACE_UI_PLAN.md](FILE_WORKSPACE_UI_PLAN.md): Stage 2 has 29/35 accepted
requirements. The other six remain open, including complete recovery and progress
qualification. External viewer copies are intentionally retained in the client
workspace cache; failed copies are removed. Viewer installation/launch,
PostgreSQL production, million-file/TB and packaged deployment are not certified.

## Stage 3 native batches and the editing flow — 2026-10-13

In Handler, right-click empty Pending space to create a numbered changelist.
Drop Depot files/folders onto it to open their mapped local copies for editing;
missing copies use the changelist base revision and existing local bytes are kept.
Double-click a pending file to launch its associated editor. Local notifications
also update the expanded changelist. Submit/Shelve first prepare actual edited
opened files, then show the server review. Files outside this changelist are not
included. Edits after review or a different native edit revision invalidate the
approval rather than publishing stale bytes. Preparation can transfer bytes even
if the subsequent review is cancelled; publication still requires Submit.
Stream keeps its remote inspection/admin role and the matching background menu.

Whole server selections now use native `select_query` and `bulk_begin` instead of
client loops over a million paths. The selection pins an immutable catalog root,
prefix, optional inclusive `start_path`/`end_path`, name and action filter.
`bulk_begin` takes `selection`, `operation`, `change`, `edit_revision` and a stable
`request_id`; checkout also takes `mode`, and move takes `target_change` and
`target_edit_revision`. Supported operations are `checkout`, `move_files`,
`remove_files` (selected revert) and `mark_delete` (staged until Submit).
The existing files service owns the job; `bulk_status`, `bulk_tasks`, `bulk_items`
and `bulk_cancel` inspect/control it. Private worker commands are service-only.

Each job uses bounded 1000-path native operations in one database transaction,
with the ordinary rights, checkout and trigger machinery. A late failure or
cancellation rolls back every chunk. Rename pairs must be selected together.
Progress says Applying until commit; processed paths are not durable publication.
Stop waiting retains the server job; explicit Cancel signals it without waiting
for SQLite's write lock. A lost commit reply is reconciled against the same task.
The worker pool is bounded. SQLite still serializes project writes during a long
atomic mutation; million-path atomic-job duration/memory are not certified.

Mappings/exclusions have a structured editor and native path preview. Cancel
restores the active workspace settings. Switching previews pending changes and
active transfer/bulk work; it keeps that work in the previous workspace. Handler
checks absolute roots, directories, symlink ancestry and available space before
saving local setup. These checks do not reserve disk space for a future download.

Fresh SQLite catalog benchmark: **1,000,000 logical files**, 1,000,000 version
records, 1,000,000 checkout records and **two small physical payload files**.
Native build: 1717.54 s; peak process memory: 73.64 MiB; first/tail 1000-file pages:
10.53/12.12 ms; Have acknowledgment of 1000 paths: 26.89 ms. After that catalog,
editing 1000 new staged versions took **1717.19 ms**, final Submit **19.67 ms**.
The combined preparation/publication target below one second is not achieved.
This is neither a network/TB benchmark nor a million-path single atomic mutation.
See `benchmarks/file_project_scale_2026-10-13.json` for the recorded data.



Stopped downloads are now recorded on the server as `blocked`, including local edit conflicts and recoverable download errors. Retrying the same selection resumes its pinned task. Requesting another file, folder or revision in the same workspace and local root replaces the stopped task atomically, keeping local edits, partial files and confirmed Have entries. A download still in progress or belonging to another local root is not replaced implicitly. Stream displays the stopped task in Transfers and can cancel it. Tasks left active by an older client, a killed process or a fully lost connection may need cancellation in Transfers before changing the selection.

Menu permission hints use native Security. Depot/stream listing and
`stream_status.writable` describe current depot edit access; file-state and
changelist metadata carry `depot_writable`, independently of catalog pagination.
`file_states.writable` still describes the workspace mapping. Both restrictions
apply to editing. Hints are cached display information, never authorization;
every mutation rechecks native permissions, revisions and locks.

Handler 0.6.0.47 / Stream 0.112.95: workspace switching retains prior pending
work, Have, local bytes and server jobs, rejects unsaved descriptions/stale
confirmation and clears workspace-bound presentation/cache references. The
shared download SDK checks absolute roots and available space per bounded page.
`transfer_pause` accepts `insufficient_disk_space` with nonnegative client-reported
`required_bytes`/`available_bytes`; these are informational estimates, not server
storage quota reservations. Native owner/depot/ack-revision guards and triggers
remain authoritative. Retry clears the old space estimate and resumes the pinned
task without acknowledging unreceived paths. Earlier confirmed pages retain Have.
Restart Stream manually after updating its sources; no production restart is
performed by the verification helpers. Browser scope remains inspection and
administration; the full working file interface is the standalone Handler.

## Recovery, catalog views and bounded retention

The toolbar shows **Resume interrupted operation** after an interrupted upload,
download or local rename. Journals are scoped to server, login, project, workspace
and local root; they contain no ticket. Resume uses the original selected sources
and native task/receipt. A lost successful Submit response reads the submitted
change instead of publishing again. A pending Submit returns to Review. Keep the
workspace cache and upload journal until recovery completes; do not point a
foreign journal at another workspace. Repeated Explorer import during recovery
accepts only byte-identical copied destinations and preserves other local edits.

Rename moves local dirty bytes after the native rename succeeds. If the local
move is interrupted, **Resume local moves** replays its receipt and completes the
same move; an existing different destination is never overwritten. Reconcile
updates local/Have/Head state and per-change unstaged file/byte counts. After a
watch event or changed server edit revision, unknown counts explicitly request
Reconcile rather than rescanning millions of files on every click.

**View** opens Workspaces, Streams, Depots, storage inspection and **Stream
Graph**. Lists are paged; graph nodes and connections are bounded and pinned to
the current submitted heads. Branch/merge links refer to actual published changes.
Refresh when the graph's heads change. Graph zoom and normal tab/column/splitter
preferences restore; deep expanded folders and selected files outside the first
page are sought directly. Trees retain at most 8192 rows, changelist children
8000 across loaded changes, 1000 per change, and 128 file-page cursors. Reopen a
released branch to reload it; whole queries still run on the server.

The operation footer distinguishes scan, manifest, upload, verification, staging,
download and submit. Rate and ETA use measured byte progress only after a real
sample interval; they reset between phases. The last staging chunk waits more
frequently, without increasing polling throughout a million-file job. File errors
show the path plus overall failure in the Log; Debug Log retains diagnostics.

Stream exposes inspection and administration. Its file-project panel has no
checkout, local edit, shelve, submit or bulk transfer commands. Ordinary Search
tabs and administrator managed-record inspection remain available. No browser
view infers the state of a desktop file.

## Desktop Submit contract

Handler 0.6.0.71 uses the dedicated Submit dialog with Stream 0.112.118 or newer.
`update_change` and `submit` accept `description`, boolean `restricted`, at most
100 `task_codes`, and `task_status_updates` (`code`, configured `status`, reviewed
task `revision`). Task candidates come from `submit_tasks`; its initial page also
returns linked tasks outside that page. `submit_shelves` scans bounded pages of
the owner's shelves and returns snapshots linked to the pending source change.
Related shelves keep their separate identities and are read-only in this dialog.

`submit_options` contains boolean `selection_all`, at most 1000 `selection_paths`
(exceptions when selecting all; inclusions otherwise), `unchanged` with values
`submit`, `revert` or `leave`, and boolean `reopen` / `guard_resolved`. Selection
must include both sides of a rename. The native Command streams the work catalog,
moves excluded/remaining files into a new pending change, publishes the selected
set, and optionally reopens published paths. All metadata changes roll back if
publication fails. Uploads are staged before that atomic publication boundary.
The SDK stores review/selection on disk and uploads selected dirty paths only.

Restricted metadata is readable only by its owner or administrators; file
history omits its description for other users. Published bytes still follow
depot permissions. Task links are part of changelist metadata. The desktop calls
`submit_task_status` after successful publication; it uses normal task commands,
field/process/status permissions and triggers. It intentionally does not add
system-database task writes to the project-database publication transaction.
Failed task updates leave the files submitted and appear in Log; explicit retry
accepts already applied statuses but rejects concurrent task edits. A crash
between publication and task updating requires that retry from the submitted
changelist. Save/Apply change metadata only, never bytes or task statuses.

`tests/test_file_submit.py` covers selection, rollback, privacy, native task
updates, stale task revisions, unchanged policies, post-resolution edits and
fresh selected-only HTTP uploads. The Submit scenario in
`tests/test_file_workspace_layout.py` exercises real Qt EN/RU layouts and
Cancel/Apply/Save/reopen/Submit with an isolated HTTP server. These checks do not
certify production PostgreSQL deployment or physical million-file/TB workloads.
