<script setup>
// Handler TaskGanttView.qml / TaskGanttProgressHandle.qml (EPL-1.0).
// TaskManager owns revisions, permissions, draft history and server writes.
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { t } from '../../i18n.js'
import { appearance } from '../../appearance.js'
import AppButton from '../../controls/AppButton.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppSelect from '../../controls/AppSelect.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
const props=defineProps({projection:Object,tasks:{type:Array,default:()=>[]},selected:{type:Array,default:()=>[]},collapsed:{type:Array,default:()=>[]},busy:Boolean,projecting:Boolean,workingDays:Boolean,resourceMode:Boolean,canUndo:Boolean,canRedo:Boolean,active:String,hasMore:Boolean})
const emit=defineEmits(['select','select-all','activate','object','collapse','edit','inspect','working-days','resource-mode','undo','redo','batch','schedule','milestone','progress','delete','load-more'])
const root=ref(null), body=ref(null), viewport=ref(800), gutter=ref(0), scrollX=ref(0), scrollY=ref(0), bodyHeight=ref(400), zoom=ref(1), scale=ref('auto'), drag=ref(null)
let observer, resizeFrame, autoScroll, ignoreClickUntil=0
const range=computed(()=>props.projection?.gantt)
const dayCount=computed(()=>Math.max(1,range.value?.days || 1))
const labelWidth=computed(()=>Math.min(310,Math.max(220,viewport.value*.3)))
const timelineViewport=computed(()=>Math.max(1,viewport.value-labelWidth.value-gutter.value))
const baseDayWidth=computed(()=>Math.max(10,Math.min(28,timelineViewport.value/dayCount.value)))
const dayWidth=computed(()=>Math.max(2,Math.min(80,baseDayWidth.value*zoom.value)))
const timelineWidth=computed(()=>Math.max(timelineViewport.value,dayCount.value*dayWidth.value))
const tasksByKey=computed(()=>new Map(props.tasks.map(task=>[task.key,task])))
const ticks=computed(()=>{
 const mode=dayWidth.value>=22?'days':dayWidth.value>=7?'weeks':dayWidth.value>=2.8?'months':'quarters'
 return (range.value?.tickSets[mode] || []).filter(tick=>tick.offsetDay*dayWidth.value>=scrollX.value-100 && tick.offsetDay*dayWidth.value<=scrollX.value+timelineViewport.value+100)
})
const rows=computed(()=>{
 const result=[];let top=0
 function add(kind,key,record,height){result.push({kind,key,record,height,top});top+=height}
 for(const record of range.value?.records || []){
  if(record.ganttSectionFirst) add('section','section:'+record.ganttSection,record,28)
  if(record.groupFirst && record.groupKey) add('group',record.ganttSection+':'+record.groupKey,record,27)
  if(!props.collapsed.includes(record.groupKey))add('task',record.taskCode,record,50)
 }
 return result
})
const totalHeight=computed(()=>rows.value.at(-1) ? rows.value.at(-1).top+rows.value.at(-1).height : 0)
const visibleRows=computed(()=>rows.value.filter(row=>row.top+row.height>=scrollY.value-100 && row.top<scrollY.value+bodyHeight.value+100))
const grid=computed(()=>{
 const first=Math.max(0,Math.floor(scrollX.value/dayWidth.value)-1), last=Math.min(dayCount.value,Math.ceil((scrollX.value+timelineViewport.value)/dayWidth.value)+1)
 return Array.from({length:Math.max(0,last-first+1)},(_,index)=>{const day=first+index,date=new Date(dateForDay(day)+'T12:00:00Z');return {day,major:date.getUTCDate()===1,week:date.getUTCDay()===1}})
})
const warningCount=computed(()=>range.value?.warnings || 0)
const overviewThumb=computed(()=>({left:scrollX.value/timelineWidth.value*100+'%',width:Math.min(100,timelineViewport.value/timelineWidth.value*100)+'%'}))
const batchActions=[['Shift one day earlier','shift',-1],['Shift one day later','shift',1],['Align start dates','align-start',1],['Align deadlines','align-end',1],['Schedule sequentially','sequence',1],['Extend by one day','extend',1],['Shorten by one day','shorten',1]]
function dateForDay(day){const value=new Date((range.value?.rangeStart || '2000-01-01')+'T12:00:00Z');value.setUTCDate(value.getUTCDate()+day);return value.toISOString().slice(0,10)}
function dateLabel(value,options={month:'short',day:'numeric'}){return value?new Intl.DateTimeFormat(appearance.language,options).format(new Date(value.slice(0,10)+'T12:00:00')):'—'}
function tickLabel(tick){
 if(dayWidth.value>=22)return dateLabel(tick.date,{day:'numeric'})
 if(dayWidth.value>=7)return dateLabel(tick.date)
 if(dayWidth.value>=2.8)return dateLabel(tick.date,{month:'short',year:'numeric'})
 return t('Q{quarter} {year}',{quarter:Math.floor((Number(tick.date.slice(5,7))-1)/3)+1,year:tick.date.slice(0,4)})
}
function warningText(record){return (record.ganttWarning || record.ganttIssue || '').split('\n').map(value=>t(value)).join('\n')}
function color(record){return tasksByKey.value.get(record.taskCode)?.__status__?.color || record.ganttColor || 'var(--primary)'}
function progress(record){return drag.value?.key===record.taskCode && drag.value.mode==='progress'?drag.value.progress:record.progress}
function geometry(record){
 const pending=drag.value?.key===record.taskCode && drag.value.mode!=='progress'?drag.value:null
 return {left:(pending?.start ?? record.ganttStartDay)*dayWidth.value+'px',width:Math.max(7,(pending?.duration ?? record.ganttDurationDays)*dayWidth.value-4)+'px','--bar-color':color(record)}
}
function synchronize(){scrollX.value=body.value.scrollLeft;scrollY.value=body.value.scrollTop}
function setScroll(value){body.value.scrollLeft=Math.max(0,Math.min(timelineWidth.value-timelineViewport.value,value));synchronize()}
async function setZoom(value,anchor=timelineViewport.value/2,mode='custom'){
 const day=(scrollX.value+anchor)/dayWidth.value;scale.value=mode;zoom.value=Math.max(.15,Math.min(5,value))
 await nextTick();setScroll(day*dayWidth.value-anchor)
}
function setScale(mode){const widths={days:28,weeks:12,months:5,quarters:2,auto:baseDayWidth.value};setZoom(widths[mode]/baseDayWidth.value,timelineViewport.value/2,mode)}
function wheel(event){
 event.preventDefault()
 if(event.shiftKey || Math.abs(event.deltaX)>Math.abs(event.deltaY))setScroll(scrollX.value+(event.deltaX || event.deltaY)*1.65)
 else setZoom(zoom.value*Math.pow(1.16,-event.deltaY/(event.deltaMode===1?3:100)),Math.max(0,event.clientX-event.currentTarget.getBoundingClientRect().left))
}
function edit(key){if(performance.now()>=ignoreClickUntil && !props.busy)emit('edit',key)}
function begin(record,mode,event){
 if(props.busy || event.pointerType!=='mouse' || event.button!==0)return
 event.preventDefault();event.stopPropagation();event.currentTarget.setPointerCapture(event.pointerId)
 const timeline=event.currentTarget.closest('.task-gantt-timeline'), box=timeline.getBoundingClientRect()
 drag.value={key:record.taskCode,mode,x:event.clientX,baseScroll:scrollX.value,baseStart:record.ganttStartDay,baseDuration:record.ganttDurationDays,start:record.ganttStartDay,duration:Math.max(1,record.ganttDurationDays),progress:record.progress,baseProgress:record.progress,clientX:event.clientX,barLeft:box.left+record.ganttStartDay*dayWidth.value,barWidth:Math.max(7,record.ganttDurationDays*dayWidth.value-4)}
 if(mode==='create'){drag.value.start=Math.round((event.clientX-box.left)/dayWidth.value);drag.value.baseStart=drag.value.start;drag.value.duration=1}
 autoScroll=setInterval(()=>{
  if(!drag.value || drag.value.mode==='progress')return
  const rect=body.value.getBoundingClientRect(),x=drag.value.clientX
  if(x<rect.left+labelWidth.value+28)setScroll(scrollX.value-10)
  else if(x>rect.right-28)setScroll(scrollX.value+10)
  updateDrag(x)
 },20)
}
function updateDrag(x){
 const value=drag.value;if(!value)return
 value.clientX=x
 if(value.mode==='progress'){value.progress=Math.max(0,Math.min(100,Math.round((x-value.barLeft)/value.barWidth*100)));return}
 const delta=Math.round((x-value.x+scrollX.value-value.baseScroll)/dayWidth.value)
 if(value.mode==='move')value.start=Math.max(-3650,Math.min(36600,value.baseStart+delta))
 else if(value.mode==='start'){value.start=Math.max(-3650,Math.min(value.baseStart+value.baseDuration-1,value.baseStart+delta));value.duration=Math.min(3650,value.baseDuration+value.baseStart-value.start)}
 else if(value.mode==='create'){value.start=value.baseStart+Math.min(0,delta);value.duration=Math.min(3650,Math.abs(delta)+1)}
 else value.duration=Math.max(1,Math.min(3650,value.baseDuration+delta))
}
function finish(cancel=false){
 clearInterval(autoScroll);const value=drag.value;drag.value=null
 if(!value)return
 const changed=value.mode==='create' || value.mode==='progress' && value.progress!==value.baseProgress || value.start!==value.baseStart || value.duration!==value.baseDuration
 if(changed)ignoreClickUntil=performance.now()+150
 if(cancel || !changed)return
 if(value.mode==='progress')emit('progress',value.key,value.progress)
 else if(value.mode==='create' || value.start!==value.baseStart || value.duration!==value.baseDuration)emit('schedule',value.key,value.start,value.duration,value.mode)
}
function keyboard(event){if(event.key==='Escape' && drag.value){event.preventDefault();event.stopPropagation();finish(true)}}
function progressKey(event,record){
 const step={ArrowLeft:-1,ArrowRight:1,Home:-100,End:100}[event.key];if(step===undefined)return
 event.preventDefault();event.stopPropagation();emit('progress',record.taskCode,Math.max(0,Math.min(100,record.progress+step)))
}
function overview(event){
 if(event.type==='pointerdown'){event.preventDefault();event.currentTarget.setPointerCapture(event.pointerId)}
 if(event.type==='pointermove' && !event.buttons)return
 const box=event.currentTarget.getBoundingClientRect()
 setScroll((event.clientX-box.left)/box.width*timelineWidth.value-timelineViewport.value/2)
}
function pan(event){
 if(event.pointerType!=='mouse' || ![0,1].includes(event.button) || event.target.closest('button,input,label,summary'))return
 event.preventDefault();event.currentTarget.setPointerCapture(event.pointerId);event.currentTarget.dataset.panX=event.clientX;event.currentTarget.dataset.panScroll=scrollX.value
}
function move(event){if(drag.value)updateDrag(event.clientX);else if([1,4].includes(event.buttons) && event.currentTarget.dataset.panX)setScroll(Number(event.currentTarget.dataset.panScroll)+Number(event.currentTarget.dataset.panX)-event.clientX)}
onMounted(()=>{
 const measured={width:800,bodyWidth:800,bodyHeight:400}
 observer=new ResizeObserver(entries=>{
  // Rounded client sizes can make the canvas overflow its own fractional viewport.
  for(const {target,contentRect} of entries) {
   if(target===root.value)measured.width=contentRect.width
   else {measured.bodyWidth=contentRect.width;measured.bodyHeight=contentRect.height}
  }
  cancelAnimationFrame(resizeFrame)
  resizeFrame=requestAnimationFrame(()=>{viewport.value=measured.width;gutter.value=Math.max(0,measured.width-measured.bodyWidth);bodyHeight.value=measured.bodyHeight})
 })
 observer.observe(root.value);observer.observe(body.value)
 document.addEventListener('keydown',keyboard,true);window.addEventListener('blur',cancel)
})
function cancel(){finish(true)}
onBeforeUnmount(()=>{observer?.disconnect();cancelAnimationFrame(resizeFrame);clearInterval(autoScroll);document.removeEventListener('keydown',keyboard,true);window.removeEventListener('blur',cancel)})
</script>
<template>
 <section ref="root" class="task-schedule-view task-gantt-view" :aria-label="t('Task Gantt')" :aria-busy="projecting" :style="{'--gantt-label-width':labelWidth+'px','--gantt-width':timelineWidth+'px','--gantt-scroll-gutter':gutter+'px'}">
  <header class="gantt-heading"><div class="gantt-heading-label"><AppCheckbox hide-label label="Select all tasks" :model-value="!!tasks.length && tasks.every(task=>selected.includes(task.key))" :disabled="busy" @update:model-value="emit('select-all',$event)" /><AppIcon name="MDI_CHART_GANTT" /><div class="gantt-heading-copy"><strong>{{ t('Task schedule') }}</strong><small>{{ t('{scheduled} scheduled · {unscheduled} unscheduled',{scheduled:range?.scheduled || 0,unscheduled:range?.unscheduled || 0}) }}</small></div></div>
   <div class="gantt-heading-viewport" @wheel="wheel"><div class="gantt-heading-content" :style="{transform:'translateX('+-scrollX+'px)',width:timelineWidth+'px'}">
    <span v-for="tick in ticks" :key="tick.date" class="task-gantt-tick" :class="{major:tick.major}" :style="{left:tick.offsetDay*dayWidth+6+'px',width:Math.max(0,(tick.spanDays || 1)*dayWidth-8)+'px'}">{{ tickLabel(tick) }}</span>
    <AppButton v-for="marker in range?.milestones || []" :key="marker.code" class="task-gantt-milestone" :style="{left:marker.offsetDay*dayWidth+'px'}" icon="MDI_FLAG_VARIANT" :title="marker.label+' · '+marker.dueDate" @click="emit('milestone',marker.code)">{{ marker.label }}</AppButton>
    <span v-if="range?.todayDay>=0" class="task-gantt-today" :style="{left:range.todayDay*dayWidth+'px'}"><small>{{ t('TODAY') }}</small></span>
   </div></div>
  </header>
  <div ref="body" class="gantt-body" tabindex="0" :aria-label="t('Task schedule')" @scroll="synchronize" @pointerdown="pan" @pointermove="move" @pointerup="finish()" @pointercancel="finish(true)">
   <div class="gantt-canvas" :style="{height:Math.max(bodyHeight,totalHeight)+'px',width:labelWidth+timelineWidth+'px'}">
    <div class="gantt-grid" :style="{left:labelWidth+'px',width:timelineWidth+'px'}">
     <span v-for="weekend in range?.weekends || []" :key="'weekend'+weekend.offsetDay" class="gantt-weekend" :style="{left:weekend.offsetDay*dayWidth+'px',width:weekend.durationDays*dayWidth+'px'}" />
     <span v-for="line in dayWidth>=16?grid:ticks.map(tick=>({day:tick.offsetDay,major:tick.major,week:true}))" :key="'line'+line.day" class="gantt-grid-line" :class="{major:line.major,week:line.week}" :style="{left:line.day*dayWidth+'px'}" />
     <span v-for="marker in range?.milestones || []" :key="marker.code" class="gantt-milestone-line" :style="{left:marker.offsetDay*dayWidth+'px'}" />
     <span v-if="range?.todayDay>=0" class="task-gantt-today" :style="{left:range.todayDay*dayWidth+'px'}" />
    </div>
    <div v-for="row in visibleRows" :key="row.key" class="task-gantt-row" :class="['gantt-'+row.kind,{'task-selected':selected.includes(row.key),'task-active':active===row.key,pending:tasksByKey.get(row.key)?.pending}]" :data-task-key="row.kind==='task'?row.key:undefined" :style="{top:row.top+'px',height:row.height+'px'}">
     <template v-if="row.kind==='section'"><div class="task-gantt-label task-gantt-section"><AppIcon :name="row.record.ganttSection==='scheduled'?'MDI_CLOCK_OUTLINE':'warning'" />{{ t(row.record.ganttSection==='scheduled'?'Scheduled tasks':'Unscheduled tasks') }}</div><div class="task-gantt-timeline" /></template>
     <template v-else-if="row.kind==='group'"><div class="task-gantt-label"><AppButton :icon="collapsed.includes(row.record.groupKey)?'next':'MDI_CHEVRON_DOWN'" :aria-expanded="!collapsed.includes(row.record.groupKey)" @click="emit('collapse',row.record.groupKey)">{{ row.record.group }} · {{ row.record.groupCount }}</AppButton></div><div class="task-gantt-timeline"><span v-if="row.record.ganttGroupDurationDays" class="task-gantt-summary" :style="{left:row.record.ganttGroupStartDay*dayWidth+'px',width:row.record.ganttGroupDurationDays*dayWidth+'px'}"><span :style="{width:row.record.ganttGroupProgress+'%'}" /></span></div></template>
     <template v-else><div class="task-gantt-label">
      <AppCheckbox hide-label :label="t('Select task')+' '+row.record.parentTitle+' '+row.record.processLabel" :translate-label="false" :model-value="selected.includes(row.key)" :disabled="busy" @update:model-value="emit('select',row.key,$event)" />
      <ItemPreview :source="tasksByKey.get(row.key)?.parent?.__preview_url__" :fallback-text="row.record.parentTitle.slice(0,2).toUpperCase()" fallback-icon="sobject" :preview-size="30" :accent="color(row.record)" />
      <AppButton class="task-gantt-title" :title="row.record.parentTitle+' · '+row.record.processLabel" :disabled="busy" @click="emit('activate',row.key,$event)" @dblclick="emit('object',row.key)"><strong>{{ row.record.parentTitle }}</strong><small>{{ row.record.processLabel }} · {{ row.record.assignedLabel }}</small></AppButton>
      <AppButton label="Edit schedule" icon="edit" icon-only :disabled="busy" @click="edit(row.key)" /><AppIcon v-if="row.record.ganttWarning" name="warning" class="gantt-warning" :title="warningText(row.record)" />
     </div><div class="task-gantt-timeline" @pointerdown="!row.record.ganttScheduled && !$event.target.closest('button,input') && begin(row.record,'create',$event)" @dblclick="edit(row.key)">
      <div v-if="row.record.ganttScheduled || drag?.key===row.key" class="task-gantt-bar" :style="geometry(row.record)" :title="row.record.parentTitle+' · '+row.record.status+'\n'+row.record.start+' — '+row.record.end+'\n'+warningText(row.record)">
       <AppButton class="task-gantt-move" :aria-label="t('Edit schedule')+' '+row.record.parentTitle" :disabled="busy" @click="emit('activate',row.key,$event)" @dblclick="emit('object',row.key)" @pointerdown="begin(row.record,'move',$event)" @pointermove="move" @pointerup.stop="finish()" @pointercancel="finish(true)">
        <span class="task-gantt-progress" :style="{width:progress(row.record)+'%'}" /><span>{{ row.record.processLabel }} {{ progress(row.record) }}%</span>
       </AppButton>
       <small class="gantt-date-chip start">{{ dateLabel(row.record.start) }}</small><small class="gantt-date-chip end">{{ dateLabel(row.record.end) }}</small>
       <AppButton label="Resize start date" class="task-gantt-resize start" :disabled="busy" @click="edit(row.key)" @pointerdown="begin(row.record,'start',$event)" @pointermove="move" @pointerup.stop="finish()" @pointercancel="finish(true)"><span /></AppButton>
       <AppButton label="Resize deadline" class="task-gantt-resize end" :disabled="busy" @click="edit(row.key)" @pointerdown="begin(row.record,'end',$event)" @pointermove="move" @pointerup.stop="finish()" @pointercancel="finish(true)"><span /></AppButton>
       <AppButton v-if="row.record.ganttScheduled && parseFloat(geometry(row.record).width)>=36 && (Object.hasOwn(tasksByKey.get(row.key) || {},'progress') || Object.hasOwn(tasksByKey.get(row.key) || {},'completion'))" class="gantt-progress-handle" label="Progress" role="slider" :aria-valuenow="progress(row.record)" aria-valuemin="0" aria-valuemax="100" :style="{left:Math.max(18,Math.min(parseFloat(geometry(row.record).width)-18,parseFloat(geometry(row.record).width)*progress(row.record)/100))-9+'px'}" :disabled="busy" @keydown="progressKey($event,row.record)" @pointerdown="begin(row.record,'progress',$event)" @pointermove="move" @pointerup.stop="finish()" @pointercancel="finish(true)"><span /></AppButton>
      </div>
      <AppButton v-else class="gantt-issue" label="Set task schedule" :disabled="busy" @click="edit(row.key)">{{ warningText(row.record) }}</AppButton>
     </div></template>
    </div>
   </div>
   <p v-if="!range?.records.length" class="gantt-empty">{{ t(projecting?'Loading data…':'No tasks match the current scope and filters') }}</p>
  </div>
  <div class="gantt-overview"><span :title="t('{count} schedule warnings',{count:warningCount})"><AppIcon :name="warningCount?'warning':'MDI_EYE_OUTLINE'" />{{ warningCount?t('{count} schedule warnings',{count:warningCount}):t('Project overview') }}</span><div class="task-gantt-overview" role="slider" tabindex="0" :aria-label="t('Timeline overview')" aria-valuemin="0" :aria-valuemax="dayCount" :aria-valuenow="Math.round(scrollX/dayWidth)" @pointerdown="overview" @pointermove="overview" @keydown.left.prevent="setScroll(scrollX-100)" @keydown.right.prevent="setScroll(scrollX+100)"><i v-for="(item,index) in range?.overview || []" :key="index" :style="{left:item.startDay/dayCount*100+'%',width:item.durationDays/dayCount*100+'%'}" :class="{warning:item.warning}" /><b :style="overviewThumb" /></div></div>
  <footer class="gantt-footer">
   <small>{{ range?.rangeStart }} — {{ range?.rangeEnd }}</small><AppButton v-if="hasMore" label="Load more tasks" icon="add" icon-only :disabled="busy" @click="emit('load-more')" />
   <AppMenu label="Schedule options" overlay :close-on-select="false">
    <AppCheckbox label="Working days only" :model-value="workingDays" :disabled="busy" @update:model-value="emit('working-days',$event)" />
    <AppCheckbox label="Group workload by assignee" :model-value="resourceMode" :disabled="busy" @update:model-value="emit('resource-mode',$event)" />
    <AppSelect :model-value="scale" label="Timeline scale" :options="[{value:'auto',label:'Fit range'},{value:'days',label:'Days'},{value:'weeks',label:'Weeks'},{value:'months',label:'Months'},{value:'quarters',label:'Quarters'}]" @update:model-value="setScale" />
    <AppButton v-for="[label,operation,amount] in batchActions" :key="label" :label="label" :disabled="busy || !selected.length" @click="emit('batch',operation,amount)" />
    <AppButton label="Delete selected tasks" icon="delete" destructive :disabled="busy || !selected.length" @click="emit('delete')" />
   </AppMenu>
   <AppButton label="Undo schedule change" icon="MDI_UNDO" icon-only :disabled="busy || !canUndo" @click="emit('undo')" /><AppButton label="Redo schedule change" icon="MDI_REDO" icon-only :disabled="busy || !canRedo" @click="emit('redo')" />
   <AppButton label="Working days only" icon="MDI_CALENDAR_TODAY" icon-only :aria-pressed="workingDays" :disabled="busy" @click="emit('working-days',!workingDays)" /><AppButton label="Group workload by assignee" icon="MDI_ACCOUNT_GROUP" icon-only :aria-pressed="resourceMode" :disabled="busy" @click="emit('resource-mode',!resourceMode)" />
   <AppButton v-if="viewport>=700" label="Zoom out" icon="MDI_MAGNIFY_MINUS_OUTLINE" icon-only :disabled="zoom<=.15" @click="setZoom(zoom/1.25)" /><AppButton v-if="viewport>=700" label="Timeline scale" class="gantt-zoom" @click="setScale('auto')">{{ Math.round(zoom*100) }}%</AppButton><AppButton v-if="viewport>=700" label="Zoom in" icon="MDI_MAGNIFY_PLUS_OUTLINE" icon-only :disabled="zoom>=5" @click="setZoom(zoom*1.25)" />
   <AppButton label="Center today" icon="MDI_CALENDAR_TODAY" icon-only :disabled="!range || range.todayDay<0" @click="setScroll(range.todayDay*dayWidth-timelineViewport*.42)" /><slot name="footer" />
  </footer>
 </section>
</template>
<style>
.task-gantt-view { display:flex; flex-direction:column; height:100%; min-height:0; min-width:0; overflow:hidden; }
.task-gantt-view .gantt-heading { flex:none; height:54px; display:grid; grid-template-columns:var(--gantt-label-width) minmax(0,1fr); padding-right:var(--gantt-scroll-gutter); background:var(--surface); border-radius:var(--item-radius); }
.gantt-heading-label { display:flex; align-items:center; gap:7px; padding:0 10px; min-width:0; }
.gantt-heading-label strong { text-transform:uppercase; font-size:var(--text-caption); }
.gantt-heading-copy { display:flex; flex:1; flex-direction:column; min-width:0; gap:2px; }
.gantt-heading-copy > * { overflow:hidden; white-space:nowrap; text-overflow:ellipsis; }
.gantt-heading-label small { color:var(--muted); font-size:var(--text-caption); }
.gantt-heading-viewport { overflow:hidden; min-width:0; }
.gantt-heading-content { position:relative; height:54px; }
.task-gantt-view .task-gantt-tick { position:absolute; top:50%; transform:translateY(-50%); font-size:7px; color:var(--muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.task-gantt-view .task-gantt-tick.major { font-size:8px; font-weight:600; color:var(--on-surface); }
.task-gantt-view .task-gantt-milestone { position:absolute; bottom:3px; height:22px; min-height:22px; min-width:0; padding:0 4px; font-size:var(--text-caption); color:var(--tertiary); border:0; background:var(--surface-high); max-width:140px; overflow:hidden; white-space:nowrap; }
.gantt-body { flex:1; min-height:0; min-width:0; overflow:auto; overscroll-behavior:contain; position:relative; margin-top:3px; }
.gantt-canvas { position:relative; }
.gantt-grid { position:absolute; inset:0 auto 0 0; pointer-events:none; }
.gantt-weekend { position:absolute; top:0; bottom:0; background:var(--surface-high); opacity:.22; }
.gantt-grid-line { position:absolute; top:0; bottom:0; width:1px; background:var(--outline-variant); opacity:.24; }
.gantt-grid-line.week { background:var(--outline); opacity:.38; }
.gantt-grid-line.major { width:2px; opacity:.52; }
.gantt-milestone-line { position:absolute; top:0; bottom:0; width:3px; background:var(--tertiary); opacity:.45; }
.task-gantt-view .task-gantt-today { position:absolute; top:0; bottom:0; width:3px; background:var(--error); opacity:.82; pointer-events:none; }
.task-gantt-today small { position:absolute; bottom:2px; right:7px; font-size:var(--text-micro); color:var(--error); }
.task-gantt-view .task-gantt-row { position:absolute; left:0; width:100%; display:grid; grid-template-columns:var(--gantt-label-width) var(--gantt-width); min-height:0; border-bottom:1px solid var(--outline-variant); }
.task-gantt-view .task-gantt-row:hover { background:var(--hover); }
.task-gantt-view .task-gantt-label { position:sticky; left:0; z-index:3; display:flex; align-items:center; gap:7px; min-width:0; padding:0 8px 0 5px; background:var(--surface); }
.task-gantt-view .task-gantt-row.task-selected { background:var(--content-selection); }
.task-gantt-view .task-gantt-row.pending .task-gantt-label { box-shadow:inset 2px 0 var(--primary); }
.task-gantt-view .task-gantt-section { text-transform:uppercase; color:var(--muted); font-size:var(--text-caption); }
.task-gantt-view .task-gantt-label > .image-picker-preview { width:30px; height:30px; flex:0 0 30px; }
.task-gantt-view .task-gantt-label > .app-checkbox { padding:0; gap:0; }
.task-gantt-view .task-gantt-title.app-button { flex:1; display:flex; flex-direction:column; align-items:flex-start; gap:0; padding:0; min-width:0; min-height:0; background:transparent; border:0; border-radius:0; text-align:left; overflow:hidden; }
.task-gantt-title strong,.task-gantt-title small { max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.task-gantt-title strong { font-size:var(--text-label); }
.task-gantt-title small { color:var(--muted); font-size:var(--text-micro); font-weight:400; }
.gantt-warning.app-icon { width:13px; height:13px; font-size:13px; color:var(--yellow); }
.task-gantt-view .task-gantt-timeline { position:relative; min-height:0; background:none; }
.task-gantt-view .task-gantt-bar { position:absolute; top:50%; transform:translateY(-50%); height:27px; min-width:7px; border:0; background:transparent; border-radius:var(--item-radius); }
.task-gantt-view .task-gantt-move.app-button { position:relative; width:100%; height:27px; min-height:27px; min-width:0; padding:0 7px 0 30px; border:0; border-radius:inherit; background:color-mix(in srgb,var(--bar-color) 30%,transparent); font-size:var(--text-caption); overflow:hidden; justify-content:start; cursor:grab; }
.task-gantt-view .task-gantt-progress { position:absolute; inset:0 auto 0 0; background:var(--bar-color); opacity:.88; border-radius:inherit; pointer-events:none; }
.task-gantt-view .task-gantt-move > span:last-child { position:relative; z-index:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.task-gantt-view .task-gantt-resize.app-button { position:absolute; top:50%; transform:translateY(-50%); width:12px; height:22px; min-width:12px; min-height:22px; padding:0; border:1px solid var(--on-surface); border-radius:5px; background:var(--surface-high); opacity:1; cursor:ew-resize; }
.task-gantt-view .task-gantt-resize.start { left:-8px; }
.task-gantt-view .task-gantt-resize.end { right:-8px; }
.task-gantt-resize > span { width:2px; height:10px; border-radius:1px; background:var(--on-surface); }
.gantt-progress-handle.app-button { position:absolute; z-index:5; top:50%; transform:translateY(-50%); width:18px; height:22px; min-width:18px; min-height:22px; padding:0; border:1px solid var(--on-surface); border-radius:6px; background:var(--surface-high); cursor:ew-resize; opacity:0; }
.task-gantt-row:hover .gantt-progress-handle,.task-gantt-row:focus-within .gantt-progress-handle { opacity:1; }
.gantt-progress-handle span { width:7px; height:9px; border-inline:2px solid var(--on-surface); }
.gantt-date-chip { display:none; position:absolute; top:-10px; height:17px; padding:0 6px; border:1px solid var(--outline-variant); border-radius:9px; background:var(--surface-high); color:var(--on-surface); font-size:var(--text-micro); pointer-events:none; z-index:8; white-space:nowrap; }
.gantt-date-chip.end { right:0; }
.task-gantt-bar:hover .gantt-date-chip { display:block; }
.task-gantt-view .task-gantt-summary { position:absolute; height:5px; top:11px; min-width:0; padding:0; border-radius:3px; background:color-mix(in srgb,var(--primary) 34%,transparent); }
.task-gantt-summary > span { display:block; height:100%; border-radius:inherit; background:var(--primary); }
.gantt-group .task-gantt-label .app-button { padding:0; min-height:0; min-width:0; background:transparent; border:0; text-transform:uppercase; font-size:var(--text-caption); }
.gantt-issue.app-button { margin:12px 8px; min-height:24px; height:24px; padding:0 8px; border:1px solid var(--yellow); background:transparent; color:var(--yellow); border-radius:12px; font-size:var(--text-caption); }
.gantt-empty { position:absolute; inset:20px 0 auto; text-align:center; color:var(--muted); }
.gantt-overview { flex:none; height:30px; display:grid; grid-template-columns:var(--gantt-label-width) minmax(0,1fr); padding-right:var(--gantt-scroll-gutter); gap:0; }
.gantt-overview > span { display:flex; align-items:center; gap:6px; padding:0 10px; font-size:var(--text-caption); color:var(--muted); min-width:0; overflow:hidden; white-space:nowrap; }
.task-gantt-view .task-gantt-overview { position:relative; left:auto; width:auto; height:30px; min-width:0; border:1px solid var(--outline-variant); border-radius:var(--item-radius); background:var(--surface); overflow:hidden; cursor:ew-resize; touch-action:none; }
.task-gantt-overview > i { position:absolute; top:9px; height:10px; background:var(--primary); min-width:2px; opacity:.5; pointer-events:none; }
.task-gantt-overview > i.warning { background:var(--yellow); opacity:.9; }
.task-gantt-overview > b { position:absolute; inset:3px auto 3px; min-width:8px; border:1px solid var(--primary); border-radius:var(--item-radius); background:color-mix(in srgb,var(--primary) 15%,transparent); pointer-events:none; }
.gantt-footer { flex:none; display:flex; align-items:center; gap:5px; height:36px; border-top:1px solid var(--outline-variant); background:var(--surface); padding:0 8px; min-width:0; }
.gantt-footer > small { flex:1; min-width:0; overflow:hidden; white-space:nowrap; color:var(--muted); font-size:var(--text-caption); }
.gantt-footer > .icon-button,.gantt-footer > .workspace-menu > summary { width:28px; height:28px; min-width:28px; min-height:28px; }
.gantt-footer > .gantt-zoom { height:28px; min-height:28px; min-width:48px; padding:0 4px; border:0; background:transparent; font-size:var(--text-caption); }
.gantt-footer > .workspace-menu { position:relative; }
@media(max-width:700px){.gantt-footer > small {display:none}}
</style>


<style>
.task-gantt-view .task-gantt-label > .icon-button { width:22px; height:22px; min-width:22px; min-height:22px; flex:none; opacity:0; }
.task-gantt-row:hover .task-gantt-label > .icon-button,.task-gantt-row:focus-within .task-gantt-label > .icon-button { opacity:1; }
.task-gantt-view .task-active .task-gantt-label { box-shadow:inset 2px 0 var(--primary); }
.task-gantt-view .task-gantt-move.app-button:not(:has(~ .gantt-progress-handle)) { padding-left:7px; }
</style>

<style>
@media(hover:none) { .task-gantt-view .task-gantt-label > .icon-button { opacity:1; } }
</style>
