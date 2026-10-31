<script setup>
// Handler ComboBox.qml colorRole/actionField, using the shared browser popup.
import { computed, ref } from 'vue';
import AppMenu from './AppMenu.vue';
import AppButton from './AppButton.vue';
import AppIcon from './AppIcon.vue';
import { t } from '../i18n.js';
const props = defineProps({
  value: String,
  options: { type: Array, default: () => [] },
  disabled: Boolean,
  placeholder: String,
  actionField: { type: Boolean, default: true }
});
const emit = defineEmits(['change']);
const menu = ref(null);
const current = computed(() =>
  props.options.find((option) => option.value === props.value)
);
const emptyLabel = computed(() => props.placeholder || t('Select status'));
const caption = computed(
  () => current.value?.label || props.value || emptyLabel.value
);
const choices = computed(() => {
  const rows = props.options.map((option) =>
    option.value === '' && !option.label
      ? {
          ...option,
          label: emptyLabel.value,
          disabled: true
        }
      : option
  );
  return rows.some((option) => option.value === '')
    ? rows
    : [
        {
          value: '',
          label: emptyLabel.value,
          disabled: true
        },
        ...rows
      ];
});
function choose(option) {
  if (props.disabled || option.disabled || option.enabled === false) return;
  emit('change', option.value);
  menu.value?.close(true);
}
</script>
<template>
  <AppMenu
    ref="menu"
    class="status-select"
    :data-value="value || ''"
    :class="{ 'status-select-field': !actionField }"
    label="Status"
    :disabled="disabled"
    overlay
    align-start
    :close-on-select="false"
  >
    <template #trigger>
      <span
        class="status-select-dot"
        :style="{ backgroundColor: current?.color || 'var(--primary)' }"
        aria-hidden="true"
      ></span>
      <span class="status-select-label">{{ caption }}</span>
      <AppIcon
        v-if="!actionField"
        class="status-select-indicator"
        name="expand_more"
      />
    </template>
    <AppButton
      v-for="option in choices"
      :key="option.value"
      class="status-select-option"
      :data-value="option.value"
      :label="option.label"
      :translate-label="false"
      role="menuitemradio"
      :aria-checked="(value || '') === option.value"
      :disabled="disabled || option.disabled || option.enabled === false"
      @click="choose(option)"
    >
      <span
        class="status-select-dot"
        :style="{ backgroundColor: option.color || 'var(--primary)' }"
        aria-hidden="true"
      ></span>
      <span class="status-select-label">{{ option.label }}</span>
      <AppIcon v-if="(value || '') === option.value" name="check" />
    </AppButton>
  </AppMenu>
</template>
<style>
.status-select.workspace-menu {
  width: 100%;
  min-width: 0;
  height: 28px;
  font-size: var(--control-text-size);
  font-weight: 400;
}
.workspace-menu.status-select > summary.icon-button {
  display: flex;
  justify-content: flex-start;
  gap: 7px;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 0 11px;
  background: var(--surface);
  border: 0;
  border-radius: var(--item-radius);
  color: var(--on-surface);
  font: inherit;
}
.workspace-menu.status-select > summary:hover {
  background: var(--surface-high);
}
.workspace-menu.status-select > summary[aria-disabled='true'] {
  color: var(--disabled);
}
.status-select .status-select-dot {
  flex: none;
  width: 9px;
  height: 9px;
  border-radius: 50%;
}
.status-select-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: start;
}
.status-select.status-select-field {
  height: var(--control-height);
}
.workspace-menu.status-select-field > summary.icon-button {
  border: 1px solid var(--outline-variant);
  border-radius: var(--field-radius);
}
.status-select-field[open] > summary > .status-select-indicator {
  transform: rotate(180deg);
}
.status-select .status-select-option {
  gap: 7px;
}
.status-select .status-select-option[aria-checked='true']:not(:disabled) {
  background: var(--selected);
  color: var(--on-selected);
}
</style>
