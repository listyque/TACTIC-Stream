<script setup>
import AppButton from '../AppButton.vue';
import AppIcon from '../AppIcon.vue';
import ItemSurface from '../ItemSurface.vue';
import SummaryChip from '../SummaryChip.vue';
defineProps({
  text: String,
  description: String,
  icon: String,
  badgeText: String,
  selected: Boolean,
  wrapTitle: Boolean,
  accent: String,
  disabled: Boolean
});
</script>

<template>
  <ItemSurface
    class="editor-list-item-surface"
    :selected="selected"
    :accent="accent"
    :selected-color="'var(--selected)'"
    normal-color="transparent"
    :rail-visible="!!selected"
    :separator-visible="false"
    :inset="0"
  >
    <AppButton
      class="editor-list-item"
      :class="{ selected, 'wrap-title': wrapTitle }"
      :label="text"
      :translate-label="false"
      :aria-description="description"
      :disabled="disabled"
    >
      <AppIcon
        v-if="icon"
        :name="icon"
        :style="{ color: accent || 'var(--primary)' }"
      />
      <span class="editor-list-item-text"
        ><strong>{{ text }}</strong
        ><span v-if="description">{{ description }}</span></span
      >
      <SummaryChip
        v-if="badgeText"
        :label="badgeText"
        :show-dot="false"
        :show-count="false"
      />
    </AppButton>
  </ItemSurface>
</template>

<style>
.editor-list-item-surface {
  min-width: 0;
}
.editor-list-item.app-button:not(.icon-button),
.editor-list-item.app-button:not(.icon-button):hover:not(:disabled) {
  width: 100%;
  min-height: 48px;
  height: 100%;
  padding: var(--editor-list-item-padding);
  gap: var(--editor-list-item-spacing);
  border: 0;
  background: transparent;
  color: var(--on-surface);
  text-align: left;
  border-radius: var(--item-radius);
}
.editor-list-item.app-button > .app-icon {
  width: var(--editor-list-item-icon-size);
  height: var(--editor-list-item-icon-size);
  font-size: var(--editor-list-item-icon-size);
}
.editor-list-item .editor-list-item-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--editor-list-item-text-spacing);
}
.editor-list-item-text > strong {
  font-size: var(--font-body-size);
  line-height: var(--font-body-line-height);
  font-weight: 400;
}
.editor-list-item.selected .editor-list-item-text > strong {
  font-weight: 600;
}
.editor-list-item-text > :not(strong) {
  font-size: var(--font-secondary-size);
  line-height: var(--font-secondary-line-height);
  font-weight: 400;
  color: var(--muted);
}
.editor-list-item-text > * {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.editor-list-item.wrap-title .editor-list-item-text > strong {
  white-space: normal;
}
.editor-list-item .summary-chip {
  flex: none;
}
.editor-list-item:disabled .editor-list-item-text > strong,
.editor-list-item:disabled > .app-icon {
  color: var(--disabled);
}
</style>
