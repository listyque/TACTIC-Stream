<script setup>
import { ref, computed } from 'vue';
import * as Canvas from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/canvas.mjs';
import { t } from '../../i18n.js';
const props = defineProps({ boxes: Array, selected: String });
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
function start(e, box, handle) {
  if (e.button !== 0) return;
  e.preventDefault();
  e.stopPropagation();
  e.currentTarget.focus();
  e.currentTarget.setPointerCapture(e.pointerId);
  emit('select', box.key);
  gesture.value = { box: { ...box }, handle, x: e.clientX, y: e.clientY };
  ghost.value = { ...box };
}
function move(e) {
  const g = gesture.value;
  if (g)
    ghost.value = Canvas.transform(
      g.box,
      g.handle,
      e.clientX - g.x,
      e.clientY - g.y
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
  <div class="canvas-selection">
    <div
      v-for="(box, i) in boxes"
      :key="box.key"
      class="canvas-hit"
      :style="{ ...css(box.hit || box), zIndex: i }"
      :data-canvas-key="box.key"
      tabindex="0"
      role="button"
      :aria-label="t('Select element') + ' ' + box.key"
      @pointerdown="start($event, box, 'move')"
      @pointermove="move"
      @pointerup="finish"
      @pointercancel="cancel"
      @keydown="key($event, box)"
    />
    <div v-if="chosen" class="canvas-outline" :style="css(chosen)">
      <div
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
      <span class="canvas-size"
        >{{ Math.round(chosen.width) }} × {{ Math.round(chosen.height) }}</span
      >
      <div
        v-for="handle in Canvas.handles"
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
  outline: 1px dashed var(--content-accent, var(--primary));
  outline-offset: -1px;
}
.canvas-hit:focus-visible {
  outline: 1px solid var(--content-accent, var(--primary));
  outline-offset: -1px;
}
.canvas-move-edge {
  position: absolute;
  left: 0;
  top: -4px;
  width: 100%;
  height: 8px;
  pointer-events: auto;
  cursor: move;
  touch-action: none;
}
.canvas-outline {
  position: absolute;
  border: 1px solid var(--content-accent, var(--primary));
  pointer-events: none;
  z-index: 200;
  box-sizing: border-box;
}
.canvas-size {
  position: absolute;
  top: -20px;
  left: 0;
  white-space: nowrap;
  font-size: 11px;
  color: var(--content-accent, var(--primary));
  background: var(--panel);
  padding: 1px 4px;
}
.canvas-handle {
  position: absolute;
  width: 14px;
  height: 14px;
  pointer-events: auto;
  touch-action: none;
}
.canvas-handle:after {
  content: '';
  position: absolute;
  inset: 4px;
  background: var(--panel);
  border: 1px solid var(--content-accent, var(--primary));
}
.canvas-handle-e {
  right: -7px;
  top: calc(50% - 7px);
  cursor: ew-resize;
}
.canvas-handle-s {
  bottom: -7px;
  left: calc(50% - 7px);
  cursor: ns-resize;
}
.canvas-handle-se {
  right: -7px;
  bottom: -7px;
  cursor: nwse-resize;
}
</style>
