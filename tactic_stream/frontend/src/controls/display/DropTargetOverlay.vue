<script setup>
import AppIcon from '../AppIcon.vue';
import { t } from '../../i18n.js';
defineProps({ prompt: String, accepted: { type: Boolean, default: true } });
</script>

<template>
  <div
    class="drop-target-overlay"
    :class="{ rejected: !accepted }"
    role="status"
  >
    <AppIcon :name="accepted ? 'move-to-inbox' : 'cancel'" />
    <strong>{{ t(prompt) }}</strong>
  </div>
</template>

<style>
.drop-target-overlay {
  position: absolute;
  inset: var(--drop-target-margin);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--drop-target-spacing);
  border: var(--drop-target-border-width) solid var(--primary);
  border-radius: var(--surface-radius);
  background: var(--surface-high);
  opacity: var(--drop-target-surface-opacity);
  pointer-events: none;
}
.drop-target-overlay > .app-icon {
  width: var(--drop-target-icon-size);
  height: var(--drop-target-icon-size);
  font-size: var(--drop-target-icon-size);
  color: var(--primary);
}
.drop-target-overlay > strong {
  max-width: calc(100% - 24px);
  overflow-wrap: anywhere;
  text-align: center;
  font-size: var(--drop-target-text-size);
  line-height: var(--font-secondary-line-height);
  font-weight: 600;
}
.drop-target-overlay.rejected {
  border-color: var(--error);
}
.drop-target-overlay.rejected > .app-icon {
  color: var(--error);
}
</style>
