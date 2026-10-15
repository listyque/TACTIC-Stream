<script setup>
// Handler TaskCalendarView.qml (EPL-1.0), presented in its own workspace dock.
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { appearance } from '../../appearance.js'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
const props=defineProps({projection:Object,year:Number,month:Number,selectedDay:String,busy:Boolean,projecting:Boolean,error:String,hasMore:Boolean})
const emit=defineEmits(['month','month-value','today','day','inspect','milestone','load-more','tasks'])
const root=ref(null),width=ref(600),height=ref(500),agenda=ref(false)
let observer
const compact=computed(()=>width.value<500 || height.value<430)
const title=computed(()=>new Intl.DateTimeFormat(appearance.language,{month:'long',year:'numeric'}).format(new Date(props.year,props.month-1,1)))
const weekdays=computed(()=>Array.from({length:7},(_,index)=>new Intl.DateTimeFormat(appearance.language,{weekday:'short'}).format(new Date(2024,0,1+index))))
const days=computed(()=>props.projection?.calendar || [])
const agendaDays=computed(()=>days.value.filter(day=>props.selectedDay ? day.date===props.selectedDay : day.inMonth))
function limit(day){return compact.value?0:Math.max(1,Math.min(3,Math.floor(((height.value-96)/6-(day.milestoneCount?54:30))/22)))}
onMounted(()=>{observer=new ResizeObserver(()=>{width.value=root.value.clientWidth;height.value=root.value.clientHeight});observer.observe(root.value,{box:'border-box'})})
onBeforeUnmount(()=>observer?.disconnect())
</script>
<template>
 <section ref="root" class="task-calendar-view" :class="{compact}" :aria-label="t('Task calendar')" :aria-busy="projecting">
  <header class="calendar-navigation"><AppButton label="Previous month" icon="previous" icon-only :disabled="busy" @click="emit('month',-1)" /><label><span>{{ title }}</span><input type="month" :value="year+'-'+String(month).padStart(2,'0')" :aria-label="t('Calendar month')" :disabled="busy" @change="emit('month-value',$event.target.value)"></label><AppButton label="Next month" icon="next" icon-only :disabled="busy" @click="emit('month',1)" /><AppButton label="Today" icon="MDI_CALENDAR_TODAY" icon-only :disabled="busy" @click="emit('today')" /><AppButton v-if="selectedDay" label="Clear selected day" icon="MDI_FILTER_REMOVE_OUTLINE" icon-only :disabled="busy" @click="emit('day','')" /><AppButton label="Agenda" icon="MDI_FORMAT_LIST_BULLETED" icon-only :aria-pressed="agenda" @click="agenda=!agenda" /></header>
  <p v-if="error" role="alert" class="error">{{ t(error) }}</p>
  <div v-if="!agenda" class="calendar-weekdays"><span v-for="weekday in weekdays" :key="weekday">{{ weekday.toUpperCase() }}</span></div>
  <div v-if="!agenda" class="task-calendar-grid">
   <div v-for="(day,index) in days" :key="day.date" class="task-calendar-day" :class="{outside:!day.inMonth,today:day.today,selected:day.date===selectedDay,weekend:index%7>=5}">
    <AppButton class="calendar-day-action" :data-date="day.date" :aria-label="day.date" :aria-pressed="day.date===selectedDay" :disabled="busy" @click="emit('day',day.date)"><span class="calendar-day-number">{{ day.day }}</span><small v-if="day.taskCount" :class="{overdue:day.overdueCount>0}">{{ day.taskCount }}</small></AppButton>
    <AppButton v-if="day.milestones?.length" class="calendar-milestone-band" :title="day.milestones.map(item=>item.label).join(', ')" :disabled="busy" @click="emit('milestone',day.milestones[0].code)"><AppIcon name="MDI_FLAG_VARIANT" /><span>{{ day.milestones[0].label }}</span></AppButton>
    <div v-if="limit(day)" class="calendar-day-tasks"><AppButton v-for="task in day.tasks.slice(0,limit(day))" :key="task.taskCode" class="task-calendar-event" :title="task.parentTitle+' · '+task.processLabel+' · '+task.status+' · '+task.assignedLabel" :disabled="busy" @click="emit('inspect',task.taskCode)"><i :style="{background:task.statusColor || 'var(--primary)'}" /><span>{{ task.parentTitle }} · {{ task.processLabel }}</span></AppButton><small v-if="day.taskCount>limit(day)">{{ t('{count} more tasks',{count:day.taskCount-limit(day)}) }}</small></div>
    <div v-else-if="day.taskCount" class="calendar-status-dots" aria-hidden="true"><i v-for="task in day.tasks.slice(0,5)" :key="task.taskCode" :style="{background:task.statusColor || 'var(--primary)'}" /></div>
   </div>
  </div>
  <div v-else class="task-calendar-agenda"><section v-for="day in agendaDays.filter(item=>item.tasks.length || item.milestones?.length)" :key="day.date" class="calendar-agenda-day"><strong>{{ day.date }}</strong><AppButton v-for="milestone in day.milestones" :key="milestone.code" icon="MDI_FLAG_VARIANT" @click="emit('milestone',milestone.code)">{{ milestone.label }}</AppButton><AppButton v-for="task in day.tasks" :key="task.taskCode" class="task-calendar-agenda-row" :disabled="busy" @click="emit('inspect',task.taskCode)">{{ task.parentTitle }} · {{ task.processLabel }} · {{ task.status }}</AppButton></section><p v-if="!agendaDays.some(day=>day.taskCount || day.milestones?.length)" class="muted">{{ t('No loaded tasks on these dates.') }}</p></div>
  <footer><small>{{ selectedDay ? t('Task Browser filtered by {date}',{date:selectedDay}) : t('Select a day to filter Task Browser') }}</small><AppButton v-if="hasMore" label="Load more tasks" icon="add" icon-only :disabled="busy" @click="emit('load-more')" /><AppButton label="Task Manager" icon="MDI_CLIPBOARD_TEXT_OUTLINE" icon-only @click="emit('tasks')" /></footer>
 </section>
</template>
<style>
.task-calendar-view { display:flex; flex-direction:column; height:100%; min-height:0; min-width:0; padding:10px; gap:8px; background:var(--page); }
.task-calendar-view.compact { padding:6px; gap:5px; }
.calendar-navigation { display:flex; align-items:center; gap:4px; flex:none; height:34px; }
.calendar-navigation > label { position:relative; flex:1; min-width:0; text-align:center; font-size:14px; font-weight:600; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.compact .calendar-navigation > label { font-size:12px; }
.calendar-navigation input { position:absolute; inset:0; width:100%; opacity:0; cursor:pointer; }
.calendar-navigation .icon-button,.task-calendar-view footer .icon-button { width:28px; height:28px; min-width:28px; min-height:28px; }
.calendar-weekdays { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); height:22px; flex:none; text-align:center; align-items:center; color:var(--muted); font-size:var(--text-caption); font-weight:600; }
.task-calendar-view .task-calendar-grid { flex:1; min-height:0; display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); grid-template-rows:repeat(6,minmax(0,1fr)); gap:4px; padding:0; }
.task-calendar-view.compact .task-calendar-grid { gap:2px; }
.task-calendar-view .task-calendar-day { position:relative; min-height:0; min-width:0; border:0; border-radius:var(--item-radius); background:var(--surface-container); overflow:hidden; box-shadow:none; }
.task-calendar-view .task-calendar-day.weekend { background:var(--surface); }
.task-calendar-view .task-calendar-day:hover { background:var(--surface-high); }
.task-calendar-view .task-calendar-day.selected { background:var(--hover); box-shadow:inset 0 0 0 1px var(--primary); }
.task-calendar-view .calendar-day-action.app-button { position:absolute; inset:0; width:100%; height:100%; min-width:0; min-height:0; align-items:flex-start; justify-content:space-between; padding:5px; background:transparent; border:0; border-radius:inherit; }
.calendar-day-number { width:23px; height:23px; display:grid; place-items:center; border-radius:50%; font-size:var(--text-label); }
.task-calendar-view .today .calendar-day-number { color:var(--on-selected); background:var(--primary); font-weight:600; }
.calendar-day-action small { color:var(--muted); font-size:var(--text-caption); }
.calendar-day-action small.overdue { color:var(--error); }
.task-calendar-view .calendar-milestone-band { position:relative; display:flex; margin:31px 5px 0; height:20px; min-height:20px; width:calc(100% - 10px); padding:0 5px; gap:4px; min-width:0; border:1px solid var(--tertiary); color:var(--tertiary); font-size:var(--text-caption); overflow:hidden; }
.calendar-milestone-band > span { min-width:0; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.compact .calendar-milestone-band { height:8px; min-height:8px; background:color-mix(in srgb,var(--tertiary) 20%,transparent); }
.compact .calendar-milestone-band > * { display:none; }
.calendar-day-tasks { position:relative; margin:31px 5px 0; display:grid; gap:3px; pointer-events:none; }
.calendar-milestone-band + .calendar-day-tasks { margin-top:4px; }
.task-calendar-view .task-calendar-event.app-button { pointer-events:auto; display:flex; align-items:center; text-align:left; height:19px; min-height:19px; min-width:0; width:100%; gap:4px; padding:0 5px; border:0; background:var(--row); font-size:var(--text-caption); }
.task-calendar-event i { width:6px; height:6px; border-radius:50%; flex:none; }
.task-calendar-event span { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.calendar-day-tasks > small { font-size:var(--text-caption); color:var(--muted); }
.calendar-status-dots { position:absolute; bottom:6px; left:6px; right:6px; height:8px; display:flex; gap:3px; pointer-events:none; }
.calendar-status-dots > i { width:6px; height:6px; border-radius:50%; }
.task-calendar-view .task-calendar-agenda { flex:1; overflow:auto; min-height:0; padding:0; }
.calendar-agenda-day { display:flex; flex-direction:column; gap:6px; padding:8px 0; border-bottom:1px solid var(--outline-variant); }
.calendar-agenda-day > .app-button { justify-content:start; width:100%; min-width:0; text-align:left; white-space:normal; overflow-wrap:anywhere; }
.task-calendar-view footer { display:flex; align-items:center; flex:none; min-height:28px; gap:6px; }
.task-calendar-view footer > small { flex:1; min-width:0; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; color:var(--muted); font-size:var(--text-caption); }
</style>

