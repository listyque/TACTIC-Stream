<script setup>
// TextField.qml: shared single-line editor; the caller owns its value and actions.
import { ref } from 'vue'
import { t } from '../i18n.js'
defineProps({ modelValue: { type: [String,Number], default: '' }, label: String, placeholder: String, disabled: Boolean })
defineEmits(['update:modelValue'])
const field = ref(null)
defineExpose({ focus() { field.value?.focus() } })
</script>
<template><input ref="field" class="app-text-field" :value="modelValue" :aria-label="label || placeholder ? t(label || placeholder) : undefined" :placeholder="t(placeholder || '')" :disabled="disabled" @input="$emit('update:modelValue', $event.target.value)"></template>
<style>
.app-text-field { min-width:0; font-size:var(--text-body); height:var(--control-height); padding-inline:12px; }
.app-text-field:focus { outline:none; border:2px solid var(--primary); padding-inline:11px; }
.app-text-field:disabled { color:var(--disabled); }
.app-text-field.table-cell { appearance:none; border:0; border-radius:0; background:transparent; padding:4px 8px; box-sizing:border-box; }
.app-text-field.table-cell:focus { border:0; box-shadow:inset 0 0 0 2px var(--primary); background:var(--surface-high); padding:4px 8px; }
</style>
