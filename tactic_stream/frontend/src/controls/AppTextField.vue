<script setup>
// TextField.qml: shared single-line editor; the caller owns its value and actions.
import { computed, ref } from 'vue';
import { t } from '../i18n.js';
const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: String,
  placeholder: String,
  disabled: Boolean,
  errorState: Boolean
});
const emit = defineEmits(['update:modelValue']);
// Vue's text directive owns IME composition; retain this control's string events.
const text = computed({
  get: () => String(props.modelValue ?? ''),
  set: (value) => emit('update:modelValue', String(value))
});
const field = ref(null);
defineExpose({
  focus() {
    field.value?.focus();
  }
});
</script>
<template>
  <input
    ref="field"
    v-model="text"
    class="app-text-field"
    :aria-invalid="errorState || undefined"
    :aria-label="label || placeholder ? t(label || placeholder) : undefined"
    :placeholder="t(placeholder || '')"
    :disabled="disabled"
  />
</template>
<style>
.app-text-field {
  min-width: 0;
  font-size: var(--control-text-size);
  height: var(--control-height);
  padding-inline: calc(var(--field-padding) - 1px);
}
.app-text-field:focus {
  outline: none;
  border: var(--field-focus-border-width) solid var(--field-focus-border);
  padding-inline: calc(var(--field-padding) - 2px);
}
.app-text-field[aria-invalid='true'],
.app-text-field[aria-invalid='true']:focus {
  border-color: var(--field-error-border);
}
.app-text-field:disabled {
  color: var(--disabled);
}
.app-text-field.table-cell {
  appearance: none;
  border: 0;
  border-radius: 0;
  background: transparent;
  padding: 4px 8px;
  box-sizing: border-box;
}
.app-text-field.table-cell:focus {
  border: 0;
  box-shadow: inset 0 0 0 2px var(--primary);
  background: var(--surface-high);
  padding: 4px 8px;
}
</style>
