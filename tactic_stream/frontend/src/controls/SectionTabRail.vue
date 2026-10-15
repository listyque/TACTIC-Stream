<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { t } from '../i18n.js'
import AppButton from './AppButton.vue'
import AppIcon from './AppIcon.vue'
import { displacedTabOffset } from './tabWidths.js'
import { readableText } from '../appearance.js'

defineOptions({ inheritAttrs: false })
const props = defineProps({ tabs: { type: Array, default: () => [] }, selected: String })
const emit = defineEmits(['select', 'close', 'reorder'])
const rail = ref(null)
const popup = ref(null)
const revealed = ref(null)
const actions = ref(false)
let collapseTimer
let holdTimer
let held = false
const drag = shallowRef(null)
let pressed
let suppressClick = false

function tabStyle(tab) {
  const accent = tab?.accent || '#607d8b'
  const hex = accent.match(/^#([\da-f]{3}|[\da-f]{6})$/i)?.[1]
  const channels = hex && (hex.length === 3 ? [...hex].map(value => value + value) : hex.match(/../g))
  const darker = props.selected === tab?.id ? 1.35 : 1.65
  return { '--tab-accent': accent, '--tab-icon-color': channels
    ? readableText(channels.map(value => parseInt(value, 16) / darker)) : 'var(--on-selected)' }
}

function cancelCollapse() { clearTimeout(collapseTimer) }
function collapse() {
  cancelCollapse()
  collapseTimer = setTimeout(() => {
    if (actions.value || drag.value) return
    popup.value?.hidePopover()
    revealed.value = null
  }, 350)
}
async function reveal(tab, event) {
  if (pressed) return
  if (event.type === 'pointerenter' && event.pointerType !== 'mouse') return
  if (actions.value && popup.value?.matches(':popover-open')) return
  cancelCollapse()
  actions.value = false
  const bounds = event.currentTarget.getBoundingClientRect()
  revealed.value = tab
  await nextTick()
  if (!popup.value || revealed.value?.id !== tab.id) return
  const title = popup.value.querySelector('.section-tab-title')
  const range = document.createRange()
  range.selectNodeContents(title)
  popup.value.style.width = (Math.min(innerWidth - 8, 320, Math.max(260, range.getBoundingClientRect().width + 112)) - 4) + 'px'
  popup.value.style.top = Math.max(0, Math.min(bounds.top, innerHeight - 38)) + 'px'
  popup.value.style.left = bounds.left + 'px'
  popup.value.showPopover()
}
function select(id) {
  if (held) { held = false; return }
  popup.value?.hidePopover(); revealed.value = null; emit('select', id)
}
function close(id) { popup.value?.hidePopover(); revealed.value = null; emit('close', id) }
async function openActions(tab, anchor) {
  cancelCollapse()
  const bounds = anchor.getBoundingClientRect()
  actions.value = true
  revealed.value = tab
  await nextTick()
  popup.value.style.width = ''
  popup.value.showPopover()
  popup.value.style.top = Math.max(4, Math.min(bounds.bottom, innerHeight - popup.value.offsetHeight - 8)) + 'px'
  popup.value.style.left = Math.max(4, Math.min(bounds.left, innerWidth - popup.value.offsetWidth - 4)) + 'px'
}
function press(tab, event) {
  clearTimeout(holdTimer)
  held = false
  if (event.pointerType !== 'touch') return
  const anchor = event.currentTarget
  holdTimer = setTimeout(() => { held = true; openActions(tab, anchor) }, 500)
}
function cancelHold() { clearTimeout(holdTimer) }
function release(tab, event) {
  clearTimeout(holdTimer)
  if (!held) return
  const anchor = event.currentTarget
  // Native popover light-dismiss runs when the original touch ends outside it.
  holdTimer = setTimeout(() => openActions(tab, anchor), 0)
}
function reorder(direction) {
  const index = props.tabs.findIndex(tab => tab.id === revealed.value.id)
  emit('reorder', index, index + direction)
  popup.value.hidePopover()
  revealed.value = null
}
function move(event) {
  const buttons = [...rail.value.querySelectorAll('[role="tab"]')]
  let index = buttons.indexOf(event.target)
  if (index < 0) return
  if (event.key === 'ArrowDown') index = (index + 1) % buttons.length
  else if (event.key === 'ArrowUp') index = (index + buttons.length - 1) % buttons.length
  else if (event.key === 'Home') index = 0
  else if (event.key === 'End') index = buttons.length - 1
  else if (event.key === 'Delete') { event.preventDefault(); close(props.tabs[index].id); return }
  else return
  event.preventDefault()
  buttons[index].focus()
}
function startDrag(tab, event) {
  suppressClick = false
  if (pressed || event.button !== 0 || !event.isPrimary || event.pointerType === 'touch'
      || actions.value || revealed.value?.id !== tab.id) return
  const boxes = [...rail.value.querySelectorAll('.section-tab-row')].map(node => {
    const bounds = node.getBoundingClientRect(), translated = parseFloat(getComputedStyle(node).translate.split(' ')[1]) || 0
    return { top: bounds.top - translated, bottom: bounds.bottom - translated, height: bounds.height }
  })
  pressed = { node: event.currentTarget, pointer: event.pointerId, source: props.tabs.indexOf(tab),
    x: event.clientX, y: event.clientY, scroll: rail.value.scrollTop, top: parseFloat(popup.value.style.top), boxes }
  cancelCollapse()
  document.addEventListener('pointermove', dragSection, { passive: false })
  document.addEventListener('pointerup', finishDrag)
  document.addEventListener('pointercancel', cancelPointer)
  document.addEventListener('lostpointercapture', cancelPointer)
  document.addEventListener('keydown', cancelKey)
  window.addEventListener('blur', cancelDrag)
}
function dragSection(event) {
  if (!pressed || event.pointerId !== pressed.pointer) return
  const dy = event.clientY - pressed.y
  if (!drag.value) {
    if (Math.abs(dy) < 10 || Math.abs(dy) < Math.abs(event.clientX - pressed.x)) return
    pressed.node.setPointerCapture(pressed.pointer)
  }
  event.preventDefault()
  const translation = dy + rail.value.scrollTop - pressed.scroll
  const box = pressed.boxes[pressed.source], center = box.top + box.height / 2 + translation
  // Native indexAt(rail.width / 2, ...) misses collapsed 48px rows; hit-test their Y instead.
  let target = pressed.boxes.findIndex(row => center >= row.top && center < row.bottom)
  if (target < 0) target = center < pressed.boxes[0].top ? 0 : props.tabs.length - 1
  drag.value = { source: pressed.source, target, translation, step: box.height + 3 }
  popup.value.style.top = pressed.top + dy + 'px'
}
function finishDrag(event) {
  if (!pressed || event.pointerId !== pressed.pointer) return
  const finished = drag.value
  cancelDrag()
  if (finished && finished.source !== finished.target) emit('reorder', finished.source, finished.target)
}
function cancelPointer(event) { if (pressed && event.pointerId === pressed.pointer) cancelDrag() }
function cancelKey(event) {
  if (event.key !== 'Escape') return
  event.preventDefault(); event.stopPropagation(); cancelDrag()
}
function cancelDrag() {
  const previous = pressed
  suppressClick ||= !!drag.value
  pressed = null; drag.value = null
  document.removeEventListener('pointermove', dragSection)
  document.removeEventListener('pointerup', finishDrag)
  document.removeEventListener('pointercancel', cancelPointer)
  document.removeEventListener('lostpointercapture', cancelPointer)
  document.removeEventListener('keydown', cancelKey)
  window.removeEventListener('blur', cancelDrag)
  if (previous?.node.hasPointerCapture(previous.pointer)) previous.node.releasePointerCapture(previous.pointer)
  nextTick(positionRevealed)
  collapse()
}
function positionRevealed() {
  if (!revealed.value || actions.value || drag.value) return
  const row = [...rail.value.querySelectorAll('.section-tab-row')].find(node => node.dataset.sectionId === revealed.value.id)
  if (!row) return
  const bounds = row.getBoundingClientRect(), viewport = rail.value.getBoundingClientRect()
  if (bounds.bottom <= viewport.top || bounds.top >= viewport.bottom) { popup.value.hidePopover(); revealed.value = null; return }
  popup.value.style.top = Math.max(0, Math.min(bounds.top + 2, innerHeight - 38)) + 'px'
}
function rowOffset(index) {
  return !drag.value ? 0 : index === drag.value.source ? drag.value.translation
    : displacedTabOffset(index, drag.value.source, drag.value.target, drag.value.step)
}
function afterDrag(event) {
  if (!suppressClick || !event.detail) return
  suppressClick = false; event.preventDefault(); event.stopPropagation()
}
function resized() {
  cancelDrag(); cancelCollapse(); clearTimeout(holdTimer)
  popup.value?.hidePopover()
  revealed.value = null; actions.value = false; held = false
}
onMounted(() => window.addEventListener('resize', resized))
onBeforeUnmount(() => {
  window.removeEventListener('resize', resized)
  cancelDrag(); cancelCollapse(); clearTimeout(holdTimer)
})
watch(() => props.tabs.map(tab => tab.id), () => {
  cancelDrag()
  if (revealed.value && !props.tabs.some(tab => tab.id === revealed.value.id)) {
    popup.value?.hidePopover(); revealed.value = null; actions.value = false
  }
})
</script>

<template>
  <nav ref="rail" v-bind="$attrs" class="section-tab-rail" :class="{ reordering: drag }" role="tablist" aria-orientation="vertical" :aria-label="t('Open sections')" @keydown="move" @scroll="positionRevealed" @pointerdown.capture="suppressClick = false" @click.capture="afterDrag">
    <div v-for="(tab, index) in tabs" :key="tab.id" class="section-tab-row" :class="{ current: selected === tab.id, dragging: drag?.source === index }" :data-section-id="tab.id"
      :style="{ ...tabStyle(tab), '--section-drag-y': rowOffset(index) + 'px' }" @dragstart.prevent>
    <AppButton role="tab" class="section-tab" :label="tab.title"
      :aria-selected="selected === tab.id" :tabindex="selected === tab.id ? 0 : -1" :title="tab.title"
      @click="select(tab.id)" @auxclick.prevent="$event.button === 1 && close(tab.id)"
      @contextmenu.prevent="openActions(tab, $event.currentTarget)" @keydown.shift.f10.prevent="openActions(tab, $event.currentTarget)"
      @pointerdown="press(tab, $event); startDrag(tab, $event)" @pointerup="release(tab, $event)" @pointercancel="cancelHold" @pointermove="cancelHold"
      @pointerenter="reveal(tab, $event)" @pointerleave="collapse" @focus="reveal(tab, $event)"
      >
      <span class="section-tab-badge"><AppIcon :name="tab.icon || 'link'" /></span>
    </AppButton>
    </div>
  </nav>
  <div ref="popup" class="section-tab-reveal" :class="{ 'section-tab-reveal-actions': actions, current: selected === revealed?.id, dragging: !!drag }" popover="auto" :aria-label="revealed?.title"
    :style="tabStyle(revealed)" @pointerenter="cancelCollapse" @pointerleave="collapse"
    @focusout="collapse" @focusin="cancelCollapse" @pointerdown.capture="suppressClick = false" @click.capture="afterDrag" @keydown.esc="cancelDrag(); popup.hidePopover(); revealed = null">
    <template v-if="revealed && actions">
      <strong>{{ revealed.title }}</strong>
      <AppButton label="Move section up" icon="previous" :disabled="tabs[0]?.id === revealed.id" @click="reorder(-1)" />
      <AppButton label="Move section down" icon="next" :disabled="tabs.at(-1)?.id === revealed.id" @click="reorder(1)" />
      <AppButton label="Close tab" icon="close" @click="close(revealed.id)" />
    </template>
    <template v-else-if="revealed">
      <AppButton class="section-tab-expanded" :label="revealed.title" :aria-pressed="selected === revealed.id" @pointerdown="startDrag(revealed, $event)" @click="select(revealed.id)" @auxclick.prevent="$event.button === 1 && close(revealed.id)">
        <span class="section-tab-badge"><AppIcon :name="revealed.icon || 'link'" /></span><span class="section-tab-title">{{ revealed.title }}</span>
      </AppButton>
      <AppButton icon-only icon="close" label="Close tab" @click="close(revealed.id)" />
    </template>
  </div>
</template>
