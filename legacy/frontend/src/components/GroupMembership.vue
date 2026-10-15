<script>
import api from '../api.js';
export default {
 name:'GroupMembership',props:['project','target','initialKey'],emits:['changed'],
 data(){return {groups:[],selected:'',group:null,members:[],query:'',busy:false,error:'',message:''}},
 computed:{users(){const q=this.query.toLowerCase();return (this.group?.users||[]).filter(u=>u.login.toLowerCase().includes(q)||u.name.toLowerCase().includes(q))},dirty(){return this.group&&JSON.stringify([...this.members].sort())!==JSON.stringify([...this.group.members].sort())}},
 async mounted(){try{this.groups=(await api.request('/memberships',{project:this.project,target:this.target})).items;if(this.initialKey){this.selected=this.initialKey;await this.load()}}catch(e){this.error=e.message}},
 methods:{
 async load(){this.error='';this.message='';this.group=null;this.busy=true;try{if(this.selected){this.group=await api.request('/memberships',{project:this.project,target:this.target,key:this.selected});this.members=[...this.group.members]}}catch(e){this.error=e.message}finally{this.busy=false}},
 async save(){this.error='';this.message='';this.busy=true;try{await api.request('/memberships',{project:this.project,target:this.target,key:this.group.key,members:this.members,revision:this.group.revision},'POST');await this.load();this.message='Состав группы сохранён через команду TACTIC';this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}}
 }
};
</script>
<template>
<section class="membership-panel"><div class="toolbar"><label>Группа<select v-model="selected" @change="load" :disabled="busy"><option value="">Выберите группу…</option><option v-for="g in groups" :key="g.key" :value="g.key">{{g.name}}</option></select></label><input v-model="query" placeholder="Найти пользователя"><span class="spacer"></span><button class="primary" :disabled="!group?.can_write||!dirty||busy" @click="save">Сохранить состав</button></div><p class="notice">Назначения хранятся в sthpw/login_in_group. Удаление существующих участников группы admin через этот экран запрещено.</p><p v-if="error" class="error">{{error}}</p><p v-if="message" class="success">{{message}}</p><template v-if="group"><p>{{members.length}} участников · {{group.users.length}} пользователей загружено<span v-if="dirty"> · Есть несохранённые изменения</span></p><div class="member-grid"><label v-for="u in users" :key="u.login" class="member-row"><input type="checkbox" v-model="members" :value="u.login" :disabled="busy||!group.can_write||(group.group==='admin'&&group.members.includes(u.login))"><span><b>{{u.name}}</b><code>{{u.login}}</code></span></label></div><p v-if="group.users.length>=group.limit" class="notice">Показан лимит {{group.limit}} пользователей. Неотображаемые участники сохраняются.</p></template></section>
</template>
