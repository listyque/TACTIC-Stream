<script setup>
import { computed, ref, onMounted, onBeforeUnmount, markRaw, h } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/empty.ui.mjs';
import * as Workspace from '../../../../src/tactic_stream/shared_ui/features/tasks/workspace.ui.mjs';
import { metrics } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
const props = defineProps({
  busy: Boolean,
  filtered: Boolean,
  canCreate: Boolean,
  toolbarWidth: Number
});
const host = ref(null),
  width = ref(0),
  height = ref(0);
const scene = computed(() => {
  const toolbar = Workspace.toolbar(
      {
        embedded: true,
        controlHeight: metrics(appearance.theme).controlHeight
      },
      props.toolbarWidth || width.value + 12,
      appearance.language
    ),
    bounds = toolbar.createBounds;
  return UI.describe(
    {
      ...props,
      target: {
        x: bounds.x + bounds.width / 2 - 6,
        y: bounds.y + bounds.height - toolbar.height - 5 + 4
      }
    },
    width.value,
    height.value,
    appearance.language
  );
});
const arrow = markRaw({
  props: { frameNode: Object },
  setup(p) {
    return () => {
      const n = p.frameNode,
        offset = -n.y;
      const path = `M ${n.source[0]} ${n.source[1] + offset} C ${n.first[0]} ${n.first[1] + offset}, ${n.second[0]} ${n.second[1] + offset}, ${n.target[0]} ${n.target[1] + offset}`;
      const head = n.tips
        .map(
          (tip) =>
            `M ${n.target[0]} ${n.target[1] + offset} L ${tip[0]} ${tip[1] + offset}`
        )
        .join(' ');
      return h(
        'svg',
        { width: n.width, height: n.height, 'aria-hidden': 'true' },
        [
          h('path', {
            d: path + ' ' + head,
            fill: 'none',
            stroke: 'var(--primary)',
            'stroke-width': 2.5,
            'stroke-linecap': 'round',
            'stroke-linejoin': 'round'
          })
        ]
      );
    };
  }
});
const views = { arrow: { component: arrow, nodeProps: true } };
let observer;
onMounted(() => {
  const measure = () => {
    width.value = frameContentWidth(host.value);
    height.value = host.value.clientHeight;
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="host" class="task-empty-state" role="status">
    <FrameView :scene="scene" :views="views" />
  </div>
</template>
<style>
.task-empty-state {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
}
.task-empty-state [data-frame='taskWorkspaceEmptyArrow'] {
  pointer-events: none;
}
</style>
