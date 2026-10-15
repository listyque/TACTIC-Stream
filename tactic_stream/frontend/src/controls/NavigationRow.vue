<script setup>
import { computed, ref } from 'vue';
import AppButton from './AppButton.vue';
import FrameView from '../frame/FrameView.vue';
import { appearance } from '../appearance.js';
import { metrics } from '../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import { navigationRow } from '../../../src/tactic_stream/shared_ui/controls/lists/tree.ui.mjs';
import { observeFrameSizes } from '../frame/resize.js';
import { onMounted, onBeforeUnmount } from 'vue';
defineOptions({ inheritAttrs: false });
const props = defineProps({
  record: { type: Object, required: true },
  selected: Boolean,
  disabled: Boolean
});
const emit = defineEmits(['activated']);
const root = ref(null),
  width = ref(280),
  hovered = ref(false),
  pressed = ref(false);
const scene = computed(() =>
  navigationRow(width.value, props.record, {
    selected: props.selected,
    hovered: hovered.value,
    pressed: pressed.value,
    radius: metrics(appearance.theme).itemRadius
  })
);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    width.value = entries.at(-1).contentRect.width;
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="root"
    class="navigation-row"
    :style="{ height: scene.height + 'px', opacity: disabled ? 0.5 : 1 }"
  >
    <FrameView :scene="scene" :interactive="false" />
    <AppButton
      v-if="record.kind !== 'separator'"
      v-bind="$attrs"
      class="navigation-row-hit"
      :label="record.title"
      :translate-label="false"
      :disabled="disabled"
      :aria-pressed="selected"
      :aria-expanded="record.kind === 'section' ? record.expanded : undefined"
      @pointerenter="hovered = true"
      @pointerleave="
        hovered = false;
        pressed = false;
      "
      @pointerdown="pressed = true"
      @pointerup="pressed = false"
      @pointercancel="pressed = false"
      @blur="pressed = false"
      @click="emit('activated')"
      ><span class="sr-only">{{ record.title }}</span></AppButton
    >
  </div>
</template>
<style>
.navigation-row {
  position: relative;
  width: 100%;
  flex: none;
}
.navigation-row > .frame-view {
  pointer-events: none;
}
.navigation-row .navigation-row-hit.app-button {
  position: absolute;
  inset: 4px 12px;
  width: calc(100% - 24px);
  height: calc(100% - 8px);
  min-width: 0;
  min-height: 0;
  margin: 0;
  padding: 0;
  background: transparent;
  border: 0;
  box-shadow: none;
}
.navigation-row .navigation-row-hit.app-button:disabled {
  opacity: 1;
}
</style>
