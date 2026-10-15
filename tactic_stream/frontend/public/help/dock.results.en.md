---
reference: Handler
group: Docks
icon: search
order: 26
---
# Search dock

> Search is the main project browser. Each tab keeps its own Search Type, filters, result layout,
> expanded rows, selection, paging mode and scroll position.

## What the dock follows

The active sidebar item chooses the Search Type or saved search. The selected result publishes the
current sObject, process and snapshot to the other docks. Returning to an already loaded tab reveals
its retained result surface instead of requesting and rebuilding every row.

## Top bar

The search toolbar has no dock grip. When results share a stack with another dock,
the common dock header provides the grip beside the panel tabs.
Table date columns use the shared localized date display. Hover a date for its full date and time, without database microseconds.
The column settings button stays at the right of the header; scrollbars occupy separate gutters outside the table cells.
Table headers use the same compact uppercase style as Task Manager. As the table narrows, optional columns disappear in their configured hide order; order 1 hides first and order 0 keeps a column visible. Use **Auto Fit columns** to stretch the remaining columns across the available width, or open column settings to change widths and hide order.
Right-click a table header to sort ascending or descending, group by that column, or remove the current grouping. The grouped column is accented and marked in its header; group headers can be expanded and collapsed.
Collapsing a group preserves staged task changes. If a row is reused for another object, its open task editor closes rather than switching its edit target.
Table previews fill a circular frame, cropping the edges without stretching the image.

| Control | Purpose |
| --- | --- |
| Search field | Searches the current tab and provides server-backed suggestions. |
| Refresh current results | Repeats the current query without replacing its filters. |
| Script shelf | Shows the personal or shared script shelf for the current tab. |
| Tags | Adds or clears tag filters. Typing filters the loaded tag catalog. |
| Quick filters | Enables saved one-click conditions for this Search Type. |
| Workspace panels | Shows, hides or restores project docks. |

On narrow widths the essential search, refresh, Tags and Quick Filters controls remain available;
secondary actions move to the overflow menu.

## Search tabs

- **Add new search tab** opens another independent result context.
- **Search filters and presets** (funnel icon) edits the active tab's filters and saved presets.
- **All search tabs** finds or activates an open tab when the rail is long.
- Hovering a tab in the left rail expands it over the workspace without changing the dock layout.
- Closing a tab does not first activate it; the closed-tab history can restore it.
- A tab-specific script shelf overrides the common shelf only for that tab.

## Restoring your workspace

The browser automatically saves the active project, sidebar sections and search tabs for the signed-in
account. Each search tab retains its query and unsubmitted search text, result mode/grouping, loaded page
offsets, selection, expansion, scroll position and its own dock layout. **Save Preferences** also saves the
current state explicitly. Reloading or signing out and back in restores it. A new account/project starts
empty; Projects and Administration are never inserted automatically. The URL carries the project and
shareable search/object context, without generated internal tab IDs.

The browser retains the last 20 closed search tabs per sidebar section. Restore one from the clock menu
beside the tabs; **Clear tab history** removes only that history. Closing a sidebar section removes its
tabs and history. Search tab reordering uses dragging or the overflow menu's Move left/right commands.
The restored selected object is loaded from the server again and feeds Description/Snapshot Browser;
stale records and credentials are not stored in workspace data. Missing rows lose their selection.
Current permissions and current available Search Types govern restoration.

Local state is isolated by login/project and belongs to this browser. Clearing browser site data removes
it. Storage failure is shown rather than presented as a successful save. Named shared layouts are a
different mechanism: **Workspace panels → Layout presets** stores native project definitions on the
server. See [Windows and modal editors](help://windows) for panel geometry and shared preset rules.

## Context menus

Right-click an object, process, snapshot, relation or file to open the menu for that exact target.
The object menu initially shows the basic TХ actions; **Advanced menu** reveals preview/duplicate,
copy sKey/web link, new-tab and editing tools. **Basic menu** collapses it again.
Save snapshot/Clipboard/MultiCheckin use the common check-in preparation and queue. Revision is tied
to the chosen snapshot. Multi-selection operates on the selected objects, not just the hovered row.
Destructive actions use the native confirmed editor and permissions, including **Delete Whole Tree**
for a versionless snapshot: the command exposes dependencies for review; it is not an unchecked cascade.

File menus resolve the selected file code inside its native snapshot. Copy File Path returns its
repository path; Copy Web Link returns its file URL; Open File shows the same file in the browser.
Copy To Clipboard copies an image and requires HTTPS/localhost plus browser permission.
Show Folder/Watch Folder remain visible with a desktop limitation; this web application does not
connect to TХ or launch desktop/DCC applications. Browser additions such as object details, related
objects and retire/reactivate remain visible in the expanded menu.

## Result presentation

The footer and overflow menu provide **Sort items**, **Group items**, **Change search results view**
and **Result actions**. In the compact menu, sorting, grouping and view choice open submenus;
refresh remains beside the search field. Tree, list and card presentations use the same query and
selection; changing the view never edits project data. An sObject subtitle shows its description,
the pipeline's
user-facing name and its configured category; the pipeline code is only a fallback.
Category names come from the field's configured values/labels (including expressions).
Their lookup runs in the search worker and is cached; refreshing results reloads it.
An unknown category retains its code.
Double-click tags or a multiline description to edit them in a wide panel.
Add tags with Enter or Add, remove them individually, and apply the draft with Save.
Cancel or Escape discards the draft; typing alone does not save changes.
Inline table editors use the full choice list of the underlying field, including
columns mapped to another field through the server's action configuration.
Loading field choices retries temporary server failures up to three attempts;
a persistent failure remains visible as an error.
The results table uses the same flat row styling and rounded header as Task Manager, with horizontal separators and a default row height of 58. Circular previews fit inside each row; widening their column does not enlarge the row by default.
Note entries use the process title and color configured by the active pipeline; the number at the right is the note count for that process.
In table view, **Fit to Preview** grows rows with the Preview column. The Compact, Comfortable and Large
presets set an explicit row height instead. Task Workflow keeps status and assignee controls separate;
cards keep a stable width. When the column cannot show every card, hovering over the Task Workflow cell opens
the same editable cards above the table. The centered task indicator opens Task Manager for the
object. Large rows also show each task's localized planned start and end dates;
click that date row to edit both values. Changing a task's status, assignee, or dates creates a local
draft for the selected rows.
The Save and Reset buttons appear above the table with an unsaved-task count.
Task calendars load only when you click the dates, rather than for every row when opening the table.
Save applies all staged task changes; Reset discards them. Failed saves retain
unconfirmed changes. Changing selection does not submit or discard the drafts.
Saving an object field updates only affected table rows, preserving scroll position and selection.
Hovering an overflowing task cell expands its cards over the same table row, extending sideways within the window. The inline cards are hidden while this overlay is open, so tasks are not shown twice. For multiple selected rows, hovering over a selected workflow cell expands the tasks of all visible selected rows. Other cells do not trigger expansion.
In card view, click a card to select it, use its action buttons directly, or click empty grid space to clear selection.
Object cards place the title and description below the top controls. Task and note buttons have their own footer, including when their counts are zero.
Card and preview corners remain rounded during scrolling.
Related-object cards always show Create and, for instance relations, Link actions.
Nonempty relations also offer an Open button; double-clicking the card opens the same contents.

Expanded hierarchy rows load related objects only when needed. Ctrl and Shift extend selection.
The context menu always applies to the item under the pointer; middle-click opens a new Search tab
only for sObject result items.
Delete appears only for an object created by the signed-in user less than one hour ago. For a
multi-selection, every selected object must qualify; the deletion dialog checks again before deleting.

## Paging and synchronization

| Control | Behavior |
| --- | --- |
| Previous / Next page | Moves through server pages in paged mode. |
| Page number | Jumps to a known page. |
| Page size | Changes the number requested per page. |
| Pages / Continuous | Chooses explicit pages or append-on-scroll loading. |
| Sync current Search Type | Refreshes server metadata and this Search Type's result state. |

Continuous loading appends the next page near the end. It does not imply that every server result is
already loaded; counts and bulk actions distinguish loaded rows from the complete query.

## Typical workflow

1. Open a Search Type or saved search from the sidebar.
2. Add text, tags, quick filters or Advanced Search rules.
3. Choose grouping and presentation without changing the query.
4. Select one or several results and use their context or overflow actions.
5. Inspect snapshots, tasks, description and notes in the following docks.

## Empty, loading and error states

- A loading overlay means the current generation is still pending; switching tabs does not apply a
  stale response to the newly selected tab.
- An empty result means the combined active filters returned no rows, not that the Search Type is missing.
- A server error preserves the tab and its filters so Refresh can retry the same query.
- If the layout or tab state is unusable, **Reset layout** restores dock geometry; it does not delete saved searches.

## Snapshot file availability

Online/Offline describes files of an existing snapshot. When there is no snapshot, no file availability label is displayed. An existing snapshot with missing files still displays File Offline. This rule is shared by TACTIC-Handler and TACTIC Stream.

## Continuous tree: mouse and actions

The tree follows the current `WorkspaceResultItem.qml`, using logical pixels at browser zoom 100%:
object rows 100 px, relation rows 38 px, process rows 32 px, snapshot rows 84 px and nesting 24 px.

- A single click selects the row, including its preview. The disclosure arrow or a double click expands/collapses it; Shift applies disclosure recursively. Double-clicking a snapshot opens its file preview.
- Ctrl/Cmd toggles compatible siblings; Shift selects a range of siblings. Branch headings remain single selections. Right-click preserves an existing multi-selection. Middle-click opens the object in another search tab.
- Hovering the title reveals **Save snapshot** and, when a snapshot exists, **Open snapshot**. An object title keeps priority: actions disappear if they would truncate it.
- Hovering an object reveals **Related and child objects**. Its menu offers parent and child types from the project schema; task and note buttons offer a process, and **Choose task** handles several tasks in one process. The Knowledge Base button stays available when linked articles exist.
- Relation headings expose **Link existing objects** for instance relationships, **Create related object**, and the child count. Empty task/note buttons on process rows appear on hover. These buttons do not select or expand their row.
- Hover tools remain stable while the pointer crosses their controls (500 ms release delay) and while their menu is open. Scrolling suppresses mouse hover decoration; keyboard focus remains accessible.
- Versionless snapshots expand directly into version rows, without a separate “Versions” heading. Snapshot rows show the file name/group, size, version/revision, repository, author, description and metadata. Hover the relative date for the full timestamp.

The existing context menu retains Stream's object details, copy Search Key/web link and other advanced actions. Repository Sync, Watch Folder and DCC commands are intentionally excluded from the web client. Browser file opening uses preview/download rather than launching a local application.


### Publish and relation topology

On phones, this hierarchy uses separate sliding screens without expanded rows. See [Mobile application](help://mobile)
for gestures, navigation, versions and scroll restoration. This is a Stream phone presentation; Handler's desktop tree is the reference for data and actions.

Expanding an object in Continuous tree shows its direct publish contexts first, then schema relations, then workflow processes. These are the same snapshot rows and version actions used inside the publish process. Reloading restores both disclosure paths. A snapshot without a description shows **No description**; an author without a full name keeps the login.

A relation does not recurse back into any ancestor object's Search Type, and an object already in the ancestor path is excluded. The first self-type relationship still works; schema links remain available from the object menu. Thus Assets → Texture → Brushed Metal shows **Icon**, **Attachment**, **Publish**, without a reverse Assets branch.

Main-search subtitles resolve category labels (for example, Props) from native SelectWdg/edit_definition options. Relation children follow Handler's shorter description-only subtitle and raw category metadata; literal selects still show their labels, such as Diffuse. Metadata follows record-field order.
