<script setup>
import AppIcon from '../AppIcon.vue';
import AppButton from '../AppButton.vue';
import { t } from '../../i18n.js';
defineProps({
  title: String,
  message: String,
  icon: { type: String, default: 'info' },
  action: Object,
  error: Boolean
});
defineEmits(['action']);
</script>

<template>
  <div class="empty-state" :role="error ? 'alert' : 'status'">
    <AppIcon :name="icon" :class="{ 'error-icon': error }" />
    <strong v-if="title">{{ t(title) }}</strong>
    <p v-if="message">{{ t(message) }}</p>
    <AppButton
      v-if="action"
      :label="action.label"
      :icon="action.icon"
      :disabled="action.disabled"
      @click="$emit('action', action.command)"
    />
  </div>
</template>

<style>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 0;
  min-height: var(--empty-state-height);
  gap: var(--empty-state-spacing);
  text-align: center;
}
.empty-state > .app-icon {
  width: var(--empty-state-icon-size);
  height: var(--empty-state-icon-size);
  font-size: var(--empty-state-icon-size);
  color: var(--muted);
}
.empty-state > .app-icon.error-icon {
  color: var(--error);
}
.empty-state > strong {
  font-size: var(--font-body-large-size);
  line-height: var(--font-body-large-line-height);
}
.empty-state > p {
  color: var(--muted);
  font-size: var(--font-body-size);
  line-height: var(--font-body-line-height);
}
.empty-state > :is(p, strong) {
  margin: 0;
  max-width: min(var(--empty-state-maximum-width), 100%);
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
</style>
