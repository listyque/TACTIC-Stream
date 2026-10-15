<script setup>
// ConfigurationRepositoryPage.qml: repository summary, editor and native path check.
import { computed, onMounted, ref } from 'vue'
import { rpc } from '../../api.js'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import SettingRow from '../../controls/SettingRow.vue'
import SummaryChip from '../../controls/SummaryChip.vue'
import { preferences } from './preferences.js'
const props = defineProps({ ticket:String, busy:Boolean })
const emit = defineEmits(['edit','session-expired'])
const records = ref([]), platform = ref(''), checking = ref(false), error = ref('')
const current = computed(() => records.value.find(item => item.alias === preferences.repository.defaultAlias) || records.value.find(item => item.is_default))
async function load(action = 'load', paths) {
  if (checking.value) return
  checking.value = true; error.value = ''
  try { const result = await rpc('execute_cmd',[{ ticket:props.ticket,project:'admin' },'tactic.ui.app.RepositoryPathsCmd',{ action,...(paths ? { paths } : {}) }],{},true); records.value = result.info.repositories; platform.value = result.info.platform; return true }
  catch (failure) { if (failure.code === 'authentication_failed') emit('session-expired'); error.value = failure.message; return false }
  finally { checking.value = false }
}
onMounted(() => load())
defineExpose({ load,records,checking })
</script>
<template>
  <section class="content repository-settings" :aria-busy="checking">
    <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
    <section class="settings-section"><header><h2>{{ t('Repository storage') }}</h2><p class="muted">{{ t('Snapshots, previews, check-in and check-out depend on a valid repository path.') }}</p></header><div class="configuration-group">
      <SettingRow :title="current?.title || 'Repository configuration is loading'" :description="current?.path"><SummaryChip :label="t(current ? 'Configured' : 'Loading')" :show-count="false" :accent="current ? 'var(--success)' : undefined" /></SettingRow>
      <SettingRow title="Repository definitions" description="Configure server roots, repository aliases, labels and client paths."><div class="repository-definition-actions"><AppButton label="Open Repository Editor" icon="database" :disabled="busy || checking" @click="emit('edit')" /><AppButton :label="checking ? 'Checking…' : 'Check paths'" icon="check" :disabled="busy || checking || !records.length" @click="load('check')" /></div></SettingRow>
    </div></section>
    <section class="settings-section"><header><h2>{{ t('Active repositories') }}</h2><p class="muted">{{ t('The default repository is used when an operation does not choose another destination explicitly.') }}</p></header><div class="configuration-group">
      <SettingRow v-for="item in records.filter(item => item.alias !== 'plugins' && (preferences.repository.enabledAliases === null || preferences.repository.enabledAliases.includes(item.alias)))" :key="item.alias" :title="item.title" :description="item.path"><div class="repository-chips"><SummaryChip :label="item.alias === current?.alias ? t('Default') : item.alias" :accent="/^#[a-f\d]{6}$/i.test(item.color) ? item.color : undefined" :show-count="false" /><SummaryChip v-if="item.status !== 'unchecked'" :label="t(item.status === 'available' ? 'Available' : 'Folder not found or inaccessible')" :show-count="false" :accent="item.status === 'available' ? 'var(--success)' : 'var(--error)'" /></div></SettingRow>
    </div><p class="muted">{{ t('Paths are checked by the server account ({platform}). Missing configured folders are created; existing files are preserved.', { platform }) }}</p></section>
  </section>
</template>
<style>.repository-definition-actions { display:flex; gap:8px; }.configuration-native .repository-settings .settings-row { grid-template-columns:minmax(0,1fr) auto; }.repository-chips { display:flex; align-items:center; gap:8px; }.repository-settings { gap:22px; }</style>
