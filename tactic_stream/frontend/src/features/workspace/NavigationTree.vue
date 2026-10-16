<script setup>
import { computed, reactive } from 'vue';
import NavigationRow from '../../controls/NavigationRow.vue';
import { t } from '../../i18n.js';
import { move as navigationMove } from '../../../../src/tactic_stream/shared_ui/shell/navigation.ui.mjs';

const props = defineProps({
  entries: { type: Array, default: () => [] },
  project: String,
  query: String,
  selected: String
});
const emit = defineEmits(['select']);
const collapsed = reactive(new Set());
const key = (entry) => props.project + ':' + entry.key;
const rows = computed(() => {
  const term = (props.query || '').trim().toLowerCase();
  const result = [];
  const childMatches = (children) =>
    children.some(
      (child) =>
        `${child.title} ${child.searchText || child.search_type || ''}`
          .toLowerCase()
          .includes(term) || childMatches(child.children || [])
    );
  function visit(entries, depth, parentMatches = false) {
    for (const entry of entries) {
      const matches =
        parentMatches ||
        `${entry.title} ${entry.searchText || entry.search_type || ''}`
          .toLowerCase()
          .includes(term);
      if (term && !matches && !childMatches(entry.children || [])) continue;
      if (term && entry.kind === 'separator') continue;
      const expanded = !!term || !collapsed.has(key(entry));
      result.push({ ...entry, depth, expanded });
      if (expanded) visit(entry.children || [], depth + 1, matches && !!term);
    }
  }
  visit(props.entries, 0);
  return result;
});
function toggle(entry) {
  if (collapsed.has(key(entry))) collapsed.delete(key(entry));
  else collapsed.add(key(entry));
}
function move(event) {
  const entries = rows.value.map((row) => ({
    ...row,
    id: row.key,
    hasChildren: row.kind === 'section',
    enabled: row.kind === 'section' || row.supported
  }));
  const result = navigationMove(
    entries,
    event.target.dataset.entryKey,
    event.key
  );
  if (!result) return;
  event.preventDefault();
  if (result.type === 'expand' || result.type === 'collapse')
    toggle(rows.value.find((row) => row.key === result.id));
  else {
    const target = [...event.currentTarget.querySelectorAll('button')].find(
      (button) => button.dataset.entryKey === result.id
    );
    target?.focus();
    target?.scrollIntoView({ block: 'nearest' });
  }
}
</script>

<template>
  <nav class="navigation-tree" :aria-label="t('Project views')" @keydown="move">
    <NavigationRow
      v-for="entry in rows"
      :key="entry.key"
      :record="entry"
      :selected="selected === entry.key"
      :data-entry-key="entry.key"
      :data-search-type="entry.search_type"
      :disabled="
        entry.kind !== 'section' &&
        entry.kind !== 'separator' &&
        !entry.supported
      "
      @activated="
        entry.kind === 'section' ? toggle(entry) : emit('select', entry)
      "
    />
    <p v-if="!rows.length" class="muted sidebar-empty">
      {{ t(query ? 'No types found' : 'No navigation items') }}
    </p>
  </nav>
</template>
