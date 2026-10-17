<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/inspector.ui.mjs';
const props = defineProps({
  summary: Object,
  expanded: Boolean,
  busy: Boolean,
  hasTask: { type: Boolean, default: true }
});
const emit = defineEmits(['log', 'timesheet']);
const host = ref(null),
  width = ref(0);
let observer;
const scene = computed(() =>
  UI.workHours(props, width.value, appearance.language)
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
</script>
<template>
  <section
    ref="host"
    class="work-hours-summary shared-work-hours"
    :class="{ compact: !expanded }"
    :aria-label="t('Work hours')"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView :scene="scene" @event="emit($event.type)" />
  </section>
</template>
<style>
.notes-panel > .shared-work-hours {
  position: relative;
  min-width: 0;
  flex: none;
  padding: 0;
  border: 0;
  overflow: hidden;
  width: calc(100% - 16px);
  margin: 0 8px 5px;
}
</style>
