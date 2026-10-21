<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/controls/forms/file.ui.mjs';
const props = defineProps({
  value: String,
  disabled: Boolean,
  label: String,
  required: Boolean
});
const emit = defineEmits(['change']);
const input = ref(null);
const host = ref(null),
  width = ref(0);
let observer;
const scene = computed(() =>
  UI.describe(props.value, width.value, appearance.language, !props.disabled)
);
onMounted(() => {
  const measure = () => {
    width.value = host.value.clientWidth;
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
function action(event) {
  if (props.disabled) return;
  if (event.type === 'choose') input.value.click();
  else if (event.type === 'clear') {
    input.value.value = '';
    emit('change', { target: { files: [] } });
  }
}
</script>
<template>
  <div
    ref="host"
    class="app-file-input"
    style="position: relative; height: 44px; width: 100%"
  >
    <FrameView :scene="scene" @event="action" />
    <input
      ref="input"
      type="file"
      hidden
      :aria-label="label"
      :disabled="disabled"
      :required="required"
      @change="emit('change', $event)"
    />
  </div>
</template>
