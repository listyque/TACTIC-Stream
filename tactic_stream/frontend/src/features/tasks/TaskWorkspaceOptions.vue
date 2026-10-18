<script setup>
import { markRaw, computed } from 'vue';
import TaskWorkspacePart from './TaskWorkspacePart.vue';
import TaskWorkspaceSurfaceSwitcher from './TaskWorkspaceSurfaceSwitcher.vue';
const props = defineProps({ model: Object });
const emit = defineEmits(['event']);
const views = computed(() => ({
  surfaces: {
    component: markRaw(TaskWorkspaceSurfaceSwitcher),
    props: {
      value: props.model.surface,
      disabled: props.model.blocked,
      onChange: (value) => emit('event', { type: 'surface', value })
    }
  }
}));
</script>
<template>
  <TaskWorkspacePart
    part="options"
    :model="model"
    :views="views"
    @event="(action, source) => emit('event', action, source)"
  />
</template>
