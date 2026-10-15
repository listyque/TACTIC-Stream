<script>
import SidebarEditor from './SidebarEditor.vue';
import UserManager from './UserManager.vue';
import UserGroups from './UserGroups.vue';
import SecurityMatrix from './SecurityMatrix.vue';
import api from '../api.js';
import GlobalSettings from './GlobalSettings.vue';
import ConfiguredTabs from './ConfiguredTabs.vue';
import EmbeddedForm from './EmbeddedForm.vue';
import WidgetTable from './WidgetTable.vue';
import GraphEditor from './GraphEditor.vue';
import ScriptEditor from './ScriptEditor.vue';
import ConfigEditor from './ConfigEditor.vue';
import SearchTypes from './SearchTypes.vue';
import GroupMembership from './GroupMembership.vue';
import AdminPanel from './AdminPanel.vue';
import MessageCenter from './MessageCenter.vue';
import CollectionPanel from './CollectionPanel.vue';
import WidgetDefinition from './WidgetDefinition.vue';
export default {
 name:'WidgetHost',components:{SecurityMatrix,UserGroups,UserManager,SidebarEditor,GlobalSettings,ConfiguredTabs,EmbeddedForm,WidgetTable,GraphEditor,ScriptEditor,ConfigEditor,SearchTypes,GroupMembership,AdminPanel,MessageCenter,CollectionPanel,WidgetDefinition},
 props:{project:String,target:String,user:Object,active:{type:Boolean,default:true},initial:Object,refreshKey:Number},emits:['open','dirty','close','changed'],
 data(){return {screen:this.initial||null,error:'',busy:false,seq:0,definition:false,menu:null,menuSeq:0,dirty:false}},mounted(){if(!this.screen)this.load()},beforeUnmount(){this.seq++;this.menuSeq++},watch:{target(){this.load()},refreshKey(){this.load()}},
 methods:{
 async context(e){if(!this.screen||e.shiftKey||e.defaultPrevented||e.target.closest('input,textarea,select,[contenteditable=true]'))return;e.preventDefault();e.stopPropagation();const seq=++this.menuSeq;this.menu={x:e.clientX,y:e.clientY,title:this.screen.title,loading:true,items:[]};try{const d=await api.request('/context-menu',{project:this.project,target:this.target,scope:'widget'});if(this.menu&&seq===this.menuSeq)this.menu={...this.menu,...d,loading:false}}catch(err){if(this.menu&&seq===this.menuSeq)this.menu={...this.menu,loading:false,error:err.message}}},
 action(item){this.menu=null;this.menuSeq++;if(item.id==='definition')this.definition=true;else if(item.id==='refresh'){if(this.dirty&&!confirm('Обновить виджет и отменить правки?'))return;this.screen=null;this.$emit('dirty',false);this.load()}},
 mark(value){this.dirty=value;this.$emit('dirty',value)},
 async load(){const seq=++this.seq;this.busy=true;this.error='';try{const d=await api.request('/open',{project:this.project,target:this.target});if(seq===this.seq)this.screen=d}catch(e){if(seq===this.seq)this.error=e.message}finally{if(seq===this.seq)this.busy=false}}}
};
</script>
<template>
<div class="widget-host" @contextmenu="context"><p v-if="error" class="error">{{error}}</p><p v-if="busy&&!screen" class="muted">Загрузка виджета…</p><template v-if="screen">
 <ConfiguredTabs v-if="screen.kind==='tabs'" :project="project" :screen="screen" :user="user" :active="active" :refresh-key="refreshKey" @open="$emit('open',$event)" @dirty="mark" @changed="$emit('changed',$event)"/>
 <EmbeddedForm v-else-if="screen.kind==='form'" :project="project" :target="screen.id" :refresh-key="refreshKey" @close="$emit('close')" @dirty="mark" @changed="$emit('changed',$event)"/>
 <WidgetTable @refresh="load" v-else-if="screen.kind==='table'" :project="project" :screen="screen" :user="user" :refresh-key="refreshKey" @open="$emit('open',$event)" @dirty="mark" @changed="$emit('changed',$event)"/>
 <GraphEditor :key="project+screen.id+':'+(refreshKey||0)" v-else-if="['pipeline','schema'].includes(screen.kind)" :project="project" :kind="screen.kind" :target="screen.id" @dirty="mark"/>
 <GlobalSettings v-else-if="['system-config','license'].includes(screen.kind)" :project="project" :target="screen.id" :kind="screen.kind" @dirty="mark"/>
 <ScriptEditor v-else-if="screen.kind==='script-editor'" :project="project" :target="screen.id" @dirty="mark" @open="$emit('open',$event)"/>
 <SidebarEditor v-else-if="screen.kind==='sidebar-editor'" :project="project" :target="screen.id" :initial-view="screen.options?.view||(project==='admin'?'admin_views':'project_view')" :user="user" :allow-writes="user.allow_writes" @dirty="mark" @changed="$emit('changed',$event)"/>
 <CustomLayoutEditor v-else-if="screen.kind==='layout-editor'" :key="project+screen.id" :project="project" :target="screen.id" :user="user" @dirty="mark" @open="$emit('open',$event)" @changed="$emit('changed',$event)"/>
 <ManageViews v-else-if="screen.kind==='views-manager'" :key="project+screen.id" :project="project" :target="screen.id" :screen="screen" :user="user" @dirty="mark" @open="$emit('open',$event)" @changed="$emit('changed',$event)"/>
 <LayoutPreview v-else-if="screen.kind==='custom-layout'" :key="project+screen.id" :parts="screen.layout.parts" :children="screen.layout.children" :project="project" :user="user" @dirty="mark" @open="$emit('open',$event)" @changed="$emit('changed',$event)"/>
 <ConfigEditor v-else-if="screen.kind==='config-editor'" :project="project" :mode="screen.kind" :initial-view="screen.options?.view||(project==='admin'?'admin_views':'project_view')" :allow-writes="user.allow_writes" @changed="$emit('changed',$event)"/>
 <SearchTypes v-else-if="screen.kind==='search-types'" :project="project" :target="screen.id" :screen="screen" :user="user" @dirty="mark" :allow-writes="user.allow_writes" @open="$emit('open',$event)" @changed="$emit('changed',$event)"/>
 <GroupMembership :initial-key="screen.options?.search_key" v-else-if="screen.kind==='group-membership'" :project="project" :target="screen.id" @changed="$emit('changed',$event)"/>
 <UserManager v-else-if="['users','groups'].includes(screen.kind)" :project="project" :target="screen.id" :screen="screen" :mode="screen.kind" :user="user" @dirty="mark" @changed="$emit('changed',$event)" @open="$emit('open',$event)"/>
 <UserGroups v-else-if="screen.kind==='group-assignment'&&screen.handler.endsWith('GroupAssignWdg')" :project="project" :target="screen.id" :initial-key="screen.options?.search_key" @dirty="mark" @changed="$emit('changed',$event)"/>
 <SecurityMatrix v-else-if="['security','group-assignment'].includes(screen.kind)" :project="project" :target="screen.id" :screen="screen" :user="user" @dirty="mark" @changed="$emit('changed',$event)" @open="$emit('open',$event)"/>
 <AdminPanel :initial-key="screen.options?.search_key" v-else-if="['project-create','system'].includes(screen.kind)" :project="project" :target="screen.id" :kind="screen.kind" @dirty="mark" @changed="$emit('changed',$event)"/>
 <MessageCenter v-else-if="screen.kind==='message-center'" :project="project" :target="screen.id" :options="screen.options" :login="user.login" :active="active" @close="$emit('close')"/>
 <CollectionPanel v-else-if="screen.kind==='collections'" :project="project" :target="screen.id" @changed="$emit('changed',$event)" @open="$emit('open',$event)"/>
 <section v-else class="unsupported-panel"><h3>{{screen.title}}</h3><p>Обработчик присутствует в исходной конфигурации, но ещё не перенесён. Он не заменён таблицей.</p><code>{{screen.handler}}</code><button @click="definition=true">Определение виджета</button></section>
 <ContextMenu v-if="menu" :menu="menu" @action="action" @close="menu=null;menuSeq++"/><WidgetDefinition v-if="definition" :project="project" :target="screen.id" @close="definition=false"/>
</template></div>
</template>
