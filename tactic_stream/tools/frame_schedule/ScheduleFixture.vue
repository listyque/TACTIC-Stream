<script setup>
import { ref, computed, nextTick } from 'vue';
import {
  appearance,
  hostedPalette,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import TaskGanttView from '../../frontend/src/features/tasks/TaskGanttView.vue';
import TaskCalendarView from '../../frontend/src/features/tasks/TaskCalendarView.vue';
import MilestoneContent from '../../frontend/src/features/tasks/MilestoneContent.vue';
import TaskScheduleEditor from '../../frontend/src/features/tasks/TaskScheduleEditor.vue';
const fixture = ref(null);
hostedPalette.value = {
  dark: '#78a6c4',
  darkBase: '#292d30',
  light: '#3d7599',
  lightBase: '#d4dce1'
};
initializeAppearance();
const tasks = computed(() =>
  (fixture.value?.model.gantt.records || []).map((row) => ({
    key: row.taskCode,
    progress: row.progress,
    parent: { __preview_url__: '' },
    __process__: { color: row.processColor },
    __status__: { color: row.ganttColor }
  }))
);
window.scheduleFixture = {
  async show(value) {
    fixture.value = value;
    Object.assign(appearance, {
      theme: value.style,
      mode: value.dark ? 'dark' : 'light',
      language: value.language,
      clickAnimations: false,
      hoverAnimations: false,
      fadeAnimations: false,
      popupAnimations: false
    });
    await nextTick();
    await document.fonts.ready;
    await new Promise((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(resolve))
    );
  }
};
</script>
<template>
  <main
    v-if="fixture"
    id="schedule-fixture"
    :style="{ width: fixture.width + 'px', height: fixture.height + 'px' }"
  >
    <TaskScheduleEditor
      v-if="fixture.screen === 'editor'"
      :model="fixture.model.schedule"
    />
    <TaskCalendarView
      v-else-if="['calendar', 'agenda'].includes(fixture.screen)"
      :projection="fixture.model"
      :year="2026"
      :month="10"
      selected-day=""
    />
    <MilestoneContent
      v-else-if="fixture.screen.startsWith('milestone')"
      project="demo"
      :rows="fixture.model.milestones"
      :result="{
        records: fixture.model.milestones,
        fields: [
          { name: 'description', editable: true },
          { name: 'due_date', editable: true }
        ],
        canCreate: true,
        canDelete: true
      }"
      query=""
    />
    <TaskGanttView
      v-else
      :projection="fixture.model"
      :tasks="tasks"
      active="sthpw/task?id=2"
      :selected="[]"
      :collapsed="[]"
    />
  </main>
</template>
<style>
html,
body,
#app {
  margin: 0;
  padding: 0;
}
#schedule-fixture {
  position: relative;
  overflow: hidden;
  background: var(--page);
}
</style>
