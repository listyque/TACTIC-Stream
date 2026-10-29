<script setup>
import { reactive } from 'vue';
import NestedTable from '../../frontend/src/features/interface/NestedTable.vue';
import '../../frontend/src/style.css';
import gallery from '../../tests/fixtures/frame_table_gallery.json';
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
const original = {
  searchType: 'demo/asset',
  view: 'parent',
  parentKey: 'demo/asset?code=A'
};
const child = {
  searchType: 'demo/asset',
  view: 'child',
  parentKey: 'demo/asset?code=A'
};
const columns = [
  {
    name: 'code',
    title: 'Code',
    width: 160,
    supported: true,
    cell: { kind: 'text', supported: true }
  },
  {
    name: 'expand',
    title: 'Details',
    width: 100,
    supported: true,
    cell: { kind: 'commands', supported: true }
  }
];
const state = reactive({
  scope: original,
  loaded: true,
  columns,
  selected: [],
  rows: [
    {
      key: 'demo/asset?code=A',
      record: { code: 'A', __search_key__: 'demo/asset?code=A' },
      cells: {
        code: { text: 'A' },
        expand: {
          nestedTable: child,
          actions: [
            {
              name: 'nested-table',
              label: 'Show related table',
              icon: 'chevron-right'
            }
          ]
        }
      }
    }
  ]
});
const edits = [];
const actions = [];
window.nestedFixture = {
  state,
  original,
  edits,
  actions,
  gallery(language = 'en') {
    appearance.language = language;
    appearance.mode = 'dark';
    Object.assign(state, structuredClone(gallery));
  },
  summary() {
    state.rows[0].cells.expand = {
      summary: [
        ['sthpw/task', 'Tasks'],
        ['sthpw/snapshot', 'Checkins']
      ].map(([searchType, label]) => ({
        label,
        value: '2',
        icon: 'task',
        nestedTable: {
          searchType,
          view: 'table',
          parentKey: original.parentKey,
          projectCode: 'demo',
          insert: false,
          shelf: false
        }
      }))
    };
  }
};
</script>
<template>
  <NestedTable
    ticket="test-fixture"
    project="demo"
    :state="state"
    style="width: 100%; max-width: 800px"
    @action="(record, kind, cell) => actions.push({ record, kind, cell })"
    @edit="
      (record, target) =>
        edits.push({
          record,
          parentKey: target.scope.parentKey,
          searchType: target.scope.searchType,
          projectCode: target.scope.projectCode || 'demo'
        })
    "
  />
</template>
