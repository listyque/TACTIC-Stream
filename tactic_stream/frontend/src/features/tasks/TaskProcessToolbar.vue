<script setup>
import { appearance } from '../../appearance.js';
import { metrics } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import { computed, markRaw } from 'vue';
import TaskWorkspacePart from './TaskWorkspacePart.vue';
import TaskWorkspaceSurfaceSwitcher from './TaskWorkspaceSurfaceSwitcher.vue';
const props = defineProps({ model: Object });
const paintModel = computed(() => ({
  ...props.model,
  controlHeight: metrics(appearance.theme).controlHeight
}));
const emit = defineEmits(['event']);
const surfacePort = markRaw(TaskWorkspaceSurfaceSwitcher);
const views = computed(() => ({
  surfaces: {
    component: surfacePort,
    props: {
      value: props.model.surface,
      disabled: props.model.busy,
      onChange: (value) => emit('event', { type: 'surface', value })
    }
  }
}));
</script>
<template>
  <TaskWorkspacePart
    class="task-manager-toolbar task-process-toolbar shared-process-toolbar"
    part="processToolbar"
    :model="paintModel"
    :views="views"
    @event="(action, source) => emit('event', action, source)"
  />
</template>
<style>
.task-manager-toolbar.shared-process-toolbar {
  display: block;
  padding: 0;
}
</style>
