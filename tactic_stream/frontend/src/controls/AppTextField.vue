<script setup>
// TextField.qml: shared single-line editor; the caller owns its value and actions.
import { computed, ref } from 'vue'
import { t } from '../i18n.js'
const props = defineProps({ modelValue: { type: [String,Number], default: '' }, label: String, placeholder: String, disabled: Boolean })
const emit = defineEmits(['update:modelValue'])
// Vue's text directive owns IME composition; retain this control's string events.
const text = computed({ get: () => String(props.modelValue ?? ''), set: value => emit('update:modelValue', String(value)) })
const field = ref(null)
defineExpose({ focus() { field.value?.focus() } })
</script>
<template><input ref="field" v-model="text" class="app-text-field" :aria-label="label || placeholder ? t(label || placeholder) : undefined" :placeholder="t(placeholder || '')" :disabled="disabled"></template>
<style>
.app-text-field { min-width:0; font-size:var(--text-body); height:var(--control-height); padding-inline:12px; }
.app-text-field:focus { outline:none; border:2px solid var(--primary); padding-inline:11px; }
.app-text-field:disabled { color:var(--disabled); }
.app-text-field.table-cell { appearance:none; border:0; border-radius:0; background:transparent; padding:4px 8px; box-sizing:border-box; }
.app-text-field.table-cell:focus { border:0; box-shadow:inset 0 0 0 2px var(--primary); background:var(--surface-high); padding:4px 8px; }
</style>
