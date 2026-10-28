<script setup>
import AppMenu from '../../controls/AppMenu.vue';
import ActionRows from '../../controls/ActionRows.vue';
defineProps({ frameNode: { type: Object, required: true } });
defineEmits(['command']);
</script>
<template>
  <AppMenu
    :label="frameNode.label"
    icon="more"
    compact-trigger
    overlay
    style="--touch-target: 32px"
  >
    <ActionRows
      :actions="frameNode.actions"
      @triggered="$emit('command', $event)"
    />
  </AppMenu>
</template>
