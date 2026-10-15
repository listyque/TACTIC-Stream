---
reference: Handler
group: Workflows
icon: publish
order: 16
---
# Commit Queue

> Commit Queue is the final review and execution point for prepared check-ins. Nothing is submitted
> merely by adding it: select an operation, verify its files and destination, then choose a commit
> action.

## Queue toolbar

On a phone, the queue opens below the main application header with a compact file list,
status and a bottom **Commit all** button. Details stay collapsed initially. Tap a row or
**Check-in details** to inspect source files, description and advanced options; tap the
details button again to collapse them. Auto-clean, ordering and clearing are in the bottom
menu. Errors appear in the affected row, with **Retry** for failed operations. Duplicate
decisions remain visible even with details collapsed.

| Control | What it does |
| --- | --- |
| **Help** | Opens this article. |
| **Auto-clean** | Removes each successful operation automatically. Failed or cancelled operations remain for diagnosis or retry. |
| **Move operation up / down** | Changes execution order for the selected queue row. The buttons appear only when more than one operation exists. |
| **Clear completed** | Removes completed rows and leaves prepared, running, failed, and cancelled work untouched. |
| **Clear queue** | Removes every prepared, failed, and completed operation after confirmation. It does not submit anything. |

Each queue row shows its check state, target, context, file count, status, and progress. Select a row
to edit it. The close button removes only that operation. Checked rows are used by **Commit selected**
and by batch editing; selecting a row is not the same as checking it.

## Files pane

The lower-left pane lists source files belonging to the selected operation. Its close button removes
that file from this operation only. Removing the last required file can make an operation invalid;
the source file on disk is not deleted.

## Operation summary and previews

The summary identifies the target object and snapshot status. **Add context** edits only the branch
below the base process. Preview actions are:

| Action | Result |
| --- | --- |
| **Capture screenshot** | Uses browser screen capture permission and attaches an image. HTTPS/localhost and browser support are required. |
| **Choose preview images** | Selects one or more existing images. |
| **Paste preview image from clipboard** | Adds the current clipboard image when one is available. |
| **Manage selected previews** | Opens the full preview list, where an individual image can be removed. |
| **Clear operation previews** | Removes all attached previews from the operation, not from disk. |

At narrow widths, secondary preview actions move into the three-dot menu without changing their
behavior.

## Basic and advanced settings

**Description** becomes snapshot metadata. **Advanced options** exposes:

| Field | Meaning |
| --- | --- |
| **Repository** | Destination repository. Titles are shown to the user; native TACTIC codes remain internal. |
| **Version** | Explicit numeric version. Leave it empty or zero when automatic allocation should be used. |
| **Method** | Upload in the browser. Local Preallocate, In-Place, Copy and Move require a desktop connection and remain disabled. |
| **Filename** | Explicit destination name. Leave it empty to use naming rules; it is disabled when context is the filename. |
| **Update versionless** | Refreshes the versionless/latest snapshot along with the numbered version. |
| **Commit versionless only** | Produces only the versionless result. |
| **Keep source filename** | Preserves source names instead of applying generated names. |
| **Use context as filename** | Derives the filename from snapshot context. |
| **Generate previews** | Produces supported thumbnail and preview derivatives. |

When **Apply every edit to checked items** is enabled, every change below it applies to the current
operation and all checked rows. Review the checked set before editing.

## Naming preview

The filename row expands to show the source name plus predicted versioned and versionless paths for
every file. **Naming Editor** changes the templates used to generate them. A waiting label means the
operation has not produced a naming preview yet; it is not a committed path.

## Starting and controlling work

| Control | What it does |
| --- | --- |
| **Commit all** | Starts every ready operation in queue order. |
| **More send actions → Commit current** | Starts only the selected operation. |
| **More send actions → Commit selected** | Starts checked ready operations. |
| **Cancel** | Requests cancellation of the running work. |
| **Retry** | Re-runs a failed or cancelled operation after its cause is corrected. |

A duplicate prompt pauses preparation: **Replace** targets the matching item, **Add another** keeps a
separate duplicate, and **Ignore duplicate** dismisses that duplicate decision. Read the operation
error before retrying; the queue keeps full failure details rather than treating a failed row as
completed.

## Browser recovery

See [Commit Queue dock](dock.commit_queue.en.md) for missing-file reselection, cancellation boundaries, unknown results, permissions and transfer limits. [Drop Plate](dock.drop_plate.en.md) covers matching and preparation.
