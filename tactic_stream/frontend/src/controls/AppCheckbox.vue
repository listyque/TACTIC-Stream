<script setup>
import { t } from '../i18n.js';
import AppIcon from './AppIcon.vue';
const props = defineProps({
  label: String,
  controlId: String,
  disabled: Boolean,
  indeterminate: Boolean,
  compact: Boolean,
  prominent: Boolean,
  hideLabel: Boolean,
  translateLabel: { type: Boolean, default: true }
});
const model = defineModel({ type: Boolean, default: false });
const emit = defineEmits(['update:modelValue']);
function changed(event) {
  // A mixed value becomes checked in Qt; report intent even when the model was already true.
  if (props.indeterminate) emit('update:modelValue', true);
  else model.value = event.target.checked;
}
</script>

<template>
  <label class="app-checkbox" :class="{ disabled, compact, prominent }"
    ><span class="app-checkbox-indicator"
      ><input
        :id="controlId"
        type="checkbox"
        :checked="!indeterminate && model"
        @change="changed"
        :disabled="disabled"
        :indeterminate="indeterminate"
        :aria-label="
          label ? (translateLabel ? t(label) : label) : undefined
        " /><AppIcon
        v-if="model || indeterminate"
        :name="indeterminate ? 'minus' : 'check'" /></span
    ><slot v-if="!hideLabel">{{
      label ? (translateLabel ? t(label) : label) : ''
    }}</slot></label
  >
</template>
<style>
.app-checkbox.compact {
  min-height: var(--check-box-compact-height);
  gap: var(--check-box-compact-spacing);
  font-size: var(--control-compact-text-size);
}
.app-checkbox.compact .app-checkbox-indicator {
  flex-basis: var(--check-box-compact-indicator);
  width: var(--check-box-compact-indicator);
  height: var(--check-box-compact-indicator);
}
.app-checkbox.compact input {
  width: var(--check-box-compact-indicator);
  height: var(--check-box-compact-indicator);
}
.app-checkbox.compact .app-icon {
  font-size: var(--check-box-compact-icon-size);
}
</style>

<style>
.app-checkbox.prominent {
  --check-box-indicator: var(--check-box-prominent-indicator);
  --check-box-compact-indicator: var(--check-box-prominent-indicator);
  --check-box-icon-size: var(--check-box-prominent-icon-size);
  --check-box-compact-icon-size: var(--check-box-prominent-icon-size);
}
.app-checkbox.prominent input {
  border-width: 2px;
}
.app-checkbox.prominent input:not(:checked):not(:indeterminate):not(:disabled) {
  background: var(--surface-highest);
  border-color: var(--muted);
}
</style>
