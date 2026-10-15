<script setup>
// TaskQuickFilterPopup.qml: controls only; the screen owns the query and requests.
import AppCheckbox from '../../controls/AppCheckbox.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppButton from '../../controls/AppButton.vue'
import { t } from '../../i18n.js'
defineProps({ filters: Object, quick: Object, presets: Object, facets: Object, busy: Boolean })
defineEmits(['filter', 'quick', 'clear'])
</script>
<template>
  <div class="task-filter-fields">
    <AppCheckbox v-for="(label, value) in presets" :key="value" :label="`${t(label)} · ${facets?.preset?.[value] || 0}`" :translate-label="false" :model-value="quick.preset?.includes(value) || false" :disabled="busy" @update:model-value="$emit('quick', 'preset', value, $event)" />
    <label v-for="(label, name) in { process: 'Process', status: 'Status', assigned: 'Assigned to', supervisor: 'Supervisor', priority: 'Priority', milestone: 'Milestone' }" :key="name">{{ t(label) }}<AppSelect :model-value="filters[name]" :label="label" :translate-labels="false" :disabled="busy" :options="[{ value: '', label: t('All') }, ...(facets?.[name] || []).filter(item => item.key).map(item => ({ value: item.key, label: `${item.title} · ${item.count}` }))]" @update:model-value="$emit('filter', name, $event)" /></label>
    <label>{{ t('Deadline') }}<AppSelect :model-value="filters.due" label="Deadline" :disabled="busy" :options="[{ value: '', label: 'All' }, { value: 'overdue', label: 'Overdue' }, { value: 'today', label: 'Today' }, { value: 'soon', label: 'Next three days' }, { value: 'scheduled', label: 'Later' }]" @update:model-value="$emit('filter', 'due', $event)" /></label>
    <AppCheckbox label="Has notes" :model-value="filters.hasNotes || false" :disabled="busy" @update:model-value="$emit('filter', 'hasNotes', $event)" />
    <AppButton label="Clear filters" icon="close" :disabled="busy" @click="$emit('clear')" />
  </div>
</template>
