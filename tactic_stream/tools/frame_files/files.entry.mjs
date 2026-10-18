import { createApp } from 'vue';
import Fixture from './FilesFixture.vue';
import { windowDirective } from '../../frontend/src/controls/window.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
createApp(Fixture)
  .provide('openHelp', () => {})
  .directive('window', windowDirective)
  .mount('#app');
