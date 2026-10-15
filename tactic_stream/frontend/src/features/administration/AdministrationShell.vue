<script setup>
import {computed,onMounted,onBeforeUnmount,ref,markRaw} from 'vue'
import FrameView from '../../frame/FrameView.vue'
import Port from './AdministrationPort.vue'
import {appearance} from '../../appearance.js'
import * as UI from '../../../../src/tactic_stream/shared_ui/features/administration/administration.ui.mjs'
import * as State from '../../../../src/tactic_stream/shared_ui/features/administration/administration.state.mjs'
const props=defineProps({model:{type:Object,required:true}}),emit=defineEmits(['command'])
const host=ref(null),size=ref({width:1,height:1}),ui=ref(State.initial())
const scene=computed(()=>UI.describe(props.model,ui.value,size.value.width,size.value.height,appearance.language))
const views={toolbar:{component:markRaw(Port),props:{target:'administration-actions'}},content:{component:markRaw(Port),props:{target:'administration-pages'}}}
function dispatch(event){const result=State.transition(ui.value,props.model,event);ui.value=result.ui;for(const command of result.commands)emit('command',command)}
defineExpose({dispatch,ui,scene})
let observer
onMounted(()=>{observer=new ResizeObserver(([entry])=>{size.value={width:Math.max(1,entry.contentRect.width),height:Math.max(1,entry.contentRect.height)}});observer.observe(host.value)})
onBeforeUnmount(()=>observer?.disconnect())
</script>
<template><section ref="host" class="administration-frame-shell"><FrameView :scene="scene" :views="views" :models="{sections:UI.sections}" :describe-row="(list,record)=>UI.row(list,record,model,ui,appearance.language)" @event="dispatch" /></section></template>
<style scoped>.administration-frame-shell{position:relative;flex:1;min-height:0;min-width:0;width:100%;height:100%}:deep(.administration-page > section){padding:0;flex:1;min-height:0;margin:0}:deep(#administration-actions){display:block;overflow:visible}</style>
