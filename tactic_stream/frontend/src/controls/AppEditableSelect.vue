<script setup>
import { nextTick, ref, useId, watch } from 'vue';
import AppTextField from './AppTextField.vue';
import AppButton from './AppButton.vue';
import AppMenu from './AppMenu.vue';

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] },
  label: String,
  placeholder: String,
  disabled: Boolean
});
const emit = defineEmits(['update:modelValue', 'accept']);
const owner = ref(null),
  field = ref(null),
  menu = ref(null),
  expanded = ref(false);
const popupId = useId();
const popupWidth = ref(0);
function choose(option) {
  if (props.disabled || option.disabled || option.enabled === false) return;
  emit('update:modelValue', option.value);
  menu.value.close();
  field.value.focus();
}
async function toggle(keyboard = false, last = false) {
  if (props.disabled) return;
  if (menu.value.open) {
    menu.value.close();
    return;
  }
  popupWidth.value = owner.value.getBoundingClientRect().width;
  menu.value.openAt({ target: owner.value.querySelector('input') });
  if (keyboard) {
    await nextTick();
    const options = [
      ...menu.value.$el.querySelectorAll('[role="option"]:not(:disabled)')
    ];
    (
      options.find(
        (option) => option.getAttribute('aria-selected') === 'true'
      ) || (last ? options.at(-1) : options[0])
    )?.focus();
  }
}
function key(event) {
  if (event.isComposing || event.keyCode === 229 || props.disabled) return;
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault();
    toggle(true, event.key === 'ArrowUp');
  } else if (event.key === 'Enter') {
    event.preventDefault();
    emit('accept', props.modelValue);
  }
}
watch(
  () => props.disabled,
  (value) => {
    if (value) menu.value?.close();
  }
);
defineExpose({ focus: () => field.value?.focus() });
</script>

<template>
  <div ref="owner" class="app-editable-select" :class="{ disabled }">
    <AppTextField
      ref="field"
      :model-value="modelValue"
      :label="label"
      :placeholder="placeholder"
      :disabled="disabled"
      role="combobox"
      aria-autocomplete="list"
      :aria-expanded="expanded"
      :aria-controls="popupId"
      tabindex="0"
      @keydown="key"
      @update:model-value="emit('update:modelValue', $event)"
    />
    <AppButton
      class="editable-select-indicator"
      icon-only
      :icon="expanded ? 'expand_less' : 'expand_more'"
      :label="label"
      :disabled="disabled"
      tabindex="-1"
      @click="toggle()"
    />
    <AppMenu
      ref="menu"
      class="editable-select-menu"
      external-trigger
      overlay
      align-start
      :anchor="owner"
      :label="label"
      :width="popupWidth"
      :disabled="disabled"
      :focus-on-open="false"
      :close-on-select="false"
      @toggle="expanded = $event.newState === 'open'"
    >
      <div
        :id="popupId"
        role="listbox"
        :aria-label="label"
        class="editable-select-options"
      >
        <AppButton
          v-for="option in options"
          :key="option.value"
          role="option"
          :label="option.label"
          :translate-label="false"
          :disabled="option.disabled || option.enabled === false"
          :aria-selected="modelValue === option.value"
          @click="choose(option)"
        />
      </div>
    </AppMenu>
  </div>
</template>

<style>
.app-editable-select {
  position: relative;
  min-width: 0;
  height: var(--control-height);
}
.app-editable-select > .app-text-field {
  width: 100%;
  height: 100%;
  padding-left: calc(var(--choice-padding-left) - 1px);
  padding-right: var(--choice-padding-right);
  background: var(--surface-low);
}
.app-editable-select > .app-text-field:focus {
  padding-left: calc(var(--choice-padding-left) - 2px);
  padding-right: calc(var(--choice-padding-right) - 1px);
}
.app-editable-select > .editable-select-indicator {
  position: absolute;
  right: 0;
  top: 0;
  width: var(--choice-indicator-hit);
  min-width: 0;
  height: 100%;
  border: 0;
  border-radius: 0 var(--field-radius) var(--field-radius) 0;
  background: transparent;
  color: var(--muted);
}
.editable-select-indicator .app-icon {
  position: absolute;
  right: var(--choice-indicator-right);
  top: 50%;
  transform: translateY(-50%);
  font-size: var(--choice-indicator-size);
}
.editable-select-menu {
  position: absolute;
  width: 0;
  height: 0;
}
.editable-select-menu > .account-panel {
  padding: var(--choice-popup-padding);
}
.editable-select-options {
  overflow-y: auto;
  overflow-x: hidden;
  max-height: calc(var(--choice-row-height) * var(--choice-visible-rows));
  scrollbar-gutter: stable;
  padding-right: 4px;
}
.editable-select-options > .app-button {
  display: flex;
  justify-content: flex-start;
  width: 100%;
  height: var(--choice-row-height);
  min-height: 0;
  padding: 0 10px 0 12px;
  border: 0;
  border-radius: var(--item-radius);
  background: transparent;
  font-weight: 400;
  text-align: left;
}
.editable-select-options > .app-button:is(:hover, :focus-visible) {
  background: var(--secondary-container);
}
</style>
