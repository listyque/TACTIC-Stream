<script setup>
import { computed, ref, h, useSlots, onMounted, onBeforeUnmount } from 'vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import FrameView from '../../frame/FrameView.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/search/header.ui.mjs';
const props = defineProps({ model: Object });
const emit = defineEmits(['event']);
const slots = useSlots(),
  host = ref(null),
  width = ref(0);
const views = Object.fromEntries(
  ['field', 'panels', 'quick', 'tags'].map((name) => [
    name,
    {
      component: () =>
        h('div', { class: 'search-header-slot' }, slots[name]?.())
    }
  ])
);
const scene = computed(() =>
  UI.describe(props.model, width.value, appearance.language)
);
let observer;
onMounted(() => {
  width.value = host.value.clientWidth;
  observer = observeFrameSizes((entries) => {
    width.value = entries.at(-1).contentRect.width;
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="search-header frame-search-header"
    :class="{
      'mobile-search-collapsed':
        model.compact && model.collapseSearch && !model.searchOpen
    }"
  >
    <FrameView
      :scene="scene"
      :views="views"
      @event="(action) => emit('event', action)"
    />
  </div>
</template>
<style>
.search-header.frame-search-header {
  padding: 0;
  gap: 0;
  height: 48px;
  min-height: 48px;
  position: relative;
}
.frame-search-header .search-header-slot {
  min-width: 0;
  min-height: 0;
}
.frame-search-header
  .search-header-slot
  > :is(.workspace-search, .tag-cloud, .search-quick-filter-host) {
  width: 100%;
  height: 100%;
}
.workspace-footer.frame-search-footer {
  padding: 0;
  gap: 0;
}
@media (max-width: 700px) {
  .search-header.frame-search-header.mobile-search-collapsed {
    height: 0;
    min-height: 0;
  }
}
</style>
