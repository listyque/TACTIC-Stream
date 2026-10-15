---
reference: Handler
group: Docks
icon: description
order: 29
---
# Description dock

> Description shows and edits the text associated with the current sObject, process or snapshot and
> can pin one text as the description used by the next check-in.

## Current target

The header names the exact object and scope whose description is displayed. Search, process and
snapshot selection can each change that target. Entering edit mode creates a local draft; changing
selection never silently writes it to another object.

## Controls

| Control | Behavior |
| --- | --- |
| **Edit** | Opens the current text as a draft. |
| **Save** | Commits that draft to its current target. |
| **Cancel** | Discards only the current draft and reloads the saved text. |
| **Pin** | Keeps this description as the check-in description while selection changes. |
| **Unpin** | Returns check-in description selection to the current context. |

The dock distinguishes **Editing**, **Unsaved**, **Saving** and **Used for check-in**. A pinned value is
not copied into another object's description; it is only selected as Commit Queue input.

## Typical workflow

1. Select the required object, process or snapshot.
2. Confirm the target title before editing.
3. Edit and Save the stored description.
4. Pin it only when it should follow the next prepared check-in.
5. Unpin after the check-in when the current selection should take over again.

## States and errors

- **No description** means the selected target has no saved text yet.
- **No target** means the workspace has not published a compatible selection.
- A save error preserves the draft for correction and retry.
- Closing or hiding the dock does not implicitly save edited text.

## Stream implementation

Open Workspace panels → Browsing → Description. Current DescriptionEditor.qml/state_detail_editing.py are translated with 8px padding, 6px spacing, native typography and 28px compact controls. Objects/snapshots save through the same native `update(search_key, {description: text})` as Handler. Process text is local/check-in input: it has no writable object key. Pin follows selection; Unpin restores the current target. Unsaved drafts survive selection and hiding the dock; the visible Retained description drafts selector returns to them. They are session memory, not disk backups. Logout/reload warns about unsaved edits. Native update uses last-write-wins, as in Handler; concurrent edits are not merged. A failed save retains text for retry. Shared docking, floating/maximizing and layout presets include this panel.

Pinned text initializes new Save snapshot/Clipboard/Revision forms in this project. Editing that form does not change the pin; already queued jobs keep their own description. Drop Plate and full Snapshot Browser integration remain in the working-panels plan. Native rich text linkification escapes HTML and opens skey/tactic-search links through the existing project route.
