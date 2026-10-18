# Tactic Frame B11: communication

B11 covers Messages, its retained conversations and child panels, attachment
staging, the activity journal, notification history and toast content. Stream
and Handler ship independent copies of the portable modules. QML continues to
render native Qt controls; there is no browser, HTML view or runtime dependency
on the other checkout inside Handler.

## Sources and ownership

| Portable description | Production adapters | Responsibility |
| --- | --- | --- |
| `features/messages/messaging.state.mjs` | Both composers and message frames | IME/keyboard decisions, mentions, emoji clusters, bubble contour/geometry and popup kinds/sizes |
| `features/messages/conversation.ui.mjs` | ConversationList / MessagesConversationList and chat headers | List/header layout, profiles, presence, counters and actions |
| `features/messages/message.ui.mjs` | MessageHeader, MessageBody, MessageReference and pinned presenters | Metadata, body port order, references, pins and badges |
| `features/messages/composer.ui.mjs` | MessageComposer / MessageComposerField and send button | Field/send geometry, bounds, padding and compact presentation |
| `features/messages/forms.ui.mjs` | Both MessageForm adapters | Creation, membership, rename, search, edit and confirmations |
| `features/messages/panels.ui.mjs` | Members, revision/history, forwarding and gallery adapters | Panel headings, measured rows, selection and virtual forwarding lists |
| `features/messages/attachments.ui.mjs` | Both AttachmentComposerControls | Staging actions, draft list and compact/preview rows |
| `features/activity/feed.ui.mjs` | ActivityToolbar / ActivityFeedView | Responsive toolbar, day headings and user filter composition |
| `features/activity/event.ui.mjs` | Both ActivityEventCard adapters | Card, measured semantic sentence/change ports, expand and profiles |
| `features/activity/calendar.ui.mjs` | ActivityCalendar / ActivityCalendarPopup | Local dates, month navigation, 42 cells, counts and actions |
| `features/activity/notifications.ui.mjs` | SystemActivity / NotificationsView and history rows | Header, capability filters, list/empty state and selectable history ports |
| `features/activity/toast.ui.mjs` | NotificationToast / native stack content | Source/avatar/message/detail/progress, dismiss, reply and error geometry |
| `controls/forms/emoji.ui.mjs`, `people.ui.mjs` | EmojiPicker and UserPicker in both hosts | Neutral picker geometry, categories, rows, selection and accessibility |

`MessagesController`, attachment controllers, `ActivityFeedController` and
`NotificationController` remain Handler's owners. Stream retains MessagesView's
request generations, conversation cache/drafts/read positions, attachment owner,
ActivityFeed's paging/filter requests and notifications.js's timers/reply state.
Frame does not authorize requests, send files, persist drafts or create a second
message store. Existing server procedures, receipts, mutation checks and private
file authorization are retained.

Native feature adapters live under `qml/features/messages` and
`qml/features/activity`; public root components keep their existing entry points.
Vue adapters live in the corresponding `frontend/src/features` directories.
The two neutral pickers remain available to their existing callers, including
Notes, search and administration.

## Behavior and capability boundaries

- Opening and restoring a conversation creates its retained surface before history is shown. Late opening callbacks cannot reopen a closed owner or continue into another session.
- Switching a cached conversation retains the rendered surface, images, draft,
  reply, files and scroll state. An unloaded conversation still waits for its
  history. Refreshes use the existing generation checks and background reads.
- Desktop Enter sends, Ctrl/Meta+Enter inserts a line, phone Enter inserts a
  line. Mention selection takes Enter before send. IME composition, disabled
  fields, pending sends and repeated keys do not submit another message.
- Members, files, search and revision/pin history are anchored panels. Creation,
  membership editing and destructive confirmations keep their existing kinds.
  Escape belongs to the anchored popup even when its trigger is in another
  window. Closing it does not close the Messages owner.
- Native selectable/rich text, image/file cards and safe link handling stay in
  measured ports. Body measurements are deferred until the live item has its
  actual size. Natural widths, zero-size hidden surfaces and scrollbar room
  are handled explicitly. Activity rich text uses the same font advance policy
  as Frame controls instead of rounding every character's width to a pixel.
- Staging uses the existing attachment owner and token identities. The draft
  count opens compact rows or optional previews. Failure keeps the staged data;
  known uploaded snapshots are not blindly uploaded again. Handler retains its
  local file operations and cancellation. Browser files can require reselection
  after reload, and browser uploads are not advertised as cancellable.
- Handler alone exposes Repository Sync history. Stream retains browser
  downloads, its phone composition/safe area and scrollable long phone errors.
  Notification timers, active/history limits, source actions and quick-reply
  failure state remain with their original owners.
- Hidden/logout/expiry paths retain cancellation and stale-response guards.
  Stream additionally stops subsequent reads immediately on authentication
  failure while waiting for the parent to clear the ticket; relogin resumes it.
  Phone activity keeps a compact search row and expandable options; desktop
  and narrow desktop keep their shared toolbar.
  User/calendar filters initialize before accepting input. Asynchronous counts
  do not reset a calendar month already being viewed.

## Acceptance and reproduction

The pinned pre-migration Handler is
`a824d3ec3fa02653e9e9c9fe3da51c0cde11abc4`. The capture driver verifies the Git
archive comment and every extracted QML byte. Each pass fingerprints production,
portable, fixture and driver sources before/after; browser and report drivers
reject stale fingerprints. The original is never patched to make a pair pass.

Create the immutable original once in a fresh checkout (leave an existing
extraction intact):

```powershell
New-Item -ItemType Directory -Force .tmp/b11 | Out-Null
git -C D:/code/th_codex archive --format=zip --output=D:/code/TACTIC_VUE/tactic_stream/.tmp/b11/original-handler.zip a824d3ec3fa02653e9e9c9fe3da51c0cde11abc4
Expand-Archive -LiteralPath .tmp/b11/original-handler.zip -DestinationPath .tmp/b11/original
```

```powershell
.venv/Scripts/python.exe -X utf8 tools/sync_tactic_frame.py --handler-root D:/code/th_codex
.venv/Scripts/python.exe -X utf8 tools/format_tactic_frame.py --handler-root D:/code/th_codex --check
.venv/Scripts/python.exe -X utf8 tools/frame_messages/capture.py
node frontend/tests/frame_messages.mjs
.venv/Scripts/python.exe -X utf8 tools/frame_messages/report.py
.venv/Scripts/python.exe -X utf8 tools/frame_foundation/check_platform.py --handler-root D:/code/th_codex
```

`--smoke` captures dark EN and light RU. The full matrix captures three styles,
both modes/languages and wide/narrow production content. `QT_SCALE_FACTOR` and
`MESSAGES_FRAME_OUTPUT` select a separate scale/output run. Native fonts and
icons are loaded explicitly. Window chrome and native external shadows are
outside content comparisons. Original form content uses its own intrinsic
layout; current content is compared against the matching Vue description.
The gallery is `tools/frame_messages/output/index.html`.

`frame_messages_state.mjs`, `messages_ui.mjs`, `test_frame_messages` and the
existing communication/activity/notification/emoji/notes suites exercise state
and actual input. The private-server Collaboration scenarios cover messages,
activity, pagination, notification history and toast actions. Activity API and
mobile profile/feed scenarios are separate server checks. These are required
in addition to the paired gallery and independent-package platform gate.

The original column records visual changes and is not an assertion of blanket
pixel identity with the new Frame implementation. The current Qt/Vue comparison
checks common bounds, typography and paint on its recorded fixtures. It does
not establish arbitrary rich text, every possible file/DCC integration or all
platforms. Production PostgreSQL, physical touch, OS IME and Windows compositor
boundaries are not covered by offscreen/software Qt and Chromium automation.

The recorded visual matrix contains 288 current Qt/Vue pairs at 100% (all three
styles, both modes and languages), plus 48 pairs each at 150% and 200% (dark EN
and light RU, MD3). Every pair has the pinned original alongside it. The main
report and its `scale-1.5/` and `scale-2/` reports reject changed sources.
The matrix includes creation/membership/search/edit/confirmations, forwarding,
member lists, edit/pin history and chat files, besides the main communication
surfaces. Composer send/emoji controls are measured explicitly.

Recorded workflow acceptance for Stream 0.112.164 / Handler 0.6.0.115:

- All **111 mandatory platform stages** passed on unchanged source fingerprints,
  including complete desktop/mobile Workbench, control variants at 100/150/200%,
  retained windows/docks and independent packaging of all 153 portable modules.
- The **214 native communication tests** passed, including actual QTest input,
  measured message ports, forwarding references, selectable bodies, emoji,
  notes, activity paging and notifications.
- **Eight temporary-server checks** passed: Messages, activity, activity paging,
  notification history, notification stack, mobile activity/profile and two
  activity API cases. The separate notification geometry/input check passed.
- The shipped web build passed. Focused Python error/undefined-name checks and
  JavaScript syntax checks passed; this is not a claim of a repository-wide
  style-clean lint run.

The gate is recorded in `tools/frame_foundation/output/platform/gate.json`;
generated reports, captures, temporary databases and logs stay outside Git.
Source drivers, isolated fixtures and reproduction commands are versioned.
This completes B11 within the acceptance boundaries above; B07's remaining
legacy-widget workflows are not included or marked complete.
