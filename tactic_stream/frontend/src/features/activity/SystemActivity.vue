<script setup>
// Handler NotificationsView.qml / NotificationController; repository sync is excluded.
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppSegmentedButton from '../../controls/AppSegmentedButton.vue'
import { t } from '../../i18n.js'
import { appearance } from '../../appearance.js'
import { activateRichLink, linkifyPlainText } from '../../controls/richText.js'
import { browserLink } from '../workspace/links.js'
import { timestampLabel, timestampFullLabel } from './activity.js'
import { notificationHistory, clearNotificationHistory } from './notifications.js'
import './activityFeed.css'

const emit = defineEmits(['closed', 'open-link'])
const dialog = ref(null), content = ref(null), width = ref(0), group = ref('all')
let observer
onMounted(() => { observer = new ResizeObserver(entries => { width.value = entries[0].contentRect.width }); observer.observe(content.value) })
onBeforeUnmount(() => observer?.disconnect())
const filters = [{ value: 'all', label: 'All', icon: 'select-all' }, { value: 'server', label: 'Server', icon: 'dns' },
  { value: 'checkin', label: 'Check-in', icon: 'commit-queue' }, { value: 'client', label: 'Client', icon: 'desktop' }]
const records = computed(() => notificationHistory.records.filter(row => group.value === 'all' || row.group === group.value))
const kindIcon = kind => ({ error: 'priority-high', warning: 'warning', complete: 'check-circle', progress: 'sync' }[kind] || 'info')
const groupTitle = value => ({ server: 'Server transactions', checkin: 'Check-in operations' }[value] || 'Client')
function time(value) { appearance.language; return timestampLabel(value, new Date()) }
function activate(event) { activateRichLink(event, value => { dialog.value.close(); emit('open-link', value) }) }
defineExpose({ open() { dialog.value.show() } })
</script>

<template>
  <Teleport to="body">
    <dialog v-window="{ type:'window' }" ref="dialog" class="activity-dialog system-activity-dialog" :aria-label="t('Notifications')" @close="emit('closed')">
      <header class="activity-feed-heading"><AppIcon name="system-activity" /><strong>{{ t('Notifications') }}</strong><AppButton icon-only icon="close" label="Close Notifications" @click="dialog.close()" /></header>
      <div ref="content" class="system-activity-content"><section class="activity-feed-panel">
        <div class="activity-feed-toolbar">
          <div class="activity-feed-title"><strong>{{ t('ACTIVITY & NOTIFICATIONS') }}</strong><AppButton label="Clear history" icon="delete-sweep" :disabled="!notificationHistory.records.length" @click="clearNotificationHistory" /></div>
          <p class="muted">{{ t('Client events and background operations from this session.') }}</p>
          <AppSegmentedButton v-model="group" :options="filters" :icon-only="width < 760" label="Notification history filters" />
        </div>
        <div class="system-activity-history" role="log" :aria-label="t('Notification history')">
          <article v-for="row in records" :key="row.notificationId" class="system-activity-event" :data-kind="row.kind" :data-group="row.group" @click="activate">
            <div class="system-activity-row-content"><AppIcon :name="kindIcon(row.kind)" />
              <div><header><strong v-html="linkifyPlainText(row.sourceType ? row.message : t(row.message), browserLink)" /><time v-if="time(row.timestamp)" :datetime="row.timestamp" :title="timestampFullLabel(row.timestamp)">{{ time(row.timestamp) }}</time></header>
                <small>{{ t(groupTitle(row.group)) }}</small><p v-if="row.detail" v-html="linkifyPlainText(row.sourceType ? row.detail : t(row.detail), browserLink)" /></div>
            </div>
          </article>
          <div v-if="!records.length" class="system-activity-empty"><AppIcon name="notifications" /><p>{{ t('No events in this group') }}</p></div>
        </div>
      </section></div>
    </dialog>
  </Teleport>
</template>

<style>
.system-activity-dialog { width:min(56dvw, calc(100dvw - 16px)); height:min(64dvh, calc(100dvh - 16px)); }
.system-activity-content { flex:1; min-height:0; display:flex; }
/* Qt anchors measure from the Rectangle edge; CSS padding starts inside its 1px border. */
.system-activity-content .activity-feed-panel { min-width:0; margin:12px; padding:9px; gap:10px; border:1px solid var(--outline-variant); border-radius:var(--surface-radius); }
.system-activity-content .activity-feed-toolbar { flex-flow:column nowrap; gap:8px; padding:10px; border-radius:var(--item-radius); background:var(--surface-high); }
.system-activity-content .activity-feed-title { flex-basis:auto; flex-direction:row; flex-wrap:nowrap; gap:8px; }
.system-activity-content .activity-feed-title > strong { flex-basis:auto; min-width:0; white-space:nowrap; overflow:hidden; }
.system-activity-content .activity-feed-title > .app-button { flex-shrink:0; white-space:nowrap; }
.system-activity-content .app-segmented-button { width:100%; flex:none; }
.system-activity-dialog .activity-feed-toolbar > p { margin:0; font-size:var(--text-label); }
.system-activity-history { flex:1; min-height:0; min-width:0; overflow:auto; overscroll-behavior:contain; margin-right:8px; }
.system-activity-event { --event-accent:var(--primary); position:relative; container-type:inline-size; margin:0 12px 6px 0; padding-bottom:2px; }
.system-activity-event::before { content:''; position:absolute; inset:1px; background:var(--surface-high); border:1px solid var(--outline-variant); border-radius:var(--item-radius); transition:background var(--motion-hover-medium) var(--motion-easing-out-cubic); pointer-events:none; }
.system-activity-event:hover::before { background:color-mix(in srgb, var(--surface-high) 92%, var(--on-surface)); transition-duration:var(--motion-hover); }
.system-activity-event::after { content:''; position:absolute; left:0; top:6px; bottom:6px; width:3px; border-radius:1.5px; background:var(--event-accent); pointer-events:none; }
.system-activity-row-content { position:relative; display:flex; align-items:flex-start; gap:10px; padding:10px 10px 10px 12px; }
.system-activity-event[data-kind="error"] { --event-accent:var(--error); }
.system-activity-event[data-kind="warning"] { --event-accent:var(--yellow); }
.system-activity-event[data-kind="complete"] { --event-accent:var(--success); }
.system-activity-row-content > .app-icon { flex-shrink:0; width:19px; height:19px; font-size:19px; color:var(--event-accent); }
.system-activity-row-content > div { flex:1; min-width:0; display:flex; flex-direction:column; gap:4px; }
.system-activity-event header { display:grid; grid-template-columns:minmax(0, 1fr) auto; column-gap:8px; row-gap:2px; align-items:start; }
.system-activity-event strong { flex:1; font-size:var(--text-body-large); font-weight:600; overflow-wrap:anywhere; }
.system-activity-event time { color:var(--muted); font-size:var(--text-caption); text-align:right; }
.system-activity-event small { color:var(--event-accent); font-size:var(--text-caption); font-weight:600; }
.system-activity-event p { margin:0; color:var(--muted); font-size:var(--text-label); overflow-wrap:anywhere; }
.system-activity-empty { min-height:140px; height:100%; display:flex; flex-direction:column; gap:8px; align-items:center; justify-content:center; color:var(--muted); }
.system-activity-empty > .app-icon { font-size:30px; width:30px; height:30px; }
.system-activity-empty p { margin:0; max-width:min(440px, calc(100% - 48px)); text-align:center; color:var(--on-surface); font-size:var(--text-body-large); font-weight:600; }
@container (max-width:619px) {
  .system-activity-event header { grid-template-columns:minmax(0, 1fr); }
  .system-activity-event time { text-align:left; }
}
@media (max-width:760px) {
  .system-activity-dialog { width:calc(100dvw - 8px); height:calc(100dvh - 8px); }
}
</style>
