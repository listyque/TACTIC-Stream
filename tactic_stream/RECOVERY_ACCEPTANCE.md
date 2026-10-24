# L12 upgrade, backup and restoration acceptance

This checkpoint verifies the delivered 0.112.192 source/server packages against
0.112.193. The Windows EXE first appeared in 0.112.193: the SQLite test upgrades
an installed **previous wheel**, not an invented previous Windows EXE. The server
test uses the actual previous/current image IDs from their delivery manifests.
Neither test is a same-release update. These releases exercise the native upgrade
path without introducing a new schema conversion; they do not certify arbitrary
older releases, SQLite/PostgreSQL conversion or legacy project migration.

Upgrade trials create isolated data, passwords, repositories, processes and Docker
volumes. An additional offline trial reads the existing stopped local data directory
and works with private copies. Public reports contain outcomes, versions and
aggregate counts; private backup payloads and copies are deleted after verification.

## Verified operations

| Boundary | SQLite / Windows | PostgreSQL / Apache |
| --- | --- | --- |
| Previous installation | Installed 0.112.192 wheel and Handler 0.6.0.139 | Exported 0.112.192 images, native initialization |
| Upgrade | 0.112.193 embedded runtime, native CLI upgrade | Exported 0.112.193 images, package `manage.py update` |
| Preserved state | Object/description, tasks, notes, snapshot/file bytes, naming, XML, native Handler settings | Same domain data, password, XML, repository, Apache/Webmin configuration and `.local` secrets |
| Backups | Complete cold profile copies before/after upgrade with per-file SHA-256 | `pg_dump -Fc --create` for every fixture database; cold repository/configuration volumes and secrets |
| Restore | New directory, explicit server-path relocation; original directory unavailable | New Compose projects and volumes; original services down; no shared application data volume |
| Rollback | Previous binary plus its pre-upgrade backup | Previous image IDs plus pre-upgrade database/config/repository backup |

Every restoration checks the saved object and concrete snapshot identity, tasks,
notes, naming configuration, administrator password, native SDK repository paths
and HTTP file bytes. PostgreSQL checks also exercise Apache authentication/routes,
current assets, transactions and Webmin certificate/login/logout. Test containers
and volumes are removed after verification. CRC and per-file hashes are validated
before restoration writes; existing target directories are refused.

The upgrade fixtures are small and use the bundled PostgreSQL `stream` role.
TB-scale datasets, custom PostgreSQL roles/tablespaces, external storage roots and point-in-time
recovery are not accepted by these results. They need their own inventories and
operator-reviewed restore procedures. The scripts below are acceptance drivers;
they deliberately create their own data and are not production backup commands.

## Existing local data, offline trial

The existing stopped Windows data root was copied to a private working directory,
then to a separate backup directory, then restored into a third directory with
Windows Robocopy `/COPY:DAT /DCOPY:DAT`. It contains **4 SQLite databases, 127 tables,
122,327 rows and 21,032 files (7,918,158,004 bytes)**, including assets and
`assets.file-projects`. All SQLite integrity checks passed. File SHA-256, size,
mtime, readonly attributes and empty directories matched after restoration. A final
source inventory matched the initial inventory, including the original login hash
bytes. The stale monitor PID was absent and the application port was not listening.

Only copied databases were opened, with SQLite read-only connections. Application
jobs/plugins were not started for this dataset. Custom NTFS ACL/ownership recovery
was not tested by `/COPY:DAT`. The source was unchanged and temporary copies were
removed; the public aggregate report is `.test-tmp/l12-existing-data-recovery-193.json`.
This is a restoration trial, not a retained production backup.

```powershell
.venv/Scripts/python.exe -B -m tools.local_data_recovery_check --source-data data --output .test-tmp/l12-existing-data-recovery-193.json
```

The driver refuses an active monitor PID, a listening local application port,
external repository roots/links, and any source change observed during the trial.

## Operational procedure

1. Record the exact application/Handler versions, delivery manifests and archive
   SHA-256. Keep the old binaries/images. Identify every project database, configured
   repository root, plugin/template directory, external secret file and Handler
   profile. A directory outside the normal data root needs its own backup entry.
2. Stop every writer. On Windows close Stream and Handler and confirm the owned
   monitor/workers have stopped. On the server stop `apache` and `app` with Compose;
   leave PostgreSQL running only while creating logical dumps. Do not copy a live
   PostgreSQL data directory or treat separate live SQLite file copies as one backup.
3. For SQLite copy the complete stopped data root: all system/project DB files,
   sidecars, assets, config, plugins/templates and browser state. Include the actual
   Handler profile separately when `--data-dir` and `TACTIC_HANDLER_SETTINGS_DIR`
   point to different roots. Handler 0.6.0.139 normally stored `settings` inside its
   program directory; copy that existing tree to the new external profile using its
   native configuration layout. Do not replace it with default presets.
4. For PostgreSQL create custom-format dumps of the system and every registered
   project database with `pg_dump -Fc --create`. Preserve owners/ACLs; prepare any
   custom roles/tablespaces before restoring them. The bundled deployment requires
   its existing `stream` role and matching `.local/postgres-password`. Save cold
   `stream_data`, `apache_config` and `webmin_config` contents, and `.local` itself.
   Preserve file owners/modes and symlinks in Linux volume archives. Keep backups
   private: they contain password hashes, tickets, profiles, TLS keys and secrets.
5. Inventory all backup files and SHA-256 before reopening the source. Validate the
   completed archive and perform a restoration trial. PowerShell 5.1 text redirection
   can corrupt binary streams: write dumps/tars to files inside the container and
   use `docker cp`, or use Python subprocess byte streams as the acceptance driver does.
6. Restore into a **new empty** data root or new Compose project/volumes. Verify all
   checksums first. Restore PostgreSQL dumps with `pg_restore --exit-on-error --create
   --dbname postgres`, then repository/configuration volumes and the original secrets.
   Keep database, repository, configuration and binaries from the same backup point.
7. When a Windows data root moves, explicitly rebase server-owned XML paths under
   the old root: `install/tmp_dir`, `checkin/asset_base_dir`, and owned Windows
   local/sandbox paths. External roots and client paths require their own mapping;
   do not replace arbitrary strings in database contents. Start with `--data-dir`
   pointing to the restored root. Reuse the old port only if available and update
   Handler presets through their existing owner when the server address changes.
8. Validate SQLite `PRAGMA integrity_check` with closed connections, or PostgreSQL
   restores with errors treated as failures. Start the matching binary and check
   login/permissions, known objects/tasks/notes, snapshot identity, repository paths
   and actual file bytes. Make the original instance unavailable for the trial so
   accidentally reading the old repository cannot pass. Binary replacement alone
   is not database rollback; restore the corresponding pre-upgrade backup too.

For example, a binary-safe PostgreSQL dump uses the existing Compose secret without
putting the password in command arguments (substitute the actual database name):

```sh
docker compose exec -T postgres sh -ec 'export PGPASSWORD="$(cat /run/secrets/postgres_password)"; pg_dump -U stream -Fc --create -f /tmp/sthpw.dump sthpw'
docker compose cp postgres:/tmp/sthpw.dump /private/backup/sthpw.dump
```

## Reproduce the acceptance on owned fixtures

Run from the Stream development checkout with the existing environment:

```powershell
.venv/Scripts/python.exe -B -m tools.delivery_recovery_checks --previous-source ../releases/source-0.112.192-ready --windows-bundle ../releases/windows-0.112.193-final --output .test-tmp/l12-sqlite-recovery-193.json
.venv/Scripts/python.exe -B -m tools.server_recovery_checks --previous-server ../releases/server-0.112.192-final --server-package ../releases/server-0.112.193-final --handler ../releases/windows-0.112.193-final/TACTIC-Handler --output .test-tmp/l12-postgres-recovery-193.json
.venv/Scripts/python.exe -B -m unittest tests.test_delivery_recovery
.venv/Scripts/python.exe -B -m unittest tests.test_local_data_recovery
```

Docker images identified by both server manifests must already be loaded. Image
references in the disposable Compose copies are pinned to those exact IDs, so a
mutable local tag cannot silently replace a delivered image. Production volumes,
containers and source package files are not changed by the acceptance drivers.

## Clean Windows acceptance

The developer-host test, poisoned `PATH`/Python environment, standalone test kit and
successful backups do **not** prove a clean Windows installation. A fresh guest
must run the delivery and write a successful result itself.

```powershell
.venv/Scripts/python.exe -B -m tools.prepare_clean_windows --windows-archive ../releases/windows-0.112.193-final.zip --output ../releases/clean-windows-0.112.193
```

The kit includes only the published ZIP, acceptance scripts and the installed pinned
Playwright packages/licenses. It uses Node from the delivered Electron and Python
from the embedded runtime; no development checkout, Node installation, Python
installation or package download is available in the guest. First launch uses the
actual native password console, then login/SDK/restart/shutdown and native Handler
are exercised. The final program inventory must have neither changed nor gained files.

With Windows Sandbox **already enabled**, open `Check TACTIC Stream.wsb`. It gives
the guest 8 GB, disables networking/vGPU/clipboard, maps only kit input read-only
and a dedicated result folder writable, and runs the check automatically. Inspect
`results/result.json` and `desktop.png` before closing the guest. Guest debug logs
remain in `C:\L12\Work`; closing Sandbox discards guest data. A missing/failed result
is not a passed clean-machine check. Sandbox configuration follows the
[Microsoft configuration contract](https://learn.microsoft.com/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file).

The published **0.112.193 ZIP passed on a fresh Windows 11 Enterprise Evaluation
10.0.26300 installation** in an owned VMware Workstation 17.6.3 VM. The official
[Microsoft evaluation download](https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise)
provided the 26H2 build 26300.9457 image; the extracted Microsoft `setup.exe` signature
was valid. The downloaded ISO SHA-256 (recorded, not compared with a published
Microsoft checksum) is `bc3f24086ebadc94489066b5ad78089e2cf5c3491e90e790bb81a2b199c10e38`.

The new 64 GB virtual disk had no project data. UEFI/Secure Boot and a virtual TPM
were enabled; networking, shared folders, clipboard and 3D acceleration were disabled.
No Python, Node, VMware Tools, runtime installer or package download was added to
the guest. Windows exposed its Python Store execution alias; actual checks used only
bundled Python 3.14.9 and Electron/Node. Inputs arrived on a separate read-only DVD,
results through the VM serial pipe. The runner test body was byte-identical to the
versioned Sandbox runner; only its guest identity guard and report kind changed for
`L12Acceptance` / `TS-L12-CLEAN` / VMware. Their hashes are recorded in
`L12_RECOVERY_ACCEPTANCE_2026-10-24.json`.

Embedded Python/Qt 6.11.1 isolation, native first-password console, Electron login,
12 Handler SDK scenarios, persisted session/localStorage, restart and complete owned
monitor/worker shutdown passed. The final 7113-file program inventory matched the
manifest exactly. Native Handler passed its offline startup smoke with the software
renderer; this does not certify GPU rendering or its full interactive GUI.
The VM shut down and no VM remained running. VMware refused authentication for the
encrypted-VM snapshot operation, so no pristine snapshot was created; the check ran
on the newly installed system itself.

Evidence: `.test-tmp/l12-clean-windows-193.json` and `l12-clean-windows-193.png`; the
aggregate result and provenance are versioned in `L12_RECOVERY_ACCEPTANCE_2026-10-24.json`.
Sandbox itself was not run. No host Windows component, UAC elevation or reboot was
needed. Legacy project migration, full installed GUI acceptance and the final release
gate remain open L12 items.

## Selected legacy examples: 0.112.194 / Handler 0.6.0.141

The selected VFX Pipeline and Game 1.0.0 examples are definitions and configuration,
not a production-project database or repository export. Prepare them with
`python -m tools.prepare_legacy_examples --output ../releases/examples-0.112.194`.
The pinned VFX ZIP remains byte-identical. A separate Game stream.1 ZIP fixes six
`game_status_default` references to its defined `game/status_default` pipeline;
all other entries remain unchanged. Original archives are never rewritten.

Run `python -m tools.legacy_template_checks --windows-bundle <new-windows-kit>
--server-package <new-server-kit> --examples <prepared-examples> --output <new-report>`.
It initializes disposable installed Windows/SQLite and exported PostgreSQL/Apache
servers, imports both examples, checks hierarchy/asset instances, CRUD, task/note,
check-in and HTTP file bytes, then opens both projects through real browser and
native Handler login/navigation as administrator and artist. Qt runs offscreen
with software rendering; this does not certify GPU, physical input or pixel parity.
The artist has explicit trusted PythonCmd and sidebar grants required by the legacy
Handler contract. PythonCmd executes server-side code; it is not an untrusted role
or sandbox. Administration and direct security-record access remain denied.
Activity Feed waits for a selected project before its background requests; the
installed browser scenario rejects HTTP 400 responses, including startup polling.

VFX has 22 usable types and three explicit gaps: prod/session_contents and vfx/texture
depend on excluded pyasm.prod classes, while vfx/node_data has no DDL in the source.
Historical Maya/applet/Python-2 scripts and executable Mako pages are not certified.
Game has nine queryable types. Importing stored text does not certify executing it.
Check actual run outcomes in L12_TEMPLATE_ACCEPTANCE_2026-10-24.json. The earlier
clean-Windows and recovery evidence above applies to 0.112.193; clean Windows for
0.112.194 is not inferred from it. L12 remains open for final release acceptance.

## VFX support inventory correction: 0.112.195 / Handler 0.6.0.142

The subsequent [deep migration audit](LEGACY_MIGRATION_AUDIT_2026-10-24.md) reopens
general compatibility acceptance beyond these selected delivery scenarios. The 18
VFX view failures below are a known sample, including production dependencies and
unfinished originals; they are not the complete non-production migration backlog.

The 0.112.194 result above proves import, root asset rendering and the listed SDK operations only. It did not prove every VFX relationship, table cell, form or action. The previous phrase "22 usable types" meant 22 empty queries succeeded; it must not be read as full support.

The reproducible audit (`python -m tools.vfx_template_audit --output <new-report.json>`) inventories all 25 registered types and 151 saved/default views on an isolated SQLite project. Of these views, 78 are configuration definitions rather than table/form scenarios; 36 calculate cells, 19 load forms without saving, and 18 have known failures. Cell calculation and form loading do not certify GUI actions. All 22 native types can be inserted/read and their trees disclosed after the relationship fixes. `prod/session_contents` and `vfx/texture` still require the excluded production classes. `vfx/node_data` has no DDL. Maya and applet workflows are explicitly excluded by the user on 2026-10-24; a new clean-Windows test was also skipped by the user. Other gaps below are unfinished work, not additional agreed exclusions.

The focused VFX regression runs on both SQLite and real PostgreSQL 18.6. It checks actual Sequence → Shots and reference-image relations, native Handler relation counts, batched/reverse/self connection queries, row/type read policies, ID-only records, vertical Task Status, aggregate shot dates, native frame values and the five edit fields. Check-in History uses the scoped snapshot table, showing all versions and its normal filters (the old screen defaulted to latest). Native GUI action acceptance is a separate check.

Use `vfx-1.0.0-stream.1.zip` from `tools.prepare_legacy_examples`, keeping the original ZIP unchanged. Only `vfx/config_widget_config.spt` changes: obsolete frame display/input/action declarations become an expression and five ordinary fields; obsolete AssetDetail becomes the native object inspector. General relations read real `sthpw/connection` objects, a native extension of a path absent from the source Search implementation. No excluded `pyasm.prod` imports or aliases are restored.

Raw inventory: `VFX_SUPPORT_2026-10-24.json`. Loading metadata or calculating a cell does not certify its buttons or full GUI layout. The following 18 views still have known gaps:

| Type | View | Remaining failure |
| --- | --- | --- |
| `vfx/art_reference` | `edit` | TACTIC class is not migrated: tactic.ui.input.TextInputWdg |
| `vfx/asset` | `table` | submit: SubmissionLinkTableElement |
| `vfx/asset_in_shot` | `load` | type object 'SearchType' has no attribute 'break_up_key' |
| `vfx/camera` | `edit` | Unregistered SearchType: prod/shot |
| `vfx/episode` | `table` | submit: SubmissionLinkTableElement |
| `vfx/layer` | `edit` | TACTIC class is not migrated: tactic.ui.input.TextInputWdg |
| `vfx/layer` | `layer_list` | checkin_history: ; info: Nested widget is not a migrated table: pyasm.prod.web.LayerDetailWdg |
| `vfx/layer` | `table` | explore: pyasm.prod.web.ExploreTableElementWdg; info: Nested widget is not a migrated table: pyasm.prod.web.LayerDetailWdg |
| `vfx/plate` | `plate` | file_range: ; description: WikiElementWdg |
| `vfx/plate` | `plate_list` | file_range: ; description: WikiElementWdg |
| `vfx/plate` | `shot_sheet_wdg_plates` | description: WikiElementWdg; file_range:  |
| `vfx/plate` | `table` | description: WikiElementWdg; file_range: ; login:  |
| `vfx/review` | `review_tracking` | submission: tactic.ui.table.HiddenRowElementWdg |
| `vfx/schedule` | `schedule_bidding` | task_edit: HiddenRowToggleWdg; total_cost: Column [total_cost] does not exist in search_object type [vfx/schedule?project=vfx_audit_ok] |
| `vfx/sequence` | `planner_sequence` | asset_drop: tactic.ui.table.DropElementWdg |
| `vfx/sequence` | `table` | submit:  |
| `vfx/shot` | `planner_shot` | asset_drop: tactic.ui.table.DropElementWdg |
| `vfx/shot` | `shot_tracking` | shot_sheet_wdg:  |

L12 remains open. Resolve these ordinary VFX gaps and exercise their actual actions; repeat the saved-view audit and installed browser/native scenarios before declaring complete VFX support. Old production imports remain excluded; use native replacements where the requested workflow still applies.

### Verified delivery checkpoint

`L12_VFX_ACCEPTANCE_2026-10-24.json` records the independent
`windows-0.112.195-qualified` and `server-0.112.195-qualified` checks: all 16
database/client/role/template combinations passed on SQLite and PostgreSQL 18.6,
including real browser and native Handler login/navigation. VFX additionally opens
Sequence children (Shots and Reference Images) and the nested Shots table with
formatted frame values. CRUD, tasks, notes, check-in/HTTP bytes and ordinary-user
administration denial also passed. This is the named scenario coverage, not acceptance
of every saved view, editor or action. Qt uses offscreen/software rendering.

The full Frame gate passed all 156 stages with current source fingerprints; its
`native-table` stage passed the built-in serial retry after failing under parallel
load. The final checkout normalizes one Handler QML file to LF; the independently
tested Windows bundle contains identical content with CRLF. No functional source
difference was found in its Handler runtime.

The persistent demo was upgraded from 0.112.194 to this Windows kit. Its cold backup
contains 90 files and was restored/verified on a separate copy. Only the four listed
VFX widget configurations changed; all 24 physical project tables matched the
restored copy. Existing assets, SQ020 disclosure and its nested table passed the
browser check after restart. Neither this copy check nor the prior clean-Windows
0.112.193 run certifies a new clean-Windows 0.112.195 installation.
