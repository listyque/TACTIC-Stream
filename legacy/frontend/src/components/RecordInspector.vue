<script>
import api from '../api.js';
import FilePanel from './FilePanel.vue';
import TaskPanel from './TaskPanel.vue';
import SubscriptionPanel from './SubscriptionPanel.vue';
import HistoryPanel from './HistoryPanel.vue';
import RelationshipEditor from './RelationshipEditor.vue';
export default {
 name:'RecordInspector',components:{FilePanel,TaskPanel,HistoryPanel,RelationshipEditor,SubscriptionPanel},props:{project:String,target:String,record:Object,spec:Object,allowUploads:Boolean},emits:['close','edit','open','changed','messages'],
 data(){return {section:['files','history','subscription'].includes(this.record._section)?this.record._section:'fields',relations:[],notes:[],error:'',busy:false,comment:'',process:'publish',canNote:false,editingRelation:null}},
 methods:{
 args(){return {project:this.project,target:this.target,key:this.record.key}},
 files(){this.section='files';this.error=''},
 async related(){this.section='relations';this.error='';try{this.relations=(await api.request('/relations',this.args())).items}catch(e){this.error=e.message}},
 async discussion(){this.section='notes';this.error='';try{const d=await api.request('/notes',this.args());this.notes=d.items;this.canNote=d.can_write}catch(e){this.error=e.message}},
 async addNote(){this.busy=true;this.error='';try{await api.request('/notes',{...this.args(),note:this.comment,process:this.process},'POST');this.comment='';await this.discussion()}catch(e){this.error=e.message}finally{this.busy=false}},
 show(value){if(value===null||value===undefined)return '—';return typeof value==='object'?JSON.stringify(value,null,2):String(value)}
 }
};
</script>
<template>
<aside class="inspector"><header><h2>Запись TACTIC</h2><button @click="$emit('close')" aria-label="Закрыть">×</button></header><code class="search-key">{{record.key}}</code><div class="toolbar"><button :class="{primary:section==='fields'}" @click="section='fields'">Поля</button><button :class="{primary:section==='files'}" @click="files">Файлы</button><button :class="{primary:section==='relations'}" @click="related">Связи</button><button :class="{primary:section==='notes'}" @click="discussion">Обсуждение</button><button :class="{primary:section==='tasks'}" @click="section='tasks'">Задачи</button><button :class="{primary:section==='history'}" @click="section='history'">История</button><button :class="{primary:section==='subscription'}" @click="section='subscription'">Подписка</button><button :disabled="!spec.capabilities.update" @click="$emit('edit',record)">Изменить</button></div><p v-if="error" class="error">{{error}}</p>
<dl v-if="section==='fields'"><template v-for="f in spec.fields" :key="f.name"><dt>{{f.label}}</dt><dd>{{show(record.values[f.name])}}</dd></template></dl>
<FilePanel v-else-if="section==='files'" :key="record.key" :project="project" :target="target" :record-key="record.key" @changed="$emit('changed')"/>
<div v-else-if="section==='relations'"><p class="notice">Связи разрешены исходной Schema, включая instance-таблицы.</p><article v-for="r in relations" :key="r.search_type" class="relation-row"><button :disabled="!r.target" @click="$emit('open',{id:r.target})">{{r.search_type}} · {{r.count??'—'}}</button><small>{{r.relationship}} {{r.error}}</small><button v-if="r.relationship==='instance'" @click="editingRelation=r.search_type">Изменить связи</button></article><p v-if="!relations.length" class="muted">Нет объявленных связей.</p></div>
<div v-else-if="section==='notes'"><form v-if="canNote" @submit.prevent="addNote"><label>Процесс<input v-model="process"></label><textarea v-model="comment" rows="4" placeholder="Комментарий к объекту"></textarea><button class="primary" :disabled="busy||!comment.trim()">Отправить</button></form><article v-for="n in notes" :key="n.key" class="note"><header><b>{{n.login}}</b><small>{{n.timestamp}}</small></header><small>{{n.process}} · {{n.access}}</small><p>{{n.note}}</p></article><p v-if="!notes.length" class="muted">Комментариев пока нет.</p></div>
<SubscriptionPanel v-else-if="section==='subscription'" :project="project" :target="target" :record="record" @messages="$emit('messages',$event)"/><TaskPanel v-else-if="section==='tasks'" :project="project" :target="target" :record="record" @changed="$emit('changed')"/><HistoryPanel v-else-if="section==='history'" :project="project" :target="target" :record="record" @changed="$emit('changed')"/><RelationshipEditor v-if="editingRelation" :project="project" :target="target" :record="record" :related-type="editingRelation" @close="editingRelation=null" @changed="related();$emit('changed')"/>
</aside>
</template>
