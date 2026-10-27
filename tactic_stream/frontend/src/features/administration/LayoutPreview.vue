<script setup>
import { asyncComponent } from '../../controls/asyncComponent.js';
const ResultPresentation = asyncComponent(
  () => import('../workspace/ResultPresentation.vue')
);
import { t } from '../../i18n.js';
defineProps({
  layout: Object,
  rows: Array,
  ticket: String,
  project: String,
  searchType: String,
  selectedElement: String,
  error: String
});
defineEmits(['element']);
</script>
<template>
  <div class="layout-live-preview table-container">
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <ResultPresentation
      v-if="layout"
      :rows="rows"
      :ticket="ticket"
      :project="project"
      :search-type="searchType"
      :workspace-id="'layout-preview-' + searchType"
      :item-layout="layout"
      :mode="layout.collection === 'grid' ? 'tiles' : 'continious'"
      group-mode="none"
      :selected-keys="[]"
      :state="{}"
      active
      read-only
      editing
      :selected-element="selectedElement"
      @element="$emit('element', $event)"
    />
    <p v-else class="muted">{{ t('Loading interface...') }}</p>
  </div>
</template>
<style>
.layout-live-preview {
  height: 100%;
  overflow: auto;
  scrollbar-gutter: stable;
  padding: 4px;
}
</style>
