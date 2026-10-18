<script setup>
// Handler TaskGanttView.qml / TaskGanttProgressHandle.qml (EPL-1.0).
// TaskManager owns revisions, permissions, draft history and server writes.
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onActivated,
  onDeactivated,
  onMounted,
  ref,
  watch
} from 'vue';
import { t } from '../../i18n.js';
import { appearance } from '../../appearance.js';
import AppButton from '../../controls/AppButton.vue';
import AppMenu from '../../controls/AppMenu.vue';
import FrameView from '../../frame/FrameView.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/gantt.ui.mjs';
import { metrics as frameMetrics } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/tasks/gantt.state.mjs';
const props = defineProps({
  projection: Object,
  tasks: { type: Array, default: () => [] },
  selected: { type: Array, default: () => [] },
  collapsed: { type: Array, default: () => [] },
  busy: Boolean,
  projecting: Boolean,
  workingDays: Boolean,
  resourceMode: Boolean,
  canUndo: Boolean,
  canRedo: Boolean,
  active: String,
  hasMore: Boolean
});
const emit = defineEmits([
  'select',
  'select-all',
  'activate',
  'object',
  'collapse',
  'edit',
  'inspect',
  'working-days',
  'resource-mode',
  'undo',
  'redo',
  'batch',
  'schedule',
  'milestone',
  'progress',
  'delete',
  'load-more'
]);
const root = ref(null),
  body = ref(null),
  viewport = ref(800),
  gutter = ref(0),
  scrollX = ref(0),
  scrollY = ref(0),
  bodyHeight = ref(400),
  zoom = ref(1),
  scale = ref('auto'),
  drag = ref(null);
let observer,
  resizeFrame,
  autoScroll,
  ignoreClickUntil = 0;
const range = computed(() => props.projection?.gantt);
const dayCount = computed(() => Math.max(1, range.value?.days || 1));
const layout = computed(() =>
  State.layout(viewport.value, 0, dayCount.value, zoom.value, gutter.value)
);
const labelWidth = computed(() => layout.value.labels);
const timelineViewport = computed(() => layout.value.viewport);
const baseDayWidth = computed(() => layout.value.baseDay);
const dayWidth = computed(() => layout.value.day);
const timelineWidth = computed(() => layout.value.timeline);
const tasksByKey = computed(
  () => new Map(props.tasks.map((task) => [task.key, task]))
);
const rowLayout = computed(() =>
  State.rows(range.value?.records || [], props.collapsed)
);
const rows = computed(() => rowLayout.value.items);
const totalHeight = computed(() => rowLayout.value.height);
const visibleRows = computed(() =>
  rows.value.filter(
    (row) =>
      row.top + row.height >= scrollY.value - State.metrics.overscan &&
      row.top < scrollY.value + bodyHeight.value + State.metrics.overscan
  )
);
const headingScene = computed(() =>
  UI.heading(range.value || {}, labelWidth.value, appearance.language)
);
const gridScene = computed(() =>
  UI.grid(
    range.value || {},
    dayWidth.value,
    scrollX.value,
    timelineViewport.value,
    bodyHeight.value
  )
);
const dependencyScene = computed(() =>
  UI.dependencies(range.value?.records || [], props.collapsed, dayWidth.value)
);
const footerScene = computed(() =>
  UI.footer(
    {
      ...range.value,
      zoom: zoom.value,
      busy: props.busy,
      workingDays: props.workingDays,
      resourceMode: props.resourceMode,
      canUndo: props.canUndo,
      canRedo: props.canRedo,
      minZoom: 2 / baseDayWidth.value,
      hostWidth: viewport.value >= 380 ? 112 : 0
    },
    viewport.value,
    appearance.language
  )
);
const optionsTrigger = ref(null),
  scaleTrigger = ref(null),
  optionsAnchor = ref(null),
  scaleAnchor = ref(null);
function footerAction(action, source) {
  if (action.type === 'today')
    setScroll(
      range.value.todayDay * dayWidth.value - timelineViewport.value * 0.42
    );
  else if (action.type === 'zoom-in') setZoom(zoom.value * 1.25);
  else if (action.type === 'zoom-out') setZoom(zoom.value / 1.25);
  else if (action.type === 'working') emit('working-days', !props.workingDays);
  else if (action.type === 'resource')
    emit('resource-mode', !props.resourceMode);
  else if (action.type === 'options' && optionsTrigger.value.open)
    optionsTrigger.value.close(true);
  else if (action.type === 'options') {
    optionsAnchor.value = source;
    optionsTrigger.value.openAt({ target: source });
  } else if (action.type === 'scale' && scaleTrigger.value.open)
    scaleTrigger.value.close(true);
  else if (action.type === 'scale') {
    scaleAnchor.value = source;
    scaleTrigger.value.openAt({ target: source });
  } else emit(action.type);
}
const optionsScene = computed(() =>
  UI.options(
    {
      workingDays: props.workingDays,
      resourceMode: props.resourceMode,
      scale: scale.value,
      busy: props.busy,
      checked: props.selected.length,
      dirty: props.tasks.some((task) => task.pending)
    },
    268,
    appearance.language
  )
);
function optionAction(action) {
  if (action.type === 'working') emit('working-days', action.value);
  else if (action.type === 'resource') emit('resource-mode', action.value);
  else if (action.type === 'scale-value') {
    setScale(action.value);
    scaleTrigger.value.close(true);
  } else if (action.type === 'batch') {
    emit('batch', action.operation, action.amount);
    optionsTrigger.value.close(true);
  } else if (action.type === 'delete') {
    emit('delete');
    optionsTrigger.value.close(true);
  }
}
function rowModel(record) {
  const task = tasksByKey.value.get(record.taskCode) || {};
  return {
    ...record,
    selected: props.active === record.taskCode,
    checked: props.selected.includes(record.taskCode),
    dirty: task.pending,
    busy: props.busy,
    parentPreviewUrl: task.parent?.__preview_url__ || '',
    processColor: task.__process__?.color || record.processColor,
    warningText: warningText(record),
    touch: matchMedia('(hover:none)').matches
  };
}
function labelAction(action) {
  if (action.type === 'select')
    emit('select', action.key, !props.selected.includes(action.key));
  else if (action.type === 'edit') edit(action.key);
  else emit(action.type, action.key);
}
function barScene(record) {
  const pending = drag.value?.key === record.taskCode ? drag.value : null;
  return UI.scheduleBar(
    {
      ...record,
      progress: progress(record),
      ganttColor: color(record),
      radius: frameMetrics(appearance.theme).itemRadius,
      editing: pending && pending.mode !== 'progress',
      startLabel: pending ? dateForDay(pending.start) : '',
      endLabel: pending ? dateForDay(pending.start + pending.duration - 1) : '',
      progressSupported: progressSupported(record)
    },
    parseFloat(geometry(record).width),
    appearance.language
  );
}
function progressSupported(record) {
  const task = tasksByKey.value.get(record.taskCode) || {};
  return Object.hasOwn(task, 'progress') || Object.hasOwn(task, 'completion');
}
function dateForDay(day) {
  return State.dateForDay(range.value?.rangeStart, day);
}
function dateLabel(value) {
  return UI.dateLabel(value, appearance.language);
}
function warningText(record) {
  return (record.ganttWarning || record.ganttIssue || '')
    .split('\n')
    .map((value) => t(value))
    .join('\n');
}
function color(record) {
  return (
    tasksByKey.value.get(record.taskCode)?.__status__?.color ||
    record.ganttColor ||
    'var(--primary)'
  );
}
function progress(record) {
  return drag.value?.key === record.taskCode && drag.value.mode === 'progress'
    ? drag.value.progress
    : record.progress;
}
function geometry(record) {
  const pending =
    drag.value?.key === record.taskCode && drag.value.mode !== 'progress'
      ? drag.value
      : null;
  const value = State.bar(
    pending?.start ?? record.ganttStartDay,
    pending?.duration ?? record.ganttDurationDays,
    dayWidth.value
  );
  return {
    left: value.x + 'px',
    top: value.y + 'px',
    transform: 'none',
    width: value.width + 'px',
    '--bar-color': color(record)
  };
}
function synchronize() {
  scrollX.value = body.value.scrollLeft;
  scrollY.value = body.value.scrollTop;
}
function setScroll(value) {
  body.value.scrollLeft = Math.max(
    0,
    Math.min(timelineWidth.value - timelineViewport.value, value)
  );
  synchronize();
}
async function setZoom(
  value,
  anchor = timelineViewport.value / 2,
  mode = 'custom'
) {
  const next = State.zoomAt(layout.value, scrollX.value, value, anchor);
  scale.value = mode;
  zoom.value = next.zoom;
  await nextTick();
  setScroll(next.x);
}
function setScale(mode) {
  setZoom(
    State.scaleZoom(mode, baseDayWidth.value),
    timelineViewport.value / 2,
    mode
  );
}
function wheel(event, offset = 0) {
  event.preventDefault();
  if (event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY))
    setScroll(scrollX.value + (event.deltaX || event.deltaY) * 1.65);
  else
    setZoom(
      zoom.value *
        Math.pow(1.16, -event.deltaY / (event.deltaMode === 1 ? 3 : 100)),
      Math.max(
        0,
        event.clientX -
          event.currentTarget.getBoundingClientRect().left -
          offset
      )
    );
}
function timelineWheel(event) {
  if (
    event.clientX - event.currentTarget.getBoundingClientRect().left >=
    labelWidth.value
  )
    wheel(event, labelWidth.value);
}
function edit(key) {
  if (performance.now() >= ignoreClickUntil && !props.busy) emit('edit', key);
}
function activate(key, event) {
  if (performance.now() >= ignoreClickUntil && !props.busy)
    emit('activate', key, event);
}
function begin(record, mode, event, fromIssue = false) {
  if (props.busy || event.pointerType !== 'mouse' || event.button !== 0) return;
  if (mode === 'progress') event.currentTarget.focus({ preventScroll: true });
  else body.value.focus({ preventScroll: true });
  event.preventDefault();
  event.stopPropagation();
  event.currentTarget.setPointerCapture(event.pointerId);
  const timeline = event.currentTarget.closest('.task-gantt-timeline'),
    box = timeline.getBoundingClientRect();
  drag.value = {
    ...State.begin(
      record,
      mode,
      event.clientX - box.left,
      dayWidth.value,
      fromIssue
    ),
    originLeft: box.left + scrollX.value,
    clientX: event.clientX
  };

  autoScroll = setInterval(() => {
    if (!drag.value || drag.value.mode === 'progress') return;
    const rect = body.value.getBoundingClientRect(),
      x = drag.value.clientX;
    setScroll(
      State.autoScroll(
        x - rect.left - labelWidth.value,
        timelineViewport.value,
        scrollX.value,
        timelineWidth.value - timelineViewport.value
      )
    );
    updateDrag(x);
  }, State.metrics.autoScrollInterval);
}
function updateDrag(x) {
  const value = drag.value;
  if (!value) return;
  drag.value = {
    ...State.pointer(
      value,
      x - value.originLeft + scrollX.value,
      dayWidth.value
    ),
    clientX: x
  };
}

function finish(cancel = false) {
  clearInterval(autoScroll);
  const value = drag.value;
  drag.value = null;
  if (!value) return;
  const changed = State.changed(value);
  if (changed || State.moved(value)) ignoreClickUntil = performance.now() + 150;
  if (cancel || !changed) return;
  if (value.mode === 'progress') emit('progress', value.key, value.progress);
  else if (
    value.mode === 'create' ||
    value.start !== value.baseStart ||
    value.duration !== value.baseDuration
  )
    emit('schedule', value.key, value.start, value.duration, value.mode);
}
function keyboard(event) {
  if (event.key === 'Escape' && drag.value) {
    event.preventDefault();
    event.stopPropagation();
    finish(true);
  }
}
function progressKey(event, record) {
  const value = State.progressKey(record.progress, event.key);
  if (value === null) return;
  event.preventDefault();
  event.stopPropagation();
  emit('progress', record.taskCode, value);
}

let overviewOffset;
function overview(event) {
  const box = event.currentTarget.getBoundingClientRect();
  if (event.type === 'pointerdown') {
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    const thumb = UI.overviewGeometry(
        timelineViewport.value,
        timelineWidth.value,
        scrollX.value
      ),
      x = event.clientX - box.left;
    overviewOffset =
      x >= thumb.x && x <= thumb.x + thumb.width
        ? x - thumb.x
        : thumb.width / 2;
  }
  if (event.type === 'pointermove' && !event.buttons) return;
  setScroll(
    State.overviewPosition(
      event.clientX - box.left,
      timelineViewport.value,
      timelineWidth.value,
      overviewOffset
    )
  );
}

function pan(event) {
  if (
    event.pointerType !== 'mouse' ||
    ![0, 1].includes(event.button) ||
    event.target.closest('button,input,label,summary')
  )
    return;
  event.preventDefault();
  event.currentTarget.setPointerCapture(event.pointerId);
  event.currentTarget.dataset.panX = event.clientX;
  event.currentTarget.dataset.panScroll = scrollX.value;
}
function move(event) {
  if (drag.value) updateDrag(event.clientX);
  else if ([1, 4].includes(event.buttons) && event.currentTarget.dataset.panX)
    setScroll(
      Number(event.currentTarget.dataset.panScroll) +
        Number(event.currentTarget.dataset.panX) -
        event.clientX
    );
}
watch(visibleRows, (value) => {
  if (drag.value && !value.some((row) => row.key === drag.value.key))
    finish(true);
});
onMounted(() => {
  const measured = { width: 800, bodyWidth: 800, bodyHeight: 400 };
  observer = new ResizeObserver((entries) => {
    // Rounded client sizes can make the canvas overflow its own fractional viewport.
    for (const { target, contentRect } of entries) {
      if (target === root.value) measured.width = contentRect.width;
      else {
        measured.bodyWidth = contentRect.width;
        measured.bodyHeight = contentRect.height;
      }
    }
    cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => {
      viewport.value = measured.width;
      gutter.value = Math.max(0, measured.width - measured.bodyWidth);
      bodyHeight.value = measured.bodyHeight;
    });
  });
  observer.observe(root.value);
  observer.observe(body.value);
  document.addEventListener('keydown', keyboard, true);
  window.addEventListener('blur', cancel);
});
function cancel() {
  finish(true);
}
// KeepAlive mirrors the native lazy Gantt Loader: retain view state, suspend input.
let resumeFrame,
  activation = 0;
onDeactivated(() => {
  activation++;
  cancelAnimationFrame(resizeFrame);
  observer?.disconnect();
  finish(true);
  optionsTrigger.value?.close();
  scaleTrigger.value?.close();
  document.removeEventListener('keydown', keyboard, true);
  window.removeEventListener('blur', cancel);
  cancelAnimationFrame(resumeFrame);
});
onActivated(async () => {
  const generation = ++activation;
  const x = scrollX.value,
    y = scrollY.value;
  observer?.observe(root.value);
  observer?.observe(body.value);
  document.addEventListener('keydown', keyboard, true);
  window.addEventListener('blur', cancel);
  await nextTick();
  if (generation !== activation) return;
  resumeFrame = requestAnimationFrame(() => {
    resumeFrame = requestAnimationFrame(() => {
      body.value.scrollLeft = x;
      body.value.scrollTop = y;
      synchronize();
    });
  });
});
onBeforeUnmount(() => {
  activation++;
  observer?.disconnect();
  cancelAnimationFrame(resumeFrame);
  cancelAnimationFrame(resizeFrame);
  clearInterval(autoScroll);
  document.removeEventListener('keydown', keyboard, true);
  window.removeEventListener('blur', cancel);
});
</script>
<template>
  <section
    ref="root"
    class="task-schedule-view task-gantt-view"
    :aria-label="t('Task Gantt')"
    :aria-busy="projecting"
    :style="{
      '--gantt-label-width': labelWidth + 'px',
      '--gantt-width': timelineWidth + 'px',
      '--gantt-scroll-gutter': gutter + 'px',
      '--gantt-heading-height': State.metrics.heading + 'px',
      '--gantt-heading-gap': State.metrics.headingGap + 'px',
      '--gantt-overview-height': State.metrics.overview + 'px',
      '--gantt-footer-height': State.metrics.footer + 'px',
      '--gantt-bar-height': State.metrics.bar + 'px'
    }"
  >
    <header class="gantt-heading">
      <FrameView class="gantt-heading-label" :scene="headingScene" />
      <div class="gantt-heading-viewport" @wheel="wheel">
        <FrameView
          :scene="
            UI.timelineHeading(
              range || {},
              dayWidth,
              scrollX,
              timelineViewport,
              appearance.language
            )
          "
          @event="(action) => emit('milestone', action.value)"
        />
      </div>
    </header>
    <div
      ref="body"
      class="gantt-body"
      @wheel="timelineWheel"
      tabindex="0"
      :aria-label="t('Task schedule')"
      @scroll="synchronize"
      @pointerdown="pan"
      @pointermove="move"
      @pointerup="finish()"
      @pointercancel="finish(true)"
    >
      <div
        class="gantt-canvas"
        :style="{
          height: Math.max(bodyHeight, totalHeight) + 'px',
          width: labelWidth + timelineWidth + 'px'
        }"
      >
        <FrameView
          class="gantt-grid"
          :scene="gridScene"
          :interactive="false"
          :style="{
            left: labelWidth + scrollX + 'px',
            top: scrollY + 'px',
            width: timelineViewport + 'px',
            height: bodyHeight + 'px'
          }"
        />
        <FrameView
          class="gantt-dependencies"
          :scene="dependencyScene"
          :interactive="false"
          :style="{
            left: labelWidth + 'px',
            width: timelineWidth + 'px',
            height: totalHeight + 'px'
          }"
        />
        <div
          v-for="row in visibleRows"
          :key="row.key"
          class="task-gantt-row"
          :class="[
            'gantt-' + row.kind,
            {
              'task-selected': selected.includes(row.key),
              'task-active': active === row.key,
              pending: tasksByKey.get(row.key)?.pending
            }
          ]"
          :data-task-key="row.kind === 'task' ? row.key : undefined"
          :style="{ top: row.top + 'px', height: row.height + 'px' }"
        >
          <template v-if="row.kind === 'section'"
            ><FrameView
              class="gantt-band"
              :scene="UI.band(row.kind, labelWidth + timelineWidth)"
              :interactive="false" /><FrameView
              class="task-gantt-label task-gantt-section"
              :scene="
                UI.section(row.record, labelWidth, appearance.language)
              " />
            <div class="task-gantt-timeline"
          /></template>
          <template v-else-if="row.kind === 'group'"
            ><FrameView
              class="gantt-band gantt-group-band"
              :scene="
                UI.band(
                  row.kind,
                  labelWidth + timelineWidth,
                  row.record,
                  collapsed.includes(row.record.groupKey)
                )
              "
              @event="(action) => emit('collapse', action.value)" /><FrameView
              class="task-gantt-label gantt-group-label"
              :scene="
                UI.group(
                  row.record,
                  labelWidth,
                  collapsed.includes(row.record.groupKey)
                )
              "
              :interactive="false" /><FrameView
              class="task-gantt-timeline"
              :scene="
                UI.groupTimeline(
                  row.record,
                  dayWidth,
                  collapsed.includes(row.record.groupKey)
                )
              "
              :interactive="false"
          /></template>
          <template v-else
            ><FrameView
              class="gantt-row-surface"
              :scene="
                UI.rowSurface(rowModel(row.record), labelWidth + timelineWidth)
              "
              :interactive="false" /><FrameView
              class="task-gantt-label"
              :scene="
                UI.taskLabel(
                  rowModel(row.record),
                  labelWidth,
                  appearance.language
                )
              "
              @event="labelAction" />
            <div class="task-gantt-timeline" @dblclick="edit(row.key)">
              <div
                v-if="row.record.ganttScheduled || drag?.key === row.key"
                class="task-gantt-bar"
                :style="geometry(row.record)"
                :title="
                  row.record.parentTitle +
                  ' · ' +
                  row.record.status +
                  '\n' +
                  row.record.start +
                  ' — ' +
                  row.record.end +
                  '\n' +
                  warningText(row.record)
                "
              >
                <FrameView
                  class="gantt-bar-paint"
                  :scene="barScene(row.record)"
                  :interactive="false"
                />
                <AppButton
                  class="task-gantt-move"
                  :aria-label="
                    t('Edit schedule') + ' ' + row.record.parentTitle
                  "
                  :disabled="busy"
                  @click="activate(row.key, $event)"
                  @dblclick="emit('object', row.key)"
                  @pointerdown="begin(row.record, 'move', $event)"
                  @pointermove="move"
                  @pointerup.stop="finish()"
                  @pointercancel="finish(true)"
                >
                </AppButton>
                <small class="gantt-date-chip start">{{
                  dateLabel(row.record.start)
                }}</small
                ><small class="gantt-date-chip end">{{
                  dateLabel(row.record.end)
                }}</small>
                <AppButton
                  label="Resize start date"
                  icon-only
                  class="task-gantt-resize start"
                  :disabled="busy"
                  @click="edit(row.key)"
                  @pointerdown="begin(row.record, 'start', $event)"
                  @pointermove="move"
                  @pointerup.stop="finish()"
                  @pointercancel="finish(true)"
                ></AppButton>
                <AppButton
                  label="Resize deadline"
                  icon-only
                  class="task-gantt-resize end"
                  :disabled="busy"
                  @click="edit(row.key)"
                  @pointerdown="begin(row.record, 'end', $event)"
                  @pointermove="move"
                  @pointerup.stop="finish()"
                  @pointercancel="finish(true)"
                ></AppButton>
                <AppButton
                  v-if="
                    row.record.ganttScheduled &&
                    parseFloat(geometry(row.record).width) >= 36 &&
                    (Object.hasOwn(tasksByKey.get(row.key) || {}, 'progress') ||
                      Object.hasOwn(
                        tasksByKey.get(row.key) || {},
                        'completion'
                      ))
                  "
                  class="gantt-progress-handle"
                  label="Progress"
                  role="slider"
                  :aria-valuenow="progress(row.record)"
                  aria-valuemin="0"
                  aria-valuemax="100"
                  :style="{
                    left:
                      State.progressLeft(
                        parseFloat(geometry(row.record).width),
                        progress(row.record)
                      ) + 'px'
                  }"
                  :disabled="busy"
                  @keydown="progressKey($event, row.record)"
                  @pointerdown="begin(row.record, 'progress', $event)"
                  @pointermove="move"
                  @pointerup.stop="finish()"
                  @pointercancel="finish(true)"
                  ><span
                /></AppButton>
              </div>
              <div
                v-if="!row.record.ganttScheduled"
                class="gantt-issue"
                :style="{
                  opacity: drag?.key === row.key ? 0 : 1,
                  width:
                    UI.issue(row.record, timelineViewport, appearance.language)
                      .width + 'px'
                }"
              >
                <FrameView
                  :scene="
                    UI.issue(
                      {
                        ...row.record,
                        radius: frameMetrics(appearance.theme).itemRadius
                      },
                      timelineViewport,
                      appearance.language
                    )
                  "
                  :interactive="false"
                /><AppButton
                  label="Set task schedule"
                  icon-only
                  :disabled="busy"
                  @click="edit(row.key)"
                  @pointerdown="begin(row.record, 'create', $event, true)"
                  @pointermove="move"
                  @pointerup.stop="finish()"
                  @pointercancel="finish(true)"
                />
              </div></div
          ></template>
        </div>
      </div>
      <FrameView
        v-if="!range?.records.length"
        class="gantt-empty"
        :scene="
          UI.empty(
            viewport - gutter,
            bodyHeight,
            projecting,
            appearance.language
          )
        "
        :interactive="false"
      />
    </div>
    <div class="gantt-overview">
      <FrameView
        :scene="
          UI.overview(
            range || {},
            labelWidth,
            viewport - gutter,
            timelineWidth,
            scrollX,
            appearance.language
          )
        "
        :interactive="false"
      />
      <div
        class="task-gantt-overview"
        :style="{ left: labelWidth + 'px', width: timelineViewport + 'px' }"
        role="slider"
        tabindex="0"
        :aria-label="t('Timeline overview')"
        aria-valuemin="0"
        :aria-valuemax="dayCount"
        :aria-valuenow="Math.round(scrollX / dayWidth)"
        @pointerdown="overview"
        @pointermove="overview"
        @keydown.left.prevent="setScroll(scrollX - 100)"
        @keydown.right.prevent="setScroll(scrollX + 100)"
      />
    </div>
    <footer class="gantt-footer">
      <FrameView
        class="gantt-footer-frame"
        :scene="footerScene"
        @event="footerAction"
      />
      <AppMenu
        ref="optionsTrigger"
        :anchor="optionsAnchor"
        label="Schedule options"
        overlay
        external-trigger
        :width="284"
        :close-on-select="false"
        ><FrameView
          :style="{ width: '268px', height: optionsScene.height + 'px' }"
          :scene="optionsScene"
          @event="optionAction"
      /></AppMenu>
      <AppMenu
        ref="scaleTrigger"
        :anchor="scaleAnchor"
        label="Timeline scale"
        overlay
        external-trigger
        :width="170"
        ><FrameView
          style="width: 154px; height: 170px"
          :scene="UI.scaleOptions(scale, 154, appearance.language)"
          @event="optionAction"
      /></AppMenu>
      <div v-if="viewport >= 380" class="gantt-footer-host">
        <slot name="footer" />
      </div>
    </footer>
  </section>
</template>
<style>
.task-gantt-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}
.task-gantt-view .gantt-heading {
  flex: none;
  height: var(--gantt-heading-height);
  display: grid;
  grid-template-columns: var(--gantt-label-width) minmax(0, 1fr);
  padding-right: var(--gantt-scroll-gutter);
  background: var(--surface-container);
  border-radius: var(--item-radius);
}
.task-gantt-view .gantt-heading-label {
  height: var(--gantt-heading-height);
}
.gantt-heading-viewport {
  overflow: hidden;
  min-width: 0;
  height: var(--gantt-heading-height);
}
.gantt-heading-viewport > .frame-view {
  height: var(--gantt-heading-height);
}
/* ui-scrollbar: external-horizontal task-gantt-overview; native scrolling stays on this viewport. */
.gantt-body {
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow: auto;
  overscroll-behavior: contain;
  position: relative;
  margin-top: var(--gantt-heading-gap);
}
.gantt-body::-webkit-scrollbar:horizontal {
  height: 0;
}
.gantt-canvas {
  position: relative;
}
.gantt-grid,
.gantt-dependencies {
  position: absolute;
  top: 0;
  pointer-events: none;
}
.task-gantt-view .task-gantt-row {
  position: absolute;
  left: 0;
  width: 100%;
  display: grid;
  grid-template-columns: var(--gantt-label-width) var(--gantt-width);
  min-height: 0;
}
.task-gantt-view .task-gantt-label {
  position: sticky;
  left: 0;
  z-index: 3;
  min-width: 0;
  padding: 0;
  height: 100%;
}
.task-gantt-view .task-gantt-timeline {
  position: relative;
  min-height: 0;
}
.gantt-row-surface {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.task-gantt-view .task-gantt-bar {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  height: var(--gantt-bar-height);
  min-width: 7px;
}
.gantt-bar-paint {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: visible;
}
.task-gantt-view .task-gantt-move.app-button {
  position: relative;
  width: 100%;
  height: var(--gantt-bar-height);
  min-height: var(--gantt-bar-height);
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: grab;
}
.task-gantt-view .task-gantt-resize.app-button {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 12px;
  height: 22px;
  min-width: 12px;
  min-height: 22px;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: ew-resize;
}
.task-gantt-resize.start {
  left: -8px;
}
.task-gantt-resize.end {
  right: -8px;
}
.gantt-progress-handle.app-button {
  position: absolute;
  z-index: 5;
  top: 50%;
  transform: translateY(-50%);
  width: 18px;
  height: 22px;
  min-width: 18px;
  min-height: 22px;
  padding: 0;
  border: 1px solid var(--on-surface);
  border-radius: 6px;
  background: var(--surface-highest);
  cursor: ew-resize;
  opacity: 0;
}
.task-gantt-row:hover .gantt-progress-handle,
.task-gantt-row:focus-within .gantt-progress-handle {
  opacity: 1;
}
.gantt-progress-handle span {
  width: 7px;
  height: 9px;
  border-inline: 2px solid var(--on-surface);
}
.gantt-date-chip {
  display: none;
  position: absolute;
  top: -10px;
  height: 17px;
  padding: 0 6px;
  border: 1px solid var(--outline-variant);
  border-radius: 9px;
  background: var(--surface-highest);
  color: var(--on-surface);
  font-size: var(--text-micro);
  pointer-events: none;
  z-index: 8;
  white-space: nowrap;
}
.gantt-date-chip.end {
  right: 0;
}
.task-gantt-bar:hover .gantt-date-chip {
  display: block;
}
.gantt-empty {
  position: absolute;
  inset: 0;
  text-align: center;
  color: var(--muted);
}
.gantt-overview {
  flex: none;
  display: block;
  position: relative;
  height: var(--gantt-overview-height);
}
.gantt-overview > .frame-view {
  height: var(--gantt-overview-height);
}
.task-gantt-view .task-gantt-overview {
  position: absolute;
  top: 0;
  height: 30px;
  min-width: 0;
  cursor: ew-resize;
  touch-action: none;
}
.gantt-footer {
  flex: none;
  position: relative;
  display: block;
  height: var(--gantt-footer-height);
  min-width: 0;
}
.gantt-footer-frame {
  height: var(--gantt-footer-height);
}
.gantt-footer-host {
  position: absolute;
  right: 8px;
  top: 15px;
  height: 28px;
  display: flex;
  align-items: center;
  gap: 5px;
}
</style>

<style>
.gantt-band {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.gantt-group-band {
  pointer-events: auto;
}
.gantt-group-label {
  pointer-events: none;
}
.task-gantt-view .gantt-issue {
  position: absolute;
  top: 10px;
  left: 10px;
  height: 30px;
}
.gantt-issue > .app-button {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  padding: 0;
  border: 0;
  background: transparent;
}
</style>

<style>
.gantt-dependencies {
  z-index: 2;
}
.task-gantt-view .task-gantt-bar {
  z-index: 3;
}
</style>
