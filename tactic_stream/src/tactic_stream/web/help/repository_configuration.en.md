---
group: Configuration
icon: settings
order: 32
---
# Repository configuration

> Repository storage shows actual aliases resolved by native Config/Environment. Open Repository Editor to work with a selected alias; its layout follows `RepositoryEditorView.qml`.

The editor has a catalogue, display name, server path, Windows/Linux client paths, color, availability and Advanced settings. Names/colors and client paths edit the same File repository draft as advanced XML settings; there is no second repository store. Empty client paths fall back to the native server root. Advanced settings retain version padding, checksums, versionless copy/symlink/hardlink, web URL, sandbox/local/handoff paths and their original validators.

Enabled and Default choose the repositories available for new browser check-ins and their initial destination. They live in browser preferences. Add custom repository registers an alias in the native `checkin/asset_base_dir` map; display/color/client paths and URL stay in the same Config draft. Revisions keep their original repository. Native SDK callers without an explicit alias keep the original Naming behavior; this browser preference does not redirect all server clients.

Server roots are editable. Before changing a root, pause check-ins and copy its complete files to an existing new server directory. Saving verifies native `sthpw/file` paths and SHA-256 of present source files against the destination. Missing, changed or outside-root destinations and removal of referenced aliases are rejected. Saving never moves or deletes files. Restart the backend after changing roots/URLs so HTTP routes use the new mapping. This is a check of a prepared directory switch, not an online/concurrent migration tool. Legacy `base_dir_alias` is retained with its native Environment semantics; new aliases use `asset_base_dir` to keep web URLs independent. Windows/Linux client paths are mappings returned by `get_base_dirs`/`get_client_dir`; the browser cannot inspect another computer.

Check paths invokes administrator-only `tactic.ui.app.RepositoryPathsCmd`. It checks current editor paths, including an unsaved new repository, through FileUndo directory creation and a temporary read/write probe. Blank/invalid paths are rejected or reported inaccessible; probes are removed. Load alone never creates directories. The probe does not relocate or replace existing files.

Configuration Apply saves this page; Reset restores it without affecting other pages. Inside Repository Editor, Cancel restores the repository page and Save applies it; neither closes the editor. Close retains pending edits; Configuration Cancel offers discard/save. The editor uses the shared movable/maximizable window.

Owners: `RepositorySettings.vue`, `RepositoryEditor.vue`, the shared `ServerConfiguration.vue` draft, `RepositoryPathsCmd` and native Config/Environment/FileUndo. Repository Sync, watch-folder mappings and S3 are excluded.
