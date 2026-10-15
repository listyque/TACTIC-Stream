<script setup>
import {ref} from 'vue'
import SchemaEditor from '../../frontend/src/features/administration/SchemaEditor.vue'
import WorkflowEditor from '../../frontend/src/features/administration/WorkflowEditor.vue'
import {appearance,initializeAppearance} from '../../frontend/src/appearance.js'
import '../../frontend/src/theme.css'
import '../../frontend/src/style.css'
const params=new URLSearchParams(location.search),editor=params.get('editor')||'schema'
appearance.language=params.get('language')||'en';appearance.mode=params.get('mode')||'dark'
appearance.clickAnimations=appearance.hoverAnimations=appearance.fadeAnimations=appearance.popupAnimations=false
initializeAppearance()
const screen=ref(null);window.frameAdmin={screen,appearance,editor}
</script>
<template><component :is="editor==='schema'?SchemaEditor:WorkflowEditor" ref="screen" ticket="isolated-frame-test" project="demo" inline style="padding:0;height:100dvh" /></template>
