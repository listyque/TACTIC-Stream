<script setup>
import { computed, ref } from 'vue'
import AppButton from '../../controls/AppButton.vue'
import { t } from '../../i18n.js'
import { appearance } from '../../appearance.js'
import { dateKey, dateLabel } from './activity.js'
const props = defineProps({ counts: Object, selected: String, busy: Boolean })
const emit = defineEmits(['accepted', 'closed'])
const month = ref(new Date())
function reset() { const newest = Object.keys(props.counts || {}).filter(key => props.counts[key] > 0).sort().at(-1); month.value = new Date((props.selected || newest || dateKey(new Date())) + 'T12:00:00') }
function move(delta) { month.value = new Date(month.value.getFullYear(), month.value.getMonth() + delta, 1, 12) }
const title = computed(() => month.value.toLocaleDateString(appearance.language, { month: 'long', year: 'numeric' }))
const firstDay = computed(() => appearance.language === 'ru' ? 1 : 0)
const weekdays = computed(() => Array.from({ length: 7 }, (_, index) => new Date(2026, 0, 4 + (index + firstDay.value) % 7).toLocaleDateString(appearance.language, { weekday: 'short' })))
const cells = computed(() => {
  const first = new Date(month.value.getFullYear(), month.value.getMonth(), 1, 12)
  const offset = (first.getDay() - firstDay.value + 7) % 7
  return Array.from({ length: 42 }, (_, index) => { const date = new Date(first.getFullYear(), first.getMonth(), index - offset + 1, 12), key = dateKey(date); return { key, day: date.getDate(), inMonth: date.getMonth() === first.getMonth(), today: key === dateKey(new Date()), count: props.counts?.[key] || 0 } })
})
defineExpose({ reset })
</script>
<template>
  <section class="activity-calendar" :aria-label="t('Activity calendar')" :aria-busy="busy">
    <header><AppButton icon-only label="Previous month" icon="MDI_CHEVRON_LEFT" @click="move(-1)" /><strong>{{ title }}</strong><AppButton icon-only label="Next month" icon="MDI_CHEVRON_RIGHT" @click="move(1)" /></header>
    <div class="activity-calendar-grid"><span v-for="name in weekdays" :key="name" class="muted">{{ name }}</span>
      <AppButton v-for="cell in cells" :key="cell.key" :label="String(cell.day)" :translate-label="false" :aria-label="dateLabel(cell.key) + ' · ' + t('{count} events', { count: cell.count })" :aria-pressed="selected === cell.key" :class="{ outside: !cell.inMonth, today: cell.today }" :disabled="cell.count <= 0" @click="emit('accepted', cell.key)">{{ cell.day }}<small v-if="cell.count">{{ cell.count > 99 ? '99+' : cell.count }}</small></AppButton>
    </div><footer><AppButton label="All history" @click="emit('accepted', '')" /><span v-if="busy" role="status">{{ t('Updating calendar history…') }}</span><AppButton label="Close" @click="emit('closed')" /></footer>
  </section>
</template>
