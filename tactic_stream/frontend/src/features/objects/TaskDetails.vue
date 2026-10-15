<script setup>
import AppButton from '../../controls/AppButton.vue'
import TaskField from './TaskField.vue'
import StatusSelect from '../../controls/StatusSelect.vue'
import UserComboBox from '../../controls/UserComboBox.vue'
import AppSlider from '../../controls/AppSlider.vue'
import { computed } from 'vue'
import { t } from '../../i18n.js'

const props = defineProps({ editor: Object, draft: Object, expanded: Boolean, editing: Boolean, busy: Boolean, dirty: Boolean, pendingAction: String, assignee: String, processTitle:String })
const emit = defineEmits(['edit', 'create', 'discard', 'save', 'change', 'confirm-action', 'cancel-action', 'assignee'])
const titles = { status: 'Status', assigned: 'Assigned to', supervisor: 'Supervisor', bid_start_date: 'Start date',
  bid_end_date: 'End date', bid_duration: 'Planned hours', completion: 'Progress', progress: 'Progress', description: 'Description' }
const quickFields = computed(() => props.editor.fields.filter(field => ['status','assigned','bid_start_date','bid_end_date'].includes(field.name)))
const progress = computed(() => props.editor.fields.find(field => ['progress','completion'].includes(field.name)))
const values = computed(() => props.draft)
const assigned = computed(() => props.editor.users.find(user=>user.value === values.value.assigned)?.displayName || values.value.assigned)
</script>

<template>
  <section v-show="expanded || pendingAction || editing" class="task-details inspector-task-surface" :class="{ 'full-editor':editing || pendingAction }" :data-has-task="!!editor.selected_task">
    <header><div class="inspector-task-caption"><strong>{{ editor.selected_task ? (editor.task_context && editor.task_context !== editor.process ? editor.task_context : t('{process} task',{process:processTitle})) : t('No task for {process}',{process:processTitle}) }}</strong><small v-if="editor.selected_task && assigned">{{ assigned }}</small></div>
      <div class="configuration-actions">
        <AppButton v-if="editor.selected_task && !editing" label="Edit task" icon="edit" icon-only :disabled="busy" @click="emit('edit')" />
        <AppButton v-if="editor.process_available && !editing" label="Create task" icon="add" icon-only :disabled="busy" @click="emit('create')" />
        <AppButton v-if="dirty && !editing" label="Discard task changes" icon="undo" icon-only :disabled="busy" @click="emit('discard')" />
        <AppButton v-if="!editing && (dirty || !editor.selected_task && editor.process_available)" :label="editor.selected_task ? 'Save task' : 'Create task'" icon="save" icon-only :disabled="busy" @click="emit('save')" />
</div></header>
    <div v-if="pendingAction" class="notice">
      <template v-if="pendingAction === 'copy'"><p>{{ t('Create a separate task for another assignee in this process.') }}</p>
        <label>{{ t('Assigned to') }}<UserComboBox :value="assignee" :options="editor.users" :action-field="false" label="Assigned to" :disabled="busy" @change="emit('assignee', $event)" /></label></template>
      <p v-else>{{ t('Delete the selected task? Its notes and files will not be deleted.') }}</p>
      <div class="configuration-actions"><AppButton :label="pendingAction === 'copy' ? 'Create task copy' : 'Delete task'" :icon="pendingAction === 'copy' ? 'copy' : 'delete'" :destructive="pendingAction === 'delete'" :disabled="busy" @click="emit('confirm-action')" />
        <AppButton label="Cancel" :disabled="busy" @click="emit('cancel-action')" /></div>
    </div>
    <div v-if="!editing && (editor.selected_task || editor.process_available)" class="inspector-quick-fields">
      <template v-for="field in quickFields" :key="field.name">
        <StatusSelect v-if="field.name === 'status'" :value="values.status || ''" :options="editor.status_choices || editor.statuses.map(value=>({value,label:value}))" :disabled="busy || !field.editable" @change="emit('change','status',$event)" />
        <UserComboBox v-else-if="field.name === 'assigned'" :value="values.assigned || ''" :options="editor.users" :disabled="busy || !field.editable" @change="emit('change','assigned',$event)" />
        <TaskField v-else :field="field" :value="values[field.name]" :statuses="editor.statuses" :users="editor.users" :busy="busy" @change="emit('change',field.name,$event)" />
      </template>
    </div>
    <div v-if="!editing && (editor.selected_task || editor.process_available)" class="inspector-progress"><small>{{ t('Progress') }}</small><AppSlider :model-value="Number(values[progress?.name] || 0)" label="Progress" :disabled="busy || !progress?.editable" @update:model-value="emit('change',progress.name,$event)" /><strong>{{ Math.round(Number(values[progress?.name] || 0)) }}%</strong></div>
    <div v-if="editing" class="task-detail-fields">
      <label v-for="field in editor?.fields || []" :key="field.name" :data-task-field="field.name"><span>{{ t(titles[field.name] || field.name) }}</span>
        <TaskField :field="field" :value="draft[field.name]" :statuses="editor.statuses" :users="editor.users" :busy="busy" @change="emit('change', field.name, $event)" />
      </label>
      <footer v-if="editing"><AppButton label="Discard task changes" icon="close" :disabled="busy" @click="emit('discard')" />
        <AppButton label="Save task" icon="save" highlighted :disabled="busy || (!dirty && !!editor.selected_task)" @click="emit('save')" /></footer>
    </div>
  </section>
</template>
