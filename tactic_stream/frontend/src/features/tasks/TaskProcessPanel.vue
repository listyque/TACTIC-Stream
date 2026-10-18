<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import TaskProcessItem from './TaskProcessItem.vue';
import { t } from '../../i18n.js';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/process.ui.mjs';
defineProps({ records: Array, mode: String, blocked: Boolean, target: Object });
const emit = defineEmits([
  'change',
  'save',
  'discard',
  'inspect',
  'add',
  'edit',
  'delete',
  'select'
]);
const panel = ref(null),
  width = ref(0);
const columns = computed(() => UI.columns(width.value));
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    width.value = entries[0].contentRect.width;
  });
  observer.observe(panel.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="panel"
    class="task-process-panel"
    :class="mode"
    :aria-label="t('Task processes')"
    :style="{
      '--process-columns': columns,
      '--process-card-width':
        Math.max(0, width / columns - UI.metrics.gap) + 'px',
      padding: UI.metrics.inset + 'px',
      gap: (mode === 'cards' ? UI.metrics.gap : UI.metrics.compactGap) + 'px'
    }"
  >
    <TaskProcessItem
      v-for="record in target ? records : []"
      :key="record.value"
      :record="record"
      :mode="mode"
      :blocked="blocked"
      @change="(name, value) => emit('change', record, name, value)"
      @save="emit('save', record)"
      @discard="emit('discard', record)"
      @inspect="emit('inspect', record)"
      @add="emit('add', record)"
      @edit="emit('edit', record)"
      @delete="emit('delete', record)"
      @select="emit('select', record.value, $event)"
    />
  </div>
  <div v-if="!target" class="task-manager-empty" role="status">
    {{ t('Select an sObject to view its task processes') }}
  </div>
</template>
<style>
.task-process-panel {
  padding: 6px;
}
.task-process-panel.cards {
  display: grid;
  grid-template-columns: repeat(
    var(--process-columns),
    var(--process-card-width)
  );
  align-content: start;
  gap: 7px;
}
.task-process-panel.compact {
  display: flex;
  flex-direction: column;
  gap: 5px;
  overflow-x: auto;
}
</style>
