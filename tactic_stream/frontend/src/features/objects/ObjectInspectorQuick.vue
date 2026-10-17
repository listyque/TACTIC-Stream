<script setup>
import { computed, ref, onMounted, onBeforeUnmount, h } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import StatusSelect from '../../controls/StatusSelect.vue';
import AppSlider from '../../controls/AppSlider.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/inspector.ui.mjs';
const props = defineProps({ model: Object });
const emit = defineEmits(['event']);
const host = ref(null),
  width = ref(0);
let observer;
const scene = computed(() =>
  UI.quick(props.model, width.value, appearance.language)
);
const views = {
  status: {
    nodeProps: true,
    component: {
      props: { frameNode: Object },
      setup(port, { attrs }) {
        return () =>
          h(StatusSelect, {
            ...attrs,
            value: port.frameNode.value,
            options: port.frameNode.options,
            disabled: !port.frameNode.enabled,
            onChange: (value) =>
              emit('event', { type: 'change', field: 'status', value })
          });
      }
    }
  },
  progress: {
    nodeProps: true,
    component: {
      props: { frameNode: Object },
      setup(port, { attrs }) {
        return () =>
          h(AppSlider, {
            ...attrs,
            min: port.frameNode.minimum,
            max: port.frameNode.maximum,
            step: port.frameNode.step,
            modelValue: port.frameNode.value,
            label: 'Progress',
            disabled: !port.frameNode.enabled,
            'onUpdate:modelValue': (value) =>
              emit('event', { ...port.frameNode.action, value })
          });
      }
    }
  }
};

onMounted(() => {
  const measure = () => {
    width.value = host.value.clientWidth;
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="object-inspector-quick"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView :scene="scene" :views="views" @event="emit('event', $event)" />
  </div>
</template>
<style>
.object-inspector-quick {
  position: relative;
  min-width: 0;
  width: 100%;
}
</style>
