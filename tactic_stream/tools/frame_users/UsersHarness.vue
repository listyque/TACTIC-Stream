<script setup>
import {ref} from 'vue'
import SecurityUsers from '../../frontend/src/features/administration/SecurityUsers.vue'
import {appearance,initializeAppearance} from '../../frontend/src/appearance.js'
import '../../frontend/src/theme.css'
import '../../frontend/src/style.css'
const params=new URLSearchParams(location.search)
appearance.language=params.get('language')||'en';appearance.mode=params.get('mode')||'dark'
appearance.clickAnimations=appearance.hoverAnimations=appearance.fadeAnimations=appearance.popupAnimations=false
initializeAppearance()
const users=ref(null)
window.frameGroups={groups:users,appearance}
</script>
<template><SecurityUsers ref="users" ticket="isolated-frame-test" project="cg" style="padding:0;height:100dvh" /></template>
