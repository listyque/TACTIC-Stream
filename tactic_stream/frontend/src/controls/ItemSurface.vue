<script setup>
// Handler ItemSurface.qml: shared row overlay, rail and separator.
defineProps({
  accent: String,
  selected: Boolean,
  cornerRadius: { type: [Number, String], default: 10 },
  inset: { type: Number, default: 1 },
  normalColor: String,
  selectedColor: String,
  railVisible: { type: Boolean, default: true },
  separatorVisible: { type: Boolean, default: true }
});
</script>
<template>
  <div
    class="item-surface"
    :class="{ selected, 'without-separator': !separatorVisible }"
    :style="{
      '--item-base': (selected ? selectedColor : normalColor) || undefined,
      '--item-accent': accent || 'var(--primary)',
      '--item-corner':
        typeof cornerRadius === 'number' ? cornerRadius + 'px' : cornerRadius,
      '--item-inset': inset + 'px'
    }"
  >
    <span v-if="railVisible" class="item-surface-rail" aria-hidden="true"></span
    ><slot />
  </div>
</template>
<style>
.item-surface {
  --item-base: var(--row);
  --item-state-color: var(--on-surface);
  --item-interaction: var(--item-base);
  position: relative;
  border: var(--item-inset) solid transparent;
  border-radius: var(--item-corner);
  background: var(--item-interaction);
  background-clip: padding-box;
  transition: background-color var(--motion-hover);
}
.item-surface.selected {
  --item-base: var(--content-selection);
  --item-state-color: var(--primary);
}
.item-surface:hover {
  --item-interaction: color-mix(
    in srgb,
    var(--item-state-color) 8%,
    var(--item-base)
  );
}
.item-surface:active {
  --item-interaction: color-mix(
    in srgb,
    var(--item-state-color) 12%,
    var(--item-base)
  );
}
.item-surface-rail {
  position: absolute;
  pointer-events: none;
  left: calc(-1 * var(--item-inset));
  top: 5px;
  bottom: 5px;
  width: 3px;
  border-radius: 2px;
  background: var(--item-accent);
}
.item-surface::after {
  content: '';
  position: absolute;
  pointer-events: none;
  left: 0;
  right: 0;
  bottom: 0;
  height: 1px;
  background: var(--outline-variant);
}
</style>
<style>
.item-surface.without-separator::after {
  display: none;
}
</style>
