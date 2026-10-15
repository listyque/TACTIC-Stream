---
reference: Handler
group: Reference
icon: bug-report
order: 22
---
# Debug Log

> Debug Log collects the enabled diagnostic event levels and keeps each application run as a
> searchable session.

## Main controls

Use level filters, the group tree, text search, event details, runtime-command copy, the session
selector, Open Session, Return to Live Session, Copy Session Path, and Clear Session.

## Usage notes

- Each run writes one compact versioned JSONL session.
- Compact disk keys are expanded to descriptive fields in the viewer.
- Messages, details, runtime commands, script bodies, payloads, and stacktraces are stored without
  length or nesting truncation so a recorded operation can be reproduced; credential fields remain
  redacted.
- Successful local API setup calls such as set_server are omitted, while their failures keep the
  runtime command and stacktrace.
- Only the current session schema is listed and accepted; replaced formats are not loaded.

## Filter an investigation

Level buttons combine with the selected group and text search. The group tree counts matching events
by module and slash-separated subsystem. Search matches message, group, module, function, runtime
command and stacktrace. Clearing one filter does not reset the others.

Select an event to inspect its timestamp, level, source module, function, line, duration, message,
detail, runtime command and stacktrace. The detail splitter and group-panel width are remembered.

## Live and saved sessions

**Live session** continues receiving events from the current process. Choosing a session from history
or **Open saved debug session** loads a read-only `.jsonl` file. **Return to live session** restores the
in-memory stream; it does not merge old events into the current run.

**Clear Session** clears the current visible live entries. While a saved file is open it returns to
the live session instead of modifying that historical file.

## Reproduce and report

1. Reproduce the operation once.
2. Filter by Error/Exception and the relevant group.
3. Select the event with the matching object, action or request ID.
4. Copy the complete event and, when useful, its runtime command.
5. Copy the session path so the original structured log can be attached.

For DCC work, match Handler's request ID with Handler Server and the DCC console. Native Maya output
is not rewritten as a TACTIC error, but routed DCC tracebacks are retained.

## Browser JavaScript

Browser modules have stable readable URLs such as `/ui/assets/ColumnsEditor.js`. Editors and other
deferred screens still load separately. JavaScript retains readable function names; its adjacent
`.js.map` lets DevTools resolve a stack location to the original Vue/JS source. Debug Log keeps the
browser's reported stack rather than rewriting its locations.

The server uses `Cache-Control: public, no-cache` and a content ETag for JS and its maps. A repeat
request returns 304 when content is unchanged and downloads the new content after a build. Fonts
and generated CSS retain their existing caching. Restart the server after updating this handler;
changing the build alone does not update an already running Python worker's cache headers.

## Privacy and retention

Passwords, tickets, tokens, cookies and known credential fields are redacted before display and disk
serialization. Do not paste secrets into ordinary untyped message fields. Session retention is
bounded, but a single diagnostic event is not silently truncated.

## Native server diagnostics

After sign-in, the browser automatically sends API, JavaScript and `console.error` failures
through native `log` into `sthpw/debug_log` (SQLite: `data/db/sthpw.db`). The active session
determines the author. Entries include time, page path, viewport, group, stack and details;
tickets and known secrets are redacted. This works even with local Debug Log recording disabled.
Look for browser errors in `debug_log` and server exceptions in `exception_log`. Reading technical
journals through generic `query` remains guarded; investigations use administrator database access.

Each server-side message, stack and details field is limited to 8192 characters; the local
session keeps the full event. With an unavailable server, the attempt stops after 3 seconds
with no retry queue. Update-polling and logger failures are not reported again. Signing out
stops authenticated server logging.

XML-RPC 403 responses distinguish an expired or invalid session, incorrect login/password,
an unavailable project and denied permission. Handler offers sign-in again for a rejected
session; denied access requires checking permissions, rather than replacing the ticket.
After updating this transport, restart the server workers to apply the new messages.

Since 0.112.10, authenticated users can persist DebugLog/ExceptionLog entries in the TACTIC database. These are separate from JSONL sessions. The **Core model** Help topic describes author checks, independent commits and the active system-writer limitation. XML-RPC `log` is described in the API reference.

## Server RPC request log

JSON calls to `/admin/rpc` and XML-RPC calls to `/tactic/{project}/Api/` use the same `tactic_stream.server.api` logger at **INFO** level and the original TACTIC block format. Each call reaching the API dispatcher writes one block, including failed calls:

- `request_id`, `timestamp`, `user`, `simple method` and the legacy `ticket` header;
- arguments in method-signature order, including arguments received through JSON `kwargs`;
- `error` with the exception class when the call fails;
- `Duration`, `Memory`, `Increment` and `Total Duration`.

`Duration` measures the method after API initialization and authentication. `Total Duration` measures the whole API dispatch; HTTP body decoding and response serialization are outside this timer. Passwords and known secret fields in arguments are redacted. The `ticket` header retains the legacy representation; this server log is separate from the client JSONL log that redacts tickets. Argument display remains bounded by the existing logger.

Other browser endpoints, such as `/admin/search-configuration/query`, do not pass through `/admin/rpc`. Their HTTP access records are separate. Requests rejected before API dispatch also do not have a method block.

This logging does not switch Handler's transport. Handler continues using XML-RPC, including connections to Legacy TACTIC.
