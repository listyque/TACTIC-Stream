<script setup>
import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import ConfiguredView from '../interface/ConfiguredView.vue';
import { rpc } from '../../api.js';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as Page from '../../../../src/tactic_stream/shared_ui/features/table/page.ui.mjs';

const props = defineProps({
  ticket: String,
  project: String,
  view: String,
  title: String,
  target: String,
  workspaceId: String,
  selectedKeys: Array,
  canAdminister: Boolean,
  active: { type: Boolean, default: true }
});
const emit = defineEmits([
  'inspect',
  'operate',
  'column',
  'close',
  'select',
  'focus',
  'loaded',
  'edit'
]);
const host = ref(null),
  size = ref({ width: 800, height: 600 }),
  model = ref(null),
  renderRevision = ref(0),
  busy = ref(false),
  error = ref('');
const scene = computed(() =>
  Page.describe(
    {
      title: props.title,
      busy: busy.value,
      error: error.value,
      canEdit: props.canAdminister && props.view?.startsWith('dashboard.')
    },
    size.value.width,
    size.value.height,
    appearance.language
  )
);
const bodyStyle = computed(() => {
  const box = scene.value.bodyBounds;
  return {
    left: box.x + 'px',
    top: box.y + 'px',
    width: box.width + 'px',
    height: box.height + 'px'
  };
});
let generation = 0,
  observer;
let appliedFilters = {};
async function reload(filterValues = appliedFilters, preserveInput = false) {
  const request = ++generation;
  busy.value = true;
  error.value = '';
  try {
    const result = await rpc('execute_cmd', [
      { ticket: props.ticket, project: props.project, language: 'python' },
      'tactic.ui.table.CustomLayoutReadCmd',
      {
        view: props.view,
        search_key: props.target || '',
        filter_values: filterValues
      }
    ]);
    if (request === generation) {
      appliedFilters = filterValues;
      model.value = { ...result.info, record: result.info.layoutRecord };
      if (!preserveInput) renderRevision.value++;
    }
  } catch (failure) {
    if (request === generation) error.value = failure.message;
  } finally {
    if (request === generation) busy.value = false;
  }
}
watch(
  () => [props.ticket, props.project, props.view, props.target],
  () => {
    appliedFilters = {};
    model.value = null;
    reload();
  },
  {
    immediate: true
  }
);
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    size.value = { width: box.width, height: box.height };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => {
  ++generation;
  observer?.disconnect();
});
defineExpose({ reload, workspaceId: computed(() => props.workspaceId) });
</script>
<template>
  <section ref="host" class="workspace-page" :aria-busy="busy">
    <FrameView
      :scene="scene"
      @event="
        (event) =>
          event.type === 'edit' ? emit('edit', view.slice(10)) : reload()
      "
    />
    <ConfiguredView
      v-if="model"
      :key="renderRevision"
      class="workspace-page-layout"
      :style="bodyStyle"
      :layout-model="model"
      :layout-busy="busy"
      @filter-apply="(values) => reload(values, true)"
      :layout-width="scene.bodyBounds.width"
      :layout-height="scene.bodyBounds.height"
      :ticket="ticket"
      :project="project"
      :workspace-id="workspaceId"
      :active="active"
      @loaded="emit('loaded', $event)"
      :selected-keys="selectedKeys"
      :read-only="false"
      @inspect="emit('inspect', $event)"
      @select="(...args) => emit('select', ...args)"
      @focus="emit('focus', $event)"
      @operate="(...args) => emit('operate', ...args)"
      @column="emit('column', $event)"
      @close="emit('close')"
    />
  </section>
</template>
<style>
.workspace-page {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
  width: 100%;
  height: 100%;
}
.workspace-page > .frame-view {
  position: absolute;
  inset: 0;
}
.workspace-page-layout {
  position: absolute;
}
</style>
