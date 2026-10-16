<script setup>
import { nextTick, onMounted, ref } from 'vue';
import NavigationDrawer from '../../frontend/src/features/workspace/NavigationDrawer.vue';
import NavigationTree from '../../frontend/src/features/workspace/NavigationTree.vue';
import AppButton from '../../frontend/src/controls/AppButton.vue';
import { appearance } from '../../frontend/src/appearance.js';
const drawer = ref(null),
  selected = ref('entry0'),
  activated = ref(0),
  edited = ref(0),
  extras = ref(false),
  opened = ref(false),
  editable = ref(true);
const entries = ref([
  {
    key: 'group',
    kind: 'section',
    title: 'Assets',
    children: Array.from({ length: 16 }, (_, i) => ({
      key: 'entry' + i,
      title: 'Asset ' + i,
      kind: 'link',
      supported: true,
      icon: 'cube',
      badge: i === 0 ? 7 : 0
    }))
  }
]);
function open() {
  drawer.value.open(0);
  opened.value = true;
}
onMounted(() => {
  window.drawerHarness = {
    async configure(style, language, width) {
      Object.assign(appearance, {
        theme: style,
        language,
        mode: language === 'en' ? 'dark' : 'light'
      });
      extras.value = false;
      editable.value = true;
      await nextTick();
      open();
      await nextTick();
    },
    close() {
      drawer.value.close(false);
    },
    inputRecords() {
      entries.value[0].children.splice(
        1,
        0,
        {
          key: 'missing',
          kind: 'link',
          title: 'Unavailable',
          supported: false
        },
        { key: 'separator', kind: 'separator' }
      );
      entries.value.push({
        key: 'last',
        kind: 'link',
        title: 'Last asset',
        supported: true,
        icon: 'folder'
      });
    },
    set extras(value) {
      extras.value = value;
    },
    set editable(value) {
      editable.value = value;
    },
    get activated() {
      return activated.value;
    },
    get edited() {
      return edited.value;
    },
    get selected() {
      return selected.value;
    },
    get opened() {
      return opened.value;
    }
  };
});
</script>
<template>
  <AppButton class="drawer-opener" label="Open navigation" @click="open" />
  <NavigationDrawer
    ref="drawer"
    :editable="editable"
    edit-enabled
    @closed="opened = false"
    @edit="edited++"
  >
    <template #extras
      ><div v-if="extras" style="height: 100px">
        Mobile panel controls
      </div></template
    >
    <NavigationTree
      :entries="entries"
      project="fixture"
      :selected="selected"
      @select="
        selected = $event.key;
        activated++;
        drawer.close();
      "
    />
  </NavigationDrawer>
</template>
<style>
body {
  margin: 0;
  background: var(--workspace);
}
.drawer-opener {
  position: absolute;
  right: 20px;
  bottom: 20px;
}
</style>
