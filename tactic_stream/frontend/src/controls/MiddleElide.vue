<script setup>
// Native Text.ElideMiddle keeps the filename extension visible.
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
const props = defineProps({ text: String })
const label = ref(null), displayed = ref(props.text || '')
let observer, context
function measure() {
  if (!label.value || !context) return
  const style = getComputedStyle(label.value), width = label.value.clientWidth
  context.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`
  const text = props.text || ''
  if (context.measureText(text).width <= width) { displayed.value = text; return }
  const parts = Array.from(text), candidate = length => parts.slice(0, Math.ceil(length / 2)).join('') + '…' + parts.slice(parts.length - Math.floor(length / 2)).join('')
  let low = 0, high = parts.length
  while (low < high) { const mid = Math.ceil((low + high) / 2); if (context.measureText(candidate(mid)).width <= width) low = mid; else high = mid - 1 }
  displayed.value = candidate(low)
}
onMounted(() => { context = document.createElement('canvas').getContext('2d'); observer = new ResizeObserver(measure); observer.observe(label.value); document.fonts.ready.then(measure); measure() })
onBeforeUnmount(() => observer?.disconnect())
watch(() => props.text, () => nextTick(measure))
</script>
<template><span ref="label" class="middle-elide" :title="text" :aria-label="text">{{ displayed }}</span></template>
<style>.middle-elide { display:block; min-width:0; overflow:hidden; white-space:nowrap; }</style>
