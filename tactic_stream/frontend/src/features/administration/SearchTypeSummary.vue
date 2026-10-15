<script setup>
import { t } from '../../i18n.js'
import RelationshipMap from './RelationshipMap.vue'
import SettingRow from '../../controls/SettingRow.vue'

defineProps({ identity: String, metadata: Object, catalog: Array })
const metrics = [['total', 'Search Objects'], ['active', 'Active'], ['retired', 'Retired'], ['fields', 'Fields'], ['pipelines', 'Pipelines'], ['processes', 'Processes']]
function label(identity, catalog) { return catalog.find(row => row.identity === identity)?.label || identity }
function description(edge) {
  const parts = []
  if (edge.manyToMany) parts.push(t('Many-to-many (M:N): each side can be linked to several objects on the other side.'))
  else if (edge.type === 'hierarchy') parts.push(t('Hierarchy: child → parent.'))
  if (edge.relationship || edge.type) parts.push(t('Relationship in schema: {kind}', { kind: edge.relationship || edge.type }))
  if (edge.instanceType) parts.push(t('Link table: {name}', { name: edge.instanceType }))
  if (edge.from_col || edge.to_col) parts.push(t('Key fields: {from} → {to}', { from: edge.from_col || '—', to: edge.to_col || '—' }))
  parts.push(t('Schema: {name}', { name: edge.schema }))
  return parts.join('\n')
}
</script>

<template>
  <section class="search-type-summary" :aria-label="t('Summary')">
    <section class="search-type-section"><div class="configuration-group">
      <dl class="search-type-metrics"><div v-for="[key, title] in metrics" :key="key"><dt>{{ t(title) }}</dt><dd :data-metric="key">{{ metadata.summary?.[key] ?? '—' }}</dd></div></dl>
      <p class="muted">{{ t('Totals include retired Search Objects. Shared system types are counted in their own database. Reload to update the summary.') }}</p>
    </div></section>
    <section v-if="metadata.relationshipGraph" class="search-type-section search-type-map-section"><h3>{{ t('Relationship map') }}</h3><p class="muted">{{ t('A read-only view of this Search Type and only its direct schema relationships.') }}</p><RelationshipMap :graph="metadata.relationshipGraph" /></section>
    <section class="search-type-section"><h3>{{ t('Schema relationships') }}</h3><p class="muted">{{ t(metadata.linkTable ? 'This is a link table for a many-to-many relationship, not a separate object category.' : "Relationships come from this project's schema and inherited schemas, not from table names.") }}</p><div class="configuration-group">
      <SettingRow control-id="type-data-location" title="Data location" :description="`${t('Database')}: ${metadata.database || '—'} · ${t('Table')}: ${metadata.table || '—'}\n${t(metadata.projectLocal ? 'Stored in the selected project' : 'Shared data outside the selected project')}`" />
      <SettingRow v-for="(edge, index) in metadata.relationships" :key="index" :control-id="'type-relation-' + index" :title="label(edge.from, catalog) + ' → ' + label(edge.to, catalog)" :description="description(edge)" />
      <p v-if="!metadata.relationships?.length" class="muted">{{ t('No explicit relationships for this type in the loaded schemas.') }}</p>
    </div></section>
  </section>
</template>
