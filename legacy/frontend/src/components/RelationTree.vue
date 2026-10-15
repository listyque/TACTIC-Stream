<script>
import RelationTreeRow from './RelationTreeRow.vue';
export default {name:'RelationTree',components:{RelationTreeRow},props:{project:String,target:String,spec:Object,rows:Array,total:Number,offset:Number,limit:Number,busy:Boolean},emits:['inspect','open','page'],data(){return {generation:0}}};
</script>
<template>
<section class="relation-tree"><div class="toolbar"><p class="notice">Ленивое дерево исходной Schema. Каждый уровень загружается отдельно; instance-объекты не копируются.</p><button @click="generation++">Свернуть / перечитать дерево</button></div><ul :key="generation" role="tree"><RelationTreeRow v-for="row in rows" :key="row.key+row.revision" :project="project" :target="target" :row="row" :spec="spec" @inspect="$emit('inspect',$event)" @open="$emit('open',$event)"/></ul><p v-if="!rows.length&&!busy">Нет записей</p><footer class="toolbar"><button :disabled="busy||!offset" @click="$emit('page',Math.max(0,offset-limit))">←</button><span>{{offset+1}}–{{offset+rows.length}} из {{total??'—'}}</span><button :disabled="busy||offset+rows.length>=total" @click="$emit('page',offset+limit)">→</button></footer></section>
</template>
