<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import ShowcaseMenu from './ShowcaseMenu.vue';
import ShowcaseDialog from './ShowcaseDialog.vue';
import ShowcaseVariant from './ShowcaseVariant.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/showcase.ui.mjs';
const host = ref(null),
  view = ref(null),
  size = ref({ width: 1, height: 1 }),
  model = ref(UI.initial());
const scene = computed(() =>
  UI.describe(
    model.value,
    UI.catalogue,
    size.value.width,
    size.value.height,
    appearance.language
  )
);
const models = computed(() => ({
  ...UI.models(model.value),
  families: UI.families(UI.catalogue, model.value, appearance.language)
}));
const views = {
  showcaseVariant: {
    component: ShowcaseVariant,
    nodeProps: true,
    props: { onEvent: dispatch }
  },
  showcaseMenu: {
    component: ShowcaseMenu,
    nodeProps: true,
    props: { onEvent: dispatch }
  },
  showcaseDialog: {
    component: ShowcaseDialog,
    nodeProps: true,
    props: { onEvent: dispatch }
  }
};
function dispatch(event) {
  model.value = UI.transition(model.value, event, UI.catalogue);
}
defineExpose({ dispatch, model, scene });
let observer;
onMounted(() => {
  observer = observeFrameSizes(
    ([entry]) =>
      (size.value = {
        width: Math.max(1, entry.contentRect.width),
        height: Math.max(1, entry.contentRect.height)
      })
  );
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <section ref="host" class="component-showcase">
    <FrameView
      ref="view"
      :scene="scene"
      :models="models"
      :views="views"
      :describe-cell="
        (grid, record, row, column) =>
          UI.cell(grid, record, row, column, model, appearance.language)
      "
      :describe-row="
        (list, record) => UI.row(list, record, model, appearance.language)
      "
      @event="dispatch"
    />
  </section>
</template>
<style scoped>
.component-showcase {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
</style>
