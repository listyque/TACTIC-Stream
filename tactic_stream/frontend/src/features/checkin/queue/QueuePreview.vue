<script setup>
import ItemPreview from '../../../controls/ItemPreview.vue';
defineProps({ frameNode: Object, files: Object });
</script>
<template>
  <ItemPreview
    :file="files[frameNode.sourceKey]"
    :fallback-text="frameNode.initials"
    :fallback-icon="frameNode.icon"
    :preview-size="frameNode.width"
    :accent="frameNode.accent"
    :round="false"
    :outlined="false"
    :style="{ borderRadius: frameNode.radius + 'px' }"
  />
</template>
