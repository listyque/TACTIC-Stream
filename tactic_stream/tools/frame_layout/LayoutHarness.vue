<script setup>
import {ref} from 'vue'
import LayoutEditor from '../../frontend/src/features/administration/LayoutEditor.vue'
import {appearance,initializeAppearance} from '../../frontend/src/appearance.js'
import '../../frontend/src/theme.css'
import '../../frontend/src/style.css'
const params=new URLSearchParams(location.search)
appearance.language=params.get('language')||'en';appearance.mode=params.get('mode')||'dark'
appearance.clickAnimations=appearance.hoverAnimations=appearance.fadeAnimations=appearance.popupAnimations=false
initializeAppearance()
const screen=ref(null);window.frameAdmin={screen,appearance}
</script>
<template><LayoutEditor ref="screen" ticket="isolated-frame-test" project="demo" :search-types="[{search_type:'demo/asset',title:'Assets'}]" :initial-focus="{searchType:'demo/asset',view:'cards_example'}" style="padding:0;height:100dvh" /></template>
