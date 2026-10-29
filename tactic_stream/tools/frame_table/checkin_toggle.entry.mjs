import { createApp } from 'vue';
import Fixture from './CheckinToggle.vue';
import { tooltipDirective } from '../../frontend/src/controls/tooltip.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
import '../../frontend/src/icons.css';
createApp(Fixture).directive('tooltip', tooltipDirective).mount('#app');
