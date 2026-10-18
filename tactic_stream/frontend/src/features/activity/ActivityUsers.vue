<script setup>
import { ref, h, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import UserPicker from '../../controls/UserPicker.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/activity/feed.ui.mjs';
const props = defineProps({ modelValue: Array, users: Array, login: String });
const emit = defineEmits(['update:modelValue', 'clear', 'cancel', 'apply']);
const root = ref(null),
  width = ref(368),
  height = ref(488);
let observer;
const port = {
  setup(_, { attrs }) {
    return () =>
      h(UserPicker, {
        ...attrs,
        users: props.users,
        currentLogin: props.login,
        includeCurrent: true,
        modelValue: props.modelValue,
        'onUpdate:modelValue': (value) => emit('update:modelValue', value)
      });
  }
};
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const size = entries[0].contentRect;
    if (size.width > 0) {
      width.value = size.width;
      height.value = size.height;
    }
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div ref="root" class="activity-users-surface">
    <FrameView
      :scene="
        UI.people(
          { count: modelValue.length },
          width,
          height,
          appearance.language
        )
      "
      :views="{ people: { component: port } }"
      @event="(event) => emit(event.type)"
    />
  </div>
</template>
<style>
.activity-user-menu > .account-panel {
  display: flex;
  flex-direction: column;
  padding: 14px;
  width: min(396px, calc(100dvw - 24px));
  height: min(516px, calc(100dvh - 48px));
  gap: 0;
}
.activity-users-surface {
  position: relative;
  flex: 1;
  min-height: 0;
  min-width: 0;
}
.activity-users-surface > .frame-view {
  height: 100%;
}
</style>
