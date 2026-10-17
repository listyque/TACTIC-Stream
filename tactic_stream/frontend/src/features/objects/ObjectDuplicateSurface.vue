<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/duplicate.ui.mjs';
const props = defineProps({
  model: Object,
  part: { type: String, default: 'body' }
});
const emit = defineEmits(['event']);
const host = ref(null),
  width = ref(0);
const scene = computed(() =>
  UI[props.part](props.model, width.value, appearance.language)
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
  <section
    ref="host"
    class="object-duplicate-surface"
    :role="part === 'tabs' ? 'radiogroup' : undefined"
    :aria-label="part === 'tabs' ? t('Duplicate steps') : undefined"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView :scene="scene" @event="emit('event', $event)" />
  </section>
</template>
<style>
.object-duplicate-surface {
  position: relative;
  min-width: 0;
  flex: none;
  width: 100%;
}
</style>
