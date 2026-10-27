<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import ResultPresentation from '../workspace/ResultPresentation.vue';
import { rpc } from '../../api.js';
import { appearance } from '../../appearance.js';
import * as Items from '../../../../src/tactic_stream/shared_ui/features/table/items.ui.mjs';
const props = defineProps({
  frameNode: Object,
  ticket: String,
  project: String,
  selectedKeys: Array,
  workspaceId: String,
  active: { type: Boolean, default: true },
  editing: Boolean
});
const emit = defineEmits(['inspect', 'operate', 'select', 'focus', 'loaded']);
const records = ref([]),
  busy = ref(false),
  error = ref(''),
  hasMore = ref(false),
  state = ref({}),
  definition = ref(null);
let generation = 0;
const scene = computed(() =>
  Items.describe(
    { busy: busy.value, error: error.value, hasMore: hasMore.value },
    props.frameNode.width,
    props.frameNode.height,
    appearance.language
  )
);
const views = computed(() => ({
  itemResults: {
    component: ResultPresentation,
    props: {
      rows: records.value,
      ticket: props.ticket,
      project: props.project,
      searchType: props.frameNode.items.searchType,
      mode:
        props.editing &&
        definition.value?.table.item_layout?.collection === 'grid'
          ? 'tiles'
          : 'continious',
      itemLayout: definition.value?.table.item_layout || null,
      groupMode: 'none',
      active: props.active,
      workspaceId: props.workspaceId,
      readOnly: props.editing,
      state: state.value,
      selectedKeys: props.selectedKeys || [],
      onState: (value) => (state.value = value),
      onInspect: (record) => emit('inspect', record),
      onOperate: (...args) => emit('operate', ...args),
      onSelect: (...args) => emit('select', ...args),
      onFocus: (value) => emit('focus', value)
    }
  }
}));
async function load(append = false) {
  if (!props.active) return;
  if (append && busy.value) return;
  const current = ++generation;
  busy.value = true;
  error.value = '';
  const scope = props.frameNode.items;
  if (!append) records.value = [];
  try {
    const response = await rpc('execute_cmd', [
      { ticket: props.ticket, project: props.project, language: 'python' },
      'tactic.ui.table.NestedTableReadCmd',
      {
        search_type: scope.searchType,
        parent_key: scope.parentKey,
        view: scope.view,
        filters: scope.filters,
        project_scope: true,
        offset: append ? records.value.length : 0,
        limit: props.editing ? 3 : scope.initialLimit,
        order_by: [scope.orderBy]
      }
    ]);
    if (current !== generation) return;
    definition.value = response.info.definition;
    records.value = append
      ? [...records.value, ...response.info.records]
      : response.info.records;
    hasMore.value = !props.editing && response.info.hasNext;
    emit('loaded', { definition: definition.value, records: records.value });
  } catch (failure) {
    if (current === generation) error.value = failure.message;
  } finally {
    if (current === generation) busy.value = false;
  }
}
watch(
  () =>
    JSON.stringify([
      props.ticket,
      props.project,
      props.frameNode.items,
      props.editing
    ]),
  () => load(),
  { immediate: true }
);
onBeforeUnmount(() => ++generation);
watch(
  () => props.active,
  (value) => {
    if (value && !records.value.length && !busy.value) load();
    else if (value && definition.value)
      emit('loaded', { definition: definition.value, records: records.value });
  }
);
</script>
<template>
  <FrameView
    class="dashboard-items"
    :scene="scene"
    :views="views"
    @event="(action) => load(action.type === 'more')"
  />
</template>
<style>
.dashboard-items > [data-frame='dashboardItemResults'] {
  overflow: auto;
  scrollbar-gutter: stable;
}
</style>
