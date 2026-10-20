<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { rpc } from '../../api.js';
import { appearance } from '../../appearance.js';
import NestedTableCell from './NestedTableCell.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/table/nested.ui.mjs';

const props = defineProps({ ticket: String, project: String, state: Object });
const emit = defineEmits(['close', 'edit', 'action', 'inspect', 'cell-event']);
const host = ref(null),
  width = ref(1);
let observer,
  generation = 0;
const model = computed(() => props.state);
const scene = computed(() =>
  UI.describe(model.value, width.value, UI.height, appearance.language)
);
const views = computed(() => ({
  tableCell: {
    component: NestedTableCell,
    nodeProps: true,
    props: {
      onAction: forward,
      onInspect: (record) => emit('inspect', record),
      onCellEvent: (...args) => emit('cell-event', ...args)
    }
  }
}));
function forward(record, kind, cell, anchor) {
  if (kind === 'nested-table')
    props.state.error = 'Recursive nested tables are not available yet.';
  else if (kind === 'nested-select')
    activate({ type: 'select', key: record.__search_key__ });
  else
    emit(
      'action',
      record,
      kind,
      {
        ...cell,
        tableScope: {
          view: props.state.scope.view || 'table',
          searchKeys: [...(props.state.selected || [])],
          records: {
            ...props.state.selectionRecords,
            ...Object.fromEntries(
              (props.state.rows || []).map((row) => [
                row.key,
                { code: row.record.code }
              ])
            )
          }
        }
      },
      anchor
    );
}
function row(_node, record) {
  return UI.row(model.value, record, appearance.language);
}
async function load() {
  const request = ++generation,
    state = props.state,
    scope = state.scope;
  state.busy = true;
  state.error = '';
  const query = {
    parent_key: scope.parentKey,
    search_type: scope.searchType,
    view: scope.view || 'table',
    expression: scope.expression || '',
    offset: state.offset || 0,
    limit: 50,
    order_by: state.order ? [state.order] : [],
    filters: []
  };
  if (state.filter)
    query.filters = [
      [state.filterField || 'code', 'like', '%' + state.filter + '%']
    ];
  try {
    const response = await rpc('execute_cmd', [
      { ticket: props.ticket, project: props.project, language: 'python' },
      'tactic.ui.table.NestedTableReadCmd',
      query
    ]);
    const result = response.info;
    if (request !== generation || state !== props.state) return;
    const definition = result.definition;
    state.definition = definition;
    state.columns = definition.table.elements
      .filter((element) => !element.hidden)
      .map((element) => ({
        ...element,
        supported: element.cell?.supported,
        title: element.title || element.name,
        width:
          Number.parseFloat(element.attributes?.width) ||
          result.cells[result.records[0]?.__search_key__]?.[element.name]
            ?.widthHint ||
          160,
        sortable: !!element.cell?.sortable,
        field: element.cell?.field || element.name
      }));
    state.rows = result.records.map((record) => ({
      key: record.__search_key__,
      record,
      cells: result.cells[record.__search_key__] || {}
    }));
    state.hasNext = result.hasNext;
    state.insert = scope.insert !== false && !!definition.operations.create;
    state.filterField =
      ['name', 'title', 'code'].find((name) => definition.columns[name]) ||
      'id';
    state.loaded = true;
  } catch (error) {
    if (request === generation) state.error = error.message;
  } finally {
    if (request === generation) state.busy = false;
  }
}
function activate(action, value) {
  const state = props.state;
  if (action.type === 'close') emit('close');
  else if (action.type === 'filter') state.filter = String(action.value ?? '');
  else if (action.type === 'clear-selection') {
    state.selected = [];
    state.selectionRecords = {};
  } else if (action.type === 'select') {
    const selected = (state.selected || []).includes(action.key);
    if (!selected && (state.selected || []).length >= 500) {
      state.error = 'Choose at most 500 table records';
      return;
    }
    state.selectionRecords ||= {};
    if (selected) delete state.selectionRecords[action.key];
    else
      state.selectionRecords[action.key] = {
        code: state.rows.find((row) => row.key === action.key)?.record.code
      };
    state.selected = selected
      ? state.selected.filter((key) => key !== action.key)
      : [...(state.selected || []), action.key];
  } else if (action.type === 'edit' || action.type === 'create')
    emit(
      'edit',
      state.rows?.find((row) => row.key === action.key)?.record || null,
      state
    );
  else {
    if (state.busy) return;
    if (action.type === 'page')
      state.offset = Math.max(0, (state.offset || 0) + action.value * 50);
    else {
      state.offset = 0;
      if (action.type === 'sort')
        state.order =
          action.value +
          (state.order === action.value + ' asc' ? ' desc' : ' asc');
    }
    load();
  }
}
watch(
  () => [props.ticket, props.project, props.state],
  () => {
    ++generation;
    if (!props.state.loaded) load();
  }
);
watch(() => props.state.revision, load);
onMounted(() => {
  observer = observeFrameSizes(
    (entries) => (width.value = entries[0].contentRect.width)
  );
  observer.observe(host.value);
  if (!props.state.loaded) load();
});
onBeforeUnmount(() => {
  ++generation;
  props.state.busy = false;
  observer?.disconnect();
});
defineExpose({ reload: load });
</script>

<template>
  <div
    ref="host"
    class="nested-table"
    :style="{ height: UI.height + 'px' }"
    @click.stop
    @dblclick.stop
    @contextmenu.stop
  >
    <FrameView
      :scene="scene"
      :models="{ rows: state.rows || [] }"
      :views="views"
      :describe-row="row"
      @event="activate"
    />
  </div>
</template>

<style scoped>
.nested-table {
  position: relative;
  width: 100%;
  min-width: 0;
}
</style>
