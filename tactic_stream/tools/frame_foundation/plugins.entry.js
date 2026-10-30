import { createApp } from 'vue';
import Harness from './PluginsHarness.vue';
import { initializeAppearance } from '../../frontend/src/appearance.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
initializeAppearance();
createApp(Harness).mount('#app');
