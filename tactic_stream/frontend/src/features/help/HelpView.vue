<script setup>
// Current HelpView.qml: searchable topic list and independently scrolling article.
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppTextField from '../../controls/AppTextField.vue'
import ItemSurface from '../../controls/ItemSurface.vue'
import BusyIndicator from '../../controls/BusyIndicator.vue'
import { asyncComponent } from '../../controls/asyncComponent.js'
import { appearance } from '../../appearance.js'
import { downloadBlob } from '../../controls/files.js'
import { t } from '../../i18n.js'
import { filterTopics, loadArticles } from './help.js'
const MarkdownText = asyncComponent(() => import('../../controls/MarkdownText.vue'))

const props = defineProps({ label: { type: String, default: 'Help' }, topic: { type: String, default: 'overview' } })
const dialog = ref(null), articleScroll = ref(null), topics = ref(null), article = ref(null)
const selected = ref('overview'), query = ref(''), articles = ref([]), busy = ref(false), error = ref(''), topicsVisible = ref(false)
let controller = null, generation = 0
const current = computed(() => articles.value.find(row => row.id === selected.value))
const filtered = computed(() => filterTopics(articles.value, query.value))
function close() { dialog.value?.close(); topicsVisible.value = false }
async function reveal() {
  await nextTick()
  const row = topics.value?.querySelector('[data-topic="' + selected.value + '"]')
  if (row) {
    const top = row.getBoundingClientRect().top - topics.value.getBoundingClientRect().top + topics.value.scrollTop
    if (top < topics.value.scrollTop) topics.value.scrollTop = top
    else if (top + row.offsetHeight > topics.value.scrollTop + topics.value.clientHeight) topics.value.scrollTop = top + row.offsetHeight - topics.value.clientHeight
  }
}
async function select(id, keyboard = false) {
  if (!articles.value.some(row => row.id === id)) return
  selected.value = id; topicsVisible.value = false
  if (!filtered.value.some(row => row.id === id)) query.value = ''
  await nextTick(); if (articleScroll.value) articleScroll.value.scrollTop = 0
  await reveal()
  if (keyboard) article.value?.focus({ preventScroll: true })
}
async function reload() {
  controller?.abort(); controller = new AbortController()
  const request = ++generation
  busy.value = true; error.value = ''
  try {
    const loaded = await loadArticles(appearance.language, controller.signal)
    if (request !== generation) return
    articles.value = loaded
    const showingTopics = topicsVisible.value
    await select(loaded.some(row => row.id === selected.value) ? selected.value : loaded.some(row => row.id === 'overview') ? 'overview' : loaded[0].id)
    topicsVisible.value = showingTopics
  } catch (exception) { if (request === generation && exception.name !== 'AbortError') error.value = exception.message }
  finally { if (request === generation) busy.value = false }
}
async function open(id = props.topic) {
  selected.value = id; query.value = ''; topicsVisible.value = false
  if (!dialog.value.open) dialog.value.show()
  if (!articles.value.length) await reload()
  else await select(id)
}
function download() { if (current.value) downloadBlob(new Blob([current.value.source], { type: 'text/markdown;charset=utf-8' }), current.value.file.split('/').at(-1)) }
function topicKey(event) {
  if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const buttons = [...topics.value.querySelectorAll('button')], index = buttons.indexOf(document.activeElement)
  const target = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : event.key === 'ArrowDown' ? (index + 1) % buttons.length : (index - 1 + buttons.length) % buttons.length
  buttons[target]?.focus()
}
watch(() => appearance.language, () => { if (dialog.value?.open || articles.value.length) reload() })
onBeforeUnmount(() => { generation++; controller?.abort(); dialog.value?.close() })
defineExpose({ open, close })
</script>
<template>
  <Teleport to="body"><dialog v-window="{ type:'window' }" ref="dialog" class="help-view" :aria-label="t(label)" @cancel.prevent="close">
    <header class="help-window-header"><AppIcon name="help" /><strong>{{ t(label) }}</strong><AppButton icon-only label="Close help" icon="close" @click="close" /></header>
    <div class="help-layout" :class="{ 'topics-visible': topicsVisible }">
      <aside class="help-topics"><header><AppIcon name="help" /><strong>{{ t('Help topics') }}</strong><AppButton class="help-mobile-toggle" icon-only icon="close" label="Close help topics" @click="topicsVisible = false" /></header>
        <AppTextField v-model="query" placeholder="Search help" label="Search help" />
        <nav ref="topics" :aria-label="t('Help topics')" @keydown="topicKey"><ItemSurface v-for="row in filtered" :key="row.id" :selected="selected === row.id" :inset="0"><AppButton :data-topic="row.id" :aria-current="row.id === selected ? 'page' : undefined" @click="select(row.id, $event.detail === 0)"><AppIcon :name="row.icon" /><span class="help-topic-label"><strong>{{ row.title }}</strong><small>{{ t(row.group) }}</small></span></AppButton></ItemSurface><p v-if="!filtered.length && !busy" class="muted">{{ t('No help topics match your search') }}</p></nav>
      </aside>
      <section class="help-content" :aria-busy="busy"><header><AppButton class="help-mobile-toggle" icon-only icon="menu" label="Help topics" :aria-expanded="topicsVisible" @click="topicsVisible = !topicsVisible" /><AppIcon :name="current?.icon || 'help'" /><div><h1>{{ current?.title || t(label) }}</h1><small>{{ t(current?.group || 'Guide') }}</small></div><BusyIndicator v-if="busy" running /><AppButton icon-only icon="refresh" label="Reload help articles" :disabled="busy" @click="reload" /><AppButton icon-only icon="folder-open" label="Open article file" :href="current?.file" target="_blank" rel="noopener noreferrer" :aria-disabled="!current" :disabled="!current" /><AppButton icon-only icon="download" label="Download article" :disabled="!current" @click="download" /></header>
        <div ref="articleScroll" class="help-article-scroll"><p v-if="error" class="error" role="alert">{{ t(error) }}</p><article ref="article" tabindex="0"><p v-if="current?.reference" class="help-reference muted">{{ t('Original Handler reference. Desktop-specific options belong to Handler; this article does not indicate that every feature has been migrated to Stream.') }}</p><div v-if="current?.summary" class="help-summary"><AppIcon name="info" /><MarkdownText :text="current.summary" @topic="select" /></div><MarkdownText v-if="current" :text="current.body" @topic="select" /></article></div>
      </section>
    </div>
  </dialog></Teleport>
</template>
<style>
.help-view { width:min(70dvw,calc(100dvw - 16px)); height:min(76dvh,calc(100dvh - 16px)); min-width:min(720px,calc(100dvw - 16px)); max-width:none; max-height:none; padding:0; margin:auto; background:var(--page); color:var(--on-surface); border:1px solid var(--outline-variant); border-radius:var(--surface-radius); overflow:hidden; }
.help-view[open] { display:flex; flex-direction:column; }.help-view::backdrop { background:var(--scrim); }
.help-window-header { height:40px; flex:none; display:flex; align-items:center; gap:9px; padding:2px 6px 2px 14px; border-bottom:1px solid var(--outline-variant); background:var(--surface); }.help-window-header > strong { flex:1; }.help-window-header > .app-icon { color:var(--primary); }
.help-layout { display:flex; gap:10px; margin:12px; flex:1; min-height:0; min-width:0; position:relative; }
.help-topics { flex:0 0 clamp(236px,29%,292px); display:flex; flex-direction:column; gap:8px; min-width:0; padding:10px; background:var(--surface); border:1px solid var(--outline-variant); border-radius:var(--surface-radius); }
.help-topics > header { display:flex; align-items:center; gap:8px; }.help-topics > header > .app-icon { font-size:20px; color:var(--primary); }.help-topics > header > strong { font-size:var(--text-body-large); flex:1; }
.help-topics nav { position:relative; overflow:auto; min-height:0; flex:1; padding-right:8px; display:flex; flex-direction:column; gap:3px; }
.help-topics .item-surface { flex:none; --item-base:var(--row); }.help-topics .item-surface.selected { --item-base:var(--content-selection); }.help-topics .item-surface::after { display:none; }
.help-topics .item-surface > .app-button { height:58px; width:100%; display:flex; align-items:center; gap:9px; padding:0 9px 0 11px; margin:0; border:0; border-radius:var(--item-radius); background:transparent; text-align:left; color:var(--on-surface); }
.help-topics .item-surface > .app-button:hover { background:transparent; }.help-topics .app-button > .app-icon { font-size:17px; color:var(--muted); }.help-topics .selected .app-button > .app-icon { color:var(--primary); }
.help-topics .app-button > .help-topic-label { display:flex; min-width:0; flex:1; flex-direction:column; gap:1px; }.help-topics .app-button strong { font-size:var(--text-body); font-weight:400; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }.help-topics .selected .app-button strong { font-weight:600; }.help-topics .app-button small { font-size:var(--text-caption); color:var(--muted); }
.help-content { flex:1; min-width:0; min-height:0; display:flex; flex-direction:column; padding:4px; background:var(--surface); border:1px solid var(--outline-variant); border-radius:var(--surface-radius); }
.help-content > header { display:flex; align-items:center; gap:10px; padding:10px 10px 10px 14px; flex:none; border-bottom:1px solid var(--outline-variant); }.help-content > header > .app-icon { font-size:24px; color:var(--primary); }.help-content > header > div { flex:1; min-width:0; }.help-content h1 { font-size:var(--text-title); font-weight:600; margin:0 0 2px; overflow-wrap:anywhere; }.help-content header small { font-size:var(--text-label); color:var(--muted); }
.help-article-scroll { overflow:auto; flex:1; min-height:0; }.help-article-scroll article { margin:14px 26px 14px 14px; }.help-summary { display:flex; align-items:flex-start; gap:10px; padding:12px; margin-bottom:14px; border:1px solid var(--outline-variant); border-radius:var(--item-radius); background:var(--surface-high); }.help-summary > .app-icon { color:var(--primary); font-size:18px; flex:none; }.help-summary > .markdown-text { flex:1; min-width:0; }.help-reference { font-size:var(--text-caption); margin:0 0 14px; }.help-view .help-mobile-toggle { display:none; }
@media(max-width:760px) { .help-view { width:calc(100dvw - 16px); height:calc(100dvh - 16px); min-width:0; }.help-layout { margin:8px; gap:0; }.help-view .help-mobile-toggle { display:inline-flex; }.help-topics { display:none; }.topics-visible .help-content { visibility:hidden; }.topics-visible .help-topics { display:flex; position:absolute; inset:0; z-index:2; }.help-content > header { gap:4px; padding:6px; flex-wrap:wrap; }.help-content > header > .app-icon { display:none; }.help-content h1 { font-size:var(--text-body-large); }.help-content > header > div { flex-basis:calc(100% - 48px); }.help-content > header .app-button { width:30px; height:30px; min-width:30px; min-height:30px; }.help-article-scroll article { margin:12px; } }
</style>
