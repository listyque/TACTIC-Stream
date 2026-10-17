<script setup>
import { computed, ref, onMounted, onBeforeUnmount, markRaw } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import DescriptionValue from './DescriptionValue.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/description.ui.mjs';
const props = defineProps({ model: Object, text: String, html: String });
const emit = defineEmits(['event', 'value', 'link', 'finished']);
const host = ref(null),
  viewport = ref({ width: 0, height: 0 }),
  editor = ref(null);
const scene = computed(() =>
  UI.describe(
    props.model,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const valueComponent = markRaw(DescriptionValue);
const views = computed(() => ({
  value: {
    component: valueComponent,
    props: {
      ref: (instance) => {
        editor.value = instance;
      },
      text: props.text,
      html: props.html,
      model: UI.presentation(props.model, appearance.language),
      onValue: (value) => emit('value', value),
      onLink: (event) => emit('link', event),
      onFinished: (value) => emit('finished', value)
    }
  }
}));
let observer;
onMounted(() => {
  const measure = () => {
    viewport.value = {
      width: host.value.clientWidth,
      height: host.value.clientHeight
    };
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
defineExpose({ focus: () => editor.value?.focus() });
</script>
<template>
  <div ref="host" class="description-surface">
    <FrameView :scene="scene" :views="views" @event="emit('event', $event)" />
  </div>
</template>
<style>
.description-surface {
  width: 100%;
  height: 100%;
  min-height: 0;
}
</style>
