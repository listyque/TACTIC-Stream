<script setup>
import { t } from '../i18n.js'
import AppIcon from './AppIcon.vue'
defineProps({ label: String, controlId: String, disabled: Boolean, indeterminate: Boolean, compact: Boolean, hideLabel: Boolean, translateLabel: { type: Boolean, default: true } })
const model = defineModel({ type: Boolean, default: false })
</script>

<template>
  <label class="app-checkbox" :class="{ disabled, compact }"><span class="app-checkbox-indicator"><input :id="controlId" type="checkbox" v-model="model" :disabled="disabled" :indeterminate="indeterminate" :aria-label="label ? translateLabel ? t(label) : label : undefined"><AppIcon v-if="model || indeterminate" :name="indeterminate ? 'minus' : 'check'" /></span><slot v-if="!hideLabel">{{ label ? translateLabel ? t(label) : label : '' }}</slot></label>
</template>
<style>
.app-checkbox.compact { min-height:30px; gap:6px; font-size:var(--text-label); }
.app-checkbox.compact .app-checkbox-indicator { flex-basis:17px; width:17px; height:17px; }
.app-checkbox.compact input { width:17px; height:17px; }
.app-checkbox.compact .app-icon { font-size:13px; }
</style>
