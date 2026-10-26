<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import NestedTable from './NestedTable.vue';
import LayoutDocument from './LayoutDocument.vue';
import DashboardTree from './DashboardTree.vue';
import { appearance } from '../../appearance.js';
import { runTableScript } from './tableScript.js';
import { printCustomReport } from './customReport.js';
import * as Layout from '../../../../src/tactic_stream/shared_ui/features/table/layout.ui.mjs';
const props = defineProps({
  model: Object,
  ticket: String,
  project: String,
  width: Number,
  height: Number,
  tabs: Array,
  currentKey: String
});
const emit = defineEmits([
  'action',
  'edit',
  'inspect',
  'cell-event',
  'column',
  'close',
  'saved',
  'notice',
  'print',
  'tab',
  'close-tab'
]);
const state = ref({}),
  tables = ref({}),
  busy = ref(false),
  error = ref('');
let generation = 0,
  abort;
const scene = computed(() =>
  Layout.describe(
    {
      ...props.model,
      layoutTables: tables.value,
      layoutTabs: props.tabs || props.model.layoutTabs,
      layoutTabKey: props.currentKey || props.model.layoutTabKey,
      layoutState: state.value,
      layoutBusy: busy.value,
      layoutError: error.value
    },
    props.width,
    props.height,
    appearance.language,
    true,
    location.origin
  )
);
const views = computed(() => ({
  layoutTree: {
    component: DashboardTree,
    nodeProps: true,
    props: { ticket: props.ticket, project: props.project, onAction: activate }
  },
  layoutMarkdown: {
    component: LayoutDocument,
    nodeProps: true
  },
  layoutTable: {
    component: NestedTable,
    nodeProps: true,
    props: {
      ticket: props.ticket,
      project: props.project,
      parentState: { children: tables.value },
      onEdit: (...args) => emit('edit', ...args),
      onInspect: (record) => emit('inspect', record),
      onAction: (...args) => emit('action', ...args),
      onCellEvent: (...args) => emit('cell-event', ...args),
      onColumn: (value) => emit('column', value)
    }
  }
}));
async function run(source, selector = '') {
  if (busy.value || !source) return;
  const request = generation;
  busy.value = true;
  error.value = '';
  abort = new AbortController();
  try {
    const result = await runTableScript(
      source,
      {
        project: props.project,
        searchKey: props.model.targetSearchKey,
        searchType: props.model.targetSearchKey.split('?')[0],
        view: props.model.layoutView,
        record: props.model.record || {},
        layoutState: state.value,
        layoutTrigger: selector,
        layoutUser: props.model.layoutUser
      },
      {
        ticket: props.ticket,
        signal: abort.signal,
        confirm: () => {
          throw new Error(
            'This layout action requires an explicit confirmation control'
          );
        }
      }
    );
    if (request !== generation) return;
    for (const command of result.commands) {
      if (command.type === 'layout-state') state.value = command.state;
      else if (command.type === 'close-layout') {
        emit('saved');
        emit('close');
      } else if (command.type === 'print-layout')
        await printCustomReport(props.model, props.ticket, props.project);
      else if (command.type === 'refresh') {
        for (const table of Object.values(tables.value))
          table.revision = (table.revision || 0) + 1;
        emit('saved');
      } else if (['message', 'log'].includes(command.type))
        emit('notice', command.text);
      else throw new Error('Unsupported layout command: ' + command.type);
    }
  } catch (failure) {
    if (request === generation) error.value = failure.message;
  } finally {
    if (request === generation) busy.value = false;
  }
}
function activate(action) {
  if (action.type === 'layout-tab') emit('tab', action.key);
  else if (action.type === 'layout-close-tab') emit('close-tab', action.key);
  else if (action.type === 'layout-change')
    state.value = Layout.change(state.value, action.selector, action.value);
  else if (action.name === 'script') run(action.javascript, action.selector);
  else
    emit('action', props.model.record, action.name, {
      ...props.model,
      href: action.href
    });
}
watch(
  () => [props.model, props.ticket, props.project],
  () => {
    ++generation;
    abort?.abort();
    busy.value = false;
    error.value = '';
    state.value = Layout.initial(props.model);
    tables.value = Object.fromEntries(
      Layout.tables(props.model.layoutNodes).map((item) => [
        item.key,
        {
          scope: item.scope,
          selected: [],
          rows: [],
          columns: [],
          offset: 0,
          selection: item.scope.selection
        }
      ])
    );
    run(
      (props.model.layoutLoad || []).map((item) => item.javascript).join('\n')
    );
  },
  { immediate: true }
);
onBeforeUnmount(() => {
  ++generation;
  abort?.abort();
});
defineExpose({ tables, state });
</script>
<template>
  <FrameView :scene="scene" :views="views" @event="activate" />
</template>
