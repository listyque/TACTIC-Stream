<script setup>
// Handler UserGroupSection.qml (EPL-1.0).
import AppIcon from './AppIcon.vue'
import { t } from '../i18n.js'
defineProps({ title: String, compact: Boolean })
</script>
<template>
  <div class="user-group-section" :class="{ compact }"><AppIcon name="MDI_ACCOUNT_GROUP" /><span>{{ title === 'Ungrouped' ? t('UNGROUPED') : title?.toUpperCase() }}</span><hr></div>
</template>
<style>
.user-group-section { display:flex; align-items:center; gap:7px; height:34px; flex-shrink:0; padding:0 8px; font-size:9px; font-weight:600; color:var(--muted); }
.user-group-section > .app-icon { width:13px; height:13px; font-size:13px; }
.user-group-section hr { flex:1; border:0; border-top:1px solid var(--outline-variant); }
.user-group-section.compact { height:28px; font-size:8px; }
.user-group-section.compact > .app-icon { width:11px; height:11px; font-size:11px; }
</style>
