<script>
export default {name:'FieldInput',props:{field:Object,modelValue:null},emits:['update:modelValue'],computed:{
 inputRows(){const n=Number(this.field.display_options?.rows||4);return Number.isInteger(n)?Math.max(1,Math.min(40,n)):4},
 placeholder(){const p=this.field.display_options?.placeholder;return typeof p==='string'?p:undefined},
 inputType(){const kind=this.field.kind;if(kind==='date'){const v=String(this.modelValue??'');return !v||/^\d{4}-\d{2}-\d{2}(?:[ T].*)?$/.test(v)?'date':'text'}if(kind==='datetime'){const v=String(this.modelValue??'');return !v||/^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/.test(v)?'datetime-local':'text'}return kind==='password'?'password':['integer','number'].includes(kind)?'number':'text'},
 inputValue(){const v=this.modelValue??'';if(typeof v!=='string')return v;if(this.inputType==='date')return v.slice(0,10);if(this.inputType==='datetime-local')return v.replace(' ','T');return v}
 },methods:{emit(e){this.$emit('update:modelValue',this.field.kind==='boolean'?e.target.checked:e.target.value)}}};
</script>
<template>
<div class="field-input">
 <select v-if="field.kind==='select'" :disabled="field.read_only" :value="modelValue??''" @change="emit"><option value="">—</option><option v-for="o in field.options" :key="o.value" :value="o.value">{{o.label}}</option></select>
 <input v-else-if="field.kind==='boolean'" type="checkbox" :disabled="field.read_only" :checked="modelValue===true" @change="emit">
 <textarea v-else-if="['textarea','json'].includes(field.kind)" :disabled="field.read_only" :value="typeof modelValue==='object'&&modelValue!==null?JSON.stringify(modelValue,null,2):modelValue??''" :rows="inputRows" :placeholder="placeholder" @input="emit"></textarea>
 <input v-else :type="inputType" :placeholder="placeholder" :step="field.kind==='integer'?1:'any'" :disabled="field.read_only" :value="inputValue" :autocomplete="field.kind==='password'?'new-password':undefined" @input="emit">
 <small v-if="field.reason" class="warning-text">{{field.reason}}</small>
</div>
</template>
