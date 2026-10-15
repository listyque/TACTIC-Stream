<script>
import api from '../api.js';
import ConfiguredForm from './ConfiguredForm.vue';
export default {
 name:'EmbeddedForm',components:{ConfiguredForm},props:{project:String,target:String,refreshKey:Number},emits:['close','dirty','changed'],
 data(){return {form:null,busy:false,error:'',success:'',generation:0,formKey:0,dirty:false,previewBusy:false,previewFailed:false}},
 mounted(){this.load()},beforeUnmount(){this.generation++},watch:{refreshKey(){if(!this.dirty||confirm('Обновить форму и отменить правки?'))this.load()}},
 methods:{
 async load(){const seq=++this.generation;this.busy=true;this.error='';try{const d=await api.request('/embedded-form',{project:this.project,target:this.target});if(seq===this.generation){this.form=d;this.formKey++;this.dirty=false;this.$emit('dirty',false)}}catch(e){if(seq===this.generation)this.error=e.message}finally{if(seq===this.generation)this.busy=false}},
 async save(values){if(this.busy||this.previewBusy||this.previewFailed)return;this.busy=true;this.error='';try{const result=await api.request('/embedded-form',{project:this.project,target:this.target,key:this.form.record?.key,revision:this.form.record?.revision,values},this.form.record?'PATCH':'POST');this.success='Сохранено: '+result.key;this.dirty=false;this.$emit('dirty',false);this.$emit('changed',result);if(this.form.widget?.single&&!this.form.record)this.$emit('close');else await this.load()}catch(e){this.error=e.message}finally{this.busy=false}},
 async preview(values){const seq=++this.generation;this.previewBusy=true;this.previewFailed=false;this.error='';try{const d=await api.request('/form-preview',{project:this.project,target:this.target,key:this.form.record?.key,revision:this.form.record?.revision,values},'POST');if(seq===this.generation)this.form={...d,widget:this.form.widget}}catch(e){if(seq===this.generation){this.error=e.message;this.previewFailed=true}}finally{if(seq===this.generation)this.previewBusy=false}},
 mark(value){this.dirty=value;this.$emit('dirty',value)}
 }
};
</script>
<template>
<section class="embedded-widget"><p v-if="success" class="notice">{{success}}</p><p v-if="!form&&busy" class="muted">Загрузка EditWdg…</p><p v-if="!form&&error" class="error">{{error}}</p><ConfiguredForm v-if="form" :key="formKey" :project="project" :target="target" :form="form" :busy="busy||previewBusy||previewFailed" :error="error" embedded @dirty="mark" @preview="preview" @save="save" @close="$emit('close')"/></section>
</template>
