<script setup>
import { computed, reactive, watch, onBeforeUnmount } from 'vue';
import { mobile } from '../../mobile.js';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import DisclosureButton from '../../controls/actions/DisclosureButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import AppCheckbox from '../../controls/AppCheckbox.vue';
import ItemLayout from './ItemLayout.vue';

const props = defineProps({
  editing: Boolean,
  selectedElement: String,
  layout: Object,
  readOnly: Boolean,
  node: Object,
  compact: Boolean,
  card: Boolean,
  tree: Boolean,
  selected: Boolean,
  checked: Boolean,
  selectable: Boolean,
  back: Boolean,
  navigable: { type: Boolean, default: true }
});
const emit = defineEmits([
  'geometry',
  'element',
  'back',
  'upload',
  'expand',
  'activate',
  'doubleclick',
  'newtab',
  'quickaction',
  'relations',
  'inspect',
  'operate',
  'select',
  'preview',
  'notes',
  'tasks',
  'create',
  'completion',
  'link'
]);
const native = computed(() => props.layout.flow === 'contents');
const state = reactive({ controlHover: false, titleActionsFit: true });
const presentation = computed(() => ({
  tree: props.tree,
  card: props.card,
  compact: props.compact,
  back: props.back,
  selectable: props.selectable,
  checked: props.checked,
  state
}));
let hoverTimer;
function controls(active) {
  clearTimeout(hoverTimer);
  if (active) state.controlHover = true;
  else
    hoverTimer = setTimeout(() => {
      if (!props.node.menuVisible) state.controlHover = false;
    }, 500);
}
watch(
  () => props.node.menuVisible,
  (visible) => {
    if (!visible) controls(false);
  }
);
onBeforeUnmount(() => clearTimeout(hoverTimer));
const title = computed(() =>
  props.node.kind === 'snapshot' && props.node.snapshot_display
    ? props.node.snapshot_display.multiple
      ? t('Multiple files | {count}', {
          count: props.node.snapshot_display.multiple
        })
      : props.node.snapshot_display.title
    : props.node.title ||
      props.node.record?.name ||
      props.node.record?.title ||
      props.node.record?.code ||
      String(props.node.record?.id || '')
);
function activate(event) {
  emit('activate', props.node, event);
}
</script>

<template>
  <article
    class="result-item result-item-configured"
    :class="{
      'item-layout-editing': editing,
      'result-item-native': native,
      'control-hover': state.controlHover,
      'menu-open': node.menuVisible,
      'result-item-card': card,
      'result-item-tree': tree,
      'result-item-compact': compact,
      'result-item-branch': node.kind === 'branch',
      'result-item-object': node.kind === 'object',
      'result-item-snapshot': node.kind === 'snapshot',
      'result-item-process': node.branch?.kind === 'process',
      'result-item-relation': node.branch?.kind === 'relation',
      'result-mobile-header': back,
      selected
    }"
    :style="{
      '--result-depth': node.depth || 0,
      '--result-accent':
        node.accent || node.record?.color || 'var(--content-accent)'
    }"
    :data-result-key="node.record?.__search_key__"
    :data-node-id="node.id"
    :aria-label="title"
    tabindex="0"
    @click="activate"
    @keydown.enter.self.prevent="activate"
    @keydown.space.self.prevent="activate"
    @dblclick="
      !readOnly &&
      !$event.target.closest('button,a,summary') &&
      emit('doubleclick', node, $event)
    "
    @auxclick.middle.prevent="
      (event) => {
        if (!readOnly && !event.target.closest('button,a,summary')) {
          activate(event);
          emit('newtab', node);
        }
      }
    "
    @keydown.right.self.prevent.stop="
      mobile
        ? navigable && activate($event)
        : emit('expand', node, true, $event)
    "
    @keydown.left.self.prevent.stop="
      !mobile && emit('expand', node, false, $event)
    "
    @contextmenu.prevent.stop="
      (event) => {
        if (!readOnly) {
          if (!mobile && !selected) activate(event);
          emit('operate', node, event);
        }
      }
    "
  >
    <span class="result-surface" aria-hidden="true" />
    <span
      v-for="depth in node.depth || 0"
      :key="depth"
      class="result-guide"
      :class="{ 'result-guide-elbow': depth === node.depth }"
      :style="{ left: 11 + (depth - 1) * 24 + 'px' }"
      aria-hidden="true"
    />
    <AppIcon
      v-if="mobile && navigable"
      class="result-mobile-next"
      name="MDI_CHEVRON_RIGHT"
    />
    <AppButton
      v-if="mobile && back"
      class="result-mobile-back"
      label="Back"
      icon="MDI_ARROW_LEFT"
      icon-only
      @click.stop="emit('back')"
    />
    <DisclosureButton
      v-else-if="!mobile && node.hasChildren"
      class="result-expand"
      :identity="node.id"
      :has-children="node.hasChildren"
      :expanded="!!node.expanded"
      :loading="!!node.busy"
      :icon-size="
        node.kind === 'object'
          ? compact
            ? 14
            : 18
          : node.kind === 'branch'
            ? 13
            : 15
      "
      :indicator-size="node.kind === 'object' ? (compact ? 20 : 24) : 18"
      @click.stop="emit('expand', node, undefined, $event)"
    />
    <span v-if="!mobile && !node.hasChildren" class="result-expand-spacer" />
    <AppCheckbox
      v-if="!native && mobile && selectable && !readOnly"
      label="Select record"
      hide-label
      :model-value="checked"
      @click.stop
      @update:model-value="emit('select', node, $event)"
    />
    <ItemLayout
      :presentation="presentation"
      :layout="layout"
      :node="node"
      :read-only="readOnly"
      :editing="editing"
      :selected-element="selectedElement"
      @geometry="emit('geometry', $event)"
      @element="emit('element', $event)"
      @action="(action, ...args) => emit(action, ...args)"
      @completion="(...args) => emit('completion', ...args)"
      @controls="controls"
    />
  </article>
</template>

<style>
.result-item.result-item-configured:not(.result-item-native) {
  height: auto;
  min-height: 0;
  padding: 8px 14px 8px calc(var(--result-depth) * var(--result-indent) + 44px);
}
.result-item-configured:not(.result-item-native).result-item-branch
  .item-widget-image {
  justify-self: center;
  color: var(--result-accent);
}
.result-item-configured:not(.result-item-native).result-item-card {
  display: flex;
  padding: 12px;
}
.result-item-configured > .item-layout {
  flex: 1;
}
@media (max-width: 600px) {
  .result-item.result-item-configured:not(.result-item-native) {
    padding: 12px 32px;
  }
  .result-item-configured:not(.result-item-native) > .app-checkbox {
    position: absolute;
    left: 8px;
    top: 50%;
    transform: translateY(-50%);
  }
  .mobile-results
    .result-item-configured:not(.result-item-native).result-item-object
    .image-picker-preview
    img {
    position: static;
    transform: none;
  }
  .mobile-results
    .result-item-configured:not(.result-item-native).result-item-object
    .image-picker-preview
    > span:not(.app-icon) {
    position: static;
    transform: none;
    width: auto;
  }
  .mobile-results
    .result-item-configured:not(.result-item-native).result-item-object
    .image-picker-preview:has(img) {
    mask-image: none;
  }
  .mobile-results
    .result-item-configured:not(.result-item-native).result-item-object
    .image-picker-preview:has(img)::after {
    display: none;
  }
}
</style>
