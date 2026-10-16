<script setup>
import { t } from '../i18n.js';
import { computed } from 'vue';
import { buttonVariables } from './controlAppearance.js';
import AppIcon from './AppIcon.vue';
import { ripple } from './ripple.js';
import { capturePress } from './activation.js';
import { tooltipDirective as vTooltip } from './tooltip.js';

const props = defineProps({
  label: { type: String, default: '' },
  translateLabel: { type: Boolean, default: true },
  tooltip: String,
  icon: String,
  iconOnly: Boolean,
  highlighted: Boolean,
  destructive: Boolean,
  tonal: Boolean,
  segmented: Boolean,
  checked: Boolean,
  badgeCount: { type: Number, default: 0 },
  showZeroBadge: Boolean,
  type: { type: String, default: 'button' },
  href: String
});
const paint = computed(() => buttonVariables(props));
</script>

<template>
  <component
    :is="href ? 'a' : 'button'"
    class="app-button"
    :style="paint"
    :href="href"
    :type="href ? undefined : type"
    :class="{
      'icon-button': iconOnly,
      primary: highlighted,
      danger: destructive,
      tonal
    }"
    v-tooltip="
      tooltip
        ? t(tooltip)
        : iconOnly && label
          ? translateLabel
            ? t(label)
            : label
          : ''
    "
    :aria-label="label ? (translateLabel ? t(label) : label) : undefined"
    @pointerdown="
      capturePress($event);
      ripple($event);
    "
  >
    <AppIcon v-if="icon" :name="icon" />
    <slot
      ><span v-if="!iconOnly">{{
        translateLabel ? t(label) : label
      }}</span></slot
    >
    <span
      v-if="badgeCount > 0 || showZeroBadge"
      class="app-button-badge"
      aria-hidden="true"
      >{{ badgeCount > 99 ? '99+' : badgeCount }}</span
    >
  </component>
</template>
<style>
.app-button:not(.icon-button) {
  gap: var(--button-spacing);
  min-width: var(--button-minimum-width);
  min-height: var(--control-height);
  border-radius: var(--button-radius);
  background: var(--button-idle-background);
  color: var(--button-idle-color);
  border: var(--button-idle-border-width) solid var(--button-idle-border);
  font-size: var(--control-text-size);
}
.app-button > span:not(.app-button-badge) {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.app-button > .app-icon {
  flex: none;
  width: 16px;
  height: 16px;
}
.app-button.icon-button > .app-icon {
  width: var(--compact-icon-size);
  height: var(--compact-icon-size);
}
.app-button:not(.icon-button):hover:not(:disabled) {
  background: var(--button-hover-background);
  color: var(--button-hover-color);
  border-color: var(--button-hover-border);
}
.app-button:not(.icon-button):focus-visible:not(:disabled) {
  background: var(--button-focus-background);
  color: var(--button-focus-color);
}
.app-button:not(.icon-button):active:not(:disabled) {
  background: var(--button-pressed-background);
  color: var(--button-pressed-color);
}
.app-button:not(.icon-button):disabled {
  opacity: 1;
  background: var(--button-disabled-background);
  color: var(--button-disabled-color);
}
.app-button:where(:not(.icon-button)) {
  padding-inline: var(--button-padding);
  gap: var(--button-spacing);
}
.app-button:where(:not(.icon-button)):where(:has(> .app-icon)) {
  padding-inline-start: var(--button-icon-padding);
}
.app-button.primary,
.app-button.primary:hover:not(:disabled) {
  color: var(--on-selected);
}
.app-button.danger.primary,
.app-button.danger.primary:hover:not(:disabled) {
  color: var(--on-error);
}
a.app-button.icon-button {
  padding: 0;
  border: 0;
  border-radius: 50%;
  background: transparent;
}
a.app-button.icon-button:hover,
a.app-button.icon-button:focus-visible {
  background: color-mix(in srgb, currentColor 8%, transparent);
}
.app-button.tonal {
  background: var(--hover);
  border-color: var(--outline-variant);
  border-radius: var(--button-radius);
}
.app-button:has(> .app-button-badge) {
  overflow: visible;
}
.icon-button:has(> .app-button-badge, > .action-count) {
  overflow: visible;
}
.icon-button > :is(.app-button-badge, .action-count) {
  top: -4px;
  right: -4px;
}
.app-button-badge {
  position: absolute;
  top: -1px;
  right: -1px;
  box-sizing: border-box;
  min-width: 16px;
  height: 16px;
  padding: 0 2px;
  border: 2px solid var(--surface);
  border-radius: 8px;
  background: var(--error);
  color: var(--on-selected);
  font-size: var(--text-caption);
  font-weight: 700;
  line-height: 12px;
  text-align: center;
  pointer-events: none;
  z-index: 2;
}
</style>

<style>
/* Frame paints the row; this native button owns input and its accessible name. */
.app-button.frame-hit-target:not(.icon-button),
.app-button.frame-hit-target:not(.icon-button):is(
    :hover,
    :focus-visible,
    :active,
    :disabled
  ) {
  background: transparent;
  border: 0;
  box-shadow: none;
  opacity: 1;
}
</style>
