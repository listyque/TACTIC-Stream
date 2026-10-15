<script setup>
import AppIcon from './AppIcon.vue'
import { t } from '../i18n.js'
defineProps({ icon: String, label: String, value: String })
</script>
<template><div v-if="value" class="profile-info-row"><AppIcon :name="icon" /><span><small>{{ t(label) }}</small><span :title="value">{{ value }}</span></span></div></template>
<style>
.profile-info-row { display:flex; align-items:center; gap:9px; min-width:0; }.profile-info-row > .app-icon { width:15px; height:15px; font-size:15px; color:var(--muted); flex-shrink:0; }.profile-info-row > span { display:flex; flex-direction:column; min-width:0; }.profile-info-row small { font-size:var(--text-caption); color:var(--muted); }.profile-info-row span span { font-size:var(--text-body); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
</style>
