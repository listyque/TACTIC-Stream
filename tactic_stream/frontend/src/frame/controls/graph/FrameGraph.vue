<script setup>
import {computed, nextTick, onBeforeUnmount, onMounted, ref, watch} from 'vue'
import FrameView from '../../FrameView.vue'
import * as State from '../../../../../src/tactic_stream/shared_ui/controls/graph/graph.state.mjs'
import * as UI from '../../../../../src/tactic_stream/shared_ui/controls/graph/graph.ui.mjs'
import {colors} from '../../../../../src/tactic_stream/shared_ui/core/frame.mjs'

const props=defineProps({node:{type:Object,required:true}}), emit=defineEmits(['event'])
const host=ref(null), canvas=ref(null), scroll=ref(null), ui=ref(State.initial()), touches=new Map()
const viewport=computed(()=>UI.viewport(props.node)), scene=computed(()=>UI.describe(props.node,ui.value,props.node.language||'en'))
const toolbar=computed(()=>UI.toolbar(props.node,ui.value,props.node.language||'en'))
let frame=0,last=0,observer
function color(role){
  if(role?.mix){const [base,tint,amount]=role.mix;return `color-mix(in srgb, ${color(base)} ${(1-amount)*100}%, ${color(tint)} ${amount*100}%)`}
  return colors[role]?getComputedStyle(host.value).getPropertyValue(colors[role]).trim():role||'transparent'
}
function paint(){if(!canvas.value)return;const ratio=devicePixelRatio||1,w=viewport.value.width,h=viewport.value.height,c=canvas.value;if(c.width!==Math.round(w*ratio)||c.height!==Math.round(h*ratio)){c.width=Math.round(w*ratio);c.height=Math.round(h*ratio)}const context=c.getContext('2d');context.setTransform(ratio,0,0,ratio,0,0);UI.paint(context,props.node,ui.value,viewport.value,color,State.selectionRect(ui.value))}
function dispatch(event){const result=State.reduce(ui.value,event,props.node,viewport.value);ui.value=result.ui;for(const command of result.commands)emit('event',{...(props.node.action||{type:'graph'}),value:command})}
function modifier(event){return {control:event.ctrlKey||event.metaKey,shift:event.shiftKey,alt:event.altKey}}
function pointer(event,type){
  if(event.button>1&&type==='down')return
  if(type==='move'&&event.pointerType!=='touch'&&!ui.value.pointer&&!ui.value.pending)return
  const bounds=event.currentTarget.getBoundingClientRect(), p={x:event.clientX-bounds.left,y:event.clientY-bounds.top}
  if(event.pointerType==='touch'){
    if(type==='down'||type==='move'){if(type==='down'||touches.has(event.pointerId))touches.set(event.pointerId,p)}else touches.delete(event.pointerId)
    dispatch(type==='cancel'?{type:'cancel'}:{type:'touch',points:[...touches.values()]})
  }else dispatch({type,...p,button:event.button,...modifier(event)})
  if(type==='down'){event.currentTarget.focus({preventScroll:true});event.currentTarget.setPointerCapture(event.pointerId)}
  if(type==='up'||type==='cancel')if(event.currentTarget.hasPointerCapture(event.pointerId))event.currentTarget.releasePointerCapture(event.pointerId)
  event.preventDefault()
}
function wheel(event){const bounds=event.currentTarget.getBoundingClientRect();dispatch({type:'zoom',value:ui.value.zoom*(event.deltaY<0?1.1:1/1.1),x:event.clientX-bounds.left,y:event.clientY-bounds.top});event.preventDefault()}
function key(event){
  if(!['Escape','Delete','Home','+','=','-','f','F','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)&&!((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='s'))return
  event.preventDefault();event.stopPropagation();dispatch({type:'key',key:event.key,repeat:event.repeat,...modifier(event)})
}
function cancel(){touches.clear();dispatch({type:'cancel'})}
function animate(now){if(last&&ui.value.pointer?.active&&ui.value.pointer.kind==='node')dispatch({type:'tick',seconds:(now-last)/1000});last=now;frame=requestAnimationFrame(animate)}
watch(()=>props.node,()=>{ui.value=State.include(ui.value,props.node,viewport.value)},{immediate:true})
watch(()=>props.node.resetKey||props.node.center||props.node.id,()=>{ui.value=State.include(State.initial(),props.node,viewport.value)})
watch(()=>props.node.visible,visible=>{if(visible===false)cancel()})
watch([ui,viewport],async()=>{await nextTick();if(scroll.value){const x=(ui.value.x-ui.value.world.x)*ui.value.zoom,y=(ui.value.y-ui.value.world.y)*ui.value.zoom;if(Math.abs(scroll.value.scrollLeft-x)>.6)scroll.value.scrollLeft=x;if(Math.abs(scroll.value.scrollTop-y)>.6)scroll.value.scrollTop=y}paint()},{flush:'post'})
onMounted(()=>{observer=new MutationObserver(paint);for(let element=host.value;element;element=element.parentElement)observer.observe(element,{attributes:true,attributeFilter:['data-theme','style','class']});window.addEventListener('blur',cancel);paint();frame=requestAnimationFrame(animate)})
onBeforeUnmount(()=>{observer?.disconnect();cancelAnimationFrame(frame);window.removeEventListener('blur',cancel)})
function insertionPoint(){return {x:ui.value.x+viewport.value.width/ui.value.zoom/2-100,y:ui.value.y+viewport.value.height/ui.value.zoom/2-36}}
defineExpose({dispatch,insertionPoint,ui})
</script>

<template>
 <div ref="host" class="frame-graph" :data-frame="node.id" :aria-label="node.label" role="group">
  <FrameView class="graph-toolbar" :scene="toolbar" @event="dispatch" />
  <div class="graph-area" :style="{top:viewport.y+'px',width:node.width+'px',height:(viewport.height+16)+'px'}">
   <div ref="scroll" class="graph-scroll" :style="{width:(viewport.width+12)+'px',height:(viewport.height+12)+'px'}" @scroll="dispatch({type:'scroll',x:$event.target.scrollLeft,y:$event.target.scrollTop})"><div :style="{width:(ui.world.right-ui.world.x)*ui.zoom+'px',height:(ui.world.bottom-ui.world.y)*ui.zoom+'px'}" /></div>
   <div class="graph-camera" data-graph-camera tabindex="0" :style="{width:viewport.width+'px',height:viewport.height+'px'}" :aria-label="node.label" @pointerdown="pointer($event,'down')" @pointermove="pointer($event,'move')" @pointerup="pointer($event,'up')" @pointercancel="pointer($event,'cancel')" @lostpointercapture="ui.pointer&&cancel()" @wheel="wheel" @keydown="key" @click.capture="if($event.detail){$event.preventDefault();$event.stopPropagation()}">
    <canvas ref="canvas" :style="{width:viewport.width+'px',height:viewport.height+'px'}" aria-hidden="true" />
    <FrameView class="graph-plane" :scene="scene" :style="{width:(ui.world.right-ui.world.x)+'px',height:(ui.world.bottom-ui.world.y)+'px',transform:`translate(${-(ui.x-ui.world.x)*ui.zoom}px,${-(ui.y-ui.world.y)*ui.zoom}px) scale(${ui.zoom})`}" @event="dispatch" />
   </div>
  </div>
 </div>
</template>

<style scoped>
.frame-graph{position:relative;overflow:hidden;background:var(--page);border-radius:var(--surface-radius);min-width:0;min-height:0}.graph-toolbar{position:absolute;inset:0 0 auto;height:38px}.graph-area{position:absolute;left:0}.graph-scroll{overflow:scroll;position:absolute;left:0;top:0;overscroll-behavior:contain}.graph-scroll::-webkit-scrollbar{width:12px;height:12px}.graph-camera{position:absolute;left:0;top:0;overflow:hidden;touch-action:none;user-select:none;background:var(--page);outline:none}.graph-camera canvas{position:absolute;inset:0;pointer-events:none}.graph-plane{position:absolute;left:0;top:0;transform-origin:0 0}.graph-plane :deep(.frame-action){border-radius:0;overflow:visible}.graph-plane :deep(.frame-action>.item-surface){border-radius:0}
</style>
