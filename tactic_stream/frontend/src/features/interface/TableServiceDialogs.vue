<script setup>
import { computed, ref, nextTick, onMounted, onBeforeUnmount } from 'vue';
import AppDialog from '../../controls/AppDialog.vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as Confirmation from '../../../../src/tactic_stream/shared_ui/controls/feedback/confirmation.ui.mjs';
const dialog = ref(null),
  host = ref(null),
  model = ref({ message: '' });
const geometry = ref({ width: 420, height: 220 }),
  size = ref({ width: 380, height: 180 });
let resolve, observer;
const scene = computed(() =>
  Confirmation.describe(
    model.value,
    size.value.width,
    size.value.height,
    appearance.language
  )
);
function finish(accepted = false) {
  const pending = resolve;
  resolve = null;
  dialog.value?.close();
  pending?.(accepted);
}
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    size.value = {
      width: entries[0].contentRect.width,
      height: entries[0].contentRect.height
    };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => {
  finish();
  observer?.disconnect();
});
defineExpose({
  ask(message, options = {}) {
    if (resolve) throw new Error('Finish the current confirmation first');
    geometry.value = {
      width: options.width || 420,
      height: options.height || 220
    };
    model.value = {
      message,
      accept: options.accept || 'Continue',
      destructive: !!options.destructive
    };
    return new Promise((done) => {
      resolve = done;
      nextTick(() => {
        if (resolve === done) dialog.value.show();
      });
    });
  },
  close: () => finish()
});
</script>
<template>
  <AppDialog
    ref="dialog"
    class="table-service-confirmation"
    :style="{ width: geometry.width + 'px', height: geometry.height + 'px' }"
    @rejected="finish()"
    @closed="finish()"
  >
    <div ref="host" class="table-service-confirmation-body">
      <FrameView
        :scene="scene"
        @event="(action) => finish(action.type === 'accept')"
      />
    </div>
  </AppDialog>
</template>
<style scoped>
.table-service-confirmation-body {
  position: relative;
  flex: 1;
  min-height: 0;
}
</style>
