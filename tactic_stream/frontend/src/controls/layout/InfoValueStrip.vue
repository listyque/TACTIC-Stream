<script setup>
defineProps({
  items: { type: Array, default: () => [] },
  selected: Boolean,
  maximumItems: Number,
  maximumItemWidth: { type: Number, default: 180 },
  separator: { type: String, default: '/' }
});
defineEmits(['link']);
function text(item) {
  return item.text !== undefined
    ? String(item.text || '')
    : [item.label, item.value].filter(Boolean).join(': ');
}
function external(url) {
  return (
    /^(https?:\/\/|ftp:\/\/|mailto:)/i.test(url || '') &&
    !/[\u0000-\u001f]/.test(url)
  );
}
</script>

<template>
  <span class="info-value-strip">
    <template
      v-for="(item, index) in maximumItems > 0
        ? items.slice(0, maximumItems)
        : items"
      :key="index"
    >
      <span v-if="index" class="info-separator">{{ separator }}</span>
      <component
        :is="external(item.url) ? 'a' : 'span'"
        :href="external(item.url) ? item.url : undefined"
        target="_blank"
        rel="noopener noreferrer"
        :title="item.tooltip || item.value || text(item)"
        :style="{
          maxWidth: maximumItemWidth + 'px',
          color: item.url
            ? 'var(--primary)'
            : item.color ||
              (selected ? 'var(--on-content-selection)' : 'var(--muted)')
        }"
        @click="external(item.url) && $emit('link', item.url)"
        >{{ text(item) }}</component
      >
    </template>
  </span>
</template>

<style>
.info-value-strip {
  display: flex;
  gap: 4px;
  height: 16px;
  min-width: 0;
  overflow: hidden;
  align-items: center;
  font-size: var(--font-menu-heading-size);
  line-height: var(--font-menu-heading-line-height);
}
.info-value-strip > :not(.info-separator) {
  flex: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-decoration: none;
}
.info-value-strip > a:hover {
  text-decoration: underline;
}
.info-value-strip .info-separator {
  color: var(--outline);
  flex: none;
}
</style>
