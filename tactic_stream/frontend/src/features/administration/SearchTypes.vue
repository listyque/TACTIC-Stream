<script>
import {markRaw} from 'vue'
import {rpc} from '../../api.js'
import {t} from '../../i18n.js'
import {appearance} from '../../appearance.js'
import FrameView from '../../frame/FrameView.vue'
import NamingEditor from './NamingEditor.vue'
import {readPreviewImage} from '../../controls/previewImage.js'
import {automaticFields,fieldTypes} from './searchTypeFields.js'
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/search_types/search_types.ui.mjs'
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/search_types/search_types.state.mjs'

export default {
  components:{FrameView},
  props: { ticket: String, project: String, toolbarTarget: String, presentationVisible: { type: Boolean, default: true }, queuePreview: Function, checkins: Array, creationOnly: Boolean, schemaRevision: String },
  emits: ['saved', 'created', 'back', 'open-commit-queue', 'open-workflow'],
  data() { return { catalog: [], ui:State.initial(),viewport:{width:1,height:1},toolbarSize:620,observer:null,resizeFrame:0,namingView:null,namingSession:{},identity: '',
    document: null, metadata: {}, revision: '', baseline: '', busy: false, error: '', uncertain: false, canWrite:false,
    context: null, request: 0,
    previewFile: null, previewDataUrl:'',imageRequest:0,previewUrl: '', previewError: '', previewRequest: 0, previewValidating: false } },
  computed: {
    documentDirty() { return this.uncertain || this.document !== null && (this.previewFile !== null || JSON.stringify(this.document) !== this.baseline) },
    namingDirty(){const saved=this.namingSession.snapshot;return this.namingView?this.namingView.dirty:!!saved&&(saved.uncertain||JSON.stringify(saved.document)!==saved.baseline)},
    dirty(){return this.documentDirty||this.namingDirty},
    previewJob() { return this.checkins?.findLast(job => job.searchKey === this.metadata.searchKey) },
    previewPending() { return this.previewJob && ['Queued', 'Uploading', 'Checking in', 'Failed', 'Result unknown'].includes(this.previewJob.status) },
    page:{get(){return this.ui.page},set(value){this.ui={...this.ui,page:value}}},
    automaticFields(){return automaticFields.concat(this.document?.hasPipeline?["pipeline_code"]:[])},
    visibleTypes(){return UI.records(this.frameModel,this.ui)},
    frameModel(){return {ready:!!this.document,canWrite:!!this.ticket&&this.canWrite&&this.metadata.tableAvailable!==false,canLoad:!!this.ticket,busy:this.busy||this.previewValidating||!!this.namingView?.busy,dirty:this.documentDirty,uncertain:this.uncertain,error:this.error,message:'',identity:this.identity,document:this.document||{},metadata:this.metadata,catalog:this.catalog,creationOnly:!!this.creationOnly,namingLocked:this.namingDirty||!!this.namingView?.busy,relationshipGraph:this.metadata.relationshipGraph||{nodes:[],edges:[]},previewUrl:this.previewDataUrl||this.previewUrl,previewStaged:!!this.previewFile,previewQueued:!!this.previewPending,previewError:this.previewError}},
    frameScene(){return UI.describe(this.frameModel,this.ui,this.viewport.width,this.viewport.height,appearance.language)},
    toolbarScene(){return UI.toolbar(this.frameModel,this.ui,this.toolbarSize,appearance.language)},
    models(){return {types:this.visibleTypes,fields:UI.existing(this.frameModel,this.ui)}},
    views(){return {naming:{component:markRaw(NamingEditor),captureRef:this.captureNaming,props:{ticket:this.ticket,project:this.project,session:this.namingSession,searchType:this.identity,targetTitle:this.document?.title||this.identity,presentationVisible:this.presentationVisible,onSaved:()=>this.$emit('saved')}}}},
  },
  created() { if (this.creationOnly) { this.canWrite=!!this.ticket; this.context = { ticket: this.ticket, project: this.project }; this.create() } else this.reload() },
  mounted() {
    window.addEventListener('beforeunload',this.beforeUnload)
    this.observer=new ResizeObserver(entries=>{cancelAnimationFrame(this.resizeFrame);this.resizeFrame=requestAnimationFrame(()=>{for(const entry of entries){if(entry.target===this.$refs.body)this.viewport={width:Math.max(1,entry.contentRect.width),height:Math.max(1,entry.contentRect.height)};else this.toolbarSize=entry.contentRect.width}})})
    this.observer.observe(this.$refs.body);this.observer.observe(this.toolbarTarget?document.querySelector(this.toolbarTarget)||this.$el:this.$el)
  },
  beforeUnmount() { this.observer?.disconnect();cancelAnimationFrame(this.resizeFrame);this.imageRequest++;this.request++; this.previewRequest++; window.removeEventListener('beforeunload', this.beforeUnload) },
  watch: {identity(){this.ui=State.synchronize(this.ui,this.frameModel)},document(){this.ui=State.synchronize(this.ui,this.frameModel)}, ticket() { this.namingSession={};this.reload() }, project() { this.namingSession={};this.reload() },
    'previewJob.status'(status) { if (status === 'Complete') this.loadPreview() },
  },
  methods: {
    t,
    captureNaming(value){this.namingView=value},
    rowScene(node,record){return UI.row(node,record,this.frameModel,this.ui,appearance.language)},

    selectPage(page){return this.dispatch({type:'page',value:page})},
    async dispatch(event){
      const result=State.transition(this.ui,this.frameModel,event);this.ui=result.ui
      for(const command of result.commands){
        switch(command.type){
          case 'field':this.document[command.field]=command.value;break
          case 'page':break
          case 'select':await this.select(command.identity);break
          case 'create':this.create();break
          case 'save':await this.save(true);break
          case 'reload':await this.reload();break
          case 'discard':this.previewFile=null;this.previewDataUrl='';this.imageRequest++;this.document=this.baseline?JSON.parse(this.baseline):null;break
          case 'addField':this.addField(command.name,command.columnType);if(this.error)return;break
          case 'removeDraft':this.document.columns.splice(command.index,1);break
          case 'removeField':this.toggleDeletion(command.name);break
          case 'preview':this.$refs.previewFile.click();break
          case 'clearPreview':this.previewFile=null;this.previewDataUrl='';this.imageRequest++;this.previewError='';break
          case 'queue':this.$emit('open-commit-queue');break
          case 'workflow':this.$emit('open-workflow',{identity:command.identity,searchType:this.identity});break
          default:throw Error('Unsupported Search Types command: '+command.type)
        }
        this.ui=State.completed(this.ui,command,this.frameModel)
      }
    },
    async choosePreview(event){
      const file=event.target.files[0];event.target.value='';if(!file)return
      const id=++this.imageRequest;this.previewValidating=true;this.previewError=''
      try{const url=await readPreviewImage(file);if(id===this.imageRequest){this.previewFile=file;this.previewDataUrl=url}}
      catch{if(id===this.imageRequest)this.previewError='The selected preview is not a readable image'}
      finally{if(id===this.imageRequest)this.previewValidating=false}
    },
    beforeUnload(event) { if (this.dirty || this.busy || this.uncertain || this.previewValidating) { event.preventDefault(); event.returnValue = '' } },
    canLeave() {
      if(this.namingView&&!this.namingView.canLeave())return false
      if(!this.namingView&&this.namingDirty&&!window.confirm(t('Discard unsaved naming changes?')))return false
      return !this.busy&&!this.previewValidating&&(!this.documentDirty||window.confirm(t('Discard unsaved changes?')))
    },
    async call(action, values = {}) {
      const result = await rpc('execute_cmd', [{ ticket: this.context.ticket, project: this.context.project, language: 'python' },
        'tactic.ui.panel.search_types_cmd.SearchTypesCmd', { action, project_code: this.context.project, ...values }])
      return result.info
    },
    accept(result) {
      this.catalog = result.catalog
      this.canWrite = result.canWrite !== false
      this.identity = result.identity
      this.document = result.document
      this.metadata = result.metadata
      this.revision = result.revision
      this.baseline = JSON.stringify(this.document)
      this.previewFile = null
      this.previewDataUrl='';this.imageRequest++;this.previewValidating=false
      this.loadPreview()
    },
    async loadPreview() {
      const id = ++this.previewRequest
      const key = this.metadata.searchKey
      this.previewUrl = this.previewError = ''
      if (!key) return
      try {
        const snapshot = await rpc('get_snapshot', [{ ticket: this.context.ticket, project: 'sthpw', language: 'python' }, key, 'icon'], { include_web_paths_dict: true })
        if (id !== this.previewRequest) return
        const paths = snapshot.__web_paths_dict__ || {}
        const path = paths.web?.[0] || paths.icon?.[0] || ''
        // Repository aliases are served on this origin; never load remote images.
        if (path) {
          const url = new URL(path, location.origin)
          if (url.origin === location.origin) this.previewUrl = url.pathname + url.search
        }
      } catch (error) { if (id === this.previewRequest) this.previewError = error.message }
    },
    async reload() {
      const id = ++this.request
      this.context = { ticket: this.ticket, project: this.project }
      this.busy = true
      this.error = ''
      try {
        const result = await this.call('list')
        if (id !== this.request) return
        this.catalog = result.catalog
        this.canWrite = result.canWrite !== false
        const selected = this.catalog.find(row => row.identity === this.identity) || this.visibleTypes[0]
        if (selected) {
          const loaded = await this.call('load', { identity: selected.identity })
          if (id !== this.request) return
          this.accept(loaded)
          this.page = 'summary'
        }
        else { this.document = null; this.identity = ''; this.previewFile = null; this.previewRequest++; this.previewUrl = this.previewError = '' }
        this.uncertain = false
      } catch (error) { if (id === this.request) this.error = error.message }
      finally { if (id === this.request) this.busy = false }
    },
    async select(identity) {
      if (!identity || identity === this.identity || !this.canLeave()) return
      const id = ++this.request
      this.busy = true
      this.error = ''
      try {
        const result = await this.call('load', { identity })
        if (id === this.request) { this.accept(result); this.page = 'summary'; this.uncertain = false }
      } catch (error) { if (id === this.request) this.error = error.message }
      finally { if (id === this.request) this.busy = false }
    },
    create() {
      if (!this.canLeave()) return
      this.identity = this.revision = this.error = ''
      this.document = { title: '', description: '', color: '', hasPipeline: true, columns: [], removedColumns: [] }
      this.metadata = {}
      this.previewFile = null
      this.previewRequest++
      this.previewUrl = this.previewError = ''
      this.page = 'details'
      this.baseline = ''
      this.uncertain = false
    },
    addField(value, type) {
      if (this.busy || this.uncertain) return
      const name = value.trim()
      if (!/^[a-z][a-z0-9_]*$/.test(name)) { this.error = 'Column names must be unique lowercase SQL identifiers'; return }
      if (!fieldTypes.some(field => field.value === type)) { this.error = 'Unsupported column type'; return }
      if (name in (this.metadata.columns || {}) || this.document.columns.some(field => field.name === name) || (!this.identity && this.automaticFields.includes(name))) {
        this.error = 'A column with this name already exists'; return
      }
      this.document.columns.push({ name, type })
      this.error = ''
      this.ui={...this.ui,fieldName:''}
    },
    toggleDeletion(name) {
      if (this.busy || this.uncertain || this.metadata.columnRemovalBlocks?.[name] && !this.document.removedColumns.includes(name)) return
      const index = this.document.removedColumns.indexOf(name)
      if (index < 0) this.document.removedColumns.push(name)
      else this.document.removedColumns.splice(index, 1)
    },
    submit() {
      if (this.identity || this.page === 'ready') this.save()
      else this.selectPage(this.page === 'details' ? 'fields' : 'ready')
    },
    async save(confirmed=false) {
      if (this.busy || this.previewValidating || this.uncertain || !this.documentDirty || !this.document.title.trim()) return
      if (!this.identity && this.page !== 'ready') return
      if (!confirmed && (this.document.removedColumns||[]).length && !window.confirm(t('Delete fields from {type}: {fields}? All values in these columns will be lost. Check scripts, naming rules and saved searches before saving.', { type: this.identity, fields: this.document.removedColumns.join(', ') }))) return
      const id = this.request
      this.busy = true
      this.error = ''
      try {
        const file = this.previewFile
        const creating = !this.identity
        const result = await this.call('save', { identity: this.identity, expected_revision: this.revision, document: this.document,
          ...(creating && this.creationOnly ? { schema_revision: this.schemaRevision } : {}) })
        if (id !== this.request) return
        this.accept(result)
        if (creating) this.page = 'details'
        if (!this.creationOnly) this.$emit('saved')
        if (file) {
          try {
            this.queuePreview({ ticket: this.context.ticket, project: 'sthpw', searchKey: this.metadata.searchKey,
              title: this.document.title, file, name: file.name })
          } catch (error) {
            this.previewFile = file
            this.previewError = t('Search Type saved, but its preview could not be queued: {error}', { error: error.message })
          }
        }
        if (creating && this.creationOnly) this.$emit('created', result)
        if (this.creationOnly) this.$emit('saved')
      } catch (error) {
        if (id !== this.request) return
        this.uncertain = !error.status || error.status >= 500
        this.error = this.uncertain ? 'The save result is unknown. Refresh before trying again.' : error.message
      } finally { if (id === this.request) this.busy = false }
    },
    async workflowSaved() {
      const id = this.request
      try { const result = await this.call('load', { identity: this.identity }); if (id === this.request) { if(this.dirty){this.metadata=result.metadata;this.catalog=result.catalog}else this.accept(result); this.$emit('saved') } }
      catch (error) { if (id === this.request) this.error = error.message }
    },
    async reset() { if (this.canLeave()) { this.document = null; await this.reload() } },
  },
}
</script>

<template>
 <section class="search-types-editor frame-host" :aria-busy="busy||previewValidating">
  <Teleport :to="toolbarTarget||'body'" :disabled="!toolbarTarget"><div v-show="presentationVisible" class="frame-toolbar-host" :style="{width:toolbarSize+'px'}"><FrameView :scene="toolbarScene" @event="dispatch" /></div></Teleport>
  <div ref="body" class="frame-host-body"><FrameView :scene="frameScene" :models="models" :views="views" :describe-row="rowScene" @event="dispatch" /></div>
  <input ref="previewFile" type="file" hidden accept="image/png,image/jpeg,image/webp,image/gif,image/bmp" :disabled="busy||previewValidating||uncertain||!!previewPending" @change="choosePreview">
 </section>
</template>
