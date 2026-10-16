<script setup>
import { layoutTextWidth } from '../../controls/typography/textMetrics.js';
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import AppButton from '../../controls/AppButton.vue';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import {
  metrics,
  fontFamily
} from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import {
  card,
  lifecycle
} from '../../../../src/tactic_stream/shared_ui/shell/projects.ui.mjs';
import { observeFrameSizes } from '../../frame/resize.js';
const props = defineProps({ record: Object, selected: Boolean });
const emit = defineEmits(['selected']);
const root = ref(null),
  width = ref(248),
  hovered = ref(false),
  pressed = ref(false),
  focused = ref(false),
  textMetrics = ref({
    chipWidth: 52,
    descriptionWidth: 0,
    detailLabelWidth: 45
  });
const scene = computed(() =>
  card(
    width.value,
    props.record,
    {
      ...textMetrics.value,
      selected: props.selected,
      hovered: hovered.value,
      pressed: pressed.value,
      focused: focused.value,
      radius: metrics(appearance.theme).sectionRadius,
      previewRadius: metrics(appearance.theme).itemRadius
    },
    t
  )
);
function measure() {
  const extent = (text, font) => {
    return layoutTextWidth(text, font + ' "' + fontFamily + '"');
  };
  textMetrics.value = {
    chipWidth: extent(t(lifecycle(props.record)), '600 11px'),
    descriptionWidth: extent(
      props.record.description || t('No project description'),
      '12px'
    ),
    detailLabelWidth: Math.max(
      extent(t('Category'), '11px'),
      extent(t('Type'), '11px')
    )
  };
}
let observer;
watch(() => [props.record, appearance.language], measure, { deep: true });
onMounted(() => {
  measure();
  document.fonts.addEventListener('loadingdone', measure);
  observer = observeFrameSizes(
    (entries) => (width.value = entries.at(-1).contentRect.width)
  );
  observer.observe(root.value);
});
onBeforeUnmount(() => {
  observer?.disconnect();
  document.fonts.removeEventListener('loadingdone', measure);
});
</script>
<template>
  <div
    ref="root"
    class="project-card frame-project-card"
    :data-project="record.code"
  >
    <FrameView :scene="scene" :interactive="false" />
    <AppButton
      class="project-card-hit frame-hit-target"
      :label="record.title || record.code"
      :translate-label="false"
      :aria-pressed="selected"
      @pointerenter="hovered = true"
      @pointerleave="
        hovered = false;
        pressed = false;
      "
      @pointerdown="pressed = true"
      @pointerup="pressed = false"
      @pointercancel="pressed = false"
      @focus="focused = true"
      @blur="
        focused = false;
        pressed = false;
      "
      @click="emit('selected', record.code)"
      ><span hidden aria-hidden="true"
    /></AppButton>
  </div>
</template>
<style>
.project-card.frame-project-card {
  position: relative;
  display: block;
  height: 258px;
  padding: 0;
  border: 0;
  background: transparent;
}
.frame-project-card > .frame-view {
  pointer-events: none;
}
.frame-project-card .project-card-hit {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 0;
}
</style>
