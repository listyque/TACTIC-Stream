<script setup>
// Neutral Markdown reader. Its owner supplies content and handles links/file actions.
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import AppIcon from './AppIcon.vue';
import MarkdownText from './MarkdownText.vue';
import { controls } from '../../../src/tactic_stream/shared_ui/core/foundation.mjs';
const documentStyle = Object.fromEntries(
  Object.entries(controls.document).map(([key, value]) => [
    '--document-' + key,
    value + 'px'
  ])
);
const props = defineProps({
  documentKey: String,
  text: String,
  summary: String,
  notice: String,
  error: String,
  scrollOffset: { type: Number, default: 0 },
  presented: { type: Boolean, default: true },
  contentInset: { type: Number, default: 14 }
});
const emit = defineEmits(['link', 'scroll']);
const viewport = ref(null),
  article = ref(null);
let observer,
  restoredOffset = null;
async function restore() {
  await nextTick();
  if (!props.presented || !viewport.value?.clientHeight) return;
  viewport.value.scrollTop = Math.max(0, props.scrollOffset);
  restoredOffset = viewport.value.scrollTop;
}
function capture() {
  if (!props.presented || !viewport.value?.clientHeight) return;
  const value = viewport.value.scrollTop;
  if (value === restoredOffset) return;
  restoredOffset = null;
  emit('scroll', { id: props.documentKey, value });
}

function focus() {
  article.value?.focus({ preventScroll: true });
}
watch(() => [props.documentKey, props.scrollOffset, props.presented], restore, {
  flush: 'post'
});
onMounted(() => {
  observer = new ResizeObserver(restore);
  observer.observe(article.value);
  restore();
});
onBeforeUnmount(() => {
  capture();
  observer?.disconnect();
});
defineExpose({ capture, focus, restore, viewport });
</script>
<template>
  <div
    ref="viewport"
    class="document-pane"
    :style="{ ...documentStyle, '--document-inset': contentInset + 'px' }"
    @scroll="capture"
  >
    <article ref="article" tabindex="0">
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <p v-if="notice" class="document-notice muted">{{ notice }}</p>
      <div v-if="summary && !error" class="document-summary">
        <AppIcon name="info" /><MarkdownText
          :text="summary"
          @topic="emit('link', $event)"
        />
      </div>
      <MarkdownText
        v-if="!error"
        :text="text || ''"
        @topic="emit('link', $event)"
      />
    </article>
  </div>
</template>
<style>
.document-pane {
  overflow: auto;
  min-width: 0;
  min-height: 0;
  scrollbar-gutter: stable;
}
.document-pane article {
  margin: var(--document-inset, 14px);
  min-width: 0;
}
.document-notice {
  font-size: var(--text-caption);
  margin: 0 0 14px;
}
.document-summary {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  margin-bottom: 14px;
  border: 0;
  box-shadow: inset 0 0 0 1px var(--outline-variant);
  border-radius: var(--item-radius);
  background: var(--surface-high);
}
.document-summary > .app-icon {
  color: var(--primary);
  font-size: 18px;
  flex: none;
}
.document-summary > .markdown-text {
  flex: 1;
  min-width: 0;
}
.document-pane .markdown-text {
  font-size: var(--document-bodySize);
  line-height: var(--document-lineHeight);
}
.document-pane .markdown-text h2 {
  font-size: var(--document-headingSize);
  line-height: var(--document-headingLineHeight);
  margin: var(--document-headingGap) 0 var(--document-paragraphGap);
}
.document-pane .markdown-text table {
  table-layout: fixed;
}
.document-pane .markdown-text th,
.document-pane .markdown-text td {
  padding: var(--document-cellPadding);
}
.document-pane .markdown-text th {
  background: transparent;
  font-weight: 700;
}
</style>
