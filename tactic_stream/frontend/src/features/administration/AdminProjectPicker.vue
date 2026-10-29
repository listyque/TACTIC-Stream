<script setup>
import {
  computed,
  nextTick,
  ref,
  watch,
  onMounted,
  onBeforeUnmount
} from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppMenu from '../../controls/AppMenu.vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/projects.ui.mjs';
const props = defineProps({ model: { type: Object, required: true } });
const emit = defineEmits(['selected']);
const host = ref(null),
  menu = ref(null),
  content = ref(null),
  query = ref('');
const extent = ref({ width: 1, height: 38 });
const viewport = ref({ width: innerWidth, height: innerHeight });
function resize() {
  viewport.value = { width: innerWidth, height: innerHeight };
}
let observer;
onMounted(() => {
  window.addEventListener('resize', resize);
  observer = observeFrameSizes(([entry]) => {
    extent.value = {
      width: entry.contentRect.width,
      height: entry.contentRect.height
    };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => {
  observer?.disconnect();
  window.removeEventListener('resize', resize);
});
const bounds = computed(() =>
  UI.size(
    viewport.value.width,
    viewport.value.height,
    props.model.projects?.length || 0
  )
);
const rows = computed(() => UI.projects(props.model, query.value));
async function dispatch(event) {
  if (props.model.locked) return;
  if (event.type === 'open') {
    if (menu.value.open) return menu.value.close(true);
    query.value = '';
    menu.value.openAt({ target: host.value.querySelector('button') });
    await nextTick();
    content.value.focusControl('administrationProjectSearch');
  } else if (event.type === 'query') query.value = event.value;
  else if (event.type === 'focus') {
    const row = rows.value[event.index];
    if (row)
      content.value.focusListRow(
        'administrationProjectList',
        event.index,
        'administrationProjectOption_' + row.value
      );
  } else if (
    event.type === 'select' &&
    props.model.projects.some((row) => row.value === event.value)
  ) {
    menu.value.close(true);
    emit('selected', event.value);
  }
}
watch(
  () => props.model.locked,
  (locked) => {
    if (locked) menu.value?.close();
  }
);
</script>
<template>
  <div ref="host" class="admin-project-picker">
    <FrameView
      :scene="
        UI.trigger(model, extent.width, extent.height, appearance.language)
      "
      @event="dispatch"
    />
    <AppMenu
      ref="menu"
      frame-composition
      external-trigger
      overlay
      align-start
      :anchor="host"
      :width="bounds.width + 12"
      :disabled="model.locked"
      :close-on-select="false"
      label="Administration project"
    >
      <FrameView
        ref="content"
        :style="{ width: bounds.width + 'px', height: bounds.height + 'px' }"
        :scene="
          UI.panel(
            model,
            query,
            bounds.width,
            bounds.height,
            appearance.language
          )
        "
        :models="{ projects: rows }"
        :describe-row="
          (list, row) => UI.row(list, row, model, query, appearance.language)
        "
        @event="dispatch"
      />
    </AppMenu>
  </div>
</template>
<style scoped>
.admin-project-picker {
  width: 100%;
  height: 100%;
  position: relative;
}
</style>
