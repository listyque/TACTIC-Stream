<script setup>
defineProps({ target: String });
</script>
<template><div :id="target" class="administration-port" /></template>
<style scoped>
.administration-port {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
</style>
