<script setup>
import { appearance } from '../../appearance.js';
import { metrics } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import TaskWorkspacePart from './TaskWorkspacePart.vue';
defineProps({ value: String, disabled: Boolean });
defineEmits(['change']);
</script>
<template>
  <TaskWorkspacePart
    class="task-surface-switcher"
    part="surfaces"
    :model="{
      value,
      disabled,
      controlHeight: metrics(appearance.theme).controlHeight
    }"
    @event="$emit('change', $event.value)"
  />
</template>
<style>
.task-surface-switcher.task-workspace-part {
  width: 108px;
}
</style>
