<script setup>
// RepositoryEditorView.qml: 220px catalogue, selected repository, native Config draft owner.
import { computed, ref } from 'vue'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import AppTextField from '../../controls/AppTextField.vue'
import AppColorInput from '../../controls/AppColorInput.vue'
import AppIcon from '../../controls/AppIcon.vue'
const props = defineProps({ server:Object, repositories:Array, draft:Object, busy:Boolean })
const emit = defineEmits(['check'])
const selected = ref('default')
const entries = computed(() => {
  try { return [...new Set([...Object.keys(mapping('asset_base_dir')), ...Object.keys(mapping('base_dir_alias')), 'plugins'])].map(alias => ({ ...(props.repositories?.find(item => item.alias === alias) || {}), alias, path:root(alias) })) }
  catch { return props.repositories || [] }
})
const record = computed(() => entries.value.find(item => item.alias === selected.value) || entries.value[0])
function stored(key) { return props.server?.draft['checkin/' + key] ?? '' }
function mapping(key) { const raw = stored(key); return !raw ? {} : raw.startsWith('{') ? JSON.parse(raw) : { default:raw } }
const invalid = computed(() => { try { for (const key of ['asset_base_dir','base_dir_alias','web_base_dir','repository_display','win32_client_repo_dir','linux_client_repo_dir']) mapping(key); return false } catch { return true } })
function presentation(item) { try { return mapping('repository_display')[item.alias] || {} } catch { return {} } }
function title(item) { return presentation(item).title || item.title }
function update(key,field,value) {
  if (!record.value || invalid.value) return
  const entries = Object.assign(Object.create(null),mapping(key)), alias = record.value.alias
  if (field) entries[alias] = { ...entries[alias],[field]:value }
  else if (value.trim() || ['asset_base_dir','base_dir_alias'].includes(key)) entries[alias] = value
  else delete entries[alias]
  props.server.editSetting('checkin/' + key,Object.keys(entries).length ? JSON.stringify(entries) : '')
}
function path(key) { try { return mapping(key)[record.value?.alias] || '' } catch { return '' } }
function color() { const value = presentation(record.value).color; return Array.isArray(value) ? '#' + value.map(channel => channel.toString(16).padStart(2,'0')).join('') : value ? '#' + value.replace(/^#/,'') : '' }
function root(alias) { return mapping('base_dir_alias')[alias] || mapping('asset_base_dir')[alias] || props.repositories?.find(item => item.alias === alias)?.path || '' }
function enabled(alias) { return alias !== 'plugins' && (props.draft.enabledAliases === null || props.draft.enabledAliases.includes(alias)) }
function enable(alias,value) {
  props.draft.enabledAliases = entries.value.filter(item => item.alias !== 'plugins' && (item.alias === alias ? value : enabled(item.alias))).map(item => item.alias)
  if (!enabled(props.draft.defaultAlias)) props.draft.defaultAlias = props.draft.enabledAliases[0] || ''
}
function add() {
  let index = 0
  while(entries.value.some(item => item.alias === 'custom_' + index)) index++
  const alias = 'custom_' + index
  selected.value = alias
  const roots = Object.assign(Object.create(null),mapping('asset_base_dir')); roots[alias] = ''
  props.server.editSetting('checkin/asset_base_dir',JSON.stringify(roots))
  const urls = Object.assign(Object.create(null),mapping('web_base_dir')); urls[alias] = '/repository/' + alias
  props.server.editSetting('checkin/web_base_dir',JSON.stringify(urls))
  props.draft.enabledAliases = entries.value.filter(item => item.alias !== alias && enabled(item.alias)).map(item => item.alias)
}
function remove() {
  const alias = record.value.alias
  for(const key of ['asset_base_dir','base_dir_alias','web_base_dir','repository_display','win32_client_repo_dir','linux_client_repo_dir']) {
    const values = Object.assign(Object.create(null),mapping(key)); delete values[alias]
    props.server.editSetting('checkin/' + key,Object.keys(values).length ? JSON.stringify(values) : '')
  }
  if (props.draft.enabledAliases) props.draft.enabledAliases = props.draft.enabledAliases.filter(item => item !== alias)
  if (props.draft.defaultAlias === alias) props.draft.defaultAlias = entries.value.find(item => enabled(item.alias))?.alias || ''
}
</script>
<template>
  <div class="repository-editor-native">
    <nav class="repository-editor-catalog" :aria-label="t('Repositories')"><header><strong>{{ t('REPOSITORIES') }}</strong><AppButton icon="add" icon-only label="Add custom repository" :disabled="busy || invalid" @click="add" /></header><AppButton v-for="item in entries" :key="item.alias" :label="title(item)" :translate-label="false" :aria-pressed="record?.alias === item.alias" @click="selected = item.alias"><i :class="{ inactive:!enabled(item.alias) }" /><span><strong>{{ title(item) }}</strong><small class="muted">{{ item.alias }}</small></span></AppButton></nav>
    <section class="repository-editor-details"><p v-if="server?.error" class="error" role="alert">{{ t(server.error) }}</p><template v-if="record">
      <header><div><h3>{{ title(record) }}</h3><p class="muted">{{ t('Paths are stored in the server configuration') }}</p></div><AppCheckbox :model-value="enabled(record.alias)" :disabled="busy || record.alias === 'plugins'" label="Enabled" @update:model-value="enable(record.alias,$event)">{{ t('Enabled') }}</AppCheckbox><AppCheckbox :model-value="draft.defaultAlias === record.alias" :disabled="busy || !enabled(record.alias)" label="Default" @update:model-value="draft.defaultAlias = $event ? record.alias : entries.find(item => item.alias !== record.alias && enabled(item.alias))?.alias || record.alias">{{ t('Default') }}</AppCheckbox><AppButton v-if="record.alias.startsWith('custom_')" icon="delete" icon-only label="Remove custom repository" :disabled="busy || invalid" @click="remove" /></header>
      <p v-if="invalid" class="error" role="alert">{{ t('Fix the repository JSON in Advanced settings before editing these fields.') }}</p>
      <AppTextField :model-value="presentation(record).title || ''" label="Display name" placeholder="Display name" maxlength="100" :disabled="busy || invalid" @update:model-value="update('repository_display','title',$event)" />
      <AppTextField :model-value="root(record.alias)" label="Server repository path" placeholder="Server repository path" :readonly="record.alias === 'plugins'" :disabled="busy || invalid" @update:model-value="update(Object.hasOwn(mapping('base_dir_alias'),record.alias) ? 'base_dir_alias' : 'asset_base_dir',null,$event)" />
      <AppTextField :model-value="path('web_base_dir')" label="Repository web URL" placeholder="Repository web URL" :disabled="busy || invalid" @update:model-value="update('web_base_dir',null,$event)" />
      <AppTextField :model-value="path('win32_client_repo_dir')" label="Windows client path" placeholder="Windows client path" :disabled="busy || invalid" @update:model-value="update('win32_client_repo_dir',null,$event)" />
      <AppTextField :model-value="path('linux_client_repo_dir')" label="Linux client path" placeholder="Linux client path" :disabled="busy || invalid" @update:model-value="update('linux_client_repo_dir',null,$event)" />
      <div class="repository-editor-color"><span>{{ t('Color') }}</span><AppColorInput :model-value="color()" :disabled="busy || invalid" label="Repository color" @update:model-value="update('repository_display','color',$event)" /></div>
      <div class="repository-editor-path-policy"><strong>{{ t('SERVER STORAGE') }}</strong><p>{{ t('Enabled and Default apply to new browser check-ins. Changing server paths requires existing files at the new location and a server restart. Empty client paths fall back to the server root.') }}</p></div>
      <div class="repository-editor-status"><AppIcon :name="record.status === 'available' ? 'check-circle' : 'info'" /><span>{{ t(record.status === 'available' ? 'Available' : record.status === 'inaccessible' ? 'Folder not found or inaccessible' : 'Not checked') }}</span><AppButton label="Check paths" :disabled="busy" @click="emit('check',Object.fromEntries(entries.filter(item => item.alias !== 'plugins').map(item => [item.alias,root(item.alias)])))" /></div>
      </template>
      <details class="repository-editor-advanced"><summary>{{ t('Advanced settings') }}</summary><slot /></details>
    </section>
  </div>
</template>
<style>
.repository-editor-native { display:grid; grid-template-columns:min(220px,34%) minmax(0,1fr); gap:12px; min-height:450px; }
.repository-editor-catalog { background:var(--surface-high); border:1px solid var(--outline-variant); border-radius:12px; padding:8px; }
.repository-editor-catalog > header { display:flex; align-items:center; justify-content:space-between; padding:6px 8px 4px; font-size:12px; color:var(--muted); }
.repository-editor-catalog > .app-button { display:flex; width:100%; height:54px; min-height:54px; margin-top:4px; gap:9px; padding:0 10px; border:0; border-radius:10px; background:transparent; justify-content:flex-start; text-align:left; }
.repository-editor-catalog > .app-button[aria-pressed=true] { background:var(--content-selection); }.repository-editor-catalog > .app-button:hover { background:var(--hover); }
.repository-editor-catalog > .app-button > i { width:8px; height:8px; flex-shrink:0; border-radius:50%; background:var(--primary); }
.repository-editor-catalog > .app-button > i.inactive { background:var(--muted); }
.repository-editor-catalog > .app-button > span { display:grid; gap:1px; min-width:0; }.repository-editor-catalog strong { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-weight:600; }.repository-editor-catalog small { font-size:12px; }
.repository-editor-details { padding:16px; border:1px solid var(--outline-variant); border-radius:12px; display:flex; flex-direction:column; gap:12px; background:var(--page); }
.repository-editor-details > header { display:flex; gap:10px; align-items:center; }.repository-editor-details > header > div { flex:1; }.repository-editor-details h3 { font-size:17px; font-weight:600; }.repository-editor-details > header p { margin-top:2px; }
.repository-editor-details > .app-text-field { width:100%; flex-shrink:0; }.repository-editor-color { display:flex; gap:12px; align-items:center; justify-content:space-between; }.repository-editor-color > .app-color-input { flex:0 1 auto; }
.repository-editor-path-policy { padding:12px; background:var(--surface-high); border:1px solid var(--outline-variant); border-radius:10px; }.repository-editor-path-policy strong { font-size:12px; color:var(--muted); }.repository-editor-path-policy p { margin-top:4px; }
.repository-editor-status { display:flex; align-items:center; gap:8px; }.repository-editor-status > span:not(.app-icon) { flex:1; }.repository-editor-status .app-icon { font-size:17px; }
.repository-editor-advanced > summary { cursor:pointer; }.repository-editor-advanced > div { margin-top:12px; }
@media(max-width:700px) { .repository-editor-native { grid-template-columns:minmax(0,1fr); }.repository-editor-catalog { display:flex; flex-wrap:wrap; }.repository-editor-catalog > .app-button { width:auto; } }
</style>
