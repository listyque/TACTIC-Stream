<script setup>
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import { t } from '../../i18n.js'
defineProps({ summary: Object, expanded: Boolean, busy: Boolean })
const emit = defineEmits(['log', 'timesheet'])
const labels = { planned: 'Planned', approved: 'Approved', remaining: 'Remaining', overPlan: 'Over plan' }
const hours = value => Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })
</script>

<template>
  <section class="task-details work-hours-summary" :class="{ compact:!expanded }" :aria-label="t('Work hours')">
    <header><AppIcon name="MDI_CLOCK_OUTLINE" /><strong>{{ t('Work hours') }}</strong>
      <span v-if="!expanded">{{ hours(summary.approved) }} / {{ hours(summary.planned) }} {{ t('h') }}</span>
      <span v-else-if="summary.pending > 0" class="work-hours-pending">{{ hours(summary.pending) }} {{ t('h') }} {{ t('Pending') }}</span>
      <div class="configuration-actions"><AppButton icon-only label="Log time" icon="MDI_ALARM_PLUS" :disabled="busy" @click="emit('log')" /><AppButton icon-only label="Open timesheet" icon="MDI_CALENDAR_MONTH" :disabled="busy" @click="emit('timesheet')" /></div></header>
    <template v-if="expanded"><dl class="work-hours-metrics"><div v-for="(label, name) in labels" :key="name"><dd :class="{ 'over-plan':name === 'overPlan' && summary[name] > 0 }">{{ hours(summary[name]) }} {{ t('h') }}</dd><dt>{{ t(label) }}</dt></div></dl>
      <progress :value="summary.progress" max="100" :aria-label="t('Approved hours progress')" /></template>
  </section>
</template>
<style>
.notes-panel > .work-hours-summary { height:80px; padding:3px 7px 10px 9px; border:1px solid var(--outline-variant); border-radius:var(--item-radius); background:var(--surface-high); }.notes-panel > .work-hours-summary.compact { height:32px; padding-bottom:3px; }
.work-hours-summary > header { height:26px; min-height:26px; gap:7px; flex-wrap:nowrap; }.work-hours-summary > header > .app-icon { width:15px; height:15px; font-size:15px; color:var(--primary); }.work-hours-summary > header > strong { font-size:var(--text-caption); text-transform:uppercase; letter-spacing:.45px; }.work-hours-summary > header > span { font-size:var(--text-label); }.work-hours-summary .work-hours-pending { color:var(--yellow); }.work-hours-summary > header > .configuration-actions { margin-left:auto; gap:2px; }.work-hours-summary > header .app-button { width:25px; height:25px; min-height:0; padding:0; }
.notes-panel .work-hours-summary .work-hours-metrics { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; height:28px; margin:5px 0; text-align:center; }.work-hours-metrics > div { display:flex; flex-direction:column; justify-content:center; }.work-hours-summary .work-hours-metrics dd { margin:0; font-size:var(--text-label); font-weight:600; }.work-hours-summary .work-hours-metrics dt { font-size:var(--text-micro); color:var(--muted); }.work-hours-summary > progress { display:block; width:100%; height:3px; }
</style>

