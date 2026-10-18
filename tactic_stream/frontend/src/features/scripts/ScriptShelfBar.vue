<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/scripts/bar.ui.mjs';
const props = defineProps({
  mode: String,
  buttons: Array,
  busy: Boolean,
  running: String,
  error: String
});
const emit = defineEmits(['mode', 'edit', 'run']);
const host = ref(null),
  width = ref(0);
const bounds = computed(() => UI.layout(width.value, 48, false));
const scene = computed(() =>
  UI.describe(
    {
      mode: props.mode,
      count: props.buttons.length,
      busy: props.busy,
      running: !!props.running,
      error: props.error
    },
    width.value,
    48,
    appearance.language
  )
);
const actionHeight = computed(() =>
  UI.actionHeight(props.buttons.length, bounds.value.buttons.width)
);
const style = (rect) => ({
  position: 'absolute',
  left: rect.x + 'px',
  top: rect.y + 'px',
  width: rect.width + 'px',
  height: rect.height + 'px'
});
let observer;
onMounted(() => {
  const measure = () => (width.value = frameContentWidth(host.value));
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
function event(action) {
  if (action.type === 'mode') emit('mode', action.value);
  else if (action.type === 'edit') emit('edit');
  else if (action.type === 'run') emit('run', action.buttonId);
}
</script>
<template>
  <div
    ref="host"
    class="script-shelf-bar"
    :aria-label="t('Script shelf')"
    :aria-busy="busy || !!running"
    :title="error || undefined"
  >
    <FrameView :scene="scene" @event="event" />
    <div
      class="script-shelf-buttons"
      :style="style(bounds.buttons)"
      @wheel="
        (event) => {
          if (
            event.deltaY &&
            event.currentTarget.scrollWidth > event.currentTarget.clientWidth
          ) {
            event.preventDefault();
            event.currentTarget.scrollLeft += event.deltaY;
          }
        }
      "
    >
      <FrameView
        v-for="record in buttons"
        :key="record.buttonId"
        class="script-shelf-action"
        :style="{ height: actionHeight + 'px' }"
        :scene="UI.action(record, !!running, appearance.language, actionHeight)"
        @event="event"
      />
    </div>
  </div>
</template>
<style>
.script-shelf-bar {
  position: relative;
  height: 48px;
  min-height: 48px;
  display: block;
  padding: 0;
  background: var(--surface-high);
}
.script-shelf-buttons {
  display: flex;
  align-items: center;
  gap: 4px;
  overflow-x: auto;
  overflow-y: hidden;
}
.script-shelf-action {
  flex: 0 0 40px;
  width: 40px;
  height: 40px;
}
</style>
