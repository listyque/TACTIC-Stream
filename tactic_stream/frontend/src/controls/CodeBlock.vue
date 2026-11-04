<script setup>
import { computed } from 'vue'
import { syntaxTokens } from './pythonSyntax.js'

const props = defineProps({ code: { type: String, default: '' }, language: { type: String, default: 'auto' } })
const tokens = computed(() => syntaxTokens(props.code, props.language))
</script>

<template>
  <pre class="code-block" tabindex="0"><code><span v-for="(token, index) in tokens" :key="index" :class="token.role ? 'syntax-' + token.role : undefined">{{ token.text }}</span></code></pre>
</template>
