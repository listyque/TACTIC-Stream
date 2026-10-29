<script setup>
import { ref, nextTick, onMounted, onBeforeUnmount } from 'vue';
import { t } from '../i18n.js';
import AppButton from './AppButton.vue';
import { windowDirective as vWindow } from './window.js';
import { observeFrameSizes } from '../frame/resize.js';
import { fit } from '../../../src/tactic_stream/shared_ui/shell/window.geometry.mjs';

const props = defineProps({
  title: { type: String, default: '' },
  translateTitle: { type: Boolean, default: true },
  windowKind: String,
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
    v-window="
      modal
        ? windowKind
          ? { type: 'dialog', kind: windowKind }
          : false
        : { type: windowKind ? 'window' : 'popup', kind: windowKind || '' }
    "
    class="app-dialog"
    :class="{ 'app-dialog-untitled': !title }"
    :aria-label="translateTitle ? t(title) : title"
    @cancel.prevent="closeOnEscape && reject()"
    @close="emit('closed')"
  >
    <header v-if="title" class="app-dialog-titlebar">
      <h2>{{ translateTitle ? t(title) : title }}</h2>
      <AppButton
        v-if="windowKind"
        label="Close"
        icon="close"
        icon-only
        @click="reject"
      />
    </header>
    <div class="app-dialog-content"><slot /></div>
  </dialog>
</template>
