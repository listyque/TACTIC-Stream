<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { appearance } from '../../appearance.js';
import FrameView from '../../frame/FrameView.vue';
import ConditionValue from './ConditionValue.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/search/conditions.ui.mjs';

const props = defineProps({ model: Object });
const emit = defineEmits(['event']);
const host = ref(null),
  width = ref(700),
  expanded = ref(true);
const scene = computed(() =>
  UI.describe(
    {
      ...props.model,
      expanded: props.model.expanded ?? expanded.value,
      valueView: 'value'
    },
    width.value,
    appearance.language
  )
);
const views = computed(() => ({
  value: {
    component: ConditionValue,
    nodeProps: true,
    props: {
      suggestions: props.model.suggestions,
      active: props.model.active !== false,
      onEvent: dispatch
    }
  }
}));
let observer;
onMounted(() => {
  width.value = host.value.clientWidth;
  observer = observeFrameSizes((entries) => {
    width.value = entries.at(-1).contentRect.width;
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
function dispatch(action) {
  if (action.type === 'expand') expanded.value = !expanded.value;
  emit('event', action);
}
</script>
<template>
  <div
    ref="host"
    class="search-library-conditions"
    :style="{ position: 'relative', height: scene.contentHeight + 'px' }"
  >
    <FrameView :scene="scene" :views="views" @event="dispatch" />
  </div>
</template>
