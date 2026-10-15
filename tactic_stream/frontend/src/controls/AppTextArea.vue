<script setup>
// Handler TextArea.qml (EPL-1.0): shared multiline editor; its caller owns the value.
import { ref } from 'vue'
import { t } from '../i18n.js'
defineProps({ label: String, placeholder: String, disabled: Boolean })
const model = defineModel({ type: String, default: '' })
const field = ref(null)
defineExpose({ focus() { field.value?.focus() } })
</script>
<template><textarea ref="field" v-model="model" class="app-text-area" :aria-label="t(label || placeholder)" :placeholder="t(placeholder || '')" :disabled="disabled"></textarea></template>
<style>
.app-text-area { min-width:0; font-size:var(--text-body); padding:10px 12px; resize:vertical; }.app-text-area:focus { outline:none; border:2px solid var(--primary); padding:9px 11px; }.app-text-area:disabled { color:var(--disabled); }
</style>
