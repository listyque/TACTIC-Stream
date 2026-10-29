<script setup>
import { ref } from 'vue';
import AdminProjectPicker from '../../frontend/src/features/administration/AdminProjectPicker.vue';
import {
  appearance,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import fixture from './project_picker.json';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
const params = new URLSearchParams(location.search);
appearance.language = params.get('language') || 'en';
appearance.mode = params.get('mode') || 'dark';
appearance.popupAnimations =
  appearance.hoverAnimations =
  appearance.clickAnimations =
    false;
initializeAppearance();
const model = ref(structuredClone(fixture));
window.projectPickerHarness = { model, appearance };
</script>
<template>
  <AdminProjectPicker
    :model="model"
    style="
      position: absolute;
      left: 20px;
      top: 100px;
      width: 226px;
      height: 38px;
    "
    @selected="model.project = $event"
  />
</template>
