<script setup>
import { computed } from 'vue';
import { t } from '../../i18n.js';
import MobilePage from '../../controls/MobilePage.vue';
import AppButton from '../../controls/AppButton.vue';
import ItemPreview from '../../controls/ItemPreview.vue';
import TaskMobileCard from './TaskMobileCard.vue';
import TaskWorkspaceEditor from './TaskWorkspaceEditor.vue';

const props = defineProps({
  groups: Array,
  selected: Array,
  collapsed: Array,
  task: Object,
  editor: Object,
  busy: Boolean,
  blocked: Boolean,
  dirty: Boolean,
  active: Boolean,
  direction: String,
  scroll: Object,
  hasMore: Boolean
});
const emit = defineEmits([
  'enter',
  'back',
  'scrolled',
  'select',
  'collapse',
  'inspect',
  'operate',
  'object',
  'change',
  'milestones',
  'more',
  'retry'
]);
const tasks = computed(() => props.groups.flatMap((group) => group.tasks));
const initials = (title) =>
  title
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase();
function actions(task, event) {
  emit('operate', task, event.currentTarget.getBoundingClientRect());
}
function enter(key) {
  const task = tasks.value.find((task) => task.key === key);
  if (task && !task.deleting) emit('enter', task);
}
</script>

<template>
  <MobilePage
    class="mobile-tasks"
    :aria-label="t('Project tasks')"
    :screen-key="task?.key || 'root'"
    :title="task?.title || t('Project tasks')"
    :back="!!task"
    :direction="direction"
    :scroll="scroll"
    :busy="busy"
    :active="active"
    @enter="enter"
    @back="emit('back')"
    @scrolled="(key, top) => emit('scrolled', key, top)"
  >
    <template #header>
      <div v-if="task" class="mobile-task-heading">
        <AppButton
          label="Back"
          icon="previous"
          icon-only
          @click="emit('back')"
        />
        <ItemPreview
          :source="task.parent?.__preview__?.image"
          :fallback-text="initials(task.title)"
          :accent="task.__process__?.color"
          :preview-size="42"
        />
        <div class="mobile-task-copy">
          <h2>{{ task.title }}</h2>
          <small
            >{{ task.__process__?.label || task.process
            }}{{
              task.context && task.context !== task.process
                ? ' · ' + task.context
                : ''
            }}</small
          >
        </div>
        <AppButton
          label="Task actions"
          icon="more"
          icon-only
          :disabled="busy"
          @click="actions(task, $event)"
        />
      </div>
    </template>
    <template v-if="task">
      <p v-if="busy" class="table-message" role="status">
        {{ t('Loading data…') }}
      </p>
      <p v-if="task.deleting" class="notice">{{ t('Pending task changes') }}</p>
      <TaskWorkspaceEditor
        v-else-if="editor"
        immediate
        :editor="editor"
        :busy="blocked"
        @change="(name, value) => emit('change', task.key, name, value)"
        @milestones="emit('milestones')"
      />
      <AppButton
        v-else-if="!busy"
        label="Retry"
        icon="refresh"
        @click="emit('retry', task)"
      />
    </template>
    <template v-else>
      <section v-for="group in groups" :key="group.key">
        <AppButton
          v-if="group.key"
          class="result-group-heading"
          :icon="collapsed.includes(group.key) ? 'next' : 'MDI_CHEVRON_DOWN'"
          :aria-expanded="!collapsed.includes(group.key)"
          @click="emit('collapse', group.key)"
          >{{ group.label }} <small>{{ group.tasks.length }}</small></AppButton
        >
        <div class="mobile-task-list">
          <article
            v-for="row in collapsed.includes(group.key) ? [] : group.tasks"
            :key="row.key"
            :data-task-key="row.key"
            :data-mobile-item="row.key"
            class="mobile-task-card"
            :class="{ pending: row.pending, 'task-deleted': row.deleting }"
            tabindex="0"
            :aria-label="row.title + ': ' + row.process"
            @click="
              !$event.target.closest('button,a,input,textarea,select,label') &&
              enter(row.key)
            "
            @keydown.enter.self.prevent="enter(row.key)"
            @contextmenu.prevent="actions(row, $event)"
          >
            <TaskMobileCard
              :row="row"
              :busy="busy"
              :checked="selected.includes(row.key)"
              @enter="enter(row.key)"
              @select="emit('select', row.key, $event, {})"
              @notes="emit('inspect', row)"
              @menu="
                (source) => emit('operate', row, source.getBoundingClientRect())
              "
            />
          </article>
        </div>
      </section>
      <p v-if="!tasks.length" class="table-message" role="status">
        {{ t(busy ? 'Loading data…' : 'No records yet') }}
      </p>
      <AppButton
        v-if="hasMore"
        class="mobile-task-more"
        label="Load more tasks"
        icon="add"
        :disabled="busy"
        @click="emit('more')"
      />
    </template>
  </MobilePage>
</template>

<style>
.mobile-tasks {
  flex: 1;
  height: auto;
}
.mobile-task-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
}
.mobile-task-heading > .icon-button {
  flex: none;
  width: 32px;
  height: 32px;
  min-width: 32px;
}
.mobile-task-card > .item-preview,
.mobile-task-heading > .item-preview {
  width: 42px;
  height: 42px;
  min-width: 42px;
  flex: none;
  font-size: 12px;
}
.mobile-task-copy {
  min-width: 0;
  flex: 1;
}
.mobile-task-copy small {
  display: block;
  color: var(--muted);
  overflow-wrap: anywhere;
}
.mobile-task-list {
  display: grid;
  gap: 8px;
  padding: 8px;
}
.mobile-task-card {
  position: relative;
  min-width: 0;
  cursor: pointer;
}
.mobile-tasks .record-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
  padding: 0 16px 24px;
}
.mobile-tasks .record-form > label {
  min-width: 0;
}
.mobile-task-more {
  margin: 8px 12px;
}
</style>
