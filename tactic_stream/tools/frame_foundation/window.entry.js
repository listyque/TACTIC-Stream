import { createApp } from 'vue';
import WindowHarness from './WindowHarness.vue';
import { initializeAppearance } from '../../frontend/src/appearance.js';
import { windowDirective } from '../../frontend/src/controls/window.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
initializeAppearance();
createApp(WindowHarness).directive('window', windowDirective).mount('#app');
