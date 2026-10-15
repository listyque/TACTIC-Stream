<script setup>
import { onBeforeUnmount, onUpdated, ref, nextTick } from 'vue';
import { t } from '../i18n.js';
import AppIcon from './AppIcon.vue';
import { ripple } from './ripple.js';
import { capturePress } from './activation.js';
import { tooltipDirective as vTooltip } from './tooltip.js';

const props = defineProps({
  label: String,
  showLabel: Boolean,
  compactTrigger: Boolean,
  icon: { type: String, default: 'more' },
  badgeCount: { type: Number, default: 0 },
  closeOnSelect: { type: Boolean, default: true },
  boundary: Object,
  anchor: Object,
  alignStart: Boolean,
  centered: Boolean,
  disabled: Boolean,
  inline: Boolean,
  overlay: Boolean,
  modal: Boolean,
  submenu: Boolean,
  width: Number,
  maxHeight: Number
});
const emit = defineEmits(['before-open']);
const menu = ref(null);
const trigger = ref(null);
const expanded = ref(false);
const panelElement = ref(null);
let point = null;
let returnTarget = null;
let hoverTimer = null;
let focusEdge = null;
function cancelHover() {
  clearTimeout(hoverTimer);
}
function hoverSubmenu() {
  if (!props.submenu || props.disabled) return;
  clearTimeout(hoverTimer);
  hoverTimer = setTimeout(
    () => {
      if (menu.value.parentElement.closest('details')?.open)
        menu.value.open = true;
    },
    parseFloat(
      getComputedStyle(menu.value).getPropertyValue('--motion-medium')
    ) || 0
  );
}
function activate(event) {
  if (props.disabled) {
    event.preventDefault();
    return;
  }
  if (!props.submenu) return;
  event.preventDefault();
  clearTimeout(hoverTimer);
  menu.value.open = true;
}
function close(focus = false) {
  clearTimeout(hoverTimer);
  if (props.inline || !menu.value) return;
  menu.value.open = false;
  expanded.value = false;
  if (props.modal && panelElement.value.open) panelElement.value.close();
  if (
    props.overlay &&
    !props.modal &&
    panelElement.value?.matches(':popover-open')
  )
    panelElement.value.hidePopover();
  if (focus)
    (returnTarget?.isConnected
      ? returnTarget
      : props.anchor?.isConnected
        ? props.anchor
        : trigger.value
    )?.focus();
}
function outside(event) {
  if (
    menu.value &&
    !menu.value.contains(event.target) &&
    !props.anchor?.contains(event.target)
  )
    close();
}
function escape(event) {
  if (
    event.key !== 'Escape' ||
    event.defaultPrevented ||
    !menu.value.open ||
    props.inline ||
    menu.value.querySelector('details[open]')
  )
    return;
  const dialog = event.target.closest('dialog');
  if (dialog && dialog !== panelElement.value && !dialog.contains(menu.value))
    return;
  event.preventDefault();
  event.stopPropagation();
  close(true);
}
function position() {
  const panel = menu.value?.querySelector('.account-panel');
  if (!panel || !menu.value.open) return;
  const boundary = props.boundary?.getBoundingClientRect();
  const viewport = window.visualViewport,
    keyboardViewport = innerWidth <= 700 && viewport?.scale === 1;
  const viewportTop = keyboardViewport ? viewport.offsetTop : 0,
    viewportBottom = keyboardViewport
      ? viewportTop + viewport.height
      : innerHeight;
  const top = Math.max(viewportTop, boundary?.top || 0),
    bottom = Math.min(viewportBottom, boundary?.bottom ?? viewportBottom);
  if (props.centered) {
    const left = Math.max(0, boundary?.left || 0),
      right = Math.min(innerWidth, boundary?.right ?? innerWidth);
    panel.style.maxHeight =
      Math.max(0, Math.min(props.maxHeight ?? Infinity, bottom - top - 8)) +
      'px';
    panel.style.left = left + (right - left - panel.offsetWidth) / 2 + 'px';
    panel.style.top = top + (bottom - top - panel.offsetHeight) / 2 + 'px';
  } else if (props.overlay || props.modal) {
    const triggerBox = (props.anchor || trigger.value).getBoundingClientRect();
    panel.style.left =
      Math.max(
        4,
        props.submenu
          ? triggerBox.right + 6
          : (point?.x ??
              (props.alignStart
                ? triggerBox.left
                : triggerBox.right - panel.offsetWidth))
      ) + 'px';
    const anchorTop = point?.y ?? triggerBox.top,
      anchorBottom = point?.y ?? triggerBox.bottom;
    const below = bottom - anchorBottom - 8,
      above = anchorTop - top - 8;
    const up = !props.modal && panel.scrollHeight > below && above > below;
    // A tall popup scrolls on one side of its trigger, keeping that trigger reachable.
    panel.style.maxHeight =
      Math.max(
        0,
        Math.min(
          props.maxHeight ?? Infinity,
          props.modal ? bottom - top - 8 : up ? above : below
        )
      ) + 'px';
    if (props.overlay && !props.modal) panel.style.overflowY = 'auto';
    panel.style.top =
      (props.submenu
        ? triggerBox.top - 6
        : up
          ? anchorTop - panel.offsetHeight - 4
          : anchorBottom + 4) + 'px';
    if (props.submenu) {
      panel.style.maxHeight =
        Math.max(0, Math.min(props.maxHeight ?? Infinity, bottom - top - 8)) +
        'px';
      if (
        triggerBox.right + 6 + panel.offsetWidth >
        (boundary?.right ?? innerWidth)
      )
        panel.style.left =
          Math.max(4, triggerBox.left - panel.offsetWidth - 6) + 'px';
    }
  }
  panel.style.translate = '';
  const left = Math.max(0, boundary?.left || 0),
    right = Math.min(innerWidth, boundary?.right ?? innerWidth);
  if (boundary) panel.style.maxWidth = Math.max(0, right - left - 8) + 'px';
  // Fit the unscaled box, so an opening transition cannot shift the final popup outside its host.
  const box = panel.getBoundingClientRect(),
    style = getComputedStyle(panel);
  const scale = parseFloat(style.scale) || 1;
  const [originX, originY] = style.transformOrigin.split(' ').map(parseFloat);
  const x = box.left - originX * (1 - scale),
    y0 = box.top - originY * (1 - scale);
  const bounds = {
    left: x,
    top: y0,
    right: x + parseFloat(style.width),
    bottom: y0 + parseFloat(style.height)
  };
  const y = Math.max(
    top + 4 - bounds.top,
    Math.min(0, bottom - 4 - bounds.bottom)
  );
  panel.style.translate =
    Math.max(left + 4 - bounds.left, Math.min(0, right - 4 - bounds.right)) +
    'px ' +
    y +
    'px';
}
function items() {
  return [
    ...panelElement.value.querySelectorAll(
      'button:not(:disabled):not([data-menu-secondary]), a[href], .workspace-menu > summary'
    )
  ].filter(
    (item) =>
      item.getClientRects().length &&
      item.getAttribute('aria-disabled') !== 'true' &&
      (item.tagName === 'SUMMARY'
        ? item.parentElement.parentElement.closest('.workspace-menu')
        : item.closest('.workspace-menu')) === menu.value
  );
}
function move(event) {
  if (props.disabled) {
    event.preventDefault();
    return;
  }
  if (props.inline) return;
  if (
    event.key === 'Escape' &&
    menu.value.open &&
    !menu.value.querySelector('details[open]')
  ) {
    event.preventDefault();
    event.stopPropagation();
    close(true);
    return;
  }
  if (event.key === 'ArrowLeft' && props.submenu && menu.value.open) {
    event.preventDefault();
    event.stopPropagation();
    close(true);
    return;
  }
  if (
    event.key === 'ArrowRight' &&
    event.target.tagName === 'SUMMARY' &&
    event.target.parentElement !== menu.value
  ) {
    event.preventDefault();
    event.stopPropagation();
    const child = event.target.parentElement;
    child.open = true;
    nextTick(() =>
      child.querySelector('.account-panel button:not(:disabled)')?.focus()
    );
    return;
  }
  if (event.target.closest('input, select, textarea, [role="combobox"]'))
    return;
  if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  const backwards = event.key === 'ArrowUp' || event.key === 'End';
  if (!menu.value.open) {
    focusEdge = backwards ? 'last' : 'first';
    menu.value.open = true;
    // Native details toggle is queued; rapid Escape/reopen must still place focus.
    toggled();
    return;
  }
  const buttons = items();
  const active = document.activeElement;
  const index = buttons.indexOf(
    active?.matches('[data-menu-secondary]')
      ? active.parentElement.querySelector('[data-menu-primary]')
      : active
  );
  const target =
    event.key === 'Home'
      ? 0
      : event.key === 'End'
        ? buttons.length - 1
        : index < 0
          ? backwards
            ? buttons.length - 1
            : 0
          : (index + (backwards ? -1 : 1) + buttons.length) % buttons.length;
  buttons[target]?.focus();
}
function toggled() {
  if (!menu.value) return;
  if (menu.value.open && !expanded.value) emit('before-open');
  expanded.value = menu.value.open;
  if (!menu.value.open) {
    point = null;
    for (const child of menu.value.querySelectorAll('details[open]'))
      child.open = false;
  }
  document.removeEventListener('pointerdown', outside);
  document.removeEventListener('keydown', escape, true);
  document.removeEventListener('scroll', position, true);
  window.removeEventListener('resize', position);
  window.visualViewport?.removeEventListener('resize', position);
  window.visualViewport?.removeEventListener('scroll', position);
  window.removeEventListener('windowgeometrychange', position);
  if (menu.value.open) {
    if (props.submenu) {
      for (const sibling of menu.value.parentElement.querySelectorAll(
        ':scope > details[open]'
      ))
        if (sibling !== menu.value) sibling.open = false;
    }
    if (props.modal && !panelElement.value.open) panelElement.value.showModal();
    else if (
      props.overlay &&
      !props.modal &&
      !panelElement.value.matches(':popover-open')
    )
      panelElement.value.showPopover();
    document.addEventListener('pointerdown', outside);
    document.addEventListener('keydown', escape, true);
    window.addEventListener('resize', position);
    window.visualViewport?.addEventListener('resize', position);
    window.visualViewport?.addEventListener('scroll', position);
    position();
    if (focusEdge) {
      const buttons = items();
      (focusEdge === 'last' ? buttons.at(-1) : buttons[0])?.focus();
      focusEdge = null;
    }
    if (props.submenu && document.activeElement === trigger.value)
      nextTick(() => items()[0]?.focus());
    if (!trigger.value.getClientRects().length)
      nextTick(() =>
        (
          panelElement.value.querySelector(
            'input:not([type="hidden"]):not(:disabled), textarea:not(:disabled)'
          ) || items()[0]
        )?.focus()
      );
    window.addEventListener('windowgeometrychange', position);
    if (props.overlay) document.addEventListener('scroll', position, true);
  } else if (props.modal && panelElement.value.open) panelElement.value.close();
  else if (
    props.overlay &&
    !props.modal &&
    panelElement.value.matches(':popover-open')
  )
    panelElement.value.hidePopover();
}
function backdrop(event) {
  if (!props.modal || event.target !== panelElement.value) return;
  const box = panelElement.value.getBoundingClientRect();
  if (
    event.clientX < box.left ||
    event.clientX > box.right ||
    event.clientY < box.top ||
    event.clientY > box.bottom
  )
    close(true);
}
function selected(event) {
  // The action can unmount this menu before its click bubbles here.
  if (!menu.value) return;
  const action = event.target.closest('button, a[href]');
  if (action && !props.closeOnSelect) event.stopPropagation();
  // A dispatched action may disable its own button while the click bubbles.
  if (props.closeOnSelect && action && !action.closest('[role="combobox"]'))
    close(menu.value.contains(document.activeElement));
}
onUpdated(() => {
  if (props.disabled && menu.value?.open) close();
  else position();
});
defineExpose({
  close,
  openAt(event) {
    point = { x: event.clientX, y: event.clientY };
    returnTarget = event.target?.closest('[tabindex],button,a');
    menu.value.open = true;
    nextTick(() => {
      position();
      if (trigger.value?.getClientRects().length) trigger.value.focus();
    });
  },
  focusTrigger() {
    trigger.value?.focus();
  },
  get open() {
    return menu.value?.open;
  },
  set open(value) {
    if (menu.value) menu.value.open = value;
  }
});
onBeforeUnmount(() => {
  clearTimeout(hoverTimer);
  document.removeEventListener('pointerdown', outside);
  document.removeEventListener('keydown', escape, true);
  document.removeEventListener('scroll', position, true);
  window.removeEventListener('resize', position);
  window.visualViewport?.removeEventListener('resize', position);
  window.visualViewport?.removeEventListener('scroll', position);
  window.removeEventListener('windowgeometrychange', position);
});
</script>

<template>
  <details
    ref="menu"
    class="workspace-menu"
    :class="{
      'inline-menu': inline,
      'labelled-menu': showLabel,
      'compact-trigger': compactTrigger
    }"
    @keydown="move"
    @toggle="toggled"
  >
    <summary
      v-tooltip="t(label)"
      ref="trigger"
      class="icon-button"
      :aria-label="t(label)"
      :aria-expanded="expanded"
      :aria-disabled="disabled || undefined"
      :tabindex="disabled ? -1 : 0"
      @click="activate"
      @pointerenter="hoverSubmenu"
      @pointerleave="cancelHover"
      @pointerdown="
        cancelHover();
        point = null;
        capturePress($event);
        !disabled && ripple($event);
      "
    >
      <slot name="trigger"
        ><AppIcon :name="icon" /><span v-if="showLabel">{{
          t(label)
        }}</span></slot
      ><span
        v-if="badgeCount > 0"
        class="app-button-badge"
        aria-hidden="true"
        >{{ badgeCount > 99 ? '99+' : badgeCount }}</span
      >
    </summary>
    <component
      :is="modal ? 'dialog' : 'div'"
      ref="panelElement"
      class="account-panel"
      :style="
        width
          ? { width: 'min(' + width + 'px, calc(100dvw - 16px))' }
          : undefined
      "
      :aria-label="modal ? t(label) : undefined"
      :popover="overlay && !modal ? 'manual' : undefined"
      @cancel.prevent.stop="close(true)"
      @pointerdown="backdrop"
      @click="selected"
      @transitionend.self="position"
      ><slot
    /></component>
  </details>
</template>
<style>
.workspace-menu.labelled-menu > summary {
  width: auto;
  display: inline-flex;
  gap: var(--space-sm);
  padding-inline: 8px;
}
dialog.account-panel {
  position: fixed;
  margin: 0;
  color: var(--on-surface);
  max-width: calc(100dvw - 16px);
}
dialog.account-panel:not([open]) {
  display: none;
}
dialog.account-panel::backdrop {
  background: var(--scrim);
}
</style>

<style>
.workspace-menu.compact-trigger > summary {
  background: transparent;
  border-radius: var(--icon-button-radius);
}
:where(.workspace-menu.compact-trigger) > summary > .app-icon {
  width: var(--compact-icon-size);
  height: var(--compact-icon-size);
}
.workspace-menu.compact-trigger > summary::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  height: calc(100% - var(--icon-button-surface-inset));
  width: auto;
  aspect-ratio: 1;
  max-width: calc(100% - var(--icon-button-surface-inset));
  border-radius: var(--icon-button-radius);
  pointer-events: none;
  z-index: -1;
}
.workspace-menu.compact-trigger
  > summary:not([aria-disabled='true']):is(:hover, :focus-visible)::before {
  background: color-mix(
    in srgb,
    currentColor calc(var(--icon-button-hovered-opacity) * 100%),
    transparent
  );
}
.workspace-menu.compact-trigger
  > summary:not([aria-disabled='true']):active::before {
  background: color-mix(
    in srgb,
    currentColor calc(var(--icon-button-pressed-opacity) * 100%),
    transparent
  );
}
</style>
