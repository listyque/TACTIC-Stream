<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { rpc } from '../../api.js';
import { appearance } from '../../appearance.js';
import WorkspaceSearch from '../workspace/WorkspaceSearch.vue';
import ConfiguredTable from './ConfiguredView.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/table/nested.ui.mjs';

const props = defineProps({
  ticket: String,
  project: String,
  state: Object,
  parentState: Object,
  frameNode: Object,
  ancestors: { type: Array, default: () => [] }
});
const emit = defineEmits([
  'close',
  'edit',
  'action',
  'inspect',
  'cell-event',
  'column'
]);
const host = ref(null),
  width = ref(props.frameNode?.width || 1);
let observer,
  generation = 0;
const model = computed(
  () => props.state || props.parentState.children[props.frameNode.key]
);
const tableRecords = computed(() =>
  (model.value.rows || []).map((row) => row.record)
);
const tableCells = computed(() =>
  Object.fromEntries(
    (model.value.rows || []).map((row) => [row.key, row.cells])
  )
);
const records = computed(() =>
  UI.rows({ ...model.value.scope, ...model.value }, width.value, extent.value)
);
const extent = computed(
  () => props.frameNode?.height || UI.extent(model.value, width.value)
);
const scene = computed(() =>
  UI.describe(
    { ...model.value.scope, ...model.value },
    width.value,
    extent.value,
    appearance.language
  )
);
const searchScope = computed(() => ({
  parent_key: model.value.scope.parentKey,
  view: model.value.scope.view || 'table',
  project_scope: model.value.scope.projectScope === true,
  filters: model.value.scope.filters || [],
  expression: model.value.scope.expression || '',
  search_view: model.value.scope.searchView || '',
  simple_view: model.value.scope.simpleSearchView || '',
  simple_values: model.value.simpleValues || {}
}));
function search(text = model.value.filter || '', relation = 'EQI') {
  model.value.filter = text;
  model.value.searchQuery = text;
  model.value.searchRelation = relation;
  model.value.offset = 0;
  load();
}
const views = computed(() => ({
  tableSearch: {
    component: WorkspaceSearch,
    props: {
      modelValue: model.value.filter || '',
      label: 'Search objects',
      ticket: props.ticket,
      project: model.value.scope.projectCode || props.project,
      searchType: model.value.scope.searchType,
      scope: searchScope.value,
      'onUpdate:modelValue': (value) => {
        model.value.filter = value;
      },
      onSearch: () => search(),
      onAccept: (record) => search(record.title, '='),
      onOpen: (record) => search(record.title, '=')
    }
  },
  tableBody: {
    component: ConfiguredTable,
    props: {
      ticket: props.ticket,
      project: model.value.scope.projectCode || props.project,
      definition: model.value.definition,
      rows: tableRecords.value,
      preparedCells: tableCells.value,
      readOnly: false,
      embedded: true,
      nestedAncestors: [
        ...props.ancestors,
        UI.identity(model.value.scope, props.project)
      ],
      nestedTables: (model.value.children ||= {}),
      parentKey: model.value.scope.parentKey,
      selectionEnabled: model.value.scope.selection !== false,
      selectedKeys: model.value.selected || [],
      resultState: {
        ...model.value.resultState,
        table: { autoFit: true, ...model.value.resultState?.table }
      },
      sortField: (model.value.order || '').split(' ')[0],
      sortDirection: (model.value.order || '').split(' ')[1] || 'asc',
      onSelect: (records, selected) => {
        if (!records.length && !selected) {
          model.value.selected = [];
          model.value.selectionRecords = {};
          return;
        }
        const keys = new Set(model.value.selected || []);
        model.value.selectionRecords ||= {};
        for (const record of records) {
          if (selected) {
            keys.add(record.__search_key__);
            model.value.selectionRecords[record.__search_key__] = {
              code: record.code
            };
          } else {
            keys.delete(record.__search_key__);
            delete model.value.selectionRecords[record.__search_key__];
          }
        }
        if (keys.size > 500) {
          model.value.error = 'Choose at most 500 table records';
          return;
        }
        model.value.selected = [...keys];
      },
      onSort: (value, direction) =>
        activate({ type: 'sort', value, direction }),
      onResultState: (value) => {
        model.value.resultState = value;
        if (value.table?.view && value.table.view !== model.value.scope.view) {
          model.value.scope.view = value.table.view;
          load();
        }
      },
      onInspect: (record) => emit('inspect', record),
      onColumn: (request) => {
        model.value.loaded = false;
        emit('column', request);
      },
      onDirtyTasks: (count) => {
        model.value.dirtyTaskCount = count;
      },
      onSaved: load
    }
  }
}));
function row(list, record) {
  return UI.row(
    { ...model.value.scope, ...model.value },
    record,
    appearance.language,
    list.width - 16
  );
}
async function load() {
  const request = ++generation,
    state = model.value,
    scope = state.scope;
  state.busy = true;
  state.error = '';
  const query = {
    parent_key: scope.parentKey,
    search_type: scope.searchType,
    view: scope.view || 'table',
    search_view: scope.searchView || '',
    project_scope: scope.projectScope === true,
    simple_view: scope.simpleSearchView || '',
    simple_values: state.simpleValues || {},
    expression: scope.expression || '',
    offset: state.offset || 0,
    limit: scope.initialLimit || 50,
    order_by: state.order ? [state.order] : [],
    filters: [...(scope.filters || [])],
    keyword: state.searchQuery || '',
    keyword_relation: state.searchRelation || 'EQI'
  };
  try {
    const response = await rpc('execute_cmd', [
      {
        ticket: props.ticket,
        project: scope.projectCode || props.project,
        language: 'python'
      },
      'tactic.ui.table.NestedTableReadCmd',
      query
    ]);
    const result = response.info;
    if (request !== generation || state !== model.value) return;
    const definition = {
      ...result.definition,
      search_type: scope.searchType,
      table: { ...result.definition.table, view: scope.view || 'table' }
    };
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
          undefined,
        sortable: !!element.cell?.sortable,
        field: element.cell?.field || element.name
      }));
    state.rows = result.records.map((record) => ({
      key: record.__search_key__,
      record,
      cells: result.cells[record.__search_key__] || {}
    }));
    state.selectionRecords ||= {};
    for (const record of result.records)
      if ((state.selected || []).includes(record.__search_key__))
        state.selectionRecords[record.__search_key__] = { code: record.code };
    state.hasNext = result.hasNext;
    state.simpleFilters = result.simpleFilters || [];
    state.insert = scope.insert !== false && !!definition.operations.create;
    state.gear = scope.gear !== false && !!definition.administration;
    state.filterField =
      ['name', 'title', 'file_name', 'code'].find(
        (name) => definition.columns[name]
      ) || 'id';
    state.loaded = true;
  } catch (error) {
    if (request === generation) state.error = error.message;
  } finally {
    if (request === generation) state.busy = false;
  }
}
function activate(action, source) {
  const state = model.value;
  if (action.type === 'close') emit('close', props.frameNode?.key);
  else if (action.type === 'gallery-open') {
    const record = state.rows.find((row) => row.key === action.key)?.record;
    if (record)
      emit('action', record, 'file-checkout', {
        targetSearchKey: action.key,
        projectCode: state.scope.projectCode || props.project
      });
  } else if (action.type === 'filter')
    state.filter = String(action.value ?? '');
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
  } else if (action.type === 'columns') {
    if (!state.gear) return;
    // Administration can unmount the retained table before its save event.
    state.loaded = false;
    emit('column', {
      project: state.scope.projectCode || props.project,
      searchType: state.scope.searchType.split('?')[0],
      view: state.scope.view || 'table',
      column: action.column || '',
      target: 'definition'
    });
  } else if (action.type === 'edit' || action.type === 'create')
    emit(
      'edit',
      state.rows?.find((row) => row.key === action.key)?.record || null,
      state
    );
  else {
    if (state.busy) return;
    if (action.type === 'page')
      state.offset = Math.max(
        0,
        (state.offset || 0) + action.value * (state.scope.initialLimit || 50)
      );
    else {
      state.offset = 0;
      if (action.type === 'simple-filter')
        state.simpleValues = {
          ...state.simpleValues,
          [action.field]: action.value
        };
      if (action.type === 'sort')
        state.order =
          action.value +
          ' ' +
          (action.direction ||
            (state.order === action.value + ' asc' ? 'desc' : 'asc'));
    }
    load();
  }
}
watch(
  () => [props.ticket, props.project, model.value],
  () => {
    ++generation;
    if (!model.value.loaded) load();
  }
);
watch(() => model.value.revision, load);
watch(
  () => props.frameNode?.width,
  (value) => {
    if (value > 0) width.value = value;
  }
);
function definitionSaved({ detail }) {
  const scope = model.value.scope;
  if (
    detail.project === (scope.projectCode || props.project) &&
    [scope.searchType.split('?')[0], 'ALL'].includes(detail.searchType) &&
    [scope.view || 'table', 'definition'].includes(detail.view)
  )
    load();
}
onMounted(() => {
  window.addEventListener('tactic-column-definition-saved', definitionSaved);
  width.value = host.value.clientWidth;
  observer = observeFrameSizes(
    (entries) => (width.value = entries[0].contentRect.width)
  );
  observer.observe(host.value);
  if (!model.value.loaded) load();
});
onBeforeUnmount(() => {
  window.removeEventListener('tactic-column-definition-saved', definitionSaved);
  ++generation;
  model.value.busy = false;
  observer?.disconnect();
});
defineExpose({ reload: load });
</script>

<template>
  <div
    ref="host"
    class="nested-table"
    :style="{
      height: extent + 'px',
      background: model.scope?.embedded ? 'transparent' : 'var(--surface)'
    }"
    @click.stop
    @dblclick.stop
    @contextmenu.stop
  >
    <FrameView
      :scene="scene"
      :models="{ rows: records }"
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
