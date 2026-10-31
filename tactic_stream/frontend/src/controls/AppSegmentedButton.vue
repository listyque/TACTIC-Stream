<script setup>
import { computed } from 'vue';
import AppButton from './AppButton.vue';
import { t } from '../i18n.js';
import * as Segments from '../../../src/tactic_stream/shared_ui/controls/forms/segmented.mjs';
const props = defineProps({
  options: { type: Array, default: () => [] },
  label: String,
  disabled: Boolean,
  outlined: Boolean,
  iconOnly: Boolean,
  iconSize: { type: Number, default: 15 }
});
const model = defineModel();
const emit = defineEmits(['update:modelValue']);
const entry = computed(() => Segments.entry(props.options, model.value));
function choose(option) {
  if (props.disabled || !Segments.selectable(option)) return;
  if (model.value !== option.value) model.value = option.value;
  else if (option.reselectable) emit('update:modelValue', option.value);
}
function move(event) {
  if (
    props.disabled ||
    event.isComposing ||
    event.altKey ||
    event.ctrlKey ||
    event.metaKey
  )
    return;
  const index = Segments.target(props.options, model.value, event.key);
  if (index < 0) return;
  event.preventDefault();
  choose(props.options[index]);
  event.currentTarget.querySelectorAll('button')[index].focus();
}
</script>
<template>
  <div
    class="app-segmented-button"
    :class="{ outlined }"
    :style="{ '--segmented-icon-size': iconSize + 'px' }"
    role="radiogroup"
    :aria-label="t(label)"
    @keydown="move"
  >
    <AppButton
      v-for="(option, index) in options"
      :key="option.value"
      :label="option.label"
      :translate-label="option.translate !== false"
      :icon="option.icon"
      :icon-only="iconOnly"
      role="radio"
      :aria-checked="model === option.value"
      :tabindex="!disabled && index === entry ? 0 : -1"
      :disabled="disabled || !Segments.selectable(option)"
      @click="choose(option)"
    />
  </div>
</template>
<style>
/* Qt's 3px content inset includes the CSS 1px border. */
.app-segmented-button {
  display: flex;
  padding: 2px;
  height: var(--control-height);
  border: 1px solid var(--outline-variant);
  border-radius: var(--button-radius);
  background: var(--surface-high);
}
.app-segmented-button .app-button {
  flex: 1;
  min-width: 0;
  height: 100%;
  min-height: 0;
  padding: 0 5px;
  border: 0;
  border-radius: var(--button-radius);
  background: transparent;
  gap: 6px;
  font-size: var(--control-text-size);
  font-weight: 400;
}
.app-segmented-button .app-button[aria-checked='true'] {
  background: var(--selected);
  color: var(--on-selected);
  font-weight: 600;
}
.app-segmented-button .app-button > .app-icon {
  width: var(--segmented-icon-size);
  height: var(--segmented-icon-size);
  font-size: var(--segmented-icon-size);
  color: var(--muted);
  flex: none;
}
.app-segmented-button .app-button:disabled > .app-icon {
  color: var(--disabled);
}
.app-segmented-button
  .app-button
  > span:not(.app-icon):not(.control-ripple-clip) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.app-segmented-button [aria-checked='true'] .app-icon {
  color: inherit;
}
.app-segmented-button.outlined {
  background: transparent;
  border: 0;
  padding: 3px;
}
.app-segmented-button.outlined .app-button {
  border: 1px solid transparent;
}
.app-segmented-button.outlined .app-button[aria-checked='true'] {
  border: 1px solid var(--primary);
  background: var(--surface-high);
  color: var(--primary);
}
</style>
