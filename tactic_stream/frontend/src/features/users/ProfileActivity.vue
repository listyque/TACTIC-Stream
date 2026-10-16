<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import ActivityEventCard from '../activity/ActivityEventCard.vue';
import { observeFrameSizes } from '../../frame/resize.js';
const props = defineProps({ records: Array, expanded: Boolean });
const emit = defineEmits(['height', 'activity', 'target', 'open-link']);
const content = ref(null);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) =>
    emit('height', entries.at(-1).contentRect.height)
  );
  observer.observe(content.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div class="profile-activity-host">
    <div ref="content" class="profile-activity-cards">
      <ActivityEventCard
        v-for="record in expanded ? records : records.slice(0, 6)"
        :key="record.eventId"
        :record="record"
        @activity="emit('activity', record)"
        @target="emit('target', record)"
        @open-link="emit('open-link', $event)"
      />
    </div>
  </div>
</template>
<style scoped>
.profile-activity-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}
</style>
