<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { rpc } from '../../api.js';
import { appearance } from '../../appearance.js';
import * as Tree from '../../../../src/tactic_stream/shared_ui/features/table/tree.ui.mjs';
const props = defineProps({
  frameNode: Object,
  ticket: String,
  project: String
});
const emit = defineEmits(['action']);
const model = ref(Tree.initial(props.frameNode.tree));
let generation = 0;
const scene = computed(() =>
  Tree.describe(
    model.value,
    props.frameNode.width,
    props.frameNode.height,
    appearance.language
  )
);
const models = computed(() => ({ rows: Tree.rows(model.value) }));
function describeRow(list, item) {
  return Tree.row(model.value, item, list.width - 16, appearance.language);
}
async function activate(action) {
  if (action.type === 'inspect') {
    emit('action', {
      type: 'service',
      name: 'layout-link',
      href: 'skey://' + action.key
    });
    return;
  }
  const changed = Tree.change(model.value, action);
  model.value = changed.model;
  if (!changed.request) return;
  const request = changed.request,
    current = generation;
  try {
    const result = await rpc('execute_cmd', [
      { ticket: props.ticket, project: props.project, language: 'python' },
      'tactic.ui.panel.dashboard_cmd.DashboardCmd',
      {
        action: 'tree',
        project_code: props.project,
        tree: request.tree,
        branch_path: request.branch_path,
        parent_key: request.parent_key,
        offset: request.offset,
        limit: request.limit
      }
    ]);
    if (current === generation)
      model.value = Tree.accept(model.value, request, result.info);
  } catch (error) {
    if (current === generation)
      model.value = Tree.accept(model.value, request, null, error.message);
  }
}
watch(
  () => [props.frameNode.tree, props.ticket, props.project],
  () => {
    ++generation;
    model.value = Tree.initial(props.frameNode.tree);
    activate({ type: 'refresh' });
  },
  { immediate: true }
);
onBeforeUnmount(() => {
  ++generation;
});
</script>
<template>
  <FrameView
    :scene="scene"
    :models="models"
    :describe-row="describeRow"
    @event="activate"
  />
</template>
