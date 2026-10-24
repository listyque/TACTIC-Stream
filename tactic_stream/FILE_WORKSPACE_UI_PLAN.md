# File workspace scope and acceptance

This maintained contract replaces the historical implementation checklist at this
path. Its staged counts described past checkpoints and are not current release
qualification. See [delivery](FILE_PROJECT_DELIVERY.en.md) and
[acceptance requirements](FILE_WORKSPACE_COMPLETION_2026-10-13.md).

## Product responsibilities

Handler owns the standalone desktop workspace: editing, drag/drop, checkout,
local comparisons, shelving, submit, sync and bulk transfers. Stream owns the
native backend/API and browser inspection/administration. Equivalent common
semantics do not require another complete browser editing workflow. Classic
project workflows remain separate.

Both products retain their own runtime, controllers, transports and settings.
Check permission, identity, revision and transaction/file effects through their
existing owners. An accessible menu or API method does not prove the corresponding
native workflow or browser operation is complete.

## Required verification

Exercise selection/filtering, local file lifecycle, changelists, conflict handling,
preview/diff, locking, revision recovery and queue cancellation/failure with
representative data. Check actual file bytes and read back persisted changes.
Use native Handler for desktop-only actions and Stream for its applicable server
and browser contracts. Verify connection changes and independent bundles without
importing the other checkout at runtime.

Use the delivery guide's current limitations and fresh isolated acceptance
results. Historical stage counts and test totals are not a substitute for those
checks. Agent backlog and the original 124-item checklist are retained outside
Git in the local workspace archive; no requirements were destroyed by archiving.
