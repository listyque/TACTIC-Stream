# Legacy migration audit — 2026-10-24

What this repo does: Stream replaces the TACTIC server and browser interface; Handler is an independent native client. Existing installations bring their own configurations, trusted Python plugins, scripts and SDK callers. This review assumes multiple administrators and ordinary project users, with SQLite or PostgreSQL, rather than only the supplied CG project and current Handler calls.

**Verdict: the current build is a tested partial implementation, not a generally compatible migration target.** The reported VFX failures exposed a broader scope error. We implemented selected callers and declarations, then closed stages whose names implied much more. There is also a demonstrated regression in the native definition editor. Passing the two modern clients against each other cannot detect a feature missing from both.

Baseline: Stream `cd3e9f8` / `0.112.195`; Handler `98bf4c05` / `0.6.0.142`. No application code, production data, running services or release versions changed in this audit. The accompanying [evidence JSON](LEGACY_MIGRATION_AUDIT_2026-10-24.json) contains results, inventories and their limits, without tickets or user data.

## Scope and evidence

- Required: public non-production Python contracts, SDK wire formats, trusted plugin loading, saved widget configurations, their options/actions, and complete administration workflows. Absence from the current Handler call graph is not an exclusion.
- Excluded: production code and extra database vendors; Maya and applet scenarios remain explicitly excluded. Earlier separate decisions about Repository Sync, S3, CMS and licensing are recorded in AGENTS.md; this review did not revisit those systems. Existing architecture notes excluding an old editor or HTML renderer do not demonstrate that its required authoring workflow has a complete replacement.
- Executed 29 current-runtime probes on generated disposable SQLite data, including XML-RPC requests through the actual ASGI endpoint. The JavaScript packets reproduce the shipped SDK's ticket and trailing-kwargs format; this was not a complete legacy browser session.
- Executed eight successful reference cases with the actual original embedded Python/runtime on an independent temporary fixture. These verify keyword filtering, SObject evaluation, key splitting, short-class lookup, XPath OR, preserved CDATA, expression code prefixes and SQL view creation.
- Compared the pre-Frame Handler controller from the pinned 2026-10-15 archive with the current controller; executed the current browser definition parser in Chromium. This is not full fresh native/browser screen or save acceptance.
- Inventoried 231 qualified class references across 262 shipped configuration/template/contribution sources and ZIP entries: 86 resolve, 79 require triage, 66 name excluded production classes. Resolution does not prove rendering; some metadata adapters work without a Python class.
- Compared declared public methods of 20 core classes: 175 of 993 declarations have no current runtime attribute. This includes deprecated methods, abstract vendor hooks and separately excluded dependencies; **175 is not a count of required bugs**. Search alone lacks 25 methods, SObject 14, SearchType 10 and Common 30. The concrete failures below establish that this is not only dead source code.
- Found 377 explicit `UnsupportedContract` raises. That includes necessary security, transaction, context and validation guards. **377 is not a missing-feature count.**

## Must fix

### 1. [P1] The shipped JavaScript SDK cannot use the RPC entry point

The legacy `context/spt_js/client_api.js` delegate sends `language='javascript'` and always appends a kwargs dictionary. Stream binds these packets as Python positional arguments and then rejects non-Python tickets (`server/api.py:679–714`). A valid Python ping returns `OK`; the equivalent legacy JS ping returns Fault 400, and its query returns Fault 501. This is outside production/DCC code.

Restore the original language-specific argument normalization and result encoding at the transport boundary, retaining authentication and method authorization. Accept it with the unchanged shipped JavaScript SDK over actual HTTP as well as the existing Python SDK. Otherwise old browser integrations fail before their business logic runs.

### 2. [P1] Existing server scripts lose public Python methods

Through the real `execute_python_script` path, `Search.add_keyword_filter`, `SObject.eval` and `SearchType.break_up_key` raise `AttributeError`. The original runtime returns respectively `1`, `['A']` and the original two-part key result for the same core operations. The last missing method also appears in the VFX `asset_in_shot/load` failure.

Inventory public methods, aliases and inherited contracts from the original core, rather than only methods used by current Handler. Restore the original implementations and dependency paths, with same-body script tests for return values, errors, permissions and rollback. An exposed `execute_python_script` does not make these scripts compatible.

### 3. [P1] Class resolution deliberately removes legacy extension paths

`Common.resolve_class` (`src/pyasm/common/common.py:250`) rejects short names and every `tactic.plugins.*` path before import. `TextWdg` resolves in the original runtime and fails in Stream. The original resolver/Marshaller contains the plugin-loader hook; the availability of every external loader distribution was not verified here. Non-reserved fully qualified custom modules can still import, so this is not a claim that all Python extensions are impossible.

Restore the trusted short-name search order and installed-plugin loading contract through the existing resolver, with root validation and current permissions. Test an actual installed plugin through command, trigger, SearchType class and widget lookups. Installing its files or manifest alone is insufficient.

### 4. [P1] Custom table/form widgets have no general native rendering path

An importable custom subclass with a simple native `get_cell_value` resolves successfully, but `describe_cell` marks it unsupported because the class is absent from the built-in `WIDGETS` registry (`server/table_cells.py:196`). Form recognition also matches fixed class names (`frontend/src/features/objects/recordFields.js`). Inheritance from an existing input does not itself establish frontend support.

Preserve trusted widget class resolution and publish its existing data/options/action contract to both clients. Use existing native controls and extension registration; do not silently render arbitrary plugin HTML as plain text or bypass ACLs. Add an external example plugin with read, edit, validation, action and ordinary-user scenarios. Without this, a successfully imported customer template can still display unavailable widgets.

### 5. [P1] The definition editor lost existing visual editing capabilities

The pinned pre-Frame Handler has a generic XML-value editor and an active `TacticElementDefinitionEditor` with input widget, required/read-only, default, values and labels controls. Its generic projection exposes the text inside `<expression>`. Current `catalog_wizard` / `definitionWizard` project only name, title, visibility, width and display widget; expression editing returns “This column setting is only available in XML mode.” A non-table custom view formerly has editable rows and now returns `supported=False`.

This affects both products through `shared_ui/features/administration/columns/columns.ui.mjs`, `frontend/.../columnsEditor.js`, and `TH/thlib/ui/columns_editor.py:624`. Some richer backend authoring helpers remain, but the current QML tree no longer calls the old visual editor. Keeping XML intact is useful; it does not replace the removed controls.

Restore those controls and arbitrary existing XML-value editing, then extend widget-specific options from the original argument metadata. Accept display/edit/action definitions, inheritance, unknown options, conflict/retry and preview through actual save/reload in both clients. Otherwise administrators must hand-edit XML for workflows they could previously configure visually.

### 6. [P1] The new Layout Editor is not a replacement for legacy custom layouts

The current document editor accepts only `layout='sobject-layout'` (`layout.document.mjs:104`, `server/item_layout.py:17`). The legacy Custom Layout Editor authors a different format. At runtime the portable CustomLayout reader rejects a basic HTML table and a Mako loop over `sobjects`; it is also administrator-only (`custom_layout_element_wdg.py:7`). Thus an administrator-only, data-only subset cannot stand in for all existing read-only project panels used by artists.

Maintain a separate compatibility inventory and execution owner for old configurations; preserve required authoring, preview, bindings and actions in the modern editor. Do not enable arbitrary code for untrusted users or embed a browser in QML to hide the gap. Where a production dependency is intentionally excluded, diagnose that exact dependency before migration. Otherwise a new layout feature is mistaken for preserved legacy behavior.

### 7. [P1] Plugin/template schema migration has unsupported ordinary database features

A valid SPT `CreateView(query=...)` inside a trusted Command fails with “Plugin SQL views are not migrated” (`tactic/command/plugin.py:49,1095`). The same view creation/commit succeeds in the actual original runtime and returns all four fixture rows. On temporary SQLite tables, foreign-key, SQL-view and expression-unique-index export each fail explicitly (`database_impl.py:530`); PostgreSQL has corresponding guards at `:820`. These are features of the supported databases, not additional vendors. TableSchemaDumper calls these guards before producing its schema.

Restore import/export for the original supported schema contracts and round-trip real views/constraints/indexes through template/plugin creation and installation. Original dump limitations must be corrected explicitly, not copied as silent loss. Current safe refusal prevents a lossy export, but it also means L10 is not complete for customer schemas.

### 8. [P1] An original message-event setting makes ordinary writes fail

The original upgrade adds `search_object.message_event` (`legacy/.../sthpw_upgrade.py:725`). Restoring that original column in a disposable fixture and setting `message_event='insert'` makes a normal API insert fail with “Message subscriptions and delivery are not migrated” (`search.py:1672`; retire has another guard). The insert rolls back, which is correct, but the legacy configuration still prevents using the type. The fresh Stream registry does not contain this old column by default.

Restore the original event-to-message/subscription path, including recipients, privacy, transaction ordering and retry behavior. Accept it independently of the separate email notification tests already completed in L09. Otherwise a migrated type that works without its settings stops accepting writes when those settings are retained.

### 9. [P1] Expression-based code prefixes are rejected

With the same `code_prefix='{@GET(.code)}'` setting, the actual original `get_code_key` returns `A`; Stream raises “Expression-based code prefixes are not migrated” (`search.py:947`). The original uses the normal expression engine on the current object. Automatic object code generation calls this path.

Restore that evaluation and its original object context, preserving safe expression permissions and the native code allocator. Accept actual insertion without an explicitly supplied code. Otherwise a customer template's naming configuration can prevent object creation despite the TEL/Naming stage being marked closed.

## Should fix

### 10. [P2] Workflow acceptance omits cross-pipeline and expression connections

An actual Pipeline object with a `to_pipeline` connection is rejected by `Task._check_generation` (`task.py:927`). Original Pipeline connection traversal explicitly supports `to_pipeline` (`legacy/.../pipeline.py:1074`); the current implementation also rejects nested Pipeline XML (`pipeline.py:274`). Local hierarchy tests do not cover these forms.

Trace each original graph form through task generation and workflow execution, then restore applicable non-production behavior with transactional tests. Keep invalid cycles and missing pipeline validation. Otherwise an imported graph may be editable but fail when tasks are generated.

### 11. [P2] The XML utility is a subset of a public plugin API

`Xml.get_nodes("root/item[@name='a' or @name='b']")` returns two nodes in the original runtime and is rejected by Stream. `strip_cdata=False` preserves CDATA in the original and is also rejected (`common/lxml_wrapper.py:64,191`). These are shared configuration/script utilities, not old HTML-shell rendering.

Restore required XPath and XML round-trip behavior at the existing Xml boundary, retaining DTD/entity rejection. Use actual original-runtime cases for namespace, CDATA, comments, XPath and serialization. Otherwise plugins fail while reading or modifying otherwise valid configurations.

### 12. [P2] A valid named table view is recognized by Vue but not Handler

For `<custom_view layout="tactic.ui.panel.TableLayoutWdg">`, the current browser parser returns `supported=True`; the current Handler controller returns `supported=False`. Handler checks only the short `TableLayoutWdg` spelling for nonstandard view names (`columns_editor.py:640`), while the browser accepts both spellings (`columnsEditor.js:124`).

Use the same supported layout identities in both parsers and test this exact saved configuration through both editors. Otherwise an administrator loses visual access merely by opening the other client.

### 13. [P2] The acceptance inputs are narrower than the stage-completion claims

`tools/audit_api.py` inventories current Handler call sites and RPC exposure; the manifest itself correctly reports all 127 non-excluded methods as partial and full parity as false. `tools/frame_table/inventory.py:sources` defaults to current shipped widget XML and CG configuration, with optional explicit databases; it does not automatically enumerate all original template archives, plugin code or customer configurations. The B03 reference is the pre-Frame Handler, not original TACTIC; its columns branch selects a row and captures it, without testing its option editor (`original_reference.py:337`). The 156-stage Frame gate and independent delivery checks remain useful within their scopes.

Replace “closed” compatibility claims with a source-derived contract ledger and executable legacy scenarios. Keep UI parity, core conformance and installed migration acceptance separate. A feature needs both a compatible backend and a real user action/save result; matching two reduced implementations is insufficient. Otherwise each new imported project becomes an accidental test suite that discovers another unsupported path.

## Administration review map

There are currently ten shell entries, not eight. This pass does not declare the other entries broken merely because the editor failed.

| Entry | What this audit established | Acceptance still required |
| --- | --- | --- |
| Search Types | Core metadata paths exist; public methods and expression prefixes have gaps. | Create/alter fields, defaults, relationships, naming and deletion dependencies on imported types. |
| Project schema | Saved native graphs and relationship contracts are present; general relations were fixed in the preceding checkpoint. | Every original applicable relationship form and runtime traversal; import/save/reload, failure and rollback. |
| Workflow | Local graph support exists; cross-pipeline generation is refused. | Original connection forms, task generation, scripts, trigger order and retries. |
| Columns / definitions | Confirmed visual editor regression and one client parser mismatch. | Full display/edit/action options, visual and XML authoring, inheritance and actual writes. |
| Raw database | Existing dedicated editor/export paths were identified; no new failure asserted. | Original type/value handling, permissions, edits, CSV and concurrency on imported data. |
| Layout Editor | New SObject layout authoring is distinct from legacy layout authoring. | Existing custom layouts, bindings, previews/actions and ordinary-user viewing. |
| Sidebar Editor | Native SidebarConfig and saved navigation paths exist; unresolved panel declarations appear in the source inventory. | Original configured entries, access/visibility, targets, nested panels and save/reload. |
| Users | Existing account operations and safety checks remain; no new regression established. | Full original account operations, disabled/retired state, password handling and group changes. |
| Groups | Existing member/group editor remains; no new regression established. | Membership, inheritance, native role effects and transactional writes. |
| Access rules | Dedicated rule authoring and ACL enforcement remain; no new regression established. | Original rule categories, project/type/field/action effects, unknown XML preservation and ordinary users. |

The fresh registry also differs from the original seed: 20 of the original 62 type names are absent from the new 55-type registry. That includes production/test records, old aliases and candidate non-production services such as annotations. It requires classification against the **upgraded** original catalog; it is not evidence of 20 required missing tables, and restoring the seed wholesale would be wrong.

## Corrective sequence and closure criteria

1. **Reopen the compatibility claims now.** B03/B07, L08, L09 and L10 are partial for general legacy migration. Keep already verified behavior and its history. L11 proves the exercised SQLite/PostgreSQL foundation, not arbitrary legacy schema export. L12 stays open.
2. **Repair definition authoring first.** Restore the removed controls/general XML-value editor, named views and matching client behavior. Accept real display/edit/action changes against the original configuration and both clients, including ordinary-user effects after save.
3. **Restore core and extension contracts.** Cover public methods/aliases/signatures, original JS/Python wire formats, trusted class/plugin loading, custom inputs/cells/actions, Xml and TEL naming. The ledger must record original caller, parameters, dependency, effect and a runtime case; not only an adapter name.
4. **Complete migration and execution.** Views/constraints/indexes, full plugin lifecycle, cross-pipeline workflows and message events. Exercise rollback and stable retries on both supported databases. Add migration preflight that reports every missing class/API/setting before activation and leaves source data intact.
5. **Reaccept administration and real imported projects.** For each entry, enumerate original operations, options and states; exercise actual saves/actions in both clients and validate persisted data/side effects. Run selected SDK/plugins unchanged and retain the exact unsupported/excluded dependency list. Only then close the corresponding stage and rebuild independent deliveries.

The previous 18 VFX view failures are a known sample, not a total compatibility backlog. They also mix production dependencies, unfinished original widgets and ordinary missing behavior; classify those causes rather than treating every failed view as the same kind of task.

## Checks that prevented false findings

- Administrator `Search.add_where('COALESCE(amount, 0) >= 0')` succeeds in Stream. SQL is not universally missing.
- The original `add_op_filters` also rejects a raw single-argument SQL API filter. Do not weaken that boundary to fabricate parity.
- Original `PluginCreator.handle_plugin` warns and returns before its nested-export implementation. Its native explicit refusal is not removal of a working implementation.
- A source template mentions `GanttChildrenCbk` without a source class; the preceding native schedule adapter handles that declaration. A missing import alone would misclassify it.
- Keep transaction, authentication, ACL, source-path validation and DTD/entity guards. They are not migration defects merely because they raise `UnsupportedContract`.

Not checked: arbitrary customer projects/plugins, a fresh complete Administration GUI/save matrix, PostgreSQL execution of the new audit cases, clean Windows, GPU/physical input, and every original public method. No complete-compatibility claim follows from this audit. Production, extra vendors, Maya and applets were not proposed for restoration.
