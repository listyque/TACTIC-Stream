<script setup>
import { onBeforeUnmount, ref } from 'vue';
import { t } from '../i18n.js';
const props = defineProps({
  label: String,
  horizontal: Boolean,
  min: Number,
  max: Number,
  reverse: Boolean,
  proportional: Boolean,
  disabled: Boolean
});
const model = defineModel({ type: Number, required: true });
const dragging = ref(false);
let gesture = null;
function set(value) {
  model.value = Math.max(props.min, Math.min(props.max, value));
}
function move(event) {
  if (gesture && event.pointerId === gesture.id)
    set(
      gesture.value +
        ((props.horizontal ? event.clientY : event.clientX) -
          gesture.position) *
          gesture.scale *
          (props.reverse ? -1 : 1)
    );
}
function end() {
  gesture = null;
  dragging.value = false;
  window.removeEventListener('pointermove', move);
  window.removeEventListener('pointerup', end);
  window.removeEventListener('pointercancel', end);
  window.removeEventListener('blur', end);
}
function start(event) {
  if (props.disabled || event.button !== 0) return;
  const bounds = event.currentTarget.parentElement.getBoundingClientRect();
  gesture = {
    id: event.pointerId,
    value: model.value,
    position: props.horizontal ? event.clientY : event.clientX,
    scale: props.proportional
      ? 100 / Math.max(1, props.horizontal ? bounds.height : bounds.width)
      : 1
  };
  dragging.value = true;
  event.currentTarget.focus();
  event.preventDefault();
  window.addEventListener('pointermove', move);
  window.addEventListener('pointerup', end);
  window.addEventListener('pointercancel', end);
  window.addEventListener('blur', end);
}
function key(event) {
  if (props.disabled) return;
  const keys = props.horizontal
    ? ['ArrowUp', 'ArrowDown']
    : ['ArrowLeft', 'ArrowRight'];
  if (![...keys, 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  set(
    event.key === 'Home'
      ? props.min
      : event.key === 'End'
        ? props.max
        : model.value +
          (event.key === keys[0] ? -1 : 1) *
            (props.reverse ? -1 : 1) *
            (event.ctrlKey || props.proportional ? 1 : 10)
  );
}
onBeforeUnmount(end);
</script>
<template>
  <div
    class="app-splitter resize-grip"
    :class="{ horizontal, dragging }"
    role="separator"
    :tabindex="disabled ? -1 : 0"
    :aria-disabled="disabled || undefined"
    :aria-label="t(label)"
    :aria-orientation="horizontal ? 'horizontal' : 'vertical'"
    :aria-valuemin="min"
    :aria-valuemax="max"
    :aria-valuenow="Math.round(model)"
    @pointerdown="start"
    @keydown="key"
  />
</template>
