<script setup>
import { ref, computed, nextTick } from 'vue';
import {
  appearance,
  hostedPalette,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import ObjectLinkSurface from '../../frontend/src/features/objects/ObjectLinkSurface.vue';
import ObjectDuplicateSurface from '../../frontend/src/features/objects/ObjectDuplicateSurface.vue';
import ObjectEditorSurface from '../../frontend/src/features/objects/ObjectEditorSurface.vue';
import ObjectInspectorQuick from '../../frontend/src/features/objects/ObjectInspectorQuick.vue';
import AppTextArea from '../../frontend/src/controls/AppTextArea.vue';
import StatusSelect from '../../frontend/src/controls/StatusSelect.vue';
import * as Inspector from '../../src/tactic_stream/shared_ui/features/objects/inspector.ui.mjs';
import NoteBody from '../../frontend/src/features/objects/NoteBody.vue';
import * as Note from '../../src/tactic_stream/shared_ui/features/objects/note.ui.mjs';
import DescriptionSurface from '../../frontend/src/features/objects/DescriptionSurface.vue';
import SnapshotSummary from '../../frontend/src/features/objects/SnapshotSummary.vue';
import SnapshotToolbar from '../../frontend/src/features/objects/SnapshotToolbar.vue';
import ObjectFieldFrame from '../../frontend/src/features/objects/ObjectFieldFrame.vue';
import ObjectReportSurface from '../../frontend/src/features/objects/ObjectReportSurface.vue';
import ObjectDeleteSurface from '../../frontend/src/features/objects/ObjectDeleteSurface.vue';
import AppMenu from '../../frontend/src/controls/AppMenu.vue';
import ActionRows from '../../frontend/src/controls/ActionRows.vue';
import FrameView from '../../frontend/src/frame/FrameView.vue';
import { linkifyPlainText } from '../../frontend/src/controls/richText.js';
import * as Snapshot from '../../src/tactic_stream/shared_ui/features/objects/snapshot.ui.mjs';
import * as Watch from '../../src/tactic_stream/shared_ui/features/objects/watch.ui.mjs';
const fixture = ref(null),
  events = ref([]),
  model = ref({});
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
const repos = [
  { value: 'main', label: 'Main repository' },
  { value: 'backup', label: 'Backup repository' }
];
const watchModel = computed(() => ({
  ...model.value,
  available: Watch.available(
    repos,
    model.value.selected || [],
    appearance.language
  ),
  choice: 'main',
  selectedCount: (model.value.selected || []).length
}));
const selectedRepos = computed(() =>
  repos.filter((row) => (model.value.selected || []).includes(row.value))
);
window.objectsFixture = {
  async show(value) {
    fixture.value = value;
    model.value = { ...value.model };
    events.value = [];
    Object.assign(appearance, {
      theme: value.style,
      mode: value.dark ? 'dark' : 'light',
      language: value.language
    });
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
    id="objects-fixture"
    :style="{ width: fixture.width + 'px', height: fixture.height + 'px' }"
  >
    <div v-if="fixture.screen === 'duplicate'" class="duplicate-fixture">
      <ObjectDuplicateSurface
        :model="model"
        part="header"
      /><ObjectDuplicateSurface :model="model" part="tabs" />
      <div class="duplicate-pages">
        <ObjectDuplicateSurface :model="model" />
      </div>
      <ObjectDuplicateSurface :model="model" part="footer" />
    </div>
    <ObjectLinkSurface
      v-else-if="fixture.screen === 'links'"
      :model="model"
      :available="model.available"
      :linked="model.linked"
      :available-selected="[]"
      :linked-selected="[]"
      available-query=""
      linked-query=""
      :total="model.available.length"
    />
    <ObjectEditorSurface
      v-else-if="fixture.screen === 'editor'"
      :model="model"
      :part="model.part"
    />
    <ObjectInspectorQuick
      v-else-if="fixture.screen === 'inspector' && fixture.state === 'quick'"
      :model="model"
    />
    <FrameView
      v-else-if="fixture.screen === 'inspector'"
      :scene="Inspector[model.part](model, fixture.width, appearance.language)"
    />
    <NoteBody
      v-else-if="fixture.screen === 'note' && model.part === 'body'"
      :note="{
        body: model.body,
        entry_type: model.entryType,
        after: model.statusTo
      }"
      :files="model.attachments"
      :previews="{}"
      :status-color="model.statusColor"
    />
    <FrameView
      v-else-if="fixture.screen === 'note'"
      :scene="
        Note[model.part || 'header'](model, fixture.width, appearance.language)
      "
    />
    <section v-else-if="fixture.screen === 'regression'">
      <AppTextArea v-model="model.value" /><StatusSelect
        :value="model.status"
        :options="[
          { value: '', label: '' },
          { value: 'Ready', label: 'Ready' }
        ]"
        @change="model.status = $event"
      />
    </section>
    <DescriptionSurface
      v-else-if="fixture.screen === 'description'"
      :model="model"
      :text="model.value"
      :html="linkifyPlainText(model.value || '')"
      @event="events.push($event)"
      @value="model.value = $event"
    />
    <SnapshotSummary
      v-else-if="fixture.screen === 'summary'"
      :snapshot="model"
      :selected="model.selected"
    />
    <SnapshotToolbar
      v-else-if="fixture.screen === 'toolbar'"
      :model="model"
      @event="events.push($event)"
      ><template #options
        ><AppMenu label="Snapshot Browser options" :width="300" overlay
          ><ActionRows
            :actions="Snapshot.optionActions(model)"
            @triggered="
              events.push({ type: 'option', value: $event })
            " /></AppMenu></template
    ></SnapshotToolbar>
    <ObjectFieldFrame v-else-if="fixture.screen === 'field'" :model="model" />
    <ObjectReportSurface
      v-else-if="fixture.screen === 'report'"
      :model="model"
      :part="fixture.state === 'header' ? 'header' : 'page'"
      @event="events.push($event)"
    />
    <ObjectDeleteSurface
      v-else-if="fixture.screen === 'delete'"
      :model="model"
      @event="events.push($event)"
    />
    <FrameView
      v-else
      :scene="
        Watch.describe(
          watchModel,
          fixture.width,
          fixture.height,
          appearance.language
        )
      "
      :models="{ repositories: selectedRepos }"
      :describe-row="
        (list, row) =>
          Watch.repositoryRow(
            watchModel,
            row,
            list.width - 16,
            appearance.language
          )
      "
      @event="events.push($event)"
    />
  </main>
</template>
<style>
html,
body,
#app {
  margin: 0;
  min-width: 0;
}
#objects-fixture {
  display: flex;
  background: var(--page);
  color: var(--on-surface);
}
#objects-fixture > * {
  width: 100%;
}
.duplicate-fixture {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  background: var(--workspace);
}
.duplicate-fixture > .duplicate-pages {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 6px 10px 10px 6px;
  scrollbar-gutter: stable;
}
</style>
