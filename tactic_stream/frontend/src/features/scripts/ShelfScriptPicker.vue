<script setup>
import { computed, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { appearance } from '../../appearance.js';
import ScriptPicker from './ScriptPicker.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/scripts/shelf.ui.mjs';
const props = defineProps({ frameNode: Object, scripts: Array });
const emit = defineEmits(['pick']);
const anchor = ref(null),
  picker = ref(null);
const trigger = computed(() => anchor.value?.querySelector('button') || null);
const scene = computed(() =>
  UI.scriptPicker(props.frameNode, appearance.language)
);
</script>
<template>
  <div ref="anchor">
    <FrameView :scene="scene" @event="picker.open()" />
    <ScriptPicker
      ref="picker"
      :anchor="trigger"
      :scripts="scripts"
      :model-value="frameNode.record.script"
      :scope-key="
        JSON.stringify([frameNode.scopeKey, frameNode.record.buttonId])
      "
      :disabled="!frameNode.enabled"
      @update:model-value="
        emit('pick', {
          type: 'button',
          buttonId: props.frameNode.record.buttonId,
          scopeKey: props.frameNode.scopeKey,
          field: 'script',
          value: $event
        })
      "
    />
  </div>
</template>
