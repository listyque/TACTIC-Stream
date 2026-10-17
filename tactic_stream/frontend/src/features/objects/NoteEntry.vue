<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { mobile } from '../../mobile.js';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/note.ui.mjs';
const props = defineProps({ model: Object });
const emit = defineEmits(['event']);
const host = ref(null),
  body = ref(null),
  width = ref(0),
  bodyHeight = ref(0),
  hovered = ref(false);
let observer;
const geometry = computed(() => UI.geometry(props.model, width.value));
const height = computed(() =>
  Math.max(52, 20 + 28 + (bodyHeight.value ? 6 + bodyHeight.value : 0))
);
const header = computed(() =>
  UI.header(
    { ...props.model, actionsVisible: hovered.value || mobile.value },
    geometry.value.contentWidth,
    appearance.language
  )
);
onMounted(() => {
  const measure = () => {
    width.value = host.value.parentElement.clientWidth;
    bodyHeight.value = body.value.getBoundingClientRect().height;
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value.parentElement);
  observer.observe(body.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <article
    ref="host"
    class="note-entry shared-note-entry"
    :style="{
      width: geometry.width + 'px',
      height: height + 'px',
      marginLeft: geometry.x + 'px'
    }"
    @pointerenter="hovered = true"
    @pointerleave="hovered = false"
  >
    <FrameView :scene="UI.card(model, geometry.width, height)" />
    <div
      class="shared-note-header"
      :style="{
        left: geometry.contentX + 'px',
        width: geometry.contentWidth + 'px'
      }"
    >
      <FrameView
        :scene="header"
        @event="(action, source) => emit('event', action, source)"
      />
    </div>
    <div
      ref="body"
      class="shared-note-content"
      :style="{
        left: geometry.contentX + 'px',
        width: geometry.contentWidth + 'px'
      }"
    >
      <slot />
    </div>
    <slot name="menu" />
  </article>
</template>
<style>
.notes-panel .shared-note-entry {
  position: relative;
  flex: none;
  margin-top: 0;
  margin-bottom: 10px;
  margin-right: 0;
  padding: 0;
  border: 0;
  background: transparent;
  border-radius: 14px;
  min-width: 0;
  box-sizing: border-box;
}
.shared-note-header {
  position: absolute;
  top: 10px;
  height: 28px;
}
.shared-note-content {
  position: absolute;
  top: 44px;
  display: grid;
  gap: 6px;
  min-width: 0;
}
.shared-note-content .note-body {
  margin: 0;
  overflow-wrap: anywhere;
}
.shared-note-entry:first-of-type {
  margin-top: auto;
}
.shared-note-entry:focus {
  outline: none;
}
.shared-note-entry .note-file-card {
  min-width: 0;
}
.shared-note-entry .note-file-card > .attachment-card {
  width: 100%;
}
</style>
