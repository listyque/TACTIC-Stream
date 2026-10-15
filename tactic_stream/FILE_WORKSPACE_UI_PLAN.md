# File workspace UI: complete three-stage acceptance checklist

User scope, 2026-10-12. This groups the original 16-topic backlog without deleting
requirements. Checked items have implementation and verification evidence.
Unchecked items remain open, including partially implemented requirements.
Handler is the full desktop client; Stream provides corresponding inspection and
administration. Classic project workflows remain separate.

Scope clarification, 2026-10-13: editing, drag/drop, checkout, local comparison,
shelving, submit, sync and bulk transfer acceptance belongs to standalone Handler.
Stream supplies the native backend/API and browser inspection/administration.
Equivalent common semantics do not require another full browser working UI.
Previous browser-editing verification below remains historical evidence; it is
not a requirement to extend that browser workflow. No original item is removed.

## Checklist status — 2026-10-13

- Stage 1: **70 of 71** requirements checked.
- Stage 2: **35 of 35** requirements checked.
- Stage 3: **17 of 18** requirements checked.

All **124** original requirements remain below. An unchecked combined requirement
can contain working parts; it stays open until its remaining parts are complete
and verified. The three stages are not declared complete.

## Implementation evidence — 2026-10-12

Delivered sources: Handler 0.6.0.31 and Stream 0.112.68. This checklist retains
all requirements; release numbers do not mean every cross-stage acceptance is
closed. Basic interaction now includes scoped/paged Ctrl/Shift selection,
context/background menus, native drag/drop and Explorer import, distinct local
Trash/depot deletion, target pickers, independent views/preferences, current
Head/Have/locks, column settings, exact-path sync, ancestor-only reveal,
permitted changelist inspection, rename lineage and atomic revision restoration.
New catalogs maintain staged/waiting action summaries; old summaries report
unknown instead of scanning an unbounded tree. Whole-query mutation jobs and
complete lifecycle/per-file transfer accounting retain their later-stage work.

Evidence: 38 related domain/workspace/SDK/QML checks passed before the final
aggregate addition; the final catalog/interaction suite passed 17 checks and
the final QML/Chromium suite passed 8 checks. Native/Classic regressions passed
31 checks with 2 environment-dependent skips. The template/delivery contract
passed. Shared SDK sources are byte-identical in both clients. Tests use owned
temporary projects and fresh files, including real Explorer drop and Windows
Trash; no production project was seeded or restarted. The recorded PySide6
shutdown ResourceWarning remains unresolved. Million-file/TB and packaged
deployment acceptance is not claimed.

Follow-up: Handler 0.6.0.33 / Stream 0.112.70 add a bounded bottom operation Log,
explicit diagnostics access and expected blocked sync results without exceptions.
Dirty local bytes, same-task resume, worker diagnostics, real QML journal controls
and browser error/cancellation behavior are verified. Other lifecycle/progress
and physical scale requirements remain open.

Follow-up: Handler 0.6.0.34 / Stream 0.112.71 provide recursive scoped
Get Latest and a shared historical-selection API: per-file revision, submitted
changelist, stream revision and date/time, plus explicit Force repair. Missing
file revisions retain local data/Have with a bottom-Log warning. The native
metadata index/backfill is bounded and resumable; Classic remains separate.
Mixed menu/diff requirements and full physical-scale acceptance remain unchecked.

Verification: 18 focused revision/Handler QML/delivery checks passed, including
an actual old-schema administrator upgrade before historical download. Native
resilience checks passed 11 tests with 2 PostgreSQL-dependent skips. SDK copies
are byte-identical; frontend build passed. The recorded PySide6 shutdown
ResourceWarning remains, and million-file/TB throughput was not measured.

Follow-up: Handler 0.6.0.35 / Stream 0.112.72 fix recursive Depot/Workspace
folder drops into a pending change. One native checkout expands at most 1000
paths per chunk inside one transaction, preserving mapping exclusions, rights,
locks, triggers and rollback. Overlapping roots/files are deduplicated; source
paths remain intact and the UI reports the opened-file count. Verification uses
1105 files, late second-chunk lock/trigger failures, retry, real Qt drag/drop and
Chromium folder drag/drop. Million-file mutation jobs and the remaining lifecycle
acceptance remain open; this fix is not a completion of the three stages.

Follow-up: Handler 0.6.0.36 / Stream help 0.112.73 make Show in Explorer
usable before sync. Missing copies open the nearest existing parent within the
workspace, with an informational Log notice; missing roots and open/delete
targets return a normal unavailable outcome. The selected source is mapped
independently of the right-hand Files view. The popup fallback uses the parent
menu height instead of clipping a submenu to its anchor row. Stream has no
desktop Explorer-launch counterpart; corresponding Help is synchronized.

Verification: 28 related native-mapping/file/QML checks passed. The actual
Explorer process is mocked while its arguments, ancestor choice, menu input,
worker result and Log are exercised. Generic popup suites passed 32 of 34 checks;
two pre-existing failures (passive handlers in other pickers and an outdated
menu-height assertion) reproduce in an owned copy without this change. The
frontend build passed; the known PySide6 shutdown warning remains.

Follow-up: Handler 0.6.0.37 / Stream 0.112.75 deliver the Stage 2 lifecycle
block and the lower Files inspector. Native Command/Search/SObject mutations
retain stream rights, checkouts, optimistic revisions, callbacks and atomic
publication rollback. Manifests expose pending names before bytes; cancelled
uploads restore the original pending state. Read-only sync mappings now carry
`writable` through the native download plan. The shared SDK copies and EN/RU Help
are synchronized. Classic UI/backend paths remain separate.

Verification: the domain/workspace/lifecycle/delivery run passed 38 tests; the
Handler/Chromium run passed 16. Additional regression cases cover binary selected
resolution, local-versus-Have diff, native Windows notification invalidation,
manifest cancellation, read-only replacement, failed comparison cleanup and
same-view selection during writes. Final frontend builds passed. Repeated checks
are not counted as independent coverage. External comparison process arguments
are tested with launch mocked; an installed third-party viewer is not certified.
Physical million-file/TB, production PostgreSQL, complete cold-client recovery
and packaged deployment remain unaccepted. The existing PySide6 shutdown
ResourceWarning remains open.

## Stage 1 — workspace structure and complete basic interaction

### Selection (original topic 1)
- [x] Single click selects; double click opens the appropriate object/file.
- [x] Ctrl toggles, Shift selects a range, Ctrl+A selects loaded rows, Escape clears.
- [x] Keyboard arrows and Shift+arrows navigate/select; focus differs from selection.
- [x] Right-click preserves a selected group or selects the unselected target.
- [x] Depot, Workspace, Files, change children and History support selection.
- [x] Identities include workspace, stream, path and revision/change where relevant.
- [x] Selection survives refresh, disclosure and tab changes.
- [x] Loaded-row selection is distinguished from all-query selection; all-query operations use a server selection without materializing a million records.

Acceptance: loaded rows and pinned server queries have separate indicators and
actions. Query mutation jobs remain server-owned and bounded; UI correctness
here does not certify physical million-file throughput or concurrent restart.

### Context menus (original topic 2)
- [x] File, folder, depot, stream, workspace, change, shelf, revision and background menus.
- [x] Menu validity reflects the complete selection, object state and permissions.
- [x] File actions: checkout, sync, diff, history, add, delete, revert, move/rename, reveal and copy paths.
- [x] Change actions: edit, submit, shelve, unshelve, move, revert, delete empty and copy number.
- [x] Folder actions specify subtree scope explicitly.
- [x] Unavailable actions explain locks, conflicts, missing local data or stream mismatch.
- [x] Menus, toolbars and shortcuts invoke the same domain commands.

Selection gates now cover mixed kinds/streams/changelists, ownership, workspace,
read-only mappings, native depot write hints, ordinary/exclusive checkout conflicts
and active change work. Native checks remain authoritative at execution.
Remaining file-menu acceptance includes local move/rename completion and
physical external-application workflow qualification; its combined item stays open.

### Drag and drop (original topic 3)
- [x] Move selected files between pending changelists.
- [x] Stage Workspace/Files selection in a chosen changelist.
- [x] Import Explorer files/directories with destination preview.
- [x] Dropping a shelf begins unshelve into the chosen changelist.
- [x] Valid/invalid target feedback, file count and operation caption.
- [ ] Hover expansion, edge autoscroll and Escape cancellation.
- [x] Failed operations do not leave optimistic phantom rows.
- [x] Large directory discovery runs outside the UI thread.

Drop feedback rejects incompatible streams/workspaces, active or foreign targets
and moves back into the same change. Captions distinguish exact selected-file
counts from selected directory roots; discovery reports actual files during the
worker operation. Native Qt hover/edge timers and stopping on drag leave are
verified. Escape in the confirmation is verified; the combined hover/scroll/
Escape item remains open for cancellation of an actual native source drag.

### Status presentation (original topic 4)
- [x] Distinguish add/edit/delete/move/unchanged/conflict.
- [x] Distinguish own/other checkout and exclusive lock.
- [x] Display local, Have and Head revisions.
- [x] Distinguish local-only, server-only, modified, missing, stale and current.
- [x] Distinguish waiting/uploading/uploaded/verifying/error/shelved/submitted.
- [x] Changes show shelf, conflicts and unstaged/local changes.
- [x] Combined states retain meaning, including modified-after-upload.
- [x] Theme tokens, badges, accessible descriptions and selected-row visibility agree in both clients.

Remaining status work: complete per-file transfer/verification states,
local unstaged-change summaries. Combined badges preserve conflicts/verification
and suppress an obsolete Uploaded indicator after the staged bytes change.
Have/Head and cached local state exist; separate local-revision presentation
is not accepted yet. Stream cannot inspect the desktop filesystem.

### Deletion and undo (original topic 5)
- [x] Separate remove-from-change, mark-for-depot-delete, local-trash, revert and delete-shelf.
- [x] Depot deletion is a pending edit published only by submit.
- [x] Pending deletion can be undone; deleted revision history can be restored.
- [x] Delete empty changes; nonempty changes offer move/revert rather than silent destruction.
- [x] Selected-file revert and whole-change revert are distinct.
- [x] Revert unchanged preserves modified files.
- [x] Local destructive operations preview consequences and scope.
- [x] User deletion is separate from retention/physical GC.

Acceptance: nonempty Delete offers Move files or Revert; local copies are kept.
Move all files uses a full pinned query independently of visible filters; after
a successful move the empty source can be explicitly deleted. Native rejection,
permissions, revisions, retry and trigger rollback remain enforced.

### Command placement (original topic 6)
- [x] View, Actions, Workspace/Connection and Tools use Handler controls/design.
- [x] Current workspace and operation context stay visible.
- [x] File commands belong to files, change commands to changelists.
- [x] Frequent actions are visible; secondary commands use menus.
- [x] Icons have labels/tooltips and destructive groups are separated.
- [x] No hidden dependence on a previously selected changelist.
- [x] Add/checkout/delete offer an existing or newly created target changelist.
- [x] Narrow layouts retain every command through overflow without offscreen buttons.

### Independent views (original topic 7)
- [x] Left Depot/Workspace; independent configurable right work tabs opened from View.
- [x] Per-tab filters, selection, scroll, disclosure and sorting.
- [x] Multiple instances of a view with independent filters.
- [x] Tree context updates Files without replacing Pending/Submitted.
- [x] History can follow selection or pin a file.
- [x] Closing/switching handles dirty descriptions explicitly.
- [x] Tabs, docks, splitters, columns and working state restore after restart.

Remaining restart work: verify complete working-state restoration, including
deep disclosures outside the first fetched page. Basic tabs/preferences restore
is covered; this does not close the entire restart requirement.

### Changelist work area (original topic 8)
- [x] Compact rows with unique number, description, owner, workspace, stream and state.
- [x] Expandable files and identifiable shelved contents.
- [x] Counts for files, edits, conflicts, unstaged uploads and bytes.
- [x] Active target changelist is explicit.
- [x] Create/edit description/move files/delete empty changes.
- [x] Target picker avoids manual internal-code entry.
- [x] Mine/workspace/stream/all-permitted filters.
- [x] Navigate/copy number and link.
- [x] Other users' changes/shelves are readable only as permitted and not implicitly editable.

Remaining changelist work: complete local unstaged/upload counts; older catalogs
without action summaries currently show unknown counts. Number/link navigation
and permitted shelf inspection/target selection are verified in both clients;
other users' pending changes remain private.

### File browsing (original topic 9)
- [x] Lazy directory/file hierarchies in Depot and Workspace.
- [x] Workspace includes untracked files; missing and excluded mappings are explicit.
- [x] Name/action/local/Have/Head/checkout-owner/size/type columns.
- [x] Column resize, reorder, visibility and persistence.
- [x] Sorting, quick name search and status filters.
- [x] Local/depot address navigation, Back/Forward/Parent and reveal in opposite tree.
- [x] Long Unicode names, deep paths and empty directories display correctly.
- [x] Open with desktop application and reveal in Explorer.

Remaining browsing acceptance: verify very long/deep physical Windows paths
and launching the external desktop application/Explorer. Unicode names and
empty directories are covered. Sorting/search currently apply to loaded rows.

## Stage 2 — complete file/changelist lifecycle

### Local changes and checkout (original topic 10)
- [x] Background detection plus cancellable manual Reconcile.
- [x] Preview/select add/edit/delete/rename before applying.
- [x] Explain ignore and mapping exclusions.
- [x] Ordinary/exclusive behavior and owner/workspace/change lock information.
- [x] Local read-only handling where required by checkout.
- [x] Local modification after upload invalidates the staged-copy indication.
- [x] Large scans do not block unrelated views.

### Shelving and handoff (original topic 11)
- [x] Compare shelf with current pending contents.
- [x] Whole-change and selected-file shelve; replace and delete shelved files.
- [x] Unshelve target preview and conflicts.
- [x] Share permitted shelves by number/link.
- [x] Distinguish copying a shelf from transferring change ownership.
- [x] Explicit shelve-and-revert and post-operation local-file state.

### Submit/history/diff (original topic 12)
- [x] Submit previews description, exact files, missing uploads and conflicts.
- [x] File-level failures plus operation-level cause.
- [x] Whole-change atomic rollback and retained retryable work.
- [x] Navigate to successful submitted changelist.
- [x] History includes revision/change/author/date/action/description.
- [x] Local-vs-Have, local-vs-Head, revision-vs-revision and pending-vs-shelf diff.
- [x] Binary metadata/preview/external comparison.
- [x] Rename history lineage and restoration of deleted revisions.

### Branches/merge/resolve (original topic 13)
- [x] Source/target direction, affected-file preview and mapping exclusions.
- [x] Real Base/Ours/Theirs revisions and comparison.
- [x] Text, binary, delete/edit and rename conflicts.
- [x] Ours/theirs/manual choice, undo resolution and next conflict.
- [x] Bulk resolve applies only to explicitly selected compatible conflicts.
- [x] Unresolved count prevents submit; integration history/provenance is inspectable.

### Progress/recovery (original topic 14)
- [x] Overall scan/manifest/upload/download/verify/submit progress.
- [x] File/byte counts, rate, current item/chunk and justified ETA.
- [x] Active/completed Transfers and scoped cancel/retry/resume.
- [x] Visible connection loss and recovery after restart.
- [x] Lost submit responses are reconciled before retrying publication.
- [x] Other views remain usable during transfer.
- [x] Targeted refresh retains selection/scroll; clearing tasks also clears progress.
- [x] Concise user errors plus complete diagnostic logs.

Stage 2 now includes native shelf replacement/history and handoff, bounded review
pages, real conflict comparisons with undo and paired rename handling, cancellable
Reconcile, native Windows watching, Files Details/Checked Out By/Preview, and
per-file manifest/transfer inspection. Handler owns desktop filesystem work;
Stream has the corresponding server inspection/admin operations. Working rate,
phase, progress clearing and selection/scroll preservation do not close their
combined acceptance items without complete recovery and long-running UI tests.
The five unchecked requirements above remain explicit work: complete
file-versus-operation error attribution, all phase/counter
scenarios, measured rate/ETA behavior, cold-client connection recovery and full
refresh/clear coverage. No Stage 1 or Stage 3 requirements were removed.

## Stage 3 — scale, administration and delivery

### Bulk/API correctness (original topic 15)
- [x] Server query/range/subtree selections, immutable operation snapshots.
- [x] Batch checkout/move/delete/revert/status, missing native APIs completed.
- [x] Server-side permissions, revisions and locks across every operation.
- [x] Idempotent operation identities and no duplicate effects.
- [x] Bounded queues, concurrency, memory and visible row counts.
- [x] Stale requests cannot overwrite new workspace/tab state.
- [x] Measurements use fresh datasets, large directories and mixed file sizes.

### Workspace/admin/quality (original topic 16)
- [x] Mapping/exclusion editor with local/depot preview.
- [x] Workspace switching handles pending work and active transfers.
- [x] Root availability, disk space and mapping collision checks.
- [x] Workspace/Stream/admin views open from View.
- [x] Stream Graph and advanced views follow basic workflow completion.
- [x] Handler full desktop workflow; Stream inspection/admin with equivalent common semantics.
- [x] Mouse/keyboard/themes/DPI/narrow/restart tests.
- [x] Concurrent checkout/locks/move/shelf/conflict/submit failure/disconnection scenarios.
- [x] Classic regressions, permissions, atomic rollback and installation/template checks.
- [ ] Million-file/TB tests plus uploaded-1000-file commit target below one second, reported separately from transfer time.
- [x] EN/RU help, release versions, operational docs and delivery instructions.

Stage 3 now has server-owned native whole-query mutations, inclusive pinned
ranges, stable receipts, bounded pages and mapping/exclusion forms. Real tests
cover a late second-chunk trigger failure, HTTP cancellation while an atomic
transaction is held, lost COMMIT replies, paired rename selection and edited
rename history. The desktop editing flow additionally prepares missing checkout
copies and local edits, detects changes after review, updates expanded change
badges, opens the editor on double-click, creates a change from an actual blank
context menu and closes view tabs through pointer input. Browser menus and
mapping preview retain remote inspection/admin semantics.

The fresh million-record SQLite benchmark is recorded in
`benchmarks/file_project_scale_2026-10-13.json`: 1000-row pages 10–12 ms, peak
73.64 MiB, fresh staged 1000-file edit 1717.19 ms plus Submit 19.67 ms.
It uses two small physical payloads and excludes network/TB throughput; it is
not a million-path single atomic job. The combined sub-second target remains
open. Long SQLite atomic jobs still serialize project writes. Full concurrent
restart/DPI/physical-scale qualification, advanced admin views/Stream Graph,
cache retention and packaged deployment remain open, as does the recorded
PySide6 shutdown warning. All 124 original acceptance items are retained.

Release evidence: Handler **0.6.0.39** / Stream **0.112.81**. The native/API,
workspace, transfer, QML and resilience aggregate passed 119 checks with two
PostgreSQL-dependent skips. The final bulk/interaction/pointer run passed 32
checks. Additional actual Qt/Chromium scenarios verify mapping input/focus,
cancelled root drafts, the blank Pending menu and custom tab closure, including
360px/1500px transitions. Explorer folder import resolves local paths through
native workspace mappings in 1000-path batches. Private progress is blocked by
its actual storage root; ordinary Classic folders named `file-jobs` stay public.
The server wheel builds offline and contains the new native modules; source
packaging is not a clean-machine GUI installation qualification.

Cross-stage dependencies are retained: a Stage 1 menu is not accepted merely
because its button exists. Its basic action must work against the native API;
the full workflow and scale checks remain in Stages 2/3 respectively.


## Focused regression evidence — 2026-10-13

Depot pointer clicks no longer send retained tab file lists and duplicate trees through every Qt binding. Models keep tree ownership; navigation uses the cancellable read worker rather than the write/transfer busy state. On the same synthetic 8,000-row retained state, real QML pointer dispatch measured 1,657–1,803 ms with the original full Qt payload and 18–24 ms with the focused payload. Server response time is excluded. Raw samples and limits are in `benchmarks/file_workspace_depot_click_2026-10-13.json`.

Native `change_files`/`inspect_change_files` return current changelist metadata alongside the page. Initial expansion does not use an old displayed edit revision; continuation and mutations keep revision guards. Handler native regressions and real Stream browser folder checkout/expansion verify this behavior. This evidence does not close the remaining combined checklist requirements.


## Selection, deletion and shelf handoff acceptance — 2026-10-13

Nine original requirements are now checked; all 124 original requirements remain.
Stage totals are 62/71, 30/35 and 4/18 (96/124 overall). No stage is declared
complete. Local filesystem rename/external launch, actual-source Escape drag,
full progress/restart recovery, physical million-file/TB qualification and the
sub-second target remain explicit open requirements.

Native regression evidence: 51 API/bulk/lifecycle tests passed, including late
trigger rollback, owner isolation, request retry and the full pinned 1005-entry
move despite unrelated local/name/path/status filters. These are correctness
checks; their reused small payload does not establish physical throughput.
Handler's full 21-test QML run passed its individual tests; the browser run exposed
a mixed checkbox-selection defect that was fixed and its affected native input
flows retested. The final 4-scenario QML/Chromium run passed, including current-
project shelf links, preview cancellation and nonempty Delete choices. A separate
native Qt test verifies hover expansion, edge scroll and timer stop on drag leave.
Five production-policy checks compare Handler/Stream selection gates, malformed
MIME rejection, checkout constraints and combined status badges. Final release
verification is recorded with the delivered versions below.

The existing PySide6 shutdown ResourceWarning remains open. No production server
was restarted and no production files were submitted by these tests.


Final release verification: Handler **0.6.0.45** / Stream **0.112.93**.
The API/bulk/lifecycle/workspace aggregate passed **71 tests in 153.299 s**.
The complete related QML/Chromium/drag/checkbox run passed **24 tests in 128.361 s**;
its subsequently affected permission/target flows passed **4 tests in 77.972 s**.
Five Handler/Stream production-policy checks passed; frontend build passed in
1.54 s. Repeated checks are not additional independent coverage. Native write
hints are returned with individual file/change metadata as well as paged stream
catalogs; their checks do not depend on the first catalog page. Source SDK and
EN/RU Help synchronization, versions, syntax and the 124-item total were verified.
The recorded PySide6 shutdown ResourceWarning and unaccepted physical/restart/
packaging requirements remain open.

## Workspace switching and download preflight acceptance — 2026-10-13

Delivered sources: Handler **0.6.0.47** / Stream **0.112.95**. Two original Stage 3
requirements are now checked: switching workspace with pending work/transfers,
and root/space/mapping checks. Totals: **62/71**, **30/35**, **6/18**, **98/124**.
The original 124 items remain; no stage is declared complete.

Handler rejects switching with an unsaved description before allocating a worker;
the worker also checks its snapshot. Native active-workspace revisions reject
stale confirmation. Cancel keeps the old workspace. A confirmed switch preserves
pending changes, Have, active server tasks and local bytes; it clears workspace-
bound selections, rows, tab data, inspector/review/navigation/progress and uses
the destination workspace's own comparison cache. Tab configuration, column,
filter and sort preferences remain. Old read completions are invalidated.

The shared download SDK checks an absolute directory root and free space before
requesting each bounded page's payload. Its conservative temporary-byte estimate
credits resumable large-file partials and does not reclaim live target files in
advance. Shortage pauses the owned native task with required/available byte
counts and a normal bottom-Log warning; no unreceived page is acknowledged.
Previously confirmed pages keep Have. Retrying resumes the same pinned task.
Native mapping/exclusion/case-collision guards are unchanged and retested.
This is a page estimate, not a disk-space reservation against other processes.

Verification: the related workspace/mapping/interaction/Qt regression groups
passed **64 checks**. The final transfer/API/delivery suite passed **44 checks in
117.495 s**; the subsequently affected workspace/Qt/preference scenarios passed
**3 checks in 5.087 s**. The final one-pass byte estimate passed **4 focused
download checks in 9.388 s**. Repeated cases are not additional coverage. New tests
cover a 1001-file two-page download stopped before its last payload, retained
Have, unchanged original local bytes, exact-task retry, Range resume with only
the remaining bytes available, invalid roots, invalid pause metadata, stale
workspace confirmation, local-cache separation and actual Qt Escape cancellation.
Frontend/help build passed in **1.60 s**. SDK/help/version synchronization is
checked. No browser editing behavior was added, and production was not restarted.

Full cold-client recovery, per-phase/per-file progress, source-drag Escape,
physical millions/TB, sub-second preparation/commit, full GUI installation and
the known PySide6 shutdown warning remain open. Source deployment requires the
user's manual server restart to load the new native pause reason.

## Completion block — Handler 0.6.0.50 / Stream 0.112.100

All 26 requirements that were open at the start of this block are individually
traced in [the qualification report](FILE_WORKSPACE_COMPLETION_2026-10-13.md).
**24 of those 26 are now checked; the full original checklist is 122/124.** No
original requirement was deleted or regrouped away. Stage 1 is 70/71, Stage 2
35/35 and Stage 3 17/18.

The two combined acceptance requirements stay open: native source drag/Escape
could not be driven because the Windows desktop rejected native pointer input;
the physical TB run was deferred by the user and the strict uploaded-1000-file
<1s interval remains above target (1.045s over real HTTP, 1.239s native edit at
million-catalog scale). Hover/edge/leave, ordinary Qt mouse/key flows and actual
Explorer/Notepad launches passed. A synthetic event is not claimed as proof of
the blocked native gesture; catalog scale is not claimed as resident TB.

The coherent matrix passed 196 tests with two environment-specific skips, plus
three final-wait/writer checks. PostgreSQL's broken-body cleanup race was fixed
and both writer cases passed on a new owned container. The delivered wheel was
installed into a new environment, Handler extracted independently, Classic and
Perforce-like projects created through the installed native API, and QML loaded
from the extracted runtime. Dependencies were reused from the existing test
interpreter; this is not an offline dependency installer claim.

The full working file UI belongs to Handler. Stream routes file projects to
inspection/admin, retains ordinary Search tabs, and exposes no checkout, local
edit, shelve, submit or bulk-transfer controls. This supersedes the historical
browser-workflow test notes above while preserving shared native semantics.
No production service was restarted. Raw logs are excluded from delivery.
