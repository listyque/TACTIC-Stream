<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import CustomLayoutView from '../../frontend/src/features/interface/CustomLayoutView.vue';
import {
  appearance,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
initializeAppearance();
appearance.mode = 'dark';
appearance.language =
  new URL(location.href).searchParams.get('language') || 'en';
const size = ref({ width: innerWidth, height: innerHeight });
function resize() {
  size.value = { width: innerWidth, height: innerHeight };
}
onMounted(() => addEventListener('resize', resize));
onBeforeUnmount(() => removeEventListener('resize', resize));
const filters = [
  {
    name: 'status',
    title: 'Status',
    dataType: 'text',
    relation: '=',
    value: '',
    enabled: false
  },
  {
    name: 'amount',
    title: 'Amount',
    dataType: 'numeric',
    relation: '>=',
    value: 0,
    enabled: false
  }
];
const model = ref({
  layoutView: 'dashboard.search',
  targetSearchKey: 'sthpw/project?code=one',
  layoutFilters: filters,
  layoutNodes: [
    { kind: 'metric', text: 'Tasks', value: 13, height: 100, editorPath: [0] }
  ]
});
window.applied = [];
function apply(values) {
  window.applied.push(values);
  model.value = {
    ...model.value,
    layoutFilters: filters.map((field) => ({
      ...field,
      ...values[field.name]
    })),
    layoutNodes: [
      {
        kind: 'metric',
        text: 'Tasks',
        value: values.status?.enabled ? 4 : 13,
        height: 100,
        editorPath: [0]
      }
    ]
  };
}
if (new URL(location.href).searchParams.has('selected'))
  apply({
    status: { enabled: true, value: 'In Progress' },
    amount: { enabled: false, value: 0 }
  });
</script>
<template>
  <CustomLayoutView
    :model="model"
    :width="size.width"
    :height="size.height"
    ticket="fixture-ticket"
    project="one"
    @filter-apply="apply"
  />
</template>
