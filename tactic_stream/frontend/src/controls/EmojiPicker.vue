<script setup>
import { ref, computed } from 'vue'
import AppMenu from './AppMenu.vue'
import AppButton from './AppButton.vue'
import AppIcon from './AppIcon.vue'
import AppSearchField from './AppSearchField.vue'
import { t } from '../i18n.js'
defineProps({ label: { type: String, default: 'Choose emoji' }, disabled: Boolean, textTrigger: Boolean })
const emit = defineEmits(['selected'])
const menu = ref(null), query = ref(''), category = ref('Smileys & Emotion'), entries = ref([]), error = ref('')
const categories = computed(() => [...new Set(entries.value.map(row => row.category))])
const shown = computed(() => entries.value.filter(row => query.value ? row.name.includes(query.value.toLowerCase()) || row.value === query.value : row.category === category.value))
async function load() {
  if (!menu.value?.open || entries.value.length) return
  try { entries.value = (await import('../assets/emoji.json')).default; error.value = '' }
  catch { error.value = 'Unable to load emoji. Try again.' }
}
function select(value) { emit('selected', value); menu.value.close(true) }
</script>
<template>
  <AppMenu v-if="!disabled" ref="menu" class="emoji-picker" :class="{ 'menu-entry': textTrigger }" :label="label" icon="MDI_EMOTICON_OUTLINE" overlay :close-on-select="false" @toggle="load">
    <template v-if="textTrigger" #trigger><AppIcon name="MDI_EMOTICON_OUTLINE" /><span>{{ t(label) }}</span></template>
    <AppSearchField v-model="query" label="Find emoji" :placeholder="t('Find emoji')" />
    <div class="emoji-categories"><AppButton v-for="name in categories" :key="name" :label="name" :tonal="category === name" @click="category = name; query = ''">{{ t(name) }}</AppButton></div>
    <p v-if="error" role="alert">{{ t(error) }} <AppButton label="Retry" @click="load" /></p>
    <div class="emoji-grid"><AppButton v-for="row in shown" :key="row.value" :aria-label="row.name" :title="row.name" @click="select(row.value)">{{ row.value }}</AppButton></div>
    <p v-if="entries.length && !shown.length">{{ t('No matching emoji') }}</p>
  </AppMenu>
</template>
<style>
@font-face { font-family:'Noto Color Emoji'; src:url('/assets/NotoColorEmoji_WindowsCompatible.ttf') format('truetype'); font-display:swap; }
.emoji-picker .account-panel { width:min(336px, calc(100dvw - 16px)); padding:10px; gap:8px; }
.emoji-picker .app-search-field { flex:none; height:36px; min-height:36px; }
.emoji-picker.menu-entry > summary { width:100%; min-width:0; height:var(--control-height); justify-content:flex-start; gap:8px; padding:0 12px; font-size:var(--text-body); }
.emoji-categories { display:flex; gap:4px; overflow:auto; flex-shrink:0; }
.emoji-categories .app-button { min-height:26px; height:26px; padding:0 8px; font-size:var(--text-caption); white-space:nowrap; }
.emoji-grid { display:grid; grid-template-columns:repeat(8, minmax(0, 1fr)); max-height:260px; overflow:auto; gap:0; }
.emoji-picker .emoji-grid .app-button { min-width:0; min-height:40px; height:40px; padding:0; justify-content:center; font:26px/1 'Noto Color Emoji', 'Segoe UI Emoji', sans-serif; border:0; border-radius:var(--item-radius); background:transparent; }
@media(max-width:700px) {
  .emoji-picker .emoji-grid { grid-template-columns:repeat(auto-fill,44px); gap:4px; max-height:min(320px,45dvh); }
  .emoji-picker .emoji-grid .app-button { width:44px; height:44px; min-height:44px; padding:0; justify-content:center; font-size:32px; line-height:1; }
}
</style>
