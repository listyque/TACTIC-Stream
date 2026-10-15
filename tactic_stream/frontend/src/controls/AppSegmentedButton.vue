<script setup>
// Handler controls/SegmentedButton.qml.
import AppButton from './AppButton.vue'
import { t } from '../i18n.js'
const props = defineProps({ options: Array, label: String, disabled: Boolean, outlined: Boolean, iconOnly: Boolean })
const model = defineModel()
function move(event) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key) || props.disabled) return
  event.preventDefault()
  const index = props.options.findIndex(row => row.value === model.value), count = props.options.length
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? count - 1 : (index + (event.key === 'ArrowRight' ? 1 : count - 1)) % count
  model.value = props.options[next].value; event.currentTarget.querySelectorAll('button')[next].focus()
}
</script>
<template>
  <div class="app-segmented-button" :class="{ outlined }" role="radiogroup" :aria-label="t(label)" @keydown="move">
    <AppButton v-for="option in options" :key="option.value" :label="option.label" :icon="option.icon" :icon-only="iconOnly" role="radio" :aria-checked="model === option.value" :tabindex="model === option.value ? 0 : -1" :disabled="disabled" @click="model = option.value" />
  </div>
</template>
<style>
/* Qt's 3px content inset includes the CSS 1px border. */
.app-segmented-button { display: flex; padding: 2px; height: var(--control-height); border: 1px solid var(--outline-variant); border-radius: var(--item-radius); background: var(--surface-high); }
.app-segmented-button .app-button { flex: 1; min-width: 0; height: 100%; min-height: 0; padding: 0 5px; border: 0; border-radius: max(3px, calc(var(--item-radius) - 2px)); background: transparent; gap: 6px; font-size: var(--text-body); font-weight: 500; }
.app-segmented-button .app-button[aria-checked="true"] { background: var(--selected); color: var(--on-selected); font-weight: 600; }
.app-segmented-button .app-icon { width: 15px; height: 15px; font-size: 15px; color: var(--muted); flex:none; }
.app-segmented-button .app-button > span:not(.app-icon):not(.control-ripple-clip) { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.app-segmented-button [aria-checked="true"] .app-icon { color: inherit; }
.app-segmented-button.outlined { background:transparent; border:0; padding:3px; }
.app-segmented-button.outlined .app-button[aria-checked="true"] { border:1px solid var(--primary); background:var(--surface-high); color:var(--primary); }
</style>
