<script setup>
import { nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
const props = defineProps({ screenKey: String, title: String, back: Boolean, direction: String, scroll: Object, busy: Boolean, active: Boolean })
const emit = defineEmits(['enter', 'back', 'scrolled', 'root-scroll'])
const screen = ref(null), swipeX = ref(0), chromeHidden = ref(false), chromeInset = ref(0)
let pointer, suppressClick = false, scrollTimer, lastTop = 0, lastHeight = 0, restoreOnLoad = false
watch(chromeHidden, hidden => {
  const element = screen.value, top = element?.getBoundingClientRect().top
  nextTick(() => {
    if (props.back || !element || screen.value !== element) return
    // Keep collapsed toolbars in the scroll extent so visible rows do not move.
    if (hidden) chromeInset.value = Math.max(0, top - element.getBoundingClientRect().top)
    nextTick(() => { lastTop = element.scrollTop; lastHeight = element.clientHeight })
  })
})
function remember(element = screen.value) {
  if (element) emit('scrolled', element.dataset.screenKey, element.scrollTop)
}
function scrolling(event) {
  if (!props.back) {
    const { scrollTop, clientHeight } = event.currentTarget
    if (scrollTop <= 4) chromeHidden.value = false
    else if (clientHeight === lastHeight && Math.abs(scrollTop - lastTop) >= 8) chromeHidden.value = scrollTop > lastTop && scrollTop > 128
    if (clientHeight !== lastHeight || Math.abs(scrollTop - lastTop) >= 8) lastTop = scrollTop
    lastHeight = clientHeight
    emit('root-scroll', event)
  }
  clearTimeout(scrollTimer)
  const element = event.currentTarget
  scrollTimer = setTimeout(() => remember(element), 180)
}
function restore(element = screen.value) {
  if (props.busy) { restoreOnLoad = true; return }
  restoreOnLoad = false
  if (element) {
    element.scrollTop = props.scroll?.[element.dataset.screenKey] || 0
    if (element.dataset.screenKey === 'root') { lastTop = element.scrollTop; lastHeight = element.clientHeight; chromeHidden.value = lastTop > 128 }
  }
}
function focus(element) {
  if (document.activeElement === document.body) element.focus({ preventScroll:true })
}
watch(() => props.active, active => { if (active) nextTick(() => restore()); else remember() })
watch(() => props.busy, value => { if (!value && restoreOnLoad) nextTick(() => restore()) })
onMounted(() => nextTick(() => restore()))
onBeforeUnmount(() => { clearTimeout(scrollTimer); remember() })
function start(event) {
  restoreOnLoad = false
  suppressClick = false; pointer = null
  if (!event.isPrimary) { swipeX.value = 0; return }
  if (event.pointerType !== 'touch' || event.target.closest('button,a,input,textarea,select,label,summary,[contenteditable]') || props.busy) return
  pointer = { id: event.pointerId, x: event.clientX, y: event.clientY, row: event.target.closest('[data-mobile-item]')?.dataset.mobileItem }
}
function move(event) {
  if (!pointer || pointer.id !== event.pointerId) return
  const dx = event.clientX - pointer.x, dy = event.clientY - pointer.y
  if (Math.abs(dy) > 12 && Math.abs(dy) > Math.abs(dx)) { pointer = null; return }
  if (Math.abs(dx) > 12 && Math.abs(dx) > Math.abs(dy) * 1.5 && (dx > 0 && props.back || dx < 0 && pointer.row)) {
    event.currentTarget.setPointerCapture(event.pointerId)
    pointer.dx = dx
    swipeX.value = Math.max(-80, Math.min(80, dx * .4))
  }
}
function stop(event, cancel = false) {
  const gesture = pointer
  pointer = null; swipeX.value = 0
  if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
  if (!gesture || cancel) return
  const tap = Math.abs(event.clientX - gesture.x) < 12 && Math.abs(event.clientY - gesture.y) < 12
  if (!tap && Math.abs(gesture.dx || 0) < 60) return
  suppressClick = true
  if (!tap && gesture.dx > 0) emit('back')
  else {
    if (gesture.row) emit('enter', gesture.row)
  }
}
function click(event) {
  if (suppressClick) { event.preventDefault(); event.stopPropagation(); suppressClick = false }
}
</script>
<template>
  <section class="mobile-results" :data-chrome-hidden="chromeHidden" @wheel.passive="restoreOnLoad = false" @pointerdown="start" @pointermove="move" @pointerup="stop" @pointercancel="stop($event, true)" @click.capture="click">
    <header v-if="back" class="mobile-result-header"><slot name="header" /></header>
    <div class="mobile-result-stage">
      <Transition :name="'mobile-result-' + direction" @before-leave="remember" @enter="restore" @after-enter="focus">
        <div :key="screenKey" ref="screen" class="mobile-result-screen" role="region" :aria-label="title" tabindex="-1" :data-screen-key="screenKey" :style="{ transform:swipeX ? 'translateX(' + swipeX + 'px)' : undefined, paddingTop:!back && chromeHidden ? chromeInset + 'px' : undefined }" @scroll.passive="scrolling"><slot /></div>
      </Transition>
    </div>
    <slot name="footer" />
  </section>
</template>
<style>
.mobile-results { display:flex; flex-direction:column; height:100%; min-height:0; overflow:hidden; touch-action:pan-y pinch-zoom; background:var(--page); }
.mobile-result-header { flex:none; background:var(--surface-high); border-bottom:1px solid var(--outline-variant); }
.mobile-result-header h2 { min-width:0; margin:0; font-size:var(--result-title-size); font-weight:600; overflow-wrap:anywhere; }
.mobile-result-stage { position:relative; flex:1; min-height:0; overflow:hidden; touch-action:pan-y pinch-zoom; }
.mobile-result-screen { position:absolute; inset:0; overflow:auto; overflow-anchor:none; overscroll-behavior-y:contain; touch-action:pan-y pinch-zoom; background:var(--page); padding-bottom:16px; }
.mobile-result-screen:focus { outline:none; }
.mobile-result-forward-leave-active,.mobile-result-back-leave-active { pointer-events:none; }
.mobile-result-forward-enter-active,.mobile-result-forward-leave-active,.mobile-result-back-enter-active,.mobile-result-back-leave-active { transition:transform var(--motion-extended) var(--motion-easing); }
.mobile-result-forward-enter-from,.mobile-result-back-leave-to { transform:translateX(100%); }
.mobile-result-forward-leave-to,.mobile-result-back-enter-from { transform:translateX(-100%); }
@media(prefers-reduced-motion:reduce) { .mobile-result-stage > * { transition:none !important; } }
html[data-fade-animations="false"] .mobile-result-stage > * { transition:none; }
</style>
