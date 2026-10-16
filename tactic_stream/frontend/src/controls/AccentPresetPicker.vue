<script setup>
// Handler controls/AccentPresetPicker.qml (EPL-1.0): 36px tiles, 18px swatches, 7px flow gaps.
import AppButton from './AppButton.vue';
import AppIcon from './AppIcon.vue';
import { readableText } from '../appearance.js';
import { t } from '../i18n.js';
defineProps({ options: Array, mode: String, label: String, disabled: Boolean });
const model = defineModel();
function foreground(hex) {
  return readableText(
    [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16))
  );
}
</script>
<template>
  <div class="accent-preset-picker" role="group" :aria-label="t(label)">
    <AppButton
      v-for="preset in options"
      :key="preset.value"
      :label="preset.label"
      :title="preset.label"
      :disabled="disabled"
      :aria-pressed="model === preset.value"
      :style="{
        '--preset-base': preset[mode + 'Base'],
        '--preset-accent': preset[mode],
        '--preset-text': foreground(preset[mode])
      }"
      @click="model = preset.value"
      ><span
        ><AppIcon
          v-if="model === preset.value"
          name="fontawesome-solid:check" /></span
    ></AppButton>
  </div>
</template>
<style>
.accent-preset-picker {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  width: 100%;
}
.accent-preset-picker > .app-button {
  flex: 0 0 36px;
  min-width: 36px;
  width: 36px;
  height: 36px;
  min-height: 36px;
  padding: 0;
  border-radius: 6px;
  border: 1px solid var(--outline-variant);
  background: var(--preset-base);
}
.accent-preset-picker > .app-button[aria-pressed='true'],
.accent-preset-picker > .app-button:enabled:hover,
.accent-preset-picker > .app-button:focus-visible {
  border: 2px solid var(--preset-accent);
  background: color-mix(in srgb, var(--preset-accent) 8%, var(--preset-base));
}
.accent-preset-picker > .app-button > span {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--preset-accent);
  color: var(--preset-text);
}
.accent-preset-picker .app-icon {
  width: 15px;
  height: 15px;
  font-size: 15px;
}
</style>
