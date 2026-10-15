<script setup>
// ConfigurationProjectPage.qml: catalogue, explicit activation, edit, template and creation.
import { computed, onMounted, ref } from 'vue'
import { projectCatalog, rpc } from '../../api.js'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import ProjectChooser from '../projects/ProjectChooser.vue'
import ProjectCreation from '../projects/ProjectCreation.vue'
import RecordForm from '../objects/RecordForm.vue'
const props = defineProps({ ticket:String, project:String, canAdminister:Boolean, openProject:Function })
const emit = defineEmits(['changed'])
const projects = ref([]), selected = ref(''), editor = ref(null), creator = ref(null), busy = ref(false), error = ref('')
const item = computed(() => projects.value.find(item => item.code === selected.value))
const editable = computed(() => props.canAdminister && item.value && !item.value.__builtin__ && !busy.value)
async function load() { busy.value = true; error.value = ''; try { projects.value = await projectCatalog(props.ticket) } catch (failure) { error.value = failure.message } finally { busy.value = false } }
async function activate(code) { if (busy.value) return; busy.value = true; error.value = ''; try { if (await props.openProject(code) === false) error.value = 'The project could not be activated.' } catch (failure) { error.value = failure.message } finally { busy.value = false } }
async function changed() { await load(); emit('changed') }
async function created(code) { if (await props.openProject(code) === false) throw new Error('The project could not be activated.'); selected.value = code; await changed() }
async function archive() {
  if (!editable.value) return
  busy.value = true; error.value = ''
  try {
    const result = await rpc('execute_cmd', [{ ticket:props.ticket, project:'admin', language:'python' }, 'tactic.ui.app.ProjectTemplateExportCmd', { project_code:item.value.code }])
    const link = document.createElement('a'); link.href = '/assets/_cache/' + encodeURIComponent(props.ticket) + '/' + encodeURIComponent(result.info.filename); link.download = result.info.filename; link.click()
  } catch (failure) { error.value = failure.message } finally { busy.value = false }
}
onMounted(load)
</script>
<template>
  <section class="content configuration-projects" :aria-busy="busy">
    <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
    <section class="settings-section project-catalog-section"><header><h2>{{ t('Available projects') }}</h2><p class="muted">{{ t('Select a project to make it active in the workspace.') }}</p></header><div class="configuration-group"><ProjectChooser inline :projects="projects" :selected="selected" @selected="selected = $event" /></div></section>
    <section class="settings-section project-selection-section"><header><h2>{{ t('Project actions') }}</h2></header><div class="configuration-group">
      <small class="muted">{{ t('CURRENT') }}</small><h3>{{ projects.find(item => item.code === project)?.title || t('No active project') }}</h3>
      <p>{{ item?.title || t('Select a project') }} <code v-if="item">{{ item.code }}</code></p>
      <div class="project-settings-actions">
        <AppButton label="Activate selected project" icon="check" :disabled="!item || busy || item.code === project" @click="activate(item.code)" />
        <AppButton label="Edit selected project" icon="edit" :disabled="!editable" @click="editor.open(item.__search_key__)" />
        <AppButton label="Deactivate current project" icon="close" :disabled="!project || busy" @click="activate('')" />
        <AppButton label="Create template archive" icon="download" :disabled="!editable" @click="archive" />
        <AppButton label="Create new project" icon="add" :disabled="!canAdminister || busy" @click="creator.open()" />
        <AppButton label="Refresh projects" icon="refresh" :disabled="busy" @click="load" />
      </div>
    </div></section>
    <RecordForm ref="editor" :ticket="ticket" project="admin" search-type="sthpw/project" @saved="changed" />
    <ProjectCreation ref="creator" :ticket="ticket" :open-project="created" />
  </section>
</template>
<style>
.configuration-projects { display:grid; grid-template-columns:minmax(0, 1fr) 270px; gap:14px; }
.configuration-projects > [role=alert] { grid-column:1 / -1; }
.project-settings-actions { display:grid; gap:8px; margin-top:16px; }
.project-settings-actions > .app-button { justify-content:flex-start; }
.project-catalog-inline { position:static; width:100%; height:auto; max-width:none; max-height:none; margin:0; padding:0; border:0; border-radius:0; background:transparent; opacity:1; transform:none; box-shadow:none; }
.project-catalog-inline .project-cards { grid-template-columns:repeat(auto-fill, minmax(190px, 1fr)); }
.project-catalog-inline .project-categories { max-height:none; }
@container (max-width:900px) { .configuration-projects { grid-template-columns:minmax(0,1fr); }.project-settings-actions { display:flex; flex-wrap:wrap; } }
</style>
