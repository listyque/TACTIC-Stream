<script setup>
import { ref, computed } from 'vue';
import * as Canvas from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/canvas.mjs';
import { t } from '../../i18n.js';
const props = defineProps({
  boxes: Array,
  selected: String,
  scale: { type: Number, default: 1 }
});
const emit = defineEmits(['select', 'commit']);
const gesture = ref(null),
  ghost = ref(null);
const chosen = computed(
  () => ghost.value || (props.boxes || []).find((b) => b.key === props.selected)
);
const css = (b) => ({
  left: b.x + 'px',
  top: b.y + 'px',
  width: b.width + 'px',
  height: b.height + 'px'
});
function start(e, box, handle, hit = false) {
  if (e.button !== 0) return;
  e.preventDefault();
  e.stopPropagation();
  e.currentTarget.focus();
  e.currentTarget.setPointerCapture(e.pointerId);
  if (hit && e.altKey) {
    const bounds = e.currentTarget
      .closest('.canvas-selection')
      .getBoundingClientRect();
    box =
      Canvas.pick(
        props.boxes,
        (e.clientX - bounds.left) / props.scale,
        (e.clientY - bounds.top) / props.scale,
        props.selected,
        true
      ) || box;
  }
  emit('select', box.key);
  if (box.canTransform === false) return;
  gesture.value = {
    box: { ...box },
    handle,
    x: e.clientX,
    y: e.clientY,
    scale: props.scale
  };
  ghost.value = { ...box };
}
function move(e) {
  const g = gesture.value;
  if (g)
    ghost.value = Canvas.transform(
      g.box,
      g.handle,
      (e.clientX - g.x) / g.scale,
      (e.clientY - g.y) / g.scale
    );
}
function finish(e) {
  const g = gesture.value;
  if (!g) return;
  move(e);
  const after = { ...ghost.value };
  gesture.value = ghost.value = null;
  if (JSON.stringify(after) !== JSON.stringify(g.box))
    emit('commit', { key: g.box.key, handle: g.handle, before: g.box, after });
}
function cancel() {
  gesture.value = ghost.value = null;
}
function key(e, box, resizeHandle) {
  if (e.key === 'Escape') {
    e.preventDefault();
    cancel();
    e.stopPropagation();
    return;
  }
  const d = {
    ArrowLeft: [-1, 0],
    ArrowRight: [1, 0],
    ArrowUp: [0, -1],
    ArrowDown: [0, 1]
  }[e.key];
  if (!d) return;
  if (box.canTransform === false) return;
  e.preventDefault();
  e.stopPropagation();
  const step = e.shiftKey ? 10 : 1,
    handle = resizeHandle || (e.altKey ? 'se' : 'move');
  emit('commit', {
    key: box.key,
    handle,
    keyboard: true,
    before: box,
    after: Canvas.transform(box, handle, d[0] * step, d[1] * step)
  });
}
</script>
<template>
  <div
    class="canvas-selection"
    :style="{ '--canvas-inverse-scale': 1 / scale }"
  >
    <div
      v-for="(box, i) in boxes"
      :key="box.key"
      class="canvas-hit"
      :style="{
        ...css(box.hit || box),
        zIndex: i,
        cursor: box.canTransform === false ? 'pointer' : 'move'
      }"
      :data-canvas-key="box.key"
      tabindex="0"
      role="button"
      :aria-label="t('Select element') + ' ' + (box.label || box.key)"
      @pointerdown="start($event, box, 'move', true)"
      @pointermove="move"
      @pointerup="finish"
      @pointercancel="cancel"
      @keydown="key($event, box)"
    />
    <div v-if="chosen" class="canvas-outline" :style="css(chosen)">
      <div
        v-if="chosen.canTransform !== false"
        class="canvas-move-edge"
        tabindex="0"
        role="button"
        :aria-label="t('Move element')"
        @pointerdown="start($event, chosen, 'move')"
        @pointermove="move"
        @pointerup="finish"
        @pointercancel="cancel"
        @keydown="key($event, chosen)"
      />
      <span
        class="canvas-size"
        :style="{ fontSize: Math.round(11 / scale) + 'px' }"
        >{{ Math.round(chosen.width) }} × {{ Math.round(chosen.height) }}</span
      >
      <div
        v-for="handle in chosen.canTransform === false ? [] : Canvas.handles"
        :key="handle"
        class="canvas-handle"
        :class="'canvas-handle-' + handle"
        :data-canvas-handle="handle"
        tabindex="0"
        role="button"
        :aria-label="t('Resize element') + ' ' + handle"
        @pointerdown="start($event, chosen, handle)"
        @pointermove="move"
        @pointerup="finish"
        @pointercancel="cancel"
        @keydown="key($event, chosen, handle)"
      />
    </div>
  </div>
</template>
<style>
.canvas-selection {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 100;
}
.canvas-hit {
  position: absolute;
  pointer-events: auto;
  cursor: move;
  background: transparent;
  touch-action: none;
  outline: none;
}
.canvas-hit:hover {
  outline: calc(1px * var(--canvas-inverse-scale)) dashed
    var(--content-accent, var(--primary));
  outline-offset: calc(-1px * var(--canvas-inverse-scale));
}
.canvas-hit:focus-visible {
  outline: calc(1px * var(--canvas-inverse-scale)) solid
    var(--content-accent, var(--primary));
  outline-offset: calc(-1px * var(--canvas-inverse-scale));
}
.canvas-move-edge {
  position: absolute;
  left: 0;
  top: calc(-4px * var(--canvas-inverse-scale));
  width: 100%;
  height: calc(8px * var(--canvas-inverse-scale));
  pointer-events: auto;
  cursor: move;
  touch-action: none;
}
.canvas-outline {
  position: absolute;
  border: calc(1px * var(--canvas-inverse-scale)) solid
    var(--content-accent, var(--primary));
  pointer-events: none;
  z-index: 200;
  box-sizing: border-box;
}
.canvas-size {
  position: absolute;
  top: calc(-20px * var(--canvas-inverse-scale));
  left: 0;
  white-space: nowrap;
  font-size: 11px;
  color: var(--content-accent, var(--primary));
  background: var(--panel);
  padding: calc(1px * var(--canvas-inverse-scale))
    calc(4px * var(--canvas-inverse-scale));
}
.canvas-handle {
  position: absolute;
  width: calc(14px * var(--canvas-inverse-scale));
  height: calc(14px * var(--canvas-inverse-scale));
  pointer-events: auto;
  touch-action: none;
}
.canvas-handle:after {
  content: '';
  position: absolute;
  inset: calc(4px * var(--canvas-inverse-scale));
  background: var(--panel);
  border: calc(1px * var(--canvas-inverse-scale)) solid
    var(--content-accent, var(--primary));
}
.canvas-handle-e {
  right: calc(-7px * var(--canvas-inverse-scale));
  top: calc(50% - 7px * var(--canvas-inverse-scale));
  cursor: ew-resize;
}
.canvas-handle-s {
  bottom: calc(-7px * var(--canvas-inverse-scale));
  left: calc(50% - 7px * var(--canvas-inverse-scale));
  cursor: ns-resize;
}
.canvas-handle-se {
  right: calc(-7px * var(--canvas-inverse-scale));
  bottom: calc(-7px * var(--canvas-inverse-scale));
  cursor: nwse-resize;
}
</style>
