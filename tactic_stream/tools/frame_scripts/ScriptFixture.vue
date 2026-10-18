<script setup>
import { computed, reactive, ref } from 'vue';
import {
  appearance,
  hostedPalette,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import ScriptEditorWorkspace from '../../frontend/src/features/scripts/ScriptEditorWorkspace.vue';
import ScriptSource from '../../frontend/src/features/scripts/ScriptSource.vue';
import ScriptShelfEditor from '../../frontend/src/features/scripts/ScriptShelfEditor.vue';
import ScriptShelfBar from '../../frontend/src/features/scripts/ScriptShelfBar.vue';
import WorkspaceTabs from '../../frontend/src/controls/WorkspaceTabs.vue';
import AppSearchField from '../../frontend/src/controls/AppSearchField.vue';
import '../../frontend/src/features/scripts/scriptEditor.css';
import '../../frontend/src/features/scripts/scriptShelf.css';
const record = reactive({
  screen: 'shelf',
  model: {},
  buttons: [],
  presets: [],
  scripts: [],
  width: 900,
  height: 650
});
const source = ref(''),
  font = ref(9.25);
const model = computed(() => ({ ...record.model, native: false }));
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
window.scriptFrame = {
  configure(value) {
    Object.assign(record, structuredClone(value));
    source.value = value.model?.source || '';
    Object.assign(appearance, {
      mode: value.dark ? 'dark' : 'light',
      theme: value.style || 'md3',
      language: value.language
    });
  },
  events: []
};
function event(action) {
  window.scriptFrame.events.push(action);
}
</script>
<template>
  <main
    id="script-frame"
    :style="{ width: record.width + 'px', height: record.height + 'px' }"
  >
    <ScriptShelfEditor
      v-if="record.screen === 'shelf'"
      :model="model"
      :buttons="record.buttons"
      :presets="record.presets"
      :scripts="record.scripts"
      @event="event"
    />
    <ScriptShelfBar
      v-else-if="record.screen === 'bar'"
      style="width: 100%"
      :mode="model.mode"
      :buttons="record.buttons"
      :busy="model.busy"
      :running="model.running ? 'fixture' : ''"
      :error="model.error"
      @edit="event({ type: 'edit' })"
    />
    <ScriptEditorWorkspace v-else :model="model" @event="event">
      <template #tabs
        ><WorkspaceTabs
          kind="script"
          :tabs="[{ id: 'fixture', title: model.title, dirty: true }]"
          selected="fixture"
      /></template>
      <template #source
        ><ScriptSource
          v-model="source"
          v-model:font-size="font"
          language="python"
          buffer-key="fixture"
          :read-only="!model.editable"
          :disabled="model.busy"
      /></template>
      <template #output>
        <pre>{{ model.output }}</pre>
      </template>
      <template #tree
        ><AppSearchField label="Search scripts" placeholder="Search scripts"
      /></template>
    </ScriptEditorWorkspace>
  </main>
</template>
<style>
#script-frame {
  position: relative;
  display: flex;
  margin: 0;
  padding: 0;
  background: var(--page);
}
body {
  margin: 0;
}
</style>
