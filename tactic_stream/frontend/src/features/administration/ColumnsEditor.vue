<script>
import FrameView from '../../frame/FrameView.vue'
import {columnsEditor} from '../../api.js'
import {t} from '../../i18n.js'
import {appearance} from '../../appearance.js'
import {definitionWizard,changeDefinition,displayWidgets} from './columnsEditor.js'
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/columns/columns.ui.mjs'
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/columns/columns.state.mjs'

export default {
  components:{FrameView},
  props: { ticket: String, project: String, toolbarTarget: String, presentationVisible: { type: Boolean, default: true }, initialFocus: Object }, emits: ['saved'],
  data() { return { catalog: null, context: null, identity: '', xml: '', baseline: '',
    ui:State.initial(), viewport:{width:1,height:1},toolbarSize:620,observer:null,resizeFrame:0,  busy: false, uncertain: false, error: '', message: '',  request: 0 } },
  computed: {
    frameModel(){return {ready:!!this.selected,canWrite:!!this.catalog&&this.context?.ticket===this.ticket&&this.context?.project===this.project,canLoad:!!this.ticket,
      busy:this.busy,dirty:this.dirty,uncertain:this.uncertain,error:this.error,message:this.message,xml:this.xml,records:this.catalog?.records||[],selected:this.selected||{},wizard:this.wizard,elements:this.wizard.elements||[],element:this.element||{},
      typeOptions:this.catalog?.searchTypes||[],widgetOptions:this.widgets.map(row=>({...row,label:t(row.label)}))}},
    frameScene(){return UI.describe(this.frameModel,this.ui,this.viewport.width,this.viewport.height,appearance.language)},
    toolbarScene(){return UI.toolbar(this.frameModel,this.ui,this.toolbarSize,appearance.language)},
    models(){return {definitions:this.records,columns:this.wizard.elements||[]}},
    dirty() { return this.uncertain || this.xml !== this.baseline || State.pending(this.ui) },
    editable() { return !!this.catalog && this.context?.ticket === this.ticket && this.context?.project === this.project && !this.busy && !this.uncertain },
    records() { return UI.records(this.frameModel,this.ui) },
    selected() { return this.catalog?.records.find(row => row.identity === this.identity) },
    wizard() { try { return definitionWizard(this.xml) } catch (error) { return { supported: false, elements: [], error: error.message } } },
    element() { return this.wizard.elements.find(row => row.path === this.ui.path) || this.wizard.elements[0] },
    widgets() { const value = this.element?.widget; return value && !displayWidgets.some(row => row.value === value) ? [{ value, label: value, translate: false }, ...displayWidgets] : displayWidgets },
    typeChoices() { return [{ value: '', label: t('All Search Types') }, ...(this.catalog?.searchTypes || [])] },
  },
  watch: {
    initialFocus() { if (this.presentationVisible && this.catalog && !this.dirty) this.focusRequestedColumn() },
    presentationVisible(value) { if (value && this.catalog && !this.dirty) this.focusRequestedColumn() },
    project() { this.request++; this.busy = false; this.catalog = null; this.xml = this.baseline = ''; this.ui=State.initial();this.reload(true) },
    ticket() { this.request++; this.busy = false; this.catalog = null; this.xml = this.baseline = ''; this.reload(true) },
  },
  mounted(){
    this.reload();window.addEventListener('beforeunload',this.beforeUnload)
    this.observer=new ResizeObserver(entries=>{cancelAnimationFrame(this.resizeFrame);this.resizeFrame=requestAnimationFrame(()=>{for(const entry of entries){if(entry.target===this.$refs.body)this.viewport={width:Math.max(1,entry.contentRect.width),height:Math.max(1,entry.contentRect.height)};else this.toolbarSize=entry.contentRect.width}})})
    this.observer.observe(this.$refs.body);this.observer.observe(this.toolbarTarget?document.querySelector(this.toolbarTarget)||this.$el:this.$el)
  },
  beforeUnmount(){this.request++;this.observer?.disconnect();cancelAnimationFrame(this.resizeFrame);window.removeEventListener('beforeunload',this.beforeUnload)},
  methods: {
    rowScene(node,record){return UI.row(node,record,this.frameModel,this.ui)},
    applyText(){for(const [field,value] of Object.entries(this.ui.text)){this.change(field,value);if(this.error)return false};this.ui=State.transition(this.ui,this.frameModel,{type:'applied'}).ui;return true},
    async dispatch(event){
      const result=State.transition(this.ui,this.frameModel,event)
      for(const command of result.commands){
        if(!['reload','discard','xml'].includes(command.type)&&!this.applyText())return
        switch(command.type){
          case 'apply':break
          case 'filter':this.ui=result.ui;this.filterChanged();break
          case 'select':this.select(command.identity);break
          case 'column':break
          case 'mode':break
          case 'back':break
          case 'change':this.change(command.field,command.value);if(this.error)return;break
          case 'xml':this.xml=command.value;this.message='';break
          case 'save':await this.save();break
          case 'reload':await this.reload(true);break
          case 'discard':await this.discard();break
          default:throw Error('Unsupported Columns command: '+command.type)
        }
        result.ui=State.completed(result.ui,command,this.frameModel)
      }
      this.ui=result.ui
    },
    t,
    focusRequestedColumn() {
      if (this.initialFocus?.project !== this.project || !this.initialFocus?.searchType) return
      this.ui={...this.ui,query:'',searchType:this.initialFocus.searchType,editing:true}
      const matches = this.records.filter(row => row.view === this.initialFocus.view)
      this.select((matches.find(row => row.code === this.initialFocus.code) || matches.find(row => !row.login) || matches[0])?.identity || '',true)
    },
    beforeUnload(event) { if (this.dirty || this.busy || this.uncertain) { event.preventDefault(); event.returnValue = '' } },
    canLeave() { if (this.dirty || this.busy || this.uncertain) { this.error = 'Save or discard definition changes before leaving.'; return false }; return true },
    select(identity, force = false) {
      if (!force && (!this.editable || this.dirty)) return
      this.identity = identity; this.xml = this.baseline = this.selected?.config || ''
      this.ui=State.selected(this.ui,this.wizard.elements,this.initialFocus?.column)
      this.error = ''
    },
    filterChanged() { if (!this.dirty) this.select(this.records.some(row => row.identity === this.identity) ? this.identity : this.records[0]?.identity || '', true) },
    change(field, value) {
      if (!this.editable || !this.element) return
      try { this.xml = changeDefinition(this.xml, this.element.path, field, value); this.error = ''; this.message = '' }
      catch (error) { this.error = error.message }
    },
    async reload(force = false) {
      if (this.busy || !this.ticket) return
      if (!force && (this.dirty || this.uncertain)) { this.dispatch({type:'reload'}); return }
      const request = ++this.request, previous = this.identity, first = !this.catalog
      this.context = { ticket: this.ticket, project: this.project }; this.busy = true; this.error = ''; this.message = ''
      try {
        const result = await columnsEditor('read', this.context.ticket, this.context.project)
        if (request !== this.request) return
        this.catalog = result; this.uncertain = false
        if (first && this.initialFocus?.project === this.project && this.initialFocus?.searchType) {
          this.ui={...this.ui,searchType:this.initialFocus.searchType,editing:true}
          const matches = this.records.filter(row => row.view === this.initialFocus.view)
          this.select((matches.find(row => row.code === this.initialFocus.code) || matches.find(row => !row.login) || matches[0])?.identity || '', true)
        } else this.select(this.records.find(row => row.identity === previous)?.identity || this.records[0]?.identity || '', true)
      } catch (error) { if (request === this.request) this.error = error.message }
      finally { if (request === this.request) this.busy = false }
    },
    async discard() { if (this.uncertain) await this.reload(true); else this.select(this.identity, true) },
    async save() {
      if (!this.editable || !this.dirty || !this.selected) return
      const request = this.request; this.busy = true; this.error = ''; this.message = ''
      try {
        const result = await columnsEditor('save', this.context.ticket, this.context.project, { source_id: this.selected.id, xml: this.xml, revision: this.catalog.revision })
        if (request !== this.request) return
        this.catalog = result; this.select(result.selected, true); this.message = 'TACTIC definition saved'; this.$emit('saved', result)
      } catch (error) {
        if (request !== this.request) return
        this.uncertain = !error.status || error.status >= 500
        this.error = this.uncertain ? 'The save result is unknown. Reload definitions before trying again.' : error.message
      } finally { if (request === this.request) this.busy = false }
    },
  },
}
</script>

<template>
  <section class="columns-editor frame-host" :aria-label="t('Columns Editor')" :aria-busy="busy">
    <Teleport defer :to="toolbarTarget||'body'" :disabled="!toolbarTarget"><div v-show="presentationVisible" class="frame-toolbar-host" :style="{width:toolbarSize+'px'}"><FrameView :scene="toolbarScene" @event="dispatch" /></div></Teleport>
    <div ref="body" class="frame-host-body"><FrameView ref="frame" :scene="frameScene" :models="models" :describe-row="rowScene" @event="dispatch" /></div>
  </section>
</template>
