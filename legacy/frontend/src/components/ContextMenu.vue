<script>
import api from '../api.js';
export default {
 name:'ContextMenu',props:{menu:Object},emits:['action','close'],
 data(){return {left:0,top:0,trail:[],focusIndex:-1,origin:null,restoreFocus:true}},
 computed:{items(){let items=this.menu?.items||[];for(const i of this.trail)items=items[i]?.children||[];return items}},
 watch:{menu:{deep:true,handler(){this.trail=[];this.position()}},items(){this.position()}},
 mounted(){api.action?.('menu.open',{control:this.menu?.scope||'menu'});this.origin=document.activeElement;this.outside=e=>{if(this.menu?.anchor&&this.origin?.contains(e.target))return;if(!this.$refs.panel?.contains(e.target)){this.restoreFocus=false;this.$emit('close')}};this.resize=()=>this.$emit('close');document.addEventListener('pointerdown',this.outside,true);window.addEventListener('resize',this.resize);this.position()},
 beforeUnmount(){document.removeEventListener('pointerdown',this.outside,true);window.removeEventListener('resize',this.resize);if(this.restoreFocus&&this.origin?.isConnected)this.origin.focus({preventScroll:true})},
 methods:{
  position(){this.left=Math.max(4,this.menu?.x||0);this.top=Math.max(4,this.menu?.y||0);this.$nextTick(()=>{
   const box=this.$refs.panel?.getBoundingClientRect(),anchor=this.menu?.anchor;
   if(box){if(anchor){this.left=this.menu.align==='end'?anchor.right-box.width:anchor.left;this.top=anchor.bottom+6;if(this.top+box.height>innerHeight-8&&anchor.top-box.height-6>=8)this.top=anchor.top-box.height-6}
    this.left=Math.max(8,Math.min(this.left,innerWidth-box.width-8));this.top=Math.max(8,Math.min(this.top,innerHeight-box.height-8))}this.focusFirst()})},
  buttons(){return Array.from(this.$refs.panel?.querySelectorAll('[role="menuitem"],[role="menuitemradio"],[role="menuitemcheckbox"]')||[])},
  focusFirst(){const b=this.buttons();this.focusIndex=0;(b[0]||this.$refs.panel)?.focus({preventScroll:true})},
  choose(item,index){if(item.enabled===false)return;api.action?.('menu.select',{control:String(item.id||'submenu')});if(item.children){this.trail.push(index);return}this.$emit('action',item)},
  key(event){const b=this.buttons();const keys=['ArrowDown','ArrowUp','Home','End','Escape','ArrowLeft','ArrowRight','Tab'];if(!keys.includes(event.key))return;if(event.key==='Tab'){this.restoreFocus=false;this.$emit('close');return}event.preventDefault();event.stopPropagation();if(event.key==='Escape'){this.$emit('close');return}if(event.key==='ArrowLeft'){if(this.trail.length)this.trail.pop();return}if(event.key==='ArrowRight'){const focused=document.activeElement;if(focused?.getAttribute('aria-haspopup')==='menu')focused.click();return}if(!b.length)return;const at=b.indexOf(document.activeElement);this.focusIndex=event.key==='Home'?0:event.key==='End'?b.length-1:event.key==='ArrowDown'?(at+1)%b.length:(at-1+b.length)%b.length;b[this.focusIndex]?.focus({preventScroll:true})}
 }
};
</script>
<template>
<Teleport to="body"><section ref="panel" class="context-menu native-menu" :class="menu.variant||''" role="menu" tabindex="-1" :aria-label="menu.title||'Контекстное меню TACTIC'" :style="{left:left+'px',top:top+'px'}" @keydown="key" @contextmenu.prevent @click.stop>
 <div v-if="menu.title" class="menu-heading">{{menu.title}}</div><button v-if="trail.length" role="menuitem" @click="trail.pop()">← Назад</button>
 <p v-if="menu.loading" class="muted">Загрузка действий…</p><p v-if="menu.error" class="error">{{menu.error}}</p>
 <template v-for="(item,index) in items" :key="item.id||index"><hr v-if="item.type==='separator'" role="separator"><div v-else-if="item.type==='title'" class="menu-heading">{{item.label}}</div><button v-else :role="item.role==='radio'?'menuitemradio':item.role==='checkbox'?'menuitemcheckbox':'menuitem'" :aria-checked="item.role?Boolean(item.checked):undefined" tabindex="-1" :aria-disabled="item.enabled===false" :aria-haspopup="item.children?'menu':undefined" :class="{unavailable:item.enabled===false,checked:item.checked===true}" :title="item.reason||item.legacy_label||''" :data-action="item.id" @click="choose(item,index)"><span class="menu-label"><span v-if="item.role" class="menu-check" aria-hidden="true">{{item.checked?'✓':''}}</span>{{item.label}}</span><kbd v-if="item.shortcut">{{item.shortcut}}</kbd><span v-if="item.children" aria-hidden="true">›</span><small v-if="item.enabled===false&&item.reason">{{item.reason}}</small></button></template>
 <small v-if="menu.source" class="menu-source">{{menu.source}}</small>
</section></Teleport>
</template>
