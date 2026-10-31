<script setup>
import AppIcon from '../AppIcon.vue';
import { t } from '../../i18n.js';
import { controls } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
defineProps({
  title: String,
  description: String,
  icon: String,
  padding: { type: Number, default: controls.editorPanel.padding },
  fillContentHeight: { type: Boolean, default: true }
});
</script>

<template>
  <section
    class="editor-panel"
    :style="{ padding: Math.max(0, padding - 1) + 'px' }"
  >
    <header v-if="title || $slots.actions">
      <AppIcon v-if="icon" :name="icon" />
      <div>
        <strong>{{ t(title) }}</strong>
        <p v-if="description">{{ t(description) }}</p>
      </div>
      <div v-if="$slots.actions" class="editor-panel-actions">
        <slot name="actions" />
      </div>
    </header>
    <div
      class="editor-panel-body"
      :class="{ 'fill-content': fillContentHeight }"
    >
      <slot />
    </div>
  </section>
</template>

<style>
.editor-panel {
  display: flex;
  flex-direction: column;
  gap: var(--editor-panel-spacing);
  min-width: 0;
  border-radius: var(--surface-radius);
  border: 1px solid var(--outline-variant);
  background: var(--surface);
}
.editor-panel > header {
  display: flex;
  align-items: center;
  gap: var(--editor-panel-header-spacing);
  flex: none;
  min-width: 0;
}
.editor-panel > header > .app-icon {
  width: var(--editor-panel-icon-size);
  height: var(--editor-panel-icon-size);
  font-size: var(--editor-panel-icon-size);
  color: var(--primary);
  flex: none;
}
.editor-panel > header > div:not(.editor-panel-actions) {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--editor-panel-text-spacing);
}
.editor-panel header strong {
  font-size: var(--font-body-large-size);
  line-height: var(--font-body-large-line-height);
  font-weight: 600;
  overflow-wrap: anywhere;
}
.editor-panel header p {
  margin: 0;
  font-size: var(--font-secondary-size);
  line-height: var(--font-secondary-line-height);
  color: var(--muted);
  overflow-wrap: anywhere;
}
.editor-panel-actions {
  display: flex;
  align-items: center;
  gap: var(--editor-panel-actions-spacing);
}
.editor-panel-body {
  display: flex;
  flex-direction: column;
  gap: var(--editor-panel-content-spacing);
  min-width: 0;
}
.editor-panel-body.fill-content {
  flex: 1;
}
</style>
