<script setup>
import { ref } from 'vue';
import SystemInfo from '../../frontend/src/features/debug/SystemInfo.vue';
import AppButton from '../../frontend/src/controls/AppButton.vue';
import { appearance } from '../../frontend/src/appearance.js';
const info = ref(null),
  ticket = ref('fixture');
window.systemInfoHarness = {
  language: (value) => {
    appearance.language = value;
  },
  signOut: () => {
    ticket.value = '';
  }
};
</script>
<template>
  <AppButton label="System Info" @click="info.open()" />
  <SystemInfo ref="info" :ticket="ticket" project="one" />
</template>
