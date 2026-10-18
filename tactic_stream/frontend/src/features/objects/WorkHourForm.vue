<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/workhours/sheet.ui.mjs';
const props = defineProps({
  draft: Object,
  busy: Boolean,
  users: Array,
  error: String
});
const emit = defineEmits(['change', 'cancel', 'save']);
const host = ref(null),
  width = ref(390);
const scene = computed(() =>
  UI.editor(
    {
      ...props.draft,
      busy: props.busy,
      canManage: !!props.users?.length,
      users: props.users,
      error: props.error
    },
    width.value,
    appearance.language
  )
);
let observer;
onMounted(() => {
  observer = observeFrameSizes(() => (width.value = host.value.clientWidth));
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="work-hour-form"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView
      :scene="scene"
      @event="
        (action) =>
          action.type === 'change'
            ? emit('change', action.field, action.value)
            : action.type === 'cancel'
              ? emit('cancel')
              : emit('save', action.type === 'approve')
      "
    />
  </div>
</template>
<style>
.work-hour-form {
  position: relative;
  flex: none;
  max-width: 520px;
  width: 100%;
}
</style>
