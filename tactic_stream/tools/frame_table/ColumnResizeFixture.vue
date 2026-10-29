<script setup>
import { onMounted, ref } from 'vue';
import ConfiguredView from '../../frontend/src/features/interface/ConfiguredView.vue';
import {
  initializeAppearance,
  appearance
} from '../../frontend/src/appearance.js';
initializeAppearance();
appearance.language = 'en';
const scene = ref(null),
  editor = ref(null);
onMounted(async () => {
  scene.value = await (await fetch('/column-resize-scene')).json();
});
window.columnResizeFixture = {
  get editor() {
    return editor.value;
  }
};
</script>
<template>
  <ConfiguredView
    v-if="scene"
    ref="editor"
    :definition="scene.definition"
    :rows="scene.rows"
    ticket="fixture"
    project="column_fixture"
    :read-only="false"
  />
</template>
