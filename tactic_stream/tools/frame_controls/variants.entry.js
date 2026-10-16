import { createApp } from 'vue';
import VariantsHarness from './VariantsHarness.vue';
import {
  appearance,
  hostedPalette,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
Object.assign(appearance, {
  theme: 'md3',
  mode: 'dark',
  language: 'en',
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
createApp(VariantsHarness).mount('#app');
