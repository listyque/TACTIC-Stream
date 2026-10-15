import { createApp, h, ref } from 'vue';
import HelpView from '../../frontend/src/features/help/HelpView.vue';
import { windowDirective } from '../../frontend/src/controls/window.js';
import {
  appearance,
  hostedPalette,
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
hostedPalette.value = {
  dark: '#78a6c4',
  darkBase: '#292d30',
  light: '#3d7599',
  lightBase: '#d4dce1'
};
initializeAppearance();
createApp({
  setup() {
    const help = ref(null);
    window.help = help;
    window.appearance = appearance;
    return () => h(HelpView, { ref: help });
  }
})
  .directive('window', windowDirective)
  .mount('#app');
