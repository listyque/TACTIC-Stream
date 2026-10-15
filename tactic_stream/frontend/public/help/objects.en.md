---
reference: Handler
group: Workflows
icon: cube
order: 11
---
# SObjects, previews and snapshots

> Result cards and rows represent TACTIC sObjects, processes, children, snapshots, and files.

## Main controls

Expand an sObject to inspect processes and children. List-view sObjects use an elevated rounded card
with a circular preview, description, configured information values, and a stable right-hand action
row.

Snapshots use a quiet inset MD5 card with extra breathing room, rounded corners, and no Search Type
rail or outline. A colored inset rail identifies the Search Type in both sObject densities.

Thin neutral guides and consistent indentation show the ownership of expanded descendants, which
fade in and out without a per-row position shift. The shared disclosure chevron has no background
and changes to a loading indicator only after that button requests an unloaded branch.

Compact density preserves the same three-line hierarchy with smaller spacing and turns on
automatically in a narrow Search dock or when Compact view is selected. Child relation rows keep
their child count visible in narrow view; add and link actions appear on hover.

Selecting an sObject quietly prepares its tasks, notes, snapshots, and versions for dependent docks
without showing the global workspace loading indicator. Task and note badges open related tools.

Snapshot Browser shows versions, contexts, files, previews, repository state, and file actions.
Context menus provide open, import, reference, copy search key, SObject Info, edit, duplicate, and
delete commands when allowed.

A process row offers snapshot and folder actions only; database editing remains in its dedicated
object and tool workflows. The aggregate task and note badges show totals across every process.

If no process has records or only publish has records, the badge opens publish directly; otherwise
an anchored process menu keeps publish first and lists only other processes with records. A red
badge marks locally updated content and returns to neutral after every affected process has been
opened.

Process menus use the counts already loaded with the object and open without waiting for an
animation or another server request. Opening the menu does not change your selection.

In compact snapshot rows, the file-size badge stays pinned to the right edge and long filenames
elide before the badge. SObject Info scrolls the complete summary, icon-labelled section switcher,
and active section as one continuous page; the summary never changes into a separate compact header.

Dates in the SObject Info summary and report sections use shared friendly localized labels, with
exact timestamps available on hover. Item context-menu commands run after the native menu consumes
the activating click and closes, so the result item underneath is not activated.

Open snapshot uses the loaded publish snapshot without requiring the result tree to be expanded.
Process and child-relation rows keep their icon and title columns fixed; the disclosure chevron
occupies a separate gutter outside the row surface.

Initial search results are laid out before presentation, so startup shows the first loaded batch
together; only explicit branch expansion and collapse uses the descendant cascade. Expanded
descendants fade in as a short top-to-bottom cascade; collapse completes the matching fade before
removing rows from the virtualized list.

Nested branches can be expanded and collapsed repeatedly; recycled process and snapshot rows return
visible and continue the same fade sequence. Snapshot file sizes use the shared MD5 status badge in
regular and compact density.

Snapshot dates use the familiar relative time, while hovering reveals the complete date and time.
Relative labels and named months follow the selected interface language.

Repository Sync, Watch Folder, and Relations actions appear on hover. A configured Watch Folder
remains visible as a green eye; an unconfigured one appears as a crossed eye only on hover.

A Relations shortcut opens its result tab under the plain unfiltered Search Type section, never
under a saved sidebar filter for that Search Type. Ctrl-click toggles sibling sObjects in the
selection, including objects inside an expanded child relation.

Shift-click selects their contiguous sibling range. sObject, snapshot, and file result rows support
drag-and-drop using their native search key and file payloads.

The compact information line follows the Search Type table definition: configured labels and colors
are applied, long values remain available in tooltips, and URL columns open as external links.

## Usage notes

- Previews load in the background.
- Replacing a versionless snapshot refreshes its preview.
- If preview generation fails, check-in stops and reports the error.

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
