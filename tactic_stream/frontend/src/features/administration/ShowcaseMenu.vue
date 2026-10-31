<script setup>
import { ref, watch } from 'vue';
import AppMenu from '../../controls/AppMenu.vue';
import ActionRow from '../../controls/ActionRow.vue';
import AppButton from '../../controls/AppButton.vue';
const props = defineProps({ frameNode: { type: Object, required: true } });
const emit = defineEmits(['event']);
const menu = ref(null);
const trigger = ref(null);
function open(event, below) {
  if (!props.frameNode.enabled) return;
  const bounds = trigger.value.$el.getBoundingClientRect();
  menu.value?.openAt(
    below
      ? {
          clientX: bounds.left,
          clientY: bounds.bottom,
          target: trigger.value.$el
        }
      : event
  );
}
function choose(command) {
  menu.value?.close(true);
  emit('event', { ...props.frameNode.action, value: command });
}
watch(
  () => props.frameNode.enabled,
  (enabled) => {
    if (!enabled) menu.value?.close(true);
  }
);
</script>
<template>
  <div>
    <AppButton
      ref="trigger"
      :label="frameNode.text"
      :translate-label="false"
      :disabled="!frameNode.enabled"
      style="width: 100%; height: 100%"
      @click="open($event, true)"
      @contextmenu.prevent="open($event, false)"
    />
    <AppMenu
      ref="menu"
      :label="frameNode.text"
      external-trigger
      :anchor="trigger?.$el"
      overlay
      frame-composition
      :disabled="!frameNode.enabled"
    >
      <template v-for="(record, index) in frameNode.actions" :key="index">
        <AppMenu
          v-if="record.children"
          :label="record.title"
          show-label
          submenu
          overlay
          frame-composition
        >
          <ActionRow
            v-for="child in record.children"
            :key="child.command"
            :record="child"
            @triggered="choose(child.command)"
          />
        </AppMenu>
        <ActionRow
          v-else
          :record="record"
          @triggered="choose(record.command)"
        />
      </template>
    </AppMenu>
  </div>
</template>
