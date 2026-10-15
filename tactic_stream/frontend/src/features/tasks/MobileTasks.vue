<script setup>
import { computed } from 'vue'
import { t } from '../../i18n.js'
import MobilePage from '../../controls/MobilePage.vue'
import AppButton from '../../controls/AppButton.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import AppIcon from '../../controls/AppIcon.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
import ItemSurface from '../../controls/ItemSurface.vue'
import TaskWorkspaceEditor from './TaskWorkspaceEditor.vue'
import { timestampFullLabel } from '../activity/activity.js'

const props = defineProps({ groups: Array, selected: Array, collapsed: Array, task: Object, editor: Object,
  busy: Boolean, blocked: Boolean, dirty: Boolean, active: Boolean, direction: String, scroll: Object, hasMore: Boolean })
const emit = defineEmits(['enter', 'back', 'scrolled', 'select', 'collapse', 'inspect', 'operate', 'object', 'change', 'milestones', 'more', 'retry'])
const tasks = computed(() => props.groups.flatMap(group => group.tasks))
const initials = title => title.trim().split(/\s+/).slice(0, 2).map(word => word[0]).join('').toUpperCase()
const progress = task => Math.max(0, Math.min(100, Number(task.progress ?? task.completion) || 0))
function actions(task, event) { emit('operate', task, event.currentTarget.getBoundingClientRect()) }
function enter(key) { const task = tasks.value.find(task => task.key === key); if (task && !task.deleting) emit('enter', task) }
</script>

<template>
  <MobilePage class="mobile-tasks" :aria-label="t('Project tasks')" :screen-key="task?.key || 'root'" :title="task?.title || t('Project tasks')"
    :back="!!task" :direction="direction" :scroll="scroll" :busy="busy" :active="active"
    @enter="enter" @back="emit('back')" @scrolled="(key, top) => emit('scrolled', key, top)">
    <template #header>
      <div v-if="task" class="mobile-task-heading">
        <AppButton label="Back" icon="previous" icon-only @click="emit('back')" />
        <ItemPreview :source="task.parent?.__preview__?.image" :fallback-text="initials(task.title)" :accent="task.__process__?.color" :preview-size="42" />
        <div class="mobile-task-copy"><h2>{{ task.title }}</h2><small>{{ task.__process__?.label || task.process }}{{ task.context && task.context !== task.process ? ' · ' + task.context : '' }}</small></div>
        <AppButton label="Task actions" icon="more" icon-only :disabled="busy" @click="actions(task, $event)" />
      </div>
    </template>
    <template v-if="task">
      <p v-if="busy" class="table-message" role="status">{{ t('Loading data…') }}</p>
      <p v-if="task.deleting" class="notice">{{ t('Pending task changes') }}</p>
      <TaskWorkspaceEditor v-else-if="editor" immediate :editor="editor" :busy="blocked" @change="(name, value) => emit('change', task.key, name, value)" @milestones="emit('milestones')" />
      <AppButton v-else-if="!busy" label="Retry" icon="refresh" @click="emit('retry', task)" />
    </template>
    <template v-else>
      <section v-for="group in groups" :key="group.key">
        <AppButton v-if="group.key" class="result-group-heading" :icon="collapsed.includes(group.key) ? 'next' : 'MDI_CHEVRON_DOWN'" :aria-expanded="!collapsed.includes(group.key)" @click="emit('collapse', group.key)">{{ group.label }} <small>{{ group.tasks.length }}</small></AppButton>
        <div class="mobile-task-list">
          <article v-for="row in collapsed.includes(group.key) ? [] : group.tasks" :key="row.key" :data-task-key="row.key" :data-mobile-item="row.key"
            class="mobile-task-card" :class="{ pending: row.pending, 'task-deleted': row.deleting }" tabindex="0" :aria-label="row.title + ': ' + row.process"
            @click="!$event.target.closest('button,a,input,textarea,select,label') && enter(row.key)" @keydown.enter.self.prevent="enter(row.key)" @contextmenu.prevent="actions(row, $event)">
            <ItemSurface :accent="row.__process__?.color" :selected="selected.includes(row.key)" class="mobile-task-surface" />
            <ItemPreview :source="row.parent?.__preview__?.image" :fallback-text="initials(row.title)" :accent="row.__process__?.color" :preview-size="42" />
            <div class="mobile-task-copy"><AppButton :label="row.title" :translate-label="false" :disabled="busy || row.deleting" class="mobile-task-title" @click="enter(row.key)"><strong>{{ row.title }}</strong></AppButton>
              <small>{{ row.__process__?.label || row.process }}{{ row.context && row.context !== row.process ? ' · ' + row.context : '' }}</small>
            </div>
            <div class="mobile-task-controls"><AppCheckbox :label="row.title + ': ' + row.process" :translate-label="false" :model-value="selected.includes(row.key)" :disabled="busy" @update:model-value="emit('select', row.key, $event, {})"><span class="visually-hidden">{{ row.title }}</span></AppCheckbox><AppIcon name="next" /></div>
            <div class="mobile-task-metadata"><span><i class="task-status-dot" :style="{ background: row.__status__?.color || 'var(--primary)' }"></i>{{ row.__status__?.label || row.status || t('No status') }}</span><span>{{ row.assigned === '—' ? t('Not assigned') : row.assigned }}</span>
              <span v-if="row.bid_end_date"><AppIcon name="MDI_CALENDAR_MONTH" />{{ timestampFullLabel(row.bid_end_date) }}</span>
              <span v-if="row.pending" class="mobile-task-pending">{{ t('Pending task changes') }}</span>
            </div>
            <div class="mobile-task-bottom"><progress :value="progress(row)" max="100" :aria-label="t('Progress')" /><small>{{ progress(row) }}%</small>
              <AppButton label="Open notes" icon="comment" icon-only :badge-count="row.notes" :disabled="busy || row.pending || row.deleting || !row.__search_key__" @click="emit('inspect', row)" />
              <AppButton label="Task actions" icon="more" icon-only :disabled="busy" @click="actions(row, $event)" />
            </div>
          </article>
        </div>
      </section>
      <p v-if="!tasks.length" class="table-message" role="status">{{ t(busy ? 'Loading data…' : 'No records yet') }}</p>
      <AppButton v-if="hasMore" class="mobile-task-more" label="Load more tasks" icon="add" :disabled="busy" @click="emit('more')" />
    </template>
  </MobilePage>
</template>

<style>
.mobile-tasks { flex:1; height:auto; }
.mobile-task-heading { display:flex; align-items:center; gap:8px; padding:12px; }
.mobile-task-heading > .icon-button { flex:none; width:32px; height:32px; min-width:32px; }
.mobile-task-card > .item-preview,.mobile-task-heading > .item-preview { width:42px; height:42px; min-width:42px; flex:none; font-size:12px; }
.mobile-task-copy { min-width:0; flex:1; }
.mobile-task-copy small { display:block; color:var(--muted); overflow-wrap:anywhere; }
.mobile-task-list { display:grid; gap:8px; padding:8px; }
.mobile-task-card { position:relative; display:grid; grid-template-columns:42px minmax(0,1fr) 48px; gap:8px; padding:12px; cursor:pointer; }
.mobile-task-card > :not(.mobile-task-surface) { position:relative; }
.mobile-task-card > .mobile-task-surface { position:absolute; inset:0; border:1px solid var(--outline-variant); border-radius:var(--surface-radius); box-shadow:0 2px 3px var(--shadow-color); }
.mobile-task-surface::after { display:none; }
.mobile-task-surface > .item-surface-rail { width:1px; }
.mobile-task-card .mobile-task-title { display:block; height:auto; min-height:0; padding:0; border:0; border-radius:0; text-align:left; white-space:normal; background:none; color:var(--on-surface); }
.mobile-task-title strong { font-size:var(--result-title-size); font-weight:600; overflow-wrap:anywhere; }
.mobile-task-controls { display:flex; align-items:center; gap:4px; align-self:start; }
.mobile-task-controls > .app-icon { color:var(--muted); }
.mobile-task-metadata { grid-column:2/-1; display:flex; flex-wrap:wrap; gap:6px 12px; color:var(--muted); font-size:var(--text-caption); }
.mobile-task-metadata > span { display:flex; align-items:center; gap:5px; overflow-wrap:anywhere; }
.mobile-task-metadata .task-status-dot { display:inline-block; width:8px; height:8px; flex:none; border-radius:50%; }
.mobile-task-metadata .mobile-task-pending { color:var(--primary); }
.mobile-task-bottom { grid-column:2/-1; display:flex; align-items:center; gap:8px; }
.mobile-task-bottom progress { appearance:none; width:60px; height:4px; border:0; border-radius:2px; background:var(--outline-variant); }
.mobile-task-bottom progress::-webkit-progress-bar { border-radius:2px; background:var(--outline-variant); }
.mobile-task-bottom progress::-webkit-progress-value { border-radius:2px; background:var(--primary); }
.mobile-task-bottom > small { flex:1; color:var(--muted); }
.mobile-task-bottom > .icon-button { width:28px; height:28px; min-width:28px; min-height:28px; }
.mobile-tasks .record-form { display:grid; grid-template-columns:minmax(0,1fr); gap:16px; padding:0 16px 24px; }
.mobile-tasks .record-form > label { min-width:0; }
.mobile-task-more { margin:8px 12px; }
</style>
