<script setup>
import { ref, onMounted } from 'vue';
import AppButton from '../../frontend/src/controls/AppButton.vue';
import AppDialog from '../../frontend/src/controls/AppDialog.vue';
import FrameView from '../../frontend/src/frame/FrameView.vue';
import {
  node,
  rect,
  label,
  button
} from '../../src/tactic_stream/shared_ui/core/frame.mjs';
const legacy = ref(null),
  framed = ref(null),
  confirmation = ref(null);
const dirty = ref(false),
  busy = ref(false),
  guarded = ref(false);
function close(element) {
  if (dirty.value) guarded.value = true;
  else element.close();
}
const scene = () => ({
  nodes: [
    node('Box', 'pageTools', rect(0, 0, 800, 77), {
      titlebar: true,
      background: 'surfaceContainerLow',
      children: [
        label('pageTitle', rect(12, 12, 260, 24), 'Page tools'),
        button(
          'pageClose',
          rect(740, 12, 34, 34),
          'Close page',
          'close',
          { type: 'close' },
          !busy.value,
          { iconOnly: true }
        )
      ]
    })
  ]
});
onMounted(() => {
  window.chromeFixture = {
    legacy: legacy.value,
    framed: framed.value,
    confirmation: confirmation.value,
    busy: (value) => (busy.value = value),
    dirty: (value) => (dirty.value = value)
  };
});
</script>
<template>
  <dialog
    ref="legacy"
    id="legacy"
    class="record-dialog"
    v-window="{ kind: 'add_sobject', type: 'dialog' }"
    aria-label="Edit record"
    @cancel.prevent="close(legacy)"
  >
    <header>
      <div>
        <h2>Edit record</h2>
        <small>cg/assets · Robot Body</small>
      </div>
      <AppButton
        label="Close editor"
        icon="close"
        :disabled="busy"
        @click="close(legacy)"
      />
    </header>
    <input aria-label="Draft" />
    <p v-if="guarded" role="alert">Keep draft</p>
  </dialog>
  <dialog
    ref="framed"
    id="framed"
    class="configuration-dialog"
    v-window="{ kind: 'administration', type: 'window' }"
    aria-label="Administration"
    @cancel.prevent="close(framed)"
  >
    <div class="chrome-page">
      <FrameView :scene="scene()" @event="close(framed)" /><input
        aria-label="Page draft"
      />
      <p v-if="guarded" role="alert">Keep draft</p>
    </div>
  </dialog>
  <AppDialog ref="confirmation" title="Discard changes?"
    ><p>Keep this draft?</p>
    <AppButton label="Cancel" @click="confirmation.close()"
  /></AppDialog>
</template>
<style>
#legacy {
  width: 800px;
  height: 500px;
}
.chrome-page {
  height: 100%;
}
.chrome-page > .frame-view {
  height: 77px;
}
</style>
