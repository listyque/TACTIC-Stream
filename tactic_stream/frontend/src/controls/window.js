import { h, render } from 'vue'
import WindowControls from './WindowControls.vue'
let activeWindow = null

// Dialogs block their owner; utility windows keep the workspace available.
export const windowDirective = {
  mounted(element, binding) {
    if (element.tagName !== 'DIALOG') return
    let configuration = binding.value
    let header = null, host = null, retainedGeometry = null
    const show = element.show.bind(element), close = element.close.bind(element)
    const home = document.createComment('window owner')
    element.before(home)
    let owner = null, returnFocus = null
    const nonmodal = () => ['window','popup'].includes(configuration?.type)
    function closed() {
      if (element.matches(':popover-open')) element.hidePopover()
      owner?.removeEventListener('close', closeChild); owner = null
      if (home.parentNode && (element.parentNode !== home.parentNode || element.previousSibling !== home)) home.after(element)
      if (activeWindow === element) activeWindow = null
    }
    function nativeClosed() {
      if (element.open) return
      closed(); if (returnFocus?.isConnected) returnFocus.focus({preventScroll:true}); returnFocus = null
    }
    function closeChild(event) { if (event.target === owner) element.close() }
    function raise(event) {
      if (!element.open || !element.matches(':popover-open') || activeWindow === element || element.querySelector('dialog:modal')) return
      if (event && event.target.closest('[popover]') !== element) return
      const focused = element.contains(document.activeElement) ? document.activeElement : null
      element.hidePopover(); element.showPopover()
      focused?.focus({ preventScroll:true })
      activeWindow = element
    }
    element.show = () => {
      if (!nonmodal()) { if (element.matches(':modal')) element.focus(); else show(); return }
      if (element.open) { element.dispatchEvent(new Event('windowshow')); raise(); return }
      returnFocus = document.activeElement
      owner = returnFocus?.closest(configuration.type === 'popup' ? 'dialog[open]' : 'dialog:modal') || [...document.querySelectorAll('dialog:modal')].at(-1) || null
      if (owner === element || element.contains(owner)) owner = null
      if (owner) { owner.append(element); owner.addEventListener('close', closeChild) }
      element.popover = 'manual'; show(); element.showPopover()
      activeWindow = element
      element.dispatchEvent(new Event('windowshow'))
    }
    element.close = (...args) => { closed(); close(...args); if (returnFocus?.isConnected) returnFocus.focus({preventScroll:true}); returnFocus = null }
    function escape(event) {
      if (event.key !== 'Escape' || event.defaultPrevented || !nonmodal() || event.target.closest('dialog') !== element) return
      event.preventDefault(); event.stopPropagation()
      if (element.dispatchEvent(new Event('cancel', { cancelable:true }))) element.close()
    }
    function rememberGeometry(event) {
      if (event.target !== element || !element.open) return
      const {x,y,width,height,maximized,restore} = event.detail
      retainedGeometry = {rect:{x,y,width,height},maximized,restore}
    }
    element.addEventListener('windowgeometrychange', rememberGeometry)
    element.addEventListener('keydown', escape)
    element.addEventListener('close', nativeClosed)
    element.addEventListener('pointerdown', raise)
    function placeControls() {
      const last = [...header.querySelectorAll('button')].at(-1)
      const anchor = last?.parentElement.tagName === 'FORM' ? last.parentElement : last
      if (anchor) anchor.before(host); else header.append(host)
    }
    const attach = () => {
      element.classList.toggle('app-window', configuration !== false && configuration?.type !== 'popup')
      element.dataset.windowType = configuration?.type || 'dialog'
      element.dataset.windowKind = configuration?.kind || ''
      if (nonmodal()) element.setAttribute('aria-modal','false')
      else element.removeAttribute('aria-modal')
      const next = configuration === false ? null : [...element.querySelectorAll('header')].find(header => header.closest('.app-window') === element) || null
      if (next === header) {
        if (host && !header.contains(host)) placeControls()
        return
      }
      if (host) { render(null, host); host.remove() }
      header = next; host = null
      if (!header) return
      host = document.createElement('span'); host.className = 'app-window-controls'
      placeControls()
      render(h(WindowControls, { element, header, geometry:configuration?.geometry || retainedGeometry,backProvided:!!configuration?.backProvided }), host)
    }
    const observer = new MutationObserver(attach)
    observer.observe(element, { childList: true, subtree: true }); attach()
    element.windowConfigure = value => {
      configuration = value; attach()
      if (host) render(h(WindowControls, { element, header, geometry:configuration?.geometry || retainedGeometry,backProvided:!!configuration?.backProvided }), host)
    }
    element.windowCleanup = () => {
      closed(); home.remove(); element.show = show; element.close = close
      element.removeEventListener('windowgeometrychange', rememberGeometry)
      element.removeEventListener('keydown', escape); element.removeEventListener('close', nativeClosed); element.removeEventListener('pointerdown', raise)
      observer.disconnect(); if (host) { render(null, host); host.remove() }
    }
  },
  updated(element, binding) { element.windowConfigure?.(binding.value) },
  beforeUnmount(element) { element.windowCleanup?.(); element.classList.remove('app-window'); delete element.windowCleanup; delete element.windowConfigure },
}
