<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import TaskCell from './TaskCell.vue';
import { taskSummary } from '../../../../src/tactic_stream/shared_ui/features/table/cells.ui.mjs';
const props = defineProps({ cell: Object, height: Number, editable: Boolean });
const emit = defineEmits(['inspect', 'edit']);
const host = ref(null),
  width = ref(100);
const scene = computed(() =>
  taskSummary(props.cell?.tasks || [], width.value, props.height)
);
let observer;
onMounted(() => {
  observer = new ResizeObserver(
    (entries) => (width.value = entries[0].contentRect.width)
  );
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="host" class="table-task-summary">
    <FrameView
      v-if="cell?.summaryMode === 'minimal'"
      :scene="scene"
      :style="{ height: height + 'px' }"
      @event="emit('inspect', cell.tasks[$event.index])"
    />
    <TaskCell
      v-else
      :cell="cell"
      :height="height"
      :editable="editable"
      @inspect="emit('inspect', $event)"
      @edit="(task, field, bounds) => emit('edit', task, field, bounds)"
    />
  </div>
</template>
<style scoped>
.table-task-summary {
  display: flex;
  align-items: center;
  width: 100%;
  min-width: 0;
  height: 100%;
}
</style>
