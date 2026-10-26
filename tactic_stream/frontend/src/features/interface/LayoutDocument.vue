<script setup>
import DocumentPane from '../../controls/DocumentPane.vue';
defineProps({ frameNode: Object });
</script>
<template>
  <DocumentPane :document-key="frameNode?.key" :text="frameNode?.text || ''" />
</template>
