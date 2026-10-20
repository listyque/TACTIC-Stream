# B14 remaining surfaces and release closure

Stream **0.112.167** / Handler **0.6.0.118**, 2026-10-19. This batch closes the
remaining named surfaces and integrates their acceptance into the required
platform gate. It does **not** close B07's separate 40-class legacy widget
backlog or promise full-screen pixel identity.

## Shared composition and retained owners

| Surface | Portable description | Existing owner retained |
| --- | --- | --- |
| Knowledge workspace | `features/knowledge/workspace.ui.mjs` | Project, selection, lazy article host, navigation persistence and requests |
| Navigation and outline | `features/knowledge/navigation.ui.mjs` | Native role models/drag-and-drop and browser catalog; article lookup and heading scrolling |
| Reader/editor commands | `features/knowledge/commands.ui.mjs` | Markdown, drafts, revisions, publication, permissions, history, attachment and image operations |
| Formatting toolbar | `features/knowledge/format.ui.mjs` | Qt rich document and browser selection/range editing, native anchored menus and DOM menus |
| Collaboration first use | `features/support/collaboration/initialization.ui.mjs` | Explicit authorized schema initialization and host-owned confirmation; no creation during reads |
| Timesheet and hour editor | `features/workhours/sheet.ui.mjs` | Existing time-entry controllers/commands, selection, daily limits, approval, user scope and writes |
| Work and Cost Reports | `features/workhours/reports.ui.mjs` | Native permission-filtered report models and server-authorized browser report catalog |
| API console | `features/support/documentation/api.ui.mjs` | Stream method catalog, credentials, request validation and explicit execution |
| Transaction details | `features/support/documentation/journal.ui.mjs` | Stream server-filtered journal XML and request identity |

Corresponding renderers use their own house controls. Native Knowledge and Work
Hours adapters live in `thlib/ui/qml/features/knowledge`, `features/workhours`
and `features/collaboration`; public names remain thin facades. Vue adapters stay
under their feature directories. Both products ship independent copies of the
portable modules. No WebEngine or runtime link to another checkout is introduced.

Typed rich text, image selection/resizing and attachment presenters remain engine
adapters, not a second implementation of persistence or permissions. Browser API
and transaction details are intentional capabilities; no extra native window is
invented. Batch Manager keeps its native launcher, scheduler and existing web UI.
User/plugin/DCC-generated UI remains with its script/connector execution owner.

## Input and lifecycle corrections

- Pointer and keyboard Action controls send `pressAction` before activation.
  Anchored menus preserve their previous open state and text selection before
  focus moves; press is not a second mutation command.
- Shared editor/viewer bars wrap at narrow widths. Fields keep semantic names,
  complete primary actions, visible scrolling and stable control identities.
- Hour duration accepts 0.01–24 with two decimal places and dot/comma input.
  Existing server validation additionally enforces daily totals. Description
  remains multiline; full approval text remains visible on narrow forms.
- Report lists retain virtualization at 1,500 rows. Narrow report choices omit
  types unavailable to the existing permission owner.
- Messages and Knowledge first use now share explicit schema confirmation in
  both engines. It names both message metadata tables and project article
  columns, preserves existing data, and closes on project changes. Browser
  Messages initialization now calls the existing Knowledge schema procedure, as
  Handler already does; ordinary reads still create nothing. Isolated HTTP
  tests cover both schemas, repeated initialization, read-only calls and ACL.
- Browser Knowledge initialization, organization, deletion, attachments and
  clipboard callbacks use the existing request generation. A previous project
  cannot publish into a new one or reset its busy state/permissions. Already
  submitted writes can finish for their original project; the UI does not claim
  cancellation or retry them automatically.
- Closing the API console aborts catalogue loading and clears temporary
  credentials. Late execution/sign-in/copy completions cannot update a removed
  view. A late journal-copy completion cannot update another transaction.

## Complete source ledger

`tools/frame_remaining/surfaces.json` classifies every inventoried QML/Vue file
by batch, role and disposition. It covers controls/composites, renderer
infrastructure, shell and domain forms/presenters separately. The fresh inventory
at the B14 checkpoint contained **452 native and 297 browser sources**; the
current source-only audit below contains **453 + 298 = 751**. The coverage checker rejects
missing, duplicate and removed entries and self-tests its omission guard.

This ledger routes ownership; it does not turn static declarations into runtime
acceptance. Existing batch documents retain their workflow evidence. B07 entries
remain explicitly partial: adapted table presenters are delivered, but **40
usable legacy widget classes** formed its backlog. Four now have L02 adapters;
36 still await adapters, and used options/overall B07 acceptance remain open. Unfinished legacy
widgets and the excluded old production subsystem are not silently reintroduced.

## Reproducible release audit

From the Stream checkout, using its configured Python and installed frontend
dependencies:

```powershell
python tools/format_tactic_frame.py --handler-root D:/code/th_codex --check
python tools/sync_tactic_frame.py --handler-root D:/code/th_codex --check
python tools/frame_foundation/check_platform.py --handler-root D:/code/th_codex
python tools/frame_remaining/capture.py --handler-root D:/code/th_codex --reference-archive .tmp/b14/original-handler.zip
node frontend/tests/frame_remaining_capture.mjs
python tools/frame_remaining/report.py --handler-root D:/code/th_codex --reference-archive .tmp/b14/original-handler.zip
```

The required gate includes native Knowledge/Work Hours owners and real input,
browser lifecycle/input scenarios, portable state rules, fresh inventory and
coverage, along with earlier batches, smoke, independent packaging, input/IME,
resize/disposal and existing quality budgets. Connected transport tests exercise
Knowledge editing/publication/files/history, API authorization/execution and
table/inspector time-entry creation, approval, edit and deletion on disposable
servers. They do not write to a production database.

The final comparison rejects quick/partial/stale captures. It includes **720
native/Vue compositions** (10 panels, three themes, light/dark, EN/RU,
430/900/1200 px, normal/locked) and **44 immutable original/current native
production pairs** (11 surfaces, EN/RU, 430/1100 px). Corresponding controls are
checked for geometry, typography, colors and indicator placement. Rich document
rasterization and native-only capability regions are not full pixel-parity claims.
The source-verified report is `tools/frame_remaining/output/index.html`; source
ownership is `coverage.html`, workflows `workflows.json`, and the integrated gate
is `tools/frame_foundation/output/platform/gate.json`. These generated artifacts
are ignored, reproducible local evidence, not shipped runtime data.

The focused native suite passes **108 tests**; seven connected browser input
and lifecycle scenarios pass. The full comparison checks **7,416 rectangles**
and **5,256 typography/color checks** across its 720 pairs; indicator bounds
are checked separately. Production
Knowledge, API and table/time-entry transport journeys pass against isolated
servers. The B14 integrated platform gate passed **142 mandatory stages**, including the
existing 64-case Batch Manager suite. Its captured source fingerprints and results
are recorded in `gate.json`; later edits require new acceptance and are not
certified by this historical run.

## Restore points and remaining limits

The immutable pre-B14 Git checkpoints are Stream
`36109efdf3a4d7e2b2f5d2e1f4f9cd709be4b15a` and Handler
`1a633e848e91784bb462d5554fecc106a04a8e6e`. Local original-source archives and
protected unrelated working files live under ignored `.tmp/b14`; Git/NAS backups
remain separate per repository. Restoring code does not restore a database,
uploaded file, credentials or local configuration. Do not reset an active dirty
checkout to inspect an original; use an independent checkout/archive.

Physical touch, platform OS IME, complete packaged EXE distribution, live
production writes/PostgreSQL deployment and actual DCC/render jobs remain
deployment acceptance. The existing repository-wide structure/lint debt remains
under its previous budgets. B14's offline audit does not erase these limits or
the open B07 backlog.

<a id="source-audit-2026-10-19"></a>
## Current source-only audit — 2026-10-19

The fresh inventory and coverage check pass for 453 Handler QML and 298 Stream
Vue files (751 total). They include controls, adapters, aliases and predecessor
files, not 751 distinct screens. The shipped XML/CG census remains 239 entries,
38 referenced adapted classes, 36 pending, 27 excluded production classes and
three explicitly unfinished originals. The full adapted catalogue has 41
canonical classes / 98 aliases. API status remains 127 partial + two excluded
methods; full_api_parity_verified is false.

### Confirmed active remainder

Native TacticTableInlineEditor.qml chooses legacyTagsEditor for tags/keywords,
then SObjectValueEditor.qml and TableTextEditor.qml. Browser TableInlineEditor.vue
already describes its input with features/table/inline.ui.mjs. The specialized
native interaction has not joined that shared scene; preserve its suggestions,
editing, Save/Cancel and focus when doing U01. Do not mark an ordinary text-field
replacement as parity. The 36 pending widget classes and remaining old options
are still B07 work, not missing copies of the standalone Messages/Tasks/Gantt.

### Predecessor forms are not active migration work

The following seven sources now have the explicit retained predecessor
classification. Source tracing found no incoming call from the current shipped
hosts, outside their own old component chain and qmldir registration:

| Former source | Current shipped composition |
| --- | --- |
| Handler features/administration/search_types/AdminSearchTypeFields.qml | AdminSearchTypesView.qml → search_types/search_types.ui.mjs |
| Stream features/administration/SearchTypeFields.vue | SearchTypes.vue → the same portable search_types scene |
| Handler features/administration/security/AdminSecurityRules.qml and AdminSecurityRuleEditor.qml | AdminSecurityView.qml and Stream SecurityRules.vue → security/security.ui.mjs |
| Handler features/administration/workflow/AdminGraphProperties.qml and AdminProcessSettings.qml | AdminGraphView.qml → workflow/graph_editor.ui.mjs, inspector/process descriptions |
| Stream features/administration/WorkflowProcessSettings.vue | WorkflowEditor.vue / graphFrame.js → the same graph_editor scene |

These files remain on disk; no deletion or runtime migration was performed by
this audit. Public QML names could still be referenced by external scripts, so
source tracing of the shipped hosts is not proof that deletion is safe.

### What the scan cannot certify

A supplementary direct-import search found 183 domain form/presenter files
without a direct .mjs or Frame reference. That is a candidate list, not 183
unfinished screens: NotesPanel, ScriptEditor, FileWorkspace and DescriptionEditor
retain owners/typed ports or delegate composition to child components. Inspect
callers and actual composition before adding one to the queue. Neutral house
controls, text/code/image ports and native window/transport owners intentionally
remain engine implementations. User/plugin/DCC-generated UI and the standalone
Batch Manager keep their existing execution owners.

Only inventory, source routing and shipped-config checks were rerun here. No new
runtime or pixel-parity acceptance is claimed. The complete Frame gate and prior
comparison screenshots were not refreshed for this planning change. The ordered
queue, from smaller known work to heavier integration, is
[U01 / L01–L12](../UI_ARCHITECTURE.md#legacy-plan); ID numbers retain their original
meaning, and dependencies are implemented within the first blocked scenario.

## Delivery grouping — 2026-10-20

The source audit above is unchanged. The canonical plan now groups the first
13 ordered subblocks into three implementation stages and keeps deployment as
a separate fourth stage:

1. UI/adapters: U01 → L02 → L07a → L03 → L05.
2. Complex tables and B07 acceptance: L06 → L01 → L04 → L07b.
3. Core/integrations/database acceptance: L10 → L09 → L08 → L11.
4. Independent distribution and legacy transition: L12.

All original IDs, class coverage, dependencies and acceptance criteria remain.
A request to execute stage 1 covers all five of its subblocks, not only U01.
This planning edit implements no runtime behavior and does not refresh the
2026-10-19 inventory or the historical UI acceptance evidence.
