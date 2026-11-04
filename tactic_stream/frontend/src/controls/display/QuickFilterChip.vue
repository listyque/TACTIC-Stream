<script setup>
import { computed } from 'vue';
import AppButton from '../AppButton.vue';
import AppIcon from '../AppIcon.vue';
import { filterGeometry } from '../../../../src/tactic_stream/shared_ui/controls/display/chips.mjs';
const props = defineProps({
  text: String,
  icon: String,
  accent: String,
  showAccentMarker: Boolean,
  subtle: Boolean,
  round: Boolean,
  checked: Boolean,
  emphasis: { type: Number, default: 0 },
  maximumWidth: Number
});
const geometry = computed(() => filterGeometry(props.emphasis));
</script>

<template>
  <AppButton
    class="quick-filter-chip"
    :class="{ checked, subtle, round }"
    :label="text"
    :translate-label="false"
    :aria-pressed="checked"
    :style="{
      '--chip-accent': accent || 'var(--primary)',
      height: geometry.height + 'px',
      fontSize: geometry.fontSize + 'px',
      lineHeight: geometry.lineHeight + 'px',
      maxWidth: maximumWidth ? maximumWidth + 'px' : undefined
    }"
  >
    <span class="quick-filter-chip-content"
      ><i v-if="showAccentMarker" class="quick-filter-accent"></i
      ><AppIcon
        v-if="icon"
        :name="icon"
        :style="{
          width: geometry.iconSize + 'px',
          height: geometry.iconSize + 'px',
          fontSize: geometry.iconSize + 'px'
        }"
      /><span class="tag-label">{{ text }}</span></span
    >
  </AppButton>
</template>

<style scoped>
.quick-filter-chip.app-button:not(.icon-button) {
  --chip-surface: transparent;
  --chip-content: var(--on-surface);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  min-height: 0;
  width: max-content;
  max-width: 100%;
  border: 1px solid var(--outline);
  border-radius: var(--button-radius);
  padding: 0 8px;
  background: var(--chip-surface);
  color: var(--chip-content);
  font-weight: 600;
}
.quick-filter-chip.round.app-button:not(.icon-button) {
  border-radius: 999px;
}
.quick-filter-chip.app-button:not(.icon-button).checked {
  --chip-surface: var(--chip-accent);
  --chip-content: var(--on-selected);
  border-color: var(--chip-accent);
}
.quick-filter-chip.app-button:not(.icon-button).checked.subtle {
  --chip-surface: color-mix(in srgb, var(--chip-accent) 16%, transparent);
  --chip-content: var(--on-surface);
}
.quick-filter-chip.app-button:not(.icon-button):is(
    :hover,
    :focus-visible,
    :active
  ):not(:disabled) {
  background: var(--chip-surface);
  color: var(--chip-content);
}
.quick-filter-chip .quick-filter-chip-content {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  flex: 0 1 auto;
  width: max-content;
}
.quick-filter-chip-content > .app-icon {
  flex: none;
  color: var(--muted);
}
.quick-filter-chip.checked .quick-filter-chip-content > .app-icon {
  color: var(--on-selected);
}
.quick-filter-chip.checked.subtle .quick-filter-chip-content > .app-icon {
  color: var(--chip-accent);
}
.quick-filter-chip-content > i {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 4px;
  background: var(--chip-accent);
}
.quick-filter-chip-content > span:not(.app-icon) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
