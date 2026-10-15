<script setup>
import { t } from '../i18n.js'

defineProps({ controlId: String, title: String, description: String, path: String })
</script>

<template>
  <div class="settings-row configuration-setting">
    <div class="setting-description"><label :for="controlId"><strong>{{ t(title) }}</strong></label><code v-if="path">{{ path }}</code><p v-if="description" :id="controlId + '-help'" class="muted">{{ t(description) }}</p><slot name="description" /></div>
    <div class="setting-control"><slot /></div>
  </div>
</template>
