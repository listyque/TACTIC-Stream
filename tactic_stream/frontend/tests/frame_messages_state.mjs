import assert from 'node:assert/strict';
import * as State from '../../src/tactic_stream/shared_ui/features/messages/messaging.state.mjs';
import * as Conversations from '../../src/tactic_stream/shared_ui/features/messages/conversation.ui.mjs';
import * as Message from '../../src/tactic_stream/shared_ui/features/messages/message.ui.mjs';
import * as Forms from '../../src/tactic_stream/shared_ui/features/messages/forms.ui.mjs';
import * as Panels from '../../src/tactic_stream/shared_ui/features/messages/panels.ui.mjs';
import * as Attachments from '../../src/tactic_stream/shared_ui/features/messages/attachments.ui.mjs';
import * as Feed from '../../src/tactic_stream/shared_ui/features/activity/feed.ui.mjs';
import * as Calendar from '../../src/tactic_stream/shared_ui/features/activity/calendar.ui.mjs';
import * as Notifications from '../../src/tactic_stream/shared_ui/features/activity/notifications.ui.mjs';
import * as Toast from '../../src/tactic_stream/shared_ui/features/activity/toast.ui.mjs';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
for (const width of [210, 252, 420]) {
  const layout = Conversations.layout(width, 500);
  const scene = Conversations.row(
    {
      title: 'Review',
      unread: 123,
      mentionCount: 1,
      selected: true,
      participantCount: 3
    },
    layout.rowWidth,
    'ru'
  );
  validateScene(scene, {}, {});
  assert(
    scene.nodes.every((node) => node.x >= 0 && node.width <= layout.rowWidth)
  );
  assert.equal(
    scene.nodes[0].children.find((node) => node.id === 'conversationUnread')
      .children[0].text,
    '99+'
  );
}
assert.equal(State.composerKey({ key: 'Enter' }), 'send');
assert.equal(State.composerKey({ key: 'Enter', control: true }), 'newline');
assert.equal(State.composerKey({ key: 'Enter' }, true), 'pass');
assert.equal(State.composerKey({ key: 'Enter', composing: true }), 'pass');
assert.equal(State.composerKey({ key: 'Enter', repeat: true }), 'consume');
assert.equal(
  State.composerKey({ key: 'Enter', sending: true }, false, true, true),
  'consume'
);
assert.equal(State.composerKey({ key: 'Enter' }, false, true, true), 'mention');
assert.equal(
  State.composerKey({ key: 'Escape' }, false, true, true),
  'dismiss'
);
assert.equal(State.mentionQuery('Review @ad', 10), 'ad');
assert.deepEqual(State.insertion('Review @ad', 10, 10, '@admin ', 3), {
  text: 'Review @admin ',
  cursor: 14
});
assert.equal(State.emojiCount('👨‍👩‍👧‍👦'), 1);
assert.equal(State.emojiCount('🇫🇷 🇯🇵'), 2);
assert.equal(State.emojiCount('😀 😀 😀 😀'), 0);
assert.equal(State.emojiCount('hello 😀'), 0);
assert.equal(State.formatFileSize(1024), '1.0 KB');
for (const width of [240, 360, 520, 1200]) {
  const g = State.bubbleGeometry(width, 200, 80, { last: true, own: true });
  assert(g.x >= 0 && g.x + g.width <= width);
  assert(g.width <= g.maximum);
  assert.equal(
    State.bubbleContour(g.width, g.height, g.corner, true).match(/Z$/)?.[0],
    'Z'
  );
}
console.log(
  'PASS messaging state: common conversation scenes, bounded geometry, mentions, composer keyboard and emoji clusters'
);
const views = Object.fromEntries(
  [
    'body',
    'people',
    'description',
    'message',
    'time',
    'detail',
    'error',
    'progress',
    'reply',
    'forward',
    'previews',
    'attachments',
    'text',
    'reactions'
  ].map((key) => [key, {}])
);
const walk = (nodes) =>
  nodes.flatMap((node) => [node, ...walk(node.children || [])]);
for (const width of [240, 316, 408, 900])
  for (const language of ['en', 'ru']) {
    for (const mode of [
      'create',
      'members',
      'rename',
      'edit',
      'search',
      'delete',
      'delete-message',
      'clear'
    ]) {
      const scene = Forms.form(
        { mode, text: 'Review', count: 2, canCreateGroup: false, valid: true },
        width,
        500,
        language,
        { description: 72 }
      );
      validateScene(scene, {}, views);
      assert(
        walk(scene.nodes).every(
          (node) => node.x >= 0 && node.x + node.width <= width + 0.01
        ),
        mode + ' controls fit ' + width
      );
    }
    const history = Panels.revision(
      {
        mode: 'pin-history',
        messageId: 'message',
        body: 'Review',
        pinnedBy: 'admin'
      },
      width,
      36,
      language
    );
    validateScene(history, {}, views);
    assert.equal(history.height, 71);
    const row = Notifications.row(
      { kind: 'warning', group: 'server', detail: 'Retry', time: 'Just now' },
      width,
      { message: 38, time: 15, detail: 32 },
      language
    );
    validateScene(row, {}, views);
    const ports = walk(row.nodes).filter((node) => node.kind === 'View');
    assert(ports.every((node) => node.y + node.height <= row.height));
    const toast = Toast.describe(
      {
        sourceType: 'message',
        message: 'Review',
        action: 'messages',
        actionData: 'chat',
        replyOpen: true,
        replyText: 'Ready',
        dismissible: true
      },
      width,
      { message: 36 },
      language
    );
    validateScene(toast, {}, views);
    assert(
      walk(toast.nodes).every(
        (node) => node.x >= 0 && node.x + node.width <= width + 0.01
      )
    );
    const metadata = Message.header(
      {
        sender: 'admin',
        edited: true,
        editedBy: 'admin',
        recipientCount: 2,
        readCount: 1,
        deliveryStatus: 'read',
        own: true
      },
      width,
      language
    );
    assert.equal(
      metadata.nodes.find((node) => node.id === 'messageDelivery').focusable,
      true
    );
    assert.equal(
      metadata.nodes.find((node) => node.id === 'messageTimeLabel').focusable,
      true
    );
    const body = Message.body(
      { text: true, attachments: true, reply: true },
      width,
      { text: 18, attachments: 40, reply: 54 }
    );
    assert.deepEqual(
      body.nodes.map((node) => node.view),
      ['reply', 'attachments', 'text']
    );
    assert.equal(body.height, 124);
    const panel = Attachments.panel({ previews: true }, width, 256, language);
    validateScene(panel, { drafts: [] }, {});
    assert.equal(panel.nodes.at(-1).rowHeight, 100);
  }
const month = new Date(2028, 1, 1, 12),
  days = Calendar.cells(
    month,
    { '2028-02-29': 4 },
    'ru',
    new Date(2028, 1, 29)
  );
assert.equal(days.length, 42);
assert.equal(days.find((row) => row.key === '2028-02-29').count, 4);
assert.equal(days.find((row) => row.key === '2028-02-29').today, true);
assert.equal(
  Calendar.initialMonth('', { invalid: 4, '2024-01-10': 2 }).getFullYear(),
  2024
);
const calendar = Calendar.describe(
  { month, counts: { '2028-02-29': 123 }, selected: '2028-02-29' },
  320,
  'ru'
);
validateScene(calendar, {}, views);
assert.equal(
  walk(calendar.nodes).find(
    (node) => node.id === 'activityCalendarCountText_2028-02-29'
  ).text,
  '99+'
);
console.log(
  'PASS communication forms, body ordering, bounded notifications, accessible metadata, draft lists and leap-day calendar'
);

for (const width of [280, 320, 360]) {
  const collapsed = Feed.toolbar({ phone: true }, width, 'ru');
  assert.equal(collapsed.height, 50);
  assert(!collapsed.nodes.some((n) => n.id === 'activityFeedFilterSegments'));
  const expanded = Feed.toolbar(
    { phone: true, optionsVisible: true, filter: 'notes' },
    width,
    'ru'
  );
  validateScene(expanded, {}, {});
  assert.equal(
    expanded.nodes.find((n) => n.id === 'activityFeedFilterSegments').kind,
    'Choice'
  );
  assert(expanded.nodes.every((n) => n.x + n.width <= width));
}
