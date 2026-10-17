<script setup>
import { ref } from 'vue';
import AppTextArea from '../../controls/AppTextArea.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/description.ui.mjs';
defineProps({ text: String, html: String, model: Object });
const emit = defineEmits(['value', 'link', 'finished']);
const editor = ref(null);
defineExpose({ focus: () => editor.value?.focus() });
</script>
<template>
  <div class="description-value">
    <AppTextArea
      v-if="model.editable"
      ref="editor"
      class="description-value-input"
      :model-value="text"
      :label="model.placeholder"
      :placeholder="model.placeholder"
      :disabled="!model.enabled"
      :error-state="model.outline === 'error'"
      :style="{
        padding: UI.metrics.textPadding + 'px',
        paddingBottom: model.bottomPadding + 'px',
        fontSize: model.fontRole === 'menuHeading' ? '10px' : '11px',
        borderWidth: model.emphasized ? '2px' : '1px',
        borderColor:
          model.emphasized || model.outline === 'error'
            ? `var(${model.outline === 'tertiary' ? '--tertiary' : model.outline === 'error' ? '--error' : '--primary'})`
            : undefined
      }"
      @update:model-value="emit('value', $event)"
      @blur="emit('finished', $event.target.value)"
    />
    <div v-else class="description-value-read" @click="emit('link', $event)">
      <div
        :style="{
          padding: UI.metrics.textPadding + 'px',
          paddingBottom: model.bottomPadding + 'px'
        }"
      >
        <div v-if="text" v-html="html" />
        <span v-else class="muted">{{ model.empty }}</span>
      </div>
    </div>
  </div>
</template>
<style>
.description-value {
  width: 100%;
  height: 100%;
  min-height: 0;
}
.description-value-input.app-text-area,
.description-value-read {
  width: 100%;
  height: 100%;
  min-height: 0;
  resize: none;
  border-radius: var(--surface-radius);
  background: var(--surface-high);
}
.description-value-read {
  overflow: auto;
  border: 1px solid var(--outline);
  font-size: var(--font-body-size);
}
</style>
