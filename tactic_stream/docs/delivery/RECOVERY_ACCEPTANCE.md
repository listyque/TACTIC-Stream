# Backup, restore and upgrade verification

Use this procedure for the actual source and target releases. A previous successful
trial is not certification of another package, database, project or machine.
Record release hashes, database vendor, configuration and fixture scope in a new
local acceptance report. Historical L12 results are retained outside the repositories.

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


## Reproducible acceptance drivers

Run from the Stream source directory. Supply real previous/current package paths
and a fresh ignored output directory; do not substitute a same-release reinstall.

```powershell
python -B -m tools.delivery_recovery_checks --help
python -B -m tools.server_recovery_checks --help
python -B -m tools.local_data_recovery_check --help
python -B -m tools.prepare_clean_windows --help
python -B -m unittest tests.test_delivery_recovery tests.test_local_data_recovery
```

Drivers create owned fixtures; they are not production backup commands. Local-data
recovery requires a stopped source, refuses external roots/links, checks source
stability and opens only copied SQLite databases for validation. A cold copy must
include every database, repository, configuration, secret and client profile needed
for restoration. Test restored file bytes as well as database rows and permissions.

A clean-Windows claim requires the delivered package to pass in a fresh guest without
developer dependencies. Preparation of a test kit, developer-host success and
poisoned-PATH tests do not prove that result. Inspect the guest result and logs.

Scale, custom PostgreSQL roles/tablespaces, external storage, point-in-time recovery,
NTFS ACL/ownership and full interactive client acceptance require separate checks.
SQLite/PostgreSQL conversion and arbitrary legacy-project migration are separate
operations; never infer them from a successful native upgrade.
