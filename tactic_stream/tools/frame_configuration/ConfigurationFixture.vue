<script setup>
import { computed, ref } from 'vue';
import FrameView from '../../frontend/src/frame/FrameView.vue';
import {
  appearance,
  hostedPalette,
  initializeAppearance,
  accentPresets
} from '../../frontend/src/appearance.js';
import ImagePicker from '../../frontend/src/controls/ImagePicker.vue';
import AccentPresetPicker from '../../frontend/src/controls/AccentPresetPicker.vue';
import * as Configuration from '../../src/tactic_stream/shared_ui/features/configuration/configuration.ui.mjs';
import * as Settings from '../../src/tactic_stream/shared_ui/features/configuration/settings.ui.mjs';
import * as Projects from '../../src/tactic_stream/shared_ui/features/projects/project.ui.mjs';
import * as Templates from '../../src/tactic_stream/shared_ui/features/projects/templates.ui.mjs';
import * as Catalog from '../../src/tactic_stream/shared_ui/features/projects/catalog.ui.mjs';
import * as Editor from '../../src/tactic_stream/shared_ui/features/projects/editor.ui.mjs';
import * as Repository from '../../src/tactic_stream/shared_ui/features/configuration/repository.ui.mjs';
import * as Server from '../../src/tactic_stream/shared_ui/features/configuration/server.ui.mjs';
const fixture = ref(null);
const imageFile = ref(null);
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
const modules = {
  configuration: Configuration,
  settings: Settings,
  wizard: Projects,
  templates: Templates,
  projects: Catalog,
  editor: Editor,
  repository: Repository,
  server: Server
};
const scene = computed(() => {
  if (!fixture.value) return { nodes: [] };
  const data = fixture.value;
  const result = modules[data.module][data.describe || 'describe'](
    data.model,
    data.width,
    data.height,
    appearance.language
  );
  if (data.child) {
    const bounds = result.pageBounds;
    const child = modules[data.child.module][data.child.describe || 'describe'](
      data.child.model,
      bounds.width,
      bounds.height,
      appearance.language
    );
    for (const node of child.nodes)
      result.nodes.push({
        ...node,
        x: node.x + bounds.x,
        y: node.y + bounds.y
      });
  }
  return result;
});
const views = computed(() => {
  const data = fixture.value,
    model = data?.child?.model || data?.model || {};
  return {
    lightAccent: {
      component: AccentPresetPicker,
      props: {
        options: accentPresets,
        mode: 'light',
        modelValue: model.values?.lightAccent,
        label: 'Light mode palette'
      }
    },
    darkAccent: {
      component: AccentPresetPicker,
      props: {
        options: accentPresets,
        mode: 'dark',
        modelValue: model.values?.darkAccent,
        label: 'Dark mode palette'
      }
    },
    image: {
      component: ImagePicker,
      props: {
        previewSize: 160,
        modelValue: imageFile.value,
        fallbackText:
          data?.module === 'editor'
            ? String(model.values?.code || '')
                .slice(0, 2)
                .toUpperCase()
            : model.draft?.title || '',
        statusText:
          data?.module === 'editor'
            ? model.stagedImage
              ? 'A new preview is ready to be queued'
              : 'Current project preview'
            : '',
        description:
          data?.module === 'editor'
            ? 'Choose a large image; the repository web representation is used automatically when available.'
            : '',
        disabled: model.busy || model.step === 3
      }
    }
  };
});
function row(list, record) {
  const data = fixture.value;
  if (data.module === 'projects')
    return Catalog.row(
      data.model,
      record,
      list.width - 16,
      appearance.language
    );
  if (data.module === 'repository')
    return Repository.row(data.model, record, list.width - 16);
  throw Error('Unexpected Configuration list: ' + list.id);
}
window.frameConfiguration = {
  fixture,
  async set(data) {
    imageFile.value = data.imageData
      ? new File(
          [await (await fetch(data.imageData)).blob()],
          'fixture-preview.png',
          { type: 'image/png' }
        )
      : null;
    appearance.theme = data.style;
    appearance.mode = data.dark ? 'dark' : 'light';
    appearance.language = data.language;
    fixture.value = data;
  }
};
</script>
<template>
  <main
    id="configuration-fixture"
    class="configuration-fixture"
    :style="{
      width: (fixture?.width || 1100) + 'px',
      height: (fixture?.height || 740) + 'px',
      background: fixture?.backgroundColor
    }"
  >
    <FrameView
      :scene="scene"
      :models="fixture?.models || {}"
      :views="views"
      :describe-row="row"
    />
  </main>
</template>
<style>
body {
  margin: 0;
}
.configuration-fixture {
  position: relative;
  background: var(--workspace);
}
</style>
