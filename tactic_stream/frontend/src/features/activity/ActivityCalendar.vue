<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import BusyIndicator from '../../controls/BusyIndicator.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { t } from '../../i18n.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/activity/calendar.ui.mjs';
const props = defineProps({ counts: Object, selected: String, busy: Boolean });
const emit = defineEmits(['accepted', 'closed']);
const root = ref(null),
  width = ref(320),
  month = ref(new Date());
let observer;
const scene = computed(() =>
  UI.describe(
    {
      counts: props.counts,
      selected: props.selected,
      month: month.value,
      busy: props.busy
    },
    width.value,
    appearance.language
  )
);
function reset() {
  month.value = UI.initialMonth(props.selected, props.counts);
}
function action(event) {
  if (event.type === 'day') emit('accepted', event.value);
  else if (event.type === 'close') emit('closed');
  else {
    month.value = UI.moveMonth(month.value, event.type === 'previous' ? -1 : 1);
  }
}
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    if (entries[0].contentRect.width > 0)
      width.value = entries[0].contentRect.width;
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
defineExpose({ reset });
</script>
<template>
  <section
    ref="root"
    class="activity-calendar"
    :aria-label="t('Activity calendar')"
    :aria-busy="busy"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView
      :scene="scene"
      :views="{ busy: { component: BusyIndicator, props: { running: busy } } }"
      @event="action"
    />
  </section>
</template>
<style>
.activity-calendar {
  position: relative;
  width: 320px;
  max-width: 100%;
  min-width: 0;
}
.activity-calendar > .frame-view {
  height: 100%;
}
</style>
