<script setup>
import AppButton from '../AppButton.vue';
import AppIcon from '../AppIcon.vue';
import MiddleElide from '../MiddleElide.vue';
defineProps({
  text: String,
  icon: String,
  accent: String,
  dense: Boolean,
  interactive: Boolean,
  maximumWidth: Number,
  disabled: Boolean
});
defineEmits(['click']);
</script>

<template>
  <component
    :is="interactive ? AppButton : 'span'"
    class="status-chip"
    :class="{ dense, interactive }"
    :style="{
      '--chip-accent': accent || 'var(--muted)',
      maxWidth: maximumWidth ? maximumWidth + 'px' : undefined
    }"
    :label="interactive ? text : undefined"
    :translate-label="false"
    :disabled="interactive ? disabled : undefined"
    :title="text"
    @click="interactive && !disabled && $emit('click')"
  >
    <AppIcon v-if="icon" :name="icon" />
    <MiddleElide v-if="dense" :text="text" /><span v-else>{{ text }}</span>
  </component>
</template>

<style>
.status-chip.status-chip {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  gap: var(--status-chip-spacing);
  min-width: 0;
  min-height: var(--status-chip-height);
  height: var(--status-chip-height);
  width: max-content;
  max-width: 100%;
  border: 0;
  border-radius: 12px;
  padding: 0 var(--status-chip-padding);
  background: var(--surface-high);
  color: var(--chip-accent);
  font-size: var(--font-caption-size);
  line-height: var(--font-caption-line-height);
  font-weight: 600;
}
.status-chip > :not(.app-icon) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status-chip > .app-icon {
  flex: none;
  width: var(--status-chip-icon-size);
  height: var(--status-chip-icon-size);
  font-size: var(--status-chip-icon-size);
}
.status-chip.dense {
  height: var(--status-chip-dense-height);
  min-height: var(--status-chip-dense-height);
  padding: 0 var(--status-chip-dense-padding);
  font-size: var(--font-menu-heading-size);
  line-height: var(--font-menu-heading-line-height);
}
.status-chip.dense > .app-icon {
  width: var(--status-chip-dense-icon-size);
  height: var(--status-chip-dense-icon-size);
  font-size: var(--status-chip-dense-icon-size);
}
.status-chip.interactive:hover:not(:disabled) {
  background: color-mix(in srgb, var(--on-surface) 8%, var(--surface-high));
}
.status-chip.interactive:active:not(:disabled) {
  background: color-mix(in srgb, var(--on-surface) 12%, var(--surface-high));
}
</style>
