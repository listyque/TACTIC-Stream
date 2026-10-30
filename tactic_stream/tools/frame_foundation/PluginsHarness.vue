<script setup>
import { ref } from 'vue';
import Plugins from '../../frontend/src/features/administration/Plugins.vue';
import { appearance } from '../../frontend/src/appearance.js';
const editor = ref(null),
  ticket = ref('fixture'),
  project = ref('one');
window.pluginsHarness = {
  language: (value) => {
    appearance.language = value;
  },
  project: (value) => {
    project.value = value;
  },
  signOut: () => {
    ticket.value = '';
  },
  editor: () => editor.value
};
</script>
<template>
  <Plugins ref="editor" :ticket="ticket" :project="project" />
</template>
<style>
html,
body,
#app {
  margin: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
.plugins-frame {
  height: 100%;
}
.plugins-frame > .frame-toolbar-host {
  height: 40px;
  min-height: 40px;
}
.plugins-frame > .frame-host-body {
  flex: 1;
}
</style>
