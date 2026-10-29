<script setup>
// Handler SearchResultTable/Header: the owner supplies cells and native commands.
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch
} from 'vue';
import AppButton from '../../controls/AppButton.vue';
import AppCheckbox from '../../controls/AppCheckbox.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppIcon from '../../controls/AppIcon.vue';
import BusyIndicator from '../../controls/BusyIndicator.vue';
import { t } from '../../i18n.js';
import ActionRows from '../../controls/ActionRows.vue';
import { appearance } from '../../appearance.js';
import { cssRoles } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import * as Host from '../../../../src/tactic_stream/shared_ui/features/table/host.ui.mjs';
import * as Menus from '../../../../src/tactic_stream/shared_ui/features/table/menus.ui.mjs';
import FrameView from '../../frame/FrameView.vue';
import * as ParentUI from '../../../../src/tactic_stream/shared_ui/features/table/parent.ui.mjs';

const props = defineProps({
  columns: Array,
  groups: Array,
  selectedKeys: Array,
  selectable: Boolean,
  readOnly: Boolean,
  editable: Boolean,
  busy: Boolean,
  sortField: String,
  sortDirection: String,
  groupMode: String,
  state: Object,
  views: Array,
  closedGroups: Object,
  expandedRows: { type: Object, default: () => ({}) },
  cells: { type: Object, default: () => ({}) },
  accent: { type: String, default: 'var(--primary)' }
});
const emit = defineEmits([
  'state',
  'select',
  'focus',
  'inspect',
  'operate',
  'column',
  'sort',
  'group',
  'width',
  'move',
  'hide',
  'view',
  'save-view',
  'scroll',
  'toggle-group',
  'header-action',
  'create-child',
  'edit'
]);
const viewport = ref(null),
  saveDialog = ref(null),
  contextMenu = ref(null),
  columnContext = ref(null),
  width = ref(0),
  scrollTop = ref(0),
  viewportHeight = ref(600);
const overrides = ref({}),
  drag = ref(null),
  focusedKey = ref(''),
  anchorKey = ref(''),
  savingView = ref(false),
  viewName = ref('');
let observer, frame, resizeFrame;
const preferences = computed(() => props.state?.table || {});
const autoFit = computed(() => !!preferences.value.autoFit);
const layout = computed(() =>
  Host.describe(
    {
      columns: props.columns,
      overrides: overrides.value,
      autoFit: autoFit.value,
      rowHeight: preferences.value.rowHeight,
      automaticRowHeight: preferences.value.automaticRowHeight
    },
    width.value
  )
);
const columns = computed(() => layout.value.columns);
const contextIndex = computed(() =>
  columns.value.findIndex((column) => column.name === columnContext.value?.name)
);
const columnActions = computed(() =>
  Menus.columnActions(
    {
      column: columnContext.value,
      editable: props.editable,
      busy: props.busy,
      count: columns.value.length,
      index: contextIndex.value,
      sorted:
        !!columnContext.value &&
        props.sortField === columnContext.value.sortField,
      direction: props.sortDirection,
      group: props.groupMode || 'none',
      rowHeight: rowHeight.value,
      automaticRowHeight: preferences.value.automaticRowHeight
    },
    appearance.language
  )
);
const viewActions = computed(() =>
  Menus.viewActions(
    props.views || [],
    props.editable && !props.busy,
    appearance.language
  )
);
function columnWidth(column) {
  return (
    layout.value.cells.find((cell) => cell.name === column.name)?.width || 48
  );
}
const rowHeight = computed(() => layout.value.rowHeight);
const grid = computed(
  () =>
    `${Host.metrics.selection}px ${layout.value.cells.map((cell) => cell.width + 'px').join(' ')} minmax(${Host.metrics.actions}px,1fr)`
);
const tableWidth = computed(() => layout.value.width);
function columnCommand(command) {
  const column = columnContext.value;
  if (!column) return;
  if (command.startsWith('sort:'))
    emit(
      'sort',
      column.sortField,
      command === 'sort:ascending' ? 'asc' : 'desc'
    );
  else if (command === 'group' || command === 'ungroup')
    emit('group', command === 'group' ? 'column:' + column.name : 'none');
  else if (command === 'edit_definition' || command === 'columns')
    emit('column', command === 'columns' ? '' : column.name, 'definition');
  else if (command === 'remove') emit('hide', column.name);
  else if (command === 'left' || command === 'right') {
    const target =
      columns.value[contextIndex.value + (command === 'left' ? -1 : 1)];
    if (target) emit('move', column.name, target.name);
  } else if (command.startsWith('row_height:')) {
    const height = Number(command.split(':')[1]);
    preference(
      height
        ? { rowHeight: height, automaticRowHeight: false }
        : { automaticRowHeight: true }
    );
  }
}
function viewCommand(command) {
  if (command === 'configure') emit('column', '', 'definition');
  else if (command === 'save_as') savingView.value = true;
  else if (command.startsWith('select:'))
    emit('view', props.views[Number(command.split(':')[1])].view);
}
const records = computed(() =>
  (props.groups || []).flatMap((group) => group.records)
);
const entries = computed(() => {
  const rows = [];
  let offset = 0;
  for (const group of props.groups || []) {
    if (group.label) {
      const height = group.cell ? ParentUI.groupHeight : 38;
      rows.push({ group, key: 'group:' + group.key, top: offset, height });
      offset += height;
    }
    if (props.closedGroups?.[group.key]) continue;
    for (const record of group.records) {
      rows.push({
        record,
        key: record.__search_key__,
        top: offset,
        height: rowHeight.value
      });
      offset += rowHeight.value;
      if (props.expandedRows[record.__search_key__]?.open) {
        rows.push({
          detail: record,
          key: 'nested:' + record.__search_key__,
          top: offset,
          height: 320
        });
        offset += 320;
      }
    }
    if (group.label && group.records?.length) {
      const groupSummary = Host.summarize(
        columns.value,
        group.records,
        props.cells,
        'group_bottom'
      );
      if (groupSummary.hasSummary) {
        rows.push({
          summary: groupSummary.values,
          key: 'group-summary:' + group.key,
          top: offset,
          height: 36
        });
        offset += 36;
      }
    }
  }
  if (records.value.length) {
    const tableSummary = Host.summarize(
      columns.value,
      records.value,
      props.cells,
      'bottom'
    );
    if (tableSummary.hasSummary) {
      rows.push({
        summary: tableSummary.values,
        key: 'table-summary',
        top: offset,
        height: 38
      });
      offset += 38;
    }
  }
  return rows;
});
const contentHeight = computed(
  () => (entries.value.at(-1)?.top || 0) + (entries.value.at(-1)?.height || 0)
);
const verticalOverflow = computed(
  () => contentHeight.value + 37 > viewportHeight.value + 0.5
);
const horizontalOverflow = computed(() => tableWidth.value > width.value + 0.5);
const rendered = computed(() => {
  const first = Math.max(0, scrollTop.value - rowHeight.value * 2 - 37),
    last = scrollTop.value + viewportHeight.value + rowHeight.value * 2;
  let left = 0,
    right = entries.value.length;
  while (left < right) {
    const mid = (left + right) >>> 1;
    if (entries.value[mid].top + entries.value[mid].height < first)
      left = mid + 1;
    else right = mid;
  }
  const result = [];
  for (
    let index = left;
    index < entries.value.length && entries.value[index].top < last;
    index++
  )
    result.push({ ...entries.value[index], index });
  return result;
});
const allSelected = computed(
  () =>
    records.value.length &&
    records.value.every((record) =>
      props.selectedKeys?.includes(record.__search_key__)
    )
);
function preference(value) {
  emit('state', { ...props.state, table: { ...preferences.value, ...value } });
}
function scrolled() {
  if (!viewport.value.getClientRects().length) return;
  const top = viewport.value.scrollTop,
    left = viewport.value.scrollLeft;
  scrollTop.value = top;
  emit('scroll', { target: viewport.value });
  cancelAnimationFrame(frame);
  frame = requestAnimationFrame(() =>
    preference({ scrollTop: top, scrollLeft: left })
  );
}
function choose(record, event, toggle = false) {
  if (
    event.target.closest(
      'button,input,select,textarea,a,summary,[role="combobox"]'
    ) &&
    !toggle
  )
    return;
  const key = record.__search_key__;
  focusedKey.value = key;
  emit('focus', record);
  if (!props.selectable) return;
  if (!toggle && !event.shiftKey) {
    anchorKey.value = key;
    return;
  }
  if (event.type === 'contextmenu' && props.selectedKeys?.includes(key)) return;
  if (event.shiftKey && anchorKey.value) {
    const keys = records.value.map((record) => record.__search_key__),
      indices = [keys.indexOf(anchorKey.value), keys.indexOf(key)];
    if (indices.every((index) => index >= 0)) {
      if (!event.ctrlKey && !event.metaKey)
        emit('select', records.value, false);
      emit(
        'select',
        records.value.slice(Math.min(...indices), Math.max(...indices) + 1),
        true
      );
      return;
    }
  }
  anchorKey.value = key;
  if (toggle || event.ctrlKey || event.metaKey)
    emit('select', [record], !props.selectedKeys?.includes(key));
  else {
    emit(
      'select',
      records.value.filter((item) => item !== record),
      false
    );
    emit('select', [record], true);
  }
}
function rowDrag(record, event) {
  if (
    props.readOnly ||
    event.dataTransfer.types.includes('application/x-tactic-frame')
  )
    return;
  const key = record.__search_key__;
  const searchKeys = props.selectedKeys?.includes(key)
    ? props.selectedKeys
    : [key];
  event.dataTransfer.effectAllowed = 'move';
  event.dataTransfer.setData(
    'application/x-tactic-frame',
    JSON.stringify({
      searchType: key.split('?')[0],
      searchKeys
    })
  );
}
function rowKey(event) {
  if (event.target !== viewport.value) return;
  if (
    (event.ctrlKey || event.metaKey) &&
    event.key.toLowerCase() === 'a' &&
    props.selectable
  ) {
    event.preventDefault();
    emit('select', records.value, true);
    return;
  }
  const rows = entries.value.filter((row) => row.record),
    index = rows.findIndex((row) => row.key === focusedKey.value);
  if (['Enter', ' '].includes(event.key) && index >= 0) {
    event.preventDefault();
    if (event.key === 'Enter') emit('inspect', rows[index].record);
    else choose(rows[index].record, event, true);
    return;
  }
  if (
    !['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key) ||
    !rows.length
  )
    return;
  event.preventDefault();
  const next =
    event.key === 'Home'
      ? 0
      : event.key === 'End'
        ? rows.length - 1
        : Math.max(
            0,
            Math.min(
              rows.length - 1,
              index + (event.key === 'ArrowUp' ? -1 : 1)
            )
          );
  const row = rows[next];
  choose(row.record, event);
  if (row.top < viewport.value.scrollTop) viewport.value.scrollTop = row.top;
  else if (
    row.top + row.height + 37 >
    viewport.value.scrollTop + viewport.value.clientHeight
  )
    viewport.value.scrollTop =
      row.top + row.height + 37 - viewport.value.clientHeight;
}
function openColumn(column, event) {
  event.preventDefault();
  columnContext.value = column;
  contextMenu.value.openAt(event);
}
function resize(column, event) {
  if (!props.editable || props.busy) return;
  event.preventDefault();
  event.stopPropagation();
  const target = event.currentTarget;
  target.setPointerCapture(event.pointerId);
  const start = event.clientX,
    initial = columnWidth(column),
    previous = overrides.value;
  function move(pointer) {
    preference({ autoFit: false });
    overrides.value = {
      ...overrides.value,
      [column.name]: Host.boundedWidth(initial + pointer.clientX - start)
    };
  }
  function finish(pointer) {
    target.removeEventListener('pointermove', move);
    target.removeEventListener('pointerup', finish);
    target.removeEventListener('pointercancel', finish);
    if (pointer.type === 'pointercancel') overrides.value = previous;
    else if (overrides.value[column.name] !== undefined)
      emit('width', column.name, Math.round(overrides.value[column.name]));
  }
  target.addEventListener('pointermove', move);
  target.addEventListener('pointerup', finish);
  target.addEventListener('pointercancel', finish);
}
function resizeKey(column, event) {
  if (!props.editable || !['ArrowLeft', 'ArrowRight'].includes(event.key))
    return;
  event.preventDefault();
  const value = Host.boundedWidth(
    columnWidth(column) +
      (event.key === 'ArrowLeft' ? -1 : 1) * (event.shiftKey ? 16 : 8)
  );
  overrides.value = { ...overrides.value, [column.name]: value };
  preference({ autoFit: false });
  emit('width', column.name, value);
}
function beginMove(column, event) {
  if (
    !props.editable ||
    props.busy ||
    event.button !== 0 ||
    event.target.closest('.table-resize')
  )
    return;
  const target = event.currentTarget,
    start = event.clientX;
  let moved = false;
  target.setPointerCapture(event.pointerId);
  function move(pointer) {
    if (!moved && Math.abs(pointer.clientX - start) < 6) return;
    moved = true;
    const x =
      pointer.clientX -
      viewport.value.getBoundingClientRect().left +
      viewport.value.scrollLeft;
    const index = Host.dropIndex(layout.value.cells, x);
    drag.value = { source: column.name, target: columns.value[index]?.name };
  }
  function finish(pointer) {
    target.removeEventListener('pointermove', move);
    target.removeEventListener('pointerup', finish);
    target.removeEventListener('pointercancel', finish);
    if (
      pointer.type !== 'pointercancel' &&
      drag.value?.target &&
      drag.value.source !== drag.value.target
    )
      emit('move', drag.value.source, drag.value.target);
    drag.value = null;
  }
  target.addEventListener('pointermove', move);
  target.addEventListener('pointerup', finish);
  target.addEventListener('pointercancel', finish);
}
function moveKey(column, event) {
  if (!props.editable || !['ArrowLeft', 'ArrowRight'].includes(event.key))
    return;
  event.preventDefault();
  const index = columns.value.findIndex((item) => item.name === column.name),
    target = columns.value[index + (event.key === 'ArrowLeft' ? -1 : 1)];
  if (target) emit('move', column.name, target.name);
}
async function restore() {
  await nextTick();
  if (viewport.value) {
    viewport.value.scrollTop = preferences.value.scrollTop || 0;
    viewport.value.scrollLeft = preferences.value.scrollLeft || 0;
    scrollTop.value = viewport.value.scrollTop;
  }
}
watch(
  () => props.columns,
  () => {
    overrides.value = {};
    restore();
  }
);
watch(savingView, async (value) => {
  await nextTick();
  if (value) {
    saveDialog.value.showModal();
    saveDialog.value.querySelector('input')?.focus();
  } else saveDialog.value?.close();
});
onMounted(() => {
  observer = new ResizeObserver((entries) => {
    const bounds = entries[0].contentRect;
    cancelAnimationFrame(resizeFrame);
    // Column reflow can change automatic scrollbars; finish this observer batch first.
    resizeFrame = requestAnimationFrame(() => {
      const wasHidden = !width.value || !viewportHeight.value;
      width.value = bounds.width;
      viewportHeight.value = bounds.height;
      // A hidden retained table can lose its DOM offset without a scroll event.
      if (wasHidden && bounds.width && bounds.height) restore();
    });
  });
  observer.observe(viewport.value);
  restore();
});
onBeforeUnmount(() => {
  observer?.disconnect();
  cancelAnimationFrame(frame);
  cancelAnimationFrame(resizeFrame);
});
defineExpose({ viewport });
</script>

<template>
  <div
    ref="viewport"
    class="handler-table"
    :class="{
      'no-vertical-overflow': !verticalOverflow,
      'no-horizontal-overflow': !horizontalOverflow
    }"
    role="grid"
    :aria-label="t('Table')"
    :aria-rowcount="entries.length + 1"
    :aria-colcount="columns.length + 2"
    tabindex="0"
    :style="{
      '--table-columns': grid,
      '--table-row-height': rowHeight + 'px',
      '--table-accent': accent,
      '--table-header': 'var(' + cssRoles[Host.paint.header] + ')',
      '--table-header-text': 'var(' + cssRoles[Host.paint.headerText] + ')'
    }"
    @scroll="scrolled"
    @keydown="rowKey"
  >
    <div
      class="handler-table-header"
      role="row"
      :style="{ width: tableWidth + 'px' }"
    >
      <div class="handler-table-selection" role="columnheader">
        <AppCheckbox
          v-if="selectable"
          label="Select all rows"
          :model-value="!!allSelected"
          :indeterminate="
            !allSelected &&
            records.some((record) =>
              selectedKeys?.includes(record.__search_key__)
            )
          "
          @update:model-value="emit('select', records, $event)"
          ><span class="visually-hidden">{{
            t('Select all rows')
          }}</span></AppCheckbox
        >
      </div>
      <div
        v-for="column in columns"
        :key="column.name"
        class="handler-table-heading"
        role="columnheader"
        :aria-sort="
          sortField === column.sortField
            ? sortDirection === 'desc'
              ? 'descending'
              : 'ascending'
            : 'none'
        "
        :class="{
          dragging: drag?.source === column.name,
          'drop-target': drag?.target === column.name,
          grouped: groupMode === 'column:' + column.name
        }"
        :title="column.title"
        :aria-label="column.title"
        tabindex="0"
        @contextmenu="openColumn(column, $event)"
        @pointerdown="beginMove(column, $event)"
        @keydown="moveKey(column, $event)"
      >
        <AppButton
          v-if="Host.headerAction(column)"
          class="table-header-insert"
          :label="Host.headerAction(column).label || 'Create'"
          :icon="Host.headerAction(column).icon || 'add'"
          compact
          icon-only
          :disabled="readOnly || busy"
          @pointerdown.stop
          @click.stop="emit('header-action', Host.headerAction(column))"
        />
        <span v-else>{{ column.title }}</span>
        <AppIcon
          v-if="groupMode === 'column:' + column.name"
          name="group-items"
          class="table-group-indicator"
        />
        <span
          class="table-resize"
          role="slider"
          tabindex="0"
          :aria-label="t('Resize column') + ' ' + column.title"
          :aria-valuenow="Math.round(columnWidth(column))"
          aria-valuemin="48"
          aria-valuemax="640"
          @pointerdown="resize(column, $event)"
          @keydown.stop="resizeKey(column, $event)"
        />
      </div>
      <div class="handler-table-actions" role="columnheader">
        <BusyIndicator v-if="busy" />
        <AppButton
          v-show="!busy"
          label="Auto Fit columns"
          icon="fit-width"
          icon-only
          :aria-pressed="autoFit"
          :highlighted="autoFit"
          @click="preference({ autoFit: !autoFit })"
        />
        <AppMenu
          v-show="!busy"
          label="Table views and columns"
          icon="view-column"
          overlay
          :width="280"
          :disabled="busy"
        >
          <ActionRows :actions="viewActions" @triggered="viewCommand" />
        </AppMenu>
      </div>
    </div>
    <div
      class="handler-table-body"
      :style="{ height: contentHeight + 'px', width: tableWidth + 'px' }"
    >
      <div
        v-for="entry in rendered"
        :key="entry.key"
        class="handler-table-row"
        role="row"
        :aria-rowindex="entry.index + 2"
        :aria-selected="!!entry.record && (focusedKey === entry.key || selectedKeys?.includes(entry.key))"
        :class="{
          selected: selectedKeys?.includes(entry.key),
          active: !!entry.record && focusedKey === entry.key,
          'group-row': !!entry.group || !!entry.summary
        }"
        :style="{ top: entry.top + 'px', height: entry.height + 'px' }"
        :draggable="!!entry.record && !readOnly"
        @dragstart="entry.record && rowDrag(entry.record, $event)"
        @click="entry.record && choose(entry.record, $event)"
        @dblclick="
          entry.record &&
          !$event.target.closest('button,input,select,textarea,a') &&
          emit('inspect', entry.record)
        "
        @contextmenu="
          entry.record &&
          (choose(entry.record, $event), emit('operate', entry.record, $event))
        "
      >
        <div
          v-if="entry.detail"
          class="handler-table-detail"
          :style="{ width: width + 'px' }"
          @click.stop
          @dblclick.stop
          @contextmenu.stop
        >
          <slot name="detail" :record="entry.detail" />
        </div>
        <FrameView
          v-else-if="entry.group?.cell"
          class="handler-table-group"
          :scene="
            ParentUI.group(
              {
                cell: entry.group.cell,
                count: entry.group.records.length,
                closed: !!closedGroups?.[entry.group.key]
              },
              Math.max(0, width - 24),
              appearance.language,
              !readOnly,
              ''
            )
          "
          @event="
            (action) =>
              action.type === 'toggle'
                ? emit('toggle-group', entry.group.key)
                : action.type === 'create-child' &&
                  emit('create-child', entry.group.cell)
          "
        />
        <AppButton
          v-else-if="entry.group"
          class="handler-table-group"
          :icon="
            closedGroups?.[entry.group.key]
              ? 'MDI_CHEVRON_RIGHT'
              : 'MDI_CHEVRON_DOWN'
          "
          :aria-expanded="!closedGroups?.[entry.group.key]"
          @click="emit('toggle-group', entry.group.key)"
          >{{
            entry.group.translate || !entry.group.key
              ? t(entry.group.label)
              : entry.group.label
          }}
          <small>{{ entry.group.records.length }}</small></AppButton
        >
        <template v-else-if="entry.summary">
          <div class="handler-table-selection" role="gridcell" />
          <div
            v-for="(column, index) in columns"
            :key="column.name"
            class="handler-table-cell"
            role="gridcell"
            :class="{ 'first-column': index === 0 }"
          >
            <strong>{{ entry.summary[column.name] || '' }}</strong>
          </div>
          <div class="handler-table-actions" role="gridcell" />
        </template>
        <template v-else>
          <div class="handler-table-selection" role="gridcell">
            <AppCheckbox
              v-if="selectable"
              :label="
                t('Select record: {name}', {
                  name:
                    entry.record.name ||
                    entry.record.title ||
                    entry.record.code ||
                    entry.record.id
                })
              "
              :translate-label="false"
              :model-value="selectedKeys?.includes(entry.key)"
              @update:model-value="emit('select', [entry.record], $event)"
              ><span class="visually-hidden">{{
                t('Select row')
              }}</span></AppCheckbox
            >
          </div>
          <div
            v-for="(column, index) in columns"
            :key="column.name"
            class="handler-table-cell"
            role="gridcell"
            :class="{
              'first-column': index === 0,
              'editable-cell': editable && column.editable
            }"
            @dblclick.stop="
              editable && column.editable
                ? emit('edit', entry.record, column, $event.currentTarget)
                : emit('inspect', entry.record)
            "
          >
            <slot
              name="cell"
              :record="entry.record"
              :column="{ ...column, width: columnWidth(column) }"
              :index="index"
              :height="rowHeight"
            />
          </div>
          <div class="handler-table-actions" role="gridcell">
            <AppButton
              v-if="!readOnly"
              label="Object actions"
              icon="more"
              icon-only
              @click="emit('operate', entry.record, $event)"
            />
          </div>
        </template>
      </div>
    </div>
  </div>
  <AppMenu
    ref="contextMenu"
    class="table-column-menu"
    label="Column actions"
    overlay
    :width="280"
  >
    <ActionRows :actions="columnActions" @triggered="columnCommand" />
  </AppMenu>
  <dialog
    v-window="{ type: 'dialog' }"
    ref="saveDialog"
    class="save-table-view"
    :aria-label="t('Save table view')"
    @cancel.prevent="savingView = false"
    @close="savingView = false"
  >
    <header>
      <h2>{{ t('Save table view') }}</h2>
      <AppButton
        label="Close"
        icon="close"
        icon-only
        @click="savingView = false"
      />
    </header>
    <form
      @submit.prevent="
        emit('save-view', viewName);
        savingView = false;
        viewName = '';
      "
    >
      <input
        v-model="viewName"
        :aria-label="t('View name')"
        :placeholder="t('View name')"
        required
      />
      <footer>
        <AppButton
          label="Save"
          highlighted
          type="submit"
          :disabled="!viewName.trim() || busy"
        /><AppButton label="Cancel" @click="savingView = false" />
      </footer>
    </form>
  </dialog>
</template>

<style>
.handler-table {
  --icon-size: 17px;
  font-size: var(--font-body-size);
  position: relative;
  flex: 1;
  min-height: 120px;
  overflow: auto;
  scrollbar-gutter: auto;
  scroll-padding-top: 37px;
  padding: 0;
  margin: 0;
  outline: 0;
  overscroll-behavior: contain;
}
.handler-table.no-vertical-overflow::-webkit-scrollbar-thumb:vertical,
.handler-table.no-vertical-overflow::-webkit-scrollbar-track:vertical {
  background: transparent;
}
.handler-table.no-horizontal-overflow::-webkit-scrollbar-thumb:horizontal,
.handler-table.no-horizontal-overflow::-webkit-scrollbar-track:horizontal {
  background: transparent;
}
.handler-table-header {
  position: sticky;
  top: 0;
  display: grid;
  grid-template-columns: var(--table-columns);
  height: 37px;
  z-index: 3;
  color: var(--table-header-text);
  background: var(--table-header);
  border-radius: 0;
  border-bottom: 0;
  font-size: var(--text-caption);
  font-weight: 600;
}
.handler-table-heading {
  position: relative;
  display: flex;
  align-items: center;
  padding: 0 12px 0 10px;
  min-width: 0;
  cursor: grab;
  touch-action: none;
  text-transform: uppercase;
  outline: 0;
}
.handler-table-heading:nth-child(2) {
  padding-left: 14px;
}
.handler-table-heading > span:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.handler-table-heading.dragging {
  background: var(--hover);
}
.handler-table-heading.drop-target {
  box-shadow: inset 3px 0 var(--primary);
}
.handler-table-heading.grouped {
  color: var(--table-header-text);
}
.handler-table-heading.grouped {
  padding-right: 30px;
}
.table-group-indicator {
  position: absolute;
  right: 14px;
  font-size: 14px;
}
.table-resize {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 12px;
  cursor: col-resize;
  touch-action: none;
}
.handler-table-body {
  position: relative;
}
.handler-table-row {
  position: absolute;
  left: 0;
  width: 100%;
  display: grid;
  grid-template-columns: var(--table-columns);
  background: var(--surface);
  border-bottom: 1px solid var(--outline-variant);
  cursor: pointer;
}
.handler-table-row:hover {
  background: var(--row-hover, var(--hover));
}
.handler-table-row.selected,
.handler-table-row.active,
.handler-table-row:focus-within {
  background: var(--content-selection);
}
.handler-table-cell {
  min-width: 0;
  display: flex;
  align-items: center;
  overflow: hidden;
  padding: 0 10px;
  font-weight: 400;
  white-space: nowrap;
}
.handler-table-cell.first-column {
  padding-left: 14px;
  font-weight: 600;
}
.handler-table-cell:has(
  .table-thumbnail,
  .table-notes,
  .table-task-cell,
  .table-task-summary,
  .table-value-fields,
  .table-service-cell,
  .table-status-cell,
  .table-message-cell,
  .table-completion,
  .table-completion-groups,
  .table-action
) {
  padding: 0;
}
.handler-table-cell:has(.app-checkbox, .table-cell-symbol) {
  justify-content: center;
}
.handler-table-cell > span:not(.table-notes) {
  overflow: hidden;
  text-overflow: ellipsis;
}
.handler-table-cell.editable-cell {
  cursor: text;
}
.handler-table-selection {
  position: sticky;
  left: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: inherit;
  z-index: 2;
}
.handler-table-row .handler-table-selection::before {
  content: '';
  position: absolute;
  left: 0;
  top: 7px;
  bottom: 7px;
  width: 3px;
  border-radius: 2px;
  background: var(--table-accent);
  opacity: 0.82;
}
.handler-table-header > .handler-table-selection {
  border-radius: var(--item-radius) 0 0 var(--item-radius);
}
.handler-table-header > .handler-table-actions {
  border-radius: 0 var(--item-radius) var(--item-radius) 0;
}
.handler-table-actions {
  position: sticky;
  right: 0;
  justify-self: end;
  width: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: inherit;
  z-index: 2;
}
.handler-table-actions .app-button,
.handler-table-actions .workspace-menu > summary {
  width: 28px;
  height: 28px;
  min-width: 28px;
  min-height: 28px;
  font-size: 14px;
}
.handler-table-header .handler-table-actions :is(.app-button, summary) {
  color: var(--table-header-text);
  background: var(--surface-high);
  border-radius: var(--item-radius);
}
.handler-table-actions .busy-indicator {
  width: 24px;
  height: 24px;
}
.handler-table-row .handler-table-actions .app-button {
  opacity: 0.35;
  margin-left: auto;
  margin-right: 4px;
}
.handler-table-row:is(:hover, .selected, .active) .handler-table-actions .app-button {
  opacity: 1;
}
.handler-table-selection .app-checkbox {
  width: 28px;
  height: 28px;
  padding: 4px;
}
.handler-table-group {
  position: sticky;
  left: 12px;
  grid-column: 1/-1;
  width: calc(100% - 24px);
  justify-content: flex-start;
  border: 0;
  background: transparent;
}
.handler-table-row.group-row {
  background: var(--surface-high);
}
.table-column-menu > summary {
  display: none;
}
.save-table-view {
  width: min(390px, calc(100vw - 16px));
}
.save-table-view input {
  width: 100%;
}
.save-table-view footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
.configured-view:has(> .handler-table) {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}
.workspace-results:has(.handler-table) {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin: 0;
  border: 0;
  border-radius: 0;
  background: var(--page);
}
.workspace-results > .configured-view[data-result-mode='table'] {
  flex: 1;
  height: 100%;
  width: 100%;
}
.handler-table-cell:has(.table-structured) {
  align-items: stretch;
}
.handler-table-cell .table-structured {
  max-height: 100%;
  width: 100%;
}
.handler-table-detail {
  grid-column: 1 / -1;
  position: sticky;
  left: 0;
  padding-inline: 8px;
  box-sizing: border-box;
}
</style>
