# Project history and backup

Two independent repositories retain the projects' history:

| Project | Working tree | Branch | Authorized backup remote |
| --- | --- | --- | --- |
| TACTIC Stream | `D:/grav/Tactic Stream/TS` | `main` | `\\ListyNAS\home\codex_backups\tactic-stream.git` |
| TACTIC Handler | `D:/grav/Tactic Stream/TH` | `modern-main` | `\\ListyNAS\home\codex_backups\tactic-handler.git` |

Stream's root includes `tactic_stream/`, shared `docs/`, the `cg/` project
template, the launcher and legacy reference source. Legacy third-party Python
installations are excluded along with environments, runtime data and generated
verification output. Shipped Stream web assets and intentional legacy installer
seed databases/templates remain source resources and are versioned.

For each completed change, review `git status --short` and `git diff`, run the
relevant checks, then stage explicit paths and review `git diff --cached` before
committing. Keep corresponding source, tests, help and release metadata together.
Preserve unrelated changes from concurrent tasks. Cross-project changes require
a commit in each repository; record both ids in the delivery report.

From each working tree, back up completed commits and tags:

```powershell
git push backup --all
git push backup --tags
```

The initial commits preserve the existing working state; they do not certify
every accumulated feature. Handler's pre-existing history and `upstream` remote
are retained. Do not force-push or publish to that upstream by default.

To restore source, clone the corresponding NAS repository into a new directory.
The NAS repositories are bare Git backups, not application workspaces. Git does
not run a background backup: each completed task must commit and push; an offline
NAS leaves a local commit waiting for the next push.

Production databases, uploaded files, local settings and credentials stay on
disk outside Git and need their own backup. The `cg/` documentation-clone script
uses a credential-free Git URL; private repository access must come from the
operator's Git credential configuration.
