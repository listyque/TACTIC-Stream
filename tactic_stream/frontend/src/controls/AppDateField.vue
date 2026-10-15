<script setup>
// Handler controls/DateField.qml (EPL-1.0): local dates and a Monday-first calendar.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppTextField from './AppTextField.vue'
import AppButton from './AppButton.vue'
import AppIcon from './AppIcon.vue'
import AppMenu from './AppMenu.vue'
import { appearance } from '../appearance.js'
import { t } from '../i18n.js'
defineOptions({ inheritAttrs:false })
const props = defineProps({ modelValue:String, label:String, disabled:Boolean, readonly:Boolean,
  includeTime:{type:Boolean,default:true}, allowClear:{type:Boolean,default:true}, placeholder:String })
const emit = defineEmits(['update:modelValue', 'change'])
const host = ref(null), field = ref(null), menu = ref(null), focused = ref(false), available = ref(0)
const month = ref(new Date()), pending = ref(new Date()), hour = ref(0), minute = ref(0)
let observer
const pad = value => String(value).padStart(2,'0')
function parse(value) {
  const match = String(value || '').match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2})(?:\.\d{1,3})?)?)?$/)
  if (!match || (!props.includeTime && match[4])) return null
  const year=Number(match[1]), month=Number(match[2]), day=Number(match[3]), hour=Number(match[4] || 0), minute=Number(match[5] || 0), second=Number(match[6] || 0)
  const date = new Date(year,month-1,day,hour,minute,second)
  return date.getFullYear() === year && date.getMonth() === month-1 && date.getDate() === day
    && date.getHours() === hour && date.getMinutes() === minute && date.getSeconds() === second ? date : null
}
const dateFormat = computed(()=>new Intl.DateTimeFormat(appearance.language,{day:'numeric',month:'long',year:'numeric'}))
function dateLabel(date) {
  const parts = Object.fromEntries(dateFormat.value.formatToParts(date).map(part=>[part.type,part.value]))
  return `${parts.day} ${parts.month} ${parts.year}`
}
const presentation = computed(()=>{
  const date = parse(props.modelValue)
  if (!date) return props.modelValue || ''
  const label = dateLabel(date), full = label+' · '+pad(date.getHours())+':'+pad(date.getMinutes())
  if (!props.includeTime || !/[ T]\d{2}:\d{2}/.test(props.modelValue)) return label
  if (!host.value) return full
  const font = getComputedStyle(host.value), context = document.createElement('canvas').getContext('2d')
  context.font = `${font.fontWeight} ${font.fontSize} ${font.fontFamily}`
  return context.measureText(full).width <= available.value-49 ? full : label
})
const heading = computed(()=>new Intl.DateTimeFormat(appearance.language,{month:'long',year:'numeric'}).format(month.value))
const weekdays = computed(()=>Array.from({length:7},(_,index)=>new Intl.DateTimeFormat(appearance.language,{weekday:'narrow'}).format(new Date(2024,0,1+index))))
const days = computed(()=>{
  const offset = (new Date(month.value.getFullYear(),month.value.getMonth(),1).getDay()+6)%7
  const count = new Date(month.value.getFullYear(),month.value.getMonth()+1,0).getDate()
  return Array.from({length:42},(_,index)=>{ const day=index-offset+1; return day>0 && day<=count ? day : 0 })
})
function sameDay(date,day) { return date.getFullYear() === month.value.getFullYear() && date.getMonth() === month.value.getMonth() && date.getDate() === day }
function opened(event) {
  if (event.target !== menu.value?.$el || event.newState !== 'open') return
  const now = new Date(), date = parse(props.modelValue) || now, explicit = /[ T]\d{2}:\d{2}/.test(props.modelValue || '')
  pending.value = date; month.value = new Date(date.getFullYear(),date.getMonth(),1)
  hour.value = explicit ? date.getHours() : now.getHours(); minute.value = explicit ? date.getMinutes() : 0
  nextTick(()=>menu.value.$el.querySelector('.calendar-day.selected')?.focus())
}
function moveMonth(step) { month.value = new Date(month.value.getFullYear(),month.value.getMonth()+step,1) }
function accept(date) {
  if (props.disabled || props.readonly) return
  if (date && props.includeTime && (!Number.isInteger(hour.value) || !Number.isInteger(minute.value) || hour.value<0 || hour.value>23 || minute.value<0 || minute.value>59)) {
    menu.value.$el.querySelector('input:invalid')?.reportValidity(); return
  }
  const value = date ? `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}`+(props.includeTime ? `T${pad(hour.value)}:${pad(minute.value)}` : '') : ''
  field.value.$el.setCustomValidity('')
  emit('update:modelValue',value); emit('change',value); menu.value.close(true)
}
function validate(value) { field.value?.$el.setCustomValidity(value && !parse(value) ? t('Enter a valid date and time') : '') }
function edit(value) { validate(value); emit('update:modelValue',value) }
watch(()=>props.modelValue,validate,{flush:'post'})
function committed(event) { if (event.target.validity.valid) emit('change',event.target.value) }
function timeValue(name) { return name === 'hour' ? hour : minute }
function stepTime(name,step) {
  const value = timeValue(name)
  value.value = Math.max(0,Math.min(name === 'hour' ? 23 : 59,Number(value.value)+step*(name === 'hour' ? 1 : 5)))
}
function timeKey(event,name) {
  if (!['ArrowUp','ArrowDown'].includes(event.key)) return
  event.preventDefault(); stepTime(name,event.key === 'ArrowUp' ? 1 : -1)
}
function dayKey(event,day) {
  const step = {ArrowLeft:-1,ArrowRight:1,ArrowUp:-7,ArrowDown:7}[event.key]
  if (!step) return
  event.preventDefault(); event.stopPropagation()
  const date = new Date(month.value.getFullYear(),month.value.getMonth(),day+step)
  month.value = new Date(date.getFullYear(),date.getMonth(),1)
  nextTick(()=>menu.value.$el.querySelector(`[data-day="${date.getDate()}"]`)?.focus())
}
onMounted(()=>{validate(props.modelValue);observer = new ResizeObserver(entries=>{available.value=entries[0].contentRect.width}); observer.observe(host.value)})
onBeforeUnmount(()=>observer?.disconnect())
</script>
<template>
  <div ref="host" class="app-date-field" :class="{ focused, disabled }">
    <AppTextField ref="field" v-bind="$attrs" type="text" :model-value="modelValue" :label="label" :placeholder="placeholder || (includeTime ? 'YYYY-MM-DD HH:mm' : 'YYYY-MM-DD')" :disabled="disabled" :readonly="readonly" :aria-invalid="modelValue && !parse(modelValue) || undefined" @focus="focused=true" @blur="focused=false" @change="committed" @update:model-value="edit" />
    <span v-if="!focused && modelValue" class="app-date-presentation" aria-hidden="true">{{ presentation }}</span>
    <AppMenu ref="menu" class="app-date-menu" :label="includeTime ? 'Choose date and time' : 'Choose date'" :disabled="disabled || readonly" overlay align-start :anchor="host" :width="304" :close-on-select="false" @toggle="opened">
      <template #trigger><AppIcon name="MDI_CALENDAR_MONTH" /></template>
      <div class="date-calendar">
        <header class="date-calendar-heading"><AppButton label="Previous month" icon="previous" icon-only @click="moveMonth(-1)" /><strong>{{ heading }}</strong><AppButton label="Next month" icon="next" icon-only @click="moveMonth(1)" /></header>
        <div class="date-calendar-grid" role="group" :aria-label="heading">
          <span v-for="(day,index) in weekdays" :key="'weekday'+index" class="calendar-weekday">{{ day }}</span>
          <template v-for="(day,index) in days" :key="index"><AppButton v-if="day" class="calendar-day" :class="{selected:sameDay(pending,day),today:sameDay(new Date(),day)}" :data-day="day" :aria-label="dateLabel(new Date(month.getFullYear(),month.getMonth(),day))" :aria-pressed="sameDay(pending,day)" @keydown="dayKey($event,day)" @click="accept(new Date(month.getFullYear(),month.getMonth(),day))">{{ day }}</AppButton><span v-else class="calendar-empty" /></template>
        </div>
        <div v-if="includeTime" class="date-calendar-time"><span>{{ t('Time') }}</span><template v-for="name in ['hour','minute']" :key="name"><span v-if="name === 'minute'">:</span><div class="date-time-spin">
          <AppButton :label="name === 'hour' ? 'Decrease hours' : 'Decrease minutes'" icon="MDI_CHEVRON_DOWN" icon-only :disabled="timeValue(name).value <= 0" @click="stepTime(name,-1)" />
          <input :value="pad(timeValue(name).value)" form="" type="number" min="0" :max="name === 'hour' ? 23 : 59" step="1" :aria-label="t(name === 'hour' ? 'Hour' : 'Minute')" @input="timeValue(name).value = $event.target.value === '' ? '' : Number($event.target.value)" @keydown="timeKey($event,name)">
          <AppButton :label="name === 'hour' ? 'Increase hours' : 'Increase minutes'" icon="MDI_CHEVRON_UP" icon-only :disabled="timeValue(name).value >= (name === 'hour' ? 23 : 59)" @click="stepTime(name,1)" />
        </div></template></div>
        <footer class="date-calendar-footer"><AppButton v-if="allowClear" label="Clear" @click="accept(null)" /><AppButton label="Today" @click="accept(new Date())" /></footer>
      </div>
    </AppMenu>
  </div>
</template>
<style>
.app-date-field { display:block; min-width:0; position:relative; font-size:var(--text-body); font-weight:400; letter-spacing:normal; text-transform:none; }
.app-date-field.app-date-field > input.app-text-field { width:100%; padding-right:41px; }
.app-date-field.app-date-field > input:focus { padding-right:40px; }
.app-date-field:not(.focused):has(.app-date-presentation) > input { color:transparent; }
.app-date-presentation { position:absolute; inset:0 37px 0 12px; display:block; align-content:center; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; pointer-events:none; }
.app-date-field.disabled .app-date-presentation { color:var(--disabled); }
.app-date-menu.workspace-menu { position:absolute; right:4px; top:50%; transform:translateY(-50%); width:28px; height:28px; }
.app-date-menu > summary.icon-button { width:28px; height:28px; min-width:28px; min-height:28px; padding:0; }
.app-date-menu > summary > .app-icon { --icon-size:16px; color:var(--muted); }
.app-date-menu > summary[aria-disabled] { color:var(--disabled); cursor:default; }
.app-date-menu > .account-panel { padding:10px; }
.date-calendar { display:flex; flex-direction:column; gap:7px; }
.date-calendar-heading { display:flex; align-items:center; height:42px; border-radius:var(--item-radius); background:var(--surface-high); padding:0 4px; }
.date-calendar-heading strong { flex:1; min-width:0; font-size:var(--text-body-large); text-align:center; text-transform:none; }
.date-calendar-heading > .icon-button { width:28px; height:28px; min-width:28px; min-height:28px; }
.date-calendar-grid { display:grid; grid-template-columns:repeat(7,minmax(0,1fr)); gap:2px; }
.calendar-weekday { height:20px; align-content:center; text-align:center; font-size:var(--text-caption); color:var(--muted); }
.date-calendar .date-calendar-grid > .calendar-day.app-button { position:relative; justify-content:center; height:30px; min-height:30px; min-width:0; padding:0; background:transparent; font-size:var(--text-label); font-weight:400; isolation:isolate; }
.calendar-empty { height:30px; }
.calendar-day::before { content:''; position:absolute; z-index:-1; width:28px; height:28px; border-radius:50%; }
.date-calendar .date-calendar-grid > .calendar-day:hover { background:transparent; }
.calendar-day:hover::before { background:var(--hover); }
.calendar-day.today::before { border:1px solid var(--primary); }
.calendar-day.selected::before { background:var(--selected); border:0; }
.date-calendar .date-calendar-grid > .calendar-day.selected { color:var(--on-selected); font-weight:600; }
.date-calendar-time { display:flex; align-items:center; gap:7px; font-size:var(--text-label); color:var(--muted); }
.date-calendar-time > span:first-child { flex:1; }
.date-time-spin { position:relative; flex:0 0 92px; width:92px; height:var(--control-height); }
.app-date-field .date-calendar .date-time-spin > input { width:100%; min-width:0; height:100%; padding:0 34px; text-align:center; appearance:textfield; font-size:var(--text-body); }
.date-time-spin > input::-webkit-inner-spin-button, .date-time-spin > input::-webkit-outer-spin-button { appearance:none; margin:0; }
.date-time-spin > .icon-button { position:absolute; inset:0 auto 0 0; min-width:0; min-height:0; width:34px; height:100%; padding:0; }
.date-time-spin > .icon-button:last-child { left:auto; right:0; }
.date-time-spin > .icon-button > .app-icon { width:14px; height:14px; font-size:14px; }
.date-calendar-footer { display:flex; align-items:center; justify-content:space-between; border-top:1px solid var(--outline-variant); padding-top:7px; }
.date-calendar-footer > .app-button { min-width:0; min-height:var(--control-height); }
.date-calendar-footer > .app-button:last-child { margin-left:auto; }
</style>
