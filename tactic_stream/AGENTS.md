# TACTIC Stream

- Expanded Administration navigation keeps section names in every section, including Workflow. Never replace it automatically with an icon matrix; the workflow library belongs inside its editor.

- Catalogs, navigation and conversation history use plain compact rows and quiet
  group captions. Do not give every row a filled rounded background or render
  headings as pills. Emphasize selection, hover and keyboard focus; secondary
  row actions appear on hover/focus and remain explicit on touch devices.

- Organize Tactic Frame into `core`, `controls`, `shell`, `features/<section>`;
  the source map and reading rules are in `src/tactic_stream/shared_ui/README.md`.
  Format shared modules, Vue renderers, styles and administration adapters with
  `tools/format_tactic_frame.py`; run its `--check` before committing.
  Do not compress source into long single-line blocks. Put new QML components
  in their domain directories, preserving public names through `qmldir`.

- Check Frame changes with `tools/frame_foundation/check_platform.py --handler-root
  <handler-checkout>`: contracts, formatting, copies, input/IME, virtualization,
  resize, smoke tests and independent packaging. Releases also require related
  user scenarios and fresh paired comparisons; matching declarations or a static
  inventory do not prove a screen is ready. A report with stale source
  fingerprints is not evidence for the current implementation.

- Follow `docs/frame/contract.md` for shared QML/Vue UI: one skeleton and
  rules, native house controls in each engine, real input and paired screenshots.
  Do not use WebEngine/WebView/HTML inside QML without an explicit user request.
  Wrappers around two independent screens are not a shared skeleton; identify
  limitations and incomplete migration explicitly.

- User clarification, 2026-10-13: corresponding TH and TS implementations must
  match in layout, dimensions, actions and behavior. Compare them side by side
  with identical data, theme, language, scale and window size; fix differences
  in the same change. Do not claim parity after checking only one implementation.

- User clarification, 2026-10-11: investigate and fix discovered and user-reported
  bugs in both TH (`D:/grav/Tactic Stream/TH`) and TS. Synchronize equivalent screens,
  checks and help; explicitly identify missing counterparts instead of claiming
  complete parity.

- The product name is TACTIC Stream. The directory and Python namespace are
  `tactic_stream`; the package and CLI are `tactic-stream`. Preserve compatible
  `pyasm`/`tactic` imports.

- Write simple, top-down code in the style of Handler's `tactic_classes.py` and
  `tactic_query.py`. Use direct functions and methods, with classes for domain
  entities and state. No factories, single-implementation interfaces, service
  layers or configuration for hypothetical future needs.
- Minimize wrappers and intermediate calls, especially on the API hot path.
  Reuse the original legacy logging blocks; do not write a second formatter.
  Measure method time and total request time separately: the original
  get_simple_cmd starts Duration after ApiXMLRPC.init.
- When responding in Russian, use feminine first-person grammatical forms.
- User priority, 2026-10-10: work in substantial, verifiable blocks. Complete
  all eight Administration sections and their editors first, then all of
  Configuration, then work panels. For each block, capture fresh references
  from current QML Handler, compare operations with original TACTIC and document
  internals in the existing EN/RU Help. Extend the backend according to the
  current screen's dependencies; another small API fix does not complete a
  block. Keep the working plan outside the repositories. Preserve useful
  additional Stream capabilities.
- The working UI opens at `/`, projects at `/projects/<code>/`, and UI resources
  at `/ui/`. User clarification, 2026-10-09: do not support old interface URLs;
  do not add an `/admin/` alias/redirect or query-project fallback. Resolve the
  project from the path; retain skey and search parameters in the query string.
- The UI supports multiple languages and themes from the start. English is the
  source language and default fallback; Russian is the second language. Route
  visible text, messages, headings and aria-labels through the shared translator;
  add new strings to every shipped dictionary. Switching languages preserves
  state. Do not translate server data, names, codes or scripts.
- Existing Tactic Handler at `D:\grav\Tactic Stream\TH` is the primary reference for UI/UX,
  user scenarios and control behavior. Before changing a corresponding screen,
  inspect its Handler implementation and documentation, then adapt that behavior
  to Vue and TACTIC Stream XML configurations. Use Handler code as a reference
  when implementing Stream.
- Migrating a Handler screen means its complete functionality and behavior,
  not a simplified copy or a few links to generic tables. Inspect the original
  screen, nested components, controllers and server procedures; inventory tabs,
  operations, states and dependencies. Include related editors, preview,
  statistics, confirmations, drafts, errors and navigation. Desktop and touch
  use the same operations with adapted gestures. Only explicitly agreed
  features/old subsystems may be excluded. A menu, form or backend method does
  not prove a screen is ready. Mark incomplete migration explicitly; do not
  replace missing functionality with placeholders or silently defer it to move
  to another screen. Verify original user scenarios and appearance at identical
  theme, scale and window size. Simple code and shared controls are mandatory
  but do not justify reducing requested functionality.
- Preserve useful differences from Handler as additional capabilities, with
  accessible choices and explanations in the UI/configuration, not only in code.
  Obtain the user's agreement before removing an implemented capability.
- User clarification, 2026-10-09: finish desktop dialogs, object context menus
  and dock controls before continuing mobile adaptation. Remove the Results
  search-row grip; do not turn it into a button. Open panel controls through
  the existing three dots to the right of search, as in current Handler's
  SearchWorkspaceView.qml → DockMenu.qml. Enable navigation hover auto-close
  with the original 120px threshold only after the first pointerenter during
  that opening: the empty workspace's central button must allow the pointer
  to reach the list without dismissing the panel.
- Button proportions and icon centering are a shared contract: round buttons
  have equal width/height and do not shrink in flex layouts; text-row/heading
  styles do not apply to icon-only buttons. Align AppIcon container size with
  font size; take optical scaling from current MaterialIcon.qml. Do not repair
  individual offsets with manual margin/translate. Check the container and glyph
  after all official font sets load. AppIcon inside button/link/summary/
  role=button is decorative: shared icons.css supplies pointer-events:none.
  A standalone search icon with its own handler remains interactive. Test real
  clicks and taps at glyph coordinates while retaining native disabled behavior.
- Object/process notes open in the shared task inspector by default, as in
  Handler. The additional standalone notes window is available through
  Appearance → Object notes; it must not replace the main inspector workflow.
- One action/control type uses one shared Vue component, with consistent
  behavior and appearance everywhere. Use AppSwitch for toggles, AppSelect for
  settings choices, SettingRow for a setting's label/explanation. Do not make
  local versions or per-screen styles. The quick appearance menu and full
  configuration use AppearanceSettings. Configuration follows TH: a separate
  full-screen dialog without the project sidebar, one Reset/Apply/Save/Cancel
  header, section navigation on the left and settings cards on the right.
  Every setting has an explanation; Help/Details reveals technical information.
  On small screens sections precede settings. Apply keeps the screen open;
  Save persists and closes; Cancel/Escape discards the unapplied draft,
  including appearance preview.
- Follow `D:/grav/Tactic Stream/TH/docs/ui_component_policy.md` and `ui_component_map.md`:
  shared controls → domain components → screens → window hosts. Shared controls
  live in `frontend/src/controls`; screens and their domain components live
  together under `frontend/src/features/<section>`; `App.vue` remains the app
  host. Controls do not call APIs or know projects, SearchTypes or routes.
  Domain presenters receive data/state from the screen and emit events; one
  screen owns requests and drafts. Server business logic stays in TACTIC.
  Apply shared controls to changed screens; do not copy markup/styles/gestures.
  AppButton handles normal/compact buttons: label/icon, iconOnly,
  highlighted/destructive, native disabled/type, events and ARIA attributes.
  Themes, translation, semantic icons and motion already have shared owners.
  Do not add empty layers, barrel aliases, separate controllers or factories
  just to match a QML diagram; carry responsibility boundaries over to Vue.
  The current architecture map is in docs/architecture.md.
  Ship JS in separate chunks: /docs does not load App.vue; conditional editors
  use shared asyncComponent with loading/error states. For imperative window
  refs, load and mount the component before calling open; retain the instance
  and draft on close. Do not make frequently used refs asynchronous without
  checking callers. JS builds remain readable (minify:false) with source maps:
  DevTools must resolve chunk lines to original Vue/JS. Preserve module names
  and version hashes; serve `/ui/assets/*.js.map`. CSS minification stays enabled.
  AppMenu can unmount through its own action before click bubbles or a delayed
  toggle runs; those handlers must not access an already empty ref.
- User clarification, 2026-10-08: working modal windows use shared WindowControls
  / v-window for dragging by the header, maximizing and restoring geometry.
  Use it in every new editor, inspector and dialog; do not implement separate
  dragging/maximizing. Preserve native dialog refs and server/dirty guards.
  On narrow screens a working window fills the available screen. Menus,
  sidebars and short confirmations retain their own controls; docked sections
  do not become windows.
- Administration, like Configuration, opens in a separate full-screen dialog
  with its own header, project selection and navigation. It does not replace
  the working sidebar. Closing restores the original project, view, filters,
  sorting, page and selection. Guard unsaved changes on close and Escape.
- Use modern application layout, navigation and interactions, with Handler as
  the reference. Settings, APIs and UI use `/` in file paths, including Windows.
  Preserve the UNC `//` prefix; do not resolve client paths on the server.
- The UI must work on small mobile screens (320–360 px) and touchscreens:
  responsive layouts, collapsible navigation, actions accessible without hover,
  and no page-level horizontal overflow. Per the user's clarification, take
  control dimensions from current QML Handler without enlarging touch targets;
  users can zoom the browser if needed. This applies throughout the product,
  not only Configuration. No operation may require a mouse, right-click, hover
  or drag-and-drop: provide explicit buttons/menus, a normal touch entry to
  context menus, and control-based selection/movement alternatives to dragging.
  A normal tap is the primary gesture; context actions may require at most a
  long press. Do not require complex gestures for basic operations. Wide tables
  scroll inside their container; forms/configuration become a single column.
  Test browser touch input too.
- Mobile clarification: use a distinct layout for the whole application,
  including Messages, tasks, notes and settings. Hide quick-section sidebars,
  dock frames and geometry controls on phones. Show one active panel; select
  open sections through navigation and secondary actions through menus. Do not
  squeeze the complete desktop header onto a phone. Schema, interface and script
  editors and complex layouts are available on desktop. Reading, ordinary
  object editing, tasks and communication remain accessible. On phones Enter
  adds a line in messages/notes; sending requires an explicit tap. Preserve
  drafts and desktop preferences across width changes; hiding controls must
  not lose data. Mobile visibility is not server ACL enforcement.
- UI migration order: basic operations and their original XML settings first
  (view/add/edit and subsequent commands), then cell widgets and table behavior.
  Right-click and the explicit menu button open the same operations.
- Compare SObject menus with Handler item_actions.py, operations with
  item_operations.py and ItemCheckinDialogs.qml. ObjectOperations distinguishes
  objects, processes, snapshots and instance relationships. Check-in uses shared
  CommitQueue, native simple_checkin/FileCheckin and FileUndo, captured
  ticket/project, revision confirmation and file preservation on error. Do not
  replace check-in with property writes or overwrite another file because naming
  produced the same path. Local folders/Watch Folder need a desktop connection;
  Repository Sync is excluded. Relation Add files uses original IngestUploadCmd
  and shared CommitQueue; creation/check-in/exact linking run in one Command
  transaction. config/ingest_rule and scripts retain the TH contract; search
  matches only inside the selected relationship. Capture files/project/ticket
  before enqueueing. Deep Duplicate uses Handler's five steps and native
  procedures: independent file copies, exact relationships/direct children,
  tasks/note threads/attachments, and quick repeat with a login/project/type
  profile without retaining field values. Keep native checks and fresh paired
  QML/Chromium evidence. Do not infer complete menu parity: file clipboard/path
  menus and Delete Whole Tree remain separate migration obligations. Retain
  editor Teleport targets in the DOM when closing Administration; otherwise
  reopening sends content into a removed panel.
- Icons use TH's official font sets (Material Design Icons, Font Awesome
  Solid/Outline, Fluent Regular/Filled), selected in Appearance. Do not draw
  custom SVGs for standard actions. `frontend/src/appearance.js` owns appearance
  settings; appearanceCatalog.js owns the catalogue.
- MD3 is the main visual language; material5 is an experimental project theme
  following TH. Light/dark mode is independent of theme. Use shared CSS tokens
  for colors, dimensions, radii, fonts and motion; no component-local palettes.
  Extend languages/themes through the catalogue and shared resources. Compare
  baseline values with Handler thlib/ui/qml/Theme.qml and Typography.js: Segoe UI,
  point sizes, surface/accent blending and readable text. Do not approximate
  palettes/dimensions by eye. Compare current QML and fresh running-Handler
  screenshots, not old documentation images.
- Build the new core from the required parts of `../legacy`, preserving meaning.
  Reuse complete original modules/methods wherever possible. New implementations
  are for necessary runtime/driver adaptation and bug fixes; do not replace
  working TACTIC logic with new abstractions. User clarification, 2026-10-11:
  stop porting the complete old HTML shell; preserve working HTML methods and
  dependencies. Item 9 covers required data/command/SQL contracts, permissions
  and rollback. MySQL (item 10) is deferred; item 11 follows item 9.
  Vue is the main interface. Preserve working legacy HTML/JS APIs in a separate
  compatibility mode for original widgets; do not mix their runtime with Vue
  components. get_widget/get_column_widgets retain original signatures and
  result formats. A later user clarification allows excluding the HTML renderer
  if real clients only require metadata. TH has no identified working direct
  HTML API calls, but query_EditWdg depends on original EditWdg data. Do not port
  HTML generation just for this dependency: preserve configuration resolution
  and metadata first. Record HTML API exclusion as a compatibility scope change;
  do not silently substitute JSON for HTML responses.
- Rebuild the UI from original widget configs at runtime without rebuilding Vue:
  TACTIC defines structure, elements, parameters and actions. WidgetConfig/
  WidgetConfigView remain the shared configuration resolver; do not create a
  second frontend configuration or business-logic system. Modern UI descriptions
  are independent of Vue and its version; old APIs continue returning HTML.
  New renderers use the same core/configs. Executing arbitrary old Python/JS
  widgets is distinct from supporting their declarative configuration; a
  placeholder does not establish compatibility.
- On a compatibility gap, trace the original call first and port its necessary
  dependencies, configuration and initialization steps. Do not compensate for
  missing configs/modules with invented API fallback values. Methods return
  the original contract; configuration/upgrades belong to configuration and
  installation. Verify against the original core with an unchanged client call.
  This applies to the entire migration.
- Drupal CMS/session and commercial licensing are excluded: do not add keys,
  limits, licensing classes or `license_type`. Disable accounts through
  `s_status = 'retired'`. Preserve existing password hashing regardless of the
  algorithm name. Preserve copyright notices in ported code.
- User clarification, 2026-10-07: exclude Handler Repository Sync entirely:
  UI/controllers, synchronization queue, templates/presets, template editor,
  settings, automatic synchronization and dedicated server procedures.
  repository_sync*.py calls in the Handler inventory do not create migration
  obligations. Shared TACTIC file operations (check-in/check-out, snapshots,
  upload/download and repository paths) and the ordinary server queue remain
  part of the core/API.
- User clarification, 2026-10-09: S3 repositories are excluded; their absence
  is not an incomplete mandatory contract.
- Document internals incrementally in existing `src/tactic_stream/web/help`,
  in Russian and English, with an accessible catalogue topic: purpose, call
  path, examples, permissions and verified limitations.
- User clarification, 2026-10-13: port Table View widgets through verifiable
  examples with screenshots and documentation in the shared Help Widget Database.
  Group by purpose, readiness and original implementation state. Do not port
  demonstrably unfinished legacy widgets; record evidence in the catalogue.
  TODO or pass in an alias is not evidence: inspect inheritance.
- User clarification, 2026-10-13: the Table View checklist covers every table
  widget mentioned in any widget config, including definitions, nested configs
  and dynamic/script references. Record all references and parameters; do not
  restrict coverage to CG's main tables. Preserve agreed exclusions and proven
  unfinished originals. Rendering alone does not complete a shared inline
  editor, summary rows or widget actions.
- `Project`, `SearchType`, `Search`, `SObject`, search keys and the
  `sthpw/search_object` registry form the model. Do not add parallel Asset/Task
  models.
- Support database vendors through original `Sql`/`DbResource`/`DatabaseImpl`
  and vendor implementations. SQLite is the first working implementation, not
  a product restriction. Keep SQL dialect and JSON/date/DDL differences in the
  database layer; objects and user scripts must not know the vendor. The original
  targets were PostgreSQL and MySQL, with PostgreSQL next; the later MySQL
  deferral above takes precedence. Claim vendor support only after real
  connection, transaction, metadata, CRUD and original-contract checks on it.
- `Search`/`SObject`, APIs and unchanged user scripts must have identical domain
  semantics on supported databases. First installation creates all required
  system databases, tables and initial definitions; the user supplies connection
  details and an administrator password. The project creation command creates
  its database. Do not require manual SQL preparation.
- Preserve TACTIC core names and structure: `search.py` contains base `SObject`,
  `Search`, `SearchType`; domain classes inherit that SObject in their respective
  modules. Preserve method names and familiar `pyasm` imports.
- Complete 1:1 API compatibility is the target. Matching signatures or a
  successful client import do not prove behavioral equivalence.
- Fix discovered original-module bugs while porting. Document intentional
  differences from incorrect original behavior and use explicit separate
  expectations in comparative tests; do not present them as identical behavior.
- Existing custom server Python scripts must run unchanged, as in original
  TACTIC: `pyasm`/`tactic` imports, classes/inheritance, objects, methods,
  project/user context, results/errors, transactions, triggers and database
  effects. Do not change user scripts to accommodate the new core. Execute
  unchanged bodies in both cores on temporary data; compare results and effects.
  Missing dependencies remain incomplete compatibility.
- Preserve original TACTIC's public API for any existing client/project. Scope
  migration by original TACTIC contracts; Handler is one integration client
  used for verification.
- XML-RPC API, project creation and plugin/template installation are separate
  stages. Tell the user when each is ready for checks on their data, then connect
  TH. Do not couple plugin installation to XML-RPC. A working read transport does
  not prove project creation or plugin installation is ready.
- The inventory of 129 XML-RPC methods (128 original plus corrected
  get_ticket_data) is a snapshot of one transport. Track other public APIs and
  protocols separately. Prioritize core dependencies and whole-API contract
  coverage.
- Verify each port against the original method and a real client. Writes preserve
  transactions, permissions and triggers; plain SQL UPDATE does not replace
  Command.
- Unsupported behavior must fail explicitly. Do not return placeholder success.
- The server must not import `legacy` or Handler; use them only for checks and
  algorithm extraction. Ported code retains its source attribution and license.
- Never use user data in `legacy/local_data` for bootstrap, tests or experiments.
  Initialize a new database only through an explicit command.
- Checks: `.venv\Scripts\python.exe -B -X utf8 -m unittest discover -s tests -v`.
  Real Handler tests need its checkout; pass this workspace's path when a tool
  defaults to the old `D:\code\th_codex` location.

- Core implementations live in original sections `src/pyasm/common`, `search`,
  `biz`, `security`, `command`; do not flatten them into tactic_stream or add
  duplicate forwarding domain modules. `tactic_stream/server` owns HTTP/API,
  startup and process monitoring; resources live in config/compatibility/web.
- Start through TacticMonitor with its own tactic-conf.xml. Test crashes, hangs
  and shutdown only with temporary data and processes owned by the test.
- Stop every agent-started test server in finally, including its monitor,
  workers and launcher, before finishing, even after failure/timeout. Verify
  that its child processes are gone. Do not leave test servers running in the
  background. Reuse a user-started server without creating another instance;
  never stop it as test cleanup. Leave an agent-started server running only
  when the user explicitly requests that.
- A small UI change needs a build and the relevant browser check. Do not run the
  complete core suite for a local interface change.

- The user excluded the old production layer: Asset/Shot/Texture, production
  schemas, Flash/Maya naming, SessionContents, commit_session/get_md5_info.
  Create projects through CreateProjectCmd, Administration, plugins and templates.
  Do not restore that layer to fill an API inventory. Record exclusions explicitly.
  The original exception for pyasm.prod.service.ApiXMLRPC and deprecated
  ProdSetting imports was superseded by the following clarification.

- Later user clarification: exclude the `pyasm.prod` directory and imports
  completely, without aliases. The active API lives in `pyasm.web.api_xmlrpc`;
  project settings use `pyasm.biz.ProjectSetting`. `config/prod_setting` remains
  a valid search type. Do not restore deprecated ProdSetting/ProdNodeNaming.

- Unused SnapshotType and `sthpw/snapshot_type` are excluded. Retain the
  snapshot_type field in Snapshot/check-in/naming. TransactionState remains
  part of the core for start/finish/abort/set_state.

- Unused FileAccess and `sthpw/file_access` are excluded: they have no working
  API/callers. Keep `sthpw/interaction` for add_interaction/get_interaction_count.

- HANDLER_DEPLOYMENT.md defines bundles and acceptance criteria: local Windows
  EXE/Vue/Electron + bundled Python/headless TACTIC/SQLite, and server-side
  Apache/headless TACTIC/PostgreSQL. Bundle existing Handler with the local
  edition using its existing launcher/presets. Do not rewrite its code,
  connection or user settings. Handler selects the project separately from the
  server preset through its current mechanism. The launcher manages the local
  server; the server environment manages remote servers. Vue and Handler share
  one backend, permissions, database and repository. Vue must not intercept
  XML-RPC/UploadServer routes. A call inventory does not replace behavioral
  checks; isolated integration tests do not prove GUI/EXE bundle readiness.

- AI assistant requirements: use existing headless TACTIC Search/SObject/
  Command/Security operations with the same SQLite/PostgreSQL contract; retain
  Handler XML-RPC. Connect the model through a replaceable external adapter;
  MCP thinly calls the same operations with the same schemas. Select context
  by objects/fields/source and permissions. Keep draft, validate, preview,
  apply, script test and activation separate. Preview uses the normal dynamic
  Vue renderer. Update history/revisions in the shared write path, including
  XML-RPC/native scripts/import. Apply atomically checks source revisions and
  dependencies; retries must be durably idempotent across workers/restarts.
  Naming uses its native engine with dynamic context/TSQL/scripts, without a
  persistent cache of resolved paths. Mako/subprocess/rollback are not sandboxes:
  trial execution requires verified OS isolation, test data, limits and a log.
  AI receives no more authority than the user; activation separately checks
  execute permission. Documenting these requirements/schemas does not mean
  those APIs have been implemented.

- The administrator agent starts at `docs/admin_agent/START.md`, not this AGENTS
  or UI_ARCHITECTURE. `MODEL.md` explains the domain; read `OPERATIONS.md` and
  `RECIPES.md` as needed. Do not add backlog, release history, work journals or
  future methods presented as available capabilities. Update the relevant
  section and verify affected examples when a described contract changes.
  Keep START + MODEL within 16 KiB, the four core files within 40 KiB; separate
  `SOURCES.md` stays within 16 KiB and links task-specific references with their
  baselines/limitations. Retrieve detailed method inventories through discovery.

- Server XML configuration must appear in Administration with understandable
  names, descriptions, keys, defaults, units and restart requirements. Add new
  supported options to server/configuration.py and the shared Russian dictionary.
  Distinguish configured values from running parameters/CLI overrides. Do not
  imply unknown or unported options work. Never expose secrets or their files.
  Access is admin-only through existing authorization. Only supported EDITABLE
  fields in server/configuration.py may be edited: services, networking, client
  paths, security and scheduling. Validate before writing; services and repository
  web routes use the shared startup validator and require the original XML
  revision. All normal config writes use a shared interprocess lock and atomic
  publication; Config.save_config also keeps the previous XML. Do not restart
  automatically on save. Changing databases/repository roots is not data
  migration; they, root aliases and plugin root remain read-only in the UI.
  Edit secrets without reading their current value; removing one is explicit.
  Preserve drafts between sections.

- Agent instructions and maintained engineering contracts are written in English.
  Keep TH client APIs/help/internal objects distinct from TS server APIs/help/core
  structures; shared Tactic Frame descriptions do not make their runtimes or
  transport contracts interchangeable. Preserve product EN/RU help and translation
  dictionaries. Keep agent backlog, handoffs and work journals outside both Git
  repositories in the workspace's `agent-work/` directory; do not embed them in
  README files or product documentation. Do not ship that directory in bundles.

- New and touched screens must have a readable header (title/context/tools),
  bounded scrolling content and a footer for actions/status/navigation when
  present. Use shared surface/divider/padding rules; preserve the hierarchy on
  resize. Do not float tools and footer actions among data rows without grouping,
  or add an empty footer when the surface has no footer content.

- User clarification, 2026-10-31: round buttons are used in the main menu and every window/dock title bar, including auxiliary windows. Service actions (tables, nested content, local toolbars and auxiliary editors) use square icon controls, with the theme's small corner radius; never full circular rounding. In Frame descriptions reuse iconAction with round:false.

- User clarification, 2026-10-31: edge-to-edge panel backgrounds do not make their controls edge-to-edge. Keep symmetric inner content padding (the shared spacing token), including checkboxes and action rows; preserve authored layout spacing and scrollbar reserves. Check the surface bounds and the control bounds separately.

- The primary search workspace header belongs to main-window chrome: refresh, shelf, tags, quick filters, Help and panel-menu actions stay round. Local/nested service toolbars remain square.
