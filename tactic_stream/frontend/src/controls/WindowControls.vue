<script setup>
// Shared geometry for native dialogs; callers retain their close and dirty guards.
import { ref, onMounted, onBeforeUnmount, watch, watchEffect } from 'vue'
import AppButton from './AppButton.vue'
import { t } from '../i18n.js'
import { mobile } from '../mobile.js'
import {fit, moved, resized} from '../../../src/tactic_stream/shared_ui/shell/window.geometry.mjs'
import {layout} from '../../../src/tactic_stream/shared_ui/core/foundation.mjs'
import {windowMinimumWidth,windowMinimumHeight} from '../../../src/tactic_stream/shared_ui/shell/window.sizing.mjs'
const props = defineProps({ element: Object, header: Object, geometry:Object, backProvided:Boolean })
const previousTitle = props.header.getAttribute('title'), previousTabIndex = props.header.getAttribute('tabindex')
const maximized = ref(false)
const minimized = ref(false)
const edges = ref({})
function back() {
  if (props.element.dispatchEvent(new Event('cancel', { cancelable:true }))) props.element.close()
}
watchEffect(() => { props.header.title = t('Drag the title bar to move. Double-click or Alt+F10 to maximize. Alt+arrows moves the focused title bar.') })
let saved = null, placed = null, gesture = null
function geometryChanged() {
  resizeEdges()
  props.element.dispatchEvent(new CustomEvent('windowgeometrychange', { detail:{ ...rectangle(), maximized:maximized.value, restore:saved } }))
  window.dispatchEvent(new Event('windowgeometrychange'))
}
watch(() => props.geometry, value => {
  if (!value) return
  saved = clamp(value.restore || value.rect); placed = clamp(value.rect); maximized.value = !!value.maximized
  for (const [key,value] of Object.entries(placed)) props.element.style.setProperty('--window-' + key,value + 'px')
  props.element.classList.add('app-window-positioned')
  props.element.classList.toggle('app-window-maximized',maximized.value)
}, { deep:true, immediate:true })
const compact = () => innerWidth <= 700
function rectangle() { const box = props.element.getBoundingClientRect(); return { x: box.x, y: box.y, width: box.width, height: box.height } }
function resizeEdges() {
  const box = rectangle()
  edges.value = { '--edge-left':box.x + 'px','--edge-top':box.y + 'px',
    '--edge-right':innerWidth - box.x - box.width + 'px','--edge-bottom':innerHeight - box.y - box.height + 'px' }
}
function clamp(rect) {
  return fit(rect,{x:0,y:0,width:innerWidth,height:innerHeight},minimum(),layout.windowMargin)
}
function minimum() {
  const kind = props.element.dataset.windowKind
  return {width:Math.min(kind?windowMinimumWidth(kind):280,innerWidth-layout.windowMargin),height:Math.min(kind?windowMinimumHeight(kind):180,innerHeight-layout.windowMargin)}
}
function place(rect) {
  placed = clamp(rect)
  for (const [key, value] of Object.entries(placed)) props.element.style.setProperty('--window-' + key, value + 'px')
  props.element.classList.add('app-window-positioned')
  geometryChanged()
}
function toggle() {
  if (compact()) return
  if (!maximized.value) { saved = rectangle(); maximized.value = true }
  else { maximized.value = false; props.element.classList.remove('app-window-maximized'); place(saved); return }
  props.element.classList.toggle('app-window-maximized', maximized.value)
  geometryChanged()
}
function minimize() {
  minimized.value = !minimized.value
  props.element.classList.toggle('app-window-minimized', minimized.value)
  geometryChanged()
}
function shown() { if (minimized.value) minimize() }
function start(event) {
  if (gesture || event.isPrimary === false || compact() || maximized.value || event.button !== 0 || event.target.closest('button, a, input, select, textarea, summary, label, [role="button"], [role="tab"]')) return
  event.preventDefault(); props.header.setPointerCapture(event.pointerId)
  gesture = { pointer: event.pointerId, x: event.clientX, y: event.clientY, before: rectangle() }
}
function move(event) {
  if (!gesture || gesture.pointer !== event.pointerId) return
  const delta = {x:event.clientX-gesture.x,y:event.clientY-gesture.y}
  const rect = gesture.edge
    ? resized(gesture.before,gesture.edge,delta,{x:0,y:0,width:innerWidth,height:innerHeight},
      minimum())
    : moved(gesture.before,delta)
  place(rect)
}
function startResize(event, edge) {
  if (gesture || event.isPrimary === false || compact() || maximized.value || event.button !== 0) return
  event.preventDefault(); props.header.setPointerCapture(event.pointerId)
  gesture = { pointer:event.pointerId,x:event.clientX,y:event.clientY,before:rectangle(),edge }
}
function stop(event) {
  if (!gesture || event.pointerId !== gesture.pointer) return
  const current = gesture; gesture = null
  if (['pointercancel','lostpointercapture'].includes(event.type)) place(current.before)
  if (props.header.hasPointerCapture(current.pointer)) props.header.releasePointerCapture(current.pointer)
}
function doubleClick(event) { if (!event.target.closest('button, a, input, select, textarea, summary, label')) toggle() }
function resize() { if (placed && !maximized.value && !compact()) place(placed); resizeEdges() }
function cancelGesture() { if (gesture) stop({ pointerId:gesture.pointer,type:'pointercancel' }) }
function opened() {
  if (!props.element.open || saved || placed || compact()) return
  if (props.element.offsetWidth < innerWidth - 16 || props.element.offsetHeight < innerHeight - 16) return
  const width = Math.min(1100, innerWidth * .8), height = Math.min(760, innerHeight * .8)
  saved = { width, height, x: (innerWidth - width) / 2, y: (innerHeight - height) / 2 }
  maximized.value = true; props.element.classList.add('app-window-maximized')
  geometryChanged()
}
const observer = new MutationObserver(opened)
const sizeObserver = new ResizeObserver(resizeEdges)
function key(event) {
  if (event.target.closest('.app-window') !== props.element || event.target.closest('dialog') !== props.element) return
  if (event.key === 'Escape' && gesture) { event.preventDefault(); event.stopPropagation(); cancelGesture(); return }
  if (event.altKey && event.key === 'F10') { event.preventDefault(); event.stopPropagation(); toggle() }
  if (event.target !== props.header || !event.altKey || !event.key.startsWith('Arrow') || compact() || maximized.value) return
  event.preventDefault(); event.stopPropagation()
  const rect = rectangle(), dx = event.key === 'ArrowLeft' ? -10 : event.key === 'ArrowRight' ? 10 : 0, dy = event.key === 'ArrowUp' ? -10 : event.key === 'ArrowDown' ? 10 : 0
  place(event.shiftKey ? { ...rect,width:Math.max(280,rect.width + dx),height:Math.max(180,rect.height + dy) } : { ...rect,x:rect.x + dx,y:rect.y + dy })
}
onMounted(() => {
  props.header.classList.add('app-window-titlebar'); props.header.tabIndex = 0
  for (const [name, fn] of Object.entries({ pointerdown: start, pointermove: move, pointerup: stop, pointercancel: stop, lostpointercapture: stop, dblclick: doubleClick })) props.header.addEventListener(name, fn)
  props.element.addEventListener('keydown', key, true); window.addEventListener('resize', resize)
  props.element.addEventListener('windowshow', shown)
  window.addEventListener('blur',cancelGesture); window.addEventListener('pagehide',cancelGesture)
  observer.observe(props.element, { attributes: true, attributeFilter: ['open'] }); opened()
  sizeObserver.observe(props.element)
})
onBeforeUnmount(() => {
  cancelGesture()
  for (const [name, fn] of Object.entries({ pointerdown: start, pointermove: move, pointerup: stop, pointercancel: stop, lostpointercapture: stop, dblclick: doubleClick })) props.header.removeEventListener(name, fn)
  props.header.classList.remove('app-window-titlebar')
  for (const [name, value] of [['title', previousTitle], ['tabindex', previousTabIndex]]) {
    if (value === null) props.header.removeAttribute(name); else props.header.setAttribute(name, value)
  }
  props.element.classList.remove('app-window-positioned', 'app-window-maximized', 'app-window-minimized')
  for (const key of ['x', 'y', 'width', 'height']) props.element.style.removeProperty('--window-' + key)
  props.element.removeEventListener('keydown', key, true); window.removeEventListener('resize', resize)
  props.element.removeEventListener('windowshow', shown)
  window.removeEventListener('blur',cancelGesture); window.removeEventListener('pagehide',cancelGesture)
  observer.disconnect()
  sizeObserver.disconnect()
})
</script>
<template><AppButton v-if="element.dataset.windowType === 'window'" icon-only :icon="minimized ? 'window-restore' : 'minus'" :label="minimized ? 'Restore window' : 'Minimize window'" :aria-pressed="minimized" @click="minimize" /><AppButton v-if="!minimized" icon-only :icon="maximized ? 'window-restore' : 'open-in-full'" :label="maximized ? 'Restore window' : 'Maximize window'" :aria-pressed="maximized" @click="toggle" /><Teleport :to="header"><AppButton v-if="mobile && !backProvided" class="app-window-back" icon-only icon="MDI_ARROW_LEFT" label="Back" @click="back" /></Teleport><Teleport v-if="minimized && header.parentElement !== element" :to="element">
  <header class="app-window-titlebar app-window-minimized-titlebar">
    <strong>{{ element.getAttribute('aria-label') || header.querySelector('[role="heading"]')?.textContent || t('Restore window') }}</strong>
    <AppButton icon-only icon="window-restore" label="Restore window" @click="minimize" />
    <AppButton icon-only icon="close" label="Close" @click="minimize(); back()" />
  </header>
</Teleport><Teleport :to="element"><template v-if="!maximized && !minimized"><span v-for="edge in ['left','right','top','bottom','top-left','top-right','bottom-left','bottom-right']" :key="edge" class="app-window-resize" :class="edge" :style="edges" aria-hidden="true" @pointerdown.stop="startResize($event,edge)" /></template></Teleport></template>
<style>
.app-window-titlebar { touch-action:none; cursor:grab; user-select:none; outline:none; }
.app-window:not(.app-window-maximized) { border:1px solid var(--outline); border-radius:8px !important; box-shadow:0 8px 24px var(--shadow-color) !important; }
.app-window-back.icon-button { order:-1; width:28px; height:28px; min-width:28px; min-height:28px; flex:none; font-size:16px; }
.app-window-controls { display:inline-flex; align-items:center; flex-shrink:0; margin-left:auto; }
.app-window-resize { position:fixed; z-index:10; touch-action:none; }.app-window-resize.left,.app-window-resize.right { top:calc(var(--edge-top) + 10px); bottom:calc(var(--edge-bottom) + 10px); width:6px; cursor:ew-resize; }.app-window-resize.left { left:var(--edge-left); }.app-window-resize.right { right:var(--edge-right); }.app-window-resize.top,.app-window-resize.bottom { left:calc(var(--edge-left) + 10px); right:calc(var(--edge-right) + 10px); height:6px; cursor:ns-resize; }.app-window-resize.top { top:var(--edge-top); }.app-window-resize.bottom { bottom:var(--edge-bottom); }.app-window-resize.top-left,.app-window-resize.bottom-right { width:10px; height:10px; cursor:nwse-resize; }.app-window-resize.top-right,.app-window-resize.bottom-left { width:10px; height:10px; cursor:nesw-resize; }.app-window-resize.top-left { left:var(--edge-left); top:var(--edge-top); }.app-window-resize.top-right { right:var(--edge-right); top:var(--edge-top); }.app-window-resize.bottom-left { left:var(--edge-left); bottom:var(--edge-bottom); }.app-window-resize.bottom-right { right:var(--edge-right); bottom:var(--edge-bottom); }
.app-window-positioned { position:fixed !important; margin:0 !important; inset:var(--window-y) auto auto var(--window-x) !important; width:var(--window-width) !important; height:var(--window-height) !important; min-width:0 !important; min-height:0 !important; max-width:none !important; max-height:none !important; }
.app-window-maximized { position:fixed !important; margin:0 !important; inset:0 !important; width:100dvw !important; height:100dvh !important; min-width:0 !important; min-height:0 !important; max-width:none !important; max-height:none !important; border-radius:0 !important; box-shadow:none !important; }
.app-window.app-window-minimized { width:min(360px,calc(100dvw - 16px)) !important; height:42px !important; min-width:0 !important; min-height:0 !important; max-height:42px !important; overflow:hidden !important; padding:0 !important; }
.app-window-minimized-titlebar {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--header);
}
.app-window-minimized-titlebar > strong {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: var(--dialog-title-size);
}
.app-window-minimized > :not(.app-window-titlebar) { display:none !important; }
.app-window-minimized > .app-window-titlebar { width:100%; height:40px; min-height:40px; margin:0 !important; padding:2px 6px; flex:none; }
@media (max-width:700px) { .app-window-controls,.app-window-resize { display:none; } .app-window, .app-window-positioned, .app-window-maximized { position:fixed !important; margin:0 !important; inset:var(--phone-top,0px) 0 auto !important; width:100dvw !important; height:var(--phone-height,100dvh) !important; min-width:0 !important; min-height:0 !important; max-width:none !important; max-height:none !important; border:0 !important; border-radius:0 !important; box-shadow:none !important; } .app-window-titlebar { cursor:default; touch-action:auto; } }
</style>
