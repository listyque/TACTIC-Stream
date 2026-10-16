<script setup>
import AppButton from '../AppButton.vue';
import BusyIndicator from '../BusyIndicator.vue';
import { t } from '../../i18n.js';
defineProps({
  message: { type: String, default: 'Loading…' },
  cancellable: Boolean,
  disabled: Boolean
});
defineEmits(['cancel']);
</script>

<template>
  <div
    class="content-loading-overlay"
    role="status"
    aria-busy="true"
    @pointerdown.stop
    @click.stop
  >
    <div>
      <BusyIndicator running /><strong>{{ t(message) }}</strong
      ><AppButton
        v-if="cancellable"
        label="Cancel"
        :disabled="disabled"
        @click="$emit('cancel')"
      />
    </div>
  </div>
</template>

<style>
.content-loading-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  isolation: isolate;
}
.content-loading-overlay::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  background: var(--page);
  opacity: var(--loading-overlay-surface-opacity);
}
.content-loading-overlay > div {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--loading-overlay-spacing);
  width: min(
    var(--loading-overlay-maximum-width),
    max(
      var(--loading-overlay-minimum-width),
      calc(100% - var(--loading-overlay-horizontal-margin))
    )
  );
}
.content-loading-overlay strong {
  text-align: center;
  font-size: 12px;
  line-height: 14px;
  font-weight: 600;
  color: var(--muted);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.content-loading-overlay .busy-indicator {
  width: 24px;
  height: 24px;
}
</style>
