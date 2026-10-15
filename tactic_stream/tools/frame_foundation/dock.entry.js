import { createApp } from 'vue';
import DockHarness from './DockHarness.vue';
import {
  appearance,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
Object.assign(appearance, {
  mode: 'dark',
  theme: 'md3',
  language: 'en',
  clickAnimations: false,
  hoverAnimations: false,
  popupAnimations: false,
  fadeAnimations: false
});
initializeAppearance();
createApp(DockHarness).mount('#app');
