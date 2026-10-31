<script setup>
import { ref } from 'vue';
import TaskCell from '../../frontend/src/features/interface/TaskCell.vue';
import {
  appearance,
  initializeAppearance,
  hostedPalette
} from '../../frontend/src/appearance.js';
const width = ref(180),
  height = ref(52),
  events = ref([]);
const tasks = ref([
  {
    process: 'model',
    processLabel: 'Model',
    taskSearchKey: 'sthpw/task?code=TASK001',
    hasTask: true,
    status: 'In Progress',
    statusColor: '#bd6d58',
    assigned: 'admin',
    assignedLabel: 'Administrator',
    bidStart: '2026-11-01',
    bidEnd: '2026-11-05',
    simpleDates: false
  },
  {
    process: 'rig',
    processLabel: 'Rig',
    status: '',
    assigned: '',
    bidStart: '',
    bidEnd: '',
    simpleDates: false
  }
]);
Object.assign(appearance, {
  mode: 'dark',
  theme: 'md3',
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
window.taskHover = {
  configure(options) {
    width.value = options.width || 180;
    height.value = options.height || 52;
    appearance.theme = options.style || 'md3';
    appearance.mode = options.dark === false ? 'light' : 'dark';
    if (options.tasks) tasks.value = options.tasks;
  },
  events() {
    return events.value;
  },
  reset() {
    events.value = [];
  }
};
</script>
<template>
  <div
    class="handler-table-cell"
    :style="{ width: width + 'px', height: height + 'px', margin: '80px 24px' }"
  >
    <TaskCell
      :cell="{ tasks, count: 1 }"
      :height="height"
      editable
      @inspect="
        events.push({ type: 'inspect', process: $event?.process || '' })
      "
      @edit="
        (task, field) =>
          events.push({ type: 'edit', process: task.process, field })
      "
    />
  </div>
</template>
