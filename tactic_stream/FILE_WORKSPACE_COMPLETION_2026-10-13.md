# File workspace completion qualification — 2026-10-13

Sources: Handler 0.6.0.50 / Stream 0.112.100. The original checklist retains all
124 requirements. This report addresses all 26 requirements that were open at
the start of this stage; it does not equate implementation with full acceptance.

| # | Requirement | Evidence / acceptance |
|---|---|---|
| 1 | File commands, rename/move, reveal | Native + Qt operation suite; physical dirty rename and replay after lost reply; actual Explorer and Notepad launches. |
| 2 | Hover, edge scroll, source Escape | Hover/edge/leave runtime tests pass. **Open:** Windows native source input was rejected by the test desktop; no input was sent to another application. Run the platform probe in an interactive session. |
| 3 | Local / Have / Head | Shared SDK and real inspector; local revision includes dirty marker; missing/untracked copies show no invented revision. |
| 4 | Per-file transfer states | Native task items distinguish waiting/uploading/uploaded/verifying/verified/staged/error; shelf/submitted metadata remains separate. |
| 5 | Shelf/conflict/local indicators | Qt shelving/conflict/local watcher flows; per-change indexed unstaged counters invalidate on changed edit revision. |
| 6 | Restart state | Tab/column/filter/splitter preference tests; graph zoom; direct restore of deep off-page directories and selected change files. |
| 7 | File/edit/conflict/upload/byte counts | Native action summaries and bounded indexed reconciliation counters. Unknown local counts request Reconcile. |
| 8 | Unicode/deep/empty directories | Real Windows path longer than 260 characters, Unicode bytes, iterative walk and empty-directory index. |
| 9 | Desktop application / Explorer | Platform probe opened the owned document in Notepad and selected the owned folder in Explorer; closed only those windows and verified unchanged bytes. |
| 10 | File + operation failures | Native/HTTP/SDK `file_error` path/operation/cause and bottom Log; Debug Log retains full diagnostics. |
| 11 | All operation phases | Scan/manifest/upload/download/verify/staging/submit phases and overall stage labels. |
| 12 | Counts/rate/item/ETA | Phase-specific byte/file counters; measured-time rate/ETA test; TAR padding excluded from payload progress. |
| 13 | Disconnect/restart | Cold client replays exact upload sources; lost successful Submit is inspected, never republished; paused download and rename journal recovery. |
| 14 | Targeted refresh / clear | Selection/read-during-operation Qt tests; terminal task clear removes details and progress. |
| 15 | Rights/revisions/locks | Native ACL suite; Have rechecks secondary-stream access; native callbacks and optimistic revisions remain authoritative. |
| 16 | Bounded work | Four server workers; existing SDK concurrency limit; 8192 retained tree rows, 8000 change children, 1000 per change, 128 cursors. Whole selections remain server-owned. |
| 17 | Stale requests | Old worker completion cannot release a new worker or overwrite newer view data; workspace switch keeps the user's selected tab while clearing old rows. |
| 18 | Fresh/mixed/large measurements | Five fresh sets of 1000 distinct payloads/new paths; real HTTP 1012-file mixed-size round trip; million-record native catalog. |
| 19 | Workspace/Stream/admin views | Native paged metadata views from View; real Qt narrow/theme tests and browser inspection. |
| 20 | Stream Graph | Real submitted parent/merge changes, native head pinning and bounded edge pagination; runtime graph + restored zoom. |
| 21 | Client scope | Handler full work interface; Stream routes to inspection/admin with no checkout/edit/shelve/submit/bulk-transfer UI. Common native semantics and shared SDK preserved. |
| 22 | Input/theme/DPI/layout | Qt pointer/key workflows, English/Russian, light/dark, 360px and DPI 150%; browser inspection layouts. Native external pointer qualification remains in #2. |
| 23 | Concurrent/recovery flows | Ordinary/exclusive checkout, moves/shelves/conflicts, late trigger failure, dropped connection, lost commit reply and worker rights recheck. |
| 24 | Classic/atomic/install | Native + Classic regression coverage, row ACL/trigger rollback, template and source-delivery checks; clean wheel/source installation is recorded with the delivery manifest. |
| 25 | Million/TB / <1s target | Million catalog passed. **Open:** physical resident TB was deferred by the user; strict end-to-end uploaded-1000-file <1s target is not yet met consistently. |
| 26 | Help/release/delivery | Canonical EN/RU Help synchronized, new strings localized, versions advanced once, public qualification and delivery inventory. |

## Measured limits

- Five newly generated 1000-file sets used 1000 distinct payloads and new paths
  per sample. Native preparation + Submit took **0.878–0.961 s**; payload upload
  was measured separately. This is not a claim about arbitrary custom scripts
  or production hardware.
- Real HTTP, 1000 new random 4 KiB files: upload + Submit **5.698 s**; from
  fully received bytes to confirmed completion **1.045 s**; download + Have
  **4.662 s**. The strict <1s target remains open. Staged Submit alone is not
  substituted for the complete interval.
- Real HTTP mixed set: 1000 × 8 KiB plus 12 × 16 MiB, **209,518,592 bytes**:
  upload + Submit **9.959 s**, received-to-confirmed **2.243 s**, download + Have
  **7.118 s**, peaks **124/138 MiB**. Background verification is included here.
- Million logical paths persisted **1,000,000 version and checkout records**,
  **13,652 catalog pages**, with **two physical payload files** across the test.
  Build **1460.71 s**, peak **73.38 MiB**, head/tail pages of 1000 **12.35/10.74 ms**,
  history **10.81 ms**, sync-next **12.78 ms**, ack-1000 **25.71 ms**. Last initial
  1000-record edit **1590.7 ms**; later fresh edit **1238.82 ms** plus Submit
  **20.61 ms**. These measurements also leave the large-catalog <1s write target
  open. A sparse/catalog-only test is not a physical TB transfer.

## Verification and delivery

The integrated SQLite/native/HTTP/Qt/Chromium suite passed **196 tests**, with
two environment-specific skips. PostgreSQL ran 95 checks: 94 passed and exposed
one cleanup race after a broken HTTP body. The corrected case and an additional
live-writer case passed on a new PostgreSQL container. A live byte lease now
returns marked retryable busy, preserves the lease and confirmed offset, and
does not overwrite another writer. Three focused final-wait/writer tests passed.
No production project, database or service was restarted or seeded.

Raw logs include disposable test credentials and are excluded from delivery.
Only public counts/timings and qualification summaries enter its inventory.
The existing PySide6 shutdown ResourceWarning remains an acceptance limitation;
runtime QML warnings are asserted separately. Native Windows pointer injection
was rejected; Explorer and Notepad qualification succeeded independently.

Before accepting production: perform the native external drag/Escape probe on
an interactive desktop; run the deferred physical TB test on sufficient storage;
meet the strict write/confirmation target on the intended database and hardware.
Keep Classic projects separate and restart the running server/client manually
when installing the supplied sources.
