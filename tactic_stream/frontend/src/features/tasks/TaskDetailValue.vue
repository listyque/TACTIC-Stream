<script setup>
import TaskField from '../objects/TaskField.vue';
import StatusSelect from '../../controls/StatusSelect.vue';
import UserComboBox from '../../controls/UserComboBox.vue';
import AppSlider from '../../controls/AppSlider.vue';
import AppButton from '../../controls/AppButton.vue';
import { titles } from '../../../../src/tactic_stream/shared_ui/features/tasks/details.ui.mjs';
defineProps({ field: Object, editor: Object, busy: Boolean });
const emit = defineEmits(['change', 'milestones']);
</script>
<template>
  <div class="task-detail-value" :data-task-field="field.name">
    <StatusSelect
      v-if="field.name === 'status'"
      :value="editor.values.status || ''"
      :options="editor.statusChoices"
      :disabled="busy || !field.editable"
      @change="emit('change', $event)"
    />
    <UserComboBox
      v-else-if="['assigned', 'supervisor'].includes(field.name)"
      :label="titles[field.name]"
      :value="editor.values[field.name] || ''"
      :empty-label="
        field.name === 'supervisor' ? 'No supervisor' : 'Not assigned'
      "
      :options="editor.users"
      :disabled="busy || !field.editable"
      @change="emit('change', $event)"
    />
    <AppSlider
      v-else-if="['progress', 'completion'].includes(field.name)"
      :label="titles[field.name]"
      :model-value="Number(editor.values[field.name] || 0)"
      :step="5"
      :disabled="busy || !field.editable"
      @update:model-value="emit('change', $event)"
    />
    <div
      v-else-if="field.name === 'milestone_code'"
      class="task-detail-milestone"
    >
      <TaskField
        :field="field"
        :value="editor.values[field.name]"
        :catalog="editor.catalog"
        :busy="busy"
        @change="emit('change', $event)"
      /><AppButton
        label="Project milestones"
        icon="add"
        icon-only
        :disabled="busy"
        @click="emit('milestones')"
      />
    </div>
    <TaskField
      v-else
      :field="field"
      :value="editor.values[field.name]"
      :catalog="editor.catalog"
      :busy="busy"
      @change="emit('change', $event)"
    />
  </div>
</template>
<style>
.task-detail-value,
.task-detail-value > :first-child {
  width: 100%;
  height: 100%;
  min-height: 0;
}
.task-detail-value .app-slider {
  height: 26px;
}
.task-detail-milestone {
  display: flex;
  gap: 5px;
}
.task-detail-milestone > :first-child {
  flex: 1;
  min-width: 0;
}
.task-detail-milestone > .app-button {
  flex: none;
  width: 32px;
  min-width: 32px;
  height: 32px;
  min-height: 32px;
}
</style>
