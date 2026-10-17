<script setup>
// Handler TacticTaskCell: delayed pointer preview, tap pinning, native light dismiss.
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch
} from 'vue';
import AppButton from '../../controls/AppButton.vue';
import TaskCards from './TaskCards.vue';
import { t } from '../../i18n.js';
import * as Cells from '../../../../src/tactic_stream/shared_ui/features/table/cells.ui.mjs';

const props = defineProps({
  cell: Object,
  editable: Boolean,
  height: Number,
  selectedPreview: Boolean
});
const emit = defineEmits(['inspect', 'edit', 'hover']);
const anchor = ref(null),
  popup = ref(null),
  menu = ref(null);
const width = ref(240),
  visible = ref(false),
  pinned = ref(false);
const tasks = computed(() => props.cell?.tasks || []);
const layout = computed(() =>
  Cells.taskLayout(tasks.value.length, width.value, props.height || 58)
);
const overflow = computed(() => layout.value.overflow);
const count = computed(() => layout.value.visible);
let observer,
  opening,
  closing,
  hovering = false,
  inside = false,
  request = 0;

function cancelTimers() {
  clearTimeout(opening);
  clearTimeout(closing);
}
function close(focus = false) {
  request++;
  cancelTimers();
  popup.value?.hidePopover();
  visible.value = pinned.value = false;
  inside = hovering = false;
  emit('hover', false);
  if (focus === true) menu.value?.$el.focus();
}
async function open(pin = false) {
  if (!tasks.value.length) {
    emit('inspect', null);
    return;
  }
  cancelTimers();
  pinned.value = pin || pinned.value;
  const id = ++request;
  await nextTick();
  if (id !== request || !popup.value || !anchor.value?.isConnected) return;
  const bounds = anchor.value.getBoundingClientRect();
  const cardsWidth = layout.value.previewWidth;
  const popupWidth = Math.min(innerWidth - 16, cardsWidth + 16);
  popup.value.style.width = popupWidth + 'px';
  popup.value.style.height =
    (props.height || 58) + 16 + (cardsWidth > popupWidth - 16 ? 16 : 0) + 'px';
  popup.value.style.setProperty(
    '--table-row-height',
    (props.height || 58) + 'px'
  );
  popup.value.showPopover();
  visible.value = true;
  const size = {
    width: popup.value.offsetWidth,
    height: popup.value.offsetHeight
  };
  popup.value.style.left =
    Math.max(8, Math.min(bounds.left - 8, innerWidth - size.width - 8)) + 'px';
  popup.value.style.top =
    Math.max(8, Math.min(bounds.top - 8, innerHeight - size.height - 8)) + 'px';
  if (pin) popup.value.querySelector('button')?.focus();
}
function enter(event) {
  if (event.pointerType !== 'mouse') return;
  hovering = true;
  emit('hover', true);
  scheduleOpen();
}
function moved(event) {
  if (!hovering) enter(event);
}
function scheduleOpen() {
  clearTimeout(closing);
  clearTimeout(opening);
  if (overflow.value && tasks.value.length && !visible.value)
    opening = setTimeout(() => {
      if (hovering || props.selectedPreview) open();
    }, 260);
}
function leave() {
  hovering = false;
  emit('hover', inside);
  if (!props.selectedPreview) clearTimeout(opening);
  scheduleClose();
}
function scheduleClose() {
  clearTimeout(closing);
  if (!pinned.value && !hovering && !inside && !props.selectedPreview)
    closing = setTimeout(() => {
      if (!pinned.value && !hovering && !inside && !props.selectedPreview)
        close();
    }, 180);
}
function popupEnter() {
  inside = true;
  emit('hover', true);
  clearTimeout(closing);
}
function popupLeave() {
  inside = false;
  emit('hover', hovering);
  scheduleClose();
}
function activate() {
  pinned.value = true;
  clearTimeout(closing);
}
function inspect(task) {
  close();
  emit('inspect', task);
}
function edit(task, field, bounds) {
  cancelTimers();
  if (visible.value) pinned.value = true;
  emit('edit', task, field, bounds);
}
function scrolled(event) {
  if (!(event.target instanceof Node) || !popup.value?.contains(event.target))
    close();
}
function toggled(event) {
  if (event.newState === 'closed') {
    request++;
    cancelTimers();
    visible.value = pinned.value = false;
    inside = false;
  }
}
function outside(event) {
  if (
    visible.value &&
    !popup.value?.contains(event.target) &&
    !anchor.value?.contains(event.target) &&
    !event.target.closest('.task-table-editor,.user-combo-box,.date-calendar')
  )
    close();
}
function escape(event) {
  if (visible.value && event.key === 'Escape' && !event.defaultPrevented) {
    event.preventDefault();
    close(true);
  }
}
watch(
  () =>
    tasks.value
      .map((task) => task.taskSearchKey || task.context || task.process)
      .join('\n'),
  () => close()
);
watch(
  () => props.height,
  () => close()
);
watch(
  () => props.selectedPreview,
  (active) => {
    if (active) scheduleOpen();
    else {
      if (!hovering) clearTimeout(opening);
      scheduleClose();
    }
  }
);
onMounted(() => {
  observer = new ResizeObserver((entries) => {
    width.value = entries[0].contentRect.width;
  });
  observer.observe(anchor.value);
  window.addEventListener('scroll', scrolled, true);
  window.addEventListener('resize', close);
  window.addEventListener('pointerdown', outside, true);
  window.addEventListener('keydown', escape);
});
onBeforeUnmount(() => {
  close();
  observer?.disconnect();
  window.removeEventListener('scroll', scrolled, true);
  window.removeEventListener('resize', close);
  window.removeEventListener('pointerdown', outside, true);
  window.removeEventListener('keydown', escape);
});
</script>

<template>
  <div
    ref="anchor"
    class="table-tasks table-task-cell"
    :style="{ '--table-row-height': (height || 52) + 'px' }"
    @pointerenter="enter"
    @pointermove="moved"
    @pointerleave="leave"
  >
    <TaskCards
      :tasks="tasks.slice(0, count)"
      :height="height"
      :editable="editable"
      :class="{ 'task-cards-covered': visible }"
      @inspect="inspect"
      @edit="edit"
    />
    <AppButton
      v-if="overflow"
      ref="menu"
      label="Task Manager"
      icon="tasks"
      icon-only
      class="task-preview-trigger"
      :badge-count="cell?.count || 0"
      @click="inspect(null)"
    />
  </div>
  <Teleport to="body">
    <div
      ref="popup"
      popover="manual"
      class="task-preview"
      role="dialog"
      :aria-label="t('Task previews')"
      @toggle="toggled"
      @keydown.esc.stop.prevent="close(true)"
      @pointerenter="popupEnter"
      @pointerleave="popupLeave"
      @pointerdown="activate"
      @focusin="activate"
    >
      <TaskCards
        :tasks="tasks"
        :height="height || 58"
        :editable="editable"
        @inspect="inspect"
        @edit="edit"
      />
    </div>
  </Teleport>
</template>

<style>
.task-preview > .task-cards {
  width: max-content;
  height: var(--table-row-height);
}
.handler-table-cell .table-task-cell {
  width: calc(100% - 12px);
  height: var(--table-row-height);
  margin: 3px 6px;
}
.task-preview-trigger {
  color: var(--primary);
}
.task-preview-trigger .app-button-badge {
  background: var(--primary);
}
</style>
