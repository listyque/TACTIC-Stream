<script setup>
import { ref, computed } from 'vue';
import * as Canvas from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/canvas.mjs';
import * as Selection from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/page.selection.mjs';
import { t } from '../../i18n.js';
const props = defineProps({
  boxes: Array,
  selected: String,
  scale: { type: Number, default: 1 },
  selection: Array,
  multiple: Boolean,
  multiSelect: Boolean,
  snap: Boolean
});
const emit = defineEmits(['select', 'selection', 'commit']);
const gesture = ref(null),
  ghost = ref(null),
  preview = ref(null),
  rubber = ref(null);
const group = computed(() =>
  Selection.selected(props.boxes || [], props.selection || [props.selected])
);
const outlines = computed(
  () => preview.value?.changes.map((change) => change.after) || group.value
);
const chosen = computed(() =>
  props.multiple && group.value.length > 1
    ? Object.assign({}, Selection.bounds(outlines.value), { group: true })
    : ghost.value ||
      preview.value?.changes[0]?.after ||
      (props.boxes || []).find((box) => box.key === props.selected)
);
const css = (b) => ({
  left: b.x + 'px',
  top: b.y + 'px',
  width: b.width + 'px',
  height: b.height + 'px'
});
const point = (e) => {
  const area = e.currentTarget
    .closest('.canvas-selection')
    .getBoundingClientRect();
  return {
    x: (e.clientX - area.left) / props.scale,
    y: (e.clientY - area.top) / props.scale
  };
};
function start(e, box, handle, hit = false) {
  if (e.button !== 0) return;
  e.preventDefault();
  e.stopPropagation();
  e.currentTarget.focus();
  e.currentTarget.setPointerCapture(e.pointerId);
  const p = point(e);
  if (props.multiple && (!box || e.shiftKey)) {
    gesture.value = {
      marquee: true,
      start: p,
      base: props.selection || [],
      box
    };
    rubber.value = { x: p.x, y: p.y, width: 0, height: 0 };
    return;
  }
  if (hit && e.altKey)
    box = Canvas.pick(props.boxes, p.x, p.y, props.selected, true) || box;
  if (props.multiple) {
    let keys = props.selection || [];
    if (!box.group && (e.ctrlKey || e.metaKey || props.multiSelect)) {
      emit('selection', Selection.toggle(keys, box.key));
      return;
    }
    if (!box.group && !keys.includes(box.key)) keys = [box.key];
    emit('selection', keys);
    const boxes = Selection.selected(props.boxes, keys);
    if (!boxes.length) return;
    gesture.value = {
      boxes,
      handle,
      x: e.clientX,
      y: e.clientY,
      scale: props.scale
    };
    return;
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
  if (!g) return;
  if (g.marquee) {
    const p = point(e);
    rubber.value = Selection.bounds([
      { ...g.start, width: 0, height: 0 },
      { ...p, width: 0, height: 0 }
    ]);
    return;
  }
  const dx = (e.clientX - g.x) / g.scale,
    dy = (e.clientY - g.y) / g.scale;
  if (g.boxes) {
    if (Math.hypot(dx, dy) * g.scale < 3 && !g.moved) return;
    g.moved = true;
    preview.value = Selection.drag(
      g.boxes,
      g.handle,
      dx,
      dy,
      props.boxes,
      g.scale,
      props.snap && !e.altKey
    );
  } else ghost.value = Canvas.transform(g.box, g.handle, dx, dy);
}
function finish(e) {
  const g = gesture.value;
  if (!g) return;
  move(e);
  if (g.marquee) {
    const p = point(e);
    const small =
      Math.hypot(p.x - g.start.x, p.y - g.start.y) * props.scale < 3;
    emit(
      'selection',
      small
        ? g.box
          ? Selection.toggle(g.base, g.box.key)
          : []
        : Selection.roots(
            g.base.concat(Selection.marquee(props.boxes, g.start, p))
          )
    );
  } else if (g.boxes) {
    const changes = preview.value?.changes || [];
    if (
      changes.some((c) => JSON.stringify(c.before) !== JSON.stringify(c.after))
    )
      emit('commit', { changes });
  } else {
    const after = { ...ghost.value };
    if (JSON.stringify(after) !== JSON.stringify(g.box))
      emit('commit', {
        key: g.box.key,
        handle: g.handle,
        before: g.box,
        after
      });
  }
  cancel();
}
function cancel() {
  gesture.value = ghost.value = preview.value = rubber.value = null;
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
  if (!d || box.canTransform === false) return;
  e.preventDefault();
  e.stopPropagation();
  const step = e.shiftKey ? 10 : 1,
    handle = resizeHandle || (e.altKey ? 'se' : 'move');
  if (props.multiple) {
    if (group.value.length > 1 && handle !== 'move') return;
    emit('commit', {
      changes: Selection.drag(
        group.value,
        handle,
        d[0] * step,
        d[1] * step,
        [],
        props.scale,
        false
      ).changes
    });
  } else
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
      v-if="multiple"
      class="canvas-background"
      tabindex="0"
      @pointerdown="start($event, null, 'move')"
      @pointermove="move"
      @pointerup="finish"
      @pointercancel="cancel"
    />
    <div
      v-for="box in multiple ? outlines : []"
      :key="'outline-' + box.key"
      class="canvas-outline"
      :style="css(box)"
    />
    <div
      v-for="(guide, index) in preview?.guides || []"
      :key="'guide-' + index"
      class="canvas-guide"
      :data-canvas-guide="guide.axis"
      :style="
        guide.axis === 'x'
          ? {
              left: guide.value + 'px',
              top: guide.start + 'px',
              height: guide.end - guide.start + 'px',
              width: 0
            }
          : {
              top: guide.value + 'px',
              left: guide.start + 'px',
              width: guide.end - guide.start + 'px',
              height: 0
            }
      "
    />
    <div v-if="rubber" class="canvas-marquee" :style="css(rubber)" />
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
        >{{ Math.round(chosen.width) }} Г— {{ Math.round(chosen.height) }}</span
      >
      <div
        v-for="handle in chosen.canTransform === false || chosen.group
          ? []
          : Canvas.handles"
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
.canvas-background {
  position: absolute;
  inset: 0;
  pointer-events: auto;
  touch-action: none;
}
.canvas-guide {
  position: absolute;
  z-index: 250;
  pointer-events: none;
  border-left: calc(1px * var(--canvas-inverse-scale)) dashed
    var(--content-accent, var(--primary));
  border-top: calc(1px * var(--canvas-inverse-scale)) dashed
    var(--content-accent, var(--primary));
}
.canvas-marquee {
  position: absolute;
  z-index: 260;
  pointer-events: none;
  border: calc(1px * var(--canvas-inverse-scale)) solid
    var(--content-accent, var(--primary));
  background: color-mix(
    in srgb,
    var(--content-accent, var(--primary)) 12%,
    transparent
  );
}

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
