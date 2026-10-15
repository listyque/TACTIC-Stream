<script setup>
import {ref} from 'vue'
import Shell from '../../frontend/src/features/administration/AdministrationShell.vue'
import {appearance,initializeAppearance} from '../../frontend/src/appearance.js'
import '../../frontend/src/theme.css'
import '../../frontend/src/style.css'
const params=new URLSearchParams(location.search)
appearance.language=params.get('language')||'en';appearance.mode=params.get('mode')||'dark'
appearance.clickAnimations=appearance.hoverAnimations=appearance.fadeAnimations=appearance.popupAnimations=false
initializeAppearance()
const screen=ref(null),model=ref({section:'types',project:'demo',projects:[{value:'demo',label:'Demo'}],locked:false,busy:false,drafts:[]});window.frameAdmin={screen,appearance,model}
function command(value){if(value.type==='section')model.value={...model.value,section:value.value}}
</script>
<template><Shell ref="screen" :model="model" @command="command" style="height:100dvh" /></template>
