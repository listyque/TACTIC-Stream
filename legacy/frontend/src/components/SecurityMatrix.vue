<script>
import api from '../api.js';
export default {
 name:'SecurityMatrix',props:['project','target','user','screen'],emits:['dirty','changed','open'],
 data(){return {matrix:null,category:'',groupKeys:[],pending:{},query:'',busy:false,error:'',message:'',section:'matrix',groupsScreen:null,advanced:false,userKey:'',childDirty:false,groupDirty:false,seq:0}},
 computed:{rows(){const q=this.query.toLowerCase();return (this.matrix?.rows||[]).filter(r=>[r.label,r.value,r.pipeline,r.section].some(v=>String(v||'').toLowerCase().includes(q)))},changes(){return Object.values(this.pending)},dirty(){return this.changes.length>0||this.childDirty||this.groupDirty},fixed(){return !!this.screen?.options?.native_fixed_group||/(?:Project|Link|GearMenu|SearchType|Process|Task|User)SecurityWdg$/.test(this.screen?.handler||'')}},
 watch:{dirty(v){this.$emit('dirty',v)}},mounted(){this.load()},beforeUnmount(){this.seq++},
 methods:{
 args(){return {project:this.project,target:this.target}},
 async load(category=this.category){const seq=++this.seq;this.busy=true;this.error='';try{const m=await api.request('/security-matrix',{...this.args(),category:category||undefined,groups:this.groupKeys.length?JSON.stringify(this.groupKeys):undefined});if(seq!==this.seq)return;this.matrix=m;this.category=m.category;this.groupKeys=m.groups.map(g=>g.key);this.pending={}}catch(e){if(seq===this.seq)this.error=e.message}finally{if(seq===this.seq)this.busy=false}},
 choose(category){if(category===this.category)return;if(this.dirty&&!confirm('Отменить изменения текущей матрицы?'))return;this.groupKeys=[];this.load(category)},
 groupChange(){if(this.dirty&&!confirm('Отменить правки перед сменой групп?'))return;this.load()},
 value(row,group){return this.pending[JSON.stringify([row.id,group.key])]?.value??row.cells[group.key].checked},
 toggle(row,group,event){const cell=row.cells[group.key];if(this.busy||cell.read_only||!this.matrix.can_write)return;const id=JSON.stringify([row.id,group.key]),value=event.target.checked,next={...this.pending};if(value===cell.explicit)delete next[id];else next[id]={row:row.id,group:group.key,value};this.pending=next},
 discard(){if(this.dirty&&!confirm('Отменить все несохранённые изменения прав?'))return;this.pending={}},
 async save(){if(this.busy||!this.dirty)return;this.busy=true;this.error='';try{api.action?.('form.save',{...this.args(),control:'security-matrix',count:this.changes.length});const r=await api.request('/security-matrix',{...this.args(),category:this.category,groups:this.groupKeys,changes:this.changes,revision:this.matrix.revision},'PATCH');this.pending={};await this.load();this.message=r.notice;this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}},
 async showGroups(){if(this.dirty&&!confirm('Отменить правки матрицы и открыть группы?'))return;this.pending={};this.error='';try{this.groupsScreen=await api.request('/open',{project:this.project,target:this.target+'/~admin/groups-table'});this.section='groups'}catch(e){this.error=e.message}},
 editUser(row){if(this.dirty||this.busy){this.error='Сначала сохраните или отмените правки матрицы';return}if(this.category==='users'){this.childDirty=false;this.userKey=row.key}},
 openAdvanced(){if(this.dirty||this.busy){this.error='Сначала сохраните или отмените текущие правки';return}this.advanced=true;this.childDirty=false},
 closeChild(){if(this.childDirty&&!confirm('Отменить несохранённые изменения?'))return;this.advanced=false;this.userKey='';this.childDirty=false},
 showMatrix(){if(this.section==='matrix')return;if(this.groupDirty&&!confirm('Отменить правки таблицы групп?'))return;this.groupDirty=false;this.section='matrix';this.load()}
 }
};
</script>
<template>
<section class="security-workspace" aria-label="Права TACTIC">
 <header class="widget-toolbar" role="group" aria-label="Инструменты прав"><div class="toolbar"><button v-if="!fixed" :class="{primary:section==='matrix'}" @click="showMatrix">Матрицы</button><button v-if="!fixed" @click="showGroups">Группы</button><button v-if="category!=='users'" :disabled="busy||dirty" @click="openAdvanced">XML правил…</button></div></header>
 <p v-if="error" class="error" role="alert">{{error}}</p><p v-if="message" class="success">{{message}}</p>
 <template v-if="section==='matrix'">
  <nav v-if="matrix?.categories.length>1" class="admin-section-tabs" aria-label="Категории прав"><button v-for="c in matrix.categories" :key="c.id" :aria-selected="category===c.id" @click="choose(c.id)">{{c.label}}</button></nav>
  <div class="toolbar admin-matrix-tools"><input v-model="query" type="search" placeholder="Найти строку…" aria-label="Поиск в матрице"><details v-if="matrix" class="admin-group-picker"><summary>Группы · {{matrix.groups.length}}</summary><div><label v-for="g in matrix.available_groups" :key="g.key"><input type="checkbox" v-model="groupKeys" :value="g.key" :disabled="busy||dirty">{{g.label||g.name}} <small>{{g.project||'общая'}}</small></label><button :disabled="busy||!groupKeys.length||groupKeys.length>40||dirty" @click="groupChange">Показать выбранные</button></div></details><button :disabled="busy||dirty" @click="load()">Обновить</button><span class="spacer"></span><span v-if="changes.length" class="pending-count">{{changes.length}} правок</span><button v-if="changes.length" :disabled="busy" @click="discard">Отменить</button><button v-if="changes.length" class="primary" :disabled="busy||!matrix.can_write" @click="save">Сохранить изменения</button></div>
  <p v-if="busy" class="muted">Загрузка…</p>
  <template v-if="matrix"><p class="muted admin-source-caption">{{matrix.notice}} · <code>{{matrix.command}}</code></p><p v-if="!matrix.can_write" class="notice">Запись отключена в настройках установки.</p>
   <div class="table-scroll security-matrix-scroll"><table class="security-matrix"><thead><tr><th>Область / объект</th><th v-for="g in matrix.groups" :key="g.key"><b>{{g.label||g.name}}</b><small>{{g.level}} · {{g.project||'global'}}</small></th></tr></thead><tbody><tr v-for="row in rows" :key="row.id" :data-rule="row.value"><th><button v-if="category==='users'" class="text-button" @click="editUser(row)">{{row.label}}</button><b v-else>{{row.label}}</b><small>{{row.pipeline||row.submenu||row.section||row.value}}</small></th><td v-for="g in matrix.groups" :key="g.key" :class="{'matrix-pending':pending[JSON.stringify([row.id,g.key])],'matrix-inherited':row.cells[g.key].inherited}" :title="row.cells[g.key].reason||'Явное правило allow'"><label class="matrix-checkbox"><input type="checkbox" :checked="value(row,g)" :disabled="busy||row.cells[g.key].read_only||!matrix.can_write" :aria-label="row.label+' — '+g.name" @change="toggle(row,g,$event)"><span v-if="row.cells[g.key].inherited" aria-hidden="true">↳</span><span v-else-if="row.cells[g.key].read_only" aria-hidden="true">•</span></label></td></tr></tbody></table></div>
   <p v-if="!matrix.groups.length" class="notice">Для этой категории нет групп текущего проекта. Назначьте группе проект в её исходной форме или Project Security.</p><p v-if="!rows.length" class="muted">Подходящих строк нет.</p><p class="muted">↳ задано access_level или общим правилом. Наведите указатель на недоступную ячейку для причины. XML и нетронутые категории сохраняются.</p>
  </template>
 </template>
 <WidgetTable v-else-if="groupsScreen" :project="project" :screen="groupsScreen" :user="user" @open="$emit('open',$event)" @dirty="groupDirty=$event" @changed="$emit('changed')"/>
 <Teleport to="body"><div v-if="advanced" class="modal-backdrop"><section class="modal widget-popup"><header><h2>Исходные access_rules</h2><button @click="closeChild">×</button></header><AdminPanel :project="project" :target="target" kind="security" :initial-key="matrix?.groups[0]?.key" @dirty="childDirty=$event" @changed="load();$emit('changed')"/></section></div><div v-if="userKey" class="modal-backdrop"><section class="modal widget-popup"><header><h2>Группы пользователя</h2><button @click="closeChild">×</button></header><UserGroups :project="project" :target="target" :initial-key="userKey" @dirty="childDirty=$event" @changed="load();$emit('changed')"/></section></div></Teleport>
</section>
</template>
