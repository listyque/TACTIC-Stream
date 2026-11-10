# TACTIC on Windows

Download a Windows x64 package from [Stream Releases](https://github.com/listyque/TACTIC-Stream/releases)
or [Handler Releases](https://github.com/listyque/TACTIC-Handler/releases).
Python and the required libraries are included; no source checkout, system Python
or Node.js is needed. These are unsigned preview builds.

| Package | What it contains | Start here |
| --- | --- | --- |
| Handler Clean | Native Handler, Python and PySide6; connect to your server | Run the Setup EXE, then TH Setup.exe |
| Handler Demo | Handler plus a local Stream server and demo projects | Run the Setup EXE; initialize Stream, then open TH Setup.exe |
| Stream Clean / Demo | Stream EXE, Python, SQLite and browser UI | Extract the whole ZIP and run TACTIC Stream.exe |
| TH + TS Clean / Demo | Both applications in one portable folder | Extract the whole ZIP; run Stream, then TH Setup.exe |

Handler's demo includes a server because projects and publications belong to the
server. You can inspect the same demo in native Item View and the browser.
Clean packages have no demo payload or business projects. All packages retain
their runtime, resources and licenses together; copying out one EXE is insufficient.

## First launch

**Stream:** run `TACTIC Stream.exe`. A console asks twice for a new administrator
password. Sign in as `admin` with that password. The launcher initializes its owned
database, starts the server on loopback and opens the application. Closing its
window stops that local server. Handler needs it to remain running when connected locally.

**Handler:** run `TH Setup.exe`. Choose the server URL, sign in, select a project
and repository, and apply your settings. Then open `TACTIC Handler.exe`.
The wizard also configures supported DCC plugins and the shelf.
For a remote server, use its URL; no local Stream launch is necessary.
The bundled `TH Setup Builder.exe` creates installers with public deployment
presets. Passwords and session tickets are never included in those presets.

**Demo:** the first Stream launch creates Orbit Studio and Atlas Reference Library,
their pictures, publications, tasks, users, workflow and example plugins.
See the [demo walkthrough](https://github.com/listyque/TACTIC-Stream/wiki/Demo).
The initial server URL is `http://127.0.0.1:18881`. Generated user passwords are in
`%APPDATA%\TACTIC Stream Demo\server\demo-accounts.json`.
Initialization refuses existing business projects and preserves an already installed demo.

## Where data lives

- Stream Clean and the clean combined bundle: `%APPDATA%\TACTIC Stream`.
- Every local demo bundle: `%APPDATA%\TACTIC Stream Demo`.
- Within either folder: `server` holds databases, published files, configuration and logs;
  `browser` holds browser sessions; `handler` holds the bundled Handler profile.
- Standalone Handler Clean keeps its profile in its `TACTIC-Handler` application folder.
  Install it in a writable directory, not a protected system folder.

Clean and demo can run side by side. The three demo downloads use the same default
demo profile; they are different ways to open the same local server, not three servers.
For another isolated Stream instance, run `"TACTIC Stream.exe" --data-dir "D:\Tactic data"`.
Its actual port is recorded in `server/config/tactic-conf.xml`; a clean first launch
chooses a free port. Set `TACTIC_HANDLER_SETTINGS_DIR` when a separate Handler profile
is needed. `TACTIC_QML_TEST_SETTINGS_DIR` takes priority in isolated tests.

## Updating and restoring

Close both applications and back up the complete data/profile directory first.
Extract a new ZIP into a new folder and use the same Stream data directory.
The native schema upgrade runs before the server starts. The Handler EXE installer
preserves its local settings and repository, keeps a previous-installation folder,
and refuses to overwrite modified application files.

Keep the old application and its matching pre-upgrade backup. Replacing binaries
does not roll back a database schema. See the [recovery procedure](RECOVERY_ACCEPTANCE.md).
Release notes identify checks performed for that build; older acceptance results
do not certify a new bundle. The File Workspace remains a prototype.

## Building

From `tactic_stream`, with Python 3.14 on Windows x64:

```powershell
.venv/Scripts/python.exe -m tools.windows_delivery --handler ../../TH --edition suite --demo --output ../releases/TACTIC-Suite-Demo
```

Choose `handler`, `stream` or `suite`; omit `--demo` for a clean package.
The output must not exist. The builder checks pinned Python/Electron archives,
installs wheels into the isolated embedded runtime and compiles Handler's existing
.NET launchers. Handler editions also produce a self-contained Setup EXE.
`manifest.json`, `BUILD.json` and `SHA256SUMS` record versions and file integrity.
The embedded runtime ignores system/user Python packages. The Handler allowlist
excludes saved credentials, settings and private scripts.
