<script setup>
import { computed, ref, watchPostEffect } from 'vue'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
import { t } from '../../i18n.js'
import { appearance } from '../../appearance.js'
import { eventSentence, eventIcon, changeValue, compactText, needsExpansion, timestampLabel, safeColor } from './activity.js'
import { escapeHtml, linkifyPlainText, activateRichLink } from '../../controls/richText.js'
import { browserLink } from '../workspace/links.js'
const props = defineProps({ record: Object, now: Number })
const emit = defineEmits(['activity', 'target', 'open-link'])
const expanded = ref(false)
const sentence = ref(null)
const html = computed(() => eventSentence(props.record, expanded.value))
// CSSOM assignments preserve the site's CSP; injected style attributes are blocked.
watchPostEffect(() => { html.value; sentence.value?.querySelectorAll('[data-color]').forEach(element => { element.style.color = safeColor(element.dataset.color) }) })
const accent = computed(() => safeColor(props.record.processColor) || safeColor(props.record.typeColor) || ({ publication: 'var(--success)', task: 'var(--yellow)', work_hour: 'var(--cyan)' }[props.record.kind]) || 'var(--primary)')
const changes = computed(() => !props.record.relationAction && ['create', 'change', 'delete'].includes(props.record.kind) ? props.record.changes || [] : [])
const expandable = computed(() => [props.record.detail, props.record.title, ...changes.value.map(change => changeValue(props.record, change))].some(needsExpansion))
const time = computed(() => { appearance.language; return timestampLabel(props.record.timestamp, new Date(props.now || Date.now())) })
function activate(event) {
  if (activateRichLink(event, value => emit('open-link', value))) return
  const action = event.target.closest('[data-action]')?.dataset.action
  if (action) { event.preventDefault(); emit(action) }
}
</script>
<template>
  <article class="activity-event-card" :data-event-id="record.eventId" @click="activate">
    <ItemPreview :source="record.actorAvatar" :fallback-text="record.serverGenerated ? '' : record.actorInitials || record.actor?.slice(0, 1).toUpperCase()" :fallback-icon="record.serverGenerated ? 'system-activity' : !record.actor ? 'user' : undefined" :accent="record.actorColor" :preview-size="40" round outlined />
    <div class="activity-event-bubble">
      <header><strong>{{ record.serverGenerated ? t('Server trigger') : record.actorLabel || record.actor || t('Unknown user') }}</strong><time :datetime="record.timestamp" :title="record.timestamp">{{ time }}</time></header>
      <div class="activity-event-sentence"><AppIcon :name="eventIcon(record)" :style="{ color: accent }" /><div ref="sentence" v-html="html" /></div>
      <div v-if="changes.length" class="activity-changes"><div v-for="(change, index) in changes" :key="index"><span class="muted" :title="change.field">{{ t({ name: 'Name', title: 'Title', description: 'Description', assigned: 'Assignee', status: 'Status', priority: 'Priority', 'bid start date': 'Start date', 'bid end date': 'Deadline' }[String(change.field).toLowerCase()] || change.field) }}</span><span v-html="expanded ? linkifyPlainText(changeValue(record, change), browserLink) : escapeHtml(compactText(changeValue(record, change)))" /></div></div>
      <AppButton v-if="expandable" class="activity-expand" tonal :label="expanded ? 'Collapse' : 'Expand'" :icon="expanded ? 'MDI_CHEVRON_UP' : 'MDI_CHEVRON_DOWN'" :aria-expanded="expanded" @click="expanded = !expanded" />
    </div>
  </article>
</template>
