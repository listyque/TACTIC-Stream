<script setup>
import {ref} from 'vue'
import ColumnsEditor from '../../frontend/src/features/administration/ColumnsEditor.vue'
import {appearance,initializeAppearance} from '../../frontend/src/appearance.js'
import '../../frontend/src/theme.css'
import '../../frontend/src/style.css'
const params=new URLSearchParams(location.search)
appearance.language=params.get('language')||'en';appearance.mode=params.get('mode')||'dark'
appearance.clickAnimations=appearance.hoverAnimations=appearance.fadeAnimations=appearance.popupAnimations=false
initializeAppearance()
const columns=ref(null)
window.frameAdmin={screen:columns,appearance}
</script>
<template><ColumnsEditor ref="columns" ticket="isolated-frame-test" project="demo" style="padding:0;height:100dvh" /></template>
