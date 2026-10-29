import { createApp } from 'vue';
import ChromeHarness from './ChromeHarness.vue';
import { windowDirective } from '../../frontend/src/controls/window.js';
import {
  initializeAppearance,
  appearance
} from '../../frontend/src/appearance.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
appearance.mode = 'dark';
appearance.popupAnimations = false;
initializeAppearance();
window.chromeAppearance = appearance;
createApp(ChromeHarness).directive('window', windowDirective).mount('#app');
