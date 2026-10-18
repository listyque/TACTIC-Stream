<script setup>
// Handler MilestoneManagerView.qml (EPL-1.0), presenter only.
import { ref } from 'vue';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import MilestoneContent from './MilestoneContent.vue';
const props = defineProps({
  project: String,
  result: Object,
  rows: Array,
  query: String,
  busy: Boolean,
  error: String,
  uncertain: String,
  confirmation: String,
  deleting: String,
  focused: String
});
const emit = defineEmits([
  'query',
  'create',
  'change',
  'save',
  'discard',
  'delete',
  'review',
  'refresh',
  'inspect-server',
  'close',
  'keep-editing',
  'confirm',
  'cancel-delete',
  'confirm-delete'
]);
const dialog = ref(null);
function action(event) {
  if (event.type === 'change')
    emit('change', event.code, event.field, event.value);
  else if (event.type === 'query') emit('query', event.value);
  else emit(event.type, event.code);
}
function focusRow(code, input = false) {
  const row = [
    ...(dialog.value?.querySelectorAll('[data-milestone]') || [])
  ].find((row) => row.dataset.milestone === code);
  row?.scrollIntoView({ block: 'nearest' });
  if (input) row?.querySelector('input')?.focus();
}
defineExpose({
  open: () => {
    if (!dialog.value.open) dialog.value.show();
  },
  close: () => dialog.value?.close(),
  focusRow
});
</script>

<template>
  <Teleport to="body">
    <dialog
      v-window="{ kind: 'milestone_manager', type: 'window' }"
      ref="dialog"
      class="configuration-dialog milestone-manager"
      :aria-label="t('Project milestones')"
      @cancel.prevent="emit('close')"
    >
      <header class="task-manager-heading">
        <div>
          <h2>{{ t('Project milestones') }}</h2>
          <small class="muted"
            >{{ project }} ·
            {{ t('Reusable deadlines and the plan of linked tasks.') }}</small
          >
        </div>
        <div class="configuration-actions">
          <AppButton
            label="Close"
            icon="close"
            icon-only
            :disabled="busy"
            @click="emit('close')"
          />
        </div>
      </header>
      <aside v-if="confirmation" class="notice">
        <p>
          {{
            t(
              confirmation === 'close'
                ? 'Discard unsaved milestone changes?'
                : 'Refreshing will discard every unsaved milestone change.'
            )
          }}
        </p>
        <AppButton
          label="Keep editing"
          @click="emit('keep-editing')"
        /><AppButton
          label="Discard changes"
          destructive
          @click="emit('confirm')"
        />
      </aside>
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <aside v-if="uncertain" class="notice" role="alert">
        <p>
          {{
            t(
              'The server may have saved this milestone. Inspect the server data before discarding the draft; saving is blocked.'
            )
          }}
        </p>
        <AppButton
          label="Inspect current server data"
          icon="refresh"
          :disabled="busy"
          @click="emit('inspect-server')"
        /><AppButton
          label="Discard changes"
          :disabled="busy"
          @click="emit('discard', uncertain)"
        />
      </aside>
      <div v-if="uncertain && result" class="milestone-server-data">
        <strong>{{ t('Current server data') }}</strong>
        <p v-for="row in result.records" :key="row.code">
          {{ row.code }} · {{ row.description }} · {{ row.dueDate }}
        </p>
      </div>
      <MilestoneContent
        class="milestone-manager-content"
        :project="project"
        :result="result"
        :rows="rows"
        :query="query"
        :busy="busy"
        :uncertain="uncertain"
        :focused="focused"
        @event="action"
      />
      <aside v-if="deleting" class="notice milestone-delete" role="alert">
        <p>
          {{
            t(
              'Delete this milestone? It can only be deleted when no tasks use it.'
            )
          }}
        </p>
        <AppButton
          label="Cancel"
          :disabled="busy"
          @click="emit('cancel-delete')"
        /><AppButton
          label="Delete milestone"
          icon="delete"
          destructive
          :disabled="busy || !!uncertain"
          @click="emit('confirm-delete')"
        />
      </aside>
    </dialog>
  </Teleport>
</template>

<style>
.milestone-manager > .milestone-manager-content {
  flex: 1;
  min-height: 0;
}
</style>
