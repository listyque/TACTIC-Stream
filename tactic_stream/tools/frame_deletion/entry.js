import {createApp} from 'vue'
import {windowDirective} from '../../frontend/src/controls/window.js'
import Harness from './DeleteHarness.vue'
createApp(Harness).directive('window',windowDirective).mount('#app')
