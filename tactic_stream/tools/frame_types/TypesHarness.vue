<script setup>
import {ref} from 'vue'
import SearchTypes from '../../frontend/src/features/administration/SearchTypes.vue'
import {appearance,initializeAppearance} from '../../frontend/src/appearance.js'
import '../../frontend/src/theme.css'
import '../../frontend/src/style.css'
const params=new URLSearchParams(location.search)
appearance.language=params.get('language')||'en';appearance.mode=params.get('mode')||'dark'
appearance.clickAnimations=appearance.hoverAnimations=appearance.fadeAnimations=appearance.popupAnimations=false
initializeAppearance()
const screen=ref(null)
window.frameAdmin={screen,appearance}
</script>
<template><SearchTypes ref="screen" ticket="isolated-frame-test" project="demo" style="padding:0;height:100dvh" /></template>
