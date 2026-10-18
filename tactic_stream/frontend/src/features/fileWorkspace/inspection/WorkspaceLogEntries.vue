<script setup>
import { ref, watch, nextTick, onMounted, onBeforeUnmount, markRaw } from 'vue';
import FrameView from '../../../frame/FrameView.vue';
import { observeFrameSizes } from '../../../frame/resize.js';
import { t } from '../../../i18n.js';
import * as UI from '../../../../../src/tactic_stream/shared_ui/features/files/workspace/log.ui.mjs';
import LogMessage from './WorkspaceLogMessage.vue';

const props = defineProps({ entries: Array });
const host = ref(null),
  width = ref(400),
  heights = ref({});
const messageComponent = markRaw(LogMessage);
const rowScene = (entry) =>
  UI.entry(entry, width.value, heights.value[entry.id] || 18);
function views(entry) {
  return {
    message: {
      component: messageComponent,
      nodeProps: true,
      props: {
        onMeasured: (value) => {
          if (heights.value[entry.id] === value) return;
          const follow =
            host.value &&
            host.value.scrollHeight -
              host.value.clientHeight -
              host.value.scrollTop <
              40;
          heights.value[entry.id] = value;
          if (follow)
            nextTick(() => {
              if (host.value) host.value.scrollTop = host.value.scrollHeight;
            });
        }
      }
    }
  };
}
watch(
  () => props.entries.map((entry) => entry.id),
  async (ids) => {
    const retained = new Set(ids);
    heights.value = Object.fromEntries(
      Object.entries(heights.value).filter(
        ([id]) => retained.has(Number(id)) || retained.has(id)
      )
    );
    await nextTick();
    if (host.value) host.value.scrollTop = host.value.scrollHeight;
  }
);
let observer;
onMounted(() => {
  observer = observeFrameSizes(
    (entries) =>
      (width.value = Math.max(0, entries.at(-1).contentRect.width - 16))
  );
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="workspace-log-entries"
    role="log"
    aria-live="polite"
    :aria-label="t('Operation log')"
  >
    <div
      v-for="entry in entries"
      :key="entry.id"
      class="workspace-log-row"
      :style="{ height: (heights[entry.id] || 18) + 'px' }"
    >
      <FrameView :scene="rowScene(entry)" :views="views(entry)" />
    </div>
  </div>
</template>
<style scoped>
.workspace-log-entries {
  overflow: auto;
  scrollbar-gutter: stable;
}
.workspace-log-row {
  position: relative;
}
</style>
