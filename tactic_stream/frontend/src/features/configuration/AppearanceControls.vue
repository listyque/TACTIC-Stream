<script setup>
import { t } from '../../i18n.js'
import AppIcon from '../../controls/AppIcon.vue'
import AppearanceSettings from './AppearanceSettings.vue'

defineProps({ compact: Boolean })
</script>

<template>
  <details class="appearance-controls">
    <summary :class="{ 'icon-button': compact }" :aria-label="t('Appearance')" :title="t('Appearance')"><AppIcon name="appearance" /><span v-if="!compact" class="appearance-title">{{ t('Appearance') }}</span></summary>
    <div class="appearance-options"><AppearanceSettings compact /></div>
  </details>
</template>
