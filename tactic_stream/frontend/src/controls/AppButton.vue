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
  iconAtEnd: Boolean,
  iconOnly: Boolean,
  compact: Boolean,
  round: Boolean,
  highlighted: Boolean,
  filledAction: Boolean,
  destructive: Boolean,
  tonal: Boolean,
  segmented: Boolean,
  checked: Boolean,
  badgeCount: { type: Number, default: 0 },
  badgeColor: String,
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
    :style="[paint, badgeColor ? { '--badge-color': badgeColor } : null]"
    :href="href"
    :type="href ? undefined : type"
    :class="{
      'icon-button': iconOnly || compact,
      'compact-button': compact,
      'round-button': round,
      primary: highlighted,
      'filled-action': filledAction,
      danger: destructive,
      tonal,
      'icon-at-end': iconAtEnd
    }"
    v-tooltip="
      tooltip
        ? t(tooltip)
        : (iconOnly || compact) && label
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
      ><span v-if="!iconOnly && !compact">{{
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
.app-button.icon-at-end > .app-icon {
  order: 1;
}
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
  width: var(--button-icon-size);
  height: var(--button-icon-size);
  font-size: var(--button-icon-size);
}
.app-button.icon-button > .app-icon {
  width: var(--compact-icon-size);
  height: var(--compact-icon-size);
}
.app-button.icon-button:disabled {
  opacity: 1;
  color: var(--disabled);
}
.app-button.icon-button:not(.compact-button) {
  --ripple-inset: calc(var(--icon-button-surface-inset) / 2);
  padding: var(--ripple-inset);
  background-clip: content-box;
}
.app-button.icon-button.primary {
  color: var(--on-selected);
}
.app-button.compact-button {
  border-radius: var(--button-radius);
  background: var(--button-idle-background);
  color: var(--button-idle-color);
  border: var(--button-idle-border-width) solid var(--button-idle-border);
}
.app-button.compact-button:hover:not(:disabled) {
  background: var(--button-hover-background);
  color: var(--button-hover-color);
}
.app-button.compact-button:active:not(:disabled) {
  background: var(--button-pressed-background);
  color: var(--button-pressed-color);
}
.app-button.compact-button:disabled {
  background: var(--button-disabled-background);
  color: var(--button-disabled-color);
}
.app-button.compact-button > .app-icon {
  width: 18px;
  height: 18px;
  font-size: 18px;
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
  padding-inline: calc(var(--button-padding) - var(--button-idle-border-width));
  gap: var(--button-spacing);
}
.app-button:where(:not(.icon-button)):where(:has(> .app-icon)) {
  padding-inline-start: calc(
    var(--button-icon-padding) - var(--button-idle-border-width)
  );
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
  border-radius: var(--icon-button-radius);
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
  top: -1px;
  right: -1px;
}
.app-button-badge {
  position: absolute;
  top: -1px;
  right: -1px;
  box-sizing: border-box;
  min-width: 16px;
  height: 16px;
  padding: 0 1.5px;
  border: 2px solid var(--surface);
  border-radius: 8px;
  background: var(--badge-color, var(--error));
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

<style>
.frame-view > .frame-node.frame-button.app-button.filled-action {
  padding: 2px;
  border: 0;
  border-radius: calc(var(--button-radius) + 2px);
  background: transparent;
  box-shadow: none;
  isolation: isolate;
}
.frame-view > .frame-button.app-button.filled-action::before {
  content: '';
  position: absolute;
  inset: 2px;
  border-radius: var(--button-radius);
  background: var(--primary);
  z-index: -1;
  pointer-events: none;
}
/* shortcut: brightness matches shipped accents; saturated custom accents need Qt HSV tinting for exact hover parity. */
.app-button.filled-action:is(:hover, :focus-visible):not(:disabled)::before {
  filter: brightness(1.08);
}
.app-button.filled-action:active:not(:disabled)::before {
  filter: brightness(0.8695652174);
}
.frame-view > .frame-button.app-button.filled-action:disabled::before {
  background: var(--surface-high);
}
</style>

<style>
.app-button.round-button {
  border-radius: 999px;
}
.app-button.round-button.filled-action::before {
  border-radius: 999px;
}
</style>
