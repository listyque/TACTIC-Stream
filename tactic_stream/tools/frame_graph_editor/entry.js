import {createApp} from 'vue'
import {windowDirective} from '../../frontend/src/controls/window.js'
import EditorHarness from './EditorHarness.vue'
createApp(EditorHarness).directive('window',windowDirective).mount('#app')
