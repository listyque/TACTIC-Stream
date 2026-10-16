<script setup>
import AppButton from '../AppButton.vue';
defineProps({
  icon: { type: String, default: 'chevron-right' },
  label: String
});
</script>

<template>
  <AppButton
    class="preview-navigation-button"
    icon-only
    :icon="icon"
    :label="label"
  />
</template>

<style>
.preview-navigation-button.app-button.icon-button {
  --ripple-inset: 0px;
  padding: 0;
  background-clip: border-box;
  width: 40px;
  height: 84px;
  min-height: 0;
  border-radius: var(--item-radius);
  background: var(--surface-high);
  color: var(--on-surface);
}
.preview-navigation-button.app-button.icon-button > .app-icon {
  width: 18px;
  height: 18px;
  font-size: 18px;
}
</style>
