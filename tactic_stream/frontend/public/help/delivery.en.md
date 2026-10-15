---
group: Guide
icon: cloud
order: 92
---
# Installation, updates and acceptance

> TACTIC Stream runs from the checkout or an installed Python wheel. This guide describes the implemented delivery, not the future Windows EXE/Electron bundle.

## What is supported

Python 3.14+ is required. SQLite and PostgreSQL are implemented; the acceptance uses SQLite on Windows and PostgreSQL 18.6 in Linux Docker. MySQL is still a target, not a supported runtime. PostgreSQL requires the package's `postgres` extra and a native XML database resource; credentials can use `password_file`. Changing vendors does not migrate existing data.

The server imports packaged `pyasm` and `tactic`; it needs neither the reference `legacy` directory nor a running Handler. The unmodified Handler XML-RPC client remains an acceptance client. Repository Sync, S3 and the desktop/DCC bridge are excluded.

## Starting on Windows

After installing the documented dependencies into `tactic_stream/.venv`, launch `START_TACTIC_STREAM.bat`. The BAT calls `init --if-needed`, `upgrade`, then `serve --open-browser`. Initial creation asks for a new administrator password; an existing configured system database is left intact. Explicit `init` still refuses existing databases. This applies to PostgreSQL as well as SQLite; the launcher does not infer the vendor from a SQLite filename.

`TACTIC_DATA_DIR` selects the data directory, defaulting to `data`. `TACTIC_CONFIG_PATH` selects an explicit XML configuration; otherwise the owned data directory supplies it. Existing service/port environment overrides apply. The browser opens the application root only after the workers are ready. The selected project and workspace come from the saved user/browser state; the launcher does not force a Projects tab. `/admin/` is not a UI route. Native transport URLs under `/admin/...` remain API endpoints.

## Update and restart

Back up the owned data directory, repositories and all registered databases before updating; PostgreSQL backups require the database server's tools. Stop the instance using Ctrl+C in its launcher or `tactic-stream --data-dir <directory> stop` with the same configuration. `status` reads the native monitor state. Wait for the monitor and workers to stop before replacing the package and frontend resources. Run `upgrade`, then `serve`; the BAT performs these steps automatically after its conditional initialization.

Schema upgrade operates on the system database and registered owned project resources. It is idempotent and does not reset objects, versions or preferences. An external project resource is rejected instead of silently migrated. Tickets, selected project, tabs, named layouts and browser state have their existing persistence owners; reinstalling code is not a command to delete them. Browser-local state belongs to its origin/profile, so another address or a private browser session does not inherit it.

## Frontend and installed package

Run `npm ci` and `npm run build` in `frontend` before building the wheel. Vite recreates its generated output from current chunks and `frontend/public`, including Help and license notices. Old build chunks are not accumulated. Use a clean Python build directory when rebuilding a wheel; setuptools may otherwise retain files from a prior package.

JavaScript is split into readable feature files. The wheel includes each current JS source map for browser debugging. JS uses ETag and revalidation; hashed CSS/fonts may be cached indefinitely. Reload open browser tabs after deployment. Stable JS names do not support a seamless rolling update across mixed server versions.

## CG acceptance and its boundaries

The supplied `cg.zip` contains a template named `niki_friends` in its manifest, independent of the archive filename. The browser can upload it in Manage templates and choose it in the normal project wizard. Acceptance uses private projects, not the user's working `cg_test`.

The sample seeds 32 objects, 13 explicit tasks, 47 notes and 45 checked relationships: nested/shared assets, episodes and shots, asset categories and shared textures. Native workflow can generate additional tasks. Reseeding preserves the existing sample and checks idempotence. Only imported Telegram callbacks are disabled in test projects, preserving their scripts; the other native triggers remain active. Snapshot checks preserve old version contents and update the latest versionless representation; the current Handler procedure is tested unchanged.

Windows file checks use copy mode where the process cannot create symbolic links. Linux checks exercise the template's link behavior. This is not proof of symlink privilege on every Windows installation. Native APIs are not all complete: 127 entry points are available with documented variant limits; the full old HTML shell and two production-layer contracts are excluded, and MySQL is deferred; see [Core and API compatibility](help://api_compatibility).

All private acceptance servers, workers, browsers and containers must close in cleanup. A working user server is never a test fixture. Regression counts and delivery evidence are recorded in the repository plan and release reports; this guide does not claim every production data shape or physical phone was tested.
