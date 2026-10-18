<script setup>
import { markRaw, h, computed } from 'vue';
import TaskWorkspacePart from './TaskWorkspacePart.vue';
import BusyIndicator from '../../controls/BusyIndicator.vue';
import { appearance } from '../../appearance.js';
import { metrics } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
const props = defineProps({ model: Object });
const emit = defineEmits(['event']);
const model = computed(() => ({
  ...props.model,
  controlHeight: metrics(appearance.theme).controlHeight
}));
const views = {
  busy: {
    component: markRaw({
      setup() {
        return () => h(BusyIndicator, { running: props.model.busy });
      }
    })
  }
};
</script>
<template>
  <TaskWorkspacePart
    class="task-workspace-footer"
    part="footer"
    :model="model"
    :views="views"
    @event="(action) => emit('event', action)"
  />
</template>
<style>
.task-workspace-footer.task-manager-footer {
  display: block;
  padding: 0;
  border-radius: 0;
  min-height: 58px;
  background: var(--surface-container);
}
.task-workspace-footer [data-frame='taskFooterCount'] {
  white-space: pre;
}
</style>

<style>
.task-workspace-footer::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 1px;
  background: var(--outline-variant);
  pointer-events: none;
  z-index: 100;
}
</style>
