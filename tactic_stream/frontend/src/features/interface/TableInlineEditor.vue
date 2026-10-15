<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import AppTextField from '../../controls/AppTextField.vue'
import AppTextArea from '../../controls/AppTextArea.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import AppSwitch from '../../controls/AppSwitch.vue'
import AppDateField from '../../controls/AppDateField.vue'
import AppColorInput from '../../controls/AppColorInput.vue'
import AppButton from '../../controls/AppButton.vue'
import { fieldKind } from '../objects/recordFields.js'
import { t } from '../../i18n.js'

const props = defineProps({ editor: Object, busy: Boolean, error: String, uncertain: Boolean })
const emit = defineEmits(['save', 'cancel', 'check'])
const panel = ref(null), value = ref('')
const initialValue = ref('')
const kind = computed(() => props.editor ? fieldKind(props.editor.field) : '')
const multiline = computed(() => kind.value === 'TextAreaWdg' || props.editor?.field.name === 'description')
const choices = computed(() => {
  const field = props.editor.field, options = (field.choices || []).map((value,index) => ({value,label:field.labels[index]}))
  return field.input?.empty_label != null ? [{value:'',label:field.input.empty_label}, ...options] : options
})
async function open(bounds) {
  const field = props.editor.field
  value.value = ['CalendarInputWdg','TimeInputWdg','ColorInputWdg','MultiSelectWdg'].includes(fieldKind(field)) ? field.input?.value ?? field.values[0] ?? '' : field.values[0] ?? ''
  if (fieldKind(field) === 'CheckboxWdg') value.value = [true,1,'1','true','on'].includes(value.value)
  initialValue.value = JSON.stringify(value.value)
  await nextTick()
  panel.value.style.width = Math.min(innerWidth - 16, multiline.value ? 620 : bounds.width - 8) + 'px'
  panel.value.style.setProperty('--inline-height', (bounds.height - 8) + 'px')
  panel.value.showPopover()
  panel.value.style.left = Math.max(8,Math.min(bounds.left + (multiline.value ? 0 : 4),innerWidth-panel.value.offsetWidth-8)) + 'px'
  panel.value.style.top = Math.max(8,Math.min(multiline.value ? bounds.bottom + 4 : bounds.top + 4,innerHeight-panel.value.offsetHeight-8)) + 'px'
  panel.value.querySelector('input,textarea,select,button')?.focus()
}
function close() { panel.value?.hidePopover() }
function save() { if (!props.busy && !props.uncertain) { if (JSON.stringify(value.value) === initialValue.value) cancel(); else emit('save', value.value) } }
function cancel() { if (!props.busy && !props.uncertain) { close(); emit('cancel') } }
function toggle(event) { if (event.newState === 'closed' && props.editor && !props.busy && !props.uncertain) emit('cancel') }
function outside(event) { if (props.editor && !multiline.value && !panel.value?.contains(event.target) && !props.busy && !props.uncertain) save() }
function moved(event) { if (props.editor && !panel.value?.contains(event.target) && !props.busy && !props.uncertain) cancel() }
onMounted(() => { window.addEventListener('pointerdown',outside,true); window.addEventListener('scroll',moved,true); window.addEventListener('resize',moved) })
onBeforeUnmount(() => { close(); window.removeEventListener('pointerdown',outside,true); window.removeEventListener('scroll',moved,true); window.removeEventListener('resize',moved) })
defineExpose({ open, close })
</script>

<template>
  <Teleport to="body"><div ref="panel" popover="manual" class="table-inline-editor" :class="{ 'in-cell': !multiline }" role="dialog" :aria-label="editor?.field.title" @toggle="toggle" @keydown.esc.stop.prevent="cancel">
    <form v-if="editor" @submit.prevent="save">
      <header v-if="multiline"><strong>{{ t('Edit description') }}</strong></header>
      <AppTextArea v-if="multiline" v-model="value" :label="editor.field.title" :disabled="busy || uncertain" rows="8" />
      <AppSelect v-else-if="kind === 'SelectWdg'" v-model="value" :label="editor.field.title" :translate-labels="false" :options="choices" :disabled="busy || uncertain" @update:model-value="save" />
      <div v-else-if="kind === 'CheckboxWdg'" class="inline-boolean"><AppSwitch v-model="value" :label="editor.field.title" :disabled="busy || uncertain" @update:model-value="save" /><span>{{ t(value ? 'Yes' : 'No') }}</span></div>
      <AppDateField v-else-if="kind === 'CalendarInputWdg'" v-model="value" :label="editor.field.title" :include-time="editor.field.input?.type === 'datetime-local'" :disabled="busy || uncertain" />
      <AppColorInput v-else-if="kind === 'ColorInputWdg'" v-model="value" :label="editor.field.title" :disabled="busy || uncertain" />
      <fieldset v-else-if="kind === 'MultiSelectWdg'" :disabled="busy || uncertain"><legend>{{ editor.field.title }}</legend><AppCheckbox v-for="option in choices" :key="option.value" :label="option.label" :translate-label="false" :model-value="value.includes(option.value)" @update:model-value="value = $event ? [...value,option.value] : value.filter(item => item !== option.value)" /></fieldset>
      <AppTextField v-else v-model="value" :label="editor.field.title" :type="kind === 'TimeInputWdg' ? 'time' : 'text'" :disabled="busy || uncertain" />
      <p v-if="editor.plans.length > 1 && multiline" class="muted">{{ t('Apply to {count} rows', {count:editor.plans.length}) }}</p>
      <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
      <p v-if="uncertain" class="notice">{{ t('Check the server result before saving again.') }}</p>
      <footer v-if="multiline || error || uncertain || ['CalendarInputWdg','ColorInputWdg','MultiSelectWdg'].includes(kind)"><AppButton v-if="uncertain" label="Check saved changes" icon="refresh" :disabled="busy" @click="emit('check',value)" /><AppButton label="Cancel" :disabled="busy" @click="uncertain ? emit('cancel',true) : cancel()" /><AppButton label="Save" type="submit" :disabled="busy || uncertain" /></footer>
    </form>
  </div></Teleport>
</template>

<style>
.table-inline-editor { position:fixed; inset:auto; margin:0; padding:10px; max-height:min(520px, calc(100dvh - 16px)); overflow:auto; background:var(--surface-high); color:var(--on-surface); border:1px solid var(--outline-variant); border-radius:var(--item-radius); box-shadow:2px 6px 16px var(--shadow-color); }
.table-inline-editor form { display:flex; flex-direction:column; gap:8px; }.table-inline-editor header,.table-inline-editor footer { display:flex; align-items:center; justify-content:flex-end; gap:8px; }.table-inline-editor header strong { margin-right:auto; }
.table-inline-editor :is(input,textarea,select) { width:100%; }.table-inline-editor textarea { height:260px; min-height:260px; }
.table-inline-editor.in-cell { border:0; border-radius:0; box-shadow:none; background:transparent; padding:0; overflow:visible; }
.table-inline-editor.in-cell form > :is(input,select,.app-date-field,.app-color-input,.inline-boolean) { min-height:var(--inline-height); height:var(--inline-height); }
.table-inline-editor.in-cell :is(footer,.error,.notice) { background:var(--surface-high); padding:8px; border-radius:var(--item-radius); }
.table-inline-editor.in-cell footer { flex-wrap:wrap; }
.inline-boolean { display:flex; gap:7px; align-items:center; padding:0 10px; border-radius:var(--field-radius); border:1px solid var(--outline-variant); background:var(--surface-high); }
</style>
