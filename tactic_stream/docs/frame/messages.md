# Tactic Frame: Communication

This contract describes source ownership, behavior and verification scope.
TH and TS ship independently; native-only actions remain native capabilities.
Use [the shared contract](contract.md) and [the feature index](index.md).

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

## Verification

Run the focused drivers under `tools/frame_messages/` from the Stream development
checkout, with the actual Handler checkout supplied using `--handler-root`
where supported. The complete shared gate is:

```powershell
python tools/frame_foundation/check_platform.py --handler-root "../../TH"
```

Adjust that path relative to the working directory; in the two-repository
workspace, Stream commands run from `TS/tactic_stream` and Handler is `../../TH`.
Use isolated data, actual input, fresh source fingerprints and independent-package
checks. Generated reports belong in the ignored tool `output/` directories.
Historical release counts and captures are local archive material, not current
acceptance. Offscreen checks do not establish physical touch/IME, compositor,
DCC or deployment readiness; exercise those when the feature requires them.
