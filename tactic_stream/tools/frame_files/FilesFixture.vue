<script setup>
import { ref, nextTick, provide } from 'vue';
import {
  appearance,
  hostedPalette,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import MatchingTemplates from '../../frontend/src/features/checkin/MatchingTemplates.vue';
import IngestFiles from '../../frontend/src/features/checkin/IngestFiles.vue';
import DropPlate from '../../frontend/src/features/checkin/DropPlate.vue';
import CommitQueue from '../../frontend/src/features/checkin/CommitQueue.vue';
import ObjectCheckin from '../../frontend/src/features/checkin/ObjectCheckin.vue';
import WorkspaceInspectorView from '../../frontend/src/features/fileWorkspace/inspection/WorkspaceInspectorView.vue';
import FileWorkspaceDepots from '../../frontend/src/features/fileWorkspace/FileWorkspaceDepots.vue';
import FileWorkspaceStorage from '../../frontend/src/features/fileWorkspace/FileWorkspaceStorage.vue';
import { preferences } from '../../frontend/src/features/configuration/preferences.js';
const fixture = ref(null),
  session = ref({ login: 'fixture', ticket: 'fixture' }),
  ingest = ref(null),
  queue = ref(null),
  objectCheckin = ref(null),
  events = ref([]);
provide('queueCheckin', (value) => events.value.push({ type: 'queue', value }));
provide('openScriptEditor', (value) =>
  events.value.push({ type: 'script', value })
);
hostedPalette.value = {
  dark: '#78a6c4',
  darkBase: '#292d30',
  light: '#3d7599',
  lightBase: '#d4dce1'
};
initializeAppearance();
window.filesFixture = {
  async show(value) {
    fixture.value = null;
    await nextTick();
    session.value = { login: 'fixture', ticket: 'fixture' };
    if (value.screen.startsWith('queue'))
      localStorage.removeItem('tactic_stream.commit_queue.fixture');
    Object.assign(appearance, {
      theme: value.style,
      mode: value.dark ? 'dark' : 'light',
      language: value.language,
      clickAnimations: false,
      hoverAnimations: false,
      fadeAnimations: false,
      popupAnimations: false
    });
    fixture.value = value;
    if (value.screen.startsWith('drop-plate'))
      Object.assign(preferences.checkin, {
        groupCheckin: false,
        keepFilename: false,
        includeSubfolders: false
      });
    events.value = [];
    await nextTick();
    if (value.screen === 'object-checkin')
      await objectCheckin.value.open(
        value.options?.append
          ? { code: 'S7', version: 7, __search_key__: 'sthpw/snapshot?code=S7' }
          : { name: 'Hero Robot', __search_key__: 'cg/asset?code=ROBOT001' },
        value.options || {}
      );
    if (value.screen.startsWith('queue')) {
      preferences.checkin.commitQueueAutoClean = false;
      for (const row of value.model.queue || []) {
        const files = row.files.map((path) => {
          const file = new File(['queue input'], path.split('/').at(-1));
          Object.defineProperty(file, 'webkitRelativePath', { value: path });
          return file;
        });
        queue.value.enqueue({
          ...row,
          ticket: 'fixture',
          project: 'cg',
          searchKey: 'cg/asset?code=ROBOT001',
          files
        });
      }
      await queue.value.validateAll();
      if (queue.value.jobs[0])
        await queue.value.select(queue.value.jobs[0], false);
      queue.value.advanced = value.screen === 'queue-advanced';
      queue.value.mobileDetails =
        value.screen === 'queue-advanced' && value.width < 700;
      await nextTick();
    }
    if (value.screen.startsWith('ingest')) {
      await ingest.value.open(
        {
          name: value.model.ingest.parentTitle,
          __search_key__: 'cg/episode?code=EP01'
        },
        {
          title: value.model.ingest.targetTitle,
          search_type: value.model.ingest.searchType
        }
      );
      ingest.value.selectRule(ingest.value.rules[1]);
      ingest.value.files = value.model.ingest.files.map((row, index) => ({
        key: String(index),
        file: new File(['fixture'], row.title),
        status: row.status,
        reason: row.error
      }));
      ingest.value.advanced = value.screen === 'ingest-advanced';
      await nextTick();
      const workspace = document.querySelector('.ingest-workspace');
      workspace.style.width = value.width + 'px';
      workspace.style.height = value.height + 'px';
      workspace.style.flex = 'none';
      const dialog = workspace.closest('dialog');
      dialog.style.maxWidth = 'none';
      dialog.style.maxHeight = 'none';
      dialog.style.width = value.width + 40 + 'px';
      dialog.style.inset = '0 auto auto 0';
      dialog.style.margin = '0';
      dialog.style.transform = 'none';
      await nextTick();
    }
  },
  events: () => events.value,
  ingest: () => ingest.value,
  queue: () => queue.value,
  async session(values) {
    Object.assign(session.value, values);
    await nextTick();
  },
  checkin: () => objectCheckin.value
};
</script>
<template>
  <section
    v-if="fixture"
    id="files-fixture"
    :style="{ width: fixture.width + 'px', height: fixture.height + 'px' }"
  >
    <WorkspaceInspectorView
      v-if="fixture.screen.startsWith('workspace-inspector')"
      v-bind="fixture.model.workspace"
    />
    <FileWorkspaceDepots
      v-else-if="fixture.screen.startsWith('workspace-depots')"
      v-bind="fixture.model.workspace"
    />
    <FileWorkspaceStorage
      v-else-if="fixture.screen === 'workspace-storage'"
      v-bind="fixture.model.workspace"
    />
    <MatchingTemplates
      v-else-if="fixture.screen.startsWith('matching')"
      :scope="{ ticket: 'fixture', project: 'cg' }"
      :items="fixture.model.templates"
      :padding="3"
      :processes="
        fixture.model.processes.map((value) => ({ value, label: value }))
      "
      context="review"
      @save="events.push({ type: 'save', value: $event })"
      @close="events.push({ type: 'close' })"
    />
    <IngestFiles
      v-else-if="fixture.screen.startsWith('ingest')"
      ref="ingest"
      ticket="fixture"
      project="cg"
    />
    <ObjectCheckin
      v-else-if="fixture.screen === 'object-checkin'"
      ref="objectCheckin"
      ticket="fixture"
      project="cg"
    />
    <div v-else-if="fixture.screen.startsWith('queue')" id="dock-commit_queue">
      <CommitQueue
        ref="queue"
        inline
        :ticket="session.ticket"
        project="cg"
        :login="session.login"
        can-administer
      />
    </div>
    <div
      v-else-if="fixture.screen.startsWith('drop-plate')"
      id="dock-drop_plate"
    >
      <DropPlate
        ticket="fixture"
        project="cg"
        :target="{
          project: 'cg',
          searchKey: 'cg/asset?code=ROBOT001',
          title: 'Hero Robot',
          process: 'publish',
          context: 'review'
        }"
      />
    </div>
  </section>
</template>
<style>
html,
body {
  margin: 0;
  background: var(--surface-high);
}
#files-fixture {
  position: relative;
  display: flex;
  overflow: hidden;
}
#dock-drop_plate,
#dock-commit_queue {
  width: 100%;
  height: 100%;
}
</style>
