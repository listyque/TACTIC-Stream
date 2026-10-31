<script setup>
import { computed, ref } from 'vue';
import FrameView from '../../frontend/src/frame/FrameView.vue';
import EditorPanel from '../../frontend/src/controls/layout/EditorPanel.vue';
import SettingRow from '../../frontend/src/controls/SettingRow.vue';
import EditorListItem from '../../frontend/src/controls/lists/EditorListItem.vue';
import AppTextField from '../../frontend/src/controls/AppTextField.vue';
import AppDialog from '../../frontend/src/controls/AppDialog.vue';
import AppButton from '../../frontend/src/controls/AppButton.vue';
import {
  appearance,
  hostedPalette,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import { sections } from '../../src/tactic_stream/shared_ui/controls/forms/sections.ui.mjs';
const fields = ref([]),
  width = ref(800),
  mode = ref('form'),
  dialog = ref(null);
const lastEvent = ref(null);
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
const scene = computed(() =>
  sections(
    fields.value,
    width.value,
    appearance.language,
    true,
    appearance.theme
  )
);
window.spacingFixture = {
  configure(options) {
    fields.value = options.fields;
    width.value = options.width;
    mode.value = options.mode || 'form';
    appearance.theme = options.style || 'md3';
    appearance.mode = options.dark === false ? 'light' : 'dark';
  },
  openDialog() {
    dialog.value.show();
  },
  lastEvent() {
    return lastEvent.value;
  }
};
</script>
<template>
  <main
    :style="{
      width: width + 'px',
      height: '600px',
      background: 'var(--workspace)'
    }"
  >
    <FrameView
      v-if="mode === 'form'"
      :scene="scene"
      @event="lastEvent = $event"
    />
    <EditorPanel
      v-else
      class="spacing-panel"
      title="General"
      description="A shared panel and settings row"
      :fill-content-height="false"
    >
      <SettingRow title="Name" description="Object name"
        ><AppTextField model-value="Robot Arm" style="width: 160px"
      /></SettingRow>
    </EditorPanel>
    <EditorListItem
      v-if="mode === 'panel'"
      text="Robot Arm"
      description="Object name"
      style="position: absolute; left: 12px; right: 12px; top: 200px"
    />
    <AppDialog
      ref="dialog"
      title="Confirmation"
      style="width: 440px; height: 220px"
    >
      <div
        class="spacing-dialog-body"
        style="flex: 1; background: var(--surface)"
      >
        <AppButton label="Apply" @click="dialog.close()" />
      </div>
    </AppDialog>
  </main>
</template>
<style>
body {
  margin: 0;
}
.spacing-panel {
  margin: var(--space-content);
}
</style>
