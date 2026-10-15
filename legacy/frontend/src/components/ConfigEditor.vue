<script>
import api from '../api.js';
export default {
 name:'ConfigEditor',props:{project:String,mode:String,initialView:String,allowWrites:Boolean},emits:['changed','dirty'],
 data(){return {items:[],key:'',record:null,xml:'',view:this.initialView||'project_view',effective:null,order:[],error:'',busy:false,changed:false,newMode:false,newType:'SideBarWdg',newView:'project_view',newLogin:''}},
 watch:{changed(v){this.$emit('dirty',v)}},
 async mounted(){await this.loadList();if(this.mode==='sidebar-editor')await this.loadEffective()},
 methods:{
 async run(fn){this.error='';this.busy=true;try{await fn()}catch(e){this.error=e.message}finally{this.busy=false}},
 async loadList(){await this.run(async()=>{this.items=(await api.request('/configs',{project:this.project,search_type:this.mode==='sidebar-editor'?'SideBarWdg':undefined})).items})},
 async load(){if(!this.key)return;await this.run(async()=>{this.record=await api.request('/config',{project:this.project,key:this.key});this.xml=this.record.xml;this.changed=false;this.newMode=false})},
 async loadEffective(){await this.run(async()=>{this.effective=await api.request('/config',{project:this.project,view:this.view});this.order=this.effective.elements.map((_,i)=>i)})},
 move(index,delta){const j=index+delta;if(j<0||j>=this.order.length)return;const a=[...this.order];[a[index],a[j]]=[a[j],a[index]];this.order=a},
 async saveOrder(){await this.run(async()=>{await api.request('/sidebar-order',{project:this.project,view:this.view,revision:this.effective.revision,order:this.order},'POST');await this.loadEffective();await this.loadList();this.$emit('changed')})},
 async save(){await this.run(async()=>{const res=await api.request('/config',{project:this.project,key:this.key,xml:this.xml,revision:this.record?.revision,view:this.newView,search_type:this.newType,login:this.newLogin},this.newMode?'POST':'PATCH');this.key=res.key;await this.loadList();await this.load();this.$emit('changed')})},
 create(){this.newMode=true;this.record=null;this.key='';this.xml='<config>\n  <project_view>\n    <element name="project_admin"/>\n  </project_view>\n</config>';this.changed=true}
 }
};
</script>
<template>
<section class="config-workbench" aria-label="Widget Config">
 <p v-if="error" class="error">{{error}}</p>
 <div v-if="mode==='sidebar-editor'" class="effective-editor">
  <div class="toolbar"><label>View <input v-model="view" @keyup.enter="loadEffective"></label><button @click="loadEffective" :disabled="busy">Разрешить конфигурацию</button><button class="primary" :disabled="busy||!effective||!allowWrites" @click="saveOrder">Сохранить порядок в TACTIC</button></div>
  <div v-if="effective" class="config-columns"><ol class="element-list"><li v-for="(index,pos) in order" :key="index"><span><b>{{effective.elements[index].title}}</b><small>{{effective.elements[index].name}} · {{effective.elements[index].handler||'default'}}</small></span><button :disabled="pos===0" @click="move(pos,-1)" aria-label="Вверх">↑</button><button :disabled="pos===order.length-1" @click="move(pos,1)" aria-label="Вниз">↓</button></li></ol><div class="layers"><h3>Слои разрешения · по приоритету</h3><details v-for="(layer,i) in effective.layers" :key="i"><summary>{{i+1}}. {{layer.view}} · {{layer.origin}}</summary><pre>{{layer.xml}}</pre></details></div></div>
 </div>
 <hr><div class="toolbar"><select v-model="key" @change="load"><option value="">Запись из базы…</option><option v-for="row in items" :key="row.key" :value="row.key">{{row.search_type}} / {{row.view}} {{row.login?'· '+row.login:''}}</option></select><button @click="loadList">Обновить</button><button :disabled="!allowWrites" @click="create">Новый widget_config</button></div>
 <p v-if="!items.length" class="muted">В базе нет подходящих переопределений. Sidebar продолжает наследоваться из штатных XML.</p>
 <div v-if="newMode" class="toolbar"><label>Search type<input v-model="newType"></label><label>View<input v-model="newView"></label><label>Login (пусто — общий)<input v-model="newLogin"></label></div>
 <div v-if="record||newMode" class="xml-editor"><div class="toolbar"><code>{{record?.search_type||newType}} / {{record?.view||newView}}</code><span class="spacer"></span><button class="primary" :disabled="busy||!changed||!allowWrites" @click="save">Сохранить XML</button></div><textarea spellcheck="false" v-model="xml" @input="changed=true" :readonly="!allowWrites" aria-label="Исходный XML widget_config"></textarea><p class="muted">Изменения конфигурации влияют на действующий проект. Неизвестные атрибуты и соседние views не удаляются автоматически.</p></div>
</section>
</template>
