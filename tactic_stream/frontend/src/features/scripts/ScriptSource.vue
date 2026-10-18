<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import CodeEditor from '../../controls/CodeEditor.vue';
import FrameView from '../../frame/FrameView.vue';
import { frameContentWidth, observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/scripts/source.ui.mjs';

defineOptions({ inheritAttrs: false });
const props = defineProps({
  saved: Boolean,
  readOnly: Boolean,
  disabled: Boolean
});
const emit = defineEmits(['run', 'outline', 'help', 'saved']);
const model = defineModel({ default: '' }),
  fontSize = defineModel('fontSize', { default: 9.25 });
const source = ref(null),
  host = ref(null),
  width = ref(0),
  revision = ref(0);
const state = computed(() => ({
  ...source.value?.frameState,
  historyCount: source.value?.frameState?.historyCount || 1,
  historyIndex: source.value?.frameState?.historyIndex || 0,
  fontSize: fontSize.value,
  readOnly: props.readOnly || props.disabled,
  saved: props.saved,
  busy: props.disabled
}));
const scene = computed(() =>
  UI.describe(state.value, width.value, appearance.language, revision.value)
);
async function event(action) {
  revision.value++;
  if (action.type === 'font') fontSize.value = Number(action.value);
  else if (action.type === 'history')
    await source.value?.historyTo(Number(action.value));
  else if (action.type === 'selection') emit('run', source.value?.selectedText);
  else if (['outline', 'saved'].includes(action.type)) emit(action.type);
  else if (action.type === 'command') {
    if (['cut', 'copy', 'paste'].includes(action.value))
      await source.value?.clipboard(action.value);
    else if (['undo', 'redo'].includes(action.value))
      await source.value?.[action.value]();
    else if (['find', 'replace'].includes(action.value))
      source.value?.showFind(action.value === 'replace');
    else if (action.value === 'help') emit('help');
  }
}
let observer;
onMounted(() => {
  const measure = () => (width.value = frameContentWidth(host.value));
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
defineExpose({
  focus: () => source.value?.focus(),
  goToLine: (line) => source.value?.goToLine(line)
});
</script>
<template>
  <div ref="host" class="script-source">
    <div
      class="script-source-toolbar"
      :style="{ height: UI.toolbarHeight(width) + 'px' }"
    >
      <FrameView
        :scene="scene"
        :style="{ width: scene.contentWidth + 'px', height: '30px' }"
        @event="event"
      />
    </div>
    <CodeEditor
      ref="source"
      v-bind="$attrs"
      v-model="model"
      v-model:font-size="fontSize"
      :source-toolbar="false"
      :read-only="readOnly"
      :disabled="disabled"
      @run="emit('run', $event)"
      @outline="emit('outline')"
      @help="emit('help')"
    />
  </div>
</template>
<style>
.script-source {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px;
  background: var(--surface);
  border: 0;
  box-shadow: inset 0 0 0 1px var(--outline-variant);
  border-radius: 12px;
}
.script-source-toolbar {
  flex-shrink: 0;
  height: 30px;
  overflow: auto;
}
.script-source > .code-editor {
  flex: 1;
  min-height: 0;
  padding: 0;
  border: 0;
}
</style>
