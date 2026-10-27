<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppMenu from '../../controls/AppMenu.vue';
import { appearance } from '../../appearance.js';
import * as Filter from '../../../../src/tactic_stream/shared_ui/features/search/branch_filter.ui.mjs';
const props = defineProps({
  text: String,
  count: Number,
  more: Boolean,
  busy: Boolean
});
const emit = defineEmits(['filter']);
const menu = ref(null),
  query = ref(props.text || '');
let timer;
watch(
  () => props.text,
  (value) => (query.value = value || '')
);
const trigger = computed(() =>
  Filter.trigger(query.value, appearance.language)
);
const height = computed(() => (query.value ? 68 : 44));
const panel = computed(() =>
  Filter.panel(
    {
      query: query.value,
      count: props.count,
      more: props.more,
      busy: props.busy
    },
    280,
    appearance.language
  )
);
function change(value) {
  query.value = value;
  clearTimeout(timer);
  timer = setTimeout(() => emit('filter', value), 250);
}
function activate(action) {
  if (action.type === 'close') menu.value.close();
  else if (action.type === 'clear') {
    clearTimeout(timer);
    query.value = '';
    emit('filter', '');
  } else change(String(action.value));
}
function open(source) {
  const box = source.getBoundingClientRect();
  menu.value.openAt({ clientX: box.left, clientY: box.bottom, target: source });
}
onBeforeUnmount(() => clearTimeout(timer));
</script>
<template>
  <div
    class="result-branch-filter"
    @click.stop
    @dblclick.stop
    @contextmenu.stop
    @pointerdown.stop
  >
    <FrameView :scene="trigger" @event="(_, source) => open(source)" />
    <AppMenu
      ref="menu"
      external-trigger
      overlay
      :close-on-select="false"
      :width="296"
      :label="trigger.nodes[0].text"
    >
      <FrameView
        :scene="panel"
        :style="{ width: '280px', height: height + 'px' }"
        @event="activate"
      />
    </AppMenu>
  </div>
</template>
