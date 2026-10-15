import {createApp} from 'vue'
import {windowDirective} from '../../frontend/src/controls/window.js'
import ColumnsHarness from './ColumnsHarness.vue'
createApp(ColumnsHarness).directive('window',windowDirective).mount('#app')
