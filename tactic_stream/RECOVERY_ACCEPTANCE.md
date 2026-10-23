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

At this checkpoint Sandbox is not installed, the process is not an administrator,
Hyper-V enumeration was denied by Windows, and the available VMware VM is Ubuntu.
The connected Desktop Commander device is offline. Enabling Sandbox/UAC and any
reboot, or access to a clean Windows VM/PC, require the user's response. The prepared
kit does not enable Windows components or reboot the working machine.
