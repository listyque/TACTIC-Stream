<script setup>
import { computed, ref, onMounted, onBeforeUnmount, h, useSlots } from 'vue';
import { observeFrameSizes } from '../../frame/resize.js';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/snapshot.ui.mjs';
const props = defineProps({ model: Object });
const emit = defineEmits(['event']);
const host = ref(null),
  width = ref(0),
  slots = useSlots();
const views = {
  options: {
    component: (props, { attrs }) =>
      h(
        'div',
        { ...attrs, class: ['snapshot-options-control', attrs.class] },
        slots.options?.()
      )
  }
};
const scene = computed(() =>
  UI.toolbar(props.model, width.value, appearance.language)
);
let observer;
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
  <header ref="host" class="snapshot-frame-toolbar">
    <FrameView :scene="scene" :views="views" @event="emit('event', $event)" />
  </header>
</template>
<style>
.snapshot-frame-toolbar {
  height: 46px;
  flex: none;
  min-width: 0;
}
.snapshot-options-control,
.snapshot-options-control > .workspace-menu {
  width: 100%;
  height: 100%;
}
.snapshot-options-control summary.icon-button {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  background: var(--surface-high);
  --icon-size: 16px;
}
</style>
