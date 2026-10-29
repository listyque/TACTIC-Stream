<script setup>
import { computed, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppMenu from '../../controls/AppMenu.vue';
import ActionRows from '../../controls/ActionRows.vue';
import {
  button,
  rect
} from '../../../../src/tactic_stream/shared_ui/core/frame.mjs';
const props = defineProps({ frameNode: { type: Object, required: true } });
const menu = ref(null),
  anchor = ref(null);
const trigger = computed(() => ({
  nodes: [
    button(
      'pageEditorToolsButton',
      rect(0, 0, props.frameNode.width, props.frameNode.height),
      props.frameNode.label,
      'more',
      { type: 'menu' },
      true
    )
  ]
}));
function toggle(_action, source) {
  anchor.value = source;
  if (menu.value.open) menu.value.close(true);
  else {
    const bounds = source.getBoundingClientRect();
    menu.value.openAt({
      clientX: bounds.left,
      clientY: bounds.bottom,
      target: source
    });
  }
}
defineEmits(['command']);
</script>
<template>
  <div>
    <FrameView :scene="trigger" @event="toggle" />
    <AppMenu
      ref="menu"
      :anchor="anchor"
      :label="frameNode.label"
      external-trigger
      overlay
    >
      <ActionRows
        :actions="frameNode.actions"
        @triggered="$emit('command', $event)"
      />
    </AppMenu>
  </div>
</template>
