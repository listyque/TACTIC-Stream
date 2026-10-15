<script setup>
import {computed,ref} from 'vue'
import FrameGraph from '../../frontend/src/frame/controls/graph/FrameGraph.vue'
import {appearance,initializeAppearance} from '../../frontend/src/appearance.js'
import * as Model from './model.mjs'
import '../../frontend/src/theme.css'
import '../../frontend/src/style.css'
const params=new URLSearchParams(location.search)
appearance.language=params.get('language')||'en';appearance.mode=params.get('mode')||'dark'
appearance.clickAnimations=appearance.hoverAnimations=appearance.fadeAnimations=appearance.popupAnimations=false
initializeAppearance()
const canvas=ref(null),graph=ref(Model.initial()),commands=ref([])
const node=computed(()=>({...graph.value,id:'testGraph',label:'Graph',width:innerWidth,height:innerHeight,language:appearance.language}))
function dispatch(action){commands.value.push(action.value);graph.value=Model.apply(graph.value,action.value)}
window.frameGraph={canvas,graph,commands,node}
</script>
<template><FrameGraph ref="canvas" style="width:100vw;height:100dvh" :node="node" @event="dispatch" /></template>
