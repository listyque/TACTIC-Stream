<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import AppButton from './AppButton.vue';
import FrameView from '../frame/FrameView.vue';
import { appearance } from '../appearance.js';
import { t } from '../i18n.js';
import {
  fontFamily,
  metrics
} from '../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import { row } from '../../../src/tactic_stream/shared_ui/controls/menus/action.ui.mjs';
import { observeFrameSizes } from '../frame/resize.js';
const props = defineProps({
  record: { type: Object, required: true },
  suppressFocus: Boolean
});
defineEmits(['triggered']);
const root = ref(null),
  width = ref(230),
  hovered = ref(false),
  pressed = ref(false),
  focused = ref(false),
  badgeTextWidth = ref(0);
const title = computed(() =>
  props.record.translate === false
    ? props.record.title
    : t(props.record.title || '', props.record.titleArgs)
);
const scene = computed(() =>
  row(
    {
      ...props.record,
      title: title.value,
      status:
        props.record.statusTranslate === false
          ? props.record.status
          : t(props.record.status || '')
    },
    width.value,
    {
      extent: metrics(appearance.theme).compactControlHeight,
      radius: metrics(appearance.theme).itemRadius,
      badgeTextWidth: badgeTextWidth.value,
      hovered: hovered.value,
      pressed: pressed.value,
      focused: focused.value && !props.suppressFocus
    }
  )
);
let observer;
const measureBadge = () => {
  if (props.record.badgeCount === undefined && !props.record.showZeroBadge)
    return;
  const context = document.createElement('canvas').getContext('2d');
  context.font = `700 11px "${fontFamily}"`;
  const count = Number(props.record.badgeCount || 0);
  badgeTextWidth.value = context.measureText(
    count > 99 ? '99+' : String(count)
  ).width;
};
watch(() => props.record.badgeCount, measureBadge);

onMounted(() => {
  measureBadge();
  document.fonts.addEventListener('loadingdone', measureBadge);
  observer = observeFrameSizes((entries) => {
    width.value = entries.at(-1).contentRect.width;
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => {
  observer?.disconnect();
  document.fonts.removeEventListener('loadingdone', measureBadge);
});
</script>
<template>
  <div
    ref="root"
    class="action-row"
    :data-menu-command="record.command"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView :scene="scene" :interactive="false" />
    <AppButton
      v-if="!record.separator && !record.header"
      class="action-row-hit frame-hit-target"
      :label="title"
      :translate-label="false"
      :href="record.href"
      :target="record.href ? '_blank' : undefined"
      :rel="record.href ? 'noopener' : undefined"
      :disabled="record.enabled === false"
      :role="
        record.role ||
        (record.checked === undefined ? undefined : 'menuitemradio')
      "
      :aria-checked="record.checked"
      @pointerenter="hovered = true"
      @pointerleave="hovered = pressed = false"
      @pointerdown="pressed = true"
      @pointerup="pressed = false"
      @pointercancel="pressed = false"
      @focus="focused = true"
      @blur="focused = pressed = false"
      @click="$emit('triggered')"
    >
      <span hidden aria-hidden="true" />
    </AppButton>
  </div>
</template>
<style>
.action-row {
  position: relative;
  width: 100%;
  min-width: 0;
}
.action-row > .frame-view {
  pointer-events: none;
}
.action-row .action-row-hit.app-button {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}
.action-row .action-row-hit.app-button:disabled {
  opacity: 1;
}
</style>
