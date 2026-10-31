<script setup>
import AppButton from './AppButton.vue';
defineProps({ checked: Boolean });
</script>
<template>
  <AppButton class="app-tab-button" :aria-pressed="checked" />
</template>
<style>
.app-tab-button.app-button:not(.icon-button) {
  border: 0;
  background: transparent;
  border-radius: var(--button-radius);
  font-size: var(--control-text-size);
  font-weight: 400;
  padding: 0 6px;
  height: var(--control-height);
}
.app-tab-button.app-button:not(.icon-button):hover:not(:disabled) {
  background: var(--hover);
}
.app-tab-button.app-button:not(.icon-button)[aria-pressed='true'] {
  border: 1px solid var(--primary);
  color: var(--primary);
  background: var(--secondary-container);
  font-weight: 600;
}
</style>
