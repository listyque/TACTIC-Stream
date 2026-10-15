---
group: Configuration
icon: settings
order: 34
---
# Check-in Options

Native `versionless_mode` is configured separately in project `config/prod_setting` or
the server `checkin` section; the project value takes precedence. `copy` duplicates the file,
`hardlink` shares the same file on one volume, and `symlink` requires OS permission.
Windows `WinError 1314` while updating latest means symbolic-link permission is missing;
an explicit `hardlink` setting works for a repository on one volume. This also applies to
note attachments. New check-ins use the selected mode; existing files are not migrated.

> These defaults initialize new searches and new browser check-in jobs. Existing saved search views and prepared queue jobs keep their own explicit settings.

| Setting | Effect |
| --- | --- |
| Result limit | New search page size, integer 1–500; default 20. |
| Loading mode | Explicit pages or infinite scroll. |
| Default result view | Continuous tree by default; cards/table/compact/versions right/bottom are available. |
| Group selected files | Prepare one snapshot for selected files, or one per file. |
| Keep original filename | Preserve filenames rather than apply the native naming template. |
| Generate previews | Pass create_icon to native check-in; disabled means no generated web/icon files. |
| Confirm revision replacement | Start revision check-in with explicit confirmation required. |
| Clean completed check-ins | Remove successful Complete rows after a batch; keep Failed/Result unknown rows for review. |

These values flow from `preferences.checkin` into searchTab/ObjectCheckin/CommitQueue, then native simple_checkin or UploadedCheckinCmd/FileCheckin/IconCreator. Existing collision, revision, rollback, ACL and versionless behavior remains native. Local filesystem move/copy, associated applications and directory scans require a desktop client.

Repositories → Repository Editor sets the enabled destinations and Default for new browser check-ins. The form offers an explicit repository selector. A selected alias goes through UploadedCheckinCmd and native FileCheckin even for one file; callers without a selected alias keep the original simple_checkin path. Revisions retain their snapshot repository. Description → Pin supplies the initial text for new forms; already queued jobs keep their text.
