<script setup>
import { computed, ref, watch } from 'vue';
import AppButton from '../controls/AppButton.vue';
import AppCheckbox from '../controls/AppCheckbox.vue';
import AppSwitch from '../controls/AppSwitch.vue';
import AppTextField from '../controls/AppTextField.vue';
import AppTextArea from '../controls/AppTextArea.vue';
import AppSelect from '../controls/AppSelect.vue';
import FrameGrid from './controls/grid/FrameGrid.vue';
import FrameGraph from './controls/graph/FrameGraph.vue';
import FrameCode from './controls/code/FrameCode.vue';
import IconPicker from '../controls/IconPicker.vue';
import AppColorInput from '../controls/AppColorInput.vue';
import AppSplitter from '../controls/AppSplitter.vue';
import AppIcon from '../controls/AppIcon.vue';
import ItemPreview from '../controls/ItemPreview.vue';
import ItemSurface from '../controls/ItemSurface.vue';
import {
  colors,
  virtualRange
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
const nodes = computed(() => props.scene.nodes || []);
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
function style(node) {
  return {
    left: node.x + 'px',
    top: node.y + 'px',
    width: node.width + 'px',
    height: node.height + 'px',
    display: node.visible === false ? 'none' : undefined,
    fontSize: node.fontSize + 'px',
    fontWeight: node.weight,
    textAlign: node.align,
    fontFamily: node.monospace ? 'Consolas' : undefined,
    color: color(node.color),
    opacity: node.opacity,
    textDecoration: node.strike ? 'line-through' : undefined
  };
}
function background(node) {
  return {
    background: color(node.background),
    boxShadow: node.border
      ? 'inset 0 0 0 ' + (node.borderWidth || 1) + 'px ' + color(node.border)
      : undefined,
    borderRadius:
      node.radius === undefined ? 'var(--surface-radius)' : node.radius + 'px'
  };
}
function send(action, value) {
  if (action && props.interactive)
    emit(
      'event',
      Object.assign({}, action, value === undefined ? {} : { value })
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
    node.dropAction &&
    event.dataTransfer.types.includes('application/x-tactic-frame')
  ) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }
}
function drop(event, node) {
  if (!node.dropAction) return;
  const source = event.dataTransfer.getData('application/x-tactic-frame');
  if (!source) return;
  event.preventDefault();
  try {
    send(node.dropAction, JSON.parse(source));
  } catch (error) {
    if (!(error instanceof SyntaxError)) throw error;
  }
}
function key(event, node) {
  if (
    node.tableCell &&
    (event.shiftKey || event.ctrlKey || event.altKey || event.metaKey)
  )
    return;
  if (node.keys?.[event.key]) {
    event.preventDefault();
    send(node.keys[event.key]);
  }
}
function records(node) {
  const rows = props.models[node.source] || [],
    range = virtualRange(
      rows.length,
      node.rowHeight,
      node.height,
      scroll.value[node.id] || 0,
      3
    );
  return rows
    .slice(range.first, range.last)
    .map((record, index) => ({ record, index: range.first + index }));
}
watch(
  () => props.models,
  () => {
    for (const node of nodes.value)
      if (node.kind === 'List')
        scroll.value[node.id] = Math.min(
          scroll.value[node.id] || 0,
          Math.max(
            0,
            (props.models[node.source]?.length || 0) * node.rowHeight -
              node.height
          )
        );
  },
  { deep: false }
);
function focusControl(name) {
  const el = host.value?.querySelector('[data-frame="' + name + '"]');
  if (!el) return false;
  (el.matches('label') ? el.querySelector('input') : el)?.focus();
  return true;
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
defineExpose({ focusControl, focusGrid, graphCommand });
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
        class="frame-node frame-box"
        :class="{ 'frame-titlebar': node.titlebar }"
        :style="
          Object.assign(style(node), background(node), {
            '--frame-titlebar-actions-right': (node.chromeRight || 0) + 'px'
          })
        "
        :role="node.role"
        ><FrameView
          ref="branches"
          :scene="{ nodes: node.children }"
          :models="models"
          :views="views"
          :describe-row="describeRow"
          :describe-cell="describeCell"
          :interactive="interactive"
          @event="emit('event', $event)"
      /></component>
      <span
        v-else-if="node.kind === 'Label'"
        :data-frame="node.id"
        :role="node.role"
        :aria-level="node.role === 'heading' ? node.level || 2 : undefined"
        class="frame-node frame-label"
        :class="{ 'frame-wrap': node.wrap }"
        :style="
          Object.assign(style(node), {
            textAlign: node.align || 'left',
            lineHeight: node.wrap ? 'normal' : node.height + 'px'
          })
        "
        :title="node.text"
        ><span>{{ node.text }}</span></span
      >
      <AppIcon
        v-else-if="node.kind === 'Icon'"
        :data-frame="node.id"
        class="frame-node"
        :style="Object.assign(style(node), { fontSize: node.width + 'px' })"
        :name="node.icon"
        :title="node.text || undefined"
      />
      <AppButton
        v-else-if="node.kind === 'Button'"
        :data-frame="node.id"
        class="frame-node frame-button"
        :class="{
          'frame-radio': node.radio,
          'frame-radio-selected': node.radio && node.selected
        }"
        :style="style(node)"
        :label="node.text"
        :translate-label="false"
        :icon="node.icon"
        :icon-only="node.iconOnly"
        :highlighted="node.highlighted"
        :destructive="node.destructive"
        :disabled="!node.enabled"
        :role="node.radio ? 'radio' : undefined"
        :aria-checked="node.radio ? !!node.selected : undefined"
        :tabindex="node.radio && !node.selected ? -1 : undefined"
        @keydown="key($event, node)"
        @click="send(node.action)"
        @dragover="dragOver($event, node)"
        @drop="drop($event, node)"
      />
      <AppButton
        v-else-if="node.kind === 'Action'"
        :data-frame="node.id"
        class="frame-node frame-action"
        :style="style(node)"
        :label="node.text"
        :translate-label="false"
        :disabled="!node.enabled"
        :aria-pressed="node.selected"
        :aria-description="node.description"
        :role="node.role"
        :aria-checked="node.role === 'checkbox' ? node.checked : undefined"
        @keydown="key($event, node)"
        @click="send(node.action)"
        :draggable="node.dragValue != null && interactive"
        @dragstart="drag($event, node)"
      >
        <ItemSurface
          :selected="node.selected"
          :normal-color="color(node.normalColor) || 'transparent'"
          :selected-color="color(node.selectedColor) || 'transparent'"
          :rail-visible="!!node.rail"
          :separator-visible="false"
          :inset="0"
          ><FrameView
            ref="branches"
            :scene="{ nodes: node.children }"
            :interactive="false"
        /></ItemSurface>
      </AppButton>
      <AppCheckbox
        v-else-if="node.kind === 'CheckBox'"
        :data-frame="node.id"
        class="frame-node frame-checkbox"
        :style="
          Object.assign(style(node), {
            '--frame-indicator-x': (node.indicatorX || 0) + 'px'
          })
        "
        :model-value="node.checked"
        :label="node.text"
        :translate-label="false"
        :disabled="!node.enabled"
        @keydown="key($event, node)"
        @update:model-value="send(node.action, $event)"
      >
        <ItemSurface
          :selected="node.checked"
          :normal-color="color(node.normalColor) || 'transparent'"
          :selected-color="color(node.selectedColor) || 'transparent'"
          :rail-visible="false"
          :separator-visible="false"
          :inset="0"
          ><FrameView
            ref="branches"
            :scene="{ nodes: node.children }"
            :interactive="false"
        /></ItemSurface>
      </AppCheckbox>
      <div
        v-else-if="node.kind === 'Switch'"
        :data-frame="node.id"
        class="frame-node frame-switch"
        :style="style(node)"
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
        class="frame-node frame-field"
        @focus="
          $event.target.scrollIntoView({ block: 'nearest', inline: 'nearest' })
        "
        :class="{ 'table-cell': node.tableCell }"
        :style="style(node)"
        :label="node.label"
        :placeholder="node.placeholder"
        :model-value="node.text"
        :readonly="node.readOnly"
        :maxlength="node.maxLength"
        :type="node.password ? 'password' : 'text'"
        :autocomplete="node.password ? 'new-password' : 'off'"
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
        class="frame-node frame-area"
        @focus="
          $event.target.scrollIntoView({ block: 'nearest', inline: 'nearest' })
        "
        :role="node.role"
        :class="{ 'frame-notice': node.notice }"
        :style="style(node)"
        :label="node.label"
        :placeholder="node.placeholder"
        :model-value="node.text"
        :readonly="node.readOnly"
        :maxlength="node.maxLength"
        :disabled="!node.enabled"
        @update:model-value="send(node.action, $event)"
      />
      <ItemPreview
        v-else-if="node.kind === 'Preview'"
        :data-frame="node.id"
        class="frame-node frame-preview"
        :style="
          Object.assign(
            style(node),
            node.round === false ? { borderRadius: '4px' } : {}
          )
        "
        :source="node.source"
        :fallback-text="node.initials"
        :fallback-icon="node.icon || 'person'"
        :accent="color(node.accent) || 'var(--primary)'"
        :preview-size="node.width"
        :round="node.round !== false"
        :outlined="node.outlined !== false"
        :fill-mode="node.fit || 'cover'"
      />
      <div
        v-else-if="node.kind === 'List'"
        :data-frame="node.id"
        class="frame-node frame-list"
        :style="style(node)"
        :aria-label="node.label"
        @scroll="scroll[node.id] = $event.target.scrollTop"
      >
        <div
          :style="{
            position: 'relative',
            height: (models[node.source]?.length || 0) * node.rowHeight + 'px'
          }"
        >
          <FrameView
            ref="branches"
            v-for="item in records(node)"
            :key="item.record[node.keyField]"
            class="frame-row"
            :style="{
              top: item.index * node.rowHeight + 'px',
              height: node.rowHeight - 4 + 'px',
              width: node.width - 16 + 'px'
            }"
            :scene="describeRow(node, item.record)"
            :models="models"
            :views="views"
            :describe-row="describeRow"
            :describe-cell="describeCell"
            :interactive="interactive"
            @event="emit('event', $event)"
          />
        </div>
      </div>
      <div
        v-else-if="node.kind === 'Scroll'"
        :key="node.id + ':' + node.resetKey"
        :data-frame="node.id"
        class="frame-node frame-scroll"
        :style="style(node)"
      >
        <FrameView
          ref="branches"
          :style="{ height: node.contentHeight + 'px' }"
          :scene="{ nodes: node.children }"
          :models="models"
          :views="views"
          :describe-row="describeRow"
          :describe-cell="describeCell"
          :interactive="interactive"
          @event="emit('event', $event)"
        />
      </div>
      <AppSelect
        v-else-if="node.kind === 'Choice'"
        :data-frame="node.id"
        class="frame-node frame-choice"
        @focus="
          $event.target.scrollIntoView({ block: 'nearest', inline: 'nearest' })
        "
        :style="style(node)"
        :label="node.label"
        :translate-labels="false"
        :options="node.options"
        :model-value="node.value"
        :disabled="!node.enabled"
        @update:model-value="send(node.action, $event)"
      />
      <div
        v-else-if="node.kind === 'IconChoice'"
        :data-frame="node.id"
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
        class="frame-node frame-splitter"
        :style="style(node)"
        :model-value="node.value"
        :min="node.min"
        :max="node.max"
        :horizontal="node.horizontal"
        :reverse="node.reverse"
        :label="node.text"
        @update:model-value="send(node.action, $event)"
      />
      <FrameGrid
        v-else-if="node.kind === 'Grid'"
        ref="grids"
        class="frame-node"
        :style="style(node)"
        :node="node"
        :source="models[node.source]"
        :describe-cell="describeCell"
        @event="emit('event', $event)"
      />
      <FrameGraph
        v-else-if="node.kind === 'Graph'"
        ref="graphs"
        class="frame-node"
        :style="style(node)"
        :node="node"
        @event="emit('event', $event)"
      />
      <FrameCode
        v-else-if="node.kind === 'Code'"
        class="frame-node"
        :style="style(node)"
        :node="node"
        @event="emit('event', $event)"
      />
      <component
        v-else-if="node.kind === 'View'"
        :is="views[node.view]?.component"
        :ref="views[node.view]?.captureRef"
        v-bind="views[node.view]?.props"
        class="frame-node frame-child-view"
        :data-frame="node.id"
        :style="style(node)"
      />
    </template>
  </div>
</template>
