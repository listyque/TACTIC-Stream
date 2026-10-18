<script setup>
import {
  computed,
  ref,
  shallowRef,
  markRaw,
  onMounted,
  onBeforeUnmount
} from 'vue';
import FrameView from '../../../frame/FrameView.vue';
import WorkspaceTabs from '../../../controls/WorkspaceTabs.vue';
import AppMenu from '../../../controls/AppMenu.vue';
import AppMenuItem from '../../../controls/AppMenuItem.vue';
import { observeFrameSizes } from '../../../frame/resize.js';
import { appearance } from '../../../appearance.js';
import { metrics } from '../../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import * as UI from '../../../../../src/tactic_stream/shared_ui/features/files/workspace/toolbar.ui.mjs';

const props = defineProps({ tabs: Array, selected: String, presets: Array });
const emit = defineEmits(['select', 'close', 'reorder', 'open']);
const host = ref(null),
  menu = ref(null),
  anchor = shallowRef(null),
  width = ref(800),
  gutter = ref(0);
const height = computed(
  () => metrics(appearance.theme).controlHeight + gutter.value
);
const scene = computed(() =>
  UI.views(
    { style: appearance.theme, canActions: false },
    width.value,
    height.value,
    appearance.language
  )
);
const views = computed(() => ({
  tabs: {
    component: markRaw(WorkspaceTabs),
    props: {
      kind: 'view',
      tabs: props.tabs,
      selected: props.selected,
      onSelect: (value) => emit('select', value),
      onClose: (value) => emit('close', value),
      onReorder: (value) => emit('reorder', value),
      onGutter: (value) => (gutter.value = value)
    }
  }
}));
function event(action, source) {
  if (action.type === 'menu' && action.kind === 'views') {
    anchor.value = source;
    menu.value.openAt({ target: source });
  }
}
let observer;
onMounted(() => {
  observer = observeFrameSizes(
    (entries) => (width.value = entries.at(-1).contentRect.width)
  );
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="host" class="inspection-views" :style="{ height: height + 'px' }">
    <FrameView :scene="scene" :views="views" @event="event" />
    <AppMenu
      ref="menu"
      label="View"
      :anchor="anchor"
      external-trigger
      overlay
      align-start
    >
      <AppMenuItem
        v-for="view in presets"
        :key="view.id"
        :label="view.title"
        :icon="view.icon"
        @click="emit('open', view)"
      />
    </AppMenu>
  </div>
</template>
<style scoped>
.inspection-views {
  position: relative;
  flex: none;
  min-width: 0;
}
</style>
