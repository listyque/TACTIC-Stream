<script setup>
import { computed, ref, h, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/messages/panels.ui.mjs';
const props = defineProps({ record: Object, mode: String, busy: Boolean });
const emit = defineEmits(['open']);
const root = ref(null),
  width = ref(340),
  bodyHeight = ref(18);
let observer;
const scene = computed(() =>
  UI.revision(
    { ...props.record, mode: props.mode, busy: props.busy },
    width.value,
    bodyHeight.value,
    appearance.language
  )
);
const port = {
  setup(_, { attrs }) {
    const text = ref(null);
    let resize;
    onMounted(() => {
      resize = observeFrameSizes(() => {
        const height = text.value.getBoundingClientRect().height;
        if (height > 0) bodyHeight.value = height;
      });
      resize.observe(text.value);
    });
    onBeforeUnmount(() => resize?.disconnect());
    return () =>
      h('div', attrs, [
        h(
          'p',
          {
            ref: text,
            style: {
              margin: 0,
              whiteSpace: 'pre-wrap',
              overflowWrap: 'anywhere',
              fontSize: '13px',
              lineHeight: '18px'
            }
          },
          props.mode === 'pin-history'
            ? props.record.summary || props.record.body || t('Pinned message')
            : props.record.body
        )
      ]);
  }
};
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    if (entries[0].contentRect.width > 0)
      width.value = entries[0].contentRect.width;
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <article
    ref="root"
    class="message-revision"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView
      :scene="scene"
      :views="{ body: { component: port } }"
      @event="emit('open', record)"
    />
  </article>
</template>
<style>
.message-revision.message-revision {
  position: relative;
  flex: none;
  display: block;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
}
.message-revision > .frame-view {
  height: 100%;
}
</style>
