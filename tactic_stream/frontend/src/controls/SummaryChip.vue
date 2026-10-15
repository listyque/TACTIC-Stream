<script setup>
// SummaryChip.qml: one presentation for groups, statuses and processes.
import AppButton from './AppButton.vue'
import AppIcon from './AppIcon.vue'
defineProps({ label:String, count:Number, accent:String, icon:String, compact:Boolean, clickable:Boolean, showDot:{ type:Boolean, default:true }, showCount:{ type:Boolean, default:true } })
defineEmits(['click'])
</script>
<template><component :is="clickable ? AppButton : 'div'" class="summary-chip" :class="{clickable, compact}" :label="clickable ? label + (showCount && count != null ? ' ' + count : '') : undefined" :style="{ '--chip-accent':accent || 'var(--primary)' }" @click="clickable && $emit('click')"><AppIcon v-if="icon" :name="icon" /><i v-if="showDot"></i><span>{{ label }}</span><small v-if="showCount">{{ count }}</small></component></template>
<style>
.summary-chip, .summary-chip.app-button { display:inline-flex; align-items:center; gap:7px; width:max-content; min-height:30px; height:30px; padding:0 10px; border:1px solid var(--outline-variant); border-radius:15px; background:var(--surface-high); color:var(--on-surface); font-size:var(--text-label); font-weight:400; }.summary-chip i { width:8px; height:8px; flex-shrink:0; border-radius:50%; background:var(--chip-accent); }.summary-chip small { color:var(--chip-accent); font-size:inherit; font-weight:600; }.summary-chip.clickable:hover { background:var(--hover); }.summary-chip.clickable:focus-visible { border-color:var(--primary); }
</style>
<style>
.summary-chip.compact { height:24px; min-height:24px; padding:0 8px; border:0; color:var(--chip-accent); font-size:var(--text-caption); }
.summary-chip.compact .app-icon { font-size:14px; }
</style>
