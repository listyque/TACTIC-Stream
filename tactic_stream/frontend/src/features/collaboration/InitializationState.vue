<script setup>
import {
  computed,
  nextTick,
  onMounted,
  onBeforeUnmount,
  ref,
  watch
} from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppDialog from '../../controls/AppDialog.vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/support/collaboration/initialization.ui.mjs';
const props = defineProps({
  title: String,
  message: String,
  icon: String,
  project: String,
  canInitialize: Boolean,
  busy: Boolean,
  error: String,
  canRefresh: Boolean
});
const emit = defineEmits(['initialize', 'refresh']);
const host = ref(null),
  dialog = ref(null),
  body = ref(null),
  confirmationFrame = ref(null),
  epoch = ref(0),
  width = ref(600),
  height = ref(500),
  bodyWidth = ref(580),
  bodyHeight = ref(400);
const model = computed(() => ({ ...props, epoch: epoch.value }));
const scene = computed(() =>
  UI.state(model.value, width.value, height.value, appearance.language)
);
const confirmation = computed(() =>
  UI.confirmation(
    model.value,
    bodyWidth.value,
    bodyHeight.value,
    appearance.language
  )
);
const size = computed(() => UI.dialogSize(width.value, height.value));
let observer;
onMounted(() => {
  observer = observeFrameSizes(() => {
    width.value = host.value.clientWidth;
    height.value = host.value.clientHeight;
    bodyWidth.value = frameContentWidth(body.value);
    bodyHeight.value = body.value.clientHeight;
  });
  observer.observe(host.value);
  observer.observe(body.value);
});
onBeforeUnmount(() => observer?.disconnect());
watch(
  () => props.project,
  () => dialog.value?.close()
);
async function action(event) {
  if (event.type === 'open') {
    epoch.value++;
    dialog.value.show(host.value);
    await nextTick();
    bodyWidth.value = frameContentWidth(body.value);
    bodyHeight.value = body.value.clientHeight;
    confirmationFrame.value.focusControl('collaborationInitializationCancel');
  } else emit('refresh');
}
function confirmed(event) {
  dialog.value.close();
  if (event.type === 'initialize') emit('initialize');
}
</script>
<template>
  <div ref="host" class="collaboration-initialization-state">
    <FrameView :scene="scene" @event="action" />
    <AppDialog
      ref="dialog"
      title="Initialize server features?"
      :owner-margin="0"
      :style="{ width: size.width + 'px', height: size.height + 'px' }"
      ><div ref="body" class="collaboration-initialization-body">
        <FrameView
          ref="confirmationFrame"
          :scene="confirmation"
          @event="confirmed"
        /></div
    ></AppDialog>
  </div>
</template>
<style>
.collaboration-initialization-state,
.collaboration-initialization-body {
  position: relative;
  min-width: 0;
  min-height: 0;
  flex: 1;
  height: 100%;
}
</style>
