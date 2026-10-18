<script setup>
// Handler ComboBox.qml colorRole/actionField.
import { computed } from 'vue';
import AppSelect from './AppSelect.vue';
import { t } from '../i18n.js';
const props = defineProps({
  value: String,
  options: Array,
  disabled: Boolean,
  placeholder: String
});
defineEmits(['change']);
const current = computed(() =>
  props.options.find((option) => option.value === props.value)
);
const choices = computed(() => {
  const rows = props.options.map((option) =>
    option.value === '' && !option.label
      ? {
          ...option,
          label: props.placeholder || t('Select status'),
          disabled: true
        }
      : option
  );
  return rows.some((option) => option.value === '')
    ? rows
    : [
        {
          value: '',
          label: props.placeholder || t('Select status'),
          disabled: true
        },
        ...rows
      ];
});
</script>
<template>
  <div class="status-select" :class="{ empty: !current }">
    <span
      v-if="current?.color"
      class="status-select-dot"
      :style="{ backgroundColor: current.color }"
    ></span>
    <AppSelect
      :model-value="value || ''"
      label="Status"
      :options="choices"
      :translate-labels="false"
      :disabled="disabled"
      @update:model-value="$emit('change', $event)"
    />
  </div>
</template>
<style>
.status-select {
  position: relative;
  min-width: 0;
  height: 28px;
}
.status-select > select {
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 2px 8px 2px 27px;
  appearance: none;
  background: var(--surface);
  border: 0;
  border-radius: 8px;
  color: var(--on-surface);
  font-size: var(--control-text-size);
}
.status-select.empty > select {
  padding-left: 16px;
}
.status-select-dot {
  position: absolute;
  left: 11px;
  top: calc(50% - 4.5px);
  width: 9px;
  height: 9px;
  border-radius: 50%;
  pointer-events: none;
}
</style>
