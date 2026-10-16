<script setup>
import AppButton from '../AppButton.vue';
defineProps({
  emoji: String,
  count: { type: Number, default: 0 },
  checked: Boolean,
  label: String
});
</script>

<template>
  <AppButton
    class="reaction-chip"
    :class="{ checked }"
    :aria-pressed="checked"
    :label="label || emoji"
  >
    <span class="reaction-emoji">{{ emoji }}</span
    ><span v-if="count > 1">{{ count }}</span>
  </AppButton>
</template>

<style>
.reaction-chip.app-button:not(.icon-button) {
  --reaction-mix: calc(var(--reaction-chip-tint-opacity) * 100%);
  display: inline-flex;
  gap: var(--reaction-chip-spacing);
  height: var(--reaction-chip-height);
  min-height: var(--reaction-chip-height);
  min-width: 0;
  width: max-content;
  padding: 0 var(--reaction-chip-padding);
  border: 0;
  border-radius: 14px;
  background: color-mix(
    in srgb,
    var(--cyan) var(--reaction-mix),
    var(--surface-highest)
  );
  color: var(--on-surface);
  font-size: var(--font-body-size);
  line-height: var(--font-body-line-height);
  font-weight: 600;
}
.reaction-chip.app-button.checked:not(.icon-button) {
  --reaction-mix: calc(var(--reaction-chip-checked-tint-opacity) * 100%);
}
.reaction-chip.app-button:not(.icon-button):is(
    :hover,
    :focus-visible,
    :active
  ):not(:disabled) {
  background: color-mix(
    in srgb,
    var(--cyan) var(--reaction-mix),
    var(--surface-highest)
  );
  color: var(--on-surface);
}
.reaction-chip .reaction-emoji {
  display: inline-flex;
  width: var(--reaction-chip-emoji-size);
  flex: none;
  justify-content: center;
  font-family: 'Noto Color Emoji', 'Segoe UI Emoji', sans-serif;
  font-size: var(--reaction-chip-emoji-size);
  font-weight: 400;
  line-height: 1;
}
</style>
