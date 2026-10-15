<script setup>
// Handler TaskWorkspaceSurfaceSwitcher.qml, EPL-1.0.
import AppSegmentedButton from '../../controls/AppSegmentedButton.vue'
defineProps({ value: String, disabled: Boolean })
defineEmits(['change'])
const options = [{ value: 'cards', label: 'Task cards', icon: 'MDI_VIEW_GRID' },
  { value: 'compact', label: 'Compact task list', icon: 'MDI_VIEW_LIST' },
  { value: 'workspace', label: 'Open task workspace', icon: 'MDI_VIEW_DASHBOARD' }]
</script>
<template><AppSegmentedButton class="task-surface-switcher" :model-value="value" label="Task workspace surface" icon-only :options="options" :disabled="disabled" @update:model-value="$emit('change', $event)" /></template>
