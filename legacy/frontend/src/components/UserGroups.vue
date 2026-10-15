<script>
import api from '../api.js';
export default {
 name:'UserGroups',props:['project','target','initialKey'],emits:['dirty','changed'],
 data(){return {users:[],key:this.initialKey||'',loadedKey:'',model:null,members:[],query:'',busy:false,error:'',message:'',seq:0}},
 computed:{dirty(){return this.model&&JSON.stringify([...this.members].sort())!==JSON.stringify([...this.model.members].sort())},groups(){const q=this.query.toLowerCase();return (this.model?.groups||[]).filter(g=>[g.name,g.title,g.project].some(v=>String(v||'').toLowerCase().includes(q)))}},
 watch:{dirty(v){this.$emit('dirty',!!v)}},async mounted(){if(this.key)await this.load(this.key);else try{this.users=(await api.request('/user-groups',{project:this.project,target:this.target})).users}catch(e){this.error=e.message}},beforeUnmount(){this.seq++},
 methods:{
 async change(){if(this.dirty&&!confirm('Отменить изменения групп пользователя?')){this.key=this.loadedKey;return}await this.load(this.key)},
 async load(key){if(!key){this.model=null;return}const seq=++this.seq;this.busy=true;this.error='';try{const m=await api.request('/user-groups',{project:this.project,target:this.target,key});if(seq!==this.seq)return;this.model=m;this.loadedKey=this.key=m.key;this.members=[...m.members]}catch(e){if(seq===this.seq)this.error=e.message}finally{if(seq===this.seq)this.busy=false}},
 async save(){if(this.busy||!this.dirty)return;this.busy=true;this.error='';try{const r=await api.request('/user-groups',{project:this.project,target:this.target,key:this.model.key,members:this.members,revision:this.model.revision},'PATCH');await this.load(this.model.key);this.message=r.notice;this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}}
 }
};
</script>
<template>
<section class="membership-panel"><div class="toolbar"><select v-if="!initialKey" v-model="key" @change="change" :disabled="busy" aria-label="Пользователь"><option value="">Выберите пользователя…</option><option v-for="u in users" :key="u.key" :value="u.key">{{u.label}} · {{u.login}}</option></select><b v-else>{{model?.login}}</b><input v-model="query" type="search" placeholder="Найти группу…"><span class="spacer"></span><button v-if="dirty" @click="members=[...model.members]" :disabled="busy">Отменить</button><button :disabled="busy||!dirty||!model?.can_write" class="primary" @click="save">Сохранить состав</button></div><p class="muted">Исходный GroupAssignCbk · sthpw/login_in_group. Существующее членство в admin защищено. Неотображаемые назначения не снимаются фильтром.</p><p v-if="error" class="error">{{error}}</p><p v-if="message" class="success">{{message}}</p><p v-if="model">{{members.length}} групп <span v-if="dirty">· Несохранённые изменения</span></p><div class="member-grid"><label v-for="g in groups" :key="g.name" class="member-row"><input type="checkbox" v-model="members" :value="g.name" :disabled="busy||!model.can_write||(g.name==='admin'&&model.members.includes('admin'))"><span><b>{{g.name}}</b><small>{{g.project||'Общая группа'}} · {{g.title}}</small></span></label></div></section>
</template>
