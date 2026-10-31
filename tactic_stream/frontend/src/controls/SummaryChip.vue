<script setup>
// SummaryChip.qml: one presentation for groups, statuses and processes.
import AppButton from './AppButton.vue';
import AppIcon from './AppIcon.vue';
defineProps({
  label: String,
  count: Number,
  accent: String,
  icon: String,
  compact: Boolean,
  clickable: Boolean,
  showDot: { type: Boolean, default: true },
  showCount: { type: Boolean, default: true }
});
defineEmits(['click']);
</script>
<template>
  <component
    :is="clickable ? AppButton : 'div'"
    class="summary-chip"
    :class="{ clickable, compact }"
    :label="
      clickable
        ? label + (showCount && count != null ? ' ' + count : '')
        : undefined
    "
    :style="{ '--chip-accent': accent || 'var(--primary)' }"
    @click="clickable && $emit('click')"
    ><AppIcon v-if="icon" :name="icon" /><i v-if="showDot"></i
    ><span>{{ label }}</span
    ><small v-if="showCount">{{ count }}</small></component
  >
</template>
<style>
.summary-chip,
.summary-chip.app-button {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  gap: var(--summary-chip-spacing);
  width: max-content;
  min-height: var(--summary-chip-height);
  height: var(--summary-chip-height);
  padding: 0 calc(var(--summary-chip-padding) - 1px);
  border: 1px solid var(--outline-variant);
  border-radius: 15px;
  background: var(--surface-high);
  color: var(--on-surface);
  font-size: var(--font-secondary-size);
  line-height: var(--font-secondary-line-height);
  font-weight: 400;
}
.summary-chip i {
  width: var(--summary-chip-dot);
  height: var(--summary-chip-dot);
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--chip-accent);
}
.summary-chip > span {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.summary-chip small {
  flex-shrink: 0;
  color: var(--chip-accent);
  font-size: inherit;
  font-weight: 600;
}
.summary-chip.clickable:hover {
  background: var(--hover);
}
.summary-chip.clickable:focus-visible {
  border-color: var(--primary);
}
</style>
<style>
.summary-chip.compact {
  height: var(--summary-chip-compact-height);
  min-height: var(--summary-chip-compact-height);
  padding: 0 var(--summary-chip-compact-padding);
  border: 0;
  color: var(--chip-accent);
  font-size: var(--font-caption-size);
  line-height: var(--font-caption-line-height);
}
.summary-chip.compact .app-icon {
  font-size: 14px;
}
.summary-chip {
  justify-content: center;
}
</style>

<style>
.summary-chip.clickable {
  border-radius: var(--button-radius);
}
</style>
