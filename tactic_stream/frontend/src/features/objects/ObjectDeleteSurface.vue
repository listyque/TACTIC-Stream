<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import ContentLoadingOverlay from '../../controls/display/ContentLoadingOverlay.vue';
import ObjectDependencyList from './ObjectDependencyList.vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/delete.ui.mjs';
const props = defineProps({ model: Object });
const emit = defineEmits(['event']);
const host = ref(null),
  size = ref({ width: 0, height: 0 });
const models = computed(() => UI.models(props.model, appearance.language));
const views = computed(() => ({
  dependencies: {
    component: ObjectDependencyList,
    nodeProps: true,
    props: { models: models.value }
  }
}));
let observer;
const scene = computed(() =>
  UI.describe(
    props.model,
    size.value.width,
    size.value.height,
    appearance.language
  )
);
onMounted(() => {
  const measure = () => {
    size.value = {
      width: host.value.clientWidth,
      height: host.value.clientHeight
    };
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <section ref="host" class="object-delete-surface">
    <FrameView
      :scene="scene"
      :models="models"
      :views="views"
      :describe-row="
        (list, record) =>
          list.id === 'deleteSObjectTargets'
            ? UI.target(record, list.width - 16)
            : UI.dependency(record, list.width - 16)
      "
      @event="emit('event', $event)"
    />
    <ContentLoadingOverlay
      v-if="scene.loading"
      :message="scene.loading.message"
      :cancellable="scene.loading.cancellable"
      :style="{
        left: scene.loading.bounds.x + 'px',
        top: scene.loading.bounds.y + 'px',
        width: scene.loading.bounds.width + 'px',
        height: scene.loading.bounds.height + 'px'
      }"
      @cancel="emit('event', { type: 'cancel' })"
    />
  </section>
</template>
<style>
.object-delete-surface {
  position: relative;
  min-width: 0;
  min-height: 0;
  flex: 1;
  height: 100%;
}
</style>
