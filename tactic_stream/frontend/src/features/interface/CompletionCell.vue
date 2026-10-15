<script setup>
// Handler TacticCompletionCell.qml: 18px track, 10px margins, bounded fill.
import { computed } from 'vue'
import { t } from '../../i18n.js'
const props = defineProps({ percent: Number, text: String })
const percent = computed(() => Math.max(0, Math.min(100, Number(props.percent) || 0)))
</script>

<template>
  <div class="table-completion" role="progressbar" :aria-label="t('Completion')" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="percent" :aria-valuetext="text || percent.toFixed(1) + '%'">
    <span class="table-completion-fill" :style="{ width: percent + '%' }"></span>
    <span class="table-completion-label">{{ text || percent.toFixed(1) + '%' }}</span>
  </div>
</template>

<style scoped>
.table-completion { position:relative; height:18px; min-width:0; margin:0 10px; border-radius:9px; background:var(--surface-container); box-shadow:inset 0 0 0 1px var(--outline-variant); }
.table-completion-fill { position:absolute; inset:0 auto 0 0; border-radius:inherit; background:var(--primary); }
.table-completion-label { position:absolute; inset:0; display:grid; place-items:center; font:600 var(--text-caption)/18px var(--font-family); color:var(--on-surface); white-space:nowrap; }
</style>
