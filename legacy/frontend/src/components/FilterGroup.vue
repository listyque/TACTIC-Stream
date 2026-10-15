<script>
export default {
 name:'FilterGroup',props:{node:Object,fields:Array,depth:{type:Number,default:0}},emits:['remove'],
 computed:{count(){const walk=n=>n.children?n.children.reduce((a,x)=>a+walk(x),0):1;return walk(this.node)}},
 methods:{field(n){return this.fields.find(f=>f.name===n.field)||{}},
 operators(n){const k=this.field(n).kind;const ops=[['eq','равно'],['ne','не равно (включая NULL)'],['null','NULL'],['not_null','не NULL'],['empty','пусто'],['not_empty','не пусто'],['in','в списке'],['not_in','не в списке']];if(['text','textarea','select'].includes(k))ops.push(['contains','содержит'],['not_contains','не содержит'],['starts','начинается'],['ends','заканчивается']);if(['integer','number','date','datetime','text'].includes(k))ops.push(['gt','больше'],['gte','не меньше'],['lt','меньше'],['lte','не больше']);return ops},
 changed(n){n.op=['text','textarea','select'].includes(this.field(n).kind)?'contains':'eq';n.value=this.field(n).kind==='boolean'?false:''},
 add(){const f=this.fields[0];if(f)this.node.children.push({field:f.name,op:'eq',value:''})},
 addGroup(){this.node.children.push({op:this.node.op==='and'?'or':'and',children:[]})},
 nullOp(n){return ['null','not_null','empty','not_empty'].includes(n.op)},
 list(n,event){n.value=event.target.value.split(/\r?\n/).filter(x=>x.length>0)},
 type(n){return {integer:'number',number:'number',date:'date',datetime:'datetime-local'}[this.field(n).kind]||'text'}
 }
};
</script>
<template>
<fieldset class="filter-group"><legend><select v-model="node.op" aria-label="Логика группы"><option value="and">И · все условия</option><option value="or">ИЛИ · любое условие</option></select><button v-if="depth" type="button" @click="$emit('remove')" aria-label="Удалить группу">×</button></legend>
 <div v-for="(child,i) in node.children" :key="i" class="filter-node">
  <FilterGroup v-if="child.children" :node="child" :fields="fields" :depth="depth+1" @remove="node.children.splice(i,1)"/>
  <div v-else class="filter-clause"><select v-model="child.field" @change="changed(child)" aria-label="Поле условия"><option v-for="f in fields" :key="f.name" :value="f.name">{{f.label}}</option></select><select v-model="child.op" aria-label="Оператор условия" @change="child.value=['in','not_in'].includes(child.op)?[]:child.value"><option v-for="o in operators(child)" :key="o[0]" :value="o[0]">{{o[1]}}</option></select>
   <span v-if="nullOp(child)" class="muted">без значения</span><textarea v-else-if="['in','not_in'].includes(child.op)" :value="Array.isArray(child.value)?child.value.join('\n'):''" @input="list(child,$event)" rows="2" placeholder="Одно значение на строку" aria-label="Значения списка"></textarea>
   <select v-else-if="field(child).kind==='boolean'" v-model="child.value" aria-label="Значение условия"><option :value="true">Да</option><option :value="false">Нет</option></select><input v-else v-model="child.value" :type="type(child)" step="any" aria-label="Значение условия" placeholder="Значение"><button type="button" @click="node.children.splice(i,1)" aria-label="Удалить условие">×</button>
  </div>
 </div>
 <div class="toolbar"><button type="button" :disabled="!fields.length||count>=40" @click="add">+ Условие</button><button v-if="depth<1" type="button" :disabled="count>=40" @click="addGroup">+ Группа</button></div>
</fieldset>
</template>
