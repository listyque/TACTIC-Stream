<script setup>
import { ref, shallowRef } from 'vue';
import Shell from '../../frontend/src/features/administration/AdministrationShell.vue';
import Workflow from '../../frontend/src/features/administration/WorkflowEditor.vue';
import {
  appearance,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
Object.assign(appearance, {
  language: 'ru',
  mode: 'dark',
  clickAnimations: false,
  hoverAnimations: false,
  fadeAnimations: false,
  popupAnimations: false
});
initializeAppearance();
const shell = ref(null),
  workflow = ref(null),
  model = ref({ section: 'types', project: 'demo', projects: [], drafts: [] }),
  presentation = shallowRef({ mobile: true, library: null });
window.libraryHarness = { shell, workflow, model };
function command(event) {
  if (event.type === 'section')
    model.value = { ...model.value, section: event.value };
}
</script>
<template>
  <Shell
    ref="shell"
    :model="model"
    @command="command"
    @presentation="presentation = $event"
    style="height: 100dvh"
  />
  <Teleport defer to="#administration-pages"
    ><Workflow
      v-if="model.section === 'workflow'"
      ref="workflow"
      ticket="isolated-frame-test"
      project="demo"
      inline
      defer-initial-load
      toolbar-target="#administration-actions"
      :catalog-target="presentation.library"
      :catalog-placement="presentation.mobile ? 'inline' : 'sidebar'"
      style="padding: 0; height: 100%"
  /></Teleport>
</template>
