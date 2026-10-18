// MessagesController's identity, UTC timestamps, five-minute author groups and stable paging.
export const messageId = (row) => row?.__search_key__ || row?.code || '';
export const messageDate = (value) =>
  new Date(
    /(?:Z|[+-]\d\d:\d\d)$/.test(value || '')
      ? value
      : String(value || '').replace(' ', 'T') + 'Z'
  );
export function initials(value) {
  return (
    String(value || '')
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0])
      .join('')
      .toUpperCase() || '?'
  );
}
export function groupedMessages(rows) {
  const same = (a, b) =>
    a &&
    b &&
    a.login === b.login &&
    Math.abs(messageDate(a.timestamp) - messageDate(b.timestamp)) <= 300000;
  return rows.map((row, index) => ({
    ...row,
    groupFirst: !same(rows[index - 1], row),
    groupLast: !same(row, rows[index + 1])
  }));
}
export function mergeMessages(rows) {
  return [...new Map(rows.map((row) => [messageId(row), row])).values()].sort(
    (a, b) =>
      String(a.timestamp).localeCompare(String(b.timestamp)) ||
      Number(a.id || 0) - Number(b.id || 0)
  );
}
// Match the server's timestamp/id ordering when a recent page refreshes loaded history.
export function retainOlderMessages(rows, page) {
  const oldest = page.at(-1),
    present = new Set(page.map(messageId));
  return rows.filter(
    (row) =>
      !oldest ||
      row.timestamp < oldest.timestamp ||
      (row.timestamp === oldest.timestamp &&
        Number(row.id) < Number(oldest.id)) ||
      present.has(messageId(row))
  );
}
export function canChangeMessage(row, login, privileged, now = Date.now()) {
  if (row.login !== login) return privileged;
  const stamp = messageDate(row.timestamp).getTime();
  return Number.isFinite(stamp) && stamp <= now && now - stamp <= 3600000;
}
// MessagesConversationList.qml: color depends on the number of recipients.
export function conversationColor(row) {
  return [
    'var(--primary)',
    'var(--success)',
    'var(--cyan)',
    '#a06bb4',
    'var(--yellow)'
  ][Math.min(4, row?.recipients?.length || 0)];
}
export function attachmentName(snapshot) {
  let metadata = snapshot.metadata || {};
  if (typeof metadata === 'string') {
    try {
      metadata = JSON.parse(metadata);
    } catch {
      metadata = {};
    }
  }
  return (
    metadata.chatAttachment?.name ||
    snapshot.__files__?.find((file) => !['web', 'icon'].includes(file.type))
      ?.file_name ||
    snapshot.code
  );
}
export function messageAttachments(row) {
  return [
    ...new Map(
      [
        ...(row.__attachments__ || []),
        ...(row.__forwarded_from__?.available
          ? row.__forwarded_from__.attachments || []
          : [])
      ].map((snapshot) => [snapshot.code, snapshot])
    ).values()
  ];
}
// MessagesController.conversationAttachments: each occurrence belongs to its message.
export function conversationAttachments(rows, users) {
  return rows.flatMap((row) =>
    messageAttachments(row).map((snapshot) => ({
      snapshot,
      messageId: messageId(row),
      sender:
        users.find((user) => user.login === row.login)?.displayName ||
        row.login,
      timestamp: row.timestamp
    }))
  );
}
// MessagesView.qml uses binary units with one decimal above bytes.
export {
  formatFileSize,
  bubbleContour,
  emojiCount
} from '../../../../src/tactic_stream/shared_ui/features/messages/messaging.state.mjs';
