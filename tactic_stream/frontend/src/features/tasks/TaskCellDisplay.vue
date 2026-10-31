<script setup>
import { computed, ref, markRaw, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import ItemPreview from '../../controls/ItemPreview.vue';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/cells.ui.mjs';

const props = defineProps({
  model: Object,
  user: Object,
  height: { type: Number, default: 29 }
});
const host = ref(null),
  width = ref(0),
  hovered = ref(false);
const scene = computed(() =>
  UI.choice(
    { ...props.model, hovered: hovered.value },
    width.value,
    props.height
  )
);
const avatar = markRaw(ItemPreview);
const views = computed(() => ({
  avatar: {
    component: avatar,
    props: {
      source: props.user?.avatarUrl,
      fallbackText:
        props.user?.initials ||
        (props.model.avatarLabel === ''
          ? ''
          : UI.initials(props.model.avatarLabel ?? props.model.text)),
      fallbackIcon: 'user',
      accent: props.user?.avatarColor,
      previewSize: Math.max(
        0,
        Math.min(
          props.model.cardField ? UI.cardMetrics.avatar : 22,
          props.height - 4
        )
      ),
      round: true,
      outlined: true
    }
  }
}));
let observer;
onMounted(() => {
  const measure = () => {
    width.value = frameContentWidth(host.value);
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <span
    ref="host"
    class="task-cell-display"
    :style="{ height: height + 'px' }"
    @pointerenter="hovered = true"
    @pointerleave="hovered = false"
    ><FrameView :scene="scene" :views="views"
  /></span>
</template>
<style>
.task-cell-display {
  display: block;
  position: relative;
  width: 100%;
  height: 29px;
  min-width: 0;
}
</style>
