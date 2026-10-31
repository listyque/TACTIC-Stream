<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from 'vue';
import AppButton from '../../controls/AppButton.vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import {
  describe,
  shouldClose,
  move
} from '../../../../src/tactic_stream/shared_ui/shell/navigation.ui.mjs';
import { t } from '../../i18n.js';

const props = defineProps({ editable: Boolean, editEnabled: Boolean });
const emit = defineEmits(['closed', 'edit']);
const dialog = ref(null),
  extras = ref(null),
  opened = ref(false);
const width = ref(innerWidth),
  height = ref(innerHeight),
  extraHeight = ref(0),
  top = ref(0);
let entered = false,
  opener,
  observer;
const scene = computed(() =>
  describe(
    {
      width: width.value,
      height: height.value,
      editable: props.editable,
      extraHeight: extraHeight.value
    },
    t
  )
);
const chrome = computed(() => ({
  ...scene.value,
  nodes: scene.value.nodes.filter((node) => node.kind !== 'View')
}));
const positions = computed(() =>
  Object.fromEntries(scene.value.nodes.map((node) => [node.id, node]))
);
function bounds(id) {
  const node = positions.value[id];
  return {
    left: node.x + 'px',
    top: node.y + 'px',
    width: node.width + 'px',
    height: node.height + 'px'
  };
}
async function open(headerHeight) {
  if (opened.value) return;
  opener = document.activeElement;
  top.value = headerHeight;
  width.value = innerWidth;
  height.value = innerHeight - headerHeight;
  entered = false;
  opened.value = true;
  dialog.value.show();
  observer = observeFrameSizes((entries) => {
    extraHeight.value = entries.at(-1).contentRect.height;
  });
  observer.observe(extras.value);
  await nextTick();
  if (opened.value) dialog.value.focus();
}
function close(restoreFocus = true) {
  if (!opened.value) return;
  opened.value = false;
  observer?.disconnect();
  dialog.value.close();
  emit('closed');
  if (restoreFocus && opener?.isConnected) opener.focus();
}
function pointerMoved(event) {
  if (shouldClose(entered, event.pointerType, event.clientX, scene.value.width))
    close();
}
function navigateFromContainer(event) {
  if (event.target !== dialog.value) return;
  const buttons = [
    ...dialog.value.querySelectorAll('[data-entry-key]:not(:disabled)')
  ];
  const result = move(
    buttons.map((button) => ({ id: button.dataset.entryKey })),
    '',
    event.key
  );
  if (!result) return;
  event.preventDefault();
  buttons.find((button) => button.dataset.entryKey === result.id)?.focus();
}
function edit() {
  close(false);
  emit('edit');
}
onBeforeUnmount(() => observer?.disconnect());
defineExpose({ open, close });
</script>

<template>
  <div
    class="navigation-host"
    :style="{ '--workspace-header-height': top + 'px' }"
  >
    <Transition name="navigation-scrim"
      ><div
        v-if="opened"
        class="navigation-backdrop"
        @click="close()"
        @pointermove="pointerMoved"
      ></div
    ></Transition>
    <dialog
      ref="dialog"
      id="workspace-sidebar"
      class="sidebar frame-navigation-drawer"
      tabindex="-1"
      :aria-label="t('Workspace navigation')"
      :style="{ width: scene.width + 'px', height: scene.height + 'px' }"
      @cancel.prevent="close()"
      @keydown.esc.stop.prevent="close()"
      @keydown="navigateFromContainer"
      @pointerenter="entered = true"
    >
      <FrameView :scene="chrome" :interactive="false" />
      <AppButton
        round
        v-if="editable"
        class="navigation-drawer-action"
        :style="bounds('navigationEdit')"
        icon-only
        icon="edit"
        label="Edit navigation"
        :disabled="!editEnabled"
        @click="edit"
      />
      <AppButton
        round
        class="navigation-drawer-action"
        :style="bounds('navigationClose')"
        icon-only
        icon="close"
        label="Close navigation"
        @click="close()"
      />
      <div ref="extras" class="navigation-extras"><slot name="extras" /></div>
      <nav
        class="type-list"
        :aria-label="t('Object types')"
        :style="bounds('navigationContent')"
      >
        <slot />
      </nav>
    </dialog>
  </div>
</template>

<style>
.navigation-host {
  display: contents;
}
.frame-navigation-drawer.sidebar {
  display: block;
  padding: 0;
  border-radius: 0;
  box-shadow: 6px 0 10px var(--scrim);
}
.frame-navigation-drawer.sidebar:not([open]) {
  display: none;
}
.frame-navigation-drawer > .frame-view {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.frame-navigation-drawer .navigation-drawer-action {
  position: absolute;
  margin: 0;
  min-height: 0;
  padding: 0;
}
.frame-navigation-drawer .navigation-extras {
  position: absolute;
  top: 77px;
  width: 100%;
}
.frame-navigation-drawer .type-list {
  position: absolute;
  padding: 0;
  scrollbar-gutter: stable;
  padding-bottom: env(safe-area-inset-bottom);
}
</style>
