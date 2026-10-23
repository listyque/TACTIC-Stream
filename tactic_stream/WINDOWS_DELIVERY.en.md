# Portable Windows desktop

The x64 package contains `TACTIC Stream.exe` (Electron), Python 3.14.9,
SQLite, Stream and the native Handler with its pinned PySide6 dependency.
No system Python, Node.js or checkout is required. Extract the entire ZIP
to a writable local directory; keep its runtime, resources and licenses together.
The EXE is not signed. Clean Windows VM acceptance remains pending.

Run `TACTIC Stream.exe`. On first launch the native installer opens a console
and asks for a new administrator password. No default password is shipped.
The launcher then upgrades the native schema, starts its local monitor/workers
on loopback and opens the existing Vue UI. Closing the window stops its backend.
An occupied port or a failed initializer is an error; existing data is not reset.
Native confirmation dialogs use the Windows language (English fallback/Russian);
the application language remains selectable in Appearance.

By default all user data lives outside the program folder:

- `%APPDATA%\TACTIC Stream\server`: databases, repository, XML configuration and logs.
- `%APPDATA%\TACTIC Stream\browser`: browser sessions and interface preferences.
- `%APPDATA%\TACTIC Stream\handler`: native Handler settings, presets and caches.

For an isolated installation run `"TACTIC Stream.exe" --data-dir "D:\Tactic data"`.
The selected local port persists in `server/config/tactic-conf.xml`.
Read it there or in the window URL when configuring Handler.
Run `Handler.cmd` to open the bundled native application, then use its existing
server preset/login and project selection. It does not share browser sessions.
`TACTIC_HANDLER_SETTINGS_DIR` overrides the Handler profile directory;
`TACTIC_QML_TEST_SETTINGS_DIR` takes priority for isolated tests.
Handler can connect to a remote server without starting the local Stream EXE.
The local EXE only manages its own local backend.

Before updating, close both applications and back up the complete data directory.
Extract the new bundle into a new folder and launch it with the same data directory.
Do not copy databases or settings into the program folder. Native upgrade runs
before serving; binary replacement is not a database rollback. Keep the old
bundle and a matching pre-upgrade data backup for restoration.
Upgrade 0.112.192 to 0.112.193, before/after backups, independent restoration and
rollback passed on isolated fixtures. An offline copy of the existing local dataset
also passed content/integrity checks. See [recovery procedure and acceptance](RECOVERY_ACCEPTANCE.md).
Clean Windows and legacy project migration remain L12 work. The previous Windows
EXE did not exist; previous-version SQLite acceptance starts from the delivered wheel.

Build from the development checkout with Python 3.14 on Windows x64:

```powershell
.venv\Scripts\python.exe -m tools.windows_delivery --handler "D:/grav/Tactic Stream/TH" --output "../releases/windows-0.112.193"
```

The output must not exist. Official Python/Electron archives are checked against
pinned SHA-256 digests; dependencies are installed from wheels into the embedded
runtime. `manifest.json` records exact versions and per-file hashes.
The embedded `_pth` disables system/user package discovery. The Handler archive
uses the existing source allowlist and excludes saved credentials and settings.
