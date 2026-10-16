<script setup>
import { t } from '../../i18n.js';
defineProps({ text: String });
</script>
<template>
  <span class="section-label">{{ t(text) }}</span>
</template>
<style>
.section-label {
  display: block;
  color: var(--muted);
  font-size: var(--font-body-size);
  line-height: var(--font-body-line-height);
  font-weight: 600;
  letter-spacing: 0.5px;
}
</style>
