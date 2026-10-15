<script setup>
import { ref, onMounted } from 'vue';
import DockWorkspace from '../../frontend/src/features/workspace/DockWorkspace.vue';
import {
  defaults,
  captureLayout,
  place
} from '../../frontend/src/features/workspace/docks.js';
const docks = ref(null);
onMounted(() => {
  window.dockHarness = { docks, defaults, captureLayout, place };
});
</script>
<template>
  <DockWorkspace
    ref="docks"
    login="frame-dock-interaction"
    :can-administer="true"
  />
</template>
