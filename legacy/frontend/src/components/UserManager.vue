<script>
import api from '../api.js';
export default {
 name:'UserManager',props:['project','target','user','screen','mode'],emits:['dirty','changed','open'],
 data(){return {section:'users',table:null,child:null,error:'',busy:false,dirty:false,seq:0}},
 computed:{standalone(){return this.mode==='groups'||this.screen?.handler?.endsWith('UserPanelWdg')}},
 mounted(){this.select(this.mode==='groups'?'groups':'users')},beforeUnmount(){this.seq++},
 methods:{mark(v){this.dirty=v;this.$emit('dirty',v)},async select(section){if(this.dirty&&!confirm('Отменить несохранённые изменения?'))return;const seq=++this.seq;this.busy=true;this.error='';const part=section==='users'?'users-table':section==='groups'?'groups-table':section==='assignment'?'assignment':'security';try{const s=await api.request('/open',{project:this.project,target:this.target+'/~admin/'+part});if(seq!==this.seq)return;this.section=section;if(s.kind==='table')this.table=s;else this.child=s;this.mark(false)}catch(e){if(seq===this.seq)this.error=e.message}finally{if(seq===this.seq)this.busy=false}}}
};
</script>
<template>
<section class="user-manager"><nav v-if="!standalone" class="admin-section-tabs" aria-label="Manage Users"><button :aria-selected="section==='users'" @click="select('users')">Users</button><button :aria-selected="section==='assignment'" @click="select('assignment')">Group Assignment</button><button :aria-selected="section==='security'" @click="select('security')">Group Security</button></nav><p v-if="error" class="error">{{error}}</p><p v-if="busy" class="muted">Загрузка исходного виджета…</p><WidgetTable v-if="['users','groups'].includes(section)&&table" :key="table.id" :project="project" :screen="table" :user="user" @open="$emit('open',$event)" @dirty="mark" @changed="$emit('changed')"/><SecurityMatrix v-else-if="child" :key="child.id" :project="project" :target="child.id" :screen="child" :user="user" @open="$emit('open',$event)" @dirty="mark" @changed="$emit('changed')"/></section>
</template>
