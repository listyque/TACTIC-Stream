<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import AppMenu from '../../controls/AppMenu.vue';
import ActionRows from '../../controls/ActionRows.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/search/presets.ui.mjs';

const props = defineProps({ model: Object });
const emit = defineEmits(['event']);
const host = ref(null),
  menu = ref(null),
  anchor = ref(null),
  width = ref(700);
const scene = computed(() =>
  UI.describe(props.model, width.value, appearance.language)
);
const actions = computed(() => UI.actions(props.model));
let observer;
onMounted(() => {
  width.value = host.value.clientWidth;
  observer = observeFrameSizes((entries) => {
    width.value = entries.at(-1).contentRect.width;
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
function dispatch(action, source) {
  if (action.type === 'pressMore') return;
  if (action.type !== 'more') {
    emit('event', action);
    return;
  }
  if (menu.value.open) {
    menu.value.close(true);
    return;
  }
  anchor.value = source;
  const bounds = source.getBoundingClientRect();
  menu.value.openAt({
    clientX: bounds.left,
    clientY: bounds.bottom,
    target: source
  });
}
</script>
<template>
  <div
    ref="host"
    class="search-preset-bar"
    :style="{
      position: 'relative',
      height: UI.barHeight + 'px',
      flex: 'none',
      overflow: 'hidden'
    }"
  >
    <FrameView :scene="scene" @event="dispatch" />
    <AppMenu
      ref="menu"
      external-trigger
      frame-composition
      overlay
      label="Saved search actions"
      :anchor="anchor"
      :width="300"
    >
      <ActionRows
        :actions="actions"
        @triggered="(type) => emit('event', { type })"
      />
    </AppMenu>
  </div>
</template>
