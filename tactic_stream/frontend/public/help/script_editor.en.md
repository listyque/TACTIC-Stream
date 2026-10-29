---
reference: Handler
group: Workflows
icon: code
order: 19
---
# Script Editor

> Script Editor stores and runs scripts with syntax highlighting, line numbers, search and replace,
> occurrence highlighting, completion, scrollbars, output, and server-backed script folders.

Administrators and supervisors can edit, save, delete, and run code in the editor. Other users can
open and copy scripts, but the editor is read-only and cannot save or execute edited source.

## TACTIC Stream server permission

Since 0.112.13 ordinary API/Workflow callers can execute trusted server Python with
an explicit project-scoped `api_cmd` grant for `tactic.command.PythonCmd`.
Editing stored scripts and Script Editor UI permissions are unchanged.
Since 0.112.14 a cross-project Workflow callback uses its object's actual
project for saved script lookup and the grant, then restores the caller project.
The grant is not a sandbox; see [Core model](core_model.en.md) for XML rules,
checks, transaction rollback and remaining restrictions.

## Main controls

The source editor supports Python keywords and built-ins, names declared in the current script, and
TACTIC Handler gf and tc APIs. Open scripts use the shared workspace tabs.

The scripts tree can be hidden with the directional arrow; Local Python and Server Python use the
same Python glyph with distinct colors. Unsaved source from new and server-backed tabs is restored
locally for the current project.
The tree search stays at the top even when the current project has no scripts.

Local Python runs on Qt's GUI thread, so trusted scripts can import or reload native PySide6 UI
modules and show their windows directly.

## Usage notes

- The Source toolbar provides 120-step undo and redo history, a history list, cut, copy, paste, text
  sizes, search, selection execution, and help.
- Output is read-only but supports a text cursor, selection, copy, collapse, horizontal scrolling,
  and automatic word wrap.
- Right-click a server script in the tree to copy its runner or delete it from TACTIC.
- Run only trusted scripts.
- Copy Script Runner creates the original execute_custom_script call for a server-backed custom
  script.
- An explicit local Python file path can use the same API without refreshing or publishing the
  script in TACTIC.

## Shortcuts

| Key | Action |
| --- | --- |
| Ctrl+S | Save the current script |
| F5 | Run the whole script |
| Ctrl+Enter | Run the selection, or the whole script when nothing is selected |
| Ctrl+Z / Ctrl+Y | Undo or redo an edit |
| Ctrl+X / Ctrl+C / Ctrl+V | Cut, copy, or paste |
| Ctrl+F | Open search |
| Ctrl+H | Open search and replace |
| F3 / Shift+F3 | Go to the next or previous match |
| Ctrl+Space | Show code completions |
| Ctrl+/ | Toggle comments for selected lines |
| Tab / Shift+Tab | Indent or unindent selected lines |
| Ctrl+D | Duplicate the selection or current line |
| Esc | Close completions or search |

## Script identity and server storage

Folder and Title are separate fields. Together they form the project script path shown by the tree.
Save writes the current server-backed script through TACTIC; Refresh downloads the published tree and
reconciles open tabs without discarding an unsaved local draft. A dirty marker identifies source that
differs from its last saved version.

The history button lists saved revisions for the active script. Closing one dirty tab or all tabs
asks whether to save, discard or return to editing.

## Execution targets

| Target | Behavior |
| --- | --- |
| **Standalone** | Runs supported Python in Handler for Handler UI and public API work. |
| **Selected DCC** | Sends a validated action to the exact selected client and runs on its native thread. |
| **Server** | Executes supported server-side Python through TACTIC and returns output or traceback. |

The target includes application, scene and PID when available. A missing `execute_custom_script`
capability disables DCC execution instead of routing to another client.

Local Python is a trusted developer mode and intentionally runs on Handler's Qt UI thread. Do not
perform blocking TACTIC, repository or large filesystem work there. DCC Python follows the DCC's
native thread rules; submit Handler data work rather than waiting on that UI thread.

## Output and debugging

Each tab owns its output. Standard output, standard error, completion detail and tracebacks appear in
the Output splitter for the producing script. Trigger output is appended to its script tab when
possible. Collapse, resize, wrap, select, copy or clear Output without changing source.

The completion notification is only a summary. Use Output for prints and the real traceback, and
Debug Log for request IDs, runtime commands and remote details.

## Server JavaScript

Since 0.112.39 the editor also supports `server_js` and shelves execute it through native JsCmd. Select **Server JavaScript** in Script Editor. This is synchronous administrator code, using `server` and kwargs globals; browser `javascript` retains its separate context. See [Native HTML and server JavaScript API](html_api.en.md) for examples, transactions and limits.

## TACTIC Stream execution and editing

Browser JavaScript receives `context`, `project`, `searchType`, `searchKeys`, `rpc(method, args, kwargs)` and `refresh()`. RPC calls use your account and the captured project. Run only trusted code: browser JavaScript can access this page and your session. Server Python uses the TACTIC server API; its print output remains in the server log. Server JavaScript uses QuickJS-NG with `server` and kwargs globals, without browser or DCC access.

Saved revisions restore into a local draft before Save publishes them. Refresh preserves unsaved drafts. Ctrl+Shift+O opens the outline; Alt+Up/Down navigates symbols; F12 goes to a definition; Ctrl+Shift+K deletes a line. Undo/redo retains 120 steps. Tab or Space accepts a completion; Enter inserts a new line.

Local Python, DCC execution and Handler/DCC action hooks are excluded in this web editor. Imported scripts in other languages remain readable. Editor and source-toolbar Help both open this article in the shared catalog.

## Shared presentation and native script tools

Script Editor uses the shared Frame workspace and source command layout. Python,
QML, server and selected-DCC execution still use their existing execution owners;
the browser offers only its supported server/browser runtimes. Saved scripts do
not need conversion. Source edits, undo, revisions and drafts remain with the
editor. Cancel in a confirmation cancels a pending run; it does not forcibly
interrupt Python that is already running.

In Handler, a small native example is available for local Python scripts:

```python
from side_tools.frame_tool.showcase import show
show([{"id": "asset-a", "title": "Robot Arm"}])
```

Run this on the GUI thread, like other scripts that create QML windows. It opens
a nonmodal native window using existing fields, buttons, a virtualized record
list and the current theme. Preview shows the exact selection; it submits no
render jobs. Close releases the window and its model. The three example files
separate portable composition, native event adaptation and Python lifetime.
Batch Manager keeps its existing scheduler and web UI; this is an example of
reusing controls, not another Batch Manager.

## Native Handler automation

External agents can prepare inactive Local Python drafts for Handler check-in hooks and shared shelf buttons. Saving, syntax validation and activation are separate operations; activation requires explicit host authorization and native server execution permission. Drafts/receipts survive restart. An isolated arbitrary-code trial runner is unavailable.

These bindings execute in TACTIC Handler. The browser does not launch local programs, execute Local Python or open native QML tools. Refresh the saved configuration in Handler after publication. Handler's trigger editor uses one revision-checked command to save its complete hook set. Input paths and operation identity are captured before check-in; After hooks receive the completed snapshot. These client hooks do not enforce uploads from headless APIs or other clients.

## Agent drafts and isolated reports

Open **Agent drafts** in Script Editor to inspect your saved agent drafts, exact
source and binding, and reports published by the external test host. The review
panel runs no code. Stale reports stay readable but cannot authorize activation.
Ask the connected agent for fresh trials, then refresh. Before check-in requires
passing allow and reject cases; After requires allow; a shelf requires a modal
case. Review the source and execution owner, check the review box, and confirm
activation. Scripts targeting Handler run on its desktop after activation; the
Stream browser does not execute Local Python/QML. Return to the editor without
losing its open buffers. Reports belong to their author and project.

The editor toolbar starts 8 px below the window title bar, using the workspace inset without an additional title-bar gap.
