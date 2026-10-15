<script>
import api from '../api.js';
export default {
 name:'RelationshipEditor',props:{project:String,target:String,record:Object,relatedType:String},emits:['close','changed'],
 data(){return {data:null,descriptor:null,error:'',busy:false,keyword:'',offset:0,epoch:0}},
 mounted(){this.load()},beforeUnmount(){this.epoch++},
 methods:{args(){return {project:this.project,target:this.target,key:this.record.key,related_type:this.relatedType}},
 async load(){const seq=++this.epoch;this.busy=true;this.error='';try{const d=await api.request('/relationship',this.args());const rows=await api.request('/relation-candidates',{...this.args(),keyword:this.keyword,offset:this.offset,limit:30},'POST');if(seq===this.epoch){this.descriptor=d;this.data=rows}}catch(e){if(seq===this.epoch)this.error=e.message}finally{if(seq===this.epoch)this.busy=false}},
 title(row){const v=row.values;return v.name||v.title||v.code||v.description||row.key},
 search(){this.offset=0;this.load()},page(n){this.offset=n;this.load()},
 async change(row){if(!this.data.can_write||this.busy)return;if(row.linked&&!confirm('Удалить '+row.links+' записей связи? Сам объект не удаляется; настроенные серверные триггеры выполняются.'))return;this.busy=true;this.error='';try{await api.request('/relationship',{...this.args(),other_key:row.key,other_revision:row.revision,revision:this.data.revision,confirm_count:row.links},row.linked?'DELETE':'POST');await this.load();this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}}
 }
};
</script>
<template>
<Teleport to="body"><div class="modal-backdrop" @click.self="$emit('close')"><section class="modal relation-editor" role="dialog" aria-modal="true"><header><div><small>INSTANCE RELATIONSHIP</small><h2>{{relatedType}}</h2></div><button @click="$emit('close')">×</button></header><p class="notice">{{descriptor?.notice||'Связь разрешается исходной Schema'}}<br><code>{{descriptor?.instance_type}}</code></p><form class="toolbar" @submit.prevent="search"><input v-model="keyword" placeholder="Найти связанный объект"><button :disabled="busy">Найти</button><button type="button" :disabled="busy" @click="load">Обновить</button></form><p v-if="error" class="error">{{error}}</p><div class="relation-candidates"><article v-for="row in data?.items||[]" :key="row.key"><div><b>{{title(row)}}</b><code>{{row.key}}</code></div><span class="spacer"></span><small v-if="row.linked">Связей: {{row.links}}</small><button :disabled="busy||!data.can_write" :class="{primary:!row.linked}" @click="change(row)">{{row.linked?'Отвязать':'Связать'}}</button></article></div><footer><button :disabled="busy||offset===0" @click="page(Math.max(0,offset-30))">←</button><span>{{offset+1}}–{{offset+(data?.items.length||0)}} / {{data?.total??'—'}}</span><button :disabled="busy||offset+(data?.items.length||0)>=data?.total" @click="page(offset+30)">→</button></footer><small>Удаление связи вызывает SObject.remove_instance. Существующие атрибуты других связей сохраняются.</small></section></div></Teleport>
</template>
