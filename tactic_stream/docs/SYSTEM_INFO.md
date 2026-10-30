# System Info

`tactic.ui.app.system_info_wdg` ports the information sections and diagnostic
actions of `legacy/src/tactic/ui/app/system_info_wdg.py`. Both clients use the
existing authenticated `execute_class_method` API and its Command transaction.
Every method separately requires a current administrator. `get_info` is read-only;
`connection_probe` returns worker identity/port, and `performance_probe` builds
the modern Users table definition and reads up to 20 rows without returning
account values. The legacy HTML ViewPanel renderer is not restored.

The allowlisted output covers `platform.uname`, CPU count, service login,
timezone-aware UTC clock, Stream/Python versions, request user agent/account,
mail server name and original Environment repository/handoff resolution.
Handoff resolution omits the ticket suffix. Directory access checks never create
files. No environment/config dumps, database DSNs or secret-bearing files are
returned. The existing API may record failures in its diagnostic log.

`run_test` validates a finite action/input schema, invokes original
EmailTriggerTestCmd or PythonCmd for email/saved-script tests. SMTP connect/read
timeout is 30 seconds. Script writes retain native authorization, transactions
and rollback. Navigation is retained in client memory and refreshed through its
normal owner; System Info does not clear an unused legacy filesystem cache.

`get_links` retains the original project-definition/internal-definition ordering,
separator removal and deduplication. `resolve_link` reads the configured target;
the normal browser navigation owner handles `system_link` addresses. Unsupported
page handlers fail explicitly; there is no substitute page or HTML execution.

The shared `features/support/diagnostics/system.ui.mjs` owns the structured
sections, inputs, buttons, formatted results, spacing and responsive bounds.
Client adapters run sequential/parallel probes off the native GUI thread or with
async browser requests. Parallelism is bounded at eight; request count follows
CPU count up to 256. Balancing samples 11 requests for one observed worker, up
to 50 otherwise, and distinguishes workers sharing one listener. These request
measurements include transport/server time. Window/session generations reject
stale results and stop further probes. No polling or automatic write retries.

Tests: `tests/test_system_info.py` exercises the real API over an owned temporary
store with SQL writes prohibited during repeated reads. It covers pre-probe
authorization, UTC timestamps and secret omission. `frontend/tests/system_info.mjs`
exercises every Vue test button and editable field, keyboard/mouse input, narrow
Russian layout, copy, errors, sign-out and stale completion. Backend tests use
mock SMTP, a real saved Python script/rollback, rejected obsolete cache actions
and configured page resolution on owned data. Browser client-folder checks are explicitly
unavailable without the obsolete applet; actual local paths are checked in TH.
Page-load tests open real Stream addresses in browser windows; popup blocking is
reported and individual page buttons allow retry. No live email or user script
is executed by the automated checks.
