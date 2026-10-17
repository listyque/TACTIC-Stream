<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import FrameView from '../../frame/FrameView.vue';
import AppMenu from '../../controls/AppMenu.vue';
import ActionRows from '../../controls/ActionRows.vue';
import { qtLabelTextWidth } from '../../controls/typography/textMetrics.js';
import { fontFamily } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/search/footer.ui.mjs';
const props = defineProps({ model: Object, boundary: Object });
const emit = defineEmits(['event']);
const host = ref(null),
  frame = ref(null),
  popup = ref(null),
  anchor = ref(null),
  width = ref(0),
  height = ref(58),
  kind = ref(''),
  draft = ref('');
const scene = computed(() =>
  UI.describe(
    {
      ...props.model,
      countWidth: qtLabelTextWidth(
        UI.countText(props.model, width.value, appearance.language),
        '400 14px "' + fontFamily + '"'
      )
    },
    width.value,
    height.value,
    appearance.language
  )
);
const pickerScene = computed(() =>
  UI.pagePicker(draft.value, 200, appearance.language)
);
const actions = computed(() => UI.menu(kind.value, props.model));
let observer;
onMounted(() => {
  width.value = host.value.clientWidth;
  height.value = host.value.clientHeight;
  observer = observeFrameSizes((entries) => {
    const size = entries.at(-1).contentRect;
    width.value = size.width;
    height.value = size.height;
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
function dispatch(action, source) {
  if (action.type === 'press') return;
  if (['mode', 'size', 'pagePicker'].includes(action.type)) {
    const same = kind.value === action.type && anchor.value === source;
    kind.value = action.type;
    draft.value = String(props.model.page);
    anchor.value = source;
    if (same && popup.value.open) {
      popup.value.close(true);
      return;
    }
    const bounds = source.getBoundingClientRect();
    popup.value.openAt({
      clientX: bounds.left,
      clientY: bounds.top,
      target: source
    });
  } else emit('event', action);
}
function choose(value) {
  emit('event', {
    type: kind.value,
    value: kind.value === 'size' ? Number(value) : value
  });
  popup.value.close(true);
}
function pageEvent(action) {
  if (action.type === 'pageDraft') draft.value = action.value;
  else if (
    action.type === 'go' &&
    /^\d+$/.test(draft.value) &&
    Number(draft.value) > 0 &&
    (props.model.pageCount == null ||
      Number(draft.value) <= props.model.pageCount)
  ) {
    emit('event', { type: 'page', value: Number(draft.value) });
    popup.value.close(true);
  }
}
</script>
<template>
  <div
    ref="host"
    class="search-footer-frame"
    style="
      position: relative;
      width: 100%;
      height: 100%;
      min-width: 0;
      overflow: hidden;
    "
  >
    <FrameView ref="frame" v-if="width" :scene="scene" @event="dispatch" />
    <AppMenu
      ref="popup"
      external-trigger
      frame-composition
      overlay
      :boundary="boundary"
      :anchor="anchor"
      :close-on-select="false"
      :label="
        kind === 'pagePicker'
          ? 'Go to page'
          : kind === 'size'
            ? 'Items per page'
            : 'Result loading'
      "
      :width="224"
    >
      <FrameView
        v-if="kind === 'pagePicker'"
        :scene="pickerScene"
        style="height: 80px"
        @event="pageEvent"
      />
      <ActionRows v-else :actions="actions" @triggered="choose" />
    </AppMenu>
  </div>
</template>
