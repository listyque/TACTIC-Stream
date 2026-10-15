<script>
import api from '../api.js';
import uiState from '../uiState.js';
import ConfiguredTable from './ConfiguredTable.vue';
import ConfiguredForm from './ConfiguredForm.vue';
import RecordInspector from './RecordInspector.vue';
import AdvancedFilter from './AdvancedFilter.vue';
import CsvExport from './CsvExport.vue';
import ConfigAudit from './ConfigAudit.vue';
import TaskTimeline from './TaskTimeline.vue';
import CollectionPanel from './CollectionPanel.vue';
import RelationTree from './RelationTree.vue';
import ViewDesigner from './ViewDesigner.vue';
export default {
 name:'WidgetTable',components:{ConfiguredTable,ConfiguredForm,RecordInspector,AdvancedFilter,CsvExport,ConfigAudit,TaskTimeline,CollectionPanel,RelationTree,ViewDesigner},
 props:{project:String,screen:Object,user:Object,refreshKey:Number},emits:['open','dirty','changed','refresh'],
 data(){return {stateReady:false,stateSeq:0,rows:[],summaries:[],offset:0,limit:this.screen.spec?.table_options?.page_size||50,total:null,where:{op:'and',children:[]},sort:null,state:'active',mode:'data',error:'',busy:false,seq:0,selected:[],form:null,formError:'',saving:false,formKey:0,formSeq:0,previewBusy:false,previewFailed:false,inspected:null,exporting:false,audit:false,designer:false,dirty:false,searchOpen:false,quickField:'',quickText:'',filters:[]}},
 computed:{filterCount(){const count=n=>n?.children?n.children.reduce((v,c)=>v+count(c),0):n?.field?1:0;return count(this.where)+this.filters.length},query(){return {where:this.where,filters:this.filters,sort:this.sort||undefined,record_state:this.state}},spec(){return this.screen.spec}},
 mounted(){this.restoreState()},beforeUnmount(){this.seq++;this.formSeq++;this.stateSeq++},watch:{refreshKey(){this.load()},screen(){this.restoreState()},mode(){this.saveState()},searchOpen(){this.saveState()},quickField(){this.saveState()},quickText(){this.saveState()}},
 methods:{
  async restoreState(){const seq=++this.stateSeq,args=this.args(),current=()=>seq===this.stateSeq&&args.project===this.project&&args.target===this.screen.id;this.seq++;this.stateReady=false;try{const r=await uiState.load({...args,scope:'query'});if(!current())return;if(r.value){const q=r.value;Object.assign(this,{filters:q.filters,where:q.where,sort:q.sort,state:q.record_state,offset:q.offset,limit:q.limit,mode:q.presentation,searchOpen:q.search_open,quickField:q.quickField,quickText:q.quickText})}await this.$nextTick();if(!current())return;this.stateReady=true}catch(e){if(!current())return;this.error='Не удалось восстановить настройки: '+e.message}if(current())await this.load()},
  saveState(){if(this.stateReady&&this.user?.allow_writes)uiState.schedule({...this.args(),scope:'query'},{filters:this.filters,where:this.where,sort:this.sort,record_state:this.state,offset:this.offset,limit:this.limit,presentation:this.mode,search_open:this.searchOpen,quickField:this.quickField,quickText:this.quickText,quickOp:'contains'})},
  tableAction({id,value}){
   if(id==='create')this.edit(null);else if(id==='refresh')this.load();
   else if(id==='search')this.searchOpen=!this.searchOpen;
   else if(id==='bulk')this.bulk();else if(id==='export')this.exporting=true;
   else if(id==='designer')this.designer=true;else if(id==='audit')this.audit=true;
   else if(id==='save-view')this.saveSearch();else if(id==='mode')this.mode=value;
   else if(id==='state'){this.state=value;this.offset=0;this.load()}
  },
  quickSearch(){if(!this.quickField||!this.quickText.trim())return;this.filters=[{field:this.quickField,op:'contains',value:this.quickText}];this.offset=0;this.load()},
  clearQuickSearch(){this.filters=[];this.quickText='';this.offset=0;this.load()},
  args(){return {project:this.project,target:this.screen.id}},
  async load(){const seq=++this.seq,args=this.args(),current=()=>seq===this.seq&&args.project===this.project&&args.target===this.screen.id;this.busy=true;this.error='';try{const d=await api.request('/query',{...args,...this.query,offset:this.offset,limit:this.limit},'POST');if(current()){this.rows=d.items;this.summaries=d.summaries||[];this.total=d.total;this.saveState()}}catch(e){if(current())this.error=e.message}finally{if(seq===this.seq)this.busy=false}},
  apply(where){this.where=where;this.offset=0;this.load()},page(offset){this.offset=offset;this.load()},
  order(field){this.sort=typeof field==='object'?field:{field,direction:this.sort?.field===field&&this.sort.direction==='asc'?'desc':'asc'};this.offset=0;this.load()},
  async edit(row){this.error='';this.formError='';this.previewFailed=false;try{this.form=await api.request('/form',{...this.args(),key:row?.key});this.formKey++}catch(e){this.error=e.message}},
  inspect(row){this.inspected=row},
  async preview(values){const seq=++this.formSeq;this.previewBusy=true;this.previewFailed=false;try{const f=await api.request('/form-preview',{...this.args(),key:this.form.record?.key,revision:this.form.record?.revision,values},'POST');if(seq===this.formSeq)this.form=f}catch(e){if(seq===this.formSeq){this.formError=e.message;this.previewFailed=true}}finally{if(seq===this.formSeq)this.previewBusy=false}},
  async save(values){if(this.previewFailed||this.previewBusy||this.saving)return;this.saving=true;this.formError='';try{if(this.form.records)await api.request('/bulk-records',{...this.args(),records:this.form.records.map(r=>({key:r.key,revision:r.revision,values}))},'PATCH');else await api.request('/record',{...this.args(),key:this.form.record?.key,revision:this.form.record?.revision,values},this.form.record?'PATCH':'POST');this.form=null;this.dirty=false;this.$emit('dirty',false);await this.load()}catch(e){this.formError=e.message}finally{this.saving=false}},
  async bulk(){if(!this.selected.length||this.selected.length>100)return;this.error='';try{const forms=[];for(const key of this.selected)forms.push(await api.request('/form',{...this.args(),key}));const fields=forms[0].spec.fields.filter(f=>!f.read_only&&forms.every(x=>x.spec.fields.some(g=>g.name===f.name&&!g.read_only&&g.kind===f.kind))).map(f=>({...f,options:(f.options||[]).filter(o=>forms.every(x=>x.spec.fields.find(g=>g.name===f.name).options?.some(v=>String(v.value)===String(o.value))))}));this.form={spec:{...forms[0].spec,fields},records:forms.map(f=>f.record),record:null,bulk:true};this.formKey++}catch(e){this.error=e.message}},
  async saveSearch(){const title=prompt('Название поиска в My Views');if(!title)return;try{await api.request('/saved-view',{...this.args(),...this.query,title},'POST');this.$emit('changed')}catch(e){this.error=e.message}},
  async dates(change){try{const form=await api.request('/form',{...this.args(),key:change.row.key});if(form.record.revision!==change.row.revision)throw Error('Запись изменилась; обновите период');const values={};for(const name of [change.startField,change.endField]){const f=form.spec.fields.find(f=>f.name===name);if(!f||f.read_only)throw Error('Дата недоступна для изменения');const m=/^(\d{4}-\d{2}-\d{2})(.*)$/.exec(String(form.record.values[name]));if(!m)throw Error('Некорректная дата');const d=new Date(m[1]+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+change.delta);values[name]=d.toISOString().slice(0,10)+(f.kind==='date'?'':m[2]||'T00:00:00')}await api.request('/record',{...this.args(),key:change.row.key,revision:form.record.revision,values},'PATCH');await this.load()}catch(e){this.error=e.message}},
  mark(value){this.dirty=value;this.$emit('dirty',value)}
 }
};
</script>
<template>
<section class="widget-table" :aria-label="screen.title" :data-widget-target="screen.id">
 <ConfiguredTable :project="project" :target="screen.id" :spec="spec" :rows="rows" :summaries="summaries" :busy="busy" :total="total" :offset="offset" :limit="limit" :presentation="mode" :record-state="state" :allow-writes="user.allow_writes" :filter-count="filterCount" :search-open="searchOpen" @table-action="tableAction" @inspect="inspect" @edit="edit" @sort="order" @page="page" @selection="selected=$event" @edit-selected="bulk" @dirty="mark" @changed="load" @open="$emit('open',$event)" @view-changed="$emit('refresh')">
  <template #filters><div class="table-search-heading"><strong>Поиск в представлении</strong><button class="text-button" aria-label="Свернуть поиск" @click="searchOpen=false">×</button></div><form v-if="spec.table_options?.show_keyword_search!==false" class="table-quick-search" @submit.prevent="quickSearch"><select v-model="quickField" aria-label="Поле поиска"><option value="">Поле…</option><option v-for="f in spec.fields.filter(f=>f.storage&&['text','textarea'].includes(f.kind))" :key="f.name" :value="f.name">{{f.label}}</option></select><input v-model="quickText" placeholder="Значение…" aria-label="Значение поиска"><button :disabled="!quickField||!quickText.trim()||busy" class="primary">Найти</button><button v-if="filters.length" type="button" @click="clearQuickSearch">Сбросить</button></form><AdvancedFilter v-if="spec.table_options?.show_search!==false" :value="where" :fields="spec.fields" :base-filter="screen.options?.filter" @apply="apply"/></template>
  <template #status><p v-if="spec.write_notice" class="notice write-mode-notice">{{spec.write_notice}}</p><p v-if="error" class="error">{{error}}</p></template>
  <template #alternate><RelationTree v-if="mode==='tree'" :project="project" :target="screen.id" :spec="spec" :rows="rows" :summaries="summaries" :busy="busy" :total="total" :offset="offset" :limit="limit" @open="$emit('open',$event)" @inspect="$emit('open',{id:$event.target})" @page="page"/><TaskTimeline v-else-if="mode==='timeline'" :project="project" :target="screen.id" :spec="spec" :query="query" :refresh-key="seq" @edit="edit" @inspect="inspect" @dates="dates"/><CollectionPanel v-else-if="mode==='collections'" :project="project" :target="screen.id" :selected-keys="selected" @open="$emit('open',$event)" @changed="load"/></template>
 </ConfiguredTable>
 <RecordInspector v-if="inspected" :key="inspected.key+':'+(inspected._section||'fields')" :project="project" :target="screen.id" :record="inspected" :spec="spec" :allow-uploads="user.allow_uploads" @close="inspected=null" @edit="edit" @open="$emit('open',$event)" @changed="load"/>
 <ConfiguredForm v-if="form" :key="formKey" :project="project" :target="screen.id" :form="form" :busy="saving||previewBusy||previewFailed" :error="formError" @preview="preview" @dirty="mark" @save="save" @close="form=null;mark(false)"/>
 <ConfigAudit v-if="audit" :project="project" :target="screen.id" @close="audit=false"/><CsvExport v-if="exporting" :project="project" :target="screen.id" :spec="spec" :query="query" :selected-keys="selected" @close="exporting=false"/><ViewDesigner v-if="designer" :project="project" :search-type="spec.type" :initial-view="spec.view" :login="user.login" @close="designer=false" @saved="$emit('refresh');$emit('changed')"/>
</section>
</template>
