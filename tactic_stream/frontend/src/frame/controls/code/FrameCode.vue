<script setup>
import { computed, ref } from 'vue';
import FrameView from '../../FrameView.vue';
import CodeEditor from '../../../controls/CodeEditor.vue';
import * as UI from '../../../../../src/tactic_stream/shared_ui/controls/code/code.ui.mjs';
const props = defineProps({ node: { type: Object, required: true } }),
  emit = defineEmits(['event']),
  source = ref(null),
  font = ref(9.25),
  revision = ref(0);
const model = computed(() => ({
  canUndo: false,
  canRedo: false,
  canCopy: false,
  ...source.value?.frameState,
  historyCount: source.value?.frameState?.historyCount || 1,
  historyIndex: source.value?.frameState?.historyIndex || 0,
  fontSize: font.value,
  readOnly: props.node.readOnly || !props.node.enabled
}));
const toolbar = computed(() =>
  UI.toolbar(
    model.value,
    props.node.width,
    props.node.language || 'en',
    revision.value
  )
);
async function dispatch(event) {
  revision.value++;
  if (event.type === 'font') {
    font.value = Number(event.value);
    return;
  }
  if (event.type === 'history') {
    await source.value?.historyTo(Number(event.value));
    return;
  }
  const action = event.value;
  if (
    (action === 'copy' && model.value.canCopy) ||
    (['cut', 'paste'].includes(action) && !model.value.readOnly)
  )
    await source.value?.clipboard(action);
  else if (action === 'undo' && model.value.canUndo && !model.value.readOnly)
    await source.value?.undo();
  else if (action === 'redo' && model.value.canRedo && !model.value.readOnly)
    await source.value?.redo();
  else if (action === 'find' || (action === 'replace' && !model.value.readOnly))
    source.value?.showFind(action === 'replace');
  else if (action === 'help')
    emit('event', props.node.helpAction || { type: 'help' });
}
</script>
<template>
  <div class="frame-code" :data-frame="node.id">
    <FrameView
      class="frame-code-toolbar"
      :scene="toolbar"
      @event="dispatch"
    /><CodeEditor
      ref="source"
      class="frame-code-source"
      :source-toolbar="false"
      :model-value="node.text"
      :language="node.syntax || 'xml'"
      :buffer-key="node.bufferKey"
      :read-only="model.readOnly"
      :disabled="!node.enabled"
      :font-size="font"
      @update:model-value="emit('event', { ...node.action, value: $event })"
      @help="emit('event', node.helpAction || { type: 'help' })"
    />
  </div>
</template>
<style scoped>
.frame-code {
  position: relative;
  overflow: hidden;
  min-width: 0;
  min-height: 0;
}
.frame-code-toolbar {
  position: absolute;
  inset: 0 0 auto;
  height: 30px;
}
.frame-code-source {
  position: absolute;
  left: 0;
  top: 36px;
  width: 100%;
  height: calc(100% - 36px);
  border: 0;
  border-radius: 0;
  padding: 0;
}
.frame-code-source :deep(.code-buffer) {
  border-radius: 0;
}
.frame-code-source :deep(.code-line-numbers) {
  width: 36px;
  border: 0;
}
</style>
