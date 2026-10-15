<script>
export default {
 name:'SidebarNode', props:{node:Object,selected:String,folders:{type:Object,default:()=>({})}}, emits:['open','context','folder'],
 computed:{expanded(){return Object.hasOwn(this.folders,this.node.id)?this.folders[this.node.id]:this.node.open===true},isFolder(){return this.node.kind==='folder'}}
};
</script>
<template>
<li v-if="node.kind==='separator'" class="nav-separator" role="separator"></li>
<li v-else-if="node.kind==='title'" class="nav-caption">{{node.title}}</li>
<li v-else-if="node.kind==='diagnostic'" class="nav-warning">{{node.title}}</li>
<li v-else>
 <button class="nav-item" :class="{active:selected===node.id,folder:isFolder}" :title="node.name" :aria-expanded="isFolder?expanded:undefined" @click="isFolder?$emit('folder',{id:node.id,open:!expanded}):$emit('open',node)" @contextmenu="!isFolder&&$emit('context',{event:$event,node})" @keydown="($event.key==='ContextMenu'||($event.shiftKey&&$event.key==='F10'))&&!isFolder&&$emit('context',{event:$event,node,keyboard:true})">
  <span class="nav-symbol">{{isFolder?(expanded?'▾':'▸'):'◫'}}</span><span>{{node.title}}</span><span v-if="!isFolder&&node.renderer==='unsupported'" class="not-ported" title="Обработчик ещё не перенесён">·</span>
 </button>
 <ul v-if="isFolder&&expanded" class="nav-children"><SidebarNode v-for="child in node.children" :key="child.id" :node="child" :selected="selected" :folders="folders" @folder="$emit('folder',$event)" @open="$emit('open',$event)" @context="$emit('context',$event)" /></ul>
</li>
</template>
