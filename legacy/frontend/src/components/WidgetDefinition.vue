<script>
import api from '../api.js';
export default {name:'WidgetDefinition',props:{project:String,target:String,field:String,formField:Boolean,recordKey:String},emits:['close'],data(){return {data:null,error:''}},async mounted(){try{this.data=await api.request('/open',{project:this.project,target:this.target});if(this.field){const form=this.formField?await api.request('/form',{project:this.project,target:this.target,key:this.recordKey}):null;const spec=form?.spec||this.data.spec;const f=spec?.fields?.find(f=>f.name===this.field);this.data={target:this.target,field:f||this.field,widget:this.formField?'EditWdg':this.data.handler,view:spec?.view||this.data.view}}}catch(e){this.error=e.message}}};
</script>
<template>
<Teleport to="body"><div class="modal-backdrop" @click.self="$emit('close')"><section class="modal widget-definition" role="dialog" aria-modal="true" aria-label="Определение виджета"><header><h2>Определение виджета</h2><button @click="$emit('close')" aria-label="Закрыть">×</button></header><p class="notice">Описание прочитано из исходной конфигурации. Неперенесённые обработчики не исполняются как HTML/JavaScript.</p><p v-if="error" class="error">{{error}}</p><pre v-else>{{data?JSON.stringify(data,null,2):'Загрузка…'}}</pre></section></div></Teleport>
</template>
