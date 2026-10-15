<script setup>
// Handler TaskProcessPanel.qml: API-free quick process cards and compact rows, EPL-1.0.
import AppButton from '../../controls/AppButton.vue'
import StatusSelect from '../../controls/StatusSelect.vue'
import UserComboBox from '../../controls/UserComboBox.vue'
import AppMenu from '../../controls/AppMenu.vue'
import ItemSurface from '../../controls/ItemSurface.vue'
import { t } from '../../i18n.js'
import { ref, onMounted, onBeforeUnmount } from 'vue'
defineProps({ records: Array, mode: String, blocked: Boolean, target: Object })
defineEmits(['change', 'save', 'discard', 'inspect', 'add', 'edit', 'delete', 'select'])
const editable = (record, name) => record.plan.fields.some(field => field.name === name && field.editable) && !record.deleting
const panel = ref(null), columns = ref(1)
let observer
onMounted(() => { observer = new ResizeObserver(entries => { columns.value = Math.max(1, Math.floor(entries[0].contentRect.width / 224)) }); observer.observe(panel.value) })
onBeforeUnmount(() => observer.disconnect())
</script>
<template>
  <div ref="panel" class="task-process-panel" :class="mode" :aria-label="t('Task processes')" :style="{ '--process-columns': columns }">
    <ItemSurface v-for="record in target ? records : []" :key="record.value" :accent="record.color" :inset="0" class="task-process-item" :class="{ dirty: record.dirty, missing: !record.plan.task_key }" :data-process="record.value" :data-task-key="record.key">
      <div class="task-process-title"><span class="task-process-dot" :style="{ backgroundColor: record.color }"></span><strong>{{ record.label }}<template v-if="record.choices.length > 1"> | {{ record.choices.length }}</template></strong></div>
      <StatusSelect :value="record.values.status || ''" :options="record.statuses" :disabled="blocked || !editable(record, 'status')" @change="$emit('change', record, 'status', $event)" />
      <UserComboBox :value="record.values.assigned || ''" :options="record.users" :disabled="blocked || !editable(record, 'assigned')" @change="$emit('change', record, 'assigned', $event)" />
      <div class="task-process-actions">
        <AppButton v-if="record.dirty" label="Reset task changes" icon="undo" icon-only :disabled="blocked" @click="$emit('discard', record)" />
        <AppButton v-if="record.dirty" :label="record.plan.task_key ? 'Save task changes' : 'Create task'" icon="save" icon-only :disabled="blocked" @click="$emit('save', record)" />
        <AppButton label="Task notes" icon="comment" icon-only :badge-count="record.notes" :disabled="blocked || record.deleting" @click="$emit('inspect', record)" />
        <AppMenu label="Task actions" overlay :disabled="blocked">
          <AppButton label="Add task" icon="add" :disabled="blocked" @click="$emit('add', record)" />
          <AppButton v-if="record.plan.task_key" label="Edit task" icon="edit" :disabled="blocked || record.deleting" @click="$emit('edit', record)" />
          <AppButton v-if="record.plan.task_key" label="Delete task" icon="delete" destructive :disabled="blocked || record.dirty" @click="$emit('delete', record)" />
          <template v-if="record.choices.length > 1"><hr><strong>{{ t('Tasks') }}</strong><AppButton v-for="choice in record.choices" :key="choice.key" :label="choice.label" :aria-label="choice.label" :aria-pressed="record.key === choice.key" :icon="record.key === choice.key ? 'check' : undefined" @click="$emit('select', record.value, choice.key)">{{ choice.label }}</AppButton></template>
        </AppMenu>
      </div>
    </ItemSurface>
  </div>
  <div v-if="!target" class="task-manager-empty" role="status">{{ t('Select an sObject to view its task processes') }}</div>
</template>
