---
reference: Handler → Stream
group: Docks
icon: cloud-upload
order: 38
---
# Commit Queue dock

The dock and dialog above Administration share one application-owned queue. Files remain unsubmitted until **Commit all**, **Commit current**, **Commit selected** or **Retry** is pressed.

Restoring workspace panels does not open a queue dialog or switch away from the saved active panel.
On phones, the restored queue stays inside its pane; **Back to search** returns to results.
Closing a separate queue window hides it without opening its dock. These actions keep the pending operations.

The queue has one visible host: dock content without window controls, or a
separate window while a modal editor remains open. Wait for the preparation
dialog to close before choosing that host. Reopening Commit Queue preserves all
prepared jobs and returns to the dock when no modal editor remains open.

## Review and execution

Select a row to review its source files, owner, process/context, description, previews and destination. Checking a row is separate from selecting it: checked identities control **Commit selected** and batch editing. **Commit all** runs every ready operation in order. Move operations up/down or remove them; automatic naming plans recalculate against the rows still pending in that context.

**Advanced options** includes repository, explicit version, filename and file options. Empty or zero version means automatic allocation. A revision keeps its captured numbered snapshot and repository; versionless-only has no numbered output. **Keep source filename** switches off latest updating; **Commit versionless only** requires it. **Generate previews** uses native IconCreator, including an explicitly selected image. Naming preview shows every main/group member destination and links to Naming Editor. Read-only users may review; actual check-in requires owner, snapshot, file and relevant field permissions.

Only **Upload** is available as browser transfer. Server staging uses native inplace registration and the same Command/FileUndo journal. Copy, Move, In-Place and Preallocate as local transfer methods, DCC saving and TH connections are unavailable. Repository Sync and S3 are excluded.

## Errors and recovery

Cancel stops an upload or a waiting server job. A transaction that has started can finish. Failed or cancelled rows retain files for Retry. The browser recovers lost replies from the server queue. If the worker reports **Result unknown**, inspect Snapshot Browser before preparing a new operation. Successful rows can be removed automatically by **Auto-clean**.

Closing the dock keeps the queue alive. Tabs share operation metadata for the same account. A reload checks submitted work on the server. Unsent or partially uploaded operations return as **Missing files**. Reselect matching relative paths and sizes, using Directory when basenames collide. Completed rows open their exact result in Snapshot Browser. The Stream queue service runs submitted operations.

See [Commit Queue](commit_queue.en.md) for controls and preview actions, and [Internal object model](core_model.en.md) for the native transaction path.
