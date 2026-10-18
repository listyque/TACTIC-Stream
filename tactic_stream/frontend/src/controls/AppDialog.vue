<script setup>
import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue';
import { t } from '../i18n.js';
import { windowDirective as vWindow } from './window.js';
import { observeFrameSizes } from '../frame/resize.js';
import { fit } from '../../../src/tactic_stream/shared_ui/shell/window.geometry.mjs';

const props = defineProps({
  title: String,
  modal: { type: Boolean, default: true },
  closeOnEscape: { type: Boolean, default: true },
  closeOnOutside: { type: Boolean, default: true },
  ownerMargin: { type: Number, default: 24 }
});
const emit = defineEmits(['closed', 'rejected']);
const dialog = ref(null);
let ownerElement, observer;
function position() {
  const element = dialog.value;
  if (!element?.open) return;
  const owner = ownerElement?.isConnected
    ? ownerElement.getBoundingClientRect()
    : { x: 0, y: 0, width: innerWidth, height: innerHeight };
  element.style.setProperty(
    '--dialog-owner-width',
    Math.max(1, owner.width - props.ownerMargin) + 'px'
  );
  element.style.setProperty(
    '--dialog-owner-height',
    Math.max(1, owner.height - props.ownerMargin) + 'px'
  );
  const box = element.getBoundingClientRect();
  const fitted = fit(
    {
      x: owner.x + (owner.width - box.width) / 2,
      y: owner.y + (owner.height - box.height) / 2,
      width: box.width,
      height: box.height
    },
    { x: 0, y: 0, width: innerWidth, height: innerHeight }
  );
  Object.assign(element.style, {
    left: fitted.x + 'px',
    top: fitted.y + 'px',
    right: 'auto',
    bottom: 'auto',
    margin: '0'
  });
}
function reject() {
  emit('rejected');
  dialog.value.close();
}
function outside(event) {
  const element = dialog.value;
  if (!element?.open || !props.closeOnOutside) return;
  const box = element.getBoundingClientRect();
  const backdrop =
    event.target === element &&
    (event.clientX < box.left ||
      event.clientX > box.right ||
      event.clientY < box.top ||
      event.clientY > box.bottom);
  if (backdrop || (!props.modal && !element.contains(event.target))) reject();
}
onMounted(() => {
  document.addEventListener('pointerdown', outside, true);
  window.addEventListener('resize', position);
  window.addEventListener('windowgeometrychange', position);
  observer = observeFrameSizes(position);
  observer.observe(dialog.value);
});
onBeforeUnmount(() => {
  observer?.disconnect();
  document.removeEventListener('pointerdown', outside, true);
  window.removeEventListener('resize', position);
  window.removeEventListener('windowgeometrychange', position);
});
defineExpose({
  get open() {
    return !!dialog.value?.open;
  },
  show(owner) {
    if (dialog.value.open) return;
    if (ownerElement) observer?.unobserve(ownerElement);
    ownerElement = owner || document.activeElement?.closest('dialog[open]');
    if (ownerElement) observer?.observe(ownerElement);
    if (props.modal) dialog.value.showModal();
    else dialog.value.show();
    position();
    nextTick(position);
  },
  close: () => dialog.value.close(),
  element: () => dialog.value
});
</script>
<template>
  <dialog
    ref="dialog"
    v-window="modal ? false : { type: 'popup' }"
    class="app-dialog"
    :class="{ 'app-dialog-untitled': !title }"
    :aria-label="t(title)"
    @cancel.prevent="closeOnEscape && reject()"
    @close="emit('closed')"
  >
    <header v-if="title" class="app-dialog-titlebar">
      <h2>{{ t(title) }}</h2>
    </header>
    <div class="app-dialog-content"><slot /></div>
  </dialog>
</template>
<style>
.app-dialog {
  position: fixed;
  inset: 0;
  margin: auto;
  padding: 0;
  border: 0;
  border-radius: var(--dialog-radius);
  max-width: min(calc(100dvw - 24px), var(--dialog-owner-width, 100dvw));
  max-height: min(calc(100dvh - 24px), var(--dialog-owner-height, 100dvh));
  background: var(--surface-high);
  color: var(--on-surface);
  box-sizing: border-box;
  box-shadow:
    0 var(--dialog-shadow-y) var(--dialog-shadow-blur) var(--dialog-shadow),
    inset 0 0 0 1px var(--outline-variant);
  overflow: hidden;
}
.app-dialog[open] {
  display: flex;
  flex-direction: column;
}
.app-dialog::backdrop {
  background: var(--scrim);
}
.app-dialog-titlebar {
  flex: none;
  display: flex;
  align-items: center;
  min-width: 0;
  height: var(--dialog-header-height);
  padding: 0 var(--dialog-padding);
  box-sizing: border-box;
  background: var(--surface-highest);
  box-shadow: inset 0 0 0 1px var(--outline-variant);
}
.app-dialog-titlebar > h2 {
  margin: 0;
  font-family: var(--font-family, 'Segoe UI');
  font-size: var(--dialog-title-size);
  font-weight: 600;
  line-height: normal;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.app-dialog-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  min-width: 0;
  box-sizing: border-box;
  padding: calc(var(--dialog-padding) + var(--dialog-spacing))
    var(--dialog-padding) var(--dialog-padding);
}
.app-dialog-untitled > .app-dialog-content {
  padding-top: var(--dialog-padding);
}
</style>
