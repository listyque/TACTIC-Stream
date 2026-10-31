<script setup>
import { computed, ref } from 'vue';
import FrameView from '../../frontend/src/frame/FrameView.vue';
import AppButton from '../../frontend/src/controls/AppButton.vue';
import SummaryChip from '../../frontend/src/controls/SummaryChip.vue';
import QuickFilterChip from '../../frontend/src/controls/display/QuickFilterChip.vue';
import ReactionChip from '../../frontend/src/controls/display/ReactionChip.vue';
import records from '../../tests/fixtures/frame_service_buttons.json';
import {
  appearance,
  initializeAppearance,
  hostedPalette
} from '../../frontend/src/appearance.js';
import {
  node,
  button,
  rect
} from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import { metrics } from '../../src/tactic_stream/shared_ui/core/foundation.mjs';
const events = ref([]),
  width = ref(360);
Object.assign(appearance, {
  theme: 'md3',
  mode: 'dark',
  language: 'en',
  clickAnimations: false,
  hoverAnimations: false,
  fadeAnimations: false,
  popupAnimations: false
});
hostedPalette.value = {
  dark: '#78a6c4',
  darkBase: '#292d30',
  light: '#3d7599',
  lightBase: '#d4dce1'
};
initializeAppearance();
const scene = computed(() => {
  const h = metrics(appearance.theme).controlHeight;
  return {
    nodes: [
      node('Box', 'mainTitlebar', rect(0, 0, width.value, 64), {
        titlebar: true,
        background: 'surfaceContainerLow',
        radius: 0,
        children: [
          button(
            'mainClose',
            rect(12, 12, h, h),
            'Close',
            'close',
            { type: 'test', id: 'mainClose' },
            true,
            { iconOnly: true }
          ),
          button(
            'mainSave',
            rect(60, 12, 140, h),
            'Save',
            'save',
            { type: 'test', id: 'mainSave' },
            true
          )
        ]
      }),
      ...records.map((record, index) => {
        const { id, ...options } = record;
        return button(
          id,
          rect(12, 80 + index * 48, record.iconOnly ? h : 140, h),
          record.text,
          record.icon,
          { type: 'test', id },
          record.enabled !== false,
          options
        );
      })
    ]
  };
});
window.serviceButtons = {
  configure(options) {
    appearance.theme = options.style;
    appearance.mode = options.dark ? 'dark' : 'light';
    width.value = options.width || 360;
    events.value = [];
  },
  events: () => events.value
};
</script>
<template>
  <div class="shape-fixture" :style="{ width: width + 'px' }">
    <FrameView :scene="scene" @event="events.push($event.id)" />
    <AppButton
      class="shape-special shape-count"
      data-shape="serviceCount"
      icon="tasks"
      icon-only
      label="Task Manager"
      :badge-count="7"
      @click="events.push('serviceCount')"
    />
    <QuickFilterChip
      class="shape-special shape-filter"
      data-shape="serviceFilter"
      text="Filter"
      checked
      @click="events.push('serviceFilter')"
    />
    <SummaryChip
      class="shape-special shape-summary"
      data-shape="serviceSummary"
      label="Tasks"
      :count="7"
      clickable
      @click="events.push('serviceSummary')"
    />
    <ReactionChip
      class="shape-special shape-reaction"
      data-shape="serviceReaction"
      emoji="✓"
      :count="2"
      @click="events.push('serviceReaction')"
    />
  </div>
</template>
<style>
.shape-fixture {
  position: relative;
  height: 650px;
  background: var(--page);
}
.shape-special {
  position: absolute !important;
  left: 12px;
}
.shape-count {
  top: 438px;
  width: 32px !important;
  height: 32px !important;
  min-width: 32px;
  min-height: 32px;
}
.shape-filter {
  top: 486px;
  width: 140px !important;
  height: 30px !important;
}
.shape-summary {
  top: 534px;
  width: 140px !important;
  height: 30px !important;
}
.shape-reaction {
  top: 582px;
  width: 70px !important;
  height: 28px !important;
}
</style>
