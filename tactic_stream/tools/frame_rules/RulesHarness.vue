<script setup>
import {ref} from 'vue'
import ProcessRules from '../../frontend/src/features/administration/ProcessRules.vue'
import {appearance,initializeAppearance} from '../../frontend/src/appearance.js'
import '../../frontend/src/theme.css'
import '../../frontend/src/style.css'
const params=new URLSearchParams(location.search)
appearance.language=params.get('language')||'en';appearance.mode=params.get('mode')||'dark'
appearance.clickAnimations=appearance.hoverAnimations=appearance.fadeAnimations=appearance.popupAnimations=false
initializeAppearance()
const screen=ref(null);window.frameAdmin={screen,appearance}
import {onMounted} from 'vue'
onMounted(()=>screen.value.open('PR1'))
</script>
<template><ProcessRules ref="screen" ticket="isolated-frame-test" project="demo" /></template>
<style>.process-rules-editor[open]{inset:0;margin:0;width:100vw;height:100dvh;max-width:none;max-height:none;border:0;border-radius:0;padding:0}.process-rules-editor>.configuration-header{display:none}.process-dependencies-body{height:100dvh}.app-window-resize{display:none}</style>
