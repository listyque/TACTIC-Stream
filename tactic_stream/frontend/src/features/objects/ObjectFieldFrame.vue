<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/fields.ui.mjs';
import { metrics } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
const props = defineProps({
  model: Object,
  inputId: String,
  minimumEditorHeight: Number
});
const host = ref(null),
  editor = ref(null),
  width = ref(0),
  editorHeight = ref(0);
const scene = computed(() =>
  UI.field(
    {
      ...props.model,
      minimumHeight: Math.max(
        props.model.minimumHeight || 0,
        metrics(appearance.theme).controlHeight
      )
    },
    width.value,
    Math.max(props.minimumEditorHeight || 0, editorHeight.value),
    appearance.language
  )
);
let observer;
onMounted(() => {
  const measure = () => {
    width.value = host.value.clientWidth;
    editorHeight.value = editor.value.scrollHeight;
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
  observer.observe(editor.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="object-field-frame"
    :style="{
      height: scene.height + 'px',
      '--object-input-height': minimumEditorHeight
        ? minimumEditorHeight + 'px'
        : undefined
    }"
  >
    <FrameView :scene="scene" />
    <label v-if="inputId" :for="inputId" class="visually-hidden">{{
      model.title
    }}</label>
    <div
      class="object-field-editor"
      :style="{
        left: scene.editor.x + 'px',
        top: scene.editor.y + 'px',
        width: scene.editor.width + 'px',
        minHeight: scene.editor.height + 'px'
      }"
    >
      <div ref="editor" class="object-field-content"><slot /></div>
    </div>
  </div>
</template>
<style>
.object-field-frame {
  position: relative;
  min-width: 0;
  display: block;
}
.object-field-frame > .frame-view {
  position: absolute;
  inset: 0;
}
.object-field-editor {
  position: absolute;
  min-width: 0;
}
.object-field-content {
  display: grid;
  gap: 5px;
  min-width: 0;
}
.object-field-content
  > :is(
    input:not([type='checkbox']),
    select,
    textarea,
    .app-text-field,
    .app-text-area
  ) {
  width: 100%;
  min-width: 0;
  max-width: 100%;
}
.object-field-content > textarea {
  height: var(--object-input-height, auto);
  resize: vertical;
}
</style>
