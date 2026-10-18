<script setup>
import { ref, computed, h, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/messages/message.ui.mjs';
const props = defineProps({
  reference: Object,
  users: Array,
  forwarded: Boolean,
  dismissible: Boolean
});
const emit = defineEmits(['activate', 'dismiss']);
const root = ref(null),
  width = ref(300),
  height = ref(19);
let observer;
const model = computed(() => ({
  sender:
    props.users?.find((user) => user.login === props.reference.sender)
      ?.displayName || props.reference.sender,
  body: props.reference.body,
  available: props.reference.available !== false,
  forwarded: props.forwarded,
  dismissible: props.dismissible,
  attachments: props.reference.attachments?.length || 0
}));
const scene = computed(() =>
  UI.reference(model.value, width.value, appearance.language, height.value)
);
const port = {
  setup(_, { attrs }) {
    const text = ref(null);
    let resize;
    onMounted(() => {
      resize = observeFrameSizes(() => {
        const value = text.value.getBoundingClientRect().height;
        if (value > 0) height.value = value;
      });
      resize.observe(text.value);
    });
    onBeforeUnmount(() => resize?.disconnect());
    return () =>
      h('div', attrs, [
        h(
          'div',
          {
            ref: text,
            style: {
              display: '-webkit-box',
              WebkitBoxOrient: 'vertical',
              WebkitLineClamp: props.forwarded ? 3 : 2,
              overflow: 'hidden',
              overflowWrap: 'anywhere',
              fontSize: '14px',
              fontWeight: 400,
              lineHeight: '19px'
            }
          },
          props.reference.body
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
  <div
    ref="root"
    class="message-reference"
    :class="{ forwarded, unavailable: reference.available === false }"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView
      :scene="scene"
      :views="{ body: { component: port } }"
      @event="(event) => emit(event.type === 'open' ? 'activate' : 'dismiss')"
    />
  </div>
</template>
<style>
.message-reference {
  display: block !important;
  position: relative;
  min-width: 0;
  padding: 0 !important;
  border: 0 !important;
  background: transparent !important;
}
.message-reference > .frame-view {
  height: 100%;
}
.message-reference::before {
  display: none !important;
}
</style>
