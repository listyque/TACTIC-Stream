---
reference: Handler
group: Workflows
icon: create-new-folder
order: 24
---
# Project settings and creation

> Project Settings and the quick chooser show active, archived, template, and built-in TACTIC
> projects. Cards explain the project category, type, lifecycle, code, description, server status, and
> square repository web preview. Retired, Templates, and Built-in filters are disabled by default and
> shared by both views; their controls reflow without overlapping the project list.

## Main controls

Select and activate an existing project. Edit selected project opens a native modal editor for its
name, category, type, description, template flag, archive/reactivate state, and preview image.

In Configuration > Projects, Deactivate current project clears the active workspace without
signing out, archiving, or deleting the server project. Select a project to activate it again.
Create template archive exports the selected editable project through TACTIC's native template
command; it does not need to be marked as a template. The archive is stored on the server and
contains configuration and structure, not production objects, tasks, or snapshots. This action
is beside Edit and Create, not inside the new-project wizard. Compact layouts use labeled tooltips.

Built-in TACTIC projects are visible but read-only. A replacement preview is prepared through the
normal Commit Queue instead of being uploaded from the UI thread.

Choose image stages a replacement preview. Undo image selection restores the previous preview before
saving.

Project Editor and the creation wizard fill the native window's bottom edge without
an inset corner gap, including while resizing.

## Usage notes

- Create new project opens the native multi-step wizard.
- The four steps are Details, Preview Image, Template and Review. They use the application's
  shared MD3 navigation, grouped setting rows and action buttons. The step rail becomes compact
  in a narrow window; hover its icons to identify the steps.
- Click an earlier step to revise it. Future steps remain disabled until you advance with Next.
  Review shows the selected preview, title, code, description, category and labeled project settings.
- The action footer stays flush with the bottom window edge while resizing; the native window frame owns its outer corners.
- Enter a title (up to 100 characters) and a unique code (up to 30 ASCII letters, numbers or
  underscores, not starting with a number). Retired projects also reserve their codes.
  Add an optional description and category on the first step; both are saved to the created project.
- The optional image is uploaded when creating the project, then checked in by TACTIC.
- Choose an empty project, a server project template, an installed ZIP archive, or a built-in
  template. Server-defined names are displayed unchanged.
  The selector, template actions and explanatory note have consistent spacing inside the card.
- Details includes the Search Type namespace, template flag and main-project flag for empty projects.
  Namespace prefixes new Search Types (for example studio/shot); blank uses the project code.
  It does not rename the project; sthpw and prod are reserved.
  The Template step defaults to No theme. Themes affect only the TACTIC web interface, not
  TACTIC-Handler's appearance. Changing the main
  project may require restarting TACTIC. Template copies use their own configuration instead.
- Manage templates installs, downloads and removes server packages. Create template archive on
  the Projects configuration page captures the selected project's current configuration.
  Removing a package does not remove existing projects.
- Create project saves the project and opens it. The project catalog refreshes after creation.
- Creation uses native TACTIC commands in a background worker and is never automatically retried.
  If creation succeeds but saving its metadata or opening fails, Retry opening project completes
  those steps without creating a second project.
  If TACTIC reports a creation failure, inspect the server error and refresh the catalog before
  trying again: native creation commands can commit some changes before failing.

## File-project backend (0.112.44)

The built-in **Perforce-like file project** template creates an opt-in file_project
project using CreateProjectCmd. Classic remains the default; there is no automatic
conversion. This is a server backend option; the separate TH/TS file interface is
not connected yet. Both project types can coexist on one server.

The native command `tactic.command.file_project_cmd.FileProjectCmd` manages depot,
stream, workspace/Have, pending changelists, ordinary/exclusive checkout, immutable
file revisions and uploads. Edit chunks contain up to 1000 paths. Submit checks
the original stream revision and atomically updates the catalog root and changelist
in the project DB. Native ACL, validation and synchronous triggers apply; a trigger
requiring another database or a deferred transaction rejects and rolls back submit.
Prepared uploads survive failure. Classic global-search and system timestamp records
are not generated for this separate file domain; its revision history is native
metadata in the project DB. Classic check-in and Undo/Redo retain their existing path.

The catalog uses immutable pages of at most 256 entries, a 64-page read cache and
16-page write batches. Streams share a baseline root until edited. Sync pins a
published changelist and returns at most 1000 files per chunk. Confirm locally
written chunks with sync_ack to advance persistent progress and Have. workspace_status
and uploads recover active jobs/upload offsets after reconnecting. Use depot ACL
`file_depot` with code/project and native access `view` or `edit`, plus appropriate
SearchType/record/column permissions; draft/upload/workspace ownership is checked.
Read-only depot access allows a personal workspace and sync; modifying a stream
requires write access.

Authenticated binary HTTP uses X-Tactic-Ticket: /file-project/upload for 4 MiB raw
chunks, /file-project/download with HTTP Range for large files, and
/file-project/sync-download for a streaming tar of the current small-file chunk.
Tar includes existing files up to 4 MiB each; use Range separately for larger files
and process deleted entries from sync_next. No whole archive is assembled in RAM.
Blob storage is private under data/file-projects, with UUID-prefix directories;
classic public repository aliases are not attached yet.

An isolated synthetic million-entry SQLite catalog measured about 16 ms for root
publication and 10–11 ms for a 1000-entry page. A separate 1000-file sample (500 KiB,
distinct physical files) measured 0.98 s from uploaded bytes to submit, without the
network; the whole descriptor/upload/edit/submit path took 3.25 s. Process peak
working set for both samples was about 69 MiB. This does not measure a million
physical uploads, version records, network transfer or TB throughput. The original
0.112.44 sample did not verify PostgreSQL; 0.112.45 checks are described below.
Merge/rebase, shelve, edit leases, multiple
depot mappings, local reconcile and quotas/GC remain future blocks. Any head change
currently requires explicit conflict resolution; deep history pagination is not
implemented. upload_finish hashes a large file with one complete streaming read
before taking writer locks, then rechecks state before saving; a background verifier
is not implemented yet.

## File-core hardening (0.112.45)

SQLite and a disposable PostgreSQL 18.6 instance now verify two-user checkout/submit
races, simultaneous idempotent upload/edit/Have acknowledgements, native callback
order, revoked column/depot rights and rollback after a late trigger or failed COMMIT.
Owned child processes are terminated during upload/edit/submit and after commit;
reconnecting recovers durable offsets and safely retries a lost response.

Private-file rollback runs before releasing database locks and truncates to the
committed offset. Missing committed bytes reject the upload instead of inserting
zero padding. After a COMMIT attempt fails, uploaded bytes are retained because
the database may already have committed; query uploads/status and retry. Immutable
catalog pages use native insert-if-absent with content verification, allowing two
workspaces to build the same Have page concurrently. File-project row lock waits
are bounded to five seconds. SQL, row/column ACL and synchronous callbacks remain native.

Database ownership is checked once at atomic transaction binding; every SObject
still checks its own permissions. Existing checkout updates now use bounded native
batches, with sequential execution when configured callbacks require it. On fresh
10000-path PostgreSQL samples, edit of 1000 added paths decreased from 9.35 s to
1.97 s, and editing 1000 existing paths from 20.36 s to 5.95 s. Client network and
physical file transfer are excluded; these results do not meet a subsecond SLA.

Reproduce isolated checks with `tools/file_project_checks.py`, adding `--postgres`
to create/remove an owned Docker container. `tools/file_project_scale.py --files
1000000` drives the actual file API and verifies persisted version/checkout counts;
it shares a small payload while testing metadata capacity, not million-file/TB IO.
TH/TS interfaces, background large-file verification, quotas/GC and merge remain
separate later blocks. Production deployment and power-loss durability are not tested.

The full SQLite metadata run persisted one million versions and one million
checkout rows: root submit 17.39 ms, a 1000-entry page 10–11 ms, process peak
68.69 MiB. The run began before the latest ownership/checkout speed changes;
building all records took 26 min 7 s. This is bounded metadata capacity, not TB IO.
A separate current sample of 1000 distinct physical files (500 KiB total) took
0.95 s from uploaded bytes to submit, without client network/GUI; its full path
including upload/fsync took 9.47 s. Classic start/finish/abort journals are explicitly
rejected by this API; use changelist submit/revert instead.

### Changelists: edit, move, shelve and resolve

Only `file_project` projects expose these actions through the existing
`execute_cmd('tactic.command.file_project_cmd.FileProjectCmd', kwargs)` API.
Classic project creation and check-in do not change. The existing schema remains
version 1: shelves are immutable `change` records in state `shelved`, while
changelist contents use a separate immutable, paged work catalog. No file bytes
are copied for shelving, moving or unshelving.

`change_files(change, edit_revision?, after?, prefix?, limit?)` lists opened files,
their checkout mode, base and draft descriptor; pages contain at most 1000 paths.
Use the returned edit revision on subsequent pages to detect concurrent edits.
`update_change` changes the description (at most 4096 UTF-8 bytes).
`remove_files` discards selected pending changes and releases their checkouts;
deleting a published file remains an `edit` operation with `delete: true`.
`move_files` transfers up to 1000 paths between the user's pending changelists
in the same stream, preserving exclusive/ordinary checkout and ready payloads.
It requires `change`, `target_change`, `paths`, `edit_revision`,
`target_edit_revision` and `request_id`. A destination already opening a path or
having a different base revision for that path rejects the entire move.

`shelve(change, edit_revision, request_id)` creates an immutable checkpoint;
the source can subsequently be edited or reverted. Repeating the same request
returns the same shelf. `changes` includes the user's shelved records.
Other depot readers can use the shelf code with `change_files`, `list`, `read`,
`history` and binary download, and unshelve it into their own changelist.
Shelf history only lists revisions actually published by their originating change.

Start with `rebase_begin(change, edit_revision, request_id)` or
`unshelve_begin(change, shelf, edit_revision, request_id)`. Unshelve initially
requires the destination based on the current head and the same stream.
Both return an `integration` identifier and `after` cursor. Call
`integration_next(change, integration, edit_revision, after, request_id)` until
`complete`; each call processes at most 1000 opened paths, never the entire stream.
During integration the original draft and published head remain visible and
content edits are blocked. Ready uploads for a merged result remain allowed.
The operation is durable across restart; query `status` to resume.

Rebase compares base, draft and head for each opened path. Unrelated published
changes need no manual resolution; identical payloads and identical deletions
coalesce. For unshelve, existing local changes participate in the comparison.
`conflicts(change, integration, edit_revision, after?, limit?)` pages the remaining
conflicts. `resolve` accepts a bounded `resolutions` array of
`{path, choice: 'ours'|'theirs'|'blob', blob?}`. Here ours is the draft/shelf,
theirs is the pinned stream head/local destination. A merged blob must be a ready
upload belonging to the destination change. `read`/`transfer` accept
`conflict_side: 'base'|'ours'|'theirs'` plus the change/integration/edit revision;
missing/deleted sides have no downloadable bytes. The binary download endpoint
accepts these same fields and supports Range; it also accepts `change` or `shelf`.

`integration_finish(change, integration, edit_revision, request_id)` requires all
chunks processed, zero unresolved conflicts and an unchanged pinned stream head.
It atomically switches the complete draft and base, incrementing its edit revision.
Then `submit` atomically publishes the whole changelist. A later head change
requires another rebase; no partial submit occurs. `integration_cancel` retains
the original draft, releasing any newly acquired unshelve checkouts in chunks of
1000. Repeat with a new request ID while `cancelling` is true. Completion increments
the edit revision. Native row locks, project/depot/row/column ACL and synchronous
transaction callbacks apply to all mutations; callback failure rolls back that
request, including roots, versions, receipts and checkout changes.

All new mutations require a stable `request_id`; use a new ID for a new chunk or
different operation data. Checkout also supports request ID and optimistic edit
revision, while preserving older callers; a changed checkout updates the revision.
Existing `edit` continues using `chunk`. Previously created pending changes without
a work catalog require repeated `index_change(change)` until `complete`. This
bounded one-time migration recovers content and checkout-only paths, preserves
exclusive mode and skips unchanged catalog subtrees; large old checkout tables
may require multiple calls.

Checks: `tools/file_project_checks.py` (add `--postgres` for an owned temporary
database); timings: `tools/file_change_benchmark.py --catalog-files 10000`.
The TH/TS changelist UI, automatic text merging and TB transfers
are later blocks. Million-path capacity of the new work catalogs and production
load have not been benchmarked in this block.

### File projects: depots, mapped workspaces and real stream integration

The following opt-in file API is available through the same `FileProjectCmd`.
Classic projects and classic check-in retain their existing contracts.

**Storage.** `create_depot(code, repository?)` and
`update_depot(depot, revision, repository?, title?)` bind a logical depot to a
configured repository alias; updating a depot requires an administrator. Arbitrary
client filesystem paths and the plugins alias are rejected. Private bytes are
stored in a sibling `<repository-directory>.file-projects` directory, outside
all public repository roots. HTTP asset aliases cannot expose that namespace.
Every new upload pins its physical location. Rebinding affects new uploads only;
existing revisions remain downloadable from their original location. Omitting
the repository keeps the original private data-directory storage.
`depots`, `streams(depot?)` and `workspaces` use code keysets (`after`, `limit <= 1000`)
and native ACL. Workspaces are listed only for their owner. `stream_status(stream)`
returns the current published snapshot, revision and catalog totals.

**Views.** Pass `mappings` when creating a workspace, for example:

```json
[
  {"stream":"main","source":"...","target":"src/...","writable":true},
  {"stream":"main","source":"cache/...","exclude":true},
  {"stream":"shared","source":"...","target":"vendor/..."}
]
```

The mapped streams may belong to different authorized depots. Rules use relative
POSIX paths, `*` within a component and a final `...` for recursion. Source and
destination use the same wildcard sequence; the last matching source rule wins.
Up to 256 rules are allowed. Positive destinations must have distinct literal
prefixes; overlapping/overlay destinations are explicitly rejected. Imports
default to read-only; writable mappings still require depot write rights. The
primary stream must be included. `case_sensitive:false` uses case-folded Have
keys and rejects multiple live server files mapping to one local path.

`update_workspace(workspace, view_revision, request_id, stream?, mappings?,
local_root?, case_sensitive?)` requires no pending changes or active sync. Changing
only the primary stream retargets its existing rules, retaining imports. Mapping
changes keep Have for the next cleanup; changing the local root or case policy
clears Have metadata, without touching any local bytes. Pending changes pin the
view they were opened with. `create_change` can select another writable mapped
`stream`. `switch_workspace(workspace, revision, request_id)` updates the selected
workspace for this login/project with compare-and-swap; `workspace_active` reads
it. Requests for another owner's workspace are denied.

**Have and sync.** Existing workspace creation without mappings retains the old
single-stream sync. Mapped sync pins all source snapshots at start and processes
at most 1000 source entries per call, including filtered entries. An empty chunk
must be acknowledged to advance its cursor. `sync_next` supplies `local_path`,
`source_path`, `stream`, `version`, `published_change` and `_have` (the previous
local baseline). Changed mappings produce cleanup deletions for previously tracked
paths; untracked local files are not included. Small-file sync tar members use
the mapped local paths; large files use protected download/Range.
After a full acknowledged sync, subsequent full syncs skip identical catalog
subtrees and process only server differences. Partial-prefix syncs and changed
views use bounded scans. Cancellation preserves already acknowledged Have but
does not record a full-sync checkpoint. `have(workspace, root?, after?, prefix?,
limit?)` returns the acknowledged revisions and guards stable pagination.
The client must verify bytes, protect local modifications using `_have`, and
acknowledge the complete chunk only after safe local writes/deletions. The server
cannot verify the client's disk. Sync state survives restart and stale/repeated
acknowledgements cannot advance Have twice.

**Local comparison.** `reconcile(workspace, files, view_revision?, have_root?,
heads?)` accepts up to 1000 local descriptors (2 MiB total), with
`{path,size,sha256}` or `{path,missing:true}`. Paths are relative to the workspace
root. Results distinguish local clean/modified/added/missing/unmapped and server
current/newer/deleted/untracked, and include Have, the server file and writability.
Reuse returned `heads` (stream to submitted change), `have_root` and `view_revision`
across chunks for a stable comparison; accumulate heads for newly encountered
streams. ACL is checked on each call. Hashing and inventory run on the client;
the server never accesses `local_root`. TH/TS screens are a separate next block.

**Branches and merge.** `create_stream(..., parent)` pins the real parent's
submitted change and shares its immutable catalog and bytes, without copying all
files or inventing revisions. `merge_begin(change, source_stream, edit_revision,
request_id, source_change?)` requires a current destination base, a common ancestor
and the same depot. It starts the existing durable integration protocol:
`integration_next`, `conflicts`, `resolve`, `integration_finish`, then `submit`.
Here `ours` is the incoming source and `theirs` the destination including its
pending edits. SHA/size comparisons use the common real snapshot; merged result
versions link to the previous destination revision and `integrated_from` source
revision/change. Deletions and binary/custom merged payloads are supported.
The source stays pinned if it advances during integration; a changed destination
head prevents finish/submit. The last integrated source root advances only with
successful atomic submit, allowing incremental repeated merge. Removing/moving
files or editing content conservatively clears pending merge checkpoints, so
omitted changes remain eligible for a later merge. Older branches lacking verified
fork metadata require administrator `stream_ancestry(stream,parent_change,
baseline_change)` matching actual submitted snapshots; ancestry is not guessed.
Automatic text merging and cross-depot merge are not provided.

All business persistence uses native Search/SObject/Command with project/depot/
row/column rights and synchronous triggers. Failed requests roll back their
metadata and receipts; submit publishes the entire changelist atomically. The
integration's earlier successful chunks remain private resumable staging.

Validation: `tests/test_file_workspace.py`; native SQLite/PostgreSQL contracts via
`tools/file_project_checks.py --postgres`. `tools/file_project_benchmark.py
--files 1000000 --checkin-files 0` checks synthetic catalog/Have metadata and sparse
sync; it does not measure million physical revisions, downloads or TB throughput.


## Bulk transfers, resumable tasks and storage policy

File projects have a separate transfer pipeline. Enable **Bulk file transfers**
in Configuration → Server → Services and workers (`services/enable=tactic|files`
or `tactic|queue|files`) and restart the server. The monitored `files` process owns
verification, staging and GC; standalone ASGI uses the same option. Classic check-in
keeps its existing path. TH/TS Perforce-like workspace UI is a later block.

Metadata uses native FileProjectCmd/Search/SObject/Command, project/depot and
row/column rights, synchronous hooks and rollback. Every worker step authenticates
the task owner again; revoked/disabled accounts stop publication. The local service
records errors without publishing as administrator. Earlier staging chunks stay
private; only the final atomic submit exposes the entire changelist.

`transfer_begin(change,request_id,submit,expected_files?,expected_bytes?)` creates an
upload. Optional expected totals provide overall progress before manifests finish.
`transfer_manifest(task,request_id,files)` accepts 1..1000 `{path,size,sha256?}`
descriptors within 2 MiB, reserves quotas and returns blob IDs. Identical receipt
retries are idempotent. `transfer_next(task,after)` pages the immutable manifest and
committed offsets. `transfer_digests(task,items)` accepts up to 1000 blob/checksum
pairs. `transfer_seal` requires all declared files/bytes, then queues verification
and bounded staging. `transfer_status`, owner-scoped `transfer_tasks(after,limit)`
and `transfer_cancel` expose overall uploaded/verified/staged files/bytes, current
verification path and errors. Worker-only actions reject client credentials.

`/file-project/command` delegates bounded JSON transfer metadata to the native API
(3 MiB transport limit). PUT `/file-project/transfer-upload?project&task&blob&offset`
streams blocks up to 64 MiB with Content-Length, fsync, confirmed offsets and an OS
writer lock. Receiving a large body does not hold a DB transaction. Project byte
writers default to 4 (configurable 1–16), with a per-web-worker gate of 4. `batch=1`
accepts strict USTAR, up to 1000 complete files within 64 MiB, preserving hooks and
atomic metadata/file rollback. The next exclusive writer truncates interrupted
tails to the confirmed offset. `/file-project/manifest` streams a bounded NDJSON
page. Sizes/offsets use signed 64-bit integers; bytes avoid XML-RPC/base64.

`transfer_begin(kind='download',workspace,client_root)` pins native sync/view and
resumes the workspace's active task for that same local root. `transfer_next`
returns at most 1000 desired entries and Have; `transfer_ack(task,ack_revision,paths)`
advances Have after the entire chunk is durable locally. `/file-project/sync-download`
streams small files as tar. Its POST accepts `{sync,ack_revision,paths}`, sending only
a subset of that pinned plan after an interrupted batch/lost acknowledgement.
Larger files use `/file-project/download` with Range and pinned published_change.
Mappings, exclusions, imports and source/local paths retain their native semantics.
Filtered/incremental totals remain unknown until traversal completes; aggregate
confirmed counters work immediately without counting the full catalog first.

`tactic_client_lib.file_transfer.FileTransferClient` implements upload/download:
local SQLite outbox (never server SQL), bounded windows, tar streamed directly from
sources, bounded parallelism and SHA-256. Keep the upload journal to resume that
exact task; a new dataset needs a new journal. Download retains partial large files,
checks SHA-256, fsyncs and atomically replaces targets. Modified/untracked files and
symlink/path escapes are rejected; `force=True` explicitly allows overwrite.
Progress includes totals, confirmed counters, current path and block/file progress.
Callbacks may execute in transfer threads; GUI adapters must marshal to the UI thread.
A resumed upload re-hashes its source prefix; a restarted verifier re-hashes its
current large file while retaining previous verified results.

Existing file projects need admin `storage_upgrade`, then bounded `storage_index`
until indexed; reads remain available, new allocations wait. New projects install
these indexes directly. `storage_status` exposes usage; admin
`storage_policy(revision,policy)` changes rules with CAS. Byte/file limits default
to 0 (unlimited). Declared sizes reserve quota before allocation; only physical GC
releases it. Defaults: idle uploads 7 days, terminal tasks 7 days, reverted drafts
30 days, shelves indefinitely, quarantine grace 1 day. Submitted history, workspace,
private drafts and live download references remain protected. Pending changelists
are never automatically reverted. `gc_interval_seconds=86400` schedules daily GC;
0 disables it. Admin `gc_begin(dry_run=True)` previews candidates; false schedules
native mark/sweep, quarantine and replayable reclamation, including expired upload
spools. Retired blobs cannot be revived. Missing references stop collection.
Concurrent root changes restart marking before further sweep. **Limit:** continuous
edits may defer GC; completing it under constant writes will need a write barrier.

Validation: `tests/test_file_transfer.py`, owned worker restart/cleanup in
`tests/test_monitor.py`, native PostgreSQL checks and fresh random-byte HTTP roundtrips
in `tools/file_transfer_benchmark.py`. Million-entry tests measure catalog/Have
metadata only; physical million-file and TB transfer capacity has not been measured.

## Desktop workspace and browser administration

Choose **Perforce-like file project** in the project wizard. Mode belongs to the project (`file_project`); the server can host Classic and file projects together. Handler opens a separate desktop workspace, while Stream opens inspection and administration. Changing the type of an existing Classic project is not a migration.

Handler supports paged pending/submitted/shelved/reverted changelist trees, file selection, ordinary/exclusive checkout and holders, descriptions, move/remove, shelving and unshelving, actual version history, local SHA reconciliation, Have, Get latest, disk-journal uploads/resumption, explicit deletions and three-way conflict resolution with a manually merged file. Reconcile is explicit; no continuous filesystem watcher or automatic text merge is implemented.

Stream supports depot/stream/workspace setup and mappings, paged changelist/depot/Have inspection, checkout holders, descriptions, move/remove, shelving, native submit/revert and conflict inspection with ours/theirs resolution. Local folders and bulk uploads/downloads are desktop operations in Handler. Browser transfer monitoring fetches one bounded task page, never a request for each file. Tasks are scoped to the current login.

Storage administration exposes byte/file quotas, transfer concurrency, retention in seconds and GC grace/interval. Zero quota means unlimited; zero shelf retention keeps shelves; zero GC interval disables scheduled runs. Save uses a policy revision check. A GC dry run reports candidates without deleting bytes; **Run safe GC** queues native fenced reclamation using the configured retention/grace. Refresh GC status for its counters. The `files` service must be running.

During active uploads, editing and submit are blocked on the server. Cancel/failure restores the whole original private draft after partial staging; completed uploads stay staged until Submit. Submit uses the native Command transaction, ACL and triggers to publish all or roll back all. Client Stop waiting preserves resumable server work.

Views contain at most 200 files, manifests at most 1000. Local hashes and byte IO run outside the Qt UI thread, with disk caches and bounded buffers. History currently exposes the latest 1000 published revisions; text previews are limited to 256 KiB. Handler saves an immutable revision with a checksum check. Millions of physical files and terabytes of GUI transfer remain unmeasured.

Workflow reference: [P4V changelists](https://help.perforce.com/helix-core/server-apps/p4v/current/Content/P4V/files.submit.html), [shelving](https://help.perforce.com/helix-core/server-apps/p4v/current/Content/P4V/files.shelve.html).

Both clients use compact shared toolbars, contextual commands and lower History/Conflicts/Transfers tabs. Open **Workspace actions** for setup and storage administration, **Changelist actions** for description/shelves/merge/revert, and **File actions** (also the file context menu) for checkout/move/remove. Setup and descriptions are separate dialogs; splitters resize the tree and details. The narrow layout opens the tree on demand.

## Transfer recovery

New uploads fail before server allocation when `files` is disabled. Enable it in Stream Configuration and explicitly restart the server; saving configuration does not restart it. Check monitor status for a healthy worker. Keep the upload journal and the same workspace root for Resume after a lost connection. Stop waiting preserves the task; Cancel server task restores the original pending draft. A lost Submit/Have response must be checked/retried against the same task, not replaced by a new upload. Changed local sources require cancellation and a fresh transfer.

Installation and backup instructions are supplied in `FILE_PROJECT_DELIVERY.en.md`; create a new project from the builtin `perforce_like` template. Back up databases and private blob storage together. Source/wheel delivery and offscreen tests do not certify a physical million-file/TB run or Windows EXE/Electron installation.

Temporary contention before the storage-policy lock is acquired is marked `file_project_busy`; metadata requests repeat with bounded backoff and server tasks remain queued/running. Arbitrary HTTP errors, failed hooks and permission/checksum errors are not retried. Worker recovery after process death can wait for its committed 60-second lease. Python 3.14/PySide6 emits a Property ResourceWarning at interpreter shutdown even in a minimal property-only program; this is recorded as an unresolved runtime acceptance issue.

Archive upload reads up to 1000 blob records in one native Search query, guarded by storage-policy and changelist locks. Per-file native permissions, SHA, hooks and whole-batch rollback are preserved.

The Depot tree is on the left; numbered, expandable changelists are in the main work area on the right. Use the arrow to open a depot, stream, directory or changelist. Children load in bounded pages; Load more continues only that branch. Selecting a folder switches the main area to depot files; choose Changelist files to return to changelists. Each changelist shows its project number, description, owner and state, with selectable files underneath. Move and unshelve accept a project changelist number such as #42. Selecting a changelist clears the depot folder filter. Refresh loads the current publication.

Ordinary object Search tabs remain available in file projects. Managed file tables are accessed through the native file API; their schema and counts are available to administrators in Search Types. The Perforce-like workspace opens in the Commit Queue dock. It can stack with Search, move or detach through the existing dock controls. Maximize panel expands it over the working area; Restore panel restores the layout without rewriting saved split ratios. Cached project restoration selects the file interface before server refresh.
