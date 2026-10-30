import { createApp } from 'vue';
import SystemInfoHarness from './SystemInfoHarness.vue';
import { initializeAppearance } from '../../frontend/src/appearance.js';
import { windowDirective } from '../../frontend/src/controls/window.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
initializeAppearance();
createApp(SystemInfoHarness).directive('window', windowDirective).mount('#app');
