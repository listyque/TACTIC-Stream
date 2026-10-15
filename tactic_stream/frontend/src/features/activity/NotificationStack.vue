<script setup>
// NotificationStack.qml / NotificationToastWindow.qml; activity and messages share toast presentation.
import { computed, ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import AppButton from '../../controls/AppButton.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
import AppProgress from '../../controls/AppProgress.vue'
import AppTextField from '../../controls/AppTextField.vue'
import { t } from '../../i18n.js'
import { mobile } from '../../mobile.js'
import { activeNotifications, dismissNotification, beginNotificationReply, cancelNotificationReply, editNotificationReply, submitNotificationReply, failNotificationReply } from './notifications.js'

const emit = defineEmits(['activity', 'messages', 'reply'])
const shown = computed(()=>activeNotifications.records.filter(row=>!(mobile.value && completed(row))))
const panel = ref(null), host = ref(document.body)
const dialogs = []
let observer, stopped = false
function updateHost(records = []) {
  for (const mutation of records) {
    const element = mutation.target
    if (mutation.type === 'attributes' && element.tagName === 'DIALOG' && element.open) {
      const previous = dialogs.indexOf(element)
      if (previous >= 0) dialogs.splice(previous, 1)
      dialogs.push(element)
    }
  }
  for (let index = dialogs.length - 1; index >= 0; index--) if (!dialogs[index].isConnected || !dialogs[index].open) dialogs.splice(index, 1)
  host.value = dialogs.at(-1) || document.body
  present()
}
async function present() {
  await nextTick()
  if (stopped || !panel.value) return
  if (shown.value.length) {
    if (!panel.value.matches(':popover-open')) panel.value.showPopover()
  } else if (panel.value.matches(':popover-open')) panel.value.hidePopover()
}
watch(shown, present)
onMounted(() => {
  dialogs.push(...document.querySelectorAll('dialog[open]'))
  observer = new MutationObserver(records => {
    if (records.some(row => row.type === 'attributes' ? row.target.tagName === 'DIALOG' : [...row.removedNodes].some(node => node.nodeType === 1 && (node.tagName === 'DIALOG' || node.querySelector('dialog'))))) updateHost(records)
  })
  observer.observe(document.body, { attributes: true, attributeFilter: ['open'], childList: true, subtree: true })
  updateHost()
})
onBeforeUnmount(() => { stopped = true; observer?.disconnect() })
function activate(row) { if (['activity', 'messages'].includes(row.action)) { dismissNotification(row.notificationId); emit(row.action, row.actionData) } }
function icon(row) { return row.sourceIcon || ({ error: 'priority-high', warning: 'warning', progress: 'sync', complete: 'check-circle' }[row.kind]) || 'info' }
function completed(row) { return row.group === 'server' && row.kind === 'complete' && row.message === 'Server operation completed' }
function accent(row) { return row.avatarColor || ({ error: 'var(--error)', warning: 'var(--yellow)', complete: 'var(--success)' }[row.kind]) || 'var(--primary)' }
async function beginReply(row) { if (beginNotificationReply(row.notificationId)) { await nextTick(); panel.value?.querySelector(`[data-notification-id="${row.notificationId}"] input`)?.focus() } }
function sendReply(row) { if (submitNotificationReply(row.notificationId)) emit('reply', { notificationId: row.notificationId, conversationId: row.actionData, body: row.replyText }) }
defineExpose({ replySent: dismissNotification, replyFailed({ notificationId, error }) { failNotificationReply(notificationId, error) } })
</script>

<template>
  <Teleport :to="host">
    <section ref="panel" popover="manual" class="notification-stack" :aria-label="t('Notifications')">
      <article v-for="row in shown" :key="row.notificationId" class="notification-card" :data-notification-id="row.notificationId" :data-kind="row.kind" :data-source="row.sourceType || ''" :data-dismissible="row.dismissible"
        :role="row.kind === 'error' || row.kind === 'warning' ? 'alert' : 'status'">
        <AppButton v-if="['activity', 'messages'].includes(row.action)" class="notification-activation" :label="row.action === 'messages' ? 'Open Messages' : 'Open Activity Feed'" @click="activate(row)" />
        <ItemPreview :source="row.previewUrl" :fallback-text="row.avatarText?.slice(0, 2).toUpperCase()" :fallback-icon="row.avatarText ? undefined : icon(row)" :accent="accent(row)" :preview-size="mobile ? 24 : 46" :round="['activity', 'messages'].includes(row.sourceType)" outlined />
        <div class="notification-content">
          <div v-if="row.sourceType" class="notification-source">{{ t(row.sourceType === 'messages' ? 'Messages' : 'Activity Feed') }}{{ row.sourceTitle ? ' · ' + row.sourceTitle : '' }}</div>
          <div class="notification-message" :tabindex="mobile && ['error','warning'].includes(row.kind) ? 0 : undefined">{{ row.sourceType ? row.message : t(row.message) }}</div>
          <div v-if="row.detail" class="notification-detail">{{ row.detail }}</div>
          <AppProgress v-if="row.kind === 'progress'" :label="row.message" />
        </div>
        <AppButton v-if="row.dismissible" class="notification-dismiss" icon-only icon="close" label="Dismiss notification" @click="dismissNotification(row.notificationId)" />
        <AppButton v-if="row.sourceType === 'messages' && row.actionData && !row.replyOpen" class="notification-reply-button" label="Reply" :disabled="!row.canReply" @click="beginReply(row)" />
        <form v-if="row.replyOpen" class="notification-reply" :aria-busy="row.replySending" @submit.prevent="sendReply(row)" @keydown.esc.prevent.stop="cancelNotificationReply(row.notificationId)">
          <AppTextField :model-value="row.replyText" label="Write a reply" :placeholder="t('Write a reply')" :disabled="row.replySending" @update:model-value="editNotificationReply(row.notificationId, $event)" @keydown.enter="event => { if (mobile || event.isComposing) event.preventDefault() }" />
          <AppButton type="submit" label="Send" :disabled="row.replySending || !row.replyText.trim()" />
          <AppButton icon-only icon="close" label="Cancel reply" :disabled="row.replySending" @click="cancelNotificationReply(row.notificationId)" />
        </form>
        <p v-if="row.replyError" class="notification-reply-error" role="alert">{{ t(row.replyError) }}</p>
      </article>
    </section>
  </Teleport>
</template>

<style scoped>
.notification-stack { position: fixed; inset: auto 18px 18px auto; width: min(420px, calc(100dvw - 36px)); max-height: calc(100dvh - 36px); margin: 0; padding: 0; border: 0; background: transparent; color: var(--on-surface); overflow: auto; }
.notification-stack:popover-open { display: flex; flex-direction: column; gap: 8px; }
.notification-card { position: relative; display: grid; grid-template-columns: 46px minmax(0, 1fr) 28px; gap: 10px; align-items: center; padding: 11px 7px 11px 13px; flex: 0 0 auto; border: 1px solid var(--outline); border-radius: 14px; background: var(--surface-high); box-shadow: 2px 5px 12px var(--shadow-color); }
.notification-card[data-dismissible="false"] { grid-template-columns: 46px minmax(0, 1fr); }
.notification-card[data-kind="progress"] { pointer-events:none; }
.notification-card > .image-picker-preview { width: 46px; height: 46px; min-width: 0; margin: 0; border-radius: 4px; pointer-events: none; }
.notification-card > .round-preview { border-radius: 50%; }
.notification-card :deep(.image-picker-preview > .app-icon) { font-size: 22px; width: 22px; height: 22px; }
.notification-content { display: flex; flex-direction: column; gap: 3px; min-width: 0; pointer-events: none; }
.notification-message { font-size: var(--text-body); line-height: 17px; font-weight: 600; overflow-wrap: anywhere; }
.notification-source, .notification-detail { font-size: var(--text-caption); line-height: 15px; }
.notification-source { color: var(--primary); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.notification-detail { color: var(--muted); display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; overflow: hidden; overflow-wrap: anywhere; }
.notification-card .notification-dismiss { width: 28px; height: 28px; min-width: 28px; min-height: 28px; border-radius: 4px; z-index: 1; }
.notification-dismiss :deep(.app-icon) { width: 17px; height: 17px; font-size: 17px; }
.notification-card .notification-activation { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; padding: 0; border-radius: inherit; background: transparent; color: transparent; font-size: 0; }
.notification-reply-button.app-button { grid-column:1/-1; justify-self:end; margin-top:0; min-width:72px; z-index:1; }
.notification-reply { grid-column:1/-1; display:flex; align-items:center; gap:6px; margin:0; z-index:1; }.notification-reply .app-text-field { flex:1; }.notification-reply .app-button:not(.icon-button) { min-width:72px; }.notification-reply .icon-button { width:28px; height:28px; min-width:28px; min-height:28px; }.notification-reply-error { grid-column:1/-1; margin:0; color:var(--error); font-size:var(--text-caption); line-height:15px; z-index:1; overflow-wrap:anywhere; }
.notification-reply :deep(.icon-button .app-icon) { width:17px; height:17px; font-size:17px; }
@media(max-width:700px) {
  .notification-stack { left:8px; right:8px; bottom:calc(8px + env(safe-area-inset-bottom)); width:auto; gap:4px; }
  .notification-stack:popover-open { gap:4px; }
  .notification-card { grid-template-columns:24px minmax(0,1fr) 24px; gap:8px; padding:8px; min-height:40px; border-radius:var(--field-radius); align-items:center; }
  .notification-card[data-dismissible="false"] { grid-template-columns:24px minmax(0,1fr); }
  .notification-card > .image-picker-preview { width:24px; height:24px; min-width:0; }
  .notification-card > .image-picker-preview .app-icon { width:14px; height:14px; font-size:14px; }
  .notification-message { font-size:var(--text-label); line-height:16px; }
  .notification-card:not([role="alert"]) .notification-message { display:-webkit-box; -webkit-box-orient:vertical; -webkit-line-clamp:2; overflow:hidden; }
  .notification-card[role="alert"] .notification-message { max-height:64px; overflow:auto; pointer-events:auto; }
  .notification-source,.notification-detail { font-size:var(--text-caption); line-height:14px; }
  .notification-card .notification-dismiss { width:24px; height:24px; min-width:24px; min-height:24px; border-radius:50%; }
  .notification-dismiss > .app-icon { width:14px; height:14px; font-size:14px; }
}
</style>
