import { createApp } from 'vue';
import PlatformHarness from './PlatformHarness.vue';
import '../../frontend/src/style.css';
import '../../frontend/src/theme.css';
import {
  initializeAppearance,
  appearance
} from '../../frontend/src/appearance.js';
appearance.mode = 'dark';
initializeAppearance();
createApp(PlatformHarness).mount('#app');
