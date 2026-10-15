<script setup>
import { t } from '../i18n.js'

defineOptions({ inheritAttrs: false })
defineProps({ label: String })
const model = defineModel({ type: Boolean, default: false })
</script>

<template>
  <label class="switch-control"><input v-bind="$attrs" class="app-switch" type="checkbox" role="switch" :aria-label="label ? t(label) : undefined" :checked="model" @change="model = $event.target.checked"></label>
</template>
