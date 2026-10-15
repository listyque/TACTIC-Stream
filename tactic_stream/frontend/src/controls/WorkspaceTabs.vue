<script setup>
import {
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  shallowRef,
  watch
} from 'vue';
import { t } from '../i18n.js';
import AppButton from './AppButton.vue';
import AppSelect from './AppSelect.vue';
import AppMenu from './AppMenu.vue';
import AppMenuItem from './AppMenuItem.vue';
import AppIcon from './AppIcon.vue';
import { appearance } from '../appearance.js';
import {
  displacedTabOffset,
  fitTabWidths,
  dockTabWidth,
  dockTabHeight,
  dockTab
} from '../../../src/tactic_stream/shared_ui/controls/tabs/tab_layout.mjs';
import { tabTarget } from '../../../src/tactic_stream/shared_ui/shell/dock.layout.mjs';
import { layout } from '../../../src/tactic_stream/shared_ui/core/foundation.mjs';

const props = defineProps({
  tabs: { type: Array, default: () => [] },
  selected: String,
  kind: { type: String, default: 'search' },
  closedTabs: { type: Array, default: () => [] },
  disabled: Boolean,
  reorderable: { type: Boolean, default: true },
  mobile: Boolean
});
const emit = defineEmits([
  'select',
  'add',
  'close',
  'reorder',
  'restore',
  'clear-history'
]);
const list = ref(null);
const menu = ref(null);
const history = ref(null);
const root = ref(null);
const overflow = ref(false);
const compact = ref(false);
const widths = ref([]);
const drag = shallowRef(null);
let pressedTab;
let suppressClick = false;
let observer;

function measure() {
  if (props.mobile) {
    cancelDrag();
    compact.value = true;
    return;
  }
  if (!list.value) return;
  cancelDrag();
  compact.value = root.value.clientWidth < 720;
  const overflowAction =
    props.kind === 'search' ||
    (props.kind === 'script' && !props.closedTabs.length);
  const available =
    list.value.clientWidth + (overflow.value && overflowAction ? 40 : 0);
  if (props.kind === 'script') {
    overflow.value = list.value.scrollWidth > available + 1;
    return;
  }
  if (props.kind === 'dock') {
    widths.value = [
      ...list.value.querySelectorAll(
        '[role="tab"] > span:not(.control-ripple):not(.control-ripple-clip):not(.app-icon)'
      )
    ].map((label) => {
      const range = document.createRange();
      range.selectNodeContents(label);
      return dockTabWidth(
        range.getBoundingClientRect().width,
        available,
        props.tabs.length
      );
    });
    overflow.value =
      widths.value.reduce((sum, width) => sum + width, 0) +
        Math.max(0, props.tabs.length - 1) * dockTab.spacing >
      available + 0.5;
    return;
  }
  const minimum =
    props.kind === 'view'
      ? 128
      : props.kind === 'dock'
        ? 112
        : compact.value
          ? 84
          : 96;
  const current = props.tabs.findIndex((tab) => tab.id === props.selected);
  const natural = [
    ...list.value.querySelectorAll(
      '[role="tab"] > span:not(.control-ripple):not(.control-ripple-clip):not(.app-icon)'
    )
  ].map((label, index) => {
    const range = document.createRange();
    range.selectNodeContents(label);
    const close =
      props.kind !== 'dock' &&
      props.tabs.length > 1 &&
      (!compact.value || index === current);
    const ideal =
      range.getBoundingClientRect().width +
      (props.kind === 'dock' ? 44 : close ? 64 : 32) +
      (props.kind === 'view' ? 24 : 0);
    return Math.max(minimum, compact.value ? Math.min(180, ideal) : ideal);
  });
  const fitted = fitTabWidths(natural, current, available, minimum);
  overflow.value =
    fitted.reduce((sum, width) => sum + width, 0) > available + 1;
  widths.value = fitTabWidths(
    natural,
    current,
    available - (overflow.value ? 40 : 0),
    minimum
  );
}
function containSelected() {
  const tab = [...(list.value?.querySelectorAll('.workspace-tab') || [])].find(
    (node) =>
      node.querySelector('[role="tab"]').dataset.tabId === props.selected
  );
  if (!tab) return;
  const bounds = tab.getBoundingClientRect(),
    viewport = list.value.getBoundingClientRect();
  if (bounds.width > viewport.width || bounds.left < viewport.left)
    list.value.scrollLeft += bounds.left - viewport.left;
  else if (bounds.right > viewport.right)
    list.value.scrollLeft += bounds.right - viewport.right;
}
onMounted(() => {
  observer = new ResizeObserver(() => {
    measure();
    nextTick(containSelected);
  });
  observer.observe(root.value);
  observer.observe(list.value);
  document.fonts.addEventListener('loadingdone', measure);
  measure();
  nextTick(containSelected);
});
watch(
  () => [props.tabs, props.selected, props.closedTabs.length, props.mobile],
  () => nextTick(measure),
  { deep: true }
);
watch(
  () => [props.selected, widths.value],
  () => nextTick(containSelected)
);
watch(
  () => [appearance.language, appearance.theme],
  () => nextTick(measure)
);
watch(
  () => [props.disabled, props.tabs.map((tab) => tab.id).join('\0')],
  cancelDrag,
  { flush: 'sync' }
);
onBeforeUnmount(() => {
  cancelDrag();
  observer?.disconnect();
  document.fonts.removeEventListener('loadingdone', measure);
});

function select(id) {
  emit('select', id);
}
function closable(tab) {
  return props.kind === 'dock'
    ? tab.closable
    : ['script', 'view'].includes(props.kind) || props.tabs.length > 1;
}
async function menuAction(source, action, ...values) {
  source.close(true);
  emit(action, ...values);
  await nextTick();
  if (document.activeElement === document.body)
    root.value?.querySelector('[role="tab"][aria-selected="true"]')?.focus();
}
function move(event) {
  const buttons = [...list.value.querySelectorAll('[role="tab"]')];
  let index = buttons.indexOf(event.target);
  if (index < 0) return;
  if (event.key === 'ArrowRight') index = (index + 1) % buttons.length;
  else if (event.key === 'ArrowLeft')
    index = (index + buttons.length - 1) % buttons.length;
  else if (event.key === 'Home') index = 0;
  else if (event.key === 'End') index = buttons.length - 1;
  else if (event.key === 'Delete' && closable(props.tabs[index])) {
    event.preventDefault();
    emit('close', props.tabs[index].id);
    return;
  } else return;
  event.preventDefault();
  select(props.tabs[index].id);
  buttons[index].focus();
}
function pressTab(event, index) {
  suppressClick = false;
  if (
    pressedTab ||
    props.disabled ||
    !props.reorderable ||
    event.button !== 0 ||
    !event.isPrimary ||
    event.target.closest('button:not([role="tab"])')
  )
    return;
  const node = event.currentTarget;
  pressedTab = {
    node,
    id: event.pointerId,
    index,
    x: event.clientX,
    y: event.clientY,
    available: list.value.clientWidth,
    scroll: list.value.scrollLeft,
    boxes: [...list.value.querySelectorAll('.workspace-tab')].map((tab) => {
      const bounds = tab.getBoundingClientRect(),
        scale = parseFloat(getComputedStyle(tab).scale) || 1;
      // Qt indexAt uses layout geometry, including during the previous scale animation.
      const width = bounds.width / scale,
        left = bounds.left + (bounds.width - width) / 2;
      return { left, right: left + width, width };
    })
  };
  document.addEventListener('pointermove', dragTab, { passive: false });
  document.addEventListener('pointerup', releaseTab);
  document.addEventListener('pointercancel', cancelPointer);
  document.addEventListener('lostpointercapture', cancelPointer);
  document.addEventListener('pointerdown', otherPointer);
  document.addEventListener('keydown', dragKey);
  window.addEventListener('blur', cancelDrag);
  window.addEventListener('resize', cancelDrag);
  window.addEventListener('pagehide', cancelDrag);
}
function dragTab(event) {
  if (!pressedTab || event.pointerId !== pressedTab.id) return;
  const dx = event.clientX - pressedTab.x;
  if (!drag.value) {
    // Qt's default startDragDistance is 10px; keep taps and vertical scrolling intact.
    if (
      Math.abs(dx) < (props.kind === 'dock' ? dockTab.dragThreshold : 10) ||
      Math.abs(dx) < Math.abs(event.clientY - pressedTab.y)
    )
      return;
    pressedTab.node.setPointerCapture(pressedTab.id);
  }
  event.preventDefault();
  const translation = dx + list.value.scrollLeft - pressedTab.scroll;
  const source = pressedTab.boxes[pressedTab.index];
  const center = source.left + source.width / 2 + translation;
  let target = pressedTab.boxes.findIndex(
    (box) => center >= box.left && center < box.right
  );
  if (target < 0)
    target =
      center < pressedTab.boxes[0].left ? 0 : pressedTab.boxes.length - 1;
  if (props.kind === 'dock')
    target = tabTarget(
      pressedTab.boxes.map((box) => box.left + box.width / 2),
      pressedTab.index,
      translation
    );
  drag.value = {
    source: pressedTab.index,
    target,
    translation,
    width: source.width
  };
}
function releaseTab(event) {
  if (!pressedTab || event.pointerId !== pressedTab.id) return;
  const finished =
    pressedTab.available === list.value.clientWidth ? drag.value : null;
  cancelDrag();
  if (finished && finished.source !== finished.target)
    emit('reorder', finished.source, finished.target);
}
function cancelPointer(event) {
  if (!pressedTab || event.pointerId !== pressedTab.id) return;
  // Touch transfers implicit capture from the button to its draggable tab.
  if (event.type === 'lostpointercapture' && event.target !== pressedTab.node)
    return;
  cancelDrag();
}
function otherPointer(event) {
  if (pressedTab && event.pointerId !== pressedTab.id) cancelDrag();
}
function dragKey(event) {
  if (event.key !== 'Escape') return;
  event.preventDefault();
  event.stopPropagation();
  cancelDrag();
}
function cancelDrag() {
  const previous = pressedTab;
  suppressClick ||= !!drag.value;
  pressedTab = null;
  drag.value = null;
  document.removeEventListener('pointermove', dragTab);
  document.removeEventListener('pointerup', releaseTab);
  document.removeEventListener('pointercancel', cancelPointer);
  document.removeEventListener('lostpointercapture', cancelPointer);
  document.removeEventListener('pointerdown', otherPointer);
  document.removeEventListener('keydown', dragKey);
  window.removeEventListener('blur', cancelDrag);
  window.removeEventListener('resize', cancelDrag);
  window.removeEventListener('pagehide', cancelDrag);
  if (previous?.node.hasPointerCapture(previous.id))
    previous.node.releasePointerCapture(previous.id);
}
function tabStyle(index) {
  const offset = drag.value
    ? index === drag.value.source
      ? drag.value.translation
      : displacedTabOffset(
          index,
          drag.value.source,
          drag.value.target,
          drag.value.width
        )
    : 0;
  return {
    width:
      props.kind !== 'script' && widths.value[index]
        ? widths.value[index] + 'px'
        : undefined,
    '--tab-drag-x': offset + 'px'
  };
}
function clickAfterDrag(event) {
  if (!suppressClick || !event.detail) return;
  suppressClick = false;
  event.preventDefault();
  event.stopPropagation();
}
</script>

<template>
  <div
    ref="root"
    class="workspace-tabs"
    :class="{ compact, 'mobile-tabs': mobile }"
    :data-kind="kind"
    :style="{
      '--dock-tab-content-height':
        dockTabHeight(layout.dockTitleHeight, overflow) + 'px',
      '--dock-tab-spacing': dockTab.spacing + 'px',
      '--dock-tab-selected-opacity': dockTab.selectedOpacity,
      '--dock-tab-hovered-opacity': dockTab.hoveredOpacity,
      '--dock-tab-dragging-opacity': dockTab.draggingOpacity,
      '--dock-tab-indicator-thickness': dockTab.indicatorThickness + 'px',
      '--dock-tab-indicator-inset': dockTab.indicatorInset + 'px'
    }"
    @pointerdown.capture="suppressClick = false"
    @click.capture="clickAfterDrag"
  >
    <AppButton
      v-if="kind === 'search' && !mobile"
      icon-only
      icon="add"
      label="Add new search tab"
      :disabled="disabled"
      @click="emit('add')"
    />
    <slot v-if="!mobile" name="before-tabs" />
    <div
      v-show="!mobile"
      ref="list"
      class="workspace-tab-list"
      :class="{ reordering: drag }"
      role="tablist"
      :aria-label="
        t(
          kind === 'view'
            ? 'Work views'
            : kind === 'dock'
              ? 'Workspace panels'
              : kind === 'script'
                ? 'Script tabs'
                : 'Search tabs'
        )
      "
      @keydown="move"
    >
      <div
        v-for="(tab, index) in tabs"
        :key="tab.id"
        class="workspace-tab"
        :class="{
          current: selected === tab.id,
          dirty: tab.dirty,
          dragging: drag?.source === index
        }"
        :style="tabStyle(index)"
        @pointerdown="pressTab($event, index)"
        @dragstart.prevent
        @auxclick.prevent="
          $event.button === 1 && closable(tab) && emit('close', tab.id)
        "
      >
        <AppButton
          role="tab"
          :icon="['dock', 'view'].includes(kind) ? tab.icon : undefined"
          :id="kind === 'dock' ? undefined : 'tab-' + tab.id"
          :aria-controls="
            kind === 'dock'
              ? tab.id === 'results'
                ? 'workspace-data'
                : 'dock-' + tab.id
              : 'panel-' + tab.id
          "
          :label="tab.title"
          :data-tab-id="tab.id"
          :aria-selected="selected === tab.id"
          :tabindex="selected === tab.id ? 0 : -1"
          :disabled="disabled"
          @click="select(tab.id)"
        />
        <AppButton
          v-if="kind !== 'dock' && closable(tab)"
          icon-only
          icon="close"
          :label="
            kind === 'view'
              ? 'Close view tab: {title}'
              : kind === 'script'
                ? 'Close script tab: {title}'
                : 'Close search tab: {title}'
          "
          :aria-label="
            t(
              kind === 'view'
                ? 'Close view tab: {title}'
                : kind === 'script'
                  ? 'Close script tab: {title}'
                  : 'Close search tab: {title}',
              { title: tab.title }
            )
          "
          :title="t('Close tab')"
          :disabled="disabled"
          @click="emit('close', tab.id)"
        />
      </div>
    </div>
    <AppMenu
      v-if="kind === 'script' && (overflow || closedTabs.length)"
      ref="menu"
      class="workspace-tab-menu"
      label="Script tab actions"
      :icon="overflow ? 'MDI_CHEVRON_DOWN' : 'history'"
    >
      <label
        >{{ t(kind === 'script' ? 'Open script tabs' : 'Open search tabs')
        }}<AppSelect
          :model-value="selected"
          :options="tabs.map((tab) => ({ value: tab.id, label: tab.title }))"
          :label="kind === 'script' ? 'Open script tabs' : 'Open search tabs'"
          :disabled="disabled"
          @update:model-value="
            select($event);
            menu.open = false;
          "
      /></label>
      <AppButton
        icon="previous"
        label="Move tab left"
        :disabled="disabled || tabs[0]?.id === selected"
        @click="
          emit(
            'reorder',
            tabs.findIndex((tab) => tab.id === selected),
            tabs.findIndex((tab) => tab.id === selected) - 1
          );
          menu.open = false;
        "
      />
      <AppButton
        icon="next"
        label="Move tab right"
        :disabled="disabled || tabs.at(-1)?.id === selected"
        @click="
          emit(
            'reorder',
            tabs.findIndex((tab) => tab.id === selected),
            tabs.findIndex((tab) => tab.id === selected) + 1
          );
          menu.open = false;
        "
      />
      <AppButton
        v-if="kind === 'script' || tabs.length > 1"
        icon="close"
        label="Close tab"
        :disabled="disabled"
        @click="
          emit('close', selected);
          menu.open = false;
        "
      />
      <template v-if="closedTabs.length">
        <strong>{{
          t(kind === 'script' ? 'Closed script tabs' : 'Closed search tabs')
        }}</strong>
        <AppButton
          v-for="tab in closedTabs"
          :key="tab.id"
          icon="history"
          :label="tab.title"
          @click="
            emit('restore', tab.id);
            menu.open = false;
          "
        />
        <AppButton
          label="Clear tab history"
          @click="
            emit('clear-history');
            menu.open = false;
          "
        />
      </template>
    </AppMenu>
    <AppMenu
      v-if="kind === 'search' && (overflow || mobile)"
      ref="menu"
      overlay
      class="workspace-tab-menu"
      :show-label="mobile"
      label="All search tabs"
      icon="MDI_CHEVRON_DOWN"
    >
      <template v-if="mobile" #trigger
        ><slot name="mobile-leading" /><span class="mobile-tab-title">{{
          tabs.find((tab) => tab.id === selected)?.title
        }}</span
        ><small v-if="tabs.length > 1" class="mobile-tab-count">{{
          tabs.length
        }}</small
        ><AppIcon name="MDI_CHEVRON_DOWN"
      /></template>
      <slot v-if="mobile" name="views" />
      <strong>{{ t('Open search tabs') }}</strong>
      <div
        class="workspace-tab-menu-items"
        role="menu"
        :aria-label="t('Open search tabs')"
      >
        <AppMenuItem
          v-for="(tab, index) in tabs"
          :key="tab.id"
          :label="tab.title"
          icon="tab"
          :translate="false"
          :autofocus="index === 0"
          :checked="selected === tab.id"
          :disabled="disabled"
          :secondary-label="
            tabs.length > 1
              ? t('Close search tab: {title}', { title: tab.title })
              : undefined
          "
          @click="menuAction(menu, 'select', tab.id)"
          @secondary="menuAction(menu, 'close', tab.id)"
        />
      </div>
      <hr />
      <AppButton
        v-if="mobile"
        icon="add"
        label="Add new search tab"
        :disabled="disabled"
        @click="menuAction(menu, 'add')"
      />
      <!-- Web touch/keyboard alternative to dragging, retained from the existing control. -->
      <AppButton
        v-if="!mobile || tabs.length > 1"
        icon="previous"
        label="Move tab left"
        :disabled="disabled || tabs[0]?.id === selected"
        @click="
          menuAction(
            menu,
            'reorder',
            tabs.findIndex((tab) => tab.id === selected),
            tabs.findIndex((tab) => tab.id === selected) - 1
          )
        "
      />
      <AppButton
        v-if="!mobile || tabs.length > 1"
        icon="next"
        label="Move tab right"
        :disabled="disabled || tabs.at(-1)?.id === selected"
        @click="
          menuAction(
            menu,
            'reorder',
            tabs.findIndex((tab) => tab.id === selected),
            tabs.findIndex((tab) => tab.id === selected) + 1
          )
        "
      />
      <template v-if="mobile && closedTabs.length"
        ><hr />
        <strong>{{ t('Closed search tabs') }}</strong
        ><AppMenuItem
          v-for="tab in closedTabs"
          :key="tab.id"
          :label="tab.title"
          icon="history"
          :translate="false"
          :disabled="disabled"
          @click="menuAction(menu, 'restore', tab.id)" /><AppButton
          label="Clear history"
          icon="delete"
          :disabled="disabled"
          @click="menuAction(menu, 'clear-history')"
      /></template>
    </AppMenu>
    <slot name="actions" :compact="compact" />
    <AppMenu
      v-if="kind === 'search' && closedTabs.length && !mobile"
      ref="history"
      overlay
      class="workspace-tab-history"
      :label="
        t(
          closedTabs.length === 1
            ? '{count} recently closed search tab'
            : '{count} recently closed search tabs',
          { count: closedTabs.length }
        )
      "
      icon="history"
    >
      <template #trigger
        ><AppIcon name="history" /><span
          class="workspace-tab-history-count"
          aria-hidden="true"
          >{{ closedTabs.length > 99 ? '99+' : closedTabs.length }}</span
        ></template
      >
      <AppButton
        icon="delete"
        label="Clear history"
        :disabled="disabled"
        autofocus
        @click="menuAction(history, 'clear-history')"
      />
      <hr />
      <div
        class="workspace-tab-menu-items"
        role="menu"
        :aria-label="t('Closed search tabs')"
      >
        <AppMenuItem
          v-for="tab in closedTabs"
          :key="tab.id"
          :label="tab.title"
          icon="history"
          :translate="false"
          :disabled="disabled"
          @click="menuAction(history, 'restore', tab.id)"
        />
      </div>
    </AppMenu>
  </div>
</template>
