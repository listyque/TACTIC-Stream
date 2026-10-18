<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/controls/forms/people.ui.mjs';
defineProps({ members: Array, login: String });
const emit = defineEmits(['profile']);
const root = ref(null),
  width = ref(278);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    if (entries[0].contentRect.width > 0)
      width.value =
        entries[0].borderBoxSize?.[0]?.inlineSize || root.value.offsetWidth;
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="root" class="messages-member-list">
    <FrameView
      v-for="user in members"
      :key="user.login"
      class="messages-member-frame"
      :scene="
        UI.row(
          { ...user, current: user.login === login },
          Math.max(0, width - 14),
          appearance.language
        )
      "
      @event="(event) => emit('profile', event.login)"
    />
  </div>
</template>
<style>
.messages-member-list {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: auto;
  scrollbar-gutter: stable;
}
.messages-member-frame {
  height: 58px;
  flex: none;
}
</style>
