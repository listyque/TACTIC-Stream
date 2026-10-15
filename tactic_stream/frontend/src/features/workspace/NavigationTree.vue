<script setup>
import { computed, reactive } from 'vue'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import { t } from '../../i18n.js'

const props = defineProps({ entries: { type: Array, default: () => [] }, project: String, query: String, selected: String })
const emit = defineEmits(['select'])
const collapsed = reactive(new Set())
const key = entry => props.project + ':' + entry.key
const rows = computed(() => {
  const term = (props.query || '').trim().toLowerCase()
  const result = []
  const childMatches = children => children.some(child => `${child.title} ${child.searchText || child.search_type || ''}`.toLowerCase().includes(term) || childMatches(child.children || []))
  function visit(entries, depth, parentMatches = false) {
    for (const entry of entries) {
      const matches = parentMatches || `${entry.title} ${entry.searchText || entry.search_type || ''}`.toLowerCase().includes(term)
      if (term && !matches && !childMatches(entry.children || [])) continue
      if (term && entry.kind === 'separator') continue
      const expanded = !!term || !collapsed.has(key(entry))
      result.push({ ...entry, depth, expanded })
      if (expanded) visit(entry.children || [], depth + 1, matches && !!term)
    }
  }
  visit(props.entries, 0)
  return result
})
function toggle(entry) {
  if (collapsed.has(key(entry))) collapsed.delete(key(entry))
  else collapsed.add(key(entry))
}
function move(event) {
  const buttons = [...event.currentTarget.querySelectorAll('button:not(:disabled)')]
  const index = buttons.indexOf(event.target)
  if (index < 0) return
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    buttons[(index + (event.key === 'ArrowDown' ? 1 : buttons.length - 1)) % buttons.length]?.focus()
  } else if (event.key === 'Home' || event.key === 'End') {
    event.preventDefault()
    buttons[event.key === 'Home' ? 0 : buttons.length - 1]?.focus()
  } else if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
    const entry = rows.value.find(row => row.key === event.target.dataset.entryKey)
    if (entry?.kind === 'section' && entry.expanded !== (event.key === 'ArrowRight')) { event.preventDefault(); toggle(entry) }
  }
}
</script>

<template>
  <nav class="navigation-tree" :aria-label="t('Project views')" @keydown="move">
    <template v-for="entry in rows" :key="entry.key">
      <hr v-if="entry.kind === 'separator'" class="navigation-separator" :style="{ '--entry-depth': entry.depth }">
      <div v-else class="navigation-entry" :style="{ '--entry-depth': entry.depth, '--navigation-accent': entry.accent || 'var(--primary)' }">
        <AppButton :label="entry.title" :data-entry-key="entry.key" :data-search-type="entry.search_type" :class="{ active: selected === entry.key, 'navigation-folder': entry.kind === 'section' }"
          :disabled="entry.kind !== 'section' && !entry.supported" :aria-expanded="entry.kind === 'section' ? entry.expanded : undefined"
          @click="entry.kind === 'section' ? toggle(entry) : emit('select', entry)">
          <span class="navigation-icon"><AppIcon :name="entry.kind === 'section' ? entry.expanded ? 'MDI_CHEVRON_DOWN' : 'next' : entry.icon || 'link'" /></span>
          <span class="navigation-text"><strong>{{ entry.title }}</strong></span>
        </AppButton>
      </div>
    </template>
    <p v-if="!rows.length" class="muted sidebar-empty">{{ t(query ? 'No types found' : 'No navigation items') }}</p>
  </nav>
</template>
