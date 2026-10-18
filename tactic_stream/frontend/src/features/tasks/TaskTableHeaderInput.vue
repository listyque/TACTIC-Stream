<script setup>
import AppButton from '../../controls/AppButton.vue';
import { t } from '../../i18n.js';
defineProps({ frameNode: Object, busy: Boolean, resizing: Object });
const emit = defineEmits([
  'sort',
  'context',
  'resize',
  'move',
  'finish',
  'resize-key'
]);
</script>
<template>
  <div
    class="task-table-header-input"
    :data-task-column="frameNode.column.sourceKey"
    @contextmenu.prevent="
      emit(
        'context',
        frameNode.column,
        $event.currentTarget.getBoundingClientRect()
      )
    "
  >
    <AppButton
      v-if="frameNode.column.sort"
      :label="frameNode.column.label"
      :disabled="busy"
      @click="emit('sort', frameNode.column.sort)"
    />
    <span
      class="task-column-resizer"
      role="separator"
      tabindex="0"
      :aria-label="t('Resize {column}', { column: t(frameNode.column.label) })"
      aria-orientation="vertical"
      :aria-valuenow="frameNode.column.width"
      aria-valuemin="40"
      aria-valuemax="480"
      @keydown="emit('resize-key', frameNode.column, $event)"
      @pointerdown="emit('resize', frameNode.column, $event)"
      @pointermove="emit('move', $event)"
      @pointerup="emit('finish', $event)"
      @pointercancel="emit('finish', $event)"
      @lostpointercapture="emit('finish', $event)"
    />
  </div>
</template>
<style>
.task-table-header-input > .app-button {
  width: 100%;
  height: 100%;
  min-height: 0;
  opacity: 0;
}
.task-table-header-input {
  position: relative;
}
</style>
