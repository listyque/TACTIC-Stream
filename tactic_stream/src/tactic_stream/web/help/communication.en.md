---
group: Workflows
icon: comment
order: 17
---
# Notes and messages

> Notes belong to an sObject or process; Messages provide personal and group conversations.

The badge above the account avatar shows unread messages. Header activity and queue buttons use the same counter placement outside their circular surface. Zero counts are hidden; counts above 99 appear as 99+.

## Conversations and drafts

Choose a chat on the left, or use **New conversation**. One recipient creates a direct chat, several recipients create a named group, and no recipients opens Favorites. Group creation requires the server's supervisor permission.

Each conversation keeps its own unsent text, reply and staged attachments across closing and reloading. Drafts belong to your account. Browser permissions mean a local file may need to be selected again after reload; it is never silently dropped from a send.

Returning to a recently opened chat retains its rendered messages, images and reading
position. Changed history refreshes in the background. The first visit to an unloaded
chat waits for its server history; the twelve most recently used timelines remain cached.
Search results are separate, so clearing search restores the full conversation.

## Text and attachments

Press **Enter** to send and **Ctrl+Enter** for a new line. Use the emoji picker or type **@** to mention a member. Attach a file, paste an image or drop files into the window. Sending attachments without text is supported.

**Chat files** groups attachments from loaded messages by category and supports search. Load earlier messages to see older files. Selecting an attachment jumps to its message; the menu provides preview, download, copy and location actions. Reading a private file requires access to its conversation.

## Message actions

Open the message menu for replies, forwarding, selection, copying, pins and edit history. Add a reaction with the emoji control. Several selected messages can be forwarded together. On touch, use the explicit controls or hold the message/chat to open the same menu.

Authors may change their own message for one hour; administrators and authorized supervisors may change other messages. The server verifies each operation. Edit history, original forwarding metadata and unavailable/deleted replies remain readable without fabricating the missing source.

The chat header provides search, participants and conversation actions. Rename, preview, membership and pin history use the same existing operations. Clearing Favorites or deleting a chat asks for confirmation.

Members, chat files and conversation search open beside their controls without blocking
Messages. Press Enter or Search to apply a phrase; Clear search restores the conversation.
Escape or clicking outside dismisses these panels. Creation, membership editing, rename
and edit history use centered nonmodal panels; Save/Create applies their changes.
Emoji use a larger grid on desktop and touch screens.

## Links and delivery

TACTIC **sKey** links show object/file previews. Opening a preview preserves the chat draft. Missing or inaccessible objects remain unavailable without interrupting the conversation. Click a sender's name or avatar to open their profile; its Message action returns to the direct chat.

Delivery metadata distinguishes sent, delivered and read counts. Hover or focus controls for a tooltip; the timestamp exposes its full date/time. Message notifications control pop-ups only: unread counters and history keep refreshing.

Browser sound and clipboard access depend on browser permissions. File previews and downloads use the browser rather than launching a desktop application. Messages and Help use the shared draggable/maximizable window controls.

## Main controls

Both composers support text, attachments, clipboard images, emoji, replies, send state, and drag-
and-drop file attachments. Drop local files over an active Notes or Messages view to add them to the
same attachment staging list used by the attachment button.

Messages also support mentions, reactions, forwarding, pins, search, members, delivery state, and
conversation files. Text and staged attachments are separate for every note target and every
conversation.
Each message send uses a stable, unique attachment context and file names. A failed send keeps its
staged files for retry; an unavailable snapshot or failed attachment link is reported as an error.
An incomplete upload cannot send the text alone; the staged files remain available for retry.
Image attachments expand the chat bubble to the available media width. A web preview keeps its
aspect ratio, stays at its natural width when smaller, and appears above the message text.

Every user has an empty Favorites chat by default. It appears when Messages first loads, even
before the user sends anything there. Favorites belongs to the login across projects; an empty
history does not show an old message preview. Existing messages remain visible even when an older
TACTIC message log did not originally have a code.

For one task, Notes remain on the process branch. When the same process has additional tasks, the
primary task keeps that branch and every additional task receives its own note and attachment
timeline.

New messages and Activity Feed events use the application's own notification stack anchored to the
bottom-right work area of the active screen. Message cards show the conversation, sender avatar and
name, and a readable content preview.

Activity cards reuse the feed's author identity, event category, and semantic action text instead of
transport fields. Windows system notification balloons are not used.

Message notifications and Activity feed notifications have independent switches in Global Settings.
Disabling a switch hides only its pop-ups; history and unread counters continue updating.
After sign-in, Messages fetches current unread conversation summaries from the server, including
messages received while the app was closed. It updates its badge and shows the latest unread
notification from each conversation without opening the window.
Delivery and read receipts keep updating while Messages is hidden. Message groups use compact
metadata spacing and stable delegates so scrolling does not leave stale bubble fragments.
While a conversation is visible in the active Messages window, that conversation alone refreshes
every five seconds so replies, reactions, and receipts arrive quickly. The fast refresh stops when
the window is hidden or inactive. Browser permissions control notification sounds.
The pop-up shows a circular sender avatar and stays visible for 15 seconds. Select Reply to type
and send without opening the chat; it stays open while you compose or while sending, and shows
any send error without discarding your text.
Background refresh keeps previously loaded older messages in place. Grabbing the scrollbar
stops the wheel animation, so it does not compete with dragging.
The scrollbar uses the measured height of loaded messages and does not change size
as you scroll past different-height cards. At the end, layout changes keep the last
message above the composer; loading older messages preserves your reading position.
The people icon in the chat header opens its members; its badge shows the member count.
The header shows a progress indicator only while a chat operation is running; otherwise its actions use that space. The timeline aligns with the header instead of adding a second side margin.
Right-click a chat in the list to select it and open its actions menu. It uses
the same permissions as the header menu, including clearing Favorites, your private chat.
A new message is revealed once, without highlighting it. Switching chats or
reactivating the window preserves each chat's position unless another new message
has arrived. Delayed read receipts do not repeat the scroll.
Server updates also preserve the position of inactive chats; returning to one
refreshes its messages in place without recreating the conversation view.
Switching chats keeps reaction rows at their existing height, so messages with
reactions do not shrink and expand or change the scrollbar when you return.
Signing out clears loaded chats and cancels their pending updates; signing in as another user
loads only that user's conversations. Per-user unsent drafts remain available on the next sign-in.

A raw server update never becomes an Activity Feed notification by itself. The app resolves the
matching journal event first, so the notification shows the same author, avatar, object and readable
change details as the feed card.

The shared emoji picker provides the complete Unicode 17 catalog with consistent Noto Color Emoji
artwork, category navigation, and name search. On a new server, an administrator confirms one schema
initialization for Messages and Knowledge Base.

The confirmation lists every Search Type and column that will be added and does not delete existing
data.

## Usage notes

- Press Enter to send and Ctrl+Enter for a new line.
- New entries stay anchored at the bottom like a messenger.
- Consecutive Messages from one author form a compact visual group: the name appears only on its
  first bubble, while one external avatar and bubble tail mark the final bubble.
  Bubbles share one corner radius; the tail and selection outline form one continuous contour.
  A modest gap separates sender details from the text, with consistent padding along the bubble edges.
- Notes keep their compact status-oriented layout unchanged.
- The author can edit or delete their own note or message for one hour after publication.
  Administrators and supervisors can edit or delete other people's notes and messages at any time.
  Unavailable actions are omitted from the item menu.
- A link to a deleted TACTIC item remains unavailable without interrupting work with an error popup.
- Direct conversations show the other user's shared live presence and last-seen time in the header;
  group conversations keep participant counts instead.
- The conversation timeline keeps a usable minimum width when its divider is dragged.
- Unsent text and attachment metadata are restored after closing or reloading; local files may need to be selected again.
- Click an application's custom notification card to open its conversation or Activity Feed event.

## Global communication and Inspector (0.112.34)

Messages and presence work before choosing a project. Favorites appear first and the first visible
conversation is selected. Profile reads also work in this global context; project-bound sKey
previews still require selecting their target project and passing its access checks.

Object notes open in Task Inspector by default. Its process/task selectors, quick fields, related
tasks, hours and timeline share one exact target. Configuration → Appearance → Object notes retains
the separate Notes view as a visible Stream option. See Help: Task Inspector for canonical note
ownership, draft isolation, refresh, conflicts and attachment-only notes.

The browser shares its composer, clipboard helper, attachment cards and window controls across
notes and messages. Clipboard image reading needs browser permission and a secure context; on
LAN HTTP use paste or the file chooser when the explicit clipboard button is unavailable. Browser
local files cannot be restored automatically after a full reload. No Handler or DCC bridge is used.


## Phone presentation

At 700px and below, task rows adapt to a vertical list; task fields are collapsed by default in Inspector. Enter adds a newline and the explicit button sends notes/messages. Phone panel selection is separate from the desktop layout. See **Mobile application** in Help for touch actions, keyboard viewport, persistence and verified limits.

## Conversation panels and attachments

Members, chat files, message search, edit history and pin history open beside their
button. Press the same button again or Escape to close that panel; its conversation
window and draft stay open. Creation and membership editing keep their confirmation
forms. The title, action buttons and list rows follow the same layout in both clients.

Use **Attachments to send** beside the attachment button to inspect staged files.
The count follows the active conversation. **Show attachment previews** switches
between compact file rows and previews; removing a row removes only that staged
attachment. Upload errors remain visible with the draft. Handler can cancel its
native upload operation; a browser file lost after reloading must be selected again
before sending. Server permissions still determine which file operations are available.

Desktop Enter sends, Ctrl+Enter or Command+Enter inserts a line, and a phone's Enter
inserts a line. During a mention, arrows choose a member, Enter inserts the mention
and Escape dismisses suggestions. Composing IME input never submits a message.
Delivery state, the full timestamp and edit metadata can be focused with the keyboard.
The emoji picker keeps large glyphs, categories, search, keyboard navigation and its
own scrollbar. Leaving or expiring the session stops further communication requests
until authentication succeeds again.
