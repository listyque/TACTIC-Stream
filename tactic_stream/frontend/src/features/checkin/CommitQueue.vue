<script>
// Handler CommitQueueView.qml / commit_queue.py: one application-owned preparation queue.
import { nextTick, markRaw } from 'vue'
import { rpc, uploadFormFile } from '../../api.js'
import { t } from '../../i18n.js'
import AppButton from '../../controls/AppButton.vue'
import AppMenu from '../../controls/AppMenu.vue'
import AppIcon from '../../controls/AppIcon.vue'
import AppCheckbox from '../../controls/AppCheckbox.vue'
import AppSwitch from '../../controls/AppSwitch.vue'
import AppSelect from '../../controls/AppSelect.vue'
import AppTextField from '../../controls/AppTextField.vue'
import AppTextArea from '../../controls/AppTextArea.vue'
import AppSplitter from '../../controls/AppSplitter.vue'
import ItemPreview from '../../controls/ItemPreview.vue'
import SummaryChip from '../../controls/SummaryChip.vue'
import { asyncComponent } from '../../controls/asyncComponent.js'
import { mobile } from '../../mobile.js'
import { notify } from '../activity/notifications.js'
import { preferences, savePreferencePage } from '../configuration/preferences.js'
import { repositories, sourcePath, descriptors, prettySize } from './files.js'

const editable = job => !!job && !['Uploading','Checking in','Complete','Skipped','Result unknown'].includes(job.status)
const NamingEditor = asyncComponent(() => import('../administration/NamingEditor.vue'))
export default {
  components: { AppButton, AppMenu, AppIcon, AppCheckbox, AppSwitch, AppSelect, AppTextField, AppTextArea, AppSplitter, ItemPreview, SummaryChip, NamingEditor },
  props: { inline:Boolean, login:String, ticket:String, project:String, canAdminister:Boolean, presentationVisible:{type:Boolean,default:true} },
  emits: ['changed','completed','opened','closed','help','snapshot'],
  data() { return { jobs:[], selectedId:'', running:false, modal:false, sequence:0, applyChecked:false, advanced:false, mobileDetails:false,
    namingExpanded:false, width:360, filesHeight:142, duplicate:null, duplicates:[], repositoryOptions:[], cancelRequested:false,
    aborter:null, validation:0, namingScope:null, contextEditing:false, contextBranch:'', error:'', preferences } },
  computed: {
    mobile() { return mobile.value }, docked() { return this.inline && !this.modal },
    selected() { return this.jobs.find(job => job.id === this.selectedId) }, pending() { return this.jobs.some(job => job.file) },
    canEdit() { return !this.running && editable(this.selected) && !!this.selected?.file },
    sourceFiles() { const active = [...(this.selected?.files || []),...(this.selected?.previews || [])]; return active.length ? active : [...(this.selected?.sourceFiles || []),...(this.selected?.previewFiles || [])].map(file => ({ ...file,name:file.path.split('/').pop(),webkitRelativePath:file.path })) },
  },
  mounted() { this.restore(); window.addEventListener('beforeunload', this.beforeUnload) },
  beforeUnmount() { this.aborter?.abort(); window.removeEventListener('beforeunload', this.beforeUnload) },
  watch: { login() { this.jobs = []; this.duplicate = null; this.duplicates = []; this.restore() } },
  methods: {
    t, editable, sourcePath, prettySize,
    beforeUnload(event) { if (this.pending) { event.preventDefault(); event.returnValue = '' } },
    canLeave() { return !this.running && (!this.pending || window.confirm(t('Discard pending file check-ins?'))) },
    async open() { if(!this.presentationVisible)return;this.modal = this.inline && !this.mobile && !!document.querySelector('dialog:modal'); await nextTick(); if (!this.docked) this.$refs.dialog.show(); this.$emit('opened') },
    changed() {
      this.$emit('changed',this.jobs)
      try { localStorage.setItem('tactic_stream.commit_queue.' + this.login,JSON.stringify(this.jobs.map(({ ticket,files,file,previews,validating,plan,...job }) => ({ ...job,sourceFiles:files?.length ? descriptors(files) : job.sourceFiles || [],previewFiles:previews?.length ? descriptors(previews) : job.previewFiles || [] })))) }
      catch { this.error = 'Queue recovery could not be saved. Keep this page open until pending work is complete.' }
    },
    restore() {
      if (this.pending || this.running) return
      let saved = []; try { saved = JSON.parse(localStorage.getItem('tactic_stream.commit_queue.' + this.login) || '[]') } catch { /* Empty queue. */ }
      this.jobs = Array.isArray(saved) ? saved.filter(job => job && typeof job.searchKey === 'string' && typeof job.project === 'string').map(job => ({ ...job,id:++this.sequence,ticket:this.ticket,files:[],previews:[],file:null,plan:null,validating:false,
        status:job.status === 'Checking in' ? 'Result unknown' : ['Complete','Skipped','Result unknown'].includes(job.status) ? job.status : 'Missing files',
        error:['Uploading','Checking in'].includes(job.status) ? 'The page closed during check-in. Inspect Snapshot Browser before repeating it.' : job.error || '' })) : []
      this.selectedId = this.jobs[0]?.id || ''; this.$emit('changed',this.jobs)
    },
    enqueue(values,force = false) {
      const files = values.files || [values.file]
      if (!values.context && this.jobs.some(job => job.searchKey === values.searchKey && job.file && !['Complete','Cancelled'].includes(job.status))) throw new Error(t('A preview check-in for this Search Type is already pending.'))
      const identity = job => JSON.stringify([job.project,job.searchKey,job.context || 'icon',!!job.isRevision,Number(job.version || 0),
        (job.files?.length ? job.files.map(sourcePath) : (job.sourceFiles || []).map(file => file.path)).map(path => path.toLowerCase()).sort()])
      const old = this.jobs.find(job => identity(job) === identity({ ...values,files }))
      if (old && !force) { const duplicate = { values,oldId:old.id }; if (this.duplicate) this.duplicates.push(duplicate); else this.duplicate = duplicate; this.selectedId = old.id; return }
      const job = { description:'',checked:true,context:'publish',process:'publish',repositoryAlias:preferences.repository.defaultAlias,
        keepFileName:preferences.checkin.keepFilename,generatePreviews:preferences.checkin.generatePreviews,updateVersionless:true,onlyVersionless:false,
        explicitFilename:'',contextAsFilename:false,previews:[],...values,id:++this.sequence,file:files[0],files:[...files],preview:!values.context,
        status:'Queued',progress:0,error:'',snapshot:null,plan:null,planError:'',validating:false,request:0,sourceFiles:descriptors(files) }
      if (job.preview) { job.context = 'icon'; job.process = 'icon'; job.updateVersionless = false }
      this.jobs.push(job); this.select(job,false); this.changed(); this.validateAll()
    },
    resolveDuplicate(decision) {
      const pending = this.duplicate
      const old = this.jobs.find(job => job.id === pending.oldId)
      if (decision === 'replace' && old && !['Uploading','Checking in','Result unknown'].includes(old.status)) {
        const index = this.jobs.indexOf(old); old.request++
        this.enqueue(pending.values,true)
        const replacement = this.jobs.pop(); replacement.id = old.id; replacement.checked = old.checked
        this.jobs.splice(index,1,replacement); this.selectedId = old.id; this.changed(); this.validateAll()
      } else if (decision === 'add' || decision === 'replace' && !old) this.enqueue(pending.values,true)
      this.duplicate = this.duplicates.shift() || null
    },
    async select(job,details = true) {
      if (this.mobile) this.mobileDetails = details
      this.selectedId = job.id; this.error = ''; this.contextEditing = false
      try { const result = await repositories({ ticket:job.ticket,project:job.project }); if (this.selectedId === job.id) this.repositoryOptions = result }
      catch (error) { if (this.selectedId === job.id) this.error = error.message }
    },
    async validateAll() {
      const validation = ++this.validation
      for (const job of [...this.jobs]) {
        if (validation !== this.validation) return
        if (editable(job) && job.file) await this.validate(job)
      }
    },
    options(job,action) {
      return { action,search_key:job.searchKey,process:job.process,context:job.context,description:job.description,
        source_files:[...job.files,...job.previews].map((file,index) => ({ path:index < job.files.length ? sourcePath(file) : 'preview/' + sourcePath(file),size:file.size,file_type:index < job.files.length ? 'main' : 'preview' })),
        templates:job.templates,padding:job.padding,repository_alias:job.repositoryAlias,keep_file_name:!!job.keepFileName,
        is_revision:!!job.isRevision,version:job.version === '' || job.version == null ? null : Number(job.version),explicit_filename:job.explicitFilename || null,
        update_versionless:!!job.updateVersionless,only_versionless:!!job.onlyVersionless,create_icon:job.generatePreviews !== false }
    },
    async validate(job) {
      if (job.ingest || job.preview) { job.planError = ''; return }
      const request = ++job.request; job.validating = true; job.planError = ''
      try {
        const reserved = this.jobs.slice(0,this.jobs.indexOf(job)).filter(other => editable(other) && other.plan && other.searchKey === job.searchKey && other.project === job.project && other.context === job.context && !other.onlyVersionless).map(other => other.plan.version)
        const result = (await rpc('execute_cmd',[{ ticket:job.ticket,project:job.project },'tactic.command.browser_checkin_cmd.BrowserCheckinCmd',{ ...this.options(job,'plan'),reserved_versions:reserved }],{},true)).info.plan
        if (request === job.request) job.plan = result
      } catch (error) { if (request === job.request) { job.plan = null; job.planError = error.message } }
      finally { if (request === job.request) { job.validating = false; this.changed() } }
    },
    update(field,value) {
      if (!this.canEdit) return
      for (const job of this.jobs.filter(job => editable(job) && !job.ingest && (!job.preview || field === 'description') && (job.id === this.selectedId || this.applyChecked && job.checked))) {
        job[field] = value
        if (field === 'process') job.context = value
        if (field === 'keepFileName' && value) job.updateVersionless = false
        if (field === 'onlyVersionless' && value) job.updateVersionless = true
        if (job.contextAsFilename && ['context','contextAsFilename'].includes(field)) job.explicitFilename = job.context.split('/').slice(1).join('_')
      }
      this.changed(); if (field !== 'description') this.validateAll()
    },
    remove(job) { if (['Uploading','Checking in'].includes(job.status)) return; job.request++; this.jobs = this.jobs.filter(item => item !== job); if (!this.selected) this.selectedId = this.jobs[0]?.id || ''; this.changed(); this.validateAll() },
    clear(completed = false) { if (this.running || !completed && !window.confirm(t('All prepared, failed and completed operations will be removed from the queue.'))) return; for (const job of [...this.jobs]) if (!completed || job.status === 'Complete') this.remove(job) },
    move(offset) { const index = this.jobs.indexOf(this.selected),target = index + offset; if (this.running || index < 0 || target < 0 || target >= this.jobs.length) return; const [job] = this.jobs.splice(index,1); this.jobs.splice(target,0,job); this.changed(); this.validateAll() },
    autoClean(value) { try { savePreferencePage('checkin',{ ...preferences.checkin,commitQueueAutoClean:value }) } catch (error) { this.error = error.message } },
    beginContext() { if (!this.canEdit || this.selected.isRevision || this.selected.ingest || this.selected.preview) return; this.contextBranch = this.selected.context.split('/').slice(1).join('/'); this.contextEditing = true; nextTick(() => this.$refs.contextField.focus()) },
    finishContext() {
      if (!this.contextEditing) return
      this.contextEditing = false
      const process = this.selected.process.replace(/^\/+|\/+$/g,'')
      let branch = this.contextBranch.trim().replaceAll(' ','_').replace(/^\/+|\/+$/g,'')
      if (branch.startsWith(process + '/')) branch = branch.slice(process.length + 1)
      this.update('context',process + (branch ? '/' + branch : ''))
    },
    removeFile(file) { if (!this.canEdit) return; const job = this.selected; job.files = job.files.filter(item => item !== file); job.previews = job.previews.filter(item => item !== file); job.sourceFiles = descriptors(job.files); job.previewFiles = descriptors(job.previews); job.file = job.files[0]; this.changed(); if (job.file) this.validateAll(); else { job.plan = null; job.planError = 'Choose source files before check-in' } },
    reselect(files) {
      const job = this.selected,expected = [...(job.sourceFiles || []),...(job.previewFiles || [])],incoming = [...files]
      if (incoming.every(file => !file.webkitRelativePath) && new Set(expected.map(source => source.path.split('/').pop())).size === expected.length) {
        for (const file of incoming) { const source = expected.find(source => source.path.split('/').pop() === file.name); if (source) Object.defineProperty(file,'webkitRelativePath',{ value:source.path }) }
      }
      if (expected.length !== incoming.length || expected.some(source => !incoming.some(file => sourcePath(file) === source.path && file.size === source.size))) { this.error = 'Choose the same source files shown in this operation.'; return }
      const resolve = source => incoming.find(file => sourcePath(file) === source.path)
      job.files = job.sourceFiles.map(resolve); job.previews = (job.previewFiles || []).map(resolve); job.file = job.files[0]; job.status = 'Queued'; job.error = ''; this.changed(); this.validateAll()
    },
    addPreviews(files) { if (!this.canEdit) return; const incoming = [...files]; if (incoming.some(file => !file.type.startsWith('image/'))) { this.error = 'Choose an image for the preview'; return }; this.selected.previews.push(...incoming); this.changed(); this.validateAll() },
    clearPreviews() { if (!this.canEdit) return; this.selected.previews = []; this.selected.previewFiles = []; this.changed(); this.validateAll() },
    snapshot() { if (!this.docked) this.$refs.dialog.close(); this.$emit('snapshot',this.selected) },
    paste(event) { if (this.canEdit && event.clipboardData?.files.length) { event.preventDefault(); this.addPreviews(event.clipboardData.files) } },
    async pasteImage() {
      try { if (!navigator.clipboard?.read) throw new Error('Paste an image with Ctrl+V or choose a file on HTTP.'); const files = []; for (const item of await navigator.clipboard.read()) { const type = item.types.find(type => type.startsWith('image/')); if (type) files.push(new File([await item.getType(type)],'clipboard-' + (files.length + 1) + '.' + type.split('/')[1],{ type })) }; if (!files.length) throw new Error('No image in clipboard'); this.addPreviews(files) } catch (error) { this.error = error.message }
    },
    async capture() {
      const job = this.selected; let stream
      try {
        if (!navigator.mediaDevices?.getDisplayMedia) throw new Error('Screen capture requires HTTPS or localhost. Choose or paste an image instead.')
        stream = await navigator.mediaDevices.getDisplayMedia({ video:true }); const video = document.createElement('video'); video.srcObject = stream; await video.play()
        const canvas = document.createElement('canvas'); canvas.width = video.videoWidth; canvas.height = video.videoHeight; canvas.getContext('2d').drawImage(video,0,0)
        const blob = await new Promise(resolve => canvas.toBlob(resolve,'image/png')); if (this.selected === job && editable(job) && blob) this.addPreviews([new File([blob],'screenshot.png',{ type:'image/png' })])
      } catch (error) { this.error = error.message } finally { stream?.getTracks().forEach(track => track.stop()) }
    },
    cancel(job = this.selected) { if (!job) return; if (['Uploading','Checking in'].includes(job.status)) { this.cancelRequested = true; if (job.status === 'Uploading') this.aborter?.abort() } else if (editable(job)) { job.status = 'Cancelled'; job.request++; this.changed() } },
    retry(job = this.selected) { if (!this.running && ['Failed','Cancelled'].includes(job?.status) && job.file) { job.status = 'Queued'; this.run([job]) } },
    async run(requested = this.jobs.filter(job => job.checked)) {
      if (this.running) return
      this.running = true; this.cancelRequested = false
      try {
        for (const job of [...requested]) {
          if (this.cancelRequested) break
          if (!editable(job) || !job.file || job.status === 'Cancelled') continue
          await this.validate(job); if (job.planError || this.cancelRequested || job.status === 'Cancelled' || !this.jobs.includes(job)) continue
          job.error = ''; job.status = 'Uploading'; job.progress = 0
          try {
            const names = [],files = [...job.files,...job.previews]; this.aborter = markRaw(new AbortController())
            for (const [index,file] of files.entries()) {
              const suffix = file.name.includes('.') ? file.name.slice(file.name.lastIndexOf('.')) : ''
              names.push(await uploadFormFile(job.ticket,job.project,file,{ signal:this.aborter.signal,filename:job.ingest || job.preview ? file.name : 'queue-' + job.id + '-' + index + '-' + Date.now() + suffix })); job.progress = (index + 1) / files.length * .85
            }
            if (this.cancelRequested) { job.status = 'Cancelled'; continue }
            job.status = 'Checking in'; this.changed(); const auth = { ticket:job.ticket,project:job.project,language:'python' }
            if (job.ingest) {
              const result = (await rpc('execute_cmd',[auth,'tactic.command.related_ingest_cmd.RelatedIngestCmd',{ ...job.ingest,action:'checkin',filenames:names }])).info
              if (result.skipped) { job.status = 'Skipped'; job.error = result.reason; job.file = null; job.files = []; this.changed(); continue }
              job.snapshot = result.snapshot; job.searchKey = result.search_key
            } else if (job.preview) job.snapshot = await rpc('simple_checkin',[auth,job.searchKey,'icon',names[0]],{ mode:'uploaded',description:job.description || 'Search Type preview',process:'icon',create_icon:job.generatePreviews !== false })
            else job.snapshot = (await rpc('execute_cmd',[auth,'tactic.command.browser_checkin_cmd.BrowserCheckinCmd',{ ...this.options(job,'checkin'),files:names }])).info.snapshot
            const completedFiles = job.files
            job.status = 'Complete'; job.progress = 1; job.file = null; job.files = []; job.previews = []
            notify('complete','Check-in completed',job.name,'checkin'); this.changed(); this.$emit('completed',{ ...job,completedFiles }); if (preferences.checkin.commitQueueAutoClean) this.remove(job)
          } catch (error) { job.status = job.status === 'Uploading' && error.name === 'AbortError' ? 'Cancelled' : job.status === 'Checking in' && (!error.status || error.status >= 500) ? 'Result unknown' : 'Failed'; job.error = error.message; this.changed(); if (job.status !== 'Cancelled') notify('error',job.error,job.name,'checkin') }
          finally { this.aborter = null }
        }
      } finally { this.running = false; this.validateAll() }
    },
    async naming() { this.namingScope = { ticket:this.selected.ticket,project:this.selected.project,type:this.selected.searchKey.split('?')[0] }; await nextTick(); this.$refs.namingDialog.show() },
    closeNaming() { if (!this.$refs.namingEditor?.canLeave || this.$refs.namingEditor.canLeave()) this.$refs.namingDialog.close() },
  },
}
</script>
<template>
  <Teleport defer :to="docked ? '#dock-commit_queue' : 'body'">
  <component v-show="presentationVisible" v-window="docked ? false : { type:'window' }" :is="docked ? 'section' : 'dialog'" ref="dialog" class="commit-queue" :class="{ 'commit-queue-docked':docked, 'record-dialog':!docked, 'queue-mobile-expanded':mobile && mobileDetails }" :aria-label="t('Commit Queue')" @paste="paste" @close="modal = false; $emit('closed')">
    <header v-if="!docked"><h2>{{ t('Commit Queue') }}</h2><AppButton label="Close" icon="close" @click="$refs.dialog.close()" /></header>
    <div class="commit-queue-workspace" :style="{ '--queue-width':width + 'px','--files-height':filesHeight + 'px' }">
      <aside class="queue-files-dock">
        <div class="queue-toolbar"><AppIcon name="MDI_FORMAT_LIST_BULLETED" /><strong>{{ t('QUEUE') }}</strong><span class="result-count">{{ jobs.length }}</span><span class="spacer" /><AppButton icon-only label="Help" icon="help" @click="$emit('help','commit_queue')" />
          <AppButton v-if="mobile" icon-only label="Check-in details" :icon="mobileDetails ? 'MDI_CHEVRON_UP' : 'MDI_CHEVRON_DOWN'" :aria-expanded="mobileDetails" :disabled="!selected" @click="mobileDetails = !mobileDetails" />
          <template v-if="!mobile">
          <AppSwitch label="Auto-clean" :disabled="running" :model-value="preferences.checkin.commitQueueAutoClean" @update:model-value="autoClean" /><span>{{ t('Auto-clean') }}</span>
          <AppButton v-if="jobs.length > 1" icon-only label="Move operation up" icon="MDI_ARROW_UP" :disabled="running || jobs.indexOf(selected) <= 0" @click="move(-1)" /><AppButton v-if="jobs.length > 1" icon-only label="Move operation down" icon="MDI_ARROW_DOWN" :disabled="running || jobs.indexOf(selected) === jobs.length - 1" @click="move(1)" />
          <AppButton v-if="jobs.some(job => job.status === 'Complete')" icon-only label="Clear completed" icon="check" :disabled="running" @click="clear(true)" /><AppButton icon-only label="Clear queue" icon="delete" :disabled="running || !jobs.length" @click="clear()" />
          </template>
        </div>
        <div class="queue-rows"><p v-if="!jobs.length" class="muted queue-empty">{{ t('No file check-ins yet.') }}</p>
          <section v-for="job in jobs" :key="job.id" class="queue-row" :class="{ selected:job.id === selectedId }" @click="select(job)" @contextmenu.prevent="$refs['jobMenu' + job.id]?.[0]?.openAt($event)">
            <AppCheckbox compact hide-label label="Select operation for commit" :model-value="job.checked" :disabled="!editable(job)" @click.stop @update:model-value="job.checked = $event; changed()" />
            <ItemPreview :file="job.previews[0] || (job.files[0]?.type.startsWith('image/') ? job.files[0] : undefined)" fallback-icon="MDI_ARCHIVE" :preview-size="38" />
            <AppButton class="queue-row-select" :label="job.name" @click="select(job)"><strong>{{ job.name }}</strong><span>{{ job.title }}</span><small>{{ job.context }} · {{ job.files.length || job.sourceFiles?.length || 0 }} {{ t('Files') }}</small></AppButton>
            <div class="queue-row-status"><span role="status">{{ t(mobile && job.status === 'Queued' ? job.validating ? 'Validating' : job.planError ? 'Invalid' : 'Ready to send' : job.status) }}</span><progress v-if="['Uploading','Checking in'].includes(job.status)" :value="job.progress" max="1" :aria-label="t('Progress')" /></div><AppButton v-if="!mobile" icon-only label="Remove operation" icon="close" :disabled="['Uploading','Checking in'].includes(job.status)" @click.stop="remove(job)" />
            <p v-if="mobile && (job.planError || job.error)" class="error queue-row-error" role="alert">{{ t(job.planError || job.error) }}</p>
            <AppMenu v-if="editable(job) || mobile" :overlay="mobile" :ref="'jobMenu' + job.id" label="Check-in actions" @click.stop><AppButton v-if="mobile" label="Check-in details" icon="edit" @click="select(job)" /><AppButton label="Commit current" icon="upload" :disabled="running || !editable(job) || !job.file || job.status === 'Cancelled'" @click="run([job])" /><AppButton v-if="['Failed','Cancelled'].includes(job.status)" label="Retry" icon="refresh" :disabled="running || !job.file" @click="retry(job)" /><AppButton label="Cancel" icon="close" :disabled="running || !editable(job)" @click="cancel(job)" /><AppButton label="Remove operation" icon="delete" :disabled="running" @click="remove(job)" /></AppMenu>
          </section>
        </div>
        <AppSplitter v-model="filesHeight" horizontal reverse :min="100" :max="430" label="Files pane height" />
        <div class="queue-source-files"><div class="queue-toolbar"><strong>{{ t('FILES') }}</strong><span class="result-count">{{ sourceFiles.length }}</span></div><p v-if="!selected" class="muted queue-empty">{{ t('Select an operation to inspect its files.') }}</p>
          <div v-for="(file,index) in sourceFiles" :key="index" class="queue-source-file"><AppIcon name="file" /><div><strong>{{ file.name }}</strong><small>{{ sourcePath(file) }}</small></div><small>{{ prettySize(file.size) }}</small><AppButton icon-only label="Remove file from operation" icon="close" :disabled="!canEdit" @click="removeFile(file)" /></div>
          <template v-if="selected?.status === 'Missing files'"><p v-for="file in [...selected.sourceFiles,...(selected.previewFiles || [])]" :key="file.path" class="queue-missing-file">{{ file.path }}</p><div class="queue-reselect"><AppButton label="Choose source files again" icon="upload" @click="$refs.reselectInput.click()" /><AppButton label="Directory" icon="folder" @click="$refs.reselectDirectory.click()" /></div><input ref="reselectInput" hidden type="file" multiple @change="reselect($event.target.files); $event.target.value = ''"><input ref="reselectDirectory" hidden type="file" multiple webkitdirectory @change="reselect($event.target.files); $event.target.value = ''"></template>
        </div>
      </aside>
      <AppSplitter v-model="width" :min="270" :max="600" label="Queue pane width" />
      <div class="queue-details">
        <div v-if="duplicate" class="notice queue-duplicate"><p>{{ t('The same files are already prepared for this object and context.') }}</p><AppButton label="Replace" :disabled="['Uploading','Checking in','Result unknown'].includes(jobs.find(job => job.id === duplicate.oldId)?.status)" @click="resolveDuplicate('replace')" /><AppButton label="Add another" @click="resolveDuplicate('add')" /><AppButton label="Ignore duplicate" @click="resolveDuplicate('ignore')" /></div><p v-if="error" class="error" role="alert">{{ t(error) }}</p>
        <template v-if="selected">
          <div class="queue-summary"><ItemPreview :file="selected.previews[0] || (selected.files[0]?.type.startsWith('image/') ? selected.files[0] : undefined)" :preview-size="72" :fallback-text="selected.files[0]?.name.split('.').pop().toUpperCase() || 'FILE'" /><div><strong>{{ selected.title }}</strong><span>{{ selected.plan?.files[0]?.versioned[0]?.split('/').pop() || selected.name }}</span><div class="queue-context"><small>{{ selected.process }} ·</small><AppTextField v-if="contextEditing" ref="contextField" v-model="contextBranch" label="Context branch" @keydown.enter.prevent="finishContext" @blur="finishContext" @keydown.esc.prevent="contextEditing = false" /><SummaryChip v-else compact clickable icon="edit" :show-dot="false" :show-count="false" :label="selected.context.includes('/') ? t('Context') + ': ' + selected.context.split('/').slice(1).join('/') : t('Add context')" @click="beginContext" /><small>· {{ sourceFiles.length || selected.sourceFiles.length }} {{ t('Files') }}</small></div></div>
            <SummaryChip class="queue-status" compact icon="queue" :show-dot="false" :show-count="false" :accent="selected.status === 'Queued' ? 'var(--success)' : selected.status === 'Failed' ? 'var(--error)' : 'var(--muted)'" :label="t(selected.status === 'Queued' ? selected.validating ? 'Validating' : selected.planError ? 'Invalid' : 'Ready to send' : selected.status)" />
            <div class="queue-preview-buttons"><AppButton icon-only label="Capture screenshot" icon="camera" :disabled="!canEdit || selected.ingest || selected.preview" @click="capture" /><AppButton icon-only label="Choose preview images" icon="image" :disabled="!canEdit || selected.ingest || selected.preview" @click="$refs.previewsInput.click()" /><AppButton icon-only label="Paste preview image from clipboard" icon="clipboard" :disabled="!canEdit || selected.ingest || selected.preview" @click="pasteImage" /></div>
            <AppMenu label="Preview actions"><AppButton label="Choose preview images" icon="image" :disabled="!canEdit || selected.ingest || selected.preview" @click="$refs.previewsInput.click()" /><AppButton label="Paste preview image from clipboard" icon="clipboard" :disabled="!canEdit || selected.ingest || selected.preview" @click="pasteImage" /><AppButton label="Capture screenshot" icon="camera" :disabled="!canEdit || selected.ingest || selected.preview" @click="capture" /><AppButton label="Manage selected previews" icon="image" :disabled="!selected.previews.length" @click="$refs.previewsDialog.showModal()" /><AppButton label="Clear operation previews" icon="delete" :disabled="!canEdit || !selected.previews.length" @click="clearPreviews" /></AppMenu>
          </div>
          <div class="queue-detail-scroll">
            <AppCheckbox v-if="jobs.length > 1" label="Apply every edit to checked items" v-model="applyChecked" :disabled="!canEdit" :title="t('The current item and all checked operations will receive each edit.')" />
            <strong class="queue-section-label">{{ t('BASIC') }}</strong><AppTextArea :model-value="selected.description" label="Description" :rows="2" :disabled="!canEdit || selected.ingest" @update:model-value="update('description',$event)" />
            <AppButton class="queue-advanced" label="Advanced options" :icon="advanced ? 'MDI_CHEVRON_DOWN' : 'next'" :aria-expanded="advanced" @click="advanced = !advanced" />
            <div v-if="advanced" class="queue-fields">
              <label>{{ t('Repository') }}<AppSelect :model-value="selected.repositoryAlias" :options="repositoryOptions" :translate-labels="false" label="Repository" :disabled="!canEdit || selected.isRevision || selected.ingest || selected.preview" @update:model-value="update('repositoryAlias',$event)" /></label><label>{{ t('Version') }}<AppTextField :model-value="String(selected.version ?? '')" type="number" min="0" label="Version" placeholder="Automatic version" :disabled="!canEdit || selected.onlyVersionless || selected.ingest || selected.preview" @update:model-value="update('version',$event)" /></label>
              <label>{{ t('Method') }}<AppSelect :model-value="'upload'" label="Method" :options="[{ value:'upload',label:'Upload' },...['Preallocate','In-Place','Copy','Move'].map(label => ({ value:label,label,disabled:true }))]" :disabled="!canEdit" /></label><label><span>{{ t('Filename') }}</span><AppTextField :model-value="selected.explicitFilename" label="Filename" placeholder="Use naming rules" :disabled="!canEdit || selected.contextAsFilename || selected.ingest || selected.preview" @update:model-value="update('explicitFilename',$event)" /></label><p class="muted queue-field-note">{{ t('Local transfer methods require a desktop connection. Browser check-in uses Upload.') }}</p>
            </div>
            <strong v-if="advanced" class="queue-section-label">{{ t('FILE OPTIONS') }}</strong><div v-if="advanced" class="queue-options"><AppCheckbox v-for="option in [['updateVersionless','Update versionless'],['onlyVersionless','Commit versionless only'],['keepFileName','Keep source filename'],['contextAsFilename','Use context as filename'],['generatePreviews','Generate previews']]" :key="option[0]" :label="option[1]" :model-value="!!selected[option[0]]" :disabled="!canEdit || selected.ingest || selected.preview || option[0] === 'onlyVersionless' && selected.isRevision" @update:model-value="update(option[0],$event)" /></div>
            <AppButton class="queue-naming-toggle" label="Naming preview" :icon="namingExpanded ? 'MDI_CHEVRON_DOWN' : 'next'" :aria-expanded="namingExpanded" @click="namingExpanded = !namingExpanded" />
            <div v-if="namingExpanded" class="queue-naming"><AppButton label="Naming Editor" icon="edit" :disabled="!canAdminister || running || selected.ingest || selected.preview" @click="naming" /><p v-if="selected.validating">{{ t('Waiting for naming preview…') }}</p><div v-for="file in selected.plan?.files" :key="file.title"><strong>{{ file.title }}</strong><small v-for="path in file.versioned" :key="path">{{ t('Versioned') }} {{ path }}</small><small v-for="path in file.versionless" :key="path">{{ t('Versionless') }} {{ path }}</small></div></div>
            <p v-if="selected.planError" class="error" role="alert">{{ t(selected.planError) }}</p><pre v-if="selected.error" class="error queue-error" role="alert">{{ t(selected.error) }}</pre><p v-if="selected.status === 'Result unknown'" class="notice">{{ t('Check the current snapshot before repeating this check-in; the server may already have saved it.') }}</p>
          </div>
        </template><p v-else class="muted queue-no-selection">{{ t('Select an operation to inspect its files.') }}</p>
        <footer class="queue-send"><span class="muted">{{ running ? t('Working…') : mobile ? t('{count} files',{count:jobs.filter(job => editable(job) && job.file && job.status !== 'Cancelled').reduce((count,job)=>count+job.files.length,0)}) : t('Ready to commit') }}</span><span class="spacer" /><AppButton v-if="selected?.snapshot || selected?.status === 'Result unknown'" label="Snapshot Browser" icon="snapshot" :icon-only="mobile" @click="snapshot" /><AppButton v-if="!mobile || ['Failed','Cancelled'].includes(selected?.status)" label="Retry" icon="refresh" :disabled="running || !selected?.file || !['Failed','Cancelled'].includes(selected?.status)" @click="retry()" /><AppButton v-if="!mobile || running" label="Cancel" icon="close" :disabled="!selected || !running && !canEdit" @click="cancel()" /><AppButton label="Commit all" icon="upload" highlighted :disabled="running || !jobs.some(job => editable(job) && job.file && job.status !== 'Cancelled')" @click="run(jobs)" /><AppMenu label="More send actions" :overlay="mobile"><AppButton label="Commit current" icon="upload" :disabled="running || !canEdit || !selected?.file" @click="run([selected])" /><AppButton label="Commit selected" icon="upload" :disabled="running || !jobs.some(job => editable(job) && job.file && job.checked)" @click="run()" />
          <template v-if="mobile"><hr><div class="queue-auto-clean"><span>{{ t('Auto-clean') }}</span><AppSwitch label="Auto-clean" :disabled="running" :model-value="preferences.checkin.commitQueueAutoClean" @update:model-value="autoClean" /></div><AppButton v-if="jobs.length > 1" label="Move operation up" icon="MDI_ARROW_UP" :disabled="running || jobs.indexOf(selected) <= 0" @click="move(-1)" /><AppButton v-if="jobs.length > 1" label="Move operation down" icon="MDI_ARROW_DOWN" :disabled="running || jobs.indexOf(selected) === jobs.length - 1" @click="move(1)" /><AppButton label="Clear completed" icon="check" :disabled="running || !jobs.some(job => job.status === 'Complete')" @click="clear(true)" /><AppButton label="Clear queue" icon="delete" :disabled="running || !jobs.length" @click="clear()" /></template>
        </AppMenu></footer>
      </div>
    </div>
    <input ref="previewsInput" class="queue-hidden-input" type="file" accept="image/*" multiple @change="addPreviews($event.target.files); $event.target.value = ''">
  </component>
  </Teleport>
  <Teleport to="body"><dialog v-window="{kind:'naming_editor', type:'window' }" ref="namingDialog" class="record-dialog queue-naming-editor" :aria-label="t('Naming Editor')" @cancel.prevent="closeNaming"><header><h2>{{ t('Naming Editor') }}</h2><AppButton label="Close" icon="close" @click="closeNaming" /></header><NamingEditor v-if="namingScope" ref="namingEditor" :ticket="namingScope.ticket" :project="namingScope.project" :search-type="namingScope.type" @saved="validateAll" /></dialog></Teleport>
  <Teleport to="body"><dialog ref="previewsDialog" class="record-dialog queue-preview-dialog" :aria-label="t('Operation previews')"><header><h2>{{ t('Operation previews') }}</h2><AppButton label="Close" icon="close" @click="$refs.previewsDialog.close()" /></header><div class="queue-preview-list"><div v-for="file in selected?.previews || []" :key="sourcePath(file)"><ItemPreview :file="file" :preview-size="46" /><strong>{{ file.name }}</strong><AppButton icon-only label="Remove preview" icon="close" :disabled="!canEdit" @click="removeFile(file)" /></div></div><footer><AppButton label="Choose preview images" icon="image" :disabled="!canEdit" @click="$refs.previewsInput.click()" /><AppButton label="Paste preview image from clipboard" icon="clipboard" :disabled="!canEdit" @click="pasteImage" /></footer></dialog></Teleport>
</template>
<style>
.commit-queue.record-dialog { width:min(1180px, calc(100vw - 24px)); height:min(820px, calc(100dvh - 24px)); padding:10px; overflow:hidden; }.commit-queue.record-dialog[open], .commit-queue-docked { display:flex; flex-direction:column; }.commit-queue-docked { width:100%; height:100%; min-height:0; padding:10px; box-sizing:border-box; }.commit-queue > header { flex-shrink:0; margin-bottom:8px; }.commit-queue-workspace { flex:1; display:flex; min-width:0; min-height:0; gap:0; }
.queue-files-dock { flex:0 0 min(var(--queue-width), 45%); min-width:270px; border:1px solid var(--outline-variant); border-radius:var(--surface-radius); background:var(--surface-deep); overflow:hidden; display:flex; flex-direction:column; }.queue-toolbar { flex-shrink:0; height:46px; padding:0 7px; display:flex; align-items:center; gap:5px; min-width:0; border-bottom:1px solid var(--outline-variant); font-size:var(--text-label); }.queue-toolbar > .app-icon { font-size:16px; }.queue-toolbar .app-button.icon-button, .queue-row .app-button.icon-button, .queue-source-file .app-button.icon-button { width:30px; min-width:30px; height:30px; min-height:30px; }.queue-toolbar .app-icon, .queue-row .app-icon, .queue-source-file .app-icon { font-size:16px; }.queue-toolbar .spacer, .queue-send .spacer { flex:1; }.queue-toolbar:has(.app-checkbox) { flex-wrap:wrap; height:auto; min-height:46px; }.queue-toolbar strong { font-size:var(--text-label); letter-spacing:1px; }
.queue-rows { flex:1; overflow:auto; min-height:110px; padding:5px; }.queue-row { display:flex; align-items:center; gap:7px; height:68px; padding:5px 6px; box-sizing:border-box; border-radius:var(--item-radius); margin-bottom:3px; background:var(--surface-container); }.queue-row:hover { background:var(--hover); }.queue-row.selected { background:var(--selected); }.queue-row .item-preview { width:38px; height:38px; flex:0 0 38px; border-radius:var(--item-radius); }.queue-row-select.app-button { display:flex; flex-direction:column; align-items:flex-start; gap:3px; flex:1; min-width:0; height:auto; padding:0; border:0; background:transparent; border-radius:0; font-size:var(--text-body); text-align:left; }.queue-row-select > * { max-width:100%; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }.queue-row-select span, .queue-row-select small { color:var(--muted); font-size:var(--text-caption); font-weight:400; }.queue-row-status { flex:0 0 auto; max-width:74px; color:var(--muted); font-size:var(--text-caption); }.queue-row-status progress { display:block; width:60px; height:4px; accent-color:var(--primary); }
.queue-source-files { flex:0 0 var(--files-height); min-height:100px; overflow:auto; }.queue-source-file { display:flex; align-items:center; gap:7px; height:56px; margin:4px 6px; padding:0 6px; border-radius:var(--item-radius); background:var(--surface-container); font-size:var(--text-label); }.queue-source-file > div { flex:1; min-width:0; }.queue-source-file small, .queue-source-file strong { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }.queue-source-file small { color:var(--muted); font-size:var(--text-caption); }.queue-empty { padding:12px; }.queue-reselect, .queue-missing-file { padding:4px 10px; font-size:var(--text-caption); }.queue-hidden-input { display:none; }
.queue-details { display:flex; flex-direction:column; flex:1; min-height:0; min-width:0; overflow:hidden; }.queue-summary { display:flex; align-items:center; gap:12px; padding:12px; min-height:98px; box-sizing:border-box; border-radius:var(--surface-radius); background:var(--surface); }.queue-summary .item-preview { flex:0 0 72px; width:72px; height:72px; border-radius:var(--item-radius); }.queue-summary > div:nth-child(2) { flex:1; min-width:0; }.queue-summary > div:nth-child(2) > strong, .queue-summary > div:nth-child(2) > span, .queue-context > small { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin:4px 0; }.queue-summary strong { font-size:var(--text-body-large); }.queue-summary small { color:var(--muted); }
.queue-detail-scroll { flex:1; overflow:auto; min-height:0; padding:12px; }.queue-detail-scroll label { font-size:var(--text-body); }.queue-detail-scroll > label { display:flex; flex-direction:column; gap:6px; }.queue-detail-scroll > label.app-checkbox { flex-direction:row; }.queue-section-label { display:block; margin:14px 0 8px; font-size:var(--text-label); letter-spacing:1px; color:var(--muted); }.queue-fields { display:grid; grid-template-columns:1fr 1fr; gap:12px; }.queue-fields label { display:flex; flex-direction:column; gap:5px; min-width:0; }.queue-field-note { grid-column:1/-1; }.queue-options { display:grid; grid-template-columns:1fr 1fr; gap:6px 12px; }.queue-advanced.app-button, .queue-naming-toggle.app-button { height:44px; width:100%; justify-content:flex-start; padding:4px; border:0; background:transparent; border-bottom:1px solid var(--outline-variant); border-radius:0; margin-top:10px; }.queue-naming small { display:block; overflow-wrap:anywhere; color:var(--muted); padding:4px 0; }.queue-naming > div { margin:10px 0; }.queue-error { white-space:pre-wrap; overflow-wrap:anywhere; max-height:250px; overflow:auto; font:inherit; }.queue-duplicate { margin:6px 0; padding:10px; }.queue-duplicate .app-button { margin-right:6px; }
.queue-send { margin:0; padding:8px 4px; display:flex; align-items:center; gap:6px; flex-shrink:0; border-top:1px solid var(--outline-variant); flex-wrap:wrap; }.queue-send .app-button { height:36px; min-height:36px; }.queue-send .muted { font-size:var(--text-caption); }.queue-no-selection { margin:auto; text-align:center; }.queue-naming-editor { height:85dvh; width:min(1200px, calc(100vw - 24px)); }
@media(max-width:700px) { .commit-queue-workspace { flex-direction:column; overflow:auto; }.queue-files-dock { min-width:0; flex:0 0 300px; }.commit-queue-workspace > .app-splitter { display:none; }.queue-source-files { flex-basis:120px; }.queue-details { flex:0 0 auto; overflow:visible; }.queue-detail-scroll { overflow:visible; }.queue-fields, .queue-options { grid-template-columns:1fr; }.queue-summary { padding:8px; }.queue-summary .item-preview { width:48px; height:48px; flex-basis:48px; } }
</style>
<style>
@media(max-width:700px) {
  .commit-queue.commit-queue-docked { padding:0; }
  .commit-queue .commit-queue-workspace { flex-direction:column; overflow:auto; }
  .commit-queue .queue-files-dock { flex:none; min-width:0; width:100%; border:0; border-radius:0; overflow:visible; background:transparent; }
  .commit-queue .queue-toolbar { height:36px; padding-inline:8px; }
  .commit-queue .queue-rows { flex:none; overflow:visible; min-height:0; padding:6px; }
  .commit-queue .queue-row { display:grid; grid-template-columns:24px 32px minmax(0,1fr) 28px; gap:4px 8px; height:auto; min-height:76px; margin:0 0 6px; padding:10px; border-radius:var(--item-radius); }
  .commit-queue .queue-row > .app-checkbox { grid-column:1; grid-row:1 / 3; align-self:center; }
  .commit-queue .queue-row > .item-preview { grid-column:2; grid-row:1 / 3; align-self:center; width:32px; height:32px; flex-basis:32px; }
  .commit-queue .queue-row-select { grid-column:3; grid-row:1; min-width:0; padding:0; min-height:0; }
  .commit-queue .queue-row-select strong { white-space:normal; overflow-wrap:anywhere; font-size:var(--text-body-large); }
  .commit-queue .queue-row-select > span,.commit-queue .queue-row-select > small { font-size:var(--text-caption); }
  .commit-queue .queue-row-status { grid-column:3; grid-row:2; min-width:0; align-items:flex-start; text-align:left; }
  .commit-queue .queue-row > .workspace-menu { grid-column:4; grid-row:1 / 3; align-self:center; }
  .commit-queue .queue-row > .workspace-menu > summary { width:28px; height:28px; min-width:28px; min-height:28px; }
  .commit-queue .queue-row-error { grid-column:1 / -1; margin:4px 0 0; max-height:64px; overflow:auto; white-space:pre-wrap; overflow-wrap:anywhere; font-size:var(--text-caption); }
  .commit-queue .queue-files-dock > .app-splitter,.commit-queue .commit-queue-workspace > .app-splitter { display:none; }
  .commit-queue:not(.queue-mobile-expanded) .queue-source-files,.commit-queue:not(.queue-mobile-expanded) .queue-details > :not(.queue-send):not(.queue-duplicate):not(.error) { display:none; }
  .commit-queue .queue-source-files { flex:none; overflow:visible; }
  .commit-queue .queue-details { display:contents; }
  .commit-queue .queue-summary { min-height:0; padding:8px 12px; background:transparent; border-radius:0; }
  .commit-queue .queue-summary > .item-preview,.commit-queue .queue-preview-buttons,.commit-queue .queue-summary > div:nth-child(2) > strong,.commit-queue .queue-summary > div:nth-child(2) > span { display:none; }
  .commit-queue .queue-detail-scroll { flex:none; overflow:visible; padding:8px 12px; }
  .commit-queue .queue-section-label { display:none; }
  .commit-queue .queue-send { position:sticky; bottom:0; margin-top:auto; padding:6px 8px max(6px,env(safe-area-inset-bottom)); background:var(--surface-high); z-index:2; }
  .commit-queue .queue-send .app-button { height:32px; min-height:32px; }
  .commit-queue .queue-send .icon-button,.commit-queue .queue-send > .workspace-menu > summary { width:28px; min-width:28px; height:28px; min-height:28px; }
  .queue-auto-clean { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:8px 12px; font-size:var(--text-body); }
}
</style>
<style>
.commit-queue { container:commitqueue / inline-size; background:var(--page); }
.queue-toolbar:has(.switch-control) { height:46px; flex-wrap:nowrap; }.queue-toolbar .result-count { position:static; display:inline-flex; align-items:center; justify-content:center; flex-shrink:0; min-width:20px; height:20px; font-size:var(--text-label); box-shadow:none; background:var(--surface-high); color:var(--on-surface); }
.queue-toolbar .switch-control { flex-shrink:0; }.queue-files-dock { container:queuefiles / inline-size; }.queue-details { container:queuedetails / inline-size; gap:8px; }
.queue-summary, .queue-detail-scroll, .queue-send { background:var(--surface); border-radius:var(--surface-radius); }
.queue-detail-scroll { padding:11px; }.queue-detail-scroll > .app-text-area { width:calc(100% - 12px); box-sizing:border-box; min-height:60px; margin:8px 6px 16px; }
.queue-section-label { margin:0 0 8px; font-weight:500; }.queue-options { gap:2px 12px; padding:12px 0 26px; }.queue-options .app-checkbox { min-height:36px; }
.queue-advanced.app-button { margin:0 0 14px; border-top:1px solid var(--outline-variant); border-bottom:0; font-weight:600; height:44px; }
.queue-fields { gap:6px 12px; margin-bottom:12px; }.queue-fields label { flex-direction:row; align-items:center; color:var(--muted); gap:8px; }.queue-fields label > * { flex:1; min-width:0; }
.queue-field-note { margin:0; font-size:var(--text-caption); }.queue-options + .queue-naming-toggle { margin-top:0; border-top:1px solid var(--outline-variant); border-bottom:0; }
.queue-context { display:flex; align-items:center; gap:5px; min-width:0; }.queue-context small { flex-shrink:0; }.queue-context .app-text-field { height:28px; width:170px; }
.queue-preview-buttons { display:flex; gap:6px; }.queue-preview-buttons .app-button { width:30px; height:30px; min-width:30px; min-height:30px; }
.queue-preview-buttons .app-icon { font-size:16px; }.queue-send { border:0; min-height:52px; padding:8px; box-sizing:border-box; }.queue-send > .app-button[aria-label="Cancel"]:disabled, .queue-send > .app-button[aria-label="Retry"]:disabled { display:none; }
.queue-preview-list { max-height:400px; overflow:auto; }.queue-preview-list > div { display:flex; align-items:center; gap:10px; margin:5px 0; }.queue-preview-list .item-preview { width:46px; height:46px; flex:0 0 46px; border-radius:var(--item-radius); }.queue-preview-list strong { flex:1; font-size:var(--text-body); }.queue-row.selected { background:var(--content-selection); }.queue-advanced.app-button { background:transparent; color:var(--on-surface); }.queue-naming-toggle.app-button { background:transparent; }
.queue-fields { grid-template-columns:minmax(0,1fr) 180px; }.queue-fields > label:last-of-type { display:contents; }.queue-fields > label:last-of-type > span { align-self:center; }.queue-fields > label:last-of-type > input { grid-column:1/-1; }.queue-detail-scroll { flex:0 1 auto; margin-bottom:auto; }.queue-row:has([role="status"]:not(:empty)) { min-height:68px; }
.queue-row { position:relative; gap:6px; margin-bottom:4px; }.queue-row.selected::before { content:''; position:absolute; left:0; top:5px; bottom:5px; width:3px; border-radius:2px; background:var(--primary); }
.queue-row-status:has(span:only-child) { font-size:var(--text-micro); }.queue-row .image-picker-preview { background:var(--surface-high); }.queue-row .app-menu > summary { width:26px; height:26px; min-width:26px; min-height:26px; }
.queue-source-file { height:32px; margin:4px 6px; }.queue-source-files .queue-toolbar { height:36px; }.queue-source-file > div small { display:none; }.queue-source-file .app-button.icon-button { width:26px; min-width:26px; height:26px; min-height:26px; }
@container queuedetails (max-width:620px) { .queue-preview-buttons, .queue-status { display:none; }.queue-fields, .queue-options { grid-template-columns:1fr; }.queue-summary { gap:8px; }.queue-summary .item-preview { width:56px; height:56px; flex-basis:56px; } }
@container queuefiles (max-width:350px) { .queue-toolbar > .switch-control + span { display:none; }.queue-toolbar { gap:3px; } }
@container commitqueue (max-width:710px) { .commit-queue-workspace { flex-direction:column; overflow:auto; }.queue-files-dock { min-width:0; flex:0 0 290px; }.commit-queue-workspace > .app-splitter { display:none; }.queue-source-files { flex-basis:120px; }.queue-details { flex:0 0 auto; overflow:visible; }.queue-detail-scroll { overflow:visible; }.queue-fields, .queue-options { grid-template-columns:1fr; } }
</style>
