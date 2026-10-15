import { createApp, h, watchEffect } from 'vue'
import { asyncComponent } from './controls/asyncComponent.js'
import { initializeAppearance } from './appearance.js'
import { t } from './i18n.js'
import { installDebugLogging } from './features/debug/debugLog.js'
import { windowDirective } from './controls/window.js'
import './theme.css'
import './style.css'
initializeAppearance()
installDebugLogging()
const documentation = location.pathname === '/docs' || location.pathname === '/docs/'
if (documentation) watchEffect(() => { document.title = t('TACTIC Stream — API reference') })
const screen = asyncComponent(documentation ? () => import('./features/documentation/ApiDocumentation.vue') : () => import('./App.vue'))
createApp({ render: () => h(screen) }).directive('window', windowDirective).mount('#app')
