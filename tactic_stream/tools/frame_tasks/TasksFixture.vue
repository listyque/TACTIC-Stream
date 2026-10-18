<script setup>
import { computed, ref, nextTick } from 'vue';
import {
  appearance,
  hostedPalette,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import TaskWorkspaceToolbar from '../../frontend/src/features/tasks/TaskWorkspaceToolbar.vue';
import TaskWorkspaceTable from '../../frontend/src/features/tasks/TaskWorkspaceTable.vue';
import TaskWorkspaceFooter from '../../frontend/src/features/tasks/TaskWorkspaceFooter.vue';
import TaskWorkspacePart from '../../frontend/src/features/tasks/TaskWorkspacePart.vue';
import TaskProcessToolbar from '../../frontend/src/features/tasks/TaskProcessToolbar.vue';
import TaskProcessPanel from '../../frontend/src/features/tasks/TaskProcessPanel.vue';
import TaskBulkBar from '../../frontend/src/features/tasks/TaskBulkBar.vue';
import TaskEmptyState from '../../frontend/src/features/tasks/TaskEmptyState.vue';
import { t } from '../../frontend/src/i18n.js';
import * as Bulk from '../../src/tactic_stream/shared_ui/features/tasks/bulk.ui.mjs';
const fixture = ref(null),
  model = ref({}),
  events = ref([]);
Object.assign(appearance, {
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
const quick = computed(() =>
  ['cards', 'compact'].includes(fixture.value?.screen)
);
const form = computed(() =>
  Bulk.prepare(
    model.value.checked.map((key) => {
      const editor = model.value.editors[key];
      return {
        task: editor.values,
        fields: editor.fields,
        statusChoices: editor.statusChoices,
        statuses: editor.statuses,
        users: editor.users,
        catalog: editor.catalog
      };
    })
  )
);
window.tasksFixture = {
  async show(value) {
    fixture.value = value;
    model.value = structuredClone(value.model);
    events.value = [];
    Object.assign(appearance, {
      theme: value.style,
      mode: value.dark ? 'dark' : 'light',
      language: value.language
    });
    model.value.toolbar.scopeLabel = t('Selected').toUpperCase();
    await nextTick();
    await document.fonts.ready;
    await new Promise((resolve) =>
      requestAnimationFrame(() => requestAnimationFrame(resolve))
    );
  },
  events,
  model
};
</script>
<template>
  <main
    v-if="fixture"
    id="tasks-fixture"
    :style="{ width: fixture.width + 'px', height: fixture.height + 'px' }"
  >
    <template v-if="quick">
      <TaskProcessToolbar
        :model="{
          title: model.title,
          surface: fixture.screen,
          dirty: !!model.processDirty,
          busy: false,
          hasTarget: true
        }"
        @event="events.push($event)"
      />
      <div class="task-fixture-processes">
        <TaskProcessPanel
          :records="model.processes"
          :mode="fixture.screen"
          :target="{ title: model.title }"
          :blocked="false"
        />
      </div>
      <TaskWorkspaceFooter
        class="task-manager-footer"
        :model="{
          quick: true,
          processes: model.processes.length,
          dirty: model.processDirty,
          busy: false
        }"
      />
    </template>
    <template v-else>
      <TaskWorkspaceToolbar
        class="task-manager-toolbar"
        :model="model.toolbar"
        @event="events.push($event)"
      />
      <section class="task-fixture-table-area">
        <TaskWorkspacePart
          v-if="model.dirty"
          class="task-fixture-pending"
          part="pending"
          :model="{ count: model.dirty }"
        />
        <TaskWorkspaceTable
          v-if="model.tasks.length"
          :groups="model.groups"
          :columns="model.columns"
          :selected="model.checked"
          :collapsed="[]"
          :active="model.active"
          :expanded="fixture.screen === 'expanded' ? ['TASK0001'] : []"
          :editors="model.editors"
          :all-selected="model.checked.length === model.tasks.length"
          :busy="false"
          :blocked="false"
        />
        <TaskEmptyState
          v-else
          :can-create="true"
          :toolbar-width="fixture.width"
        />
      </section>
      <TaskBulkBar
        v-if="model.checked.length"
        :form="form"
        :count="model.checked.length"
        :blocked="false"
        :busy="false"
      />
      <TaskWorkspaceFooter class="task-manager-footer" :model="model.footer" />
    </template>
  </main>
</template>
<style>
body {
  margin: 0;
  display: block;
  padding: 0;
  min-width: 0;
}
#tasks-fixture {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--page);
}
#tasks-fixture > * {
  flex-shrink: 0;
}
.task-fixture-table-area {
  container-type: inline-size;
  position: relative;
  flex: 1;
  min-height: 0;
  margin: 5px 6px 0;
  overflow: auto;
}
.task-fixture-pending {
  position: sticky;
  top: 0;
  height: 0 !important;
  z-index: 80;
}
.task-fixture-processes {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
</style>
