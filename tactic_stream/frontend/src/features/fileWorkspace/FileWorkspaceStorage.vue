<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import { t } from '../../i18n.js';
import { appearance } from '../../appearance.js';
import FrameView from '../../frame/FrameView.vue';
import AppDialog from '../../controls/AppDialog.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/files/workspace/storage.ui.mjs';

const props = defineProps({
  status: Object,
  draft: Object,
  busy: Boolean,
  indexing: Boolean,
  filesService: Boolean
});
const emit = defineEmits(['change', 'save', 'reset', 'action', 'stop']);
const host = ref(null),
  dialog = ref(null),
  confirmHost = ref(null),
  viewport = ref({ width: 660, height: 500 }),
  confirmSize = ref({ width: 420, height: 200 });
const scene = computed(() =>
  UI.describe(
    props,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const canGc = computed(
  () =>
    !props.busy &&
    !!props.status?.indexed &&
    props.filesService &&
    !['queued', 'running'].includes(props.status?.gc?.state)
);
const confirmation = computed(() =>
  UI.confirm(
    { busy: !canGc.value },
    confirmSize.value.width,
    confirmSize.value.height,
    appearance.language
  )
);
function event(action) {
  if (action.type === 'field')
    emit('change', {
      ...props.draft,
      policy: { ...props.draft.policy, [action.key]: action.value }
    });
  else if (action.type === 'action')
    emit('action', action.operation, action.dry);
  else if (['reset', 'save', 'stop'].includes(action.type)) emit(action.type);
  else if (action.type === 'confirmGc' && canGc.value)
    dialog.value.show(host.value);
}
function confirm(action) {
  if (action.type === 'reject') dialog.value.close();
  else if (action.type === 'accept' && canGc.value) {
    dialog.value.close();
    emit('action', 'gc_begin', false);
  }
}
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    for (const entry of entries) {
      const bounds = entry.contentRect;
      if (bounds.width > 0 && bounds.height > 0) {
        const value = { width: bounds.width, height: bounds.height };
        if (entry.target === host.value) viewport.value = value;
        else confirmSize.value = value;
      }
    }
  });
  observer.observe(host.value);
  observer.observe(confirmHost.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <section
    ref="host"
    class="storage-administration"
    :aria-label="t('Storage administration')"
  >
    <FrameView :scene="scene" @event="event" />
  </section>
  <AppDialog ref="dialog" title="Run safe GC" class="workspace-gc-confirmation"
    ><div ref="confirmHost" class="workspace-gc-body">
      <FrameView :scene="confirmation" @event="confirm" /></div
  ></AppDialog>
</template>
<style>
.storage-administration {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
}
.workspace-gc-confirmation {
  width: min(480px, var(--dialog-owner-width));
}
.workspace-gc-body {
  position: relative;
  height: 200px;
}
@media (max-width: 460px) {
  .workspace-gc-body {
    height: 250px;
  }
}
</style>
