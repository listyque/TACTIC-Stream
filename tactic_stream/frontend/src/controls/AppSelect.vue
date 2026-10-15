<script setup>
import { computed } from 'vue'
import { t } from '../i18n.js'
import AppIcon from './AppIcon.vue'

const props = defineProps({ options: { type: Array, default: () => [] }, label: String, swatchMode: String, translateLabels: { type: Boolean, default: true } })
const model = defineModel()
const decorated = computed(() => CSS.supports('appearance', 'base-select') && props.options.some(item => item.icon))
</script>

<template>
  <select class="app-select" v-model="model" :aria-label="label ? t(label) : undefined">
    <button v-if="decorated" type="button" class="app-select-trigger"><component is="selectedcontent" /></button>
    <option v-if="model !== undefined && !options.some(item => item.value === model)" :value="model">{{ model }}</option>
    <option v-for="item in options" :key="item.value" :value="item.value" :disabled="item.disabled"><AppIcon v-if="decorated && item.icon" :name="item.icon" /><span v-if="swatchMode" class="palette-swatch" :style="{ backgroundColor: item[swatchMode], borderColor: item[swatchMode + 'Base'] }"></span><span class="app-select-option-label">{{ translateLabels ? t(item.label) : item.label }}</span></option>
  </select>
</template>

<style>
.app-select > .app-select-trigger { display:flex; align-items:center; flex:1; min-width:0; min-height:0; border:0; border-radius:0; padding:0; background:transparent; color:inherit; font:inherit; text-align:start; }
.app-select selectedcontent { display:flex; align-items:center; gap:var(--space-sm); min-width:0; }
.app-select :is(option,selectedcontent) > .app-icon { width:16px; height:16px; flex:0 0 16px; font-size:16px; }
.app-select selectedcontent > .app-select-option-label { min-width:0; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
</style>
