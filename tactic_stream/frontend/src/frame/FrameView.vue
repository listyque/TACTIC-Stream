<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import { tooltipDirective as vTooltip } from '../controls/tooltip.js';
import AppButton from '../controls/AppButton.vue';
import AppTabButton from '../controls/AppTabButton.vue';
import AppCheckbox from '../controls/AppCheckbox.vue';
import AppSwitch from '../controls/AppSwitch.vue';
import AppSearchField from '../controls/AppSearchField.vue';
import UserIdentity from '../controls/UserIdentity.vue';
import AppProgress from '../controls/AppProgress.vue';
import EmptyState from '../controls/display/EmptyState.vue';
import AppFileInput from '../controls/forms/AppFileInput.vue';
import AppTextField from '../controls/AppTextField.vue';
import AppTextArea from '../controls/AppTextArea.vue';
import AppDateField from '../controls/AppDateField.vue';
import UserComboBox from '../controls/UserComboBox.vue';
import AppSegmentedButton from '../controls/AppSegmentedButton.vue';
import AppSelect from '../controls/AppSelect.vue';
import AppEditableSelect from '../controls/AppEditableSelect.vue';
import FrameGrid from './controls/grid/FrameGrid.vue';
import FrameGraph from './controls/graph/FrameGraph.vue';
import FrameChart from './controls/charts/FrameChart.vue';
import FrameCode from './controls/code/FrameCode.vue';
import IconPicker from '../controls/IconPicker.vue';
import AppColorInput from '../controls/AppColorInput.vue';
import AppSplitter from '../controls/AppSplitter.vue';
import AppIcon from '../controls/AppIcon.vue';
import ItemPreview from '../controls/ItemPreview.vue';
import ItemSurface from '../controls/ItemSurface.vue';
import SummaryChip from '../controls/SummaryChip.vue';
import StatusChip from '../controls/display/StatusChip.vue';
import MiddleElide from '../controls/MiddleElide.vue';
import {
  colors,
  listRange,
  listOffsets,
  listBounds,
  validateScene,
  recordIndex,
  revealListOffset
} from '../../../src/tactic_stream/shared_ui/core/frame.mjs';
import './frame.css';
import '../controls/panelChrome.css';

defineOptions({ name: 'FrameView' });
const props = defineProps({
  scene: { type: Object, required: true },
  models: { type: Object, default: () => ({}) },
  views: { type: Object, default: () => ({}) },
  describeRow: Function,
  describeCell: Function,
  interactive: { type: Boolean, default: true }
});
const emit = defineEmits(['event']);
const scroll = ref({}),
  host = ref(null),
  branches = ref([]),
  grids = ref([]),
  graphs = ref([]);
const nodes = computed(() =>
  validateScene(
    props.scene,
    props.models,
    Object.fromEntries(
      Object.entries(props.views).map(([name, view]) => [name, view?.component])
    )
  )
);
const color = (role) =>
  role?.mix
    ? `color-mix(in srgb, ${color(role.mix[0])} ${(1 - role.mix[2]) * 100}%, ${color(role.mix[1])} ${role.mix[2] * 100}%)`
    : role === 'transparent'
      ? 'transparent'
      : role?.startsWith('#')
        ? role
        : colors[role]
          ? 'var(' + colors[role] + ')'
          : undefined;
function previewStyle(node) {
  const bounds = style(node);
  delete bounds.color;
  return bounds;
}
function style(node) {
  return {
    transition: node.motion
      ? Object.entries(node.motion)
          .map(
            ([property, token]) =>
              (property === 'x'
                ? 'left'
                : property === 'y'
                  ? 'top'
                  : property) +
              ' var(' +
              {
                clickMotionSlow: '--motion-click-slow',
                clickMotionFast: '--motion-click',
                hoverMotionFast: '--motion-hover'
              }[token] +
              ') cubic-bezier(.215,.61,.355,1)'
          )
          .join(', ')
      : undefined,
    zIndex: node.layer,
    left: node.x + 'px',
    top: node.y + 'px',
    width: node.width + 'px',
    height: node.height + 'px',
    display: node.visible === false ? 'none' : undefined,
    pointerEvents: node.pointerTransparent ? 'none' : undefined,
    fontSize: node.fontSize + 'px',
    fontWeight: node.weight,
    letterSpacing:
      node.letterSpacing === undefined ? undefined : node.letterSpacing + 'px',
    textAlign: node.align,
    fontFamily: node.monospace ? 'Consolas' : undefined,
    paddingLeft:
      node.paddingLeft === undefined ? undefined : node.paddingLeft + 'px',
    color: color(node.color),
    opacity: node.revealOnRowInteraction ? undefined : node.opacity,
    transform: node.scale === undefined ? undefined : `scale(${node.scale})`,
    transformOrigin: 'top left',
    textDecoration: node.strike ? 'line-through' : undefined,
    '--frame-button-icon-size': node.iconSize ? node.iconSize + 'px' : undefined
  };
}
function background(node) {
  const radius = node.radiusRole
    ? `var(--${node.radiusRole.replace(/[A-Z]/g, (char) => '-' + char.toLowerCase())})`
    : node.radius === undefined
      ? 'var(--surface-radius)'
      : node.radius + 'px';
  return {
    background: color(node.background),
    boxShadow:
      [
        node.border
          ? 'inset 0 0 0 ' +
            (node.borderWidth || 1) +
            'px ' +
            color(node.border)
          : '',
        node.shadow
          ? `0 ${node.shadow.y}px ${node.shadow.blur}px color-mix(in srgb, ${color('popupShadow')} ${node.shadow.opacity * 100}%, transparent)`
          : ''
      ]
        .filter(Boolean)
        .join(', ') || undefined,
    borderRadius: radius,
    borderBottomRightRadius:
      node.bottomRightRadius === undefined
        ? radius
        : node.bottomRightRadius + 'px'
  };
}
function send(action, value, source) {
  if (action && props.interactive)
    emit(
      'event',
      Object.assign({}, action, value === undefined ? {} : { value }),
      source
    );
}
function context(event, node) {
  if (!node.contextAction || !props.interactive) return;
  event.preventDefault();
  event.stopPropagation();
  const bounds = event.currentTarget.getBoundingClientRect();
  send(
    node.contextAction,
    { x: event.clientX - bounds.left, y: event.clientY - bounds.top },
    event.currentTarget
  );
}
function drag(event, node) {
  if (node.dragValue == null) return;
  event.dataTransfer.effectAllowed = 'move';
  event.dataTransfer.setData(
    'application/x-tactic-frame',
    JSON.stringify(node.dragValue)
  );
  send(node.dragStartAction);
}
function dragOver(event, node) {
  if (
    props.interactive &&
    node.enabled !== false &&
    node.dropAction &&
    (event.dataTransfer.types.includes('application/x-tactic-frame') ||
      (node.dropAction.name === 'file-ingest' &&
        event.dataTransfer.types.includes('Files')))
  ) {
    event.preventDefault();
    event.dataTransfer.dropEffect =
      node.dropAction.name === 'file-ingest' ? 'copy' : 'move';
  }
}
function drop(event, node) {
  if (!props.interactive || node.enabled === false || !node.dropAction) return;
  if (
    node.dropAction.name === 'file-ingest' &&
    event.dataTransfer.files?.length
  ) {
    event.preventDefault();
    send(node.dropAction, Array.from(event.dataTransfer.files));
    return;
  }
  const source = event.dataTransfer.getData('application/x-tactic-frame');
  if (!source) return;
  event.preventDefault();
  try {
    send(node.dropAction, JSON.parse(source));
  } catch (error) {
    if (!(error instanceof SyntaxError)) throw error;
  }
}
function sendArea(event, node) {
  if (
    !node.sendOnEnter ||
    event.key !== 'Enter' ||
    event.shiftKey ||
    event.ctrlKey ||
    event.altKey ||
    event.metaKey ||
    event.isComposing ||
    event.keyCode === 229 ||
    event.repeat ||
    matchMedia('(max-width: 640px) and (pointer: coarse)').matches
  )
    return;
  event.preventDefault();
  send(node.sendAction);
}
function key(event, node) {
  if (event.isComposing || event.keyCode === 229) return;
  if (
    node.tableCell &&
    (event.shiftKey || event.ctrlKey || event.altKey || event.metaKey)
  )
    return;
  const name = event.key === 'Tab' && event.shiftKey ? 'Backtab' : event.key;
  if (
    ['Button', 'Action'].includes(node.kind) &&
    node.enabled &&
    !event.repeat &&
    ['Enter', ' '].includes(name) &&
    !node.keys?.[name]
  )
    send(node.pressAction, undefined, event.currentTarget);
  if (node.keys?.[name]) {
    event.preventDefault();
    send(node.keys[name]);
  }
}
const listLayouts = computed(
  () =>
    new Map(
      nodes.value
        .filter((node) => node.kind === 'List')
        .map((node) => [
          node.id,
          listOffsets(node, props.models[node.source] || [])
        ])
    )
);
function listHeight(node) {
  const rows = props.models[node.source] || [],
    offsets = listLayouts.value.get(node.id);
  return offsets ? offsets[rows.length] : rows.length * node.rowHeight;
}
function records(node) {
  const rows = props.models[node.source] || [],
    offsets = listLayouts.value.get(node.id),
    range = listRange(
      rows.length,
      node.rowHeight,
      node.height,
      scroll.value[node.id] || 0,
      3,
      offsets
    );
  return rows.slice(range.first, range.last).map((record, index) => ({
    record,
    index: range.first + index,
    ...listBounds(node, offsets, range.first + index)
  }));
}
const previousLists = new Map();
watch(
  () => [props.models, nodes.value],
  () => {
    const present = new Set();
    for (const node of nodes.value) {
      if (node.kind !== 'List') continue;
      present.add(node.id);
      const rows = props.models[node.source];
      const offsets = listLayouts.value.get(node.id);
      const previous = previousLists.get(node.id);
      if (
        previous?.rows === rows &&
        previous.keyField === node.keyField &&
        previous.offsets === offsets &&
        previous.rowHeight === node.rowHeight
      )
        continue;
      const indexes = recordIndex(rows, node.keyField);
      const container = host.value?.querySelector(
        ':scope > [data-frame="' + CSS.escape(node.id) + '"]'
      );
      const focused = document.activeElement;
      const focusedRow = container?.contains(focused)
        ? focused.closest('[data-frame-row]')
        : null;
      // A DOM scroll can precede its scroll event and the next model update.
      let offset = container ? container.scrollTop : scroll.value[node.id] || 0;
      if (focusedRow && previous) {
        const key = focusedRow.getAttribute('data-frame-row');
        const oldIndex = previous.rows.findIndex(
          (row) => String(row[previous.keyField]) === key
        );
        if (oldIndex >= 0 && indexes.has(key))
          offset +=
            (offsets
              ? offsets[indexes.get(key)]
              : indexes.get(key) * node.rowHeight) -
            (previous.offsets
              ? previous.offsets[oldIndex]
              : oldIndex * previous.rowHeight);
      }
      offset = Math.max(
        0,
        Math.min(offset, Math.max(0, listHeight(node) - node.height))
      );
      scroll.value[node.id] = offset;
      previousLists.set(node.id, {
        rows,
        keyField: node.keyField,
        offsets,
        rowHeight: node.rowHeight
      });
      if (container)
        nextTick(() => {
          if (container.isConnected)
            container.scrollTop = scroll.value[node.id] || 0;
        });
    }
    for (const id of previousLists.keys())
      if (!present.has(id)) previousLists.delete(id);
  },
  { immediate: true }
);
function focusControl(name) {
  const el = host.value?.querySelector(
    '[data-frame="' + CSS.escape(name) + '"]'
  );
  if (!el) return false;
  const focusable = 'input,textarea,select,button,summary,[tabindex]';
  const target = el.matches(focusable) ? el : el.querySelector(focusable);
  target?.focus({ preventScroll: true });
  target?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  return document.activeElement === target;
}
async function focusGrid(id, row, column, name) {
  const grid = grids.value.find((value) => value.$props.node.id === id);
  if (grid) {
    await grid.focusCell(row, column, name);
    return true;
  }
  for (const branch of branches.value)
    if (await branch.focusGrid(id, row, column, name)) return true;
  return false;
}
function graphCommand(id, command) {
  const graph = graphs.value.find((value) => value.$props.node.id === id);
  if (graph) {
    if (command.type === 'point') return graph.insertionPoint();
    graph.dispatch(command);
    return true;
  }
  for (const branch of branches.value) {
    const result = branch.graphCommand?.(id, command);
    if (result) return result;
  }
  return null;
}
async function focusListRow(id, index, controlId) {
  const definition = nodes.value.find(
    (node) => node.id === id && node.kind === 'List'
  );
  if (definition) {
    const rows = props.models[definition.source] || [];
    const list = host.value?.querySelector(
      ':scope > [data-frame="' + CSS.escape(id) + '"]'
    );
    if (!list || index < 0 || index >= rows.length) return false;
    const offset = revealListOffset(
      list.scrollTop,
      index,
      list.clientHeight,
      rows.length,
      definition.rowHeight,
      definition.rowGap ?? 4,
      listLayouts.value.get(definition.id)
    );
    list.scrollTop = offset;
    scroll.value = { ...scroll.value, [id]: offset };
    await nextTick();
    return controlId ? focusControl(controlId) : true;
  }
  for (const branch of branches.value || [])
    if (await branch?.focusListRow?.(id, index, controlId)) return true;
  return false;
}
defineExpose({ focusControl, focusGrid, graphCommand, focusListRow });
</script>

<template>
  <div
    ref="host"
    class="frame-view"
    :inert="!interactive"
    :class="{ 'frame-passive': !interactive }"
  >
    <template v-for="node in nodes" :key="node.id">
      <component
        :is="node.titlebar ? 'header' : 'div'"
        v-if="node.kind === 'Box'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node frame-box"
        :class="{ 'frame-titlebar': node.titlebar }"
        :style="
          Object.assign(style(node), background(node), {
            overflow: node.clip === false ? 'visible' : undefined,
            '--frame-titlebar-actions-right': (node.chromeRight || 0) + 'px',
            '--frame-titlebar-actions-top':
              node.chromeTop !== undefined ? node.chromeTop + 'px' : undefined,
            '--frame-titlebar-actions-height':
              node.chromeHeight !== undefined
                ? node.chromeHeight + 'px'
                : undefined
          })
        "
        :role="node.role"
        :aria-label="node.label"
        @contextmenu="context($event, node)"
        @dragover="dragOver($event, node)"
        @drop="drop($event, node)"
        ><FrameView
          v-if="node.children?.length"
          ref="branches"
          :scene="{ nodes: node.children }"
          :models="models"
          :views="views"
          :describe-row="describeRow"
          :describe-cell="describeCell"
          :interactive="interactive"
          @event="(action, source) => emit('event', action, source)"
      /></component>
      <span
        v-else-if="node.kind === 'Label'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        :role="node.role"
        :aria-level="node.role === 'heading' ? node.level || 2 : undefined"
        :tabindex="node.focusable ? 0 : undefined"
        v-tooltip="node.toolTip"
        class="frame-node frame-label"
        :class="{ 'frame-wrap': node.wrap }"
        :style="
          Object.assign(style(node), {
            overflow: node.elide === false ? 'visible' : undefined,
            textOverflow: node.elide === false ? 'clip' : undefined,
            textAlign: node.align || 'left',
            wordBreak: node.wrapAnywhere ? 'break-all' : undefined,
            lineHeight:
              node.wrap || node.verticalAlign === 'top'
                ? 'normal'
                : node.height + 'px',
            alignItems: node.verticalAlign === 'top' ? 'flex-start' : undefined,
            display:
              node.visible === false
                ? 'none'
                : node.maxLines
                  ? '-webkit-box'
                  : undefined,
            WebkitLineClamp: node.maxLines || undefined,
            WebkitBoxOrient: node.maxLines ? 'vertical' : undefined
          })
        "
        :title="node.toolTip ? undefined : node.text"
        ><MiddleElide v-if="node.elideMiddle" :text="node.text" /><span
          v-else
          >{{ node.text }}</span
        ></span
      >
      <AppIcon
        v-else-if="node.kind === 'Icon'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node"
        :style="Object.assign(style(node), { fontSize: node.width + 'px' })"
        :name="node.icon"
        :aria-hidden="node.text ? 'false' : 'true'"
        :role="node.text ? 'img' : undefined"
        :aria-label="node.text || undefined"
        :tabindex="node.focusable ? 0 : undefined"
        v-tooltip="node.toolTip || node.text"
      />
      <component
        :is="node.tab ? AppTabButton : AppButton"
        v-else-if="node.kind === 'Button'"
        @focus="
          $event.target.scrollIntoView({ block: 'nearest', inline: 'nearest' })
        "
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node"
        :class="{
          'frame-button': !node.iconAction && !node.tab,
          'frame-icon-action': node.iconAction,
          'frame-radio': node.radio,
          'frame-radio-selected': node.radio && node.selected
        }"
        :style="
          Object.assign(style(node), {
            borderRadius: node.round ? '50%' : undefined,
            color:
              node.iconAction &&
              node.enabled !== false &&
              (node.iconColor || node.highlighted)
                ? color(node.iconColor || 'selectedText')
                : undefined
          })
        "
        :label="node.text"
        :translate-label="false"
        :aria-label="node.label || node.text"
        :tooltip="
          node.toolTip || (node.iconOnly ? node.label || node.text : undefined)
        "
        :icon="node.icon"
        :icon-only="node.iconOnly"
        :href="node.href"
        :target="node.target"
        :rel="node.href ? 'noopener noreferrer' : undefined"
        :highlighted="node.highlighted"
        :filled-action="node.filledAction"
        :segmented="node.radio"
        :checked="!!node.selected"
        :destructive="node.destructive"
        :tonal="node.tonal"
        :badge-count="node.badgeCount || 0"
        :badge-color="node.badgeColor ? color(node.badgeColor) : undefined"
        :show-zero-badge="node.showZeroBadge"
        :disabled="!node.enabled"
        :role="node.radio ? 'radio' : undefined"
        :aria-checked="node.radio ? !!node.selected : undefined"
        :tabindex="node.radio && !node.selected ? -1 : undefined"
        @keydown="key($event, node)"
        @pointerdown="
          (event) => {
            if (node.retainFocus) event.preventDefault();
            send(node.pressAction, undefined, event.currentTarget);
          }
        "
        @click="send(node.action, undefined, $event.currentTarget)"
        @dragover="dragOver($event, node)"
        @drop="drop($event, node)"
      />
      <AppButton
        v-else-if="node.kind === 'Action'"
        :id="node.elementId"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node frame-action"
        :class="{ 'frame-secondary-action': node.revealOnRowInteraction }"
        :style="
          Object.assign(style(node), {
            borderRadius: (node.radius === undefined ? 10 : node.radius) + 'px'
          })
        "
        :label="node.text"
        :translate-label="false"
        :disabled="!node.enabled"
        :aria-pressed="node.selected"
        :tooltip="node.toolTip"
        :aria-description="node.description"
        :role="node.role"
        :aria-level="node.role === 'treeitem' ? node.level : undefined"
        :aria-expanded="
          ['treeitem', 'button'].includes(node.role) ? node.expanded : undefined
        "
        :aria-selected="
          ['treeitem', 'option'].includes(node.role)
            ? !!node.selected
            : undefined
        "
        :aria-checked="node.role === 'checkbox' ? node.checked : undefined"
        @pointerdown="send(node.pressAction, undefined, $event.currentTarget)"
        @focus="
          $event.target.scrollIntoView({ block: 'nearest', inline: 'nearest' })
        "
        @keydown="key($event, node)"
        @click="send(node.action, undefined, $event.currentTarget)"
        @dblclick="send(node.doubleAction)"
        :draggable="node.dragValue != null && interactive"
        @dragstart="drag($event, node)"
        @dragover="dragOver($event, node)"
        @drop="drop($event, node)"
      >
        <ItemSurface
          :selected="node.selected"
          :accent="color(node.accent)"
          :corner-radius="node.radius === undefined ? 10 : node.radius"
          :normal-color="color(node.normalColor) || 'transparent'"
          :selected-color="color(node.selectedColor) || 'transparent'"
          :rail-visible="!!node.rail"
          :separator-visible="false"
          :inset="0"
          ><FrameView
            ref="branches"
            :scene="{ nodes: node.children }"
            :interactive="false"
            :models="models"
            :views="views"
            :describe-row="describeRow"
            :describe-cell="describeCell"
        /></ItemSurface>
      </AppButton>
      <AppSegmentedButton
        v-else-if="node.kind === 'Segmented'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node"
        :style="style(node)"
        :label="node.label"
        :options="node.options"
        :model-value="node.value"
        :icon-only="node.iconOnly"
        :disabled="!node.enabled"
        @update:model-value="send(node.action, $event)"
      />
      <AppCheckbox
        v-else-if="node.kind === 'CheckBox'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node frame-checkbox"
        :class="{ 'frame-checkbox-wrap': node.wrapText }"
        :style="
          Object.assign(style(node), {
            '--frame-indicator-x': (node.indicatorX || 0) + 'px'
          })
        "
        :model-value="node.checked"
        :indeterminate="!!node.mixed"
        :compact="node.compact"
        :prominent="node.prominent"
        :label="node.label || node.text"
        :translate-label="false"
        :disabled="!node.enabled"
        @keydown="key($event, node)"
        @update:model-value="send(node.action, $event)"
      >
        <ItemSurface
          :selected="node.checked"
          :corner-radius="node.radius"
          :normal-color="color(node.normalColor) || 'transparent'"
          :selected-color="color(node.selectedColor) || 'transparent'"
          :rail-visible="false"
          :separator-visible="false"
          :inset="0"
          ><FrameView
            v-if="node.children?.length"
            ref="branches"
            :scene="{ nodes: node.children }"
            :interactive="false"
          /><span v-else class="frame-checkbox-label"
            ><span>{{ node.text }}</span></span
          ></ItemSurface
        >
      </AppCheckbox>
      <div
        v-else-if="node.kind === 'Switch'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node frame-switch"
        :style="style(node)"
        v-tooltip="node.toolTip"
      >
        <AppSwitch
          :model-value="node.checked"
          :label="node.text"
          :disabled="!node.enabled"
          @update:model-value="send(node.action, $event)"
        />
      </div>
      <AppTextField
        v-else-if="node.kind === 'Field'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node frame-field"
        @focus="
          $event.target.scrollIntoView({ block: 'nearest', inline: 'nearest' });
          node.selectOnFocus && $event.target.select();
        "
        :class="{ 'table-cell': node.tableCell }"
        :error-state="!!node.error"
        :style="style(node)"
        :label="node.label"
        :placeholder="node.placeholder"
        :model-value="node.text"
        :readonly="node.readOnly"
        :maxlength="node.maxLength"
        :type="node.password ? 'password' : node.inputType || 'text'"
        :autocomplete="
          node.autocomplete || (node.password ? 'new-password' : 'off')
        "
        :name="node.name"
        :inputmode="node.inputMode"
        :disabled="!node.enabled"
        @keydown="key($event, node)"
        @click="send(node.activateAction)"
        @blur="send(node.commitAction, $event.target.value)"
        @update:model-value="send(node.action, $event)"
      />
      <AppTextArea
        v-else-if="node.kind === 'Area'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node frame-area"
        @focus="
          $event.target.scrollIntoView({ block: 'nearest', inline: 'nearest' })
        "
        :role="node.role"
        :class="{ 'frame-notice': node.notice }"
        :flat="!!node.flat"
        :wrap="node.wrap === false ? 'off' : undefined"
        :error-state="!!node.error"
        :style="style(node)"
        :label="node.label"
        :placeholder="node.placeholder"
        :model-value="node.text"
        :readonly="node.readOnly"
        :maxlength="node.maxLength"
        :disabled="!node.enabled"
        @keydown="sendArea($event, node)"
        @update:model-value="send(node.action, $event)"
      />
      <ItemPreview
        v-else-if="node.kind === 'Preview'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node frame-preview"
        :style="
          Object.assign(
            previewStyle(node),
            node.radius !== undefined
              ? { borderRadius: node.radius + 'px' }
              : node.round === false
                ? { borderRadius: '4px' }
                : {}
          )
        "
        :source="node.source"
        :fallback-text="node.initials"
        :fallback-icon="node.icon || 'person'"
        :foreground="node.color ? color(node.color) : undefined"
        :accent="node.accent || 'action'"
        :preview-size="node.width"
        :round="node.round !== false"
        :outlined="node.outlined !== false"
        :selected="node.selected"
        :loading="node.loading"
        :fill-mode="node.fit || 'cover'"
      />
      <SummaryChip
        v-else-if="node.kind === 'SummaryChip'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node frame-summary-chip"
        :style="style(node)"
        :label="node.text"
        :count="node.count || 0"
        :accent="color(node.accent || 'action')"
        :icon="node.icon"
        :compact="node.compact"
        :clickable="!!node.action"
        :disabled="!node.enabled"
        :show-count="node.showCount !== false"
        :show-dot="node.showDot !== false"
        @click="send(node.action)"
      />
      <div
        v-else-if="node.kind === 'List'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node frame-list"
        :role="node.role"
        :style="style(node)"
        :aria-label="node.label"
        @scroll="scroll[node.id] = $event.target.scrollTop"
      >
        <div
          :style="{
            position: 'relative',
            height: listHeight(node) + 'px'
          }"
        >
          <FrameView
            ref="branches"
            v-for="item in records(node)"
            :key="item.record[node.keyField]"
            :data-frame-row="String(item.record[node.keyField])"
            class="frame-row"
            :class="{ 'frame-box': !node.fields.length }"
            :style="{
              top: item.y + 'px',
              height: item.height + 'px',
              width: node.width - 16 + 'px'
            }"
            :scene="describeRow(node, item.record, item.index)"
            :models="models"
            :views="views"
            :describe-row="describeRow"
            :describe-cell="describeCell"
            :interactive="interactive"
            @event="(action, source) => emit('event', action, source)"
          />
        </div>
      </div>
      <div
        v-else-if="node.kind === 'Scroll'"
        :key="node.id + ':' + node.resetKey"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node frame-scroll"
        :class="{ 'frame-scroll-horizontal': node.contentWidth > node.width }"
        :style="style(node)"
      >
        <FrameView
          ref="branches"
          :style="{
            height: node.contentHeight + 'px',
            width:
              node.contentWidth === undefined
                ? undefined
                : Math.max(node.width, node.contentWidth) + 'px'
          }"
          :scene="{ nodes: node.children }"
          :models="models"
          :views="views"
          :describe-row="describeRow"
          :describe-cell="describeCell"
          :interactive="interactive"
          @event="(action, source) => emit('event', action, source)"
        />
      </div>
      <component
        :is="node.editable ? AppEditableSelect : AppSelect"
        v-else-if="node.kind === 'Choice'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node frame-choice"
        @focus="
          $event.target.scrollIntoView({ block: 'nearest', inline: 'nearest' })
        "
        :style="style(node)"
        :label="node.label"
        :display-prefix="node.displayPrefix"
        :translate-labels="false"
        :options="node.options"
        :model-value="node.value"
        :placeholder="node.placeholder"
        :disabled="!node.enabled"
        @keydown="key($event, node)"
        @accept="send(node.commitAction, $event)"
        @update:model-value="send(node.action, $event)"
      />
      <div
        v-else-if="node.kind === 'IconChoice'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node frame-icon-choice"
        :style="style(node)"
      >
        <IconPicker
          :model-value="node.value"
          :tactic-compatible-only="node.tacticCompatibleOnly"
          icon-only
          :disabled="!node.enabled"
          @update:model-value="send(node.action, $event)"
        />
      </div>
      <div
        v-else-if="node.kind === 'ColorChoice'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node frame-color-choice"
        :style="style(node)"
      >
        <AppColorInput
          :model-value="node.value"
          :label="node.label"
          :disabled="!node.enabled"
          @update:model-value="send(node.action, $event)"
        />
      </div>
      <AppSplitter
        v-else-if="node.kind === 'Splitter'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node frame-splitter"
        :style="style(node)"
        :model-value="node.value"
        :min="node.min"
        :max="node.max"
        :horizontal="node.horizontal"
        :disabled="!node.enabled"
        :reverse="node.reverse"
        :label="node.text"
        @update:model-value="send(node.action, $event)"
        @committed="node.commitAction && send(node.commitAction, $event)"
        @cancelled="node.cancelAction && send(node.cancelAction, $event)"
      />
      <StatusChip
        v-else-if="node.kind === 'StatusChip'"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        class="frame-node"
        :style="
          Object.assign(style(node), {
            fontSize: undefined,
            fontWeight: undefined,
            color: undefined
          })
        "
        :text="node.text"
        :icon="node.icon"
        :accent="color(node.accent)"
        :dense="node.dense"
        :interactive="!!node.action"
        :disabled="!node.enabled"
        @click="send(node.action)"
      />
      <AppDateField
        v-else-if="node.kind === 'DateChoice'"
        class="frame-node frame-date-choice"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        :style="style(node)"
        :model-value="node.text"
        :label="node.label"
        :include-time="!!node.includeTime"
        :month-only="!!node.monthOnly"
        :allow-clear="node.allowClear !== false"
        :readonly="!!node.readOnly"
        :disabled="!node.enabled"
        @update:model-value="send(node.action, $event)"
        @change="send(node.commitAction, $event)"
      />
      <UserComboBox
        v-else-if="node.kind === 'UserChoice'"
        class="frame-node frame-user-choice"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        :style="style(node)"
        :value="node.value"
        :options="node.options || []"
        :label="node.label"
        :empty-label="
          node.options?.find((option) => option.value === '')?.label ||
          'Not assigned'
        "
        :action-field="!!node.actionField"
        :disabled="!node.enabled"
        @change="send(node.action, $event)"
      />
      <AppSearchField
        v-else-if="node.kind === 'Search'"
        class="frame-node"
        :data-frame="node.id"
        :style="style(node)"
        :model-value="node.text"
        :placeholder="node.placeholder"
        :label="node.label"
        :disabled="!interactive || !node.enabled"
        :readonly="node.readOnly"
        :suggestions="node.suggestions || []"
        :error="node.errorText || ''"
        @update:model-value="(value) => send(node.action, value)"
        @search="send(node.commitAction)"
        @accept="(record) => send(node.acceptAction, record)"
      />
      <UserIdentity
        v-else-if="node.kind === 'Identity'"
        class="frame-node"
        :data-frame="node.id"
        :style="style(node)"
        :login="node.login || ''"
        :display-name="node.text"
        :initials="node.initials || ''"
        :avatar-url="node.url || ''"
        :avatar-color="color(node.accent || 'action')"
        :avatar-size="node.avatarSize || 40"
        :retired="node.retired"
        :emphasized="node.emphasized"
      />
      <AppProgress
        v-else-if="node.kind === 'Progress'"
        class="frame-node"
        :data-frame="node.id"
        :style="style(node)"
        :label="node.text"
        :value="node.indeterminate ? undefined : node.value"
        :min="node.min ?? 0"
        :max="node.max ?? 1"
      />
      <EmptyState
        v-else-if="node.kind === 'Empty'"
        class="frame-node"
        :data-frame="node.id"
        :style="style(node)"
        :title="node.text"
        :message="node.message"
        :icon="node.icon || 'info'"
        :error="node.error"
        :action="
          node.action
            ? {
                label: node.actionText,
                icon: node.actionIcon,
                disabled: !interactive || !node.enabled || node.readOnly
              }
            : undefined
        "
        @action="send(node.action)"
      />
      <AppFileInput
        v-else-if="node.kind === 'FileField'"
        class="frame-node"
        :data-frame="node.id"
        :style="style(node)"
        :value="node.text"
        :label="node.label"
        :disabled="!interactive || !node.enabled || node.readOnly"
        @change="
          (event) => send(node.action, Array.from(event.target.files || []))
        "
      />
      <FrameGrid
        v-else-if="node.kind === 'Grid'"
        ref="grids"
        class="frame-node"
        :style="style(node)"
        :node="node"
        :source="models[node.source]"
        :describe-cell="describeCell"
        @event="(action, source) => emit('event', action, source)"
      />
      <FrameGraph
        v-else-if="node.kind === 'Graph'"
        ref="graphs"
        class="frame-node"
        :style="style(node)"
        :node="node"
        @event="(action, source) => emit('event', action, source)"
      />
      <FrameChart
        v-else-if="node.kind === 'Chart'"
        class="frame-node"
        :style="style(node)"
        :node="node"
      />
      <FrameCode
        v-else-if="node.kind === 'Code'"
        class="frame-node"
        :style="style(node)"
        :node="node"
        @event="(action, source) => emit('event', action, source)"
      />
      <component
        v-else-if="node.kind === 'View'"
        :is="views[node.view]?.component"
        :ref="views[node.view]?.captureRef"
        v-bind="views[node.view]?.props"
        :frame-node="views[node.view]?.nodeProps ? node : undefined"
        class="frame-node frame-child-view"
        :data-frame="node.id"
        :data-layout-element="node.layoutElement"
        :style="style(node)"
      />
    </template>
  </div>
</template>
