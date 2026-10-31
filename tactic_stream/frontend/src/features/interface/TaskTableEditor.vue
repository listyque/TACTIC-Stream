<script setup>
// The table owner keeps plans and staged changes.
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import AppButton from '../../controls/AppButton.vue';
import TaskField from '../objects/TaskField.vue';
import { t } from '../../i18n.js';
import { titles } from '../../../../src/tactic_stream/shared_ui/features/tasks/editor.ui.mjs';

const props = defineProps({
  editor: Object,
  busy: Boolean,
  embedded: Boolean,
  label: { type: String, default: 'Edit table tasks' }
});
const compact = computed(
  () =>
    props.editor?.fields.length === 1 &&
    ['status', 'assigned', 'supervisor', 'priority', 'milestone_code'].includes(
      props.editor.fields[0].name
    )
);
const single = computed(() => props.editor?.fields.length === 1);
const fieldLabel = (field) => t(titles[field.name] || field.name);
const emit = defineEmits(['change', 'closed', 'milestones']);
const popup = ref(null);
let anchor;
async function open(bounds) {
  anchor = bounds.anchor;
  await nextTick();
  const node = popup.value;
  if (!node) return;
  node.style.width = compact.value ? bounds.width + 'px' : '';
  node.style.setProperty('--editor-height', bounds.height + 'px');
  node.showPopover();
  node.style.left =
    Math.max(8, Math.min(bounds.left, innerWidth - node.offsetWidth - 8)) +
    'px';
  node.style.top =
    Math.max(
      8,
      Math.min(
        compact.value ? bounds.top : bounds.bottom + 4,
        innerHeight - node.offsetHeight - 8
      )
    ) + 'px';
  node.querySelector('select, input, summary')?.focus();
  if (compact.value) {
    node.querySelector('summary')?.click();
    try {
      node.querySelector('select')?.showPicker();
    } catch {
      /* The field remains keyboard accessible after transient activation expires. */
    }
  }
}
function close() {
  popup.value?.hidePopover();
  if (anchor?.isConnected) anchor.focus({ preventScroll: true });
  anchor = null;
}
function scrolled(event) {
  if (!(event.target instanceof Node) || !popup.value?.contains(event.target))
    close();
}
function outside(event) {
  if (
    compact.value &&
    !popup.value?.contains(event.target) &&
    !event.target.closest('.user-combo-box')
  )
    close();
}
onMounted(() => {
  window.addEventListener('resize', close);
  window.addEventListener('scroll', scrolled, true);
  window.addEventListener('pointerdown', outside, true);
});
onBeforeUnmount(() => {
  close();
  window.removeEventListener('resize', close);
  window.removeEventListener('scroll', scrolled, true);
  window.removeEventListener('pointerdown', outside, true);
});
defineExpose({ open, close });
</script>

<template>
  <Teleport to="body" :disabled="embedded">
    <div
      ref="popup"
      class="task-table-editor"
      :class="{ 'in-cell': compact }"
      :popover="compact ? 'manual' : 'auto'"
      role="dialog"
      :aria-label="t(label)"
      :aria-description="
        editor
          ? t('Apply to {count} rows', { count: editor.plans.length })
          : undefined
      "
      @keydown.esc.stop.prevent="close"
      @toggle="$event.newState === 'closed' && emit('closed')"
    >
      <template v-if="editor">
        <header v-if="!compact">
          <strong>{{
            single
              ? fieldLabel(editor.fields[0])
              : editor.process || t('Edit task cell')
          }}</strong
          ><AppButton label="Close" icon="close" icon-only @click="close" />
        </header>
        <p v-if="!compact && editor.plans.length > 1" class="muted">
          {{ t('Apply to {count} rows', { count: editor.plans.length }) }}
        </p>
        <label
          v-for="field in editor.fields"
          :key="field.name"
          :data-task-field="field.name"
          ><span v-if="!compact && !single">{{ fieldLabel(field) }}</span>
          <TaskField
            :field="field"
            :compact="compact"
            :value="editor.values[field.name]"
            :statuses="editor.statuses"
            :users="editor.users"
            :catalog="editor.catalog"
            :busy="busy"
            @change="emit('change', field.name, $event)"
          />
          <AppButton
            v-if="field.name === 'milestone_code'"
            class="task-table-milestones"
            label="Project milestones"
            icon="milestone"
            icon-only
            :disabled="busy"
            @click="emit('milestones')"
          />
        </label>
      </template>
    </div>
  </Teleport>
</template>

<style>
.task-table-editor.in-cell {
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
  border-radius: 0;
  overflow: visible;
}
.task-table-editor.in-cell > label {
  display: flex;
  gap: 4px;
  margin: 0;
}
.task-table-editor.in-cell :is(select, .user-combo-box) {
  width: 100%;
  min-height: var(--editor-height);
  height: var(--editor-height);
  font-size: var(--text-caption);
}
.task-table-editor.in-cell select {
  padding: 0 4px;
}
.task-table-editor.in-cell .user-combo-box > summary {
  padding: 0 11px;
  gap: 7px;
}
.task-table-editor.in-cell .user-combo-label {
  font-size: var(--text-caption);
}
.task-table-editor.in-cell .user-combo-box > summary .item-preview {
  width: min(22px, calc(var(--editor-height) - 4px));
  height: min(22px, calc(var(--editor-height) - 4px));
  min-width: 0;
  min-height: 0;
  flex-basis: min(22px, calc(var(--editor-height) - 4px));
}
</style>

<style>
.task-table-editor.in-cell > label > :first-child {
  flex: 1;
  min-width: 0;
}
.task-table-editor.in-cell .task-table-milestones {
  flex: none;
  width: var(--editor-height);
  height: var(--editor-height);
  min-width: 0;
  min-height: 0;
}
</style>
