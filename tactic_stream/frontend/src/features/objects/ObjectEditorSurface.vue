<script setup>
import { computed, ref, h, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppSpinBox from '../../controls/forms/AppSpinBox.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/editor.ui.mjs';
const props = defineProps({ model: Object, part: String });
const emit = defineEmits(['event']);
const host = ref(null),
  width = ref(0);
let observer;
const scene = computed(() =>
  UI[props.part](props.model, width.value, appearance.language)
);
const views = {
  batchCount: {
    component: (_, context) =>
      h(AppSpinBox, {
        ...context.attrs,
        modelValue: props.model.batchCount,
        min: 2,
        max: 100,
        label: 'Number of objects',
        disabled: props.model.busy,
        'onUpdate:modelValue': (value) =>
          emit('event', { type: 'count', value })
      })
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
  <section
    ref="host"
    class="object-editor-surface"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView :scene="scene" :views="views" @event="emit('event', $event)" />
  </section>
</template>
<style>
.object-editor-surface {
  position: relative;
  min-width: 0;
  width: 100%;
  flex: none;
}
</style>
