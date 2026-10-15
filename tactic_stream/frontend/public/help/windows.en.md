---
group: Reference
icon: window-restore
order: 25
---
# Windows and modal editors

> Functional tools use the shared browser window controls. An editor keeps its prepared context and asks how to resolve unsaved changes.

## Help and unfinished gestures

Help keeps the selected article, search and each article's scroll position when closed and reopened.
A contextual Help button selects its article in the same window. Search includes article contents.
Reload rereads the files and preserves the current position; changing the interface language while
Help is closed is applied when it next opens. **Open article file** opens the source; **Download article**
saves a Markdown copy. On a narrow screen, **Help topics** switches between the topic list and the reader.

Move a floating dock by its title; use its six-dot grip to dock it. Dropping onto another dock's title
exchanges positions; its center creates a tab stack. Edges split the target. Escape or a cancelled
pointer gesture restores the previous position or split; it does not accept the preview.

## Common window behavior

| Control | Action |
| --- | --- |
| Drag the title bar | Move the window inside the viewport. |
| Maximize / Restore | Fill the viewport or return to the previous geometry. |
| Double-click the title bar / Alt+F10 | Toggle maximize. |
| Focus the title bar, Alt+arrows / Alt+Shift+arrows | Move / resize the window with the keyboard. |
| Drag any edge or corner | Resize the window; Escape cancels the current gesture. |
| Close / Escape | Request closure; the owning editor protects pending writes and drafts. |

Menus, suggestions and short confirmations keep their own popup behavior. On a small screen, functional windows fill the available space and their content scrolls inside the window.

## Workspace docks and layouts

Use **Workspace panels** beside Search: Browsing contains Results, Description, Snapshot Browser and
Knowledge Base; Tasks and reports contains the implemented Task Manager; Tools contains Drop Plate and
Commit Queue. The catalog shows implemented browser panels, not empty placeholders for all TХ reports.
Results cannot be closed. Standalone Results/Commit Queue keep their own compact toolbars.

Drag a dock's six-dot grip onto a highlighted left/right/top/bottom/stack target. Right-click the grip
or title for Help, Float/Dock, Maximize/Restore and Close. The grip is a drag surface, not a button.
The visible position menu also offers an explicit target, docking side, Stack and Swap. Floating docks
stay within the browser workspace. Resize any of their eight edges/corners; Escape, window blur or
pointer cancellation rolls back an unfinished gesture. Splitters use axis-appropriate cursors and
Arrow keys; Home/End select their limits. The title's Alt+F10 toggles maximize. On a floating title,
Alt+arrows moves the panel, Alt+Shift+arrows resizes it. Shift+F10 opens the title context menu.

Panels sharing a stack use the common tab control: arrows/Home/End select, Delete or middle-click
closes a closable panel, dragging reorders. Results remains available. Closing a dock hides it; reopen
it from Workspace panels. Search tab state saves split ratios, stack order/active panel, visibility,
floating positions/sizes/z-order and maximize/restore state. A narrow view projects these panels into
a compact stack without rewriting the desktop split tree.

**Layout presets** lists named project definitions with Refresh, apply, save, replace and delete.
Administrators manage them; replacement/deletion use confirmation and optimistic revision checks.
Presets assigned to sidebar views cannot be deleted while still assigned. An assigned preset applies
to a newly opened view, while that tab's later personal layout takes precedence. Switching tabs or
projects during a load cannot apply an old response to the new context.
The stored native document contains `layout` (split/stack tree) and `panels` (native geometry/visibility).
Browser maximize/compact presentation is personal state and is not added to the shared native preset.
Presets save dock arrangement, not search queries, editor drafts or credentials.

**Reset workspace layout** restores dock defaults without removing search tabs, history or named
presets. Floating and maximizable windows are visible browser additions. Native OS-detached dock
windows are not supported; dialogs keep their geometry while mounted, but are not reopened by a
saved layout. Unsaved object/description/task edits retain their existing leave/discard guards and
are not silently committed by a layout save.

Floating docks move by the free area of their title bar, including the title text. This gesture moves
the panel without docking it; use the six-dot grip to dock it. The grip shows an open hand and a closed
hand during dragging. A docked panel moves through its grip, leaving its title tabs available for clicks.
The tab strip scrolls horizontally without a vertical scrollbar in the title.

Like Handler, each Search tab retains its own dock visibility, including Commit Queue. Switching Search
tabs can show or hide its panel; the queue contents are retained independently of that visibility.

## Prepared changes

Configuration, Administration, object/task editors and Script Editor keep drafts separate from saved data. Closing does not mean that an operation succeeded. If a revision conflict occurs, retain the draft and reload current server data before deciding what to save.

Saving and cancelling follow the current editor's controls. If a write has an uncertain result after a connection error, inspect the server state before retrying it.

## Profile and related tools

The account menu opens your profile and the user directory. Clicking a sender's name or avatar opens that person's profile without changing your signed-in identity.

The profile shows project tasks, workflow status/process groups, permitted weekly work hours and recent activity. Complete and Approved workflow mappings determine finished tasks. Clicking a status or process opens Task Manager with that user's filter; the full activity action opens Activity Feed for that user.

## If a tool appears blocked

1. Finish or cancel the active child editor or confirmation.
2. Close Help to return to its owning window; the previous chat or editor draft remains available.
3. Restore or maximize the shared window when its geometry is inconvenient.
4. Read Debug Log if content failed to initialize; an empty view does not prove success.


## Phone presentation

At 700px and below, task rows adapt to a vertical list; task fields are collapsed by default in Inspector. Enter adds a newline and the explicit button sends notes/messages. Phone panel selection is separate from the desktop layout. See **Mobile application** in Help for touch actions, keyboard viewport, persistence and verified limits.
