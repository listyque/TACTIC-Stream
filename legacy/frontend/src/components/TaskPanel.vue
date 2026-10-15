<script>
import api from '../api.js';
import ConfiguredForm from './ConfiguredForm.vue';
import WorkHoursPanel from './WorkHoursPanel.vue';
export default {
 name:'TaskPanel',components:{ConfiguredForm,WorkHoursPanel},props:{project:String,target:String,record:Object},emits:['changed'],
 data(){return {data:null,busy:false,error:'',offset:0,mode:'board',dragging:null,form:null,formError:'',saving:false,formBusy:false,formFailed:false,formSequence:0,preview:null,selectedProcesses:[],startDate:'',generationBusy:false,hours:null}},
 computed:{
  groups(){
   if(!this.data)return [];
   return this.data.pipelines.map(p=>{
    const rows=this.data.items.filter(r=>r.task_pipeline===p.code);
    const names=p.statuses.map(s=>s.name);
    const unknown=[...new Set(rows.map(r=>r.task.status||'').filter(s=>!names.includes(s)))];
    const columns=[...p.statuses,...unknown.map(name=>({name,color:null}))].map(s=>({...s,rows:rows.filter(r=>(r.task.status||'')===s.name)}));
    return {...p,columns};
   });
  }
 },
 mounted(){this.load()},
 methods:{args(){return {project:this.project,target:this.target,key:this.record.key}},
 async load(){this.busy=true;this.error='';try{this.data=await api.request('/tasks',{...this.args(),offset:this.offset,limit:100})}catch(e){this.error=e.message}finally{this.busy=false}},
 canMove(row,status){return this.data?.can_write&&!row.retired&&row.allowed_statuses.includes(status)&&row.task.status!==status},
 async move(row,status){if(!this.canMove(row,status)||this.busy)return;this.busy=true;this.error='';try{await api.request('/task-change',{...this.args(),task:row.key,revision:row.revision,values:{status}},'PATCH');await this.load();this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false;this.dragging=null}},
 dropped(p,status){const row=this.dragging;if(row?.task_pipeline===p.code)this.move(row,status)},
 async edit(row){this.formError='';this.formFailed=false;this.formSequence++;try{this.form=await api.request('/task-form',{...this.args(),task:row.key})}catch(e){this.error=e.message}},
 async previewForm(values){const seq=++this.formSequence,form=this.form;this.formBusy=true;this.formFailed=false;this.formError='';try{const d=await api.request('/task-form-preview',{...this.args(),task:form.record.key,revision:form.record.revision,values},'POST');if(seq===this.formSequence&&this.form===form)this.form=d}catch(e){if(seq===this.formSequence){this.formError=e.message;this.formFailed=true}}finally{if(seq===this.formSequence)this.formBusy=false}},
 async save(values){if(this.formBusy||this.formFailed)return;this.saving=true;this.formError='';try{await api.request('/task-change',{...this.args(),task:this.form.record.key,revision:this.form.record.revision,values},'PATCH');this.form=null;await this.load();this.$emit('changed')}catch(e){this.formError=e.message}finally{this.saving=false}},
 async generatePreview(){this.error='';try{this.preview=await api.request('/task-generate',this.args());this.selectedProcesses=[]}catch(e){this.error=e.message}},
 async generate(){if(!this.preview?.can_write||!confirm('Создать задачи штатным генератором TACTIC? Серверные defaults, расписание и триггеры будут выполнены.'))return;this.generationBusy=true;this.error='';try{const d=await api.request('/task-generate',{...this.args(),revision:this.preview.revision,processes:this.selectedProcesses,start_date:this.startDate||null,confirm:'GENERATE'},'POST');this.preview=null;await this.load();this.$emit('changed');this.error='';this.data.notice='Создано задач: '+d.created}catch(e){this.error=e.message}finally{this.generationBusy=false}},
 page(delta){this.offset=Math.max(0,this.offset+delta);this.load()},date(v){return v?String(v).slice(0,16).replace('T',' '):'—'}
 }
};
</script>
<template>
<section class="task-panel"><div class="toolbar"><button :disabled="busy" @click="load">Обновить задачи</button><button v-if="data?.can_generate" @click="generatePreview">Сгенерировать из pipeline</button><span class="spacer"></span><button :class="{primary:mode==='board'}" @click="mode='board'">Доска</button><button :class="{primary:mode==='list'}" @click="mode='list'">Список</button></div><p v-if="error" class="error">{{error}}</p><p v-if="busy" class="muted">Чтение / сохранение…</p>
 <template v-if="data"><p class="notice">{{data.parent_title}} · {{data.total}} задач. Статусы — из pipeline каждой задачи; перемещение вызывает исходный EditCmd.</p><p v-if="data.notice" class="notice">{{data.notice}}</p>
 <div v-if="mode==='board'" class="task-boards"><section v-for="p in groups" :key="p.code" class="task-board"><h3>Pipeline: {{p.code||'по умолчанию'}}</h3><div class="task-lanes"><section v-for="status in p.columns" :key="status.name" class="task-lane" :style="{borderTopColor:status.color||undefined}" @dragover.prevent @drop.prevent="dropped(p,status.name)"><h4>{{status.name||'Статус не задан'}} <small>{{status.rows.length}}</small></h4><article v-for="row in status.rows" :key="row.key" class="task-card" :draggable="data.can_write&&!busy" @dragstart="dragging=row" @dragend="dragging=null"><button class="text-button" @click="edit(row)">{{row.task.process||row.task.code||row.key}}</button><p>{{row.task.description}}</p><small>{{row.task.assigned||'Не назначена'}}</small><button class="text-button" @click="hours=row">Рабочее время</button><div class="task-dates">{{date(row.task.bid_start_date)}} → {{date(row.task.bid_end_date)}}</div><select :value="row.task.status||''" :disabled="!data.can_write||busy||row.retired" @change="move(row,$event.target.value)" aria-label="Статус задачи"><option v-for="s in [...new Set([row.task.status||'',...row.allowed_statuses])]" :key="s" :value="s">{{s||'—'}}</option></select></article></section></div></section></div>
 <table v-else class="task-list"><thead><tr><th>Процесс / контекст</th><th>Статус</th><th>Исполнитель</th><th>Срок</th></tr></thead><tbody><tr v-for="row in data.items" :key="row.key" @dblclick="edit(row)"><td><button class="text-button" @click="edit(row)">{{row.task.process||row.task.code}}</button><small>{{row.task.context}}</small><button class="text-button" @click="hours=row">Рабочее время</button></td><td>{{row.task.status}}</td><td>{{row.task.assigned}}</td><td>{{date(row.task.bid_end_date)}}</td></tr></tbody></table>
 <p v-if="!data.items.length" class="muted">Задачи пока не созданы.</p><div class="toolbar"><button :disabled="busy||offset===0" @click="page(-100)">←</button><span>{{data.items.length}} показано · {{offset}} пропущено · {{data.total}} всего</span><button :disabled="busy||offset+data.items.length>=data.total" @click="page(100)">→</button></div></template>
 <Teleport to="body"><WorkHoursPanel v-if="hours" :key="hours.key" :project="project" :target="target" :record="record" :task="hours" @close="hours=null" @changed="$emit('changed')"/><div v-if="preview" class="modal-backdrop" @click.self="preview=null"><section class="modal task-generation"><header><h2>Генерация задач</h2><button :disabled="generationBusy" @click="preview=null">×</button></header><p>Pipeline {{preview.pipeline}} · уже есть {{preview.existing}} задач</p><p class="notice">{{preview.notice}}</p><div class="process-checks"><label v-for="p in preview.processes" :key="p.name"><input type="checkbox" :value="p.name" v-model="selectedProcesses">{{p.name}} <small>{{p.type}}</small></label></div><label>Дата начала<input type="date" v-model="startDate"></label><p v-if="error" class="error">{{error}}</p><footer><button :disabled="generationBusy" @click="preview=null">Отмена</button><button class="primary" :disabled="!preview.can_write||generationBusy" @click="generate">{{generationBusy?'Создание…':selectedProcesses.length?'Создать выбранные':'Штатная генерация всего pipeline'}}</button></footer></section></div><ConfiguredForm v-if="form" :key="form.record.key" :form="form" :error="formError" :busy="saving||formBusy||formFailed" @preview="previewForm" @save="save" @close="form=null"/></Teleport>
</section>
</template>
