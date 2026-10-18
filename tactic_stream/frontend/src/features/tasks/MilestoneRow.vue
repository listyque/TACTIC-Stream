<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import { metrics as frameMetrics } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/milestones.ui.mjs';
const props = defineProps({ model: Object });
const emit = defineEmits(['event']);
const root = ref(null),
  width = ref(800);
let observer;
const scene = computed(() =>
  UI.row(
    {
      ...props.model,
      radius: frameMetrics(appearance.theme).itemRadius,
      controlHeight: frameMetrics(appearance.theme).controlHeight
    },
    width.value,
    appearance.language
  )
);
onMounted(() => {
  observer = observeFrameSizes(
    (entries) => (width.value = entries[0].contentRect.width)
  );
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <article
    ref="root"
    class="milestone-frame-row"
    role="group"
    :aria-label="model.description || t('New milestone')"
    :data-milestone="model.code"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView :scene="scene" @event="(event) => emit('event', event)" />
  </article>
</template>
<style>
.milestone-frame-row {
  position: relative;
  flex: none;
  min-width: 0;
}
</style>
