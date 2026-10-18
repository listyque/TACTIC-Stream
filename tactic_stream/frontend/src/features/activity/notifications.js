// Handler NotificationController: session history and at most three active notices.
import { shallowReactive } from 'vue';
import { redact } from '../debug/debugLog.js';

export const notificationHistory = shallowReactive({ records: [] });
export const activeNotifications = shallowReactive({ records: [] });
const recent = new Map();
const timers = new Map();
let sequence = 0;

export function notify(
  kind,
  message,
  detail = '',
  group = 'client',
  key = '',
  source = {}
) {
  if (!['info', 'warning', 'error', 'progress', 'complete'].includes(kind))
    kind = 'info';
  message = String(redact(message || '')).trim();
  if (!message) return;
  const now = Date.now(),
    signature = key || `${kind}:${message}`;
  if (
    activeNotifications.records.some((row) => row.dedupeKey === signature) ||
    (recent.has(signature) && now - recent.get(signature) < 5000)
  )
    return;
  recent.set(signature, now);
  for (const [value, stamp] of recent)
    if (now - stamp >= 30000) recent.delete(value);
  const row = {
    notificationId: ++sequence,
    kind,
    group,
    message,
    detail: String(redact(detail || '')),
    timestamp: new Date(now).toISOString(),
    dedupeKey: signature,
    dismissible: true,
    sourceType: source.sourceType || '',
    sourceTitle: source.sourceTitle || '',
    previewUrl: source.previewUrl || '',
    avatarText: source.avatarText || '',
    avatarColor: source.avatarColor || '',
    sourceIcon: source.sourceIcon || '',
    action: source.action || '',
    actionData: source.actionData || '',
    canReply: source.canReply !== false,
    replyOpen: false,
    replySending: false,
    replyError: '',
    replyText: ''
  };
  notificationHistory.records = [row, ...notificationHistory.records].slice(
    0,
    200
  );
  activeNotifications.records = [...activeNotifications.records, row];
  limitActive();
  startTimer(
    row.notificationId,
    row.sourceType === 'messages'
      ? 15000
      : row.sourceType === 'activity'
        ? 8000
        : ['error', 'warning'].includes(kind)
          ? 5000
          : 3200
  );
  return row.notificationId;
}

function startTimer(id, duration) {
  clearTimeout(timers.get(id));
  const timer = setTimeout(() => dismissNotification(id), duration);
  timer.unref?.();
  timers.set(id, timer);
}

function limitActive() {
  while (activeNotifications.records.length > 3)
    dismissNotification(
      (
        activeNotifications.records.find((row) => !row.replyOpen) ||
        activeNotifications.records.at(-1)
      ).notificationId
    );
}

function updateReply(id, values) {
  activeNotifications.records = activeNotifications.records.map((row) =>
    row.notificationId === id ? { ...row, ...values } : row
  );
}
export function beginNotificationReply(id) {
  const row = activeNotifications.records.find(
    (row) => row.notificationId === id
  );
  if (!row || row.sourceType !== 'messages' || !row.actionData || !row.canReply)
    return false;
  clearTimeout(timers.get(id));
  timers.delete(id);
  updateReply(id, { replyOpen: true });
  return true;
}
export function cancelNotificationReply(id) {
  const row = activeNotifications.records.find(
    (row) => row.notificationId === id
  );
  if (!row?.replyOpen || row.replySending) return;
  updateReply(id, { replyOpen: false, replyError: '' });
  startTimer(id, 15000);
}
export function editNotificationReply(id, text) {
  updateReply(id, { replyText: text });
}
export function submitNotificationReply(id) {
  const row = activeNotifications.records.find(
    (row) => row.notificationId === id
  );
  if (
    !row?.replyOpen ||
    !row.canReply ||
    row.replySending ||
    !row.replyText.trim()
  )
    return false;
  updateReply(id, { replySending: true, replyError: '' });
  return true;
}
export function failNotificationReply(id, error) {
  updateReply(id, {
    replySending: false,
    replyError: error || 'Unable to send message'
  });
}

export function dismissNotification(id) {
  clearTimeout(timers.get(id));
  timers.delete(id);
  activeNotifications.records = activeNotifications.records.filter(
    (row) => row.notificationId !== id
  );
}

export function setNotificationProgress(message) {
  const id = 'application-progress';
  if (!message) {
    dismissNotification(id);
    return;
  }
  const row = {
    notificationId: id,
    kind: 'progress',
    message,
    detail: '',
    dismissible: false
  };
  const index = activeNotifications.records.findIndex(
    (row) => row.notificationId === id
  );
  if (index >= 0)
    activeNotifications.records = activeNotifications.records.map((item) =>
      item.notificationId === id ? row : item
    );
  else {
    activeNotifications.records = [...activeNotifications.records, row];
    limitActive();
  }
}

export function clearNotificationHistory() {
  notificationHistory.records = [];
}
export function resetNotifications() {
  for (const timer of timers.values()) clearTimeout(timer);
  timers.clear();
  recent.clear();
  activeNotifications.records = [];
  clearNotificationHistory();
}
