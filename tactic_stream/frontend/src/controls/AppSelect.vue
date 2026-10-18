<script setup>
import { computed } from 'vue';
import { t } from '../i18n.js';
import AppIcon from './AppIcon.vue';

const props = defineProps({
  options: { type: Array, default: () => [] },
  label: String,
  displayPrefix: String,
  swatchMode: String,
  translateLabels: { type: Boolean, default: true }
});
const model = defineModel();
const customizable = CSS.supports('appearance', 'base-select');
const decorated = computed(
  () => customizable && props.options.some((item) => item.icon)
);
const selectedOption = computed(() =>
  props.options.find((item) => item.value === model.value)
);
const optionLabel = (item) =>
  props.translateLabels ? t(item.label) : item.label;
</script>

<template>
  <select
    class="app-select"
    :style="
      displayPrefix
        ? { '--select-display-prefix': JSON.stringify(displayPrefix) }
        : undefined
    "
    v-model="model"
    :aria-label="label ? t(label) : undefined"
  >
    <button v-if="customizable" type="button" class="app-select-trigger">
      <span class="app-select-selected-content">
        <AppIcon
          v-if="decorated && selectedOption?.icon"
          :name="selectedOption.icon"
        />
        <span
          v-if="swatchMode && selectedOption"
          class="palette-swatch"
          :style="{
            backgroundColor: selectedOption[swatchMode],
            borderColor: selectedOption[swatchMode + 'Base']
          }"
        />
        <span class="app-select-option-label">{{
          selectedOption ? optionLabel(selectedOption) : model
        }}</span>
      </span>
      <AppIcon name="expand_more" class="app-select-indicator" />
    </button>
    <option
      v-if="
        model !== undefined && !options.some((item) => item.value === model)
      "
      :value="model"
    >
      {{ model }}
    </option>
    <component
      is="option"
      v-for="item in options"
      :key="item.value"
      :value="item.value"
      :disabled="item.disabled || item.enabled === false"
      ><AppIcon v-if="decorated && item.icon" :name="item.icon" /><span
        v-if="swatchMode"
        class="palette-swatch"
        :style="{
          backgroundColor: item[swatchMode],
          borderColor: item[swatchMode + 'Base']
        }"
      ></span
      ><span class="app-select-option-label">{{
        optionLabel(item)
      }}</span></component
    >
  </select>
</template>

<style>
.app-select {
  font-size: var(--control-text-size);
  background: var(--surface);
  border-color: var(--outline-variant);
}
.app-select:disabled {
  color: var(--disabled);
}
.app-select:focus {
  border: var(--field-focus-border-width) solid var(--field-focus-border);
  padding-inline: 9px 7px;
}
.app-select > .app-select-trigger {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  min-height: 0;
  border: 0;
  border-radius: 0;
  padding: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: start;
}
.app-select .app-select-selected-content {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  flex: 1;
}
.app-select .app-select-indicator {
  flex: none;
  width: 17px;
  height: 17px;
  font-size: 17px;
  color: var(--muted);
}
@supports (appearance: base-select) {
  .app-select {
    padding-inline: 10px 8px;
  }
  .app-select::picker-icon {
    display: none;
  }
  .app-select:open .app-select-indicator {
    transform: rotate(180deg);
  }
}
.app-select :is(option, .app-select-selected-content) > .app-icon {
  width: 15px;
  height: 15px;
  flex: 0 0 15px;
  font-size: 15px;
}
.app-select .app-select-selected-content > .app-select-option-label {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.app-select .app-select-selected-content > .app-icon {
  color: var(--muted);
}
</style>

<style>
.app-select
  > .app-select-trigger
  .app-select-selected-content
  .app-select-option-label::before {
  content: var(--select-display-prefix, '');
}
</style>
