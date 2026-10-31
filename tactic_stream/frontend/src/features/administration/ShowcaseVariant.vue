<script setup>
import { computed } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import ShowcaseControl from './ShowcaseControl.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/showcase.variants.mjs';
import * as Variants from '../../../../src/tactic_stream/shared_ui/controls/catalog/variants.mjs';
import * as Base from '../../../../src/tactic_stream/shared_ui/controls/catalog.ui.mjs';
const props = defineProps({ frameNode: Object });
const model = computed(() => props.frameNode.model);
const state = computed(() => props.frameNode.state);
const language = computed(() => props.frameNode.language);
const emit = defineEmits(['event']);
const models = computed(() => ({
  cells: model.value.id.startsWith('table')
    ? Array.from({ length: 50 }, () => [{}, {}, {}])
    : [],
  treeRows: Base.treeRows(model.value)
}));
const scene = computed(() =>
  UI.describe(model.value, props.frameNode.width, language.value, state.value)
);
function dispatch(action) {
  emit('event', {
    type: props.frameNode.gallery ? 'galleryEvent' : 'variantEvent',
    id: props.frameNode.gallery,
    value: action
  });
}
const views = computed(() => ({
  example: {
    component: ShowcaseControl,
    props: {
      example: Variants.find(model.value.id),
      value: model.value.value,
      disabled: ['disabled', 'loading'].includes(state.value),
      readonly: state.value === 'readonly',
      onEvent: dispatch
    }
  }
}));
</script>
<template>
  <FrameView
    :scene="scene"
    :models="models"
    :views="views"
    :describe-row="
      (list, record) => Variants.row(list, record, model, language, state)
    "
    :describe-cell="
      (grid, record, row, column) =>
        Variants.cell(grid, record, row, column, model, state)
    "
    @event="dispatch"
  />
</template>
