<script setup>
import CompletionCell from './CompletionCell.vue';
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import { completionGroups } from '../../../../src/tactic_stream/shared_ui/features/table/cells.ui.mjs';
const props = defineProps({ groups: Array });
const host = ref(null),
  size = ref({ width: 160, height: 58 });
const layout = computed(() =>
  completionGroups(
    props.groups?.length || 0,
    size.value.width,
    size.value.height
  )
);
let observer;
onMounted(() => {
  observer = new ResizeObserver(() => {
    const bounds = host.value.getBoundingClientRect();
    size.value = { width: bounds.width, height: bounds.height };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>

<template>
  <div ref="host" class="table-completion-groups">
    <div
      class="table-completion-list"
      :style="{ width: layout.width + 'px', gap: layout.gap + 'px' }"
    >
      <CompletionCell
        v-for="(group, index) in groups"
        :key="index"
        :percent="group.completion"
        :text="group.text"
      />
    </div>
  </div>
</template>

<style scoped>
.table-completion-groups {
  align-self: stretch;
  width: 100%;
  min-height: 0;
  overflow: auto;
}
.table-completion-list {
  display: flex;
  flex-direction: column;
}
.table-completion-groups :deep(.table-completion) {
  min-height: 18px;
  flex-shrink: 0;
}
</style>
