<script setup>
import { computed, h, useSlots } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/search/card.ui.mjs';
const props = defineProps({ model: Object, width: Number, height: Number });
const slots = useSlots();
const views = Object.fromEntries(
  ['title', 'metadata', 'technical', 'description'].map((name) => [
    name,
    {
      component: () => h('div', { class: 'result-body-slot' }, slots[name]?.())
    }
  ])
);
const scene = computed(() => UI.body(props.model, props.width, props.height));
</script>
<template><FrameView :scene="scene" :views="views" /></template>
<style>
.result-body-slot {
  display: flex;
  align-items: center;
  min-width: 0;
  overflow: hidden;
}
.result-body-slot > * {
  min-width: 0;
  max-width: 100%;
}
.result-body-slot .result-title-line {
  display: flex;
  align-items: center;
  width: max-content;
  max-width: 100%;
  height: 100%;
  overflow: visible;
}
.result-body-slot .result-title-line strong {
  font-size: inherit;
}
.result-body-slot .result-snapshot-technical,
.result-body-slot .result-snapshot-description {
  width: 100%;
}
.result-body-slot .result-metadata {
  height: 100%;
  flex-wrap: nowrap;
}
.result-body-slot .result-completion {
  flex: none;
}
</style>
