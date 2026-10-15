<script setup>
import AppSelect from '../../controls/AppSelect.vue'
import AppTextField from '../../controls/AppTextField.vue'
import AppSwitch from '../../controls/AppSwitch.vue'
import AppButton from '../../controls/AppButton.vue'
import { t } from '../../i18n.js'
defineProps({ columns: Array, disabled: Boolean })
const field = defineModel('field'), value = defineModel('value'), retired = defineModel('retired')
defineEmits(['apply'])
</script>
<template>
  <form class="search-filter-panel" @submit.prevent="$emit('apply')">
    <label>{{ t('Filter field') }}<AppSelect v-model="field" :options="columns.map(name => ({ value: name, label: name }))" label="Filter field" :disabled="disabled" /></label>
    <label>{{ t('Filter value') }}<AppTextField v-model="value" placeholder="Filter value" :disabled="disabled" /></label>
    <label class="configuration-toggle"><AppSwitch v-model="retired" label="Show retired" :disabled="disabled" /><span>{{ t('Show retired') }}</span></label>
    <AppButton type="submit" label="Apply filters" highlighted :disabled="disabled" />
  </form>
</template>
<style>
.search-filter-panel { display:grid; gap:12px; }
.search-filter-panel > label:not(.configuration-toggle) { display:grid; gap:6px; }
.search-filter-panel > .app-button { justify-content:center; padding:0 12px; border:1px solid var(--primary); border-radius:var(--button-radius); min-height:var(--control-height); background:var(--primary); color:var(--on-primary); font-size:var(--text-body); font-weight:600; }
</style>
