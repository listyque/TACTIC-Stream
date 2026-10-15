<script>
import api from '../api.js';
import FieldInput from './FieldInput.vue';
import ContextMenu from './ContextMenu.vue';
import WidgetDefinition from './WidgetDefinition.vue';
export default {
 name:'ConfiguredForm',components:{FieldInput,ContextMenu,WidgetDefinition},
 props:{form:Object,busy:Boolean,error:String,embedded:Boolean,project:String,target:String},emits:['save','close','preview','dirty'],
 data(){return {values:{...(this.form.defaults||{}),...(this.form.record?.values||{})},dirty:{},menu:null,menuSequence:0,definition:null,submitting:false}},
 computed:{readOnly(){return this.form.widget?.mode==='view'||(!this.form.spec.capabilities?.create&&!this.form.spec.capabilities?.update)},hasChanges(){return Object.keys(this.dirty).length>0},titleId(){return 'form-title-'+this.$.uid}},
 watch:{busy(value){if(!value)this.submitting=false},form(){this.submitting=false}},
 beforeUnmount(){this.menuSequence++;this.$emit('dirty',false)},
 methods:{
  change(name,value){this.values[name]=value;const original=this.form.record?.values?.[name]??this.form.defaults?.[name];if(JSON.stringify(original)===JSON.stringify(value))delete this.dirty[name];else this.dirty[name]=value;this.$emit('dirty',this.hasChanges);if(this.form.record&&this.form.spec.fields.find(f=>f.name===name)?.choice_refresh){const v={};for(const f of this.form.spec.fields)if(f.choice_refresh&&Object.hasOwn(this.dirty,f.name))v[f.name]=this.dirty[f.name];this.$emit('preview',v)}},
  save(){if(this.busy||this.submitting||this.readOnly)return;api.action?.('form.save',{project:this.project,target:this.target,count:Object.keys(this.dirty).length});this.submitting=true;this.$emit('save',this.form.record?{...this.dirty}:{...(this.form.defaults||{}),...this.dirty});this.$nextTick(()=>{if(!this.busy)this.submitting=false})},
  close(){if(this.hasChanges&&!confirm('Закрыть форму без сохранения?'))return;api.action?.('form.cancel',{project:this.project,target:this.target});this.$emit('close')},
  hotkey(e){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();if(this.form.widget?.show_action!==false)this.save()}},
  async context(e,f){if(e.shiftKey||!this.project||!this.target)return;e.preventDefault();e.stopPropagation();const seq=++this.menuSequence;const r=e.currentTarget.getBoundingClientRect();this.menu={x:e.clientX||r.left,y:e.clientY||r.bottom,title:f.label,loading:true,items:[],field:f};try{const d=await api.request('/context-menu',{project:this.project,target:this.target,scope:'form-field',field:f.name,key:this.form.record?.key});if(seq===this.menuSequence&&this.menu)this.menu={...this.menu,...d,loading:false}}catch(error){if(seq===this.menuSequence&&this.menu)this.menu={...this.menu,loading:false,error:error.message}}},
  fieldMenu(e,f){if(e.key==='ContextMenu'||(e.shiftKey&&e.key==='F10')){e.preventDefault();this.context({preventDefault(){},stopPropagation(){},currentTarget:e.currentTarget,clientX:0,clientY:0},f)}},
  menuAction(item){const f=this.menu.field;if(item.id==='definition')this.definition=f.name;else if(item.id==='reset_field')this.change(f.name,this.form.record?.values?.[f.name]??this.form.defaults?.[f.name]);else if(item.id==='null_field')this.change(f.name,null);this.menu=null;this.menuSequence++}
 }
};
</script>
<template>
<div :class="embedded?'embedded-form-frame':'modal-backdrop'" @click.self="!embedded&&close()"><section :class="embedded?'embedded-form':'modal'" :role="embedded?'region':'dialog'" :aria-modal="embedded?undefined:true" :aria-labelledby="form.widget?.show_header!==false?titleId:undefined" :aria-label="form.widget?.show_header===false?(form.widget?.title||'Форма записи TACTIC'):undefined" @keydown="hotkey">
 <header v-if="form.widget?.show_header!==false" :class="{'visually-hidden':embedded}"><div><small>{{form.spec.type}} · {{form.spec.view}}</small><h2 :id="titleId">{{form.widget?.title||(form.bulk?'Изменить '+form.records.length+' записей':form.record?'Редактирование записи':'Новая запись')}}</h2></div><button v-if="!embedded" aria-label="Закрыть" @click="close">×</button></header>
 <p v-if="form.spec.write_notice" class="notice">{{form.spec.write_notice}}</p><p v-if="form.dependency_notice" class="notice">{{form.dependency_notice}}</p><p v-if="error" class="error">{{error}}</p>
 <form @submit.prevent="save"><div class="form-scroll"><div v-for="f in form.spec.fields.filter(f=>!f.hidden)" :key="f.name" :class="f.kind==='heading'?'form-section-title':'form-row'"><h3 v-if="f.kind==='heading'">{{f.label}}</h3><template v-else><label tabindex="0" @contextmenu="context($event,f)" @keydown="fieldMenu($event,f)">{{f.label}}<small>{{f.name}}</small></label><div><FieldInput :field="f" :model-value="values[f.name]" @update:model-value="change(f.name,$event)"/><button v-if="f.nullable&&!f.read_only&&!readOnly" class="null-button" type="button" @click="change(f.name,null)">Установить NULL</button></div></template></div></div>
 <footer v-if="form.widget?.show_action!==false"><span>Поля и actions из widget_config</span><button type="button" @click="close">{{embedded?'Закрыть':'Отмена'}}</button><button v-if="!readOnly" type="submit" class="primary" :disabled="busy||submitting||(!hasChanges&&!(!form.record&&Object.keys(form.defaults||{}).length))">{{busy?'Сохранение…':'Сохранить'}}</button></footer></form>
 <ContextMenu v-if="menu" :menu="menu" @action="menuAction" @close="menu=null;menuSequence++"/><WidgetDefinition v-if="definition" :project="project" :target="target" :field="definition" form-field :record-key="form.record?.key" @close="definition=null"/>
</section></div>
</template>
