<script setup>
import { computed } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import CanvasSelection from './CanvasSelection.vue';
import { appearance } from '../../appearance.js';
import * as Samples from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/layout.samples.mjs';
import { asyncComponent } from '../../controls/asyncComponent.js';
const ResultPresentation = asyncComponent(
  () => import('../workspace/ResultPresentation.vue')
);
import { t } from '../../i18n.js';
const props = defineProps({
  frameNode: Object,
  sample: Object,
  layout: Object,
  rows: Array,
  ticket: String,
  project: String,
  searchType: String,
  selectedElement: String,
  editing: Boolean,
  error: String
});
const emit = defineEmits(['element', 'geometry']);
const sampleScene = computed(() =>
  Samples.scene(
    props.layout,
    props.sample,
    props.frameNode?.width || 1,
    props.frameNode?.height || 1,
    props.selectedElement,
    props.editing,
    appearance.language,
    window.innerWidth,
    location.origin
  )
);
const sampleViews = computed(() => ({
  canvasOverlay: {
    component: CanvasSelection,
    props: {
      boxes: sampleScene.value.canvasBoxes || [],
      selected: props.selectedElement,
      onSelect: (name) => emit('element', name),
      onCommit: (value) => emit('geometry', value)
    }
  }
}));
</script>
<template>
  <div
    class="layout-live-preview"
    :class="sample ? 'layout-sample-preview' : 'table-container'"
  >
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <FrameView
      v-if="sample"
      :scene="sampleScene"
      :views="sampleViews"
      @event="
        (event) => {
          if (event.type === 'select') emit('element', event.name);
        }
      "
    />
    <ResultPresentation
      v-if="layout"
      v-show="!sample"
      :rows="rows"
      :ticket="ticket"
      :project="project"
      :search-type="searchType"
      :workspace-id="'layout-preview-' + searchType"
      :item-layout="layout"
      :mode="layout.collection === 'grid' ? 'tiles' : 'continious'"
      group-mode="none"
      :selected-keys="[]"
      :state="{}"
      active
      read-only
      :editing="editing"
      :selected-element="selectedElement"
      @geometry="$emit('geometry', $event)"
      @element="$emit('element', $event)"
    />
    <p v-else-if="!error" class="muted">{{ t('Loading interface...') }}</p>
  </div>
</template>
<style>
.layout-live-preview {
  height: 100%;
  overflow: auto;
  scrollbar-gutter: stable;
  padding: 4px;
}
.layout-sample-preview {
  padding: 0;
  overflow: hidden;
  scrollbar-gutter: auto;
}
</style>
