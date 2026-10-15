<script setup>
import { computed, ref, useAttrs } from 'vue'
import { t } from '../i18n.js'
import AppButton from './AppButton.vue'
import ColorPicker from './ColorPicker.vue'

defineOptions({ inheritAttrs: false })
defineProps({ label: String, disabled: Boolean, readonly: Boolean })
const model = defineModel()
const attrs = useAttrs()
const picker = ref(null)
const swatch = computed(() => /^#[\da-f]{6}$/i.test(model.value || '') ? model.value : 'var(--primary)')
</script>

<template>
  <div class="app-color-input">
    <span class="color-swatch" :style="{ background: swatch }" aria-hidden="true" />
    <AppButton :id="attrs.id" label="Choose color" icon="appearance" :disabled="disabled || readonly"
      :aria-label="t('Choose color for {field}', { field: label })" :aria-describedby="attrs['aria-describedby']" :title="model || ''" @click="picker.open(model)" />
    <input v-if="attrs.name" type="hidden" :name="attrs.name" :value="model">
    <ColorPicker ref="picker" @chosen="model = $event" />
  </div>
</template>
