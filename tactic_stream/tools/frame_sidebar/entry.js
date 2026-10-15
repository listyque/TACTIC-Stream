import {createApp} from 'vue'
import {windowDirective} from '../../frontend/src/controls/window.js'
import SidebarHarness from './SidebarHarness.vue'
createApp(SidebarHarness).provide('openHelp',()=>{}).directive('window',windowDirective).mount('#app')
