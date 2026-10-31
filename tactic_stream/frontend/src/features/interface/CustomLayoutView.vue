<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { qtLabelTextWidth } from '../../controls/typography/textMetrics.js';
import NestedTable from './NestedTable.vue';
import LayoutDocument from './LayoutDocument.vue';
import DashboardItems from './DashboardItems.vue';
import PageFilterSearch from './PageFilterSearch.vue';
import { appearance } from '../../appearance.js';
import { runTableScript } from './tableScript.js';
import { layoutUrl } from './itemLayout.js';
import { printCustomReport } from './customReport.js';
import { rpc } from '../../api.js';
import { copyText } from '../../controls/clipboard.js';
import * as Parts from '../../../../src/tactic_stream/shared_ui/features/table/record.parts.mjs';
import * as Layout from '../../../../src/tactic_stream/shared_ui/features/table/layout.ui.mjs';
import * as Report from '../../../../src/tactic_stream/shared_ui/features/table/report.ui.mjs';
import * as Filters from '../../../../src/tactic_stream/shared_ui/features/table/page.filters.mjs';
import * as Canvas from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/canvas.mjs';
import CanvasSelection from '../administration/CanvasSelection.vue';
import * as Viewport from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/page.viewport.mjs';
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
  filterBusy: Boolean,
  editing: Boolean,
  guides: { type: Boolean, default: true },
  selectedBlock: String,
  selectedBlocks: Array,
  multiSelect: Boolean,
  snap: Boolean,
  canvasViewport: Object
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
  'geometry',
  'selection',
  'canvasBoxes',
  'filter-apply'
]);
const state = ref({}),
  tables = ref({}),
  detail = ref({}),
  busy = ref(false),
  error = ref('');
const filterDraft = ref({}),
  forms = ref({}),
  localNodes = ref(null);
let generation = 0,
  abort;
let detailGeneration = 0;
const baseScene = computed(() =>
  Layout.describe(
    {
      ...props.model,
      layoutForms: forms.value,
      layoutNodes: localNodes.value || props.model.layoutNodes,
      layoutTables: tables.value,
      layoutDetail: props.editing
        ? props.model.layoutDetail || {}
        : detail.value,
      layoutTabs: props.tabs || props.model.layoutTabs,
      layoutTabKey: props.currentKey || props.model.layoutTabKey,
      layoutState: state.value,
      layoutBusy: busy.value,
      layoutFilterDraft: filterDraft.value,
      layoutEditing: props.editing,
      layoutDesigning: props.editing && props.guides,
      layoutFilterBusy: props.filterBusy,
      layoutError: error.value
    },
    canvasSize.value.width - (props.canvasViewport ? 24 : 0),
    Math.max(1, canvasSize.value.height - (props.canvasViewport ? 24 : 0)),
    appearance.language,
    true,
    location.origin,
    (text, size, weight = 400) =>
      qtLabelTextWidth(text, `${weight} ${size}px Segoe UI`)
  )
);
const canvasSize = computed(() =>
  props.canvasViewport
    ? Viewport.dimensions(
        props.canvasViewport,
        props.frameNode?.width ?? props.width,
        props.frameNode?.height ?? props.height
      )
    : {
        width: props.frameNode?.width ?? props.width,
        height: props.frameNode?.height ?? props.height,
        scale: 1
      }
);
const scene = computed(() => {
  const document =
    props.editing && props.guides
      ? Canvas.decorate(baseScene.value, 'editorPath')
      : baseScene.value;
  return props.canvasViewport
    ? Viewport.describe(
        document,
        props.canvasViewport,
        props.frameNode?.width ?? props.width,
        props.frameNode?.height ?? props.height
      )
    : document;
});
watch(
  () => scene.value.canvasBoxes,
  (boxes) => emit('canvasBoxes', boxes || []),
  { immediate: true }
);
const views = computed(() => ({
  pageFilterSearch: {
    component: PageFilterSearch,
    props: {
      model: props.model,
      values: filterDraft.value,
      ticket: props.ticket,
      project: props.project,
      disabled: props.editing || props.filterBusy || !props.active,
      onApply: (values) => {
        filterDraft.value = values;
        emit('filter-apply', values);
      }
    }
  },
  canvasOverlay: {
    component: CanvasSelection,
    props: {
      boxes: scene.value.canvasBoxes || [],
      selected: props.selectedBlock,
      selection: props.selectedBlocks,
      multiple: !!props.canvasViewport,
      multiSelect: props.multiSelect,
      snap: props.snap,
      onSelection: (keys) => emit('selection', keys),
      scale: canvasSize.value.scale,
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
async function focusItem(value, force = false) {
  if (props.editing) return;
  if (!force) emit('focus', value);
  if (!props.model.layoutItems || !Layout.hasDetails(props.model.layoutNodes))
    return;
  if (value?.kind === 'branch') return;
  const key = value?.record?.__search_key__;
  if (!force && key && key === detail.value.targetSearchKey) return;
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
        detail_key: key,
        filter_values: props.model.layoutFilterValues
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
async function saveForm(action) {
  const request = generation,
    selected = detailGeneration;
  const result = Parts.change(
    forms.value,
    {
      ...props.model,
      layoutNodes: localNodes.value || props.model.layoutNodes,
      layoutDetail: detail.value
    },
    action
  );
  forms.value = result.store;
  if (!result.command) return;
  try {
    const response = (
      await rpc('execute_cmd', [
        { ticket: props.ticket, project: props.project },
        'tactic.ui.panel.dashboard_form_cmd.DashboardFormCmd',
        result.command
      ])
    ).info;
    if (request !== generation) return;
    forms.value = Parts.settled(forms.value, action.key, response);
    if (response.model) {
      if (result.command.detail_key) {
        if (selected === detailGeneration) detail.value = response.model;
      } else localNodes.value = response.model.layoutNodes;
    }
  } catch (failure) {
    if (request === generation)
      forms.value = Parts.settled(forms.value, action.key, null, {
        message: failure.message,
        uncertain: !failure.status || failure.status >= 500
      });
  }
}
function activate(action, source) {
  if (props.editing) return;
  if (action.type === 'layout-split') {
    state.value = Layout.resize(state.value, action);
    return;
  }
  if (action.type === 'record-form') {
    saveForm(action).catch((failure) => (error.value = failure.message));
    return;
  }
  if (action.type === 'record-action') {
    if (action.name === 'layout-link') {
      const href = layoutUrl(action.href);
      if (href)
        window.open(
          href,
          href.startsWith('/') ? '_self' : '_blank',
          'noopener'
        );
      return;
    }
    if (action.name === 'copy_link') {
      copyText('skey://' + action.targetSearchKey).catch(
        (failure) => (error.value = failure.message)
      );
      return;
    }
    if (action.name === 'refresh') {
      if (props.model.layoutItems && action.targetSearchKey)
        focusItem({ record: { __search_key__: action.targetSearchKey } }, true);
      else emit('filter-apply', props.model.layoutFilterValues || {});
      return;
    }
    emit(
      'action',
      action.record || { __search_key__: action.targetSearchKey },
      action.name === 'details' ? 'sobject_detail' : action.name,
      {
        targetSearchKey: action.targetSearchKey,
        actionView: action.view,
        process: action.process,
        command: action.command
      },
      {
        currentTarget: source,
        target: source,
        preventDefault() {},
        clientX: source?.getBoundingClientRect()?.left,
        clientY: source?.getBoundingClientRect()?.bottom
      }
    );
    return;
  }
  if (action.type === 'page-filter') {
    filterDraft.value = Filters.change(filterDraft.value, action);
    return;
  }
  if (action.type === 'page-filter-remove') {
    filterDraft.value = Filters.change(filterDraft.value, {
      name: action.name,
      field: 'enabled',
      value: false
    });
    emit(
      'filter-apply',
      Filters.values(props.model.layoutFilters, filterDraft.value)
    );
    return;
  }
  if (['page-filter-apply', 'page-filter-reset'].includes(action.type)) {
    try {
      const values =
        action.type === 'page-filter-reset'
          ? {}
          : Filters.values(props.model.layoutFilters, filterDraft.value);
      emit('filter-apply', values);
      error.value = '';
    } catch (failure) {
      error.value = failure.message;
    }
    return;
  }
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
    forms.value = Parts.interrupted(forms.value);
    localNodes.value = null;
    filterDraft.value = Filters.initial(props.model.layoutFilters);
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
watch(
  () =>
    JSON.stringify([
      props.ticket,
      props.project,
      props.model.layoutView,
      props.model.targetSearchKey
    ]),
  () => {
    forms.value = {};
  }
);
onBeforeUnmount(() => {
  ++generation;
  ++detailGeneration;
  abort?.abort();
});
defineExpose({ tables, state });
</script>
<template>
  <FrameView
    :scene="scene"
    :views="views"
    :models="
      Report.models({
        ...model,
        layoutDetail: editing ? model.layoutDetail : detail
      })
    "
    :describe-cell="Report.cell"
    @event="activate"
  />
</template>
