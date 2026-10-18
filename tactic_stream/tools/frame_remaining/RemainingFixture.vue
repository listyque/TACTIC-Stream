<script setup>
import { computed, reactive, ref, nextTick } from 'vue';
import FrameView from '../../frontend/src/frame/FrameView.vue';
import ApiDocumentation from '../../frontend/src/features/documentation/ApiDocumentation.vue';
import JournalDetails from '../../frontend/src/features/journal/JournalDetails.vue';
import TimeEntryPanel from '../../frontend/src/features/objects/TimeEntryPanel.vue';
import InitializationState from '../../frontend/src/features/collaboration/InitializationState.vue';
import KnowledgeBase from '../../frontend/src/features/knowledge/KnowledgeBase.vue';
import {
  appearance,
  hostedPalette,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import * as Commands from '../../src/tactic_stream/shared_ui/features/knowledge/commands.ui.mjs';
import * as Formatting from '../../src/tactic_stream/shared_ui/features/knowledge/format.ui.mjs';
import * as Navigation from '../../src/tactic_stream/shared_ui/features/knowledge/navigation.ui.mjs';
import * as Sheet from '../../src/tactic_stream/shared_ui/features/workhours/sheet.ui.mjs';
import * as Reports from '../../src/tactic_stream/shared_ui/features/workhours/reports.ui.mjs';
import * as Collaboration from '../../src/tactic_stream/shared_ui/features/support/collaboration/initialization.ui.mjs';
const data = reactive({
  screen: 'editor',
  model: { kind: 'article' },
  width: 900,
  height: 500,
  language: 'en'
});
Object.assign(appearance, {
  mode: 'dark',
  theme: 'md3',
  language: 'en',
  clickAnimations: false,
  hoverAnimations: false,
  popupAnimations: false,
  fadeAnimations: false
});
hostedPalette.value = {
  dark: '#78a6c4',
  darkBase: '#292d30',
  light: '#3d7599',
  lightBase: '#d4dce1'
};
initializeAppearance();
const events = [];
const time = ref(null),
  timeSelected = ref([]);
window.frameEvents = events;
window.fixture = {
  async load(value) {
    Object.assign(data, value);
    Object.assign(appearance, {
      mode: value.dark ? 'dark' : 'light',
      theme: value.style,
      language: value.language
    });
    await nextTick();
  },
  openTime() {
    time.value.open();
  },
  data
};
const scene = computed(() =>
  data.screen === 'editor'
    ? Commands.editor(data.model, data.width, data.language)
    : data.screen === 'viewer'
      ? Commands.viewer(data.model, data.width, data.language)
      : data.screen === 'format'
        ? Formatting.describe(data.model, data.width, data.language)
        : data.screen === 'navigation'
          ? Navigation.row(data.model, true, '', data.width, data.language)
          : data.screen === 'entry'
            ? Sheet.entry(data.model, data.width, data.language)
            : data.screen === 'hourEditor'
              ? Sheet.editor(data.model, data.width, data.language)
              : data.screen === 'summary'
                ? Sheet.summary(data.model, data.width, data.language)
                : data.screen === 'reports'
                  ? Reports.describe(
                      data.model,
                      data.width,
                      data.height,
                      data.language
                    )
                  : data.screen === 'initializeState'
                    ? Collaboration.state(
                        data.model,
                        data.width,
                        data.height,
                        data.language
                      )
                    : data.screen === 'initializeConfirm'
                      ? Collaboration.confirmation(
                          data.model,
                          data.width,
                          data.height,
                          data.language
                        )
                      : Reports.valueRow(data.model, data.width, data.language)
);
</script>
<template>
  <main
    :style="{
      position: 'relative',
      width: data.width + 'px',
      height: data.height + 'px'
    }"
  >
    <ApiDocumentation v-if="data.screen === 'api'" />
    <JournalDetails
      v-else-if="data.screen === 'journal'"
      ticket="fixture"
      project="private"
      :search-key="data.model.searchKey"
    />
    <KnowledgeBase
      v-else-if="data.screen === 'knowledge'"
      ticket="fixture"
      :project="data.model.project"
      login="robin"
      active
    />
    <InitializationState
      v-else-if="data.screen === 'initialization'"
      title="Knowledge Base is not initialized"
      message="Initialize the collaboration schema before writing project documentation."
      icon="file"
      :project="data.model.project || 'demo'"
      :can-initialize="data.model.canInitialize"
      @initialize="events.push({ type: 'initialize' })"
    />
    <template v-else-if="data.screen === 'time'">
      <div id="time-entry-target" style="height: 100%; overflow: auto" />
      <TimeEntryPanel
        ref="time"
        dock-target="#time-entry-target"
        :data="data.model.result"
        :users="data.model.users"
        :draft="data.model.draft"
        :editing="!!data.model.draft"
        :mode="data.model.mode || 'week'"
        week="2026-10-12"
        login="robin"
        :selected="timeSelected"
        report="my_hours"
        can-create
        @create="
          data.model.draft = {
            day: '2026-10-14',
            hours: '',
            category: 'regular',
            login: 'robin',
            description: ''
          }
        "
        @change="(field, value) => (data.model.draft[field] = value)"
        @select="
          (key, value) =>
            (timeSelected = value
              ? [...timeSelected, key]
              : timeSelected.filter((id) => id !== key))
        "
        @scope="(field, value) => (data.model[field] = value)"
        @cancel-edit="data.model.draft = null"
        @save="
          (approve) =>
            events.push({
              type: 'saveHour',
              approve,
              draft: { ...data.model.draft }
            })
        "
      />
    </template>
    <FrameView
      v-else
      :scene="scene"
      :models="{
        reports: data.model.options || [],
        values: data.model.values || []
      }"
      :describe-row="
        (list, record) =>
          list.source === 'reports'
            ? Reports.descriptor(
                record,
                data.model,
                Math.max(0, list.width - 16),
                data.language
              )
            : Reports.valueRow(
                record,
                Math.max(0, list.width - 16),
                data.language
              )
      "
      @event="(action) => events.push(action)"
    />
  </main>
</template>
