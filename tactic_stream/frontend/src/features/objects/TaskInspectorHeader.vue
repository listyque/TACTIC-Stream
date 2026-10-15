<script setup>
// TaskInspector.qml contextHeader: 46px, 32px preview, process and task menus.
import { computed } from 'vue'
import AppButton from '../../controls/AppButton.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppIcon from '../../controls/AppIcon.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
import { mobile } from '../../mobile.js'
import UserIdentity from '../../controls/UserIdentity.vue'
import { t } from '../../i18n.js'
const props = defineProps({ editor:Object,process:String,expanded:Boolean,busy:Boolean,editing:Boolean })
const emit = defineEmits(['back','help','toggle','preview','process','task','refresh','edit','create','action','log','timesheet'])
const selected = computed(() => props.editor.processes.find(row => row.value === props.process))
const title = computed(() => props.editor.object.record.name || props.editor.object.record.title || props.editor.object.record.code || String(props.editor.object.record.id))
const initials = computed(() => title.value.trim().split(/\s+|_+/).slice(0,2).map(word => word[0]).join('').toUpperCase())
</script>
<template>
  <div class="inspector-object inspector-context">
    <AppButton icon-only :icon="mobile ? 'MDI_ARROW_LEFT' : expanded ? 'MDI_CHEVRON_DOWN' : 'MDI_CHEVRON_RIGHT'" :label="mobile ? 'Back' : expanded ? 'Collapse task details' : 'Expand task details'" :aria-expanded="mobile ? undefined : expanded" :disabled="!mobile && busy" @click="emit(mobile ? 'back' : 'toggle')" />
    <ItemPreview :source="editor.object.preview.image" :fallback-text="initials" :round="!mobile" :outlined="!mobile" :preview-size="mobile ? 42 : 32" :accent="mobile ? selected?.color : undefined" />
    <AppButton class="inspector-object-title" label="Object preview" :disabled="busy" @click="emit('preview')"><span><strong>{{ title }}</strong><small>{{ editor.object.type_title || editor.object.search_type }}</small></span></AppButton>
    <AppMenu class="inspector-process" label="Process" overlay :width="320" :aria-disabled="busy" @pointerdown.capture="busy && $event.preventDefault()" @keydown.capture="busy && $event.preventDefault()">
      <template #trigger><AppIcon v-if="selected?.type === 'progress'" name="MDI_CHART_DONUT" :style="{color:selected?.color || 'var(--primary)'}" /><span v-else class="inspector-process-dot" :style="{background:selected?.color || 'var(--primary)'}"></span><span>{{ selected?.label || process }}</span><AppIcon name="MDI_CHEVRON_DOWN" /></template>
      <strong class="inspector-menu-heading">{{ t('Process and note context') }}</strong>
      <AppButton v-for="row in editor.processes" :key="row.value" :data-process-choice="row.value" :translate-label="false" :label="row.label" role="menuitemradio" :aria-checked="row.value === process" :disabled="busy" @click="emit('process',row.value)">
        <span class="inspector-process-dot" :style="{background:row.color || 'var(--primary)'}"></span><span class="inspector-choice-copy"><strong>{{ row.label }}</strong><small>{{ row.type === 'progress' ? t('Related tasks') : row.type === 'built-in' ? t('Built-in') : row.type }} · {{ row.type === 'progress' ? (row.approved || 0) + ' / ' + (row.total || 0) : t('{count} notes',{count:row.count || 0}) }}</small></span><AppIcon v-if="row.value === process" name="check-circle" />
      </AppButton>
    </AppMenu>
    <AppMenu v-if="editor.task_choices.length > 1" class="inspector-task-picker" label="Task" icon="MDI_SWAP_HORIZONTAL" overlay :width="330" :aria-disabled="busy" @pointerdown.capture="busy && $event.preventDefault()" @keydown.capture="busy && $event.preventDefault()">
      <strong class="inspector-menu-heading">{{ t('Tasks for this process') }}</strong>
      <AppButton v-for="row in editor.task_choices" :key="row.value" :data-task-choice="row.value" :translate-label="false" :label="row.label" role="menuitemradio" :aria-checked="row.value === editor.selected_task" :disabled="busy" @click="emit('task',row.value)"><UserIdentity v-if="row.identity" v-bind="row.identity" /><span class="inspector-choice-copy"><strong>{{ row.label }}<template v-if="row.primary"> · {{ t('Main') }}</template></strong><small>{{ row.status }} · {{ t('{count} notes',{count:row.count || 0}) }}</small></span><AppIcon v-if="row.value === editor.selected_task" name="check-circle" /></AppButton>
    </AppMenu>
    <AppMenu v-if="mobile || editor.process_type !== 'progress'" class="inspector-task-actions" label="Task actions" overlay>
      <template v-if="mobile"><AppButton :label="expanded ? 'Collapse task details' : 'Expand task details'" icon="MDI_CHEVRON_DOWN" :disabled="busy" @click="emit('toggle')" /><AppButton label="Refresh" icon="refresh" :disabled="busy" @click="emit('refresh')" /><template v-if="editor.work_hours"><AppButton label="Log time" icon="MDI_ALARM_PLUS" :disabled="busy" @click="emit('log')" /><AppButton label="Open timesheet" icon="MDI_CALENDAR_MONTH" :disabled="busy" @click="emit('timesheet')" /></template><hr></template>
      <template v-if="editor.process_type !== 'progress'">
      <AppButton label="Edit task" icon="edit" :disabled="busy || editing" @click="emit('edit')" />
      <AppButton v-if="editor.selected_task" label="Add task assignee" icon="copy" :disabled="busy || editing" @click="emit('action','copy')" />
      <AppButton v-if="editor.selected_task" label="Delete task" icon="delete" destructive :disabled="busy || editing" @click="emit('action','delete')" />
      <AppButton v-else label="Create task" icon="add" :disabled="busy" @click="emit('create')" />
      </template>
    </AppMenu>
    <AppButton v-if="!mobile" class="inspector-refresh" icon-only label="Refresh" icon="refresh" :disabled="busy" @click="emit('refresh')" />
    <AppButton v-else class="inspector-help" icon-only label="Help" icon="help" @click="emit('help')" />
  </div>
</template>
<style>
.inspector-context { height:46px; display:flex; align-items:center; gap:7px; padding:0 6px 0 7px; border-radius:var(--item-radius); background:var(--surface-high); min-width:0; flex-shrink:0; }
.inspector-context > .app-button:first-child { width:24px; height:24px; min-height:0; flex:0 0 24px; }.inspector-context > .app-button:first-child .app-icon { font-size:13px; width:13px; height:13px; }
.inspector-context > .image-picker-preview { width:32px; height:32px; flex:0 0 32px; }.inspector-context .inspector-object-title.app-button { min-width:0; flex:1; height:auto; border:0; background:transparent; padding:0; justify-content:flex-start; text-align:left; }
.inspector-object-title > span:not(.control-ripple-clip) { display:grid; width:100%; min-width:0; gap:1px; }.inspector-object-title strong,.inspector-object-title small { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.inspector-object-title strong { font-size:var(--text-label); }.inspector-object-title small { color:var(--muted); font-size:var(--text-caption); font-weight:400; }
.inspector-process { flex:0 0 clamp(112px,34%,166px); min-width:0; }.inspector-process > summary.icon-button { width:100%; min-width:0; min-height:0; aspect-ratio:auto; justify-content:flex-start; display:flex; height:var(--compact-control-height); align-items:center; gap:7px; background:var(--surface-deep); border-radius:var(--field-radius); border:1px solid var(--outline-variant); padding:0 8px 0 10px; font-size:var(--text-label); font-weight:600; }.inspector-process > summary > span:nth-child(2) { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.inspector-process > summary .app-icon { width:15px; height:15px; font-size:15px; }
.inspector-process-dot { width:8px; height:8px; flex:0 0 8px; border-radius:50%; }.inspector-task-picker > summary,.inspector-task-actions > summary,.inspector-context > .app-button:last-child { width:28px; height:28px; min-height:0; flex:0 0 28px; }.inspector-context > .app-button:last-child .app-icon { width:16px; height:16px; font-size:16px; }
.inspector-choice-copy { display:grid; min-width:0; flex:1; gap:2px; text-align:left; }.inspector-choice-copy strong,.inspector-choice-copy small { overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }.inspector-choice-copy small,.inspector-menu-heading { color:var(--muted); font-size:var(--text-caption); }.inspector-menu-heading { display:block; padding:6px 10px; }
</style>

