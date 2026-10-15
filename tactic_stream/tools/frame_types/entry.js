import {createApp} from 'vue'
import {windowDirective} from '../../frontend/src/controls/window.js'
import TypesHarness from './TypesHarness.vue'
createApp(TypesHarness).directive('window',windowDirective).mount('#app')
