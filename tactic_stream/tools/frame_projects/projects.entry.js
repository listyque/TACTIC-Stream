import { createApp } from 'vue';
import ProjectsHarness from './ProjectsHarness.vue';
import {
  initializeAppearance,
  appearance,
  hostedPalette
} from '../../frontend/src/appearance.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
Object.assign(appearance, {
  theme: 'md3',
  language: 'en',
  mode: 'dark',
  clickAnimations: false,
  hoverAnimations: false,
  fadeAnimations: false,
  popupAnimations: false
});
hostedPalette.value = {
  dark: '#78a6c4',
  darkBase: '#292d30',
  light: '#3d7599',
  lightBase: '#d4dce1'
};
initializeAppearance();
createApp(ProjectsHarness).mount('#app');
