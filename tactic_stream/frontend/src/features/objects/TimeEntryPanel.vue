<script setup>
import { computed, ref, onMounted, onBeforeUnmount, nextTick } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import WorkReportSurface from './WorkReportSurface.vue';
import WorkHourForm from './WorkHourForm.vue';
import { appearance } from '../../appearance.js';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/workhours/sheet.ui.mjs';
import AppDateField from '../../controls/AppDateField.vue';
import AppButton from '../../controls/AppButton.vue';
import AppSelect from '../../controls/AppSelect.vue';
import { t } from '../../i18n.js';
const props = defineProps({
  dockTarget: String,
  dockReport: String,
  data: Object,
  draft: Object,
  editing: Boolean,
  busy: Boolean,
  error: String,
  uncertain: Boolean,
  deleting: String,
  users: Array,
  mode: { type: String, default: 'task' },
  week: String,
  login: String,
  selected: Array,
  report: String,
  canCreate: Boolean,
  confirmation: Boolean
});
const emit = defineEmits([
  'create',
  'edit',
  'save',
  'action',
  'cancel-edit',
  'delete',
  'close',
  'refresh',
  'change',
  'scope',
  'move-week',
  'select',
  'clear-selection',
  'bulk',
  'keep-editing',
  'discard-close'
]);
const dialog = ref(null);
const width = ref(640);
const language = computed(() => appearance.language);
const toolbarModel = computed(() => ({
  weekStart: props.week,
  login: props.login,
  busy: props.busy,
  locked: props.uncertain || props.editing,
  canCreate: props.canCreate,
  canManage: !!props.users?.length,
  users: [{ value: '', label: t('All users') }, ...(props.users || [])],
  selectedCount: props.selected?.length || 0
}));
const toolbar = computed(() =>
  UI.toolbar(toolbarModel.value, width.value, language.value)
);
function scopeAction(action) {
  if (action.type === 'week') emit('move-week', action.value);
  else if (action.type === 'date') emit('scope', 'week', action.value);
  else if (action.type === 'user') emit('scope', 'login', action.value);
  else if (action.type === 'refresh') emit('refresh');
  else if (action.type === 'create') emit('create');
  else if (action.type === 'reports') emit('scope', 'mode', 'report');
  else if (action.type === 'clear') emit('clear-selection');
  else emit('bulk', action.type);
}
function entryScene(entry) {
  return UI.entry(
    {
      id: entry.search_key,
      day: entry.day,
      taskTitle: entry.task_title || '',
      process: entry.process,
      loginLabel: entry.login,
      description: entry.description,
      hours: entry.hours,
      overtimeHours: entry.category === 'overtime' ? entry.hours : 0,
      status: entry.status,
      canEdit: entry.can_edit !== false,
      canApprove: true,
      selectable: props.mode === 'week',
      selected: props.selected?.includes(entry.search_key),
      disabled: props.busy || props.uncertain || props.editing
    },
    width.value,
    language.value
  );
}
function entryAction(entry, action) {
  if (action.type === 'select') emit('select', entry.search_key, action.value);
  else if (action.type === 'edit') emit('edit', entry);
  else if (action.type === 'delete') emit('delete', entry.search_key);
  else
    emit('action', entry, entry.status === 'approved' ? 'reject' : 'approve');
}
let observer;
onMounted(() =>
  nextTick(() => {
    observer = observeFrameSizes(
      () => (width.value = frameContentWidth(dialog.value))
    );
    observer.observe(dialog.value);
  })
);
onBeforeUnmount(() => observer?.disconnect());
const opened = ref(false);
defineExpose({
  open: () => {
    opened.value = true;
    if (!props.dockTarget) dialog.value.show();
  },
  close: () => {
    opened.value = false;
    if (!props.dockTarget) dialog.value?.close();
  },
  isOpen: () => (props.dockTarget ? opened.value : !!dialog.value?.open)
});
</script>

<template>
  <Teleport defer :to="dockTarget || 'body'"
    ><component
      :is="dockTarget ? 'section' : 'dialog'"
      v-show="!dockTarget || opened"
      v-window="dockTarget ? false : { type: 'window' }"
      ref="dialog"
      class="time-entry-panel"
      :class="{
        'record-dialog': !dockTarget,
        'time-entry-panel-docked': !!dockTarget
      }"
      :role="dockTarget ? 'region' : 'dialog'"
      :aria-label="
        t(
          mode === 'task'
            ? 'Task timesheet'
            : mode === 'report'
              ? dockReport === 'labor_cost'
                ? 'Cost Reports'
                : 'Work reports'
              : 'Weekly timesheet'
        )
      "
      :aria-busy="busy"
      @cancel.prevent="emit('close')"
    >
      <header>
        <div>
          <h2>
            {{
              t(
                mode === 'task'
                  ? 'Task timesheet'
                  : mode === 'report'
                    ? dockReport === 'labor_cost'
                      ? 'Cost Reports'
                      : 'Work reports'
                    : 'Weekly timesheet'
              )
            }}
          </h2>
          <small>{{
            mode === 'task'
              ? t('Time entries for the selected task')
              : `${data?.week_start || week} — ${data?.week_end || ''}`
          }}</small>
        </div>
        <AppButton
          label="Close"
          icon="close"
          icon-only
          :disabled="busy"
          @click="emit('close')"
        />
      </header>
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <p v-if="uncertain" class="notice">
        {{
          t(
            'Refresh and check the timesheet before retrying. The server may have saved the changes.'
          )
        }}
      </p>
      <aside v-if="confirmation" class="notice" role="alert">
        <p>{{ t('Discard unsaved changes?') }}</p>
        <AppButton
          label="Keep editing"
          @click="emit('keep-editing')"
        /><AppButton
          label="Discard changes"
          destructive
          @click="emit('discard-close')"
        />
      </aside>
      <div class="configuration-actions">
        <AppButton
          v-if="mode === 'task'"
          label="Log time"
          icon="add"
          :disabled="busy || uncertain || editing || !data || !canCreate"
          @click="emit('create')"
        /><AppButton
          v-if="mode !== 'week'"
          label="Weekly timesheet"
          icon="table"
          :disabled="busy || uncertain || editing"
          @click="emit('scope', 'mode', 'week')"
        /><AppButton
          v-if="mode !== 'task' && canCreate"
          label="Task timesheet"
          icon="MDI_CLOCK_OUTLINE"
          :disabled="busy || uncertain || editing"
          @click="emit('scope', 'mode', 'task')"
        /><AppButton
          v-if="mode === 'task'"
          label="Open work reports"
          icon="bar-chart"
          :disabled="busy || uncertain || editing"
          @click="emit('scope', 'mode', 'report')"
        /><AppButton
          v-if="mode === 'task'"
          label="Refresh"
          icon="refresh"
          :disabled="busy"
          @click="emit('refresh')"
        />
      </div>
      <FrameView
        v-if="mode === 'week'"
        class="time-entry-frame"
        :style="{ height: toolbar.height + 'px' }"
        :scene="toolbar"
        @event="scopeAction"
      />
      <FrameView
        v-if="mode === 'week' && data"
        class="time-entry-frame"
        :style="{
          height: UI.summary(data.summary, width, language).height + 'px'
        }"
        :scene="UI.summary(data.summary, width, language)"
      />
      <div v-if="mode === 'report'" class="timesheet-filters">
        <AppDateField
          :model-value="week"
          label="Week"
          :include-time="false"
          :allow-clear="false"
          :disabled="busy || uncertain || editing"
          @change="emit('scope', 'week', $event)"
        /><AppSelect
          :model-value="login"
          :options="[{ value: '', label: t('All users') }, ...users]"
          label="Team member"
          :disabled="busy || uncertain || editing"
          :translate-labels="false"
          @update:model-value="emit('scope', 'login', $event)"
        />
      </div>
      <WorkReportSurface
        v-if="mode === 'report'"
        :data="data"
        :report="report"
        :busy="busy || uncertain"
        @report="emit('scope', 'report', $event)"
        @refresh="emit('refresh')"
      />
      <WorkHourForm
        v-if="editing"
        :draft="draft"
        :users="users"
        :busy="busy || uncertain"
        :error="error"
        @change="(field, value) => emit('change', field, value)"
        @cancel="emit('cancel-edit')"
        @save="emit('save', $event)"
      />
      <p v-if="busy" role="status">{{ t('Loading data…') }}</p>
      <p
        v-else-if="mode !== 'report' && data && !data.entries.length"
        class="muted"
      >
        {{
          t(
            mode === 'week'
              ? 'No work hours for this week'
              : 'No time entries yet'
          )
        }}
      </p>
      <div v-if="mode !== 'report'" class="time-entry-list">
        <article
          v-for="entry in data?.entries || []"
          :key="entry.search_key"
          class="timesheet-entry"
        >
          <FrameView
            class="time-entry-frame"
            :scene="entryScene(entry)"
            :style="{ height: entryScene(entry).height + 'px' }"
            @event="(action) => entryAction(entry, action)"
          />
          <div v-if="deleting === entry.search_key" class="notice">
            <p>{{ t('Delete this time entry?') }}</p>
            <AppButton
              label="Delete time entry"
              icon="delete"
              destructive
              :disabled="busy || uncertain"
              @click="emit('action', entry, 'delete')"
            /><AppButton
              label="Cancel"
              :disabled="busy"
              @click="emit('delete', '')"
            />
          </div>
        </article>
      </div> </component
  ></Teleport>
</template>

<style>
.time-entry-frame {
  position: relative;
  flex: none;
  width: 100%;
}
.timesheet-entry {
  position: relative;
  margin: 5px 0;
  padding: 0;
}
</style>
