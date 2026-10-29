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
const lastColumn = new URLSearchParams(location.search).has('last-column');
if (lastColumn) document.getElementById('app').style.width = '424px';
const columns = ref([
  {
    name: 'code',
    title: 'Code',
    width: lastColumn ? 160 : 180,
    kind: 'text',
    supported: true,
    sortable: true,
    sortField: 'code'
  },
  {
    name: lastColumn ? 'notes' : 'name',
    title: lastColumn ? 'Notes' : 'Asset name',
    width: lastColumn ? 160 : 220,
    hideOrder: lastColumn ? 1 : 0,
    kind: 'text',
    supported: true,
    sortable: true,
    sortField: 'name'
  }
]);
function resize(name, width) {
  events.push({ type: 'width', name, width });
  columns.value = columns.value.map((column) =>
    column.name === name ? { ...column, width } : column
  );
}
const groups = [
  {
    key: 'all',
    label: '',
    records: (lastColumn ? [0] : [0, 1, 2]).map((n) => ({
      __search_key__: 'demo/asset?code=A' + n,
      code: 'A' + n,
      name: 'Workshop'
    }))
  }
];
window.headerFixture = {
  columns,
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
    @width="resize"
    @state="(value) => (state = value)"
    ><template #cell="{ record, column }">{{
      record[column.name]
    }}</template></TableView
  >
</template>
