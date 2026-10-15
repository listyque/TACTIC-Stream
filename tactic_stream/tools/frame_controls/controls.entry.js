import { createApp } from 'vue';
import ControlsHarness from './ControlsHarness.vue';
import {
  initializeAppearance,
  appearance,
  hostedPalette
} from '../../frontend/src/appearance.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
Object.assign(appearance, {
  mode: 'dark',
  theme: 'md3',
  clickAnimations: false,
  hoverAnimations: false,
  popupAnimations: false,
  fadeAnimations: false
});
hostedPalette.value = {
  dark: '#78a6c4',
  darkBase: '#292d30',
  light: '#3d7599',
  lightBase: '#d4dce1'
};
initializeAppearance();
createApp(ControlsHarness).mount('#app');
