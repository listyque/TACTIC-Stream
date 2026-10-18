<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import AppDialog from '../../controls/AppDialog.vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/files/object_checkin.ui.mjs';

const props = defineProps({ busy: Boolean });
const emit = defineEmits(['event']);
const dialog = ref(null),
  host = ref(null),
  viewport = ref({ width: 440, height: 170 });
const scene = computed(() =>
  UI.revision(
    { busy: props.busy },
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    if (box.width > 0 && box.height > 0)
      viewport.value = { width: box.width, height: box.height };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
defineExpose({
  show: (owner) => dialog.value.show(owner),
  close: () => dialog.value.close()
});
</script>
<template>
  <AppDialog
    ref="dialog"
    class="object-revision-confirmation"
    title="Replace snapshot revision?"
    :close-on-escape="false"
    :close-on-outside="false"
  >
    <div ref="host" class="object-revision-confirmation-content">
      <FrameView :scene="scene" @event="emit('event', $event)" />
    </div>
  </AppDialog>
</template>
<style>
.object-revision-confirmation {
  width: 480px;
}
.object-revision-confirmation-content {
  position: relative;
  height: 170px;
  min-height: 140px;
}
</style>
