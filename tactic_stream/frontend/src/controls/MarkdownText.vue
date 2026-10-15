<script setup>
import { computed } from 'vue'
import { renderMarkdown } from './markdown.js'

const props = defineProps({ text: { type: String, default: '' } })
const emit = defineEmits(['topic'])
function activate(event) {
  const href = event.target.closest('a')?.getAttribute('href')
  const topic = href?.match(/^([a-z][a-z0-9_.-]*)\.(?:en|ru)\.md(?:#.*)?$/i)?.[1]
  if (topic && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && !event.button) { event.preventDefault(); emit('topic', topic) }
  if (href?.startsWith('#')) {
    event.preventDefault()
    event.currentTarget.closest('article')?.querySelector('#' + CSS.escape(decodeURIComponent(href.slice(1))))?.scrollIntoView({ block: 'start' })
  }
}
const html = computed(() => renderMarkdown(props.text))
</script>
<template><div class="markdown-text" v-html="html" @click="activate" /></template>
<style>
.markdown-text { font-size:var(--text-document-body); line-height:var(--text-document-line-height); font-weight:400; overflow-wrap:anywhere; }
.markdown-text > :first-child { margin-top:0; }.markdown-text > :last-child { margin-bottom:0; }
.markdown-text p, .markdown-text ul, .markdown-text ol, .markdown-text blockquote, .markdown-text pre { margin:0 0 8px; }
.markdown-text h2 { font-size:var(--text-document-heading); font-weight:600; line-height:1.25; margin:14px 0 8px; }.markdown-text h3 { font-size:var(--text-body-large); font-weight:600; margin:14px 0 8px; }
.markdown-text a { color:var(--primary); }.markdown-text ul, .markdown-text ol { padding-left:24px; }.markdown-text li > p { margin-bottom:8px; }
.markdown-text code { font-family:var(--font-mono, Consolas, monospace); }.markdown-text :not(pre) > code { background:var(--surface-high); padding:1px 4px; border-radius:4px; }
.markdown-text pre { white-space:pre-wrap; overflow-wrap:anywhere; padding:12px; background:var(--surface-high); border:1px solid var(--outline-variant); border-radius:var(--item-radius); font-size:var(--text-caption); }
.markdown-text table { border-collapse:collapse; width:100%; margin-bottom:14px; table-layout:fixed; }.markdown-text th, .markdown-text td { padding:8px; text-align:left; vertical-align:top; white-space:normal; overflow-wrap:anywhere; border:1px solid var(--outline-variant); }.markdown-text th { background:var(--surface-high); font-weight:600; }
.markdown-text blockquote { border-left:3px solid var(--primary); padding-left:12px; color:var(--muted); }
.markdown-text img { max-width:100%; height:auto; }
</style>
