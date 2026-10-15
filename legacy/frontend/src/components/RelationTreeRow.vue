<script>
import api from '../api.js';
export default {
 name:'RelationTreeRow',props:{project:String,target:String,row:Object,spec:Object,ancestry:{type:Array,default:()=>[]},depth:{type:Number,default:0}},emits:['inspect','open'],
 data(){return {expanded:false,loaded:false,busy:false,error:'',relations:[],epoch:0}},
 computed:{cycle(){return this.ancestry.includes(this.row.key)},title(){const v=this.row.values;return v.name||v.title||v.code||v.description||this.row.key}},
 beforeUnmount(){this.epoch++},
 methods:{async expand(){this.expanded=!this.expanded;if(!this.expanded||this.loaded||this.cycle||this.depth>=7)return;const seq=++this.epoch;this.busy=true;this.error='';try{const d=await api.request('/relations',{project:this.project,target:this.target,key:this.row.key});if(seq===this.epoch){this.relations=d.items.map(r=>({...r,expanded:false,items:[],loaded:false,busy:false,error:r.error||'',offset:0,has_more:false,screen:null}));this.loaded=true}}catch(e){if(seq===this.epoch)this.error=e.message}finally{if(seq===this.epoch)this.busy=false}},
 async branch(r){r.expanded=!r.expanded;if(r.expanded&&!r.loaded)await this.more(r)},
 async more(r){if(r.busy||!r.target)return;r.busy=true;r.error='';const seq=this.epoch;try{if(!r.screen)r.screen=await api.request('/open',{project:this.project,target:r.target});const d=await api.request('/query',{project:this.project,target:r.target,offset:r.offset,limit:30,filters:[]},'POST');if(seq===this.epoch){r.items.push(...d.items);r.offset+=d.items.length;r.has_more=d.has_more;r.count=d.total;r.loaded=true}}catch(e){r.error=e.message}finally{r.busy=false}}
 }
};
</script>
<template>
<li class="relation-tree-row"><div class="tree-record"><button :disabled="cycle||depth>=7" :aria-expanded="expanded" @click="expand" :title="cycle?'Объект уже встречался в этой ветке':depth>=7?'Достигнут предел глубины':'Раскрыть связи'">{{expanded?'−':'+'}}</button><button class="text-button" @click="$emit('inspect',{target,row})">{{title}}</button><code>{{spec.type}}</code><small v-if="cycle">↩ цикл</small><small v-if="depth>=7">предел глубины</small></div>
 <div v-if="expanded" class="tree-children"><p v-if="busy" class="muted">Чтение связей…</p><p v-if="error" class="error">{{error}}</p><ul role="group"><li v-for="r in relations" :key="r.search_type" class="tree-relation"><div class="toolbar"><button :disabled="!r.target" :aria-expanded="r.expanded" @click="branch(r)">{{r.expanded?'▾':'▸'}} {{r.search_type}} · {{r.count??'—'}}</button><small>{{r.relationship}}</small><button v-if="r.target" class="text-button" @click="$emit('open',{id:r.target})">Открыть таблицу</button></div><p v-if="r.error" class="error">{{r.error}}</p><template v-if="r.expanded"><ul role="group"><RelationTreeRow v-for="child in r.items" :key="child.key" :project="project" :target="r.target" :row="child" :spec="r.screen.spec" :depth="depth+1" :ancestry="[...ancestry,row.key]" @inspect="$emit('inspect',$event)" @open="$emit('open',$event)"/></ul><button v-if="r.has_more||r.busy" :disabled="r.busy" @click="more(r)">{{r.busy?'Загрузка…':'Ещё 30'}}</button><small v-if="r.loaded&&!r.items.length">Нет связанных записей</small></template></li></ul><small v-if="loaded&&!relations.length">Нет объявленных связей Schema</small></div>
</li>
</template>
