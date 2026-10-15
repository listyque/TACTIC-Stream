<script>
import FilterGroup from './FilterGroup.vue';
export default {
 name:'AdvancedFilter',components:{FilterGroup},props:{value:Object,fields:Array,baseFilter:[String,Array]},emits:['apply'],
 data(){return {draft:JSON.parse(JSON.stringify(this.value||{op:'and',children:[]})),error:''}},
 computed:{usable(){return this.fields.filter(f=>f.storage&&f.kind!=='json')},base(){try{return typeof this.baseFilter==='string'?JSON.parse(this.baseFilter):this.baseFilter||[]}catch{return []}}},
 watch:{value:{deep:true,handler(v){this.draft=JSON.parse(JSON.stringify(v||{op:'and',children:[]}))}}},
 methods:{apply(){this.error='';let count=0;const check=n=>{if(n.children){if(!n.children.length&&n!==this.draft)throw Error('Удалите пустую вложенную группу');n.children.forEach(check)}else{count++;if(!this.usable.some(f=>f.name===n.field))throw Error('Выберите доступное поле')}};try{check(this.draft);if(count>40)throw Error('Не больше 40 условий');this.$emit('apply',JSON.parse(JSON.stringify(this.draft)))}catch(e){this.error=e.message}},clear(){this.draft={op:'and',children:[]};this.apply()}}
};
</script>
<template>
<details class="advanced-filter"><summary>Составной поиск · И / ИЛИ</summary><p class="muted">Дополнительные условия объединяются с фильтром исходного представления. «Не равно» сохраняет NULL-семантику TACTIC. «Содержит» здесь ищет буквальный текст.</p><details v-if="base.length"><summary>Условия, сохранённые в widget_config</summary><pre>{{JSON.stringify(base,null,2)}}</pre></details><FilterGroup :node="draft" :fields="usable"/><p v-if="error" class="error">{{error}}</p><div class="toolbar"><button class="primary" type="button" @click="apply">Применить составной поиск</button><button type="button" @click="clear">Очистить дополнительные условия</button><small>До 40 условий. Сохранение в sidebar использует исходный формат FilterData; несовместимое выражение не упрощается.</small></div></details>
</template>
