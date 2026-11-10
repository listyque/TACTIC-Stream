# Handler connection and Stream delivery contract

TACTIC Handler is an independent desktop product. Reuse its existing launcher,
XML-RPC client, connection presets and native object/file owners. Handler supplies
integration scenarios; it does not limit the complete original TACTIC API contract
that Stream must preserve.

## Bundle ownership

| Mode | Components | Handler connection | Server lifecycle owner |
| --- | --- | --- | --- |
| Local | Windows launcher, Vue/Electron, bundled Python/headless TACTIC, SQLite, native Handler and pinned dependencies | Local instance's XML-RPC | Launcher and TacticMonitor/workers |
| Server | Apache, headless TACTIC and PostgreSQL; Vue in browser/Electron | Server XML-RPC through Apache | Server environment; desktop clients do not manage remote processes |

Build Handler through its existing launch.py/launch.pyw or packaged application;
pin its version and dependencies when bundling. Both clients use the same server
projects, users, groups, ACL, objects, tasks, snapshots and repository. Initial
installation creates system definitions/databases; CreateProjectCmd owns project
database creation on the configured vendor. Changing a connection is not data
migration. Each product builds independently; do not add embedded WebEngine to
QML or a web Batch Manager as part of delivery.

Native Handler repository/file features remain owned by Handler. Do not port its
Repository Sync subsystem into Stream. Shared server check-in/check-out, upload,
download and repository paths still require compatibility checks.

## Existing connection mechanism

Handler presets in `thlib/environment.py` use `server`, `user`, `ticket`, `site`,
`proxy`, `timeout`, `config_format` and `team_local_repository`. Reuse them rather
than inventing a parallel format. Existing get_ticket exchanges the password for
a ticket; subsequent requests use that ticket. Verify site/proxy behavior for
an installation rather than assuming all options are supported.

Project selection is separate from the server preset: EnvInstance.current_project,
server_start(project=...) and server_auth(host, project, ...) retain their roles.
Do not add a project preset field that Handler does not read. Supply the configured
host/port without `/Api/`; the client adds `/tactic/default/Api/` and passes the
project in its existing ticket structure. A different instance needs its own valid
ticket. Keep local/server profiles separate and never publish credentials.

## Routes and repository files

| Route | Owner |
| --- | --- |
| `/tactic/{route_project}/Api/` | Original XML-RPC, including Handler's `/tactic/default/Api/` |
| `/tactic/{route_project}/UploadServer/` | Existing ticket-authenticated HTTP upload |
| `/`, `/projects/<code>/`, `/ui/` | Stream Vue workspace/resources |
| `/admin/rpc`, `/admin/session/...` | Stream API/session, not the Handler object API |
| Configured `checkin/web_base_dir`, usually `/assets/...` | Files under the corresponding asset_base_dir |

Apache forwards to the same backend workers. Vue fallback must not intercept
XML-RPC, upload or repository routes. Electron uses those same web routes.
Handler downloads published repository files over ordinary HTTP without an API
ticket, preserving original TACTIC asset-alias behavior. API operations and upload
require authorization. Local StaticFiles disallows symlink traversal outside the
root and supports HEAD/Range; external web_base_dir URLs belong to their external
file server. Repository aliases require an asset root and cannot overlap app routes.

## Reproducible integration checks

Use `/api/documentation` and `/api/compatibility` for the selected server's actual
surface. The captured API manifest and `tools/capture_legacy.py` inventory provide
signatures/call provenance, not proof of every option, side effect or GUI workflow.
Unchanged SDK/native scripts must be tested against real transports and temporary
data, including permissions, failures, revision conflicts and rollback.

From the Stream product directory, supplying the actual Handler checkout:

```powershell
.venv/Scripts/python.exe -B -X utf8 tools/handler_deployment_check.py --handler "../../TH"
# SQLite only, without Docker:
.venv/Scripts/python.exe -B -X utf8 tools/handler_deployment_check.py --handler "../../TH" --local-only
```

The full check needs the existing PostgreSQL/Apache Compose environment. It uses
the unchanged Handler SDK and native prepare_serverside_script,
get_projects_and_logins, query_search_types_extended and query_sobjects paths.
Its temporary databases/configs/processes are isolated from working data/profiles
and cleaned up by the harness. The report is `.test-tmp/handler-deployment.json`;
fixture addresses cease to be valid when their processes stop. This checks client
and backend behavior, not the complete Handler GUI or a clean Windows installation.

## Deployment references and acceptance

- Server bundle: [English](SERVER_DELIVERY.en.md) / [Russian](SERVER_DELIVERY.ru.md).
  The exported image-only package uses named volumes and its installed wheel;
  the source-mounted development environment is separate.
- Windows bundle: [English](WINDOWS_DELIVERY.en.md) / [Russian](WINDOWS_DELIVERY.ru.md).
  Keep user data, browser state and Handler settings outside program files.
- [Upgrade, backup and restoration evidence](RECOVERY_ACCEPTANCE.md) states the
  tested versions, environments and outstanding qualification limits.
- File projects: [English](FILE_PROJECT_DELIVERY.en.md) / [Russian](FILE_PROJECT_DELIVERY.ru.md).

Acceptance requires the existing Handler to perform the relevant workflows in
both delivered modes by changing connection settings only. Check ordinary users
as well as administrators. Independent package startup, GUI workflows, upgrade
from an actual prior release, migration and backup/restore each need their own
evidence. A successful backend fixture is only part of that criterion.

User-facing documentation records supported procedures and evidence limits.
Development queues, intermediate failures and superseded checkpoints belong to
local agent work outside the repositories and are not included in bundles.
