<script setup>
import ObjectInspectorQuick from './ObjectInspectorQuick.vue';
import AppButton from '../../controls/AppButton.vue';
import TaskField from './TaskField.vue';
import StatusSelect from '../../controls/StatusSelect.vue';
import UserComboBox from '../../controls/UserComboBox.vue';
import AppSlider from '../../controls/AppSlider.vue';
import { computed } from 'vue';
import { t } from '../../i18n.js';

const props = defineProps({
  editor: Object,
  draft: Object,
  expanded: Boolean,
  editing: Boolean,
  busy: Boolean,
  dirty: Boolean,
  pendingAction: String,
  assignee: String,
  processTitle: String
});
const emit = defineEmits([
  'edit',
  'full-edit',
  'create',
  'discard',
  'save',
  'change',
  'confirm-action',
  'cancel-action',
  'assignee'
]);
const titles = {
  status: 'Status',
  assigned: 'Assigned to',
  supervisor: 'Supervisor',
  bid_start_date: 'Start date',
  bid_end_date: 'End date',
  bid_duration: 'Planned hours',
  completion: 'Progress',
  progress: 'Progress',
  description: 'Description'
};
const quickFields = computed(() =>
  props.editor.fields.filter((field) =>
    ['status', 'assigned', 'bid_start_date', 'bid_end_date'].includes(
      field.name
    )
  )
);
const progress = computed(() =>
  props.editor.fields.find((field) =>
    ['progress', 'completion'].includes(field.name)
  )
);
const values = computed(() => props.draft);
const assigned = computed(
  () =>
    props.editor.users.find((user) => user.value === values.value.assigned)
      ?.displayName || values.value.assigned
);
const quickModel = computed(() => {
  const field = (name) =>
    props.editor.fields.find((field) => field.name === name);
  return {
    hasTask: !!props.editor.selected_task,
    canCreate: props.editor.process_available,
    canEdit: !!props.editor.selected_task || props.editor.process_available,
    title: props.editor.selected_task
      ? props.editor.task_context &&
        props.editor.task_context !== props.editor.process
        ? props.editor.task_context
        : t('{process} task', { process: props.processTitle })
      : '',
    processLabel: props.processTitle,
    assignedLabel: assigned.value,
    dirty: props.dirty,
    busy: props.busy,
    status: values.value.status,
    statuses:
      props.editor.status_choices ||
      props.editor.statuses.map((value) => ({ value, label: value })),
    assigned: values.value.assigned,
    users: props.editor.users,
    start: values.value.bid_start_date,
    end: values.value.bid_end_date,
    progress: values.value[progress.value?.name] || 0,
    statusEditable: !!field('status')?.editable,
    assignedEditable: !!field('assigned')?.editable,
    startEditable: !!field('bid_start_date')?.editable,
    endEditable: !!field('bid_end_date')?.editable,
    progressEditable: !!progress.value?.editable
  };
});
function event(action) {
  if (action.type === 'change')
    emit(
      'change',
      {
        start: 'bid_start_date',
        end: 'bid_end_date',
        progress: progress.value?.name
      }[action.field] || action.field,
      action.value
    );
  else emit(action.type === 'edit' ? 'full-edit' : action.type);
}
</script>

<template>
  <section
    v-show="expanded || pendingAction || editing"
    class="task-details inspector-task-surface"
    :class="{
      'full-editor': editing || pendingAction,
      'shared-task-quick': !editing && !pendingAction
    }"
    :data-has-task="!!editor.selected_task"
  >
    <ObjectInspectorQuick
      v-if="!editing && !pendingAction"
      :model="quickModel"
      @event="event"
    />
    <header v-else>
      <div class="inspector-task-caption">
        <strong>{{
          editor.selected_task
            ? editor.task_context && editor.task_context !== editor.process
              ? editor.task_context
              : t('{process} task', { process: processTitle })
            : t('No task for {process}', { process: processTitle })
        }}</strong
        ><small v-if="editor.selected_task && assigned">{{ assigned }}</small>
      </div>
      <div class="configuration-actions">
        <AppButton
          v-if="editor.selected_task && !editing"
          label="Edit task"
          icon="edit"
          icon-only
          :disabled="busy"
          @click="emit('edit')"
        />
        <AppButton
          v-if="editor.process_available && !editing"
          label="Create task"
          icon="add"
          icon-only
          :disabled="busy"
          @click="emit('create')"
        />
        <AppButton
          v-if="dirty && !editing"
          label="Discard task changes"
          icon="undo"
          icon-only
          :disabled="busy"
          @click="emit('discard')"
        />
        <AppButton
          v-if="
            !editing &&
            (dirty || (!editor.selected_task && editor.process_available))
          "
          :label="editor.selected_task ? 'Save task' : 'Create task'"
          icon="save"
          icon-only
          :disabled="busy"
          @click="emit('save')"
        />
      </div>
    </header>
    <div v-if="pendingAction" class="notice">
      <template v-if="pendingAction === 'copy'"
        ><p>
          {{
            t('Create a separate task for another assignee in this process.')
          }}
        </p>
        <label
          >{{ t('Assigned to')
          }}<UserComboBox
            :value="assignee"
            :options="editor.users"
            :action-field="false"
            label="Assigned to"
            :disabled="busy"
            @change="emit('assignee', $event)" /></label
      ></template>
      <p v-else>
        {{
          t(
            'Delete the selected task? Its notes and files will not be deleted.'
          )
        }}
      </p>
      <div class="configuration-actions">
        <AppButton
          :label="pendingAction === 'copy' ? 'Create task copy' : 'Delete task'"
          :icon="pendingAction === 'copy' ? 'copy' : 'delete'"
          :destructive="pendingAction === 'delete'"
          :disabled="busy"
          @click="emit('confirm-action')"
        />
        <AppButton
          label="Cancel"
          :disabled="busy"
          @click="emit('cancel-action')"
        />
      </div>
    </div>
    <div v-if="editing" class="task-detail-fields">
      <label
        v-for="field in editor?.fields || []"
        :key="field.name"
        :data-task-field="field.name"
        ><span>{{ t(titles[field.name] || field.name) }}</span>
        <TaskField
          :field="field"
          :value="draft[field.name]"
          :statuses="editor.statuses"
          :users="editor.users"
          :busy="busy"
          @change="emit('change', field.name, $event)"
        />
      </label>
      <footer v-if="editing">
        <AppButton
          label="Discard task changes"
          icon="close"
          :disabled="busy"
          @click="emit('discard')"
        />
        <AppButton
          label="Save task"
          icon="save"
          highlighted
          :disabled="busy || (!dirty && !!editor.selected_task)"
          @click="emit('save')"
        />
      </footer>
    </div>
  </section>
</template>
