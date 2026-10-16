<script setup>
// Handler controls/Slider.qml (EPL-1.0): 4px track and 16px handle.
import { t } from '../i18n.js';
defineProps({
  label: String,
  disabled: Boolean,
  min: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  step: { type: Number, default: 1 }
});
const model = defineModel({ type: Number, default: 0 });
</script>
<template>
  <input
    class="app-slider"
    type="range"
    v-model.number="model"
    :style="{
      '--slider-position':
        (max > min
          ? Math.max(0, Math.min(100, ((model - min) / (max - min)) * 100))
          : 0) + '%'
    }"
    :aria-label="t(label)"
    :disabled="disabled"
    :min="min"
    :max="max"
    :step="step"
  />
</template>
<style>
.app-slider {
  appearance: none;
  height: 26px;
  width: 100%;
  min-height: 0;
  margin: 0;
  padding: 0 6px;
  border: 0;
  background: transparent;
  cursor: pointer;
}
.app-slider::-webkit-slider-runnable-track {
  height: 4px;
  border-radius: 2px;
  background: linear-gradient(
    to right,
    var(--primary) var(--slider-position),
    var(--hover) var(--slider-position)
  );
}
.app-slider::-moz-range-track {
  height: 4px;
  border-radius: 2px;
  background: var(--hover);
}
.app-slider::-moz-range-progress {
  height: 4px;
  border-radius: 2px;
  background: var(--primary);
}
.app-slider::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--primary);
  border: 2px solid var(--surface-high);
  margin-top: -6px;
}
.app-slider::-moz-range-thumb {
  box-sizing: border-box;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--primary);
  border: 2px solid var(--surface-high);
}
.app-slider:disabled {
  cursor: default;
  opacity: 0.5;
}
.app-slider:active::-webkit-slider-thumb {
  background: var(--selected);
}
.app-slider:active::-moz-range-thumb {
  background: var(--selected);
}
</style>
