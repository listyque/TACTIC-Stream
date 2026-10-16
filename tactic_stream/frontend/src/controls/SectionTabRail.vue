<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  shallowRef,
  watch
} from 'vue';
import { t } from '../i18n.js';
import AppButton from './AppButton.vue';
import SectionTabVisual from './SectionTabVisual.vue';
import ActionRows from './ActionRows.vue';
import * as Section from '../../../src/tactic_stream/shared_ui/controls/tabs/section.ui.mjs';
import { displacedTabOffset } from '../../../src/tactic_stream/shared_ui/controls/tabs/tab_layout.mjs';
import * as Workspace from '../../../src/tactic_stream/shared_ui/controls/tabs/workspace.ui.mjs';
import FrameView from '../frame/FrameView.vue';
import { appearance } from '../appearance.js';
import { metrics as themeMetrics } from '../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import { observeFrameSizes } from '../frame/resize.js';

defineOptions({ inheritAttrs: false });
const props = defineProps({
  tabs: { type: Array, default: () => [] },
  selected: String
});
const emit = defineEmits(['select', 'close', 'reorder']);
const host = ref(null),
  panelHeight = ref(260);
const panel = computed(() =>
  Section.panel(panelHeight.value, themeMetrics(appearance.theme).surfaceRadius)
);
const rail = ref(null),
  pressedSection = ref('');
const layoutStyle = {
  '--section-rail-width': Section.metrics.railWidth + 'px',
  '--section-row-height': Section.metrics.rowHeight + 'px',
  '--section-row-gap': Section.metrics.rowSpacing + 'px',
  '--section-inset-top': Section.metrics.top + 'px',
  '--section-inset-bottom': Section.metrics.bottom + 'px',
  '--section-close-allowance': Section.metrics.closeAllowance + 'px',
  '--section-close-icon': Section.metrics.closeIconSize + 'px'
};
const closeStyle = computed(() => {
  const box = Section.closeBounds(revealedWidth.value);
  return {
    left: box.x + 'px',
    top: box.y + 'px',
    width: box.width + 'px',
    height: box.height + 'px'
  };
});
const popup = ref(null);
const revealedId = ref(null);
const revealed = computed({
  get: () => props.tabs.find((tab) => tab.id === revealedId.value) || null,
  set: (tab) => (revealedId.value = tab?.id || null)
});
const actions = ref(false);
const revealedWidth = ref(260),
  revealedPressed = ref(false);
let collapseTimer;
let holdTimer;
let holdFrame;
let held = false;
const drag = shallowRef(null);
let pressed;
let suppressClick = false;

function cancelCollapse() {
  clearTimeout(collapseTimer);
}
function collapse() {
  cancelCollapse();
  collapseTimer = setTimeout(() => {
    if (
      actions.value ||
      drag.value ||
      rail.value?.contains(document.activeElement) ||
      popup.value?.contains(document.activeElement)
    )
      return;
    popup.value?.hidePopover();
    revealed.value = null;
  }, Workspace.dimensions.revealDelay);
}
async function reveal(tab, event) {
  if (pressed) return;
  if (event.type === 'pointerenter' && event.pointerType !== 'mouse') return;
  if (event.type === 'focus' && !event.currentTarget.matches(':focus-visible'))
    return;
  if (actions.value && popup.value?.matches(':popover-open')) return;
  cancelCollapse();
  actions.value = false;
  revealed.value = tab;
  await nextTick();
  if (!popup.value || revealed.value?.id !== tab.id) return;
  positionRevealed();
  if (!revealed.value) return;
  popup.value.showPopover();
}
function select(id) {
  if (held) {
    held = false;
    return;
  }
  popup.value?.hidePopover();
  revealed.value = null;
  emit('select', id);
}
function close(id) {
  popup.value?.hidePopover();
  revealed.value = null;
  emit('close', id);
  nextTick(() => rail.value?.querySelector('[aria-selected="true"]')?.focus());
}
async function openActions(tab, anchor) {
  cancelCollapse();
  const bounds = anchor.getBoundingClientRect();
  actions.value = true;
  revealed.value = tab;
  await nextTick();
  popup.value.style.width = Section.metrics.menuWidth + 'px';
  popup.value.showPopover();
  popup.value.style.top =
    Math.max(
      4,
      Math.min(bounds.bottom, innerHeight - popup.value.offsetHeight - 8)
    ) + 'px';
  popup.value.style.left =
    Math.max(
      4,
      Math.min(bounds.left, innerWidth - popup.value.offsetWidth - 4)
    ) + 'px';
  popup.value.querySelector('button:enabled')?.focus();
}
function menuKey(event) {
  if (
    !actions.value ||
    !['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)
  )
    return;
  const buttons = [...popup.value.querySelectorAll('button:enabled')];
  const index = buttons.indexOf(event.target);
  const command = Workspace.key(
    buttons.map((_, i) => ({ id: String(i) })),
    String(Math.max(0, index)),
    event.key,
    true
  );
  if (command) {
    event.preventDefault();
    buttons[Number(command.id)]?.focus();
  }
}
function press(tab, event) {
  pressedSection.value = tab.id;
  cancelHold();
  held = false;
  if (event.pointerType !== 'touch') return;
  const anchor = event.currentTarget;
  holdTimer = setTimeout(() => {
    held = true;
    openActions(tab, anchor);
  }, Section.metrics.holdDelay);
}
function cancelHold() {
  clearTimeout(holdTimer);
  cancelAnimationFrame(holdFrame);
}
function release(tab, event) {
  pressedSection.value = '';
  cancelHold();
  if (!held) return;
  const anchor = event.currentTarget;
  // Reopen after the touch's native light-dismiss and compatibility click settle.
  holdFrame = requestAnimationFrame(() => {
    holdFrame = requestAnimationFrame(() => {
      if (popup.value && anchor.isConnected) openActions(tab, anchor);
    });
  });
}
function reorder(direction) {
  const index = props.tabs.findIndex((tab) => tab.id === revealed.value.id);
  emit('reorder', index, index + direction);
  popup.value.hidePopover();
  revealed.value = null;
}
function move(event) {
  const buttons = [...rail.value.querySelectorAll('[role="tab"]')];
  let index = buttons.indexOf(event.target);
  if (index < 0) return;
  const action = Workspace.key(
    props.tabs,
    props.tabs[index].id,
    event.key,
    true,
    event.ctrlKey && event.shiftKey
  );
  if (!action) return;
  event.preventDefault();
  if (action.type === 'close') close(action.id);
  else if (action.type === 'reorder')
    emit('reorder', action.source, action.target);
  else buttons[props.tabs.findIndex((tab) => tab.id === action.id)]?.focus();
}
function startDrag(tab, event) {
  suppressClick = false;
  if (
    pressed ||
    event.button !== 0 ||
    !event.isPrimary ||
    event.pointerType === 'touch' ||
    actions.value ||
    revealed.value?.id !== tab.id
  )
    return;
  const boxes = [...rail.value.querySelectorAll('.section-tab-row')].map(
    (node) => {
      const bounds = node.getBoundingClientRect(),
        translated =
          parseFloat(getComputedStyle(node).translate.split(' ')[1]) || 0;
      return {
        top: bounds.top - translated,
        bottom: bounds.bottom - translated,
        height: bounds.height
      };
    }
  );
  pressed = {
    node: event.currentTarget,
    pointer: event.pointerId,
    source: props.tabs.indexOf(tab),
    x: event.clientX,
    y: event.clientY,
    scroll: rail.value.scrollTop,
    top: parseFloat(popup.value.style.top),
    boxes
  };
  cancelCollapse();
  document.addEventListener('pointermove', dragSection, { passive: false });
  document.addEventListener('pointerup', finishDrag);
  document.addEventListener('pointercancel', cancelPointer);
  document.addEventListener('lostpointercapture', cancelPointer);
  document.addEventListener('keydown', cancelKey);
  window.addEventListener('blur', cancelDrag);
}
function dragSection(event) {
  if (!pressed || event.pointerId !== pressed.pointer) return;
  const next = Section.drag(
    pressed,
    { x: event.clientX, y: event.clientY },
    rail.value.scrollTop,
    drag.value ? 0 : Section.metrics.dragThreshold
  );
  if (!next) return;
  if (!drag.value) pressed.node.setPointerCapture(pressed.pointer);
  event.preventDefault();
  drag.value = next;
  const dy = event.clientY - pressed.y;
  popup.value.style.top = pressed.top + dy + 'px';
}
function finishDrag(event) {
  if (!pressed || event.pointerId !== pressed.pointer) return;
  const finished = drag.value;
  cancelDrag();
  if (finished && finished.source !== finished.target)
    emit('reorder', finished.source, finished.target);
}
function cancelPointer(event) {
  if (pressed && event.pointerId === pressed.pointer) cancelDrag();
}
function cancelKey(event) {
  if (event.key !== 'Escape') return;
  event.preventDefault();
  event.stopPropagation();
  cancelDrag();
}
function cancelDrag() {
  const previous = pressed;
  suppressClick ||= !!drag.value;
  pressed = null;
  drag.value = null;
  document.removeEventListener('pointermove', dragSection);
  document.removeEventListener('pointerup', finishDrag);
  document.removeEventListener('pointercancel', cancelPointer);
  document.removeEventListener('lostpointercapture', cancelPointer);
  document.removeEventListener('keydown', cancelKey);
  window.removeEventListener('blur', cancelDrag);
  if (previous?.node.hasPointerCapture(previous.pointer))
    previous.node.releasePointerCapture(previous.pointer);
  nextTick(positionRevealed);
  collapse();
}
let titleMeasure;
function positionRevealed() {
  if (
    !rail.value ||
    !popup.value ||
    !revealed.value ||
    actions.value ||
    drag.value
  )
    return;
  const row = [...rail.value.querySelectorAll('.section-tab-row')].find(
    (node) => node.dataset.sectionId === revealed.value.id
  );
  if (!row) return;
  const bounds = row.getBoundingClientRect(),
    viewport = rail.value.getBoundingClientRect();
  if (bounds.bottom <= viewport.top || bounds.top >= viewport.bottom) {
    popup.value.hidePopover();
    revealed.value = null;
    return;
  }
  titleMeasure ||= document.createElement('canvas').getContext('2d');
  titleMeasure.font =
    (props.selected === revealed.value.id ? '700' : '600') + ' 13px "Segoe UI"';
  revealedWidth.value = Section.expandedWidth(
    titleMeasure.measureText(revealed.value.title).width,
    innerWidth - bounds.left - 4
  );
  popup.value.style.width = revealedWidth.value + 'px';
  popup.value.style.left = bounds.left + 'px';
  popup.value.style.top =
    Math.max(0, Math.min(bounds.top, innerHeight - Section.metrics.rowHeight)) +
    'px';
}
function rowOffset(index) {
  return !drag.value
    ? 0
    : index === drag.value.source
      ? drag.value.translation
      : displacedTabOffset(
          index,
          drag.value.source,
          drag.value.target,
          drag.value.step
        );
}
function afterDrag(event) {
  if (!suppressClick || !event.detail) return;
  suppressClick = false;
  event.preventDefault();
  event.stopPropagation();
}
function resized() {
  cancelDrag();
  cancelCollapse();
  cancelHold();
  popup.value?.hidePopover();
  revealed.value = null;
  actions.value = false;
  held = false;
}
let resizeObserver;
onMounted(() => {
  window.addEventListener('resize', resized);
  resizeObserver = observeFrameSizes(
    (entries) => (panelHeight.value = entries.at(-1).contentRect.height)
  );
  resizeObserver.observe(host.value);
});
onBeforeUnmount(() => {
  window.removeEventListener('resize', resized);
  resizeObserver?.disconnect();
  cancelDrag();
  cancelCollapse();
  cancelHold();
});
watch(
  () => props.tabs.map((tab) => tab.id),
  () => {
    cancelDrag();
    if (
      revealedId.value &&
      !props.tabs.some((tab) => tab.id === revealedId.value)
    ) {
      popup.value?.hidePopover();
      revealed.value = null;
      actions.value = false;
    }
  }
);
watch(
  () => [revealed.value?.title, props.selected],
  () => nextTick(positionRevealed)
);
</script>

<template>
  <div ref="host" v-bind="$attrs" :style="layoutStyle" class="section-tab-host">
    <FrameView class="section-tab-panel" :scene="panel" :interactive="false" />
    <nav
      ref="rail"
      class="section-tab-rail"
      :class="{ reordering: drag }"
      role="tablist"
      aria-orientation="vertical"
      :aria-label="t('Open sections')"
      @keydown="move"
      @scroll="positionRevealed"
      @pointerdown.capture="suppressClick = false"
      @click.capture="afterDrag"
    >
      <div
        v-for="(tab, index) in tabs"
        :key="tab.id"
        class="section-tab-row"
        :class="{
          current: selected === tab.id,
          dragging: drag?.source === index
        }"
        :data-section-id="tab.id"
        :style="{ '--section-drag-y': rowOffset(index) + 'px' }"
        @dragstart.prevent
      >
        <SectionTabVisual
          :width="Section.metrics.railWidth"
          :record="{ ...tab, current: selected === tab.id }"
          :pressed="pressedSection === tab.id"
        />
        <AppButton
          role="tab"
          class="section-tab frame-hit-target"
          :label="tab.title"
          :aria-selected="selected === tab.id"
          :tabindex="selected === tab.id ? 0 : -1"
          :title="tab.title"
          @click="select(tab.id)"
          @auxclick.prevent="$event.button === 1 && close(tab.id)"
          @contextmenu.prevent="openActions(tab, $event.currentTarget)"
          @keydown.shift.f10.prevent="openActions(tab, $event.currentTarget)"
          @pointerdown="
            press(tab, $event);
            startDrag(tab, $event);
          "
          @pointerup="release(tab, $event)"
          @pointercancel="
            pressedSection = '';
            cancelHold();
          "
          @pointermove="cancelHold"
          @pointerenter="reveal(tab, $event)"
          @pointerleave="collapse"
          @focus="reveal(tab, $event)"
        >
          <span hidden aria-hidden="true" />
        </AppButton>
      </div>
    </nav>
  </div>
  <div
    ref="popup"
    :style="layoutStyle"
    class="section-tab-reveal"
    :class="{
      'section-tab-reveal-actions': actions,
      current: selected === revealed?.id,
      dragging: !!drag
    }"
    popover="auto"
    :aria-label="revealed?.title"
    @pointerenter="cancelCollapse"
    @pointerleave="collapse"
    @focusout="collapse"
    @focusin="cancelCollapse"
    @pointerdown.capture="suppressClick = false"
    @click.capture="afterDrag"
    @keydown="menuKey"
    @keydown.esc="
      cancelDrag();
      popup.hidePopover();
      revealed = null;
    "
  >
    <template v-if="revealed && actions">
      <ActionRows
        :actions="
          Section.actions(
            tabs.findIndex((tab) => tab.id === revealed.id),
            tabs.length,
            revealed.title
          )
        "
        @triggered="
          (command) =>
            command === 'close'
              ? close(revealed.id)
              : reorder(command === 'up' ? -1 : 1)
        "
      />
    </template>
    <template v-else-if="revealed">
      <SectionTabVisual
        :width="revealedWidth"
        :record="{ ...revealed, current: selected === revealed.id }"
        revealed
        :pressed="!!drag || revealedPressed"
      />
      <AppButton
        class="section-tab-expanded frame-hit-target"
        :label="revealed.title"
        :aria-pressed="selected === revealed.id"
        @contextmenu.prevent="openActions(revealed, $event.currentTarget)"
        @keydown.shift.f10.prevent="openActions(revealed, $event.currentTarget)"
        @pointerdown="
          revealedPressed = true;
          startDrag(revealed, $event);
        "
        @pointerup="revealedPressed = false"
        @pointercancel="revealedPressed = false"
        @click="select(revealed.id)"
        @auxclick.prevent="$event.button === 1 && close(revealed.id)"
      >
        <span hidden aria-hidden="true" />
      </AppButton>
      <AppButton
        :style="closeStyle"
        icon-only
        icon="close"
        label="Close tab"
        @click="close(revealed.id)"
      />
    </template>
  </div>
</template>

<style>
.section-tab-host {
  position: relative;
  width: var(--section-rail-width);
  min-height: 0;
}
.section-tab-panel {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.section-tab-rail {
  position: relative;
  height: 100%;
  padding-block: var(--section-inset-top) var(--section-inset-bottom);
  box-sizing: border-box;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: var(--section-row-gap);
  overscroll-behavior: contain;
}
.section-tab-row {
  position: relative;
  flex: none;
  width: var(--section-rail-width);
  height: var(--section-row-height);
  translate: 0 var(--section-drag-y, 0px);
}
.section-tab-rail.reordering .section-tab-row {
  transition: translate var(--motion-medium) var(--motion-easing-out-cubic);
}
.section-tab-rail .section-tab-row.dragging {
  z-index: 10;
  transition: none;
}
.section-tab-rail .section-tab.app-button {
  height: var(--section-row-height);
  min-height: var(--section-row-height);
  width: var(--section-rail-width);
  min-width: 0;
  padding: 0;
  border: 0;
  border-radius: 9px;
}
.section-tab-reveal {
  position: fixed;
  inset: auto;
  margin: 0;
  padding: 0;
  border: 0;
  outline: 0;
  border-radius: 9px;
  color: var(--on-surface);
  background: transparent;
  pointer-events: none;
}
.section-tab-reveal:popover-open:not(.section-tab-reveal-actions) {
  display: block;
  height: var(--section-row-height);
  animation: section-tab-enter var(--motion-medium)
    var(--motion-easing-out-cubic);
}
@keyframes section-tab-enter {
  from {
    clip-path: inset(0 calc(100% - 48px) 0 0);
  }
  to {
    clip-path: inset(0);
  }
}
.section-tab-reveal:not(.section-tab-reveal-actions)
  [data-frame='sectionTabSurface'] {
  box-shadow: 2px 6px 16px var(--shadow-color);
}
.section-tab-reveal .section-tab-expanded {
  pointer-events: auto;
  position: absolute;
  inset: 0 var(--section-close-allowance) 0 0;
  height: var(--section-row-height);
  width: calc(100% - var(--section-close-allowance));
  padding: 0;
  border: 0;
  border-radius: 0;
}
.section-tab-reveal:not(.section-tab-reveal-actions) > .icon-button {
  pointer-events: auto;
  position: absolute;
  margin: 0;
  min-width: 0;
  min-height: 0;
}
.section-tab-reveal:not(.section-tab-reveal-actions) > .icon-button .app-icon {
  font-size: var(--section-close-icon);
  width: var(--section-close-icon);
  height: var(--section-close-icon);
}
.section-tab-reveal-actions:popover-open {
  display: block;
  padding: 7px;
  background: var(--surface-high);
  box-shadow: 2px 6px 16px var(--shadow-color);
  pointer-events: auto;
}
</style>
