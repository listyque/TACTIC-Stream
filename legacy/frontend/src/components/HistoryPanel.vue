<script>
import api from '../api.js';
export default {
 name:'HistoryPanel',props:{project:String,target:String,record:Object},emits:['changed'],
 data(){return {state:null,data:null,error:'',busy:false,source:'changes',offset:0}},
 mounted(){this.load()},
 methods:{args(){return {project:this.project,target:this.target,key:this.record.key}},
 async load(){this.busy=true;this.error='';try{this.state=await api.request('/record-state',this.args());this.data=await api.request('/history',{...this.args(),source:this.source,offset:this.offset,limit:50})}catch(e){this.error=e.message}finally{this.busy=false}},
 sourceChanged(){this.offset=0;this.load()},page(n){this.offset=n;this.load()},
 async stateChange(){if(!this.state?.can_write||this.busy)return;const action=this.state.retired?'reactivate':'retire';if(!confirm(this.state.retired?'Восстановить запись из архива?':'Архивировать запись штатным SObject.retire? Физическое удаление не выполняется.'))return;this.busy=true;this.error='';try{await api.request('/record-state',{...this.args(),revision:this.state.revision,action,confirm:action.toUpperCase()},'POST');await this.load();this.$emit('changed')}catch(e){this.error=e.message}finally{this.busy=false}}
 }
};
</script>
<template>
<section class="history-panel"><div class="toolbar"><select v-model="source" @change="sourceChanged" aria-label="Вид истории"><option value="changes">Изменения объекта</option><option value="status">История статусов</option><option value="retire">Архивирование</option></select><button :disabled="busy" @click="load">Обновить</button></div><div v-if="state" class="toolbar"><span>{{state.retired?'Запись архивирована':'Активная запись'}}</span><button v-if="state.can_write" :disabled="busy" @click="stateChange">{{state.retired?'Восстановить из архива':'Архивировать'}}</button></div><p v-if="error" class="error">{{error}}</p><p v-if="data?.notice" class="notice">{{data.notice}}</p><article v-for="item in data?.items||[]" :key="item.key" class="history-event"><header><b>{{item.values?.login||item.login||'—'}}</b><small>{{item.values?.timestamp||item.timestamp}}</small></header><dl><template v-for="(v,k) in (item.values||item)" :key="k"><template v-if="!['login','timestamp','key'].includes(k)"><dt>{{k}}</dt><dd>{{v??'—'}}</dd></template></template></dl></article><p v-if="data&&!data.items.length" class="muted">Записей этого вида истории нет.</p><footer class="toolbar"><button :disabled="busy||offset===0" @click="page(Math.max(0,offset-50))">←</button><span>{{data?.total??'—'}} событий</span><button :disabled="busy||offset+(data?.items.length||0)>=data?.total" @click="page(offset+50)">→</button></footer><small>Исходные status_log / sobject_log / retire_log, не отдельный журнал нового интерфейса.</small></section>
</template>
