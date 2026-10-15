<script setup>
// Handler TextArea.qml (EPL-1.0): shared multiline editor; its caller owns the value.
import { ref } from 'vue';
import { t } from '../i18n.js';
defineProps({
  label: String,
  placeholder: String,
  disabled: Boolean,
  errorState: Boolean
});
const model = defineModel({ type: String, default: '' });
const field = ref(null);
defineExpose({
  focus() {
    field.value?.focus();
  }
});
</script>
<template>
  <textarea
    ref="field"
    v-model="model"
    class="app-text-area"
    :aria-invalid="errorState || undefined"
    :aria-label="t(label || placeholder)"
    :placeholder="t(placeholder || '')"
    :disabled="disabled"
  ></textarea>
</template>
<style>
.app-text-area {
  min-width: 0;
  font-size: var(--control-text-size);
  padding: calc(var(--field-area-padding) - 1px)
    calc(var(--field-padding) - 1px);
  resize: vertical;
}
.app-text-area:focus {
  outline: none;
  border: var(--field-focus-border-width) solid var(--field-focus-border);
  padding: calc(var(--field-area-padding) - 2px)
    calc(var(--field-padding) - 2px);
}
.app-text-area:disabled {
  color: var(--disabled);
}
.app-text-area[aria-invalid='true'],
.app-text-area[aria-invalid='true']:focus {
  border-color: var(--field-error-border);
}
</style>
