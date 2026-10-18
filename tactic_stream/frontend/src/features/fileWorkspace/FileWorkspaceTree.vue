<script setup>
import AppButton from '../../controls/AppButton.vue';
import WorkspaceTreePaint from './inspection/WorkspaceTreePaint.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/files/workspace/rows.ui.mjs';
import { appearance } from '../../appearance.js';
import { onBeforeUnmount, ref } from 'vue';
import { t } from '../../i18n.js';
defineProps({
  nodes: Array,
  busy: Boolean,
  selected: String,
  label: String,
  selectedIds: Array,
  dropTarget: String,
  canDrop: Boolean,
  dropReason: Function,
  dropCaption: Function,
  canDrag: { type: Boolean, default: true }
});
const emit = defineEmits([
  'expand',
  'select',
  'menu',
  'background',
  'drag',
  'drop',
  'dragover',
  'dragend'
]);
const branch = UI.isBranch;
const title = (node) => UI.treeTitle(node, appearance.language);
const subtitle = (node) => UI.treeSubtitle(node, appearance.language);
const rowStyle = (node) => ({
  '--depth': node.depth,
  height: UI.treeMetrics(node, subtitle(node)).height + 'px'
});
const invalid = ref('');
let hoverTimer,
  frame,
  hoverCode = '';
function endDrag() {
  clearTimeout(hoverTimer);
  cancelAnimationFrame(frame);
  hoverCode = '';
  invalid.value = '';
}
function dragOver(event, node) {
  emit('dragover', event, node);
  if (!event.defaultPrevented) {
    invalid.value = node.id;
    return;
  }
  invalid.value = '';
  if (hoverCode !== node.id) {
    clearTimeout(hoverTimer);
    hoverCode = node.id;
    if (branch(node) && !node.expanded)
      hoverTimer = setTimeout(() => emit('expand', node), 400);
  }
  const tree = event.currentTarget.closest('.file-workspace-branches'),
    bounds = tree.getBoundingClientRect(),
    direction =
      event.clientY < bounds.top + 28
        ? -1
        : event.clientY > bounds.bottom - 28
          ? 1
          : 0;
  cancelAnimationFrame(frame);
  const scroll = () => {
    if (direction) {
      tree.scrollTop += direction * 8;
      frame = requestAnimationFrame(scroll);
    }
  };
  scroll();
}
onBeforeUnmount(endDrag);
function key(event, node) {
  if (event.key === 'ArrowRight' && branch(node) && !node.expanded) {
    event.preventDefault();
    emit('expand', node);
  } else if (event.key === 'ArrowLeft' && branch(node) && node.expanded) {
    event.preventDefault();
    emit('expand', node);
  } else if (['ArrowUp', 'ArrowDown'].includes(event.key)) {
    const rows = [
        ...event.currentTarget.parentElement.querySelectorAll(
          '.file-tree-select'
        )
      ],
      index = rows.indexOf(
        event.currentTarget.querySelector('.file-tree-select')
      );
    rows[index + (event.key === 'ArrowUp' ? -1 : 1)]?.focus();
    event.preventDefault();
  }
}
</script>
<template>
  <div
    class="file-workspace-branches"
    role="tree"
    :aria-label="t(label)"
    @contextmenu.prevent="emit('background', $event)"
  >
    <div
      v-for="node in nodes"
      :key="node.id"
      class="file-tree-row"
      :class="{
        selected: selectedIds?.includes(node.id) || selected === node.id,
        change: node.kind === 'change',
        drop: !!dropTarget && dropTarget === node.code,
        invalid: invalid === node.id
      }"
      role="treeitem"
      :aria-level="node.depth + 1"
      :aria-expanded="branch(node) ? !!node.expanded : undefined"
      :aria-selected="selectedIds?.includes(node.id) || selected === node.id"
      @keydown="key($event, node)"
      :style="rowStyle(node)"
      :data-node="node.id"
      :title="
        invalid === node.id && dropReason
          ? dropReason(node)
          : dropTarget === node.code && dropCaption
            ? dropCaption(node)
            : undefined
      "
      :draggable="
        canDrag &&
        !busy &&
        ['file', 'change', 'directory', 'stream', 'workspace'].includes(
          node.kind
        )
      "
      @contextmenu.prevent.stop="emit('menu', $event, node)"
      @dragstart.stop="emit('drag', $event, node)"
      @dragover="canDrop && dragOver($event, node)"
      @dragleave="endDrag"
      @dragend="
        endDrag();
        emit('dragend');
      "
      @drop.stop="
        endDrag();
        canDrop && emit('drop', $event, node);
      "
    >
      <AppButton
        v-if="branch(node)"
        icon-only
        :icon="node.expanded ? 'chevron-down' : 'next'"
        :aria-label="
          t(node.expanded ? 'Collapse {name}' : 'Expand {name}', {
            name: title(node)
          })
        "
        :disabled="busy"
        @click="emit('expand', node)"
      />
      <span v-else class="file-tree-indent"></span>
      <slot
        v-if="node.kind === 'file' && $slots.file"
        name="file"
        :node="node"
      ></slot>
      <AppButton
        v-else
        class="file-tree-select"
        :aria-label="title(node)"
        :title="title(node)"
        :disabled="busy"
        @click="emit('select', node, $event)"
      >
        <WorkspaceTreePaint
          :row="node"
          :caption="title(node)"
          :subtitle="subtitle(node)"
        />
      </AppButton>
    </div>
    <p v-if="!nodes?.length" class="file-workspace-empty muted">
      {{ t('Nothing to display') }}
    </p>
  </div>
</template>
<style scoped>
.file-workspace-branches {
  overflow: auto;
  scrollbar-gutter: stable;
  min-height: 0;
  flex: 1;
  padding-right: 4px;
}
.file-tree-row {
  display: flex;
  align-items: center;
  min-width: 0;
  position: relative;
  padding-left: calc(min(var(--depth), 8) * 16px + 2px);
  border-radius: var(--item-radius);
}
.file-tree-row.drop {
  outline: 2px solid var(--primary);
}
.file-tree-row.invalid {
  outline: 2px solid var(--error);
}
.file-tree-row:hover {
  background: var(--hover);
}
.file-tree-row.selected {
  background: var(--selected);
}
.file-tree-row > .icon-button,
.file-tree-indent {
  width: 26px;
  min-width: 26px;
  height: 24px;
  flex: none;
}
.file-tree-select {
  display: flex;
  justify-content: flex-start;
  gap: 0;
  min-height: 30px;
  height: 100%;
  min-width: 0;
  flex: 1;
  padding: 0;
  position: relative;
  border: 0;
  border-radius: var(--item-radius);
  text-align: left;
  background: transparent;
}
.file-tree-row.change .file-tree-select {
  height: 42px;
  min-height: 42px;
}
</style>
