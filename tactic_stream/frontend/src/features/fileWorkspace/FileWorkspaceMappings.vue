<script>
import { t } from '../../i18n.js'
import AppTextField from '../../controls/AppTextField.vue'
import CodeEditor from '../../controls/CodeEditor.vue'
import AppCheckBox from '../../controls/AppCheckBox.vue'
import AppButton from '../../controls/AppButton.vue'
export default {
  components:{AppTextField,CodeEditor,AppCheckBox,AppButton},
  props:{modelValue:String,stream:String,disabled:Boolean},emits:['update:modelValue'],
  data(){return {rules:[],written:'',error:'',technical:false}},
  watch:{modelValue:{immediate:true,handler(value){if(value===this.written)return;try{const rules=value?JSON.parse(value):[];if(!Array.isArray(rules))throw new Error('Mappings must be an array');this.rules=rules.map(row=>({stream:row.stream || '',source:row.source || '',target:row.target || '...',exclude:!!row.exclude,writable:!!row.writable}));this.error=''}catch(error){this.error=error.message}}}},
  methods:{t,publish(){this.written=JSON.stringify(this.rules.map(row=>({stream:row.stream,source:row.source,exclude:row.exclude,writable:row.writable,...(!row.exclude?{target:row.target}:{})})));this.$emit('update:modelValue',this.written)},add(){this.rules.push({stream:this.stream,source:'...',target:'...',exclude:false,writable:true});this.publish()},remove(index){this.rules.splice(index,1);this.publish()}}
}
</script>
<template>
  <section class="workspace-mappings" :aria-label="t('Mappings and exclusions')">
    <header><span>{{ t('Mappings and exclusions') }}</span><AppButton icon-only label="Add mapping" icon="add" :disabled="disabled || rules.length>=256" @click="add" /><AppButton icon-only label="Technical JSON" icon="code" @click="technical=!technical" /></header>
    <p v-if="error" class="error" role="alert">{{ t(error) }}</p>
    <template v-if="!technical">
      <div v-for="(row,index) in rules" :key="index" class="workspace-mapping">
        <div class="workspace-mapping-head"><AppTextField v-model="row.stream" label="Mapping stream" :disabled="disabled" @update:model-value="publish" /><AppButton icon-only label="Remove mapping" icon="delete" :disabled="disabled" @click="remove(index)" /></div>
        <AppTextField v-model="row.source" label="Depot pattern" placeholder="Depot pattern, e.g. assets/..." :disabled="disabled" @update:model-value="publish" />
        <AppTextField v-if="!row.exclude" v-model="row.target" label="Local pattern" placeholder="Local pattern, e.g. art/..." :disabled="disabled" @update:model-value="publish" />
        <div class="workspace-mapping-head"><AppCheckBox v-model="row.exclude" label="Exclude" :disabled="disabled" @update:model-value="publish" /><AppCheckBox v-model="row.writable" label="Writable" :disabled="disabled || row.exclude" @update:model-value="publish" /></div>
      </div>
    </template>
    <CodeEditor v-else :model-value="modelValue" language="json" :source-toolbar="false" :read-only="disabled" :disabled="disabled" style="min-height:180px" @update:model-value="$emit('update:modelValue',$event)" />
  </section>
</template>
<style scoped>
.workspace-mappings{display:grid;gap:8px;min-width:0}.workspace-mappings header,.workspace-mapping-head{display:flex;gap:6px;align-items:center}.workspace-mappings header span,.workspace-mapping-head>:first-child{flex:1;min-width:0}.workspace-mapping{display:grid;gap:6px;padding-block:8px;border-bottom:1px solid var(--outline-variant)}
</style>
