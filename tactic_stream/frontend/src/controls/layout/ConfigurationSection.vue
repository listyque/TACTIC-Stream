<script setup>
import { t } from '../../i18n.js';
defineProps({ title: String, description: String, fillContentHeight: Boolean });
</script>

<template>
  <section
    class="configuration-section"
    :class="{ 'fill-content': fillContentHeight }"
  >
    <strong>{{ t(title) }}</strong>
    <p v-if="description">{{ t(description) }}</p>
    <div><slot /></div>
  </section>
</template>

<style>
.configuration-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}
.configuration-section > strong {
  margin-left: 1px;
  font-size: var(--font-body-large-size);
  line-height: var(--font-body-large-line-height);
  font-weight: 600;
}
.configuration-section > p {
  margin: 0 1px;
  color: var(--muted);
  font-size: var(--font-caption-size);
  line-height: var(--font-caption-line-height);
  line-height: var(--font-caption-line-height);
  overflow-wrap: anywhere;
}
.configuration-section > div {
  padding: 16px;
  border-radius: var(--section-radius);
  background: var(--surface);
  box-shadow: inset 0 0 0 1px var(--outline-variant);
}
.configuration-section.fill-content > div {
  flex: 1;
}
</style>
