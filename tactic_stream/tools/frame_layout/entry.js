import {createApp} from 'vue'
import {windowDirective} from '../../frontend/src/controls/window.js'
import Harness from './LayoutHarness.vue'
createApp(Harness).provide('openHelp',()=>{}).directive('window',windowDirective).mount('#app')
