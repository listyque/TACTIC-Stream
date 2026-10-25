---
group: Workflows
icon: comment
order: 20
---
# External agent

Open a project and page, select the relevant objects and choose **More options →
External agent**. This feature currently requires an administrator account and
an external agent connected for the same login and project.

The context box shows what will be sent: client, project, page, Search Type,
table view and selected object keys. Describe the result you want. For example:
“Create a shot review page with code, name and frames, filtered to frames above
100, with an object inspector on the right.”

Enable **Allow the requested configuration changes** to let the agent save the
requested configuration. Otherwise it can inspect and preview. **Send to agent**
creates one request; progress and the answer appear below. Open the resulting
page or project through normal navigation. Use Refresh/Reload Cache when needed.

Closing this modal does not cancel the task. Reopen it to see the same request,
or choose a recent request from the list. **New request** captures the current
page and selection. Each request is independent; include necessary details from
an earlier answer in a follow-up. A task keeps its captured project even if you
later navigate elsewhere.

**Cancel request** cancels queued work or stops the connected agent. Already
saved operations are preserved. If the connection is interrupted, inspect actual
changes before sending another task; interrupted requests are not automatically
repeated. No connection is shown as **External agent is offline**, and Send is
disabled. Ask the administrator to connect the external host.

The agent uses native TACTIC tools and the same server permissions and revision
checks as the existing editors. Generated executable scripts remain inactive
drafts. Review their source and test reports under **Script Editor → Agent
drafts**, then activate explicitly. Handler hooks and shelf scripts execute in
Handler; browser/API uploads do not execute local Handler hooks. The context
handoff does not give the agent live control of a Handler desktop.
