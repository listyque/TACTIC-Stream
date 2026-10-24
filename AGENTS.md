# Git workflow for TACTIC Stream

- The repository root is `D:/grav/Tactic Stream/TS`. Track Stream source, tests,
  shipped web resources, build configuration, project templates in `cg/`,
  shared documentation and the legacy source used by compatibility checks.
- Keep TACTIC Handler in its existing independent repository at
  `D:/grav/Tactic Stream/TH`; preserve its history and configured upstream.
- For each completed task, review the diff, run relevant checks and commit the
  files changed for that task. Include corresponding tests, documentation and
  required release metadata. For a cross-project change, commit both repositories
  and mention the counterpart commit in the final report.
- Preserve unrelated or unfinished changes from other tasks. Stage explicit
  paths or hunks; do not automatically commit, reset, stash or discard them.
- Never commit runtime databases, repository files, tickets, credentials, local
  settings, virtual environments, caches, logs or temporary test output. Review
  new files and the staged diff before committing; ignored files stay on disk.
- Keep bundled resources and intentional test fixtures versioned. Git does not
  replace backups of databases, uploaded files or local configuration.
- Do not rewrite existing history or force-push. Push only to an explicitly
  authorized destination; local commits are required even without a remote.
- The user authorized Git backups under `\\ListyNAS\home\codex_backups`.
  When a `backup` remote is configured, push completed commits and tags there
  without force. If NAS is unavailable, retain local commits and report that
  the backup is pending. Never push to Handler's public upstream by default.
- Read the nearest `AGENTS.md` before changing files in a subdirectory.

## Agent documentation

- Write agent instructions and maintained engineering contracts in English.
  Preserve the products' English/Russian Help and translation dictionaries.
- Keep Stream server APIs, core structures and web Help distinct from Handler
  client APIs, native objects and desktop Help. Shared Frame descriptions do not
  make execution environments or transport contracts interchangeable.
- Keep development backlog, handoffs, intermediate acceptance logs and work
  journals outside both repositories in the workspace's `agent-work/` directory.
  Use its `CURRENT.md` for ongoing work. Do not embed that process history in
  README files or ship it in product bundles. Retain durable contracts and
  reproducible verification procedures in product documentation.
