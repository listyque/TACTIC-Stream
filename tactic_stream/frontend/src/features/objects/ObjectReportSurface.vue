<script setup>
import { computed, ref, h, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { linkifyPlainText, activateRichLink } from '../../controls/richText.js';
import { qtLabelTextWidth } from '../../controls/typography/textMetrics.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/report.ui.mjs';
const props = defineProps({
  model: Object,
  part: { type: String, default: 'header' }
});
const emit = defineEmits(['event']);
const host = ref(null),
  width = ref(0);
function measure(text, size, weight = 400) {
  return qtLabelTextWidth(text, `${weight} ${size}px Segoe UI`);
}
const descriptionView = {
  nodeProps: true,
  props: ['frameNode'],
  setup: (props) => () =>
    h('div', {
      class: 'report-description-value',
      style: {
        color: props.frameNode.empty ? 'var(--muted)' : 'var(--on-surface)'
      },
      innerHTML: linkifyPlainText(props.frameNode.text),
      onClick: (event) =>
        activateRichLink(event, (link) =>
          emit('event', { type: 'link', value: link })
        )
    })
};
const scene = computed(() =>
  props.part === 'header'
    ? UI.header(props.model, width.value, appearance.language, measure)
    : UI.page(props.model, width.value, appearance.language)
);
let observer;
onMounted(() => {
  const measure = () => {
    width.value = host.value.clientWidth;
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <section
    ref="host"
    class="object-report-surface"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView
      :scene="scene"
      :views="{
        reportDescription: { component: descriptionView, nodeProps: true }
      }"
      @event="emit('event', $event)"
    />
  </section>
</template>
<style>
.report-description-value {
  font:
    13px/17px 'Segoe UI',
    sans-serif;
  overflow: hidden;
  height: 100%;
  user-select: text;
  overflow-wrap: anywhere;
}
.object-report-surface {
  min-width: 0;
  flex: none;
  width: 100%;
  position: relative;
}
</style>
