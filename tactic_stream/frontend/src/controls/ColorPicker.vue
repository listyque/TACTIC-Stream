<script setup>
// Handler controls/ColorPickerDialog.qml (EPL-1.0): HSV plane, hue, HEX and explicit acceptance.
import { computed, ref } from 'vue'
import { t } from '../i18n.js'
import AppButton from './AppButton.vue'
import AppSlider from './AppSlider.vue'
import AppTextField from './AppTextField.vue'
const emit = defineEmits(['chosen'])
const dialog = ref(null), hue = ref(0), saturation = ref(0), brightness = ref(1), hex = ref('#ffffff')
const valid = computed(() => /^#[\da-f]{6}$/i.test(hex.value))
function setColor(value) {
  if (!/^#[\da-f]{6}$/i.test(value || '')) return
  const [r, g, b] = [1, 3, 5].map(index => parseInt(value.slice(index, index + 2), 16) / 255)
  const max = Math.max(r, g, b), delta = max - Math.min(r, g, b)
  hue.value = delta ? (((max === r ? (g - b) / delta : max === g ? (b - r) / delta + 2 : (r - g) / delta + 4) / 6) + 1) % 1 : 0
  saturation.value = max ? delta / max : 0; brightness.value = max; hex.value = value.toLowerCase()
}
function updateHex() {
  const h = hue.value * 6, c = brightness.value * saturation.value, x = c * (1 - Math.abs(h % 2 - 1)), m = brightness.value - c
  const rgb = [[c, x, 0], [x, c, 0], [0, c, x], [0, x, c], [x, 0, c], [c, 0, x]][Math.floor(h) % 6]
  hex.value = '#' + rgb.map(value => Math.round((value + m) * 255).toString(16).padStart(2, '0')).join('')
}
function choose(event) {
  const plane = event.currentTarget, box = plane.getBoundingClientRect()
  if (event.type === 'pointerdown') { if (event.button !== 0) return; plane.setPointerCapture(event.pointerId); plane.focus() }
  if (event.type === 'pointermove' && !plane.hasPointerCapture(event.pointerId)) return
  saturation.value = Math.max(0, Math.min(1, (event.clientX - box.x) / box.width))
  brightness.value = Math.max(0, Math.min(1, 1 - (event.clientY - box.y) / box.height)); updateHex()
}
function key(event) {
  if (!event.key.startsWith('Arrow')) return
  event.preventDefault()
  saturation.value = Math.max(0, Math.min(1, saturation.value + (event.key === 'ArrowRight' ? .01 : event.key === 'ArrowLeft' ? -.01 : 0)))
  brightness.value = Math.max(0, Math.min(1, brightness.value + (event.key === 'ArrowUp' ? .01 : event.key === 'ArrowDown' ? -.01 : 0))); updateHex()
}
function open(value) { setColor(/^#[\da-f]{6}$/i.test(value || '') ? value : getComputedStyle(document.documentElement).getPropertyValue('--primary').trim()); dialog.value.showModal() }
function accept() { if (!valid.value) return; emit('chosen', hex.value.toLowerCase()); dialog.value.close() }
defineExpose({ open })
</script>
<template>
  <dialog ref="dialog" class="color-picker" :aria-label="t('Choose a color')" @close="hex = '#ffffff'">
    <header><h2>{{ t('Choose a color') }}</h2></header>
    <div class="color-picker-fields">
      <div class="color-picker-plane" role="slider" tabindex="0" :aria-label="t('Saturation and brightness')" :aria-valuetext="hex" :aria-valuenow="Math.round(brightness * 100)" :aria-valuemin="0" :aria-valuemax="100" :aria-description="t('Use the arrow keys to adjust the color')"
        :style="{ '--hue': hue * 360 + 'deg' }" @pointerdown="choose" @pointermove="choose" @keydown="key">
        <span :style="{ left: saturation * 100 + '%', top: (1 - brightness) * 100 + '%' }" />
      </div>
      <label>{{ t('Hue') }}</label><AppSlider v-model="hue" label="Hue" :min="0" :max="1" :step=".005" class="color-picker-hue" @update:model-value="updateHex" />
      <div class="color-picker-hex"><span class="color-swatch" :style="{ background: valid ? hex : '#000000' }" aria-hidden="true" /><AppTextField v-model="hex" label="Color in HEX format" :aria-invalid="!valid" @change="setColor(hex)" /></div>
    </div>
    <footer><AppButton label="Cancel" @click="dialog.close()" /><AppButton label="OK" :disabled="!valid" @click="accept" /></footer>
  </dialog>
</template>
<style>
.color-swatch { width:var(--control-height); height:var(--control-height); flex:0 0 var(--control-height); border:1px solid var(--outline-variant); border-radius:var(--item-radius); }
.app-color-input > .app-button { flex:1; }
.color-picker { width:min(380px, calc(100vw - 32px)); max-height:calc(100dvh - 32px); padding:0; border:1px solid var(--outline-variant); border-radius:var(--dialog-radius); color:var(--on-surface); background:var(--surface-high); box-shadow:0 6px 14px var(--shadow-color); overflow:auto; }
.color-picker::backdrop { background:var(--scrim); }
.color-picker > header { display:flex; align-items:center; gap:8px; height:62px; padding:0 20px; border-bottom:1px solid var(--outline-variant); background:var(--surface-highest, var(--hover)); }
.color-picker > header h2 { flex:1; font-size:16px; font-weight:600; }
.color-picker-fields { display:grid; gap:12px; padding:32px 20px 20px; }
.color-picker-plane { height:190px; position:relative; border:1px solid var(--outline-variant); background:linear-gradient(to top, #000, transparent), linear-gradient(to right, #fff, transparent), hsl(var(--hue) 100% 50%); touch-action:none; }
.color-picker-plane > span { position:absolute; width:12px; height:12px; border-radius:50%; border:2px solid #fff; box-shadow:0 0 0 1px #000; transform:translate(-50%,-50%); pointer-events:none; }
.color-picker-hue::-webkit-slider-runnable-track { background:linear-gradient(to right, #f00, #ff0, #0f0, #0ff, #00f, #f0f, #f00); height:6px; }
.color-picker-hue::-moz-range-track { background:linear-gradient(to right, #f00, #ff0, #0f0, #0ff, #00f, #f0f, #f00); height:6px; }
.color-picker-hex { display:flex; align-items:center; gap:8px; }
.color-picker-hex > input { flex:1; width:0; }
.color-picker > footer { display:flex; justify-content:flex-end; gap:8px; padding:24px 14px 12px; }
.color-picker > footer .app-button { min-width:70px; }
</style>
