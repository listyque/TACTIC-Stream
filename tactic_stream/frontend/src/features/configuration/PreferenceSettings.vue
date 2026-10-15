<script setup>
// Configuration pages compose the shared SettingsRow/controls; values remain a draft until Apply/Save.
import { computed, useId } from 'vue'
import { t } from '../../i18n.js'
import AppSelect from '../../controls/AppSelect.vue'
import AppSwitch from '../../controls/AppSwitch.vue'
import AppButton from '../../controls/AppButton.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import SettingRow from '../../controls/SettingRow.vue'
import { resultViews } from '../workspace/resultViews.js'
const props = defineProps({ page:String, draft:Object, busy:Boolean })
const uid = useId()
const options = (values, labels) => values.map((value, index) => ({ value, label:labels[index] }))
const sections = computed(() => props.page === 'checkin' ? [
  { title:'Search results', description:'Choose how result items are loaded and initially presented.', fields:[
    { key:'displayLimit', title:'Result limit', description:'Maximum number of sObjects requested for one search result page.', kind:'number', min:1, max:500 },
    { key:'loadingMode', title:'Loading mode', description:'Use explicit result pages or load the next page when scrolling reaches the end.', options:options(['pages','infinite'],['Pages','Infinite scroll']) },
    { key:'defaultViewMode', title:'Default result view', description:'Initial presentation used when a search tab has no saved view state.', options:resultViews },
  ] },
  { title:'File matching and naming', description:'Defaults used when preparing a new browser check-in.', fields:[
    { key:'groupCheckin', title:'Group selected files', description:'Combine the selected files into one snapshot instead of preparing a snapshot for each file.' },
    { key:'keepFilename', title:'Keep original filename', description:'Preserve source filenames instead of applying the active naming template.' },
    { key:'generatePreviews', title:'Generate previews', description:'Create web and icon images on the server during check-in.' },
    { key:'confirmRevision', title:'Confirm revision replacement', description:'Require explicit confirmation before replacing files in an existing revision.' },
    { key:'commitQueueAutoClean', title:'Clean completed check-ins', description:'Remove successful rows from Commit Queue after each completed batch. Failed and uncertain rows remain available.' },
  ] },
] : props.page === 'tasks' ? [
  { title:'Task workspace defaults', description:'Initial task surface, presentation, ordering and grouping.', fields:[
    { key:'workspaceSurface', title:'Initial task surface', description:'Open Quick Tasks or the detailed Task Browser first.', options:options(['quick','browser'],['Quick Tasks','Task Browser']) },
    { key:'quickViewMode', title:'Quick Tasks presentation', description:'Show editable process cards or a compact task list.', options:options(['cards','compact'],['Cards','Compact list']) },
    { key:'viewMode', title:'Initial view', description:'View opened first when Task Browser has no saved local state.', options:options(['table','gantt'],['Table','Gantt']) },
    { key:'sortMode', title:'Initial sorting', description:'Default order used before the user applies a table or column sort.', options:options(['due','recent','process','user','status','object','search_type','project','priority','milestone','supervisor'],['Deadline','Recently changed','Process','Assignee','Status','Object','Search Type','Project','Priority','Milestone','Supervisor']) },
    { key:'groupMode', title:'Initial grouping', description:'Default task groups before a workspace preference is saved.', options:options(['none','process','user','status','object'],['No grouping','Process','Assignee','Status','Object']) },
    { key:'inspectorExpanded', title:'Expand task details', description:'Initial state of task details in Task Inspector. Saved account preferences take priority.' },
  ] },
] : props.page === 'global' ? [
  { title:'Notifications', description:'Choose which incoming events show a notification. Their history remains available.', fields:[
    { key:'activityNotifications', title:'Activity feed notifications', description:'Show notifications for incoming project activity.' },
    { key:'messageNotifications', title:'Message notifications', description:'Show notifications for incoming messages.' },
  ] },
] : [
  { title:'Workspace cache', description:'Control retained presentation state independently of server records.', fields:[
    { key:'cacheProcessTabs', title:'Remember process expansion', description:'Restore expanded objects, processes and version branches when reopening saved search tabs.' },
  ] },
])
function move(index, direction) { const target = index + direction; if (target < 0 || target >= props.draft.columns.length) return; const column = props.draft.columns.splice(index,1)[0]; props.draft.columns.splice(target,0,column) }
</script>
<template>
  <section class="content preference-settings">
    <section v-for="section in sections" :key="section.title" class="settings-section"><header><h2>{{ t(section.title) }}</h2><p class="muted">{{ t(section.description) }}</p></header><div class="configuration-group">
      <SettingRow v-for="field in section.fields" :key="field.key" :control-id="uid + '-' + field.key" :title="field.title" :description="field.description">
        <AppSelect v-if="field.options" :id="uid + '-' + field.key" v-model="draft[field.key]" :options="field.options" :label="field.title" :disabled="busy" :aria-describedby="uid + '-' + field.key + '-help'" />
        <input v-else-if="field.kind === 'number'" :id="uid + '-' + field.key" v-model.number="draft[field.key]" type="number" :min="field.min" :max="field.max" :aria-label="t(field.title)" :aria-describedby="uid + '-' + field.key + '-help'" :disabled="busy">
        <AppSwitch v-else :id="uid + '-' + field.key" v-model="draft[field.key]" :label="field.title" :disabled="busy" :aria-describedby="uid + '-' + field.key + '-help'" />
      </SettingRow>
    </div></section>
    <section v-if="page === 'tasks'" class="settings-section"><header><h2>{{ t('Task Browser columns') }}</h2><p class="muted">{{ t('Default order, visibility and width. Saved project layouts take priority.') }}</p></header><div class="configuration-group task-default-columns">
      <div v-for="(column, index) in draft.columns" :key="column.key" class="task-default-column">
        <AppCheckbox v-model="column.visible" :label="column.label" :disabled="column.key === 'object' || busy"><span>{{ t(column.label) }}</span></AppCheckbox>
        <input v-model.number="column.width" type="number" min="40" max="480" :aria-label="t('Width of {column}', { column:t(column.label) })" :disabled="busy">
        <AppButton icon-only icon="up" label="Move column up" :disabled="index === 0 || busy" @click="move(index, -1)" />
        <AppButton icon-only icon="down" label="Move column down" :disabled="index === draft.columns.length - 1 || busy" @click="move(index, 1)" />
      </div>
    </div><p class="muted">{{ t('Task scope, filters, collapsed groups, calendar position and the selected task resume separately for each project. Checked tasks and unsaved edits are never restored.') }}</p></section>
    <p v-if="page === 'checkin'" class="muted">{{ t('Browser check-in uploads files to the server. Local move/copy, opening associated desktop applications and directory scanning require a desktop client.') }}</p>
  </section>
</template>
<style>
.preference-settings { gap:14px; }
.task-default-column { display:flex; align-items:center; gap:8px; min-height:44px; border-bottom:1px solid var(--outline-variant); }
.task-default-column:last-child { border-bottom:0; }
.task-default-column > .app-checkbox { flex:1; }
.task-default-column input[type=number] { width:80px; flex:0 0 80px; }
</style>
