<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import MilestoneRow from './MilestoneRow.vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes } from '../../frame/resize.js';
import { metrics as frameMetrics } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/milestones.ui.mjs';
const props = defineProps({
  project: String,
  result: Object,
  rows: { type: Array, default: () => [] },
  query: String,
  busy: Boolean,
  uncertain: String,
  focused: String
});
const emit = defineEmits(['event']);
const root = ref(null),
  width = ref(800),
  height = ref(500);
let observer;
const metrics = computed(() => frameMetrics(appearance.theme));
const geometry = computed(() =>
  UI.layout(width.value, height.value, metrics.value.controlHeight)
);
const headerModel = computed(() => ({
  project: props.project,
  count: props.result?.records?.length ?? props.rows.length,
  radius: metrics.value.itemRadius,
  busy: props.busy,
  canCreate: !!(props.result?.canCreate && !props.uncertain)
}));
const bounds = (x, y, w, h) => ({
  left: x + 'px',
  top: y + 'px',
  width: w + 'px',
  height: h + 'px'
});
const editable = (name) =>
  props.result?.fields?.some((field) => field.name === name && field.editable);
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    width.value = entries[0].contentRect.width;
    height.value = entries[0].contentRect.height;
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="root" class="milestone-content-frame">
    <FrameView
      class="milestone-common-header"
      :style="bounds(geometry.margin, geometry.margin, geometry.inner, 76)"
      :scene="UI.header(headerModel, geometry.inner, appearance.language)"
      @event="(action) => emit('event', action)"
    />
    <FrameView
      class="milestone-frame-search"
      :style="
        bounds(
          geometry.margin,
          geometry.searchY,
          geometry.inner,
          metrics.controlHeight
        )
      "
      :scene="
        UI.search(
          { query, busy, controlHeight: metrics.controlHeight },
          geometry.inner,
          appearance.language
        )
      "
      @event="(action) => emit('event', action)"
    />
    <div
      class="milestone-results milestone-frame-results"
      :style="
        bounds(
          geometry.margin,
          geometry.listY,
          geometry.inner,
          geometry.listHeight
        )
      "
      :aria-busy="busy"
    >
      <MilestoneRow
        v-for="row in rows"
        :key="row.code"
        :model="{
          ...row,
          busy,
          uncertain,
          selected: focused === row.code,
          canDelete: result?.canDelete,
          canReview: !!row.revision && !uncertain,
          nameEditable: editable('description'),
          dateEditable: editable('due_date')
        }"
        @event="(action) => emit('event', action)"
      />
    </div>
    <div
      v-if="!rows.length"
      class="milestone-frame-empty"
      :style="
        bounds(
          geometry.margin,
          geometry.listY,
          geometry.inner,
          geometry.listHeight
        )
      "
    >
      <FrameView
        :style="{
          width: Math.min(360, geometry.inner) + 'px',
          height:
            UI.empty(
              { query },
              Math.min(360, geometry.inner),
              appearance.language
            ).height + 'px'
        }"
        :scene="
          UI.empty(
            { query, busy, canCreate: !!result?.canCreate },
            Math.min(360, geometry.inner),
            appearance.language
          )
        "
        @event="(action) => emit('event', action)"
      />
    </div>
  </div>
</template>
<style>
.milestone-content-frame {
  position: relative;
  height: 100%;
  min-height: 0;
  min-width: 0;
  background: var(--surface-deep);
}
.milestone-content-frame > .frame-view,
.milestone-content-frame > .milestone-results {
  position: absolute;
}
.milestone-frame-results {
  display: flex;
  flex-direction: column;
  gap: 7px;
  overflow: auto;
  scrollbar-gutter: stable;
  padding-right: 2px;
}
.milestone-frame-empty {
  position: absolute;
  display: grid;
  place-items: center;
}
</style>
