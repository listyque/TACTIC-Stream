<script setup>
import {
  ref,
  computed,
  watch,
  nextTick,
  onMounted,
  onBeforeUnmount
} from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/note.ui.mjs';
const props = defineProps({
  active: { type: Boolean, default: true },
  editing: Object,
  deleting: Object,
  busy: Boolean,
  uncertain: Boolean,
  error: String
});
const emit = defineEmits(['text', 'cancel', 'save', 'delete']);
const dialog = ref(null),
  host = ref(null),
  width = ref(0);
let observer;
const scene = computed(() =>
  UI[props.editing ? 'edit' : 'remove'](
    {
      text: props.editing?.body,
      busy: props.busy,
      uncertain: props.uncertain,
      error: props.error
    },
    width.value,
    appearance.language
  )
);
watch(
  () => [!!props.editing, !!props.deleting, props.active],
  async () => {
    dialog.value?.close();
    if (!props.active || (!props.editing && !props.deleting)) return;
    await nextTick();
    if (props.deleting) dialog.value.showModal();
    else dialog.value.show();
    await nextTick();
    dialog.value.querySelector('textarea')?.focus();
  },
  { immediate: true }
);
function action(event) {
  if (event.type === 'text') emit('text', event.value);
  else emit(event.type);
}
onMounted(() => {
  observer = observeFrameSizes(() => {
    width.value = host.value.clientWidth;
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <Teleport to="body"
    ><dialog
      ref="dialog"
      v-window="editing ? { type: 'popup' } : false"
      class="record-dialog note-child-dialog"
      :class="{ editing }"
      :aria-label="t(editing ? 'Edit note' : 'Delete note?')"
      :aria-busy="busy"
      @cancel.prevent="!busy && emit('cancel')"
    >
      <header>
        <h2>{{ t(editing ? 'Edit note' : 'Delete note?') }}</h2>
      </header>
      <div
        ref="host"
        class="note-child-content"
        :style="{ height: scene.height + 'px' }"
      >
        <FrameView :scene="scene" @event="action" />
      </div></dialog
  ></Teleport>
</template>
<style>
.note-child-dialog {
  --dialog-content-top: 0px;
  --dialog-content-side: 20px;
  width: min(380px, calc(100vw - 32px));
  padding: 0 20px 20px;
  overflow: hidden;
}
dialog.note-child-dialog[open] {
  display: block;
}
.note-child-dialog.editing {
  width: min(520px, calc(100vw - 32px));
}
.note-child-dialog > header {
  height: 62px;
  margin: 0 -20px 20px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  background: var(--surface-highest);
  border-bottom: 1px solid var(--outline-variant);
}
.note-child-dialog > header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
.note-child-content {
  position: relative;
  width: 100%;
  min-width: 0;
}
</style>
