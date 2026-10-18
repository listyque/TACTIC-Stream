<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../../frame/FrameView.vue';
import { observeFrameSizes } from '../../../frame/resize.js';
import { appearance } from '../../../appearance.js';
import { t } from '../../../i18n.js';
import * as UI from '../../../../../src/tactic_stream/shared_ui/features/files/workspace/table.ui.mjs';

const props = defineProps({ view: String, rows: Array, focus: Object });
const emit = defineEmits(['select']);
const host = ref(null),
  width = ref(800);
const columns = computed(() => UI.columns(props.view, width.value));
const tableWidth = computed(() =>
  columns.value.reduce((sum, column) => sum + column.width, 0)
);
const selected = (row) =>
  props.view === 'files'
    ? !!props.focus && props.focus.path === row.path
    : !!props.focus && props.focus.code === row.code;
let observer;
onMounted(() => {
  observer = observeFrameSizes(
    (entries) => (width.value = entries.at(-1).contentRect.width - 16)
  );
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="host" class="workspace-table-scroll">
    <table
      :aria-label="
        t(
          view === 'history'
            ? 'Revisions'
            : view === 'streams'
              ? 'Streams'
              : view === 'workspaces'
                ? 'Workspaces'
                : view === 'tasks'
                  ? 'Transfers'
                  : 'Files'
        )
      "
      :style="{ width: tableWidth + 'px' }"
    >
      <colgroup>
        <col
          v-for="(column, index) in columns"
          :key="index"
          :style="{ width: column.width + 'px' }"
        />
      </colgroup>
      <thead>
        <tr>
          <th v-for="(column, index) in columns" :key="index">
            {{ t(column.title) }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, index) in rows"
          :key="row.path || row.code || row.task || index"
          tabindex="0"
          :aria-selected="selected(row)"
          @click="emit('select', row)"
          @keydown.enter="emit('select', row)"
          @keydown.space.prevent="emit('select', row)"
        >
          <td :colspan="columns.length">
            <FrameView
              :interactive="false"
              :scene="
                UI.row(
                  { view, row, selected: selected(row) },
                  width,
                  appearance.language
                )
              "
            />
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="!rows.length" class="muted">
      {{ t('No permitted records on this page') }}
    </p>
  </div>
</template>
<style scoped>
.workspace-table-scroll {
  position: relative;
  overflow: auto;
  scrollbar-gutter: stable;
  flex: 1;
  min-height: 0;
  padding-right: 4px;
}
table {
  table-layout: fixed;
  border-collapse: collapse;
}
th {
  text-align: left;
  height: 28px;
  padding: 0 8px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 400;
}
tbody tr,
td {
  height: 32px;
}
td {
  position: relative;
  padding: 0;
}
tr[aria-selected='true'] {
  background: var(--selected);
}
tr:hover {
  background: var(--hover);
}
tr[aria-selected='true']:hover {
  background: var(--selected);
}
</style>
