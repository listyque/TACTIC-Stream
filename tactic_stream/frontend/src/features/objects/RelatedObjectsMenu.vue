<script setup>
import { computed, ref } from 'vue';
import AppMenu from '../../controls/AppMenu.vue';
import ActionRows from '../../controls/ActionRows.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/related.ui.mjs';
const props = defineProps({ node: Object });
const emit = defineEmits(['choose']);
const menu = ref(null);
const actions = computed(() => {
  const parents = props.node?.related_parents || [];
  const children =
    props.node?.branches?.filter((branch) => branch.kind === 'relation') || [];
  const records = [];
  for (const [kind, branches] of [
    ['parent', parents],
    ['relation', children]
  ]) {
    if (kind === 'relation' && parents.length && children.length)
      records.push({ separator: true });
    branches.forEach((branch, index) =>
      records.push({
        title: branch.title,
        translate: false,
        icon: branch.icon,
        accent: branch.accent,
        accentIcon: true,
        command: kind + ':' + index,
        branch: { ...branch, kind }
      })
    );
  }
  return UI.menuActions(records);
});
function choose(command) {
  const branch = actions.value.find((item) => item.command === command)?.branch;
  menu.value.close(false);
  emit('choose', branch || null);
}
defineExpose({ openAt: (event) => menu.value.openAt(event) });
</script>
<template>
  <AppMenu
    ref="menu"
    label="Related and child objects"
    frame-composition
    external-trigger
    overlay
    :width="260"
    @toggle="node && (node.menuVisible = $event.target.open)"
  >
    <ActionRows :actions="actions" @triggered="choose" />
  </AppMenu>
</template>
