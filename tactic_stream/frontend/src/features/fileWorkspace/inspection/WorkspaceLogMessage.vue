<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { observeFrameSizes } from '../../../frame/resize.js';

const props = defineProps({ frameNode: Object });
const emit = defineEmits(['measured']);
const text = ref(null);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) =>
    emit('measured', entries.at(-1).contentRect.height)
  );
  observer.observe(text.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div class="workspace-log-message">
    <div ref="text">{{ frameNode.text }}</div>
  </div>
</template>
<style scoped>
.workspace-log-message > div {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  user-select: text;
  line-height: normal;
}
</style>
