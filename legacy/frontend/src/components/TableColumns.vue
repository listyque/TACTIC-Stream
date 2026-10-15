<script>
// Column visibility and pinning are local view preferences, NOT a DB schema edit.
export default {
 name:'TableColumns',props:{fields:Array,hidden:Array,pinned:Array},emits:['close','toggle','pin','reset'],
 data(){return {search:'',origin:null}},
 computed:{filtered(){const needle=this.search.trim().toLocaleLowerCase();return this.fields.filter(f=>!needle||(f.label+' '+f.name).toLocaleLowerCase().includes(needle))}},
 mounted(){this.origin=document.activeElement;this.$refs.dialog.showModal();this.$refs.search.focus()},
 beforeUnmount(){this.$refs.dialog?.close();if(this.origin?.isConnected)this.origin.focus({preventScroll:true})},
 methods:{backdrop(e){if(e.target!==this.$refs.dialog)return;const r=this.$refs.dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)this.$emit('close')}}
};
</script>
<template>
<Teleport to="body"><dialog ref="dialog" class="table-columns-dialog" aria-label="Колонки таблицы" @cancel.prevent="$emit('close')" @click="backdrop">
 <header><div><h2>Колонки таблицы</h2><small>{{fields.length-hidden.length}} из {{fields.length}} показано</small></div><button aria-label="Закрыть выбор колонок" @click="$emit('close')">×</button></header>
 <input ref="search" v-model="search" class="column-search" placeholder="Найти колонку…" aria-label="Найти колонку">
 <div class="table-column-list"><div v-for="f in filtered" :key="f.name" class="table-column-option"><label><input type="checkbox" :checked="!hidden.includes(f.name)" @change="$emit('toggle',f.name)"><span>{{f.label}}<small>{{f.name}}</small></span></label><button class="column-pin" :class="{active:pinned.includes(f.name)}" :aria-pressed="pinned.includes(f.name)" :aria-label="'Закрепить '+f.label" @click="$emit('pin',f)"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3h8l-1 6 3 3v2H6v-2l3-3Z M12 14v7"/></svg></button></div><p v-if="!filtered.length" class="muted">Колонки не найдены.</p></div>
 <footer><small>Видимость и геометрия — в этом браузере.<br>Определения — в widget_config.</small><button @click="$emit('reset')">Сбросить геометрию</button></footer>
</dialog></Teleport>
</template>
