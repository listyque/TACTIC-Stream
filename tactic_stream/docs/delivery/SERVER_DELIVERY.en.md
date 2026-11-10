# Standalone PostgreSQL / Apache server package

This package contains versioned Linux images for TACTIC Stream, Apache/Webmin,
and PostgreSQL 18.6, plus Compose, management scripts, licenses, and SHA-256 checksums.
The server runs installed Python packages and built Vue assets. It does not need
the source checkout, Node.js, a host Python environment with application dependencies,
or a bind mount of application code. The host needs Docker Compose and Python 3.10+.
Images target the architecture on which the package was built.

## Build from the source checkout

From `tactic_stream`, with Docker running:

```powershell
.venv/Scripts/python.exe -B -m tools.server_delivery --output ../releases/server-clean
```

The destination must not exist. Export includes all three images in `images.tar`;
no saved passwords, tickets, databases, repositories, or developer dependency volumes
are copied. `manifest.json` identifies the release and image IDs. Successful export
does not certify production acceptance.

## Install on a new host

Copy the complete exported directory to the target host. From that directory:

```sh
python manage.py load
python manage.py init
python manage.py check
```

`load` verifies all manifest checksums before loading images. `init` generates
separate PostgreSQL and Webmin secrets in `.local`, waits for PostgreSQL, prepares
a new PostgreSQL configuration, and asks twice for the TACTIC administrator password
through the existing CLI. There is no default administrator password. Existing
SQLite configuration/data is never converted by this operation. Existing PostgreSQL
configuration is retained; the native initializer refuses an already initialized DB.

The default Compose project is `tactic-stream-server`. To isolate another instance,
pass `--project-name NAME` consistently to every command and use a separate package
directory with its own `.local` secrets. Set `STREAM_HTTP_PORT` and
`STREAM_WEBMIN_PORT` before startup if the default ports are occupied.

- Application: `http://127.0.0.1:8082/`.
- Webmin: `https://127.0.0.1:10000/`; user `root`, password in `.local/webmin-password`.
- PostgreSQL and backend ports are internal to the Compose network.
- Data, repository, configuration, and logs use the `stream_data` volume;
  PostgreSQL, Apache configuration, and Webmin configuration have separate volumes.

Use `status`, `logs`, `up`, and `stop` through `manage.py`. `stop` retains volumes.
Keep `.local` with protected backups: it is required to access existing volumes.
Missing secrets are not silently regenerated when their data volume already exists.
On Linux, management keeps `.local` private (0700) and its mounted secret files
readable by the non-root application (0644). The private parent directory protects
host access; preserve it when copying secrets. Compose file-based secrets retain
host file permissions; see the [Docker secret contract](https://docs.docker.com/reference/compose-file/services/#secrets).
Webmin uses its own certificate; the `check` command verifies that certificate,
login/logout, Apache routes, current assets, workers, and PostgreSQL transactions.

From 0.112.424, API request logs omit session tickets. Treat worker logs and log
exports from older versions as credential-bearing data. If such logs were shared
outside their intended audience, revoke any exposed sessions that are still active.

## Update an existing package installation

Back up the database, repository, configuration, and `.local` secrets first. Keep
the previous package. Extract the new package into a separate directory, securely
copy the existing `.local` directory there, and retain the same Compose project
name and port settings. Then run `load`, `update`, and `check` from the new package.
`update` stops the backend, runs the native schema upgrade, and recreates services
from the loaded images using existing volumes. A failed migration leaves the backend
stopped. Restoring a database backup is required if a schema change cannot be reversed;
loading an older image alone is not a database rollback.

This preview supports a new PostgreSQL installation and native upgrades.
Legacy project migration still needs checking against the particular source project.
See the [recovery procedure](RECOVERY_ACCEPTANCE.md); release notes identify the checks
performed for each build. Changing a config value does not migrate SQLite data.
For external access configure TLS and trusted proxy settings for the target environment.

## Demo edition

Add `--demo` to the build command or download the Demo package from Releases.
Run the same `load`, `init`, `check` sequence. Initialization installs the separate
checksummed demo payload into a fresh database. It does not seed an existing project.
The default Compose project is `tactic-stream-demo`, HTTP port **8084**, Webmin **10002**.
Clean and demo use separate volumes and secrets; keep them in separate directories.
Explicit `STREAM_HTTP_PORT` / `STREAM_WEBMIN_PORT` values override these defaults.

Sign in as admin and open Orbit Studio or Atlas Reference Library. To retrieve
the newly generated demo account passwords locally:

```sh
docker compose -p tactic-stream-demo exec app cat /var/lib/tactic_stream/demo-accounts.json
```

Treat this output as credentials. The [demo walkthrough](https://github.com/listyque/TACTIC-Stream/wiki/Demo)
explains the records, roles, publications and plugins. Handler connects to the same
server address with a separate login. For a Synology package, see [DSM](https://github.com/listyque/TACTIC-Stream/wiki/DSM).
