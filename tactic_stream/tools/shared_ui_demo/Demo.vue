<script setup>
import {computed, ref, onMounted} from 'vue'
import AppButton from '../../frontend/src/controls/AppButton.vue'
import AppTextField from '../../frontend/src/controls/AppTextField.vue'
import AppCheckbox from '../../frontend/src/controls/AppCheckbox.vue'
import {appearance, initializeAppearance} from '../../frontend/src/appearance.js'
import screen from './screen.json'
import palettes from './palettes.json'
import * as Logic from './logic.mjs'
import '../../frontend/src/theme.css'
import '../../frontend/src/style.css'

const query = new URLSearchParams(location.search), mode = ref(query.get('mode') || 'dark'), language = ref(query.get('language') || 'en')
const state = ref(Logic.initial(screen)), width = ref(innerWidth), nodes = Logic.leaves(screen.layout)
const boxes = computed(() => Logic.layout(screen, width.value)), model = computed(() => Logic.present(screen, state.value, language.value))
Object.assign(appearance, {theme:'md3',mode:mode.value,language:language.value,hoverAnimations:false,clickAnimations:false,fadeAnimations:false,popupAnimations:false})
initializeAppearance()
const palette = palettes[mode.value]
const colors = {'--page':'workspace','--surface-high':'surfaceContainerHigh','--on-surface':'primaryText','--muted':'secondaryText','--primary':'action','--on-selected':'selectedText','--outline':'outline','--outline-variant':'outlineVariant','--disabled':'disabledText','--hover':'rowHover','--selected':'selected','--error':'error'}
for (const [token,role] of Object.entries(colors)) document.documentElement.style.setProperty(token,palette[role])
function send(event) {state.value = Logic.transition(screen,state.value,event)}
function style(node) {
  const box = boxes.value[node.id]
  return {left:box.x+'px',top:box.y+'px',width:box.width+'px',height:box.height+'px',fontSize:screen.typography[node.role || 'body']+'px',fontWeight:node.kind==='Button'||node.role==='title'?600:400,lineHeight:box.height+'px'}
}
onMounted(() => {window.demo = {screen, state, boxes, model, send}; addEventListener('resize',() => width.value=innerWidth)})
</script>

<template>
  <main class="shared-demo" :style="{'--demo-body':screen.typography.body+'px'}">
    <template v-for="node in nodes" :key="node.id">
      <span v-if="node.kind === 'Label'" :data-control="node.id" class="demo-control demo-label" :class="{muted:node.muted,title:node.role==='title','demo-error':model[node.id].error}" :style="style(node)">{{ model[node.id].text }}</span>
      <AppTextField v-else-if="node.kind === 'TextField'" :data-control="node.id" class="demo-control" :style="style(node)" :label="node.label" :model-value="model[node.id].value" @update:model-value="send({type:'change',field:node.field,value:$event})" />
      <AppCheckbox v-else-if="node.kind === 'CheckBox'" :data-control="node.id" class="demo-control" :style="style(node)" :label="model[node.id].text" :translate-label="false" :model-value="model[node.id].value" @update:model-value="send({type:'change',field:node.field,value:$event})" />
      <AppButton v-else-if="node.kind === 'Button'" :data-control="node.id" class="demo-control demo-button" :style="style(node)" :label="model[node.id].text" :translate-label="false" :highlighted="node.highlighted" :disabled="!model[node.id].enabled" @click="send({type:node.action})" />
    </template>
  </main>
</template>

<style>
html,body,#app {width:100%;height:100%;overflow:hidden}
.shared-demo {position:relative;width:100%;height:100%;background:var(--page);font-family:'Segoe UI';font-size:var(--demo-body)}
.demo-control {position:absolute;margin:0;box-sizing:border-box}
.demo-label {display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.demo-label.title {font-weight:600}.demo-label.demo-error {color:var(--error)}
.demo-button {border-radius:var(--button-radius);padding:0 16px;gap:7px;border-color:var(--outline-variant)}
.demo-button.primary {border:0;background:var(--primary);color:var(--on-selected)}
.demo-button:disabled {opacity:1;background:var(--surface-high);color:var(--disabled)}
.demo-button:hover:not(:disabled) {background:var(--hover);border-color:var(--outline-variant)}
.demo-button.primary:hover:not(:disabled) {background:var(--primary)}
.shared-demo .app-checkbox {gap:9px;font-weight:400;padding:0;min-height:0}
.shared-demo .app-checkbox-indicator,.shared-demo .app-checkbox input {width:19px;height:19px;min-height:0;flex:0 0 19px;border-radius:5px}
.shared-demo .app-checkbox .app-icon {font-size:15px}
.shared-demo .app-text-field {padding-inline:11px}
.shared-demo .app-text-field:focus {padding-inline:10px}
</style>
