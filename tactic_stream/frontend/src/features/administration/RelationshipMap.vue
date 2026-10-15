<script setup>
import { computed, nextTick, ref, useId, watch } from 'vue';
import { t } from '../../i18n.js';
import AppIcon from '../../controls/AppIcon.vue';

const props = defineProps({
  graph: { type: Object, required: true },
  interactive: Boolean,
  editable: Boolean,
  toolbarTarget: String,
  selected: { type: Array, default: () => [] },
  selectedEdge: Number,
  title: { type: String, default: 'Relationship map' },
  description: {
    type: String,
    default:
      'A read-only view of this Search Type and only its direct schema relationships.'
  }
});
const emit = defineEmits([
  'select',
  'edge',
  'move',
  'remove',
  'connect',
  'save',
  'select-many'
]);
const viewport = ref(null),
  zoom = ref(1),
  dragging = ref(null);
const movedNode = ref('');
const connecting = ref('');
const inputPort = ref(false),
  connectionCursor = ref({ x: 0, y: 0 });
const arrowId = useId();
function point(event) {
  const bounds = viewport.value.getBoundingClientRect();
  return {
    x:
      (event.clientX - bounds.left + viewport.value.scrollLeft) / zoom.value +
      left.value,
    y:
      (event.clientY - bounds.top + viewport.value.scrollTop) / zoom.value +
      top.value
  };
}
const selectionFrame = computed(() => {
  const start = dragging.value;
  if (start?.kind !== 'selection') return null;
  return {
    x: Math.min(start.origin.x, start.point.x),
    y: Math.min(start.origin.y, start.point.y),
    width: Math.abs(start.point.x - start.origin.x),
    height: Math.abs(start.point.y - start.origin.y)
  };
});
function centerSelection() {
  const selection = nodes.value.filter((node) =>
    props.selected.includes(node.identity)
  );
  if (!selection.length) return;
  const x =
    (Math.min(...selection.map((node) => node.nodeX)) +
      Math.max(...selection.map((node) => node.nodeX + nodeWidth(node)))) /
    2;
  const y =
    (Math.min(...selection.map((node) => node.nodeY)) +
      Math.max(...selection.map((node) => node.nodeY + 72))) /
    2;
  viewport.value.scrollTo(
    (x - left.value) * zoom.value - viewport.value.clientWidth / 2,
    (y - top.value) * zoom.value - viewport.value.clientHeight / 2
  );
}
const nodes = computed(() => props.graph.nodes || []);
function nodeWidth(node) {
  return node.kind === 'progress' ? 72 : 200;
}
const byIdentity = computed(() =>
  Object.fromEntries(nodes.value.map((node) => [node.identity, node]))
);
const left = computed(
  () => Math.min(0, ...nodes.value.map((node) => node.nodeX)) - 18
);
const top = computed(
  () => Math.min(0, ...nodes.value.map((node) => node.nodeY)) - 18
);
const width = computed(
  () =>
    Math.max(800, ...nodes.value.map((node) => node.nodeX + 300)) +
    18 -
    left.value
);
const height = computed(
  () =>
    Math.max(800, ...nodes.value.map((node) => node.nodeY + 172)) +
    18 -
    top.value
);
const edges = computed(() => {
  const pairs = new Set(
    (props.graph.edges || []).map((edge) =>
      JSON.stringify([edge.from, edge.to])
    )
  );
  return (props.graph.edges || []).flatMap((edge) => {
    const from = byIdentity.value[edge.from],
      to = byIdentity.value[edge.to];
    if (!from || !to) return [];
    const forward = to.nodeX >= from.nodeX;
    const x1 = from.nodeX + nodeWidth(from),
      x2 = to.nodeX;
    const y1 = from.nodeY + 36,
      y2 = to.nodeY + 36,
      middle = (x1 + x2) / 2;
    const offset = pairs.has(JSON.stringify([edge.to, edge.from]))
      ? forward
        ? -24
        : 24
      : 0;
    return [
      {
        ...edge,
        path: `M ${x1} ${y1} C ${middle} ${y1 + offset}, ${middle} ${y2 + offset}, ${x2} ${y2}`,
        x: middle,
        y: (y1 + y2) / 2 + offset * 0.75 - 8
      }
    ];
  });
});
function nodeColor(node) {
  return /^#[0-9a-f]{6}$/i.test(node.color || '') ? node.color : undefined;
}
async function zoomAt(value, event) {
  const view = viewport.value,
    bounds = view.getBoundingClientRect();
  const x = event ? event.clientX - bounds.left : view.clientWidth / 2;
  const y = event ? event.clientY - bounds.top : view.clientHeight / 2;
  const anchorX = (view.scrollLeft + x) / zoom.value,
    anchorY = (view.scrollTop + y) / zoom.value;
  zoom.value = Math.max(0.4, Math.min(2, Math.round(value * 10) / 10));
  await nextTick();
  view.scrollLeft = anchorX * zoom.value - x;
  view.scrollTop = anchorY * zoom.value - y;
}
async function reset() {
  dragging.value = null;
  zoom.value = 1;
  await nextTick();
  viewport.value?.scrollTo(0, 0);
}
function startPan(event) {
  if (event.pointerType !== 'mouse') return;
  if (connecting.value && event.button === 0) {
    connecting.value = '';
    return;
  }
  if (props.interactive && event.button === 0) {
    event.preventDefault();
    dragging.value = {
      kind: 'selection',
      id: event.pointerId,
      origin: point(event),
      point: point(event),
      additive: event.shiftKey || event.ctrlKey || event.metaKey
    };
    viewport.value.setPointerCapture(event.pointerId);
    return;
  }
  if (event.button !== 1) return;
  event.preventDefault();
  dragging.value = {
    kind: 'pan',
    id: event.pointerId,
    x: event.clientX,
    y: event.clientY,
    left: viewport.value.scrollLeft,
    top: viewport.value.scrollTop
  };
  viewport.value.setPointerCapture(event.pointerId);
}
function startMove(event, node) {
  movedNode.value = '';
  if (
    !props.editable ||
    node.referenceOnly ||
    event.button !== 0 ||
    event.pointerType !== 'mouse'
  )
    return;
  event.preventDefault();
  const additive = event.shiftKey || event.ctrlKey || event.metaKey;
  const selected = props.selected.includes(node.identity)
    ? props.selected
    : additive
      ? [...props.selected, node.identity]
      : [node.identity];
  if (additive || !props.selected.includes(node.identity))
    emit('select', node.identity, additive);
  dragging.value = {
    kind: 'node',
    id: event.pointerId,
    identity: node.identity,
    additive,
    x: event.clientX,
    y: event.clientY,
    nodes: selected
      .map((identity) => byIdentity.value[identity])
      .filter((item) => item && !item.referenceOnly)
  };
  viewport.value.setPointerCapture(event.pointerId);
}
function pan(event) {
  if (connecting.value) connectionCursor.value = point(event);
  const start = dragging.value;
  if (!start || start.id !== event.pointerId) return;
  if (start.kind === 'pan') {
    viewport.value.scrollLeft = start.left + start.x - event.clientX;
    viewport.value.scrollTop = start.top + start.y - event.clientY;
  } else if (start.kind === 'selection') {
    start.point = point(event);
  } else {
    const x = (event.clientX - start.x) / zoom.value,
      y = (event.clientY - start.y) / zoom.value;
    if (!start.moved && Math.abs(x) + Math.abs(y) > 3) {
      start.moved = true;
    }
    if (start.moved)
      emit(
        'move',
        start.nodes.map((node) => ({
          identity: node.identity,
          nodeX: Math.max(0, node.nodeX + x),
          nodeY: Math.max(0, node.nodeY + y)
        }))
      );
  }
}
function endPan(event) {
  if (dragging.value?.id === event.pointerId) {
    const frame = selectionFrame.value;
    if (frame && event.type === 'pointerup') {
      const names = nodes.value
        .filter(
          (node) =>
            node.nodeX + nodeWidth(node) >= frame.x &&
            node.nodeX <= frame.x + frame.width &&
            node.nodeY + 72 >= frame.y &&
            node.nodeY <= frame.y + frame.height
        )
        .map((node) => node.identity);
      emit(
        'select-many',
        dragging.value.additive
          ? [...new Set([...props.selected, ...names])]
          : names
      );
    }
    movedNode.value =
      dragging.value.kind === 'node' ? dragging.value.identity : '';
    dragging.value = null;
    if (viewport.value.hasPointerCapture(event.pointerId))
      viewport.value.releasePointerCapture(event.pointerId);
  }
}
function selectNode(event, node) {
  if (movedNode.value === node.identity) {
    movedNode.value = '';
    return;
  }
  if (props.interactive)
    emit(
      'select',
      node.identity,
      event.shiftKey || event.ctrlKey || event.metaKey
    );
}
const pendingPath = computed(() => {
  const node = byIdentity.value[connecting.value];
  if (!node) return '';
  const x1 = node.nodeX + (inputPort.value ? 0 : nodeWidth(node)),
    y1 = node.nodeY + 36;
  const { x: x2, y: y2 } = connectionCursor.value,
    middle = (x1 + x2) / 2;
  return `M ${x1} ${y1} C ${middle} ${y1}, ${middle} ${y2}, ${x2} ${y2}`;
});
function port(identity, input) {
  if (!props.editable) return;
  viewport.value.focus();
  if (!connecting.value || inputPort.value === input) {
    connecting.value = connecting.value === identity ? '' : identity;
    inputPort.value = input;
    const node = byIdentity.value[identity];
    connectionCursor.value = {
      x: node.nodeX + (input ? 0 : nodeWidth(node)),
      y: node.nodeY + 36
    };
  } else if (connecting.value !== identity) {
    emit(
      'connect',
      input ? connecting.value : identity,
      input ? identity : connecting.value
    );
    connecting.value = '';
  }
}
function keyboard(event) {
  if (event.key === 'Escape') {
    if (connecting.value) connecting.value = '';
    else if (dragging.value) dragging.value = null;
    else emit('select', '');
    event.stopPropagation();
  } else if (['+', '=', '-'].includes(event.key)) {
    event.preventDefault();
    zoomAt(zoom.value + (event.key === '-' ? -0.1 : 0.1));
  } else if (
    props.editable &&
    ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)
  ) {
    event.preventDefault();
    const x =
      event.key === 'ArrowLeft' ? -10 : event.key === 'ArrowRight' ? 10 : 0;
    const y =
      event.key === 'ArrowUp' ? -10 : event.key === 'ArrowDown' ? 10 : 0;
    emit(
      'move',
      nodes.value
        .filter(
          (node) =>
            props.selected.includes(node.identity) && !node.referenceOnly
        )
        .map((node) => ({
          identity: node.identity,
          nodeX: Math.max(0, node.nodeX + x),
          nodeY: Math.max(0, node.nodeY + y)
        }))
    );
  }
}
watch(
  () => props.graph.center,
  () => {
    connecting.value = '';
    reset();
  }
);
defineExpose({ centerSelection, reset });
</script>

<template>
  <section class="configuration-group relationship-map">
    <h3>{{ t(title) }}</h3>
    <p class="muted">{{ t(description) }}</p>
    <p v-if="toolbarTarget" class="graph-canvas-help muted">
      {{
        t(
          'Wheel: zoom. Middle-button drag: pan. Shift/Ctrl-click or drag a frame to select nodes.'
        )
      }}
    </p>
    <Teleport defer :to="toolbarTarget || 'body'" :disabled="!toolbarTarget"
      ><div
        class="relationship-controls"
        :class="{ 'graph-toolbar-controls': toolbarTarget }"
      >
        <p v-if="!toolbarTarget" class="muted">
          {{ t('Wheel: zoom · Middle-button drag: pan') }}
        </p>
        <div class="view-actions">
          <button
            type="button"
            class="icon-button"
            :aria-label="t('Zoom out')"
            :title="t('Zoom out')"
            :disabled="zoom <= 0.4"
            @click="zoomAt(zoom - 0.1)"
          >
            <AppIcon name="minus" />
          </button>
          <output :aria-label="t('Zoom level')" aria-live="polite"
            >{{ Math.round(zoom * 100) }}%</output
          >
          <button
            type="button"
            class="icon-button"
            :aria-label="t('Zoom in')"
            :title="t('Zoom in')"
            :disabled="zoom >= 2"
            @click="zoomAt(zoom + 0.1)"
          >
            <AppIcon name="add" />
          </button>
          <button
            type="button"
            class="icon-button"
            :aria-label="t('Reset canvas view')"
            :title="t('Reset canvas view')"
            @click="reset"
          >
            <AppIcon name="refresh" />
          </button>
        </div></div
    ></Teleport>
    <div
      ref="viewport"
      class="relationship-viewport"
      :class="{ 'is-panning': dragging?.kind === 'pan' }"
      tabindex="0"
      role="region"
      :aria-label="t(title)"
      @keydown="keyboard"
      @keydown.delete.prevent="editable && emit('remove')"
      @keydown.home.prevent="reset"
      @keydown.f.prevent="centerSelection"
      @keydown.ctrl.s.prevent="editable && emit('save')"
      @wheel.prevent="zoomAt(zoom + ($event.deltaY < 0 ? 0.1 : -0.1), $event)"
      @pointerdown="startPan"
      @pointermove="pan"
      @pointerup="endPan"
      @pointercancel="endPan"
      @lostpointercapture="dragging = null"
    >
      <svg
        :width="width * zoom"
        :height="height * zoom"
        :viewBox="`${left} ${top} ${width} ${height}`"
        :role="interactive ? 'group' : 'img'"
        :aria-label="t('Relationship map for {name}', { name: graph.center })"
      >
        <defs>
          <marker
            :id="arrowId"
            viewBox="0 0 10 10"
            refX="10"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path class="relationship-arrow" d="M 0 0 L 10 5 L 0 10 Z" />
          </marker>
        </defs>
        <g
          v-for="edge in edges"
          :key="edge.edgeIndex"
          class="relationship-edge"
          :class="{
            'is-selected': interactive && edge.edgeIndex === selectedEdge
          }"
        >
          <path :d="edge.path" :marker-end="`url(#${arrowId})`" />
          <path
            v-if="interactive"
            class="graph-edge-target"
            :d="edge.path"
            role="button"
            tabindex="0"
            :aria-label="
              t('Connection {from} to {to}', { from: edge.from, to: edge.to })
            "
            @click="emit('edge', edge.edgeIndex)"
            @keydown.enter.prevent="emit('edge', edge.edgeIndex)"
          />
          <text :x="edge.x" :y="edge.y" text-anchor="middle">
            {{ edge.label }}
          </text>
        </g>
        <g
          v-for="node in nodes"
          :key="node.identity"
          class="relationship-node"
          :class="{
            'is-center': interactive
              ? selected.includes(node.identity)
              : node.identity === graph.center,
            'is-missing': node.referenceOnly && interactive
          }"
          :data-identity="node.identity"
          :transform="`translate(${node.nodeX} ${node.nodeY})`"
          :style="{ '--node-color': nodeColor(node) }"
          :role="interactive ? 'button' : undefined"
          :tabindex="interactive ? 0 : undefined"
          :aria-label="interactive ? node.label || node.identity : undefined"
          @click="selectNode($event, node)"
          @keydown.enter.prevent="interactive && emit('select', node.identity)"
          @pointerdown.stop="startMove($event, node)"
        >
          <title>{{ node.label }} · {{ node.identity }}</title>
          <rect
            :width="nodeWidth(node)"
            height="72"
            :rx="node.kind === 'progress' ? 36 : undefined"
            :class="{ 'is-circular': node.kind === 'progress' }"
          />
          <circle
            v-for="input in [true, false]"
            :key="String(input)"
            :cx="input ? 0 : nodeWidth(node)"
            cy="36"
            r="6"
            class="graph-port"
            :class="{
              'output-port': !input,
              'is-pending': connecting === node.identity && inputPort === input
            }"
            :role="editable ? 'button' : undefined"
            :tabindex="editable ? 0 : undefined"
            :aria-label="
              t(input ? 'Input port for {name}' : 'Output port for {name}', {
                name: node.label
              })
            "
            @pointerdown.stop
            @click.stop="port(node.identity, input)"
            @keydown.enter.stop.prevent="port(node.identity, input)"
            @keydown.space.stop.prevent="port(node.identity, input)"
          />
          <foreignObject x="18" y="10" :width="nodeWidth(node) - 36" height="52"
            ><div
              xmlns="http://www.w3.org/1999/xhtml"
              class="relationship-node-label"
            >
              <strong>{{ node.label }}</strong
              ><small>{{ node.kind }}</small>
            </div></foreignObject
          >
        </g>
        <path
          v-if="pendingPath"
          :d="pendingPath"
          class="graph-pending-connection"
        />
        <rect
          v-if="selectionFrame"
          v-bind="selectionFrame"
          class="graph-selection-frame"
        />
      </svg>
    </div>
  </section>
</template>
