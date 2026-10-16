<script setup>
import { computed, reactive, ref, onMounted } from 'vue';
import AppMenu from '../../frontend/src/controls/AppMenu.vue';
import ActionRows from '../../frontend/src/controls/ActionRows.vue';
import DockWorkspaceFooter from '../../frontend/src/controls/DockWorkspaceFooter.vue';
import menus from '../../src/tactic_stream/shared_ui/shell/main.menus.json';
import { compose } from '../../src/tactic_stream/shared_ui/shell/main.menus.mjs';
import { appearance } from '../../frontend/src/appearance.js';
const context = reactive({
  platform: 'stream',
  canAdminister: true,
  updateMode: 'poll',
  pollInterval: 30,
  unread: 7
});
const menu = ref(null),
  kind = ref('user'),
  command = ref('');
const actions = computed(() => compose(menus[kind.value], context));
function invoke(value) {
  menu.value.close(true);
  command.value = value;
  if (value.startsWith('update_mode_')) context.updateMode = value.slice(12);
}
onMounted(() => {
  window.menuHarness = { context, kind, command, menu, appearance, actions };
});
</script>
<template>
  <AppMenu
    frame-composition
    ref="menu"
    :label="kind"
    :width="kind === 'connection' ? 330 : 244"
    align-start
    ><ActionRows :actions="actions" @triggered="invoke"
  /></AppMenu>
  <DockWorkspaceFooter class="tested-footer" />
</template>
<style>
.tested-footer {
  position: absolute;
  left: 20px;
  width: 300px;
  bottom: 0;
}
</style>
