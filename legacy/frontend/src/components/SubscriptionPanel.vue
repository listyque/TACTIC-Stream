<script>
import api from '../api.js';
export default {
 name:'SubscriptionPanel',props:{project:String,target:String,record:Object},emits:['messages'],
 data(){return {state:null,error:'',busy:false}},mounted(){this.load()},
 methods:{args(){return {project:this.project,target:this.target,key:this.record.key}},async load(){this.error='';try{this.state=await api.request('/record-subscription',this.args())}catch(e){this.error=e.message}},async change(){if(!this.state)return;if(this.state.subscribed&&!confirm('Отписаться от событий объекта? История останется в TACTIC.'))return;this.busy=true;this.error='';try{await api.request('/record-subscription',{...this.args(),revision:this.state.revision,...(this.state.subscribed?{confirm:'UNSUBSCRIBE'}:{})},this.state.subscribed?'DELETE':'POST');await this.load()}catch(e){this.error=e.message}finally{this.busy=false}}}
};
</script>
<template>
<section class="subscription-panel"><h3>События объекта</h3><p v-if="error" class="error">{{error}}</p><template v-if="state"><code>{{state.message_code}}</code><p class="notice">{{state.notice}}</p><p>{{state.subscribed?'Вы подписаны на изменения.':'Подписки пока нет.'}}</p><div class="toolbar"><button :disabled="!state.can_write||busy" @click="change">{{state.subscribed?'Отписаться от объекта':'Подписаться на объект'}}</button><button v-if="state.subscribed" @click="$emit('messages',state.message_code)">Открыть события</button><button @click="load" :disabled="busy">Обновить</button></div></template></section>
</template>
