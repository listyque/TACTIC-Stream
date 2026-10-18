<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/support/documentation/api.ui.mjs';
const props = defineProps({ field: Object, busy: Boolean });
const emit = defineEmits(['change']);
const host = ref(null),
  width = ref(300);
const scene = computed(() =>
  UI.parameter(
    props.field,
    props.field.value,
    props.busy,
    width.value,
    appearance.language
  )
);
let observer;
onMounted(() => {
  observer = observeFrameSizes(() => (width.value = host.value.clientWidth));
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="api-parameter"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView
      :scene="scene"
      @event="(action) => emit('change', action.value)"
    />
  </div>
</template>
<style>
.api-parameter {
  position: relative;
  min-width: 0;
  margin: 12px 0;
}
</style>
