---
group: Configuration
icon: settings
order: 33
---
# Project configuration

> Select a project in the catalogue, then explicitly Activate selected project. Selecting a card alone does not change the workspace.

Deactivate current project leaves no active project. Activating restores that project's saved search tabs/layout and writes the normal project URL. Configuration stays open. These actions affect the workspace immediately; Reset does not undo project activation.

Administrators can create a project through the existing ProjectCreation wizard and native CreateProjectCmd/template importer. Edit selected project uses the native `sthpw/project` record metadata and common RecordForm. Built-in admin/system projects cannot be edited or exported here. Creation and record edits have their own save/validation controls, independent of the outer Configuration draft.

Create template archive executes administrator-only ProjectTemplateExportCmd, which delegates to native ProjectTemplateCreatorCmd and FileUndo. The ZIP is copied into the existing ticket-qualified asset cache for download. The operation exports a reusable template; it does not delete the project or its existing data. A failed activation after creation remains an error in the creation workflow so activation can be retried without creating the project again.

Owners: ProjectSettings/ProjectChooser/ProjectCreation/RecordForm, native CreateProjectCmd, ProjectTemplateCreatorCmd, EditCmd and project catalogue. Private tests verify actual ZIP manifest and access denial for non-administrators.

The Depot tree is on the left; numbered, expandable changelists are in the main work area on the right. Use the arrow to open a depot, stream, directory or changelist. Children load in bounded pages; Load more continues only that branch. Selecting a folder changes the Files context; changelist tabs remain independent. Each changelist shows its project number, description, owner and state, with selectable files underneath. Move and unshelve accept a project changelist number such as #42. Selecting a changelist clears the depot folder filter. Refresh loads the current publication.

Ordinary object Search tabs remain available in file projects. Managed file tables are accessed through the native file API; their schema and counts are available to administrators in Search Types. The Perforce-like workspace opens in the Commit Queue dock. It can stack with Search, move or detach through the existing dock controls. Maximize panel expands it over the working area; Restore panel restores the layout without rewriting saved split ratios. Cached project restoration selects the file interface before server refresh.


The file workspace has independent left Depot/Workspace trees and right configurable work tabs. Use View to open or restore Files, Pending, Submitted, History, Shelved, Reverted, Conflicts or Transfers. Tabs use icons, can be closed, renamed or moved, and are saved for the current user/project. New view tab and Edit view tab configure the source and path filter. Files follows the selected tree by default; fixed sources retain their own filter. Clicking a folder does not replace changelists. Pending includes shelves. Copy changelist number provides a project-local #number for native unshelve/move commands. Workspace in Stream shows indexed server Have; local filesystem scanning remains a Handler operation. Editors open from their operation menus.

Administrator Search tabs read managed file tables through the native file API. The server selects the read command from registered Search Type metadata on every request; an older client metadata cache does not select the generic Search path. Column filters, bounded pages and counts are preserved. These administrative tables remain unavailable to non-administrators. Handler retries only an unsupported optional keyword, not a permission error whose traceback mentions progress.

## Project editor

Edit selected project opens a modal editor with an immutable code, title, category, type, description, archived/template flags and image selection. Closing a changed form offers Keep editing or Discard changes. Save uses the existing native command and image owner. Stream retains additional status/palette fields; unsupported custom inputs block Save explicitly. Archiving uses the native retire operation and its history, not a direct status update. Activation remains a separate immediate workspace operation.
