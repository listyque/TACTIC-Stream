import { createApp } from 'vue';
import ServerConfiguration from '../../frontend/src/features/configuration/ServerConfiguration.vue';
import {
  appearance,
  initializeAppearance
} from '../../frontend/src/appearance.js';
import '../../frontend/src/theme.css';
import '../../frontend/src/style.css';
initializeAppearance();
appearance.language =
  new URL(location.href).searchParams.get('language') || 'en';
appearance.mode = 'dark';
createApp(ServerConfiguration, {
  ticket: 'fixture-ticket',
  workersOnly: true,
  groupTitles: ['Services and workers']
}).mount('#app');
