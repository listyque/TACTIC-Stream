<script setup>
import {computed, ref, onMounted} from 'vue'
import AppButton from '../../frontend/src/controls/AppButton.vue'
import AppCheckbox from '../../frontend/src/controls/AppCheckbox.vue'
import {appearance, initializeAppearance} from '../../frontend/src/appearance.js'
import spec from './gantt.json'
import fixture from '../../frontend/tests/task_schedule_fixture.json'
import palettes from './palettes.json'
import * as State from './gantt.state.mjs'
import {scene as buildScene} from './gantt.ui.mjs'
import '../../frontend/src/theme.css'
import '../../frontend/src/style.css'

const query = new URLSearchParams(location.search), mode = query.get('mode') || 'dark', language = query.get('language') || 'en'
const palette = palettes[mode], state = ref(State.initial(fixture)), width = ref(innerWidth), height = ref(innerHeight)
Object.assign(appearance, {theme:'md3',mode,language,hoverAnimations:false,clickAnimations:false,fadeAnimations:false,popupAnimations:false})
initializeAppearance()
for (const [token,role] of Object.entries({'--page':'workspace','--surface-high':'surfaceContainerHigh','--on-surface':'primaryText','--muted':'secondaryText','--primary':'action','--on-selected':'selectedText','--outline':'outline','--outline-variant':'outlineVariant','--disabled':'disabledText','--hover':'rowHover','--selected':'selected','--error':'error'})) document.documentElement.style.setProperty(token,palette[role])
const scene = computed(() => buildScene(spec,fixture,state.value,width.value,height.value,palette,language))
function send(event) {state.value=State.transition(spec,fixture,state.value,event,width.value,height.value)}
const box = node => ({left:node.x+'px',top:node.y+'px',width:node.width+'px',height:node.height+'px'})
function style(node) {
  return Object.assign(box(node), {color:node.kind==='Button'?undefined:node.color,fontSize:node.fontSize+'px',fontWeight:node.bold||node.kind==='Button'?600:400,lineHeight:node.height+'px',textAlign:node.align,cursor:node.drag?(node.drag.mode==='start'||node.drag.mode==='end'?'ew-resize':node.drag.mode==='progress'?'crosshair':'grab'):node.action?'pointer':undefined})
}
function press(event,node) {
  if (!node.drag || event.button!==0) return
  event.preventDefault();if(node.keyAction)event.currentTarget.focus();send(Object.assign({type:'press',x:Math.round(event.clientX),y:Math.round(event.clientY)},node.drag))
}
function key(event,node) {
  if(node.keyAction&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();send(Object.assign({code:event.key},node.keyAction))}
  else if(node.action&&['Enter',' '].includes(event.key)){event.preventDefault();send(node.action)}
}
function wheel(event) {
  event.preventDefault()
  if (event.ctrlKey) send({type:'zoom',factor:event.deltaY<0?1.1:1/1.1,x:event.clientX})
  else send({type:'scroll',dx:event.shiftKey?event.deltaY:event.deltaX,dy:event.shiftKey?0:event.deltaY})
}
onMounted(() => {
  window.ganttDemo={state,scene,send}
  addEventListener('resize',()=>{width.value=innerWidth;height.value=innerHeight})
  addEventListener('pointermove',event=>{if(state.value.drag)send({type:'pointer',x:Math.round(event.clientX),y:Math.round(event.clientY)})})
  addEventListener('pointerup',()=>{if(state.value.drag)send({type:'release'})})
  addEventListener('pointercancel',()=>send({type:'cancel'}));addEventListener('blur',()=>send({type:'cancel'}))
  addEventListener('keydown',event=>{if(event.key==='Escape')send({type:'cancel'});if(event.ctrlKey&&event.key==='z'){event.preventDefault();send({type:event.shiftKey?'redo':'undo'})}})
})
</script>

<template>
  <main class="gantt-demo" @wheel="wheel">
    <div v-for="layer in scene.layers" :key="layer.id" class="gantt-layer" :data-layer="layer.id" :style="box(layer)">
      <template v-for="node in layer.nodes" :key="node.id">
        <AppButton v-if="node.kind==='Button'" :data-node="node.id" class="gantt-node gantt-button" :style="style(node)" :label="node.text" :translate-label="false" :disabled="!node.enabled" :highlighted="node.highlighted" @click="send(node.action)" />
        <AppCheckbox v-else-if="node.kind==='CheckBox'" :data-node="node.id" class="gantt-node" :style="style(node)" :label="node.text" :translate-label="false" :hide-label="!node.showLabel" :model-value="node.checked" @update:model-value="send(node.action)" />
        <span v-else-if="node.kind==='Label'" :data-node="node.id" class="gantt-node gantt-label" :style="style(node)" :tabindex="node.action?0:undefined" :role="node.action?'button':undefined" @keydown="key($event,node)" @pointerdown="press($event,node)" @click="node.action&&send(node.action)">{{node.text}}</span>
        <div v-else-if="node.kind==='Rectangle'" :data-node="node.id" class="gantt-node gantt-rectangle" :style="Object.assign(style(node),{background:node.background,border:node.border==='transparent'?'none':'1px solid '+node.border,borderRadius:node.radius+'px'})" :tabindex="node.keyAction?0:undefined" :role="node.keyAction?'button':undefined" :aria-label="node.keyAction?node.a11yLabel:undefined" @keydown="key($event,node)" @pointerdown="press($event,node)" @click="node.action&&send(node.action)" />
      </template>
    </div>
  </main>
</template>

<style>
html,body,#app {width:100%;height:100%;overflow:hidden}
.gantt-demo {position:relative;width:100%;height:100%;background:var(--page);font-family:'Segoe UI';user-select:none;touch-action:none}
.gantt-layer {position:absolute;overflow:hidden}
.gantt-node {position:absolute;margin:0;box-sizing:border-box}
.gantt-label {display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gantt-button {min-height:0;min-width:0;border-radius:var(--button-radius);padding:0 16px;gap:7px;border-color:var(--outline-variant)}
.gantt-button:disabled {opacity:1;background:var(--surface-high);color:var(--disabled)}
.gantt-button:hover:not(:disabled) {background:var(--hover);border-color:var(--outline-variant)}
.gantt-demo .app-checkbox {gap:9px;font-weight:400;padding:0;min-height:0}
.gantt-demo .app-checkbox-indicator,.gantt-demo .app-checkbox input {width:19px;height:19px;min-height:0;flex:0 0 19px;border-radius:5px}
.gantt-demo .app-checkbox .app-icon {font-size:15px}
</style>
