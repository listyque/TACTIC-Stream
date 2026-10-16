<script setup>
import { ref } from 'vue';
import ActionRow from './ActionRow.vue';
defineProps({ actions: { type: Array, required: true } });
defineEmits(['triggered']);
const hovered = ref(null);
</script>
<template>
  <div class="action-rows">
    <ActionRow
      v-for="(record, index) in actions"
      :key="record.command || index"
      :record="record"
      :suppress-focus="hovered !== null"
      @pointerenter="
        !record.header &&
        !record.separator &&
        record.enabled !== false &&
        (hovered = index)
      "
      @pointerleave="hovered = null"
      @triggered="$emit('triggered', record.command)"
    />
  </div>
</template>
<style>
.action-rows {
  display: grid;
  gap: 1px;
  min-width: 0;
}
</style>
