<script setup>
// NotificationStack.qml / NotificationToastWindow.qml; activity and messages share toast presentation.
import {
  computed,
  ref,
  watch,
  nextTick,
  onMounted,
  onBeforeUnmount
} from 'vue';
import NotificationToast from './NotificationToast.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/activity/toast.ui.mjs';
import { t } from '../../i18n.js';
import { mobile } from '../../mobile.js';
import {
  activeNotifications,
  dismissNotification,
  beginNotificationReply,
  cancelNotificationReply,
  editNotificationReply,
  submitNotificationReply,
  failNotificationReply
} from './notifications.js';

const emit = defineEmits(['activity', 'messages', 'reply']);
const shown = computed(() =>
  activeNotifications.records.filter((row) => !(mobile.value && completed(row)))
);
const panel = ref(null),
  host = ref(document.body);
const dialogs = [];
let observer,
  stopped = false;
function updateHost(records = []) {
  for (const mutation of records) {
    const element = mutation.target;
    if (
      mutation.type === 'attributes' &&
      element.tagName === 'DIALOG' &&
      element.open
    ) {
      const previous = dialogs.indexOf(element);
      if (previous >= 0) dialogs.splice(previous, 1);
      dialogs.push(element);
    }
  }
  for (let index = dialogs.length - 1; index >= 0; index--)
    if (!dialogs[index].isConnected || !dialogs[index].open)
      dialogs.splice(index, 1);
  host.value = dialogs.at(-1) || document.body;
  present();
}
async function present() {
  await nextTick();
  if (stopped || !panel.value) return;
  if (shown.value.length) {
    if (!panel.value.matches(':popover-open')) panel.value.showPopover();
  } else if (panel.value.matches(':popover-open')) panel.value.hidePopover();
}
watch(shown, present);
onMounted(() => {
  dialogs.push(...document.querySelectorAll('dialog[open]'));
  observer = new MutationObserver((records) => {
    if (
      records.some((row) =>
        row.type === 'attributes'
          ? row.target.tagName === 'DIALOG'
          : [...row.removedNodes].some(
              (node) =>
                node.nodeType === 1 &&
                (node.tagName === 'DIALOG' || node.querySelector('dialog'))
            )
      )
    )
      updateHost(records);
  });
  observer.observe(document.body, {
    attributes: true,
    attributeFilter: ['open'],
    childList: true,
    subtree: true
  });
  updateHost();
});
onBeforeUnmount(() => {
  stopped = true;
  observer?.disconnect();
});
function activate(row) {
  if (['activity', 'messages'].includes(row.action)) {
    dismissNotification(row.notificationId);
    emit(row.action, row.actionData);
  }
}
function completed(row) {
  return (
    row.group === 'server' &&
    row.kind === 'complete' &&
    row.message === 'Server operation completed'
  );
}
async function beginReply(row) {
  if (beginNotificationReply(row.notificationId)) {
    await nextTick();
    panel.value
      ?.querySelector(`[data-notification-id="${row.notificationId}"] input`)
      ?.focus();
  }
}
function sendReply(row) {
  if (submitNotificationReply(row.notificationId))
    emit('reply', {
      notificationId: row.notificationId,
      conversationId: row.actionData,
      body: row.replyText
    });
}
function toastAction(row, event) {
  if (event.type === 'activate') activate(row);
  else if (event.type === 'dismiss') dismissNotification(row.notificationId);
  else if (event.type === 'reply') beginReply(row);
  else if (event.type === 'cancel') cancelNotificationReply(row.notificationId);
  else if (event.type === 'text')
    editNotificationReply(row.notificationId, event.value);
  else if (event.type === 'send') sendReply(row);
}
defineExpose({
  replySent: dismissNotification,
  replyFailed({ notificationId, error }) {
    failNotificationReply(notificationId, error);
  }
});
</script>

<template>
  <Teleport :to="host">
    <section
      ref="panel"
      popover="manual"
      class="notification-stack"
      :style="{ '--notification-width': UI.metrics.width + 'px' }"
      :aria-label="t('Notifications')"
    >
      <NotificationToast
        v-for="row in shown"
        :key="row.notificationId"
        :row="row"
        @action="(event) => toastAction(row, event)"
      />
    </section>
  </Teleport>
</template>

<style scoped>
.notification-stack {
  position: fixed;
  inset: auto 18px 18px auto;
  width: min(var(--notification-width), calc(100dvw - 36px));
  max-height: calc(100dvh - 36px);
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--on-surface);
  overflow: auto;
  scrollbar-gutter: stable;
}
.notification-stack:popover-open {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
@media (max-width: 700px) {
  .notification-stack {
    left: 8px;
    right: 8px;
    bottom: calc(8px + env(safe-area-inset-bottom));
    width: auto;
    gap: 4px;
  }
  .notification-stack:popover-open {
    gap: 4px;
  }
}
</style>
