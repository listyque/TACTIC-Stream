# Tactic Frame: Configuration and projects

This contract describes source ownership, behavior and verification scope.
TH and TS ship independently; native-only actions remain native capabilities.
Use [the shared contract](contract.md) and [the feature index](index.md).

## Composition and command ownership

| Shared module | Native adapter | Browser adapter | Side-effect owner |
| --- | --- | --- | --- |
| configuration.ui | ConfigurationView | Configuration | Existing per-page drafts and Apply/Save/Reset/Close, shared dirty/clear confirmations |
| settings.fields, settings.ui | features/configuration/SettingsPage and public page facades | FrameSettings | ConfigurationController, browser preferences/appearance/network/debug owners |
| repository.ui | ConfigurationRepositoryPage, RepositoryEditorView | RepositorySettings, RepositoryEditor | RepositoryEditorController; existing server Config revision/validation and RepositoryPathsCmd |
| server.ui | Not a native XML editor | ServerConfiguration + FrameSettings | Existing admin configuration API, interprocess XML lock, revisions and restart policy |
| projects/catalog.ui | ConfigurationProjectPage | ProjectSettings | Native ProjectModel/application; existing project catalogue and workspace activation |
| projects/project.ui | ProjectWizardView | ProjectCreation | Existing creation/template commands, uploads and activation |
| projects/editor.ui | ProjectEditorView | ProjectEditorSurface inside RecordForm | Existing ProjectEditorController/queue; native EditCmd and UploadAction |
| projects/templates.ui | ProjectTemplatesView | ProjectTemplates | Existing template install/download/delete commands and modal host |

The shared layer owns geometry, captions, enabled states, responsive layout and
action records. Controllers retain validation, authorization and persistence.
Apply saves the current page, Save saves pending pages and keeps Configuration
open. Reset affects the current page. These are separate page writes, not a
cross-page transaction. Saving presets refreshes only a clean Server draft,
retaining pending changes elsewhere. Notifications still use their existing
immediate owners. Appearance previews until Apply or guarded discard.

Project editing is modal. The browser's named `configuration_edit` XML view adds
the original record fields and image upload, preserving extra status/palette
fields. Code is read-only. `ProjectArchiveAction` delegates lifecycle changes to
SObject.retire/reactivate after ordinary fields have committed inside EditCmd;
it must not write s_status directly and bypass retire history. The catalogue
returns each project's native search key. Unsupported extra inputs explicitly
block Save; they are never silently converted into text fields.

Creation has four steps, dirty guards, separate image/template operations and
an explicit retry-opening state. An unknown creation result blocks another
creation until the catalogue is refreshed. If the project exists, only opening
is retried. Ticket/context changes invalidate late reads and completions.

## Declared capabilities

- Handler retains endpoint presets, ticket generation, local repository platform
  paths, TEAM confirmation, disk cache, DCC schemas and rendering/tray options.
- Stream uses its current origin, browser-owned preferences/cache and supported
  server XML fields. Client paths and repository web paths remain available.
  Secrets are edited without reading stored values; clearing is explicit.
  Saving XML does not automatically restart the backend.
- Stream keeps project status/palette extras and its browser mode/notes choices.
  Repository Sync and S3 remain excluded; no nonworking browser buttons are added.
- ImagePicker and palette pickers are existing house Views inside shared bounds.
  Window chrome, native file dialogs and browser file inputs belong to the host.
  Project previews use a 160 px square crop; uploaded originals remain intact.
  Narrow selected-image states reserve room for Undo. Invalid images report
  through the containing form; Save waits for image validation.
- Matching-template editing remains with the file/check-in work in B12; its
  existing Configuration link is retained. Native presets already use the B04
  shared composition.

## Verification

Run the focused drivers under `tools/frame_configuration/` from the Stream development
checkout, with the actual Handler checkout supplied using `--handler-root`
where supported. The complete shared gate is:

```powershell
python tools/frame_foundation/check_platform.py --handler-root "../../TH"
```

Adjust that path relative to the working directory; in the two-repository
workspace, Stream commands run from `TS/tactic_stream` and Handler is `../../TH`.
Use isolated data, actual input, fresh source fingerprints and independent-package
checks. Generated reports belong in the ignored tool `output/` directories.
Historical release counts and captures are local archive material, not current
acceptance. Offscreen checks do not establish physical touch/IME, compositor,
DCC or deployment readiness; exercise those when the feature requires them.


## Managed server restart

`features/configuration/server_control.ui.mjs` owns the common worker-count and
restart card. Administration exposes it in both products; Stream also retains
its full native configuration form. The draft owner saves through native
`save_configuration` with its source revision. Restart is a separate confirmed
action requiring the same revision, monitor instance UUID and request UUID.

Administrator-only `/admin/configuration/runtime` and `/restart` share the
configuration authentication boundary. `server/lifecycle.py` writes only a fixed
restart marker under the native Config lock. It never spawns a process or accepts
an executable/command. The owning TacticMonitor validates the revision again,
drains its children through the existing shutdown path, rereads configuration
and re-creates the workers/listeners. Its instance UUID changes; request ID and
failure remain in the atomic monitor status. Duplicate accepted IDs return the
same status; stale instances cannot schedule another restart. Explicit CLI
overrides are retained. The marker stores no ticket or provider credential.

The clients poll only during that explicit operation (at most 90 seconds) and
match the request ID and new instance before announcing success. Poll failures
do not resubmit the mutation. Session/owner changes cancel local waiting, not an
accepted server restart. Network-origin changes require opening the new address.
TH uses its standard asynchronous administration owner and the same authenticated
HTTP configuration endpoints, with per-request timeouts and no new
QML global binding; an explicit subclass status signal keeps native property
notification separate from inherited document-state notifications.
