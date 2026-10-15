<script setup>
import {ref} from 'vue'
import SecurityRules from '../../frontend/src/features/administration/SecurityRules.vue'
import {appearance,initializeAppearance} from '../../frontend/src/appearance.js'
import '../../frontend/src/theme.css'
import '../../frontend/src/style.css'
const params=new URLSearchParams(location.search)
appearance.language=params.get('language')||'en';appearance.mode=params.get('mode')||'dark'
appearance.clickAnimations=appearance.hoverAnimations=appearance.fadeAnimations=appearance.popupAnimations=false
initializeAppearance()
const security=ref(null)
window.frameAdmin={screen:security,appearance}
</script>
<template><SecurityRules ref="security" ticket="isolated-frame-test" project="demo" style="padding:0;height:100dvh" /></template>
