---
reference: Handler → Stream
group: Docks
icon: move-to-inbox
order: 36
---
# Drop Plate dock

Drop Plate prepares files for the application-owned Commit Queue. Adding or queueing a file does not submit it.

## Files and groups

Use **Files**, **Directory**, drag-and-drop or paste actual clipboard files. **Include subfolders** includes nested directory entries. Browsers provide filenames and relative directory paths, not access to pasted absolute paths. The current preparation accepts up to 1000 files.

Native Handler `MatchTemplate` and `FileObject` recognize individual files, frame sequences, UDIM, UV tiles, layers and combined sequences. Sparse frames remain compressed in metadata. Each row shows its pattern, member count, size and matching state. Filter by filename or extension, uncheck unwanted groups, or remove a group. Removing preparation never deletes source files.

Select the owner in Results or Snapshot Browser. The footer captures its project, process and context. **Group check-in** queues all checked groups as one snapshot; otherwise each group becomes a separate operation. **Keep filename** preserves source names. Description can come from the Description panel.

## Matching Templates

The editor uses the 19 current Handler defaults, including initially disabled layer patterns. Create, duplicate, enable, reorder and delete templates. The two filename fallback templates are mandatory and locked. Pattern priority and native matching rules determine group recognition. Optional **Process mapping** and **Context mapping** restrict a pattern to that exact selection; empty values apply everywhere. **Test on filename** calls the native matcher and reports the recognized type or an error. Supported tokens: `$FILENAME`, `$EXT`, `$FRAME`, `$UDIM`, `$UV`, `$LAYER`, separated by `.` or `_`. A token occurs once. Frame padding is 1–9.

Save applies the template draft and rematches the plate; Cancel discards it. Templates and padding are browser preferences, separate from server `config/naming` destination rules. The browser supports relative paths and explicit file selection. **Show folder**, desktop launch actions and DCC operations require a desktop connection and are unavailable here.

## Add to queue

Queueing captures the selected files, ticket, project and target. Subsequent project changes do not retarget queued work. Preparation moves the selected File handles from Drop Plate into Commit Queue, as in Handler. The queue retains them until completion or explicit removal. Commit Queue owns destination validation, editing, upload, cancel/retry and Snapshot Browser results. Do not refresh with unsent files unless you intend to reselect them; browser permissions are not persisted.
