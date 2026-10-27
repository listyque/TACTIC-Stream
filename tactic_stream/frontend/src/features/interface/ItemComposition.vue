<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { layoutUrl } from './itemLayout.js';
import * as Composition from '../../../../src/tactic_stream/shared_ui/features/administration/layouts/layout.preview.mjs';
const props = defineProps({
  layout: Object,
  node: Object,
  editing: Boolean,
  readOnly: Boolean,
  selectedElement: String
});
const emit = defineEmits(['action', 'element']);
const host = ref(null),
  width = ref(1);
let observer;
const scene = computed(() =>
  Composition.describe(
    props.layout,
    props.node,
    width.value,
    props.selectedElement,
    appearance.language,
    window.innerWidth,
    location.origin,
    'itemComposition',
    0,
    props.editing || props.readOnly
  )
);
function dispatch(event, source) {
  if (event.type === 'select') {
    if (props.editing) emit('element', event.name);
    return;
  }
  if (props.editing || props.readOnly || event.type !== 'itemAction') return;
  if (event.href) {
    const href = layoutUrl(event.href);
    if (href)
      window.open(href, href.startsWith('/') ? '_self' : '_blank', 'noopener');
    return;
  }
  if (event.urlOnly || !Composition.actionAvailable(event.action, props.node))
    return;
  const bounds = source?.getBoundingClientRect();
  emit(
    'action',
    event.action,
    props.node,
    event.command || {
      currentTarget: source,
      target: source,
      clientX: bounds?.left,
      clientY: bounds?.bottom
    }
  );
}
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    width.value = Math.max(1, entries[0].contentRect.width);
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="item-composition"
    :style="{ height: scene.height + 'px' }"
    @click="
      (event) => {
        if (editing || event.target.closest('button,a,[role=button]'))
          event.stopPropagation();
      }
    "
  >
    <FrameView :scene="scene" @event="dispatch" />
  </div>
</template>
<style>
.item-composition {
  isolation: isolate;
  position: relative;
  width: 100%;
  min-width: 0;
}
.item-composition .frame-label {
  overflow: clip;
}
.item-composition .frame-label > span {
  display: block;
  max-width: 100%;
  max-height: 100%;
  overflow: clip;
  text-overflow: ellipsis;
}
</style>
