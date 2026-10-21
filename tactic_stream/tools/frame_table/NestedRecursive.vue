<script setup>
import { reactive } from 'vue';
import NestedTable from '../../frontend/src/features/interface/NestedTable.vue';
import '../../frontend/src/style.css';
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
window.nestedFixture = {
  state,
  original,
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
    style="width: 600px"
  />
</template>
