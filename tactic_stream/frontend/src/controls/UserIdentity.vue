<script setup>
import ItemPreview from './ItemPreview.vue'
import AppIcon from './AppIcon.vue'
import { t } from '../i18n.js'
defineProps({ login: String, displayName: String, initials: String, avatarUrl: String, avatarColor: String, retired: Boolean })
</script>

<template>
  <span class="user-identity" :class="{ retired }"><ItemPreview :source="avatarUrl" :fallback-text="initials" :accent="avatarColor" /><span class="user-identity-text"><strong>{{ displayName || login }}</strong><small v-if="displayName !== login" class="muted">{{ login }}</small></span><span v-if="retired" class="muted" :title="t('Retired')"><AppIcon name="archive" />{{ t('Retired') }}</span></span>
</template>
