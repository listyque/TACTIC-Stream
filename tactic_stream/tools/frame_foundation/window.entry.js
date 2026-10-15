import { createApp } from 'vue';
import WindowHarness from './WindowHarness.vue';
import { windowDirective } from '../../frontend/src/controls/window.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
createApp(WindowHarness).directive('window', windowDirective).mount('#app');
