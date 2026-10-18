<script setup>
import { computed, ref, watch, markRaw, h, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppSpinBox from '../../controls/forms/AppSpinBox.vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/columns.ui.mjs';
const props = defineProps({ columns: Array, busy: Boolean });
const emit = defineEmits(['event']);
const host = ref(null),
  width = ref(0);
const scene = computed(() =>
  UI.describe(props, width.value, appearance.language)
);
const input = markRaw({
  props: { frameNode: Object },
  setup(p) {
    return () =>
      h(AppSpinBox, {
        min: 40,
        max: 480,
        step: 1,
        decimals: 0,
        label: p.frameNode.label,
        modelValue: Number(p.frameNode.record.width),
        disabled: !p.frameNode.enabled,
        'onUpdate:modelValue': (value) =>
          emit('event', { type: 'width', field: p.frameNode.record.key, value })
      });
  }
});
const views = { width: { component: input, nodeProps: true } };
let observer;
watch(
  host,
  (element) => {
    observer?.disconnect();
    if (!element) return;
    const measure = () => (width.value = frameContentWidth(element));
    measure();
    observer = observeFrameSizes(measure);
    observer.observe(element);
  },
  { flush: 'post' }
);
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="task-columns-frame"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView
      :scene="scene"
      :views="views"
      @event="(action) => emit('event', action)"
    />
  </div>
</template>
<style>
.task-columns-frame {
  position: relative;
  width: 100%;
  min-width: 0;
}
.task-columns-frame input {
  width: 100%;
  height: 100%;
  min-height: 0;
}
</style>
