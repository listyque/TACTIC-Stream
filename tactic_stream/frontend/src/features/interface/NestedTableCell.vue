<script setup>
import TableCell from './TableCell.vue';
defineProps({ frameNode: Object });
defineEmits(['action', 'inspect', 'cell-event']);
</script>
<template>
  <div
    class="handler-table-cell nested-table-cell"
    :class="{ 'first-column': frameNode.column.index === 0 }"
  >
    <TableCell
      :element="frameNode.column"
      :record="frameNode.record"
      :cell="frameNode.cell"
      :height="frameNode.height"
      :editable="true"
      :inspectable="true"
      :selected="frameNode.selected"
      @inspect="$emit('inspect', frameNode.record)"
      @select="$emit('action', frameNode.record, 'nested-select', {}, null)"
      @preview="
        (...args) => $emit('cell-event', 'preview', frameNode.record, args)
      "
      @notes="(...args) => $emit('cell-event', 'notes', frameNode.record, args)"
      @tasks="(...args) => $emit('cell-event', 'tasks', frameNode.record, args)"
      @task-edit="
        (...args) => $emit('cell-event', 'task-edit', frameNode.record, args)
      "
      @action="
        (kind, cell, anchor) =>
          $emit('action', frameNode.record, kind, cell, anchor)
      "
    />
  </div>
</template>
<style scoped>
.nested-table-cell {
  width: 100%;
  height: 100%;
}
</style>
