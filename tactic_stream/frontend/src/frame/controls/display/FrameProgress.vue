<script setup>
import AppProgress from '../../../controls/AppProgress.vue';
defineProps({ frameNode: Object });
</script>
<template>
  <AppProgress
    :label="frameNode.label"
    :value="frameNode.indeterminate ? undefined : frameNode.value"
    :min="frameNode.min"
    :max="frameNode.max"
  />
</template>
