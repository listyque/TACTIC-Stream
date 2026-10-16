<script setup>
import { computed, ref, watch } from 'vue';
import AppButton from '../AppButton.vue';
import AppTextField from '../AppTextField.vue';
import * as Numbers from '../../../../src/tactic_stream/shared_ui/controls/forms/number.mjs';
import { appearance } from '../../appearance.js';

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  step: { type: Number, default: 1 },
  decimals: { type: Number, default: 0 },
  label: String,
  disabled: Boolean,
  readonly: Boolean
});
const emit = defineEmits(['update:modelValue']);
const formatted = computed(() =>
  Numbers.format(props.modelValue, props.decimals, appearance.language)
);
const text = ref(formatted.value);
const parsed = computed(() =>
  Numbers.parse(text.value, props.decimals, appearance.language)
);
const invalid = computed(() => parsed.value === null);
watch(formatted, (value) => {
  text.value = value;
});
function accept(value) {
  if (props.disabled || props.readonly) return;
  const next = Numbers.clamp(value, props.min, props.max, props.decimals);
  if (next === null) return;
  text.value = Numbers.format(next, props.decimals, appearance.language);
  if (next !== props.modelValue) emit('update:modelValue', next);
}
function commit() {
  if (invalid.value) text.value = formatted.value;
  else accept(parsed.value);
}
function increment(direction) {
  accept(
    Numbers.step(
      props.modelValue,
      direction,
      props.min,
      props.max,
      props.step,
      props.decimals
    )
  );
}
function key(event) {
  if (event.isComposing || props.disabled || props.readonly) return;
  if (!['ArrowUp', 'ArrowDown', 'Enter', 'Escape'].includes(event.key)) return;
  event.preventDefault();
  if (event.key === 'Escape') text.value = formatted.value;
  else if (event.key === 'Enter') commit();
  else increment(event.key === 'ArrowUp' ? 1 : -1);
}
</script>

<template>
  <div class="app-spin-box" :class="{ disabled }" @keydown="key">
    <AppButton
      icon-only
      icon="chevron-down"
      label="Decrease value"
      :disabled="disabled || readonly || modelValue <= min"
      @click="increment(-1)"
    />
    <AppTextField
      v-model="text"
      inputmode="decimal"
      role="spinbutton"
      :label="label"
      :disabled="disabled"
      :readonly="readonly"
      :min="min"
      :max="max"
      :step="step"
      :aria-valuemin="min"
      :aria-valuemax="max"
      :aria-valuenow="modelValue"
      :error-state="invalid"
      @blur="commit"
    />
    <AppButton
      icon-only
      icon="chevron-up"
      label="Increase value"
      :disabled="disabled || readonly || modelValue >= max"
      @click="increment(1)"
    />
  </div>
</template>

<style>
.app-spin-box {
  position: relative;
  display: flex;
  height: var(--control-height);
  min-width: 0;
}
.app-spin-box > .app-text-field {
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
  text-align: center;
  padding-inline: var(--number-indicator-width);
  appearance: textfield;
}
.app-spin-box input::-webkit-inner-spin-button,
.app-spin-box input::-webkit-outer-spin-button {
  appearance: none;
}
.app-spin-box > .app-button {
  position: absolute;
  inset-block: 0;
  width: var(--number-indicator-width);
  height: 100%;
  z-index: 1;
}
.app-spin-box > .app-button:last-child {
  right: 0;
}
.app-spin-box > .app-button .app-icon {
  font-size: var(--number-icon-size);
}
</style>
