<script>
import { useId } from 'vue'
import { t } from '../../i18n.js'
import { fieldGroups } from '../../workflowFields.js'
import AppIcon from '../../controls/AppIcon.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppSwitch from '../../controls/AppSwitch.vue'
import SettingRow from '../../controls/SettingRow.vue'

export default {
  components: { AppIcon, AppSelect, AppSwitch, SettingRow },
  props: { node: Object, settings: Object, properties: Object, metadata: Object, document: Object, identity: String, editable: Boolean },
  emits: ['setting', 'attribute', 'dependencies', 'open', 'description', 'error'],
  setup() { return { uid: useId() } },
  data() { return { subpipelineSearch: '' } },
  computed: {
    defaults() { return this.settings.default || {} },
    groups() { return fieldGroups.filter(group => !group.kinds || group.kinds.includes(this.node.kind)) },
    taskNode() { return ['manual', 'node', 'approval'].includes(this.node.kind) },
    actionNode() { return ['action', 'condition'].includes(this.node.kind) },
    taskPipelines() { return [{ value: '', label: 'Use TACTIC default' }, ...this.metadata.pipelines.filter(row => row.searchType === 'sthpw/task').map(row => ({ value: row.identity, label: row.label }))] },
    subpipelines() { return this.metadata.pipelines.filter(row => row.identity !== this.identity && row.searchType === this.document.searchType && `${row.label} ${row.identity}`.toLowerCase().includes(this.subpipelineSearch.toLowerCase())) },
    modes() { return [
      { value: '', label: 'Not set' }, { value: 'same process,same transaction', label: 'Same transaction' },
      { value: 'separate process,blocking', label: 'Separate process, wait' }, { value: 'separate process,non-blocking', label: 'Separate process, background' },
      { value: 'separate process,queued', label: 'Queued' },
    ] },
  },
  methods: {
    t,
    section(field) { return field.section ?? (this.node.kind === 'progress' ? 'progress' : 'default') },
    value(field) { const section = this.section(field); return (section === 'properties' ? this.properties : section ? this.settings[section] : this.settings)?.[field.key] ?? field.initial ?? '' },
    options(field) {
      let rows = field.choices || this.metadata[field.options] || []
      const related = this.settings[this.node.kind === 'progress' ? 'progress' : 'default'] || {}
      if (field.options === 'relatedPipelines') rows = this.metadata.pipelines.filter(row => row.searchType === related.related_search_type)
      if (field.options === 'relatedProcesses') rows = this.metadata.processes.filter(row => row.pipeline === related.related_pipeline_code).map(row => ({ identity: this.node.kind === 'progress' ? row.identity : row.label, label: row.label }))
      return [{ value: '', label: 'Not set' }, ...rows.map(row => ({ value: row.identity, label: row.label }))]
    },
    update(field, value) {
      if (field.editor === 'integer' && value !== '') {
        value = Number(value)
        if (!Number.isInteger(value) || value < (field.minimum || 0) || value > (field.maximum || 1000000)) { this.$emit('error', 'Enter a whole number within the allowed range'); return }
      }
      this.$emit('setting', this.section(field), field.key, value)
    },
  },
}
</script>

<template>
  <fieldset class="workflow-process-settings" :disabled="!editable">
    <div class="configuration-group">
      <SettingRow :control-id="uid + '-process-description'" title="Description" description="Explain what happens at this stage of the workflow."><textarea :id="uid + '-process-description'" :value="document.processDescriptions[node.identity] || ''" rows="3" @input="$emit('description', $event.target.value)" /></SettingRow>
      <SettingRow v-if="document.searchType !== 'sthpw/task'" :control-id="uid + '-process-kind'" title="Node type" description="Choose the native behavior of this process."><AppSelect :id="uid + '-process-kind'" :model-value="node.kind" :options="metadata.nodeTypes.map(value => ({ value, label: value }))" label="Node type" @update:model-value="$emit('attribute', 'type', $event)" /></SettingRow>
    </div>
    <div v-for="group in groups" :key="group.title" class="configuration-group">
      <h3>{{ t(group.title) }}</h3><p v-if="group.description" class="muted">{{ t(group.description) }}</p>
      <SettingRow v-for="field in group.fields.filter(field => !field.kinds || field.kinds.includes(node.kind))" :key="field.key" :control-id="uid + '-process-' + field.key" :title="field.label" :description="field.help">
        <AppSwitch v-if="field.editor === 'boolean'" :id="uid + '-process-' + field.key" :model-value="value(field) === true || value(field) === 'true'" :label="field.label" @update:model-value="update(field, $event)" />
        <AppSelect v-else-if="!field.editor" :id="uid + '-process-' + field.key" :model-value="value(field)" :options="options(field)" :label="field.label" @update:model-value="update(field, $event)" />
        <input v-else :id="uid + '-process-' + field.key" :type="field.editor === 'integer' ? 'number' : 'text'" :value="value(field)" :min="field.minimum || 0" :max="field.maximum || 1000000" :pattern="field.editor === 'color' ? '#[0-9a-fA-F]{6}' : undefined" :aria-describedby="uid + '-process-' + field.key + '-help'" @change="update(field, $event.target.value)" />
      </SettingRow>
    </div>
    <div v-if="taskNode" class="configuration-group">
      <h3>{{ t('Task status workflow') }}</h3><p class="muted">{{ t('Defines statuses only for tasks of this process, not stages of the parent Search Object workflow.') }}</p>
      <SettingRow :control-id="uid + '-process-task-pipeline'" title="Task status workflow" description="Choose a project or shared task status pipeline."><AppSelect :id="uid + '-process-task-pipeline'" :model-value="properties.task_pipeline || ''" :options="taskPipelines" label="Task status workflow" @update:model-value="$emit('setting', 'properties', 'task_pipeline', $event)" /></SettingRow>
      <button type="button" :disabled="!properties.task_pipeline" @click="$emit('open', properties.task_pipeline)"><AppIcon name="workflow" />{{ t('Edit task status workflow') }}</button>
    </div>
    <div v-if="actionNode" class="configuration-group">
      <h3>{{ t('Process action') }}</h3><p class="muted">{{ t('Action and condition nodes use a native process|action trigger. Script changes are saved, not executed by this editor.') }}</p>
      <SettingRow :control-id="uid + '-process-action'" title="Action" description="Use a script or an installed server command class."><AppSelect :id="uid + '-process-action'" :model-value="defaults.action === 'command' ? 'command' : 'create_new'" :options="[{ value: 'create_new', label: 'Script' }, { value: 'command', label: 'Command class' }]" label="Action" @update:model-value="$emit('setting', 'default', 'action', $event)" /></SettingRow>
      <SettingRow v-if="defaults.action === 'command'" :control-id="uid + '-process-command'" title="Native command class" description="The installed Python command that handles this action."><input :id="uid + '-process-command'" :value="defaults.on_action_class || ''" @input="$emit('setting', 'default', 'on_action_class', $event.target.value)" /></SettingRow>
      <template v-else>
        <SettingRow :control-id="uid + '-process-script-path'" title="Script path (optional)" description="Use an existing server script, or provide a script body below."><input :id="uid + '-process-script-path'" :value="defaults.script_path || ''" @input="$emit('setting', 'default', 'script_path', $event.target.value.replaceAll('\\', '/'))" /></SettingRow>
        <SettingRow :control-id="uid + '-process-language'" title="Script language" description="The language used by the native server handler."><AppSelect :id="uid + '-process-language'" :model-value="defaults.language || 'python'" :options="[{ value: 'python', label: 'python' }, { value: 'server_js', label: 'server_js' }]" label="Script language" @update:model-value="$emit('setting', 'default', 'language', $event)" /></SettingRow>
        <SettingRow :control-id="uid + '-process-script'" title="Script body" description="The code is stored with this process. Applying the draft does not run it."><textarea :id="uid + '-process-script'" :value="defaults.script || ''" rows="12" spellcheck="false" @input="$emit('setting', 'default', 'script', $event.target.value)" /></SettingRow>
      </template>
      <SettingRow :control-id="uid + '-process-mode'" title="Trigger execution mode" description="Use the execution mode supported by the installed server handler."><AppSelect :id="uid + '-process-mode'" :model-value="defaults.execute_mode || ''" :options="modes" label="Trigger execution mode" @update:model-value="$emit('setting', 'default', 'execute_mode', $event)" /></SettingRow>
    </div>
    <div v-if="node.kind === 'hierarchy'" class="configuration-group">
      <h3>{{ t('Subpipeline') }}</h3><p class="muted">{{ t('Choose the pipeline this hierarchy process opens.') }}</p>
      <label>{{ t('Find a pipeline') }}<input v-model="subpipelineSearch" type="search" /></label>
      <AppSelect :model-value="settings.hierarchy?.subpipeline || ''" :options="[{ value: '', label: 'Not set' }, ...subpipelines.map(row => ({ value: row.identity, label: row.label }))]" label="Subpipeline" @update:model-value="$emit('setting', 'hierarchy', 'subpipeline', $event)" />
      <SettingRow :control-id="uid + '-process-hierarchy-tasks'" title="Create tasks" description="Choose which tasks are generated for a hierarchy node."><AppSelect :id="uid + '-process-hierarchy-tasks'" :model-value="defaults.task_creation || 'subtasks_only'" :options="[{ value: 'subtasks_only', label: 'Create subtasks only' }, { value: 'top_only', label: 'Create parent task only' }, { value: 'all', label: 'Create parent task and subtasks' }, { value: 'none', label: 'Do not create tasks' }]" label="Create tasks" @update:model-value="$emit('setting', 'default', 'task_creation', $event)" /></SettingRow>
    </div>
  </fieldset>
  <div class="configuration-group"><h3>{{ t('Process dependencies') }}</h3><p class="muted">{{ t('Triggers, notifications, naming conventions and objects using this pipeline. Save node changes before editing dependencies.') }}</p><button type="button" @click="$emit('dependencies')"><AppIcon name="link" />{{ t('Open process dependencies') }}</button></div>
</template>
