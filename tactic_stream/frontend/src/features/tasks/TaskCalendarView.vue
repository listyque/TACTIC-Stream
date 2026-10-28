<script setup>
// The independent calendar dock shares its entire composition with Handler.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { metrics as frameMetrics } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/calendar.ui.mjs';
const props = defineProps({
  projection: Object,
  year: Number,
  month: Number,
  selectedDay: String,
  busy: Boolean,
  projecting: Boolean,
  error: String,
  hasMore: Boolean
});
const emit = defineEmits([
  'month',
  'month-value',
  'today',
  'day',
  'inspect',
  'milestone',
  'load-more',
  'tasks'
]);
const root = ref(null),
  width = ref(600),
  height = ref(500),
  agenda = ref(false),
  hovered = ref('');
let observer;
const layout = computed(() => UI.layout(width.value, height.value));
const days = computed(() => props.projection?.calendar || []);
const model = computed(() => ({
  ...props,
  monthDate: props.year + '-' + String(props.month).padStart(2, '0') + '-01'
}));
const rows = computed(() => UI.agendaRows(days.value, props.selectedDay));
const bounds = (x, y, w, h) => ({
  left: x + 'px',
  top: y + 'px',
  width: w + 'px',
  height: h + 'px'
});
function action(event) {
  if (event.type === 'previous') emit('month', -1);
  else if (event.type === 'next') emit('month', 1);
  else if (event.type === 'agenda') agenda.value = !agenda.value;
  else if (event.type === 'clear') emit('day', '');
  else
    emit(
      event.type,
      event.type === 'month-value' ? event.value.slice(0, 7) : event.value
    );
}
function dayModel(day, index) {
  return {
    ...day,
    index,
    compact: layout.value.compact,
    selected: day.date === props.selectedDay,
    hovered: hovered.value === day.date,
    busy: props.busy,
    radius: frameMetrics(appearance.theme).itemRadius
  };
}
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
  <section
    ref="root"
    class="task-calendar-view"
    :class="{ compact: layout.compact }"
    :aria-label="t('Task calendar')"
    :aria-busy="projecting"
  >
    <FrameView
      class="calendar-navigation"
      :style="bounds(layout.margin, layout.margin, layout.inner, 34)"
      :scene="UI.navigation(model, layout.inner, appearance.language)"
      @event="action"
    />
    <p v-if="error" role="alert" class="calendar-error">{{ t(error) }}</p>
    <div
      v-show="!agenda"
      class="calendar-weekdays"
      :style="{
        ...bounds(
          layout.margin,
          layout.margin + 34 + layout.gap,
          layout.inner,
          22
        ),
        gap: layout.cellGap + 'px'
      }"
    >
      <FrameView
        v-for="index in 7"
        :key="index"
        :scene="UI.weekday(index - 1, layout.cellWidth, appearance.language)"
      />
    </div>
    <div
      v-show="!agenda"
      class="task-calendar-grid"
      :style="{
        ...bounds(layout.margin, layout.gridY, layout.inner, layout.gridHeight),
        gap: layout.cellGap + 'px'
      }"
    >
      <FrameView
        v-for="(day, index) in days"
        :key="day.date"
        class="task-calendar-day"
        :data-date="day.date"
        :style="{ opacity: day.inMonth ? 1 : 0.55 }"
        :scene="
          UI.day(
            dayModel(day, index),
            layout.cellWidth,
            layout.cellHeight,
            appearance.language
          )
        "
        @pointerenter="hovered = day.date"
        @pointerleave="hovered = ''"
        @event="action"
      />
    </div>
    <div
      v-if="agenda"
      class="task-calendar-agenda"
      :style="
        bounds(
          layout.margin,
          layout.margin + 34 + layout.gap,
          layout.inner,
          layout.footerY - layout.margin - 34 - layout.gap * 2
        )
      "
    >
      <FrameView
        v-for="row in rows"
        :key="row.key"
        style="height: 34px"
        :scene="UI.agendaRow(row, layout.inner - 14)"
        @event="action"
      />
      <p v-if="!rows.length" class="muted">
        {{ t('No loaded tasks on these dates.') }}
      </p>
    </div>
    <FrameView
      class="calendar-footer"
      :style="bounds(layout.margin, layout.footerY, layout.inner, 28)"
      :scene="UI.footer(model, layout.inner, appearance.language)"
      @event="action"
    />
  </section>
</template>
<style>
.task-calendar-view {
  position: relative;
  height: 100%;
  min-height: 0;
  min-width: 0;
  background: var(--page);
  overflow: hidden;
}
.task-calendar-view > .frame-view,
.task-calendar-view > .calendar-weekdays,
.task-calendar-view > .task-calendar-grid,
.task-calendar-view > .task-calendar-agenda {
  position: absolute;
}
.task-calendar-view .calendar-weekdays,
.task-calendar-view .task-calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
}
.task-calendar-view .task-calendar-grid {
  grid-template-rows: repeat(6, minmax(0, 1fr));
  padding: 0;
  border: 0;
}
.task-calendar-view .task-calendar-day {
  overflow: hidden;
  border-radius: var(--item-radius);
}
.task-calendar-agenda {
  overflow: auto;
  scrollbar-gutter: stable;
  padding-right: 2px;
}
.calendar-error {
  position: absolute;
  top: 44px;
  left: 10px;
  right: 10px;
  z-index: 5;
  color: var(--error);
  background: var(--page);
}
</style>
