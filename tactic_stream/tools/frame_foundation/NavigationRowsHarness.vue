<script setup>
import { reactive } from 'vue';
import NavigationRow from '../../frontend/src/controls/NavigationRow.vue';
const state = reactive({ width: 320, selected: true, depth: 0 });
window.navigationCase = state;
const records = [
  { kind: 'section', title: 'Assets', expanded: true },
  { kind: 'link', title: 'Sample asset', icon: 'cube', badge: 7 },
  { kind: 'separator' },
  {
    kind: 'link',
    title: 'Long navigation title for an example object',
    icon: 'folder',
    badge: 120
  }
];
</script>
<template>
  <div
    id="navigation-capture"
    :style="{ width: state.width + 'px', height: '176px' }"
  >
    <NavigationRow
      v-for="(record, index) in records"
      :key="index"
      :record="{ ...record, depth: state.depth }"
      :selected="state.selected && index === 1"
    />
  </div>
</template>
