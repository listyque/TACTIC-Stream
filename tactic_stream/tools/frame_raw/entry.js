import {createApp} from 'vue'
import {windowDirective} from '../../frontend/src/controls/window.js'
import RawHarness from './RawHarness.vue'
createApp(RawHarness).directive('window',windowDirective).mount('#app')
