<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import NestedTable from './NestedTable.vue';
import LayoutDocument from './LayoutDocument.vue';
import DashboardItems from './DashboardItems.vue';
import { appearance } from '../../appearance.js';
import { runTableScript } from './tableScript.js';
import { printCustomReport } from './customReport.js';
import { rpc } from '../../api.js';
import * as Layout from '../../../../src/tactic_stream/shared_ui/features/table/layout.ui.mjs';
import * as Canvas from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/canvas.mjs';
import CanvasSelection from '../administration/CanvasSelection.vue';
const props = defineProps({
  model: Object,
  frameNode: Object,
  ticket: String,
  project: String,
  width: Number,
  height: Number,
  tabs: Array,
  currentKey: String,
  selectedKeys: Array,
  workspaceId: String,
  active: { type: Boolean, default: true },
  editing: Boolean,
  guides: { type: Boolean, default: true },
  selectedBlock: String
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
  'close-tab',
  'select',
  'focus',
  'operate',
  'loaded',
  'block',
  'geometry'
]);
const state = ref({}),
  tables = ref({}),
  detail = ref({}),
  busy = ref(false),
  error = ref('');
let generation = 0,
  abort;
let detailGeneration = 0;
const baseScene = computed(() =>
  Layout.describe(
    {
      ...props.model,
      layoutTables: tables.value,
      layoutDetail: props.editing
        ? props.model.layoutDetail || {}
        : detail.value,
      layoutTabs: props.tabs || props.model.layoutTabs,
      layoutTabKey: props.currentKey || props.model.layoutTabKey,
      layoutState: state.value,
      layoutBusy: busy.value,
      layoutError: error.value
    },
    props.frameNode?.width ?? props.width,
    props.frameNode?.height ?? props.height,
    appearance.language,
    true,
    location.origin
  )
);
const scene = computed(() =>
  props.editing && props.guides
    ? Canvas.decorate(baseScene.value, 'editorPath')
    : baseScene.value
);
const views = computed(() => ({
  canvasOverlay: {
    component: CanvasSelection,
    props: {
      boxes: scene.value.canvasBoxes || [],
      selected: props.selectedBlock,
      onSelect: (key) => emit('block', key),
      onCommit: (value) =>
        emit('geometry', value, scene.value.canvasBoxes || [])
    }
  },
  layoutItems: {
    component: DashboardItems,
    nodeProps: true,
    props: {
      editing: props.editing,
      inert: props.editing ? true : undefined,
      ticket: props.ticket,
      project: props.project,
      selectedKeys: props.selectedKeys,
      workspaceId: props.workspaceId,
      active: props.active,
      onLoaded: (value) => emit('loaded', value),
      onInspect: (record) => emit('inspect', record),
      onOperate: (...args) => emit('operate', ...args),
      onSelect: (...args) => emit('select', ...args),
      onFocus: focusItem
    }
  },
  layoutMarkdown: {
    component: LayoutDocument,
    nodeProps: true,
    props: { inert: props.editing ? true : undefined }
  },
  layoutTable: {
    component: NestedTable,
    nodeProps: true,
    props: {
      inert: props.editing ? true : undefined,
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
async function focusItem(value) {
  if (props.editing) return;
  emit('focus', value);
  if (!props.model.layoutItems || !Layout.hasDetails(props.model.layoutNodes))
    return;
  if (value?.kind === 'branch') return;
  const key = value?.record?.__search_key__;
  if (key && key === detail.value.targetSearchKey) return;
  const request = ++detailGeneration;
  detail.value = { busy: !!key, targetSearchKey: key };
  for (const name of Object.keys(tables.value))
    if (name.startsWith('customLayoutDetails_')) delete tables.value[name];
  if (!key) return;
  try {
    const result = await rpc('execute_cmd', [
      { ticket: props.ticket, project: props.project },
      'tactic.ui.table.CustomLayoutReadCmd',
      {
        view: props.model.layoutView,
        search_key: props.model.targetSearchKey,
        detail_key: key
      }
    ]);
    if (request !== detailGeneration) return;
    for (const item of Layout.tables(
      result.info.layoutNodes,
      'customLayoutDetails'
    ))
      tables.value[item.key] = {
        scope: item.scope,
        selected: [],
        rows: [],
        columns: [],
        offset: 0,
        selection: item.scope.selection
      };
    detail.value = result.info;
  } catch (failure) {
    if (request === detailGeneration) detail.value = { error: failure.message };
  }
}
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
  if (props.editing) return;
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
    ++detailGeneration;
    detail.value = {};
    abort?.abort();
    busy.value = false;
    error.value = '';
    state.value = Layout.initial(props.model);
    tables.value = Object.fromEntries(
      Layout.tables(props.model.layoutNodes)
        .concat(
          props.editing
            ? Layout.tables(
                props.model.layoutDetail?.layoutNodes,
                'customLayoutDetails'
              )
            : []
        )
        .map((item) => [
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
  ++detailGeneration;
  abort?.abort();
});
defineExpose({ tables, state });
</script>
<template>
  <FrameView :scene="scene" :views="views" @event="activate" />
</template>
