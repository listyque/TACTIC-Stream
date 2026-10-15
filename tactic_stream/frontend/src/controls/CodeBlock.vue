<script setup>
import { computed } from 'vue'
import { pythonTokens, javascriptTokens, xmlTokens } from './pythonSyntax.js'

const props = defineProps({ code: { type: String, default: '' }, language: { type: String, default: 'python' } })
const tokens = computed(() => props.language === 'text' ? [{ text: props.code }] : props.language === 'xml' ? xmlTokens(props.code) : props.language === 'javascript' ? javascriptTokens(props.code) : pythonTokens(props.code))
</script>

<template>
  <pre class="code-block" tabindex="0"><code><span v-for="(token, index) in tokens" :key="index" :class="token.role ? 'syntax-' + token.role : undefined">{{ token.text }}</span></code></pre>
</template>
