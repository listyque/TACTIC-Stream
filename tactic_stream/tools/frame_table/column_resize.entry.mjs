import { createApp } from 'vue';
import ColumnResizeFixture from './ColumnResizeFixture.vue';
import { windowDirective } from '../../frontend/src/controls/window.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
import '../../frontend/src/icons.css';
createApp(ColumnResizeFixture)
  .directive('window', windowDirective)
  .mount('#app');
