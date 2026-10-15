import { defineAsyncComponent, h } from 'vue'
import BusyIndicator from './BusyIndicator.vue'
import { t } from '../i18n.js'

// Keep loading and failed downloads visible without replacing an editor's state owner.
export function asyncComponent(loader) {
  return defineAsyncComponent({
    loader,
    loadingComponent: () => h('p', { role:'status', class:'muted' }, [h(BusyIndicator, { running:true }), ' ' + t('Loading interface…')]),
    errorComponent: () => h('p', { role:'alert', class:'error' }, t('Unable to load the interface. Check your connection and reload the page.')),
  })
}
