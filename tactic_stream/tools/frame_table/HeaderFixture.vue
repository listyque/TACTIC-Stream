<script setup>
import { ref, nextTick } from 'vue';
import TableView from '../../frontend/src/features/interface/TableView.vue';
import {
  appearance,
  hostedPalette,
  initializeAppearance
} from '../../frontend/src/appearance.js';
hostedPalette.value = {
  dark: '#78a6c4',
  darkBase: '#292d30',
  light: '#3d7599',
  lightBase: '#d4dce1'
};
Object.assign(appearance, {
  clickAnimations: false,
  hoverAnimations: false,
  fadeAnimations: false,
  popupAnimations: false
});
initializeAppearance();
const grouped = ref(false),
  state = ref({});
const events = [];
const columns = [
  {
    name: 'code',
    title: 'Code',
    width: 180,
    kind: 'text',
    supported: true,
    sortable: true,
    sortField: 'code'
  },
  {
    name: 'name',
    title: 'Asset name',
    width: 220,
    kind: 'text',
    supported: true,
    sortable: true,
    sortField: 'name'
  }
];
const groups = [
  {
    key: 'all',
    label: '',
    records: [0, 1, 2].map((n) => ({
      __search_key__: 'demo/asset?code=A' + n,
      code: 'A' + n,
      name: 'Workshop'
    }))
  }
];
window.headerFixture = {
  events,
  async show(value) {
    grouped.value = value.grouped;
    appearance.mode = value.dark ? 'dark' : 'light';
    appearance.language = 'en';
    appearance.theme = 'md3';
    await nextTick();
    await document.fonts.ready;
  }
};
</script>
<template>
  <TableView
    :columns="columns"
    :groups="groups"
    :selected-keys="[]"
    selectable
    editable
    :state="state"
    :group-mode="grouped ? 'column:code' : 'none'"
    sort-field="name"
    sort-direction="asc"
    @sort="(value) => events.push({ type: 'sort', value })"
    @state="(value) => (state = value)"
    ><template #cell="{ record, column }">{{
      record[column.name]
    }}</template></TableView
  >
</template>
