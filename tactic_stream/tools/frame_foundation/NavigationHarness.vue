<script setup>
import { ref, onMounted } from 'vue';
import NavigationTree from '../../frontend/src/features/workspace/NavigationTree.vue';
const selected = ref('first'),
  query = ref(''),
  activated = ref(0);
const entries = [
  {
    key: 'group',
    kind: 'section',
    title: 'Assets',
    children: [
      {
        key: 'first',
        kind: 'link',
        title: 'First asset',
        supported: true,
        icon: 'link',
        badge: 7
      },
      {
        key: 'second',
        kind: 'link',
        title: 'Second asset',
        supported: true,
        icon: 'folder',
        accent: '#dddd80'
      },
      {
        key: 'missing',
        kind: 'link',
        title: 'Unavailable',
        supported: false,
        icon: 'link'
      }
    ]
  },
  { key: 'separator', kind: 'separator' },
  {
    key: 'last',
    kind: 'link',
    title: 'Last asset',
    supported: true,
    icon: 'cube'
  }
];
onMounted(() => {
  window.navigationHarness = {
    get selected() {
      return selected.value;
    },
    get activated() {
      return activated.value;
    }
  };
});
</script>
<template>
  <div style="width: 320px">
    <input v-model="query" aria-label="Search navigation" /><NavigationTree
      :entries="entries"
      project="fixture"
      :query="query"
      :selected="selected"
      @select="
        selected = $event.key;
        activated++;
      "
    />
  </div>
</template>
