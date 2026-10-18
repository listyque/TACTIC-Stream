<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/schedule.ui.mjs';
const props = defineProps({
  model: Object,
  workingDays: Boolean,
  multi: Boolean,
  busy: Boolean,
  error: String
});
const emit = defineEmits(['change', 'working', 'cancel', 'apply']);
const root = ref(null),
  width = ref(360);
let observer;
const scene = computed(() =>
  UI.describe(
    {
      ...props.model,
      workingDays: props.workingDays,
      multi: props.multi,
      busy: props.busy,
      error: props.error
    },
    width.value,
    appearance.language
  )
);
function action(event) {
  if (event.type === 'change') emit('change', event.field, event.value);
  else emit(event.type, event.value);
}
onMounted(() => {
  observer = observeFrameSizes(
    (entries) => (width.value = entries[0].contentRect.width)
  );
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="root"
    class="task-schedule-editor"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView :scene="scene" @event="action" />
  </div>
</template>
