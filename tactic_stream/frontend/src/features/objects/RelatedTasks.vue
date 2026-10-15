<script setup>
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import SummaryChip from '../../controls/SummaryChip.vue'
import { t } from '../../i18n.js'

defineProps({ related: Object, busy: Boolean, accent: String })
const emit = defineEmits(['open'])
const messages = { unconfigured: 'No related Search Type configured for this progress',
  missingType: 'Search Type is unavailable', unrelated: 'No schema relationship to this Search Type' }
</script>

<template>
  <section class="task-details related-tasks" :aria-label="t('Related object tasks')">
    <header><AppIcon name="MDI_CHART_DONUT" /><strong>{{ t('Related object tasks') }}</strong>
      <SummaryChip v-if="related.summary_available" :label="related.approved + ' / ' + related.total" icon="MDI_CHART_DONUT" :accent="accent" compact :show-dot="false" :show-count="false" /></header>
    <p v-if="related.state !== 'ready'" class="muted">{{ t(messages[related.state]) }}<span v-if="related.search_type">: {{ related.search_type }}</span></p>
    <template v-else>
      <p v-if="!related.summary_available" class="notice">{{ t('Task process or status pipeline is not configured for this progress count.') }}</p>
      <p v-if="!related.items.length" class="muted">{{ t(related.object_count ? 'No tasks on related objects' : 'No related objects') }}</p>
      <ul v-else class="related-task-list">
        <li v-for="item in related.items" :key="item.task_key">
          <div class="related-task-title"><strong>{{ item.parent_title }}</strong><small> · {{ item.process }}</small></div>
          <small>{{ item.assigned }}</small>
          <SummaryChip :label="item.status || t('No status')" :accent="accent" compact :show-dot="false" :show-count="false" />
          <AppButton label="Open related task" icon="MDI_CHEVRON_RIGHT" icon-only :disabled="busy" @click="emit('open', item)" />
        </li>
      </ul>
    </template>
  </section>
</template>
<style>
.notes-panel > .related-tasks { display:flex; flex-direction:column; height:148px; max-height:none; overflow:hidden; border-color:var(--outline-variant); background:var(--surface-deep); }.related-tasks > header { min-height:24px; gap:6px; flex-wrap:nowrap; }.related-tasks > header > .app-icon { width:17px; height:17px; font-size:17px; color:var(--primary); }.related-tasks > header > strong { flex:1; font-size:var(--text-label); font-weight:600; }.related-tasks > p { flex:1; display:flex; align-items:center; font-size:var(--text-caption); }.related-tasks > .related-task-list { flex:1; overflow:auto; margin:5px 0 0; padding:0; }.related-tasks .related-task-list li { display:flex; align-items:center; height:28px; gap:6px; padding:0; margin-bottom:3px; border:0; background:transparent; font-size:var(--text-caption); }.related-tasks .related-task-list li > .related-task-title { flex:1; min-width:0; display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.related-tasks .related-task-list strong { font-weight:400; }.related-tasks .related-task-list small { color:var(--muted); font-size:inherit; }.related-tasks .related-task-list .app-button { width:24px; height:24px; min-height:0; padding:0; }
</style>


